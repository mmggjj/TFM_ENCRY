#!/usr/bin/env python3
"""Campana de jitter del anillo frente a la densidad de ruido inyectada.

Comprueba la ley que debe cumplir el banco: el jitter por periodo escala
con la RAIZ de la densidad espectral de ruido, y el exponente de
acumulacion vale 1 mientras el ruido sea blanco. Si el banco no reproduce
eso con un ruido que ponemos nosotros, no sirve para medir el que no
conocemos.

La densidad cero no es un punto mas: es la medida de la RESOLUCION del
banco, o sea el ruido numerico del propio simulador. Todo jitter por
debajo de ese valor no existe.

Escritura incremental con volcado a disco por fila: una campana larga no
puede perderse por un corte, y los resultados parciales deben poder
mirarse mientras corre.

Uso:
    python campana_ruido.py [--etapas 5] [--cl 10f] [--tstop 120n]
"""
from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import numpy as np

from spice_ring import (cruces_subida, jitter_desde_cruces, netlist, simular)

RESULTADOS = Path(__file__).resolve().parent.parent / "results"
DENSIDADES = [0.0, 1.0e-20, 4.0e-20, 1.6e-19]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etapas", type=int, default=5)
    ap.add_argument("--cl", default="10f")
    ap.add_argument("--tstop", default="120n")
    ap.add_argument("--paso", default="0.2p")
    ap.add_argument("--paso-max", default="1p")
    ap.add_argument("--nt-ruido", type=float, default=2e-13)
    ap.add_argument("--descartar", type=int, default=20,
                    help="cruces iniciales a descartar (arranque del anillo)")
    ap.add_argument("--sesion", default="s1")
    args = ap.parse_args()

    RESULTADOS.mkdir(exist_ok=True)
    salida = RESULTADOS / f"spice_ruido_{args.sesion}.csv"

    with salida.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["densidad_ruido_A2Hz", "etapas", "cl", "tstop",
                    "n_cruces", "periodo_ps", "sigma_fs", "sigma_rel",
                    "exponente", "segundos", "t_epoch"])
        f.flush()

        print(f"{'S_i [A2/Hz]':>12} {'cruces':>7} {'T [ps]':>9} "
              f"{'sigma [fs]':>11} {'exp':>6} {'s':>7}")

        for s_i in DENSIDADES:
            t0 = time.time()
            txt = netlist(n_etapas=args.etapas, cl=args.cl, tstop=args.tstop,
                          paso=args.paso, paso_max=args.paso_max,
                          densidad_ruido=s_i, nt_ruido=args.nt_ruido)
            _, m, log = simular(txt)
            tc = cruces_subida(m[:, 0], m[:, 1], 0.9)
            dur = time.time() - t0

            if tc.size < 60:
                print(f"{s_i:12.1e} solo {tc.size} cruces; ngspice dijo:")
                print(log[-1500:])
                w.writerow([s_i, args.etapas, args.cl, args.tstop, tc.size,
                            "", "", "", "", f"{dur:.1f}", time.time()])
                f.flush()
                continue

            r = jitter_desde_cruces(tc, descartar=args.descartar)
            w.writerow([s_i, args.etapas, args.cl, args.tstop, r["n_cruces"],
                        f"{r['periodo'] * 1e12:.4f}",
                        f"{r['sigma_periodo'] * 1e15:.4f}",
                        f"{r['sigma_rel']:.4e}",
                        f"{r['exponente']:.4f}", f"{dur:.1f}", time.time()])
            f.flush()
            print(f"{s_i:12.1e} {r['n_cruces']:7d} "
                  f"{r['periodo'] * 1e12:9.2f} {r['sigma_periodo'] * 1e15:11.3f} "
                  f"{r['exponente']:6.2f} {dur:7.0f}", flush=True)

    # Contraste de la ley de escalado sobre lo ya escrito.
    filas = list(csv.DictReader(salida.open()))
    val = [(float(x["densidad_ruido_A2Hz"]), float(x["sigma_fs"]))
           for x in filas if x["sigma_fs"] and float(x["densidad_ruido_A2Hz"]) > 0]
    print(f"\nresolucion del banco (ruido apagado): "
          f"{filas[0]['sigma_fs'] or 'n/d'} fs")
    if len(val) >= 2:
        s0, j0 = val[0]
        print("escalado del jitter frente a la raiz de la densidad:")
        for s, j in val[1:]:
            print(f"  S_i x{s / s0:5.1f} -> sigma x{j / j0:5.2f} "
                  f"(teorico x{np.sqrt(s / s0):5.2f})")
    print(f"\ndatos en {salida}")


if __name__ == "__main__":
    main()
