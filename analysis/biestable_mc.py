#!/usr/bin/env python3
"""Criterio del Monte Carlo del biestable sg13g2 (fijado el 16-11-2026 antes
de simular; docs/basys2.md, "H 0,60: provisional hasta el Monte Carlo").

Por esquina: media y desviacion de P(1) ponderada (p1w_ff, montaje uno_buf)
entre chips; H de la esquina = -log2 max(p, 1-p) en mu -/+ 3 sigma (la cola
que se aleja de 0,5); H declarable = minimo sobre esquinas. Se da tambien
Shapiro-Wilk, el intervalo del 95 % de sigma (chi-cuadrado) y la H con el
extremo alto de ese intervalo, y el peor chip como dato. SIMULADO, sin ruido.

    ~/eda/venv/bin/python analysis/biestable_mc.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
from scipy import stats

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "results"
FUENTES = ["biestable_ihp_sf_ff_mm.csv", "biestable_ihp_mc24.csv", "biestable_ihp_mc8_v108.csv",
           "biestable_ihp_mc16_v108.csv"]
SALIDA = RES / "biestable_mc.md"
H_OBJ = 0.60


def h(p: float) -> float:
    return float(-np.log2(max(p, 1 - p))) + 0.0


def cola(mu: float, s: float) -> float:
    return float(np.clip(mu - 3 * s if mu < 0.5 else mu + 3 * s, 0.0, 1.0))


def main() -> int:
    datos: dict[str, list[tuple[str, float]]] = {}
    for f in FUENTES:
        p = RES / f
        if not p.exists():
            print(f"falta {f}")
            continue
        for fila in csv.DictReader(p.open()):
            if fila["montaje"] != "uno_buf" or fila["mismatch"] != "1":
                continue
            datos.setdefault(fila["caso"], []).append((f, float(fila["p1w_ff"])))
    lin = ["# Monte Carlo del biestable sg13g2 (analysis/biestable_mc.py)", "",
           "SIMULADO, sin ruido; P(1) ponderada por fase, montaje uno_buf, 125 °C.",
           "Criterio fijado antes de simular (docs/basys2.md, 16-11-2026).", "",
           "| Esquina | n | μ | σ | σ IC 95 % | Shapiro-Wilk p | μ ∓ 3σ | H | H con σ alta | peor chip | H peor |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    hs = {}
    notas: list[str] = []
    for caso, v in sorted(datos.items()):
        x = np.array([b for _, b in v])
        n = x.size
        mu, s = x.mean(), x.std(ddof=1)
        lo = s * np.sqrt((n - 1) / stats.chi2.ppf(0.975, n - 1))
        hi = s * np.sqrt((n - 1) / stats.chi2.ppf(0.025, n - 1))
        sw = stats.shapiro(x).pvalue if n >= 3 else float("nan")
        q = cola(mu, s)
        peor = x[np.argmax(np.abs(x - 0.5))]
        hs[caso] = h(q)
        tandas = [np.array([b for g, b in v if g == f]) for f in FUENTES if any(g == f for g, _ in v)]
        if len(tandas) == 2 and min(t.size for t in tandas) >= 2:
            notas.append(f"{caso}: tandas {tandas[0].mean():.4f} (n {tandas[0].size}) y {tandas[1].mean():.4f} "
                         f"(n {tandas[1].size}), Welch p = {stats.ttest_ind(*tandas, equal_var=False).pvalue:.2f}")
        orig = ", ".join(f"{f.removeprefix('biestable_ihp_').removesuffix('.csv')} {sum(1 for g, _ in v if g == f)}"
                         for f in FUENTES if any(g == f for g, _ in v))
        lin.append(f"| {caso} ({orig}) | {n} | {mu:.4f} | {s:.4f} | {lo:.4f}-{hi:.4f} | {sw:.2f} | "
                   f"{q:.4f} | {h(q):.3f} | {h(cola(mu, hi)):.3f} | {peor:.4f} | {h(peor):.3f} |")
    if notas:
        lin += ["", "Tandas independientes de la misma esquina (sorteos distintos):", ""] + [f"- {t}" for t in notas]
    if hs:
        peor_caso = min(hs, key=hs.get)
        hd = hs[peor_caso]
        lin += ["", f"**H declarable = {hd:.3f}** (esquina {peor_caso}); objetivo {H_OBJ}: "
                + ("se cierra H 0,60." if hd >= H_OBJ else "por debajo: corregir el circuito, no bajar H.")]
        for a, b in (("sf125_v108_mm", "sf125_mm"),):
            if a in datos and b in datos:
                ma = np.mean([x for _, x in datos[a]])
                mb = np.mean([x for _, x in datos[b]])
                peor = abs(ma - 0.5) > abs(mb - 0.5)
                cola_txt = ("(no peor)." if not peor else
                            "(peor: ampliar a 24 chips)." if len(datos[a]) < 24 else
                            f"(peor, ya con {len(datos[a])} chips).")
                lin.append(f"sf 1,08 V frente a 1,2 V en media: {ma:.4f} frente a {mb:.4f} {cola_txt}")
    txt = "\n".join(lin) + "\n"
    print(txt)
    SALIDA.write_text(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
