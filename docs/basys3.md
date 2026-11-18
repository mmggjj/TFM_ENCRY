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
(lectura del display y cableado). Todo [MEDIDO] en placa salvo lo marcado.

| | Resultado |
|---|---|
| Herramienta | Vivado 2025.2 en Ubuntu 26.04 (no soportado) con dos ajustes de entorno |
| Implementación | motor entero: 4 011 LUT (19 %), 4 561 FF; todas las restricciones cumplen tras tres arreglos (pblocks, anillos de 11/13 etapas, APT) |
| Anillos | ro2 357,8 MHz (5 etapas, display), 293 MHz (7), **130,0 MHz (11)** (flujo) |
| **O5** | **40/40 retos AES-CMAC iguales a mbedtls**, dos claves distintas, aleatorio, zeroización |
| Jitter | Q por periodo de ro2 ~1-8·10⁻⁵ según el método; el modelo deja residuo (como en la Basys 2) |
| SP 800-90B | `kd 8` 0,125, `kd 10` 0,558, `kd 11` 0,786, `kd 12-16` saturada; a 8,4·10⁶ bits 0,932 (ESP32 0,911, ideal 0,935) |
| Divisor | `CFG_KD` ≥ 16 (conservador); la batería sería compatible con K\* ≈ 2^11,5 |
| Sesgo / correlación | fracción de unos 0,495-0,496 (z −7 a −26); sin correlación a retardo 1 (muestreo libre) |
| Salud | el RCT salta a `kd 8`; a `kd 10` (batería 0,558 < 0,60) no |
| Reinicios (§3.1.4) | **pasa**: 1 000 reprogramaciones, H_r 0,843 y H_c 0,892 ≥ H_I 0,819; 1 000 arranques distintos |
| Revisión | dos agentes independientes: APT equivalente (exhaustivo, cosimulación, formal) y cifras recalculadas; correcciones aplicadas |

### Basys 2 frente a Basys 3

| | Basys 2 (XC3S100E, 90 nm) | Basys 3 (XC7A35T, 28 nm) |
|---|---|---|
| Qué cabe | solo la fuente | el motor entero |
| Anillos en placa | 7/9 etapas, ro2 ~144 MHz | 11/13 etapas, ro2 130 MHz |
| Q por periodo de ro2 | 1,0-4,9·10⁻⁵ (según implementación, `kd 7-9`) | ~1-8·10⁻⁵ (según método, `kd 0-2`) |
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
   el "LUT Combining" del placer, que `DONT_TOUCH` no impide; ro1 no. Para
   una colocación estable entre implementaciones habría que fijar LOC y BEL
   de cada etapa (pendiente).
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

| Reloj | Restricción | WNS | WHS |
|---|---|---|---|
| sistema (100 MHz) | 10 ns | +1,014 ns | +0,043 ns |
| ro2 (11 etapas) | 4,2 ns (medido luego 7,69 ns) | +0,075 ns | +0,155 ns |
| ro1 (13 etapas) | 4,7 ns | +3,101 ns | +0,223 ns |

Utilización [Vivado, implementado; `build/util_hier.rpt`, local]: **4 011 LUT
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
valor más bajo bien determinado es **0,94·10⁻⁵** (`kd 2`, M = 100).

Lectura:

1. **Q por periodo de ro2 entre ~1·10⁻⁵ y 8·10⁻⁵ según el método**: σ/T
   de 3-9·10⁻³, σ ≈ 25-70 ps por periodo de 7,7 ns. Del mismo orden que en
   la Basys 2 (1,0-4,9·10⁻⁵ en `kd 7-9` con el ajuste conjunto según la
   implementación, `docs/basys2.md` "Residuo del jitter: halo, CE e
   implementación"; σ calculada allí con el periodo de ro1) y entre 5 y 35
   veces los 2-5 ps de jitter térmico por periodo que da la literatura para
   anillos en FPGA (`docs/modelo_ero_resultados.md` §5).
2. **El modelo del ERO no describe la forma**: la b libre de la
   autocorrelación sale de 1,6 a 2,1 (1 sería jitter térmico; la del
   estimador por varianza, 0,96-1,44, no es fiable a `kd 0`) y los residuos
   del ajuste conjunto son decenas de veces el ruido. Mismo problema abierto
   que en la Basys 2, ahora con otra FPGA (28 nm frente a 90 nm) y otra
   herramienta. No separa FPGA de montaje ni de modelo: las dos placas
   comparten ESP32, alimentación por USB del mismo PC y análisis.
3. **Las dos variantes difieren** en fracción de unos (0,5133 frente a
   0,4956; en la Basys 2, 0,519 y 0,498 con y sin frecuencímetro) y en la Q
   del ajuste global (5,0-5,5 frente a 8,3-8,5·10⁻⁵, ×1,6 en los dos `kd`).
   No se puede atribuir a la carga de ro1: son implementaciones distintas
   (la silenciosa colocó ro1 de otra forma dentro de su pblock) y cambian
   display y medidor a la vez. Sin repetibilidad medida en esta placa.
4. **Divisor de trabajo provisional: `CFG_KD` ≥ 16.** Con la Q más baja bien
   determinada (0,94·10⁻⁵), K\* = 0,2286 / Q ≈ 2^14,6 y con un factor 2 de
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

- **Cada método es repetible** (±0,3-2 % los de autocorrelación), así que la
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
con P(0) = 0,5046 dan ~0,987.

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
