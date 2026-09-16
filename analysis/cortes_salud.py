#!/usr/bin/env python3
"""Recalculo de los cortes de los tests de salud (SP 800-90B, seccion 4.4).

Los genericos G_RCT_C y G_APT_C de rtl/trng/health_tests.vhd son
parametros normativos: de ellos depende que la fuente degradada se
detecte y que el ruido normal no dispare alarmas. Estaban calculados a
mano en docs/estado_del_arte_trng.md y no habia forma de comprobarlos.
Este modulo los deriva de las formulas de la norma y los coteja con los
valores del RTL.

Comprueba ademas el efecto de mirar tambien el complemento en el APT, que
es una adicion propia (la norma solo cuenta las repeticiones del primer
valor de la ventana) y por tanto hay que justificar.

    python analysis/cortes_salud.py
"""
from __future__ import annotations

import math
import sys

from scipy.stats import binom

# Valores vigentes en rtl/trng/health_tests.vhd
RTL_RCT_C = 22
RTL_APT_W = 1024
RTL_APT_C = 596

ALFA = 2.0 ** -20        # tasa de falsa alarma de la norma
H_OBJ = 0.98             # min-entropia por bit de diseno


def corte_rct(h: float, alfa: float = ALFA) -> int:
    """4.4.1: C = 1 + ceil(-log2(alfa) / H)."""
    return 1 + math.ceil(-math.log2(alfa) / h)


def corte_apt(h: float, w: int = RTL_APT_W, alfa: float = ALFA) -> int:
    """4.4.2: C = 1 + CRITBINOM(W, 2^-H, 1-alfa)."""
    return 1 + int(binom.ppf(1 - alfa, w, 2.0 ** -h))


def falsa_alarma_apt(c: int, h: float, w: int = RTL_APT_W,
                     complemento: bool = False) -> float:
    """Probabilidad de alarma por ventana con una fuente ideal de min-entropia h."""
    p = 2.0 ** -h
    pr = 1.0 - binom.cdf(c - 1, w, p)          # cola de coincidencias
    if complemento:
        pr += binom.cdf(w - c, w, p)           # cola del complemento
    return pr


def main() -> int:
    fallos = 0

    def chk(cond: bool, msg: str) -> None:
        nonlocal fallos
        print(f"  [{'ok ' if cond else 'FALLO'}] {msg}")
        fallos += 0 if cond else 1

    print(f"SP 800-90B 4.4 — cortes para H = {H_OBJ}, alfa = 2^-20, W = {RTL_APT_W}\n")

    print("1) Repetition Count Test")
    c = corte_rct(H_OBJ)
    chk(c == RTL_RCT_C, f"C = {c}, el RTL usa {RTL_RCT_C}")

    print("2) Adaptive Proportion Test")
    c = corte_apt(H_OBJ)
    chk(c == RTL_APT_C, f"C = {c}, el RTL usa {RTL_APT_C}")

    print("3) Coste del test del complemento (adicion propia, no de la norma)")
    una = falsa_alarma_apt(RTL_APT_C, H_OBJ)
    dos = falsa_alarma_apt(RTL_APT_C, H_OBJ, complemento=True)
    print(f"      una cola : {una:.4e}  (2^{math.log2(una):+.2f})")
    print(f"      dos colas: {dos:.4e}  (2^{math.log2(dos):+.2f})")
    chk(dos <= ALFA,
        f"con las dos colas la falsa alarma sigue por debajo de 2^-20 "
        f"({dos:.4e} <= {ALFA:.4e})")
    chk(dos / una < 1.05,
        f"el complemento apenas encarece la falsa alarma (x{dos / una:.4f}): "
        f"su cola cae a {(RTL_APT_W * 2.0 ** -H_OBJ - (RTL_APT_W - RTL_APT_C)) / math.sqrt(RTL_APT_W * 2.0 ** -H_OBJ * (1 - 2.0 ** -H_OBJ)):.1f} sigma")

    print("4) Los cortes dependen de H: hay que recalcularlos con la H MEDIDA")
    for h in (0.99, 0.98, 0.90, 0.75, 0.50):
        print(f"      H = {h:.2f}  ->  RCT C = {corte_rct(h):3d}   APT C = {corte_apt(h)}")
    chk(corte_apt(0.50) > corte_apt(0.98),
        "menos min-entropia exige un corte mas alto (mas permisivo)")
    chk(corte_rct(0.50) > corte_rct(0.98),
        "lo mismo en el RCT")

    print(f"\ncortes_salud: {fallos} fallos")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
