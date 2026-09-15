#!/usr/bin/env python3
"""Modelo estocastico del ERO (Baudet et al., J. Cryptology 2011).

La fase del anillo muestreado es un proceso de Wiener: entre dos muestras
avanza nu ciclos de media y acumula varianza Q (el factor de calidad).
El bit es el semiperiodo en que cae la fase.

Dos usos: generar bits con Q CONOCIDA (banco de pruebas del estimador de
jitter y de los estimadores de entropia) y calcular las entropias exactas
con la gaussiana envuelta, que es la referencia contra la que se contrasta
la formula analitica.

Razonamiento y referencias: docs/estado_del_arte_trng.md seccion 2 y
docs/modelo_ero_resultados.md.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

LN2 = np.log(2.0)
# Coeficientes del desarrollo de H(s|phi0) en potencias de exp(-4*pi^2*Q).
# c1 es el de la ec. 14 de Baudet; c2 sale del termino epsilon^4 de la
# entropia binaria (deduccion en docs/modelo_ero_resultados.md).
_C1 = 4.0 / (np.pi**2 * LN2)
_C2 = 8.0 / (np.pi**4 * LN2)
# Amplitud del primer armonico del sesgo, ec. 8 de Baudet 2011.
_C_SESGO = 2.0 / np.pi


def shannon_serie(Q, orden=1):
    """Desarrollo asintotico de H(s(dt)|phi(0)) en bits.

    orden=1 es la ec. 14 de Baudet. ATENCION: no es una cota inferior de
    esa entropia; la serie tiene todos sus terminos negativos, luego
    cualquier truncamiento la SOBREESTIMA. El valor conservador es el de
    entropias_exactas(). Ver autotest(), apartado 1.
    """
    Q = np.asarray(Q, dtype=float)
    h = 1.0 - _C1 * np.exp(-4.0 * np.pi**2 * Q)
    if orden >= 2:
        h = h - _C2 * np.exp(-8.0 * np.pi**2 * Q)
    return h


def sesgo_max_analitico(Q):
    """Sesgo maximo |p-1/2| segun el primer armonico de la ec. 8."""
    Q = np.asarray(Q, dtype=float)
    return np.minimum(_C_SESGO * np.exp(-2.0 * np.pi**2 * Q), 0.5)


def min_entropia_analitica(Q):
    """Min-entropia por bit estimada con el sesgo del primer armonico."""
    return -np.log2(0.5 + sesgo_max_analitico(Q))


def p_uno(phi0, Q, nu=0.0, n_sigmas=10.0):
    """P(bit=1 | fase previa phi0) exacta, con la gaussiana envuelta.

    phi0 en ciclos (solo importa su parte fraccionaria). El bit vale 1 si
    frac(fase) cae en [1/2, 1).
    """
    phi0 = np.atleast_1d(np.asarray(phi0, dtype=float))
    s = np.sqrt(float(Q))
    m = phi0 + float(nu)
    k_lo = int(np.floor(m.min() - n_sigmas * s)) - 1
    k_hi = int(np.ceil(m.max() + n_sigmas * s)) + 1
    k = np.arange(k_lo, k_hi + 1)[:, None]
    z_hi = (k + 1.0 - m[None, :]) / s
    z_lo = (k + 0.5 - m[None, :]) / s
    p = (norm.cdf(z_hi) - norm.cdf(z_lo)).sum(axis=0)
    return np.clip(p, 0.0, 1.0)


def _h2(p):
    """Entropia binaria en bits, con los extremos definidos a 0."""
    p = np.clip(np.asarray(p, dtype=float), 0.0, 1.0)
    out = np.zeros_like(p)
    m = (p > 0.0) & (p < 1.0)
    out[m] = -(p[m] * np.log2(p[m]) + (1 - p[m]) * np.log2(1 - p[m]))
    return out


def entropias_exactas(Q, nu=0.0, n_grid=8192):
    """Entropias del bit condicionadas a la fase previa, sobre una rejilla
    de phi0 uniforme (distribucion estacionaria de la fase).

    Devuelve (shannon_media, min_entropia_peor_caso, sesgo_max).
    El peor caso de phi0 es el criterio conservador para la min-entropia:
    un atacante que conociera la fase elegiria el instante mas predecible.
    """
    phi0 = (np.arange(n_grid) + 0.5) / n_grid
    p = p_uno(phi0, Q, nu)
    shannon = float(_h2(p).mean())
    p_max = float(np.maximum(p, 1.0 - p).max())
    return shannon, float(-np.log2(p_max)), float(np.abs(p - 0.5).max())


def q_necesaria(objetivo, criterio="shannon", nu=0.0, lo=1e-4, hi=2.0):
    """Q minima para alcanzar un objetivo de entropia por bit.

    criterio: 'shannon' o 'min' (exactas), 'serie1' / 'serie2' (analiticas).
    Biseccion; las cuatro magnitudes crecen monotonamente con Q.
    """
    def f(q):
        if criterio == "serie1":
            return float(shannon_serie(q, 1))
        if criterio == "serie2":
            return float(shannon_serie(q, 2))
        s, hmin, _ = entropias_exactas(q, nu)
        return s if criterio == "shannon" else hmin

    if f(hi) < objetivo:
        raise ValueError(f"objetivo {objetivo} inalcanzable con Q<={hi}")
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if f(mid) < objetivo:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def simular_bits(n_bits, Q, nu=0.4771, semilla=None, phi0=None, bloque=1 << 16):
    """Genera n_bits del ERO con factor de calidad Q conocido.

    nu = avance medio de fase entre muestras (ciclos de RO1). Su parte
    entera es irrelevante; por defecto un valor irracional para no caer en
    un ciclo corto. La acumulacion se hace por bloques conservando solo la
    parte fraccionaria: con 1e7 muestras la suma directa perderia digitos
    significativos justo en la parte que importa.
    """
    rng = np.random.default_rng(semilla)
    n_bits = int(n_bits)
    s = np.sqrt(float(Q))
    fase = rng.random() if phi0 is None else float(phi0)
    bits = np.empty(n_bits, dtype=np.uint8)
    i = 0
    while i < n_bits:
        n = min(bloque, n_bits - i)
        incr = (nu + rng.normal(0.0, s, n)) % 1.0
        fases = (fase + np.cumsum(incr)) % 1.0
        bits[i:i + n] = (fases >= 0.5).astype(np.uint8)
        fase = float(fases[-1])
        i += n
    return bits


def autotest(verbose=True):
    """Valida el modelo, el simulador y las formulas analiticas."""
    fallos = []

    def chk(cond, msg):
        if not cond:
            fallos.append(msg)
        if verbose:
            estado = "ok " if cond else "FALLO"
            print(f"  [{estado}] {msg}")

    if verbose:
        print("1) La serie truncada SOBREESTIMA la entropia exacta")
        print("   (los terminos omitidos son todos negativos: no es cota inferior)")
    for Q in [0.02, 0.05, 0.10, 0.15, 0.20]:
        sh, _, _ = entropias_exactas(Q)
        s1 = float(shannon_serie(Q, 1))
        s2 = float(shannon_serie(Q, 2))
        chk(s1 >= sh - 1e-15 and s2 >= sh - 1e-15,
            f"Q={Q:.2f}: exacta {sh:.7f} <= orden2 {s2:.7f} <= orden1 {s1:.7f}")

    if verbose:
        print("2) El termino de orden 2 explica el error de la ec. 14")
    for Q in [0.10, 0.15, 0.20]:
        sh, _, _ = entropias_exactas(Q)
        e1 = float(shannon_serie(Q, 1)) - sh
        e2 = float(shannon_serie(Q, 2)) - sh
        chk(abs(e2) < 0.05 * abs(e1),
            f"Q={Q:.2f}: error orden1 {e1:.3e} pasa a {e2:.3e} "
            f"(reduccion x{abs(e1 / e2):.0f})")

    if verbose:
        print("3) Sesgo maximo: primer armonico frente al calculo exacto")
    for Q in [0.05, 0.10, 0.15, 0.20, 0.30]:
        _, _, sesgo = entropias_exactas(Q)
        aprox = float(sesgo_max_analitico(Q))
        err = abs(aprox - sesgo) / max(sesgo, 1e-15)
        chk(err < 0.02,
            f"Q={Q:.2f}: exacto {sesgo:.4e} vs armonico {aprox:.4e} "
            f"(error {100 * err:.3f} %)")

    if verbose:
        print("4) La min-entropia del primer armonico coincide con la exacta")
    for Q in [0.05, 0.10, 0.15, 0.20, 0.30]:
        _, hmin, _ = entropias_exactas(Q)
        aprox = float(min_entropia_analitica(Q))
        chk(abs(aprox - hmin) < 1e-4,
            f"Q={Q:.2f}: H_min exacta {hmin:.6f} vs armonico {aprox:.6f}")

    if verbose:
        print("5) El simulador reproduce p(1|phi0) exacta (fase fijada)")
    rng = np.random.default_rng(7)
    for Q in [0.05, 0.20]:
        for phi0 in [0.10, 0.37, 0.80]:
            n = 400_000
            fases = (phi0 + rng.normal(0.0, np.sqrt(Q), n)) % 1.0
            p_emp = float((fases >= 0.5).mean())
            p_teo = float(p_uno(phi0, Q)[0])
            err = abs(p_emp - p_teo)
            chk(err < 4.0 * 0.5 / np.sqrt(n),
                f"Q={Q:.2f} phi0={phi0:.2f}: p_emp {p_emp:.5f} vs "
                f"p_teo {p_teo:.5f} (dif {err:.1e})")

    if verbose:
        print("6) Q necesaria para los umbrales de AIS 20/31 v3.0 (PTG.2.2)")
    q_sh = q_necesaria(0.9998, "shannon")
    q_hm = q_necesaria(0.98, "min")
    q_s1 = q_necesaria(0.9998, "serie1")
    if verbose:
        print(f"  Shannon >= 0,9998   (exacta) -> Q >= {q_sh:.4f}")
        print(f"  min-entropia >= 0,98 (exacta) -> Q >= {q_hm:.4f}   <-- mas exigente")
        print(f"  Shannon >= 0,9998   (ec. 14) -> Q >= {q_s1:.4f}   (optimista)")
    chk(q_s1 <= q_sh,
        "la ec. 14 pide menos Q que el calculo exacto: optimista, no conservadora")
    chk(q_hm > q_sh,
        "el criterio de min-entropia es mas exigente que el de Shannon")

    print(f"\nautotest ero_model: {len(fallos)} fallos")
    for f in fallos:
        print("  -", f)
    return not fallos


if __name__ == "__main__":
    import sys
    sys.exit(0 if autotest() else 1)
