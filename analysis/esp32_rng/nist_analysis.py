#!/usr/bin/env python3
"""
nist_analysis.py -- Full NIST SP 800-22 battery over the captured campaign.

Input : results/cond{A..D}_rep{N}.bin (from capture_rng.py)
Output: results/nist_results.csv        p-value per test/condition/rep
        results/nist_heatmap.png/.pdf   test x condition matrix (rep 1)
        results/nist_summary.csv        pass counts per condition

Usage:
  python nist_analysis.py   (por defecto lee results/esp32_rng_agosto)

TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nist_sp800_22 import run_all_nist_tests, ALPHA

CONDITIONS = ["A", "B", "C", "D"]
COND_DESC = {
    "A": "WiFi ON + ADC ON",
    "B": "WiFi ON + ADC OFF",
    "C": "WiFi OFF + ADC ON",
    "D": "WiFi OFF + ADC OFF",
}
# short labels for the heatmap axis (the long ones overlap)
COND_SHORT = {"A": "Wi-Fi\n+ ADC", "B": "Wi-Fi", "C": "ADC", "D": "none"}

plt.rcParams.update({"figure.dpi": 130, "font.size": 9,
                     "savefig.bbox": "tight"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dir", default=str(Path(__file__).resolve().parents[2] / "results" / "esp32_rng_agosto"))
    ap.add_argument("--figdir", default=None,
                    help="extra dir for figures (thesis)")
    args = ap.parse_args()
    d = Path(args.dir)

    rows = []
    matrix = {}          # (test, cond) -> p of rep 1
    test_names = None

    for cond in CONDITIONS:
        for f in sorted(d.glob(f"cond{cond}_rep*.bin")):
            rep = int(f.stem.split("rep")[1])
            data = f.read_bytes()
            print(f"\n=== NIST battery: condition {cond} "
                  f"({COND_DESC[cond]}), rep {rep}, "
                  f"{len(data)*8:,} bits ===")
            results = run_all_nist_tests(data, f"{cond}{rep}")
            if test_names is None:
                test_names = [r.name for r in results]
            for r in results:
                rows.append([cond, rep, r.name, f"{r.p_value:.6f}",
                             int(r.passed)])
                if rep == 1:
                    matrix[(r.name, cond)] = r.p_value
            n_pass = sum(1 for r in results if r.passed)
            print(f"  => condition {cond} rep {rep}: {n_pass}/15 PASS")

    if not rows:
        raise SystemExit("no cond*.bin files found -- run capture first")

    with (d / "nist_results.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["condition", "rep", "test", "p_value", "passed"])
        w.writerows(rows)
    print(f"\n[nist] results -> {d / 'nist_results.csv'}")

    # summary: pass count per condition/rep
    with (d / "nist_summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["condition", "rep", "tests_passed", "tests_total"])
        seen = {}
        for cond, rep, _, _, passed in rows:
            seen.setdefault((cond, rep), 0)
            seen[(cond, rep)] += int(passed)
        for (cond, rep), n in sorted(seen.items()):
            w.writerow([cond, rep, n, 15])

    # heatmap (rep 1)
    if test_names and matrix:
        conds = [c for c in CONDITIONS
                 if any((t, c) in matrix for t in test_names)]
        M = np.array([[matrix.get((t, c), np.nan) for c in conds]
                      for t in test_names])
        fig, ax = plt.subplots(figsize=(6.2, 6.4))
        # green for pass intensity, red for fail
        display = np.where(M >= ALPHA, np.minimum(M, 1.0), np.nan)
        im = ax.imshow(display, cmap="Greens", vmin=0, vmax=1,
                       aspect="auto")
        fails = np.where(M < ALPHA)
        for i, j in zip(*fails):
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                       color="tab:red", alpha=0.85))
            ax.text(j, i, f"{M[i, j]:.3f}", ha="center", va="center",
                    fontsize=6, color="white")
        ok = np.where(M >= ALPHA)
        for i, j in zip(*ok):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                    fontsize=6)
        ax.set_xticks(range(len(conds)))
        ax.set_xticklabels([f"{c}\n{COND_SHORT[c]}" for c in conds],
                           fontsize=7)
        ax.set_yticks(range(len(test_names)))
        ax.set_yticklabels(test_names, fontsize=7)
        ax.set_title("NIST SP 800-22 p-values by operating condition\n"
                     "(red = FAIL, p < 0.01)", fontsize=9)
        fig.colorbar(im, ax=ax, shrink=0.7, label="p-value")
        outs = [d]
        if args.figdir:
            outs.append(Path(args.figdir))
        for o in outs:
            o.mkdir(parents=True, exist_ok=True)
            for ext in ("png", "pdf"):
                fig.savefig(o / f"nist_heatmap.{ext}")
        plt.close(fig)
        print(f"[nist] heatmap -> nist_heatmap.png/.pdf")


if __name__ == "__main__":
    main()
