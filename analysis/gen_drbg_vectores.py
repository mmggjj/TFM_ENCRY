#!/usr/bin/env python3
"""Genera el paquete VHDL de vectores para el banco del CTR_DRBG a partir
del modelo de referencia (validado contra 960 casos del CAVP).

La disposicion de entrada es la misma que fija el hardware: entropia de
48 bytes seguida de nonce de 16, sin cadena de personalizacion, con lo que
la funcion de derivacion ve L = 64 (512 bits crudos desde el 16-11-2026;
antes 32 + 16). Si el hardware cambia esa disposicion,
hay que cambiarla aqui tambien, y solo aqui.

    python gen_drbg_vectores.py  ->  rtl/tb/drbg_vectores_pkg.vhd

Desde el 23-11-2026 el paquete lleva ademas C_LOTE: N_LOTE semillas mas,
cada una con instanciar, dos generaciones, resembrar y otra generacion,
para que el banco no dependa de dos semillas solas.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ctr_drbg_ref import CtrDrbg

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "rtl" / "tb" / "drbg_vectores_pkg.vhd"
N_LOTE = 50


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
    e1, n1 = derivar("entropia-1", 48), derivar("nonce-1", 16)
    e2, n2 = derivar("entropia-2", 48), derivar("nonce-2", 16)

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

    lote = []
    for i in range(N_LOTE):
        e, n = derivar(f"lote-e-{i}", 48), derivar(f"lote-n-{i}", 16)
        er, nr = derivar(f"lote-er-{i}", 48), derivar(f"lote-nr-{i}", 16)
        dl = CtrDrbg(usar_df=True)
        dl.instantiate(e, n)
        a, b = dl.generate(32), dl.generate(32)
        dl.reseed(er + nr)
        lote.append((e, n, a, b, er, nr, dl.generate(32)))
    filas = ",\n".join(
        f'    {i} => (e => x"{e.hex()}", n => x"{n.hex()}",\n'
        f'          a => x"{a.hex()}",\n          b => x"{b.hex()}",\n'
        f'          er => x"{er.hex()}", nr => x"{nr.hex()}",\n'
        f'          c => x"{c.hex()}")'
        for i, (e, n, a, b, er, nr, c) in enumerate(lote))

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
        "  -- Lote: instanciar(e, n), generar a y b, resembrar(er, nr), generar c.",
        "  type t_caso is record",
        "    e, er : std_logic_vector(383 downto 0);",
        "    n, nr : std_logic_vector(127 downto 0);",
        "    a, b, c : std_logic_vector(255 downto 0);",
        "  end record;",
        f"  type t_lote is array (0 to {N_LOTE - 1}) of t_caso;",
        "  constant C_LOTE : t_lote := (",
        filas,
        "  );",
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
