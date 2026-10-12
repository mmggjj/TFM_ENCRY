#!/usr/bin/env python3
"""Captura de la prueba de reinicios del RNG del ESP32 (SP 800-90B, 3.1.4).

Resetea el chip por EN (RTS del CP2102) y guarda los RST_BYTES que
firmware/reinicios lee nada mas arrancar. Repite hasta --n reinicios
validos (CRC, longitud, MAC y variante comprobados). Se puede cortar y
seguir: retoma desde lo que ya haya en el CSV.

    python analysis/reinicios_esp32.py --variante normal --n 1000
    python analysis/reinicios_esp32.py --variante sin_ruido --n 1000

Salidas en results/esp32_reinicios/mac_<mac>/<variante>/: reinicios.bin
(un bloque de RST_BYTES por reinicio, en orden), reinicios.csv (una fila
por reinicio) y serie_<sesion>.log (flujo serie integro, no se versiona).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import zlib
from pathlib import Path

import serial

RAIZ = Path(__file__).resolve().parent.parent / "results" / "esp32_reinicios"
RE_KV = re.compile(r"(\w+)=([^\s]+)")
HEX = set("0123456789abcdef")
COLUMNAS = ["i", "mac", "variante", "reset", "t_us", "ccount", "aviso_bootloader",
            "ruido_arranque_encendido", "duracion_s", "intentos"]


def un_reinicio(s: serial.Serial, f, timeout: float) -> tuple[dict | None, bytes, str]:
    """Resetea, lee hasta RST_END. Devuelve (cabecera, datos, motivo de rechazo)."""
    s.reset_input_buffer()
    s.dtr = False
    s.rts = True
    time.sleep(0.05)
    s.rts = False
    t0 = time.time()
    cab, hexs, boot = None, [], []
    while time.time() - t0 < timeout:
        cruda = s.readline()
        if not cruda:
            continue
        linea = cruda.decode("utf-8", errors="replace")
        f.write(linea)
        linea = linea.strip()
        if linea.startswith("### RST_BEGIN"):
            cab, hexs = dict(RE_KV.findall(linea)), []
        elif linea.startswith("### RST_END") and cab is not None:
            fin = dict(RE_KV.findall(linea))
            if not all(set(h) <= HEX and len(h) % 2 == 0 for h in hexs):
                return None, b"", "linea hex corrupta"
            datos = bytes.fromhex("".join(hexs))
            if len(datos) != int(cab.get("bytes", "0")):
                return None, b"", f"longitud {len(datos)}"
            if zlib.crc32(datos) != int(fin.get("crc32", "0"), 16):
                return None, b"", "crc"
            cab["boot"] = boot
            cab["duracion_s"] = time.time() - t0
            return cab, datos, ""
        elif cab is not None:
            hexs.append(linea)
        else:
            boot.append(linea)
    return None, b"", "tiempo agotado"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", default="COM7")
    ap.add_argument("--variante", required=True, choices=["normal", "sin_ruido"])
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--sesion", default=time.strftime("%Y%m%d_%H%M%S"))
    a = ap.parse_args()
    RAIZ.mkdir(parents=True, exist_ok=True)

    with serial.Serial(a.puerto, 115200, timeout=0.5) as s:
        # primer reinicio solo para saber la MAC y la carpeta
        with open(RAIZ / f"sondeo_{a.sesion}.log", "w", encoding="utf-8") as f0:
            cab, _, motivo = un_reinicio(s, f0, a.timeout)
        if cab is None:
            print(f"sin respuesta del firmware: {motivo}")
            return 1
        if cab.get("variante") != a.variante:
            print(f"el chip lleva la variante {cab.get('variante')}, no {a.variante}: flashear antes")
            return 1
        mac = cab["mac"]
        dest = RAIZ / f"mac_{mac.replace(':', '')}" / a.variante
        dest.mkdir(parents=True, exist_ok=True)
        (RAIZ / f"sondeo_{a.sesion}.log").unlink()
        ruta_csv, ruta_bin = dest / "reinicios.csv", dest / "reinicios.bin"
        hechos = sum(1 for _ in ruta_csv.open(encoding="utf-8")) - 1 if ruta_csv.exists() else 0
        if ruta_bin.exists() and ruta_bin.stat().st_size != hechos * int(cab["bytes"]):
            print(f"reinicios.bin ({ruta_bin.stat().st_size} B) no cuadra con {hechos} filas del CSV")
            return 1
        print(f"chip {mac}, variante {a.variante}: {hechos} hechos, faltan {max(0, a.n - hechos)}")

        rechazos = 0
        with (dest / f"serie_{a.sesion}.log").open("w", encoding="utf-8") as f, \
                ruta_bin.open("ab") as fb, ruta_csv.open("a", newline="", encoding="utf-8") as fc:
            w = csv.writer(fc)
            if hechos == 0:
                w.writerow(COLUMNAS)
            i = hechos
            while i < a.n:
                for intento in range(1, 4):
                    f.write(f"\n=== reinicio {i} intento {intento} ===\n")
                    cab, datos, motivo = un_reinicio(s, f, a.timeout)
                    if cab is not None and cab.get("mac") == mac and cab.get("variante") == a.variante:
                        break
                    rechazos += 1
                    print(f"  reinicio {i} intento {intento} rechazado: {motivo or 'mac/variante'}")
                else:
                    print("tres rechazos seguidos: paro")
                    return 1
                boot = "\n".join(cab["boot"])
                encendido = "Enabling RNG early entropy source" in boot and "NO encendida" not in boot
                aviso = "NO encendida" in boot
                fb.write(datos)
                fb.flush()
                w.writerow([i, mac, a.variante, cab.get("reset"), cab.get("t_us"), cab.get("ccount"),
                            int(aviso), int(encendido), f"{cab['duracion_s']:.2f}", intento])
                fc.flush()
                if i % 50 == 0 or i == a.n - 1:
                    print(f"  {i + 1}/{a.n}  primeros bytes {datos[:8].hex()}  reset={cab.get('reset')}"
                          f"  t_us={cab.get('t_us')}  ruido_arranque={'si' if encendido else 'no'}"
                          f"  {cab['duracion_s']:.2f} s")
                i += 1
        print(f"hecho: {a.n} reinicios en {dest}; rechazos {rechazos}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
