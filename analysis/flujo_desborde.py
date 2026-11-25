#!/usr/bin/env python3
"""Trozos de bits consecutivos a CFG_KD bajo con el flujo continuo y sin
buffer de captura (la Basys 2, docs/basys2.md).

Por debajo de CFG_KD ~12 el flujo llega mas deprisa de lo que el ESP32
saca por la UART y la FIFO de 256 B se desborda en milisegundos. Lo que
el verificador manda antes del desbordamiento son tramas completas con
CRC y numeradas: bits consecutivos y validos (la FIFO se para al
desbordarse, docs/mapa_registros.md). Repitiendo `flujo` se juntan cientos
de trozos independientes de ~2000-3000 bits, que es lo que necesita el
estimador de jitter (jitter_autocorrelacion.py --npz). NO sirven para SP
800-90B, que pide 10^6 consecutivos.

    python flujo_desborde.py --puerto /dev/ttyUSB0 --kd 7 8 9 10 --bits 1000000

Log serie integro en results/motor_campana/<sesion>/serie.log y un
kdNN_trozos.npz por divisor (bytes concatenados y longitud de cada trozo).
"""
from __future__ import annotations

import argparse
import re
import time
import zlib
from pathlib import Path

import numpy as np
import serial

RAIZ = Path(__file__).resolve().parent.parent
TRAMA = re.compile(r"^FC([0-9a-f]{4})([0-9a-f]*)([0-9a-f]{8})\s*$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", required=True)
    ap.add_argument("--kd", type=int, nargs="+", required=True)
    ap.add_argument("--bits", type=int, default=1_000_000, help="bits por divisor (suma de trozos)")
    ap.add_argument("--sesion", default=time.strftime("flujo_desborde_%Y%m%d_%H%M%S"))
    a = ap.parse_args()
    carpeta = RAIZ / "results" / "motor_campana" / a.sesion
    carpeta.mkdir(parents=True, exist_ok=True)
    log = (carpeta / "serie.log").open("w", encoding="utf-8")

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

        s.reset_input_buffer()
        for kd in a.kd:
            r = orden(f"kd {kd}", re.compile(r"^kd "), 5)
            if not any(f"leido {kd} ok" in l for l in r):
                raise RuntimeError(f"kd {kd} no se escribio: {r}")
            trozos, n_bits, ejec, malas, t0 = [], 0, 0, 0, time.time()
            while n_bits < a.bits:
                lineas = orden("flujo 1000000", re.compile(r"^flujo (fin|:)|^flujo: "), 30)
                ejec += 1
                carga, esperada, valido = bytearray(), 0, True
                for l in lineas:
                    m = TRAMA.match(l)
                    if not m:
                        continue
                    datos = bytes.fromhex(m.group(2))
                    if len(datos) != int(m.group(1), 16) or zlib.crc32(datos) & 0xFFFFFFFF != int(m.group(3), 16):
                        valido = False
                        break
                    if int.from_bytes(datos[:4], "little") != esperada:
                        valido = False
                        break
                    esperada += 1
                    carga += datos[4:]
                fin = [l for l in lineas if l.startswith("flujo")][-1]
                # Solo trozos cortados por desbordamiento (o completos): un
                # error de bus o una trama rota invalida la ejecucion entera.
                if valido and ("DESBORDADO" in fin or " ok" in fin) and len(carga) >= 64:
                    trozos.append(bytes(carga))
                    n_bits += 8 * len(carga)
                else:
                    malas += 1
            longitudes = np.array([len(t) for t in trozos])
            np.savez(carpeta / f"kd{kd:02d}_trozos.npz",
                     datos=np.frombuffer(b"".join(trozos), dtype=np.uint8), longitudes=longitudes, kd=kd)
            print(f"kd {kd}: {len(trozos)} trozos, {n_bits} bits, bytes por trozo "
                  f"{longitudes.min()}-{longitudes.max()} (mediana {int(np.median(longitudes))}), "
                  f"{ejec} ejecuciones, {malas} descartadas, {time.time() - t0:.0f} s")
    log.close()
    print(f"log integro: {carpeta / 'serie.log'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
