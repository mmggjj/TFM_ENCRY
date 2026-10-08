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
| aes_enc | 10.439 | 262 | 114.771 | 15,81 |
| aes_cmac (incluye su AES) | 13.210 | 909 | 169.766 | 23,39 |
| ctr_drbg (incluye su AES) | 17.953 | 2.355 | 267.262 | 36,83 |
| health_tests | 568 | 85 | 8.986 | 1,24 |
| ero_core (contador de 24 bits) | 132 | 28 | 2.397 | 0,33 |
| bit_cdc | 11 | 7 | 408 | 0,06 |
| i2c_slave (con guarda de bus colgado) | 431 | 85 | 7.408 | 1,02 |
| trng_capture | 12.592 | 4.140 | 339.698 | 46,81 |
| **motor_top** (anillos como cable, `synth/ring_osc_stub.vhd`) | 47.252 | 8.409 | 834.033 | **114,92** |

Filas al día con `results/sintesis_sg13g2.csv` el 08-10-2026. Cambios
respecto a la primera versión de esta tabla: el ERO pasó de 20 a 24 bits
de contador (0,29 → 0,33 kGE; el motor entero, 114,73 → 114,92) porque el
anillo de IHP pide K_D ≈ 941 000 (`anillo_ihp.md`); el I2C y la captura
no se habían actualizado tras la guarda de bus colgado y la lectura a cero
hasta trozo completo.

Los anillos no se sintetizan: son el único bloque atado a la tecnología y
en un integrado se diseñan a nivel de transistor.

## Lectura de los números

**El motor digital, tal como está, son unos 68 kGE** (todo menos la
captura): 62,9 en los bloques de la tabla y 5,2 en el secuenciador y los
registros del nivel superior, que solo aparecen al sintetizar el motor
entero (114,92 − 46,81). Hasta el 08-10 este documento daba 62 kGE, que
era solo la suma de bloques. **El AES es casi la mitad**: hay dos núcleos AES, uno dentro
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
