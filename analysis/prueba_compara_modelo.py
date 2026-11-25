#!/usr/bin/env python3
"""Prueba de compara_modelo_campana.py con una campana simulada de Q conocida.

Genera lo que daria campana_motor.py: por divisor, 245 trozos de 4096 bits
del modelo del ERO (fase independiente por trozo, como el buffer de
captura) con Q = 2^kd * Q_raw, y un kd00.bin para medir Q_raw; los pasa por
la bateria SP 800-90B (ea_non_iid, bits) y escribe resumen.csv. Despues
comprueba:
  1. que jitter_estimator recupera Q_raw a menos del 10 %;
  2. con la Q_raw verdadera, ningun divisor sale "por debajo"/"por encima";
  3. diciendo que hay 4 veces mas jitter del que hay (Q_raw x 4), los
     divisores con poca entropia salen "por debajo";
  4. diciendo que hay 4 veces menos, salen "por encima".

    ~/eda/venv/bin/python analysis/prueba_compara_modelo.py [--carpeta DIR]
"""
from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entropia_90b as e90                            # noqa: E402
import compara_modelo_campana as cmc                  # noqa: E402
from ero_model import simular_bits                    # noqa: E402
from jitter_estimator import desde_capturas           # noqa: E402

Q_RAW = 2.4e-7            # por periodo de ro2: CFG_KD 20 da Q ~ 0,25
KDS = [17, 18, 19, 20, 21]
TROZOS = 245
BITS = 4096


def trozos(q, n, semilla):
    rng = np.random.default_rng(semilla)
    filas = [simular_bits(BITS, q, semilla=int(rng.integers(1 << 31)), phi0=rng.random())
             for _ in range(n)]
    return np.packbits(np.array(filas, dtype=np.uint8).ravel()).tobytes()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--carpeta", type=Path, default=None)
    a = ap.parse_args()
    carpeta = a.carpeta or Path(tempfile.mkdtemp(prefix="prueba_compara_"))
    carpeta.mkdir(parents=True, exist_ok=True)
    e90.DIR90B = carpeta / "entropia90b"
    e90.BITS = e90.DIR90B / "bits"
    e90.BITS.mkdir(parents=True, exist_ok=True)
    fallos = 0

    def chk(c, m):
        nonlocal fallos
        print(f"  [{'ok ' if c else 'FALLO'}] {m}")
        fallos += not c

    print(f"campana simulada en {carpeta}, Q_raw = {Q_RAW:.2e}")
    (carpeta / "kd00.bin").write_bytes(trozos(Q_RAW, 3000, 1))
    filas = []
    for kd in KDS:
        nombre = f"kd{kd:02d}"
        fich = carpeta / f"{nombre}.bin"
        fich.write_bytes(trozos(Q_RAW * 2 ** kd, TROZOS, 100 + kd))
        r = e90.ejecutar(nombre, e90.desempaquetar(nombre, fich), "noniid", "b1")
        h = next(v for k, v in r.items() if k.endswith("hAssessed"))
        filas.append({"kd": kd, "bits": TROZOS * BITS, "h_min_90b": h, "exit_90b": r["exit"]})
    with (carpeta / "resumen.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    print("\n1) Q_raw medido con jitter_estimator")
    r = desde_capturas(str(carpeta / "kd00.bin"), 0)
    err = r["q_por_periodo"] / Q_RAW - 1
    chk(abs(err) < 0.10, f"Q_raw {r['q_por_periodo']:.3e} frente a {Q_RAW:.3e} ({100 * err:+.1f} %)")

    print("\n2) Con la Q_raw medida")
    rc = cmc.main(["--campana", str(carpeta), "--jitter", str(carpeta / "kd00.bin")])
    v = [s["veredicto"] for s in csv.DictReader((carpeta / "compara_modelo.csv").open())]
    chk(rc == 0 and not ({"por debajo", "por encima"} & set(v)), f"veredictos {v}")
    informativos = [x for x in v if x == "compatible"]
    chk(len(informativos) >= 3, f"{len(informativos)} divisores por debajo de la saturacion")

    print("\n3) Diciendo 4 veces mas jitter del real")
    rc = cmc.main(["--campana", str(carpeta), "--q-raw", str(4 * Q_RAW)])
    v = [s["veredicto"] for s in csv.DictReader((carpeta / "compara_modelo.csv").open())]
    chk(rc == 1 and "por debajo" in v, f"veredictos {v}")

    print("\n4) Diciendo 4 veces menos")
    rc = cmc.main(["--campana", str(carpeta), "--q-raw", str(Q_RAW / 4)])
    v = [s["veredicto"] for s in csv.DictReader((carpeta / "compara_modelo.csv").open())]
    chk(rc == 1 and "por encima" in v, f"veredictos {v}")

    # deja la figura y la tabla del caso bueno
    cmc.main(["--campana", str(carpeta), "--jitter", str(carpeta / "kd00.bin")])
    print(f"\nprueba_compara_modelo: {fallos} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
