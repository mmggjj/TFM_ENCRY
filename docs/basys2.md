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
`G_MEDIDOR = false`: sin frecuencímetro, con `build/basys2_sin_medidor.ucf`
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

## Pendiente

1. Repetibilidad: la misma variante capturada varias veces (y a distintas
   horas) para saber la dispersión de Q entre sesiones; frecuencias de los
   anillos en cada variante (por la duración del flujo a `kd 13`). Después,
   lo que quede del residuo: el ESP32 parado entre lecturas, el reloj de 50
   MHz lejos de los anillos, un modelo con componente común/determinista.
2. Campaña SP 800-90B con `--flujo` a varios divisores (desde `kd 13`) y
   contraste con el modelo cuando haya K\*.
