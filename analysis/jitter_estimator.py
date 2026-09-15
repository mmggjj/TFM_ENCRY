#!/usr/bin/env python3
"""Estimador embebido de jitter por pares de bits (Fischer y Lubicz,
CHES 2014) con las dos correcciones que exige el metodo para no sesgarse.

Metodo: la fraccion c de pares (b_j, b_{j+M}) distintos dentro de un
bloque es una onda TRIANGULAR de la fase acumulada en M muestras. En la
zona lineal la pendiente vale 2, luego Var(c) = 4*M*Q_raw mas el ruido de
estimar una fraccion con N pares.

Correcciones respecto al ajuste ingenuo de una recta (ambas validadas en
autotest, ver docs/modelo_ero_resultados.md):

  1. Los vertices de la triangular comprimen la varianza. Cuando la fase
     determinista cae cerca de un vertice, Var(c) baja hasta la mitad de
     lo que le toca. El vertice se detecta con la propia media medida:
     c ~ 0 o c ~ 1 es vertice, c ~ 1/2 es el centro de la rampa. Se
     descartan las distancias M cuya media se sale de la banda central y
     aquellas en que la dispersion de fase alcanza el vertice.
  2. El ruido de estimacion NO es constante con M: escala con c*(1-c).
     Se ajusta como segundo regresor en vez de como ordenada en el origen.

Sin estas dos correcciones el estimador subestima Q_raw entre un 13 % y
un 38 % segun el jitter, es decir, subestima la entropia y lleva a elegir
un divisor K_D demasiado grande.
"""
from __future__ import annotations

import numpy as np

from ero_model import simular_bits

# Lista de distancias por defecto: geometrica, para cubrir a la vez la
# zona termica (pendiente 1 en log-log) y el arranque de la de flicker.
M_POR_DEFECTO = np.unique(np.round(np.geomspace(50, 4000, 32)).astype(int))


def fraccion_pares_distintos(bits, M, K, N):
    """Fraccion de pares a distancia M, en K bloques de N pares tomados de
    una tira contigua de bits. Requiere K*N + M bits."""
    L = K * N
    if bits.size < L + M:
        raise ValueError(f"hacen falta {L + M} bits, hay {bits.size}")
    d = np.bitwise_xor(bits[:L], bits[M:M + L])
    return d.reshape(K, N).mean(axis=1)


def fraccion_pares_trozos(trozos, M, N):
    """Igual, pero con los bloques ya separados: matriz (K, L) con una
    captura independiente por fila, L >= N + M.

    Esta es la forma que tendra la campana real: la FPGA captura a la
    velocidad del anillo en una FIFO de N+M bits y la vuelca despacio por
    SPI antes de capturar el siguiente trozo. Los bloques salen
    independientes, que es mejor que la tira contigua.
    """
    trozos = np.atleast_2d(trozos)
    if trozos.shape[1] < N + M:
        raise ValueError(f"cada trozo necesita {N + M} bits, tiene {trozos.shape[1]}")
    d = np.bitwise_xor(trozos[:, :N], trozos[:, M:M + N])
    return d.mean(axis=1)


def curva_varianza(bits, M_list, K=None, N=100):
    """Media y varianza de c para cada M. Acepta tira contigua (1D) o
    matriz de trozos independientes (2D)."""
    bits = np.asarray(bits)
    medias, varianzas = [], []
    for M in M_list:
        if bits.ndim == 2:
            c = fraccion_pares_trozos(bits, int(M), N)
        else:
            c = fraccion_pares_distintos(bits, int(M), K, N)
        medias.append(c.mean())
        varianzas.append(c.var(ddof=1))
    return np.array(medias), np.array(varianzas)


def _ajuste(M_sel, c_sel, var_sel, N):
    """Minimos cuadrados de Var(c) = Q*(4M) + kappa*c(1-c)/N."""
    A = np.vstack([4.0 * M_sel, c_sel * (1.0 - c_sel) / N]).T
    (q, kappa), *_ = np.linalg.lstsq(A, var_sel, rcond=None)
    return float(q), float(kappa)


def estimar_q_raw(bits, M_list=None, K=None, N=100, banda=0.15, k_sigma=3.0,
                  iteraciones=4):
    """Estima Q_raw, la varianza de fase acumulada por muestra (ciclos^2).

    Devuelve un diccionario con la estimacion y el diagnostico completo:
    ninguna magnitud se descarta en silencio, las M usadas quedan
    registradas.
    """
    M_list = M_POR_DEFECTO if M_list is None else np.asarray(M_list)
    medias, varianzas = curva_varianza(bits, M_list, K, N)

    en_banda = (medias > banda) & (medias < 1.0 - banda)
    # Arranque conservador: solo las distancias cortas, donde la fase
    # acumulada no puede haber alcanzado el vertice.
    sel = en_banda & (M_list <= M_list[max(len(M_list) // 3, 1)])
    if sel.sum() < 3:
        sel = en_banda
    if sel.sum() < 3:
        raise ValueError("ninguna distancia M cae en la banda central: "
                         "revisar N, K o el rango de M")
    q, kappa = _ajuste(M_list[sel], medias[sel], varianzas[sel], N)

    for _ in range(iteraciones):
        # Distancia de la fase determinista al vertice mas proximo, en
        # ciclos: la triangular tiene pendiente 2, asi que media/2.
        dist_vertice = np.minimum(medias, 1.0 - medias) / 2.0
        nueva = en_banda & (k_sigma * np.sqrt(M_list * q) < dist_vertice)
        if nueva.sum() < 3:
            break
        q, kappa = _ajuste(M_list[nueva], medias[nueva], varianzas[nueva], N)
        sel = nueva

    return {
        "q_raw": q,
        "sigma_rel": float(np.sqrt(max(q, 0.0))),  # sigma/T por muestra
        "kappa": kappa,
        "M_usadas": M_list[sel],
        "n_M_usadas": int(sel.sum()),
        "M_list": M_list,
        "medias": medias,
        "varianzas": varianzas,
        "seleccion": sel,
    }


def exponente_acumulacion(res):
    """Exponente b del ajuste Var(c) - ruido ~ M^b sobre las M usadas.

    b = 1 indica acumulacion termica (paseo aleatorio, la unica que cuenta
    como entropia); b = 2 indica flicker o jitter determinista global.
    """
    sel = res["seleccion"]
    M = res["M_list"][sel].astype(float)
    c = res["medias"][sel]
    v = res["varianzas"][sel] - res["kappa"] * c * (1.0 - c) / 100.0
    ok = v > 0
    if ok.sum() < 3:
        return float("nan")
    b, _ = np.polyfit(np.log(M[ok]), np.log(v[ok]), 1)
    return float(b)


def kd_necesario(q_raw, q_objetivo=0.2286):
    """Divisor K_D para que la Q de generacion alcance el objetivo.

    Q_gen = K_D * Q_raw (la varianza de fase se acumula linealmente).
    El objetivo por defecto es el que exige min-entropia >= 0,98 por bit
    (AIS 20/31 v3.0, PTG.2.2), calculado en ero_model.q_necesaria.
    """
    return int(np.ceil(q_objetivo / q_raw))


def autotest(verbose=True):
    """Valida el estimador contra bits de Q conocida."""
    fallos = []

    def chk(cond, msg):
        if not cond:
            fallos.append(msg)
        if verbose:
            estado = "ok " if cond else "FALLO"
            print(f"  [{estado}] {msg}")

    K, N = 20_000, 100
    n_bits = K * N + int(M_POR_DEFECTO[-1]) + 10

    if verbose:
        print(f"1) Recuperacion de Q_raw en tira contigua "
              f"({K} bloques x {N} pares, {n_bits / 1e6:.2f} Mbit)")
    for q_real in [2.0e-7, 5.0e-7, 2.0e-6, 8.0e-6, 3.0e-5]:
        bits = simular_bits(n_bits, q_real, semilla=2024)
        r = estimar_q_raw(bits, K=K, N=N)
        err = (r["q_raw"] - q_real) / q_real
        chk(abs(err) < 0.05,
            f"Q_raw {q_real:.2e} -> {r['q_raw']:.3e} ({100 * err:+.2f} %), "
            f"sigma/T = {r['sigma_rel']:.2e}, {r['n_M_usadas']} distancias")

    if verbose:
        print("2) Sin las correcciones el sesgo es grande (recta simple)")
    bits = simular_bits(n_bits, 2.0e-6, semilla=2024)
    Ms = np.arange(200, 1601, 50)
    medias, var = curva_varianza(bits, Ms, K, N)
    A = np.vstack([4.0 * Ms, np.ones_like(Ms, dtype=float)]).T
    (q_ing, _), *_ = np.linalg.lstsq(A, var, rcond=None)
    r = estimar_q_raw(bits, K=K, N=N)
    chk(abs(q_ing / 2.0e-6 - 1) > 0.10 and abs(r["q_raw"] / 2.0e-6 - 1) < 0.05,
        f"recta simple {q_ing:.3e} ({100 * (q_ing / 2e-6 - 1):+.1f} %) frente a "
        f"corregido {r['q_raw']:.3e} ({100 * (r['q_raw'] / 2e-6 - 1):+.1f} %)")

    if verbose:
        print("3) Efecto vertice: la varianza se hunde donde la media se va")
    peor = np.argmin(var / (4.0 * Ms * 2.0e-6))
    mejor = np.argmax(var / (4.0 * Ms * 2.0e-6))
    chk(min(medias[peor], 1 - medias[peor]) < min(medias[mejor], 1 - medias[mejor]),
        f"peor M={Ms[peor]} con media {medias[peor]:.3f} (razon "
        f"{var[peor] / (4 * Ms[peor] * 2e-6):.2f}); mejor M={Ms[mejor]} con "
        f"media {medias[mejor]:.3f}")

    if verbose:
        print("4) Captura por trozos independientes (la forma real)")
    M_tr = np.unique(np.round(np.geomspace(50, 2000, 24)).astype(int))
    K_tr, L_tr = 20_000, int(M_tr[-1]) + N
    q_real = 2.0e-6
    trozos = np.empty((K_tr, L_tr), dtype=np.uint8)
    rng = np.random.default_rng(4)
    for i in range(K_tr):
        trozos[i] = simular_bits(L_tr, q_real, semilla=int(rng.integers(1 << 31)))
    r = estimar_q_raw(trozos, M_list=M_tr, N=N)
    err = (r["q_raw"] - q_real) / q_real
    chk(abs(err) < 0.05,
        f"Q_raw {q_real:.2e} -> {r['q_raw']:.3e} ({100 * err:+.2f} %) con "
        f"{K_tr} trozos de {L_tr} bits = {K_tr * L_tr / 8 / 1024:.0f} kB")

    if verbose:
        print("5) Exponente de acumulacion (el simulador no tiene flicker)")
    bits = simular_bits(n_bits, 2.0e-6, semilla=77)
    r = estimar_q_raw(bits, K=K, N=N)
    b = exponente_acumulacion(r)
    chk(abs(b - 1.0) < 0.10,
        f"exponente {b:.3f}, compatible con acumulacion termica (b = 1)")

    if verbose:
        print("6) Repetibilidad con 8 semillas (Q_raw = 2e-6)")
    ests = []
    for s in range(8):
        bits = simular_bits(n_bits, 2.0e-6, semilla=3000 + s)
        ests.append(estimar_q_raw(bits, K=K, N=N)["q_raw"])
    ests = np.array(ests)
    sesgo = ests.mean() / 2.0e-6 - 1
    disp = ests.std(ddof=1) / ests.mean()
    if verbose:
        print(f"  media {ests.mean():.4e}, sesgo {100 * sesgo:+.2f} %, "
              f"dispersion {100 * disp:.2f} %")
    chk(abs(sesgo) < 0.05, f"sesgo {100 * sesgo:+.2f} %")
    chk(disp < 0.08, f"dispersion {100 * disp:.2f} % con {K} bloques")

    if verbose:
        print("7) Divisor K_D y caudal resultantes (RO2 a 500 MHz supuestos)")
    for q_raw in [5.0e-7, 2.0e-6, 8.0e-6]:
        kd = kd_necesario(q_raw)
        if verbose:
            print(f"  Q_raw {q_raw:.1e} (sigma/T {np.sqrt(q_raw):.1e}) -> "
                  f"K_D = {kd:7d}, caudal {500e6 / kd / 1e3:7.2f} kbit/s")
        chk(kd > 0, f"K_D positivo para Q_raw {q_raw:.1e}")

    print(f"\nautotest jitter_estimator: {len(fallos)} fallos")
    for f in fallos:
        print("  -", f)
    return not fallos


if __name__ == "__main__":
    import sys
    sys.exit(0 if autotest() else 1)
