#!/usr/bin/env python3
"""Tabla O8: SP 800-90B no-IID en bits, estimador a estimador, para la
fuente en FPGA (Basys 2), el ESP32 y bits ideales del modelo, a 10^6 y a
8 378 368 bits. Solo lee resultados ya calculados; no corre la batería.

    python3 analysis/tabla_o8.py [--salida results/tabla_o8.md]

Sesgo: p̂ del estimador MCV y z = (p̂ - 0,5) / sqrt(0,25 / N).
"""
import argparse
import csv
import json
import math
import statistics
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "results"
CAMP = RES / "motor_campana"

ESTIM = ["MCV", "Colisión", "Markov", "Compresión", "t-Tuple", "LRS",
         "MultiMCW", "Lag", "MultiMMC", "LZ78Y"]


def valores_json(p):
    d = json.load(open(p))
    tc = d["testCases"]
    v = []
    for t in tc[:10]:
        v.append(t.get("hOriginal", t.get("tTupleRes", t.get("lrsRes"))))
    p_hat = tc[0]["mcvEstimatePHat"]
    n = round(tc[0]["mcvEstimateMode"] / p_hat)
    return v, tc[10]["hAssessed"], p_hat, n


def valores_fila(r):
    v = []
    for i in range(10):
        for c in ("hOriginal", "tTupleRes", "lrsRes", "hBitstring"):
            x = r.get(f"testCases.{i}.{c}", "")
            if x:
                v.append(float(x))
                break
        else:
            v.append(None)
    p_hat = float(r["testCases.0.mcvEstimatePHat"])
    n = round(float(r["testCases.0.mcvEstimateMode"]) / p_hat)
    return v, float(r["testCases.10.hAssessed"]), p_hat, n


def grupo(nombre, filas):
    return {"nombre": nombre, "filas": filas}


def cargar():
    g = {}
    # FPGA
    fpga1 = []
    for kd in (13, 14, 15, 16):
        p = CAMP / "basys2_campana_90b_kd12_16/entropia90b" / f"kd{kd}_flujo_noniid_b1.json"
        fpga1.append((f"kd{kd}",) + valores_json(p))
    g["fpga_1e6"] = fpga1
    p = CAMP / "basys2_larga_kd14_n8378368/entropia90b/kd14_flujo_noniid_b1.json"
    g["fpga_8e6"] = [("kd14",) + valores_json(p)]
    # ESP32: las 36 de los ANOVA (tres chips, A-D, tres repeticiones)
    e = [r for r in csv.DictReader(open(RES / "entropia_90b.csv"))
         if r["test"] == "noniid" and r["modo"] == "b1"]
    anova = [r for r in e if r["nombre"].split("_")[0] in ("condA", "condB", "condC", "condD", "fb4c", "0928")]
    g["esp_1e6"] = [(r["nombre"],) + valores_fila(r) for r in anova]
    g["esp_8e6"] = [(r["nombre"],) + valores_fila(r) for r in e if r["nombre"] == "esp_rf_off_2"]
    # Ideal (bits uniformes, tres semillas)
    s = [r for r in csv.DictReader(open(RES / "fuente_simulada_90b.csv"))
         if r["caso"] == "ideal" and r["test"] == "noniid" and r["modo"] == "b1"]
    g["ideal_1e6"] = [(r["nombre"],) + valores_fila(r) for r in s if not r.get("n_bits")]
    g["ideal_8e6"] = [(r["nombre"],) + valores_fila(r) for r in s if r.get("n_bits") == "8378368"]
    # Bits independientes con el sesgo de la FPGA (analysis/sesgo_90b.py)
    sc = RES / "sesgo_90b" / "sesgo_90b.csv"
    b = [r for r in csv.DictReader(open(sc)) if r["p1"] == "0.4979"] if sc.exists() else []
    g["sesgo_1e6"] = [(r["nombre"],) + valores_fila(r) for r in b if r["n_bits"] == "1000000"]
    g["sesgo_8e6"] = [(r["nombre"],) + valores_fila(r) for r in b if r["n_bits"] == "8378368"]
    return g


def rango(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) == 1:
        return f"{xs[0]:.3f}"
    return f"{statistics.median(xs):.3f} ({min(xs):.3f}-{max(xs):.3f})"


def z(p_hat, n):
    return (p_hat - 0.5) / math.sqrt(0.25 / n)


def tabla(g, sufijo, titulo):
    cols = [("FPGA", g[f"fpga_{sufijo}"]), ("ESP32", g[f"esp_{sufijo}"]),
            ("Ideal", g[f"ideal_{sufijo}"]), ("iid p1=0,4979", g[f"sesgo_{sufijo}"])]
    out = [f"### {titulo}", "",
           "| Estimador | " + " | ".join(f"{c} (n={len(f)})" for c, f in cols) + " |",
           "|---|" + "---|" * len(cols)]
    for i, nom in enumerate(ESTIM):
        out.append(f"| {nom} | " + " | ".join(rango([f[1][i] for f in fs]) for _, fs in cols) + " |")
    out.append("| **Mínimo (H asignada)** | " + " | ".join(rango([f[2] for f in fs]) for _, fs in cols) + " |")
    out.append("| p̂ del MCV | " + " | ".join(rango([f[3] for f in fs]) for _, fs in cols) + " |")
    out.append("| z del sesgo | " + " | ".join(
        rango([z(f[3], f[4]) for f in fs]) for _, fs in cols) + " |")
    out.append("| N (bits) | " + " | ".join(
        ", ".join(sorted({str(f[4]) for f in fs})) for _, fs in cols) + " |")
    out.append("")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(RES / "tabla_o8.md"))
    a = ap.parse_args()
    g = cargar()
    lin = ["# Tabla O8: SP 800-90B no-IID en bits (generado por analysis/tabla_o8.py)", "",
           "Mediana (mínimo-máximo) entre secuencias. FPGA: Basys 2, variante sin",
           "display ni medidor, flujo consecutivo, kd 13-16 a 10^6 (kd 12 fuera: por",
           "debajo de K*) y kd 14 a 8 378 368. ESP32: las 36 capturas de los ANOVA",
           "(tres chips, condiciones A-D) y esp_rf_off_2. Ideal: bits uniformes,",
           "tres semillas. iid p1=0,4979: bits independientes con el sesgo de la",
           "FPGA y nada más (analysis/sesgo_90b.py), tres semillas.", ""]
    lin += tabla(g, "1e6", "10^6 bits")
    lin += tabla(g, "8e6", "8 378 368 bits")
    txt = "\n".join(lin)
    print(txt)
    Path(a.salida).write_text(txt + "\n")


if __name__ == "__main__":
    main()
