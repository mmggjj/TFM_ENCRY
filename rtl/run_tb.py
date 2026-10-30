#!/usr/bin/env python3
"""Analiza todo el VHDL y ejecuta los bancos de pruebas.

    python rtl/run_tb.py            todos
    python rtl/run_tb.py aes        solo los que contengan "aes"

No se filtra la salida de GHDL: se imprime entera. Un filtro esconde
justo el aviso que importaba.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CONSTRUIR = RAIZ / "build"
UNISIM = CONSTRUIR / "unisim"
WORK = CONSTRUIR / "work"

GHDL_CANDIDATOS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "ghdl" / "bin" / "ghdl.exe",
    Path.home() / "eda" / "ghdl" / "bin" / "ghdl.exe",   # mismo sitio que usa synth/sintetiza.py
    Path("ghdl"),
    Path.home() / "eda" / "oss-cad-suite" / "bin" / "ghdl",
]

# Orden de analisis: las dependencias primero.
FUENTES_UNISIM = ["sim/unisim_modelos.vhd"]
FUENTES = [
    "trng/ring_osc.vhd",
    "trng/reset_sync.vhd",
    "trng/ero_core.vhd",
    "trng/trng_capture.vhd",
    "trng/health_tests.vhd",
    "trng/bit_cdc.vhd",
    "io/i2c_slave.vhd",
    "aes/aes_pkg.vhd",
    "aes/aes_enc.vhd",
    "aes/aes_enc_32.vhd",
    "aes/aes_cmac.vhd",
    "drbg/ctr_drbg.vhd",
    "tb/drbg_vectores_pkg.vhd",      # generado por analysis/gen_drbg_vectores.py
    "top/motor_top.vhd",
    "fpga/basys3_top.vhd",           # envoltorio de placa: solo se analiza, no tiene banco
]
BANCOS = [
    ("tb_ring_osc", "tb/tb_ring_osc.vhd", ["-Pbuild/unisim"]),
    ("tb_i2c_slave", "tb/tb_i2c_slave.vhd", []),
    ("tb_aes_enc", "tb/tb_aes_enc.vhd", []),
    ("tb_aes_cmac", "tb/tb_aes_cmac.vhd", []),
    ("tb_ctr_drbg", "tb/tb_ctr_drbg.vhd", []),
    ("tb_health_tests", "tb/tb_health_tests.vhd", []),
    ("tb_motor_top", "tb/tb_motor_top.vhd", ["-Pbuild/unisim"]),
]


def buscar_ghdl():
    for c in GHDL_CANDIDATOS:
        try:
            r = subprocess.run([str(c), "--version"], capture_output=True,
                               text=True, timeout=60)
            if r.returncode == 0:
                return str(c)
        except Exception:
            continue
    raise SystemExit("no se encuentra ghdl")


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    ghdl = buscar_ghdl()
    version = subprocess.run([ghdl, "--version"], capture_output=True,
                             text=True).stdout
    mcode = "mcode" in version
    UNISIM.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    os.chdir(RAIZ.parent)

    def correr(args, etiqueta):
        r = subprocess.run([ghdl] + args, capture_output=True, text=True,
                           timeout=7200)   # tb_motor_top: ~8 min solo, mucho mas con la CPU compartida
        salida = (r.stdout + r.stderr).rstrip()
        if salida:
            print(salida)
        if r.returncode != 0:
            print(f"  --> {etiqueta} devolvio {r.returncode}")
        return r.returncode

    print("=== analisis ===")
    errores = 0
    for f in FUENTES_UNISIM:
        errores += 1 if correr(
            ["-a", "--std=08", "--work=unisim", "--workdir=rtl/build/unisim",
             f"rtl/{f}"], f) else 0
    for f in FUENTES:
        errores += 1 if correr(
            ["-a", "--std=08", "--workdir=rtl/build/work", "-Prtl/build/unisim",
             f"rtl/{f}"], f) else 0
    for nombre, f, _ in BANCOS:
        errores += 1 if correr(
            ["-a", "--std=08", "--workdir=rtl/build/work", "-Prtl/build/unisim",
             f"rtl/{f}"], f) else 0

    if errores:
        print(f"\n{errores} ficheros no analizaron: no se ejecuta nada")
        return 1

    print("\n=== ejecucion ===")
    fallidos = []
    for nombre, _, extra in BANCOS:
        if filtro and filtro not in nombre:
            continue
        print(f"\n--- {nombre} ---")
        # Las propiedades PSL del banco (si las tiene) se informan aparte: una
        # asercion violada ya hace fallar la simulacion, pero el informe dice
        # ademas cuantas se evaluaron y que coberturas se alcanzaron.
        psl = CONSTRUIR / f"{nombre}_psl.json"
        opciones = ["--std=08", "--workdir=rtl/build/work", "-Prtl/build/unisim"]
        if mcode:
            rc = correr(["-r"] + opciones + [nombre, f"--psl-report={psl}"], nombre)
        else:
            # LLVM/GCC: elaborar a un ejecutable y lanzarlo desde la raiz
            exe = CONSTRUIR / nombre
            rc = correr(["-e"] + opciones + ["-o", str(exe), nombre], nombre)
            if not rc:
                r = subprocess.run([str(exe), f"--psl-report={psl}"],
                                   capture_output=True, text=True, timeout=7200)
                salida = (r.stdout + r.stderr).rstrip()
                if salida:
                    print(salida)
                rc = r.returncode
                if rc:
                    print(f"  --> {nombre} devolvio {rc}")
        if psl.exists():
            import json
            s = json.loads(psl.read_text())["summary"]
            if s["assert"] or s["cover"]:
                print(f"  PSL: {s['assert']} aserciones ({s['assert-failure']} violadas), "
                      f"{s['cover']} coberturas ({s['cover-pass']} alcanzadas)")
                if s["assert-failure"] or s["cover-pass"] < s["cover"]:
                    print("  --> PSL: aserciones violadas o coberturas sin alcanzar")
                    rc = rc or 1
        if rc:
            fallidos.append(nombre)

    print("\n=== resumen ===")
    if fallidos:
        print("bancos con fallos: " + ", ".join(fallidos))
        return 1
    print("todos los bancos pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
