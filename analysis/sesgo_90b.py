#!/usr/bin/env python3
"""Bits independientes con sesgo bajo SP 800-90B no-IID (modo bit).

Contraste para la tabla O8: ¿basta un sesgo de ~0,2 % (ciclo de trabajo de
ro1 distinto del 50 %, ero_core muestrea ro1 directamente) para dar el
perfil por estimador de la FPGA? Misma vía que el ESP32 y la fuente
simulada (entropia_90b.ejecutar).

    ~/eda/venv/bin/python analysis/sesgo_90b.py --p1 0.4979 --n 1000000 8378368
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entropia_90b as e90                       # noqa: E402

DIR = e90.RES / "sesgo_90b"
SEC = DIR / "secuencias"                         # se regeneran: fuera de git


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--p1", type=float, nargs="+", default=[0.4979])
    ap.add_argument("--n", type=int, nargs="+", default=[1_000_000])
    ap.add_argument("--semillas", type=int, nargs="+", default=[1, 2, 3])
    a = ap.parse_args()
    SEC.mkdir(parents=True, exist_ok=True)
    e90.DIR90B = DIR
    filas = []
    for p1 in a.p1:
        for n in a.n:
            for s in a.semillas:
                rng = np.random.default_rng(1000 * s + 7)
                bits = (rng.random(n) < p1).astype(np.uint8)
                nombre = f"p{p1:.4f}_n{n}_s{s}"
                fich = SEC / f"{nombre}.bits"
                fich.write_bytes(bits.tobytes())
                f = e90.ejecutar(nombre, fich, "noniid", "b1")
                f.update({"p1": p1, "n_bits": n, "semilla": s,
                          "frac_unos": float(bits.mean())})
                filas.append(f)
    claves = sorted({k for f in filas for k in f})
    with open(DIR / "sesgo_90b.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=claves)
        w.writeheader()
        w.writerows(filas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
