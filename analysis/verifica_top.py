#!/usr/bin/env python3
"""Verificacion cruzada del banco del motor completo.

El banco VHDL (rtl/tb/tb_motor_top.vhd) no puede saber si la etiqueta es
el CMAC correcto, porque la clave sale del ruido del anillo. Vuelca clave,
reto y etiqueta a results/tb_motor_top.txt y aqui se recalcula el CMAC con
el modelo de referencia en Python (AES independiente del VHDL, validado
contra FIPS 197). Es la misma comprobacion que hara el ESP32 con mbedtls.
"""
from __future__ import annotations

import sys
from pathlib import Path

from ctr_drbg_ref import aes128_encrypt

RESULTADO = Path(__file__).resolve().parent.parent / "results" / "tb_motor_top.txt"


def _subclave(v: bytes) -> bytes:
    n = int.from_bytes(v, "big") << 1
    if v[0] & 0x80:
        n ^= 0x87
    return (n & ((1 << 128) - 1)).to_bytes(16, "big")


def aes_cmac(clave: bytes, mensaje: bytes) -> bytes:
    """SP 800-38B, mensajes de cualquier longitud."""
    L = aes128_encrypt(clave, bytes(16))
    k1 = _subclave(L)
    k2 = _subclave(k1)
    n = max(1, -(-len(mensaje) // 16))
    completo = len(mensaje) > 0 and len(mensaje) % 16 == 0
    bloques = [mensaje[16 * i:16 * i + 16] for i in range(n)]
    if completo:
        ultimo = bytes(a ^ b for a, b in zip(bloques[-1], k1))
    else:
        rell = bloques[-1] + b"\x80" + bytes(15 - len(bloques[-1]))
        ultimo = bytes(a ^ b for a, b in zip(rell, k2))
    x = bytes(16)
    for b in bloques[:-1]:
        x = aes128_encrypt(clave, bytes(a ^ c for a, c in zip(x, b)))
    return aes128_encrypt(clave, bytes(a ^ c for a, c in zip(x, ultimo)))


def main() -> int:
    # Autovalidacion del CMAC contra RFC 4493 antes de fiarse de el.
    k = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
    assert aes_cmac(k, b"") == bytes.fromhex("bb1d6929e95937287fa37d129b756746")
    assert aes_cmac(k, bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")) \
        == bytes.fromhex("070a16b46b4d4144f79bdd9dd04a287c")

    if not RESULTADO.exists():
        print(f"no existe {RESULTADO}: ejecutar antes tb_motor_top")
        return 1
    v = {}
    for linea in RESULTADO.read_text().splitlines():
        nombre, _, hexv = linea.partition(" ")
        v[nombre] = bytes.fromhex(hexv.strip())

    fallos = 0

    def chk(cond, msg):
        nonlocal fallos
        print(f"  [{'ok ' if cond else 'FALLO'}] {msg}")
        fallos += 0 if cond else 1

    print("Verificacion cruzada del motor con el modelo de referencia")
    for i in (1, 2):
        esperado = aes_cmac(v["clave1"], v[f"reto{i}"])
        chk(esperado == v[f"etiqueta{i}"],
            f"etiqueta{i} = CMAC_clave1(reto{i}) -> {esperado.hex()}")
    chk(v["clave1"] == v["aleatorio1"][:16], "clave1 = primeros 16 bytes de aleatorio1")
    chk(v["clave1"] != v["clave2"], "las dos claves difieren")
    chk(len(set(v["clave1"])) > 4, "clave1 no es un patron trivial")

    print(f"\nverifica_top: {fallos} fallos")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
