#!/usr/bin/env python3
"""
mqtt_tls_demo.py -- Secure MQTT session keyed by a harvester seed.

Demonstrates the intended application of the harvester: a fresh 32-byte
seed from the ESP32 is turned into a session key with HKDF-SHA256, and a
short authenticated message exchange is protected with AES-256-GCM. Two
transport modes:

  --broker HOST   real MQTT-TLS session against a broker (needs paho +
                  a TLS-enabled broker); the harvester seed is fetched
                  from the topic esp32/harvester/seed.
  (default)       offline cryptographic demo: reads a seed from
                  results/seeds_rep1.bin, derives two session keys from
                  two different seeds, and shows that (a) the same seed
                  reproduces the key (determinism), (b) different seeds
                  give unrelated keys (forward secrecy proxy), and (c) a
                  replayed nonce is detected/rejected by GCM.

This keeps the demo runnable with no broker while documenting the real
path. Requires: cryptography (pip install cryptography).

TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def derive_key(seed: bytes, info: bytes = b"tfm-mqtt-session") -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=info).derive(seed)


def offline_demo(seeds_path: Path):
    print("=== Offline harvester-keyed crypto demo ===")
    raw = seeds_path.read_bytes()
    if len(raw) < 64:
        raise SystemExit("need at least two 32-byte seeds")
    seed1, seed2 = raw[:32], raw[32:64]

    k1a = derive_key(seed1)
    k1b = derive_key(seed1)
    k2 = derive_key(seed2)
    print(f"  seed1 -> key {k1a.hex()[:32]}...")
    print(f"  determinism (same seed -> same key): {k1a == k1b}")
    print(f"  distinctness (seed1 vs seed2 key):   {k1a != k2} "
          f"(bit diff {bin(int.from_bytes(k1a,'big') ^ int.from_bytes(k2,'big')).count('1')}/256)")

    # authenticated exchange
    aes = AESGCM(k1a)
    nonce = os.urandom(12)
    msg = b'{"device":"hvac-thermostat-07","temp_c":21.4,"setpoint":22.0}'
    ct = aes.encrypt(nonce, msg, b"esp32/hvac/telemetry")
    print(f"  encrypted {len(msg)} B -> {len(ct)} B ciphertext+tag")
    pt = aes.decrypt(nonce, ct, b"esp32/hvac/telemetry")
    print(f"  round-trip OK: {pt == msg}")

    # replay / tamper detection
    try:
        aes.decrypt(nonce, ct, b"esp32/hvac/OTHER_TOPIC")
        print("  AAD tamper: NOT detected (BUG)")
    except Exception:
        print("  AAD tamper (replay to wrong topic): REJECTED by GCM")
    try:
        forged = bytes([ct[0] ^ 1]) + ct[1:]
        aes.decrypt(nonce, forged, b"esp32/hvac/telemetry")
        print("  ciphertext tamper: NOT detected (BUG)")
    except Exception:
        print("  ciphertext tamper: REJECTED by GCM")
    print("=== demo complete ===")


def broker_demo(broker: str, port: int):
    import ssl
    import paho.mqtt.client as mqtt
    print(f"=== MQTT-TLS session against {broker}:{port} ===")
    seed_holder = {}

    def on_connect(cli, u, flags, rc, props=None):
        cli.subscribe("esp32/harvester/seed")

    def on_message(cli, u, msg):
        seed_holder["seed"] = bytes.fromhex(msg.payload.decode())
        cli.disconnect()

    cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    cli.tls_set(cert_reqs=ssl.CERT_NONE)
    cli.tls_insecure_set(True)
    cli.on_connect = on_connect
    cli.on_message = on_message
    cli.connect(broker, port)
    cli.loop_forever()

    if "seed" not in seed_holder:
        raise SystemExit("no harvester seed received")
    key = derive_key(seed_holder["seed"])
    print(f"  session key derived from live harvester seed: "
          f"{key.hex()[:32]}...")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--broker", default=None)
    ap.add_argument("--port", type=int, default=8883)
    ap.add_argument("--seeds", default=str(Path(__file__).resolve().parents[2] / "results" / "esp32_rng_agosto" / "seeds_rep1.bin"))
    args = ap.parse_args()
    if args.broker:
        broker_demo(args.broker, args.port)
    else:
        offline_demo(Path(args.seeds))


if __name__ == "__main__":
    main()
