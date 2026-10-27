#!/usr/bin/env python3
"""Verifica en el PC las lecturas firmadas que manda el medidor.

Lee un log serie (el de consola_esp32.py, o la salida del banco en host)
y saca de el las tramas 'F' con CRC32: las 'P' llevan la clave publica
del equipo (SubjectPublicKeyInfo DER) y las 'L' una lectura (24 bytes,
ver firmware/medidor/main/lectura.h) seguida de su firma ECDSA P-256 en
DER sobre SHA-256. Tambien busca peticiones de certificado PEM y
comprueba su firma y que lleven la misma publica.

    python verifica_lecturas.py results/esp32_consola_X.log [--publica CLAVE.der]

Cada lectura se comprueba contra la ultima publica anunciada antes de
ella en el log, o contra --publica si se da (lo correcto en un
despliegue: la publica se fija al registrar el equipo, no se cree la del
propio canal). Una lectura cuya secuencia no supera a la anterior del
mismo equipo se marca repetida: con la firma valida, un atacante puede
reinyectar lecturas viejas, y es la secuencia la que lo delata.

La criptografia la hace el paquete "cryptography", que no es mbedtls: la
firma del equipo la comprueba otra implementacion.

Salida: una linea por lectura y una linea final
    resumen: lecturas=N validas=V firma_invalida=F repetidas=R sin_clave=S crc_malo=C csr=K csr_mala=M
Devuelve 1 si hay algo invalido.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
import zlib
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

TRAMA = re.compile(r"^F([A-Z])([0-9a-f]{4})([0-9a-f]*)([0-9a-f]{8})\s*$")
PEM = re.compile(r"-----BEGIN CERTIFICATE REQUEST-----.*?-----END CERTIFICATE REQUEST-----", re.S)
LECTURA = struct.Struct(">8sIIII")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("--publica", type=Path, default=None,
                    help="SubjectPublicKeyInfo DER fijado de antemano; ignora las tramas P")
    args = ap.parse_args()

    fijada = None
    if args.publica is not None:
        fijada = serialization.load_der_public_key(args.publica.read_bytes())

    clave = fijada
    clave_der = args.publica.read_bytes() if args.publica else None
    ultima_seq: dict[bytes, int] = {}
    n = validas = firma_invalida = repetidas = sin_clave = crc_malo = 0
    texto = args.log.read_text(encoding="utf-8", errors="replace")

    for linea in texto.splitlines():
        m = TRAMA.match(linea.strip())
        if not m:
            continue
        tipo, n_hex, carga_hex, crc_hex = m.groups()
        if len(carga_hex) != 2 * int(n_hex, 16):
            crc_malo += 1
            continue
        carga = bytes.fromhex(carga_hex)
        if zlib.crc32(carga) & 0xFFFFFFFF != int(crc_hex, 16):
            crc_malo += 1
            continue
        if tipo == "P":
            if fijada is not None:
                aviso = "" if carga == clave_der else "  AVISO: distinta de la fijada"
                print(f"publica anunciada ({len(carga)} bytes){aviso}")
            else:
                clave = serialization.load_der_public_key(carga)
                clave_der = carga
                print(f"publica anunciada ({len(carga)} bytes): {carga.hex()}")
            continue
        if tipo != "L":
            continue
        n += 1
        if len(carga) < LECTURA.size + 8:
            firma_invalida += 1
            print(f"lectura {n}: trama corta ({len(carga)} bytes)")
            continue
        ident, seq, t, wh, w = LECTURA.unpack(carga[:LECTURA.size])
        firma = carga[LECTURA.size:]
        desc = f"equipo {ident.hex()} seq {seq} t {t} s energia {wh} Wh potencia {w} W"
        if clave is None:
            sin_clave += 1
            print(f"lectura {n}: {desc}: SIN CLAVE con la que comprobar")
            continue
        try:
            clave.verify(firma, carga[:LECTURA.size], ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            firma_invalida += 1
            print(f"lectura {n}: {desc}: FIRMA INVALIDA")
            continue
        if seq <= ultima_seq.get(ident, -1):
            repetidas += 1
            print(f"lectura {n}: {desc}: REPETIDA (ultima secuencia {ultima_seq[ident]})")
            continue
        ultima_seq[ident] = seq
        validas += 1
        print(f"lectura {n}: {desc}: ok")

    csr_ok = csr_mala = 0
    for bloque in PEM.findall(texto):
        try:
            csr = x509.load_pem_x509_csr(bloque.encode())
        except ValueError as e:
            csr_mala += 1
            print(f"CSR: no se parsea: {e}")
            continue
        pub = csr.public_key().public_bytes(serialization.Encoding.DER,
                                           serialization.PublicFormat.SubjectPublicKeyInfo)
        sujeto = csr.subject.rfc4514_string()
        if not csr.is_signature_valid:
            csr_mala += 1
            print(f"CSR {sujeto}: FIRMA INVALIDA")
        elif clave_der is not None and pub != clave_der:
            csr_mala += 1
            print(f"CSR {sujeto}: firma valida pero la publica NO es la del equipo")
        else:
            csr_ok += 1
            print(f"CSR {sujeto}: firma valida, publica del equipo")

    print(f"resumen: lecturas={n} validas={validas} firma_invalida={firma_invalida} "
          f"repetidas={repetidas} sin_clave={sin_clave} crc_malo={crc_malo} csr={csr_ok} csr_mala={csr_mala}")
    return 0 if firma_invalida == repetidas == sin_clave == crc_malo == csr_mala == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
