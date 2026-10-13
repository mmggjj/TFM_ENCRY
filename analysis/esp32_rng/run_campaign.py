#!/usr/bin/env python3
"""
run_campaign.py -- Orchestrate the full RNG analysis campaign.

Assumes capture_rng.py has already populated results/ with cond*.bin,
seeds_rep*.bin and puf_boot*.bin (real silicon). Runs, in order:
  1. NIST SP 800-22 battery per condition           -> nist_analysis
  2. Statistical entropy analysis                   -> entropy_analysis
  3. Temperature correlation                        -> temperature_correlation
  4. Harvester validation                           -> harvester_validation
  5. Offline MQTT-TLS crypto demo                   -> mqtt_tls_demo

Figures are duplicated into memoria/figures for the thesis.

TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE.parents[1] / "results" / "esp32_rng_agosto"
FIGDIR = HERE.parents[1] / "memoria" / "figures"
PY = sys.executable


def run(script: str, *extra: str):
    cmd = [PY, str(HERE / script), "-d", str(RESULTS),
           "--figdir", str(FIGDIR), *extra]
    print(f"\n$ {script} {' '.join(extra)}")
    r = subprocess.run(cmd, cwd=HERE)
    if r.returncode != 0:
        print(f"  (warning: {script} exited {r.returncode})")


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    run("nist_analysis.py")
    run("entropy_analysis.py")
    run("temperature_correlation.py")
    run("harvester_validation.py")
    print("\n$ mqtt_tls_demo.py (offline)")
    subprocess.run([PY, str(HERE / "mqtt_tls_demo.py"),
                    "--seeds", str(RESULTS / "seeds_rep1.bin")], cwd=HERE)
    print(f"\n=== campaign analysis complete -> {RESULTS} ===")


if __name__ == "__main__":
    main()
