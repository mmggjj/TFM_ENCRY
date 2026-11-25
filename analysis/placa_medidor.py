#!/usr/bin/env python3
"""Sesion con el medidor en una placa real por el puerto serie.

El medidor (firmware/medidor) compilado con MOTOR_SIMULADO corre en un
ESP32-C3 de verdad sin el motor: la unica diferencia con el banco en host
y con QEMU es que aqui la NVS es la flash del chip, los reinicios son
fisicos (RTS) y los tiempos son los de los aceleradores del silicio. Lo
que se mide:

  1. arranque y 'id' (pila libre, contador de arranques en NVS);
  2. 'sembrar' y 'clave': tiempo de generar la P-256 con aleatorio del
     motor (simulado) y guardarla en NVS;
  3. 'publica', 'csr' y N lecturas firmadas: tiempo por firma;
  4. reinicio fisico por RTS: la clave vuelve de la NVS, el contador de
     arranques sube y la secuencia de la primera lectura supera a la
     ultima de antes;
  5. 'olvidar' y reinicio: sin clave, 'lectura' se niega.

El log que se guarda es la salida serie integra, tal cual la emite el
chip, con las ordenes enviadas ('>') y las comprobaciones con una marca de
tiempo relativa en segundos. Las tramas F que lleva
las verifica despues analysis/verifica_lecturas.py (con --permitir-cambio
no hace falta: la clave es la misma antes y despues del reinicio; 'olvidar'
y una clave nueva al final la cambian a proposito).

    python analysis/placa_medidor.py COM25 [--lecturas 5] [--salida results/placa_medidor_esp32c3.log]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import serial


class Placa:
    def __init__(self, puerto: str, salida: Path):
        self.s = serial.Serial(puerto, 115200, timeout=0.2)
        self.log = salida.open("w", encoding="utf-8", newline="\n")
        self.t0 = time.monotonic()

    def _marca(self) -> str:
        return f"{time.monotonic() - self.t0:9.3f} "

    def escribe(self, linea: str, del_chip: bool = False) -> None:
        # Las lineas del chip van tal cual, sin marca: asi el log lo lee
        # verifica_lecturas.py igual que uno de consola_esp32.py. La marca
        # de tiempo relativa va en las ordenes y en las comprobaciones.
        self.log.write(("" if del_chip else self._marca()) + linea + "\n")
        print(linea)

    def reinicio(self) -> None:
        """Reset fisico: EN por RTS, como hace esptool, con IO9 (DTR) alto."""
        self.escribe("> [reinicio fisico por RTS]")
        self.s.dtr = False
        self.s.rts = True
        time.sleep(0.1)
        self.s.rts = False
        self.s.reset_input_buffer()

    def leer_hasta(self, patrones: list[str], max_s: float) -> list[str]:
        """Lee lineas hasta ver uno de los patrones o agotar el plazo."""
        fin = time.monotonic() + max_s
        lineas: list[str] = []
        resto = b""
        while time.monotonic() < fin:
            cruda = resto + self.s.readline()
            # readline devuelve lo que haya al vencer el timeout, con o sin
            # fin de linea: una trama larga que el chip escribe byte a byte
            # llegaria en trozos y se compararian trozos.
            if not cruda.endswith(b"\n"):
                resto = cruda
                continue
            resto = b""
            linea = cruda.decode("utf-8", errors="replace").rstrip("\r\n")
            self.escribe(linea, del_chip=True)
            lineas.append(linea)
            if any(p in linea for p in patrones):
                break
        return lineas

    def orden(self, cmd: str, patrones: list[str], max_s: float = 10.0) -> tuple[list[str], float]:
        self.s.reset_input_buffer()
        self.escribe("> " + cmd)
        t = time.monotonic()
        self.s.write((cmd + "\n").encode())
        lineas = self.leer_hasta(patrones, max_s)
        return lineas, time.monotonic() - t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("puerto")
    ap.add_argument("--lecturas", type=int, default=5)
    ap.add_argument("--salida", type=Path, default=Path("results/placa_medidor_esp32c3.log"))
    a = ap.parse_args()
    a.salida.parent.mkdir(exist_ok=True)
    p = Placa(a.puerto, a.salida)
    fallos = 0

    def chk(cond: bool, msg: str) -> None:
        nonlocal fallos
        p.escribe(("  [ok ] " if cond else "  [FALLO] ") + msg)
        if not cond:
            fallos += 1

    p.escribe(f"# medidor en placa, puerto {a.puerto}, {time.strftime('%Y-%m-%d %H:%M')}")

    p.escribe("\n# 1) arranque limpio")
    p.reinicio()
    arr = p.leer_hasta(["medidor listo"], 15)
    chk(any("medidor listo" in l for l in arr), "el firmware arranca y abre la consola")
    # Empezar desde cero: sin clave en la NVS.
    p.orden("olvidar", ["olvidar:"])
    l, _ = p.orden("id", ["pila_libre"])
    idl = next((x for x in l if x.startswith("id ")), "")
    chk("version 0x03" in idl, "id: motor (simulado) version 0x03")
    arranque_1 = _campo(idl, "arranques=")

    p.escribe("\n# 2) sembrar y generar la clave")
    l, dt = p.orden("sembrar", ["sembrar:"], 60)
    chk(any("sembrar: " in x and "FALLO" not in x for x in l), f"sembrar en {dt:.2f} s")
    l, dt = p.orden("clave", ["clave:"], 60)
    chk(any(x.startswith("clave: ok") for x in l), f"clave P-256 generada y guardada en {dt:.3f} s")
    t_clave = dt

    p.escribe("\n# 3) publica, csr y lecturas firmadas")
    l, _ = p.orden("publica", ["FP"])
    pub1 = next((x for x in l if x.startswith("FP")), "")
    chk(bool(pub1), "publica anunciada (trama P)")
    l, dt = p.orden("csr", ["END CERTIFICATE REQUEST"], 30)
    chk(any("END CERTIFICATE REQUEST" in x for x in l), f"CSR en {dt:.3f} s")
    t = time.monotonic()
    l, _ = p.orden(f"lectura {a.lecturas}", [], 1.5 * a.lecturas + 5)
    lect = [x for x in l if x.startswith("FL")]
    dt = time.monotonic() - t
    chk(len(lect) == a.lecturas, f"{len(lect)} lecturas firmadas (intervalo 1 s): {dt:.2f} s en total")
    # Tiempo de una firma sola: una lectura mas, sin espera entre lecturas.
    l, dt = p.orden("lectura 1", ["FL"], 10)
    chk(any(x.startswith("FL") for x in l), f"una lectura firmada en {dt*1000:.0f} ms (ida y vuelta serie incluida)")
    sec_antes = _secuencia(l)

    p.escribe("\n# 4) reinicio fisico: la clave vuelve de la NVS")
    p.reinicio()
    arr = p.leer_hasta(["medidor listo"], 15)
    chk(any("clave recuperada de la NVS" in x for x in arr), "clave recuperada de la NVS al arrancar")
    l, _ = p.orden("id", ["pila_libre"])
    idl = next((x for x in l if x.startswith("id ")), "")
    arranque_2 = _campo(idl, "arranques=")
    chk(arranque_1 is not None and arranque_2 == arranque_1 + 1,
        f"el contador de arranques en NVS sube: {arranque_1} -> {arranque_2}")
    l, _ = p.orden("publica", ["FP"])
    pub2 = next((x for x in l if x.startswith("FP")), "")
    chk(pub2 == pub1, "la publica es la misma de antes del reinicio")
    l, dt = p.orden("lectura 1", ["FL"], 10)
    sec_despues = _secuencia(l)
    chk(sec_antes is not None and sec_despues is not None and sec_despues > sec_antes,
        f"la primera lectura tras el reinicio supera a la ultima de antes: 0x{sec_antes or 0:08x} -> 0x{sec_despues or 0:08x}")

    p.escribe("\n# 5) olvidar y reinicio: sin clave no hay lecturas")
    p.orden("olvidar", ["olvidar:"])
    p.reinicio()
    arr = p.leer_hasta(["medidor listo"], 15)
    chk(not any("clave recuperada" in x for x in arr), "tras olvidar, nada que recuperar al arrancar")
    l, _ = p.orden("lectura 1", ["lectura:"], 5)
    chk(any("primero 'clave'" in x for x in l), "lectura rechazada sin clave")
    # Y una clave nueva, para que el verificador del PC vea el cambio.
    p.orden("sembrar", ["sembrar:"], 60)
    l, dt = p.orden("clave", ["clave:"], 60)
    chk(any(x.startswith("clave: ok") for x in l), f"clave nueva en {dt:.3f} s (antes {t_clave:.3f} s)")
    l, _ = p.orden("publica", ["FP"])
    pub3 = next((x for x in l if x.startswith("FP")), "")
    chk(bool(pub3), "clave nueva anunciada")
    # Con el motor SIMULADO la clave nueva sale igual que la olvidada: el
    # simulador es determinista y en cada arranque repite la misma secuencia
    # de "aleatorio". No es un fallo del medidor, es la demostracion de por
    # que hace falta el motor: con el real las dos claves son distintas.
    p.escribe("  [info] clave nueva " + ("IGUAL a la olvidada (motor simulado, determinista: "
              "cada arranque repite el mismo aleatorio)" if pub3 == pub1 else
              "distinta de la olvidada (aleatorio real)"))
    p.orden("lectura 2", [], 5)

    p.escribe(f"\nplaca_medidor: {fallos} fallos")
    p.log.close()
    return 1 if fallos else 0


def _campo(linea: str, clave: str) -> int | None:
    i = linea.find(clave)
    if i < 0:
        return None
    v = linea[i + len(clave):].split()[0]
    return int(v, 0)


def _secuencia(lineas: list[str]) -> int | None:
    """Secuencia (bytes 8..11 del registro, tras el id del equipo) de la
    ultima trama L. La trama es 'FL' + longitud (4 hex) + datos + CRC."""
    for x in reversed(lineas):
        if x.startswith("FL"):
            cuerpo = x[6:]
            return int(cuerpo[16:24], 16)
    return None


if __name__ == "__main__":
    sys.exit(main())
