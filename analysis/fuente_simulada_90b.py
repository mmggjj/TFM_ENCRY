#!/usr/bin/env python3
"""El lado de la fuente en la comparacion con el ESP32, simulado.

Genera secuencias del ERO con el modelo estocastico (ero_model.simular_bits)
y el jitter de los transistores IHP (Q por periodo de anillo_ihp_*), y las
pasa por la bateria SP 800-90B del NIST con la misma via que las capturas
del ESP32 (entropia_90b.ejecutar: mismos binarios, opciones y longitud).
Compara la min-entropia estimada con la exacta del modelo.

Son bits SIMULADOS: validan la cadena jitter -> modelo -> entropia, no
sustituyen a la campana en la FPGA. Lectura en docs/fuente_simulada_90b.md.

    python analysis/fuente_simulada_90b.py              barrido completo
    python analysis/fuente_simulada_90b.py --kd 20 22   solo esos divisores
    python analysis/fuente_simulada_90b.py --casos ideal --kd 0   referencia uniforme
    python analysis/fuente_simulada_90b.py --tests iid --modos b8  via IID (b1 tarda ~28 min)
    python analysis/fuente_simulada_90b.py --n 8378368 --kd 23    longitud de esp_rf_off_2
"""
from __future__ import annotations

import argparse
import csv
import sys
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entropia_90b as e90                       # noqa: E402
from ero_model import entropias_exactas, simular_bits   # noqa: E402

RES = e90.RES
DIR = RES / "fuente_simulada_90b"
SEC = DIR / "secuencias"                         # se regeneran: fuera de git
CSV = RES / "fuente_simulada_90b.csv"
N_BITS = 10**6                                   # como las capturas del ESP32; --n lo cambia

# Q por periodo (sigma/T)^2 de results/anillo_ihp_*_resumen.csv
CASOS = {
    "tt27": 2.3301e-07,          # tt, 27 C, 1,2 V, media de 8 realizaciones
    "ss40v108": 6.0024e-08,      # ss, -40 C, 1,08 V, media de 8
    "ss40v108_peor": 5.0857e-08, # el peor de los 15 chips con desapareamiento
    "ideal": None,               # referencia: bits uniformes e independientes
}


def nombre_de(caso: str, kd_exp: int, rep: int) -> str:
    sufijo = "" if N_BITS == 10**6 else f"_n{N_BITS}"   # no pisa las filas de 1e6
    return f"{caso}_kd{kd_exp}_r{rep}{sufijo}"


def secuencia(caso: str, kd_exp: int, rep: int) -> tuple[Path, Path, float]:
    nombre = nombre_de(caso, kd_exp, rep)
    semilla = zlib.crc32(nombre.encode())          # reproducible y distinta por secuencia
    if CASOS[caso] is None:
        q = float("inf")
        bits = np.random.default_rng(semilla).integers(0, 2, N_BITS, dtype=np.uint8)
    else:
        q = CASOS[caso] * 2.0**kd_exp
        bits = simular_bits(N_BITS, q, semilla=semilla)
    b1 = SEC / f"{nombre}.bits"
    b8 = SEC / f"{nombre}.bin"
    b1.write_bytes(bits.tobytes())
    b8.write_bytes(np.packbits(bits).tobytes())    # MSB primero, como el ESP32
    return b1, b8, q


def main() -> int:
    global N_BITS
    ap = argparse.ArgumentParser()
    ap.add_argument("--kd", nargs="*", type=int,
                    default=[14, 16, 18, 19, 20, 21, 22, 23, 24])
    ap.add_argument("--casos", nargs="*", default=[c for c in CASOS if c != "ideal"])
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--tests", nargs="*", default=["noniid"])
    ap.add_argument("--modos", nargs="*", default=["b1", "b8"])
    ap.add_argument("--n", type=int, default=N_BITS, help="bits por secuencia")
    args = ap.parse_args()
    N_BITS = args.n
    SEC.mkdir(parents=True, exist_ok=True)
    e90.DIR90B = DIR                               # logs y json aqui

    filas = []
    for caso in args.casos:
        for k in args.kd:
            for r in range(1, args.reps + 1):
                b1, b8, q = secuencia(caso, k, r)
                hmin_mod = 1.0 if q == float("inf") else entropias_exactas(q)[1]
                nombre = nombre_de(caso, k, r)
                for modo, fich in (("b1", b1), ("b8", b8)):
                    if modo not in args.modos:
                        continue
                    for test in args.tests:
                        f = e90.ejecutar(nombre, fich, test, modo)
                        f.update({"caso": caso, "kd_exp": k, "rep": r,
                                  "q_muestra": q, "hmin_modelo": hmin_mod,
                                  "n_bits": N_BITS})
                        filas.append(f)

    if CSV.exists():                               # fusiona: una pasada parcial no borra el resto
        nuevas = {(f["nombre"], f["test"], f["modo"]) for f in filas}
        with CSV.open(encoding="utf-8", newline="") as fh:
            filas = [v for v in csv.DictReader(fh)
                     if (v["nombre"], v["test"], v["modo"]) not in nuevas] + filas
    columnas = []
    for f in filas:
        for c in f:
            if c not in columnas:
                columnas.append(c)
    with CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)
    print(f"\nresumen: {CSV} ({len(filas)} filas)")
    return 0 if all(int(f["exit"]) == 0 for f in filas) else 1   # las viejas vienen como texto


if __name__ == "__main__":
    sys.exit(main())
