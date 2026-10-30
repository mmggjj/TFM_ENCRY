#!/usr/bin/env python3
"""Tasa de fallos de la via IID de ea_iid (SP 800-90B v1.1.8) con datos
buenos del mismo tamano que las capturas del ESP32: 125 000 B en modo byte
y 10^6 bits en modo bit, de os.urandom. Sin esta referencia no se puede
decir si un fallo suelto del ESP32 es mucho o poco.

    python analysis/calibra_iid.py --genera 1000 200   crea y evalua (WSL, horas)
    python analysis/calibra_iid.py                     resume lo que haya

Los ficheros (unos 300 MB) van a results/entropia90b/calibracion/, que no se
sube; el resumen, a results/chi2_90b/calibracion_ea_iid.csv.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
CAL = RAIZ / "results" / "entropia90b" / "calibracion"
SALIDA = RAIZ / "results" / "chi2_90b" / "calibracion_ea_iid.csv"


def genera(n_bytes: int, n_bits: int) -> None:
    CAL.mkdir(parents=True, exist_ok=True)
    for i in range(n_bytes):
        f = CAL / f"csprng_{i:03d}.bin"
        if not f.exists():
            f.write_bytes(os.urandom(125000))
    for i in range(n_bits):
        f = CAL / f"csprng_{i:03d}.bits"
        if not f.exists():
            b = np.frombuffer((CAL / f"csprng_{i:03d}.bin").read_bytes(), dtype=np.uint8)
            f.write_bytes(np.unpackbits(b).tobytes())
    en_windows = sys.platform == "win32"
    wsl = ("/mnt/" + CAL.drive[0].lower() + CAL.as_posix()[2:]) if en_windows else CAL.as_posix()
    ea = "~/SP800-90B_EntropyAssessment/cpp/ea_iid"
    orden = (f"cd {wsl} && "
             f"ls csprng_*.bin | while read f; do [ -f \"$f.iid8.json\" ] || echo \"$f\"; done | "
             f"xargs -P 12 -I{{}} sh -c 'OMP_NUM_THREADS=1 {ea} -i -a -o {{}}.iid8.json {{}} 8 > {{}}.iid8.log 2>&1'; "
             f"ls csprng_*.bits | while read f; do [ -f \"$f.iid1.json\" ] || echo \"$f\"; done | "
             f"xargs -P 12 -I{{}} sh -c 'OMP_NUM_THREADS=1 {ea} -i -a -o {{}}.iid1.json {{}} 1 > {{}}.iid1.log 2>&1'")
    subprocess.run((["wsl.exe", "-e"] if en_windows else []) + ["bash", "-lc", orden], check=True)


def resume() -> None:
    filas = []
    for modo, patron in (("byte", "*.bin.iid8.json"), ("bit", "*.bits.iid1.json")):
        fs = sorted(glob.glob(str(CAL / patron)))
        if not fs:
            continue
        perm = chi = lrs = alguno = 0
        for f in fs:
            t = json.loads(Path(f).read_text(encoding="utf-8"))["testCases"][0]
            a, b, c = (not t["passedIidPermutationTests"], not t["passedChiSquareTests"],
                       not t["passedLongestRepeatedSubstringTest"])
            perm += a; chi += b; lrs += c; alguno += a or b or c
        n = len(fs)
        filas.append([modo, n, perm, chi, lrs, alguno])
        print(f"{modo:4s} {n:5d} ficheros: permutacion {perm} ({perm / n * 100:.1f} %), chi2 {chi} "
              f"({chi / n * 100:.1f} %), LRS {lrs}, alguna {alguno} ({alguno / n * 100:.1f} %)")
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["modo", "ficheros", "fallos_permutacion", "fallos_chi2", "fallos_lrs", "fallos_alguna"])
        w.writerows(filas)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--genera", type=int, nargs=2, metavar=("N_BYTE", "N_BIT"))
    a = ap.parse_args()
    if a.genera:
        genera(*a.genera)
    resume()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
