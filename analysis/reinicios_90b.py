#!/usr/bin/env python3
"""Analisis de la prueba de reinicios del RNG del ESP32 (SP 800-90B, 3.1.4).

Variantes (capturadas con reinicios_esp32.py; "sin_ruido" = bootloader que
no enciende la fuente de entropia del arranque):
  normal, sin_ruido      lectura nada mas arrancar, radio apagada (cond. D)
  radio, radio_sin_ruido lectura tras encender el Wi-Fi y esperar 200 ms
  espera_sin_ruido       control: la misma espera sin encender la radio
Las tres ultimas guardan ademas la lectura de nada mas arrancar ("antes").

1. Prueba oficial: matriz de 1000 reinicios x 1000 muestras, en modo bit
   (primeros 1000 bits de cada arranque) y en modo byte (primeros 1000
   bytes), por ea_restart de la herramienta del NIST (WSL). H_I es la
   estimacion no-IID mas baja de las capturas del mismo chip en la misma
   condicion (D sin radio, B con Wi-Fi); con una H_I menor la comprobacion
   es menos exigente, no mas.
2. Comprobacion directa: arranques repetidos, distancia de Hamming entre
   arranques, sesgo por posicion (columna) y arranques que son el mismo
   flujo leido desde otro punto.

    python analysis/reinicios_90b.py --mac a0dd6c0efb4c

Salidas: results/esp32_reinicios/mac_<mac>/<variante>/ea_restart_{b1,b8}.log
(integros) y results/esp32_reinicios/resumen_mac_<mac>.md.
"""
from __future__ import annotations

import argparse
import collections
import csv
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binom, chisquare, norm

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "results"
DIR = RES / "esp32_reinicios"
HERRAMIENTA = "~/SP800-90B_EntropyAssessment/cpp"
N_REIN, N_MUES = 1000, 1000


def a_wsl(p: Path) -> str:
    p = p.resolve()
    return "/mnt/" + p.drive[0].lower() + p.as_posix()[2:]


# variante -> (condicion de la campana con la que se fija H_I, guarda "antes")
VARIANTES = {"normal": ("D", False), "sin_ruido": ("D", False),
             "radio_sin_ruido": ("B", True), "espera_sin_ruido": ("D", True),
             "radio": ("B", True),
             # firmware/reinicios_fuentes: bootloader sin ruido, una fuente y
             # lectura "despues" a los 800 ms con la fuente ya apagada (por
             # eso H_I de D)
             **{v: ("D", True) for v in (
                 "fuente_control", "fuente_wifi_init", "fuente_radio_0", "fuente_radio_1",
                 "fuente_radio_10", "fuente_radio_100", "fuente_adc_200", "fuente_bootrand_200",
                 "fuente_adc_0", "fuente_adc_1")}}
LECTURA_FUENTE = {
    "fuente_control": "sin ninguna fuente (control)",
    "fuente_wifi_init": "tras iniciar el Wi-Fi sin encender la radio (sin esp_wifi_start)",
    "fuente_adc_200": "tras 200 ms de lecturas normales del ADC (adc_oneshot, ADC1 canal 0)",
    "fuente_adc_1": "tras 1 ms de lecturas normales del ADC (adc_oneshot, ADC1 canal 0)",
    "fuente_adc_0": "tras crear y borrar la unidad del ADC sin ninguna lectura",
    "fuente_bootrand_200": "tras 200 ms con la fuente del arranque (bootloader_random_enable) "
                           "encendida desde el programa",
    **{f"fuente_radio_{m}": f"tras {m} ms con la radio encendida (desde que vuelve esp_wifi_start "
                            f"hasta esp_wifi_stop)" for m in (0, 1, 10, 100)},
}


def h_inicial(mac: str, cond: str = "D") -> tuple[float, float, str]:
    """H no-IID (bit/bit y bit/byte) mas baja de las capturas del chip en cond."""
    filas = list(csv.DictReader((RES / "entropia_90b.csv").open(encoding="utf-8")))
    pref = {"a0dd6c0efb4c": "fb4c_", "f8b3b72a0928": "0928_"}.get(mac)
    if pref is None:
        raise SystemExit(f"sin capturas de la campana para el chip {mac}")
    b1 = {f["nombre"]: float(f["testCases.10.hAssessed"]) for f in filas
          if f["test"] == "noniid" and f["modo"] == "b1" and f["nombre"].startswith(pref + "cond" + cond)}
    peor = min(b1, key=b1.get)
    return b1[peor], 8 * b1[peor], peor


def ea_restart(datos: np.ndarray, bits: int, h_i: float, dest: Path, etiqueta: str) -> dict:
    ruta = dest / f"restart_{etiqueta}.bin"          # derivado, no se versiona
    ruta.write_bytes(datos.astype(np.uint8).tobytes())
    orden = f"cd {HERRAMIENTA} && ./ea_restart -n -v {a_wsl(ruta)} {bits} {h_i:.6f}"
    r = subprocess.run(["wsl.exe", "-e", "bash", "-lc", orden], capture_output=True, text=True,
                       timeout=4 * 3600)
    texto = r.stdout + r.stderr
    (dest / f"ea_restart_{etiqueta}.log").write_text(texto, encoding="utf-8")
    print(f"--- ea_restart {dest.name} {etiqueta} (H_I = {h_i:.4f}): exit {r.returncode} ---")
    print(texto.rstrip())
    return {"exit": r.returncode, "texto": texto}


def directa(bloques: np.ndarray) -> dict:
    """bloques: (n, RST_BYTES) uint8."""
    n = len(bloques)
    bits = np.unpackbits(bloques, axis=1).astype(np.int32)            # (n, 8*RST_BYTES)
    nb = bits.shape[1]
    # arranques identicos (bloque entero y primeros 8 bytes)
    unicos = len({b.tobytes() for b in bloques})
    unicos8 = len({b[:8].tobytes() for b in bloques})
    # distancia de Hamming entre todos los pares: d = w_i + w_j - 2 <b_i, b_j>
    w = bits.sum(axis=1)
    g = bits @ bits.T
    d = w[:, None] + w[None, :] - 2 * g
    iu = np.triu_indices(n, 1)
    dist = d[iu]
    # sesgo por columna: unos por posicion a lo largo de los arranques
    unos = bits.sum(axis=0)
    z = (unos - n / 2) / np.sqrt(n / 4)
    # binomial: p de la columna mas desviada, con correccion por nb columnas
    peor = int(np.argmax(np.abs(z)))
    k = unos[peor]
    p_col = 2 * min(binom.cdf(k, n, 0.5), binom.sf(k - 1, n, 0.5))
    # primer byte de cada arranque: uniforme en 256 valores?
    chi_b0 = chisquare(np.bincount(bloques[:, 0], minlength=256)).pvalue
    return {"n": n, "bits": nb, "unicos": unicos, "unicos8": unicos8,
            "dist_min": int(dist.min()), "dist_media": float(dist.mean()), "dist_sd": float(dist.std()),
            "dist_esperada": nb / 2, "dist_sd_esperada": float(np.sqrt(nb / 4)),
            # minimo esperado de len(dist) distancias ~ normales (cuantil 1/len)
            "dist_min_esperada": nb / 2 - norm.isf(1 / len(dist)) * np.sqrt(nb / 4),
            "z_max": float(np.abs(z).max()), "col_peor": peor, "p_col_peor": float(p_col),
            "p_col_corr": float(min(1.0, p_col * nb)), "chi_byte0": float(chi_b0)}


def flujo_comun(bloques: np.ndarray) -> dict:
    """Busca arranques que sean el mismo flujo de palabras de 32 bits leido
    desde otro punto: el inicio de un arranque (dos palabras) aparece en
    otro desplazado p palabras. Comprueba que el solape coincide entero y
    agrupa los arranques alineables (componentes)."""
    n = len(bloques)
    w = bloques.view("<u4").reshape(n, -1)
    nw = w.shape[1]
    idx: dict = collections.defaultdict(list)
    for i in range(n):
        for p in range(nw - 1):
            idx[(w[i, p], w[i, p + 1])].append((i, p))
    rel = [(i, j, p) for i in range(n) for (j, p) in idx[(w[i, 0], w[i, 1])] if j != i and p > 0]
    enteros = sum(bool(np.array_equal(w[i, :nw - p], w[j, p:])) for i, j, p in rel)
    vecinos = collections.defaultdict(set)
    for i, j, _ in rel:
        vecinos[i].add(j)
        vecinos[j].add(i)
    visto, comps = set(), []
    for s in range(n):
        if s in visto:
            continue
        pila, c = [s], 0
        visto.add(s)
        while pila:
            a = pila.pop()
            c += 1
            for b in vecinos[a] - visto:
                visto.add(b)
                pila.append(b)
        comps.append(c)
    # entropia por arranque a partir de las repeticiones exactas
    cuenta = collections.Counter(b.tobytes() for b in bloques)
    k, m = len(cuenta), max(cuenta.values())
    p_hat = m / n
    p_u = min(1.0, p_hat + 2.576 * math.sqrt(p_hat * (1 - p_hat) / n))
    lo, hi = k, 10 ** 9                        # estados equiprobables con k distintos en n
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if mid * (1 - (1 - 1 / mid) ** n) < k:
            lo = mid
        else:
            hi = mid
    return {"relaciones": len(rel), "enteros": enteros, "componentes": len(comps),
            "comp_max": max(comps), "distintos": k, "repe_max": m,
            "hmin_arranque": -math.log2(p_u), "estados": hi if k < n else None}


def veredicto(texto: str) -> str:
    # la herramienta escribe lineas como "*** Restart Sanity Check Passed ***"
    lineas = [l.strip() for l in texto.splitlines()
              if re.search(r"sanity|validation|passed|failed|H_r|H_c|H_I|min\(", l, re.I)]
    return " / ".join(lineas[-8:]) if lineas else "(sin veredicto en la salida: ver log)"


def tablas(bloques: np.ndarray) -> list[str]:
    dr = directa(bloques)
    fc = flujo_comun(bloques)
    est = (f"{fc['estados']} (≈ {math.log2(fc['estados']):.1f} bits)" if fc["estados"]
           else "sin repeticiones: no se puede estimar")
    return ["| Comprobación directa | Valor | Esperado con datos al azar |", "|---|---|---|",
            f"| bloques distintos | {dr['unicos']} de {dr['n']} | {dr['n']} |",
            f"| primeros 8 bytes distintos | {dr['unicos8']} de {dr['n']} | {dr['n']} |",
            f"| distancia de Hamming entre arranques, media ± desv. | {dr['dist_media']:.1f} ± {dr['dist_sd']:.1f} "
            f"| {dr['dist_esperada']:.0f} ± {dr['dist_sd_esperada']:.1f} |",
            f"| distancia mínima entre dos arranques | {dr['dist_min']} | ≈ {dr['dist_min_esperada']:.0f} |",
            f"| posición más sesgada (unos en {dr['n']} arranques) | z = {dr['z_max']:.2f}, "
            f"p corregida = {dr['p_col_corr']:.3g} | p corregida ≈ uniforme |",
            f"| primer byte, χ² frente a uniforme | p = {dr['chi_byte0']:.3g} | p ≈ uniforme |", "",
            "| Mismo flujo leído desde otro punto | Valor |", "|---|---|",
            f"| arranques cuyo inicio aparece desplazado dentro de otro arranque | {fc['relaciones']} relaciones |",
            f"| de ellas, con el solape entero idéntico | {fc['enteros']} |",
            f"| grupos de arranques alineables / el mayor | {fc['componentes']} / {fc['comp_max']} |",
            f"| secuencias distintas; la más repetida sale | {fc['distintos']}; {fc['repe_max']} veces |",
            f"| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) "
            f"| {fc['hmin_arranque']:.1f} bits |",
            f"| estados equiprobables que darían esas repeticiones | {est} |", ""]


def por_tick(bloques: np.ndarray, t_us: np.ndarray, antes: np.ndarray) -> list[str]:
    """La lectura "despues" va tras un vTaskDelay y cae en un tick de 10 ms:
    agrupa los arranques por tick y mira repeticiones dentro de cada grupo,
    y si dos arranques con la misma lectura "antes" repiten la "despues"."""
    tick = np.round(t_us / 10000).astype(int)
    lin = ["| Tick de la lectura (ms) | Arranques | Secuencias distintas | Relaciones de desplazamiento |",
           "|---|---|---|---|"]
    for k in sorted(set(tick)):
        sel = np.where(tick == k)[0]
        if len(sel) < 2:
            continue
        fc = flujo_comun(bloques[sel])
        lin.append(f"| {k * 10} | {len(sel)} | {fc['distintos']} | {fc['relaciones']} |")
    pares, mismos = pares_antes(bloques, antes)
    lin += ["", f"Pares de arranques con la lectura \"antes\" idéntica: {pares}; "
            f"de ellos con la lectura \"despues\" también idéntica: {mismos}.", ""]
    return lin


def pares_antes(bloques: np.ndarray, antes: np.ndarray) -> tuple[int, int]:
    """Parejas de arranques con la lectura "antes" identica (mismo estado del
    generador) y cuantas de ellas repiten tambien la "despues"."""
    grupos = collections.defaultdict(list)
    for i, b in enumerate(antes):
        grupos[b.tobytes()].append(i)
    pares = mismos = 0
    for g in grupos.values():
        for x in range(len(g)):
            for y in range(x + 1, len(g)):
                pares += 1
                mismos += bool(np.array_equal(bloques[g[x]], bloques[g[y]]))
    return pares, mismos


def fuente(filas: list[dict], bloques: np.ndarray, antes: np.ndarray) -> tuple[list[str], dict]:
    """Variantes fuente_*: tiempos de la fuente y de la lectura, y la pareja
    de cifras que decide si la fuente mete ruido (mismo "antes" -> mismo
    "despues")."""
    cc = np.array([int(f["ccount"]) for f in filas], dtype=np.int64)
    t_on = np.array([int(f["t_on_us"]) for f in filas])
    t_off = np.array([int(f["t_off_us"]) for f in filas])
    tarde = sum(int(f["tarde"]) for f in filas)
    pares, mismos = pares_antes(bloques, antes)
    fc_a, fc_d = flujo_comun(antes), flujo_comun(bloques)
    lin = [f"Fuente encendida de {t_on.min()} a {t_on.max()} µs y apagada de {t_off.min()} a "
           f"{t_off.max()} µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: {tarde}; "
           f"contador de ciclos en la lectura \"despues\": {cc.min()}-{cc.max()} "
           f"(variación {cc.max() - cc.min()} ciclos).", ""]
    if "rf_ts_ini" in filas[0] and int(filas[0]["rf_ts_ini"]) >= 0:
        # esp_phy_rf_get_on_ts: ultimo encendido de la radio, leido al volver
        # esp_wifi_start y al volver esp_wifi_stop
        ini = np.array([int(f["rf_ts_ini"]) for f in filas])
        fin = np.array([int(f["rf_ts_fin"]) for f in filas])
        lin += [f"Radio encendida según la PHY a los {ini.min()}-{ini.max()} µs; tiempo con la radio "
                f"encendida hasta que vuelve esp_wifi_stop: {(t_off - ini).min() / 1000:.1f}-"
                f"{(t_off - ini).max() / 1000:.1f} ms; arranques en que esp_wifi_stop la volvió a "
                f"encender: {int((fin != ini).sum())} de {len(filas)}.", ""]
    if "n_adc" in filas[0] and int(filas[0]["n_adc"]) >= 0:
        n_adc = np.array([int(f["n_adc"]) for f in filas])
        ult = np.array([int(f["adc_ultimo"]) for f in filas])
        lin += [f"Lecturas correctas del ADC por arranque: {n_adc.min()}-{n_adc.max()}; última lectura "
                f"cruda {ult.min()}-{ult.max()} (12 bits).", ""]
    lin += [
           f"Pares de arranques con la lectura \"antes\" idéntica: {pares}; "
           f"de ellos con la lectura \"despues\" también idéntica: {mismos}.", ""]
    return lin, {"n": len(filas), "dist_antes": fc_a["distintos"], "dist_despues": fc_d["distintos"],
                 "rel_despues": fc_d["relaciones"], "enteros_despues": fc_d["enteros"],
                 "pares": pares, "mismos": mismos, "hmin": fc_d["hmin_arranque"],
                 "variacion_cc": int(cc.max() - cc.min())}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--mac", default="a0dd6c0efb4c")
    ap.add_argument("--sin-nist", action="store_true", help="solo la comprobacion directa")
    a = ap.parse_args()
    base = DIR / f"mac_{a.mac}"
    out = [f"# Prueba de reinicios del RNG del ESP32, chip {a.mac}", "",
           "Generado por analysis/reinicios_90b.py. H_I: estimación no-IID más baja de las capturas "
           "de la campaña de este chip en la misma condición (D sin radio, B con Wi-Fi).", ""]
    resumen_fuentes: dict[str, dict] = {}
    for var, (cond, con_antes) in VARIANTES.items():
        dest = base / var
        ruta = dest / "reinicios.bin"
        if not ruta.exists():
            if not var.startswith("fuente_"):
                out += [f"## Variante {var}", "", "Sin capturar.", ""]
            continue
        h1, h8, de = h_inicial(a.mac, cond)
        crudo = np.frombuffer(ruta.read_bytes(), dtype=np.uint8)
        filas = list(csv.DictReader((dest / "reinicios.csv").open(encoding="utf-8")))
        rst_bytes = len(crudo) // len(filas)
        bloques = crudo.reshape(len(filas), rst_bytes)
        resets = sorted({f["reset"] for f in filas})
        ruido = collections.Counter(f["ruido_arranque_encendido"] for f in filas)
        t_us = np.array([int(f["t_us"]) for f in filas])
        lectura = (f"a los 800 ms, {LECTURA_FUENTE[var]}" if var in LECTURA_FUENTE else
                   "tras encender el Wi-Fi y esperar 200 ms" if var.startswith("radio") else
                   "tras la misma espera, sin encender la radio" if var.startswith("espera") else
                   "nada más arrancar, radio apagada")
        out += [f"## Variante {var}", "",
                f"{len(filas)} reinicios de {rst_bytes} B, lectura {lectura}; motivo de reset {resets} "
                f"(1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: "
                f"{ruido.get('1', 0)} de {len(filas)}; instante de la lectura {t_us.min()}-{t_us.max()} µs "
                f"desde el arranque del programa. H_I = {h1:.4f} bit/bit ({de}).", ""]
        out += tablas(bloques)
        if con_antes:
            antes = np.frombuffer((dest / "reinicios_antes.bin").read_bytes(),
                                  dtype=np.uint8).reshape(len(filas), rst_bytes)
            out += ["Lectura de nada más arrancar en esta misma variante (\"antes\"):", ""]
            out += tablas(antes)
            if var.startswith("fuente_"):
                lin, resumen_fuentes[var] = fuente(filas, bloques, antes)
                out += lin
            else:
                out += ["Lectura \"despues\" agrupada por el tick de FreeRTOS en que cae:", ""]
                out += por_tick(bloques, t_us, antes)
        if len(filas) >= N_REIN and not a.sin_nist:
            m1 = np.unpackbits(bloques[:N_REIN, :N_MUES // 8], axis=1)      # 1000 x 1000 bits
            m8 = bloques[:N_REIN, :N_MUES]                                  # 1000 x 1000 bytes
            r1 = ea_restart(m1, 1, h1, dest, "b1")
            r8 = ea_restart(m8, 8, h8, dest, "b8")
            out += ["Prueba oficial (ea_restart, no-IID), salida íntegra en "
                    f"`{var}/ea_restart_b1.log` y `ea_restart_b8.log`:", "",
                    f"- bit: {veredicto(r1['texto'])}",
                    f"- byte: {veredicto(r8['texto'])}", ""]
    if resumen_fuentes:
        out += ["## Comparación de fuentes (firmware/reinicios_fuentes, lectura \"despues\" a los 800 ms)", "",
                "| Variante | Arranques | Distintas \"antes\" | Distintas \"despues\" | Trozos compartidos "
                "(solapes idénticos) | Pares con \"antes\" idéntica | de ellos, \"despues\" idéntica | "
                "Min-entropía por arranque (bits) | Variación del instante (ciclos) |",
                "|---|---|---|---|---|---|---|---|---|"]
        for var, r in resumen_fuentes.items():
            out.append(f"| {var} | {r['n']} | {r['dist_antes']} | {r['dist_despues']} | "
                       f"{r['rel_despues']} ({r['enteros_despues']}) | {r['pares']} | {r['mismos']} | "
                       f"{r['hmin']:.1f} | {r['variacion_cc']} |")
        out.append("")
    salida = DIR / f"resumen_mac_{a.mac}.md"
    salida.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
