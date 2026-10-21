#!/usr/bin/env python3
"""Analisis de segundo nivel de SP 800-22 (Rev. 1a, 4.2) sobre todas las
secuencias del ESP32 de 10^6 bits.

Con una secuencia por condicion (primera campana) solo cabe mirar si cada
prueba pasa. Con varias decenas, la norma pide dos cosas por estadistico:
la proporcion de secuencias que pasan a alfa = 0,01 debe caer en
p_hat +- 3 sqrt(p_hat (1 - p_hat) / m), con p_hat = 0,99; y las p deben ser
uniformes (chi-cuadrado sobre 10 intervalos, P-value_T = igamc(9/2, chi2/2)
>= 1e-4), para lo que pide al menos 55 secuencias.

Secuencias: las capturas A-D de entropia_90b.FUENTES (125 000 B cada una) y
las dos largas sin radio cortadas en trozos de 125 000 B (los restos se
descartan); ademas, si existen, las de una segunda tanda del tercer chip
(results/esp32_campana_rng/mac_f8b3b72a0928/tanda2/cond?_rep?.bin).

Estadisticos: cada p de la implementacion propia
(analysis/esp32_rng/nist_sp800_22.py) por separado, como en el informe final
de la herramienta del NIST: las 8 plantillas no solapadas, las dos p de
Serial, las dos de Cumulative Sums, los 8 estados de Random Excursions y los
18 de la variante. Las de Random Excursions solo cuentan en las secuencias
con J >= 500 ciclos (la norma las da por no aplicables si no).

    python analysis/nist_segundo_nivel.py

Salidas: results/nist_segundo_nivel/pvalores.csv (una fila por secuencia y
estadistico) y resumen.md.
"""
from __future__ import annotations

import csv
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.special import gammaincc

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI / "esp32_rng"))
from entropia_90b import FUENTES, RES  # noqa: E402
import nist_sp800_22 as nist  # noqa: E402

SALIDA = RES / "nist_segundo_nivel"
TAM = 125_000
ALFA = 0.01


def secuencias() -> list[tuple[str, str, Path, int]]:
    """(nombre, chip, fichero, desplazamiento) de cada secuencia de 125 000 B."""
    from chi2_90b import chip
    out = []
    for nombre, ruta in FUENTES.items():
        if not ruta.exists():
            continue
        if nombre.startswith("esp_rf_off"):
            n = ruta.stat().st_size // TAM
            out += [(f"{nombre}_t{k + 1}", "ec:e3:34:9a:d1:18", ruta, k * TAM) for k in range(n)]
        elif chip(nombre):
            out.append((nombre, chip(nombre), ruta, 0))
    for ruta in sorted((RES / "esp32_campana_rng" / "mac_f8b3b72a0928" / "tanda2").glob("cond?_rep?.bin")):
        out.append((f"0928t2_{ruta.stem}", "f8:b3:b7:2a:09:28", ruta, 0))
    return out


def estadisticos(r: nist.TestResult) -> list[tuple[str, float | None]]:
    """Las p de una prueba por separado; None si la norma no la aplica."""
    d = r.detail
    if "note" in d or "error" in d:
        n = {"Random Excursions": 8, "Random Excursions Variant": 18}.get(r.name, 1)
        return [(f"{r.name} {k + 1}" if n > 1 else r.name, None) for k in range(n)]
    if r.name.startswith("Non-overlapping"):
        return [(f"{r.name} {k + 1}", p) for k, p in enumerate(d["p_values"])]
    if r.name == "Serial":
        return [("Serial 1", d["p1"]), ("Serial 2", d["p2"])]
    if r.name == "Cumulative Sums":
        return [("Cumulative Sums fwd", d["p_forward"]), ("Cumulative Sums bwd", d["p_backward"])]
    if r.name.startswith("Random Excursions"):
        return [(f"{r.name} {k + 1}", p) for k, p in enumerate(d["p_values"])]
    return [(r.name, r.p_value)]


def una(arg):
    nombre, chipm, ruta, desp = arg
    with open(ruta, "rb") as f:
        f.seek(desp)
        datos = f.read(TAM)
    t0 = time.time()
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        res = nist.run_all_nist_tests(datos, nombre)
    filas = [(nombre, chipm, r.name, est, p) for r in res for est, p in estadisticos(r)]
    return filas, time.time() - t0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    SALIDA.mkdir(parents=True, exist_ok=True)
    seqs = secuencias()
    print(f"{len(seqs)} secuencias de {TAM} B")
    filas = []
    with Pool() as pool:
        for k, (f, t) in enumerate(pool.imap(una, seqs), 1):
            filas += f
            print(f"  {k}/{len(seqs)} {f[0][0]}: {t:.0f} s", flush=True)
    with (SALIDA / "pvalores.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["secuencia", "chip", "prueba", "estadistico", "p"])
        w.writerows([(a, b, c, d, "" if p is None else f"{p:.6f}") for a, b, c, d, p in filas])

    por_est: dict[str, list[float]] = {}
    no_aplica: dict[str, int] = {}
    for _, _, _, est, p in filas:
        por_est.setdefault(est, [])
        if p is None:
            no_aplica[est] = no_aplica.get(est, 0) + 1
        else:
            por_est[est].append(p)
    lin = ["# SP 800-22, análisis de segundo nivel (§4.2)", "",
           f"Generado por analysis/nist_segundo_nivel.py. {len(seqs)} secuencias de 10^6 bits; "
           "α = 0,01; proporción aceptable p̂ ± 3·√(p̂(1−p̂)/m) con p̂ = 0,99; uniformidad: χ² sobre 10 "
           "intervalos, P-value_T ≥ 10⁻⁴ (la norma pide m ≥ 55).", "",
           "| Estadístico | m | Pasan | Proporción | Mínimo aceptable | P-value_T | Veredicto |",
           "|---|---|---|---|---|---|---|"]
    malos = []
    for est, ps in por_est.items():
        m = len(ps)
        if m == 0:
            lin.append(f"| {est} | 0 | — | — | — | — | no aplicable en ninguna |")
            continue
        ps = np.array(ps)
        pasan = int((ps >= ALFA).sum())
        minimo = (1 - ALFA) - 3 * np.sqrt(ALFA * (1 - ALFA) / m)
        F = np.histogram(ps, bins=10, range=(0, 1))[0]
        chi2 = float(((F - m / 10) ** 2 / (m / 10)).sum())
        pt = float(gammaincc(4.5, chi2 / 2))
        ok_p = pasan / m >= minimo
        ok_u = pt >= 1e-4 if m >= 55 else None
        ver = ("pasa" if ok_p and ok_u is not False else "**falla**") + ("" if m >= 55 else " (m < 55: uniformidad orientativa)")
        if not ok_p or ok_u is False:
            malos.append(est)
        extra = f" ({no_aplica[est]} no aplicables)" if est in no_aplica else ""
        lin.append(f"| {est}{extra} | {m} | {pasan} | {pasan / m:.4f} | {minimo:.4f} | {pt:.4f} | {ver} |")
    tot = sum(len(v) for v in por_est.values())
    fallos = sum(int((np.array(v) < ALFA).sum()) for v in por_est.values())
    lin += ["", f"{len(por_est)} estadísticos, {tot} p en total; {fallos} por debajo de 0,01 "
            f"(esperadas {tot * ALFA:.1f}). Estadísticos que no pasan el segundo nivel: "
            + (", ".join(malos) if malos else "ninguno") + ".", ""]
    (SALIDA / "resumen.md").write_text("\n".join(lin) + "\n", encoding="utf-8")
    print("\n".join(lin))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
