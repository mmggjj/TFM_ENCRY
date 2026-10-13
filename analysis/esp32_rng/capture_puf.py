#!/usr/bin/env python3
"""
capture_puf.py -- Capture ONE SRAM power-up pattern into the clean
power-cycle series (puf_pc{N}.bin). Run once after each physical
USB unplug/replug so every file in the series is a true power-up.
Usage: python capture_puf.py --port COM7
"""
from __future__ import annotations
import argparse, re, time, zlib
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[2] / "results" / "esp32_rng_agosto"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args()
    import serial
    n = len(list(RESULTS.glob("puf_pc*.bin"))) + 1

    with serial.Serial(args.port, args.baud, timeout=2) as ser:
        ser.dtr = False; ser.rts = True; time.sleep(0.1); ser.rts = False
        ser.reset_input_buffer()
        hexbuf, mode, meta = [], None, {}
        t0 = time.time()
        while time.time() - t0 < 30:
            raw = ser.readline().decode(errors="replace").strip()
            if raw.startswith("### PUF_BEGIN"):
                mode, hexbuf = "PUF", []
                meta = dict(re.findall(r"(\w+)=([^\s]+)", raw))
            elif raw.startswith("### PUF_END"):
                clean = "".join(c for c in "".join(hexbuf)
                                if c in "0123456789abcdef")
                if len(clean) % 2:
                    clean = clean[:-1]
                data = bytes.fromhex(clean)
                kv = dict(re.findall(r"(\w+)=([^\s]+)", raw))
                crc_ok = ("crc32" not in kv or
                          int(kv["crc32"], 16) == zlib.crc32(data))
                if crc_ok and len(data) == 4096:
                    out = RESULTS / f"puf_pc{n}.bin"
                    out.write_bytes(data)
                    print(f"[capture_puf] power-cycle pattern #{n} -> "
                          f"{out.name} (entropy={meta.get('entropy','?')}, "
                          f"weight={meta.get('weight','?')})")
                    return
                print(f"[capture_puf] bad PUF frame (len={len(data)} "
                      f"crc_ok={crc_ok}), retry")
                mode, hexbuf = None, []
            elif mode == "PUF" and len(raw) >= 2 and all(
                    c in "0123456789abcdef" for c in raw):
                hexbuf.append(raw)
    print("[capture_puf] no PUF frame captured -- power-cycle and retry")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
