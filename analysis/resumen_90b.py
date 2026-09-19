#!/usr/bin/env python3
"""Resumen legible de results/entropia_90b.csv: tabla por estimador (modo
binario, via no-IID) para cada captura, y media +- desviacion por condicion
sobre sus repeticiones, con el cociente entre la separacion de condiciones
y la dispersion dentro de condicion. Escribe results/entropia_90b_resumen.md.

    python analysis/resumen_90b.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from statistics import mean, pstdev

RES = Path(__file__).resolve().parent.parent / "results"
CSV = RES / "entropia_90b.csv"
SALIDA = RES / "entropia_90b_resumen.md"

# (etiqueta corta, indice de testCase, campo) en el JSON de ea_non_iid binario
ESTIMADORES = [
    ("MCV", 0, "hOriginal"), ("Collision", 1, "hOriginal"), ("Markov", 2, "hOriginal"),
    ("Compression", 3, "hOriginal"), ("t-Tuple", 4, "tTupleRes"), ("LRS", 5, "lrsRes"),
    ("MultiMCW", 6, "hOriginal"), ("Lag", 7, "hOriginal"), ("MultiMMC", 8, "hOriginal"),
    ("LZ78Y", 9, "hOriginal"), ("min", 10, "hAssessed"),
]


def main() -> int:
    filas = list(csv.DictReader(CSV.open(encoding="utf-8")))
    noniid = {f["nombre"]: f for f in filas if f["test"] == "noniid" and f["modo"] == "b1"}
    iid_b1 = {f["nombre"]: f for f in filas if f["test"] == "iid" and f["modo"] == "b1"}
    iid_b8 = {f["nombre"]: f for f in filas if f["test"] == "iid" and f["modo"] == "b8"}
    nombres = sorted(noniid, key=lambda n: (not n.startswith("cond"), n))

    def val(f, i, campo):
        return float(f[f"testCases.{i}.{campo}"])

    def pasa(f):
        return (f["testCases.0.passedIidPermutationTests"] == "True"
                and f["testCases.0.passedChiSquareTests"] == "True"
                and f["testCases.0.passedLongestRepeatedSubstringTest"] == "True")

    lineas = ["# Resumen SP 800-90B (modo binario)", "",
              "Generado por analysis/resumen_90b.py a partir de results/entropia_90b.csv.", "",
              "## Por captura", "",
              "| Captura | N (bits) | IID b1 | IID b8 | " + " | ".join(e[0] for e in ESTIMADORES) + " | manda |",
              "|---|---|---|---|" + "---|" * len(ESTIMADORES) + "---|"]
    valores: dict[str, dict[str, float]] = {}
    for n in nombres:
        f = noniid[n]
        v = {e[0]: val(f, e[1], e[2]) for e in ESTIMADORES}
        valores[n] = v
        manda = min((e[0] for e in ESTIMADORES if e[0] != "min"), key=lambda k: v[k])
        nbits = int(float(f["testCases.0.mcvEstimateMode"]) / float(f["testCases.0.mcvEstimatePHat"]) + 0.5)
        lineas.append(f"| {n} | {nbits:,} | {'pasa' if pasa(iid_b1[n]) else 'FALLA'} | "
                      f"{'pasa' if pasa(iid_b8[n]) else 'FALLA'} | "
                      + " | ".join(f"{v[e[0]]:.4f}" for e in ESTIMADORES) + f" | {manda} |")

    # por condicion: media +- desviacion sobre repeticiones
    conds: dict[str, list[str]] = {}
    for n in nombres:
        m = re.match(r"cond([A-D])_rep(\d+)", n)
        if m:
            conds.setdefault(m.group(1), []).append(n)
    # ANOVA de un factor por estimador (condicion como factor, repeticiones
    # como replicas). Con 11 estimadores el umbral de Bonferroni es 0,05/11.
    from scipy.stats import f_oneway
    k_cond = len(conds)
    n_rep = sum(len(v) for v in conds.values())
    lineas += ["", "## Por condicion (media ± desviación poblacional sobre las repeticiones)", "",
               f"ANOVA de un factor, F({k_cond - 1}, {n_rep - k_cond}); umbral de Bonferroni "
               f"para {len(ESTIMADORES)} estimadores: p < {0.05 / len(ESTIMADORES):.4f}.", "",
               "| Estimador | " + " | ".join(f"{c} (n={len(conds[c])})" for c in sorted(conds))
               + " | F | p |",
               "|---|" + "---|" * len(conds) + "---|---|"]
    p_min = 1.0
    for e in ESTIMADORES:
        k = e[0]
        grupos = [[valores[n][k] for n in conds[c]] for c in sorted(conds)]
        medias = {c: mean(valores[n][k] for n in conds[c]) for c in conds}
        sds = {c: pstdev(valores[n][k] for n in conds[c]) for c in conds}
        F, p = f_oneway(*grupos)
        p_min = min(p_min, p)
        lineas.append(f"| {k} | " + " | ".join(f"{medias[c]:.4f} ± {sds[c]:.4f}" for c in sorted(conds))
                      + f" | {F:.2f} | {p:.3f} |")
    lineas += ["", f"p mínima entre los {len(ESTIMADORES)} estimadores: {p_min:.3f}. "
               + ("Ningún estimador separa las condiciones al nivel corregido."
                  if p_min >= 0.05 / len(ESTIMADORES) else
                  "Al menos un estimador separa las condiciones al nivel corregido: revisar.")]
    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
