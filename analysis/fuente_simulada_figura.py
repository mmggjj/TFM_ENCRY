#!/usr/bin/env python3
"""Figura y tabla de la fuente simulada bajo SP 800-90B.

Lee results/fuente_simulada_90b.csv (fuente_simulada_90b.py) y dibuja, por
divisor, la min-entropia exacta del modelo frente a la estimacion no-IID
del NIST, con la banda de bits uniformes a la misma longitud y la del
ESP32 (results/entropia_90b.csv, condiciones A-D, no-IID en bits).

    ~/eda/venv/bin/python analysis/fuente_simulada_figura.py
"""
from __future__ import annotations

import csv
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[1]
CSV = RAIZ / "results" / "fuente_simulada_90b.csv"
CSV_ESP = RAIZ / "results" / "entropia_90b.csv"
FIG = RAIZ / "memoria" / "figures" / "fuente_simulada_90b.pdf"
RESUMEN = RAIZ / "results" / "fuente_simulada_90b_resumen.md"

CASOS = {   # etiqueta, color, marca
    "tt27": ("tt, 27 °C, 1.2 V", "#2a78d6", "o"),
    "ss40v108": ("ss, −40 °C, 1.08 V", "#eb6834", "s"),
    "ss40v108_peor": ("ss, −40 °C, 1.08 V, worst chip", "#1baf7a", "^"),
}
TINTA2 = "#52514e"

plt.rcParams.update({
    "font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.edgecolor": TINTA2, "axes.linewidth": 0.6,
    "grid.color": "#d8d7d2", "grid.linewidth": 0.4,
    "savefig.bbox": "tight", "pdf.fonttype": 42,
})


def h(f: dict) -> float:
    v = float(f["testCases.10.hAssessed"])
    return v if f["modo"] == "b1" else v / 8


def iid_pasa(f: dict) -> bool:
    return all(f[f"testCases.0.{c}"] == "True" for c in
               ("passedChiSquareTests", "passedIidPermutationTests",
                "passedLongestRepeatedSubstringTest"))


def esp32() -> list[float]:
    out = []
    with CSV_ESP.open(encoding="utf-8", newline="") as fh:
        for f in csv.DictReader(fh):
            # las 36 de A-D en tres chips; fuera la segunda tanda (0928t2_) y rf_off
            if (f["test"] == "noniid" and f["modo"] == "b1" and f["exit"] == "0"
                    and re.fullmatch(r"(fb4c_|0928_)?cond[ABCD]_rep[123]", f["nombre"])):
                out.append(float(f["testCases.10.hAssessed"]))
    return out


def main() -> int:
    filas = list(csv.DictReader(CSV.open(encoding="utf-8", newline="")))
    nist = defaultdict(list)
    modelo = {}
    iid = defaultdict(list)
    for f in filas:
        k = (f["caso"], int(f["kd_exp"]))
        if f["test"] == "noniid" and f["modo"] == "b1":
            nist[k].append(h(f))
            modelo[k] = max(0.0, float(f["hmin_modelo"]))
        if f["test"] == "iid" and f["modo"] == "b8":
            iid[k].append(iid_pasa(f))
    ideal = nist[("ideal", 0)]
    esp = esp32()

    fig, ax = plt.subplots(figsize=(4.8, 3.0))
    ax.axhspan(min(ideal), max(ideal), color="#b9b8b3", alpha=0.45, lw=0,
               label=f"uniform bits, same $N$ ({len(ideal)} seeds)")
    if esp:
        ax.axhspan(min(esp), max(esp), facecolor="none", edgecolor=TINTA2,
                   hatch="////", lw=0.0, alpha=0.6,
                   label=f"ESP32, measured ({len(esp)} captures)")
    for caso, (etq, col, mk) in CASOS.items():
        kds = sorted(k for c, k in modelo if c == caso)
        ax.plot(kds, [modelo[(caso, k)] for k in kds], color=col, lw=1.4)
        m = [st.mean(nist[(caso, k)]) for k in kds]
        s = [st.stdev(nist[(caso, k)]) for k in kds]
        ax.errorbar(kds, m, yerr=s, fmt=mk, ms=4.5, color=col, mfc="white",
                    mew=1.1, elinewidth=0.8, capsize=1.5, label=etq)
    ax.plot([], [], color=TINTA2, lw=1.4, label="model $H_\\infty$ (lines)")
    ax.plot([], [], "o", color=TINTA2, mfc="white", ms=4.5,
            label="SP 800-90B non-IID (markers)")
    ax.set_xlabel("divider $\\log_2 K_D$")
    ax.set_ylabel("min-entropy (bit/bit)")
    ax.set_ylim(-0.02, 1.04)
    kds = sorted({k for c, k in modelo if c in CASOS})
    ax.set_xticks(kds)
    ax.set_xlim(kds[0] - 0.5, kds[-1] + 0.5)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False)
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG)

    lin = ["# Fuente simulada bajo SP 800-90B (generado por fuente_simulada_figura.py)", "",
           f"Ideal (bits uniformes, N = 10^6): {st.mean(ideal):.4f} ± {st.stdev(ideal):.4f}"
           f" (min {min(ideal):.4f}, max {max(ideal):.4f}, {len(ideal)} semillas)",
           f"ESP32 A-D no-IID b1: {len(esp)} capturas, media {st.mean(esp):.4f},"
           f" {min(esp):.4f}-{max(esp):.4f}" if esp else "ESP32: sin filas", "",
           "| caso | log2 K_D | H_inf modelo | NIST no-IID b1 (media ± sd, 3) | IID b8: pasan |",
           "|---|---|---|---|---|"]
    for caso in CASOS:
        for k in sorted(k for c, k in modelo if c == caso):
            v = nist[(caso, k)]
            p = iid.get((caso, k))
            lin.append(f"| {caso} | {k} | {modelo[(caso, k)]:.4f} | {st.mean(v):.4f} ± {st.stdev(v):.4f}"
                       f" | {f'{sum(p)}/{len(p)}' if p else '-'} |")
    p = iid.get(("ideal", 0))
    lin.append(f"| ideal | - | 1 | {st.mean(ideal):.4f} ± {st.stdev(ideal):.4f} | {sum(p)}/{len(p)} |")
    RESUMEN.write_text("\n".join(lin) + "\n", encoding="utf-8")
    print("\n".join(lin))
    print(f"\n{FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
