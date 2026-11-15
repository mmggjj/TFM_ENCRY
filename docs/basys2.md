# La Basys 2: la fuente en una FPGA pequeña

La placa disponible es una **Basys 2** de Digilent con **XC3S100E-4CP132**
(Spartan-3E, 90 nm, grado de velocidad -4, rango comercial; serigrafía leída
el 14-11-2026 y IDCODE leído por JTAG): 1 920 LUT4, 1 920
biestables, 4 bloques de RAM de 18 kbit. No es la Basys 3 (Artix-7) para la
que se preparó `basys3_top`. Todo lo de la Basys 3 (`rtl/fpga/basys3_top.vhd`,
`synth/basys3/`, `docs/puesta_en_marcha_fpga.md`) se conserva sin cambios:
el RTL del motor es el mismo, y si algún día hay una Basys 3 el mismo diseño
queda medido en dos tecnologías de FPGA (90 y 28 nm) además de la simulada
de IHP (130 nm).

## Estado al 14-11-2026 y qué significa para la memoria

**Decisión de Mario (14-11-2026):** va a intentar conseguir una Basys 3.
Los resultados de la Basys 2 son **provisionales**: la memoria no se cierra
con ellos. Si llega la Basys 3, se repite allí lo que haga falta y se decide
entonces qué va a la memoria (las dos placas, o la Basys 3 con la Basys 2
como contraste). Si no llega, esto es lo que hay y O5 se reformula.

Resumen de lo conseguido (todo en placa salvo lo marcado):

| | Resultado | Tipo |
|---|---|---|
| Fuente en la FPGA | variante de solo fuente, 85 % de slices; reloj 50 MHz; ro2 143,8 MHz y ro1 108,7 MHz (7 y 9 etapas, colocados); tiempos cumplidos con 33 % de margen | medido |
| Integración con el ESP32 | I2C a 400 kHz; `id` con `solo_fuente=1`; flujo de 10⁶ bits consecutivos sin un error | medido |
| Ruido de fase entre anillos | Q por periodo de ro2 ≈ 4,5·10⁻⁵ (±3-5 % entre capturas) en la variante sin display ni medidor; depende ×2,5 de la lógica colgada de los anillos; el modelo deja residuo 3-11 veces el ruido en `kd 7-9` | medido, interpretación provisional |
| Modulación determinista | el display multiplexado modula los anillos (ν bimodal por trozo); apagarlo baja el residuo de 45 a ~7 veces el ruido | medido |
| SP 800-90B | `kd 13-16` saturadas (0,82-0,86); `kd 12` = 0,760, coherente con el modelo con la Q medida y no con la de otra variante | medido |
| Divisor de trabajo | `CFG_KD` ≥ 14 (K\* ≈ 2^12,3 con factor 2 de margen) | provisional |
| Criptografía en la FPGA (O5) | no cabe en el XC3S100E | — |

Lo que queda abierto en esta placa: el origen del residuo del modelo (ESP32
leyendo durante la captura, reloj de 50 MHz, alimentación), la comparación
con el ESP32 (O8) con estas cifras, y la redacción.

## Si llega la Basys 3: qué se reutiliza y qué hay que repetir

Se reutiliza sin cambios: el RTL del motor (la Basys 3 lleva el motor entero,
`G_SOLO_FUENTE` falso), el firmware (el verificador ya distingue
`solo_fuente`), `flujo_desborde.py`, `jitter_autocorrelacion.py`,
`campana_motor.py --flujo`, `compara_modelo_campana.py`, la línea base del
ESP32. Hay que repetir, con lo aprendido aquí (lista detallada en
`docs/puesta_en_marcha_fpga.md` §9):

1. Comprobar en la netlist implementada que los anillos tienen sus etapas
   (en ISE desaparecieron; en Vivado el `DONT_TOUCH` sí llega, pero se mira).
2. Medir frecuencias y cerrar tiempos del contador de `ero_core` con la
   frecuencia medida.
3. Apagar el display durante las capturas (añadir a `basys3_top` el
   equivalente de `G_QUIETO`).
4. Jitter a `kd 0` con el buffer de captura (en la Basys 3 cabe) y, como
   contraste, el mismo procedimiento que aquí (trozos por desbordamiento y
   ajuste de c(M)); repetibilidad con al menos tres capturas.
5. Campaña SP 800-90B con `--flujo` barriendo por debajo y por encima de K\*.
6. Motor completo con el ESP32 (O5): `sembrar`, `generar`, `reto`,
   `aleatorio`.
7. Comparación entre placas: mismo anillo en Spartan-3E (90 nm) y Artix-7
   (28 nm) y el de IHP simulado (130 nm).

## Qué cabe

Estimación con Yosys `synth_xilinx -family xc3se` (14-11-2026). **Es una
estimación de otra herramienta**: el soporte de Yosys para Spartan-3E es
experimental y no infiere SRL16; ISE dará otra cifra. Una RAM16X1D cuenta
como 2 LUT4.

| Bloque | LUT4 | FF |
|---|---|---|
| `aes_enc_32` | 3 812 | 265 |
| `ctr_drbg` (sin AES) | 2 268 | 2 093 |
| `aes_cmac` (sin AES) | 733 | 647 |
| `trng_capture` (512 B) | ~824 | 44 |
| `flujo_crudo` (256 B) | ~610 | 55 |
| `health_tests` / `i2c_slave` / `ero_core` / `medidor_frec` | 300 / 192 / 146 / 182 | 86 / 85 / 28 / 60 |
| `motor_top` entero, sin FIFO | ~9 080 | 4 068 |
| **`motor_top` solo fuente, sin captura, FIFO de 256 B** | **~1 016** | **287** |
| `motor_top` solo fuente, con captura y FIFO de 256 B | ~1 879 | 333 |
| **`basys2_top` entero** (motor solo fuente, frecuencímetro, display, latido) | **~1 250** | **452** |

La última fila sale de la misma netlist Verilog que leerá XST
(`synth/basys2/yosys_xc3se.sh`, `results/basys2_yosys_xc3se.log`): ~65 % de
las LUT4 y ~24 % de los biestables del XC3S100E.

La criptografía sola pide unas 6 800 LUT4, tres veces y media el chip: **el
motor entero no cabe**, y ninguna reducción razonable del AES o del DRBG lo
mete en las ~900 LUT4 que deja la fuente. La fuente sí cabe, sin el buffer
de captura por trozos (con él, ~98 % antes del frecuencímetro y el display).

## La variante de solo fuente

`motor_top` con `G_SOLO_FUENTE => true` y `G_CAPTURA_BYTES => 0`: mismo mapa
I2C y misma VERSION, `DIAG.solo_fuente` = 1, las órdenes criptográficas y
`capturar` rechazadas con `DIAG.rechazada` (`docs/mapa_registros.md`,
"Variantes sintetizables"). Banco `tb_motor_solo_fuente` (21 comprobaciones,
PSL 4/4 y 2/2). Con los genéricos por defecto el motor no cambia: las
netlists antes y después del cambio son idénticas byte a byte en cuatro
variantes (`synth/equivalencia.sh`, `results/equivalencia_motor_top.log`).

## El envoltorio: `basys2_top`

`rtl/fpga/basys2_top.vhd`, con los mismos servicios que `basys3_top`:

| Señal | Pin | Uso |
|---|---|---|
| `clk` | B8 | oscilador de placa (se esperan 50 MHz, `G_CLK_MHZ`) |
| `btn_rst` | G12 (btn0) | reset, activo a nivel alto |
| `sw_test` | P11 (sw0) | `modo_test` |
| `sw_ro` | L3 (sw1) | anillo del display: abajo ro2, arriba ro1 |
| `scl`, `sda` | B2, A3 (JA1, JA2) | I2C, SDA en colector abierto, pull-up del pin |
| `ro_div` | J3 (JA3) | anillo / 64, solo en modo test |
| `led_alarma` | M5 (ld0) | alarma de salud |
| `led_vivo` | G1 (ld7) | cambia cada medio segundo exacto si el reloj es `G_CLK_MHZ` |
| `seg`, `dp`, `an` | ver UCF | frecuencia del anillo en MHz con un decimal |

Pines del manual de referencia de Digilent (revisión del 11-11-2010),
contrastados con el UCF general publicado para la placa; la tabla del manual
pone K14 = AN2, pero su figura y el UCF dicen AN3, y se sigue la figura.
Diferencias con la Basys 3: reloj de 50 MHz (ventana del frecuencímetro de
`640 · G_CLK_MHZ` ciclos, la misma resolución de 100 kHz), `G_KD_MIN => 7`
(a 50 MHz el cruce de dominio pide el doble de divisor para los mismos 8
ciclos por bit) y el latido calibrado. Banco `tb_basys2_top`: frecuencímetro
sobre los anillos, JA3 con y sin modo test, latido, e I2C a través del pin
bidireccional (ID y `DIAG.solo_fuente`).

**Conexión con el ESP32:** JA1 a SCL, JA2 a SDA, pin 5 del Pmod a masa, y
pull-ups de 2,2-4,7 kΩ al pin 6 (3,3 V) si el cable es largo o el bus va a
400 kHz. Los Pmod de la Basys 2 llevan resistencias serie de protección.

## Flujo de ISE (probado el 14-11-2026)

XST, el sintetizador de ISE 14.7, no lee VHDL-2008 y el RTL lo usa (`process
(all)`, puertos de salida leídos, etc.). Por eso `synth/basys2/a_verilog.sh`
elabora `basys2_top` con GHDL a una netlist Verilog (el mismo camino que
`synth/sintetiza.py --verilog` para el integrado) y XST sintetiza esa
netlist; las LUT1/LUT2 de los anillos llegan como instancias de primitiva y
se conservan. `synth/basys2/build.sh` encadena GHDL, `xst`, `ngdbuild`,
`map`, `par`, `trce` y `bitgen` (`StartUpClk:JtagClk`, porque se graba por
JTAG) y con `programar` graba con `djtgcfg` (dispositivo 0 de la cadena). El
UCF es `synth/basys2/basys2.ucf`.

Al pasar a Verilog se pierden los atributos (`ASYNC_REG`, `DONT_TOUCH`): en
Spartan-3E `ASYNC_REG` no cambia la implementación, y a los anillos los
protege ser primitivas instanciadas. GHDL encontró al pasar a Verilog un
latch en la variante de solo fuente (`siembra_es_reseed` solo asignado en el
reset), que Yosys con el plugin había tragado sin aviso; corregido en
`motor_top` con la señal `sin_cripto`.

## Riesgos conocidos

- **El contador de 24 bits de `ero_core` corre a la frecuencia de ro2**
  (resuelto: ver "Anillos colocados y alargados"). Si se cambian los
  anillos o su colocación, repetir `trce` y comparar con el display.
- **Los anillos pueden desaparecer en la implementación** (pasó en el
  primer bitstream): comprobar en el XDL que tienen sus etapas.
- **ISE 14.7 en Ubuntu 26.04:** no soportado por AMD; solo se usan las
  herramientas de línea de órdenes.

## Qué cubre y qué no

- **Objetivo oficial** (integrar la fuente en una FPGA con un ESP32 y
  comparar sus secuencias con las del ESP32): cubierto. La fuente, los
  tests de salud y el flujo continuo van en la placa, y el ESP32 lee los
  bits por I2C.
- **O6** de la memoria (campaña SP 800-90B sobre los anillos de la FPGA):
  cubierto.
- **O5** de la memoria (el motor entero verificado en FPGA con el ESP32
  como oráculo): **no se puede en esta placa**. La criptografía queda
  verificada en simulación (vectores CAVP, mbedtls real contra el modelo,
  QEMU) y sintetizada sobre IHP. O5 se reformula en la memoria.

## Reloj

El oscilador principal es un LTC6905 con el jumper JP4 de selección
(25/50/100 MHz) **sin soldar**, como sale de fábrica. Con la patilla de
división al aire el LTC6905 divide por 2: se espera **50 MHz** [sin
comprobar en esta placa]. Se confirma el primer día con un LED a 1 Hz y un
cronómetro durante 60 s (resolución ~1 %, de sobra para distinguir 25, 50 y
100 MHz). `motor_top` no depende del reloj salvo en el filtro y la guarda del
I2C (en ciclos: a 50 MHz el filtro de 5 ciclos son 100 ns y la guarda 70 ms,
los dos válidos) y en el suelo de `CFG_KD` del cruce de dominio, que se
revisa con la frecuencia medida de ro2.

## Herramientas

- **Síntesis:** ISE 14.7 WebPACK (Vivado no admite Spartan-3E). Instalador
  único de Linux, `Xilinx_ISE_DS_Lin_14.7_1015_1.tar` (6 538 618 880 bytes,
  MD5 `e8065b2ffb411bb74ae32efa475f9817`, comprobado el 14-11-2026), bajado
  con la cuenta de AMD de Mario. Instalado sin interfaz ni sudo en
  `~/Xilinx` con el instalador por lotes y un guion que solo marca ISE
  WebPACK (sin drivers de cable ni gestor de licencias):
  `LD_LIBRARY_PATH=~/eda/ise_compat bin/lin64/batchxsetup --batch <guion>`.
  Los acuerdos de licencia los acepta Mario en su terminal: sin nadie que
  conteste, el instalador repite la pregunta en bucle y llenó 4,4 GB de
  `/tmp`. Ubuntu 26.04 no trae `libncurses.so.5`: `~/eda/ise_compat` tiene
  `libncurses.so.5 -> libncurses.so.6` y `libtinfo.so.5 -> libtinfo.so.6`, y
  `build.sh` lo pone en `LD_LIBRARY_PATH`. `build.sh` busca ISE en
  `~/Xilinx/14.7/ISE_DS` (`ISE_DIR`).
- **Licencia:** la "ISE WebPACK License" de la cuenta de Mario está atada a
  la MAC de su PC con Windows (generada el 10-03-2025); en este PC no vale.
  Pendiente de ver si XST la pide para el Spartan-3E.
- **Grabación desde Linux:** la placa aparece como `1443:0007 Digilent
  Adept USB Device`. openFPGALoader solo conoce los cables FTDI de Digilent,
  así que no sirve. Se usa Adept 2 de Digilent: ver la sección siguiente.

## Adept 2 y la cadena JTAG (14-11-2026, medido)

Instalados Adept 2 Runtime 2.30.1 y Utilities 2.6.1 (`.deb` amd64 de la
página de Digilent; el enlace de las Utilities 2.7.1 da AccessDenied). La
regla udev del Runtime deja la placa en `crw-rw-rw-` tras reconectarla.
`djtgcfg enum` la ve como **"Digilent Basys2-100"**, con el nombre de usuario
corrupto en su memoria: no se puede elegir con `-d Basys2`, se elige por
número de serie (`-d SN:<serie>`; `build.sh` lo saca de `djtgcfg enum`).
`djtgcfg init` lee la cadena JTAG sin grabar nada:

| Posición | Chip | IDCODE |
|---|---|---|
| 0 | XC3S100E | `0x11C10093` (revisión 1 de `x1C10093`) |
| 1 | XCF02S (Platform Flash) | `0xD5045093` |

## Primera implementación con ISE (14-11-2026)

`synth/basys2/build.sh` completo con ISE 14.7 en Linux (log íntegro en
`results/basys2_ise_build.log`). XST y ngdbuild funcionan sin licencia; map
pide la WebPACK. La licencia que tenía Mario estaba atada a la MAC de su PC
con Windows; la nueva es **HOSTID=ANY** (así no importa que el FlexLM de ISE
solo mire `eth0` y aquí vea `000000000000`), en `~/.Xilinx/Xilinx.lic`, fuera
del repositorio. `lmutil` pide el cargador LSB: se lanza con
`/lib64/ld-linux-x86-64.so.2`.

| | ISE (map/par, medido por la herramienta) | Yosys (estimación) |
|---|---|---|
| Slices | 818 / 960 (85 %) | — |
| LUT4 | 1 516 / 1 920 (78 %; 256 en la RAM de la FIFO, ~170 de paso) | ~1 250 |
| Biestables | 451 / 1 920 (23 %) | 452 |
| `TS_clk` 20 ns | cumple, mejor caso 15,97 ns (62,6 MHz) | — |
| `TS_ro2` 5 ns (contador de `ero_core`) | cumple, mejor caso 4,65 ns (~215 MHz) | — |
| `TS_ro1` 4 ns (prescaler) | cumple, mejor caso 3,85 ns (~260 MHz) | — |

Los relojes de los anillos van por rutado local (sin BUFG): desfase de red
0,06 ns en ro2 (26 slices) y 0,002 ns en ro1.

**Fallo del primer bitstream: no había anillos.** Al pasar por Verilog se
pierde el `DONT_TOUCH`; XST vio que tras la NAND hay un número par de
inversores y llevó los relojes a la salida de la NAND (lógicamente igual), y
map colapsó después la cadena de LUT1 como un cable: la NAND quedó
realimentada consigo misma y el frecuencímetro marcó 000.0. Se vio en la
netlist física (`xdl -ncd2xdl`): la red `u_nand_O` salía por X y volvía a la
entrada F2 de la misma LUT. Corregido con `KEEP` en el UCF sobre todas las
redes del lazo; comprobado en el XDL que quedan 5 LUT en ro2 y 7 en ro1, con
el lazo cerrado y los relojes en la salida del anillo (`ro_mon`). **Lección
para cualquier herramienta:** comprobar en la netlist implementada que el
anillo tiene sus etapas, no solo en la síntesis (XST sí las conservaba).

## Primer día en placa (14-11-2026, medido)

Bitstream grabado por JTAG con `djtgcfg` (volátil: la Platform Flash no se
toca). Nada conectado a los Pmod, sw0 abajo (sin modo test).

| Medida | Valor | Resolución / incertidumbre |
|---|---|---|
| Reloj de placa (ld7, 60 s de cronómetro) | 60 parpadeos: **50 MHz** | ±1 parpadeo + reacción: ±2 %; descarta 25 y 100 MHz |
| ro2, 5 etapas (display, sw1 abajo) | **167,8 MHz** | ±0,1 MHz (una cuenta en 640 µs) y ±2 % de escala por el reloj |
| ro1, 7 etapas (display, sw1 arriba) | **105,8 MHz** | ídem |
| Alarma de salud (ld0) | apagada | — |

- Retardo por etapa: 0,596 ns en ro2 y 0,675 ns en ro1 (LUT más rutado). La
  razón ro2/ro1 es 1,59 y no 7/5: el rutado de cada anillo es distinto
  porque la colocación aún no está fijada (`AREA_GROUP` pendiente); estas
  cifras cambiarán al fijarla.
- ro2 queda por debajo de los ~215 MHz que aguanta el contador de
  `ero_core` según `trce`: no hace falta alargar los anillos.
- Para comparar: la estimación para Artix-7 era 170-330 MHz y el anillo de
  IHP simulado a nivel de transistor oscila a 2,73 GHz.

## Anillos colocados y alargados (14-11-2026, tarde, medido)

Un `AREA_GROUP` cerrado por anillo, en bordes opuestos del chip
(`SLICE_X0Y20` y `SLICE_X28Y20`), comprobado en el XDL. Con 5 y 7 etapas
compactas, ro2 subió a **204,8 MHz** y ro1 a 145,8 MHz: por encima de los
~203 MHz que `trce` garantiza para el contador de `ero_core` (camino
crítico: comparación con la máscara del divisor por el CE del biestable de
muestreo, 4,3 ns de datos más 0,6 ns de desfase del reloj local). Se
alargaron los anillos en `basys2_top` (genéricos que ya existían; el motor,
la Basys 3 y el integrado no cambian): **7 etapas en ro2 y 9 en ro1**.

| Medida (display, sw1) | Valor | Retardo por etapa |
|---|---|---|
| ro2, 7 etapas, 1 CLB | **143,8 MHz** | 0,497 ns |
| ro1, 9 etapas, 2 CLB | **108,7 MHz** | 0,511 ns |

±0,1 MHz de lectura y ±2 % de escala. `TS_ro2` mejor caso 4,68 ns
(~214 MHz): ro2 queda un 33 % por debajo. Colocados, los dos anillos tienen
casi el mismo retardo por etapa (sin colocar diferían un 13 %). ro2 medido
también con el reloj del ESP32 por la duración del flujo: 143,1 MHz.

## El ESP32 en el bus (14-11-2026, medido)

ESP32 a0:dd:6c:0e:fb:4c con el verificador, GPIO22 → JA1 (SCL), GPIO21 →
JA2 (SDA), GND → pin 5 del Pmod, pull-ups internos de las dos placas (sin
resistencias externas), I2C a 400 kHz. `id` da `id 0xa5 version 0x04 ...
arrancado=1 ... solo_fuente=1` (log serie local, no versionado como todos los de consola: `results/esp32_consola_basys2_id_20261114.log`).
Flujo con modo test: 2000 bytes a `kd 13` en 16 tramas con CRC correcto, y
10⁶ bits consecutivos a `kd 13` y `kd 14` sin un error
(`results/motor_campana/basys2_jitter_kd13_14/`: los `.bin` y `resumen.csv`; el `serie.log` queda en local). Fracción de unos 0,519
(ciclo de trabajo de ro1).

## Jitter: primeros resultados (PRELIMINARES, no concluyentes)

Sin buffer de captura no hay `kd 0` (el paso 6 de la puesta en marcha). Dos
herramientas nuevas, validadas con bits simulados de Q conocida antes de
usarlas:

- `analysis/flujo_desborde.py`: por debajo de `kd 12` la FIFO del flujo se
  desborda en milisegundos, pero lo enviado antes son tramas completas con
  CRC y numeradas, bits consecutivos. Repitiendo `flujo`: trozos de 2048 a
  5120 bits (`kd 7` a `11`, 10⁶ bits por divisor en 40-100 s).
- `analysis/jitter_autocorrelacion.py`: ajusta la curva media c(M) (pares
  distintos a distancia M) con el modelo del ERO (triangular suavizada por
  el paseo aleatorio de la fase, con ciclo de trabajo d). El estimador por
  varianza de `jitter_estimator.py` **no vale** a divisores altos: con bits
  simulados infraestima Q entre un 65 y un 100 %. El nuevo recupera Q con
  sesgo ≤ 1,2 % y dispersión ≤ 1,7 % (tira contigua) y ≤ 0,4 % / 0,6 % por
  trozos; el exponente libre b delata una deriva (b ≈ 2). `--conjunto` da a
  cada trozo su propio ν y separa la deriva entre trozos del jitter.
  Autotest en `results/jitter_autocorrelacion_autotest.log`.

Resultados (`results/motor_campana/basys2_jitter_kd07_12/jitter_*.txt`):

| kd | Q por muestra (conjunto) | Q por periodo de ro2 | residuo / ruido |
|---|---|---|---|
| 7 | 5,0·10⁻³ | 3,9·10⁻⁵ | 45 |
| 8 | 1,29·10⁻² | 5,0·10⁻⁵ | 31 |
| 9 | 2,71·10⁻² | 5,3·10⁻⁵ | 13 |
| 10 | 7,0·10⁻² | 6,9·10⁻⁵ | 6 |
| 11 | 6,0·10⁻² (saturándose) | — | 1,4 |
| 13, 14 | ≥ 0,2 (saturado: c(M) plano desde M = 2) | — | — |

Lectura:

1. Hay mucho ruido de fase entre los dos anillos: Q por periodo de ro2 de
   4-7·10⁻⁵, σ ≈ 60-70 ps por periodo (en periodos de ro1 de 9,2 ns), del
   orden de diez veces el jitter térmico típico de un anillo en FPGA (2-5
   ps, literatura). Crece con K_D más o menos linealmente (de `kd 7` a
   `kd 10`, ×14 para ×8).
2. La deriva de la razón de frecuencias entre trozos no lo explica: el
   ajuste con un ν por trozo deja la misma Q.
3. **El modelo no describe la forma**: los residuos son 13-45 veces el ruido
   binomial en los divisores bajos, cuando con bits simulados que cumplen el
   modelo exactamente la razón es ~1,7 (Q 3·10⁻³) o menor (autotest). Hay algo más que jitter gaussiano:
   candidatos, modulación periódica de las frecuencias (acoplamiento con el
   reloj de 50 MHz, la lógica que conmuta, el I2C) o ruido de alimentación
   común a los dos anillos.
4. **No se da K\* todavía.** Si parte del ruido es común o determinista no
   cuenta como entropía, aunque a `kd 13` los bits ya parezcan aleatorios.
   Es justo el caso que los tests estadísticos no distinguen y el modelo sí.

### El display modula los anillos (14-11-2026, medido)

Espectro medio de los trozos a `kd 7` frente al de bits simulados con el
modelo ajustado: el modelo da un pico en ν ≈ 0,39-0,41 y los datos **dos**
(0,37 y 0,43) con un valle donde el modelo tiene el máximo. El ν de cada
trozo es bimodal y el estado alterna casi en cada trozo (autocorrelación
−0,25 a desfase 1, +0,31 a 2): una modulación periódica rápida vista con
aliasing. Candidato: el display multiplexado (cada trozo dura 1,8 ms y cada
dígito 1,3 ms; cada dígito enciende distinto número de segmentos). Las tiras
de `kd 13` y `kd 14` no tienen líneas (máximo 1,28 veces la mediana, lo
esperable por azar con 4 097 frecuencias).

Variantes de `basys2_top` (genérico `G_QUIETO`: display apagado y LED fijo;
`G_MEDIDOR = false`: sin frecuencímetro, con `synth/basys2/basys2_sin_medidor.ucf` (antes solo en `build/`, sin versionar)
porque la salida del anillo cambia de nombre), mismos CLB para los anillos,
10⁶ bits por divisor (`results/motor_campana/basys2_quieto*`):

| Variante | Q por periodo de ro2 (kd 7 / 8 / 9) | residuo / ruido | fracción de unos |
|---|---|---|---|
| Normal | 3,9 / 5,0 / 5,3 ·10⁻⁵ | 45 / 31 / 13 | 0,519 |
| `G_QUIETO` | 1,6 / 2,0 / 2,1 ·10⁻⁵ | 7,1 / 7,0 / 4,3 | 0,517 |
| `G_QUIETO`, sin medidor | 4,1 / 4,4 / 4,7 ·10⁻⁵ | 10,8 / 6,6 / 3,3 | 0,498 |

- El display modula los anillos: apagarlo baja el residuo en todos los
  divisores. En la campaña de entropía, display apagado.
- Quitar el medidor no baja Q (vuelve a subir) y cambia la forma de onda de
  ro1 (fracción de unos): la carga de sus prescalers forma parte del anillo.
- **Repetibilidad** (misma variante, `G_QUIETO` sin medidor, tres capturas
  seguidas, `_r2` y `_r3`): Q por periodo de ro2 a `kd 7` 4,08 / 4,45 /
  4,54 ·10⁻⁵ (±5 %), a `kd 8` 4,38 / 4,54 / 4,65 (±3 %), a `kd 9` 4,69 /
  4,93 / 4,86 (±3 %); residuo/ruido 8-11, 5-7 y 2,6-3,3. ro2 en esta
  variante 143,09 MHz (flujo a `kd 13`). El ×2,5 entre variantes es real:
  lo que cuelga de las redes de los anillos cambia su ruido de fase
  relativo (hipótesis: acoplamiento entre anillos a través de esa lógica,
  que haría parecer menor el jitter relativo; sin demostrar).
- Q por periodo casi constante de `kd 7` a `kd 9` (+10 % al cuadruplicar
  K_D): se acumula casi como jitter térmico. El residuo baja con K_D.
- **K\* provisional**: con Q ≈ 4,5·10⁻⁵ por periodo, K\* ≈ 5 100 (`CFG_KD`
  13); según la variante, 13-14. No se da por bueno mientras quede residuo
  sin explicar.

## Campaña SP 800-90B (14-11-2026, medido)

Variante `G_QUIETO` sin medidor (la de la repetibilidad), flujo de 10⁶ bits
consecutivos por divisor, `kd 12` a `16`, batería no-IID en bits
(`results/motor_campana/basys2_campana_90b_kd12_16/`): 0 CRC malos, ro2
143,17-143,24 MHz durante toda la captura, fracción de unos 0,497-0,498.

| kd | H SP 800-90B (mínimo, estimador) | H del modelo con Q 4,5·10⁻⁵ | banda esperada de la batería | veredicto |
|---|---|---|---|---|
| 12 | **0,760** (compresión; MultiMMC 0,968) | 0,952 | 0,762-0,856 | por debajo (por 0,002) |
| 13 | 0,863 (compresión) | 0,9987 | 0,787-0,909 | saturada |
| 14 | 0,846 | 1,0000 | 0,785-0,909 | saturada |
| 15 | 0,821 | 1,0000 | 0,785-0,909 | saturada |
| 16 | 0,845 | 1,0000 | 0,785-0,909 | saturada |

(`compara_modelo_campana.py --q-raw 4.5e-5 --u-q 0.10`; la banda es la de la
calibración con bits del modelo, `fuente_simulada_90b.md`.)

- De `kd 13` en adelante la batería está saturada (0,82-0,86, como con bits
  ideales a 10⁶): no distingue nada, como se esperaba.
- A `kd 12` la batería **sí ve menos entropía** (0,760, el estimador de
  compresión) y cae justo en el borde inferior de lo que predice el modelo
  con la Q medida: coherente con el modelo, si acaso algo peor, en línea con
  el residuo que el modelo no explica.
- Con Q = 2·10⁻⁵ (la de la variante con medidor) el modelo predice menos
  entropía de la que mide la batería en `kd 12` y `13` ("por encima"): la
  campaña es coherente con la Q medida para esta variante y no con la otra.
  Contraste cruzado entre el estimador de jitter y la batería.
- **Divisor de trabajo propuesto (provisional): `CFG_KD` ≥ 14** (H del
  modelo 1,0000 con un factor 2 de margen sobre K\* ≈ 2^12,3), mientras el
  residuo del modelo no esté explicado.

## Captura larga para O8 (14-11-2026, medido)

8 378 368 bits consecutivos a `kd 14` (la longitud de la captura larga del
ESP32 sin radio, `esp_rf_off_2`), misma variante, 0 errores, ro2 143,2 MHz
durante 16 min (`results/motor_campana/basys2_larga_kd14_n8378368/`):
SP 800-90B no-IID **0,890** (colisión). A la misma N: ESP32 0,911; bits
ideales del modelo 0,912 (0,889-0,935). La FPGA cae dentro de la banda de
los bits ideales (en su borde bajo): **a esta N la batería tampoco separa
FPGA, ESP32 y fuente perfecta**, como predecía la simulación.

## Los tests de salud en hardware (14-11-2026, medido)

Al empezar la prueba la alarma ya estaba levantada (RCT y APT), casi seguro
desde las capturas de jitter a `kd 7-9`; el flujo saca bits con alarma (es
modo test), así que los datos de las campañas valen, pero la alarma pegajosa
no dice nada de los divisores de trabajo. Prueba: para cada `kd`, escribir
CFG_KD, `borrar`, 30 s y `id` (`results/esp32_consola_basys2_alarma_kd*.log`,
locales):

| kd | 14 | 13 | 12 | 11 | 10 | 9 | 8 | 7 | 6 |
|---|---|---|---|---|---|---|---|---|---|
| Alarma | — | — | RCT | RCT | — | — | RCT + APT | — | — |

- Los tests saltan en la placa (hasta ahora solo probados en simulación).
- El patrón no es monótono: a `kd` bajos manda la fase determinista ν (según
  el divisor rompe o alarga las rachas), y el RCT tiene falsas alarmas
  frecuentes a tasas altas.
- **Falsas alarmas del RCT (hallazgo de diseño).** El corte C = 22 se
  calculó para α = 2⁻²⁰ por muestra. En los 8,4·10⁶ bits de `kd 14` hay 1
  racha de ≥ 22 (máximo 23) frente a ~2 esperadas con bits ideales, y el
  resto de longitudes también cuadra (136 frente a 128 rachas ≥ 16, 30
  frente a 32 ≥ 18): las rachas son las de una fuente ideal. Con esa α, a
  `kd 14` (8,7 kbit/s) **cabe esperar una falsa alarma cada ~8 min**, y cada
  alarma bloquea el motor hasta `borrar_alarmas`. En el integrado
  (`CFG_KD` 23, 0,2-0,4 kbit/s) sería una cada pocas horas. SP 800-90B
  admite α de 2⁻²⁰ a 2⁻⁴⁰. **Decisión pendiente de Mario**: subir el corte
  (con α = 2⁻³⁰, C = 1 + ⌈30/0,98⌉ = 32) o que el maestro borre la alarma y
  vuelva a sembrar de forma automática. El APT va holgado: máximo 571 en
  ventanas de 1024 (corte 596).

## Prueba de reinicios, SP 800-90B §3.1.4 (14-11-2026, medido)

`analysis/reinicios_fpga.py`: 1 000 ciclos de reprogramar la FPGA por JTAG
(solo la FPGA, la Platform Flash no se toca; 0,6 s) y leer por el ESP32 los
primeros 128 bytes del flujo a `kd 14` (0,4 s), misma variante que la
campaña. 3 ciclos repetidos porque el ESP32 no respondió a tiempo a `kd 14`
tras reprogramar. **Matiz para la memoria:** los bits son los primeros del
flujo, ~0,4 s después de configurar, no los de los primeros nanosegundos;
los anillos sí arrancan desde cero en cada ciclo.
(`results/fpga_reinicios/basys2_kd14/`: `bloques.npy`, `resumen.md`,
`ea_restart_b1.log`.)

- `ea_restart` en modo bit (1000 × 1000), H_I = 0,845 (la de `kd 16` de la
  campaña): **Restart Sanity Check Passed** (X_max 556, corte 626) y
  **Validation Test Passed** (H_r 0,855, H_c 0,873).
- Comprobación directa (la misma que el ESP32): 1000 arranques distintos de
  1000 (también en los 8 primeros bytes); distancia de Hamming media 512,0
  (esperada 512) y desviación 16,02 (16,00); ningún arranque es el flujo de
  otro desplazado; sin sesgo por posición (p corregida 0,45) y primer byte
  uniforme (p = 0,43).
- Contraste con el ESP32 (`docs/esp32_reinicios.md`): sin el ruido del
  cargador de arranque el ESP32 sacaba siempre la misma secuencia; la FPGA
  no tiene ese problema.

## Tabla O8 y un defecto que la cifra asignada no ve (15-11-2026)

`analysis/tabla_o8.py` → `results/tabla_o8.md`: SP 800-90B no-IID en bits,
estimador a estimador, FPGA (`kd 13-16` a 10⁶, `kd 14` a 8 378 368) frente
a ESP32 (36 capturas de los ANOVA y `esp_rf_off_2`), bits ideales y bits
independientes con el sesgo de la FPGA (`analysis/sesgo_90b.py`).
`analysis/sesgo_correlacion.py` → `results/sesgo_correlacion.md`. Todo con
datos medidos ya existentes; nada nuevo en placa.

- **La H asignada (el mínimo) no separa** las tres fuentes: 0,845 / 0,848 /
  0,847 a 10⁶ (la manda la compresión, saturada) y 0,890 / 0,911 /
  0,907-0,935 a 8,4·10⁶.
- **Los estimadores sueltos sí separan la FPGA**, sin solaparse con el ESP32
  ni con bits ideales: Markov 0,984-0,990 frente a 0,994-1,000 (ESP32) a
  10⁶, 0,988 frente a 1,000 a 8,4·10⁶; también MCV, MultiMMC, LZ78Y y
  colisión.
- **Dos defectos medidos en los bits de la FPGA, ninguno en el ESP32:**
  sesgo, fracción de unos 0,4979 (z = −12 a 8,4·10⁶), y correlación
  positiva a retardo 1, ρ₁ = +0,0045 (z = 13); nada a retardos 2-8. En el
  ESP32 las 36 capturas dan z de sesgo y de ρ₁ como una normal (0,1)
  (desviaciones 1,06 y 1,16, máximo |z| 2,9).
- **No dependen del divisor** de `kd 13` a `16` (ρ₁ 0,003-0,006, ±0,001
  cada uno): no es jitter insuficiente (eso bajaría al subir `kd`), es
  determinista, en el camino de muestreo. `kd 12` no cuenta como prueba:
  su ρ₁ por bloques salta de −0,011 a +0,021 y tiene 375 rachas ≥ 12
  frente a 244 esperadas, jitter insuficiente (revisión independiente,
  abajo). A `kd 13` aún hay un leve exceso de rachas ≥ 12 (z 2,4-3,9):
  la comparación limpia es `kd 14`.
- El sesgo solo explica MCV y los predictores (bits iid con p₁ = 0,4979 los
  reproducen), **no** Markov ni colisión, que piden la correlación.
  Probabilidades de transición (8,4·10⁶): P(0|0) = 0,5043, P(0|1) = 0,4998.
- `bit_cdc` queda descartado: una conmutación por bit, y con `kd ≥ 6` no
  puede duplicar ni perder bits.
- Hipótesis de partida: `ero_core` muestrea ro1 directamente, con
  habilitación (`muestra_cruda <= ro1` solo cuando `tic`; en la netlist,
  el pin CE del biestable, sin LUT delante). Con la fase ya aleatoria, P(0)
  es el ciclo de trabajo de ro1 *visto por el biestable*; la correlación
  encajaría con que ese ciclo efectivo dependa del estado anterior del
  biestable (~0,45 % del periodo de ro1, unos 40 ps). **Comprobada en placa
  para la correlación** (sección siguiente); el sesgo no viene de ahí.
- **Lo que cuesta:** −log₂ max P(b|anterior) da una **cota superior** de
  primer orden de la min-entropía por bit, no una cifra declarable, y
  depende de la implementación: 0,9875 la del 14-11, 0,980-0,982 la
  regenerada (con CE), 0,989 la libre (sin CE). Justo en el 0,98 con el que
  se calcularon los tests de salud, por debajo del 1,0000 del modelo, que
  no tiene sesgo de muestreo. Para la memoria: el modelo da la entropía del jitter y no la
  del muestreador, y la cifra única de SP 800-90B esconde un defecto que
  dos estadísticos sencillos ven con z > 10.

## Muestreo sin habilitación (15-11-2026, medido)

Genérico **`G_MUESTREO_LIBRE`** (`ero_core`, `motor_top`, `basys2_top`;
false por defecto): `muestra_cruda` toma ro1 en cada flanco de ro2 y el
`tic` solo marca qué muestra vale, así que el estado previo del biestable
deja de ser el bit anterior. Mismos bits en simulación: **`tb_ero_core`**
(12/12, 110 710 bits iguales entre las dos formas; mutante que adelanta un
ciclo el bit cazado con 56 518 distintos, `results/tb_ero_core*.log`). Con
el genérico por defecto el motor es secuencialmente equivalente a HEAD en
las cuatro variantes de `synth/equivalencia.sh` (`results/equivalencia_motor_top.log`):
`cec` ya no lo prueba porque `habilita` renumera las señales de GHDL y
cambia el orden de los biestables, y el script recurre ahora a ABC `dsec`
(inducción, sin emparejar biestables). Control negativo, `G_KD_MIN=5`
frente a HEAD: `dsec` no lo da por equivalente (sin veredicto en 20 min;
`results/equivalencia_motor_top_control_kdmin5.log`). Ojo: la variante
libre misma no sirve de control, porque es lógicamente equivalente.

Tres implementaciones de la variante sin display ni medidor, con **los dos
anillos y el biestable de muestreo en los mismos slices, BEL y patas de LUT**
(`synth/basys2/basys2_sin_medidor_fijo.ucf`, sacado del XDL de la del 14-11;
comprobado en el XDL de cada una). Lo que `par` decide en cada ejecución,
el rutado de las redes de los anillos, es distinto en el XDL de las tres
(aunque ro2 da la misma frecuencia en regenerada y libre, 143,698 y 143,704
MHz a `kd 13`, frente a 143,2 el 14-11):

- referencia del 14-11 (CE), los datos de la campaña;
- **referencia regenerada** (CE, `basys2_top_quieto_sin_medidor_fijo.bit`):
  mide cuánto mueve el resultado una implementación distinta;
- **libre** (sin CE, `basys2_top_quieto_sin_medidor_libre.bit`; ISE: un FDCE
  pasa a FDC, todas las restricciones cumplen).

2²² bits consecutivos a `kd 13` y `14` de cada una nueva
(`results/motor_campana/basys2_{fijo,libre}_kd13_14_n4194304/`, 0 errores,
ro2 143,7 MHz en las dos). Tabla en `results/muestreo_libre_ce.md`
(`sesgo_correlacion.py --extra`):

| implementación | kd | fracción de unos | ρ₁ | z ρ₁ |
|---|---|---|---|---|
| 14-11 (CE) | 13 / 14 / 14 larga | 0,4981 / 0,4973 / 0,4979 | +0,0032 / +0,0060 / +0,0045 | 3,2 / 6,0 / 13,1 |
| regenerada (CE) | 13 / 14 | 0,4959 / 0,4957 | +0,0042 / +0,0052 | 8,6 / 10,7 |
| libre (sin CE) | 13 / 14 | 0,4962 / 0,4962 | +0,0005 / +0,0000 | 1,0 / 0,1 |
| libre `par -t 7` (sin CE) | 14 | 0,4971 | +0,0002 | 0,4 |

La última fila es una segunda implementación libre (`PAR_OPC="-t 7"` en
`build.sh`, `basys2_top_quieto_sin_medidor_libre_t7.bit`,
`results/motor_campana/basys2_libre_t7_kd14_n4194304/`). Sale con la red
de ro1 rutada **exactamente igual** que la regenerada (mismos pips en el
XDL; solo cambia la de ro2): sin correlación otra vez, y un sesgo distinto
(0,4971 frente a 0,4957) con el mismo rutado de ro1. Así que el sesgo no lo
fija solo el camino de ro1: también ro2 (aquí 143,92 frente a 143,68 MHz)
o el momento de la captura.

- **La correlación la produce la habilitación del biestable de muestreo.**
  Con CE, en dos implementaciones independientes, ρ₁ = 0,003-0,006; sin
  CE desaparece (z ≤ 1; con 2²² bits, un ρ₁ de 0,0045 daría z ≈ 9). A
  `kd 14`, P(0|0) − P(0|1) = +0,0052 con CE y +0,0000 sin CE (±0,0005).
  El mecanismo no está identificado: los datos no distinguen un efecto de
  la historia del biestable de una habilitación que falle ~0,5 % de las
  veces (las dos dan correlación solo a retardo 1). Para la memoria: "al
  quitar la habilitación desaparece", sin mecanismo. Una sola
  implementación libre, una captura por divisor.
- **El sesgo no.** Regenerada y libre casi iguales (0,4957-0,4962) y las
  dos distintas de la del 14-11 (0,4979). No viene de la habilitación; si
  lo mueve el rutado de ro1 o el día no se sabe (se separaría regrabando el
  `.bit` del 14-11 y capturando). Hipótesis: ciclo de trabajo de ro1 más la
  asimetría subida/bajada del camino hasta el biestable (ro1 viaja de
  X29Y21 a X31Y41) y su apertura.
- SP 800-90B: con la libre, Markov sube de 0,980-0,982 a 0,988-0,989; MCV
  y los predictores quedan en ~0,987, limitados por el sesgo; la cifra
  asignada (compresión) sigue saturada, 0,84-0,88 en las dos.
- **Para el integrado:** el RTL es el mismo y un biestable con
  habilitación de biblioteca suele ser un mux con Q realimentada delante de
  un DFF; nada garantiza que no pase lo mismo. Sin CE el coste es un
  biestable conmutando a la frecuencia de ro2 (despreciable frente al
  anillo). Además, con CE el `tic` (AND de 24 bits, el camino más lento del
  dominio ro2) entra en el biestable que fija el bit; sin CE solo va a
  `stb_d1`. Decisión en la sección siguiente.
- La placa queda con la referencia regenerada grabada.

## Decisión del 15-11-2026 (dos agentes, a petición de Mario)

Mario pidió que la sesión principal y un revisor independiente (otro
agente, solo lectura, con su propio script sobre los diez `.bits`, que
reproduce exactas las cifras de sesgo y ρ₁) decidieran entre los dos. Cortes
y tasas de falsa alarma comprobados por los dos (binomial exacta):

| α | RCT C | APT C (W 1024) | bits entre falsas alarmas del APT, p₀ 0,5 / 0,5038 |
|---|---|---|---|
| 2⁻²⁰ | 22 | 596 (actual) | 2^33,3 / 2^32,3 |
| 2⁻³⁰ | 32 | 616 | 2^44,2 / 2^42,8 |
| 2⁻⁴⁰ | 42 | 632 | — |

(con H = 0,98; con 0,988 los cortes apenas cambian, 593/613/630: no se
recalculan). RCT con bits ideales: ~2^(C−1) bits entre falsas alarmas.

1. **`G_MUESTREO_LIBRE = true` por defecto en `motor_top`: sí.** Quita la
   correlación (cota de primer orden de 0,980 a 0,989 con la misma
   colocación), saca el `tic` del biestable que fija el bit y no cambia los
   bits en simulación. **Antes de cambiar el defecto:** los bancos con true
   (sobre todo `tb_motor_top` paso 9), la síntesis (kGE) y decidir contra
   qué compara `synth/equivalencia.sh`. Se cambiaría de opinión si una
   segunda implementación libre (otro rutado, o tras apagar la placa)
   devolviera ρ₁ > 0.
2. **El sesgo se cuenta, no se toca el hardware; H declarada 0,80** (para
   el integrado y la FPGA). Esta decisión se reabrió al medir el ciclo de
   trabajo del anillo IHP [SIMULADO] (`analysis/ciclo_trabajo_ihp.py` →
   `results/ciclo_trabajo_ihp.{csv,log}`; anillo de `anillo_ihp.py` sin
   ruido, 5 nudos, umbral V_DD/2 ± 100 mV, nueve esquinas y 8 chips con
   desapareamiento en tt 27 °C y en ss −40 °C 1,08 V):
   - a V_DD/2 el ciclo depende del nudo, con el mismo patrón en todas las
     esquinas: n2 y n4 en 0,517-0,528 (sistemático), n1, n3 y n5 en
     0,486-0,508;
   - con desapareamiento, 0,483-0,535 (cota de primer orden peor 0,90);
     con ±100 mV de umbral, 0,464-0,553 (0,854). Sensibilidad: 0,018-0,019
     de ciclo por 100 mV, porque los flancos son lentos frente a T = 270-600 ps;
   - sin el cable, el buffer ni la apertura del biestable.

   En el integrado, muestrear ro1 directamente puede dar un sesgo del
   2-5 %; en la FPGA es del 0,4 %. Opciones discutidas: (a) biestable T y
   muestrear ro1/2; (b) contarlo; (c) elegir nudo o dimensionar; (d) XOR de
   pares. La sesión principal se inclinaba por (a); **el revisor convenció
   de (b)**, y los números se comprobaron por los dos:
   - el CTR_DRBG AES-128 no necesita 384 bits de entropía. SP 800-90A pide
     128 de entropía más un nonce de 64, 192 en total (citado de memoria por
     los dos agentes: **comprobar la cláusula**). La semilla son 384 bits
     crudos. Regla de diseño: H en el límite de detección del APT × 384 ≥
     192;
   - con H declarada 0,80 y α = 2⁻³⁰: **RCT C = 39, APT C = 683**. El APT
     deja pasar hasta p ≈ 0,667 (H ≈ 0,584), y aun así la semilla lleva 224
     bits ≥ 192 (con 0,85: 37 y 664, 240 bits). Se declara 0,80 y no 0,85
     porque 0,854 es el peor de solo 8 chips y falta el biestable real;
   - coste de (b): cero en caudal y área; cambian dos genéricos y la
     documentación. Los vectores del DRBG no cambian, porque la semilla
     sigue siendo de 384 bits;
   - (a) cuesta **×4 de divisor, no ×2**: Q va con la varianza de fase
     partida por el periodo muestreado al cuadrado, Q/4. Con
     `ero_model.min_entropia_analitica` calibrado al peor chip (H_∞ 0,973 a
     2²²): ro1/2 a 2²⁴ da 0,973 y a 2²⁵ 0,9996, así que hace falta 2²⁵, un
     contador de 26 bits a 2,7 GHz sin análisis de tiempos. Caudal a la
     cuarta parte (0,05-0,10 kbit/s; semilla y test de arranque en 14-28 s).
     Además mete un biestable T sin verificar con flancos lentos y no evita
     declarar H < 1;
   - (d) queda dominada por (b): gasta el doble de bits crudos, deja H ≈
     0,984 con el peor sesgo simulado y los tests de salud deben ver los
     bits crudos;
   - de (c), lo gratuito: sacar ro1 de un nudo impar, nunca n2 ni n4.
     Como mejora, sin contar con ella; la correspondencia entre los nudos
     del anillo de SPICE (solo inversores) y `ring_osc` (NAND + inversores)
     está por hacer.

   Se pasaría a (a) si Mario o los tutores quieren una fuente cruda con
   H ≈ 1 (el objetivo es caracterizar la aleatoriedad), si la simulación con
   el biestable real da un sesgo por encima del 10 %, o si en la Basys 2 un
   biestable T confirma la bajada del sesgo y Q/4. **Antes de fijar la H
   del integrado:** SPICE con el biestable real de sg13g2 (y el buffer, si
   lo hay) colgado del anillo, barriendo la fase del muestreo; más de 8
   chips si la cifra se apoya en esa cola.
3. **Tests de salud: α = 2⁻³⁰, con los cortes de H = 0,80: RCT C = 39 y
   APT C = 683** (sustituye a los 32 y 616 calculados con H = 0,98). Subir
   solo el RCT habría dejado al APT (596) como fuente dominante de falsas
   alarmas con el sesgo medido (~2^32 bits). Con 39 y 683 las falsas
   alarmas pasan a ser rarísimas (RCT ~2^38 bits con bits ideales, un año
   a `kd 14`). Aun así, **política de rearme en el maestro, acotada y nada
   automático en el hardware**: borrar alarmas, esperar el test de
   arranque, resembrar, y fallo permanente si se repite N veces en una
   ventana. La propuesta inicial de la sesión principal, C = 32 sin rearme,
   no aguantaba.
4. Otros puntos del revisor, recogidos arriba: `kd 12` no prueba nada sobre
   el divisor; "0,988" era una cota y de una sola implementación; mecanismo
   del CE sin identificar; falta una segunda implementación libre; el
   contador de 24 bits y el `tic` a 2,73 GHz en SG13G2 siguen sin análisis
   de tiempos (`docs/sintesis_resultados.md`). Descartado por el revisor:
   estructura por posición de bit mod 8 (acoplo con la lectura por bytes)
   y dependencia de orden 2.

### Aplicado el 15-11-2026

- `motor_top`: **`G_MUESTREO_LIBRE = true`** y los cortes pasan a ser
  genéricos suyos, **`G_RCT_C = 39`** y **`G_APT_C = 683`** (también por
  defecto en `health_tests`). `basys2_top` deja `G_MUESTREO_LIBRE = false`
  para seguir siendo comparable con sus campañas. Con
  `GEN_ACT="-gG_MUESTREO_LIBRE=false -gG_RCT_C=22 -gG_APT_C=596"`,
  `synth/equivalencia.sh` da las cuatro variantes equivalentes a HEAD por
  `dsec` (`results/equivalencia_motor_top.log`): no cambia nada más.
- Bancos: los doce pasan con el muestreo libre por defecto en una copia
  (`results/run_tb_muestreo_libre_true*.log`; `tb_motor_top` 85/85, PSL
  14/14 y 8/8). `tb_health_tests` con 39/683: el RCT salta en la muestra
  39 y la fuente al 70 % en 713.
- `analysis/cortes_salud.py` con H 0,80 y α = 2⁻³⁰, y la regla de la
  semilla (7/7, `results/cortes_salud.log`).
- Firmware: **`motor_rearmar()`** en `componentes/motor_i2c` (3 rearmes en
  24 h y luego fallo permanente hasta reiniciar) y la orden `rearmar` del
  medidor; banco en PC paso 5b (135 comprobaciones, 0 fallos, también con
  ASan/UBSan). Compilado con ESP-IDF 5.3.2: verificador (esp32) y medidor
  para esp32 sin avisos; el medidor para esp32c3 no, porque en este PC no
  está la cadena RISC-V (`install.sh esp32c3`).
- `docs/mapa_registros.md` (cortes, rearme, `G_MUESTREO_LIBRE`) y memoria
  EN y ES: cap. 4 §salud (cortes, rearme, muestreo sin habilitación), cap. 7
  §anillo IHP (párrafo del ciclo de trabajo) y §verificación, apéndice de
  evidencias. PDF regenerados.
- Pendiente: confirmar la cláusula de SP 800-90A (192 bits); SPICE con el
  biestable real de sg13g2 colgado del anillo; síntesis (kGE) con el
  muestreo libre; probar ro1/2 en la Basys 2 si se quiere validar la
  alternativa.

## Pendiente (lista para el 15-11-2026 en adelante)

Por orden; lo marcado (M) necesita a Mario delante de la placa.

1. **Decidir el corte del RCT** (Mario): con α = 2⁻²⁰ hay una falsa alarma
   cada ~8 min a `kd 14`. Opciones: C = 32 (α = 2⁻³⁰; cambia `G_RCT_C` de
   `health_tests`, el banco, `docs/mapa_registros.md` y la memoria) o rearme
   automático en el maestro. Afecta también al motor del integrado.
2. **Residuo del modelo de jitter** (3-11 veces el ruido en `kd 7-9`):
   - (M) bus I2C más lento o con pausas entre lecturas durante la captura
     (¿la actividad del ESP32 modula los anillos?);
   - reloj de 50 MHz y lógica lejos de los anillos (`AREA_GROUP` para el
     resto del diseño) y repetir `flujo_desborde.py` + `--conjunto`;
   - modelo con una componente común o determinista además del paseo
     aleatorio, si lo anterior no lo explica.
3. (M) **Temperatura**: frecuencias de los anillos y Q en frío y con la
   placa calentada (secador a distancia); repetir `kd 7-9` y una tira de
   `kd 14`.
4. **Comparación con el ESP32 (O8)** con las cifras de hoy: tabla FPGA /
   ESP32 / ideal a 10⁶ y 8,4·10⁶ bits, y la prueba de reinicios de los dos.
5. **Memoria**: no cerrar con la Basys 2 hasta saber si llega la Basys 3
   (nota no impresa en el cap. 8). Sí se puede ir escribiendo como borrador
   aparte lo que no depende de la placa: el estimador de c(M) y su
   validación, la modulación del display como ejemplo de ruido determinista
   que la batería no ve, el hallazgo del RCT.
6. Si llega la **Basys 3**: `docs/puesta_en_marcha_fpga.md` §3 con las
   lecciones del §9, y "Si llega la Basys 3" más arriba en este documento.

Estado de las cosas al cerrar el 14-11: la Basys 2 con la variante sin
display ni medidor grabada (se pierde al desenchufar: volver a grabarla con
`djtgcfg prog -d SN:<serie> -i 0 -f synth/basys2/build/basys2_top_quieto_sin_medidor.bit`
o regenerarla con `UCF=../basys2_sin_medidor.ucf GENERICOS="-gG_QUIETO=true
-gG_MEDIDOR=false" bash synth/basys2/build.sh`); el ESP32 a0:dd:6c:0e:fb:4c
con el verificador y cableado a JA1/JA2/GND; `/dev/ttyUSB0` pide `chmod`
al reconectar. Todo subido a `feat/lecturas-firmadas` (992ba88 y la nota
de pendientes).
