# Línea base del ESP32 con los estimadores SP 800-90B

Fecha: 2026-09-19. Cierra la parte del ESP32 del objetivo O8 (comparación
numérica con el generador del ESP32) sin esperar a la placa: la mitad del
motor sigue pendiente de O6.

## 1. Qué se mide y con qué

**Datos.** Cinco capturas reales del generador hardware del ESP32-D0WD
(`esp_fill_random`, es decir, lo que ve una aplicación):

| Nombre | Origen | Condición | Bytes | Símbolos binarios |
|---|---|---|---|---|
| condA_rep1 | TFM_RNG, 2026-08-04 | Wi-Fi + ADC activos | 125 000 | 1 000 000 |
| condB_rep1 | TFM_RNG, 2026-08-04 | Wi-Fi activo | 125 000 | 1 000 000 |
| condC_rep1 | TFM_RNG, 2026-08-04 | ADC activo | 125 000 | 1 000 000 |
| condD_rep1 | TFM_RNG, 2026-08-04 | nada activo (RF apagada) | 125 000 | 1 000 000 |
| esp_rf_off_1 | este TFM, 2026-09-19 | nada activo (verificador, `esp N`) | 440 384 | 3 523 072 |
| esp_rf_off_2 | este TFM, 2026-09-19 | nada activo (verificador, `esp N`) | 1 047 296 | 8 378 368 |
| cond{A,B,C,D}_rep2 | firmware del TFM_RNG, 2026-09-19 | las cuatro, ciclo D→C→B→A desde arranque en frío | 125 000 | 1 000 000 |
| cond{A,B,C,D}_rep3 | firmware del TFM_RNG, 2026-09-19 | ídem, segundo arranque en frío | 125 000 | 1 000 000 |

Catorce capturas en total: doce de las condiciones A-D (tres repeticiones
por condición) y dos largas sin radio.

**Repeticiones 2 y 3 (pedidas por Mario el 19-09).** El firmware del
TFM_RNG (`tfm_esp32_rng/firmware`, sin tocar una línea) se compiló con el
ESP-IDF 5.3.2 de Windows en un directorio de build aparte y se flasheó en
el mismo ESP32 del verificador (MAC ec:e3:34:9a:d1:18; la campaña original
de agosto no anotó la MAC de su placa, así que no se puede afirmar que sea
la misma). La captura la hace `analysis/campana_rng.py`, que habla el
protocolo de aquel firmware, guarda el flujo serie íntegro
(`results/esp32_campana_rng/serie_*.log`, no versionado) y numera las
secuencias a partir de la repetición 2 para no pisar las de agosto. Cada
repetición viene de un arranque en frío distinto: en este build el
firmware se queda parado tras el primer ciclo, en la generación de semillas
del *harvester* (nunca llega a imprimir `### SEEDS_BEGIN`), cosa que en
agosto no ocurría; no se ha investigado porque las semillas no intervienen
aquí, y basta con resetear para obtener el ciclo siguiente. Las ocho
secuencias llegaron con longitud y CRC32 correctos y ningún rechazo.
Temperatura del sensor ROM (resolución 0,556 °C, entero en °F): agosto
52,2-52,8 °C; rep2 49,4-50,6 °C; rep3 51,1-51,7 °C. Caudal de generación
medido por el firmware: 5,21 MB/s sin ADC, 2,77 MB/s con ADC (la bomba del
ADC roba CPU), idéntico al de agosto.

Las cuatro primeras son las del TFM anterior del autor (`TFM_RNG`,
`tfm_esp32_rng/results/cond?_rep1.bin`, una repetición por condición). Aquel
trabajo les aplicó Shannon (7,9985 bit/byte), autocorrelación, planitud
espectral, compresión y χ² de bytes, y la batería SP 800-22 (15/15 en las
cuatro condiciones); **nunca** los estimadores de min-entropía de SP 800-90B.
Esa es la corrección que Mario dictó para aquella memoria ("Shannon no es
min-entropía") y que aquí se cuantifica. La quinta es de hoy, con el
verificador de este TFM (`analysis/consola_esp32.py`, orden `esp 32768`);
el límite de 400 s del primer intento cortó la escucha a las 13 762 tramas
de 32 B, todas con CRC32 correcto. Es la misma condición que D en otra
placa del mismo silicio, otro firmware y otro día. La sexta es la captura
completa (`esp 32768`, 32 768 tramas en 262 s ≈ 125 tramas/s): el
analizador recuperó 32 728 tramas con CRC correcto; las 40 restantes
llevaban pegado el mensaje del *task watchdog* del ESP32 (cada 5 s, porque
el bucle de `cmd_esp` no cedía la CPU), y se descartan enteras en vez de
recomponerlas. Corregido en el firmware (`vTaskDelay(1)` cada 32 tramas);
el volumen perdido es el 0,12 %.

**Herramienta.** `SP800-90B_EntropyAssessment` v1.1.8 del NIST (commit
87c104d), compilada sin root en WSL (receta en
`docs/plataforma_y_flujo.md` §8.4). Se ejecutan las dos vías:

- `ea_iid`: pruebas de permutación (§5.1) y χ² (§5.2); si pasan, la
  estimación es la del valor más frecuente (MCV, §6.3.1).
- `ea_non_iid`: los diez estimadores de §6.3 y el mínimo de todos.

Cada captura se evalúa en **modo binario** (un bit por símbolo, la
disposición que la propia norma manda para fuentes binarias) y en **modo
byte** (8 bits por símbolo, la disposición que usaría un evaluador que
tratase la salida del ESP32 como fuente de bytes; en ese modo la
herramienta calcula además `H_bitstring` sobre los bits desempaquetados y
devuelve `min(H_original, 8·H_bitstring)`). La herramienta exige un símbolo
por byte, así que el modo binario parte de los ficheros desempaquetados
(`results/entropia90b/bits/`, MSB primero, derivados y no versionados).

Reproducción: `python analysis/entropia_90b.py` (unos tres minutos para
las veinticuatro ejecuciones; logs y JSON íntegros en
`results/entropia90b/`, resumen en `results/entropia_90b.csv`). Ojo al
leer el CSV: en las filas `iid` el campo `hAssessed` del JSON de la
herramienta vale 8,0 o 1,0 siempre; no es un resultado sino un relleno.
La estimación de la vía IID es el MCV (`hOriginal`), y solo vale si
`passedIidPermutationTests`, `passedChiSquareTests` y
`passedLongestRepeatedSubstringTest` son verdaderos.

## 2. Resolución del instrumento, antes de leer nada

Regla del proyecto: declarar la resolución antes de interpretar una
tendencia. Aquí el instrumento es cada estimador con su cota de confianza
al 99 % (z = 2,576), y el parámetro que fija la resolución es el número de
símbolos N.

**Techo del estimador MCV** (fuente perfectamente uniforme, p̂ = 1/k):
`p_u = p̂ + 2,576·√(p̂(1−p̂)/N)`, H_max = −log2 p_u.

| Disposición | N | p_u | H_max |
|---|---|---|---|
| binario, 1 Mbit (condA-D) | 1 000 000 | 0,501288 | **0,99629 / 1** |
| binario, 3,52 Mbit (rf_off_1) | 3 523 072 | 0,500686 | **0,99802 / 1** |
| binario, 8,38 Mbit (rf_off_2) | 8 378 368 | 0,500445 | **0,99872 / 1** |
| bytes, 125 kB (condA-D) | 125 000 | 0,004361 | 7,841 / 8 (†) |
| bytes, 440 kB (rf_off_1) | 440 384 | 0,004148 | 7,913 / 8 (†) |
| bytes, 1,05 MB (rf_off_2) | 1 047 296 | 0,004063 | 7,943 / 8 (†) |

(†) En modo byte el techo real es más bajo, porque p̂ es el máximo de 256
recuentos multinomiales, no su media: con N = 125 000 la media por símbolo
es 488 y su desviación 22, así que el máximo esperado ronda 543 (los
medidos: 548, 550, 542, 561) y el techo práctico queda en ≈ 7,70 bit. En
modo byte con 125 kB **el MCV no puede distinguir una fuente perfecta de
una con 7,7 bit/byte**: por eso la vía de comparación válida es la binaria
con ≥ 1 Mbit, y por eso el TFM_RNG capturó exactamente 125 000 B por
condición (1 000 000 bits, el mínimo de la norma).

**Sesgo de unos** (σ(p̂) = √(0,25/N) = 5,0·10⁻⁴ para 1 Mbit):

| Captura | p̂(1) | z |
|---|---|---|
| condA | 0,500791 | +1,58 |
| condB | 0,499523 | −0,95 |
| condC | 0,500114 | +0,23 |
| condD | 0,499853 | −0,29 |
| rf_off_1 | 0,500123 | +0,46 |
| rf_off_2 | 0,500178 | +1,03 |

Ninguna captura tiene un sesgo resoluble; el MCV de cada una es, por
tanto, su propio techo menos el término de fluctuación.

## 3. Resultados

### 3.1 Vía IID

| Captura | Binario: permutación / χ² | H_IID (MCV, bit/bit) | Bytes: permutación / χ² | H_IID (MCV, bit/byte) |
|---|---|---|---|---|
| condA_rep1 | pasa / pasa | 0,9940 | pasa / pasa | 7,683 |
| condA_rep2 | pasa / pasa | 0,9954 | pasa / pasa | 7,698 |
| condA_rep3 | pasa / pasa | 0,9962 | pasa / pasa | 7,671 |
| condB_rep1 | pasa / pasa | 0,9949 | pasa / pasa | 7,678 |
| condB_rep2 | pasa / pasa | 0,9957 | pasa / pasa | 7,688 |
| condB_rep3 | pasa / pasa | 0,9934 | pasa / pasa | 7,671 |
| condC_rep1 | pasa / pasa | 0,9960 | pasa / pasa | 7,698 |
| condC_rep2 | pasa / pasa (χ² ajuste p = 0,031) | 0,9946 | pasa / pasa | 7,646 |
| condC_rep3 | pasa / pasa | 0,9928 | pasa / pasa | 7,676 |
| condD_rep1 | pasa / pasa | 0,9959 | pasa / **falla** (ajuste p = 2,4·10⁻⁴) | (vía no-IID: 7,324) |
| condD_rep2 | pasa / pasa (χ² indep. p = 0,041) | 0,9951 | pasa / pasa | 7,663 |
| condD_rep3 | pasa / pasa | 0,9958 | pasa / pasa | 7,698 |
| rf_off_1 | pasa / pasa | 0,9977 | pasa / pasa | 7,823 |
| rf_off_2 | pasa / pasa (χ² indep. p = 0,0086) | 0,9982 | pasa / pasa | 7,893 |

Los catorce MCV binarios están entre 0,0003 y 0,0035 por debajo de su techo
(0,99629 con 1 Mbit; 0,99802 con 3,52 Mbit; 0,99872 con 8,38 Mbit), y el
sesgo de unos que implican no pasa de 2,4 σ (condC_rep3), compatible con
catorce extracciones: **a esta N la salida del ESP32 es indistinguible de
una fuente binaria de entropía plena por la vía IID**. La captura de 1 MB es la única que cumple
el mínimo de 10⁶ símbolos también en modo byte (sin aviso de la
herramienta): su MCV de bytes, 7,893, queda a 0,05 bit del techo nominal
(7,943) y a menos de 0,01 del práctico (máximo esperado de 256 recuentos
con media 4091 y desviación 64: ≈ 4251, medido 4239 → 7,90).

El único fallo es la χ² de bondad de ajuste de condD_rep1 en modo byte
(§5.2.2 de la norma: compara la distribución de símbolos entre diez
subconjuntos consecutivos, o sea, estabilidad en el tiempo): p = 2,4·10⁻⁴
con umbral 10⁻³; la de independencia dio p = 0,042 (pasa). El mismo fichero
pasa ambas χ² en modo binario (p = 0,66 y 0,14) y todas las pruebas de
permutación en los dos modos. **Cerrado con las repeticiones**: condD_rep2
y condD_rep3 pasan esa misma prueba con p = 0,83 y p = 0,96, y las dos
capturas largas sin radio con p = 0,27 y 0,28. En total se han lanzado 56
pruebas χ² (14 capturas × 2 modos × 2 pruebas); la probabilidad de que al
menos una caiga por debajo de 10⁻³ por azar es del 5,4 %, y la que cayó no
se reproduce. Se atribuye al azar, no a la condición "RF apagada": la
advertencia de Espressif (sin RF ni ADC el generador no garantiza
aleatoriedad verdadera) sigue en pie como advertencia, pero estas pruebas
no la ven. De las 56 pruebas, 4 dieron p < 0,05 (esperadas 2,8), sin
concentrarse en ninguna condición.

### 3.2 Vía no-IID, modo binario (bit/bit)

| Estimador (§6.3) | condA | condB | condC | condD | rf_off_1 | rf_off_2 |
|---|---|---|---|---|---|---|
| MCV | 0,9940 | 0,9949 | 0,9960 | 0,9959 | 0,9977 | 0,9982 |
| Collision | 0,9314 | 0,9285 | 0,9244 | 0,9155 | 0,9441 | 0,9583 |
| Markov | 0,9983 | 0,9985 | 0,9992 | 0,9989 | 0,9996 | 0,9996 |
| Compression | **0,8255** | 0,9297 | **0,8199** | 0,9245 | **0,8671** | **0,9108** |
| t-Tuple | 0,9191 | 0,9216 | 0,9398 | 0,9314 | 0,9405 | 0,9350 |
| LRS | 0,9430 | **0,8980** | 0,9656 | 0,9773 | 0,9185 | 0,9985 |
| MultiMCW | 0,9962 | 0,9952 | 0,9987 | 0,9973 | 0,9994 | 0,9986 |
| Lag | 0,9958 | 0,9934 | 0,9953 | 0,9956 | 0,9985 | 0,9985 |
| MultiMMC | 0,9968 | 0,9976 | 1,0000 | 0,9945 | 0,9994 | 0,9988 |
| LZ78Y | 0,9966 | 0,9968 | 0,9980 | 0,9971 | 0,9985 | 0,9989 |
| **H_bitstring = mín.** | **0,8255** | **0,8980** | **0,8199** | **0,9155** | **0,8671** | **0,9108** |

### 3.3 Vía no-IID, modo byte

| Captura | H_original (bit/byte) | estimador que manda | 8·H_bitstring | H evaluada = mín. |
|---|---|---|---|---|
| condA | 7,683 | MCV | 6,604 | 6,604 |
| condB | 7,670 | LRS | 7,184 | 7,184 |
| condC | 7,698 | MCV | 6,559 | 6,559 |
| condD | 7,651 | MCV | 7,324 | 7,324 |
| rf_off_1 | 7,823 | MCV | 6,937 | 6,937 |
| rf_off_2 | 7,388 | t-Tuple (t = 2) | 7,286 | 7,286 |

En rf_off_2 el que manda en bytes ya no es el MCV sino el t-Tuple con
t = 2: con 10⁶ bytes hay 65 536 pares posibles y una media de 15 recuentos
por par, así que el par más frecuente de una fuente uniforme ronda los 32
y el estimador devuelve ≈ 7,4-7,5 bit aunque la fuente sea perfecta. Es el
mismo fenómeno que el techo del MCV, trasladado a la longitud de tupla: la
resolución de cada estimador depende de N frente al tamaño del alfabeto
elevado a la longitud que examina.

### 3.4 Tres repeticiones por condición: ¿hay efecto de la condición?

Tabla completa de las catorce capturas, estimador a estimador, en
`results/entropia_90b_resumen.md` (la genera `analysis/resumen_90b.py`).
Por condición, media ± desviación (poblacional, n = 3) y ANOVA de un
factor, F(3, 8); con once estimadores el umbral de Bonferroni es
p < 0,0045:

| Estimador | A (n=3) | B (n=3) | C (n=3) | D (n=3) | F | p |
|---|---|---|---|---|---|---|
| MCV | 0,9952 ± 0,0009 | 0,9947 ± 0,0010 | 0,9944 ± 0,0013 | 0,9956 ± 0,0003 | 0,57 | 0,647 |
| Collision | 0,9231 ± 0,0171 | 0,9118 ± 0,0126 | 0,9050 ± 0,0142 | 0,9249 ± 0,0136 | 0,86 | 0,501 |
| Markov | 0,9983 ± 0,0004 | 0,9986 ± 0,0008 | 0,9972 ± 0,0016 | 0,9980 ± 0,0007 | 0,71 | 0,573 |
| Compression | 0,8711 ± 0,0450 | 0,8670 ± 0,0454 | 0,8330 ± 0,0243 | 0,8683 ± 0,0403 | 0,41 | 0,750 |
| t-Tuple | 0,9240 ± 0,0053 | 0,9277 ± 0,0086 | 0,9371 ± 0,0051 | 0,9298 ± 0,0061 | 1,45 | 0,299 |
| LRS | 0,9770 ± 0,0241 | 0,9526 ± 0,0400 | 0,9758 ± 0,0109 | 0,9874 ± 0,0071 | 0,74 | 0,559 |
| MultiMCW | 0,9952 ± 0,0007 | 0,9952 ± 0,0002 | 0,9973 ± 0,0011 | 0,9965 ± 0,0007 | 3,66 | 0,063 |
| Lag | 0,9573 ± 0,0568 | 0,9967 ± 0,0023 | 0,9961 ± 0,0007 | 0,9957 ± 0,0012 | 0,93 | 0,468 |
| MultiMMC | 0,9956 ± 0,0009 | 0,9958 ± 0,0014 | 0,9972 ± 0,0033 | 0,9955 ± 0,0008 | 0,38 | 0,767 |
| LZ78Y | 0,9957 ± 0,0007 | 0,9973 ± 0,0009 | 0,9959 ± 0,0019 | 0,9955 ± 0,0013 | 0,81 | 0,522 |
| **mínimo (H no-IID)** | 0,8526 ± 0,0211 | 0,8564 ± 0,0310 | 0,8330 ± 0,0243 | 0,8653 ± 0,0362 | 0,45 | 0,724 |

Ningún estimador separa las condiciones: la p más pequeña es 0,063
(MultiMCW), por encima incluso del 0,05 sin corregir. El mínimo no-IID de
las doce capturas A-D va de 0,812 (condC_rep3) a 0,916 (condD_rep1), media
0,852; en once de las doce lo fija Compression, Collision o LRS, y en una
(condA_rep3) el predictor Lag, con 0,877. Los valores de los predictores
por encima del techo del MCV (hasta 1,0000) no son un error: su cota usa la
misma σ pero su acierto puede quedar por debajo de 0,5, y entonces
devuelven 1 bit. Con n = 3 la desviación tiene poca precisión (un solo
valor atípico, como el Lag 0,877 de condA_rep3, la domina), pero la
conclusión no depende de ella: las medias de condición se cruzan de un
estimador a otro sin ningún orden estable.

## 4. Lectura

1. **Shannon ≠ min-entropía, con números.** El TFM_RNG dio 0,99999 bit/bit
   de Shannon. Las mismas capturas, por la letra de SP 800-90B, valen
   0,993-0,996 bit/bit si se admite IID y **0,81-0,92 bit/bit** (media 0,85
   sobre doce capturas) si no. El orden H_min ≤ H_Shannon se cumple siempre;
   lo que cambia es cuánto crédito se puede dar a cada bit al contar entropía
   para una clave. Con la cifra no-IID más baja (0,81), 256 bits de entropía
   requieren 316 bits de salida; con la Shannon, 256. Es la diferencia entre
   "pasa los tests" y "está acotado".

2. **El mínimo lo fijan casi siempre Compression, Collision o LRS** (13 de
   14 capturas; la otra, el predictor Lag), y nunca Markov ni MCV, que
   quedan por encima de 0,99. Esos tres estimadores tienen un sesgo
   conservador conocido en fuentes casi uniformes: el de compresión (Maurer)
   y el de colisión están calibrados para fuentes con sesgo apreciable y,
   sobre datos de entropía plena, devuelven sistemáticamente ≈ 0,85-0,93
   (Zhu et al., ToSC 2017(3):151-168 [VERIFICADO-META por Crossref]; Kelsey
   et al., CHES 2015 [VERIFICADO], que introdujeron los predictores
   justamente porque los estimadores anteriores fallaban en ese tipo de
   fuente). Prueba interna de que es sesgo y no señal: la dispersión del
   estimador de compresión **dentro de una misma condición** (0,024-0,045
   con tres repeticiones; 0,83-0,92 entre las cinco capturas sin radio) es
   tan grande como la separación entre las medias de las cuatro condiciones
   (0,038), y el ANOVA de §3.4 no encuentra efecto en ningún estimador. Con
   tres repeticiones por condición, **ningún estimador resuelve diferencias
   entre A, B, C y D**.

3. **Lo que esto significa para O8.** La cifra de referencia del ESP32 que
   la memoria debe usar es la no-IID binaria, porque es la que un evaluador
   aplicaría sin conceder IID: **0,81-0,92 bit/bit según captura (media
   0,85), sin dependencia resoluble de la condición**. Frente a ella, el motor ofrece
   una cota derivada del modelo (≥ 0,98 por diseño con Q ≥ 0,2286) y, cuando
   haya placa, la misma batería sobre sus bits crudos. La comparación justa
   es estimador a estimador y a igual N: el sesgo de Compression/Collision
   afectará igual a los bits del ERO. Lo que el ESP32 no puede ofrecer, con
   independencia del número que salga, es la cota: sus bits son la salida
   de un bloque cuya fuente física y post-procesado no están documentados,
   y los estimadores de la norma están pensados para ruido crudo, no para
   salidas ya acondicionadas. Aplicárselos es, literalmente, medir una caja
   negra desde fuera.

4. **Coste de evaluación.** Cincuenta y seis ejecuciones (14 capturas × 2
   vías × 2 modos) en unos seis minutos con la herramienta oficial; el
   cuello no es el cómputo sino la captura: 125 kB por condición tardan
   unos 25 s con el firmware del TFM_RNG (hex a 115200 baudios) y un ciclo
   de cuatro condiciones, unos dos minutos con arranque incluido.

## 5. Pendiente

- El firmware del TFM_RNG recompilado con IDF 5.3.2 se queda parado en el
  *harvester* tras el primer ciclo (no en agosto): sin investigar, no afecta
  a estas capturas. Si se quisieran más repeticiones seguidas sin resetear,
  habría que mirarlo.
- La placa de la campaña de agosto no dejó anotada su MAC: no se puede
  afirmar que rep1 y rep2/rep3 sean del mismo chip, solo del mismo modelo.
- Cuando exista la placa: la misma batería sobre los bits crudos del ERO
  (registro CAPTURA, modo test) a K_D de diseño, y sobre la salida del
  DRBG; contrastar con la cota del modelo (`analysis/ero_model.py`).
