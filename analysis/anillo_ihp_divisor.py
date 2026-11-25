#!/usr/bin/env python3
"""Divisor del integrado a partir de las realizaciones de anillo_ihp_repeticiones.py.

Q por periodo del anillo muestreado (ro1) -> H_min del bit para cada CFG_KD,
con la ventana de 2^CFG_KD periodos de ro2. T(ro2)/T(ro1): --razon (simulada,
results/anillo_ihp_periodo_*) o, sin ella, etapas2/etapas1; se ignora el jitter de ro2
(conservador). Factor de peor chip: cociente peor/medio de K_D del Monte
Carlo de 5 etapas en la misma esquina (23 chips, docs/anillo_ihp.md §4.3).

    ~/eda/venv/bin/python analysis/anillo_ihp_divisor.py --prefijo ss_m40_v108_e11_
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ero_model import entropias_exactas  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefijo", default="ss_m40_v108_e11_")
    ap.add_argument("--etapas-ro2", type=int, default=13)
    ap.add_argument("--peor-chip", type=float, default=4494997 / 3824707)
    ap.add_argument("--razon", type=float, default=0.0, help="T(ro2)/T(ro1) simulada")
    ap.add_argument("--kd", default="22,23,24,25,26")
    a = ap.parse_args()
    filas = []
    for f in sorted(RES.glob(f"anillo_ihp_{a.prefijo}[0-9][0-9].json")):
        an = json.loads(f.read_text())["anillo"][0]
        filas.append((f.name, an["etapas"], an["periodo_ps"], an["sigma_fs"], an["q_periodo"],
                      an["n_espurios"]))
    if not filas:
        print("sin realizaciones")
        return 1
    print("| realizacion | etapas | T ps | sigma fs | Q por periodo | dobles cruces |")
    print("|---|---|---|---|---|---|")
    for r in filas:
        print(f"| {r[0]} | {r[1]} | {r[2]:.3f} | {r[3]:.1f} | {r[4]:.3e} | {r[5]} |")
    q = np.array([r[4] for r in filas])
    e1 = filas[0][1]
    razon = a.razon or a.etapas_ro2 / e1
    print(f"\nn = {q.size}; Q media {q.mean():.3e}, dispersion {100 * q.std(ddof=1) / q.mean():.1f} %, "
          f"minima {q.min():.3e}")
    origen = "SIMULADA" if a.razon else f"{a.etapas_ro2}/{e1}, ESTIMADA"
    print(f"T(ro2)/T(ro1) = {razon:.4f} [{origen}]; peor chip Q/{a.peor_chip:.3f}\n")
    casos = [("Q media", q.mean()), ("Q minima", q.min()), ("Q minima, peor chip", q.min() / a.peor_chip)]
    print("| CFG_KD | " + " | ".join(c for c, _ in casos) + " |")
    print("|---|" + "---|" * len(casos))
    for kd in (int(k) for k in a.kd.split(",")):
        print(f"| {kd} | " + " | ".join(f"{entropias_exactas(2 ** kd * razon * x)[1]:.5f}"
                                         for _, x in casos) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
