#!/usr/bin/env python3
"""Jitter del ERO a partir de una tira CONTIGUA de bits capturada con un
divisor alto (el flujo continuo de la Basys 2, CFG_KD 12-14), donde el
estimador por varianza de jitter_estimator.py no vale.

Por que no vale aquel: promedia N pares consecutivos a distancia M y
supone que comparten el ruido de fase (M >> N) y que M*Q es diminuto. Con
la Q por muestra de un divisor alto (1e-4 a 1e-2 ciclos^2) no se cumplen
las dos cosas a la vez; con bits simulados de Q conocida infraestima entre
un 65 y un 100 % (docs/basys2.md).

Este ajusta la CURVA MEDIA. Con fase phi_j = phi_0 + j*nu + paseo
aleatorio de varianza Q por muestra y anillo con ciclo de trabajo d, la
fraccion de pares (b_j, b_{j+M}) distintos vale

    c(M) = 2 d (1-d) - sum_k 4 sin^2(pi k d) / (pi k)^2
                        * cos(2 pi k nu M) * exp(-2 pi^2 k^2 Q M^b)

con b = 1 para jitter termico (paseo aleatorio). Se mide c(M) sobre la
tira entera para M = 1..Mmax, d sale de la fraccion de unos, nu de la
oscilacion de c(M) (busqueda en rejilla y luego ajuste) y Q (y b) por
minimos cuadrados. Q es por MUESTRA: por periodo de ro2 es Q / 2^kd.
Una deriva lenta de nu (temperatura) tambien amortigua c(M), pero como
exp(-M^2): sale como b > 1. Por eso se ajusta b y se da tambien Q con b=1.

    python jitter_autocorrelacion.py --autotest
    python jitter_autocorrelacion.py --flujo kd13_flujo.bin --kd 13
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np
from scipy.optimize import least_squares

ARMONICOS = 25
Q_OBJETIVO = 0.2286          # Q de generacion para H_inf >= 0,98 (jitter_estimator)


def curva_c(bits, m_max: int) -> np.ndarray:
    """c(M) para M = 1..m_max: sobre la tira entera, o con una lista de
    trozos independientes, solo con pares dentro de cada trozo."""
    trozos = bits if isinstance(bits, list) else [bits]
    m_max = min(m_max, min(t.size for t in trozos) - 1)
    c = []
    for m in range(1, m_max + 1):
        dist = sum(int(np.count_nonzero(t[:-m] != t[m:])) for t in trozos)
        pares = sum(t.size - m for t in trozos)
        c.append(dist / pares)
    return np.array(c)


def modelo(M, d, nu, q, b=1.0):
    k = np.arange(1, ARMONICOS + 1)[:, None]
    coef = 4.0 * np.sin(np.pi * k * d) ** 2 / (np.pi * k) ** 2
    amort = np.exp(-2.0 * np.pi ** 2 * k ** 2 * q * np.power(M, b)[None, :])
    return 2 * d * (1 - d) - np.sum(coef * np.cos(2 * np.pi * k * nu * M[None, :]) * amort, axis=0)


def ajustar(c: np.ndarray, d: float, con_b: bool = True) -> dict:
    """Ajusta nu, Q (y b) a la curva c(M). nu y 1-nu son indistinguibles."""
    M = np.arange(1, c.size + 1, dtype=float)
    # nu inicial: rejilla fina en (0, 1/2]; Q inicial por cada nu, la mejor.
    mejor = None
    for nu0 in np.linspace(0.0005, 0.5, 2000):
        for q0 in (1e-5, 1e-4, 1e-3, 1e-2):
            r = np.sum((modelo(M, d, nu0, q0) - c) ** 2)
            if mejor is None or r < mejor[0]:
                mejor = (r, nu0, q0)
    _, nu0, q0 = mejor

    def res1(p):
        return modelo(M, d, p[0], 10 ** p[1]) - c
    s1 = least_squares(res1, [nu0, math.log10(q0)],
                       bounds=([0.0, -9.0], [0.5, 1.0]), x_scale=[1e-3, 0.1])
    out = {"nu": s1.x[0], "q": 10 ** s1.x[1],
           "rms": float(np.sqrt(np.mean(s1.fun ** 2))), "b": 1.0}
    if con_b:
        def res2(p):
            return modelo(M, d, p[0], 10 ** p[1], p[2]) - c
        s2 = least_squares(res2, [s1.x[0], s1.x[1], 1.0],
                           bounds=([0.0, -12.0, 0.3], [0.5, 1.0, 3.0]),
                           x_scale=[1e-3, 0.1, 0.05])
        out["b_libre"] = s2.x[2]
        out["q_b_libre"] = 10 ** s2.x[1]
        out["rms_b_libre"] = float(np.sqrt(np.mean(s2.fun ** 2)))
    return out


def m_max_auto(q_aprox: float) -> int:
    """M hasta que el fundamental se amortigua a ~e^-4 (o 4000)."""
    return int(min(4000, max(50, 4.0 / (2 * np.pi ** 2 * max(q_aprox, 1e-9)))))


def estimar(bits, m_max: int | None = None) -> dict:
    if isinstance(bits, list):
        d = float(np.concatenate(bits).mean())
        n = int(sum(t.size for t in bits))
    else:
        d = float(bits.mean())
        n = int(bits.size)
    if m_max is None:
        # Pasada corta para tener el orden de Q y elegir hasta donde mirar.
        r0 = ajustar(curva_c(bits, 200), d, con_b=False)
        m_max = m_max_auto(r0["q"])
    c = curva_c(bits, m_max)
    r = ajustar(c, d)
    r.update({"d": d, "m_max": c.size, "c": c, "n_bits": n})
    return r


def ajuste_conjunto(lista, m_max: int = 30) -> dict:
    """Q comun con un nu PROPIO por trozo: separa el jitter (dentro del
    trozo) de una deriva o salto de la razon de frecuencias entre trozos,
    que el ajuste global confunde con jitter. Rejilla en nu y en Q; el
    residuo se compara con el ruido binomial de estimar c(M) por trozo."""
    d = float(np.concatenate(lista).mean())
    C = np.stack([curva_c(t, m_max) for t in lista])
    M = np.arange(1, m_max + 1, dtype=float)
    nus = np.linspace(0.0, 0.5, 1001)
    qs = np.geomspace(1e-5, 0.5, 70)
    sse = []
    for q in qs:
        G = np.stack([modelo(M, d, nu, q) for nu in nus])
        S = (C ** 2).sum(1)[:, None] - 2 * C @ G.T + (G ** 2).sum(1)[None, :]
        sse.append(S.min(axis=1).sum())
    sse = np.array(sse)
    i = int(np.argmin(sse))
    q = float(qs[i])
    if 0 < i < qs.size - 1:
        x, y = np.log(qs[i - 1:i + 2]), sse[i - 1:i + 2]
        a2, a1, _ = np.polyfit(x, y, 2)
        if a2 > 0:
            q = float(np.exp(-a1 / (2 * a2)))
    longitudes = np.array([t.size for t in lista])[:, None]
    ruido = float(np.mean(C * (1 - C) / (longitudes - M[None, :])))
    return {"q": q, "residuo": float(sse[i] / C.size), "ruido": ruido,
            "saturado": i >= qs.size - 2}


def kd_necesario(q_por_periodo: float) -> float:
    return Q_OBJETIVO / q_por_periodo


def autotest() -> bool:
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    from ero_model import simular_bits
    fallos = 0
    print("Bits simulados con Q conocida (ero_model.simular_bits, d = 0,5), 10^6 bits")
    for q in (1e-4, 3e-4, 1e-3, 3e-3):
        for nu in (0.4771, 0.1234, 0.31):
            errs = []
            for s in range(3):
                bits = simular_bits(1_000_000, q, nu=nu, semilla=500 + s)
                r = estimar(bits)
                errs.append(r["q"] / q - 1)
            errs = np.array(errs)
            ok = abs(errs.mean()) < 0.05 and errs.std(ddof=1) < 0.08
            fallos += not ok
            print(f"  [{'ok ' if ok else 'FALLO'}] Q {q:.0e} nu {nu}: sesgo {100 * errs.mean():+.1f} %, "
                  f"dispersion {100 * errs.std(ddof=1):.1f} % (3 semillas), "
                  f"b libre {r['b_libre']:.2f}, M hasta {r['m_max']}")
    # Ciclo de trabajo distinto de 0,5: umbral de la fase en d.
    rng = np.random.default_rng(9)
    q, nu, dd = 1e-3, 0.2718, 0.42
    fase = (rng.random() + np.cumsum((nu + rng.normal(0, math.sqrt(q), 1_000_000)) % 1.0)) % 1.0
    bits = (fase < dd).astype(np.uint8)
    r = estimar(bits)
    ok = abs(r["q"] / q - 1) < 0.05
    fallos += not ok
    print(f"  [{'ok ' if ok else 'FALLO'}] ciclo de trabajo 0,42: Q {r['q']:.3e} frente a {q:.0e} "
          f"({100 * (r['q'] / q - 1):+.1f} %)")
    # Deriva lenta de nu sin jitter: no debe pasar por jitter termico.
    n = 1_000_000
    nus = 0.2718 + 2e-4 * np.sin(np.linspace(0, 3, n))
    fase = (0.1 + np.cumsum(nus + rng.normal(0, math.sqrt(1e-6), n))) % 1.0
    bits = (fase >= 0.5).astype(np.uint8)
    r = estimar(bits)
    ok = r["b_libre"] > 1.3
    fallos += not ok
    print(f"  [{'ok ' if ok else 'FALLO'}] deriva lenta de nu y jitter casi nulo (Q 1e-6): "
          f"b libre {r['b_libre']:.2f} (> 1,3 la delata), Q con b=1 {r['q']:.2e}")
    # Ajuste conjunto: nu distinto en cada trozo (deriva entre trozos).
    rng = np.random.default_rng(1)
    for q, desv in ((3e-3, 0.0), (3e-3, 0.03), (1e-4, 0.03)):
        lista = [simular_bits(2048, q, nu=0.37 + desv * rng.standard_normal(),
                              semilla=int(rng.integers(1 << 30))) for _ in range(300)]
        r = ajuste_conjunto(lista)
        # Con el modelo exacto el residuo no baja al ruido binomial: los c(M)
        # de M vecinas estan correlacionados y nu va en rejilla. Sale ~1,7
        # veces a Q 3e-3: es el suelo con el que comparar los datos reales.
        ok = abs(r["q"] / q - 1) < 0.05 and r["residuo"] < 2.5 * r["ruido"]
        fallos += not ok
        print(f"  [{'ok ' if ok else 'FALLO'}] conjunto, 300 trozos, Q {q:.0e}, nu con desviacion {desv} "
              f"entre trozos: Q {r['q']:.3e} ({100 * (r['q'] / q - 1):+.1f} %), residuo/ruido "
              f"{r['residuo'] / r['ruido']:.2f}")
    # Trozos independientes como los de flujo_desborde.py (3072 bits).
    for q in (3e-3, 3e-2):
        rng = np.random.default_rng(11)
        lista = [simular_bits(3072, q, nu=0.3141, semilla=int(rng.integers(1 << 30))) for _ in range(330)]
        r = estimar(lista)
        ok = abs(r["q"] / q - 1) < 0.03
        fallos += not ok
        print(f"  [{'ok ' if ok else 'FALLO'}] 330 trozos de 3072 bits, Q {q:.0e}: {r['q']:.4e} "
              f"({100 * (r['q'] / q - 1):+.1f} %), b libre {r['b_libre']:.2f}")
    print(f"autotest jitter_autocorrelacion: {fallos} fallos")
    return fallos == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--flujo", help="kdNN_flujo.bin de campana_motor.py --flujo (MSB primero)")
    ap.add_argument("--npz", help="kdNN_trozos.npz de flujo_desborde.py (trozos independientes)")
    ap.add_argument("--kd", type=int, help="CFG_KD de la captura")
    ap.add_argument("--m-max", type=int, default=None)
    ap.add_argument("--trozos", type=int, default=1,
                    help="parte la tira en n trozos y ajusta cada uno (deriva)")
    ap.add_argument("--conjunto", action="store_true",
                    help="con --npz: Q comun y un nu por trozo (separa deriva de jitter)")
    ap.add_argument("--autotest", action="store_true")
    a = ap.parse_args(argv)
    if a.autotest or not (a.flujo or a.npz):
        return 0 if autotest() else 1
    if a.npz:
        z = np.load(a.npz)
        cortes = np.cumsum(z["longitudes"])[:-1]
        lista = [np.unpackbits(t) for t in np.split(z["datos"], cortes)]
        if a.kd is None:
            a.kd = int(z["kd"])
        todos = np.concatenate(lista)
        print(f"{a.npz}: {len(lista)} trozos, {todos.size} bits, CFG_KD {a.kd}, "
              f"fraccion de unos {todos.mean():.4f}")
        if a.conjunto:
            r = ajuste_conjunto(lista)
            qp = r["q"] / 2 ** a.kd
            print(f"ajuste conjunto (nu por trozo, M = 1..30): Q por muestra {r['q']:.4e}"
                  f"{' (SATURADO: cota inferior)' if r['saturado'] else ''}; por periodo de ro2 {qp:.4e}; "
                  f"residuo medio {r['residuo']:.3e} frente a ruido binomial {r['ruido']:.3e} "
                  f"({r['residuo'] / r['ruido']:.1f} veces)")
            return 0
        partes = [list(p) for p in np.array_split(np.array(lista, dtype=object), a.trozos)]
    else:
        datos = np.frombuffer(open(a.flujo, "rb").read(), dtype=np.uint8)
        bits = np.unpackbits(datos)
        print(f"{a.flujo}: {bits.size} bits, CFG_KD {a.kd}, fraccion de unos {bits.mean():.4f}")
        partes = np.array_split(bits, a.trozos)
    qs = []
    for i, p in enumerate(partes):
        r = estimar(p, a.m_max)
        qs.append(r["q"])
        etiqueta = "tira entera" if a.trozos == 1 else f"trozo {i + 1}/{a.trozos}"
        print(f"{etiqueta}: nu {r['nu']:.5f}, Q por muestra {r['q']:.4e} (b = 1, rms {r['rms']:.2e}); "
              f"b libre {r['b_libre']:.3f} con Q {r['q_b_libre']:.4e} (rms {r['rms_b_libre']:.2e}); "
              f"M = 1..{r['m_max']}")
        if a.trozos == 1:
            print("  M     c medido   c modelo")
            Ms = np.unique(np.round(np.geomspace(1, r["m_max"], 25)).astype(int))
            mod = modelo(np.arange(1, r["m_max"] + 1, dtype=float), r["d"], r["nu"], r["q"])
            for m in Ms:
                print(f"  {m:5d}  {r['c'][m - 1]:.4f}    {mod[m - 1]:.4f}")
    q = float(np.median(qs))
    if a.trozos > 1:
        print(f"Q por muestra: mediana {q:.4e}, dispersion entre trozos {100 * np.std(qs, ddof=1) / np.mean(qs):.1f} %")
    if a.kd is not None:
        qp = q / 2 ** a.kd
        kd = kd_necesario(qp)
        print(f"Q por periodo de ro2 {qp:.4e} (sigma/T {math.sqrt(qp):.3e}); K_D para Q >= {Q_OBJETIVO}: "
              f"{kd:.3e} = 2^{math.log2(kd):.2f} -> CFG_KD {math.ceil(math.log2(kd))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
