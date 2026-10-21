#!/usr/bin/env python3
"""Analisis de firmware/reinicios_paso: ¿el RNG del ESP32 sin ruido avanza
con el reloj o con las lecturas, y cuantos ciclos por paso?

Cada arranque lee "antes" (1024 B), espera un numero fijo de NOP (variante
0: N0; 1: N0 + 2; 2: N0 + 174; 3: N0 + 17400, elegida por el contador de
ciclos al empezar) y lee "despues". Para cada pareja de arranques con el
"antes" identico (el generador estaba en el mismo punto) se mide en cuantas
palabras de 32 bits esta desplazado un "despues" respecto del otro: se busca
el inicio (dos palabras) de uno dentro del otro y se comprueba que el
solape entero coincide.

Predicciones si el generador da un paso por ciclo de APB (2 ciclos de CPU a
160 MHz) desde un estado fijo y las lecturas no lo mueven, con una palabra
de esp_fill_random cada 174 ciclos de CPU:
  misma variante           desplazamiento 0 (bloques identicos)
  0 frente a 2 / 3         desplazamiento 1 / 100 palabras
  0 frente a 1             sin alineacion (otro desfase de 2 ciclos)

    python analysis/reinicios_paso.py --mac f8b3b72a0928

Salida: results/esp32_reinicios/mac_<mac>/paso/resumen.md.
"""
from __future__ import annotations

import argparse
import collections
import csv
import itertools
import sys
from pathlib import Path

import numpy as np

DIR = Path(__file__).resolve().parent.parent / "results" / "esp32_reinicios"
EXTRA = {0: 0, 1: 2, 2: 174, 3: 17400}


def desplazamiento(a: np.ndarray, b: np.ndarray) -> int | None:
    """Palabras que b va por delante de a (b[0] = a[k]); negativo si va
    detras; None si no se alinean con el solape entero identico."""
    n = len(a)
    for k in range(n - 1):
        if a[k] == b[0] and a[k + 1] == b[1] and np.array_equal(a[k:], b[:n - k]):
            return k
    for k in range(1, n - 1):
        if b[k] == a[0] and b[k + 1] == a[1] and np.array_equal(b[k:], a[:n - k]):
            return -k
    return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--mac", default="f8b3b72a0928")
    a = ap.parse_args()
    d = DIR / f"mac_{a.mac}" / "paso"
    filas = list(csv.DictReader((d / "reinicios.csv").open(encoding="utf-8")))
    n = len(filas)
    antes = np.fromfile(d / "reinicios_antes.bin", dtype=np.uint8)[: n * 1024].reshape(n, 1024)
    desp = np.fromfile(d / "reinicios.bin", dtype=np.uint8)[: n * 1024].reshape(n, 1024)
    wa = antes.view("<u4").reshape(n, -1)
    wd = desp.view("<u4").reshape(n, -1)
    var = np.array([int(f["var"]) for f in filas])
    c_r = np.array([int(f["c_r"]) for f in filas])
    c_a = np.array([int(f["c_a"]) for f in filas])
    c_d = np.array([int(f["c_d"]) for f in filas])

    lin = [f"# Paso del RNG sin ruido, chip {a.mac}", "",
           "Generado por analysis/reinicios_paso.py. Cada arranque: \"antes\", un retardo de N NOP con las "
           "interrupciones apagadas y \"despues\".", "",
           "| Variante | NOP extra | Arranques | Ciclos del retardo (medidos) | Ciclos de \"antes\" | Ciclos de \"despues\" |",
           "|---|---|---|---|---|---|"]
    for v in range(4):
        s = var == v
        if not s.any():
            continue
        lin.append(f"| {v} | {EXTRA[v]} | {int(s.sum())} | {c_r[s].min()}-{c_r[s].max()} | "
                   f"{c_a[s].min()}-{c_a[s].max()} | {c_d[s].min()}-{c_d[s].max()} |")

    grupos = collections.defaultdict(list)
    for i in range(n):
        grupos[antes[i].tobytes()].append(i)
    res: dict = collections.defaultdict(collections.Counter)
    for g in grupos.values():
        for i, j in itertools.combinations(g, 2):
            vi, vj = int(var[i]), int(var[j])
            if vi > vj:
                i, j, vi, vj = j, i, vj, vi
            k = desplazamiento(wd[i], wd[j])
            res[(vi, vj)]["sin alinear" if k is None else f"{k:+d}"] += 1
    pares = sum(len(g) * (len(g) - 1) // 2 for g in grupos.values())
    lin += ["", f"{n} arranques; {len(grupos)} lecturas \"antes\" distintas; {pares} parejas con el "
            "\"antes\" idéntico. Desplazamiento del \"despues\" de la segunda variante respecto del de la "
            "primera, en palabras de 32 bits:", "",
            "| Variantes | Parejas | Desplazamientos observados | Predicción (paso por ciclo de APB) |",
            "|---|---|---|---|"]
    pred = {(0, 0): "0", (1, 1): "0", (2, 2): "0", (3, 3): "0", (0, 2): "+1", (0, 3): "+100",
            (2, 3): "+99", (0, 1): "sin alinear", (1, 2): "sin alinear", (1, 3): "sin alinear"}
    for clave in sorted(res):
        obs = ", ".join(f"{k}: {c}" for k, c in res[clave].most_common())
        lin.append(f"| {clave[0]} y {clave[1]} | {sum(res[clave].values())} | {obs} | {pred.get(clave, '?')} |")
    lin.append("")
    (d / "resumen.md").write_text("\n".join(lin) + "\n", encoding="utf-8")
    print("\n".join(lin))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
