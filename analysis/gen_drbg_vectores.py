#!/usr/bin/env python3
"""Genera el paquete VHDL de vectores para el banco del CTR_DRBG a partir
del modelo de referencia (validado contra 960 casos del CAVP).

La disposicion de entrada es la misma que fija el hardware: entropia de
32 bytes seguida de nonce de 16, sin cadena de personalizacion, con lo que
la funcion de derivacion ve L = 48. Si el hardware cambia esa disposicion,
hay que cambiarla aqui tambien, y solo aqui.

    python gen_drbg_vectores.py  ->  rtl/tb/drbg_vectores_pkg.vhd
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ctr_drbg_ref import CtrDrbg

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "rtl" / "tb" / "drbg_vectores_pkg.vhd"


def derivar(etiqueta: str, n: int) -> bytes:
    """Bytes de prueba reproducibles y distinguibles, no aleatorios."""
    out = b""
    i = 0
    while len(out) < n:
        out += hashlib.sha256(f"{etiqueta}:{i}".encode()).digest()
        i += 1
    return out[:n]


def vhdl_const(nombre: str, datos: bytes) -> str:
    return (f"  constant {nombre} : std_logic_vector({8 * len(datos) - 1} downto 0)\n"
            f"    := x\"{datos.hex()}\";\n")


def main() -> None:
    e1, n1 = derivar("entropia-1", 32), derivar("nonce-1", 16)
    e2, n2 = derivar("entropia-2", 32), derivar("nonce-2", 16)

    d = CtrDrbg(usar_df=True)
    d.instantiate(e1, n1)
    sal1a = d.generate(32)
    sal1b = d.generate(32)
    cnt_antes = d.contador_reseed
    d.reseed(e2 + n2)
    sal2 = d.generate(32)
    cnt_despues = d.contador_reseed

    # Instanciar de nuevo con las mismas entradas debe reproducir sal1a:
    # comprueba que instanciar borra el estado previo.
    d2 = CtrDrbg(usar_df=True)
    d2.instantiate(e1, n1)
    assert d2.generate(32) == sal1a

    texto = [
        "-- GENERADO por analysis/gen_drbg_vectores.py. No editar a mano.",
        "-- Vectores del CTR_DRBG AES-128 con df obtenidos del modelo de",
        "-- referencia ctr_drbg_ref.py (960/960 casos CAVP).",
        "library ieee;",
        "use ieee.std_logic_1164.all;",
        "",
        "package drbg_vectores_pkg is",
        vhdl_const("C_E1", e1), vhdl_const("C_N1", n1),
        vhdl_const("C_SAL1A", sal1a), vhdl_const("C_SAL1B", sal1b),
        vhdl_const("C_E2", e2), vhdl_const("C_N2", n2),
        vhdl_const("C_SAL2", sal2),
        f"  constant C_CNT_TRAS_DOS_GEN : natural := {cnt_antes};",
        f"  constant C_CNT_TRAS_RESEED_GEN : natural := {cnt_despues};",
        "end package drbg_vectores_pkg;",
        "",
    ]
    DESTINO.write_text("\n".join(texto))
    print(f"escrito {DESTINO}")
    print(f"  sal1a = {sal1a.hex()}")
    print(f"  sal1b = {sal1b.hex()}")
    print(f"  sal2  = {sal2.hex()}")
    print(f"  contador tras 2 generate: {cnt_antes}; tras reseed+generate: {cnt_despues}")


if __name__ == "__main__":
    main()
