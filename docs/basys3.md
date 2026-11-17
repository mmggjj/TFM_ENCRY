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
oscilador de 100 MHz; las del flujo, ±1 ms en la duración (tick del ESP32)
más la latencia de arranque del flujo.

## Resumen

(se completa al final de la sesión)

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
   **130,0 MHz** [MEDIDO, flujo] y todas las restricciones se cumplen. El
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
   pequeños; además, los doce bancos. Reloj de sistema +1,0 ns.

| Reloj | Restricción | WNS | WHS |
|---|---|---|---|
| sistema (100 MHz) | 10 ns | +1,014 ns | +0,043 ns |
| ro2 (11 etapas) | 4,2 ns (medido luego 7,69 ns) | +0,075 ns | +0,155 ns |
| ro1 (13 etapas) | 4,7 ns | +3,101 ns | +0,223 ns |

Utilización [Vivado, implementado; `build/util_hier.rpt`, local]: **4 011 LUT
(19 % del XC7A35T, 144 de ellas como RAM distribuida) y 4 561 biestables
(11 %)**, sin BRAM ni DSP. Del motor (3 880 LUT, 4 392 FF): `ctr_drbg` 1 631 /
2 225, `aes_enc_32` 647 / 266, `aes_cmac` 390 / 523, `i2c_slave` 452 / 86,
`health_tests` 419 / 86, `trng_capture` 156 / 44, `flujo_crudo` 113 / 55. La
estimación de Yosys del 10-11 (5 125 LUT) quedaba un 28 % por encima.

## Frecuencias de los anillos [MEDIDO]

| Etapas ro2 / ro1 | ro2 | ro1 | Cómo |
|---|---|---|---|
| 5 / 7 | 357,8 MHz | 291,8 MHz | display (Mario) |
| 7 / 9 | 293 MHz | — | duración de un flujo de 16 000 B a `kd 14` |
| 11 / 13 | 130,0 MHz (129,94 / 130,02 / 130,10 a `kd 13`, `14`, `15`) | sin medir (display) | flujo de 128 000 bits |

La medida por flujo divide `bits · 2^kd` por la duración que da el ESP32
(tick de 1 ms); las tres coinciden en ±0,1 %. Fracción de unos de esas tiras:
0,512-0,513.

## El motor entero con el ESP32 (O5) [MEDIDO]

ESP32 a0:dd:6c:0e:fb:4c con el verificador, I2C a 400 kHz (GPIO22 → JA1,
GPIO21 → JA2, GND), pull-ups de los pines (ESP32 y FPGA). `sw0` arriba
(modo test). Secuencia (`results/esp32_consola_basys3_motor_completo_20261117.log`):

- `id`: `id 0xa5 version 0x04 ... solo_fuente=0` (motor entero).
- `kd 16`, `sembrar` (test de arranque y semilla de 512 bits): ok.
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

Q por periodo de ro2 (ro2 a 130,0 MHz, T = 7,69 ns):

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
inferior de la rejilla de Q (1·10⁻⁵): es una cota, no un valor.

Lectura:

1. **Q por periodo de ro2 entre 1·10⁻⁵ y 8·10⁻⁵ según el método**: σ/T de
   3-9·10⁻³, σ ≈ 25-70 ps por periodo de 7,7 ns. Del mismo orden que en la
   Basys 2 (4-7·10⁻⁵ en periodos de 7 ns) y, como allí, unas diez veces el
   jitter térmico típico de un anillo en FPGA.
2. **El modelo del ERO no describe la forma**: el exponente libre sale de 1,3
   a 2,1 (1 sería jitter térmico) y los residuos son decenas de veces el
   ruido. Mismo problema abierto que en la Basys 2 (`docs/basys2.md`,
   "Residuo del modelo de jitter"), ahora en otra tecnología (28 nm frente a
   90 nm) y con otra herramienta: apunta a algo de las FPGA (deriva lenta,
   ruido común de alimentación, acoplamiento) más que a una placa.
3. **La lógica colgada de ro1 cambia su ciclo de trabajo**: fracción de unos
   0,5133 con el frecuencímetro y 0,4956 sin él (en la Basys 2, 0,519 y
   0,498). La Q no cambia de forma clara entre variantes con estos métodos.
4. **Divisor de trabajo provisional: `CFG_KD` ≥ 16.** Con la Q más baja
   (1·10⁻⁵), K\* = 0,2286 / Q ≈ 2^14,5 y con un factor 2 de margen, 2^15,5.
   Mientras el modelo no describa los datos, el divisor no se apoya solo en
   el jitter: la campaña SP 800-90B de abajo hace de contraste.

## Campaña SP 800-90B [MEDIDO]

Variante silenciosa (`G_QUIETO=true G_MEDIDOR=false`, muestreo sin
habilitación, cortes 51/766), 10⁶ bits por divisor, batería no-IID en bits
(`campana_motor.py --90b`). `kd 8`, `10` y `11` por trozos de 4 096 bits (el
flujo no da abasto por debajo de `kd 12` a 115 200 baudios); `kd 12` a `16`
en flujo consecutivo. 0 CRC malos; ro2 130,28-130,34 MHz durante los flujos.
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
  medida y cuadra con **Q ≈ 8·10⁻⁵**, justo la del ajuste global por
  autocorrelación de esta misma variante (8,3-8,5·10⁻⁵). Con esa Q,
  K\* ≈ 2^11,5.
- `kd 8` queda por debajo con 8·10⁻⁵: a divisores bajos manda la fase
  determinista (como en la Basys 2), y es donde salta el RCT en placa (abajo).
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
(0,496-0,498). El sesgo es del camino de muestreo de ro1, no del CE.

## Tabla O8 (`tabla_o8.py`)

La Basys 3 entra en `results/tabla_o8.md` como columna propia. A 10⁶ bits la
H asignada no separa nada: Basys 3 0,838 (0,819-0,877), Basys 2 0,845, ESP32
0,848, bits ideales 0,847. Los estimadores sueltos sí separan las dos FPGA del
ESP32 por el sesgo (MCV 0,983 frente a 0,995; MultiMMC y LZ78Y 0,984 frente a
0,996); Markov 0,988 frente a 0,998, aquí sin correlación, solo por el sesgo.

## Tests de salud en placa [MEDIDO]

Cortes 51/766 (H 0,60, α = 2⁻³⁰), variante silenciosa: por divisor, `kd`,
`borrar` y 40 s (`results/esp32_consola_basys3_salud_kd*.log`, locales):

| kd | 6 | 8 | 10 |
|---|---|---|---|
| Alarma | — | **RCT** | — |

El RCT salta a `kd 8`, donde la batería da 0,125; a `kd 6` (más
determinista aún) no salta en 40 s y a `kd 10` tampoco. Como en la Basys 2
(`salud_offline.py`), los tests de salud no cubren de forma fiable el
régimen de poco jitter: lo protege el divisor mínimo (`G_KD_MIN`, 6 por
defecto, sin decidir).
