#!/usr/bin/env python3
"""Enganche entre ro1 (11 etapas) y ro2 (13) cuando comparten alimentacion
a traves de una impedancia. SIMULADO, sin ruido, PDK de IHP.

Los dos anillos van en la misma netlist y toman V_DD de un mismo nudo, que
cuelga de la fuente ideal por una resistencia R (sin condensador de
desacoplo: caso pesimista). Cada anillo modula la corriente y por tanto la
tension que ve el otro. Si se enganchan, el cociente de periodos se queda en
un racional p/q y la fase de ro1 muestreada en los flancos de ro2 solo toma
q valores; si no, la recorre entera. Se mide:
  - el cociente de periodos medios, frente al de R = 0;
  - el mayor hueco de la fase de ro1 en los flancos de ro2 (mod 1): con N
    muestras repartidas ~1/N; enganchado a p/q, ~1/q;
  - el cociente en tres tramos (deriva hacia un racional).

    ~/eda/venv/bin/python analysis/enganche_anillos.py [--procesos 5]
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anillo_ihp import NGSPICE, SPICEINIT, cabecera_ihp  # noqa: E402
from spice_ring import cruces_subida, simular  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SALIDA = RES / "enganche_anillos.md"
CRUDO = RES / "enganche_anillos.json"
ESQUINAS = {"tt27": ("mos_tt", 27.0, 1.20, 400), "ss_m40_v108": ("mos_ss", -40.0, 1.08, 600)}
RESISTENCIAS = [0.0, 10.0, 100.0, 1000.0]
DESCARTE_NS = 30

NETLIST = """* ro1 (11) y ro2 (13) con alimentacion comun a traves de R
{cabecera}
.temp {temp}
.param lmin=0.13u wn=0.5u wp=1.2u cl=1f
vsup vs 0 dc {vdd}
{rama}
ven en 0 dc {vdd}
.subckt inv a y vdd vss
xmp y a vdd vdd pmos_tec w={{wp}} l={{lmin}}
xmn y a vss vss nmos_tec w={{wn}} l={{lmin}}
cc y vss {{cl}}
.ends
.subckt nand2 a b y vdd vss
xmp1 y a vdd vdd pmos_tec w={{wp}} l={{lmin}}
xmp2 y b vdd vdd pmos_tec w={{wp}} l={{lmin}}
xmn1 y a nx  vss nmos_tec w={{2*wn}} l={{lmin}}
xmn2 nx b vss vss nmos_tec w={{2*wn}} l={{lmin}}
cc y vss {{cl}}
.ends
xna en a11 a1 vdd 0 nand2
{cadena_a}
xnb en b13 b1 vdd 0 nand2
{cadena_b}
.options reltol=1e-5 abstol=1e-13 vntol=1e-9 chgtol=1e-15 trtol=1
.options method=gear maxord=2
.tran 0.2p {tstop}n 0 1p
.save v(a11) v(b13) v(vdd)
.end
"""


def correr(esquina: str, r: float) -> dict:
    esq, temp, vdd, tstop = ESQUINAS[esquina]
    rama = "rsup vs vdd 1e-6" if r == 0 else f"rsup vs vdd {r:g}"
    txt = NETLIST.format(
        cabecera=cabecera_ihp(esq, False), temp=temp, vdd=vdd, rama=rama, tstop=tstop,
        cadena_a="\n".join(f"xia{i} a{i} a{i + 1} vdd 0 inv" for i in range(1, 11)),
        cadena_b="\n".join(f"xib{i} b{i} b{i + 1} vdd 0 inv" for i in range(1, 13)))
    nombres, m, _ = simular(txt, orden=NGSPICE, spiceinit=SPICEINIT, timeout=4 * 3600)
    t = m[:, 0]
    va, vb, vd = (m[:, nombres.index(n)] for n in ("v(a11)", "v(b13)", "v(vdd)"))
    sel = t > DESCARTE_NS * 1e-9
    vmed = float(np.mean(vd[sel]))
    ta = cruces_subida(t, va, vmed / 2, histeresis=0.1 * vmed)
    tb = cruces_subida(t, vb, vmed / 2, histeresis=0.1 * vmed)
    ta, tb = ta[ta > DESCARTE_NS * 1e-9], tb[tb > DESCARTE_NS * 1e-9]
    pa = float(np.polyfit(np.arange(ta.size), ta, 1)[0])
    pb = float(np.polyfit(np.arange(tb.size), tb, 1)[0])
    # fase de ro1 (en ciclos) en cada flanco de ro2, interpolada
    k = np.arange(ta.size)
    dentro = (tb > ta[0]) & (tb < ta[-1])
    fase = np.mod(np.interp(tb[dentro], ta, k), 1.0)
    f = np.sort(fase)
    hueco = float(max(np.max(np.diff(f)), 1.0 - f[-1] + f[0]))
    tramos = []
    for x in np.array_split(np.arange(tb.size), 3):
        xa = ta[(ta >= tb[x[0]]) & (ta <= tb[x[-1]])]
        tramos.append(float(np.polyfit(np.arange(x.size), tb[x], 1)[0]
                            / np.polyfit(np.arange(xa.size), xa, 1)[0]))
    return {"esquina": esquina, "R": r, "vdd_medio": vmed,
            "rizado_mVpp": float(np.ptp(vd[sel]) * 1e3), "Ta_ps": pa * 1e12,
            "Tb_ps": pb * 1e12, "cociente": pb / pa, "tramos": tramos,
            "n_fases": int(fase.size), "hueco_fase": hueco,
            "racional_cercano": str(Fraction(pb / pa).limit_denominator(12))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--procesos", type=int, default=5)
    a = ap.parse_args()
    trabajos = [(e, r) for e in ESQUINAS for r in RESISTENCIAS]
    with ThreadPoolExecutor(max_workers=a.procesos) as ex:
        filas = list(ex.map(lambda j: correr(*j), trabajos))
    CRUDO.write_text(json.dumps(filas, indent=1))
    lin = ["# Enganche entre anillos con alimentación común (analysis/enganche_anillos.py)", "",
           "SIMULADO, sin ruido, PDK IHP SG13G2, sin desacoplo. Los dos anillos toman V_DD del "
           "mismo nudo, que cuelga de la fuente ideal por R. Enganchados, el cociente se queda en "
           "un racional p/q y el mayor hueco de la fase de ro1 en los flancos de ro2 sube a ~1/q; "
           "sin enganche, ~1/(número de flancos).", "",
           "| Esquina | R (Ω) | V_DD media (V) | rizado (mV pp) | T(ro1) ps | T(ro2) ps | "
           "T(ro2)/T(ro1) | en tres tramos | Δ frente a R = 0 | flancos | mayor hueco de fase | "
           "racional más cercano (q ≤ 12) |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in ESQUINAS:
        ref = next(f for f in filas if f["esquina"] == e and f["R"] == 0)["cociente"]
        for f in (x for x in filas if x["esquina"] == e):
            lin.append(f"| {e} | {f['R']:g} | {f['vdd_medio']:.4f} | {f['rizado_mVpp']:.2f} | "
                       f"{f['Ta_ps']:.2f} | {f['Tb_ps']:.2f} | {f['cociente']:.5f} | "
                       + ", ".join(f"{x:.5f}" for x in f["tramos"])
                       + f" | {100 * (f['cociente'] / ref - 1):+.3f} % | {f['n_fases']} | "
                       f"{f['hueco_fase']:.4f} | {f['racional_cercano']} |")
    texto = "\n".join(lin) + "\n"
    SALIDA.write_text(texto)
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
