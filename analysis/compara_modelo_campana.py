#!/usr/bin/env python3
"""Modelo frente a campana: H_inf del modelo y cifra SP 800-90B por divisor.

Entrada: la carpeta de una sesion de analysis/campana_motor.py (resumen.csv
con h_min_90b por divisor, pasada con --90b) y la Q_raw por periodo de ro2,
dada o medida (`--jitter kd00.bin --kd-captura 0`, jitter_estimator).

La bateria no es una cota: a 10^6 bits se satura en ~0,84, con poca
entropia sobreestima y entre medias da algo menos que el modelo
(docs/fuente_simulada_90b.md). Por eso cada punto real NO se compara con
H_inf del modelo, sino con lo que da la bateria para bits del propio modelo
con esa H_inf: la calibracion de results/fuente_simulada_90b.csv (tres
casos IHP, tres semillas, 10^6 bits, no-IID en bits). La banda es el
minimo y maximo de la calibracion interpolados en H_inf, ensanchados por la
incertidumbre de Q_raw (--u-q, relativa) y una tolerancia (--tol).

Veredicto por divisor:
  compatible     la cifra real cae en la banda
  por debajo     menos de lo que da la bateria con bits del modelo: la
                 fuente tiene menos entropia que la que el modelo le da
                 con esa Q_raw (o hay dependencias que el modelo no tiene)
  por encima     mas: Q_raw medido por debajo del real, o la fuente mezcla
                 algo que el modelo no tiene
  saturada       H_inf del modelo >= 0,97: la bateria no distingue nada
                 ahi (se informa, no se juzga)

    python analysis/compara_modelo_campana.py --campana results/motor_campana/<sesion> \\
        --jitter results/motor_campana/<sesion>/kd00.bin --kd-captura 0
    python analysis/compara_modelo_campana.py --campana DIR --q-raw 2.4e-7
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ero_model import entropias_exactas            # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CALIBRACION = RAIZ / "results" / "fuente_simulada_90b.csv"
SATURADA = 0.97


def h_modelo(q: float) -> float:
    return max(entropias_exactas(q)[1], 0.0)


def leer_calibracion(ruta: Path):
    """(x, minimo, media, maximo) de la bateria frente a H_inf del modelo,
    con los puntos de igual H_inf agrupados."""
    filas = list(csv.DictReader(ruta.open(encoding="utf-8")))
    clave = next(c for c in filas[0] if c.endswith("hAssessed"))
    grupos: dict[float, list[float]] = {}
    for f in filas:
        if f["modo"] != "b1" or f["test"] != "noniid":
            continue
        if f.get("n_bits", "") not in ("", "1000000"):
            continue
        if f["caso"] == "ideal" or not f.get(clave):
            continue
        x = round(max(float(f["hmin_modelo"]), 0.0), 4)
        grupos.setdefault(x, []).append(float(f[clave]))
    xs = np.array(sorted(grupos))
    if xs.size < 4:
        raise SystemExit(f"{ruta}: calibracion con {xs.size} puntos")
    lo = np.array([min(grupos[x]) for x in xs])
    me = np.array([np.mean(grupos[x]) for x in xs])
    hi = np.array([max(grupos[x]) for x in xs])
    return xs, lo, me, hi


def comparar(filas, q_raw, u_q, tol, cal):
    xs, lo, me, hi = cal
    salida = []
    for f in filas:
        kd = int(f["kd"])
        h90 = f.get("h_min_90b", "")
        q = q_raw * 2 ** kd
        h = h_modelo(q)
        h_baja = h_modelo(q * (1 - u_q))
        h_alta = h_modelo(q * (1 + u_q))
        # banda de la bateria para bits del modelo con H_inf entre h_baja y h_alta
        b_lo = float(np.interp(h_baja, xs, lo)) - tol
        b_hi = float(np.interp(h_alta, xs, hi)) + tol
        esperado = float(np.interp(h, xs, me))
        if h90 in ("", None):
            veredicto, h90 = "sin cifra 90B", float("nan")
        else:
            h90 = float(h90)
            if h >= SATURADA:
                veredicto = "saturada"
            elif h90 < b_lo:
                veredicto = "por debajo"
            elif h90 > b_hi:
                veredicto = "por encima"
            else:
                veredicto = "compatible"
        salida.append({"kd": kd, "Q": q, "h_modelo": h, "h_modelo_baja": h_baja,
                       "h_modelo_alta": h_alta, "h90b_esperada": esperado,
                       "banda_baja": b_lo, "banda_alta": b_hi, "h90b": h90,
                       "bits": f.get("bits", ""), "veredicto": veredicto})
    return salida


def figura(salida, cal, q_raw, ruta: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "savefig.bbox": "tight", "pdf.fonttype": 42})
    xs, lo, me, hi = cal
    kds = np.array([s["kd"] for s in salida])
    k = np.linspace(kds.min() - 1, kds.max() + 1, 200)
    hm = np.array([h_modelo(q_raw * 2 ** v) for v in k])
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.plot(k, hm, color="0.2", lw=1.2, label=r"$H_\infty$ del modelo")
    ax.fill_between(k, np.interp(hm, xs, lo), np.interp(hm, xs, hi), color="0.75",
                    label="SP 800-90B con bits del modelo")
    ax.errorbar(kds, [s["h90b"] for s in salida],
                fmt="o", color="C3", ms=4, label="SP 800-90B, campaña")
    ax.axhline(SATURADA, color="0.5", lw=0.6, ls=":")
    ax.set_xlabel(r"CFG_KD ($K_D = 2^{\mathrm{CFG\_KD}}$)")
    ax.set_ylabel("min-entropía por bit")
    ax.set_ylim(0, 1.05)
    ax.set_title(rf"$Q_{{\mathrm{{raw}}}}$ = {q_raw:.3g} por periodo de ro2", fontsize=9)
    ax.legend(fontsize=7, loc="lower right")
    fig.savefig(ruta)
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--campana", type=Path, required=True,
                    help="carpeta de campana_motor.py con resumen.csv")
    q = ap.add_mutually_exclusive_group(required=True)
    q.add_argument("--q-raw", type=float, help="Q_raw por periodo de ro2")
    q.add_argument("--jitter", type=Path, help="kdNN.bin para jitter_estimator")
    ap.add_argument("--kd-captura", type=int, default=0)
    ap.add_argument("--u-q", type=float, default=0.10,
                    help="incertidumbre relativa de Q_raw (por defecto 10 %%)")
    ap.add_argument("--tol", type=float, default=0.03)
    ap.add_argument("--calibracion", type=Path, default=CALIBRACION)
    a = ap.parse_args(argv)

    if a.jitter:
        from jitter_estimator import desde_capturas
        r = desde_capturas(str(a.jitter), a.kd_captura)
        q_raw = r["q_por_periodo"]
        print(f"Q_raw de {a.jitter.name}: {q_raw:.4e} por periodo de ro2 "
              f"({r['n_M_usadas']} distancias, b = {r['b']:.2f})")
    else:
        q_raw = a.q_raw
    cal = leer_calibracion(a.calibracion)
    filas = list(csv.DictReader((a.campana / "resumen.csv").open(encoding="utf-8")))
    salida = comparar(filas, q_raw, a.u_q, a.tol, cal)

    print(f"\nQ_raw = {q_raw:.4e}, incertidumbre {100 * a.u_q:.0f} %, tolerancia {a.tol}")
    print(f"{'kd':>3} {'Q':>9} {'H_modelo':>9} {'90B esp.':>9} {'banda':>13} {'90B':>7}  veredicto")
    for s in salida:
        print(f"{s['kd']:3d} {s['Q']:9.4f} {s['h_modelo']:9.4f} {s['h90b_esperada']:9.4f} "
              f"{s['banda_baja']:6.3f}-{s['banda_alta']:5.3f} {s['h90b']:7.4f}  {s['veredicto']}")
    out = a.campana / "compara_modelo.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(salida[0]))
        w.writeheader()
        w.writerows(salida)
    fig = a.campana / "compara_modelo.png"
    figura(salida, cal, q_raw, fig)
    print(f"\ntabla: {out}\nfigura: {fig}")
    malos = [s for s in salida if s["veredicto"] in ("por debajo", "por encima")]
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
