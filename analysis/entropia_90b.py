#!/usr/bin/env python3
"""Estimadores de min-entropia SP 800-90B (herramienta oficial del NIST) sobre
capturas del ESP32 y, cuando lleguen, del motor.

Envuelve `ea_non_iid` y `ea_iid` de usnistgov/SP800-90B_EntropyAssessment
compilados en WSL (receta en docs/plataforma_y_flujo.md). La herramienta
espera un simbolo por byte, con el simbolo en los `bits` bajos: en modo
binario hay que desempaquetar antes (MSB primero), y eso se hace aqui.

    python analysis/entropia_90b.py                    todo (5 capturas, b1 y b8, no-IID e IID)
    python analysis/entropia_90b.py --solo condD_rep1  una captura
    python analysis/entropia_90b.py --modos b1         solo binario

Salidas, sin filtrar: results/entropia90b/<nombre>_<test>_<modo>.{log,json}
y el resumen results/entropia_90b.csv (una fila por ejecucion, todos los
campos numericos del JSON). Las cifras se interpretan en
docs/esp32_linea_base_90b.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "results"
DIR90B = RES / "entropia90b"
BITS = DIR90B / "bits"
CSV = RES / "entropia_90b.csv"
HERRAMIENTA = "~/SP800-90B_EntropyAssessment/cpp"   # en WSL o en Linux

AGOSTO = RES / "esp32_rng_agosto"
FUENTES = {
    # primera campana (2026-08-04, ESP32-D0WD, esp_fill_random, firmware/esp32_rng):
    # A = WiFi+ADC, B = WiFi, C = ADC, D = nada (RF apagada)
    "condA_rep1": AGOSTO / "condA_rep1.bin",
    "condB_rep1": AGOSTO / "condB_rep1.bin",
    "condC_rep1": AGOSTO / "condC_rep1.bin",
    "condD_rep1": AGOSTO / "condD_rep1.bin",
    # verificador de este TFM, 2026-09-19, sin radio (equivale a D);
    # _1 se corto a los 400 s (440.384 B), _2 es la captura completa de 1 MB
    "esp_rf_off_1": RES / "esp32_tramas_E_esp_rf_off_1.bin",
    "esp_rf_off_2": RES / "esp32_tramas_E_esp_rf_off_2.bin",
    # segunda campana con el mismo firmware (firmware/esp32_rng, 2026-09-19):
    # dos ciclos D->C->B->A seguidos; rep2 y rep3 de cada condicion
    **{f"cond{c}_rep{r}": RES / "esp32_campana_rng" / f"cond{c}_rep{r}.bin"
       for c in "ABCD" for r in (2, 3)},
    # mismo firmware y protocolo en el chip de MAC a0:dd:6c:0e:fb:4c
    # (2026-10-12); los de arriba (rep1 de agosto, rep2 y rep3) son del chip
    # ec:e3:34:9a:d1:18
    **{f"fb4c_cond{c}_rep{r}": RES / "esp32_campana_rng" / "mac_a0dd6c0efb4c" / f"cond{c}_rep{r}.bin"
       for c in "ABCD" for r in (1, 2, 3)},
    # y en el chip de MAC f8:b3:b7:2a:09:28 (2026-10-20)
    **{f"0928_cond{c}_rep{r}": RES / "esp32_campana_rng" / "mac_f8b3b72a0928" / f"cond{c}_rep{r}.bin"
       for c in "ABCD" for r in (1, 2, 3)},
    # segunda tanda del mismo chip (2026-10-21), fuera de los ANOVA (12 + 12 + 12)
    **{f"0928t2_cond{c}_rep{r}": RES / "esp32_campana_rng" / "mac_f8b3b72a0928" / "tanda2" / f"cond{c}_rep{r}.bin"
       for c in "ABCD" for r in (1, 2, 3)},
}


def a_wsl(p: Path) -> str:
    p = p.resolve()
    if sys.platform != "win32":
        return p.as_posix()
    return "/mnt/" + p.drive[0].lower() + p.as_posix()[2:]


def bash(orden: str) -> list[str]:
    """Orden de bash en WSL (Windows) o directamente (Linux)."""
    if sys.platform == "win32":
        return ["wsl.exe", "-e", "bash", "-lc", orden]
    return ["bash", "-lc", orden]


def desempaquetar(nombre: str, origen: Path) -> Path:
    destino = BITS / f"{nombre}.bits"
    if not destino.exists() or destino.stat().st_mtime < origen.stat().st_mtime:
        bits = np.unpackbits(np.frombuffer(origen.read_bytes(), dtype=np.uint8))
        destino.write_bytes(bits.tobytes())
    return destino


def aplanar(obj, prefijo="", salida=None):
    salida = {} if salida is None else salida
    if isinstance(obj, dict):
        for k, v in obj.items():
            aplanar(v, f"{prefijo}{k}.", salida)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            aplanar(v, f"{prefijo}{i}.", salida)
    elif isinstance(obj, (int, float, bool)) or obj is None:
        salida[prefijo.rstrip(".")] = obj
    elif isinstance(obj, str) and len(obj) < 80:
        salida[prefijo.rstrip(".")] = obj
    return salida


def ejecutar(nombre: str, fichero: Path, test: str, modo: str) -> dict:
    etiqueta = f"{nombre}_{test}_{modo}"
    log = DIR90B / f"{etiqueta}.log"
    js = DIR90B / f"{etiqueta}.json"
    bits = 1 if modo == "b1" else 8
    binario = "ea_non_iid" if test == "noniid" else "ea_iid"
    orden = (f"cd {HERRAMIENTA} && /usr/bin/time -f 'tiempo_s=%e maxrss_kB=%M' "
             f"./{binario} -i -a -v -o {a_wsl(js)} {a_wsl(fichero)} {bits}")
    t0 = time.time()
    r = subprocess.run(bash(orden),
                       capture_output=True, text=True, timeout=4 * 3600)
    texto = r.stdout + r.stderr
    log.write_text(texto, encoding="utf-8")
    print(f"--- {etiqueta}: exit {r.returncode}, {time.time() - t0:.0f} s ---")
    print(texto.rstrip())
    fila = {"nombre": nombre, "test": test, "modo": modo, "bits_por_simbolo": bits,
            "fichero": fichero.name, "exit": r.returncode}
    if js.exists():
        fila.update(aplanar(json.loads(js.read_text(encoding="utf-8"))))
    return fila


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", nargs="*", default=list(FUENTES))
    ap.add_argument("--modos", nargs="*", default=["b8", "b1"])
    ap.add_argument("--tests", nargs="*", default=["noniid", "iid"])
    args = ap.parse_args()
    DIR90B.mkdir(exist_ok=True)
    BITS.mkdir(exist_ok=True)

    filas = []
    for nombre in args.solo:
        origen = FUENTES[nombre]
        if not origen.exists():
            print(f"{nombre}: no existe {origen}")
            continue
        for modo in args.modos:
            fichero = desempaquetar(nombre, origen) if modo == "b1" else origen
            for test in args.tests:
                filas.append(ejecutar(nombre, fichero, test, modo))

    if not filas:
        return 1
    # Se fusiona con el CSV existente (clave nombre/test/modo): un --solo no
    # debe borrar los resultados de las demas capturas.
    if CSV.exists():
        nuevas = {(f["nombre"], f["test"], f["modo"]) for f in filas}
        with CSV.open(encoding="utf-8", newline="") as fh:
            viejas = [v for v in csv.DictReader(fh)
                      if (v["nombre"], v["test"], v["modo"]) not in nuevas]
        filas = viejas + filas
    columnas = []
    for f in filas:
        for k in f:
            if k not in columnas:
                columnas.append(k)
    with CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)
    print(f"\nresumen: {CSV} ({len(filas)} filas, {len(columnas)} columnas)")
    return 0 if all(int(f["exit"]) == 0 for f in filas) else 1   # las filas viejas vienen del CSV como texto


if __name__ == "__main__":
    sys.exit(main())
