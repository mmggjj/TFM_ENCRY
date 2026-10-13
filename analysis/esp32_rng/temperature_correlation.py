#!/usr/bin/env python3
"""
temperature_correlation.py -- RNG quality vs die temperature.

Uses the per-sequence metadata recorded by capture_rng.py
(capture_log.csv: condition, rep, die temperature at frame begin/end,
throughput) joined with the Shannon entropy of each captured sequence.
The die self-heats along the campaign (radio + CPU), so successive
repetitions sample different temperatures without external equipment.

Outputs: results/entropy_vs_temperature.png/.pdf + Pearson r,
         results/temperature_correlation.csv

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
from scipy import stats

from entropy_analysis import shannon_entropy_bytes

plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "savefig.bbox": "tight"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dir", default=str(Path(__file__).resolve().parents[2] / "results" / "esp32_rng_agosto"))
    ap.add_argument("--figdir", default=None)
    args = ap.parse_args()
    d = Path(args.dir)
    figdirs = [d] + ([Path(args.figdir)] if args.figdir else [])

    rows = []
    with (d / "capture_log.csv").open() as f:
        for r in csv.DictReader(f):
            seq = d / f"cond{r['cond']}_rep{r['rep']}.bin"
            if not seq.exists():
                continue
            h = shannon_entropy_bytes(seq.read_bytes())
            try:
                temp = (float(r["temp_begin_c"]) +
                        float(r["temp_end_c"])) / 2.0
            except ValueError:
                continue
            rows.append((r["cond"], int(r["rep"]), temp, h,
                         float(r["throughput_Bps"] or 0)))
            print(f"  cond={r['cond']} rep={r['rep']} T={temp:.1f}C "
                  f"H={h:.5f} b/byte")

    if len(rows) < 4:
        raise SystemExit("not enough sequences with temperature metadata")

    temps = np.array([r[2] for r in rows])
    ents = np.array([r[3] for r in rows])
    conds = [r[0] for r in rows]

    pear_r, pear_p = stats.pearsonr(temps, ents)
    slope, intercept, *_ = stats.linregress(temps, ents)
    print(f"[temp] Pearson r={pear_r:.3f} (p={pear_p:.4f}), "
          f"slope={slope:.2e} bits/byte per C")

    fig, ax = plt.subplots(figsize=(6.2, 4))
    colors = {"A": "tab:green", "B": "tab:olive",
              "C": "tab:orange", "D": "tab:red"}
    for c in "ABCD":
        sel = [i for i, cc in enumerate(conds) if cc == c]
        if sel:
            ax.scatter(temps[sel], ents[sel], color=colors[c], s=40,
                       label=f"cond {c}")
    xs = np.linspace(temps.min() - 1, temps.max() + 1, 10)
    ax.plot(xs, slope * xs + intercept, "k--", lw=0.8,
            label=f"fit (r={pear_r:.2f})")
    ax.set_xlabel("die temperature [$^\\circ$C]")
    ax.set_ylabel("Shannon entropy [bits/byte]")
    ax.set_title("RNG output entropy vs die temperature")
    ax.legend(fontsize=8)
    for o in figdirs:
        o.mkdir(parents=True, exist_ok=True)
        for ext in ("png", "pdf"):
            fig.savefig(o / f"entropy_vs_temperature.{ext}")
    plt.close(fig)

    with (d / "temperature_correlation.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cond", "rep", "temp_c", "H_bits_per_byte",
                    "throughput_Bps"])
        w.writerows(rows)
        w.writerow([])
        w.writerow(["pearson_r", f"{pear_r:.4f}"])
        w.writerow(["pearson_p", f"{pear_p:.6f}"])
        w.writerow(["slope_per_C", f"{slope:.3e}"])
    print(f"[temp] -> entropy_vs_temperature.png/.pdf + CSV")


if __name__ == "__main__":
    main()
