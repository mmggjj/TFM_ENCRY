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

Dos caminos hacia Yosys, el mismo flujo de sintesis en los dos:
  - OSS CAD Suite en WSL (~/eda/oss-cad-suite): Yosys lee el VHDL con el
    plugin de GHDL.
  - Sin OSS CAD Suite: el GHDL de Windows elabora el VHDL a una netlist
    Verilog (ghdl --synth --out=verilog, que es lo mismo que hace el
    plugin por dentro) y la lee el Yosys instalable con pip (yowasp-yosys,
    ~/.local/bin en WSL). Con aes_enc da 113 763 um2 frente a 114 771 del
    plugin (-0,9 %), misma biblioteca y mismo abc.
Se elige solo con la herramienta que haya; --verilog fuerza el segundo.

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
YOWASP = "$HOME/.local/bin/yowasp-yosys"
GHDL_CANDIDATOS = ["ghdl", str(Path.home() / "eda" / "ghdl" / "bin" / "ghdl.exe")]
# En Windows, Yosys corre en WSL; en Linux (un runner de CI, o un PC con
# Linux) corre directo con el mismo guion de sintesis.
EN_WINDOWS = sys.platform == "win32"


def sh(orden: str, timeout: int) -> subprocess.CompletedProcess:
    """Ejecuta una orden de shell: en WSL desde Windows, en bash en Linux."""
    if EN_WINDOWS:
        return subprocess.run(["wsl.exe", "-e", "bash", "--noprofile", "--norc", "-c", orden],
                              capture_output=True, text=True, timeout=timeout)
    return subprocess.run(["bash", "-c", orden], capture_output=True, text=True, timeout=timeout)


def hay_en_wsl(ruta: str) -> bool:
    return sh(f"test -x {ruta}", 60).returncode == 0


def buscar_ghdl() -> str | None:
    import shutil
    for c in GHDL_CANDIDATOS:
        if shutil.which(c) or Path(c).is_file():
            return c
    return None

# Bloque -> ficheros (en orden de dependencia). Los anillos no se
# sintetizan: son el unico bloque atado a la tecnologia.
BLOQUES = {
    "aes_enc":      ["rtl/aes/aes_pkg.vhd", "rtl/aes/aes_enc.vhd"],
    "aes_enc_32":   ["rtl/aes/aes_pkg.vhd", "rtl/aes/aes_enc_32.vhd"],
    "aes_cmac":    ["rtl/aes/aes_pkg.vhd", "rtl/aes/aes_enc.vhd", "rtl/aes/aes_cmac.vhd"],
    "ctr_drbg":     ["rtl/aes/aes_pkg.vhd", "rtl/aes/aes_enc.vhd", "rtl/drbg/ctr_drbg.vhd"],
    "health_tests": ["rtl/trng/health_tests.vhd"],
    "ero_core":     ["rtl/trng/ero_core.vhd"],
    "bit_cdc":      ["rtl/trng/bit_cdc.vhd"],
    "reset_sync":   ["rtl/trng/reset_sync.vhd"],
    "trng_capture": ["rtl/trng/trng_capture.vhd"],
    "i2c_slave":    ["rtl/io/i2c_slave.vhd"],
    # Nivel superior: la cifra que va en la memoria. Los anillos entran
    # con el sustituto de rtl/synth/, porque el real usa primitivas de
    # Xilinx y no se puede sintetizar a celdas estandar; su area se cuenta
    # aparte. Incluye la logica propia de motor_top (registros de clave,
    # aleatorio, reto y semilla, y el decodificador), que la suma de
    # bloques no recogia.
    "motor_top":    ["rtl/aes/aes_pkg.vhd", "rtl/aes/aes_enc.vhd", "rtl/aes/aes_enc_32.vhd",
                     "rtl/aes/aes_cmac.vhd", "rtl/drbg/ctr_drbg.vhd",
                     "rtl/synth/ring_osc_stub.vhd", "rtl/trng/reset_sync.vhd",
                     "rtl/trng/ero_core.vhd",
                     "rtl/trng/bit_cdc.vhd", "rtl/trng/health_tests.vhd",
                     "rtl/trng/trng_capture.vhd", "rtl/io/i2c_slave.vhd",
                     "rtl/top/motor_top.vhd"],
}
# Variantes de un bloque con otros genericos: nombre de fila -> (entidad,
# genericos de GHDL). Sirven para medir una optimizacion contra la
# configuracion anterior en la misma tanda, con la misma herramienta.
VARIANTES = {
    # El motor con el AES de una ronda por ciclo en vez del compacto.
    "motor_top_aes11": ("motor_top", ["-gG_AES_COMPACTO=false"]),
}
BLOQUES["motor_top_aes11"] = BLOQUES["motor_top"]


def wsl(p: Path) -> str:
    """Ruta tal como la ve el shell que ejecuta Yosys."""
    if not EN_WINDOWS:
        return str(p)
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


def sintetizar(bloque: str, ficheros: list[str], via_verilog: bool, ghdl: str | None) -> dict:
    BUILD.mkdir(parents=True, exist_ok=True)
    ys = BUILD / f"{bloque}.ys"
    log = BUILD / f"{bloque}.log"
    entidad, genericos = VARIANTES.get(bloque, (bloque, []))
    t0 = time.time()
    if via_verilog:
        # 1) GHDL (Windows) elabora a Verilog. Su salida de error se guarda
        #    entera: son las notas de ROM encontradas y avisos de sintesis.
        v = BUILD / f"{bloque}.v"
        with v.open("w") as fv, (BUILD / f"{bloque}.ghdl.log").open("w") as fl:
            rg = subprocess.run([ghdl, "--synth", "--std=08", "--out=verilog"] + genericos
                                + [str(RAIZ / f) for f in ficheros] + ["-e", entidad],
                                stdout=fv, stderr=fl, text=True, timeout=1800)
        if rg.returncode != 0:
            return {"bloque": bloque, "segundos": round(time.time() - t0, 1), "ok": False,
                    "error": (BUILD / f"{bloque}.ghdl.log").read_text(errors="replace")[-800:]
                    .replace(str(RAIZ), ".")}
        entrada = f"read_verilog {wsl(v)}"
        yosys = YOWASP
    else:
        fuentes = " ".join(wsl(RAIZ / f) for f in ficheros)
        entrada = f"plugin -i ghdl\nghdl --std=08 {' '.join(genericos)} {fuentes} -e {entidad}"
        yosys = YOSYS
    ys.write_text(f"""{entrada}
hierarchy -check -top {entidad}
synth -top {entidad} -flatten
dfflibmap -liberty {wsl(LIB)}
abc -liberty {wsl(LIB)}
opt_clean -purge
stat -liberty {wsl(LIB)}
""")
    r = sh(f"{yosys} -q -l {wsl(log)} -s {wsl(ys)}", 3600)
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
    # Sin rutas de maquina en lo que va a results/: el repositorio es publico.
    if "error" in res:
        res["error"] = res["error"].replace(str(RAIZ), ".").replace(wsl(RAIZ), ".")
    return res


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    filtro = args[0] if args else ""
    global YOWASP
    via_verilog = "--verilog" in sys.argv or not hay_en_wsl(YOSYS)
    if not EN_WINDOWS:
        import shutil
        YOWASP = shutil.which("yowasp-yosys") or YOWASP
    if not LIB.exists():
        raise SystemExit(f"falta el liberty {LIB}")
    ghdl = None
    if via_verilog:
        ghdl = buscar_ghdl()
        if ghdl is None or not hay_en_wsl(YOWASP):
            raise SystemExit("hace falta GHDL y yowasp-yosys (pip install --user yowasp-yosys)")
        print("camino: GHDL --synth -> Verilog -> yowasp-yosys" + (" (WSL)" if EN_WINDOWS else ""))
    else:
        print("camino: OSS CAD Suite (WSL), Yosys con el plugin de GHDL")
    ge, celda = area_nand2(LIB)
    print(f"biblioteca {LIB.name}: 1 GE = {celda} = {ge} um2\n")
    print(f"{'bloque':14s} {'celdas':>7s} {'FF':>6s} {'area um2':>10s} {'kGE':>7s} {'s':>5s}")

    filas = []
    for bloque, ficheros in BLOQUES.items():
        if filtro and filtro not in bloque:
            continue
        res = sintetizar(bloque, ficheros, via_verilog, ghdl)
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
    print(f"datos en {RESULTADOS.relative_to(RAIZ)}")
    return 0 if all(r["ok"] for r in filas) else 1


if __name__ == "__main__":
    sys.exit(main())
