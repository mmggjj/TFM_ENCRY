#!/usr/bin/env python3
"""Tabla O8: SP 800-90B no-IID en bits, estimador a estimador, para la
fuente en FPGA (Basys 2), el ESP32 y bits ideales del modelo, a 10^6 y a
8 378 368 bits. Solo lee resultados ya calculados; no corre la batería.

    python3 analysis/tabla_o8.py [--salida results/tabla_o8.md]

Sesgo: p̂ del estimador MCV y z = (p̂ - 0,5) / sqrt(0,25 / N).

16-11-2026: seccion a 4 194 304 bits (FPGA con y sin habilitacion en el
biestable de muestreo, docs/basys2.md "Muestreo sin habilitacion") y
cuadro de la prueba de reinicios (SP 800-90B 3.1.4, ea_restart en bit)
de la FPGA y de los dos ESP32, leidos de sus logs.
"""
import argparse
import csv
import json
import math
import re
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
    # 4 194 304 bits: FPGA con CE (referencia regenerada) y sin CE (libre y
    # libre con par -t 7), mismos anillos y biestable colocados.
    j = lambda carpeta, kd: CAMP / carpeta / "entropia90b" / f"kd{kd}_flujo_noniid_b1.json"
    g["ce_4e6"] = [(f"fijo kd{kd}",) + valores_json(j("basys2_fijo_kd13_14_n4194304", kd))
                   for kd in (13, 14)]
    g["libre_4e6"] = [(f"libre kd{kd}",) + valores_json(j("basys2_libre_kd13_14_n4194304", kd))
                      for kd in (13, 14)]
    g["libre_4e6"].append(("libre t7 kd14",) + valores_json(j("basys2_libre_t7_kd14_n4194304", 14)))
    b4 = [r for r in csv.DictReader(open(sc)) if r["n_bits"] == "4194304"] if sc.exists() else []
    g["ideal_4e6"] = [(r["nombre"],) + valores_fila(r) for r in b4 if r["p1"] in ("0.5", "0.5000")]
    g["sesgo_4e6"] = [(r["nombre"],) + valores_fila(r) for r in b4 if r["p1"] == "0.4962"]
    return g


def reinicios():
    """ea_restart en bit: (fuente, variante, H_I, H_r, H_c, veredicto)."""
    filas = []
    log = RES / "fpga_reinicios" / "basys2_kd14" / "ea_restart_b1.log"
    t = log.read_text()
    v = {k: float(re.search(rf"^{k}: ([0-9.]+)", t, re.M).group(1)) for k in ("H_I", "H_r", "H_c")}
    filas.append(("FPGA (Basys 2, kd 14)", "1000 reprogramaciones por JTAG", v["H_I"], v["H_r"],
                  v["H_c"], "pasa" if "Validation Test Passed" in t else "falla"))
    for mac in ("a0dd6c0efb4c", "f8b3b72a0928"):
        t = (RES / "esp32_reinicios" / f"analisis_mac_{mac}.log").read_text(encoding="utf-8-sig")
        for bloque in re.split(r"(?=^--- ea_restart )", t, flags=re.M):
            m = re.match(r"--- ea_restart (\S+) b1 \(H_I", bloque)
            if not m:
                continue
            v = {k: float(re.search(rf"^{k}: ([0-9.]+)", bloque, re.M).group(1))
                 for k in ("H_I", "H_r", "H_c")}
            filas.append((f"ESP32 {mac[:2]}:{mac[2:4]}:..:{mac[-2:]}", m.group(1), v["H_I"],
                          v["H_r"], v["H_c"],
                          "pasa" if "Validation Test Passed" in bloque else "falla"))
    return filas


def rango(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) == 1:
        return f"{xs[0]:.3f}"
    return f"{statistics.median(xs):.3f} ({min(xs):.3f}-{max(xs):.3f})"


def z(p_hat, n):
    return (p_hat - 0.5) / math.sqrt(0.25 / n)


def tabla(g, sufijo, titulo, cols=None):
    cols = cols or [("FPGA", g[f"fpga_{sufijo}"]), ("ESP32", g[f"esp_{sufijo}"]),
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
    lin += ["Con y sin habilitacion (CE) en el biestable que muestrea ro1: mismos",
            "anillos y biestable colocados; kd 13 y 14, y una segunda implementacion",
            "libre (par -t 7) a kd 14. iid p1=0,4962: el sesgo de la libre.", ""]
    lin += tabla(g, "4e6", "4 194 304 bits", [
        ("FPGA con CE", g["ce_4e6"]), ("FPGA sin CE", g["libre_4e6"]),
        ("Ideal", g["ideal_4e6"]), ("iid p1=0,4962", g["sesgo_4e6"])])
    lin += ["### Prueba de reinicios (SP 800-90B 3.1.4, ea_restart en bit, 1000 x 1000)", "",
            "H_I: la entropia no-IID de la fuente con la que se compara. Pasa si",
            "min(H_r, H_c) >= H_I/2 y la comprobacion de cordura pasa. ESP32:",
            "docs/esp32_reinicios.md (sin_ruido = sin el ruido del cargador de arranque).", "",
            "| Fuente | Variante | H_I | H_r | H_c | Veredicto |", "|---|---|---|---|---|---|"]
    lin += [f"| {f} | {v} | {hi:.3f} | {hr:.3f} | {hc:.3f} | {ver} |"
            for f, v, hi, hr, hc, ver in reinicios()]
    lin.append("")
    txt = "\n".join(lin)
    print(txt)
    Path(a.salida).write_text(txt + "\n")


if __name__ == "__main__":
    main()
