#!/usr/bin/env python3
"""Dispersion de Q entre realizaciones de anillo_ihp_repeticiones.py frente a
la que daria el propio estimador (spice_ring.jitter_desde_cruces) con jitter
blanco iid y el mismo numero de cruces.

Para cada tanda guardada en results/ (anillo_ihp_<prefijo>_NN.json, escala 1):
dispersion de Q, la del estimador con blanco (Monte Carlo), su cociente y la
p de chi-cuadrado ((n-1) s^2 / d^2 ~ chi2(n-1)). Prueba conjunta de las
tandas de 5 etapas. SIMULADO.

    ~/eda/venv/bin/python analysis/dispersion_q.py
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spice_ring import jitter_desde_cruces  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SALIDA = RES / "dispersion_q.md"
EXCLUIR = {"mc_ss_m40_v108"}   # incluye el chip 9 excluido (docs/anillo_ihp.md 4.3)
OBJETIVO = "ss_m40_v108_e11"


def disp_blanco(n: int, rng, reps: int = 800) -> float:
    q = [jitter_desde_cruces(np.cumsum(1 + rng.normal(0, 1e-3, n)), descartar=20)["q_por_periodo"]
         for _ in range(reps)]
    return float(np.std(q) / np.mean(q))


def main() -> int:
    rng = np.random.default_rng(2)
    grupos: dict[str, list] = collections.defaultdict(list)
    for f in RES.glob("anillo_ihp_*_[0-9][0-9].json"):
        pre = f.stem.rsplit("_", 1)[0].removeprefix("anillo_ihp_")
        for a in json.loads(f.read_text())["anillo"]:
            if a["escala"] == 1:
                grupos[pre].append(a)
    cache: dict[int, float] = {}
    lin = ["# Dispersión de Q entre realizaciones (analysis/dispersion_q.py)", "",
           "SIMULADO. \"blanco\" = dispersión del mismo estimador con jitter blanco iid y el mismo "
           "número de cruces (800 Monte Carlo); p de chi-cuadrado de la dispersión observada.", "",
           "| Tanda | etapas | n | cruces | dispersión Q | blanco | cociente | p | exponente medio |",
           "|---|---|---|---|---|---|---|---|---|"]
    chi_tot, gl_tot = 0.0, 0
    for k, v in sorted(grupos.items()):
        if k in EXCLUIR or len(v) < 4:
            continue
        q = np.array([a["q_periodo"] for a in v])
        n_c = int(round(np.mean([a["n_cruces"] for a in v]), -1))
        if n_c not in cache:
            cache[n_c] = disp_blanco(n_c, rng)
        s, d = q.std(ddof=1) / q.mean(), cache[n_c]
        chi = (q.size - 1) * s ** 2 / d ** 2
        p = stats.chi2.sf(chi, q.size - 1)
        if v[0]["etapas"] == 5:
            chi_tot += chi
            gl_tot += q.size - 1
        lin.append(f"| {k} | {v[0]['etapas']} | {q.size} | {n_c} | {s:.3f} | {d:.3f} | {s / d:.2f} | "
                   f"{p:.3f} | {np.mean([a['exponente'] for a in v]):.2f} |")
    lin += ["", f"Tandas de 5 etapas juntas: χ² {chi_tot:.1f} con {gl_tot} gl, p {stats.chi2.sf(chi_tot, gl_tot):.3f}; "
            f"factor medio sobre el blanco {np.sqrt(chi_tot / gl_tot):.2f}."]
    if OBJETIVO in grupos:
        q = np.array([a["q_periodo"] for a in grupos[OBJETIVO]])
        f = np.sqrt(chi_tot / gl_tot)
        n_c = int(round(np.mean([a["n_cruces"] for a in grupos[OBJETIVO]]), -1))
        s = q.std(ddof=1) / q.mean()
        chi = (q.size - 1) * s ** 2 / (f * cache[n_c]) ** 2
        t = stats.t.ppf(0.975, q.size - 1) * q.std(ddof=1) / np.sqrt(q.size)
        lin += [f"{OBJETIVO} frente al blanco ya escalado por ese factor: p {stats.chi2.sf(chi, q.size - 1):.3f}. "
                f"Q media {q.mean():.3e} ± {t:.2e} (IC 95 %), mínima {q.min():.3e}."]
    texto = "\n".join(lin) + "\n"
    SALIDA.write_text(texto)
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
