#!/usr/bin/env python3
"""Prueba de reinicios de la fuente en la FPGA (SP 800-90B, 3.1.4), como la
del ESP32 (reinicios_90b.py) para poder compararlas.

Cada ciclo: se reprograma la FPGA por JTAG (djtgcfg, solo la FPGA: la
Platform Flash no se toca), lo que reinicia el diseño y arranca los anillos
desde cero; despues, por el ESP32 con el verificador, CFG_KD y los primeros
--bytes del flujo continuo. Los bits NO son los de los primeros
nanosegundos tras el arranque sino los primeros del flujo, que empieza unos
cientos de ms despues de configurar (se dice al escribirlo).

    python reinicios_fpga.py capturar --puerto /dev/ttyUSB0 --bit <bitstream> --n 1000
    python reinicios_fpga.py analizar --sesion <carpeta> --h-i 0.846

Captura: results/fpga_reinicios/<sesion>/{bloques.npy, serie.log (local),
tiempos.csv}. Analisis: ea_restart (modo bit, 1000 x 1000) y la comprobacion
directa de reinicios_90b.py, en resumen.md.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import zlib
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
DIR = RAIZ / "results" / "fpga_reinicios"
TRAMA = re.compile(r"^FC([0-9a-f]{4})([0-9a-f]*)([0-9a-f]{8})\s*$")


def programar(bit: Path, dispositivo: str) -> float:
    entorno = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
    t0 = time.time()
    r = subprocess.run(["djtgcfg", "prog", "-d", dispositivo, "-i", "0", "-f", str(bit)],
                       capture_output=True, text=True, errors="replace", env=entorno, timeout=120)
    if "Programming succeeded" not in r.stdout:
        raise RuntimeError(f"djtgcfg: {r.stdout}{r.stderr}")
    return time.time() - t0


def capturar(a) -> int:
    import serial
    carpeta = DIR / a.sesion
    carpeta.mkdir(parents=True, exist_ok=True)
    entorno = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
    enum = subprocess.run(["djtgcfg", "enum"], capture_output=True, text=True, errors="replace", env=entorno).stdout
    dispositivo = "SN:" + re.search(r"Serial Number:\s*(\S+)", enum).group(1)
    log = (carpeta / "serie.log").open("a", encoding="utf-8")
    tiempos = (carpeta / "tiempos.csv").open("a", encoding="utf-8")
    bloques = []
    previos = carpeta / "bloques.npy"
    if previos.exists():
        bloques = list(np.load(previos))
        print(f"continuando: {len(bloques)} arranques ya capturados")

    with serial.Serial(a.puerto, 115200, timeout=0.2) as s:
        def orden(texto: str, hasta: re.Pattern, plazo: float) -> list[str]:
            log.write(f"\n>>> {texto}\n")
            s.write((texto + "\n").encode())
            lineas, resto, fin = [], "", time.time() + plazo
            while time.time() < fin:
                trozo = s.read(4096).decode("utf-8", errors="replace")
                if not trozo:
                    continue
                log.write(trozo)
                resto += trozo
                *completas, resto = resto.split("\n")
                lineas += [l.strip() for l in completas]
                if any(hasta.search(l) for l in completas):
                    return lineas
            raise RuntimeError(f"sin respuesta a '{texto}'")

        fallos = 0
        while len(bloques) < a.n:
            i = len(bloques)
            t_prog = programar(Path(a.bit), dispositivo)
            t0 = time.time()
            s.reset_input_buffer()
            try:
                r = orden(f"kd {a.kd}", re.compile(r"^kd "), 5)
                if not any(f"leido {a.kd} ok" in l for l in r):
                    raise RuntimeError(f"kd: {r}")
                lineas = orden(f"flujo {a.bytes}", re.compile(r"^flujo (fin|:)|^flujo: "), 30)
            except RuntimeError as e:
                fallos += 1
                log.write(f"\n# arranque {i}: descartado ({e})\n")
                if fallos > 20:
                    raise
                continue
            carga, esperada, ok = bytearray(), 0, True
            for l in lineas:
                m = TRAMA.match(l)
                if not m:
                    continue
                datos = bytes.fromhex(m.group(2))
                if (len(datos) != int(m.group(1), 16) or zlib.crc32(datos) & 0xFFFFFFFF != int(m.group(3), 16)
                        or int.from_bytes(datos[:4], "little") != esperada):
                    ok = False
                    break
                esperada += 1
                carga += datos[4:]
            fin = [l for l in lineas if l.startswith("flujo")][-1]
            if not ok or " ok" not in fin or len(carga) != a.bytes:
                fallos += 1
                log.write(f"\n# arranque {i}: descartado ({fin})\n")
                continue
            bloques.append(np.frombuffer(bytes(carga), dtype=np.uint8))
            tiempos.write(f"{i},{t_prog:.2f},{time.time() - t0:.3f}\n")
            if (i + 1) % 25 == 0:
                np.save(previos, np.stack(bloques))
                tiempos.flush()
                log.flush()
                print(f"{i + 1} arranques, {fallos} descartados, programar {t_prog:.1f} s", flush=True)
    np.save(previos, np.stack(bloques))
    print(f"hecho: {len(bloques)} arranques en {carpeta}, {fallos} descartados")
    return 0


def analizar(a) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from reinicios_90b import directa, ea_restart, flujo_comun, veredicto
    carpeta = DIR / a.sesion
    b = np.load(carpeta / "bloques.npy")
    n = min(len(b), 1000)
    b = b[:n]
    bits = np.unpackbits(b, axis=1)[:, :1000]
    salida = [f"# Reinicios de la FPGA: {a.sesion}", "",
              f"{n} arranques; {b.shape[1]} bytes por arranque; H_I = {a.h_i}", ""]
    d = directa(b)
    fc = flujo_comun(b)
    salida += ["## Comprobacion directa (como reinicios_90b.py)", "",
               f"- arranques distintos: {d['unicos']} de {d['n']} (primeros 8 bytes: {d['unicos8']})",
               f"- distancia de Hamming entre arranques: minima {d['dist_min']} (esperada ~{d['dist_min_esperada']:.0f}), "
               f"media {d['dist_media']:.1f} (esperada {d['dist_esperada']:.0f}), "
               f"desviacion {d['dist_sd']:.2f} (esperada {d['dist_sd_esperada']:.2f})",
               f"- columna mas desviada: {d['col_peor']} (|z| {d['z_max']:.2f}, p corregida {d['p_col_corr']:.3g})",
               f"- primer byte uniforme: p = {d['chi_byte0']:.3g}",
               f"- arranques que son el mismo flujo desde otro punto: {fc['relaciones']} relaciones, "
               f"{fc['componentes']} componentes (mayor {fc['comp_max']}); repeticion maxima {fc['repe_max']}", ""]
    if not a.sin_nist and n == 1000:
        r = ea_restart(bits.astype(np.uint8), 1, a.h_i, carpeta, "b1")
        salida += ["## ea_restart (modo bit, 1000 x 1000)", "", f"exit {r['exit']}: {veredicto(r['texto'])}",
                   "(log integro en ea_restart_b1.log)", ""]
    (carpeta / "resumen.md").write_text("\n".join(salida), encoding="utf-8")
    print("\n".join(salida))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="accion", required=True)
    c = sub.add_parser("capturar")
    c.add_argument("--puerto", required=True)
    c.add_argument("--bit", required=True)
    c.add_argument("--n", type=int, default=1000)
    c.add_argument("--kd", type=int, default=14)
    c.add_argument("--bytes", type=int, default=128)
    c.add_argument("--sesion", default=time.strftime("basys2_%Y%m%d_%H%M%S"))
    z = sub.add_parser("analizar")
    z.add_argument("--sesion", required=True)
    z.add_argument("--h-i", type=float, required=True, help="H inicial (no-IID) de la misma fuente")
    z.add_argument("--sin-nist", action="store_true")
    a = ap.parse_args()
    return capturar(a) if a.accion == "capturar" else analizar(a)


if __name__ == "__main__":
    sys.exit(main())
