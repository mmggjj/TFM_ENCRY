#!/usr/bin/env python3
"""Sensibilidad del periodo de ro1 (11 etapas) y ro2 (13) a la alimentacion,
y cuanto rizado comun llega a la fase relativa de los dos anillos.

Cada simulacion (sin ruido, PDK de IHP) es un solo transitorio con V_DD en
tres mesetas: nominal, nominal + dV y nominal - dV. Asi la derivada sale del
mismo chip aunque haya desapareamiento (ngspice no deja fijar el sorteo
entre simulaciones). S = (1/T) dT/dV, por diferencia centrada.

El divisor cuenta periodos de ro2 y el bit es la fase de ro1: un rizado
comun dV mueve el cociente T(ro2)/T(ro1) en (S2 - S1) dV, no en S1 dV. El
rechazo del modo comun es |S2 - S1| / |S1|. Con desapareamiento, ro1 y ro2
son instancias distintas: su S es independiente, asi que se combinan
realizaciones de cada anillo por separado. SIMULADO.

    ~/eda/venv/bin/python analysis/sensibilidad_vdd.py [--n-mm 8] [--procesos 5]
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anillo_ihp import NGSPICE, SPICEINIT, cabecera_ihp  # noqa: E402
from spice_ring import cruces_subida, netlist, simular  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SALIDA = RES / "sensibilidad_vdd.md"
CRUDO = RES / "sensibilidad_vdd.json"
ESQUINAS = {  # nombre: (esquina, temp, vdd, meseta ns)
    "tt27": ("mos_tt", 27.0, 1.20, 40),
    "ss_m40_v108": ("mos_ss", -40.0, 1.08, 60),
    "ffm40_v132": ("mos_ff", -40.0, 1.32, 30),
    "ff125_v132": ("mos_ff", 125.0, 1.32, 30),
}
DV = 0.010
ARRANQUE_NS = 20
RAMPA_NS = 1.0
DESCARTE_NS = 8          # tras cada escalon, para que se asiente


def correr(nombre: str, etapas: int, mm: bool) -> dict:
    esq, temp, vdd, mes = ESQUINAS[nombre]
    t1 = ARRANQUE_NS + mes
    t2 = t1 + mes
    t3 = t2 + mes
    pwl = (f"pwl(0 {vdd} {t1}n {vdd} {t1 + RAMPA_NS}n {vdd + DV} {t2}n {vdd + DV} "
           f"{t2 + RAMPA_NS}n {vdd - DV} {t3}n {vdd - DV})")
    txt = netlist(n_etapas=etapas, vdd=vdd, lmin="0.13u", wn="0.5u", wp="1.2u",
                  cl="1f", tstop=f"{t3}n", paso="0.2p", paso_max="1p",
                  cabecera=cabecera_ihp(esq, mm) + f".temp {temp}\n",
                  guardar=f"v(n{etapas})")
    viejo = "vdd vdd 0 dc {vdd_v}"
    assert viejo in txt
    txt = txt.replace(viejo, f"vdd vdd 0 {pwl}")
    nombres, m, _ = simular(txt, orden=NGSPICE, spiceinit=SPICEINIT, timeout=3 * 3600)
    t, v = m[:, 0], m[:, nombres.index(f"v(n{etapas})")]
    tc = cruces_subida(t, v, vdd / 2.0, histeresis=0.1 * vdd)

    def periodo(a_ns: float, b_ns: float) -> tuple[float, int]:
        x = tc[(tc > (a_ns + DESCARTE_NS) * 1e-9) & (tc < b_ns * 1e-9)]
        return float(np.polyfit(np.arange(x.size), x, 1)[0]), int(x.size)

    t0, n0 = periodo(ARRANQUE_NS - DESCARTE_NS + 2, t1)
    tm, nm_ = periodo(t1 + RAMPA_NS, t2)
    tb, nb = periodo(t2 + RAMPA_NS, t3)
    s = (tm - tb) / (2 * DV) / t0
    return {"esquina": nombre, "etapas": etapas, "mismatch": mm, "T0_ps": t0 * 1e12,
            "Tmas_ps": tm * 1e12, "Tmenos_ps": tb * 1e12, "cruces": [n0, nm_, nb],
            "S_porV": s}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-mm", type=int, default=8, help="chips con desapareamiento por anillo")
    ap.add_argument("--mm-esquinas", default="tt27,ss_m40_v108")
    ap.add_argument("--procesos", type=int, default=5)
    a = ap.parse_args()
    trabajos = [(e, n, False) for e in ESQUINAS for n in (11, 13)]
    trabajos += [(e, n, True) for e in a.mm_esquinas.split(",") for n in (11, 13)
                 for _ in range(a.n_mm)]
    with ThreadPoolExecutor(max_workers=a.procesos) as ex:
        filas = list(ex.map(lambda j: correr(*j), trabajos))
    CRUDO.write_text(json.dumps(filas, indent=1))

    lin = ["# Sensibilidad de los anillos a V_DD (analysis/sensibilidad_vdd.py)", "",
           f"SIMULADO, sin ruido, PDK IHP SG13G2; escalón de ±{DV * 1e3:.0f} mV dentro del "
           "mismo transitorio. S = (1/T) dT/dV (negativa: al subir V_DD el anillo va más "
           "deprisa). Rechazo del modo común = |S2 − S1| / |S1|.", "",
           "## Sin desapareamiento", "",
           "| Esquina | T(ro1) ps | T(ro2) ps | S1 (1/V) | S2 (1/V) | S2 − S1 (1/V) | rechazo |",
           "|---|---|---|---|---|---|---|"]
    for e in ESQUINAS:
        r1 = next(f for f in filas if f["esquina"] == e and f["etapas"] == 11 and not f["mismatch"])
        r2 = next(f for f in filas if f["esquina"] == e and f["etapas"] == 13 and not f["mismatch"])
        d = r2["S_porV"] - r1["S_porV"]
        lin.append(f"| {e} | {r1['T0_ps']:.1f} | {r2['T0_ps']:.1f} | {r1['S_porV']:.4f} | "
                   f"{r2['S_porV']:.4f} | {d:+.5f} | {abs(d / r1['S_porV']):.4f} |")
    lin += ["", "## Con desapareamiento", "",
            "| Esquina | n por anillo | S1 μ ± σ (1/V) | S2 μ ± σ (1/V) | S2 − S1: μ ± σ (1/V) | "
            "rechazo típico (μ + 2σ de |S2 − S1|, / |S1|) |",
            "|---|---|---|---|---|---|"]
    for e in a.mm_esquinas.split(","):
        s1 = np.array([f["S_porV"] for f in filas if f["esquina"] == e and f["etapas"] == 11 and f["mismatch"]])
        s2 = np.array([f["S_porV"] for f in filas if f["esquina"] == e and f["etapas"] == 13 and f["mismatch"]])
        dmu = s2.mean() - s1.mean()
        dsd = float(np.sqrt(s1.var(ddof=1) + s2.var(ddof=1)))
        lin.append(f"| {e} | {s1.size}/{s2.size} | {s1.mean():.4f} ± {s1.std(ddof=1):.4f} | "
                   f"{s2.mean():.4f} ± {s2.std(ddof=1):.4f} | {dmu:+.5f} ± {dsd:.5f} | "
                   f"{(abs(dmu) + 2 * dsd) / abs(s1.mean()):.4f} |")
    texto = "\n".join(lin) + "\n"
    SALIDA.write_text(texto)
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
