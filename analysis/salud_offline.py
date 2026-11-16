#!/usr/bin/env python3
"""Tests de salud de SP 800-90B (RCT y APT, como rtl/trng/health_tests.vhd)
aplicados en software a bits ya capturados, con varios juegos de cortes.

Separa el efecto de los cortes del de la implementacion: la prueba en placa
(escribir CFG_KD, borrar, 30 s, id) solo dice si salto alguna alarma, con
los bits de ese momento y los cortes de ese bitstream. Aqui los mismos bits
pasan por 22/596 (H 0,98, alfa 2^-20), 39/683 (H 0,80, 2^-30) y 51/766
(H 0,60, 2^-30): lo que deja de detectarse al bajar la H.

RCT: alarma cuando una racha llega a C (cada racha cuenta una vez).
APT: ventanas consecutivas de W = 1024 sin solapar; la cuenta incluye la
primera muestra; alarma si la cuenta o su complemento llegan a C. Los
trozos de flujo_desborde.py son independientes: las rachas y las ventanas
no cruzan de un trozo a otro, y la ventana incompleta del final se
descarta.

    ~/eda/venv/bin/python analysis/salud_offline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
CAMP = RAIZ / "results" / "motor_campana"
SALIDA = RAIZ / "results" / "salud_offline.md"
W = 1024
CORTES = [("22/596", 22, 596), ("39/683", 39, 683), ("51/766", 51, 766)]


def rachas(bits: np.ndarray) -> np.ndarray:
    """Longitudes de las rachas de valores iguales."""
    if bits.size == 0:
        return np.array([], dtype=int)
    cambios = np.flatnonzero(np.diff(bits)) + 1
    bordes = np.concatenate(([0], cambios, [bits.size]))
    return np.diff(bordes)


def cuentas_apt(bits: np.ndarray) -> np.ndarray:
    """Cuenta de cada ventana completa: muestras iguales a la primera."""
    n = bits.size // W
    v = bits[: n * W].reshape(n, W)
    return (v == v[:, :1]).sum(axis=1)


def evaluar(trozos: list[np.ndarray]) -> dict:
    r = np.concatenate([rachas(t) for t in trozos])
    a = np.concatenate([cuentas_apt(t) for t in trozos])
    peor_apt = np.maximum(a, W - a) if a.size else np.array([0])
    res = {"bits": sum(t.size for t in trozos), "ventanas": a.size,
           "racha_max": int(r.max()), "apt_max": int(peor_apt.max())}
    for nom, c_rct, c_apt in CORTES:
        res[f"rct {nom}"] = int((r >= c_rct).sum())
        res[f"apt {nom}"] = int((peor_apt >= c_apt).sum())
    return res


def de_npz(p: Path) -> list[np.ndarray]:
    d = np.load(p)
    bits = np.unpackbits(d["datos"])
    fin = np.cumsum(8 * d["longitudes"])
    return np.split(bits, fin[:-1])


def de_bin(p: Path) -> list[np.ndarray]:
    return [np.unpackbits(np.frombuffer(p.read_bytes(), dtype=np.uint8))]


def fuentes():
    for v, nombre in (("quieto_sin_medidor_kd07_09_r4", "14-11 (CE), hoy"),
                      ("fijo_kd07_09", "fijo (CE)"),
                      ("libre_c51_kd07_09", "libre 51/766 (sin CE)")):
        for kd in (7, 8, 9):
            p = CAMP / f"basys2_{v}" / f"kd{kd:02d}_trozos.npz"
            if p.exists():
                yield f"{nombre}", kd, "trozos", de_npz(p)
    for kd in (12, 13, 14, 15, 16):
        p = CAMP / "basys2_campana_90b_kd12_16" / f"kd{kd}_flujo.bin"
        if p.exists():
            yield "14-11 (CE), campaña 90B", kd, "tira", de_bin(p)
    p = CAMP / "basys2_larga_kd14_n8378368" / "kd14_flujo.bin"
    if p.exists():
        yield "14-11 (CE), larga", 14, "tira", de_bin(p)
    for kd in (13, 14):
        p = CAMP / "basys2_libre_kd13_14_n4194304" / f"kd{kd}_flujo.bin"
        if p.exists():
            yield "libre 39/683 (sin CE)", kd, "tira", de_bin(p)
    rng = np.random.default_rng(16112026)
    for p1 in (0.5, 0.4962):
        yield f"iid p1={p1}", "-", "tira", [(rng.random(8_388_608) < p1).astype(np.uint8)]


def main() -> int:
    cab = ["Fuente", "kd", "tipo", "bits", "racha máx", "APT máx"] + \
          [f"RCT {n}" for n, _, _ in CORTES] + [f"APT {n}" for n, _, _ in CORTES]
    lin = ["# Tests de salud en software sobre bits capturados (analysis/salud_offline.py)", "",
           "Alarmas (rachas >= C del RCT; ventanas de 1024 con cuenta o complemento",
           ">= C del APT) con cada juego de cortes, sobre los mismos bits.", "",
           "| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    for nom, kd, tipo, trozos in fuentes():
        r = evaluar(trozos)
        fila = [nom, str(kd), tipo, str(r["bits"]), str(r["racha_max"]), str(r["apt_max"])]
        fila += [str(r[f"rct {n}"]) for n, _, _ in CORTES]
        fila += [str(r[f"apt {n}"]) for n, _, _ in CORTES]
        lin.append("| " + " | ".join(fila) + " |")
    txt = "\n".join(lin) + "\n"
    print(txt)
    SALIDA.write_text(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
