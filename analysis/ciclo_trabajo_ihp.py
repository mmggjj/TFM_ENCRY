#!/usr/bin/env python3
"""Ciclo de trabajo del anillo con transistores IHP SG13G2 [SIMULADO].

Sin el CE en el muestreo (G_MUESTREO_LIBRE), con la fase ya aleatoria, la
probabilidad de un 1 es la fraccion del periodo que ro1 pasa por encima del
umbral del biestable. Este script la mide en el anillo de anillo_ihp.py
(mismos transistores y cabecera), sin ruido (es determinista), en cada nudo
y para varios umbrales alrededor de V_DD/2, por esquinas.

    ~/eda/venv/bin/python analysis/ciclo_trabajo_ihp.py [--mismatch-n 8]

Cota de primer orden: H <= -log2(max(D, 1 - D)). No incluye el camino del
anillo al biestable ni su apertura (en el integrado aun no hay trazado).
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anillo_ihp as ai                           # noqa: E402
from spice_ring import cruces_subida, netlist, simular   # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
ETAPAS = 5
DESPL_MV = (-100, -50, 0, 50, 100)

CASOS = [  # (nombre, esquina, temp, vdd)
    ("tt27", "mos_tt", 27.0, 1.2),
    ("ss_m40", "mos_ss", -40.0, 1.2),
    ("ss_m40_v108", "mos_ss", -40.0, 1.08),
    ("ff125", "mos_ff", 125.0, 1.2),
    ("ff125_v132", "mos_ff", 125.0, 1.32),
    ("sf_m40", "mos_sf", -40.0, 1.2),
    ("fs_m40", "mos_fs", -40.0, 1.2),
    ("sf125", "mos_sf", 125.0, 1.2),
    ("fs125", "mos_fs", 125.0, 1.2),
]


def ciclo(t, v, umbral, descartar=10):
    """Fraccion del periodo por encima del umbral, de flancos interpolados."""
    sub = cruces_subida(t, v, umbral)
    baj = cruces_subida(t, -v, -umbral)
    sub = sub[descartar:]
    baj = baj[baj > sub[0]]
    n = min(sub.size - 1, baj.size)
    alto = baj[:n] - sub[:n]
    periodo = np.diff(sub)[:n]
    return float(np.mean(alto / periodo)), float(np.mean(periodo)), n


def un_caso(arg):
    nombre, esquina, temp, vdd, mismatch, rep = arg
    nudos = " ".join(f"v(n{i})" for i in range(1, ETAPAS + 1))
    txt = netlist(n_etapas=ETAPAS, vdd=vdd, lmin="0.13u", wn="0.5u", wp="1.2u",
                  cl="1f", tstop="25n", paso="0.1p", paso_max="0.5p",
                  densidad_ruido=0.0,
                  cabecera=ai.cabecera_ihp(esquina, mismatch) + f".temp {temp}\n",
                  guardar=nudos)
    t0 = time.time()
    nombres, m, log = simular(txt, orden=ai.NGSPICE, spiceinit=ai.SPICEINIT, timeout=3600)
    t = m[:, 0]
    filas = []
    for i in range(1, ETAPAS + 1):
        v = m[:, nombres.index(f"v(n{i})")]
        for d in DESPL_MV:
            D, T, n = ciclo(t, v, vdd / 2.0 + d / 1000.0)
            p = max(D, 1.0 - D)
            filas.append({"caso": nombre, "esquina": esquina, "temp": temp, "vdd": vdd,
                          "mismatch": int(mismatch), "rep": rep, "nudo": i,
                          "despl_mV": d, "ciclo": D, "periodo_ps": T * 1e12,
                          "n_periodos": n, "h_cota": -np.log2(p),
                          "segundos": time.time() - t0})
    return filas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mismatch-n", type=int, default=8,
                    help="chips con desapareamiento en tt 27 C y en ss -40 C 1,08 V")
    ap.add_argument("--procesos", type=int, default=4)
    a = ap.parse_args()
    trabajos = [(n, e, t, v, False, 0) for n, e, t, v in CASOS]
    for r in range(a.mismatch_n):
        trabajos.append(("tt27_mm", "mos_tt", 27.0, 1.2, True, r))
        trabajos.append(("ss_m40_v108_mm", "mos_ss", -40.0, 1.08, True, r))
    filas = []
    with ProcessPoolExecutor(a.procesos) as ex:
        for fs in ex.map(un_caso, trabajos):
            filas += fs
            f0 = [f for f in fs if f["despl_mV"] == 0]
            print(f"{fs[0]['caso']} rep {fs[0]['rep']}: periodo {f0[0]['periodo_ps']:.1f} ps, "
                  "ciclo a VDD/2 por nudo " +
                  " ".join(f"{f['ciclo']:.4f}" for f in f0), flush=True)
    salida = RES / "ciclo_trabajo_ihp.csv"
    with open(salida, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f"\nCSV: {salida}")
    print("\nResumen por caso (todos los nudos; umbral VDD/2 y VDD/2 +-100 mV):")
    print("| caso | n | periodo ps | ciclo a VDD/2 (min-max) | ciclo con +-100 mV (min-max) | H cota peor a VDD/2 | H cota peor con +-100 mV |")
    print("|---|---|---|---|---|---|---|")
    for caso in dict.fromkeys(f["caso"] for f in filas):
        c = [f for f in filas if f["caso"] == caso]
        c0 = [f for f in c if f["despl_mV"] == 0]
        print(f"| {caso} | {len({f['rep'] for f in c})} | {np.mean([f['periodo_ps'] for f in c0]):.1f} | "
              f"{min(f['ciclo'] for f in c0):.4f}-{max(f['ciclo'] for f in c0):.4f} | "
              f"{min(f['ciclo'] for f in c):.4f}-{max(f['ciclo'] for f in c):.4f} | "
              f"{min(f['h_cota'] for f in c0):.4f} | {min(f['h_cota'] for f in c):.4f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
