#!/usr/bin/env python3
"""
entropy_analysis.py -- Statistical entropy analysis per condition.

For each cond{X}_rep1.bin:
  * Shannon entropy (bits/byte, ideal 8.0; and bits/bit, ideal 1.0)
  * bit-stream autocorrelation up to lag 1000 (ideal ~0 beyond lag 0)
  * power spectrum flatness (white-noise check)
  * byte-value histogram (uniformity, chi-square)
  * zlib compression ratio (1.0 = incompressible)

Output: results/entropy_summary.csv + 4-panel figure per condition +
        comparative figure.

TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
"""

from __future__ import annotations

import argparse
import csv
import zlib
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import fft as sfft
from scipy import stats

CONDITIONS = ["A", "B", "C", "D"]

plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "savefig.bbox": "tight"})


def shannon_entropy_bytes(data: bytes) -> float:
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8),
                         minlength=256)
    p = counts[counts > 0] / len(data)
    return float(-np.sum(p * np.log2(p)))


def shannon_entropy_bits(data: bytes) -> float:
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    p1 = bits.mean()
    if p1 in (0.0, 1.0):
        return 0.0
    return float(-(p1 * np.log2(p1) + (1 - p1) * np.log2(1 - p1)))


def autocorrelation(data: bytes, max_lag: int = 1000) -> np.ndarray:
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    x = bits.astype(np.float64) - bits.mean()
    # FFT-based autocorrelation, normalized
    n = len(x)
    f = sfft.rfft(x, 2 * n)
    ac = sfft.irfft(f * np.conj(f))[:max_lag + 1]
    return ac / ac[0]


def power_spectrum(data: bytes, nfft: int = 1 << 16):
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    x = 2.0 * bits[:nfft].astype(np.float64) - 1.0
    spec = np.abs(sfft.rfft(x)) ** 2 / nfft
    return spec


def compression_ratio(data: bytes) -> float:
    return len(zlib.compress(data, 9)) / len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dir", default=str(Path(__file__).resolve().parents[2] / "results" / "esp32_rng_agosto"))
    ap.add_argument("--figdir", default=None)
    args = ap.parse_args()
    d = Path(args.dir)
    figdirs = [d] + ([Path(args.figdir)] if args.figdir else [])

    rows = []
    fig_cmp, axes_cmp = plt.subplots(1, 3, figsize=(11, 3.2))

    for cond in CONDITIONS:
        f = d / f"cond{cond}_rep1.bin"
        if not f.exists():
            print(f"  [skip] {f.name} not found")
            continue
        data = f.read_bytes()
        h_byte = shannon_entropy_bytes(data)
        h_bit = shannon_entropy_bits(data)
        ac = autocorrelation(data)
        ac_max = float(np.max(np.abs(ac[1:])))
        spec = power_spectrum(data)
        flatness = float(np.exp(np.mean(np.log(spec + 1e-30))) /
                         np.mean(spec))
        cr = compression_ratio(data)
        counts = np.bincount(np.frombuffer(data, dtype=np.uint8),
                             minlength=256)
        chi2, chi2_p = stats.chisquare(counts)

        rows.append([cond, f"{h_byte:.6f}", f"{h_bit:.8f}",
                     f"{ac_max:.5f}", f"{flatness:.5f}", f"{cr:.5f}",
                     f"{chi2:.1f}", f"{chi2_p:.5f}"])
        print(f"  cond {cond}: H={h_byte:.4f} b/byte  H_bit={h_bit:.6f}  "
              f"acmax={ac_max:.4f}  flat={flatness:.3f}  zlib={cr:.4f}  "
              f"chi2_p={chi2_p:.4f}")

        # per-condition panel
        fig, ax = plt.subplots(2, 2, figsize=(8.5, 5.6))
        ax[0, 0].bar(np.arange(256), counts, width=1.0)
        ax[0, 0].axhline(len(data) / 256, color="k", ls="--", lw=0.7)
        ax[0, 0].set_title(f"byte histogram (chi2 p={chi2_p:.3f})",
                           fontsize=8)
        ax[0, 1].plot(ac[:200], lw=0.6)
        ax[0, 1].set_title(f"autocorrelation (max |ac|={ac_max:.4f})",
                           fontsize=8)
        ax[1, 0].semilogy(spec[1:], lw=0.4)
        ax[1, 0].set_title(f"power spectrum (flatness={flatness:.3f})",
                           fontsize=8)
        ax[1, 1].axis("off")
        ax[1, 1].text(0.05, 0.5,
                      f"condition {cond}\n"
                      f"H = {h_byte:.4f} bits/byte (ideal 8)\n"
                      f"H_bit = {h_bit:.6f} (ideal 1)\n"
                      f"zlib ratio = {cr:.4f} (ideal ~1)",
                      fontsize=10, va="center")
        fig.suptitle(f"Entropy analysis, condition {cond}")
        for o in figdirs:
            o.mkdir(parents=True, exist_ok=True)
            for ext in ("png", "pdf"):
                fig.savefig(o / f"entropy_cond{cond}.{ext}")
        plt.close(fig)

        axes_cmp[0].plot(ac[:100], lw=0.7, label=f"cond {cond}")
        axes_cmp[1].semilogy(spec[1:2048], lw=0.4, label=f"cond {cond}",
                             alpha=0.7)
        axes_cmp[2].bar(cond, cr)

    axes_cmp[0].set_title("autocorrelation (lag 1-100)", fontsize=8)
    axes_cmp[0].legend(fontsize=7)
    axes_cmp[1].set_title("power spectrum", fontsize=8)
    axes_cmp[2].set_title("zlib compression ratio", fontsize=8)
    axes_cmp[2].set_ylim(0.9, 1.05)
    for o in figdirs:
        for ext in ("png", "pdf"):
            fig_cmp.savefig(o / f"entropy_comparison.{ext}")
    plt.close(fig_cmp)

    with (d / "entropy_summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["condition", "H_bits_per_byte", "H_bits_per_bit",
                    "autocorr_max", "spectral_flatness", "zlib_ratio",
                    "byte_chi2", "byte_chi2_p"])
        w.writerows(rows)
    print(f"[entropy] summary -> {d / 'entropy_summary.csv'}")


if __name__ == "__main__":
    main()
