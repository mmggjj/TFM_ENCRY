#!/usr/bin/env python3
"""Probabilidad de un 1 vista por el biestable real de sg13g2 [SIMULADO].

ciclo_trabajo_ihp.py mide el ciclo de trabajo del anillo con un umbral
ideal. Aqui se cuelga un sg13g2_dfrbpq_1 de la biblioteca de IHP de cada
nudo del anillo (carga simetrica) y se le da un reloj ideal de periodo sin
relacion con el del anillo, de modo que las fases de muestreo recorren el
periodo como cuando la fase del ERO ya es aleatoria. Sin ruido: todo es
determinista. Con las muestras ordenadas por fase se localizan los dos
bordes donde el biestable pasa a capturar 1 y a capturar 0, y su
diferencia es la P(1) efectiva: umbral, apertura y carga reales del
biestable. Se compara con lo que daria un comparador ideal a VDD/2 en los
mismos instantes.

    ~/eda/venv/bin/python analysis/biestable_ihp.py [--n 600] [--mismatch-n 6]

Necesita ihp-sg13g2/libs.ref/sg13g2_stdcell/spice en el PDK (checkout
parcial: git sparse-checkout add ...). Sin el cable ni un buffer entre el
anillo y el biestable.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anillo_ihp as ai                           # noqa: E402
from spice_ring import cruces_subida, netlist, simular   # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
ETAPAS = 5                 # por defecto; --etapas para anillos mas lentos
CELDA = "sg13g2_dfrbpq_1"
BUFFER = "sg13g2_buf_1"
# El biestable va en la salida del anillo, n<etapas> (la que lleva el RTL).
# Montajes: "cinco" = un biestable en cada nudo, todos con el mismo reloj
# (exagera el tiron del reloj sobre el anillo, 15-11-2026); "uno" = solo en
# n5; "uno_buf" = n5 -> sg13g2_buf_1 -> biestable, como en el circuito.
MONTAJES = ("cinco", "uno", "uno_buf")
T0 = 15e-9                 # el anillo ya oscila de forma estable
# El periodo de reloj se elige por caso: 2 + 0,618 periodos del anillo ya
# cargado con los biestables (simulacion previa corta). Con la razon aurea
# las fases de muestreo quedan casi uniformes; con 1,0137 ns fijos, en tt
# la razon era ~2 + 12/41 y dejaba huecos del 2,7 % (15-11-2026).
AUREA = 0.6180339887

CASOS = [  # (nombre, esquina, temp, vdd)
    ("tt27", "mos_tt", 27.0, 1.2),
    ("ss_m40_v108", "mos_ss", -40.0, 1.08),
    ("ff125_v132", "mos_ff", 125.0, 1.32),
    ("sf125", "mos_sf", 125.0, 1.2),
    ("fs125", "mos_fs", 125.0, 1.2),
]


def celda_spice(mismatch: bool, celda: str = CELDA) -> str:
    ruta = Path(ai.PDK.replace("$HOME", str(Path.home()))) / \
        "libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
    txt = ruta.read_text()
    m = re.search(rf"^\.subckt {celda} .*?^\.ends", txt, re.S | re.M)
    if not m:
        raise SystemExit(f"no encuentro {celda} en {ruta}")
    sub = m.group(0)
    if mismatch:
        sub = re.sub(r"(sg13_lv_[np]mos .*)$", r"\1 mm_ok=1", sub, flags=re.M)
    return sub


def bordes(fase, bit):
    """Fases (en [0,1)) donde el bit pasa de 0 a 1 y de 1 a 0, con las
    muestras ordenadas por fase; punto medio entre vecinas."""
    o = np.argsort(fase)
    f, b = fase[o], bit[o]
    f2 = np.concatenate([f, f[:1] + 1.0])
    b2 = np.concatenate([b, b[:1]])
    sube = np.flatnonzero((b2[:-1] == 0) & (b2[1:] == 1))
    baja = np.flatnonzero((b2[:-1] == 1) & (b2[1:] == 0))
    if sube.size != 1 or baja.size != 1:
        return None, None, int(sube.size + baja.size)
    fs = 0.5 * (f2[sube[0]] + f2[sube[0] + 1]) % 1.0
    fb = 0.5 * (f2[baja[0]] + f2[baja[0] + 1]) % 1.0
    return fs, fb, 2


def nudos_ff(montaje, etapas=ETAPAS):
    return list(range(1, etapas + 1)) if montaje == "cinco" else [etapas]


def p1_ponderada(fase, bit):
    """Fraccion de unos pesando cada muestra por el tramo de fase que cubre
    (mitad del hueco a cada vecina): no la sesga un reparto irregular."""
    o = np.argsort(fase)
    f, b = fase[o], bit[o]
    sig = np.concatenate([f[1:], f[:1] + 1.0]) - f
    ant = f - np.concatenate([f[-1:] - 1.0, f[:-1]])
    return float(np.sum(0.5 * (sig + ant) * b))


def deck(esquina, temp, vdd, mismatch, tstop, t_clk, guardar, montaje="cinco",
         etapas=ETAPAS):
    txt = netlist(n_etapas=etapas, vdd=vdd, lmin="0.13u", wn="0.5u", wp="1.2u",
                  cl="1f", tstop=f"{tstop:.4e}", paso="0.2p", paso_max="1p",
                  densidad_ruido=0.0,
                  cabecera=ai.cabecera_ihp(esquina, mismatch) + f".temp {temp}\n",
                  guardar=guardar)
    extra = celda_spice(mismatch) + "\n"
    if montaje == "uno_buf":
        extra += celda_spice(mismatch, BUFFER) + "\n"
    extra += (f"vclk clk 0 pulse(0 {vdd} {T0:.4e} 10p 10p "
              f"{t_clk / 2 - 10e-12:.4e} {t_clk:.4e})\n")
    for i in nudos_ff(montaje, etapas):
        if montaje == "uno_buf":
            extra += f"xbuf{i} d{i} n{i} vdd 0 {BUFFER}\n"
            extra += f"xff{i} q{i} clk d{i} vdd vdd 0 {CELDA}\n"
        else:
            extra += f"xff{i} q{i} clk n{i} vdd vdd 0 {CELDA}\n"
    return txt.replace(".options reltol", extra + "\n.options reltol", 1)


def un_caso(arg):
    nombre, esquina, temp, vdd, mismatch, rep, n, montaje, etapas = arg
    nudos = " ".join(f"v(n{i})" for i in range(1, etapas + 1))
    qs = " ".join(f"v(q{i})" for i in nudos_ff(montaje, etapas))
    t0 = time.time()
    # Periodo del anillo ya cargado. El desapareamiento se sortea en cada
    # ejecucion (ngspice no deja fijar la semilla), asi que con mismatch el
    # periodo de la previa es de otro chip: vale solo para elegir el reloj.
    nombres, m, _ = simular(deck(esquina, temp, vdd, mismatch, T0 + 8e-9, 1e-9, "v(n1)",
                                 montaje, etapas),
                            orden=ai.NGSPICE, spiceinit=ai.SPICEINIT, timeout=3600)
    sub = cruces_subida(m[:, 0], m[:, 1], vdd / 2.0)
    t_prev = float(np.median(np.diff(sub[sub > 5e-9])))
    T_CLK = t_prev * (2 + AUREA)
    tstop = T0 + (n + 2) * T_CLK
    nombres, m, log = simular(deck(esquina, temp, vdd, mismatch, tstop, T_CLK,
                                   f"{nudos} {qs} v(clk)", montaje, etapas),
                              orden=ai.NGSPICE, spiceinit=ai.SPICEINIT,
                              timeout=4 * 3600)
    t = m[:, 0]
    tk = T0 + 5e-12 + np.arange(n) * T_CLK          # flanco de subida (mitad)
    filas = []
    crudo = {"tk": tk, "t_clk": T_CLK}
    for i in nudos_ff(montaje, etapas):
        v = m[:, nombres.index(f"v(n{i})")]
        q = m[:, nombres.index(f"v(q{i})")]
        sub = cruces_subida(t, v, vdd / 2.0)
        sub = sub[sub > 5e-9]
        periodo = float(np.median(np.diff(sub)))
        j = np.searchsorted(sub, tk) - 1
        ok = j >= 0
        fase = ((tk[ok] - sub[j[ok]]) / periodo) % 1.0
        bit_ff = (np.interp(tk[ok] + 0.8 * T_CLK, t, q) > vdd / 2).astype(int)
        bit_id = (np.interp(tk[ok], t, v) > vdd / 2).astype(int)
        # fase con el periodo local (cruces que rodean tk), para comparar
        jl = np.clip(j[ok], 0, sub.size - 2)
        fase_local = (tk[ok] - sub[jl]) / (sub[jl + 1] - sub[jl])
        crudo.update({f"sub{i}": sub, f"fase{i}": fase, f"fase_local{i}": fase_local,
                      f"ff{i}": bit_ff, f"id{i}": bit_id})
        # cobertura de fases: el mayor hueco entre fases vecinas
        fo = np.sort(fase)
        hueco = float(np.max(np.diff(np.concatenate([fo, fo[:1] + 1]))))
        # modulacion del periodo del anillo por el reloj: periodo medio de
        # los ciclos segun la fase de reloj en que empiezan (8 tramos)
        per = np.diff(sub)
        fc = ((sub[:-1] - tk[0]) / T_CLK) % 1.0
        sel = sub[:-1] > tk[0]
        tramos = [per[sel & (fc >= k / 8) & (fc < (k + 1) / 8)].mean() for k in range(8)]
        res = {}
        for nom, bit in (("ff", bit_ff), ("ideal", bit_id)):
            fs, fb, nb = bordes(fase, bit)
            p1 = (fb - fs) % 1.0 if fs is not None else float("nan")
            res[nom] = (p1, fs, fb, nb, float(bit.mean()))
        p = res["ff"][0]
        filas.append({"caso": nombre, "esquina": esquina, "temp": temp, "vdd": vdd,
                      "mismatch": int(mismatch), "rep": rep, "montaje": montaje,
                      "etapas": etapas, "nudo": i,
                      "periodo_ps": periodo * 1e12, "t_clk_ps": T_CLK * 1e12,
                      "n": int(ok.sum()),
                      "hueco_fase": hueco,
                      "p1_ff": p, "p1_ideal": res["ideal"][0],
                      "borde_sube_ff": res["ff"][1], "borde_baja_ff": res["ff"][2],
                      "borde_sube_ideal": res["ideal"][1], "borde_baja_ideal": res["ideal"][2],
                      "n_bordes_ff": res["ff"][3], "n_bordes_ideal": res["ideal"][3],
                      "frac_ff": res["ff"][4], "frac_ideal": res["ideal"][4],
                      "p1w_ff": p1_ponderada(fase, bit_ff),
                      "p1w_ideal": p1_ponderada(fase, bit_id),
                      "modulacion_periodo_ps": (max(tramos) - min(tramos)) * 1e12,
                      "h_cota_ff": -np.log2(max(p, 1 - p)) if p == p else float("nan"),
                      "h_cota_ff_w": -np.log2(max(pw := p1_ponderada(fase, bit_ff), 1 - pw)),
                      "segundos": time.time() - t0})
    dcr = RES / "biestable_ihp_crudo"
    dcr.mkdir(exist_ok=True)
    sm = ("" if montaje == "cinco" else f"_{montaje}") + \
        ("" if etapas == ETAPAS else f"_e{etapas}")
    np.savez(dcr / f"{nombre}{sm}_r{rep}.npz", **crudo)
    return filas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400, help="flancos de reloj por simulacion")
    ap.add_argument("--mismatch-n", type=int, default=6)
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--solo", default="", help="solo el caso con este nombre (prueba)")
    ap.add_argument("--montajes", default="cinco",
                    help="lista separada por comas de " + ", ".join(MONTAJES))
    ap.add_argument("--casos", default="", help="lista de casos sin desapareamiento "
                    "(por defecto, todos)")
    ap.add_argument("--etiqueta", default="", help="sufijo del CSV")
    ap.add_argument("--etapas", default=str(ETAPAS), help="lista de etapas del anillo")
    ap.add_argument("--mm-casos", default="tt27,ss_m40_v108",
                    help="casos que se repiten con desapareamiento")
    a = ap.parse_args()
    montajes = a.montajes.split(",")
    etapas = [int(e) for e in a.etapas.split(",")]
    assert all(e % 2 == 1 for e in etapas), etapas
    assert all(mo in MONTAJES for mo in montajes), montajes
    casos = [c for c in CASOS if not a.casos or c[0] in a.casos.split(",")]
    trabajos = []
    for mo in montajes:
        trabajos += [(c[0], c[1], c[2], c[3], False, 0, a.n, mo, e)
                     for e in etapas for c in casos]
        mm = [c for c in CASOS if c[0] in a.mm_casos.split(",")]
        for r in range(a.mismatch_n):
            trabajos += [(c[0] + "_mm", c[1], c[2], c[3], True, r, a.n, mo, e)
                         for e in etapas for c in mm]
    if a.solo:
        trabajos = [w for w in trabajos if w[0] == a.solo][:1]
    filas = []
    with ProcessPoolExecutor(a.procesos) as ex:
        for fs in ex.map(un_caso, trabajos):
            filas += fs
            print(f"{fs[0]['caso']} {fs[0]['montaje']} {fs[0]['etapas']} etapas rep {fs[0]['rep']}: periodo "
                  f"{fs[0]['periodo_ps']:.1f} ps, modulacion {fs[0]['modulacion_periodo_ps']:.2f} ps, "
                  f"hueco de fase max {max(f['hueco_fase'] for f in fs):.4f}, "
                  f"{fs[0]['segundos']:.0f} s; P(1) biestable / ideal por nudo (bordes; "
                  "ponderada): " +
                  "  ".join(f"n{f['nudo']} {f['p1_ff']:.4f}/{f['p1_ideal']:.4f}; "
                            f"{f['p1w_ff']:.4f}/{f['p1w_ideal']:.4f}" for f in fs), flush=True)
            for f in fs:
                if f["n_bordes_ff"] != 2 or f["n_bordes_ideal"] != 2:
                    print(f"  AVISO nudo {f['nudo']}: bordes ff {f['n_bordes_ff']}, "
                          f"ideal {f['n_bordes_ideal']} (deberian ser 2)", flush=True)
    sufijo = (f"_{a.solo}" if a.solo else "") + (f"_{a.etiqueta}" if a.etiqueta else "")
    salida = RES / f"biestable_ihp{sufijo}.csv"
    with open(salida, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f"\nCSV: {salida}")
    print("\nP(1) ponderada por el tramo de fase de cada muestra (no necesita bordes limpios)")
    print("\n| caso | montaje | n | periodo ps | modulacion ps | P(1) biestable (min-max) | "
          "ideal VDD/2 (min-max) | biestable - ideal (min-max) | H cota peor (biestable) | "
          "bordes ff max |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for clave in dict.fromkeys((f["caso"], f["montaje"], f["etapas"]) for f in filas):
        c = [f for f in filas if (f["caso"], f["montaje"], f["etapas"]) == clave]
        d = [f["p1w_ff"] - f["p1w_ideal"] for f in c]
        print(f"| {clave[0]} | {clave[1]} {clave[2]} et. | {len({f['rep'] for f in c})} | "
              f"{np.mean([f['periodo_ps'] for f in c]):.1f} | "
              f"{max(f['modulacion_periodo_ps'] for f in c):.2f} | "
              f"{min(f['p1w_ff'] for f in c):.4f}-{max(f['p1w_ff'] for f in c):.4f} | "
              f"{min(f['p1w_ideal'] for f in c):.4f}-{max(f['p1w_ideal'] for f in c):.4f} | "
              f"{min(d):+.4f}-{max(d):+.4f} | {min(f['h_cota_ff_w'] for f in c):.4f} | "
              f"{max(f['n_bordes_ff'] for f in c)} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
