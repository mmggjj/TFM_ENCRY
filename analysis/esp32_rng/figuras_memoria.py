#!/usr/bin/env python3
"""
figuras_memoria.py -- Figuras del capitulo del ESP32 a partir de los datos
de la primera campana (results/esp32_rng_agosto), con la referencia de una
fuente perfecta a la misma longitud en vez del ideal de longitud infinita.

  esp32_metricas.pdf     autocorrelacion tipificada y periodograma frente a
                         ruido blanco (N(0,1) y exponencial)
  esp32_temperatura.pdf  entropia por byte frente a la lectura del sensor
                         en su propia unidad (entero en grados F)
  esp32_recolector.pdf   distancias de Hamming entre semillas frente a
                         Binomial(256, 1/2) y valores p del subconjunto NIST

Uso: ~/eda/venv/bin/python analysis/esp32_rng/figuras_memoria.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import scipy.fft as sfft
from scipy import stats

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
DATOS = RAIZ / "results" / "esp32_rng_agosto"
FIG = RAIZ / "memoria" / "figures"
sys.path.insert(0, str(AQUI))

CONDS = "ABCD"
COLOR = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a", "D": "#eda100"}
MARCA = {"A": "o", "B": "s", "C": "^", "D": "D"}
TINTA = "#0b0b0b"
TINTA2 = "#52514e"

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.edgecolor": TINTA2, "axes.linewidth": 0.6,
    "grid.color": "#d8d7d2", "grid.linewidth": 0.4,
    "savefig.bbox": "tight", "pdf.fonttype": 42,
})


def bits_de(cond: str) -> np.ndarray:
    datos = (DATOS / f"cond{cond}_rep1.bin").read_bytes()
    return np.unpackbits(np.frombuffer(datos, dtype=np.uint8))


def autocorrelacion(bits: np.ndarray, max_lag: int = 1000) -> np.ndarray:
    # Mismo calculo que entropy_analysis.py
    x = bits.astype(np.float64) - bits.mean()
    n = len(x)
    f = sfft.rfft(x, 2 * n)
    ac = sfft.irfft(f * np.conj(f))[:max_lag + 1]
    return ac / ac[0]


def periodograma(bits: np.ndarray, nfft: int = 1 << 16) -> np.ndarray:
    x = 2.0 * bits[:nfft].astype(np.float64) - 1.0
    return np.abs(sfft.rfft(x)) ** 2 / nfft


def figura_metricas():
    fig, ax = plt.subplots(1, 2, figsize=(6.3, 2.5))
    z = np.linspace(-4, 4, 400)
    u = np.linspace(0, 10, 400)
    bordes_z = np.linspace(-4, 4, 33)
    bordes_u = np.linspace(0, 10, 41)
    for c in CONDS:
        b = bits_de(c)
        r = autocorrelacion(b)[1:]
        ax[0].hist(r * np.sqrt(len(b)), bins=bordes_z, density=True,
                   histtype="step", lw=1.0, color=COLOR[c],
                   label=f"{c}")
        p = periodograma(b)[1:-1]
        p = p / p.mean()
        planitud = np.exp(np.mean(np.log(p)))
        ax[1].hist(p, bins=bordes_u, density=True, histtype="step", lw=1.0,
                   color=COLOR[c],
                   label=f"{c} (flatness {planitud:.3f})")
    ax[0].plot(z, stats.norm.pdf(z), color=TINTA, lw=0.8, ls="--",
               label="white noise")
    ax[0].set_xlabel(r"$r_k\sqrt{n}$, lags $k = 1$ to 1000")
    ax[0].set_ylabel("density")
    ax[0].set_title("(a) autocorrelation")
    ax[1].plot(u, np.exp(-u), color=TINTA, lw=0.8, ls="--",
               label=r"white noise ($e^{-\gamma}=0.561$)")
    ax[1].set_yscale("log")
    ax[1].set_ylim(1e-5, 2)
    ax[1].set_xlabel("periodogram bin / mean, first 65 536 bits")
    ax[1].set_title("(b) periodogram")
    for a in ax:
        a.grid(True)
        a.legend(frameon=False)
    fig.savefig(FIG / "esp32_metricas.pdf")
    plt.close(fig)


def figura_temperatura():
    filas = list(csv.DictReader((DATOS / "capture_log.csv").open()))
    h = {}
    for r in csv.DictReader((DATOS / "temperature_correlation.csv").open()):
        if r.get("cond") in CONDS:
            h[r["cond"]] = float(r["H_bits_per_byte"])
    n_bytes = 125000
    k = 255
    media = 8 - k / (2 * n_bytes * np.log(2))
    sigma = np.sqrt(2 * k) / (2 * n_bytes * np.log(2))

    def a_f(t_c: str) -> float:
        return round(float(t_c) * 1.8 + 32)

    fig, ax = plt.subplots(figsize=(4.2, 2.6))
    ax.axhspan(media - sigma, media + sigma, color="#e6e5e0", lw=0)
    ax.axhline(media, color=TINTA2, lw=0.7, ls="--")
    ax.text(125.55, media - 0.9 * sigma,
            r"perfect source, $\pm1\sigma$", color=TINTA2, fontsize=7)
    desp = {"A": 0.06, "B": 0.0, "C": -0.06, "D": 0.0}
    for r in filas:
        c = r["cond"]
        f0, f1 = a_f(r["temp_begin_c"]), a_f(r["temp_end_c"])
        y = h[c]
        xs = sorted({f0, f1})
        x = np.mean(xs) + desp[c]
        ax.plot([xs[0] + desp[c], xs[-1] + desp[c]], [y, y],
                color=COLOR[c], lw=1.2)
        ax.plot(x, y, MARCA[c], color=COLOR[c], ms=6,
                mec="white", mew=0.8, label=f"{c}")
    ax.set_xlim(125.5, 127.5)
    ax.set_xticks([126, 127])
    ax.set_xticklabels(["126 °F\n(52.2 °C)",
                        "127 °F\n(52.8 °C)"])
    ax.set_xlabel("sensor reading, begin to end of the sequence")
    ax.set_ylabel("Shannon entropy (bit/byte)")
    ax.set_ylim(media - 3.2 * sigma, media + 2.4 * sigma)
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.5f}"))
    ax.grid(True, axis="y")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, ncol=4, loc="upper left")
    fig.savefig(FIG / "esp32_temperatura.pdf")
    plt.close(fig)


def figura_recolector():
    from nist_sp800_22 import (frequency_test, block_frequency_test,
                               runs_test, spectral_test, serial_test,
                               approximate_entropy_test,
                               cumulative_sums_test, _bits)
    datos = (DATOS / "seeds_rep1.bin").read_bytes()
    n = len(datos) // 32
    arr = np.unpackbits(np.frombuffer(datos, dtype=np.uint8)).reshape(n, 256)
    # Misma muestra de pares que harvester_validation.py
    rng = np.random.default_rng(1)
    pares = set()
    while len(pares) < 20000:
        i, j = rng.integers(0, n, 2)
        if i != j:
            pares.add((min(i, j), max(i, j)))
    d = np.array([np.count_nonzero(arr[i] ^ arr[j]) for i, j in pares])
    print(f"Hamming: media {d.mean():.3f}, desviacion {d.std():.3f}")

    fig, ax = plt.subplots(1, 2, figsize=(6.3, 2.4),
                           gridspec_kw={"width_ratios": [1.5, 1],
                                        "wspace": 0.75})
    bordes = np.arange(d.min() - 0.5, d.max() + 1.5)
    ax[0].hist(d, bins=bordes, color=COLOR["A"], lw=0, alpha=0.85,
               label="1000 seeds, 20 000 pairs")
    x = np.arange(d.min(), d.max() + 1)
    ax[0].plot(x, len(d) * stats.binom.pmf(x, 256, 0.5), color=TINTA,
               lw=0.8, ls="--", label=r"Binomial(256, 1/2)")
    ax[0].set_xlabel("Hamming distance between two seeds (bits)")
    ax[0].set_ylabel("pairs")
    ax[0].set_title("(a) distance between seeds")
    ax[0].legend(frameon=False, loc="upper left", fontsize=6)
    ax[0].set_ylim(0, 1.3 * np.bincount(d).max())
    ax[0].grid(True, axis="y")
    ax[0].set_axisbelow(True)

    b = _bits(datos)
    pruebas = [frequency_test, block_frequency_test, runs_test,
               spectral_test, serial_test, approximate_entropy_test,
               cumulative_sums_test]
    nombres, ps = [], []
    for fn in pruebas:
        r = fn(b)
        nombres.append(r.name)
        ps.append(r.p_value)
        print(f"{r.name}: p = {r.p_value:.6f}")
    y = np.arange(len(ps))
    ax[1].plot(ps, y, "o", color=COLOR["A"], ms=5)
    ax[1].axvline(0.01, color=TINTA2, lw=0.7, ls="--")
    ax[1].set_yticks(y)
    ax[1].set_yticklabels(nombres)
    ax[1].set_xlim(0, 1)
    ax[1].set_xlabel(r"$p$ value ($\alpha = 0.01$ dashed)")
    ax[1].set_title("(b) SP 800-22 on the seed stream")
    ax[1].grid(True, axis="x")
    fig.savefig(FIG / "esp32_recolector.pdf")
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    figura_metricas()
    figura_temperatura()
    figura_recolector()
    print(f"figuras en {FIG}")


if __name__ == "__main__":
    main()
