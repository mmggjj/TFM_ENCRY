#!/usr/bin/env python3
"""Robustez de verifica_lecturas.py: basura y tramas corrompidas no deben
tumbarlo (ninguna excepcion) ni contar nunca como lecturas validas.

    python fuzz_verifica_lecturas.py [--base results/qemu_medidor_esp32c3.log]

Casos: lineas de basura; el log base con un caracter hexadecimal cambiado
en cada trama; tramas con CRC bueno y cargas raras (L vacias, cortas,
largas, P que no es DER, tipos desconocidos); publicas validas de otro
tipo (RSA) y de otra curva (P-384) seguidas de lecturas, y firmas basura
con una P-256 buena; bloques PEM rotos. Cada caso debe acabar con rc=1,
sin excepcion y con validas=0. Los logs de cada caso se dejan en un
directorio temporal y la salida completa se imprime.
"""
from __future__ import annotations

import argparse
import random
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

from cryptography.hazmat.primitives import serialization as ser
from cryptography.hazmat.primitives.asymmetric import ec, rsa

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "analysis" / "verifica_lecturas.py"


def crc(c: bytes) -> str:
    return f"{zlib.crc32(c) & 0xffffffff:08x}"


def trama(t: str, c: bytes) -> str:
    return f"F{t}{len(c):04x}{c.hex()}{crc(c)}"


def spki(k) -> bytes:
    return k.public_key().public_bytes(ser.Encoding.DER, ser.PublicFormat.SubjectPublicKeyInfo)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=RAIZ / "results" / "qemu_medidor_esp32c3.log",
                    help="log real con tramas, para mutarlo")
    args = ap.parse_args()
    texto = args.base.read_text(encoding="utf-8", errors="replace").splitlines()
    random.seed(1)
    casos: list[tuple[str, list[str]]] = []

    casos.append(("basura", ["".join(random.choice("F0123456789abcdefXYZ- \t") for _ in range(random.randint(0, 200)))
                             for _ in range(300)]))

    mut = []
    for l in texto:
        if l.startswith("FL") or l.startswith("FP"):
            i = random.randrange(2, len(l))
            l = l[:i] + random.choice("0123456789abcdef") + l[i + 1:]
        mut.append(l)
    casos.append(("tramas_mutadas", mut))

    casos.append(("cargas_raras", [
        trama("L", b""), trama("L", b"\x00" * 24), trama("L", bytes(range(31))), trama("L", bytes(200)),
        trama("P", b"\x30\x03\x02\x01\x01"), trama("P", b"no soy DER"), trama("Q", b"xyz"), trama("L", b"\xff" * 100),
        "FLffff" + "00" * 10 + "00000000", "FL0001zz00000000",
        trama("L", bytes(24) + bytes([0x30, 0x44]) + bytes(68)),
    ]))

    casos.append(("claves_de_otro_tipo", [
        trama("P", spki(rsa.generate_private_key(65537, 2048))), trama("L", bytes(24) + bytes(70)),
        trama("P", spki(ec.generate_private_key(ec.SECP384R1()))), trama("L", bytes(24) + bytes(70)),
        trama("P", spki(ec.generate_private_key(ec.SECP256R1()))),
        trama("L", bytes(24) + bytes(70)),
        trama("L", bytes(24) + bytes([0x30, 0x44, 0x02, 0x20]) + bytes(66)),
        trama("L", bytes(24) + bytes([0x30, 0x06, 0x02, 0x01, 0x01, 0x02, 0x01, 0x01])),
    ]))

    casos.append(("pem_roto", [
        "-----BEGIN CERTIFICATE REQUEST-----", "MIIBad", "-----END CERTIFICATE REQUEST-----",
        "-----END CERTIFICATE REQUEST-----", "-----BEGIN CERTIFICATE REQUEST-----", "sin cierre",
    ]))

    out = Path(tempfile.mkdtemp(prefix="fuzz_verifica_"))
    fallos = 0
    for nombre, lineas in casos:
        f = out / f"{nombre}.log"
        f.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True)
        salida = r.stdout + r.stderr
        excepcion = "Traceback" in salida
        resumen = [l for l in salida.splitlines() if l.startswith("resumen:")]
        validas = int(resumen[0].split("validas=")[1].split()[0]) if resumen else -1
        ok = bool(resumen) and not excepcion and r.returncode == 1 and validas == 0
        print(f"[{'ok ' if ok else 'FALLO'}] {nombre}: rc={r.returncode} excepcion={excepcion} "
              f"{resumen[0] if resumen else ''}")
        if not ok:
            fallos += 1
            print(salida)
    print(f"logs de los casos en {out}")
    print(f"fuzz_verifica_lecturas: {fallos} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
