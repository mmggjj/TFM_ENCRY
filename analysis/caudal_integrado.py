#!/usr/bin/env python3
"""Caudal, tiempos de arranque y siembra, y falsas alarmas de los tests de
salud del integrado (ro1 de 11 etapas, ro2 de 13, CFG_KD 25).

Caudal [SIMULADO -> ESTIMADO]: un bit cada 2^CFG_KD periodos de ro2, con el
periodo de ro2 de 13 etapas simulado sin ruido y sin desapareamiento en cada
esquina (results/anillo_ihp_periodo_<esquina>_e13.json, carga de 1 fF).

Falsas alarmas [ESTIMADO, bits iid con el sesgo del biestable]: tasas
exactas para la logica de rtl/trng/health_tests.vhd:
  RCT: alarma al llegar una racha a C; por bit, sum_v (1 - q_v) q_v^C.
  APT: ventana de W; alarma si una de las dos cuentas (unos o ceros) >= C.
P(1) del Monte Carlo de 11 etapas (results/biestable_mc_e11.md): mu - 3 sigma
de la peor esquina y el peor chip. Cota de tasa: el caudal de la esquina mas
rapida con el sesgo de la peor (las esquinas no coinciden: conservador).

    ~/eda/venv/bin/python analysis/caudal_integrado.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binom, poisson

sys.path.insert(0, str(Path(__file__).resolve().parent))
from biestable_mc import cola, filas_log  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "results"
SALIDA = RES / "caudal_integrado.md"

CFG_KD = 25
KD_MAX = 26
RCT_C, APT_W, APT_C = 51, 1024, 766
BITS_SEMILLA = 512
ANIO = 365.25 * 86400
ESQUINAS = [("ffm40_v132", "ff, −40 °C, 1,32 V"),
            ("ff125_v132", "ff, 125 °C, 1,32 V"), ("tt27", "tt, 27 °C, 1,2 V"),
            ("ss_m40_v108", "ss, −40 °C, 1,08 V")]
MC = ["biestable_ihp_mc24_e11_criticas.log", "biestable_ihp_mc24_e11_criticas_b.log",
      "biestable_ihp_mc24_e11_resto.log"]
# Basys 3, bitstream final a kd 19 [MEDIDO, docs/basys3.md 22-11-2026]
FPGA_BPS = 1e6 / 2564.516
FPGA_P1 = 0.495933


def tasa_rct(p1: float, c: int = RCT_C) -> float:
    """Alarmas del RCT por bit con bits iid."""
    return sum((1 - q) * q ** c for q in (p1, 1 - p1))


def prob_apt(p1: float, w: int = APT_W, c: int = APT_C) -> float:
    """Probabilidad de alarma del APT por ventana (cuenta o complemento)."""
    return float(binom.sf(c - 1, w, p1) + binom.sf(c - 1, w, 1 - p1))


def periodos() -> list[tuple[str, float]]:
    out = []
    for clave, nombre in ESQUINAS:
        f = RES / f"anillo_ihp_periodo_{clave}_e13.json"
        if f.exists():
            out.append((nombre, json.load(f.open())["anillo"][0]["periodo_ps"] * 1e-12))
    return out


def sesgos() -> list[tuple[str, float]]:
    datos: dict[str, list[float]] = {}
    for f in MC:
        for fila in filas_log(RES / f):
            if fila["mismatch"] == "1":
                datos.setdefault(fila["caso"], []).append(float(fila["p1w_ff"]))
    colas = {k: cola(np.mean(v), np.std(v, ddof=1)) for k, v in datos.items()}
    peor_esq = max(colas, key=lambda k: abs(colas[k] - 0.5))
    todos = np.concatenate([np.array(v) for v in datos.values()])
    peor_chip = float(todos[np.argmax(np.abs(todos - 0.5))])
    return [("bits ideales", 0.5),
            (f"peor chip de 120 ({peor_chip:.4f})", peor_chip),
            (f"μ − 3σ de {peor_esq.removesuffix('_mm')} ({colas[peor_esq]:.4f})", colas[peor_esq]),
            ("justo en H 0,60", 2 ** -0.6)]


def main() -> int:
    per = periodos()
    lin = ["# Caudal y falsas alarmas del integrado (analysis/caudal_integrado.py)", "",
           f"`CFG_KD` {CFG_KD} (`G_KD_MIN` = `G_KD_RESET`), ro2 de 13 etapas. Periodo de ro2 "
           "SIMULADO sin ruido, sin desapareamiento y con 1 fF de carga; caudal y tiempos ESTIMADOS.", "",
           "| Esquina | T(ro2) ps | bit cada (ms) | bit/s | arranque, 1024 bits (s) | siembra, 512-1535 bits (s) | bit/s con `CFG_KD` 26 |",
           "|---|---|---|---|---|---|---|"]
    for nombre, t in per:
        tb = 2 ** CFG_KD * t
        lin.append(f"| {nombre} | {t * 1e12:.1f} | {tb * 1e3:.1f} | {1 / tb:.1f} | {APT_W * tb:.0f} | "
                   f"{BITS_SEMILLA * tb:.0f}-{(BITS_SEMILLA + APT_W - 1) * tb:.0f} | {1 / (2 ** KD_MAX * t):.1f} |")
    bps_max = max(1 / (2 ** CFG_KD * t) for _, t in per)
    lin += ["", "Arranque tras reset o `borrar_alarmas`: una ventana completa del APT. Siembra: 512 bits y "
            "la espera al cierre de la ventana que contiene el último (de 0 a 1023 bits más); si se "
            "ordena justo al acabar el arranque, 1024. El DRBG y el CMAC (cientos de ciclos de reloj) "
            "no cuentan.", "",
            f"## Falsas alarmas [ESTIMADO, bits iid], cortes RCT {RCT_C} / APT {APT_C} de {APT_W}", "",
            f"Cota: integrado a {bps_max:.1f} bit/s (la esquina más rápida, con el sesgo de la peor). "
            f"Basys 3 a `kd 19`: {FPGA_BPS:.0f} bit/s [MEDIDO].", "",
            "| Fuente | P(1) | H | RCT por bit | APT por ventana | integrado, alarmas/año | "
            "P(≥ 4 en 24 h) | Basys 3, alarmas/año |",
            "|---|---|---|---|---|---|---|---|"]
    casos = sesgos() + [(f"Basys 3, sesgo medido ({FPGA_P1:.4f})", FPGA_P1)]
    for nombre, p1 in casos:
        r, a = tasa_rct(p1), prob_apt(p1)
        h = -np.log2(max(p1, 1 - p1))
        por_bit = r + a / APT_W
        ano_i = por_bit * bps_max * ANIO
        dia = poisson.sf(3, por_bit * bps_max * 86400)
        ano_f = por_bit * FPGA_BPS * ANIO
        lin.append(f"| {nombre} | {p1:.4f} | {h:.3f} | {r:.2e} | {a:.2e} | {ano_i:.2e} | {dia:.1e} | {ano_f:.2e} |")
    lin += ["", "El rearme del maestro (`motor_rearmar()`, 3 en 24 h) se agota con 4 alarmas en un día. "
            "El RCT domina; el APT queda por debajo de 10⁻²⁰ por ventana en todos los casos del "
            "biestable."]
    texto = "\n".join(lin) + "\n"
    SALIDA.write_text(texto)
    print(texto)
    print(f"datos en {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
