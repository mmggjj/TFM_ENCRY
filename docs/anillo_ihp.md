# Anillo con transistores reales: PDK abierto IHP SG13G2

Fecha: 2026-10-08. Sustituye los modelos genéricos de nivel 1 del banco
SPICE por los transistores del PDK abierto de IHP (130 nm, núcleo a 1,2 V,
modelo PSP 103.6, licencia Apache 2.0) y cierra la cadena
transistor → ruido → jitter → min-entropía **sin suponer el ruido**: la
densidad que se inyecta sale del propio modelo del PDK.

Código: `analysis/anillo_ihp.py` (usa `analysis/spice_ring.py`).
Resultados: `results/anillo_ihp_*`.

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
| Ruido térmico S_th | **4,126·10⁻²⁴ A²/Hz**, plano de 100 kHz a 10 GHz |
| γ efectiva = S_th / (4kT·g) | 1,04 (canal corto: más de los 2/3 de canal largo) |
| Ruido 1/f | **S = K/f^α con K = 8,156·10⁻¹⁷ A², α = 1,000** |
| Frecuencia de esquina 1/f | **19,8 MHz** |
| V_T del nmos (extrapolación lineal) | 0,557 V |

El espectro es 1/f puro más un suelo plano hasta 10 GHz; por encima de
30 GHz sube (ruido inducido en puerta), lejos de lo que importa aquí. Un
primer cálculo del suelo como mediana entre 100 MHz y 1 GHz daba
4,385·10⁻²⁴, un 6 % de más, porque a 100 MHz el 1/f todavía suma un 20 %:
se corrigió restando el 1/f antes de tomar la mediana.

## 3. Calibración de la fuente 1/f de ngspice

`trnoise(NA NT NALPHA NAMP)` genera 1/f con amplitud NAMP, pero el manual
no da la relación con la densidad con precisión suficiente: se midió con
una fuente sola sobre 1 Ω, 1 µs a paso 0,5 ps, periodograma de Welch.

| NAMP | Semilla | S·f por bandas 10 MHz … 1 THz (A²) |
|---|---|---|
| 1 | 1 | 0,341 · 0,318 · 0,315 · 0,321 · 0,381 |
| 2 | 1 | 1,197 · 1,201 · 1,252 · 1,260 · 1,491 |
| 1 | 2 | 0,350 · 0,318 · 0,317 · 0,323 · 0,381 |

S·f es plano de 10 MHz a 100 GHz (la última banda sube por la retención de
muestras), escala con NAMP² (×3,92 frente a ×4, misma semilla) y no
depende de la semilla. **K = 0,317·NAMP², que es 1/π al 0,4 %.** Para el
PDK: NAMP = √(π·K) = 1,60·10⁻⁸ A. Un primer ajuste en escala logarítmica
sobre toda la banda daba ×5,75 en vez de ×4, porque lo dominaban los bines
altos: se cambió a media de S·f en 0,1-10 GHz.

## 4. Anillo de 5 etapas en transitorio [simulado]

Anillo: NAND de arranque + 4 inversores, W_n = 0,5 µm, W_p = 1,2 µm,
L = 0,13 µm, 1 fF por nudo como estimación del cableado (antes del trazado),
1,2 V, 27 °C, esquina típica. 400 ns por punto, paso máximo 1 ps, fuente de
ruido con NT = 0,5 ps (banda de 1 THz, muy por encima de los flancos). Se
descartan los 20 primeros cruces (arranque).

| Ruido inyectado | Cruces | Periodo (ps) | σ por periodo (fs) | σ/T | Exponente | Potencia (µW) |
|---|---|---|---|---|---|---|
| ninguno (resolución del banco) | 1071 | 366,039 | 0,696 | 1,90·10⁻⁶ | 0,47 | 143,0 |
| térmico del PDK, 4,126·10⁻²⁴ A²/Hz | 1073 | 365,972 | **180,37** | **4,93·10⁻⁴** | 1,05 | 143,0 |
| térmico ×4 | 1074 | 365,967 | 358,64 | 9,80·10⁻⁴ | 1,08 | 143,0 |
| térmico + 1/f del PDK | 1073 | 365,974 | 183,33 | 5,01·10⁻⁴ | 1,005 | 143,0 |

Lectura:

- **Resolución primero.** Sin ruido el banco mide 0,70 fs, 259 veces por
  debajo del jitter con el ruido del PDK. Su exponente (0,47) muestra que
  ese suelo es ruido numérico, no un paseo aleatorio.
- **Ley de la raíz.** Ruido ×4 → σ ×1,988 frente a ×2,000 teórico (0,6 %).
  El periodo medio no se mueve (365,97 ps en los tres puntos con ruido): el
  banco está dentro del régimen lineal, al contrario que el punto alto del
  banco genérico.
- **Exponente 1,05.** Ruido blanco: la varianza acumulada crece lineal con
  el número de periodos, como supone el modelo de Baudet.
- **Contraste con Abidi** (JSSC 2006, orden de magnitud). Con
  V_car = 4·I_trip/(γ·g_nudo) = 0,181 V, todo medido en el mismo punto,
  la fórmula da σ/T = 1,18·10⁻³; la simulación da 0,42 veces eso. Mismo
  orden. Dos tropiezos documentados: una primera versión de la fórmula
  olvidaba el factor f₀ y daba 10⁻⁸ (cuatro órdenes de menos), y la forma
  de canal largo con V_T (V_car = (V_DD/2 − V_T)/γ) no sirve aquí porque
  en el punto de conmutación los transistores están casi en el umbral
  (V_trip − V_T ≈ 0,07 V); con ella salía un cociente de 0,20.

## 5. Del jitter al divisor [simulado → estimado]

Con σ = 180,37 fs y T = 365,97 ps:

| Magnitud | Valor |
|---|---|
| Q por periodo, (σ/T)² | 2,43·10⁻⁷ |
| Constante de difusión c = σ²/T | 8,89·10⁻¹⁷ s |
| K_D para H_min ≥ 0,98 (Q ≥ 0,2286), contando solo el jitter de RO1 | 941 107 |
| Intervalo de muestreo y caudal con RO2 igual (2,73 GHz) | 344 µs → **2,9 kbit/s** |
| Si se cuenta también el jitter de RO2 (independiente e igual) | K_D = 470 553 → 5,8 kbit/s |

El caudal cae dentro del rango que se estimó sin transistores reales
(1-17 kbit/s, `modelo_ero_resultados.md`). La cifra conservadora es la
primera: el jitter de RO2 suma, pero contarlo exige que los dos anillos no
compartan ruido (alimentación, sustrato), y eso solo se puede comprobar en
silicio.

**Consecuencia de diseño aplicada:** el contador del divisor del ERO tenía
20 bits, K_D máximo 2²⁰ = 1 048 576, solo un 11 % por encima de lo
necesario en esquina típica a 27 °C. Pasa a 24 bits (`G_CNT_BITS`, K_D
máximo 16,8 millones; 0,29 → 0,33 kGE; motor entero 114,73 → 114,92 kGE).
`tb_motor_top` 18/18, `verifica_top.py` 5/5 y `tb_ring_osc` re-ejecutados
con el cambio. `CFG_KD` efectivo pasa a 0-24 (`mapa_registros.md`).

## 6. El ruido 1/f [simulado]

### 6.1 Con el 1/f real, 400 ns no lo ven

Térmico + 1/f del PDK, 400 ns: σ = 183,3 fs frente a 180,4 fs sin 1/f, y
el exponente baja a 1,005. El separador (`separar_componentes`, ajuste
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

| Cómo actúa el ruido | Esquina 1/f³ | 1/f = térmico a | A K_D = 941 107 (344 µs), 1/f / térmico |
|---|---|---|---|
| (a) estacionario, los dos transistores todo el periodo (lo que hace el banco) | 36,5 kHz | 27 000 periodos (9,9 µs) | 35 |
| (b) cada transistor solo en su lóbulo | 5,3 MHz | 185 periodos (68 ns) | 5 080 |

El caso real está entre los dos: el ruido de un transistor no se enciende y
apaga de golpe con su lóbulo. Lo que no depende del caso:

1. **En el punto de trabajo del generador el 1/f domina el jitter
   acumulado**, entre 35 y 5 000 veces. Si la cota de entropía se sacara de
   la varianza total acumulada a K_D, se acreditaría entropía que no hay.
2. **La medida que fija la cota tiene que hacerse con acumulaciones
   cortas**, por debajo de ~100 periodos en este anillo, donde manda el
   térmico, y separando componentes (a₁M + a₂M²). Es lo que hacen el
   estimador de Fischer–Lubicz con M pequeño y el método de Benea et al.,
   y lo que tendrá que hacer la campaña en la FPGA.
3. En el caso (b) la varianza térmica es 0,48 veces la del banco: el ruido
   estacionario la sobrestima, y K_D podría tener que doblarse
   (≈ 1,96 millones). El contador de 24 bits lo cubre. En sentido
   contrario, durante una conmutación real el transistor activo lleva más
   corriente que en el punto de conmutación (11 µA) y mete más ruido. La
   herramienta que resuelve las dos cosas a la vez es un análisis de ruido
   transitorio cicloestacionario (el `trannoise` de Spectre): un uso
   concreto del Cadence del instituto.

## 7. Qué queda

- Ruido transitorio cicloestacionario (Spectre) para cerrar el factor ~2
  del térmico y situar el 1/f entre los dos extremos.
- Esquinas (ss, ff) y temperatura (−40 a 125 °C): el ruido térmico sube
  con T y el K_D necesario cambia. Cada esquina cuesta ~13 min de
  simulación con un hilo.
- Anillos más largos (menos σ/T por periodo, misma constante de difusión)
  y la relación jitter-potencia.
- Trazado y extracción de parásitos: el 1 fF por nudo es una estimación.
