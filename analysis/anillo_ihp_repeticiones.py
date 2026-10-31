#!/usr/bin/env python3
"""Jitter del anillo IHP con incertidumbre: N realizaciones independientes.

trnoise de ngspice 47 no es reproducible: el generador de Wallace se
siembra con getpid() al arrancar y ni `set rndseed`, ni `setseed`, ni
`.options seed` lo resiembran (solo tocan el Tausworthe;
src/frontend/trannoise/wallace.c, initw). Cada proceso da otra
realizacion, asi que la incertidumbre sale de repetir.

Lanza anillo_ihp.py N veces en paralelo (la primera con escalas 0,1,4
para la resolucion y la ley de la raiz; el resto solo con la 1) y
promedia Q = (sigma/T)^2, que es el estimador insesgado de la varianza
con el mismo numero de periodos. K_D va con 1/Q.

    python analysis/anillo_ihp_repeticiones.py            8 repeticiones, 400 ns
    python analysis/anillo_ihp_repeticiones.py --n 12 --procesos 6
    python analysis/anillo_ihp_repeticiones.py --n 4 --esquina mos_ss --temp 125 \
        --escalas-primera 1 --prefijo ss125_
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "results"
sys.path.insert(0, str(Path(__file__).resolve().parent))


def correr(k: int, args) -> Path:
    sesion = f"{args.prefijo}{k:02d}"
    js = RES / f"anillo_ihp_{sesion}.json"
    if js.exists():
        return js
    escalas = args.escalas_primera if k == 1 else "1"
    log = RES / f"anillo_ihp_{sesion}.log"
    with log.open("w", encoding="utf-8") as fh:
        r = subprocess.run([sys.executable, str(RAIZ / "analysis" / "anillo_ihp.py"),
                            "--tstop", args.tstop, "--escalas", escalas, "--sesion", sesion,
                            "--esquina", args.esquina, "--temp", str(args.temp),
                            "--vdd", str(args.vdd)] + (["--mismatch"] if args.mismatch else []),
                           stdout=fh, stderr=subprocess.STDOUT, timeout=6 * 3600)
    if r.returncode or not js.exists():
        raise RuntimeError(f"{sesion} devolvio {r.returncode}; ver {log}")
    return js


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--procesos", type=int, default=8)
    ap.add_argument("--tstop", default="400n")
    ap.add_argument("--prefijo", default="rep400n_")
    ap.add_argument("--esquina", default="mos_tt")
    ap.add_argument("--temp", type=float, default=27.0)
    ap.add_argument("--vdd", type=float, default=1.2)
    ap.add_argument("--mismatch", action="store_true",
                    help="cada realizacion es ademas un sorteo del desapareamiento (Monte Carlo)")
    ap.add_argument("--escalas-primera", default="0,1,4",
                    help="escalas de la primera realizacion (las demas, solo 1)")
    args = ap.parse_args()

    with ThreadPoolExecutor(max_workers=args.procesos) as ex:
        rutas = list(ex.map(lambda k: correr(k, args), range(1, args.n + 1)))

    filas, extra = [], {}
    for k, js in enumerate(rutas, 1):
        d = json.loads(js.read_text(encoding="utf-8"))
        for x in d["anillo"]:
            if x["escala"] == 1:
                filas.append({"rep": k, **x})
            elif k == 1:
                extra[x["escala"]] = x
    n = len(filas)
    q = [f["q_periodo"] for f in filas]
    q_m = sum(q) / n
    q_sd = math.sqrt(sum((x - q_m) ** 2 for x in q) / (n - 1))
    q_se = q_sd / math.sqrt(n)
    t_m = sum(f["periodo_ps"] for f in filas) / n
    s_m = math.sqrt(q_m) * t_m * 1e3                    # fs
    s_se = 0.5 * q_se / q_m * s_m

    from jitter_estimator import kd_necesario
    kd = kd_necesario(q_m)
    kd_lo, kd_hi = kd_necesario(q_m + q_se), kd_necesario(q_m - q_se)
    f0 = 1e12 / t_m

    out = RES / f"anillo_ihp_{args.prefijo}resumen.csv"
    cab = ["rep", "n_cruces", "periodo_ps", "sigma_fs", "sigma_rel", "q_periodo",
           "exponente", "potencia_uW", "segundos"]
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(",".join(cab) + "\n")
        for f in filas:
            fh.write(",".join(str(f[c]) for c in cab) + "\n")

    print(f"{n} realizaciones independientes, tstop {args.tstop}, escala 1 (ruido del PDK), "
          f"{args.esquina}, {args.temp:g} C, {args.vdd:g} V"
          + (", con desapareamiento" if args.mismatch else ""))
    for f in filas:
        print(f"  rep {f['rep']:2d}: {f['n_cruces']} cruces, T {f['periodo_ps']:.3f} ps, "
              f"sigma {f['sigma_fs']:.2f} fs, exp {f['exponente']:.2f}")
    print(f"\n  sigma por periodo = {s_m:.1f} +- {s_se:.1f} fs (1 sigma de la media; "
          f"dispersion entre repeticiones {100 * q_sd / q_m / 2:.1f} % en sigma)")
    print(f"  Q por periodo = {q_m:.4e} +- {q_se:.2e}")
    print(f"  K_D = {kd} (intervalo 1 sigma {kd_lo} - {kd_hi}); "
          f"{f0 / kd / 1e3:.2f} kbit/s a {f0 / 1e9:.3f} GHz")
    t = [f["periodo_ps"] for f in filas]
    t_sd = math.sqrt(sum((x - t_m) ** 2 for x in t) / (n - 1))
    kds = sorted(kd_necesario(x) for x in q)
    print(f"  periodo {t_m:.3f} ps, dispersion {t_sd:.3f} ps ({100 * t_sd / t_m:.2f} %); "
          f"K_D de cada realizacion: {kds[0]} - {kds[-1]} (mediana {kds[n // 2]})")
    if 0.0 in extra and 4.0 in extra:
        r1 = [f for f in filas if f["rep"] == 1][0]
        print(f"  rep 1: resolucion {extra[0.0]['sigma_fs']:.3f} fs; "
              f"ley de la raiz S x4 -> sigma x{extra[4.0]['sigma_fs'] / r1['sigma_fs']:.3f}")
    print(f"\ndatos en {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
