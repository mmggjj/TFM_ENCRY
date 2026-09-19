#!/usr/bin/env python3
"""Sintesis logica de cada bloque del motor sobre celdas estandar abiertas
(IHP SG13G2, 130 nm) con Yosys + GHDL, y area en puertas equivalentes.

Es el capitulo de "camino a circuito integrado" del TFM (objetivo O7):
el mismo VHDL que se verifica en simulacion se sintetiza sobre una
biblioteca de celdas real. Lo que sale es una COTA INFERIOR del area:
solo celdas, sin rutado, sin relleno ni arboles de reloj. El area de
nucleo final es entre 1,7 y 4,6 veces mayor (docs/via_asic.md). Se
declara asi siempre.

La puerta equivalente (GE) es el area de la NAND2 minima de la
biblioteca, leida del propio fichero liberty, no de memoria.

    python synth/sintetiza.py            todos los bloques
    python synth/sintetiza.py aes_enc    uno

La salida de Yosys no se filtra: el log completo de cada bloque queda en
synth/build/<bloque>.log.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUILD = RAIZ / "synth" / "build"
LIB = RAIZ / "synth" / "lib" / "sg13g2_stdcell_typ_1p20V_25C.lib"
RESULTADOS = RAIZ / "results" / "sintesis_sg13g2.csv"
YOSYS = "$HOME/eda/oss-cad-suite/bin/yosys"

# Bloque -> ficheros (en orden de dependencia). Los anillos no se
# sintetizan: son el unico bloque atado a la tecnologia.
BLOQUES = {
    "aes_enc":      ["rtl/aes/aes_pkg.vhd", "rtl/aes/aes_enc.vhd"],
    "aes_cmac":     ["rtl/aes/aes_pkg.vhd", "rtl/aes/aes_enc.vhd", "rtl/aes/aes_cmac.vhd"],
    "ctr_drbg":     ["rtl/aes/aes_pkg.vhd", "rtl/aes/aes_enc.vhd", "rtl/drbg/ctr_drbg.vhd"],
    "health_tests": ["rtl/trng/health_tests.vhd"],
    "ero_core":     ["rtl/trng/ero_core.vhd"],
    "bit_cdc":      ["rtl/trng/bit_cdc.vhd"],
    "trng_capture": ["rtl/trng/trng_capture.vhd"],
    "i2c_slave":    ["rtl/io/i2c_slave.vhd"],
    # Nivel superior: la cifra que va en la memoria. Los anillos entran
    # con el sustituto de rtl/synth/, porque el real usa primitivas de
    # Xilinx y no se puede sintetizar a celdas estandar; su area se cuenta
    # aparte. Incluye la logica propia de motor_top (registros de clave,
    # aleatorio, reto y semilla, y el decodificador), que la suma de
    # bloques no recogia.
    "motor_top":    ["rtl/aes/aes_pkg.vhd", "rtl/aes/aes_enc.vhd",
                     "rtl/aes/aes_cmac.vhd", "rtl/drbg/ctr_drbg.vhd",
                     "rtl/synth/ring_osc_stub.vhd", "rtl/trng/ero_core.vhd",
                     "rtl/trng/bit_cdc.vhd", "rtl/trng/health_tests.vhd",
                     "rtl/trng/trng_capture.vhd", "rtl/io/i2c_slave.vhd",
                     "rtl/top/motor_top.vhd"],
}


def wsl(p: Path) -> str:
    s = str(p).replace("\\", "/")
    return "/mnt/" + s[0].lower() + s[2:]


def area_nand2(lib: Path) -> float:
    """Area de la NAND2 mas pequena del liberty."""
    texto = lib.read_text(errors="replace")
    mejor = None
    for m in re.finditer(r"cell\s*\(\s*\"?(\w*nand2\w*)\"?\s*\)\s*\{(.*?)\n\s*\}\s*\n", texto, re.S):
        a = re.search(r"\barea\s*:\s*([0-9.]+)", m.group(2))
        if a:
            v = float(a.group(1))
            if mejor is None or v < mejor[1]:
                mejor = (m.group(1), v)
    if mejor is None:
        raise SystemExit("no se encontro una celda NAND2 en el liberty")
    return mejor[1], mejor[0]


def sintetizar(bloque: str, ficheros: list[str]) -> dict:
    BUILD.mkdir(parents=True, exist_ok=True)
    ys = BUILD / f"{bloque}.ys"
    log = BUILD / f"{bloque}.log"
    fuentes = " ".join(wsl(RAIZ / f) for f in ficheros)
    ys.write_text(f"""plugin -i ghdl
ghdl --std=08 {fuentes} -e {bloque}
hierarchy -check -top {bloque}
synth -top {bloque} -flatten
dfflibmap -liberty {wsl(LIB)}
abc -liberty {wsl(LIB)}
opt_clean -purge
stat -liberty {wsl(LIB)}
""")
    t0 = time.time()
    r = subprocess.run(["wsl.exe", "-e", "bash", "-lc",
                        f"{YOSYS} -q -l {wsl(log)} -s {wsl(ys)}"],
                       capture_output=True, text=True, timeout=3600)
    dur = time.time() - t0
    salida = log.read_text(errors="replace") if log.exists() else r.stdout + r.stderr

    res = {"bloque": bloque, "segundos": round(dur, 1), "ok": r.returncode == 0}
    # Con -flatten hay un solo modulo; se toma la ULTIMA linea de area por si
    # quedara jerarquia (los totales se imprimen al final).
    areas = re.findall(r"Chip area for (?:top )?module.*?:\s*([0-9.]+)", salida)
    m = areas[-1] if areas else None
    res["area_um2"] = float(m) if m else float("nan")
    # Formato de Yosys 0.69: "   10439 1.15E+05 cells" y una linea por celda
    # "     262 1.28E+04   sg13g2_dfrbpq_1".
    m = re.search(r"^\s*(\d+)\s+\S+\s+cells\s*$", salida, re.M)
    res["celdas"] = int(m.group(1)) if m else -1
    ff = 0
    for m in re.finditer(r"^\s*(\d+)\s+\S+\s+sg13g2_(?:dfr|dfl|sdf|dlh)\w*\s*$", salida, re.M):
        ff += int(m.group(1))
    res["biestables"] = ff
    if r.returncode != 0:
        res["error"] = (r.stderr or salida)[-800:]
    return res


def main() -> int:
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    if not LIB.exists():
        raise SystemExit(f"falta el liberty {LIB}")
    ge, celda = area_nand2(LIB)
    print(f"biblioteca {LIB.name}: 1 GE = {celda} = {ge} um2\n")
    print(f"{'bloque':14s} {'celdas':>7s} {'FF':>6s} {'area um2':>10s} {'kGE':>7s} {'s':>5s}")

    filas = []
    for bloque, ficheros in BLOQUES.items():
        if filtro and filtro not in bloque:
            continue
        res = sintetizar(bloque, ficheros)
        res["kGE"] = round(res["area_um2"] / ge / 1000, 3) if res["ok"] else float("nan")
        filas.append(res)
        if res["ok"]:
            print(f"{bloque:14s} {res['celdas']:7d} {res['biestables']:6d} "
                  f"{res['area_um2']:10.1f} {res['kGE']:7.3f} {res['segundos']:5.0f}")
        else:
            print(f"{bloque:14s} FALLO (ver synth/build/{bloque}.log)")
            print("  " + res.get("error", "").replace("\n", "\n  "))

    # Con filtro se actualizan solo las filas afectadas: antes una ejecucion
    # de un solo bloque machacaba el CSV entero con una fila.
    RESULTADOS.parent.mkdir(exist_ok=True)
    campos = ["bloque", "celdas", "biestables", "area_um2", "kGE", "segundos", "ok"]
    previas = {}
    if filtro and RESULTADOS.exists():
        with RESULTADOS.open(newline="") as f:
            for fila in csv.DictReader(f):
                previas[fila["bloque"]] = fila
    for r in filas:
        previas[r["bloque"]] = {k: r.get(k, "") for k in campos}
    with RESULTADOS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for bloque in BLOQUES:
            if bloque in previas:
                w.writerow(previas[bloque])
    print(f"\nGE = area de {celda} ({ge} um2). Area de celdas, sin rutar: cota inferior.")
    print(f"datos en {RESULTADOS}")
    return 0 if all(r["ok"] for r in filas) else 1


if __name__ == "__main__":
    sys.exit(main())
