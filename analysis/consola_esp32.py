#!/usr/bin/env python3
"""Consola serie minima para el verificador del ESP32, sin filtrar nada.

Abre el puerto a 115200 (la unica velocidad fiable con el CP2102 en los
montajes del autor), resetea la placa por RTS, guarda TODO lo que llega
en un log integro y manda las ordenes que se le pidan, esperando entre
ellas. Las tramas 'F' hacia el PC (tipo, longitud, carga, CRC32) se
extraen del log y se comprueba su CRC; las cargas validas se guardan en
binario por tipo para el analisis posterior (misma cadena que los bits
del motor).

    python consola_esp32.py --puerto COM7 --ordenes "id" "esp 20" --espera 3

Regla del proyecto: el log serie se guarda entero; el parseo se hace
sobre el log, nunca en captura.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import zlib
from pathlib import Path

import serial

RESULTS = Path(__file__).resolve().parent.parent / "results"
TRAMA = re.compile(r"^F([A-Z])([0-9a-f]{4})([0-9a-f]*)([0-9a-f]{8})\s*$")


def resetear(s: serial.Serial) -> None:
    """Reset por RTS (EN) con IO0 alto: arranque normal, no bootloader."""
    s.dtr = False          # IO0 en alto
    s.rts = True           # EN en bajo
    time.sleep(0.1)
    s.rts = False
    time.sleep(0.05)


def main() -> int:
    # La consola de Windows redirigida es cp1252: la basura del arranque
    # (bytes invalidos -> U+FFFD) no debe tumbar la captura.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", default="COM7")
    ap.add_argument("--ordenes", nargs="*", default=["id"])
    ap.add_argument("--espera", type=float, default=2.0,
                    help="segundos de escucha tras cada orden")
    ap.add_argument("--arranque", type=float, default=3.0,
                    help="segundos de escucha tras el reset")
    ap.add_argument("--sesion", default=time.strftime("%Y%m%d_%H%M%S"))
    ap.add_argument("--sin-reset", action="store_true")
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    log = RESULTS / f"esp32_consola_{args.sesion}.log"

    with serial.Serial(args.puerto, 115200, timeout=0.2) as s, log.open("w", encoding="utf-8") as f:
        def escuchar(seg: float) -> str:
            fin = time.time() + seg
            acumulado = ""
            while time.time() < fin:
                trozo = s.read(4096)
                if trozo:
                    texto = trozo.decode("utf-8", errors="replace")
                    acumulado += texto
                    f.write(texto)
                    f.flush()
            return acumulado

        if not args.sin_reset:
            resetear(s)
        salida = escuchar(args.arranque)
        print(f"--- arranque ({len(salida)} caracteres) ---")
        print(salida.rstrip())

        for orden in args.ordenes:
            f.write(f"\n>>> {orden}\n"); f.flush()
            s.write((orden + "\n").encode())
            salida = escuchar(args.espera)
            print(f"--- {orden} ---")
            print(salida.rstrip())

    # Tramas: se extraen del log completo y se comprueba el CRC32.
    texto = log.read_text(encoding="utf-8", errors="replace")
    cargas: dict[str, bytearray] = {}
    buenas = malas = 0
    for linea in texto.splitlines():
        m = TRAMA.match(linea.strip())
        if not m:
            continue
        tipo, n_hex, carga_hex, crc_hex = m.groups()
        n = int(n_hex, 16)
        if len(carga_hex) != 2 * n:
            malas += 1
            continue
        carga = bytes.fromhex(carga_hex)
        if zlib.crc32(carga) & 0xFFFFFFFF != int(crc_hex, 16):
            malas += 1
            continue
        buenas += 1
        cargas.setdefault(tipo, bytearray()).extend(carga)
    for tipo, datos in cargas.items():
        destino = RESULTS / f"esp32_tramas_{tipo}_{args.sesion}.bin"
        destino.write_bytes(datos)
        print(f"tramas tipo {tipo}: {len(datos)} bytes -> {destino.name}")
    print(f"tramas con CRC correcto: {buenas}; incorrectas: {malas}")
    print(f"log integro: {log}")
    return 0 if malas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
