#!/usr/bin/env python3
"""Modelo de referencia de CTR_DRBG con AES-128 (NIST SP 800-90A Rev. 1,
seccion 10.2.1), con y sin funcion de derivacion (Block_Cipher_df,
seccion 10.3.2).

Es el modelo de oro del motor: bit a bit, en Python puro, validado contra
los vectores oficiales del CAVP (tests/vectors/drbg/CTR_DRBG_*.rsp). Una
vez validado, genera los vectores de los bancos VHDL y sirve para
contrastar con el ESP32.

El AES tambien va en Python puro, escrito desde el estandar de forma
independiente al VHDL, y se autovalida contra FIPS 197 al importar. Dos
implementaciones independientes que coinciden valen mas que una.

Parametros de AES-128 (Tabla 3 de la norma): blocklen = 128,
keylen = 128, seedlen = 256, ctr_len = 128.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# --------------------------------------------------------------------
# AES-128, solo cifrado
# --------------------------------------------------------------------

_SBOX = bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d8311504c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f8453d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa851a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d197360814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df8ca1890dbfe6426841992d0fb054bb16")


def _xtime(a: int) -> int:
    a <<= 1
    return (a ^ 0x1B) & 0xFF if a & 0x100 else a


def _expandir(clave: bytes) -> list[bytes]:
    w = [clave[i:i + 4] for i in range(0, 16, 4)]
    rcon = 1
    for i in range(4, 44):
        t = bytearray(w[i - 1])
        if i % 4 == 0:
            t = bytearray([_SBOX[t[1]] ^ rcon, _SBOX[t[2]], _SBOX[t[3]], _SBOX[t[0]]])
            rcon = _xtime(rcon)
        w.append(bytes(a ^ b for a, b in zip(w[i - 4], t)))
    return [b"".join(w[4 * r:4 * r + 4]) for r in range(11)]


def aes128_encrypt(clave: bytes, bloque: bytes) -> bytes:
    """Cifra un bloque de 16 bytes. Estado en orden de columnas, como en
    la norma: el byte i es fila i % 4, columna i // 4."""
    rk = _expandir(clave)
    s = bytearray(a ^ b for a, b in zip(bloque, rk[0]))
    for ronda in range(1, 11):
        s = bytearray(_SBOX[b] for b in s)
        # ShiftRows: la fila r gira r posiciones.
        s = bytearray(s[(r + 4 * ((c + r) % 4))] for c in range(4) for r in range(4))
        if ronda != 10:
            for c in range(4):
                a0, a1, a2, a3 = s[4 * c:4 * c + 4]
                s[4 * c + 0] = _xtime(a0) ^ _xtime(a1) ^ a1 ^ a2 ^ a3
                s[4 * c + 1] = a0 ^ _xtime(a1) ^ _xtime(a2) ^ a2 ^ a3
                s[4 * c + 2] = a0 ^ a1 ^ _xtime(a2) ^ _xtime(a3) ^ a3
                s[4 * c + 3] = _xtime(a0) ^ a0 ^ a1 ^ a2 ^ _xtime(a3)
        s = bytearray(a ^ b for a, b in zip(s, rk[ronda]))
    return bytes(s)


# Autovalidacion al importar: si el AES esta mal, nada de lo demas vale.
assert aes128_encrypt(bytes.fromhex("000102030405060708090a0b0c0d0e0f"),
                      bytes.fromhex("00112233445566778899aabbccddeeff")) \
    == bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a"), "AES: FIPS 197 C.1"
assert aes128_encrypt(bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c"),
                      bytes.fromhex("3243f6a8885a308d313198a2e0370734")) \
    == bytes.fromhex("3925841d02dc09fbdc118597196a0b32"), "AES: FIPS 197 B"


# --------------------------------------------------------------------
# CTR_DRBG
# --------------------------------------------------------------------

BLOCKLEN = 16          # bytes
KEYLEN = 16
SEEDLEN = KEYLEN + BLOCKLEN   # 32 bytes = 256 bits


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def _inc128(v: bytes) -> bytes:
    return ((int.from_bytes(v, "big") + 1) & ((1 << 128) - 1)).to_bytes(16, "big")


def _bcc(clave: bytes, datos: bytes) -> bytes:
    """CBC-MAC con IV cero, seccion 10.3.3."""
    encadenado = bytes(BLOCKLEN)
    for i in range(0, len(datos), BLOCKLEN):
        encadenado = aes128_encrypt(clave, _xor(encadenado, datos[i:i + BLOCKLEN]))
    return encadenado


def block_cipher_df(entrada: bytes, n_bytes: int) -> bytes:
    """Funcion de derivacion, seccion 10.3.2. Devuelve n_bytes."""
    L = len(entrada).to_bytes(4, "big")
    N = n_bytes.to_bytes(4, "big")
    S = L + N + entrada + b"\x80"
    S += bytes((-len(S)) % BLOCKLEN)

    K = bytes(range(KEYLEN))             # 000102...0f
    temp = b""
    i = 0
    while len(temp) < KEYLEN + BLOCKLEN:
        IV = i.to_bytes(4, "big") + bytes(BLOCKLEN - 4)
        temp += _bcc(K, IV + S)
        i += 1
    K = temp[:KEYLEN]
    X = temp[KEYLEN:KEYLEN + BLOCKLEN]
    salida = b""
    while len(salida) < n_bytes:
        X = aes128_encrypt(K, X)
        salida += X
    return salida[:n_bytes]


class CtrDrbg:
    """CTR_DRBG AES-128. usar_df elige entre 10.2.1.3.2 y 10.2.1.3.1."""

    def __init__(self, usar_df: bool = True):
        self.usar_df = usar_df
        self.key = bytes(KEYLEN)
        self.v = bytes(BLOCKLEN)
        self.contador_reseed = 0

    def _update(self, datos: bytes) -> None:
        assert len(datos) == SEEDLEN
        temp = b""
        while len(temp) < SEEDLEN:
            self.v = _inc128(self.v)
            temp += aes128_encrypt(self.key, self.v)
        temp = _xor(temp[:SEEDLEN], datos)
        self.key = temp[:KEYLEN]
        self.v = temp[KEYLEN:]

    def _preparar(self, material: bytes) -> bytes:
        """Con df: deriva a seedlen. Sin df: rellena con ceros a seedlen
        (la norma exige que no exceda seedlen)."""
        if self.usar_df:
            return block_cipher_df(material, SEEDLEN)
        assert len(material) <= SEEDLEN, "sin df la entrada no puede exceder seedlen"
        return material + bytes(SEEDLEN - len(material))

    def instantiate(self, entropia: bytes, nonce: bytes = b"",
                    personalizacion: bytes = b"") -> None:
        if self.usar_df:
            material = self._preparar(entropia + nonce + personalizacion)
        else:
            # Sin df: la entropia debe medir seedlen exactos y se le suma
            # la cadena de personalizacion rellenada.
            assert len(entropia) == SEEDLEN
            material = _xor(entropia, self._preparar(personalizacion))
        self.key = bytes(KEYLEN)
        self.v = bytes(BLOCKLEN)
        self._update(material)
        self.contador_reseed = 1

    def reseed(self, entropia: bytes, adicional: bytes = b"") -> None:
        if self.usar_df:
            material = self._preparar(entropia + adicional)
        else:
            assert len(entropia) == SEEDLEN
            material = _xor(entropia, self._preparar(adicional))
        self._update(material)
        self.contador_reseed = 1

    def generate(self, n_bytes: int, adicional: bytes = b"") -> bytes:
        if adicional:
            adicional = self._preparar(adicional)
            self._update(adicional)
        else:
            adicional = bytes(SEEDLEN)
        temp = b""
        while len(temp) < n_bytes:
            self.v = _inc128(self.v)
            temp += aes128_encrypt(self.key, self.v)
        self._update(adicional)
        self.contador_reseed += 1
        return temp[:n_bytes]


# --------------------------------------------------------------------
# Validacion contra los vectores del CAVP
# --------------------------------------------------------------------

def _leer_rsp(ruta: Path):
    """Itera (nombre_seccion, parametros, caso) sobre un .rsp del CAVS.
    Las lineas repetidas (AdditionalInput x2) se acumulan en lista."""
    seccion, params, caso = None, {}, {}
    for linea in ruta.read_text().splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        m = re.fullmatch(r"\[(.+?)\]", linea)
        if m:
            # Un encabezado nuevo cierra el caso pendiente ANTES de tocar
            # seccion o parametros; si no, el ultimo caso de cada bloque se
            # evaluaria con los parametros del bloque siguiente.
            if caso:
                yield seccion, dict(params), caso
                caso = {}
            cuerpo = m.group(1)
            if "=" in cuerpo:
                k, v = (x.strip() for x in cuerpo.split("=", 1))
                params[k] = v
            else:
                seccion = cuerpo
                params = {}
            continue
        k, _, v = linea.partition("=")
        k, v = k.strip(), v.strip()
        if k == "COUNT":
            if caso:
                yield seccion, dict(params), caso
            caso = {"COUNT": int(v)}
        else:
            caso.setdefault(k, []).append(bytes.fromhex(v) if v else b"")
    if caso:
        yield seccion, dict(params), caso


def validar_rsp(ruta: Path, verbose: bool = True):
    """Ejecuta los casos AES-128 de un .rsp y cuenta aciertos."""
    total = aciertos = 0
    por_seccion: dict[str, list[int]] = {}
    for seccion, params, caso in _leer_rsp(ruta):
        if not seccion.startswith("AES-128"):
            continue
        usar_df = "use df" in seccion
        d = CtrDrbg(usar_df)
        g = lambda k: caso.get(k, [b""])
        d.instantiate(g("EntropyInput")[0], g("Nonce")[0],
                      g("PersonalizationString")[0])
        if "EntropyInputReseed" in caso:
            d.reseed(g("EntropyInputReseed")[0], g("AdditionalInputReseed")[0])
        n = int(params["ReturnedBitsLen"]) // 8
        adic = g("AdditionalInput") + [b"", b""]
        d.generate(n, adic[0])
        salida = d.generate(n, adic[1])
        ok = salida == caso["ReturnedBits"][0]
        total += 1
        aciertos += ok
        por_seccion.setdefault(seccion, [0, 0])
        por_seccion[seccion][0] += ok
        por_seccion[seccion][1] += 1
        if not ok and verbose:
            print(f"  FALLO {seccion} COUNT={caso['COUNT']}")
    if verbose:
        for s, (a, t) in por_seccion.items():
            print(f"  {s:22s} {a:4d}/{t:<4d}")
    return aciertos, total


def autotest(verbose: bool = True) -> bool:
    raiz = Path(__file__).resolve().parent.parent / "tests" / "vectors" / "drbg"
    fallos = 0
    if verbose:
        print("1) Block_Cipher_df es determinista y del tamano pedido")
    a = block_cipher_df(b"prueba", 32)
    b = block_cipher_df(b"prueba", 32)
    if not (a == b and len(a) == 32 and block_cipher_df(b"otra", 32) != a):
        fallos += 1
    if verbose:
        print(f"  [{'ok ' if not fallos else 'FALLO'}] df(32 bytes) = {a.hex()[:32]}...")

    for nombre in ["CTR_DRBG_no_reseed.rsp", "CTR_DRBG_pr_false.rsp"]:
        ruta = raiz / nombre
        if verbose:
            print(f"2) Vectores CAVP: {nombre}")
        if not ruta.exists():
            print(f"  [FALLO] no existe {ruta}")
            fallos += 1
            continue
        ac, tot = validar_rsp(ruta, verbose)
        if verbose:
            print(f"  [{'ok ' if ac == tot else 'FALLO'}] {ac}/{tot} casos AES-128")
        if ac != tot:
            fallos += 1

    print(f"\nautotest ctr_drbg_ref: {fallos} fallos")
    return fallos == 0


if __name__ == "__main__":
    sys.exit(0 if autotest() else 1)
