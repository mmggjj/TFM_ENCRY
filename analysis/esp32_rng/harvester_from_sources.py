#!/usr/bin/env python3
"""
harvester_from_sources.py -- Reproduce the firmware harvester in Python
over the REAL captured silicon sources, and emit 1000 seeds for validation.

The firmware harvester (entropy_harvester.c) is deterministic given its
three inputs; this script applies the identical SHA-256 construction to
the captured SRAM power-up pattern (puf_boot1.bin) and the captured
hardware-RNG stream (condD_rep1.bin, the worst-case condition, as the RNG
contribution), with the ADC contribution drawn from the same RNG stream
tail as a stand-in when no separate ADC capture exists. This validates the
harvester ALGORITHM on real-silicon entropy without depending on the
fragile on-device SEEDS capture.

  pool     = SHA256(rng32 || SHA256(PUF) || adc32 || "TFM0")
  seed_i   = SHA256(pool || i || rng_fresh32)
  ratchet  : pool = SHA256(pool || seed_i)

Output: results/seeds_rep1.bin (1000 x 32 B) for harvester_validation.py.

TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
"""
from __future__ import annotations
import hashlib
import struct
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[2] / "results" / "esp32_rng_agosto"


def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def main():
    puf = (RESULTS / "puf_boot1.bin").read_bytes()
    rng = (RESULTS / "condD_rep1.bin").read_bytes()   # real hardware RNG
    n_seeds = 1000

    h_puf = sha256(puf)
    # walk the real RNG stream for the per-block "fresh RNG" material
    off = 0

    def take(n):
        nonlocal off
        chunk = rng[off:off + n]
        off += n
        return chunk

    rng32 = take(32)
    adc32 = take(32)              # stand-in ADC contribution from RNG tail
    pool = sha256(rng32 + h_puf + adc32 + b"TFM0")

    seeds = bytearray()
    for i in range(n_seeds):
        fresh = take(32)
        if len(fresh) < 32:       # wrap around the 125 KB stream if needed
            off = 0
            fresh = take(32)
        seed = sha256(pool + struct.pack("<I", i) + fresh)
        seeds += seed
        pool = sha256(pool + seed)          # forward-secrecy ratchet

    out = RESULTS / "seeds_rep1.bin"
    out.write_bytes(bytes(seeds))
    print(f"[harvester_from_sources] {n_seeds} seeds -> {out.name} "
          f"({len(seeds)} B) from real PUF + real RNG(condD)")


if __name__ == "__main__":
    main()
