#!/usr/bin/env python3
"""
capture_rng.py -- Capture framed RNG campaign data from the ESP32 (UART).

Firmware protocol (921600 baud):
  ### DEVICE mac=.. idf=.. puf_bytes=..
  ### PUF_BEGIN bytes=4096 entropy=.. weight=..      + hex + ### PUF_END crc32=..
  ### CYCLE_BEGIN rep=N
  ### RNG_BEGIN cond=X rep=N bytes=125000 temp_c=.. throughput_Bps=..
      <hex lines>
  ### RNG_END cond=X rep=N crc32=0x.. temp_c=..
  ### SEEDS_BEGIN n=100 bytes=32                      + hex + ### SEEDS_END
  ### CYCLE_END rep=N

Outputs to --outdir:
  cond{A..D}_rep{N}.bin      raw 1 Mbit sequences (CRC-verified)
  puf_boot{k}.bin            SRAM power-up patterns (one per boot seen)
  seeds_rep{N}.bin           100 x 32-byte harvester seeds
  capture_log.csv            cond, rep, temp_begin, temp_end, throughput, crc_ok

Usage:
  python capture_rng.py --port COM7 --cycles 3   (por defecto escribe en results/esp32_rng_agosto)

TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import zlib
from pathlib import Path

RE_KV = re.compile(r"(\w+)=([^\s]+)")


def parse_kv(line: str) -> dict:
    return dict(RE_KV.findall(line))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--cycles", type=int, default=3)  # kept for compat
    ap.add_argument("--reps", type=int, default=3,
                    help="valid sequences to collect per condition")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("-o", "--outdir", default=str(Path(__file__).resolve().parents[2] / "results" / "esp32_rng_agosto"))
    args = ap.parse_args()

    import serial
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    log_rows = []
    puf_count = len(list(outdir.glob("puf_boot*.bin")))

    hexbuf = []
    mode = None          # None | "PUF" | "RNG" | "SEEDS"
    meta = {}

    # host-side repetition counters per condition, so device resets
    # (WiFi brown-outs restart the firmware's own rep counter) never cause
    # collisions: each valid sequence is numbered by how many we already have
    got = {c: 0 for c in "ABCD"}
    seeds_count = [0]

    def finish_block(end_line: str):
        nonlocal mode, hexbuf, puf_count
        # sanitize: keep only hex chars, drop a stray trailing nibble that
        # an interleaved firmware log line could leave behind
        joined = "".join(hexbuf)
        clean = "".join(c for c in joined if c in "0123456789abcdef")
        if len(clean) % 2:
            clean = clean[:-1]
        data = bytes.fromhex(clean)
        kv = parse_kv(end_line)
        crc_ok = True
        if "crc32" in kv:
            crc_ok = int(kv["crc32"], 16) == zlib.crc32(data)
        if mode == "PUF":
            if not crc_ok:
                print("  [puf] CRC mismatch, discarded")
            else:
                puf_count += 1
                (outdir / f"puf_boot{puf_count}.bin").write_bytes(data)
                print(f"  [puf] 4096 B -> puf_boot{puf_count}.bin "
                      f"(entropy={meta.get('entropy','?')})")
        elif mode == "RNG":
            cond = meta.get("cond", "?")
            expected = int(meta.get("bytes", "125000"))
            # accept only complete, CRC-valid, correct-length sequences
            if not crc_ok or len(data) != expected or cond not in got:
                print(f"  [rng] cond={cond} REJECTED "
                      f"(len={len(data)}/{expected} crc_ok={crc_ok})")
            elif got[cond] >= args.reps:
                pass  # already have enough of this condition
            else:
                got[cond] += 1
                rep = got[cond]
                (outdir / f"cond{cond}_rep{rep}.bin").write_bytes(data)
                log_rows.append([cond, rep, meta.get("temp_c", ""),
                                 kv.get("temp_c", ""),
                                 meta.get("throughput_Bps", ""), 1])
                print(f"  [rng] cond={cond} rep={rep} {len(data)} B OK "
                      f"temp={meta.get('temp_c','?')}C "
                      f"tput={meta.get('throughput_Bps','?')} B/s  "
                      f"[{sum(got.values())}/{4*args.reps}]")
        elif mode == "SEEDS":
            if crc_ok and len(data) >= 32:
                seeds_count[0] += 1
                (outdir / f"seeds_rep{seeds_count[0]}.bin").write_bytes(data)
                print(f"  [seeds] {len(data)} B -> "
                      f"seeds_rep{seeds_count[0]}.bin")
        mode = None
        hexbuf = []

    def have_enough():
        return all(got[c] >= args.reps for c in "ABCD")

    print(f"[capture] {args.port} @ {args.baud}, collecting {args.reps} "
          f"valid sequences per condition (reset/reconnect-tolerant)...")

    def open_port():
        """Open with RTS/DTR reset; retry until the port re-appears (the
        CP2102 re-enumerates on ESP32 brown-outs)."""
        while True:
            try:
                s = serial.Serial(args.port, args.baud, timeout=2)
                s.dtr = False
                s.rts = True
                time.sleep(0.1)
                s.rts = False
                s.reset_input_buffer()
                return s
            except serial.SerialException:
                time.sleep(1.5)

    t0 = time.time()
    ser = open_port()
    reconnects = 0
    while time.time() - t0 < args.timeout and not have_enough():
        try:
            raw = ser.readline().decode(errors="replace").strip()
        except serial.SerialException:
            # port dropped mid-read (brown-out / re-enumeration): drop the
            # in-flight block, reopen, keep accumulating -- host-side rep
            # counters make this safe across reconnects
            reconnects += 1
            print(f"  [reconnect #{reconnects}] port dropped, reopening...")
            mode, hexbuf = None, []
            try:
                ser.close()
            except Exception:
                pass
            time.sleep(1.5)
            ser = open_port()
            continue
        if not raw:
            continue
        if raw.startswith("### DEVICE"):
            print(f"  [dev] {raw[4:]}")
        elif raw.startswith("### PUF_BEGIN"):
            mode, hexbuf, meta = "PUF", [], parse_kv(raw)
        elif raw.startswith("### PUF_END"):
            finish_block(raw)
        elif raw.startswith("### RNG_BEGIN"):
            mode, hexbuf, meta = "RNG", [], parse_kv(raw)
        elif raw.startswith("### RNG_END"):
            finish_block(raw)
        elif raw.startswith("### SEEDS_BEGIN"):
            mode, hexbuf, meta = "SEEDS", [], parse_kv(raw)
        elif raw.startswith("### SEEDS_END"):
            finish_block(raw)
        elif raw.startswith("### "):
            pass  # STATUS / CYCLE markers
        elif mode is not None and len(raw) >= 2 and all(
                c in "0123456789abcdef" for c in raw):
            hexbuf.append(raw)
    try:
        ser.close()
    except Exception:
        pass

    if log_rows:
        import csv
        log_path = outdir / "capture_log.csv"
        new = not log_path.exists()
        with log_path.open("a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["cond", "rep", "temp_begin_c", "temp_end_c",
                            "throughput_Bps", "crc_ok"])
            w.writerows(log_rows)
        print(f"[capture] log -> {log_path}")

    summary = ", ".join(f"{c}:{got[c]}" for c in "ABCD")
    if not have_enough():
        print(f"[capture] INCOMPLETE after timeout ({summary})")
        sys.exit(1)
    print(f"[capture] complete ({summary})")


if __name__ == "__main__":
    main()
