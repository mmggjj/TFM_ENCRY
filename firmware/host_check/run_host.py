#!/usr/bin/env python3
"""Banco en el PC del firmware del motor: verificador y medidor contra el
motor simulado, sin placa ni toolchain de Espressif.

    python3 firmware/host_check/run_host.py --mbedtls RUTA_FUENTES_MBEDTLS

RUTA_FUENTES_MBEDTLS es un arbol de mbedtls 3.x (vale el de ESP-IDF,
$IDF_PATH/components/mbedtls/mbedtls, que es la misma version que corre
en el chip); si no se da y hay IDF_PATH, se toma de ahi. Se compila con
cmake en firmware/host_check/build/mbedtls la primera vez. Sin mbedtls
solo corre el verificador, con el CMAC falso de mbedtls_stub.c, y el
medidor se salta y se dice.

Hace falta gcc, cmake y el paquete Python "cryptography" (para
verifica_lecturas.py). Todo lo que sale se escribe tal cual en
results/host_check.log; las rutas de maquina se enmascaran. Con --sanear
se compila con ASan y UBSan (fugas, desbordamientos, comportamiento
indefinido): encontro una fuga de la clave al "reiniciar" el medidor.

Pasos:
  1. cabeceras simuladas (mk_stubs.py)
  2. test_verificador: compila y corre
  3. test_medidor: compila, corre y guarda su salida en
     build/medidor_consola.log
  4. analysis/verifica_lecturas.py sobre ese log: lo que encuentra tiene
     que coincidir con lo que el banco dice haber mandado
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
FW = Path("firmware")
HC = FW / "host_check"
BUILD = HC / "build"
LOG = Path("results") / "host_check.log"

CFLAGS = ["-std=gnu11", "-Wall", "-Wextra", "-Wno-unused-parameter", "-O1"]

salida_log: list[str] = []


def decir(texto: str = "") -> None:
    print(texto)
    salida_log.append(texto)


def correr(cmd: list[str], mascara: dict[str, str], **kw) -> subprocess.CompletedProcess:
    mostrado = " ".join(cmd)
    for k, v in mascara.items():
        mostrado = mostrado.replace(k, v)
    decir(f"$ {mostrado}")
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    texto = r.stdout + r.stderr
    for k, v in mascara.items():
        texto = texto.replace(k, v)
    if texto:
        decir(texto.rstrip("\n"))
    decir(f"(rc={r.returncode})")
    return r


def preparar_mbedtls(fuentes: Path, mascara: dict[str, str]) -> tuple[list[str], list[str]] | None:
    """Devuelve (-I..., libs) de un mbedtls compilado, o None si no se puede."""
    inc = fuentes / "include"
    if not (inc / "mbedtls" / "pk.h").is_file():
        decir(f"mbedtls: no hay include/mbedtls/pk.h en {mascara.get(str(fuentes), fuentes)}")
        return None
    bdir = BUILD / "mbedtls"
    libs = [bdir / "library" / f"lib{n}.a" for n in ("mbedx509", "mbedcrypto")]
    if not all(l.is_file() for l in libs):
        if shutil.which("cmake") is None:
            decir("mbedtls: falta cmake para compilarlo")
            return None
        r = correr(["cmake", "-S", str(fuentes), "-B", str(bdir), "-DENABLE_TESTING=OFF",
                    "-DENABLE_PROGRAMS=OFF", "-DGEN_FILES=OFF", "-DCMAKE_BUILD_TYPE=Release"], mascara)
        if r.returncode != 0:
            return None
        r = correr(["cmake", "--build", str(bdir), "-j", str(os.cpu_count() or 2)], mascara)
        if r.returncode != 0:
            return None
    return (["-I", str(inc)], [str(l) for l in libs])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mbedtls", type=Path, default=None, help="fuentes de mbedtls 3.x")
    ap.add_argument("--cc", default="gcc")
    ap.add_argument("--sanear", action="store_true",
                    help="compila con ASan y UBSan: fugas, desbordamientos y UB en el firmware")
    args = ap.parse_args()
    if args.sanear:
        # Sin salida temprana ni recuperacion: cualquier aviso es fallo. ASAN_OPTIONS
        # para que la salida del programa no se pierda en el buffer al abortar.
        CFLAGS.extend(["-g", "-fsanitize=address,undefined", "-fno-sanitize-recover=all"])
        os.environ.setdefault("ASAN_OPTIONS", "detect_leaks=1")

    os.chdir(RAIZ)
    BUILD.mkdir(parents=True, exist_ok=True)
    Path("results").mkdir(exist_ok=True)

    fuentes = args.mbedtls
    if fuentes is None and os.environ.get("IDF_PATH"):
        fuentes = Path(os.environ["IDF_PATH"]) / "components" / "mbedtls" / "mbedtls"
    mascara: dict[str, str] = {str(RAIZ): "."}
    if fuentes is not None:
        fuentes = fuentes.resolve()
        mascara[str(fuentes)] = "$MBEDTLS"

    decir("Banco en el PC del firmware del motor (run_host.py)" + (" con ASan+UBSan" if args.sanear else ""))
    decir()

    mbed = preparar_mbedtls(fuentes, mascara) if fuentes is not None else None
    if mbed is None:
        decir("mbedtls real: NO disponible; el verificador usa mbedtls_stub.c y el medidor se salta")
    else:
        decir("mbedtls real: " + mascara.get(str(fuentes), str(fuentes)))
    decir()

    fallos = 0
    stubs = BUILD / "stubs"
    r = correr([sys.executable, str(HC / "mk_stubs.py"), str(stubs)] + ([] if mbed is None else ["--sin-mbedtls"]), mascara)
    fallos += r.returncode != 0

    comunes = [str(FW / "componentes" / "motor_i2c" / "motor_i2c.c"), str(HC / "motor_sim.c"),
               str(HC / "plataforma_sim.c")]
    incs = ["-I", str(stubs), "-I", str(FW / "componentes" / "motor_i2c" / "include")]

    decir("\n== test_verificador ==")
    exe = BUILD / "test_verificador"
    cmd = [args.cc] + CFLAGS + incs + ["-I", str(FW / "verificador" / "main"),
           str(HC / "test_verificador.c")] + comunes
    cmd += [str(HC / "mbedtls_stub.c")] if mbed is None else mbed[0] + mbed[1]
    cmd += ["-o", str(exe)]
    r = correr(cmd, mascara)
    if r.returncode != 0:
        fallos += 1
    else:
        r = correr([str(exe)], mascara)
        fallos += r.returncode != 0

    if mbed is not None:
        decir("\n== test_medidor ==")
        exe = BUILD / "test_medidor"
        cmd = [args.cc] + CFLAGS + incs + mbed[0] + ["-I", str(FW / "medidor" / "main"),
               str(HC / "test_medidor.c"), str(FW / "medidor" / "main" / "lectura.c")] + comunes + mbed[1]
        cmd += ["-o", str(exe)]
        r = correr(cmd, mascara)
        if r.returncode != 0:
            fallos += 1
        else:
            r = correr([str(exe)], mascara)
            fallos += r.returncode != 0
            consola = BUILD / "medidor_consola.log"
            consola.write_text(r.stdout, encoding="utf-8")
            esperado = re.search(r"^esperado: (.*)$", r.stdout, re.M)

            decir("\n== verifica_lecturas.py sobre la salida del medidor ==")
            decir("(el banco planta a proposito una lectura manipulada y una repetida: "
                  "el script debe devolver rc=1 y contarlas)")
            r = correr([sys.executable, "analysis/verifica_lecturas.py", str(consola), "--permitir-cambio"], mascara)
            resumen = re.search(r"^resumen: (.*)$", r.stdout, re.M)
            if esperado is None or resumen is None:
                decir("  [FALLO] faltan las lineas 'esperado:' o 'resumen:'")
                fallos += 1
            else:
                esp = dict(p.split("=") for p in esperado.group(1).split())
                enc = dict(p.split("=") for p in resumen.group(1).split())
                for k, v in esp.items():
                    ok = enc.get(k) == v
                    decir(f"  [{'ok ' if ok else 'FALLO'}] {k}: el banco mando {v}, el PC encontro {enc.get(k)}")
                    fallos += not ok
                ok = enc.get("crc_malo") == "0"
                decir(f"  [{'ok ' if ok else 'FALLO'}] crc_malo: {enc.get('crc_malo')}")
                fallos += not ok

    decir(f"\nrun_host: {fallos} fallos")
    LOG.write_text("\n".join(salida_log) + "\n", encoding="utf-8")
    decir(f"log integro: {LOG}")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
