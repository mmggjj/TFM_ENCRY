#!/usr/bin/env python3
"""
harvester_validation.py -- Validation of the multi-source entropy harvester.

Inputs: results/seeds_rep*.bin  (100 x 32-byte seeds per cycle, captured
        from the ESP32) and results/puf_boot*.bin (SRAM patterns).

Checks:
  1. Uniqueness      -- no duplicated seed across all captured seeds.
  2. Distribution    -- byte histogram uniformity (chi-square).
  3. Hamming         -- pairwise bit distance ~128/256 bits (50%).
  4. NIST            -- battery over the concatenated seed stream
                        (needs >= ~4000 seeds for 1 Mbit; with fewer,
                        runs the subset of tests valid at that length).
  5. PUF stability   -- inter-boot Hamming distance of SRAM patterns
                        (intra-device: expected ~3-8% noisy bits).

Output: results/harvester_validation.csv/.png/.pdf + console report.

TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "savefig.bbox": "tight"})


def load_seeds(d: Path) -> np.ndarray:
    seeds = []
    for f in sorted(d.glob("seeds_rep*.bin")):
        raw = f.read_bytes()
        seeds += [raw[i:i + 32] for i in range(0, len(raw) - 31, 32)]
    return seeds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dir", default=str(Path(__file__).resolve().parents[2] / "results" / "esp32_rng_agosto"))
    ap.add_argument("--figdir", default=None)
    args = ap.parse_args()
    d = Path(args.dir)
    figdirs = [d] + ([Path(args.figdir)] if args.figdir else [])

    seeds = load_seeds(d)
    n = len(seeds)
    if n == 0:
        raise SystemExit("no seeds_rep*.bin found")
    print(f"[harvester] {n} seeds of 32 bytes loaded")

    # 1. uniqueness
    unique = len(set(seeds))
    print(f"  uniqueness: {unique}/{n} distinct "
          f"({'OK' if unique == n else 'DUPLICATES FOUND'})")

    # 2. byte distribution
    all_bytes = np.frombuffer(b"".join(seeds), dtype=np.uint8)
    counts = np.bincount(all_bytes, minlength=256)
    chi2, p_chi = stats.chisquare(counts)
    print(f"  byte distribution: chi2={chi2:.1f} p={p_chi:.4f} "
          f"({'OK' if p_chi >= 0.01 else 'BIASED'})")

    # 3. pairwise Hamming distances (sample up to 20k pairs)
    arrs = np.unpackbits(
        np.frombuffer(b"".join(seeds), dtype=np.uint8)).reshape(n, 256)
    rng = np.random.default_rng(1)
    n_pairs = min(20000, n * (n - 1) // 2)
    pairs = set()
    while len(pairs) < n_pairs:
        i, j = rng.integers(0, n, 2)
        if i != j:
            pairs.add((min(i, j), max(i, j)))
    dists = np.array([np.count_nonzero(arrs[i] ^ arrs[j])
                      for i, j in pairs])
    print(f"  hamming: mean={dists.mean():.2f}/256 "
          f"({100*dists.mean()/256:.2f}%, ideal 50%), "
          f"std={dists.std():.2f} (ideal ~8)")

    # 4. NIST subset over concatenated seeds
    stream = b"".join(seeds)
    from nist_sp800_22 import (frequency_test, block_frequency_test,
                               runs_test, spectral_test, serial_test,
                               approximate_entropy_test,
                               cumulative_sums_test, _bits)
    bits = _bits(stream)
    subset = [frequency_test, block_frequency_test, runs_test,
              spectral_test, serial_test, approximate_entropy_test,
              cumulative_sums_test]
    nist_rows = []
    for fn in subset:
        r = fn(bits)
        nist_rows.append((r.name, r.p_value, r.passed))
        print(f"  NIST {r.name:24s} p={r.p_value:.5f} "
              f"{'PASS' if r.passed else 'FAIL'}")

    # 5. PUF inter-boot stability
    pufs = [f.read_bytes() for f in sorted(d.glob("puf_boot*.bin"))]
    puf_stats = []
    if len(pufs) >= 2:
        for (i, a), (j, b) in itertools.combinations(
                enumerate(pufs, 1), 2):
            hd = np.count_nonzero(
                np.unpackbits(np.frombuffer(a, np.uint8)) ^
                np.unpackbits(np.frombuffer(b, np.uint8)))
            puf_stats.append(hd)
        arr = np.array(puf_stats)
        total = len(pufs[0]) * 8
        print(f"  PUF inter-boot Hamming: mean={arr.mean():.0f}/{total} "
              f"bits ({100*arr.mean()/total:.2f}%) over "
              f"{len(pufs)} boots")
    else:
        print(f"  PUF stability: only {len(pufs)} boot pattern(s) -- "
              "need >=2 power cycles")

    # figure
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
    axes[0].hist(dists, bins=40, color="tab:blue", alpha=0.8)
    axes[0].axvline(128, color="k", ls="--", lw=0.8)
    axes[0].set_title(f"pairwise Hamming ({n_pairs} pairs)\n"
                      f"mean={dists.mean():.1f}, ideal 128", fontsize=8)
    axes[1].bar(np.arange(256), counts, width=1.0)
    axes[1].axhline(len(all_bytes) / 256, color="k", ls="--", lw=0.8)
    axes[1].set_title(f"seed byte histogram (p={p_chi:.3f})", fontsize=8)
    names = [r[0] for r in nist_rows]
    pvals = [r[1] for r in nist_rows]
    colors = ["tab:green" if r[2] else "tab:red" for r in nist_rows]
    axes[2].barh(names, pvals, color=colors)
    axes[2].axvline(0.01, color="k", ls="--", lw=0.8)
    axes[2].set_title("NIST subset on seed stream", fontsize=8)
    axes[2].set_xlabel("p-value")
    fig.suptitle(f"Harvester validation: {n} seeds, "
                 f"{unique} unique, Hamming {100*dists.mean()/256:.1f}%")
    for o in figdirs:
        o.mkdir(parents=True, exist_ok=True)
        for ext in ("png", "pdf"):
            fig.savefig(o / f"harvester_validation.{ext}")
    plt.close(fig)

    with (d / "harvester_validation.csv").open("w") as f:
        f.write("metric,value\n")
        f.write(f"n_seeds,{n}\n")
        f.write(f"unique,{unique}\n")
        f.write(f"byte_chi2_p,{p_chi:.6f}\n")
        f.write(f"hamming_mean_bits,{dists.mean():.3f}\n")
        f.write(f"hamming_std_bits,{dists.std():.3f}\n")
        for name, p, ok in nist_rows:
            f.write(f"nist_{name.replace(' ', '_')},{p:.6f}\n")
        if puf_stats:
            f.write(f"puf_interboot_hamming_pct,"
                    f"{100*np.mean(puf_stats)/(len(pufs[0])*8):.4f}\n")
    print(f"[harvester] -> harvester_validation.csv/.png/.pdf")


if __name__ == "__main__":
    main()
