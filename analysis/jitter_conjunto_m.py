#!/usr/bin/env python3
"""Ajuste conjunto (un nu por trozo) de jitter_autocorrelacion con un alcance M a eleccion:
    python3 analysis/jitter_conjunto_m.py <kdNN_trozos.npz> <M max>
(la orden --conjunto de jitter_autocorrelacion.py fija M = 30)."""
import sys, numpy as np
sys.path.insert(0, __import__("os").path.dirname(__file__))
import jitter_autocorrelacion as ja
npz, mmax = sys.argv[1], int(sys.argv[2])
z = np.load(npz); kd = int(z["kd"])
cortes = np.cumsum(z["longitudes"])[:-1]
lista = [np.unpackbits(t) for t in np.split(z["datos"], cortes)]
r = ja.ajuste_conjunto(lista, m_max=mmax)
print(f"{npz}: conjunto M=1..{mmax}: Q/muestra {r['q']:.4e}, por periodo de ro2 {r['q']/2**kd:.4e}, "
      f"residuo/ruido {r['residuo']/r['ruido']:.2f}, saturado {r['saturado']}")
