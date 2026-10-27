#!/usr/bin/env python3
"""Verifica en el PC las lecturas firmadas que manda el medidor.

Lee un log serie (el de consola_esp32.py, o la salida del banco en host)
y saca de el las tramas 'F' con CRC32: las 'P' llevan la clave publica
del equipo (SubjectPublicKeyInfo DER) y las 'L' una lectura (24 bytes,
ver firmware/medidor/main/lectura.h) seguida de su firma ECDSA P-256 en
DER sobre SHA-256. Tambien recoge las peticiones de certificado PEM y
comprueba su firma y que lleven la misma publica.

    python verifica_lecturas.py results/esp32_consola_X.log [--publica CLAVE.der] [--permitir-cambio]

Todo se procesa en una sola pasada y en orden: cada lectura y cada CSR se
comprueban contra la publica vigente en ese punto del log, que es la
ultima anunciada antes, o la de --publica si se da (lo correcto en un
despliegue: la publica se fija al registrar el equipo, no se cree la del
propio canal). Sin --publica, un cambio de publica a mitad del log se
cuenta y se avisa, y el resultado es fallo salvo con --permitir-cambio:
cualquiera que pueda escribir en el canal podria anunciar una clave suya
y firmar con ella. Una lectura cuya secuencia no supera a la anterior del
mismo equipo se marca repetida: con la firma valida, un atacante puede
reinyectar lecturas viejas, y es la secuencia la que lo delata.

La criptografia la hace el paquete "cryptography", que no es mbedtls: la
firma del equipo la comprueba otra implementacion.

Salida: una linea por lectura y una linea final
    resumen: lecturas=N validas=V firma_invalida=F repetidas=R sin_clave=S
             crc_malo=C csr=K csr_mala=M clave_cambiada=X
Devuelve 1 si hay algo invalido, si cambio la clave sin --permitir-cambio,
o si el log no tiene ni lecturas ni CSR (una captura vacia no "pasa").
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
import zlib
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

TRAMA = re.compile(r"^F([A-Z])([0-9a-f]{4})([0-9a-f]*)([0-9a-f]{8})\s*$")
PEM_INICIO = "-----BEGIN CERTIFICATE REQUEST-----"
PEM_FIN = "-----END CERTIFICATE REQUEST-----"
LECTURA = struct.Struct(">8sIIII")


class Cuentas:
    def __init__(self) -> None:
        self.lecturas = self.validas = self.firma_invalida = self.repetidas = 0
        self.sin_clave = self.crc_malo = self.csr = self.csr_mala = self.clave_cambiada = 0
        self.publica_mala = 0


def cargar_publica(der: bytes):
    """Una publica P-256 o None: una trama P con CRC bueno puede llevar
    cualquier cosa (otro tipo de clave, basura) y no debe tumbar el script."""
    try:
        clave = serialization.load_der_public_key(der)
    except (ValueError, TypeError, UnsupportedAlgorithm):
        return None
    if not isinstance(clave, ec.EllipticCurvePublicKey) or clave.curve.name != "secp256r1":
        return None
    return clave


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("--publica", type=Path, default=None,
                    help="SubjectPublicKeyInfo DER fijado de antemano; las tramas P solo se comparan")
    ap.add_argument("--permitir-cambio", action="store_true",
                    help="un cambio de publica anunciada no es fallo (banco, equipo que regenera)")
    args = ap.parse_args()

    fijada = args.publica is not None
    clave_der = args.publica.read_bytes() if fijada else None
    clave = cargar_publica(clave_der) if fijada else None
    if fijada and clave is None:
        print(f"--publica {args.publica}: no es una publica P-256 en DER")
        return 2
    ultima_seq: dict[bytes, int] = {}
    c = Cuentas()
    pem: list[str] | None = None   # lineas de la CSR en curso

    def comprobar_csr(bloque: str) -> None:
        try:
            csr = x509.load_pem_x509_csr(bloque.encode())
        except ValueError as e:
            c.csr_mala += 1
            print(f"CSR: no se parsea: {e}")
            return
        pub = csr.public_key().public_bytes(serialization.Encoding.DER,
                                           serialization.PublicFormat.SubjectPublicKeyInfo)
        sujeto = csr.subject.rfc4514_string()
        if not csr.is_signature_valid:
            c.csr_mala += 1
            print(f"CSR {sujeto}: FIRMA INVALIDA")
        elif clave_der is None:
            c.csr_mala += 1
            print(f"CSR {sujeto}: firma valida pero SIN publica anunciada con la que compararla")
        elif pub != clave_der:
            c.csr_mala += 1
            print(f"CSR {sujeto}: firma valida pero la publica NO es la vigente del equipo")
        else:
            c.csr += 1
            print(f"CSR {sujeto}: firma valida, publica del equipo")

    for cruda in args.log.read_text(encoding="utf-8", errors="replace").splitlines():
        linea = cruda.strip()
        if pem is not None:
            pem.append(linea)
            if linea == PEM_FIN:
                comprobar_csr("\n".join(pem))
                pem = None
            continue
        if linea == PEM_INICIO:
            pem = [linea]
            continue
        m = TRAMA.match(linea)
        if not m:
            continue
        tipo, n_hex, carga_hex, crc_hex = m.groups()
        if len(carga_hex) != 2 * int(n_hex, 16):
            c.crc_malo += 1
            continue
        carga = bytes.fromhex(carga_hex)
        if zlib.crc32(carga) & 0xFFFFFFFF != int(crc_hex, 16):
            c.crc_malo += 1
            continue
        if tipo == "P":
            if fijada:
                aviso = "" if carga == clave_der else "  AVISO: distinta de la fijada, se ignora"
                print(f"publica anunciada ({len(carga)} bytes){aviso}")
                continue
            nueva = cargar_publica(carga)
            if nueva is None:
                c.publica_mala += 1
                print(f"trama P que no es una publica P-256 valida ({len(carga)} bytes): se ignora")
                continue
            if clave_der is not None and carga != clave_der:
                c.clave_cambiada += 1
                print(f"AVISO: la publica anunciada CAMBIA (cambio {c.clave_cambiada})")
            clave = nueva
            clave_der = carga
            print(f"publica anunciada ({len(carga)} bytes): {carga.hex()}")
            continue
        if tipo != "L":
            continue
        c.lecturas += 1
        n = c.lecturas
        if len(carga) < LECTURA.size + 8:
            c.firma_invalida += 1
            print(f"lectura {n}: trama corta ({len(carga)} bytes)")
            continue
        ident, seq, t, wh, w = LECTURA.unpack(carga[:LECTURA.size])
        firma = carga[LECTURA.size:]
        desc = f"equipo {ident.hex()} seq {seq} t {t} s energia {wh} Wh potencia {w} W"
        if clave is None:
            c.sin_clave += 1
            print(f"lectura {n}: {desc}: SIN CLAVE con la que comprobar")
            continue
        try:
            clave.verify(firma, carga[:LECTURA.size], ec.ECDSA(hashes.SHA256()))
        except (InvalidSignature, ValueError):   # ValueError: DER de la firma irreconocible
            c.firma_invalida += 1
            print(f"lectura {n}: {desc}: FIRMA INVALIDA")
            continue
        if seq <= ultima_seq.get(ident, -1):
            c.repetidas += 1
            print(f"lectura {n}: {desc}: REPETIDA (ultima secuencia {ultima_seq[ident]})")
            continue
        ultima_seq[ident] = seq
        c.validas += 1
        print(f"lectura {n}: {desc}: ok")

    if pem is not None:
        c.csr_mala += 1
        print("CSR: bloque PEM sin cerrar")
    if c.lecturas == 0 and c.csr == 0 and c.csr_mala == 0:
        print("AVISO: el log no tiene lecturas ni CSR")
    print(f"resumen: lecturas={c.lecturas} validas={c.validas} firma_invalida={c.firma_invalida} "
          f"repetidas={c.repetidas} sin_clave={c.sin_clave} crc_malo={c.crc_malo} "
          f"csr={c.csr} csr_mala={c.csr_mala} clave_cambiada={c.clave_cambiada} "
          f"publica_mala={c.publica_mala}")
    mal = (c.firma_invalida or c.repetidas or c.sin_clave or c.crc_malo or c.csr_mala
           or c.publica_mala or (c.clave_cambiada and not args.permitir_cambio)
           or (c.lecturas == 0 and c.csr == 0))
    return 1 if mal else 0


if __name__ == "__main__":
    raise SystemExit(main())
