#!/usr/bin/env python3
"""Sesgo y autocorrelación a retardos cortos de las secuencias de la tabla
O8 (FPGA, ESP32, bits con sesgo), con su z frente a bits independientes.

    ~/eda/venv/bin/python analysis/sesgo_correlacion.py [--extra nombre=fichero ...]

Ficheros .bits (un bit por byte) o .bin (empaquetados, MSB primero).
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entropia_90b as e90                       # noqa: E402

RES = e90.RES
CAMP = RES / "motor_campana"
RETARDOS = (1, 2, 3, 4, 8)


def bits_de(f: Path) -> np.ndarray:
    if f.suffix == ".bits":
        return np.frombuffer(f.read_bytes(), dtype=np.uint8)
    return np.unpackbits(np.frombuffer(f.read_bytes(), dtype=np.uint8))


def fila(nombre, b):
    b = b.astype(float)
    n = len(b)
    m = b.mean()
    x = b - m
    v = x.var()
    r = [(x[:-k] * x[k:]).mean() / v for k in RETARDOS]
    return nombre, n, m, (m - 0.5) / np.sqrt(0.25 / n), r, r[0] * np.sqrt(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", nargs="*", default=[], help="nombre=fichero")
    ap.add_argument("--solo-extra", action="store_true")
    a = ap.parse_args()
    sec = [(f"FPGA kd{k}", CAMP / "basys2_campana_90b_kd12_16/entropia90b/bits" / f"kd{k}_flujo.bits")
           for k in (12, 13, 14, 15, 16)]
    sec.append(("FPGA kd14 larga", CAMP / "basys2_larga_kd14_n8378368/entropia90b/bits/kd14_flujo.bits"))
    for s in (1, 2, 3):
        sec.append((f"iid p1=0,4979 s{s}", RES / "sesgo_90b/secuencias" / f"p0.4979_n8378368_s{s}.bits"))
    esp = {n: f for n, f in e90.FUENTES.items() if not n.startswith(("0928t2", "0928rd"))}
    extra = [(e.split("=", 1)[0], Path(e.split("=", 1)[1])) for e in a.extra]
    if a.solo_extra:
        sec, esp_largas = extra, []
    else:
        sec, esp_largas = sec + extra, [(f"ESP32 {n}", esp[n]) for n in ("esp_rf_off_1", "esp_rf_off_2")]
    print("| secuencia | N | fracción de unos | z sesgo | " +
          " | ".join(f"ρ{k}" for k in RETARDOS) + " | z ρ1 |")
    print("|---|---|---|---|" + "---|" * len(RETARDOS) + "---|")
    for nombre, f in sec + esp_largas:
        if not f.exists():
            print(f"| {nombre} | falta {f} |")
            continue
        n_, n, m, zf, r, zr = fila(nombre, bits_de(f))
        print(f"| {n_} | {n} | {m:.4f} | {zf:.1f} | " + " | ".join(f"{q:+.4f}" for q in r) + f" | {zr:.1f} |")
    if a.solo_extra:
        return
    zs = [fila(n, bits_de(f)) for n, f in esp.items() if not n.startswith("esp_rf_off")]
    zf = np.array([t[3] for t in zs])
    zr = np.array([t[5] for t in zs])
    print()
    print(f"ESP32, {len(zs)} capturas de 10^6 (las de los ANOVA): z sesgo media {zf.mean():.2f}, "
          f"desviación {zf.std(ddof=1):.2f}, máx |z| {abs(zf).max():.1f}; z ρ1 media {zr.mean():.2f}, "
          f"desviación {zr.std(ddof=1):.2f}, máx |z| {abs(zr).max():.1f}")


if __name__ == "__main__":
    main()
