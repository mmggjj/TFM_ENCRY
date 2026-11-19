# La Basys 3: el motor entero en la FPGA

Placa **Digilent Basys 3** con **XC7A35T-1CPG236C** (Artix-7, 28 nm; IDCODE
`0x0362D093` leído por JTAG, Adept la ve como "Basys3", serie
210183BE6DF6). Llegó el 17-11-2026. Al contrario que la Basys 2
(`docs/basys2.md`), aquí cabe el motor entero: fuente, tests de salud,
CTR_DRBG, AES y CMAC. Lo preparado sin placa está en
`docs/puesta_en_marcha_fpga.md`; este documento recoge lo que pasó en la
placa.

Convenciones: [MEDIDO] en placa, [SIMULADO], [ESTIMADO]. Las frecuencias del
display tienen ±0,1 MHz de lectura (una cuenta en 640 µs) y ±50 ppm del
oscilador de 100 MHz; las del flujo, ±10 ms en la duración (el tick de
FreeRTOS del verificador; ver "Hallazgo del firmware") más la latencia de
arranque del flujo.

## Resumen

Sesión del 17-11-2026 por la noche, sin Mario delante salvo al principio
(lectura del display y cableado). Todo [MEDIDO] en placa salvo la
implementación (informes de Vivado). La revisión de cifras no cubre la
repetibilidad, añadida después.

| | Resultado |
|---|---|
| Herramienta | Vivado 2025.2 en Ubuntu 26.04 (no soportado) con dos ajustes de entorno |
| Implementación | motor entero: 4 011 LUT (19 %), 4 561 FF; todas las restricciones cumplen tras tres arreglos (pblocks, anillos de 11/13 etapas, APT) |
| Anillos | ro2 357,8 MHz (5 etapas, display), 293 MHz (7), **130,0 MHz (11)** (flujo) |
| **O5** | **40/40 retos AES-CMAC iguales a mbedtls**, dos claves distintas, aleatorio, zeroización |
| Jitter | Q por periodo de ro2 ~1-8·10⁻⁵ según método y variante (las dos cosas repetibles, ±0,3-4 % con autocorrelación); el modelo deja residuo (como en la Basys 2) |
| SP 800-90B | `kd 8` 0,125, `kd 10` 0,558, `kd 11` 0,786 (trozos no consecutivos), `kd 12-16` saturada; a 8,4·10⁶ bits 0,932 (ESP32 0,911, ideal 0,935) |
| Divisor | `CFG_KD` ≥ 16 (conservador); la batería sería compatible con K\* ≈ 2^11,5 |
| Sesgo / correlación | fracción de unos 0,495-0,496 en la silenciosa (z −7 a −26; la normal 0,513: el signo cambia con la implementación); sin correlación a retardo 1 (muestreo libre) |
| Salud | el RCT salta a `kd 8`; ni a `kd 6` ni a `kd 10` (batería 0,558 < 0,60) |
| Reinicios (§3.1.4) | **pasa**: 1 000 reprogramaciones, H_r 0,843 y H_c 0,892 ≥ H_I 0,819; 1 000 arranques distintos |
| Colocación fija | con los anillos en los mismos LUT6 (sin combinar): ro2 207 MHz y el frecuencímetro baja Q ×4,4 (conjunto) frente a la silenciosa: es la lógica colgada, no la colocación |
| Campaña con `ro_bel.xdc` (18-11, por defecto) | ro2 207,2 / ro1 167,2 MHz; O5 40/40; `kd 10` 0,430, `kd 11` 0,695, `kd 12-16` saturada; a 8,4·10⁶ bits 0,880; fracción de unos 0,505 (signo cambiado); salud sin alarma ni a `kd 8` (bits anticorrelados); reinicios sin repetir |
| Revisión de Fable (18-11) | raya a ~38 kHz en la fase de los anillos (repetible, origen sin ver); `CFG_KD` ≥ 16 quizá no conservador; tareas en "Tareas pendientes" |
| Revisión | dos agentes independientes: APT equivalente (exhaustivo, cosimulación, formal) y cifras recalculadas; correcciones aplicadas |

### Basys 2 frente a Basys 3

| | Basys 2 (XC3S100E, 90 nm) | Basys 3 (XC7A35T, 28 nm) |
|---|---|---|
| Qué cabe | solo la fuente | el motor entero |
| Anillos en placa | 7/9 etapas, ro2 ~144 MHz | 11/13 etapas, ro2 130 MHz |
| Q por periodo de ro2 | 1,0-4,9·10⁻⁵ (según implementación, `kd 7-9`) | ~1-8·10⁻⁵ (según método y variante, `kd 0-2`) |
| Residuo del modelo | sí | sí |
| Sesgo (fracción de unos, flujos) | 0,496-0,498 (`kd 13-16`) | 0,495-0,496 (silenciosa, `kd 12-16`) |
| Correlación ρ₁ | 0,003-0,006 con CE, ~0 sin CE | ~0 (sin CE) |
| SP 800-90B a 8,4·10⁶ | 0,890 (`kd 14`) | 0,932 (`kd 16`) |
| Divisor provisional | ≥ 16 | ≥ 16 |

## Herramientas en el Linux (17-11-2026)

- **Vivado 2025.2** (ML Standard, solo Artix-7; 49 GB en `~/Xilinx/2025.2`).
  No la 2026.x: desde la 2026.1 Vivado pide una licencia anual (nivel BASIC,
  gratuito para la serie 7) que hay que generar y renovar, y el FlexLM de este
  PC ve el host ID `000000000000` (lo que ya pasó con ISE). El instalador web
  se verificó por MD5 contra la web de AMD. En lotes, `xsetup` solo dice "not
  enough disk space" sin cifra; el instalador gráfico dio 65,83 GB con solo
  Artix-7 (Vitis HLS va obligatorio). Para hacer sitio, ISE 14.7 quedó
  comprimido en `~/eda/ise_14.7.tar.zst` (restaurar con
  `tar -I zstd -xf ~/eda/ise_14.7.tar.zst -C ~/Xilinx`).
- **Ubuntu 26.04 no está soportado** por AMD; Vivado arranca con dos ajustes,
  sin tocar el sistema:
  - `LOCPATH=~/eda/locale`: `rdiArgs.sh` impone `LC_ALL=en_US.UTF-8` y el
    sistema no lo tenía (`terminate called ... locale::facet`); se generó con
    `localedef -i en_US -f UTF-8 ~/eda/locale/en_US.UTF-8`.
  - `LD_LIBRARY_PATH=~/eda/ise_compat`: `libxv_commontasks.so` pide
    `libncurses.so.5` (los mismos enlaces que ISE).

  Orden completa:

  ```bash
  cd synth/basys3 && LOCPATH=~/eda/locale LD_LIBRARY_PATH=~/eda/ise_compat ~/Xilinx/2025.2/Vivado/bin/vivado -mode batch -source build.tcl -log build/build.log -journal build/build.jou
  ```

- **Grabación** con `openFPGALoader -b basys3 build/basys3_top.bit` (OSS CAD
  Suite) o con `djtgcfg` (Adept 2, `-d SN:210183BE6DF6 -i 0`). Volátil: la
  flash de la placa no se toca.
- Puertos serie: `/dev/ttyUSB0` es el ESP32 (CP2102) y `/dev/ttyUSB1` la UART
  de la Basys 3 (FT2232). El ESP32 pide `chmod` tras reconectarlo.

## Implementación con Vivado (17-11-2026)

Tres problemas, en este orden, y cómo se resolvieron:

1. **Los anillos no se rutaban.** `ro_pblocks.xdc` encerraba cada anillo en
   dos slices con `CONTAIN_ROUTING`: dentro no hay pistas para cerrar el lazo
   y quedaban 10 conexiones sin rutar (`Route 35-8`). Ahora el pblock solo
   fija la colocación y aparta el resto de la lógica (`EXCLUDE_PLACEMENT`).
   `build.tcl` lista tras rutar cada celda de los anillos con su sitio y el
   estado de cada red del lazo (la lección de la Basys 2: comprobar en la
   netlist implementada que el anillo existe), y se para si los relojes de
   los anillos no existen tras la síntesis: el XDC los pone en `g_inv[N-1]`
   con N fijo (11/13), y con otros `G_ETAPAS` por `GENERICOS` se habrían
   quedado sin objeto sin error (hallazgo de la revisión).
2. **El dominio de ro2 no cerraba tiempos a la frecuencia real.** Con 5/7
   etapas ro2 iba a 357,8 MHz [MEDIDO, display] y el camino crítico
   (`bit_stb` de `ero_core` → habilitación de escritura de la RAM distribuida
   de `trng_capture`) tarda 3,3-3,9 ns. Con 7/9, 293 MHz [MEDIDO, flujo]:
   tampoco. Con **11/13** (genéricos nuevos `G_ETAPAS_RO1/RO2` de
   `basys3_top`; el motor y el integrado siguen con 5/7), ro2 va a
   **130,0 MHz** [MEDIDO, flujo] y todas las restricciones se cumplen en el
   informe final de tiempos (el rutador había estimado −0,085 ns antes de su
   última pasada; manda `timing.rpt`). El
   salto de 293 a 130 MHz no sigue la recta de 5 y 7 etapas: no se
   extrapola. Una pista (revisión independiente, sin comprobar su efecto):
   en la implementación, ro2 ocupa una sola fila (SLICE_X0Y90 y X1Y90) y
   Vivado **ha combinado inversores de dos en dos en la misma LUT6** (NAND e
   inversor 5 en A6/A5, inversores 2 y 6 en B6/B5 de X1Y90, y 3 y 7 en C6/C5),
   el "LUT Combining" del placer, que `DONT_TOUCH` no impide; ro1 no.
   **Comprobado el 18-11** con `ro_bel.xdc` (una LUT6 por etapa, LOC y BEL
   fijos; `build.tcl` lo carga por defecto desde el 18-11 y `SIN_BEL=1` lo
   quita): sin combinar, ro2 con 11
   etapas va a **207,0 MHz** (variante normal) y 205,0 MHz (silenciosa)
   [MEDIDO, flujo], no a 130 MHz. Ver "Colocación fija de los anillos".
3. **El cierre de ventana del APT no cerraba a 100 MHz** (−0,26 ns en la
   esquina lenta, 13 niveles de lógica). `health_tests` compara ahora
   `c <= W − C` y `c >= ceil(W/2)` con constantes en vez de restar `W − c`:
   las mismas condiciones. Comprobado por una revisión independiente:
   34 236 958 casos exhaustivos de las dos condiciones (todo W ≤ 300 con todo
   C, W de 511 a 2048 y en el límite de 16 bits), cosimulación de la versión
   de HEAD frente a la nueva con 30 juegos de genéricos y 0 diferencias (dos
   mutantes cazados), y equivalencia formal con ABC `dsec` en genéricos
   pequeños (bancos, logs y salidas en `results/revision_apt_20261117/`);
   además, los doce bancos. Reloj de sistema +1,0 ns.

Variante normal (display y frecuencímetro; la silenciosa, con la que se
hicieron campaña, captura larga, reinicios y salud: sistema +1,111 / +0,027
ns, ro2 +0,229 / +0,086 ns, sin cargas en el reloj de ro1):

| Reloj | Restricción | WNS | WHS |
|---|---|---|---|
| sistema (100 MHz) | 10 ns | +1,014 ns | +0,043 ns |
| ro2 (11 etapas) | 4,2 ns (medido luego 7,69 ns) | +0,075 ns | +0,155 ns |
| ro1 (13 etapas) | 4,7 ns | +3,101 ns | +0,223 ns |

Utilización de la variante normal [Vivado, implementado; `build/util_hier.rpt`, local]: **4 011 LUT
(19 % del XC7A35T, 144 de ellas como RAM distribuida) y 4 561 biestables
(11 %)**, sin BRAM ni DSP. Del motor (3 880 LUT, 4 392 FF): `ctr_drbg` 1 631 /
2 225, `aes_enc_32` 647 / 266, `aes_cmac` 390 / 523, `i2c_slave` 452 / 86,
`health_tests` 419 / 86, `trng_capture` 156 / 44, `flujo_crudo` 113 / 55. (La
estimación de Yosys del 10-11, 5 125 LUT, era de otro diseño: anillos de 5/7
y semilla de 384 bits; no es comparable uno a uno.)

## Frecuencias de los anillos [MEDIDO]

| Etapas ro2 / ro1 | ro2 | ro1 | Cómo |
|---|---|---|---|
| 5 / 7 | 357,8 MHz | 291,8 MHz | display (Mario) |
| 7 / 9 | 293 MHz | — | duración de un flujo de 16 000 B a `kd 14` |
| 11 / 13 | 130,0 MHz (129,94 / 130,02 / 130,10 a `kd 13`, `14`, `15`) | sin medir (display) | flujo de 128 000 bits |
| 11 / 13, `ro_bel.xdc` | **207,2 MHz** (display; 207,0 por flujo) | **167,2 MHz** | display (Mario, 18-11), variante normal |

La medida por flujo divide `bits · 2^kd` por la duración que da el ESP32
(resolución 10 ms: ±0,12 % a `kd 13`); las tres coinciden en ±0,06 %.
Fracción de unos de esas tiras: 0,512-0,513. ro1 con 11/13 queda por leer en
el display. Los valores del display (357,8 y 291,8 MHz) los leyó Mario; no
hay fichero.

## El motor entero con el ESP32 (O5) [MEDIDO]

ESP32 a0:dd:6c:0e:fb:4c con el verificador, I2C a 400 kHz (GPIO22 → JA1,
GPIO21 → JA2, GND), pull-ups de los pines (ESP32 y FPGA). `sw0` arriba
(modo test). Secuencia: salida de consola versionada en
`results/basys3_o5_consola_20261117.txt`; el log serie íntegro,
`results/esp32_consola_basys3_motor_completo_20261117.log`, es local (los
logs de consola no se versionan).

- `id`: `id 0xa5 version 0x04 ... solo_fuente=0` (motor entero;
  `arrancado=1` ya antes de sembrar: el test de arranque había pasado con
  `kd 14` en la medida de frecuencia anterior).
- `kd 16`, `sembrar` (semilla de 512 bits validada por la ventana del APT): ok.
- `generar`: clave provisionada en modo test.
- `reto 20`: **20 aciertos de 20**: la etiqueta AES-CMAC del hardware coincide
  con la de `mbedtls_cipher_cmac` con la clave leída.
- `aleatorio 4`: cuatro bloques de 256 bits con CRC correcto.
- `cero`: sin clave ni siembra. `sembrar` y `generar` otra vez: **clave
  distinta** y otros **20 aciertos de 20**.

Es la integración FPGA + ESP32 del objetivo oficial y lo que pedía O5, con el
ESP32 de comprobador independiente. Lo que O5 prometía y el mapa de registros
no permite: cargar en placa una clave o semilla conocidas (vectores de
respuesta conocida); eso sigue cubierto en simulación (CAVP, RFC 4493).

## Jitter con el buffer de captura (`kd 0` y `kd 2`) [MEDIDO]

En la Basys 3 hay buffer de captura (`trng_capture`, 4 096 bits seguidos por
trozo), así que se puede medir a `kd 0`, lo que en la Basys 2 no se podía.
2 000 trozos por divisor (8 192 000 bits), 0 CRC malos, dos variantes del
envoltorio: la normal (display y frecuencímetro) y la silenciosa
(`G_QUIETO=true G_MEDIDOR=false`). Carpetas
`results/motor_campana/basys3_jitter_kd00_02_{normal,quieto}/`, con la salida
completa de cada estimador en `jitter_*.txt`.

Q por periodo de ro2 (ro2 a 130,0 MHz en la normal y 130,3 MHz en la
silenciosa, T = 7,69 y 7,68 ns). Cuidado con la columna de varianza a `kd 0`:
con 3-4 distancias útiles y κ negativo el estimador no es fiable allí:

| Variante | kd | fracción de unos | varianza (`jitter_estimator`) | autocorrelación global, b = 1 (`jitter_autocorrelacion`) | b libre |
|---|---|---|---|---|---|
| normal | 0 | 0,5133 | 1,69·10⁻⁵ (4 distancias, κ −1,5) | 5,0·10⁻⁵ | 1,61 |
| normal | 2 | 0,5133 | 2,41·10⁻⁵ (9 distancias, b 1,44) | 5,5·10⁻⁵ | 1,82 |
| silenciosa | 0 | 0,4956 | 3,26·10⁻⁵ (3 distancias, κ −2,3) | 8,5·10⁻⁵ | 2,08 |
| silenciosa | 2 | 0,4956 | 1,94·10⁻⁵ (10 distancias, b 1,27) | 8,3·10⁻⁵ | 2,10 |

Ajuste conjunto (un ν por trozo, separa la deriva entre trozos del jitter;
variante normal; `analysis/jitter_conjunto_m.py`, que permite elegir el
alcance M, salida en `jitter_conjunto_m.txt`): con M hasta 100, 300 y 1 000
da 0,9·10⁻⁵ a 2,8·10⁻⁵ por periodo, con residuos de 5 a 250 veces el ruido
binomial, creciendo con el rango. El de `kd 0` con M = 300 cae en el borde
inferior de la rejilla de Q (1·10⁻⁵): es una cota superior, no un valor. El
valor más bajo bien determinado es **0,93·10⁻⁵** (`kd 2`, M = 100; 0,92-0,94
en tres capturas, ver "Repetibilidad").

Lectura:

1. **Q por periodo de ro2 entre ~1·10⁻⁵ y 8·10⁻⁵ según el método**: σ/T
   de 3-9·10⁻³, σ ≈ 25-70 ps por periodo de 7,7 ns. Del mismo orden que en
   la Basys 2 (1,0-4,9·10⁻⁵ en `kd 7-9` con el ajuste conjunto según la
   implementación, `docs/basys2.md` "Residuo del jitter: halo, CE e
   implementación"; σ calculada allí con el periodo de ro1) y entre 6 y 35
   veces los 2-4 ps de jitter térmico por periodo de 3-5 ns que da la
   literatura para anillos en FPGA (`docs/modelo_ero_resultados.md` §5).
2. **El modelo del ERO no describe la forma**: la b libre de la
   autocorrelación sale de 1,6 a 2,1 (1 sería jitter térmico; la del
   estimador por varianza, 0,96-1,44, no es fiable a `kd 0`) y los residuos
   del ajuste conjunto son decenas de veces el ruido. Mismo problema abierto
   que en la Basys 2, ahora con otra FPGA (28 nm frente a 90 nm) y otra
   herramienta. No separa FPGA de montaje ni de modelo: las dos placas
   comparten ESP32, alimentación por USB del mismo PC y análisis.
3. **Las dos variantes difieren** en fracción de unos (0,5133 frente a
   0,4956; en la Basys 2, 0,519 y 0,498 con y sin frecuencímetro) y en la Q
   del ajuste global (5,0-5,5 frente a 8,3-8,5·10⁻⁵, ×1,5-1,7).
   No se puede atribuir a la carga de ro1: son implementaciones distintas
   (la silenciosa colocó ro1 de otra forma dentro de su pblock) y cambian
   display y medidor a la vez. La diferencia sí es repetible (×2,95 con el
   ajuste conjunto y ×1,5 con el global en tres capturas; ver
   "Repetibilidad").
4. **Divisor de trabajo provisional: `CFG_KD` ≥ 16.** Con la Q más baja bien
   determinada (0,93·10⁻⁵), K\* = 0,2286 / Q ≈ 2^14,6 y con un factor 2 de
   margen, 2^15,6.
   Mientras el modelo no describa los datos, el divisor no se apoya solo en
   el jitter: la campaña SP 800-90B de abajo hace de contraste.

### Repetibilidad (18-11-2026) [MEDIDO]

Tres capturas de la variante silenciosa con el mismo bitstream, seguidas
(`basys3_jitter_kd00_02_quieto`, `_r2`, `_r3`), cada una de 2 000 trozos por
divisor, 0 CRC malos, fracción de unos 0,4954-0,4956:

| Q por periodo de ro2 | r1 | r2 | r3 | dispersión |
|---|---|---|---|---|
| ajuste conjunto, `kd 2`, M ≤ 100 (`jitter_conjunto_m.txt`) | 2,754·10⁻⁵ | 2,750·10⁻⁵ | 2,764·10⁻⁵ | ±0,3 % |
| autocorrelación global, `kd 0` | 8,47·10⁻⁵ | 8,20·10⁻⁵ | 8,20·10⁻⁵ | ±2 % |
| autocorrelación global, `kd 2` | 8,35·10⁻⁵ | 8,32·10⁻⁵ | 8,16·10⁻⁵ | ±1 % |
| varianza, `kd 2` | 1,94·10⁻⁵ | 2,01·10⁻⁵ | 2,38·10⁻⁵ | ±10 % |
| varianza, `kd 0` (no fiable, κ < 0) | 3,26·10⁻⁵ | 1,76·10⁻⁵ | 1,83·10⁻⁵ | ×1,9 |

Residuo del ajuste conjunto 5,7-5,9 veces el ruido en las tres.

- **Los métodos de autocorrelación son repetibles** (±0,3-4 %; la varianza
  no: ±10-25 % a `kd 2` y ×1,9 a `kd 0`), así que la
  diferencia entre métodos (×3 entre el conjunto y el global) es
  **sistemática**: depende de qué parte de la forma de c(M) atribuye cada uno
  al jitter, porque el modelo no describe esa forma. No es ruido de medida.
- **La diferencia entre variantes también se repite.** Variante normal a
  `kd 2`, tres capturas (`basys3_jitter_kd00_02_normal`,
  `basys3_jitter_kd02_normal_r2`, `_r3`): ajuste conjunto (M ≤ 100) 9,37 /
  9,21 / 9,31·10⁻⁶ (±1 %, residuo 5,3-5,5), global 5,45 / 5,70 /
  5,91·10⁻⁵, varianza 2,41 / 2,12 / 1,48·10⁻⁵; fracción de unos 0,5133. Frente
  a la silenciosa: ×2,95 con el conjunto y ×1,5 con el global, muy por encima
  de la repetibilidad. Lo que cuelga de los anillos (o la colocación, que
  cambia entre las dos implementaciones) cambia el ruido de fase relativo,
  como en la Basys 2 (×2,5 entre variantes). Para separar las dos causas
  haría falta fijar la colocación de los anillos (LOC/BEL) y quitar solo el
  medidor.

### Colocación fija de los anillos: el frecuencímetro baja el ruido de fase (18-11-2026) [MEDIDO]

Para separar la colocación de la lógica colgada, las dos variantes se
regeneraron con **los anillos en los mismos LUT6** (`ro_bel.xdc`: NAND y
cada inversor con su LOC y su BEL `*6LUT`, sin combinar; verificado en la
lista de celdas de las dos implementaciones). Fijados solo los LUT de los
anillos: el rutado entre etapas y el biestable de muestreo no. Tiempos: ro2
−0,391 ns (normal) y −0,120 ns (silenciosa) contra la restricción de 4,2 ns,
es decir caminos de 4,59 y 4,32 ns frente a periodos medidos de 4,83 y 4,88
ns: cumplen con un 5 y un 12 % de margen en la esquina lenta. Una captura
por variante a `kd 2`, 2 000 trozos (`basys3_jitter_kd02_{normal,quieto}_bel/`,
`basys3_frec_*ro_bel/`):

| Q por periodo de ro2, `kd 2` | normal (display y frecuencímetro) | silenciosa | silenciosa / normal |
|---|---|---|---|
| ro2 [flujo] | 207,0 MHz | 205,0 MHz | |
| fracción de unos | 0,519 | 0,506 | |
| ajuste conjunto (M ≤ 100) | **3,22·10⁻⁶** (residuo 5,8) | **1,42·10⁻⁵** (residuo 5,0) | ×4,4 |
| autocorrelación global | 4,86·10⁻⁵ | 5,75·10⁻⁵ | ×1,2 |
| varianza | 1,23·10⁻⁵ | 1,98·10⁻⁵ | ×1,6 |

- **Con los anillos en el mismo sitio la diferencia sigue (y crece):** no
  viene de la colocación de los anillos, sino de lo que cuelga de ellos (el
  frecuencímetro sobre ro1 y ro2, y el display). Los tres estimadores van en
  el mismo sentido: **con el frecuencímetro el ruido de fase relativo
  aparente es menor**, lo que encaja con un acoplamiento entre anillos (o
  con el reloj de 100 MHz) a través de esa lógica, la hipótesis de la Basys
  2. El ciclo de trabajo visto también cambia (0,519 frente a 0,506) con los
  anillos fijos. Una captura por variante: la repetibilidad de cada método
  medida arriba (±0,3-4 %) es mucho menor que estas diferencias, y una
  segunda captura de cada una (`_r2`) repite el ajuste conjunto: normal
  3,16·10⁻⁶ (antes 3,22), silenciosa 1,43·10⁻⁵ (antes 1,42), ±1 %;
  fracciones de unos 0,519 y 0,505.
- La placa queda con la silenciosa con colocación fija grabada (volátil).
- **Para el divisor:** la configuración que se parece al producto es la
  silenciosa (el integrado no lleva frecuencímetro): 1,42·10⁻⁵ da
  K\* ≈ 2^14,0 y, con factor 2, 2^15,0: **`CFG_KD` ≥ 16 sigue valiendo**. Con
  el frecuencímetro puesto (3,2·10⁻⁶) haría falta `CFG_KD` ≥ 18: las campañas
  de entropía, siempre sin él.
- Las campañas de esta noche (SP 800-90B, captura larga, reinicios) se
  hicieron con la variante silenciosa **sin** `ro_bel.xdc` (ro2 a 130 MHz,
  con inversores combinados). **Desde el 18-11 `ro_bel.xdc` es el defecto**
  (decisión de Mario) y la campaña se repitió con él: ver "Campaña con la
  colocación fija". Lo del 17-11 se reproduce con `SIN_BEL=1` (salida en
  `build/<variante>_libre`).

## Campaña con la colocación fija (18-11-2026) [MEDIDO]

`ro_bel.xdc` por defecto en `build.tcl` (decisión de Mario). La variante
silenciosa reconstruida con el `build.tcl` nuevo da un `.bin` **idéntico
bit a bit** (md5 igual) al medido la noche anterior con
`XDC_EXTRA=ro_bel.xdc`: es la misma implementación. Tiempos: sistema +0,845
ns, ro2 −0,120 ns contra 4,2 ns (camino 4,32 ns frente a 4,88 ns medidos;
la restricción no se ha relajado para no cambiar la implementación).

- **Frecuencias** (variante normal con colocación fija, display, Mario):
  ro2 **207,2 MHz**, ro1 **167,2 MHz** (±0,1 MHz de lectura). ro2/ro1 =
  1,24, frente a 13/11 = 1,18 de las etapas.
- **O5**: `kd 16`, sembrar, generar, `reto 20`, `aleatorio 4`, `cero`,
  sembrar, generar, `reto 20`: **40/40 aciertos**, dos claves distintas, 4
  tramas con CRC correcto (`results/basys3_o5_consola_20261118_bel.txt`).
- **Flujos de 10⁶ bits** (`basys3_campana_90b_flujo_bel/`): `kd 12` **ya no
  cabe**: con ro2 a 205 MHz la fuente da 6,25 kB/s y la UART a 115 200
  baudios no vacía la FIFO (desborda tras 1 285 bytes,
  `basys3_flujo_bel_kd12_desborda/serie.log`, local); el flujo sirve desde `kd 13`.

| kd | ro2 (flujo) | fracción de unos | z sesgo | ρ₁ (z) | H SP 800-90B |
|---|---|---|---|---|---|
| 13 | 205,16 MHz | 0,5064 | +12,8 | −0,0005 (−0,5) | 0,815 |
| 14 | 205,18 MHz | 0,5057 | +11,5 | −0,0005 (−0,5) | 0,876 |
| 15 | 205,16 MHz | 0,5056 | +11,2 | +0,0021 (+2,1) | 0,854 |
| 16 | 205,17 MHz | 0,5054 | +10,9 | −0,0008 (−0,8) | 0,850 |

(`sesgo_correlacion.txt` en la carpeta.) Saturada como sin colocación fija
(0,819-0,879). **El sesgo cambia de signo** con la colocación (sin ella
0,495-0,496): confirma que depende de la implementación del camino de
muestreo. Sin correlación a retardo 1 (el z 2,1 de `kd 15` es uno de cuatro).
Tabla O8 con columna "Basys 3 ro_bel": H asignada 0,852 (0,815-0,876),
indistinguible de ESP32 (0,848) e ideal (0,847).

- **Captura larga** (`basys3_larga_kd16_n8378368_bel/`): 8 378 368 bits
  consecutivos a `kd 16`, 0 errores, ro2 205,16 MHz durante 45 min. SP
  800-90B no-IID **0,880** (compresión; colisión 0,948), frente a 0,932 sin
  colocación fija. Fracción de unos 0,5054 (z +31), ρ₁ = +0,0004 (z 1,1). A
  la misma N, bits ideales 0,907-0,935 (tres semillas; 0,889-0,935 en las
  doce de `docs/fuente_simulada_90b.md`) y bits iid con el sesgo de la Basys
  2 0,885-0,910: el 0,880 queda en el borde de lo que da el sesgo solo, con
  el estimador de compresión, el más ruidoso, y una sola secuencia. No se
  interpreta como pérdida de entropía; tampoco separa.

- **Trozos** (`basys3_campana_90b_trozos_bel/`, 245 trozos de 4 096 bits por
  divisor, no consecutivos; 0 CRC malos), con `kd 12` añadido porque ya no
  cabe en flujo:

| kd | fracción de unos | ρ₁ (z) | H SP 800-90B | sin colocación fija (ro2 130 MHz) |
|---|---|---|---|---|
| 8 | 0,5050 | −0,536 (−537) | 0,186 | 0,125 |
| 10 | 0,5052 | −0,241 (−241) | **0,430** | 0,558 |
| 11 | 0,5055 | −0,010 (−10) | **0,695** | 0,786 |
| 12 | 0,5059 | +0,0045 (+4,5) | 0,848 | — (flujo, 0,879) |

  Con ro2 a 205 MHz cada divisor acumula 1,57 veces menos tiempo que con
  130 MHz, así que a igual `kd` hay menos jitter: la caída de `kd 10-11` es
  lo esperado. **La correlación de fase determinista llega hasta `kd 11-12`**
  (z −10 y +4,5). Contraste con el modelo (`compara_q*.txt`): `kd 8` y `10`
  compatibles con Q = 4·10⁻⁵ por periodo de ro2; `kd 11` y `12` por encima de
  4·10⁻⁵ y por debajo de 8·10⁻⁵; con 1,42·10⁻⁵ (el ajuste conjunto de esta
  variante) todo queda por encima. Mismo patrón que sin colocación fija: la
  batería ve más "entropía" de la que da la Q más baja medida, y no separa
  la que viene de la modulación (ver la revisión de abajo). Los flujos
  `kd 13-16` quedan saturados o por encima con cualquier Q de la rejilla.

  Con la Q del ajuste conjunto (1,42·10⁻⁵), K\* ≈ 2^14,0; el `CFG_KD` ≥ 16 se
  mantiene **provisional**, pendiente del suelo térmico (tareas 3-4).

- **Tests de salud en placa** (cortes 51/766; por divisor `kd`, `borrar`,
  40 s de escucha, `id`; logs locales `results/esp32_consola_basys3_salud_bel_kd*.log`):
  **ninguna alarma a `kd 6`, `8`, `10` ni `11`**, tampoco a `kd 8` (SP
  800-90B 0,186). Sobre los trozos guardados [MEDIDO, cálculo fuera de línea]:
  racha máxima 8 / 16 / 20 / 21 bits a `kd 8` / `10` / `11` / `12` (corte 51)
  y cuenta máxima del APT 546 / 554 / 573 / 570 (corte 766). Con la
  colocación fija el régimen de poco jitter es **anticorrelado** (ρ₁ −0,54 a
  `kd 8`): bits que alternan, que ni el RCT (rachas) ni el APT (proporción)
  pueden ver. Sin colocación fija el RCT sí saltaba a `kd 8`; depende de la
  implementación. Refuerza la tarea 7 (`G_KD_MIN`).

Sin repetir con la colocación fija: reinicios (§3.1.4).

## Revisión independiente de los problemas abiertos (18-11-2026)

Otro modelo (Fable 5.2), solo lectura, recibió los seis problemas abiertos
sin las recomendaciones de esta sesión. Informe, scripts y la comprobación
de la sesión en `results/revision_fable_20261118/LEEME.md`. Lo principal:

- **Modulación periódica en la frecuencia relativa de los anillos**: raya a
  ~38 kHz (×160 sobre el suelo) y otra hacia 477 kHz en el espectro de la
  frecuencia instantánea por trozo (`kd 2`, silenciosa con colocación fija).
  **Comprobado aquí**: se repite en las dos capturas (1,130 y 1,139 frente a
  ~7·10⁻³) y no está en fase con el inicio de la captura. **Sin comprobar**:
  el origen (hipótesis: el sondeo I2C del ESP32, 400 kHz / 9 ≈ 44 kHz por
  byte) y que el estimador sea fiable (no validado con bits simulados).
  Explicaría el residuo del modelo, la b ≈ 2 y el ×3 entre métodos.
- **Consecuencia [ESTIMADO, de la revisión]**: el suelo blanco (lo térmico)
  quedaría en Q ≲ 1,1·10⁻⁶ por periodo de ro2, y con eso `kd 16` daría
  H_∞ ≈ 0,57: **`CFG_KD` ≥ 16 no sería conservador**; propone ≥ 18-19
  provisional. Todas las campañas SP 800-90B y de reinicios son a `kd` ≤ 16,
  y la batería cuenta la modulación como entropía.
- Biestable del integrado: alargar ro1 a 11-13 etapas antes que ro1/2;
  `G_KD_MIN` como medida de seguridad (23 en el integrado); restricción de
  ro2 a ~4,5 ns con comprobación en `build.tcl`; repetir reinicios con la
  colocación fija; análisis de tiempos del contador de 24 bits a 2,73 GHz en
  el integrado.

**No se ha cambiado ningún valor de diseño** (`CFG_KD`, `G_KD_MIN`,
restricción, circuito) a la espera de Mario.

## Tareas pendientes (18-11-2026)

Medidas y análisis (sin decisión previa):

1. **Origen de la raya de ~38 kHz**: captura `kd 2` con el bus callado (que
   el maestro no sondee STATUS durante la captura) o con I2C a 100 kHz; si la
   raya se mueve con el bus, es el I2C. **Hecho el 18-11 por la tarde: no es
   el sondeo I2C** (sección "Tarde del 18-11"; no descarta el ESP32 conectado ni fuentes de la
   placa); origen aún sin identificar: línea estrecha a ~39,4 kHz que una
   carga de 4 000 biestables no cambia en amplitud y mueve un 0,9 %, y
   bandas laterales a ±39,5 kHz de una portadora a ~480 kHz (regulador
   conmutado: hipótesis abierta).
2. **Validar el estimador de fase y espectro** de la revisión con bits
   simulados del modelo, con y sin una modulación conocida. **Hecho**
   (`analysis/espectro_fase.py --valida`), con límites que encontró la
   revisión: el suelo depende de ν, de su dispersión y del sesgo; falta
   `--nu`/`--sdnu` en `--calibra` (plan del 19-11).
3. **Suelo blanco (Q térmica)**: estimarlo en frecuencia con las capturas de
   `kd 0` y fijar con él el `CFG_KD` de la FPGA (provisional ≥ 18-19 según la
   revisión, frente al ≥ 16 actual). **Hecho**: Q blanca 0,6-1,1·10⁻⁶ por
   periodo de ro2 (silenciosa, colocación fija; cota baja al divisor);
   **`CFG_KD` ≥ 19** en la FPGA (H_∞ ≥ 0,99), ≥ 20 con factor 2 en Q.
4. **Repetir SP 800-90B a `kd 17-19`** y la **prueba de reinicios** con la
   colocación fija y el divisor que salga del punto 3.
5. **Reflashear el verificador** tras borrar `firmware/verificador/sdkconfig`
   (`CONFIG_FREERTOS_HZ=100` en vez de 1000). **Hecho el 18-11** (1 kHz, con
   `crudoq`).

Decisiones de Mario (opciones, costes y recomendación en
`docs/decisiones_pendientes.md`):

6. **Corrección del biestable del integrado** (H declarable 0,532 < 0,60):
   ro1 de 11-13 etapas (recomendado por la revisión) o ro1/2; validar con el
   mismo Monte Carlo y añadir ff a −40 °C y 1,32 V.
7. **`G_KD_MIN`**: 23 en el integrado (25 con ro1 largo) según la revisión;
   en la FPGA, el que salga del punto 3. Con la colocación fija los tests de
   salud no saltan ni a `kd 8` (H 0,186): el divisor mínimo es la única
   protección de ese régimen.
8. **Restricción de ro2** a ~4,5 ns en compilaciones nuevas, con
   comprobación en `build.tcl` (camino ≤ 0,9 × periodo medido); cambia la
   implementación, así que habría que repetir una captura corta.
9. **Análisis de tiempos del contador de 24 bits a 2,73 GHz** en el
   integrado (`docs/sintesis_resultados.md`), junto con el punto 6.
10. **Aislamiento de los anillos en el integrado** (buffer a la salida,
    alimentación o anillo de guarda propios, `ro_mon` sin carga).
11. **Qué va a la memoria.**
12. **Meter en la memoria los esquemáticos de Vivado y el plano del chip**
    (`results/basys3_esquema/`, `results/basys3_plano/`), EN y ES, cuando se
    cierre la evidencia (petición de Mario, 18-11).
13. **Redacción**: en `docs/` se escribe `kd N` por `CFG_KD = N`
    (`K_D = 2^N`); en la memoria, definirlo una vez y no usar `kd` a secas
    (Mario preguntó qué era, 18-11).

## 19-11-2026: decisiones de Mario aplicadas y probadas en placa

Decisiones y su porqué en `docs/decisiones_pendientes.md` ("Decidido el
19-11-2026"): ro1 y ro2 de 11 etapas y preescalador ÷16 de ro2 en el
integrado; `G_KD_MIN` 25 (integrado) y 19 (FPGA); `CFG_KD` = 19 en la FPGA;
restricción de ro2 a 4,5 ns con comprobación en `build.tcl`.

- **RTL** (`motor_top`): `G_ETAPAS_RO1` 11, `G_ETAPAS_RO2` 11, `G_PRESC_RO2`
  4 (genérico nuevo: el dominio del anillo corre a ro2/16; `CFG_KD` sigue
  contando periodos de ro2), `G_KD_MIN` 25, `G_KD_RESET` 25, `G_KD_MAX` 26
  (genérico nuevo, ancho del contador del ERO; un `CFG_KD` mayor se ignora y
  levanta `DIAG.rechazada`). `basys3_top`: `G_KD_MIN` 19, `G_KD_RESET` 19,
  `G_KD_MAX` 24, sin preescalador; `basys2_top` igual que antes.
- **Bancos**: once de doce en verde en `results/run_tb_todos.log`
  (`tb_motor_top` 0 fallos con las comprobaciones nuevas y el preescalador,
  PSL 14/14 y 8/8; los bancos del motor fijan ro2 en 5 etapas para no
  duplicar el tiempo de simulación); `tb_basys3_top` aparte
  (`results/run_tb_basys3_top_1911.log`). Banco en PC 0 fallos, con la
  comprobación nueva de `CFG_KD` > máximo; verificador con ESP-IDF 5.3.2 sin
  avisos (rango de `kd` 0-26) y grabado en el ESP32.
- **FPGA** (variante silenciosa, restricción de 4,5 ns): la comprobación nueva
  de `build.tcl` paró la primera compilación (camino de ro2 4,407 ns > 0,9 ×
  4,88 = 4,392 ns, con el contador de 26 bits); con 24 bits, camino 3,98 ns,
  **todas las restricciones cumplen (WNS +0,524 ns)**. El bitstream del 18-11
  queda en `build/G_QUIETO_true_G_MEDIDOR_false_1811/`.
- **En placa [MEDIDO]**: tras reprogramar `CFG_KD` vale 19; `kd 18` →
  `sembrar` **rechazada**; `kd 19` → siembra; `kd 25` (> 24) **ignorado** con
  `DIAG.rechazada`; **O5: 40/40 retos CMAC** con dos claves (`cero` entre
  medias). Captura de jitter a `kd 2` (`basys3_jitter_kd02_quieto_1911/`):
  unos 0,4966 (el sesgo vuelve a cambiar de signo con la implementación),
  raya 1,22 a 37,7 kHz, Q blanca por banda 0,95-1,35·10⁻⁶ (calibrada con su
  ν 0,398, su dispersión y su sesgo): por encima de la cota de 0,6·10⁻⁶,
  `kd 19` sigue siendo conservador.
- **Integrado**: área 95,52 kGE frente a 95,09 kGE de la configuración
  anterior (`results/sintesis_19_11.log`). SPICE en marcha al escribir esto:
  jitter del anillo de 11 etapas en ss −40 °C 1,08 V (divisor del integrado)
  y Monte Carlo del biestable con ro1 de 11 etapas (primero las esquinas
  críticas; criterio del 16-11 sin cambios).

## Plan para el 19-11-2026

Lo de la tarde del 18-11 (abajo) está hecho y subido; una revisión
independiente de ese trabajo estaba en marcha al escribir esto (sus
correcciones, aplicadas o pendientes, en "Revisión de la tarde del 18-11").
Orden propuesto:

1. **Revisión de la tarde**: aplicadas las correcciones de texto (sección
   "Revisión de la tarde del 18-11"); falta en código: `--nu`, `--sdnu` y el
   sesgo en `espectro_fase.py --calibra`, y recalibrar con ellos.
2. **Decisiones de Mario** con `docs/decisiones_pendientes.md` delante:
   biestable del integrado (ro1 de 11-13 etapas o ro1/2), `G_KD_MIN` (23/25
   en `motor_top`, 19 en `basys3_top`), restricción de ro2 a ~4,5 ns.
3. **Tiempos del dominio de ro2 en el integrado** (tarea 9): no hay
   herramienta de STA instalada (ni OpenSTA ni OpenROAD en `~/eda`); opciones:
   instalar OpenSTA, o el `sta` de Yosys con la biblioteca sg13g2 sobre el
   `ero_core` sintetizado. Si el contador de 24 bits no cierra a 2,73 GHz:
   ÷2 en ro2 y recalcular K_D.
4. **Aplicar las decisiones al RTL** (si ro1 se alarga, el divisor pasa a
   `kd 25`: ensanchar `G_CNT_BITS` de `ero_core`, subir `G_KD_RESET`, abrir
   el rango de `cmd_kd` y revisar los plazos del firmware; con `G_KD_MIN` alto,
   una variante de caracterización para el flujo): genéricos por defecto, doce bancos
   (`python rtl/run_tb.py`), `verifica_top`, `synth/equivalencia.sh` donde
   aplique, síntesis (`synth/sintetiza.py`), CI en verde.
5. **Validar la corrección del biestable** si ro1 cambia: `analysis/biestable_mc.py`
   con el anillo nuevo, mismo criterio (μ − 3σ, mínimo sobre esquinas) más la
   esquina ff a −40 °C y 1,32 V; `analysis/anillo_ihp.py` en la peor esquina
   para el K_D nuevo. Horas de simulación desatendida.
6. **FPGA**: restricción de ro2 y comprobación en `build.tcl`, recompilar,
   captura corta de jitter (`espectro_fase.py`) y O5.
7. **Fusionar** `feat/lecturas-firmadas` en `main` (PR), con la CI en verde.
8. **Memoria** (tareas 11-13), con la evidencia cerrada: resultados de la
   Basys 3, esquemáticos y plano, `CFG_KD` definido.

Opcional: origen de la raya de ~39,4 kHz (osciloscopio en las
alimentaciones de la placa); medidor (ESP32-C3) con el motor real.

## Tarde del 18-11: la raya de ~38 kHz y el suelo térmico

Tareas 1-3 de la lista de arriba. Firmware y método nuevos:

- **Verificador** con `CONFIG_FREERTOS_HZ=1000` (`sdkconfig` regenerado desde
  `sdkconfig.defaults`; arregla la tarea 5) y orden **`crudoq N`**: como
  `crudo`, pero tras escribir `CONTROL ← capturar` espera sin tocar el bus
  (10 ns por periodo de ro2 más 200 µs) antes de leer DIAG y STATUS.
  `campana_motor.py --callado` la usa. Banco en PC 0 fallos (paso 13 con
  `crudoq`), ESP-IDF 5.3.2 sin avisos, grabado en el ESP32 a0:dd:6c:0e:fb:4c
  (con permiso de Mario).
- **Por qué el bus podía estar en la captura**: con `crudo`, tras la orden el
  maestro lee DIAG y STATUS enseguida (unos 100 µs por transacción a 400 kHz),
  y una captura a `kd 2` dura 4 096 · 4 · 4,88 ns ≈ 80 µs: cae entera dentro
  del sondeo. Un byte I2C son 9 ciclos de SCL, 22,5 µs (44 kHz).
- **`analysis/espectro_fase.py`**: el método de la revisión
  (`results/revision_fable_20261118/psd.py`) como script del repositorio:
  demodula cada trozo a su ν, fase por bloques de 16 muestras, espectro de la
  frecuencia instantánea promediado sobre los trozos; da el pico (25-60 kHz)
  y el suelo (mediana de 100-400 kHz).

### Validación del método con bits simulados (tarea 2) [SIMULADO]

`espectro_fase.py --valida` (`results/espectro_fase_valida.txt`): trozos de
`ero_model` con Q conocida, con y sin modulación senoidal de ν a 38 kHz:

- **Sin modulación no hay raya** (pico/suelo 0,8-1,0) y el suelo crece
  linealmente con Q: 7,6·10⁻³ con Q = 1·10⁻⁶ por periodo de ro2, 8,7·10⁻² con
  1,42·10⁻⁵ (con ν = 0,384 fija y bits sin sesgo). **Corregido por la
  revisión de la tarde (abajo)**: el 1·10⁻⁴ con Q = 0 solo vale con ν fija;
  con la dispersión de ν entre trozos de los datos el suelo del estimador
  sube a 2·10⁻³ (ν 0,384) y hasta 1,7·10⁻² (ν 0,417), y el sesgo, los
  armónicos de la raya y el ruido de fase también lo suben. El suelo mide el
  jitter blanco **más** componentes del estimador y de la fuente: la Q sale
  por arriba (el lado no conservador) y depende de ν.
- **Con modulación la raya sale a 37,7 kHz**; amplitud 1·10⁻³ ciclos por
  muestra da un pico de 1,03-1,14. La raya también sube algo el suelo
  (3,8·10⁻³ con Q = 0): hay que calibrar con ella.

### Suelo blanco medido (tarea 3) [MEDIDO, calibración SIMULADA]

`espectro_fase.py --calibra` (`results/espectro_fase_calibra*.txt`): rejilla de
Q y amplitud que reproduce pico y suelo de cada captura (1 000 trozos por
punto). **Ojo**: `--calibra` usa ν = 0,38388 fija y bits sin sesgo; solo vale
para las capturas con esa ν (la silenciosa con colocación fija). Columna de
la derecha: la recalculada por la revisión con la ν, la dispersión de ν, el
sesgo y las rayas de cada captura, y el rango por banda de 100 a 400 kHz.

| Captura (2 000 trozos, `kd 2`) | ro2 | ν | raya (frecuencia, pico) | suelo | Q (`--calibra`) | Q revisada [ESTIMADO] |
|---|---|---|---|---|---|---|
| silenciosa, colocación fija (dos) | 205 MHz | 0,384 | 37,7 kHz, 1,13-1,14 | 7,5-7,6·10⁻³ | ≈ 0,8·10⁻⁶ | **0,80-0,88·10⁻⁶; por banda 0,63-1,14·10⁻⁶** |
| normal, colocación fija (dos) | 207 MHz | 0,227 | 38,1 kHz, 0,071-0,074 | 9,1·10⁻³ | (≈ 1,2·10⁻⁶, no válida: ν distinta) | 0,3-1,3·10⁻⁶: no determinable |
| silenciosa, libre (dos) | 130 MHz | 0,359-0,361 | 39,9 kHz, 2,55 | 1,30-1,52·10⁻² | ≈ 1,2-1,6·10⁻⁶ | 0,74-1,47·10⁻⁶ |
| normal, libre | 130 MHz | — | 39,9 kHz, 0,57 | 1,60·10⁻² | ≈ 1,6·10⁻⁶ | 1,06-1,9·10⁻⁶ |

Lectura:

1. **El jitter blanco es del orden de 1·10⁻⁶ por periodo de ro2** en las
   capturas donde se puede determinar; la mejor determinada, la silenciosa
   con colocación fija, **0,6-1,1·10⁻⁶** (banda y modelo de calibración),
   σ ≈ 4-5 ps por periodo de 4,9 ns, del orden de los 2-4 ps por 3-5 ns de la
   bibliografía (`docs/modelo_ero_resultados.md` §5). Retirado (revisión):
   "escala con el periodo como el térmico" (Q en ciclos de ro1 va como
   κ²·T2/T1², ro1 de la variante a 130 MHz está sin medir y el anillo era
   otro).
2. **La raya cambia entre variantes**: con el frecuencímetro es 15 veces
   menor **en potencia** (1,13 frente a 0,074), unas 4 veces en amplitud
   (1,06·10⁻³ frente a 2,7·10⁻⁴ ciclos por muestra). Que el suelo **no**
   cambie y que el "×4,4" del ajuste conjunto sea solo la raya **no está
   establecido** (la Q de la normal no se puede determinar con su ν).
3. **La raya está a ~38-40 kHz con ro2 a 130 y a 205 MHz**: frecuencia fija
   en tiempo, no ligada al anillo. Fuente externa (¿I2C?): tarea 1, abajo.
4. **Divisor**: con Q = 0,82·10⁻⁶ (`results/cfg_kd_suelo_blanco.txt`,
   `ero_model.entropias_exactas`, peor fase) H_∞ = 0,47 a `kd 16`, 0,80 a
   `kd 17`, 0,974 a `kd 18`, 0,9996 a `kd 19`. Como el suelo arrastra
   componentes no térmicas, se lleva al divisor la **cota baja, 0,6·10⁻⁶**:
   `kd 19` da 0,996 (H ≥ 0,99 mientras Q ≥ 5,0·10⁻⁷; ≥ 0,60 mientras Q ≥
   1,3·10⁻⁷). Con la mitad de Q, `kd 19` da 0,974 y hace falta `kd 20` para
   0,99. **`CFG_KD` ≥ 16 no es conservador en la FPGA**; **≥ 19 con objetivo
   H_∞ ≥ 0,99 sobre la cota baja medida, ≥ 20 si se quiere además un
   factor 2 en Q** (decisión de Mario). Las campañas SP
   800-90B a `kd` ≤ 16 midieron bits con H_∞ del modelo ≤ 0,47 que la
   batería puntuó 0,82-0,88: la batería no ve la falta de entropía cuando la
   fase es determinista y está modulada.

### Revisión de la tarde del 18-11

Un agente revisor (otra sesión, sin las conclusiones de esta) recalculó todo
desde el código y los datos (scripts en el directorio temporal de la sesión,
no versionados). Correcciones aplicadas arriba, por orden de importancia:

1. El suelo no es solo jitter blanco: con la dispersión de ν entre trozos,
   el sesgo, los armónicos de la raya o ruido de fase el estimador lo sube,
   y depende de ν de forma no monótona (×6 entre ν 0,41728 y 0,41982 en
   simulación). La Q sale por arriba.
2. La Q de la variante normal (ν 0,227) no se puede determinar; `--calibra`
   fija ν = 0,38388. Retirado "lo que cambia es la raya, no el suelo" y "el
   ×4,4 era la modulación".
3. Q de la silenciosa con colocación fija: 0,80-0,88·10⁻⁶ con tres modelos
   de calibración, 0,63-1,14·10⁻⁶ por banda; al divisor la cota baja, 0,6·10⁻⁶.
4. Retirado "escala con el periodo como el térmico".
5. `G_KD_MIN` también bloquea el flujo; `kd 25` no cabe en el RTL actual
   (`docs/decisiones_pendientes.md` §7).
6. La raya: ×15 en potencia, ×4 en amplitud.
7. Regulador: hipótesis abierta; portadora a ~480 kHz con bandas laterales a
   ±39,5 kHz.
8. `docs/decisiones_pendientes.md` §6: H de 11-13 etapas y de ro1/2
   coherentes con la misma ley 1/T; divisor ×6,8 con 13 etapas.
9. Bus: dicho lo que el experimento no descarta.

Coincide con: el divisor calculado (`entropias_exactas`), el diseño y el
resultado del experimento del bus, la frecuencia y la amplitud de la raya en
la prueba de carga, y que no hay fase fija respecto al inicio de la captura.

### ¿Es el sondeo I2C? No (tarea 1) [MEDIDO]

Variante silenciosa con colocación fija, mismo bitstream, firmware nuevo;
2 000 trozos a `kd 0` y a `kd 2` por captura, alternando bus activo (`crudo`)
y bus callado (`crudoq`, comprobado en `serie.log`: 500 órdenes de una y 0 de
la otra), dos vueltas. Carpetas `basys3_bus_{activo,callado}_kd00_02_r{1,2}/`,
0 CRC malos.

| `kd 2` | activo r1 | callado r1 | activo r2 | callado r2 |
|---|---|---|---|---|
| pico (37,7 kHz) | 1,130 | 1,130 | 1,135 | 1,128 |
| suelo | 7,80·10⁻³ | 7,40·10⁻³ | 7,67·10⁻³ | 7,69·10⁻³ |
| fracción de unos | 0,5054 | 0,5052 | 0,5055 | 0,5054 |

A `kd 0` (bloques de 64 muestras, la misma duración; el trozo dura 20 µs,
menos que un periodo de la raya, así que el pico cae en el primer bin, 50,8
kHz): 0,0388-0,0394 en las cuatro. **Callar el bus durante la captura no
cambia la raya**: no la mete el tráfico I2C durante la captura. Tampoco el
tick de FreeRTOS: con el firmware nuevo (1 kHz) el pico es el de anoche
(1,13 con 100 Hz). **No descarta** (revisión): el ESP32 conectado y en
marcha (masa común, pull-ups a su 3,3 V, la UART vaciando la trama
anterior), la actividad del bus antes de la captura (igual en los dos
modos) ni las fuentes de la propia placa; para eso hay que desconectar o
aislar el ESP32, o un osciloscopio.

Origen sin identificar. Lo que se sabe: frecuencia fija en tiempo (~38-40 kHz
con ro2 a 130 y a 205 MHz), sin fase fija respecto al inicio de la captura,
y 15 veces menor con el frecuencímetro y el display (más consumo).
Hipótesis compatible, sin comprobar: un regulador conmutado de la placa en
modo ráfaga, cuya frecuencia y amplitud dependen de la carga. Según el
manual de referencia de Digilent (Basys 3 rev. C), el núcleo del FPGA (1,0 V,
VCCINT) sale de un LTC3633 y los 1,8 V auxiliares de un LTC3621, dos
reductores síncronos que admiten modo ráfaga a carga ligera; qué modo usa la
placa lo fija un pin del esquemático, no comprobado. Comprobación posible:
osciloscopio en la salida de 1,0 V, o alimentar la placa con otra carga en el
FPGA y ver si la raya se mueve.

**Prueba de carga (18-11, noche) [MEDIDO]**: genérico nuevo `G_CARGA` de
`basys3_top` (0 por defecto; `tb_basys3_top` 4/4 con él): 4 000 biestables
lejos de los anillos que conmutan a 100 MHz con sw1 arriba. Variante
silenciosa con colocación fija y `G_CARGA=4000` (Vivado: 7 885 LUT, 8 394 FF,
tiempos cumplidos, anillos en las mismas LUT6). Mario movió sw1 entre
capturas; `basys3_carga_sw1{abajo,arriba}_*/`, 0 CRC malos.

| | ro2 (flujo, `kd 14`) | raya a `kd 4` (bins de 3,14 kHz): frecuencia corregida, potencia | `kd 2`: pico / suelo |
|---|---|---|---|
| sin carga | 205,83 MHz | 39,41 kHz, 31,4 | 1,315 y 1,310 / 1,45-1,50·10⁻² |
| con carga (dos capturas) | 205,02 MHz (−0,39 %) | 39,76-39,77 kHz, 31,8 | 1,289 y 1,288 / 0,89-0,98·10⁻² |

(`basys3_carga_frecuencia_raya.txt`: frecuencia por interpolación entre los
dos bins de la ventana de Hann, corregida con el periodo de ro2 medido.)

- **La raya es una línea estrecha a ~39,4 kHz** (dos bins de 3,14 kHz).
- **La carga no cambia su amplitud** (31,4 frente a 31,8) y mueve su
  frecuencia un 0,9 % (+0,35 kHz, repetible entre las dos capturas con carga
  a 0,01 kHz). **Corregido (revisión)**: "encaja mal" no estaba cuantificado
  (no se estimó la corriente que añade la carga ni la de base), la carga solo
  afecta al regulador de VCCINT y no a los de 1,8 o 3,3 V, y la revisión
  encontró una **portadora a ~480 kHz con bandas laterales a ±39,5 kHz**
  (440 y 519 kHz) en todos los bitstreams (130 y 205 MHz), que no se mueve
  con la carga (480,0 → 479,7 kHz): firma compatible con un convertidor
  conmutado. **La hipótesis del regulador sigue abierta**; origen sin
  identificar.
- La carga baja ro2 un 0,39 % (caída de tensión del núcleo).
- Con la carga instalada pero parada, el suelo a `kd 2` es 1,45-1,50·10⁻² y
  crece con la frecuencia (de 1,1·10⁻² a 3·10⁻² entre 100 y 400 kHz), el
  doble que sin la carga en el bitstream; con la carga en marcha baja a
  0,9-1,0·10⁻². No se ha investigado: no cambia el `CFG_KD` de arriba, que
  sale del bitstream sin carga.
- La placa queda otra vez con la variante silenciosa sin carga. Para el
divisor no cambia nada (el `CFG_KD` de arriba solo cuenta el suelo blanco);
para el integrado es otra razón para aislar la alimentación de los anillos
(tarea 10).

### SP 800-90B y reinicios al divisor nuevo (tarea 4) [MEDIDO]

Flujos de 10⁶ bits consecutivos a `kd 17`, `18` y `19`, variante silenciosa
con colocación fija, firmware nuevo, 0 errores, ro2 205,08-205,11 MHz
(`basys3_campana_90b_flujo_kd17_19/`, 75 min):

| kd | H_∞ del modelo con Q 0,82·10⁻⁶ | fracción de unos | ρ₁ (z) | H SP 800-90B |
|---|---|---|---|---|
| 17 | 0,80 | 0,5058 | 0,0000 (0,0) | 0,864 |
| 18 | 0,974 | 0,5060 | +0,0007 (0,7) | 0,833 |
| 19 | 0,9996 | 0,5055 | +0,0008 (0,8) | 0,857 |

La batería da lo mismo que a `kd 13-16` (0,815-0,876): **no distingue un
divisor con H_∞ 0,47 de uno con 0,9996**. Confirma lo que ya se sabía de la
fuente simulada (`docs/fuente_simulada_90b.md`): a 10⁶ bits la batería se
satura y no sirve para fijar el divisor; lo fija el jitter térmico medido.
El sesgo (0,5055-0,5060) es el mismo a todos los divisores: viene del camino
de muestreo, no del jitter.

**Reinicios a `kd 19`** (`results/fpga_reinicios/basys3_kd19_bel/`): 1 000
reprogramaciones por JTAG, 0 descartadas, ~4 s por ciclo, 128 bytes del
flujo por arranque. `ea_restart` en bit con H_I = 0,857 (la de `kd 19`):
**Restart Sanity Check Passed** y **Validation Test Passed** (H_r 0,854,
H_c 0,830). Los 1 000 arranques son distintos; Hamming media 511,9 (esperada
512), desviación 16,02 (16,00), mínima 439 (~438). Igual que a `kd 16` sin
colocación fija.

### Imágenes de la implementación (18-11)

- **Esquemático de bloques de Vivado** (`synth/basys3/esquema.tcl`, diseño
  elaborado de la variante silenciosa, `vivado -mode gui` porque
  `write_schematic` no escribe nada en batch): `results/basys3_esquema/`,
  `esquema_motor_top.{pdf,png}` (los bloques del motor y sus conexiones) y
  `esquema_basys3_top.{pdf,png}` (el envoltorio de la placa). Elaboración con
  0 avisos críticos y 0 errores (19 avisos: constantes del display y del LED
  de la variante silenciosa y bits de dirección sin usar).
- **Plano del chip** (`synth/basys3/plano.tcl` vuelca sitio de cada celda del
  checkpoint rutado; `analysis/plano_basys3.py` lo dibuja):
  `results/basys3_plano/plano_basys3.{png,pdf}`. Todo el motor arriba a la
  izquierda del XC7A35T; ro2 justo debajo y ro1 más abajo, en sus pblocks.
- No hay foto del montaje (Basys 3 + ESP32): la tiene que hacer Mario.

## Campaña SP 800-90B [MEDIDO]

Variante silenciosa (`G_QUIETO=true G_MEDIDOR=false`, muestreo sin
habilitación, cortes 51/766), 10⁶ bits por divisor, batería no-IID en bits
(`campana_motor.py --90b`). `kd 8`, `10` y `11` por trozos: 245 trozos de
4 096 bits concatenados (1 003 520 bits), **no consecutivos** como pide SP
800-90B, porque el flujo no da abasto por debajo de `kd 12` a 115 200
baudios; `kd 12` a `16` en flujo consecutivo. 0 CRC malos; ro2 130,28-130,34 MHz durante los flujos.
Carpetas `results/motor_campana/basys3_campana_90b_{trozos,flujo}/`.

| kd | modo | fracción de unos | H SP 800-90B (mínimo) |
|---|---|---|---|
| 8 | trozos | 0,4945 | **0,125** |
| 10 | trozos | 0,4959 | **0,558** |
| 11 | trozos | 0,4965 | **0,786** |
| 12 | flujo | 0,4951 | 0,879 |
| 13 | flujo | 0,4955 | 0,847 |
| 14 | flujo | 0,4954 | 0,829 |
| 15 | flujo | 0,4954 | 0,877 |
| 16 | flujo | 0,4963 | 0,819 |

Contraste con el modelo (`compara_modelo_campana.py --u-q 0.10`; salida
completa en `compara_q*.txt` de cada carpeta): la banda esperada es la de la
batería con bits del modelo de esa Q (`docs/fuente_simulada_90b.md`).

| Q por periodo de ro2 | kd 8 | kd 10 | kd 11 | kd 12 | kd 13 | kd 14 |
|---|---|---|---|---|---|---|
| 1·10⁻⁵ | compatible | por encima | por encima | por encima | por encima | compatible |
| 2·10⁻⁵ | compatible | por encima | por encima | por encima | compatible | saturada |
| 4·10⁻⁵ | compatible | por encima | por encima | por encima | saturada | saturada |
| **8·10⁻⁵** | por debajo | **compatible** | **compatible** | saturada | saturada | saturada |

- La batería ve **más entropía de la que el modelo da con la Q más baja**
  medida y es compatible con Q del orden de 6-10·10⁻⁵ (la rejilla va a
  pasos de ×2 y solo `kd 10` y `11` discriminan), del orden del ajuste
  global por autocorrelación de esta misma variante (8,3-8,5·10⁻⁵). Con
  8·10⁻⁵, K\* ≈ 2^11,5.
- Ojo con `kd 10`: sus trozos tienen ρ₁ = +0,053 (z ≈ 53) y `kd 8` ρ₁ =
  +0,71 [revisión independiente]: a divisores bajos manda la fase
  determinista (como en la Basys 2). El "compatible" de `kd 10` es de la
  cifra asignada, no de que los bits se parezcan a los del modelo. `kd 8`
  queda por debajo con 8·10⁻⁵ y es donde salta el RCT en placa (abajo).
- **Divisor: se mantiene `CFG_KD` ≥ 16** (la Q más baja, factor 2). La
  batería no distingue ruido determinista o común de entropía, y el modelo
  aún no describe la forma de c(M): la cifra optimista (K\* ≈ 2^11,5) no se
  declara.

## Sesgo y correlación (`sesgo_correlacion.py`) [MEDIDO]

Flujos de 10⁶ bits, `kd 12` a `16`: **ρ₁ entre −0,0011 y +0,0014 (|z| ≤ 1,4)**,
sin correlación a retardo 1: con el muestreo sin habilitación (por defecto en
`motor_top` desde el 15-11) la correlación de la Basys 2 con CE no aparece,
ahora en otra familia (Artix-7). **El sesgo sí**: fracción de unos
0,4951-0,4963, z de −7 a −10, del mismo orden que en la Basys 2
(0,496-0,498). En la Basys 3 no hay variante con CE, y el signo del sesgo
cambia con la implementación (normal 0,5133, z +76; silenciosa 0,4956,
z −25, en los 8,2·10⁶ bits de jitter): que venga del camino de muestreo de
ro1 y no del CE es la hipótesis de la Basys 2, no un resultado de esta placa.

## Tabla O8 (`tabla_o8.py`)

La Basys 3 entra en `results/tabla_o8.md` como columna propia. A 10⁶ bits la
H asignada no separa nada: Basys 3 0,838 (0,819-0,877), Basys 2 0,845, ESP32
0,848, bits ideales 0,847. Los estimadores sueltos sí separan las dos FPGA del
ESP32 por el sesgo (MCV 0,983 frente a 0,995; MultiMMC 0,984 y LZ78Y 0,983
frente a 0,996); Markov 0,988 frente a 0,998, aquí sin correlación: bits iid
con P(0) = 0,5046 darían ~0,987 [ESTIMADO, revisión independiente; no sale
de ninguna tabla]. Entran `kd 13-16`, los mismos divisores que la Basys 2
(la columna "FPGA" de la tabla es la Basys 2); con el K\* conservador de
arriba, `kd 13` y `14` quedan por debajo, así que la columna mezcla
divisores dentro y fuera del margen.

### A 8 378 368 bits (captura larga) [MEDIDO]

Misma longitud que la captura larga del ESP32 sin radio (`esp_rf_off_2`):
8 378 368 bits consecutivos a `kd 16`, variante silenciosa, 0 errores, ro2
130,28 MHz durante 70 min (`results/motor_campana/basys3_larga_kd16_n8378368/`).
SP 800-90B no-IID **0,932** (colisión). A la misma N: Basys 2 0,890 (`kd 14`),
ESP32 0,911, bits ideales 0,935 (0,907-0,935). **La cifra asignada sigue sin
separar las fuentes**; los estimadores sensibles al sesgo sí (MCV, MultiMMC y
LZ78Y 0,986 frente a 0,998-0,999 del ESP32 e ideal). Fracción de unos 0,4955
(z −26), ρ₁ = −0,0004 (z −1,1): sin correlación también a esta longitud.

## Prueba de reinicios, SP 800-90B §3.1.4 [MEDIDO]

`analysis/reinicios_fpga.py` con `djtgcfg` (que también ve la Basys 3): 1 000
ciclos de reprogramar la FPGA por JTAG (1,1 s; volátil, la flash no se toca)
y leer por el ESP32 los primeros 128 bytes del flujo a `kd 16`, variante
silenciosa; 0 ciclos descartados, 3,6 s por ciclo
(`results/fpga_reinicios/basys3_kd16/`: `bloques.npy`, `resumen.md`,
`ea_restart_b1.log`). Mismo matiz que en la Basys 2: son los primeros bits
del flujo, unos cientos de ms tras configurar, no los de los primeros
nanosegundos.

- `ea_restart` en bit (1000 × 1000), H_I = 0,819 (la de `kd 16` a 10⁶):
  **Restart Sanity Check Passed** y **Validation Test Passed** (H_r 0,843,
  H_c 0,892).
- Comprobación directa: 1 000 arranques distintos de 1 000 (también en los 8
  primeros bytes); Hamming media 511,9 (esperada 512), desviación 15,98
  (16,00), mínima 430 (esperada ~438); ningún arranque es el flujo de otro
  desplazado; primer byte uniforme (p = 0,94).
- Igual que la Basys 2 y al contrario que el ESP32 sin el ruido del cargador
  de arranque, que repetía secuencia (`docs/esp32_reinicios.md`).

## Tests de salud en placa [MEDIDO]

Cortes 51/766 (H 0,60, α = 2⁻³⁰), variante silenciosa: por divisor, `kd`,
`borrar`, unos 40 s de escucha y una lectura de `id`
(`results/esp32_consola_basys3_salud_kd*.log`, locales, sin marcas de tiempo):

| kd | 6 | 8 | 10 |
|---|---|---|---|
| Alarma | — | **RCT** | — |

El RCT salta a `kd 8`, donde la batería da 0,125; a `kd 6` no salta en ese
rato y a `kd 10` tampoco, **aunque allí la batería da 0,558, por debajo de la
H declarada de 0,60**. Como en la Basys 2 (`salud_offline.py`), los tests de
salud no cubren de forma fiable el régimen de poco jitter: lo protege el
divisor mínimo (`G_KD_MIN`, 6 por defecto, sin decidir).

## Hallazgo del firmware: el verificador corre a 100 Hz

La revisión independiente vio que todas las duraciones de los logs son
múltiplos de 10 ms: el `sdkconfig` local de `firmware/verificador` (29-10,
sin versionar) tiene `CONFIG_FREERTOS_HZ=100`, y el `=1000` de
`sdkconfig.defaults` (arreglo del 27-10 de los plazos en tiempo real) no se
aplicó porque `sdkconfig` no se regeneró. `motor_i2c.c` lo tolera (fuerza un
paso mínimo de un tick) y no ha afectado a ninguna medida salvo la
resolución de las duraciones (10 ms). Arreglo: borrar `sdkconfig` y
recompilar el verificador (y el medidor) para que tomen los valores por
defecto; queda para Mario (reflashear el ESP32).

**Arreglado el 18-11 por la tarde**: `sdkconfig` del verificador regenerado
(`CONFIG_FREERTOS_HZ=1000`), compilado con ESP-IDF 5.3.2 sin avisos y grabado
en el ESP32 a0:dd:6c:0e:fb:4c con permiso de Mario. El medidor (ESP32-C3) no
se ha tocado.
