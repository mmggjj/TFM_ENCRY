#!/usr/bin/env python3
"""Plano de la implementacion en el XC7A35T: donde coloco Vivado cada bloque.

Lee results/basys3_plano/celdas.csv y sitios.csv (synth/basys3/plano.tcl
sobre el checkpoint rutado de la variante silenciosa con colocacion fija) y
dibuja cada celda en su sitio, coloreada por bloque del motor; los anillos,
con su pblock.

    python analysis/plano_basys3.py   # -> results/basys3_plano/plano_basys3.{png,pdf}
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = Path(__file__).resolve().parent.parent / "results" / "basys3_plano"

BLOQUES = [  # (prefijo de jerarquia, etiqueta, color)
    ("u_motor/g_cripto.u_drbg", "CTR_DRBG", "#4C72B0"),
    ("u_motor/g_cripto.g_nucleo_unico", "AES-128 (32 bits)", "#DD8452"),
    ("u_motor/g_cripto.u_cmac", "AES-CMAC", "#55A868"),
    ("u_motor/u_salud", "tests de salud", "#C44E52"),
    ("u_motor/u_i2c", "esclavo I2C", "#8172B3"),
    ("u_motor/g_captura", "buffer de captura", "#937860"),
    ("u_motor/g_flujo", "FIFO de flujo", "#DA8BC3"),
    ("u_motor/u_ero", "ERO (divisor, muestreo)", "#000000"),
    ("u_motor/u_cdc", "ERO (divisor, muestreo)", "#000000"),
    ("u_motor/", "registros y secuenciador", "#8C8C8C"),
]


def bloque(celda: str):
    for pref, etq, col in BLOQUES:
        if celda.startswith(pref):
            return etq, col
    return "E/S y envoltorio", "#CCB974"


def main():
    sitios = list(csv.DictReader(open(D / "sitios.csv")))
    celdas = list(csv.DictReader(open(D / "celdas.csv")))
    fig, ax = plt.subplots(figsize=(8, 9))
    ax.scatter([int(s["x"]) for s in sitios], [int(s["y"]) for s in sitios],
               s=2, c="#E6E6E6", marker="s", linewidths=0, label="slices libres")
    grupos = defaultdict(list)
    anillos = defaultdict(list)
    for c in celdas:
        x, y = int(c["x"]), int(c["y"])
        if c["celda"].startswith("u_motor/u_ro1/"):
            anillos["ro1 (13 etapas)"].append((x, y))
        elif c["celda"].startswith("u_motor/u_ro2/"):
            anillos["ro2 (11 etapas)"].append((x, y))
        else:
            grupos[bloque(c["celda"])].append((x, y))
    for (etq, col), pts in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=3, c=col, linewidths=0,
                   label=f"{etq} ({len(pts)})")
    for (etq, col) in (("ro1 (13 etapas)", "#FF0000"), ("ro2 (11 etapas)", "#00A0FF")):
        pts = anillos[etq]
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=40, c=col, marker="*",
                   edgecolors="k", linewidths=0.4, label=f"{etq}")
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ax.annotate(etq.split()[0], (max(xs), max(ys)), xytext=(12, 4),
                    textcoords="offset points", fontsize=9, color=col, weight="bold")
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("basys3_top en el XC7A35T (Vivado 2025.2, rutado)\n"
                 "variante silenciosa, anillos con LOC/BEL fijos (ro_bel.xdc)", fontsize=10)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, markerscale=3,
              frameon=False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(D / f"plano_basys3.{ext}", dpi=200, bbox_inches="tight")
    n = {etq: len(p) for (etq, _), p in grupos.items()}
    print(f"{len(celdas)} celdas colocadas; por bloque: {n}; anillos: "
          f"{ {k: len(v) for k, v in anillos.items()} }")
    print(f"figura: {D / 'plano_basys3.png'}")


if __name__ == "__main__":
    main()
