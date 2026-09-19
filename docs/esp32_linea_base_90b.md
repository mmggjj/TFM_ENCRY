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
| condA | pasa / pasa | 0,9940 | pasa / pasa | 7,683 |
| condB | pasa / pasa | 0,9949 | pasa / pasa | 7,678 |
| condC | pasa / pasa | 0,9960 | pasa / pasa | 7,698 |
| condD | pasa / pasa | 0,9959 | pasa / **falla** | (vía no-IID: 7,324) |
| rf_off_1 | pasa / pasa | 0,9977 | pasa / pasa | 7,823 |
| rf_off_2 | pasa / pasa (χ² indep. p = 0,0086) | 0,9982 | pasa / pasa | 7,893 |

Los seis MCV binarios están entre 0,0003 y 0,0023 por debajo de su techo
(0,99629 con 1 Mbit; 0,99802 con 3,52 Mbit; 0,99872 con 8,38 Mbit): **a
esta N la salida del ESP32 es indistinguible de una fuente binaria de
entropía plena por la vía IID**. La captura de 1 MB es la única que cumple
el mínimo de 10⁶ símbolos también en modo byte (sin aviso de la
herramienta): su MCV de bytes, 7,893, queda a 0,05 bit del techo nominal
(7,943) y a menos de 0,01 del práctico (máximo esperado de 256 recuentos
con media 4091 y desviación 64: ≈ 4251, medido 4239 → 7,90).

El único fallo es la χ² de bondad de ajuste de condD en modo byte
(§5.2.2 de la norma: compara la distribución de símbolos entre diez
subconjuntos consecutivos, o sea, estabilidad en el tiempo): p = 2,4·10⁻⁴
con umbral 10⁻³; la de independencia dio p = 0,042 (pasa). El mismo fichero
pasa ambas χ² en modo binario (p = 0,66 y 0,14) y todas las pruebas de
permutación en los dos modos; la captura de hoy en la misma condición, con
3,5 veces más datos, pasa con p = 0,27. Con diez pruebas χ² lanzadas y
α = 10⁻³, un fallo aislado tiene una probabilidad de ≈ 1 % de ser azar.
**Se registra y no se interpreta**: hace falta una segunda repetición de D
con el firmware del TFM_RNG (que ya implementa las cuatro condiciones) para
saber si la condición "RF apagada" tiene una deriva real de distribución.
Es exactamente el caso que la documentación de Espressif avisa (sin RF ni
ADC, el generador no garantiza aleatoriedad verdadera), así que no sería
sorprendente; pero una p aislada no lo demuestra.

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

## 4. Lectura

1. **Shannon ≠ min-entropía, con números.** El TFM_RNG dio 0,99999 bit/bit
   de Shannon. La misma captura, por la letra de SP 800-90B, vale 0,994-0,996
   bit/bit si se admite IID y **0,82-0,92 bit/bit** si no. El orden
   H_min ≤ H_Shannon se cumple siempre; lo que cambia es cuánto crédito se
   puede dar a cada bit al contar entropía para una clave. Con la cifra no-IID
   más baja (0,82), 256 bits de entropía requieren 313 bits de salida; con la
   Shannon, 256. Es la diferencia entre "pasa los tests" y "está acotado".

2. **El mínimo lo fijan siempre Compression, Collision o LRS**, y nunca los
   predictores ni Markov ni MCV, que quedan todos por encima de 0,99. Esos
   tres estimadores tienen un sesgo conservador conocido en fuentes casi
   uniformes: el de compresión (Maurer) y el de colisión están calibrados
   para fuentes con sesgo apreciable y, sobre datos de entropía plena,
   devuelven sistemáticamente ≈ 0,85-0,93 (Zhu et al., ToSC 2017(3):151-168 [VERIFICADO-META por Crossref];
   Kelsey et al., CHES 2015 [VERIFICADO], que introdujeron los predictores
   justamente porque los estimadores anteriores fallaban en ese tipo de
   fuente). Prueba interna de que es sesgo y no señal: la dispersión del
   estimador de compresión entre tres capturas de **la misma condición**
   (condD 0,925, rf_off_1 0,867, rf_off_2 0,911) es tan grande como la que
   hay entre condiciones distintas (0,820-0,930). Con una repetición por
   condición, **ningún estimador resuelve diferencias entre A, B, C y D**.

3. **Lo que esto significa para O8.** La cifra de referencia del ESP32 que
   la memoria debe usar es la no-IID binaria, porque es la que un evaluador
   aplicaría sin conceder IID: **0,82-0,92 bit/bit según captura, sin
   dependencia resoluble de la condición**. Frente a ella, el motor ofrece
   una cota derivada del modelo (≥ 0,98 por diseño con Q ≥ 0,2286) y, cuando
   haya placa, la misma batería sobre sus bits crudos. La comparación justa
   es estimador a estimador y a igual N: el sesgo de Compression/Collision
   afectará igual a los bits del ERO. Lo que el ESP32 no puede ofrecer, con
   independencia del número que salga, es la cota: sus bits son la salida
   de un bloque cuya fuente física y post-procesado no están documentados,
   y los estimadores de la norma están pensados para ruido crudo, no para
   salidas ya acondicionadas. Aplicárselos es, literalmente, medir una caja
   negra desde fuera.

4. **Coste de evaluación.** Veinte ejecuciones en unos dos minutos con la
   herramienta oficial; el cuello no es el cómputo sino la captura (1,1 kB/s
   por la consola del ESP32: 16 min por MB).

## 5. Pendiente

- Segunda repetición de las condiciones A-D con el firmware del TFM_RNG
  (`rng_apply_condition`, orden D→C→B→A, 125 000 B por condición) para
  cerrar la χ² de D y dar dispersión entre repeticiones a cada estimador.
- Cuando exista la placa: la misma batería sobre los bits crudos del ERO
  (registro CAPTURA, modo test) a K_D de diseño, y sobre la salida del
  DRBG; contrastar con la cota del modelo (`analysis/ero_model.py`).
