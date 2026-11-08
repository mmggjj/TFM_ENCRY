#!/usr/bin/env python3
"""Campana de entropia del motor: bits crudos por I2C con el verificador.

El ESP32 con firmware/verificador hace de puente: `kd N` fija CFG_KD y
`crudo N` lanza N capturas de 4096 bits (modo test, sw0 arriba) y vuelca
cada una en una trama R con CRC32, precedida de `crudo i kd K ms M` (el
tiempo de llenado). Por cada divisor se guardan los trozos con CRC bueno
en kd<K>.bin y, con --90b, se pasan por la bateria SP 800-90B del NIST
(analysis/entropia_90b.py, no-IID, un bit por simbolo).

    python analysis/campana_motor.py --puerto /dev/ttyUSB0 --kd 8 10 12 14 --bits 1000000
    python analysis/campana_motor.py --reparsear results/motor_campana/<sesion>/serie.log --90b
    python analysis/campana_motor.py --simulador firmware/host_check/build/consola_verificador ...

Los trozos NO son contiguos entre si: entre dos capturas se pierden los
bits que llegan mientras el ESP32 lee el buffer. SP 800-90B pide 10^6
muestras consecutivas; aqui son 245 bloques de 4096 consecutivas. Lo que
supone para la lectura, en docs/puesta_en_marcha_fpga.md.

El log serie se guarda entero y el analisis se hace sobre el log, nunca
durante la captura. La frecuencia de ro2 que se infiere del tiempo de
llenado (4096 * 2^K / t) tiene la resolucion del tick del ESP32 (1 ms) mas
el sondeo (1 o 10 ms) y la lectura I2C: solo vale con capturas de
cientos de ms o mas. Para la frecuencia esta el display de la placa.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import subprocess
import sys
import time
import zlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "results" / "motor_campana"
BITS_TROZO = 4096
LOTE = 8                     # capturas por orden "crudo"

RE_TRAMA = re.compile(r"^F([A-Z])([0-9a-f]{4})([0-9a-f]*)([0-9a-f]{8})\s*$")
RE_KD = re.compile(r"^kd (\d+) leido (\d+) (ok|IGNORADO)")
RE_CRUDO = re.compile(r"^crudo (\d+) kd (\d+) ms (\d+)")
RE_ID = re.compile(r"^id 0x([0-9a-f]{2}) version 0x([0-9a-f]{2}) .* test=(\d)")


# ---------------------------------------------------------------- transporte
class Serie:
    """Puerto serie (pyserial; vale una URL como socket://host:puerto)."""

    def __init__(self, puerto: str, resetear: bool):
        import serial
        self.s = serial.serial_for_url(puerto, 115200, timeout=0.2)
        if resetear:
            self.s.dtr = False          # IO0 alto: arranque normal
            self.s.rts = True
            time.sleep(0.1)
            self.s.rts = False

    def leer(self) -> bytes:
        return self.s.read(4096)

    def escribir(self, b: bytes) -> None:
        self.s.write(b)

    def cerrar(self) -> None:
        self.s.close()


class Simulador:
    """El verificador compilado en el PC contra el modelo del motor
    (firmware/host_check/consola_verificador.c), por tuberias."""

    def __init__(self, ruta: str):
        import os
        self.p = subprocess.Popen([ruta], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, bufsize=0)
        os.set_blocking(self.p.stdout.fileno(), False)

    def leer(self) -> bytes:
        try:
            b = self.p.stdout.read(65536)
        except BlockingIOError:
            b = None
        if not b:
            time.sleep(0.01)
            return b""
        return b

    def escribir(self, b: bytes) -> None:
        self.p.stdin.write(b)
        self.p.stdin.flush()

    def cerrar(self) -> None:
        self.p.stdin.close()
        self.p.wait(timeout=10)


# ------------------------------------------------------------------ captura
def capturar(t, log: Path, kds: list[int], trozos: int, arranque: float,
             plazo_lote: float) -> None:
    with log.open("w", encoding="utf-8") as f:
        pendiente = ""

        def escuchar(hasta, seg: float) -> str | None:
            """Lee hasta que una linea cumpla `hasta` o venza el plazo."""
            nonlocal pendiente
            fin = time.time() + seg
            while True:
                *lineas, resto = pendiente.split("\n")
                for i, ln in enumerate(lineas):
                    if hasta(ln.strip()):
                        # lo que viene detras es para la espera siguiente
                        pendiente = "\n".join(lineas[i + 1:] + [resto])
                        return ln.strip()
                pendiente = resto
                if time.time() >= fin:
                    return None
                b = t.leer()
                if b:
                    texto = b.decode("utf-8", errors="replace")
                    f.write(texto)
                    f.flush()
                    pendiente += texto

        def orden(o: str) -> None:
            f.write(f"\n>>> {o}\n")
            f.flush()
            t.escribir((o + "\n").encode())

        escuchar(lambda ln: ln.startswith("verificador listo"), arranque)
        orden("id")
        ln = escuchar(lambda ln: RE_ID.match(ln) is not None
                      or "sin respuesta I2C" in ln, 5)
        m = RE_ID.match(ln or "")
        if not m:
            raise SystemExit(f"el motor no responde a 'id' ({ln!r}); log: {log}")
        if m.group(3) != "1":
            raise SystemExit("modo test apagado (sw0): CAPTURA se lee como ceros")
        print(f"motor: ID 0x{m.group(1)}, VERSION 0x{m.group(2)}, modo test")

        for kd in kds:
            orden(f"kd {kd}")
            ln = escuchar(lambda ln: RE_KD.match(ln) is not None or ln.startswith("kd:"), 5)
            mk = RE_KD.match(ln or "")
            if not mk or mk.group(3) != "ok":
                raise SystemExit(f"kd {kd} no se escribio ({ln!r})")
            hechos = 0
            t0 = time.time()
            while hechos < trozos:
                n = min(LOTE, trozos - hechos)
                orden(f"crudo {n}")
                ult = f"crudo {n - 1} kd {kd} "
                ln = escuchar(lambda ln: ln.startswith(ult) or ln.startswith("crudo:"),
                              plazo_lote * n)
                if ln is None or ln.startswith("crudo:"):
                    raise SystemExit(f"kd {kd}: la captura fallo ({ln!r}); log: {log}")
                # la trama va en la linea siguiente
                escuchar(lambda ln: ln.startswith("FR"), 10)
                hechos += n
                print(f"\rkd {kd}: {hechos}/{trozos} trozos, {time.time() - t0:.0f} s",
                      end="", flush=True)
            print()


# ------------------------------------------------------------------ parseo
def parsear(texto: str) -> dict[int, dict]:
    """Del log integro: por divisor, los trozos con CRC bueno y los tiempos."""
    por_kd: dict[int, dict] = {}
    kd = None
    espera_trama = False
    for linea in texto.splitlines():
        linea = linea.strip()
        if m := RE_KD.match(linea):
            if m.group(3) == "ok":
                kd = int(m.group(2))
                por_kd.setdefault(kd, {"datos": bytearray(), "ms": [], "crc_malo": 0,
                                       "huerfanas": 0, "errores": []})
            continue
        if m := RE_CRUDO.match(linea):
            if kd is None or int(m.group(2)) != kd:
                raise ValueError(f"linea de crudo con kd {m.group(2)} sin 'kd' previo: {linea}")
            por_kd[kd]["ms"].append(int(m.group(3)))
            espera_trama = True
            continue
        if linea.startswith("crudo:") and kd is not None:
            por_kd[kd]["errores"].append(linea)
            continue
        m = RE_TRAMA.match(linea)
        if not m or m.group(1) != "R":
            continue
        if kd is None or not espera_trama:
            if kd is not None:
                por_kd[kd]["huerfanas"] += 1
            continue
        espera_trama = False
        n = int(m.group(2), 16)
        carga_hex = m.group(3)
        if len(carga_hex) != 2 * n or n != BITS_TROZO // 8:
            por_kd[kd]["crc_malo"] += 1
            continue
        carga = bytes.fromhex(carga_hex)
        if zlib.crc32(carga) & 0xFFFFFFFF != int(m.group(4), 16):
            por_kd[kd]["crc_malo"] += 1
            continue
        por_kd[kd]["datos"].extend(carga)
    return por_kd


def resumir(por_kd: dict[int, dict], carpeta: Path, con_90b: bool) -> list[dict]:
    filas = []
    for kd, d in sorted(por_kd.items()):
        nombre = f"kd{kd:02d}"
        fich = carpeta / f"{nombre}.bin"
        fich.write_bytes(bytes(d["datos"]))
        trozos = len(d["datos"]) * 8 // BITS_TROZO
        ms = sorted(d["ms"])
        med = ms[len(ms) // 2] if ms else float("nan")
        unos = sum(bin(b).count("1") for b in d["datos"])
        fila = {
            "kd": kd, "trozos": trozos, "bits": len(d["datos"]) * 8,
            "crc_malo": d["crc_malo"], "tramas_huerfanas": d["huerfanas"],
            "errores": len(d["errores"]),
            "ms_mediana": med, "ms_min": ms[0] if ms else "", "ms_max": ms[-1] if ms else "",
            # f_ro2 = 4096 * 2^kd / t; con t de pocos ms no significa nada
            "f_ro2_MHz": (BITS_TROZO * 2 ** kd / (med / 1000) / 1e6) if ms and med >= 100 else "",
            "fraccion_unos": unos / (len(d["datos"]) * 8) if d["datos"] else "",
            "fichero": fich.name,
        }
        print(f"kd {kd}: {trozos} trozos ({fila['bits']} bits), CRC malos {d['crc_malo']}, "
              f"huerfanas {d['huerfanas']}, errores {len(d['errores'])}, "
              f"llenado mediana {med} ms, unos {fila['fraccion_unos']}")
        for e in d["errores"]:
            print(f"   {e}")
        if con_90b:
            sys.path.insert(0, str(RAIZ / "analysis"))
            import entropia_90b as e90
            e90.DIR90B = carpeta / "entropia90b"
            e90.BITS = e90.DIR90B / "bits"
            e90.BITS.mkdir(parents=True, exist_ok=True)
            if fila["bits"] < 1_000_000:
                print(f"   AVISO: {fila['bits']} bits < 10^6 que pide SP 800-90B")
            r = e90.ejecutar(nombre, e90.desempaquetar(nombre, fich), "noniid", "b1")
            fila["exit_90b"] = r["exit"]
            # el JSON lleva hAssessed dentro del ultimo caso de testCases
            fila["h_min_90b"] = next((v for k, v in r.items() if k.endswith("hAssessed")), "")
        filas.append(fila)
    return filas


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    fuente = ap.add_mutually_exclusive_group(required=True)
    fuente.add_argument("--puerto", help="puerto serie del ESP32 (o URL de pyserial)")
    fuente.add_argument("--simulador", help="consola del verificador compilada en el PC")
    fuente.add_argument("--reparsear", type=Path, help="log serie de una sesion anterior")
    ap.add_argument("--kd", type=int, nargs="+", default=[10])
    ap.add_argument("--bits", type=int, default=1_000_000, help="bits por divisor")
    ap.add_argument("--sin-reset", action="store_true")
    ap.add_argument("--arranque", type=float, default=5.0, help="s de espera al arrancar")
    ap.add_argument("--plazo", type=float, default=0.0,
                    help="s por captura (0: 4096*2^kd a 50 MHz, x4, minimo 5 s)")
    ap.add_argument("--sesion", default=time.strftime("%Y%m%d_%H%M%S"))
    ap.add_argument("--carpeta", type=Path, default=None,
                    help="carpeta de salida (por defecto results/motor_campana/<sesion>)")
    ap.add_argument("--90b", dest="con_90b", action="store_true",
                    help="pasa cada divisor por ea_non_iid (bits)")
    args = ap.parse_args()

    if args.reparsear:
        carpeta = args.reparsear.parent
        log = args.reparsear
    else:
        carpeta = args.carpeta or DESTINO / args.sesion
        carpeta.mkdir(parents=True, exist_ok=True)
        log = carpeta / "serie.log"
        trozos = math.ceil(args.bits / BITS_TROZO)
        if any(not 0 <= k <= 24 for k in args.kd):
            raise SystemExit("kd de 0 a 24")
        plazo = args.plazo or max(5.0, 4 * BITS_TROZO * 2 ** max(args.kd) / 50e6)
        t = Simulador(args.simulador) if args.simulador else Serie(args.puerto, not args.sin_reset)
        try:
            capturar(t, log, args.kd, trozos, args.arranque, plazo)
        finally:
            t.cerrar()

    por_kd = parsear(log.read_text(encoding="utf-8", errors="replace"))
    if not por_kd:
        print("el log no tiene ningun divisor escrito con 'kd'")
        return 1
    filas = resumir(por_kd, carpeta, args.con_90b)
    with (carpeta / "resumen.csv").open("w", newline="", encoding="utf-8") as fh:
        cols = list(dict.fromkeys(c for f in filas for c in f))
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)
    print(f"log integro: {log}\nresumen: {carpeta / 'resumen.csv'}")
    malos = sum(f["crc_malo"] + f["tramas_huerfanas"] + f["errores"] for f in filas)
    return 0 if malos == 0 and all(f.get("exit_90b", 0) == 0 for f in filas) else 1


if __name__ == "__main__":
    sys.exit(main())
