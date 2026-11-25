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

15-11-2026: H de diseno 0,80 y alfa 2^-30 (antes 0,98 y 2^-20, 22 y
596). Motivo en docs/basys2.md, "Decision del 15-11-2026": el sesgo del
muestreo del anillo IHP [SIMULADO] deja la cota de primer orden en
0,85-0,90, y con 2^-20 habia una falsa alarma cada pocos minutos en la
FPGA. Comprueba tambien la regla de la semilla: con lo peor que deja pasar
el APT, los 384 bits llevan al menos los 192 de entropia que pide un
CTR_DRBG AES-128 (SP 800-90A Rev. 1: 8.6.3 y tabla 3, entropia de entrada
>= security_strength = 128; 8.6.7, nonce >= security_strength/2 = 64, o
entrada "extra fuerte" >= 3/2 security_strength = 192 si sale de la misma
fuente a la vez, que es el caso: los bits van juntos).

16-11-2026: H de diseno 0,60 (51 y 766) y semilla de 512 bits (384 de
entropia + 128 de nonce). El biestable real de sg13g2 sesga el bit hasta
P(1) 0,372 a 125 C con desapareamiento [SIMULADO, analysis/biestable_ihp.py;
docs/basys2.md]: con 0,80 cinco de ocho chips quedaban por debajo, y con
384 bits y H 0,60 la regla de la semilla no se cumple (161 < 192).

22-11-2026: el integrado lleva anillos de 11/13 etapas y el Monte Carlo de
24 chips por esquina critica (results/biestable_mc_e11.md) da H declarable
0,757 (sf 125 C 1,08 V, mu - 3 sigma de P(1) 0,4081) y peor chip P(1)
0,4166. H 0,60 queda cerrada; los cortes no cambian.
"""
from __future__ import annotations

import math
import sys

from scipy.stats import binom

# Valores vigentes en rtl/trng/health_tests.vhd
RTL_RCT_C = 51
RTL_APT_W = 1024
RTL_APT_C = 766

ALFA = 2.0 ** -30        # tasa de falsa alarma por muestra (la norma: 2^-20 a 2^-40)
H_OBJ = 0.60             # min-entropia por bit de diseno
BITS_SEMILLA = 512       # entrada fija del CTR_DRBG (384 + 128)
# Monte Carlo de 24 chips, anillos de 11 etapas, sf 125 C 1,08 V [SIMULADO]
P_PEOR_CHIP = 1 - 0.4166          # peor chip
P_MU_3SIGMA = 1 - 0.4081          # mu - 3 sigma: la H declarable
ENTROPIA_DRBG = 192      # AES-128: 128 de entropia + nonce de 64


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
    pr = binom.sf(c - 1, w, p)                 # cola de coincidencias
    if complemento:
        pr += binom.cdf(w - c, w, p)           # cola del complemento
    return pr


def main() -> int:
    fallos = 0

    def chk(cond: bool, msg: str) -> None:
        nonlocal fallos
        print(f"  [{'ok ' if cond else 'FALLO'}] {msg}")
        fallos += 0 if cond else 1

    a = -math.log2(ALFA)
    print(f"SP 800-90B 4.4 — cortes para H = {H_OBJ}, alfa = 2^-{a:g}, W = {RTL_APT_W}\n")

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
        f"con las dos colas la falsa alarma sigue por debajo de 2^-{a:g} "
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

    print("5) Semilla con lo peor que deja pasar el APT")
    p_lim = RTL_APT_C / RTL_APT_W
    h_lim = -math.log2(p_lim)
    print(f"      p en el corte = {p_lim:.4f} -> H = {h_lim:.4f}; "
          f"{BITS_SEMILLA} bits x H = {BITS_SEMILLA * h_lim:.0f}")
    chk(BITS_SEMILLA * h_lim >= ENTROPIA_DRBG,
        f"{BITS_SEMILLA * h_lim:.0f} >= {ENTROPIA_DRBG} bits que pide el CTR_DRBG AES-128")

    print("6) Biestable sg13g2, Monte Carlo de 24 chips, 11 etapas [SIMULADO]")
    h_peor = -math.log2(P_PEOR_CHIP)
    fa = falsa_alarma_apt(RTL_APT_C, h_peor, complemento=True)
    print(f"      p = {P_PEOR_CHIP:.3f} -> H = {h_peor:.3f}; "
          f"falsa alarma APT por ventana {fa:.2e}")
    chk(h_peor >= H_OBJ, f"H del peor chip {h_peor:.3f} >= H declarada {H_OBJ}")
    chk(fa <= ALFA, f"falsa alarma del APT con el peor chip {fa:.2e} <= 2^-{a:g}")
    h_dec = -math.log2(P_MU_3SIGMA)
    fa = falsa_alarma_apt(RTL_APT_C, h_dec, complemento=True)
    print(f"      mu - 3 sigma: p = {P_MU_3SIGMA:.4f} -> H = {h_dec:.3f}; "
          f"falsa alarma APT por ventana {fa:.2e}")
    chk(h_dec >= H_OBJ, f"H declarable {h_dec:.3f} >= H declarada {H_OBJ}")
    chk(fa <= ALFA, f"falsa alarma del APT en mu - 3 sigma {fa:.2e} <= 2^-{a:g}")

    print(f"\ncortes_salud: {fallos} fallos")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
