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

| Bloque | Celdas | Biestables | Área (µm²) | kGE |
|---|---|---|---|---|
| aes_enc (con entrada `borrar`) | 10.571 | 262 | 116.550 | 16,06 |
| aes_cmac (incluye su AES) | 13.289 | 912 | 169.382 | 23,34 |
| ctr_drbg (incluye su AES) | 19.881 | 2.357 | 276.945 | 38,16 |
| health_tests | 588 | 86 | 9.137 | 1,26 |
| ero_core (contador de 24 bits) | 127 | 28 | 2.371 | 0,33 |
| bit_cdc | 11 | 7 | 408 | 0,06 |
| reset_sync (uno por dominio de reloj) | 3 | 3 | 147 | 0,02 |
| i2c_slave (con guarda de bus colgado) | 435 | 89 | 7.729 | 1,07 |
| trng_capture | 12.526 | 4.140 | 339.386 | 46,76 |
| **motor_top** (anillos como cable, **un solo AES**) | 39.735 | 8.175 | 737.071 | **101,56** |

Filas al día con `results/sintesis_sg13g2.csv` el **27-10-2026 (noche),
motor versión 0x03 con AES compartido** (log íntegro en
`results/sintesis_sg13g2.log`). Historia del día:

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
de IHP pide K_D ≈ 941 000 (`anillo_ihp.md`); el I2C y la captura se
actualizaron tras la guarda de bus colgado y la lectura a cero hasta trozo
completo.

Los anillos no se sintetizan: son el único bloque atado a la tecnología y
en un integrado se diseñan a nivel de transistor.

## Lectura de los números

**El motor digital, tal como está, son unos 55 kGE** (todo menos la
captura: 101,56 − 46,76 = 54,8). Reparto aproximado: el AES compartido
16,1; el autenticador sin su AES 7,3; el generador sin su AES 22,1; tests
de salud 1,3; ERO, cruce y resets 0,4; I2C 1,1; y unos 6,6 en el
secuenciador, los registros del nivel superior y el reparto del AES.
Hasta el 08-10 este documento daba 62 kGE (suma de bloques, dos AES), y
hasta esta tarde 69 (motor entero, dos AES). **El AES es casi la mitad**: hay dos núcleos AES, uno dentro
del autenticador y otro dentro del generador, con 15,8 kGE cada uno. Eso
apunta a las tres optimizaciones del capítulo de integrado, en orden de
rendimiento por esfuerzo:

1. **Un solo AES compartido.** El secuenciador del nivel superior ya
   serializa las órdenes: generador y autenticador nunca trabajan a la
   vez. Compartir el núcleo ahorra ≈ 15,8 kGE (un cuarto del motor) a
   cambio de un árbitro trivial.
2. **S-box compacta.** El AES sintetizado ingenuamente, con 20 S-boxes
   como tablas independientes, ocupa 15,8 kGE; la literatura optimizada
   para área da entre 2,4 kGE (datapath de 8 bits, Moradi et al. 2011,
   226 ciclos por bloque) y unos 5 kGE (datapath de 32 bits). Aquí no
   importa la velocidad, así que un datapath de 32 bits con 4 S-boxes
   compartidas es el punto sensato. Ahorro estimado: 10 kGE por núcleo.
3. **Menos registros en el generador.** El generador guarda 2.355
   biestables: entropía y nonce capturados (384), material de semilla
   (256), salida (256), estado (256) y los temporales de la función de
   derivación. Consumiendo la semilla en flujo y compartiendo temporales
   se pueden quitar del orden de 800 biestables, unos 4 kGE.

Con las tres, el motor digital bajaría a **≈ 20-25 kGE** (los 5 kGE del
nivel superior apenas se reducen), que es el orden de
magnitud que estimaba el estado del arte (13 a 25 kGE) y que **cabe con
mucho margen en el bloque mínimo de una tirada académica** (0,8 mm² en IHP;
20 kGE × 7,26 µm² × 2,35 de crecimiento ≈ 0,34 mm² de núcleo).

**La captura de bits crudos no debe leerse en esta tabla.** Sus 46,7 kGE
son la memoria de 4.096 bits mapeada a biestables porque el flujo no
tiene macros de SRAM. En la FPGA va a un bloque de RAM y no cuesta
lógica; en un integrado sería una SRAM compilada (IHP la ofrece) o, más
razonable, un buffer mucho menor, porque es una vía de test que en
producción se deshabilita.

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
- Sintetizar la variante con un AES compartido y la S-box compacta y
  medir el ahorro en vez de estimarlo.
