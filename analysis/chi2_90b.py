#!/usr/bin/env python3
"""Las dos pruebas chi-cuadrado de la via IID de SP 800-90B (5.2.1 y 5.2.2),
reescritas en numpy siguiendo linea a linea cpp/iid/chi_square_tests.h de
la herramienta del NIST (v1.1.8). Sirve para calibrar: ea_iid tarda minutos
por fichero por las pruebas de permutacion; esto tarda decimas, y permite
ver la distribucion de p sobre miles de ficheros de referencia.

    python analysis/chi2_90b.py --valida            compara con los logs de ea_iid
    python analysis/chi2_90b.py --referencia 10000  p sobre os.urandom
    python analysis/chi2_90b.py --esp32             p de todas las capturas

Modo byte = simbolos de 8 bits tal cual; modo bit = bits desempaquetados
MSB primero, como en entropia_90b.py.
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
from scipy.special import gammaincc

RAIZ = Path(__file__).resolve().parent.parent
DIR90B = RAIZ / "results" / "entropia90b"
SALIDA = RAIZ / "results" / "chi2_90b"
sys.path.insert(0, str(Path(__file__).resolve().parent))


def pvalor(t: float, df: int) -> float:
    return float(gammaincc(df / 2.0, t / 2.0)) if df > 0 else 1.0


def _bins(esper: np.ndarray, clave: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """allocate_bins(): orden por (esperanza, tupla), se acumula hasta >= 5."""
    orden = np.lexsort((clave, esper))
    bin_de = np.empty(len(esper), dtype=np.int64)
    bin_exp: list[float] = []
    actual, acum = 0, 0.0
    for idx in orden:
        if acum >= 5.0:
            bin_exp.append(acum)
            actual += 1
            acum = 0.0
        bin_de[idx] = actual
        acum += esper[idx]
    if actual != 0 and acum < 5.0:
        bin_de[bin_de == actual] = actual - 1
        bin_exp[actual - 1] += acum
    else:
        bin_exp.append(acum)
    return bin_de, np.array(bin_exp)


def _alfabeto(datos: np.ndarray) -> tuple[np.ndarray, int]:
    # la herramienta traduce los simbolos presentes a 0..k-1
    vals, inv = np.unique(datos, return_inverse=True)
    return inv.astype(np.int64), len(vals)


def independencia(datos: np.ndarray) -> tuple[float, int, float]:
    d, k = _alfabeto(datos)
    n = len(d)
    if k == 2:
        p1 = d.mean()
        p0 = 1.0 - p1
        m = 11
        while m > 1 and not (min(p0, p1) ** m * (n // m) >= 5):
            m -= 1
        if m < 2:
            return 0.0, 0, 1.0
        nb = n // m
        sim = d[: nb * m].reshape(nb, m) @ (1 << np.arange(m - 1, -1, -1))
        occ = np.bincount(sim, minlength=1 << m)
        w = np.array([bin(i).count("1") for i in range(1 << m)])
        e = p1 ** w * p0 ** (m - w) * nb
        t = float(((occ - e) ** 2 / e).sum())
        df = 2 ** m - 2
        return t, df, pvalor(t, df)
    p = np.bincount(d, minlength=k) / n
    tupla = np.arange(k * k)
    esper = np.outer(p, p).ravel() * math.floor(n * 0.5)
    bin_de, bin_exp = _bins(esper, tupla)
    pares = d[0:n - 1:2] * k + d[1:n:2]
    o = np.bincount(bin_de[pares], minlength=len(bin_exp))
    t = float(((o - bin_exp) ** 2 / bin_exp).sum())
    df = len(bin_exp) - k
    return t, df, pvalor(t, df)


def ajuste(datos: np.ndarray) -> tuple[float, int, float]:
    d, k = _alfabeto(datos)
    n = len(d)
    if k == 2:
        sub = n // 10
        p = d.sum() / n
        e0, e1 = (1 - p) * sub, p * sub
        unos = d[: 10 * sub].reshape(10, sub).sum(axis=1)
        t = float((((sub - unos) - e0) ** 2 / e0 + (unos - e1) ** 2 / e1).sum())
        return t, 9, pvalor(t, 9)
    p = np.bincount(d, minlength=k) / n
    esper = p * math.floor(n / 10.0)
    bin_de, bin_exp = _bins(esper, np.arange(k))
    bloque = n // 10
    t = 0.0
    for j in range(10):
        o = np.bincount(bin_de[d[j * bloque:(j + 1) * bloque]], minlength=len(bin_exp))
        t += float(((o - bin_exp) ** 2 / bin_exp).sum())
    df = 9 * (len(bin_exp) - 1)
    return t, df, pvalor(t, df)


def leer(ruta: Path, modo: str) -> np.ndarray:
    b = np.frombuffer(ruta.read_bytes(), dtype=np.uint8)
    if ruta.suffix == ".bits" or modo == "b8":
        return b
    return np.unpackbits(b)


def valida() -> int:
    """Reproduce los p de los logs de ea_iid (6 decimales) en todas las capturas."""
    from entropia_90b import FUENTES
    peor = 0.0
    for nombre, ruta in FUENTES.items():
        for modo in ("b1", "b8"):
            log = DIR90B / f"{nombre}_iid_{modo}.log"
            if not log.exists() or not ruta.exists():
                continue
            ref = [float(x) for x in re.findall(r"p-value = ([0-9.eE+-]+)",
                                                 log.read_text(encoding="utf-8"))]
            d = leer(ruta, modo)
            mio = [independencia(d)[2], ajuste(d)[2]]
            dif = max(abs(a - b) for a, b in zip(ref, mio))
            peor = max(peor, dif)
            print(f"{nombre:18s} {modo}  NIST {ref[0]:.6f} {ref[1]:.6f}   aqui {mio[0]:.6f} {mio[1]:.6f}"
                  f"   {'OK' if dif < 6e-7 else 'DISTINTO'}")
    print(f"diferencia maxima {peor:.2e} (los logs redondean a 1e-6)")
    return 0 if peor < 6e-7 else 1


def _uno_urandom(args: tuple[int, int]) -> list:
    i, nbytes = args
    b = np.frombuffer(os.urandom(nbytes), dtype=np.uint8)
    u = np.unpackbits(b)
    return [i, independencia(b)[2], ajuste(b)[2], independencia(u)[2], ajuste(u)[2]]


def referencia(n_fich: int, nbytes: int) -> int:
    from multiprocessing import Pool
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / f"referencia_urandom_{n_fich}x{nbytes}.csv"
    with Pool() as pool, ruta.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["i", "b8_indep", "b8_ajuste", "b1_indep", "b1_ajuste"])
        for fila in pool.imap_unordered(_uno_urandom, [(i, nbytes) for i in range(n_fich)], chunksize=20):
            w.writerow(fila)
    resumen(ruta)
    return 0


def resumen(ruta: Path) -> None:
    filas = list(csv.DictReader(ruta.open(encoding="utf-8")))
    from scipy.stats import kstest
    print(f"{ruta.name}: {len(filas)} ficheros")
    for col in ("b8_indep", "b8_ajuste", "b1_indep", "b1_ajuste"):
        v = np.array([float(f[col]) for f in filas])
        print(f"  {col:10s} p<0,05: {(v < 0.05).mean() * 100:5.2f} %  p<0,01: {(v < 0.01).mean() * 100:5.2f} %"
              f"  p<0,001: {(v < 0.001).mean() * 100:5.3f} %  mediana {np.median(v):.3f}"
              f"  KS frente a uniforme p = {kstest(v, 'uniform').pvalue:.3g}")


def esp32() -> int:
    from entropia_90b import FUENTES
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / "esp32.csv"
    with ruta.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["nombre", "b8_indep", "b8_ajuste", "b1_indep", "b1_ajuste"])
        for nombre, r in FUENTES.items():
            if not r.exists():
                continue
            b = np.frombuffer(r.read_bytes(), dtype=np.uint8)
            u = np.unpackbits(b)
            fila = [nombre, independencia(b)[2], ajuste(b)[2], independencia(u)[2], ajuste(u)[2]]
            w.writerow(fila)
            print("  ".join([f"{fila[0]:18s}"] + [f"{x:.6f}" for x in fila[1:]]))
    return 0


def chip(n: str) -> str | None:
    # misma asignacion que resumen_90b.py
    if n.startswith("fb4c_"):
        return "a0:dd:6c:0e:fb:4c"
    m = re.fullmatch(r"cond[A-D]_rep(\d+)", n)
    if not m:
        return None
    return "ec:e3:34:9a:d1:18"   # rep1 (agosto) tambien: ver resumen_90b.py


def compara(ruta_ref: Path) -> int:
    """p del ESP32 (capturas A-D, 125 000 B) frente a la distribucion de
    referencia del mismo tamano: tasa de fallo (p < 0,001) esperada y
    Mann-Whitney unilateral (p del ESP32 mas bajos que los de referencia)."""
    from scipy.stats import binom, mannwhitneyu
    ref = list(csv.DictReader(ruta_ref.open(encoding="utf-8")))
    esp = [f for f in csv.DictReader((SALIDA / "esp32.csv").open(encoding="utf-8")) if chip(f["nombre"])]
    grupos: dict[str, list] = {"todas A-D": esp}
    for f in esp:
        grupos.setdefault(chip(f["nombre"]), []).append(f)
    print(f"referencia {ruta_ref.name} ({len(ref)} ficheros)")
    for col in ("b8_indep", "b8_ajuste", "b1_indep", "b1_ajuste"):
        r = np.array([float(f[col]) for f in ref])
        tasa = (r < 0.001).mean()
        print(f"\n{col}: en referencia p<0,05 {(r < 0.05).mean() * 100:.2f} %, p<0,001 {tasa * 100:.3f} %")
        for g, filas in grupos.items():
            v = np.array([float(f[col]) for f in filas])
            k = int((v < 0.001).sum())
            pk = binom.sf(k - 1, len(v), tasa) if k else 1.0
            mw = mannwhitneyu(v, r, alternative="less").pvalue
            print(f"  {g:24s} n={len(v):2d}  p<0,05: {(v < 0.05).sum():2d} (esperados {len(v) * (r < 0.05).mean():4.1f})"
                  f"  p<0,001: {k} (esperados {len(v) * tasa:.2f}, P(>= {k}) = {pk:.3g})"
                  f"  Mann-Whitney p = {mw:.3g}  mediana {np.median(v):.3f} (ref. {np.median(r):.3f})")
    return 0


def _indep_urandom(nbytes: int) -> float:
    return independencia(np.frombuffer(os.urandom(nbytes), dtype=np.uint8))[2]


def agrupa(n_ref: int) -> int:
    """Independencia en modo byte sobre las capturas A-D de cada chip
    concatenadas (mas pares, mas potencia), con desfase 0 (bytes 0-1 y 2-3 de
    cada palabra de 32 bits) y 1 (bytes 1-2 y 3-0'). Como el p de la
    herramienta no es uniforme, se compara con n_ref ficheros os.urandom del
    mismo tamano: p empirico = (1 + #(p_ref <= p_obs)) / (n_ref + 1)."""
    from multiprocessing import Pool
    from entropia_90b import FUENTES
    grupos: dict[str, list[bytes]] = {}
    for nombre, r in FUENTES.items():
        g = chip(nombre)
        if g and r.exists():
            grupos.setdefault(g, []).append(r.read_bytes())
    filas = []
    with Pool() as pool:
        for g, trozos in grupos.items():
            d = np.frombuffer(b"".join(trozos), dtype=np.uint8)
            for desf in (0, 1):
                x = d[desf:]
                x = x[: 2 * (len(x) // 2)]
                p_obs = independencia(x)[2]
                ref = np.array(pool.map(_indep_urandom, [len(x)] * n_ref, chunksize=10))
                p_emp = (1 + (ref <= p_obs).sum()) / (n_ref + 1)
                filas.append([g, len(trozos), len(x), desf, p_obs, p_emp, np.median(ref), (ref < 0.001).mean()])
                print(f"{g:24s} {len(trozos):2d} capturas, {len(x):8d} B, desfase {desf}: p herramienta {p_obs:.4g}"
                      f"  p empirico {p_emp:.4g}  (referencia: mediana {np.median(ref):.3f},"
                      f" p<0,001 en {(ref < 0.001).mean() * 100:.1f} %)")
    with (SALIDA / f"agrupado_{n_ref}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["chip", "capturas", "bytes", "desfase", "p_herramienta", "p_empirico",
                    "mediana_ref", "frac_ref_p<0.001"])
        w.writerows(filas)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agrupa", type=int, default=0, help="ficheros de referencia por tamano")
    ap.add_argument("--valida", action="store_true")
    ap.add_argument("--referencia", type=int, default=0)
    ap.add_argument("--bytes", type=int, default=125000)
    ap.add_argument("--esp32", action="store_true")
    ap.add_argument("--compara", default="", help="CSV de referencia contra el que comparar esp32.csv")
    a = ap.parse_args()
    if a.valida:
        return valida()
    if a.referencia:
        return referencia(a.referencia, a.bytes)
    if a.esp32:
        return esp32()
    if a.compara:
        return compara(Path(a.compara))
    if a.agrupa:
        return agrupa(a.agrupa)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
