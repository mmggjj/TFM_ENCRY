#!/usr/bin/env python3
"""Captura de la prueba de reinicios del RNG del ESP32 (SP 800-90B, 3.1.4).

Resetea el chip por EN (RTS del CP2102) y guarda los RST_BYTES que el
firmware lee al arrancar. Repite hasta --n reinicios validos (CRC,
longitud, MAC y variante comprobados). Se puede cortar y seguir: retoma
desde lo que ya haya en el CSV.

    python analysis/reinicios_esp32.py --variante normal --n 1000
    python analysis/reinicios_esp32.py --variante sin_ruido --n 1000
    python analysis/reinicios_esp32.py --variante radio_sin_ruido --n 1000
    python analysis/reinicios_esp32.py --variante espera_sin_ruido --n 1000
    python analysis/reinicios_esp32.py --variante radio --n 1000

normal y sin_ruido (firmware/reinicios*) sacan un bloque por arranque; las
de firmware/reinicios_radio* sacan dos: "antes" (nada mas arrancar, radio
apagada) y "despues" (tras encender el Wi-Fi y esperar 200 ms; en
espera_sin_ruido, la misma espera sin encender la radio).

Salidas en results/esp32_reinicios/mac_<mac>/<variante>/: reinicios.bin
(el bloque que se somete a la prueba: el unico, o el de "despues"; uno de
RST_BYTES por reinicio, en orden), reinicios_antes.bin en las variantes
con radio, reinicios.csv (una fila por reinicio) y serie_<sesion>.log
(flujo serie integro, no se versiona).
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
COLUMNAS_RADIO = COLUMNAS + ["t_us_antes", "ccount_antes", "t_on_us"]
# firmware/reinicios_fuentes (variantes fuente_*): ademas cuando se apago la
# fuente, cuanto duro y si la lectura llego tarde a su instante fijo; en las
# de radio, cuando se encendio la radio segun la PHY (tras start y tras stop);
# en la del ADC, lecturas correctas y la ultima (-1 donde no aplica)
EXTRA_FUENTES = ["t_off_us", "fuente_ms", "tarde", "rf_ts_ini", "rf_ts_fin", "n_adc", "adc_ultimo"]
COLUMNAS_FUENTES = COLUMNAS_RADIO + EXTRA_FUENTES
# firmware/reinicios_paso: variante de retardo y ciclos de cada tramo
EXTRA_PASO = ["var", "n_nops", "c_ini", "c_a", "c_r", "c_d"]
COLUMNAS_PASO = COLUMNAS_RADIO + EXTRA_PASO
# bloques que saca cada variante (None: firmware de un solo bloque, sin RST_FIN)
VARIANTES = {"normal": None, "sin_ruido": None,
             "radio": ["antes", "despues"], "radio_sin_ruido": ["antes", "despues"],
             "espera_sin_ruido": ["antes", "despues"],
             **{v: ["antes", "despues"] for v in (
                 "fuente_control", "fuente_wifi_init", "fuente_radio_0", "fuente_radio_1",
                 "fuente_radio_10", "fuente_radio_100", "fuente_adc_200", "fuente_bootrand_200",
                 "fuente_adc_0", "fuente_adc_1")},
             "paso": ["antes", "despues"]}


def un_reinicio(s: serial.Serial, f, timeout: float, bloques: list[str] | None):
    """Resetea y lee hasta tener todos los bloques. Devuelve
    (cabeceras por bloque, datos por bloque, info, motivo de rechazo)."""
    s.reset_input_buffer()
    s.dtr = False
    s.rts = True
    time.sleep(0.05)
    s.rts = False
    t0 = time.time()
    cab, hexs, boot = None, [], []
    cabs: dict[str, dict] = {}
    datos: dict[str, bytes] = {}
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
            nombre = cab.get("bloque", "unico")
            if not all(set(h) <= HEX and len(h) % 2 == 0 for h in hexs):
                return None, None, None, f"linea hex corrupta ({nombre})"
            d = bytes.fromhex("".join(hexs))
            # una cabecera o un final estropeados por el enlace se rechazan
            # como cualquier otro bloque corrupto (antes hacian saltar int())
            try:
                esperado = int(cab.get("bytes", "0"))
                crc = int(fin.get("crc32", "0"), 16)
            except ValueError:
                return None, None, None, f"cabecera o final corruptos ({nombre})"
            if len(d) != esperado:
                return None, None, None, f"longitud {len(d)} ({nombre})"
            if zlib.crc32(d) != crc:
                return None, None, None, f"crc ({nombre})"
            cabs[nombre], datos[nombre] = cab, d
            cab = None
            if bloques is None:
                return cabs, datos, {"boot": boot, "duracion_s": time.time() - t0}, ""
        elif linea.startswith("### RST_FIN") and bloques is not None:
            if sorted(datos) != sorted(bloques):
                return None, None, None, f"faltan bloques: {sorted(set(bloques) - set(datos))}"
            info = dict(RE_KV.findall(linea))
            info.update({"boot": boot, "duracion_s": time.time() - t0})
            return cabs, datos, info, ""
        elif cab is not None:
            hexs.append(linea)
        elif not cabs:
            boot.append(linea)
    return None, None, None, "tiempo agotado"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", default="COM7")
    ap.add_argument("--variante", required=True, choices=list(VARIANTES))
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--sesion", default=time.strftime("%Y%m%d_%H%M%S"))
    a = ap.parse_args()
    RAIZ.mkdir(parents=True, exist_ok=True)
    bloques = VARIANTES[a.variante]
    principal = "despues" if bloques else "unico"
    otros = [b for b in (bloques or []) if b != principal]

    with serial.Serial(a.puerto, 115200, timeout=0.5) as s:
        # primer reinicio solo para saber la MAC y la carpeta
        with open(RAIZ / f"sondeo_{a.sesion}.log", "w", encoding="utf-8") as f0:
            cabs, _, _, motivo = un_reinicio(s, f0, a.timeout, bloques)
        if cabs is None:
            print(f"sin respuesta valida del firmware: {motivo}")
            return 1
        cab = cabs[principal]
        if cab.get("variante") != a.variante:
            print(f"el chip lleva la variante {cab.get('variante')}, no {a.variante}: flashear antes")
            return 1
        mac = cab["mac"]
        nbytes = int(cab["bytes"])
        dest = RAIZ / f"mac_{mac.replace(':', '')}" / a.variante
        dest.mkdir(parents=True, exist_ok=True)
        (RAIZ / f"sondeo_{a.sesion}.log").unlink()
        ruta_csv = dest / "reinicios.csv"
        rutas = {principal: dest / "reinicios.bin", **{b: dest / f"reinicios_{b}.bin" for b in otros}}
        hechos = sum(1 for _ in ruta_csv.open(encoding="utf-8")) - 1 if ruta_csv.exists() else 0
        for b, r in rutas.items():
            if r.exists() and r.stat().st_size != hechos * nbytes:
                print(f"{r.name} ({r.stat().st_size} B) no cuadra con {hechos} filas del CSV")
                return 1
        print(f"chip {mac}, variante {a.variante}: {hechos} hechos, faltan {max(0, a.n - hechos)}")

        rechazos = 0
        fbs = {b: r.open("ab") for b, r in rutas.items()}
        try:
            with (dest / f"serie_{a.sesion}.log").open("w", encoding="utf-8") as f, \
                    ruta_csv.open("a", newline="", encoding="utf-8") as fc:
                w = csv.writer(fc)
                if hechos == 0:
                    w.writerow(COLUMNAS_FUENTES if a.variante.startswith("fuente_")
                               else COLUMNAS_PASO if a.variante == "paso"
                               else COLUMNAS_RADIO if bloques else COLUMNAS)
                i = hechos
                while i < a.n:
                    # hasta 10 intentos: el enlace serie de algunas placas repite
                    # trozos de lo que llega al PC (el CRC lo detecta); cada
                    # intento es un reinicio nuevo
                    for intento in range(1, 11):
                        f.write(f"\n=== reinicio {i} intento {intento} ===\n")
                        cabs, datos, info, motivo = un_reinicio(s, f, a.timeout, bloques)
                        if cabs is not None and all(c.get("mac") == mac and c.get("variante") == a.variante
                                                    for c in cabs.values()):
                            break
                        rechazos += 1
                        print(f"  reinicio {i} intento {intento} rechazado: {motivo or 'mac/variante'}")
                    else:
                        print("diez rechazos seguidos: paro")
                        return 1
                    boot = "\n".join(info["boot"])
                    encendido = "Enabling RNG early entropy source" in boot and "NO encendida" not in boot
                    aviso = "NO encendida" in boot
                    for b, fb in fbs.items():
                        fb.write(datos[b])
                        fb.flush()
                    cab = cabs[principal]
                    fila = [i, mac, a.variante, cab.get("reset"), cab.get("t_us"), cab.get("ccount"),
                            int(aviso), int(encendido), f"{info['duracion_s']:.2f}", intento]
                    if bloques:
                        fila += [cabs["antes"].get("t_us"), cabs["antes"].get("ccount"),
                                 info.get("t_on_us")]
                    if a.variante.startswith("fuente_"):
                        fila += [info.get(k) for k in EXTRA_FUENTES]
                    elif a.variante == "paso":
                        fila += [info.get(k) for k in EXTRA_PASO]
                    w.writerow(fila)
                    fc.flush()
                    if i % 50 == 0 or i == a.n - 1:
                        print(f"  {i + 1}/{a.n}  primeros bytes {datos[principal][:8].hex()}  reset={cab.get('reset')}"
                              f"  t_us={cab.get('t_us')}  ruido_arranque={'si' if encendido else 'no'}"
                              f"  {info['duracion_s']:.2f} s", flush=True)
                    i += 1
        finally:
            for fb in fbs.values():
                fb.close()
        print(f"hecho: {a.n} reinicios en {dest}; rechazos {rechazos}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
