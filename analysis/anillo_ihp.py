#!/usr/bin/env python3
"""Anillo con transistores reales: PDK abierto IHP SG13G2 (130 nm, 1,2 V).

Sustituye los modelos genericos del banco (spice_ring.py) por los del PDK
abierto de IHP (modelo PSP 103.6, licencia Apache 2.0) y cierra la cadena
transistor -> ruido -> jitter -> min-entropia sin suponer el ruido:

 1. Ruido del inversor en su punto de conmutacion (.noise de ngspice): la
    densidad de corriente de ruido termico y 1/f sale del modelo del PDK.
 2. Anillo en transitorio con esa densidad inyectada en cada nudo: jitter
    por periodo, exponente de acumulacion y potencia. Con el ruido apagado,
    la resolucion numerica del banco, que se declara antes que nada.
 3. Contraste con la formula cerrada de Abidi (JSSC 2006) [estimado].
 4. Q por periodo -> K_D para min-entropia >= 0,98 (ero_model).

Herramientas (WSL, espacio de usuario, receta en docs/anillo_ihp.md):
ngspice 47 compilado con OSDI y los modelos Verilog-A del PDK compilados
con OpenVAF-Reloaded. ngspice 41 de conda-forge no sirve: no carga OSDI 0.4.

    python analysis/anillo_ihp.py                 todo (ruido + anillo)
    python analysis/anillo_ihp.py --solo ruido    solo el paso 1
    python analysis/anillo_ihp.py --tstop 300n    anillo mas largo

Aproximacion declarada: el ruido de los transistores se inyecta como una
fuente de corriente blanca por nudo con la densidad del punto de
conmutacion. En realidad es cicloestacionario (cambia a lo largo del
periodo); cerca de la conmutacion, que es cuando mueve el cruce, la
aproximacion es la habitual (Hajimiri, Abidi). ngspice no inyecta en
transitorio el ruido propio de los modelos.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

from spice_ring import (a_wsl, cruces_subida, jitter_desde_cruces, netlist,
                        simular)

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "results"
K_B = 1.380649e-23

# Un hilo: con OpenMP cada ngspice abre 8 hilos; cuatro simulaciones en
# paralelo (32 hilos en 16 nucleos) tardaban 9 min en lo que son 15 s.
# Incluso sola, con un hilo va un 11 % mas rapida (circuito pequeno).
NGSPICE = "OMP_NUM_THREADS=1 $HOME/eda/ngspice47/bin/ngspice"
PDK = "$HOME/eda/IHP-Open-PDK/ihp-sg13g2"


def _home_wsl() -> str:
    r = subprocess.run(["wsl.exe", "-e", "bash", "-lc", "echo $HOME"],
                       capture_output=True, text=True, timeout=60)
    return [l for l in r.stdout.splitlines() if l.startswith("/")][-1].strip()


HOME = _home_wsl()
MODELOS = PDK.replace("$HOME", HOME) + "/libs.tech/ngspice/models"
OSDI = PDK.replace("$HOME", HOME) + "/libs.tech/ngspice/osdi"
SPICEINIT = "\n".join(
    f"osdi '{OSDI}/{m}.osdi'"
    for m in ("psp103", "psp103_nqs", "r3_cmc", "mosvar")) + "\n"
# ngspice fija sus hilos OpenMP con esta variable e ignora OMP_NUM_THREADS:
# con 8 hilos por proceso, cuatro simulaciones en paralelo se ahogaban.
SPICEINIT += "set num_threads=1\n"


def cabecera_ihp(esquina="mos_tt"):
    return f"""
* ---- CABECERA: PDK abierto IHP SG13G2, transistores lv (1,2 V) -----
.lib {MODELOS}/cornerMOSlv.lib {esquina}
.subckt nmos_tec d g s b w=1u l=0.13u
xm d g s b sg13_lv_nmos w={{w}} l={{l}}
.ends
.subckt pmos_tec d g s b w=2u l=0.13u
xm d g s b sg13_lv_pmos w={{w}} l={{l}}
.ends
* --------------------------------------------------------------------
"""


def _lote(texto, directorio, timeout=3600):
    """ngspice en modo lote con .control; devuelve la salida entera."""
    os.makedirs(directorio, exist_ok=True)
    sp = os.path.join(directorio, "banco.sp")
    with open(sp, "w", newline="\n") as f:
        f.write(texto)
    with open(os.path.join(directorio, ".spiceinit"), "w", newline="\n") as f:
        f.write(SPICEINIT)
    r = subprocess.run(
        ["wsl.exe", "-e", "bash", "-lc",
         f"cd '{a_wsl(directorio)}' && {NGSPICE} -b banco.sp"],
        capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr


def _wrdata(ruta):
    """Columnas de un wrdata: (x, y) por vector; se devuelven x e y."""
    d = np.loadtxt(ruta)
    return d[:, 0], d[:, 1]


# --------------------------------------------------------------------
# 1. Ruido del inversor en su punto de conmutacion
# --------------------------------------------------------------------

def ruido_inversor(wn="0.5u", wp="1.2u", l="0.13u", vdd=1.2, temp=27.0,
                   esquina="mos_tt", directorio=None):
    """Densidad de corriente de ruido en el nudo de salida de un inversor
    con la entrada unida a la salida (autopolarizado en V_trip, los dos
    transistores en saturacion: el punto donde el ruido mueve el cruce).

    La fuente de prueba iin inyecta corriente en el nudo; el ruido referido
    a la entrada (inoise_spectrum) es entonces la corriente de ruido
    equivalente del nudo, que es exactamente lo que la fuente trnoise del
    anillo tiene que reproducir.
    """
    d = directorio or tempfile.mkdtemp(prefix="ruido_ihp_")
    texto = f"""* ruido del inversor IHP en su punto de conmutacion
{cabecera_ihp(esquina)}
.temp {temp}
vdd vdd 0 dc {vdd}
xn out out 0 0 nmos_tec w={wn} l={l}
xp out out vdd vdd pmos_tec w={wp} l={l}
iin 0 out dc 0 ac 1
.control
op
let vtrip = v(out)
let idd = -i(vdd)
echo "RESULTADO vtrip $&vtrip"
echo "RESULTADO idd $&idd"
noise v(out) iin dec 10 1 1e11
setplot noise1
wrdata ruido.dat inoise_spectrum
ac dec 10 1 1e11
let zmag = mag(v(out))
wrdata z.dat zmag
quit
.endc
.end
"""
    log = _lote(texto, d)
    res = {}
    for linea in log.splitlines():
        if linea.startswith("RESULTADO"):
            _, k, v = linea.split()
            res[k] = float(v)
    try:
        f, i_n = _wrdata(os.path.join(d, "ruido.dat"))
        fz, z = _wrdata(os.path.join(d, "z.dat"))
    except OSError as e:
        raise RuntimeError(f"ngspice no escribio el ruido:\n{log}") from e
    s_i = i_n ** 2                                      # A^2/Hz, una cara

    # El espectro es S = k_f/f^alfa + S_th hasta ~10 GHz (por encima sube el
    # ruido inducido en puerta). Primero el 1/f, donde domina sin discusion
    # (<= 100 Hz), y despues el suelo termico como mediana de S - 1/f en
    # 1 kHz - 3 GHz. Tomar la mediana de S en 0,1-1 GHz sin restar el 1/f
    # lo sobrestimaba un 6 % con una esquina de ~20 MHz.
    baja = f <= 1e2
    pend, ord0 = np.polyfit(np.log10(f[baja]), np.log10(s_i[baja]), 1)
    alfa = -pend
    k_f = 10 ** ord0                                    # S_fl = k_f / f^alfa
    resto = s_i - k_f / f ** alfa
    # desde 100 kHz: por debajo, el 1/f es >200 veces el termico y un error
    # minimo en k_f deja residuos grandes en la resta
    banda = (f >= 1e5) & (f <= 3e9)
    s_th = float(np.median(resto[banda]))
    plano = float(np.max(resto[banda]) / np.min(resto[banda]))
    f_esquina = (k_f / s_th) ** (1.0 / alfa)
    g0 = 1.0 / float(z[np.argmin(fz)])                  # conductancia del nudo
    gamma_ef = s_th / (4 * K_B * (temp + 273.15) * g0)
    res.update({"wn": wn, "wp": wp, "l": l, "vdd": vdd, "temp": temp,
                "esquina": esquina, "s_termico_A2Hz": s_th,
                "planitud_banda": plano, "alfa_flicker": alfa,
                "k_flicker": k_f, "f_esquina_Hz": f_esquina,
                "g_nudo_S": g0, "gamma_efectiva": gamma_ef,
                "directorio": d})
    return res, f, s_i, log


# --------------------------------------------------------------------
# 2. Anillo en transitorio
# --------------------------------------------------------------------

def anillo(s_i, n_etapas=5, wn="0.5u", wp="1.2u", l="0.13u", vdd=1.2,
           cl="1f", tstop="100n", paso="0.2p", paso_max="1p", nt=5e-13,
           esquina="mos_tt", descartar=20, k_flicker=0.0, devolver_cruces=False):
    """Transitorio del anillo con s_i [A^2/Hz] blanco y, si k_flicker > 0,
    k_flicker/f [A^2] de 1/f, inyectados en cada nudo.
    Devuelve el resultado de jitter_desde_cruces mas potencia y tiempos."""
    flk = (1.0, namp_para(k_flicker)) if k_flicker > 0 else None
    txt = netlist(n_etapas=n_etapas, vdd=vdd, lmin=l, wn=wn, wp=wp, cl=cl,
                  tstop=tstop, paso=paso, paso_max=paso_max,
                  densidad_ruido=s_i, nt_ruido=nt,
                  cabecera=cabecera_ihp(esquina), flicker=flk,
                  guardar=f"v(n{n_etapas}) i(vdd)")
    t0 = time.time()
    nombres, m, log = simular(txt, orden=NGSPICE, spiceinit=SPICEINIT,
                              timeout=6 * 3600)
    dur = time.time() - t0
    t = m[:, 0]
    iv = nombres.index(f"v(n{n_etapas})")
    ii = [k for k, n in enumerate(nombres) if "vdd" in n.lower() and "#branch" in n.lower()
          or n.lower() == "i(vdd)"]
    tc = cruces_subida(t, m[:, iv], vdd / 2.0)
    if tc.size < 60:
        raise RuntimeError(f"solo {tc.size} cruces; ngspice dijo:\n{log[-3000:]}")
    r = jitter_desde_cruces(tc, descartar=descartar)
    # potencia media sobre periodos enteros, quitando el arranque
    p = float("nan")
    if ii:
        a, b = tc[descartar], tc[-1]
        sel = (t >= a) & (t <= b)
        corr = -m[sel, ii[0]]
        p = vdd * float(np.trapezoid(corr, t[sel]) / (t[sel][-1] - t[sel][0]))
    r.update({"potencia_W": p, "segundos": dur, "s_i": s_i, "n_etapas": n_etapas,
              "tstop": tstop, "nt": nt, "cl": cl, "k_flicker": k_flicker})
    if devolver_cruces:
        r["cruces"] = tc
    return r


# --------------------------------------------------------------------
# 2b. Calibracion de la fuente 1/f de ngspice (trnoise NALPHA, NAMP)
# --------------------------------------------------------------------

def calibrar_flicker(namp=1.0, nt=5e-13, tstop="2u", alfa=1.0, directorio=None):
    """Densidad que produce trnoise(0 NT alfa NAMP) en una resistencia de
    1 ohm: se ajusta S(f) = K/f^alfa con un periodograma de Welch sobre la
    tension remuestreada a paso NT. La relacion NAMP -> K no esta en el
    manual de ngspice con la precision necesaria, asi que se mide.
    Devuelve (K, alfa_medido, f, S)."""
    from scipy.signal import welch
    d = directorio or tempfile.mkdtemp(prefix="flk_")
    texto = f"""* calibracion de trnoise 1/f
i1 0 n dc 0 trnoise(0 {nt:.3e} {alfa:g} {namp:.6e})
r1 n 0 1
.options method=gear
.tran {nt:.3e} {tstop} 0 {nt:.3e}
.save v(n)
.end
"""
    nombres, m, log = simular(texto, directorio=d, orden=NGSPICE,
                              spiceinit="set rndseed=1\n", timeout=3600)
    t, v = m[:, 0], m[:, 1]
    tu = np.arange(t[0], t[-1], nt)
    vu = np.interp(tu, t, v)
    f, s = welch(vu, fs=1.0 / nt, nperseg=min(len(vu), 1 << 18))
    # K como media de S*f^alfa en 0,1-10 GHz, donde el espectro es plano en
    # esa escala. Un ajuste en escala log sobre toda la banda lo dominaban
    # los bines altos (suben por la retencion de muestras) y daba la escala
    # con NAMP como x5,75 en vez de x4.
    sel = (f >= 1e8) & (f <= 1e10)
    k = float(np.mean(s[sel] * f[sel] ** alfa))
    pend, _ = np.polyfit(np.log10(f[sel]), np.log10(s[sel]), 1)
    return k, -pend, f, s


# Medido con calibrar_flicker (19-10... ver docs/anillo_ihp.md): con alfa = 1,
# S(f) = K/f con K = NAMP^2 * 0,317, que es 1/pi al 0,4 %. Escala cuadratica
# comprobada (NAMP x2 -> S x3,92) e independiente de la semilla.
K_POR_NAMP2 = 1.0 / np.pi


def namp_para(k_f):
    """Amplitud NAMP de trnoise que da S(f) = k_f / f."""
    return float(np.sqrt(k_f / K_POR_NAMP2))


# --------------------------------------------------------------------
# 2c. Separacion termico / 1/f en la varianza acumulada
# --------------------------------------------------------------------

def separar_componentes(M, var, n):
    """Ajusta E[D(M)^2] = a1*M + a2*M^2 (D = diferencia de segundo orden de
    los cruces, como en jitter_desde_cruces).

    Ruido blanco de frecuencia (termico) -> a1*M con a1 = 2*sigma_T^2.
    Ruido 1/f de frecuencia (flicker) -> varianza de Allan constante ->
    a2*M^2. Es la descomposicion de Benea et al. (TCHES 2024) sin el
    termino de cuantizacion, que aqui no existe (cruces interpolados).

    Minimos cuadrados ponderados: el error relativo de cada var(M) es
    sqrt(2M/n) (ventanas independientes ~ n/M), asi que el peso es
    n / (2 M var^2). Devuelve dict con a1, a2, sigma_termico, M_cruce
    (donde las dos componentes se igualan) y sus errores tipicos.
    """
    M = np.asarray(M, float)
    var = np.asarray(var, float)
    ok = var > 0
    M, var = M[ok], var[ok]
    w = n / (2.0 * M * var ** 2)
    A = np.column_stack([M, M ** 2])
    W = np.sqrt(w)[:, None]
    coef, *_ = np.linalg.lstsq(A * W, var * W[:, 0], rcond=None)
    cov = np.linalg.inv((A * W).T @ (A * W))
    a1, a2 = coef
    e1, e2 = np.sqrt(np.diag(cov))
    return {"a1": float(a1), "a2": float(a2), "e_a1": float(e1), "e_a2": float(e2),
            "sigma_termico": float(np.sqrt(max(a1, 0) / 2.0)),
            "M_cruce": float(a1 / a2) if a2 > 0 else float("inf")}


def _fase_sintetica(n, sigma_t, h_fl, periodo, semilla=0):
    """Instantes de cruce con jitter blanco de frecuencia sigma_t por
    periodo mas ruido 1/f de frecuencia de amplitud relativa h_fl,
    generado filtrando ruido blanco por 1/sqrt(f) en el dominio de Fourier."""
    rng = np.random.default_rng(semilla)
    dT = rng.normal(0.0, sigma_t, n)
    if h_fl > 0:
        x = rng.normal(0.0, 1.0, 2 * n)
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(2 * n)
        f[0] = f[1]
        y = np.fft.irfft(X / np.sqrt(f), 2 * n)[:n]
        dT = dT + h_fl * periodo * y / np.std(y)
    return np.cumsum(periodo + dT)


def autotest_separacion(verbose=True):
    """El separador recupera el termico con y sin 1/f, y el 1/f solo
    aparece cuando existe."""
    from spice_ring import jitter_desde_cruces
    fallos = []
    T, s = 366e-12, 180e-15
    for h, etiqueta in ((0.0, "solo termico"), (2e-4, "termico + 1/f")):
        errs, cruces = [], []
        for sem in range(8):
            tc = _fase_sintetica(20000, s, h, T, semilla=sem)
            n = tc.size
            Ms = np.unique(np.round(np.geomspace(1, n // 8, 24)).astype(int))
            r = jitter_desde_cruces(tc, M_list=Ms, descartar=0)
            sep = separar_componentes(r["M_list"], r["var"], r["n_cruces"])
            errs.append(sep["sigma_termico"] / s - 1.0)
            cruces.append(sep["M_cruce"])
        err = float(np.mean(errs))
        ok = abs(err) < 0.05
        if not ok:
            fallos.append(etiqueta)
        if verbose:
            print(f"  [{'ok ' if ok else 'FALLO'}] {etiqueta}: sigma termico "
                  f"recuperado con sesgo {100 * err:+.1f} % (8 semillas), "
                  f"M de cruce mediano {np.median(cruces):.3g}")
    return not fallos


# --------------------------------------------------------------------
# 2d. Funcion de sensibilidad al impulso (ISF, Hajimiri y Lee 1998)
# --------------------------------------------------------------------
#
# Por que: amplificar el 1/f para verlo en simulaciones cortas no sirve.
# La fuente 1/f de ngspice es de banda ancha (hasta 1/NT), y amplificada
# x1000 su cola en torno a f0 = 2,73 GHz ya es 7 veces el termico: el
# anillo la convierte como ruido blanco y el termino lineal sube x8 (x30
# con x4000), mientras el termino 1/f de verdad no escala (medido el
# 08-10, docs/anillo_ihp.md). La ISF separa las dos conversiones: el ruido
# de baja frecuencia entra por su valor medio Gamma_dc, el blanco por su
# valor eficaz Gamma_rms, y la esquina 1/f^3 del ruido de fase es
# f_1/f * (Gamma_dc / Gamma_rms)^2.

def _cruces_netlist(extra, n_etapas, wn, wp, l, vdd, cl, tstop, esquina,
                    nodo_salida=None):
    txt = netlist(n_etapas=n_etapas, vdd=vdd, lmin=l, wn=wn, wp=wp, cl=cl,
                  tstop=tstop, paso="0.2p", paso_max="0.5p",
                  densidad_ruido=0.0, cabecera=cabecera_ihp(esquina),
                  guardar=f"v(n{nodo_salida or n_etapas})")
    txt = txt.replace("\n.options", f"\n{extra}\n.options", 1)
    nombres, m, log = simular(txt, orden=NGSPICE, spiceinit=SPICEINIT,
                              timeout=3600)
    return cruces_subida(m[:, 0], m[:, 1], vdd / 2.0)


def _isf_punto(args):
    (fase, nodo, t_ref, periodo, dq, ancho, n_etapas, wn, wp, l, vdd, cl,
     tstop, esquina, ref) = args
    t0 = t_ref + fase * periodo
    i_pico = dq / ancho
    extra = (f"iisf 0 n{nodo} dc 0 pulse(0 {i_pico:.6e} {t0:.6e} "
             f"{ancho / 4:.3e} {ancho / 4:.3e} {ancho * 3 / 4:.3e} 1)")
    tc = _cruces_netlist(extra, n_etapas, wn, wp, l, vdd, cl, tstop, esquina)
    n = min(tc.size, ref.size)
    # desplazamiento medio de los cruces bien despues de la inyeccion
    despues = ref[:n] > t0 + 8 * periodo
    dt = float(np.mean(tc[:n][despues] - ref[:n][despues]))
    return fase, dt


def isf(nodo=3, n_fases=40, n_etapas=5, wn="0.5u", wp="1.2u", l="0.13u",
        vdd=1.2, cl="1f", tstop="30n", esquina="mos_tt", dq_rel=0.01,
        procesos=8, fases=None):
    """ISF del nudo `nodo` por inyeccion de carga: una simulacion de
    referencia y una por fase con un pulso de carga dq = dq_rel * q_max
    (q_max = C_nudo * V_DD, con C_nudo estimada del propio anillo).
    Gamma(fase) = -2*pi * dt / T * q_max / dq (Hajimiri: el desfase por
    unidad de carga normalizada). Devuelve fases, gamma, Gamma_dc,
    Gamma_rms y q_max."""
    from concurrent.futures import ThreadPoolExecutor
    ref = _cruces_netlist("", n_etapas, wn, wp, l, vdd, cl, tstop, esquina)
    periodo = float(np.median(np.diff(ref[10:])))
    # cruce de subida de referencia hacia el tercio de la simulacion
    k0 = int(ref.size // 3)
    t_ref = float(ref[k0])
    # C del nudo: I media de carga ~ C*VDD/(T/2); se estima con la potencia:
    # P = N * C * VDD^2 * f  ->  C = P / (N VDD^2 f). Solo fija la escala
    # absoluta de Gamma; el cociente Gamma_dc/Gamma_rms no depende de ella.
    r = anillo(0.0, n_etapas=n_etapas, wn=wn, wp=wp, l=l, vdd=vdd, cl=cl,
               tstop="40n", esquina=esquina, descartar=5)
    c_nudo = r["potencia_W"] / (n_etapas * vdd ** 2 / periodo)
    q_max = c_nudo * vdd
    dq = dq_rel * q_max
    ancho = 2e-12
    fases = np.arange(n_fases) / n_fases if fases is None else np.asarray(fases)
    tareas = [(f, nodo, t_ref, periodo, dq, ancho, n_etapas, wn, wp, l, vdd,
               cl, tstop, esquina, ref) for f in fases]
    with ThreadPoolExecutor(max_workers=procesos) as ex:
        res = sorted(ex.map(_isf_punto, tareas))
    fases = np.array([x[0] for x in res])
    dt = np.array([x[1] for x in res])
    gamma = -2 * np.pi * dt / periodo * (q_max / dq)
    return {"nodo": nodo, "fases": fases, "dt": dt, "gamma": gamma,
            "gamma_dc": float(np.mean(gamma)),
            "gamma_rms": float(np.sqrt(np.mean(gamma ** 2))),
            "periodo": periodo, "q_max": q_max, "c_nudo": c_nudo,
            "dq": dq, "t_ref": t_ref}


# --------------------------------------------------------------------
# 3. Formula cerrada de Abidi (JSSC 2006), solo como orden de magnitud
# --------------------------------------------------------------------

def abidi_sigma_rel(potencia, vdd, v_car, f0, temp=27.0, eta=1.0):
    """sigma_T / T por periodo para jitter de ruido blanco.

    Abidi: L(df) = (8/(3 eta)) (kT/P) (VDD/V_car) (f0/df)^2. Para ruido
    blanco la varianza del instante crece como c*t con c = L df^2 / f0^2
    (en segundos), asi que sigma_T^2 = c*T y
    sigma_T/T = sqrt((8/(3 eta)) (kT/P) (VDD/V_car) f0).
    (Una primera version olvidaba el factor f0 y daba 1e-8: cuatro ordenes
    por debajo; el contraste con la simulacion lo delato.)"""
    kt = K_B * (temp + 273.15)
    return float(np.sqrt((8.0 / (3.0 * eta)) * kt / potencia * vdd / v_car * f0))


def ruido_por_tipo(wn="0.5u", wp="1.2u", l="0.13u", vdd=1.2, temp=27.0,
                   esquina="mos_tt", i_pol=None):
    """Ruido de cada tipo de transistor por separado: un nmos y un pmos
    conectados como diodo y alimentados por una fuente de corriente ideal
    (sin ruido) con la corriente del punto de conmutacion. El ruido referido
    a esa fuente es el del transistor solo. Devuelve {"n": (S_th, K, alfa),
    "p": (...)}. Sirve para ver si el 1/f de n y p es parecido: si no lo es,
    los dos lobulos de la ISF no se compensan y el 1/f se convierte mucho
    mas en jitter."""
    if i_pol is None:
        i_pol = ruido_inversor(wn=wn, wp=wp, l=l, vdd=vdd, temp=temp,
                               esquina=esquina)[0]["idd"]
    sal = {}
    for tipo, linea in (("n", f"xn d d 0 0 nmos_tec w={wn} l={l}\nib 0 d dc {i_pol:.6e} ac 1"),
                        ("p", f"vdd vdd 0 dc {vdd}\nxp d d vdd vdd pmos_tec w={wp} l={l}\nib d 0 dc {i_pol:.6e} ac 1")):
        d = tempfile.mkdtemp(prefix=f"ruido_{tipo}_")
        texto = f"""* ruido de un {tipo}mos conectado como diodo
{cabecera_ihp(esquina)}
.temp {temp}
{linea}
.control
op
let vd = v(d)
echo "RESULTADO vd $&vd"
noise v(d) ib dec 10 1 1e11
setplot noise1
wrdata ruido.dat inoise_spectrum
quit
.endc
.end
"""
        log = _lote(texto, d)
        f, i_n = _wrdata(os.path.join(d, "ruido.dat"))
        s = i_n ** 2
        baja = f <= 1e2
        pend, ord0 = np.polyfit(np.log10(f[baja]), np.log10(s[baja]), 1)
        k = 10 ** ord0
        resto = s - k / f ** (-pend)
        banda = (f >= 1e5) & (f <= 3e9)
        vd = [float(x.split()[2]) for x in log.splitlines() if x.startswith("RESULTADO vd")]
        sal[tipo] = {"s_termico": float(np.median(resto[banda])), "k_flicker": float(k),
                     "alfa": float(-pend), "v_d": vd[0] if vd else float("nan")}
    return sal


def v_caracteristica(r1):
    """V_car de Abidi sin pasar por V_T. En canal largo V_car = dV/gamma y
    g_m = 2 I_D / dV, luego V_car = 2 I_D / (gamma g_m). En el punto de
    conmutacion g_nudo ~ g_mn + g_mp ~ 2 g_m, de ahi 4 I/(gamma g_nudo).
    Con V_T: los transistores estan casi en el umbral (V_trip - V_T ~ 0,07 V)
    y la ley cuadratica de la que sale dV no vale; esta forma usa solo
    magnitudes medidas en el mismo punto."""
    return 4.0 * r1["idd"] / (r1["gamma_efectiva"] * r1["g_nudo_S"])


def vt_nmos(wn="0.5u", l="0.13u", vdd=1.2, temp=27.0, esquina="mos_tt"):
    """Tension umbral por extrapolacion lineal en el maximo de gm, con
    V_DS pequena (metodo ELR). Solo para el contraste de Abidi."""
    d = tempfile.mkdtemp(prefix="vt_ihp_")
    texto = f"""* tension umbral del nmos lv
{cabecera_ihp(esquina)}
.temp {temp}
vd d 0 dc 0.05
vg g 0 dc 0
xn d g 0 0 nmos_tec w={wn} l={l}
.control
dc vg 0 {vdd} 0.005
let id = -i(vd)
wrdata idvg.dat id
quit
.endc
.end
"""
    log = _lote(texto, d)
    vg, i_d = _wrdata(os.path.join(d, "idvg.dat"))
    gm = np.gradient(i_d, vg)
    k = int(np.argmax(gm))
    return float(vg[k] - i_d[k] / gm[k] - 0.05 / 2.0)


# --------------------------------------------------------------------

def main() -> int:
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", choices=["ruido", "anillo", "todo"], default="todo")
    ap.add_argument("--etapas", type=int, default=5)
    ap.add_argument("--wn", default="0.5u")
    ap.add_argument("--wp", default="1.2u")
    ap.add_argument("--cl", default="1f")
    ap.add_argument("--tstop", default="100n")
    ap.add_argument("--nt", type=float, default=5e-13)
    ap.add_argument("--esquina", default="mos_tt")
    ap.add_argument("--sesion", default=time.strftime("%Y%m%d_%H%M%S"))
    ap.add_argument("--escalas", default="0,1,4",
                    help="multiplos de la densidad del PDK a simular (0 = resolucion)")
    args = ap.parse_args()
    RES.mkdir(exist_ok=True)

    print("== 1. Ruido del inversor en su punto de conmutacion (PDK IHP) ==")
    r1, f, s_i, log1 = ruido_inversor(wn=args.wn, wp=args.wp,
                                      esquina=args.esquina)
    np.savetxt(RES / f"anillo_ihp_ruido_{args.sesion}.csv",
               np.column_stack([f, s_i]), delimiter=",",
               header="f_Hz,S_i_A2Hz", comments="")
    for k, v in r1.items():
        print(f"  {k} = {v}")
    if args.solo == "ruido":
        return 0

    print("\n== 2. Anillo en transitorio ==")
    vt = vt_nmos(wn=args.wn, esquina=args.esquina)
    print(f"  V_T del nmos (extrapolacion lineal) = {vt:.4f} V")
    filas = []
    salida = RES / f"anillo_ihp_{args.sesion}.csv"
    cab = ["escala", "s_i_A2Hz", "etapas", "cl", "tstop", "nt_s", "n_cruces",
           "periodo_ps", "sigma_fs", "sigma_rel", "q_periodo", "exponente",
           "potencia_uW", "segundos"]
    with salida.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cab)
        for esc in [float(x) for x in args.escalas.split(",")]:
            s = esc * r1["s_termico_A2Hz"]
            r = anillo(s, n_etapas=args.etapas, wn=args.wn, wp=args.wp,
                       cl=args.cl, tstop=args.tstop, nt=args.nt,
                       esquina=args.esquina)
            fila = [esc, s, args.etapas, args.cl, args.tstop, args.nt,
                    r["n_cruces"], r["periodo"] * 1e12,
                    r["sigma_periodo"] * 1e15, r["sigma_rel"],
                    r["q_por_periodo"], r["exponente"],
                    r["potencia_W"] * 1e6, r["segundos"]]
            w.writerow(fila)
            fh.flush()
            filas.append(dict(zip(cab, fila)))
            print(f"  escala {esc:4g}: S_i {s:.3e} A2/Hz, {r['n_cruces']} cruces, "
                  f"T {r['periodo'] * 1e12:.3f} ps, sigma {r['sigma_periodo'] * 1e15:.3f} fs, "
                  f"sigma/T {r['sigma_rel']:.3e}, exp {r['exponente']:.2f}, "
                  f"P {r['potencia_W'] * 1e6:.1f} uW, {r['segundos']:.0f} s", flush=True)

    print("\n== 3. Lectura ==")
    base = [x for x in filas if x["escala"] == 0]
    uno = [x for x in filas if x["escala"] == 1]
    cuatro = [x for x in filas if x["escala"] == 4]
    if base and uno:
        print(f"  resolucion del banco {base[0]['sigma_fs']:.3f} fs frente a "
              f"{uno[0]['sigma_fs']:.3f} fs con el ruido del PDK "
              f"(margen x{uno[0]['sigma_fs'] / base[0]['sigma_fs']:.0f})")
    if uno and cuatro:
        print(f"  ley de la raiz: S x4 -> sigma x{cuatro[0]['sigma_fs'] / uno[0]['sigma_fs']:.3f} "
              f"(teorico x2,000)")
    if uno:
        u = uno[0]
        f0 = 1e12 / u["periodo_ps"]
        gam = r1["gamma_efectiva"]
        v_car = v_caracteristica(r1)
        ab = abidi_sigma_rel(u["potencia_uW"] * 1e-6, 1.2, v_car, f0)
        print(f"  Abidi (orden de magnitud; V_car = 4 I_trip/(gamma g_nudo) = {v_car:.3f} V, "
              f"gamma medida {gam:.2f}): sigma/T = {ab:.3e} frente a {u['sigma_rel']:.3e} "
              f"simulado (cociente {u['sigma_rel'] / ab:.2f})")
        from ero_model import entropias_exactas
        from jitter_estimator import kd_necesario
        kd = kd_necesario(u["q_periodo"])
        sh, hmin, _ = entropias_exactas(kd * u["q_periodo"])
        f2 = 1e12 / u["periodo_ps"]
        print(f"  Q por periodo {u['q_periodo']:.3e} -> K_D = {kd} -> H_min = {hmin:.4f}; "
              f"con el anillo de muestreo a {f2 / 1e9:.2f} GHz, {f2 / kd / 1e3:.1f} kbit/s")
    with (RES / f"anillo_ihp_{args.sesion}.json").open("w", encoding="utf-8") as fh:
        json.dump({"ruido": {k: v for k, v in r1.items() if k != "directorio"},
                   "vt_nmos_V": vt, "anillo": filas}, fh, indent=1)
    print(f"\ndatos en {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
