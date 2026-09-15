#!/usr/bin/env python3
"""Banco de simulacion del oscilador de anillo a nivel de transistores.

Genera la descripcion del circuito, lanza ngspice, lee el fichero de
resultados y extrae el jitter. El numero que sale de aqui (sigma por
periodo) es la entrada de ero_model.entropias_exactas, que lo convierte
en min-entropia: asi la cadena va del transistor a la entropia sin pasar
por ninguna suposicion.

Portabilidad. Toda la parte que depende de la tecnologia esta en la
cabecera del netlist: nombres de modelo, anchuras, longitud minima y
tension de alimentacion. Para pasar de los modelos genericos de aqui a un
PDK real (Cadence, Spectre) solo se cambia esa cabecera. Los modelos
genericos de este fichero son un MARCADOR DE POSICION para depurar el
flujo: sus numeros absolutos no valen para la memoria.

Medida del jitter: se extraen los instantes de cruce por la mitad de la
alimentacion y se estudia la varianza de t(k+M) - t(k) frente a M. Si la
pendiente es lineal, el jitter es blanco (termico) y la pendiente es
sigma^2 por periodo. Es el mismo analisis que en la FPGA, ver
jitter_estimator.py.

IMPORTANTE, resolucion del instrumento: un simulador tiene ruido
numerico propio. Antes de interpretar ningun jitter hay que repetir la
simulacion con las fuentes de ruido apagadas y comprobar que el jitter
medido entonces es mucho menor. Esa es la resolucion del banco.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import numpy as np

# --------------------------------------------------------------------
# Generacion del netlist
# --------------------------------------------------------------------

CABECERA_GENERICA = """
* ---- CABECERA DEPENDIENTE DE LA TECNOLOGIA -------------------------
* Modelos MARCADOR DE POSICION (MOS nivel 1). Sustituir por el .lib del
* PDK real; el resto del fichero no cambia.
.model nmos_tec nmos (level=1 vto=0.45 kp=300u gamma=0.4 lambda=0.08
+ phi=0.9 tox=4.1n cgso=0.2n cgdo=0.2n cj=1m mj=0.5 cjsw=0.2n)
.model pmos_tec pmos (level=1 vto=-0.45 kp=100u gamma=0.4 lambda=0.12
+ phi=0.9 tox=4.1n cgso=0.2n cgdo=0.2n cj=1m mj=0.5 cjsw=0.2n)
* --------------------------------------------------------------------
"""

PLANTILLA = """* Oscilador de anillo, {n_etapas} etapas - banco de jitter
{cabecera}
.param vdd_v = {vdd}
.param lmin  = {lmin}
.param wn    = {wn}
.param wp    = {wp}
.param cl    = {cl}

vdd vdd 0 dc {{vdd_v}}
ven en  0 dc {{vdd_v}}

* Inversor
.subckt inv a y vdd vss
mp y a vdd vdd pmos_tec w={{wp}} l={{lmin}}
mn y a vss vss nmos_tec w={{wn}} l={{lmin}}
cc y vss {{cl}}
.ends

* NAND de dos entradas, para arrancar y parar el anillo
.subckt nand2 a b y vdd vss
mp1 y a vdd vdd pmos_tec w={{wp}} l={{lmin}}
mp2 y b vdd vdd pmos_tec w={{wp}} l={{lmin}}
mn1 y a nx  vss nmos_tec w={{2*wn}} l={{lmin}}
mn2 nx b vss vss nmos_tec w={{2*wn}} l={{lmin}}
cc y vss {{cl}}
.ends

* Cadena: etapa 0 es la NAND, el resto inversores
xnand en n{n_ultima} n1 vdd 0 nand2
{cadena}

* Fuentes de ruido: una por nudo. Emulan el ruido de los dispositivos,
* que ngspice no inyecta solo. NA se calcula desde la densidad espectral
* objetivo: NA = sqrt(S_i / (2*NT)).
{ruido}

.options reltol=1e-5 abstol=1e-13 vntol=1e-9 chgtol=1e-15 trtol=1
.options method=gear maxord=2
.tran {paso} {tstop} {tinicio} {paso_max}
.save {senal}
.end
"""


def netlist(n_etapas=5, vdd=1.8, lmin="0.18u", wn="1u", wp="2u", cl="1f",
            tstop="2u", paso="0.2p", paso_max="1p", tinicio="0",
            densidad_ruido=0.0, nt_ruido=1e-12, cabecera=None):
    """Devuelve el netlist como texto.

    densidad_ruido: densidad espectral de corriente de ruido por nudo, en
    A^2/Hz (una cara). 0 desactiva el ruido, que es como se mide la
    resolucion numerica del banco.
    nt_ruido: paso temporal de la fuente de ruido, en segundos.
    """
    if n_etapas % 2 == 0:
        raise ValueError("el numero de etapas debe ser impar")

    cadena = "\n".join(
        f"xinv{i} n{i} n{i + 1} vdd 0 inv" for i in range(1, n_etapas)
    )

    if densidad_ruido > 0.0:
        na = np.sqrt(densidad_ruido / (2.0 * nt_ruido))
        ruido = "\n".join(
            f"iru{i} n{i} 0 dc 0 trnoise({na:.6e} {nt_ruido:.3e} 0 0)"
            for i in range(1, n_etapas + 1)
        )
    else:
        ruido = "* sin ruido: mide la resolucion numerica del banco"

    return PLANTILLA.format(
        n_etapas=n_etapas,
        n_ultima=n_etapas,
        cabecera=CABECERA_GENERICA if cabecera is None else cabecera,
        vdd=vdd, lmin=lmin, wn=wn, wp=wp, cl=cl,
        cadena=cadena, ruido=ruido,
        tstop=tstop, paso=paso, paso_max=paso_max, tinicio=tinicio,
        senal=f"v(n{n_etapas})",
    )


# --------------------------------------------------------------------
# Lectura del fichero de resultados de ngspice (formato raw binario)
# --------------------------------------------------------------------

def leer_raw(ruta):
    """Lee un raw binario de ngspice. Devuelve (nombres, matriz)."""
    with open(ruta, "rb") as f:
        contenido = f.read()
    marca = b"Binary:\n"
    pos = contenido.find(marca)
    if pos < 0:
        raise ValueError("no es un raw binario de ngspice")
    cabecera = contenido[:pos].decode("latin-1")
    datos = contenido[pos + len(marca):]

    n_vars = n_pts = None
    nombres = []
    leyendo = False
    for linea in cabecera.splitlines():
        if linea.startswith("No. Variables:"):
            n_vars = int(linea.split(":")[1])
        elif linea.startswith("No. Points:"):
            n_pts = int(linea.split(":")[1])
        elif linea.startswith("Variables:"):
            leyendo = True
        elif leyendo and linea.strip():
            partes = linea.split()
            if len(partes) >= 2:
                nombres.append(partes[1])
    if n_vars is None or n_pts is None:
        raise ValueError("cabecera del raw incompleta")

    complejo = "complex" in cabecera.lower().split("flags:")[-1][:20]
    tipo = np.complex128 if complejo else np.float64
    m = np.frombuffer(datos, dtype=tipo, count=n_vars * n_pts)
    m = m.reshape(n_pts, n_vars)
    return nombres[:n_vars], (m.real if complejo else m)


# --------------------------------------------------------------------
# Extraccion de cruces y jitter
# --------------------------------------------------------------------

def cruces_subida(t, v, umbral):
    """Instantes de cruce ascendente por el umbral, con interpolacion
    lineal entre las dos muestras que lo rodean.

    El sesgo de la interpolacion es practicamente el mismo en cada flanco,
    asi que se cancela al calcular varianzas, que es lo unico que se usa.
    """
    t = np.asarray(t, dtype=float)
    v = np.asarray(v, dtype=float)
    por_debajo = v[:-1] < umbral
    por_encima = v[1:] >= umbral
    idx = np.flatnonzero(por_debajo & por_encima)
    if idx.size == 0:
        return np.empty(0)
    v0, v1 = v[idx], v[idx + 1]
    t0, t1 = t[idx], t[idx + 1]
    frac = (umbral - v0) / np.where(v1 != v0, v1 - v0, np.inf)
    return t0 + frac * (t1 - t0)


def jitter_desde_cruces(tc, M_list=None, descartar=10):
    """Analiza la acumulacion de jitter a partir de los cruces.

    Se usa la DIFERENCIA DE SEGUNDO ORDEN de los instantes de cruce,
    D(M) = t[k+2M] - 2*t[k+M] + t[k], que es la varianza de Allan aplicada
    a datos de fase. Dos motivos frente a la diferencia simple:

      - su valor esperado es cero sin restar ninguna media muestral, asi
        que no hereda el sesgo de usar ventanas solapadas (la diferencia
        simple subestimaba un 5 % de forma sistematica), ni depende de
        cuanto valga el periodo;
      - separa las componentes de ruido por su exponente, que es como
        Benea et al. (TCHES 2024) caracterizan el jitter de anillos tanto
        en Artix-7 como en silicio de 28 nm.

    Para un paseo aleatorio de fase con varianza sigma^2 por periodo,
    E[D(M)^2] = 2*M*sigma^2. Un exponente distinto de 1 delata flicker o
    ruido determinista, que no cuentan como entropia.
    """
    tc = np.asarray(tc, dtype=float)[descartar:]
    n = tc.size
    if n < 50:
        raise ValueError(f"hacen falta mas cruces para estadistica: {n}")
    periodo = float(np.polyfit(np.arange(n), tc, 1)[0])

    if M_list is None:
        m_max = max(int(n // 8), 2)
        M_list = np.unique(np.round(np.geomspace(1, m_max, 20)).astype(int))
    M_list = np.asarray([m for m in M_list if 2 * m < n - 1])

    var = np.array([np.mean((tc[2 * m:] - 2.0 * tc[m:-m] + tc[:-2 * m]) ** 2)
                    for m in M_list])

    # E[D(M)^2] = 2*M*sigma^2, luego cada M da una estimacion de sigma^2.
    # No se promedian por igual: con M grande apenas hay ventanas
    # independientes (del orden de n/M), asi que su estimacion es mucho mas
    # ruidosa. Se ponderan por el numero de ventanas independientes, que es
    # la ponderacion de varianza inversa. Ajustar una recta sin ponderar
    # dejaba la dispersion en el 15 % por mas ciclos que se simulasen,
    # porque el ajuste lo dominaban precisamente los peores puntos.
    usar = M_list <= max(int(n * 0.05), 2)
    if usar.sum() < 2:
        usar = M_list <= M_list[min(3, M_list.size - 1)]
    s2 = var[usar] / (2.0 * M_list[usar])
    peso = np.maximum(n / M_list[usar] - 2.0, 1.0)
    pendiente = float(np.sum(peso * s2) / np.sum(peso))
    ok = var > 0
    expo = (float(np.polyfit(np.log(M_list[ok]), np.log(var[ok]), 1)[0])
            if ok.sum() >= 3 else float("nan"))

    sigma = float(np.sqrt(max(pendiente, 0.0)))
    return {
        "periodo": periodo,
        "sigma_periodo": sigma,
        "sigma_rel": sigma / periodo if periodo else float("nan"),
        "q_por_periodo": (sigma / periodo) ** 2 if periodo else float("nan"),
        "exponente": expo,
        "M_list": M_list,
        "var": var,
        "n_cruces": n,
    }


# --------------------------------------------------------------------
# Ejecucion
# --------------------------------------------------------------------

# ngspice se instalo en el espacio de usuario de WSL con micromamba, sin
# root: en esta maquina sudo pide contrasena. Se prueban las dos rutas.
NGSPICE_WSL = "$HOME/eda/bin/ngspice"


def hay_ngspice():
    return shutil.which("ngspice") is not None or _ngspice_wsl() is not None


def _ngspice_wsl():
    """Devuelve la orden con la que invocar ngspice en WSL, o None."""
    for orden in (NGSPICE_WSL, "ngspice"):
        try:
            r = subprocess.run(
                ["wsl.exe", "-e", "bash", "-lc", f"{orden} -v 2>&1 | head -2"],
                capture_output=True, text=True, timeout=120)
            if "ngspice" in r.stdout.lower():
                return orden
        except Exception:
            continue
    return None


def simular(texto_netlist, directorio=None, usar_wsl=None, timeout=1800):
    """Lanza ngspice en modo lote y devuelve (nombres, matriz, salida)."""
    directorio = directorio or tempfile.mkdtemp(prefix="ring_")
    os.makedirs(directorio, exist_ok=True)
    sp = os.path.join(directorio, "ring.sp")
    raw = os.path.join(directorio, "ring.raw")
    with open(sp, "w") as f:
        f.write(texto_netlist)

    if usar_wsl is None:
        usar_wsl = shutil.which("ngspice") is None

    if usar_wsl:
        orden = _ngspice_wsl()
        if orden is None:
            raise RuntimeError("no se encuentra ngspice ni en Windows ni en WSL")

        def w(p):
            p = os.path.abspath(p).replace("\\", "/")
            return "/mnt/" + p[0].lower() + p[2:]
        cmd = ["wsl.exe", "-e", "bash", "-lc",
               f"{orden} -b -r '{w(raw)}' '{w(sp)}'"]
    else:
        cmd = ["ngspice", "-b", "-r", raw, sp]

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if not os.path.exists(raw):
        raise RuntimeError(f"ngspice no genero el raw.\n{r.stdout}\n{r.stderr}")
    nombres, m = leer_raw(raw)
    return nombres, m, r.stdout + r.stderr


# --------------------------------------------------------------------
# Validacion sin simulador
# --------------------------------------------------------------------

def _onda_sintetica(periodo, sigma, n_periodos, muestreo, vdd=1.8,
                    t_flanco=None, semilla=0):
    """Onda con jitter acumulado CONOCIDO, muestreada a paso fijo.

    Sirve para comprobar que la extraccion de cruces y el ajuste del
    jitter funcionan antes de tener ngspice: si no recuperan el sigma que
    se les inyecta, no serviran con datos reales.
    """
    rng = np.random.default_rng(semilla)
    t_flanco = t_flanco if t_flanco is not None else periodo / 8.0
    cruces = np.cumsum(periodo + rng.normal(0.0, sigma, n_periodos))
    # El eje arranca justo antes del primer cruce real: si empezara en
    # cero, el borde virtual que se anade abajo para que el flanco sea
    # continuo caeria dentro del intervalo y se contaria como un cruce mas.
    t = np.arange(cruces[0] - periodo / 4.0,
                  cruces[-1] + periodo / 4.0, muestreo)
    # Forma de onda local: para cada muestra se busca en que ciclo cae y
    # se evalua solo el flanco de ese ciclo. Sumar una tangente por cruce
    # sobre todo el eje seria O(ciclos x muestras) y no termina.
    bordes = np.concatenate(([cruces[0] - periodo], cruces,
                             [cruces[-1] + periodo]))
    k = np.clip(np.searchsorted(bordes, t, side="right") - 1,
                1, bordes.size - 2)

    def escalon(x):
        return 0.5 * (1.0 + np.tanh(x / t_flanco))

    # Tres ciclos alrededor de cada muestra: los mas lejanos aportan un
    # escalon de subida y otro de bajada que se cancelan.
    v = np.zeros_like(t)
    for desp in (-1, 0, 1):
        subida = bordes[k + desp]
        v += escalon(t - subida) - escalon(t - (subida + periodo / 2.0))
    return t, v * vdd, cruces


def autotest(verbose=True):
    """Valida lo que no necesita ngspice: netlist y cadena de analisis."""
    fallos = []

    def chk(cond, msg):
        if not cond:
            fallos.append(msg)
        if verbose:
            print(f"  [{'ok ' if cond else 'FALLO'}] {msg}")

    if verbose:
        print("1) Generacion del netlist")
    txt = netlist(n_etapas=5, densidad_ruido=1e-20)
    chk("xnand en n5 n1" in txt, "el anillo se cierra: la NAND toma n5 y da n1")
    chk(txt.count("xinv") == 4, "5 etapas = 1 NAND + 4 inversores")
    chk("trnoise(" in txt, "las fuentes de ruido se instancian")
    chk("trnoise" not in netlist(n_etapas=5, densidad_ruido=0.0),
        "con densidad 0 no hay fuentes de ruido (modo resolucion)")
    try:
        netlist(n_etapas=4)
        chk(False, "un numero par de etapas deberia rechazarse")
    except ValueError:
        chk(True, "un numero par de etapas se rechaza")

    if verbose:
        print("2) La amplitud de ruido sale de la densidad espectral")
    s_i, nt = 1e-20, 1e-12
    na_esperada = np.sqrt(s_i / (2 * nt))
    chk(f"{na_esperada:.6e}" in netlist(n_etapas=3, densidad_ruido=s_i,
                                        nt_ruido=nt),
        f"NA = sqrt(S/(2*NT)) = {na_esperada:.3e} A")

    if verbose:
        print("3) Extraccion de cruces sobre onda sintetica")
    periodo, sigma = 1e-9, 2e-12
    t, v, reales = _onda_sintetica(periodo, sigma, 400, muestreo=1e-12,
                                   semilla=1)
    tc = cruces_subida(t, v, 0.9)
    chk(abs(tc.size - reales.size) <= 2,
        f"cruces detectados {tc.size} frente a {reales.size} reales")
    n = min(tc.size, reales.size)
    desfase = np.median(tc[:n] - reales[:n])
    error = np.std(tc[:n] - reales[:n] - desfase)
    chk(error < 0.1 * sigma,
        f"error de posicion {error:.3e} s, muy por debajo del jitter "
        f"{sigma:.1e} s")

    if verbose:
        print("4) Recuperacion del jitter inyectado")
    for sig in [5e-13, 2e-12, 8e-12]:
        t, v, reales = _onda_sintetica(periodo, sig, 4000, muestreo=1e-12,
                                       semilla=7)
        tc = cruces_subida(t, v, 0.9)
        r = jitter_desde_cruces(tc)
        err = (r["sigma_periodo"] - sig) / sig
        chk(abs(err) < 0.12,
            f"sigma inyectado {sig:.2e} -> medido {r['sigma_periodo']:.2e} "
            f"({100 * err:+.1f} %), exponente {r['exponente']:.2f}")

    if verbose:
        print("5) Exponente de acumulacion = 1 con jitter blanco")
    t, v, _ = _onda_sintetica(periodo, 2e-12, 4000, muestreo=1e-12, semilla=3)
    r = jitter_desde_cruces(cruces_subida(t, v, 0.9))
    chk(abs(r["exponente"] - 1.0) < 0.15,
        f"exponente {r['exponente']:.3f}")

    if verbose:
        print("6) Enlace con el modelo de entropia")
    try:
        from ero_model import entropias_exactas
        from jitter_estimator import kd_necesario
        q_periodo = r["q_por_periodo"]
        kd = kd_necesario(q_periodo)
        sh, hmin, _ = entropias_exactas(kd * q_periodo)
        if verbose:
            print(f"  sigma/T = {r['sigma_rel']:.3e} -> Q por periodo "
                  f"{q_periodo:.3e} -> K_D = {kd} -> H_min = {hmin:.4f}")
        chk(hmin >= 0.9799, "con ese K_D se alcanza la min-entropia objetivo")
    except ImportError as e:
        chk(False, f"no se pudo enlazar con el modelo: {e}")

    if verbose:
        print("7) Disponibilidad del simulador")
    disp = hay_ngspice()
    print(f"  [{'ok ' if disp else '-- '}] ngspice "
          f"{'disponible' if disp else 'NO instalado todavia'}")

    print(f"\nautotest spice_ring: {len(fallos)} fallos")
    for f in fallos:
        print("  -", f)
    return not fallos


if __name__ == "__main__":
    import sys
    sys.exit(0 if autotest() else 1)
