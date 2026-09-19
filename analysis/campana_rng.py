#!/usr/bin/env python3
"""Captura de la campana del firmware del TFM_RNG (repeticiones nuevas).

Habla el protocolo de aquel firmware (tfm_esp32_rng/firmware/main/main.c):
bloques `### RNG_BEGIN cond=X rep=N bytes=125000 temp_c=.. throughput_Bps=..`,
lineas hex de 64 bytes y `### RNG_END cond=X rep=N crc32=0x.. temp_c=..`.
Se diferencia de su capture_rng.py en dos cosas que este proyecto exige:
guarda el flujo serie INTEGRO en un log y numera las repeticiones a partir
de --primera-rep, para que las secuencias nuevas no pisen las de la
campana original (cond?_rep1.bin del 2026-08-04).

    python analysis/campana_rng.py --puerto COM7 --reps 2 --primera-rep 2

Salidas en results/esp32_campana_rng/: cond{A..D}_rep{N}.bin (CRC32 y
longitud comprobados), capture_log.csv (misma cabecera que la original mas
la MAC) y serie_<sesion>.log. temp_c es el sensor ROM del ESP32: entero de
8 bits en grados Fahrenheit, resolucion 0,556 C; no sirve para tendencias.
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

DESTINO = Path(__file__).resolve().parent.parent / "results" / "esp32_campana_rng"
RE_KV = re.compile(r"(\w+)=([^\s]+)")
HEXCHARS = set("0123456789abcdef")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", default="COM7")
    ap.add_argument("--reps", type=int, default=2, help="secuencias validas por condicion")
    ap.add_argument("--primera-rep", type=int, default=2, help="numero de la primera repeticion nueva")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--sesion", default=time.strftime("%Y%m%d_%H%M%S"))
    args = ap.parse_args()

    DESTINO.mkdir(parents=True, exist_ok=True)
    log = DESTINO / f"serie_{args.sesion}.log"
    tengo = {c: 0 for c in "ABCD"}
    filas = []
    ruta_csv = DESTINO / "capture_log.csv"

    def anotar(fila):
        nuevo = not ruta_csv.exists()
        with ruta_csv.open("a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if nuevo:
                w.writerow(["cond", "rep", "temp_begin_c", "temp_end_c", "throughput_Bps",
                            "crc_ok", "mac", "sesion"])
            w.writerow(fila)
    mac = "?"
    modo = None
    hexbuf: list[str] = []
    meta: dict = {}
    rechazos = 0

    with serial.Serial(args.puerto, 115200, timeout=2) as s, log.open("w", encoding="utf-8") as f:
        s.dtr = False; s.rts = True; time.sleep(0.1); s.rts = False   # reset, arranque normal
        s.reset_input_buffer()
        t0 = time.time()
        while time.time() - t0 < args.timeout and any(tengo[c] < args.reps for c in "ABCD"):
            cruda = s.readline()
            if not cruda:
                continue
            linea = cruda.decode("utf-8", errors="replace")
            f.write(linea); f.flush()
            linea = linea.strip()
            if linea.startswith("### DEVICE"):
                mac = dict(RE_KV.findall(linea)).get("mac", "?")
                print(f"  [dev] {linea[4:]}")
            elif linea.startswith("### RNG_BEGIN"):
                modo, hexbuf, meta = "RNG", [], dict(RE_KV.findall(linea))
            elif linea.startswith("### RNG_END") and modo == "RNG":
                fin = dict(RE_KV.findall(linea))
                cond = meta.get("cond", "?")
                esperado = int(meta.get("bytes", "125000"))
                datos = bytes.fromhex("".join(hexbuf)) if all(len(h) % 2 == 0 for h in hexbuf) else b""
                crc_ok = zlib.crc32(datos) == int(fin.get("crc32", "0"), 16)
                if cond not in tengo or len(datos) != esperado or not crc_ok:
                    rechazos += 1
                    print(f"  [rng] cond={cond} RECHAZADA (len={len(datos)}/{esperado} crc_ok={crc_ok})")
                elif tengo[cond] >= args.reps:
                    print(f"  [rng] cond={cond} sobrante, ignorada")
                else:
                    rep = args.primera_rep + tengo[cond]
                    tengo[cond] += 1
                    (DESTINO / f"cond{cond}_rep{rep}.bin").write_bytes(datos)
                    fila = [cond, rep, meta.get("temp_c", ""), fin.get("temp_c", ""),
                            meta.get("throughput_Bps", ""), 1, mac, args.sesion]
                    filas.append(fila)
                    anotar(fila)   # en el acto: si la captura muere, la fila ya esta
                    print(f"  [rng] cond={cond} rep={rep} {len(datos)} B ok  temp={meta.get('temp_c','?')}->"
                          f"{fin.get('temp_c','?')} C  tput={meta.get('throughput_Bps','?')} B/s  "
                          f"[{sum(tengo.values())}/{4*args.reps}]")
                modo = None
            elif linea.startswith("### "):
                print(f"  [fw] {linea[4:80]}")
            elif modo == "RNG":
                # solo lineas hex limpias: cualquier texto intercalado (log del
                # driver) invalida el bloque por CRC en vez de "sanearlo"
                if linea and set(linea) <= HEXCHARS:
                    hexbuf.append(linea)
                else:
                    hexbuf.append("zz")   # fuerza el rechazo del bloque

    resumen = ", ".join(f"{c}:{tengo[c]}" for c in "ABCD")
    print(f"secuencias validas {resumen}; rechazadas {rechazos}; log integro {log}")
    return 0 if all(tengo[c] >= args.reps for c in "ABCD") else 1


if __name__ == "__main__":
    raise SystemExit(main())
