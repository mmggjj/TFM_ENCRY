#!/usr/bin/env python3
"""Espectro de la frecuencia relativa de los anillos, trozo a trozo.

Metodo de la revision del 18-11-2026 (results/revision_fable_20261118/psd.py):
en cada trozo de 4096 bits se estima nu por FFT, se demodula a esa
frecuencia, se promedia la fase compleja en bloques de L muestras, se
desenvuelve, se quita la recta y la diferencia de fase entre bloques es la
frecuencia instantanea; su espectro se promedia sobre los trozos.

    python analysis/espectro_fase.py --npz <kdNN_trozos.npz | kdNN.bin> --kd 2 --t2-ns 4.878
    python analysis/espectro_fase.py --valida      # bits simulados (tarea 2)

--valida genera trozos con ero_model (Q por periodo de ro2 conocida) con y
sin una modulacion senoidal de frecuencia conocida y da, para cada caso, el
pico y el suelo del espectro: dice si el metodo ve la modulacion y que suelo
pone el propio estimador (Q = 0), es decir, por debajo de que Q el jitter
blanco no se puede resolver con 4096 bits por trozo.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def cargar(p: Path) -> np.ndarray:
    """Trozos de 4096 bits (filas) de un .npz (clave datos) o un kdNN.bin."""
    if p.suffix == ".npz":
        z = np.load(p)
        a = np.unpackbits(z["datos"])
    else:
        a = np.unpackbits(np.fromfile(p, dtype=np.uint8))
    return a[: a.size // 4096 * 4096].reshape(-1, 4096)


def espectro(trozos: np.ndarray, dt_bloque: float, L: int = 16):
    """(frecuencias en Hz, espectro medio, rms de la media sincronizada,
    rms total) de la frecuencia instantanea (ciclos de ro1 por bloque)."""
    x = 2.0 * trozos - 1.0
    n = x.shape[1]
    j = np.arange(n)
    nb = n // L
    P = 0.0
    fr = []
    for t in x:
        s = np.abs(np.fft.rfft(t - t.mean(), n * 16))
        nu = (np.argmax(s[16:]) + 16) / (n * 16.0)
        zc = (t * np.exp(-2j * np.pi * nu * j)).reshape(nb, L).mean(1)
        p = np.unwrap(np.angle(zc)) / (2 * np.pi)
        k = np.arange(nb)
        p = p - np.polyval(np.polyfit(k, p, 1), k)
        f = np.diff(p)
        fr.append(f)
        P = P + np.abs(np.fft.rfft(f * np.hanning(f.size))) ** 2
    P = P / len(x)
    fr = np.array(fr)
    fq = np.fft.rfftfreq(nb - 1, dt_bloque)
    return fq, P, float(fr.mean(0).std()), float(fr.std())


def resumen(fq, P, banda_pico=(25e3, 60e3), banda_suelo=(100e3, 400e3)):
    mp = (fq >= banda_pico[0]) & (fq <= banda_pico[1])
    ms = (fq >= banda_suelo[0]) & (fq <= banda_suelo[1])
    i = np.flatnonzero(mp)[np.argmax(P[mp])]
    return fq[i], P[i], float(np.median(P[ms]))


def simular(n_trozos, q_periodo, kd, t2, nu=0.38388, f_mod=0.0, a_mod=0.0, semilla=0):
    """Trozos de 4096 bits del ERO. q_periodo: Q por periodo de ro2; a_mod:
    amplitud de la modulacion de nu (ciclos de ro1 por muestra), fase
    aleatoria en cada trozo."""
    rng = np.random.default_rng(semilla)
    n = 4096
    ts = (1 << kd) * t2
    s = np.sqrt(q_periodo * (1 << kd))
    k = np.arange(n)
    out = np.empty((n_trozos, n), dtype=np.uint8)
    for i in range(n_trozos):
        th = rng.random() * 2 * np.pi
        incr = nu + a_mod * np.sin(2 * np.pi * f_mod * ts * k + th) + rng.normal(0.0, s, n)
        fase = (rng.random() + np.cumsum(incr)) % 1.0
        out[i] = fase >= 0.5
    return out


def valida(args):
    kd, t2, L = 2, args.t2_ns * 1e-9, args.L
    dt = L * (1 << kd) * t2
    print(f"bits simulados con ero_model: kd {kd}, T(ro2) {args.t2_ns} ns, L {L}, "
          f"{args.trozos} trozos de 4096; bloque {dt * 1e6:.3f} us")
    print("pico: maximo entre 25 y 60 kHz; suelo: mediana entre 100 y 400 kHz")
    print(f"{'caso':38s} {'f pico kHz':>10s} {'pico':>10s} {'suelo':>10s} {'pico/suelo':>10s} {'rms sincr/total':>15s}")
    casos = [(f"Q {q:.1e}, sin modulacion", q, 0.0) for q in (0.0, 1e-6, 3e-6, 1e-5, 1.42e-5, 3e-5)]
    casos += [(f"Q {q:.1e}, 38 kHz a {a:.0e}", q, a) for q in (0.0, 1.1e-6, 1.42e-5)
              for a in (1e-4, 3e-4, 1e-3)]
    for nombre, q, a in casos:
        tr = simular(args.trozos, q, kd, t2, f_mod=38e3, a_mod=a, semilla=1)
        fq, P, ms, mt = espectro(tr, dt, L)
        fp, pp, su = resumen(fq, P)
        print(f"{nombre:38s} {fp / 1e3:10.1f} {pp:10.3e} {su:10.3e} {pp / su:10.1f} {ms / mt:15.3f}")


def calibra(args):
    """Q blanca que reproduce el suelo medido con la raya medida: rejilla de
    Q y amplitud de modulacion a 38 kHz, mismo metodo que los datos."""
    kd, t2, L = 2, args.t2_ns * 1e-9, args.L
    dt = L * (1 << kd) * t2
    print(f"calibracion: kd {kd}, T(ro2) {args.t2_ns} ns, {args.trozos} trozos por punto")
    print(f"{'Q periodo':>10s} {'a_mod':>8s} {'pico':>10s} {'suelo':>10s}")
    for a in args.amplitudes:
        for q in args.qs:
            tr = simular(args.trozos, q, kd, t2, f_mod=38e3, a_mod=a, semilla=2)
            fq, P, _, _ = espectro(tr, dt, L)
            _, pp, su = resumen(fq, P)
            print(f"{q:10.2e} {a:8.1e} {pp:10.3e} {su:10.3e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibra", action="store_true")
    ap.add_argument("--qs", type=float, nargs="*", default=[3e-7, 5e-7, 7e-7, 9e-7, 1.1e-6, 1.3e-6])
    ap.add_argument("--amplitudes", type=float, nargs="*", default=[2.6e-4, 1.05e-3])
    ap.add_argument("--npz", type=Path, nargs="*", default=[])
    ap.add_argument("--kd", type=int, default=2)
    ap.add_argument("--t2-ns", type=float, default=4.878, help="periodo de ro2 en ns")
    ap.add_argument("--L", type=int, default=16, help="muestras por bloque")
    ap.add_argument("--trozos", type=int, default=2000)
    ap.add_argument("--valida", action="store_true")
    ap.add_argument("--lista", action="store_true", help="imprime el espectro hasta 500 kHz")
    args = ap.parse_args()
    if args.valida:
        valida(args)
        return
    if args.calibra:
        calibra(args)
        return
    dt = args.L * (1 << args.kd) * args.t2_ns * 1e-9
    for p in args.npz:
        tr = cargar(p)
        fq, P, ms, mt = espectro(tr, dt, args.L)
        fp, pp, su = resumen(fq, P)
        print(f"{p}: {tr.shape[0]} trozos, kd {args.kd}, bloque {dt * 1e6:.3f} us, unos {tr.mean():.4f}")
        print(f"  pico {fp / 1e3:.1f} kHz {pp:.3e}, suelo (100-400 kHz) {su:.3e}, pico/suelo {pp / su:.1f}, "
              f"rms sincronizada/total {ms / mt:.3f}")
        if args.lista:
            for f, v in zip(fq, P):
                if f <= 500e3:
                    print(f"    {f / 1e3:7.1f} kHz  {v:.3e}")


if __name__ == "__main__":
    main()
