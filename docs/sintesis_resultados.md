# Síntesis a celdas estándar: primeros resultados (15-09-2026)

**Flujo:** `synth/sintetiza.py`. Yosys 0.69 con el conector de GHDL lee el
mismo VHDL que pasa los bancos de pruebas, sintetiza cada bloque aplanado
y lo mapea sobre la biblioteca abierta **IHP SG13G2** (130 nm,
`sg13g2_stdcell_typ_1p20V_25C.lib`, 1,20 V, 25 °C). La puerta equivalente
se lee del propio liberty: **1 GE = sg13g2_nand2_1 = 7,2576 µm²**.

**Qué es y qué no es este número.** Es **área de celdas tras síntesis
lógica**, sin colocar ni rutar, sin celdas de relleno, sin árbol de reloj
ni reparación de temporización. Es una **cota inferior**. Según los datos
de `via_asic.md`, el área de núcleo acabada es entre 1,7 y 4,6 veces
mayor, y para un AES en esta misma biblioteca el factor publicado es
≈ 2,35. No se ha fijado restricción de reloj: Yosys no la usa para el
área, así que estas cifras no dependen de la frecuencia objetivo.

## Resultados por bloque

Tabla de la síntesis completa del 10-11-2026 (caminos de herramienta
mezclados); la vigente es la del 22-11-2026, más abajo.

| Bloque | Celdas | Biestables | Área (µm²) | kGE |
|---|---|---|---|---|
| aes_enc, una ronda por ciclo (20 S-boxes, con `borrar`) | 10.571 | 262 | 116.550 | 16,06 |
| **aes_enc_32**, ruta de 32 bits (4 S-boxes, 51 ciclos/bloque) | 3.813 | 266 | 48.434 | **6,67** |
| aes_cmac (incluye su aes_enc) | 13.289 | 912 | 169.382 | 23,34 |
| ctr_drbg (incluye su aes_enc) | 19.895 | 2.357 | 277.293 | 38,21 |
| health_tests | 588 | 86 | 9.137 | 1,26 |
| ero_core (contador de 24 bits) | 127 | 28 | 2.371 | 0,33 |
| bit_cdc | 11 | 7 | 408 | 0,06 |
| reset_sync (uno por dominio de reloj) | 3 | 3 | 147 | 0,02 |
| i2c_slave (con guarda de bus colgado) | 435 | 89 | 7.729 | 1,07 |
| trng_capture | 12.526 | 4.140 | 339.386 | 46,76 |
| motor_top_aes11 (anillos como cable, un solo aes_enc; `G_AES_COMPACTO=false`) | 39.879 | 8.175 | 739.061 | 101,83 |
| **motor_top** (anillos como cable, **un solo aes_enc_32**) | 32.954 | 8.179 | 671.576 | **92,53** |

Filas al día con `results/sintesis_sg13g2.csv` el **28-10-2026, motor
versión 0x03 con AES compartido y compacto** (log íntegro en
`results/sintesis_sg13g2.log`). Historia:

- **AES de 32 bits** (`rtl/aes/aes_enc_32.vhd`, 28-10; `G_AES_COMPACTO`,
  por defecto): cuatro S-boxes compartidas entre SubBytes y el SubWord de
  la expansión de clave, un MixColumns, ShiftRows como permutación del
  registro de estado, una columna por ciclo (5 ciclos por ronda, 51 por
  bloque frente a 11). Mismo interfaz que `aes_enc` incluida `borrar`;
  `tb_aes_enc` pasa los dos núcleos por los mismos vectores y exige que
  coincidan. **Núcleo: 6,67 frente a 16,06 kGE (−9,4; la estimación eran
  10: la diferencia son los multiplexores de columna y el registro de
  fase). Motor: 92,53 frente a 101,83 (−9,3), en la misma tanda.** El
  `motor_top_aes11` de esta tanda da 101,83 y no 101,56 porque
  `mix_columns` se reescribió sobre `mix_columna` (misma función, otra
  forma; ABC la mapea 0,27 kGE distinta) y el ctr_drbg suelto subió 0,05
  por lo mismo.

- Versión 0x03 antes de compartir el AES: **115,68 kGE** (49.548 celdas,
  8.435 biestables). Respecto a la 0x02 (114,92): el generador subió
  0,99 kGE por el contador de peticiones que no da la vuelta, la
  comparación de agotado y el borrado; el I2C 0,04 y los tests de salud
  0,02; entraron los dos sincronizadores de reset (0,02 cada uno).
- **AES compartido** (`G_AES_COMPARTIDO`, por defecto): el generador y el
  autenticador nunca cifran a la vez porque el secuenciador los
  serializa, así que el segundo núcleo era área sin uso. Con un solo
  núcleo en `motor_top` repartido por `arranca`: **101,56 kGE, −14,1 kGE
  (−12,2 %)** y 260 biestables menos (los 262 del núcleo que sobra, menos
  los de la lógica de reparto). La estimación del capítulo de integrado
  era ≈ 15,7; la diferencia son el multiplexor de entradas (≈ 0,5 kGE) y
  la entrada `borrar` que la revisión del RTL exigió al núcleo AES y al
  generador para que la zeroización no dejara residuos (aes_enc 15,68 →
  16,06; ctr_drbg +0,35).
- Los bloques sueltos siguen incluyendo su propio AES cuando se sintetizan
  aparte (`G_AES_EXTERNO = false`): sus filas sirven para comparar, no
  suman con la del motor.

Esta tanda se hizo con el segundo camino de `sintetiza.py` (GHDL de
Windows `--synth --out=verilog` y `yowasp-yosys`, el Yosys instalable con
pip, mismo `abc` y misma biblioteca), porque en este PC no hay OSS CAD
Suite; en los bloques sin cambios da entre 0,1 y 0,9 % menos que el
plugin. Cambios anteriores:
el ERO pasó de 20 a 24 bits de contador (0,29 → 0,33 kGE) porque el anillo
de IHP pide K_D ≈ 941 000 (981 000 con la media de ocho realizaciones,
`anillo_ihp.md`); el I2C y la captura se
actualizaron tras la guarda de bus colgado y la lectura a cero hasta trozo
completo.

Los anillos no se sintetizan: son el único bloque atado a la tecnología y
en un integrado se diseñan a nivel de transistor.

## Lectura de los números

**El motor digital, tal como está, son unos 46 kGE** (todo menos la
captura: 92,53 − 46,76 = 45,8). Reparto aproximado: el AES compartido de
32 bits 6,7; el autenticador sin su AES 7,3; el generador sin su AES
22,1; tests de salud 1,3; ERO, cruce y resets 0,4; I2C 1,1; y unos 7 en
el secuenciador, los registros del nivel superior y el reparto del AES.
Hasta el 08-10 este documento daba 62 kGE (suma de bloques, dos AES),
hasta el 27-10 por la tarde 69 (motor entero, dos AES) y hasta la noche
55 (un AES de una ronda compartido). Las tres optimizaciones del
capítulo de integrado, en orden de rendimiento por esfuerzo:

1. **Un solo AES compartido. Hecho (27-10).** El secuenciador del nivel
   superior ya serializa las órdenes: generador y autenticador nunca
   trabajan a la vez. Medido: −14,1 kGE (115,7 → 101,6), frente a los
   15,8 estimados.
2. **S-box compacta. Hecho (28-10).** El AES sintetizado ingenuamente,
   con 20 S-boxes como tablas independientes, ocupa 16 kGE; la literatura
   optimizada para área da entre 2,4 kGE (datapath de 8 bits, Moradi et
   al. 2011, 226 ciclos por bloque) y unos 5 kGE (datapath de 32 bits).
   Medido con `aes_enc_32`: 6,67 kGE el núcleo (−9,4) y −9,3 en el motor.
3. **Menos registros en el generador.** El generador guarda 2.355
   biestables: entropía y nonce capturados (384), material de semilla
   (256), salida (256), estado (256) y los temporales de la función de
   derivación. Consumiendo la semilla en flujo y compartiendo temporales
   se pueden quitar del orden de 800 biestables, unos 4 kGE. Estimado.

Con las dos medidas el motor digital ha pasado de 69 a 46 kGE; con la
tercera quedaría en **≈ 42 kGE**. Es más que los 13-25 kGE que
estimaba el estado del arte para motores de este tipo, y la tabla dice
por qué: el generador sin su AES son 22 kGE (la mitad registros) y el
nivel superior otros 7; llegar al rango publicado exigiría repensar el
almacenamiento del generador, no su cifrador, y eso se deja planteado,
no hecho. A 2,35 de crecimiento, 42 kGE × 7,26 µm² ≈ 0,72 mm² de núcleo:
**sigue cabiendo varias veces en el bloque mínimo de una tirada
académica** (0,8 mm² el mini@sic más pequeño; IHP no limita por bloque).

**La captura de bits crudos no debe leerse en esta tabla.** Sus 46,7 kGE
son la memoria de 4.096 bits mapeada a biestables porque el flujo no
tiene macros de SRAM. En la FPGA va a un bloque de RAM y no cuesta
lógica; en un integrado sería una SRAM compilada (IHP la ofrece) o, más
razonable, un buffer mucho menor, porque es una vía de test que en
producción se deshabilita.

## Muestreo sin habilitación y cortes nuevos (15-11-2026)

`motor_top` pasa a `G_MUESTREO_LIBRE = true` y a los cortes 39/683
(`docs/basys2.md`, "Decisión del 15-11-2026"). Síntesis comparada en una
copia, en la misma tanda y con la misma herramienta (plugin de GHDL), sin
tocar `results/sintesis_sg13g2.csv` (`results/sintesis_muestreo_libre.log`):
`ero_core` 0,336 → 0,332 kGE (139 → 135 celdas: se va el multiplexor de
la habilitación), `health_tests` 1,273 → 1,278, `motor_top` 93,18 →
92,82 kGE con los mismos 8 164 biestables. El −0,4 % del motor está en el
orden de lo que abc mueve solo por los nombres (0,2 %, 14-11): **sin
cambio de área medible**. Las filas del CSV y del capítulo 6 siguen siendo
las de antes hasta la próxima síntesis completa (92,53 con el otro camino
de herramienta).

## Semilla de 512 bits y cortes 51/766 (16-11-2026)

H declarada 0,60 y semilla de 384 + 128 bits (`docs/basys2.md`, "Decisión
del 16-11-2026"). Síntesis comparada con el plugin de GHDL, copia de HEAD
573d076 frente al árbol de trabajo, en la misma tanda, sin tocar el CSV
(`results/sintesis_semilla512.log`):

| Bloque | Antes (kGE, FF) | Después (kGE, FF) |
|---|---|---|
| `ctr_drbg` | 38,09, 2 355 | 39,62, 2 483 |
| `motor_top` | 92,82, 8 164 | **95,13**, 8 420 |
| `motor_top_aes11` | 102,32, 8 161 | 104,73, 8 417 |
| `motor_top_flujo` | 116,77, 10 270 | 119,01, 10 526 |

+256 biestables, los esperados (`semilla` y `ent_r` del DRBG, 128 cada
uno), y +2,3 kGE en el motor (+2,5 %): este cambio sí es medible. El CSV y
la tabla del capítulo 6 siguen con la síntesis completa anterior; el
capítulo lo dice en un párrafo (EN y ES).

## Síntesis completa del 22-11-2026

Todos los bloques en una tanda, con el plugin de GHDL (OSS CAD Suite, Linux),
sobre el RTL de hoy: ro1 de 11 y ro2 de 13 etapas, preescalador ÷16,
`G_KD_MIN`/`G_KD_RESET`/`G_KD_MAX` 25/25/26, semilla de 512, cortes 51/766,
`health_tests` sin restas y `CFG_KD` fuera de rango rechazado
(`results/sintesis_22_11.log`; **`results/sintesis_sg13g2.csv` reescrito
entero**; el anterior era del 10-11 con caminos de herramienta mezclados).

| Bloque | Celdas | Biestables | Área (µm²) | kGE | 10-11 (kGE) |
|---|---|---|---|---|---|
| aes_enc | 10 549 | 262 | 114 677 | 15,80 | 16,06 |
| aes_enc_32 | 3 771 | 265 | 48 175 | 6,64 | 6,67 |
| aes_cmac | 13 239 | 909 | 169 426 | 23,35 | 23,34 |
| ctr_drbg | 20 614 | 2 483 | 287 513 | 39,62 | 38,21 |
| health_tests | 530 | 86 | 8 487 | 1,17 | 1,26 |
| ero_core | 139 | 28 | 2 442 | 0,34 | 0,33 |
| bit_cdc | 11 | 7 | 408 | 0,06 | 0,06 |
| reset_sync | 3 | 3 | 147 | 0,02 | 0,02 |
| trng_capture | 12 592 | 4 140 | 339 698 | 46,81 | 46,76 |
| flujo_crudo | 6 387 | 2 103 | 171 786 | 23,67 | 23,67 |
| i2c_slave | 431 | 85 | 7 408 | 1,02 | 1,07 |
| **motor_top** | 34 179 | 8 425 | 692 782 | **95,46** | 92,53 |
| motor_top_aes11 | 42 010 | 8 422 | 763 818 | 105,24 | 101,83 |
| motor_top_flujo | 41 112 | 10 531 | 865 617 | 119,27 | 116,63 |
| motor_top_antes1911 | 34 509 | 8 420 | 693 831 | 95,60 | — |

Lectura:
- **El rechazo de `CFG_KD` fuera de rango no cuesta área medible:**
  `motor_top` 95,53 kGE el 19-11 (`results/sintesis_19_11_ro2_13.log`,
  misma herramienta) → 95,46 hoy, mismos 8 425 biestables (−0,1 %, dentro
  del 0,2 % que abc mueve por los nombres). `motor_top_antes1911` (los
  genéricos de antes del 19-11 sobre el RTL de hoy) sube de 95,09 a 95,60
  (+0,5 %): también cerca del ruido de abc, sin cambio de biestables.
- Frente al CSV del 10-11 el motor sube +2,9 kGE: la semilla de 512 (+2,3,
  16-11, `ctr_drbg` +126 biestables), ro2 de 13 etapas y el preescalador
  (+0,5 %, 19-11) y el cambio de camino de herramienta; `health_tests`
  baja un 7 % por las comparaciones sin restas del APT (17-11).
- Sigue siendo área de celdas sin rutar: cota inferior.

## Comprobación de coherencia

Las diferencias entre bloques cuadran con lo que contienen: el
autenticador añade al AES 647 biestables (subclaves K1 y K2, estado del
encadenado, clave) y 7,6 kGE; el generador añade 2.093 biestables y
21 kGE, de los que la mitad son los propios registros. Antes de aplanar
la jerarquía, el informe devolvía para los tres el área del submódulo AES
solo, y así se detectó: si el autenticador pesara lo mismo que el AES
desnudo, algo estaba mal en la lectura del informe, no en el diseño.

## Qué falta para el capítulo

- Repetir con `abc -liberty` restringido a una frecuencia objetivo y con
  `report_timing` en OpenROAD para dar frecuencia máxima.
- Colocar y rutar el motor completo con OpenROAD-flow-scripts sobre la
  misma biblioteca, y comparar el área de núcleo real con el factor 2,35
  publicado para el AES.
- Sintetizar la variante del generador con menos registros y medir el
  ahorro en vez de estimarlo (las otras dos optimizaciones ya están
  medidas).
