# Anillo con transistores reales: PDK abierto IHP SG13G2

Fecha: 2026-10-08. Sustituye los modelos genéricos de nivel 1 del banco
SPICE por los transistores del PDK abierto de IHP (130 nm, núcleo a 1,2 V,
modelo PSP 103.6, licencia Apache 2.0) y cierra la cadena
transistor → ruido → jitter → min-entropía **sin suponer el ruido**: la
densidad que se inyecta sale del propio modelo del PDK.

Código: `analysis/anillo_ihp.py` (usa `analysis/spice_ring.py`) y
`analysis/anillo_ihp_repeticiones.py` (§4.1). Resultados: `results/anillo_ihp_*`.

Revisado el 30-10-2026: §4 y §5 pasan de una realización (σ = 180,37 fs,
K_D = 941 107) a la media de ocho (σ = 176,7 ± 2,0 fs, K_D = 981 095);
los ficheros `anillo_ihp_e5_400n.*` se sustituyeron por `anillo_ihp_rep400n_*`.

## 1. Herramientas (WSL, espacio de usuario, sin root)

El ngspice 41 de conda-forge no sirve: los modelos PSP del PDK vienen en
Verilog-A y hay que compilarlos a OSDI; OpenVAF-Reloaded genera OSDI 0.4 y
ngspice solo lo carga desde la versión 44. Ningún canal de paquetes tiene
versiones más nuevas ni OpenVAF, y el servidor de binarios de OpenVAF
(fides.fe.uni-lj.si) no responde desde esta red. Se compiló todo:

| Pieza | Versión | Origen | Dónde queda |
|---|---|---|---|
| ngspice | 47 (con OSDI, KLU, OpenMP, XSPICE) | tarball oficial de SourceForge, sha256 894e6496…f675f | `~/eda/ngspice47/bin/ngspice` |
| OpenVAF-Reloaded | master 5ed9e63 (2026-08-20) | GitHub OpenVAF-Reloaded/OpenVAF | `~/eda/bin/openvaf-r` |
| Rust + LLVM 20 + clang 20 | 1.98.1 / 20.1.8 | conda-forge (micromamba) | `~/openvaf-env` |
| PDK IHP | commit 5e6d592 (2026-09-01), solo `libs.tech/ngspice` y `verilog-a` | GitHub IHP-GmbH/IHP-Open-PDK (sparse) | `~/eda/IHP-Open-PDK` |
| Modelos OSDI | psp103, psp103_nqs, r3_cmc, mosvar, cap_cmomi, cap_cmomf | compilados con el script del PDK | `…/libs.tech/ngspice/osdi/` |

Receta:

1. ngspice: `./configure --prefix=$HOME/eda/ngspice47 --with-x=no
   --with-readline=no --enable-osdi --enable-xspice --enable-cider
   --enable-openmp` con el gcc de `~/eda90b`; `make -j12 && make install`.
   La compilación da dos avisos de nombres repetidos en el modelo XSPICE
   `file_source`, que no se usa.
2. OpenVAF: entorno con `rust llvmdev=20 llvm-tools=20 clang=20 lld=20 zlib
   zstd libxml2 gcc_linux-64 gxx_linux-64 binutils`; `./configure
   --llvm=20` y `cargo build --release -p openvaf-driver --features llvm20`.
   Sin clang falla un script de compilación (genera un objeto de Windows).
   El paquete `verilogae_py` (enlace con Python) no compila con este Rust,
   pero no hace falta: se construye solo el programa `openvaf-r`.
3. Modelos: `openvaf-compile-va.sh` del PDK (quitándole los retornos de
   carro de Windows) con `openvaf-r` en el PATH.
4. ngspice carga los modelos desde un `.spiceinit` en el directorio de la
   simulación (`osdi '<ruta>/psp103.osdi'` …); `spice_ring.simular` lo
   escribe allí y lanza ngspice desde ese directorio.

El banco genérico se cambió para que cada cabecera de tecnología defina
dos subcircuitos `nmos_tec`/`pmos_tec` (en IHP los transistores ya son
subcircuitos). Comprobado que no cambia nada: el anillo genérico da el
mismo periodo que antes, 230,295 ps, y la autoprueba pasa 7/7.

## 2. Ruido del inversor en su punto de conmutación [simulado]

Inversor W_n = 0,5 µm, W_p = 1,2 µm, L = 0,13 µm, 27 °C, esquina típica,
con la entrada unida a la salida (autopolarizado en V_trip, los dos
transistores en saturación). El ruido referido a una fuente de corriente
de prueba en el nudo es exactamente la corriente de ruido que la fuente
del anillo tiene que reproducir.

| Magnitud | Valor |
|---|---|
| V_trip | 0,6305 V (V_DD/2 = 0,6: inversor equilibrado) |
| Corriente en V_trip | 11,3 µA |
| Conductancia del nudo | 0,238 mS |
| Ruido térmico S_th | **4,127·10⁻²⁴ A²/Hz**, plano de 100 kHz a 10 GHz |
| γ efectiva = S_th / (4kT·g) | 1,04 (canal corto: más de los 2/3 de canal largo) |
| Ruido 1/f | **S = K/f^α con K = 8,156·10⁻¹⁷ A², α = 1,000** |
| Frecuencia de esquina 1/f | **19,8 MHz** |
| V_T del nmos (extrapolación lineal) | 0,557 V |

El espectro es 1/f puro más un suelo plano hasta 10 GHz; por encima de
30 GHz sube (ruido inducido en puerta), lejos de lo que importa aquí. Un
primer cálculo del suelo como mediana entre 100 MHz y 1 GHz daba
4,385·10⁻²⁴, un 6 % de más, porque a 100 MHz el 1/f todavía suma un 20 %:
se corrigió restando el 1/f antes de tomar la mediana. La mediana se toma
de 100 kHz a 3 GHz (planitud 1,002); los resultados guardados hasta el
30-10 se habían hecho con la banda desde 1 kHz (4,126·10⁻²⁴, planitud
1,11), un 0,013 % menos.

## 3. Calibración de la fuente 1/f de ngspice

`trnoise(NA NT NALPHA NAMP)` genera 1/f con amplitud NAMP, pero el manual
no da la relación con la densidad con precisión suficiente: se midió con
una fuente sola sobre 1 Ω, 1 µs a paso 0,5 ps, periodograma de Welch.

| NAMP | `rndseed` | S·f por bandas 10 MHz … 1 THz (A²) |
|---|---|---|
| 1 | 1 | 0,341 · 0,318 · 0,315 · 0,321 · 0,381 |
| 2 | 1 | 1,197 · 1,201 · 1,252 · 1,260 · 1,491 |
| 1 | 2 | 0,350 · 0,318 · 0,317 · 0,323 · 0,381 |

S·f es plano de 10 MHz a 100 GHz (la última banda sube por la retención de
muestras), escala con NAMP² (×3,92 frente a ×4) y dos realizaciones con
NAMP = 1 coinciden. **K = 0,317·NAMP², que es 1/π al 0,4 %.** La columna
`rndseed` no fija la realización: en ngspice 47 el ruido de `trnoise`
(blanco y 1/f) sale del generador de Wallace, que se siembra con
`getpid()` al arrancar, y ni `set rndseed`, ni `setseed`, ni
`.options seed` lo resiembran (solo tocan el Tausworthe;
`src/frontend/trannoise/wallace.c`, `initw`; comprobado el 30-10 con un
circuito mínimo). Las tres filas son realizaciones independientes. Para el
PDK: NAMP = √(π·K) = 1,60·10⁻⁸ A. Un primer ajuste en escala logarítmica
sobre toda la banda daba ×5,75 en vez de ×4, porque lo dominaban los bines
altos: se cambió a media de S·f en 0,1-10 GHz.

## 4. Anillo de 5 etapas en transitorio [simulado]

Anillo: NAND de arranque + 4 inversores, W_n = 0,5 µm, W_p = 1,2 µm,
L = 0,13 µm, 1 fF por nudo como estimación del cableado (antes del trazado),
1,2 V, 27 °C, esquina típica. 400 ns por punto, paso máximo 1 ps, fuente de
ruido con NT = 0,5 ps (banda de 1 THz, muy por encima de los flancos). Se
descartan los 20 primeros cruces (arranque).

| Ruido inyectado | Realizaciones | Cruces | Periodo (ps) | σ por periodo (fs) | σ/T | Exponente | Potencia (µW) |
|---|---|---|---|---|---|---|---|
| ninguno (resolución del banco) | 1 (determinista) | 1071 | 366,039 | 0,675 | 1,85·10⁻⁶ | 0,42 | 143,0 |
| térmico del PDK, 4,127·10⁻²⁴ A²/Hz | **8** | 1073-1074 | 365,968 | **176,7 ± 2,0** | **4,83·10⁻⁴** | 0,99 (0,93-1,08) | 143,0 |
| térmico ×4 | 1 | 1073 | 365,978 | 351,0 | 9,59·10⁻⁴ | 0,92 | 143,0 |
| térmico + 1/f del PDK | 1 | 1073 | 365,974 | 183,33 | 5,01·10⁻⁴ | 1,005 | 143,0 |

El ± es una desviación típica de la media de las ocho; σ medio sale de
promediar Q = (σ/T)². La fila con 1/f es de la tanda del 08-10 (S_th de
4,126·10⁻²⁴); el resto, del 30-10 en Linux (`anillo_ihp_rep400n_*`).

Lectura:

- **Resolución primero.** Sin ruido el banco mide 0,68 fs, 262 veces por
  debajo del jitter con el ruido del PDK. Su exponente (0,42) muestra que
  ese suelo es ruido numérico, no un paseo aleatorio.
- **Ley de la raíz.** Ruido ×4 → σ ×1,99 ± 0,06 frente a ×2,000 teórico
  (la ×4 es una realización, con la dispersión de una sola). El periodo
  medio no se mueve (365,97 ps en todos los puntos con ruido): el banco está
  dentro del régimen lineal, al contrario que el punto alto del banco
  genérico.
- **Exponente 0,99** (media de ocho). Ruido blanco: la varianza acumulada
  crece lineal con el número de periodos, como supone el modelo de Baudet.
- **Contraste con Abidi** (JSSC 2006, orden de magnitud). Con
  V_car = 4·I_trip/(γ·g_nudo) = 0,181 V, todo medido en el mismo punto,
  la fórmula da σ/T = 1,18·10⁻³; la simulación da 0,41 veces eso. Mismo
  orden. Dos tropiezos documentados: una primera versión de la fórmula
  olvidaba el factor f₀ y daba 10⁻⁸ (cuatro órdenes de menos), y la forma
  de canal largo con V_T (V_car = (V_DD/2 − V_T)/γ) no sirve aquí porque
  en el punto de conmutación los transistores están casi en el umbral
  (V_trip − V_T ≈ 0,07 V); con ella salía un cociente de 0,20.

### 4.1 Incertidumbre: ocho realizaciones

ngspice 47 no deja fijar la realización del ruido (§3), así que cada
ejecución es otra realización y la incertidumbre sale de repetir:
`analysis/anillo_ihp_repeticiones.py` lanza ocho en paralelo.

| Realización | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| σ (fs) | 178,7 | 186,5 | 173,8 | 175,1 | 175,0 | 182,5 | 171,8 | 169,0 |

Dispersión entre realizaciones: 3,3 % en σ (5,7 fs), algo más que el
2,2 % que darían ~1070 periodos independientes. Lo que antes era la cifra
(180,37 fs, una realización en Windows) queda a +0,65 veces la dispersión
entre realizaciones de la media; otra en Linux el 30-10, fuera de estas
ocho, dio 171,06 fs (−0,97). El periodo, la potencia,
V_T y la densidad de ruido no dependen de la realización y coinciden entre
Windows y Linux (la densidad, bit a bit).

### 4.2 Esquinas y temperatura (30-10-2026)

Esquinas ss, tt y ff a −40, 27 y 125 °C; en cada punto se recalcula la
densidad del PDK (`--esquina`, `--temp`; el `.temp` llega también al
transitorio: a 125 °C el periodo pasa a 379,9 ps). Cuatro realizaciones
por punto (ocho en tt a 27 °C), 400 ns, solo con el térmico. Ficheros
`results/anillo_ihp_esq_<esquina>_<T>_*` (−40 se escribe `m40`).

| Esquina | T | Periodo (ps) | P (µW) | σ (fs) | σ/T | K_D para H_∞ ≥ 0,98 | H_∞ con 2²⁰ | 2²¹ | 2²² |
|---|---|---|---|---|---|---|---|---|---|
| ss | −40 °C | 438,6 | 117,5 | 138,1 ± 1,3 | 3,15·10⁻⁴ | **2 306 215** (2 262 960 – 2 351 156) | 0,781 | **0,970** | 0,9995 |
| ss | 27 °C | 451,7 | 113,8 | 187,8 ± 2,1 | 4,16·10⁻⁴ | 1 322 114 | 0,950 | 0,9986 | 1,0000 |
| ss | 125 °C | 469,6 | 109,6 | 274,8 ± 5,5 | 5,85·10⁻⁴ | 667 499 | 0,9985 | 1,0000 | 1,0000 |
| tt | −40 °C | 358,8 | 146,2 | 141,7 ± 0,6 | 3,95·10⁻⁴ | 1 465 702 | 0,929 | 0,9971 | 1,0000 |
| tt | 27 °C | 366,0 | 143,0 | 176,7 ± 2,0 | 4,83·10⁻⁴ | 981 095 | 0,985 | 0,9999 | 1,0000 |
| tt | 125 °C | 379,9 | 138,3 | 239,1 ± 3,2 | 6,29·10⁻⁴ | 577 234 | 0,9995 | 1,0000 | 1,0000 |
| ff | −40 °C | 289,7 | 184,8 | 125,0 ± 3,1 | 4,32·10⁻⁴ | 1 227 368 | 0,962 | 0,9992 | 1,0000 |
| ff | 27 °C | 295,7 | 180,8 | 153,8 ± 2,6 | 5,20·10⁻⁴ | 845 499 | 0,993 | 1,0000 | 1,0000 |
| ff | 125 °C | 309,0 | 174,3 | 210,2 ± 2,0 | 6,80·10⁻⁴ | 493 808 | 0,9999 | 1,0000 | 1,0000 |

H_∞ con el Q medio; a −1σ de Q, ss a −40 °C da 0,773 / 0,968 / 0,9994.

**Alimentación ±10 % y esquinas asimétricas, a −40 °C** (30-10-2026,
`--vdd`; cuatro realizaciones por punto, ocho en ss a 1,08 V; ficheros
`anillo_ihp_esq_ss_m40_v108_*`, `_ss_m40_v132_*`, `_sf_m40_*`,
`_fs_m40_*`, y `_tt_m40_v108_*`, `_sf_m40_v108_*`, `_fs_m40_v108_*`). La densidad del inversor se recalcula también con la
tensión: a 1,08 V en ss y −40 °C el inversor conmuta casi en inversión
débil (V_T 0,66 V, corriente de conmutación 0,8 µA) y el térmico baja a
5,13·10⁻²⁵ A²/Hz.

| Punto (−40 °C) | V_DD | Periodo (ps) | P (µW) | σ (fs) | σ/T | K_D para H_∞ ≥ 0,98 | H_∞ con 2²¹ | 2²² | 2²³ |
|---|---|---|---|---|---|---|---|---|---|
| **ss** | **1,08 V** | 587,7 | 70,8 | 144,0 ± 1,8 | 2,45·10⁻⁴ | **3 808 445** (3 713 192 – 3 908 714) | 0,855 | **0,9873** | 0,9999 |
| tt | 1,08 V | 465,7 | 91,0 | 160,2 ± 1,2 | 3,44·10⁻⁴ | 1 932 207 | 0,986 | 0,9999 | 1,0000 |
| sf | 1,08 V | 467,9 | 90,5 | 178,7 ± 3,8 | 3,82·10⁻⁴ | 1 566 766 | 0,9956 | 1,0000 | 1,0000 |
| fs | 1,08 V | 464,2 | 91,2 | 168,1 ± 0,9 | 3,62·10⁻⁴ | 1 743 907 | 0,9919 | 1,0000 | 1,0000 |
| ss | 1,20 V | 438,6 | 117,5 | 138,1 ± 1,3 | 3,15·10⁻⁴ | 2 306 215 | 0,970 | 0,9995 | 1,0000 |
| ss | 1,32 V | 350,9 | 178,1 | 124,5 ± 1,3 | 3,55·10⁻⁴ | 1 816 181 | 0,990 | 0,9999 | 1,0000 |
| sf | 1,20 V | 359,1 | 146,1 | 149,3 ± 0,8 | 4,16·10⁻⁴ | 1 321 853 | 0,9986 | 1,0000 | 1,0000 |
| fs | 1,20 V | 358,2 | 146,4 | 137,7 ± 0,3 | 3,85·10⁻⁴ | 1 546 328 | 0,9960 | 1,0000 | 1,0000 |

A −1σ de Q, ss a 1,08 V da 0,845 / 0,9856 / 0,9999. Con las cuatro primeras realizaciones de ss a 1,08 V salía K_D = 3 913 109 y 0,9855 con 2²²; las ocho lo bajan un 3 % y reducen a la mitad el error.

Lectura:

- **El frío es el peor caso, no el calor.** σ/T sube con T en las tres
  esquinas (el térmico va con kT y el periodo cambia poco), así que el
  K_D necesario cae de −40 a 125 °C en un factor 3,5 (ss), 2,5 (tt) y
  2,5 (ff).
- **La esquina lenta es peor que la rápida** a igual temperatura: con
  menos corriente baja más el ruido que lo que se alarga el periodo.
- **ss a −40 °C combina las dos peor que su producto**: por separado, Q ×
  0,74 (ss) y Q × 0,67 (frío) darían × 0,50; juntas dan × 0,43.
- **2²⁰ solo cumple en tt a 27 °C o mejor; 2²¹ no cubre ss a −40 °C
  (0,970); 2²² cubre toda la rejilla a 1,2 V** (0,9995 en el peor punto)
  con 0,51 – 0,82 kbit/s según la esquina.
- **La tensión baja es el tercer factor, y el más fuerte.** En ss a
  −40 °C, de 1,2 a 1,08 V el periodo se alarga un 34 % y σ casi no cambia
  (el ruido baja con la corriente al mismo ritmo que sube el tiempo de
  conmutación), así que σ/T cae y K_D sube × 1,65. A 1,32 V pasa lo
  contrario (× 0,79). El peor punto simulado es **ss, −40 °C, 1,08 V:
  K_D = 3,81 M**. En tt el mismo paso de tensión pide × 1,32.
- **2²² aún lo cubre, pero justo:** H_∞ = 0,9873 (0,9856 a −1σ), un 10 %
  de margen en K_D y 3,6 errores estándar; un margen del orden del que se
  juzgó insuficiente para 2²⁰ en tt a 27 °C (7 %, §5). **2²³ da 0,9999** en el peor
  punto (0,20 – 0,41 kbit/s en los puntos simulados).
- **Las esquinas asimétricas quedan cerca de tt (1,47 M) y por debajo de ss:** sf y fs a −40 °C
  piden 1,32 M y 1,55 M, menos que ss (2,31 M). A 1,08 V tt, sf y fs
  piden 1,93, 1,57 y 1,74 M, la mitad que ss: **ss a −40 °C y 1,08 V es el
  peor punto simulado**. ff a 1,08 V no se ha simulado (es la esquina con
  menos K_D en todo lo demás).
- La dispersión entre realizaciones va del 0,8 al 5,0 % en σ (cuatro
  realizaciones dan una estimación pobre de la dispersión; el error de la
  media sale de ella).

### 4.3 Desapareamiento: Monte Carlo de chips (31-10-2026)

`--mismatch` usa la sección `<esquina>_mismatch` de `cornerMOSlv.lib` y
`mm_ok=1` en cada transistor: el PDK sortea por instancia V_T, movilidad,
W y L (`sg13g2_moslv_mismatch.lib`). ngspice tampoco deja fijar la semilla
de ese sorteo (`rndseed` no le llega), así que cada ejecución es un chip
distinto con su propia realización de ruido. La densidad de ruido sigue
saliendo del inversor nominal; lo que cambia de chip a chip es el anillo.
Sin `--mismatch` el resultado es el de siempre (366,0389 ps, idéntico).
Ficheros `results/anillo_ihp_mc_<punto>_*` (un CSV de ruido por tanda).

**tt, 27 °C, 1,2 V, 48 chips** [simulado]:

| | Nominal (8 realizaciones, §4.1) | Con desapareamiento (48 chips) |
|---|---|---|
| Periodo | 366,04 ps | 365,91 ps, dispersión **1,31 %** (4,79 ps; 357,8 – 374,5) |
| Potencia | 143,0 µW | 143,1 µW, dispersión 1,2 % |
| σ por periodo | 176,7 ± 2,0 fs | 177,2 ± 0,7 fs |
| Dispersión de σ/T entre ejecuciones | 3,3 % (IC 95 % 2,2 – 6,7) | 2,6 % (IC 95 % 2,2 – 3,2) |
| K_D para H_∞ ≥ 0,98 | 981 095 | 974 260 (967 086 – 981 541) |
| K_D de cada ejecución | 959 000 – 1 004 000 (de la media) | 874 619 – 1 090 974, mediana 971 107 |

Lectura:

- **El desapareamiento mueve el periodo, no el jitter relativo.** La media
  de σ no cambia y la dispersión de σ/T entre chips (2,6 %) no supera la
  que da el propio ruido entre realizaciones del mismo anillo (3,3 %, con
  solo ocho). Con esta resolución el desapareamiento no añade dispersión
  medible a Q; como cota, a lo sumo ~3 % en σ/T (~6 % en K_D).
- **σ absoluto sí sigue al periodo:** r = 0,54 (p = 7·10⁻⁵), σ ∝ T^1,25
  entre chips. El chip lento tiene más jitter por periodo y casi el mismo
  σ/T (∝ T^0,25), que es lo que fija la entropía.
- **El K_D de cada chip incluye el error de estimación** de su propia
  realización (~1070 periodos), así que el intervalo 0,87 – 1,09 M es un
  envolvente pesimista. El máximo queda 3,8 veces por debajo de 2²².
- **RO1 y RO2 nunca son iguales:** entre dos chips del sorteo (las 1128
  parejas de los 48) la diferencia de periodo tiene mediana 1,4 %, p95
  3,5 % y máximo 4,6 %. Dos anillos idénticos en el mismo dado se separan
  en ese orden; si se enganchan por acoplamiento es otra cuestión
  (trazado), no de este banco.

**ss, −40 °C, 1,08 V (el peor punto de §4.2), 16 chips** [simulado]. Uno,
el 9, da σ = 780 fs y exponente 0,33, y no es jitter: sus 676 + 10 cruces
a 590,8 ps ocupan 405,3 ns, más que los 400 ns simulados, cuando los
otros quince ocupan 392,1 – 394,0 ns. Hay al menos ~20 cruces de más
(dobles cruces de un flanco lento por V_DD/2, que `cruces_subida` no
filtra porque no tiene histéresis), y un error de fase blanco así da
justo un exponente bajo. La forma de onda no se guarda y la realización
no se puede repetir (sin semilla), así que se excluye por esa
inconsistencia y no por su valor. En los 48 de tt ese cociente va de
396,1 a 398,9 ns, sin ninguno fuera. El resumen del script
(`_resumen.log`) lo incluye; las cifras de abajo son de los otros quince,
calculadas del mismo `_resumen.csv`.

| | Nominal (8 realizaciones, §4.2) | Con desapareamiento (15 chips) |
|---|---|---|
| Periodo | 587,7 ps | 587,3 ps, dispersión **1,64 %** |
| Potencia | 70,8 µW | 70,8 µW, dispersión 1,6 % |
| σ por periodo | 144,0 ± 1,8 fs | 142,5 ± 1,2 fs |
| Dispersión de σ/T entre ejecuciones | 3,6 % | 3,2 % (IC 95 % 2,4 – 5,1) |
| K_D para H_∞ ≥ 0,98 | 3 808 445 | 3 885 159 (3 821 396 – 3 951 085) |
| K_D de cada ejecución | — | 3 496 727 – **4 494 997**, mediana 3 825 074 |
| H_∞ con 2²² (media / −1σ / peor chip) | 0,9873 / 0,9856 / — | 0,9860 / 0,9848 / **0,973** |
| H_∞ con 2²³ (media / peor chip) | 0,9999 / — | 0,9999 / **0,9996** |

Lectura:

- **Lo mismo que en tt:** la media de σ y la dispersión de σ/T no se
  separan del caso nominal; el periodo se dispersa un 1,6 % (RO1 frente a
  RO2: mediana 1,6 %, máximo 6,2 %).
- **σ sigue aquí al periodo con más fuerza** (r = 0,83, σ ∝ T^2,3): en el
  peor punto el chip lento tiene *más* σ/T, no menos.
- **El peor chip ya no cabe en 2²²:** pide 4,49 M > 4,19 M y da
  H_∞ = 0,973. Ese máximo lleva dentro el error de estimación de un solo
  chip (~650 periodos), así que es pesimista, pero el margen de 2²² sobre
  la media también baja (de 10 % a 8 %). **2²³ cubre el peor chip con
  margen 1,87 (H_∞ = 0,9996).** Se mantiene la recomendación de §5: con
  ±10 % de alimentación, 2²³.
- Pendiente del banco: histéresis en la detección de cruces (o rechazar
  ejecuciones cuyo cociente cruces × periodo no cuadre con el tiempo
  simulado), y guardar la forma de onda cuando el exponente se aparte de 1.

## 5. Del jitter al divisor [simulado → estimado]

Con σ = 176,7 ± 2,0 fs (Q medio) y T = 365,97 ps:

| Magnitud | Valor |
|---|---|
| Q por periodo, (σ/T)² | (2,330 ± 0,054)·10⁻⁷ |
| Constante de difusión c = σ²/T | 8,53·10⁻¹⁷ s |
| K_D para H_min ≥ 0,98 (Q ≥ 0,2286), contando solo el jitter de RO1 | **981 095** (958 895 – 1 004 347 a ±1σ) |
| Intervalo de muestreo y caudal con RO2 igual (2,73 GHz) | 359 µs → **2,79 kbit/s** (2,72 – 2,85) |
| Si se cuenta también el jitter de RO2 (independiente e igual) | K_D = 490 548 → 5,6 kbit/s |
| Con el divisor que admite el RTL, 2²⁰ | Q = 0,244 ± 0,006, H_∞ = 0,9853 (0,9836 – 0,9868); 2,606 kbit/s |
| Para la consigna Q = 0,30 | K_D ≥ 1 287 499 → 2²¹: H_∞ = 0,9999, 1,303 kbit/s |
| Peor punto de la rejilla a 1,2 V (ss, −40 °C, §4.2) | K_D ≥ 2 306 215 → 2²²: Q = 0,416, H_∞ = 0,9995, 0,544 kbit/s (también cumple la consigna Q = 0,30, que pide 3 026 540) |
| **Peor punto con V_DD −10 % (ss, −40 °C, 1,08 V, §4.2)** | K_D ≥ 3 808 445 → 2²² da Q = 0,252, H_∞ = 0,9873 (10 % de margen; no cumple la consigna Q = 0,30, que pide 4 997 959); **2²³**: Q = 0,504, H_∞ = 0,9999, 0,203 kbit/s |

Lo de arriba es tt a 27 °C. Para un divisor fijo que valga de −40 a
125 °C en ss/tt/ff a 1,2 V, hace falta 2²² (`CFG_KD` = 22): el caudal baja a
0,51 – 0,82 kbit/s. **Si además se admite V_DD ± 10 %, 2²² queda con un
10 % de margen y lo recomendable es 2²³ (`CFG_KD` = 23): 0,20 – 0,41
kbit/s, ≈ 1,9 s para los 384 bits de una siembra en el peor punto.** El
Monte Carlo de desapareamiento (§4.3) lo confirma: en ese punto el peor de
quince chips pide 4,49 M, por encima de 2²² (H_∞ = 0,973), y 2²³ lo cubre
con H_∞ = 0,9996.
Alternativa: fijar `CFG_KD` según la temperatura
medida (2²⁰ basta en tt por encima de 27 °C), que exige un sensor y una
tabla caracterizada por chip. `CFG_KD` arranca en 24 tras el reset, así
que un maestro que no lo escriba ya está del lado seguro.

El caudal cae dentro del rango que se estimó sin transistores reales
(1-17 kbit/s, `modelo_ero_resultados.md`). La cifra conservadora es la
primera: el jitter de RO2 suma, pero contarlo exige que los dos anillos no
compartan ruido (alimentación, sustrato), y eso solo se puede comprobar en
silicio.

**Consecuencia de diseño aplicada:** el contador del divisor del ERO tenía
20 bits, K_D máximo 2²⁰ = 1 048 576, solo un 11 % por encima de lo
necesario en esquina típica a 27 °C con la primera realización (un 7 %,
de 4 a 9 % a ±1σ, con la media de ocho; en frío o en ss no basta, §4.2).
Pasa a 24 bits (`G_CNT_BITS`, K_D
máximo 16,8 millones; 0,29 → 0,33 kGE; motor entero 114,73 → 114,92 kGE).
`tb_motor_top` 18/18, `verifica_top.py` 5/5 y `tb_ring_osc` re-ejecutados
con el cambio. `CFG_KD` efectivo pasa a 0-24 (`mapa_registros.md`).

## 6. El ruido 1/f [simulado]

### 6.1 Con el 1/f real, 400 ns no lo ven

Térmico + 1/f del PDK, 400 ns: σ = 183,3 fs (una realización) frente a
176,7 ± 2,0 fs sin 1/f (ocho). La diferencia, +3,8 %, es 1,2 veces la
dispersión entre realizaciones (§4.1): σ por sí solo no distingue el 1/f.
El separador (`separar_componentes`, ajuste
ponderado de E[D²] = a₁M + a₂M², validado antes con fases sintéticas:
sesgo del térmico −0,1 % con y sin 1/f, 8 semillas) da
a₂ = (−0,5 ± 1,3)·10⁻²⁸ s²: compatible con cero. Solo permite decir que
el 1/f no iguala al térmico antes de ~260 periodos.

### 6.2 Amplificar el 1/f no sirve de atajo

| 1/f | σ (fs) | a₁ (s²) | a₂ (s²) | Lectura |
|---|---|---|---|---|
| ×1 | 183,3 | 6,72·10⁻²⁶ | (−0,5 ± 1,3)·10⁻²⁸ | sin 1/f visible |
| ×1000 | 547,3 | 5,43·10⁻²⁵ | (9,8 ± 2,5)·10⁻²⁷ | a₁ ×8 |
| ×4000 | 1023,2 | 2,04·10⁻²⁴ | (5,2 ± 5,5)·10⁻²⁷ | a₁ ×30; a₂ no escala |

La idea era subir el 1/f para verlo en 400 ns y extrapolar. Falla por una
razón física: la fuente 1/f de ngspice es de banda ancha (hasta 1/NT =
2 THz), y amplificada ×1000 su densidad en torno a f₀ = 2,73 GHz,
K/f₀, es ya 7 veces el ruido térmico. El anillo convierte ese ruido de
alta frecuencia como si fuera blanco: el término lineal sube ×8 (×30 con
×4000), exactamente el cociente esperado, y tapa el término cuadrático.
a₂ no escala con la amplificación (debería ser ×4 entre las dos), así que
no es una medida. Con el 1/f real esa cola en f₀ es el 0,7 % del térmico:
el efecto es un artefacto de amplificar, no del anillo.

### 6.3 Función de sensibilidad al impulso (ISF, Hajimiri y Lee 1998)

Se inyecta una carga pequeña (1 % de q_max = C·V_DD, C = 7,27 fF
estimada de la potencia) en un nudo, en 40 fases del periodo, y se mide el
desplazamiento de fase frente a una simulación sin inyección. El ruido de
baja frecuencia se convierte en jitter a través del valor medio Γ_dc y el
blanco a través del valor eficaz Γ_rms; la esquina 1/f³ del ruido de fase
es f_1/f · (Γ_dc/Γ_rms)². Desplazamientos de 5 a 500 fs, frente a una
resolución de 0,7 fs. Lineal: con 0,5 %, 1 % y 2 % de carga, Γ en la fase
de máximo vale −0,85865, −0,85918 y −0,85959 (0,1 %).

| Nudo | Γ_dc | Γ_rms | (Γ_dc/Γ_rms)² | Lóbulo negativo medio | Lóbulo positivo medio |
|---|---|---|---|---|---|
| inversor (n3) | −0,0191 | 0,4232 | 2,0·10⁻³ | −0,162 | +0,143 |
| NAND (n1) | +0,0137 | 0,4221 | 1,1·10⁻³ | −0,157 | +0,171 |

La ISF es casi simétrica: un lóbulo negativo en la bajada del nudo (conduce
el nMOS) y uno positivo en la subida (conduce el pMOS), que casi se
anulan.

### 6.4 El 1/f de cada transistor

Un nMOS y un pMOS conectados como diodo, con la corriente del punto de
conmutación desde una fuente ideal (`ruido_por_tipo`):

| Transistor | S térmico (A²/Hz) | K 1/f (A²) | Esquina |
|---|---|---|---|
| nMOS (W 0,5 µm) | 1,448·10⁻²⁴ | 2,007·10⁻¹⁷ | 13,9 MHz |
| pMOS (W 1,2 µm) | 2,679·10⁻²⁴ | 6,149·10⁻¹⁷ | 23,0 MHz |
| suma | 4,127·10⁻²⁴ | 8,156·10⁻¹⁷ | = inversor completo |

**El pMOS tiene tres veces más 1/f que el nMOS.** Si cada transistor solo
mete ruido mientras conduce, los dos lóbulos de la ISF dejan de
compensarse.

### 6.5 Cuánto pesa el 1/f: dos extremos

Con los cuatro nudos de inversor y el de la NAND:

| Cómo actúa el ruido | Esquina 1/f³ | 1/f = térmico a | A K_D = 981 095 (359 µs), 1/f / térmico |
|---|---|---|---|
| (a) estacionario, los dos transistores todo el periodo (lo que hace el banco) | 36,5 kHz | 27 000 periodos (9,9 µs) | 36 |
| (b) cada transistor solo en su lóbulo | 5,3 MHz | 185 periodos (68 ns) | 5 300 |

El cociente es τ/τ_cruce con τ = K_D·T; sale de la ISF y no del σ
simulado (`anillo_ihp_isf_extra.log` lo da para K_D = 941 107: 35 y 5 080).

El caso real está entre los dos: el ruido de un transistor no se enciende y
apaga de golpe con su lóbulo. Lo que no depende del caso:

1. **En el punto de trabajo del generador el 1/f domina el jitter
   acumulado**, entre 36 y 5 300 veces. Si la cota de entropía se sacara de
   la varianza total acumulada a K_D, se acreditaría entropía que no hay.
2. **La medida que fija la cota tiene que hacerse con acumulaciones
   cortas**, por debajo de ~100 periodos en este anillo, donde manda el
   térmico, y separando componentes (a₁M + a₂M²). Es lo que hacen el
   estimador de Fischer–Lubicz con M pequeño y el método de Benea et al.,
   y lo que tendrá que hacer la campaña en la FPGA.
3. En el caso (b) la varianza térmica es 0,48 veces la del banco: el ruido
   estacionario la sobrestima, y K_D podría tener que doblarse
   (≈ 2,04 millones, todavía por debajo de 2²¹). El contador de 24 bits
   lo cubre. En sentido
   contrario, durante una conmutación real el transistor activo lleva más
   corriente que en el punto de conmutación (11 µA) y mete más ruido. La
   herramienta que resuelve las dos cosas a la vez es un análisis de ruido
   transitorio cicloestacionario (el `trannoise` de Spectre): un uso
   concreto del Cadence del instituto.

## 7. Qué queda

- Ruido transitorio cicloestacionario (Spectre) para cerrar el factor ~2
  del térmico y situar el 1/f entre los dos extremos.
- Esquinas ss/tt/ff y −40/27/125 °C; sf/fs, ±10 % de V_DD y tt/sf/fs a
  1,08 V, todo a −40 °C: hechas (§4.2); desapareamiento en tt a 27 °C y
  en ss a −40 °C y 1,08 V, hecho (§4.3), con histéresis pendiente en la
  detección de cruces. Quedan ff a 1,08 V y la tensión baja en caliente (se espera
  mejor, como a 1,2 V). Cada realización
  cuesta ~11 min con un hilo (~30 min con ocho en paralelo en este PC;
  ~29 min en ss a 1,08 V con ocho).
- Anillos más largos (menos σ/T por periodo, misma constante de difusión)
  y la relación jitter-potencia.
- Trazado y extracción de parásitos: el 1 fF por nudo es una estimación.
