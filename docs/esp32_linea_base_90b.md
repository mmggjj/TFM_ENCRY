# Línea base del ESP32 con los estimadores SP 800-90B

Fecha: 2026-09-19. Cierra la parte del ESP32 del objetivo O8 (comparación
numérica con el generador del ESP32) sin esperar a la placa: la mitad del
motor sigue pendiente de O6.

## 1. Qué se mide y con qué

**Datos.** Cinco capturas reales del generador hardware del ESP32-D0WD
(`esp_fill_random`, es decir, lo que ve una aplicación):

| Nombre | Origen | Condición | Bytes | Símbolos binarios |
|---|---|---|---|---|
| condA_rep1 | primera campaña, 2026-08-04 | Wi-Fi + ADC activos | 125 000 | 1 000 000 |
| condB_rep1 | primera campaña, 2026-08-04 | Wi-Fi activo | 125 000 | 1 000 000 |
| condC_rep1 | primera campaña, 2026-08-04 | ADC activo | 125 000 | 1 000 000 |
| condD_rep1 | primera campaña, 2026-08-04 | nada activo (RF apagada) | 125 000 | 1 000 000 |
| esp_rf_off_1 | este TFM, 2026-09-19 | nada activo (verificador, `esp N`) | 440 384 | 3 523 072 |
| esp_rf_off_2 | este TFM, 2026-09-19 | nada activo (verificador, `esp N`) | 1 047 296 | 8 378 368 |
| cond{A,B,C,D}_rep2 | `firmware/esp32_rng`, 2026-09-19 | las cuatro, ciclo D→C→B→A desde arranque en frío | 125 000 | 1 000 000 |
| cond{A,B,C,D}_rep3 | `firmware/esp32_rng`, 2026-09-19 | ídem, segundo arranque en frío | 125 000 | 1 000 000 |
| fb4c_cond{A,B,C,D}_rep{1,2,3} | `firmware/esp32_rng`, 2026-10-12, chip de MAC a0:dd:6c:0e:fb:4c | las cuatro, tres arranques en frío | 125 000 | 1 000 000 |
| 0928_cond{A,B,C,D}_rep{1,2,3} | `firmware/esp32_rng`, 2026-10-20, chip de MAC f8:b3:b7:2a:09:28 | las cuatro, tres arranques en frío | 125 000 | 1 000 000 |

Treinta y ocho capturas en total: treinta y seis de las condiciones A-D
(nueve por condición) y dos largas sin radio, de tres chips ESP32-D0WD-V3
revisión 3.1 identificados por su MAC:

| Chip (MAC) | Capturas |
|---|---|
| ec:e3:34:9a:d1:18 | rep1 (agosto), rep2 y rep3 de A-D, y las dos largas sin radio |
| a0:dd:6c:0e:fb:4c | fb4c_* (tres repeticiones de A-D) |
| f8:b3:b7:2a:09:28 | 0928_* (tres repeticiones de A-D) |

La placa de agosto es el chip ec:e3:34:9a:d1:18: el firmware imprime la MAC
al arrancar y quedó anotada con los resultados de aquella campaña; lo que no
tenía era columna de MAC en su `capture_log.csv`. Hasta el 13-10-2026 este
documento la trataba como "sin anotar" y la dejaba aparte.

El mismo binario del firmware (recompilado sin cambios) y el mismo script
de captura en los tres chips; en a0:dd:6c:0e:fb:4c y f8:b3:b7:2a:09:28 es
literalmente el mismo fichero (`tfm_esp32_rng.bin`, SHA-256 05548531…,
del mismo directorio de build). Los datos de cada chip se guardan aparte
(`results/esp32_campana_rng/`, `…/mac_a0dd6c0efb4c/` y
`…/mac_f8b3b72a0928/`). El sensor ROM de temperatura marca ≈ 50 °C en el
primero, ≈ 63 °C en el segundo y 43-45 °C en el tercero (resolución
0,556 °C; dato orientativo, no se usa).

**Tercer chip (2026-10-20).** Es una placa del autor de otro uso (con
periféricos conectados que el firmware no usa); su flash se
copió entera antes y se restaura al terminar. El enlace serie de esta
placa estropea a veces lo que llega al PC: en la campaña, tres bloques de
125 000 B no cuadraron (una línea cortada; dos con 124 890 y 127 114 B), y
el CRC32 los rechazó todos. El primero destapó un fallo de
`analysis/campana_rng.py`: ante una línea que no era hexadecimal el script
se caía en vez de rechazar el bloque (corregido). Aquella primera
repetición se quedó a medias (D y C) y se apartó entera, con su log, a
`mac_f8b3b72a0928/incompletas/`; se repitió completa después de las otras
dos (orden real: rep2, rep3, rep1). En rep1 y rep3 el bloque A rechazado se
tomó del segundo ciclo del mismo arranque (a partir de los ≈ 206 y 227 s),
no del primero; D, C y B, del primer ciclo como siempre. Que el firmware
llegue al segundo ciclo corrige lo que se decía más abajo: no se queda
parado tras el primero; imprime las semillas del *harvester* y sigue. En
los otros chips el script dejaba de escuchar en cuanto tenía las cuatro
condiciones, y por eso no se veía.

**Repeticiones 2 y 3 (pedidas por Mario el 19-09).** El firmware de la
primera campaña (`firmware/esp32_rng`, sin tocar una línea) se compiló con el
ESP-IDF 5.3.2 de Windows en un directorio de build aparte y se flasheó en
el mismo ESP32 del verificador (MAC ec:e3:34:9a:d1:18, el mismo chip de la
campaña de agosto). La captura la hace `analysis/campana_rng.py`, que habla el
protocolo de aquel firmware, guarda el flujo serie íntegro
(`results/esp32_campana_rng/serie_*.log`, no versionado) y numera las
secuencias a partir de la repetición 2 para no pisar las de agosto. Cada
repetición viene de un arranque en frío distinto. (Aquí se decía que en
este build el firmware se quedaba parado tras el primer ciclo, en la
generación de semillas del *harvester*, porque `### SEEDS_BEGIN` no
llegaba a salir. El tercer chip muestra que no: las semillas tardan unos
dos minutos y luego empieza el segundo ciclo; el script de captura ya había
dejado de escuchar.) Las ocho
secuencias llegaron con longitud y CRC32 correctos y ningún rechazo.
Temperatura del sensor ROM (resolución 0,556 °C, entero en °F): agosto
52,2-52,8 °C; rep2 49,4-50,6 °C; rep3 51,1-51,7 °C. Caudal de generación
medido por el firmware: 5,21 MB/s sin ADC, 2,77 MB/s con ADC (la bomba del
ADC roba CPU), idéntico al de agosto.

Las cuatro primeras son las de la primera campaña de este trabajo
(`results/esp32_rng_agosto/cond?_rep1.bin`, una repetición por condición). Aquella
campaña les aplicó Shannon (7,9985 bit/byte), autocorrelación, planitud
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
con ≥ 1 Mbit, y por eso la primera campaña capturó exactamente 125 000 B por
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
| fb4c_condA_rep1 | pasa / pasa | 0,9962 | pasa / pasa (χ² indep. p = 0,043) | 7,673 |
| fb4c_condA_rep2 | pasa / pasa | 0,9959 | pasa / pasa | 7,701 |
| fb4c_condA_rep3 | pasa / pasa | 0,9945 | **falla** (numIncreasesDecreases) / pasa | (vía no-IID: 6,497) |
| fb4c_condB_rep1 | pasa / pasa | 0,9957 | pasa / **falla** (indep. p = 6,0·10⁻⁴) | (vía no-IID: 6,966) |
| fb4c_condB_rep2 | pasa / pasa | 0,9951 | pasa / pasa | 7,688 |
| fb4c_condB_rep3 | pasa / pasa | 0,9956 | pasa / pasa (χ² indep. p = 0,019) | 7,683 |
| fb4c_condC_rep1 | pasa / pasa | 0,9956 | pasa / pasa (χ² indep. p = 0,0034) | 7,673 |
| fb4c_condC_rep2 | pasa / pasa (χ² ajuste p = 0,043) | 0,9959 | pasa / pasa (χ² indep. p = 0,024) | 7,673 |
| fb4c_condC_rep3 | pasa / pasa | 0,9962 | pasa / pasa | 7,688 |
| fb4c_condD_rep1 | pasa / pasa (χ² ajuste p = 0,0021) | 0,9957 | pasa / pasa | 7,703 |
| fb4c_condD_rep2 | **falla** (numDirectionalRuns) / pasa | (vía no-IID: 0,8382) | pasa / pasa (χ² indep. p = 0,011) | 7,706 |
| fb4c_condD_rep3 | pasa / pasa | 0,9956 | pasa / pasa | 7,706 |
| 0928_condA_rep1 | pasa / pasa | 0,9932 | pasa / pasa (χ² indep. p = 0,016) | 7,691 |
| 0928_condA_rep2 | pasa / pasa | 0,9954 | pasa / pasa | 7,676 |
| 0928_condA_rep3 | pasa / pasa | 0,9943 | pasa / pasa | 7,671 |
| 0928_condB_rep1 | pasa / pasa | 0,9942 | pasa / pasa (χ² indep. p = 0,0016) | 7,661 |
| 0928_condB_rep2 | pasa / pasa | 0,9956 | pasa / **falla** (indep. p = 8,5·10⁻⁴) | (vía no-IID: 6,471) |
| 0928_condB_rep3 | pasa / pasa | 0,9962 | pasa / pasa | 7,706 |
| 0928_condC_rep1 | pasa / pasa | 0,9951 | pasa / pasa | 7,673 |
| 0928_condC_rep2 | pasa / pasa | 0,9926 | pasa / pasa | 7,683 |
| 0928_condC_rep3 | pasa / pasa (χ² indep. p = 0,011) | 0,9944 | pasa / pasa | 7,654 |
| 0928_condD_rep1 | pasa / pasa | 0,9953 | pasa / pasa (χ² indep. p = 0,028) | 7,691 |
| 0928_condD_rep2 | pasa / pasa | 0,9948 | pasa / pasa | 7,683 |
| 0928_condD_rep3 | pasa / pasa | 0,9954 | pasa / pasa | 7,703 |

Los treinta y ocho MCV binarios están entre 0,0001 y 0,0037 por debajo de
su techo (0,99629 con 1 Mbit; 0,99802 con 3,52 Mbit; 0,99872 con 8,38
Mbit), y el desequilibrio entre unos y ceros que implican no pasa de
2,6 σ (0928_condC_rep2; le sigue condC_rep3 con 2,4 σ), compatible con
treinta y ocho extracciones (el máximo de 38 normales pasa de 2,57 en un
32 % de los casos): **a esta N la salida del ESP32 es
indistinguible de una fuente binaria de entropía plena por la vía IID**
(los fallos sueltos se leen con la calibración de §3.1.1). La captura de 1 MB es la única que cumple
el mínimo de 10⁶ símbolos también en modo byte (sin aviso de la
herramienta): su MCV de bytes, 7,893, queda a 0,05 bit del techo nominal
(7,943) y a menos de 0,01 del práctico (máximo esperado de 256 recuentos
con media 4091 y desviación 64: ≈ 4251, medido 4239 → 7,90).

#### 3.1.1 Fallos sueltos y cuánto fallan estas pruebas con datos buenos

En las 76 ejecuciones IID (38 capturas × 2 modos) hay cinco fallos, cada
uno en una sola prueba y nunca en los dos modos del mismo fichero:

| Captura | Modo | Prueba que falla | Lo demás |
|---|---|---|---|
| condD_rep1 | byte | χ² de ajuste, p = 2,4·10⁻⁴ (§5.2.2: estabilidad de la distribución entre diez trozos) | independencia p = 0,042; pasa todo en bits |
| fb4c_condA_rep3 | byte | permutación, numIncreasesDecreases | pasa todo en bits |
| fb4c_condB_rep1 | byte | χ² de independencia, p = 6,0·10⁻⁴ | ajuste p = 0,93; pasa todo en bits |
| fb4c_condD_rep2 | bit | permutación, numDirectionalRuns | pasa todo en bytes |
| 0928_condB_rep2 | byte | χ² de independencia, p = 8,5·10⁻⁴ | ajuste p = 0,70; pasa todo en bits |

A efectos de la norma basta un fallo para no conceder IID a esa captura;
como la cifra que se usa es la no-IID, la conclusión práctica no cambia.
La pregunta es si cinco fallos son muchos, y eso exige saber cuánto fallan
estas pruebas con datos buenos **del mismo tamaño**. Se midió con datos de
`os.urandom` (generador del sistema, criptográfico):

| Prueba | Referencia | Fallos con datos buenos | ESP32 (38 capturas) | P(≥ lo del ESP32) |
|---|---|---|---|---|
| permutación, bytes | 1000 ficheros de 125 000 B, `ea_iid` | 1,9 % | 1 | 0,52 |
| χ² (las dos), bytes | 1000 ficheros de 125 000 B, `ea_iid` | 2,4 % | 3 | 0,063 |
| permutación, bits | 200 ficheros de 10⁶ bits, `ea_iid` | 2,5 % | 1 | 0,62 |
| χ² (las dos), bits | 5000 ficheros de 10⁶ bits, reimplementación (con `ea_iid`, 0 de 200) | ≈ 0,34 % | 0 | — |
| LRS, los dos modos | los mismos | 0 | 0 | — |

(`analysis/calibra_iid.py` para `ea_iid`, `analysis/chi2_90b.py` para la
reimplementación; los ficheros de referencia no se suben, los resúmenes
están en `results/chi2_90b/`.)

**La χ² de independencia en modo byte está mal calibrada a este tamaño.**
Cuenta parejas de bytes no solapadas: 62 500 parejas en 65 536 casillas,
menos de una por casilla. La herramienta agrupa casillas hasta esperar 5
por grupo, pero la p que sale no es uniforme. Para verlo se reescribieron
las dos χ² en `analysis/chi2_90b.py`, que reproduce las 52 p de la
herramienta al sexto decimal, y se pasaron por 5000 ficheros buenos: la
mediana de p es 0,175 (debería ser 0,5), cae por debajo de 0,05 en el
24,4 % de los ficheros y por debajo del umbral de 10⁻³ en el 1,7 %,
diecisiete veces lo nominal. Las otras tres χ² sí están bien calibradas
(0,04-0,22 % por debajo de 10⁻³; contraste de Kolmogorov-Smirnov frente a
la uniforme p ≥ 0,18). Con 1 MB o más el defecto desaparece (mediana
0,49-0,52).

**Comprobación del chip a0:dd:6c:0e:fb:4c.** Esa prueba le dio p < 0,05
en 6 de 12 capturas (esperadas 2,9 con la referencia; Mann-Whitney frente a
ella p = 0,03, una de doce comparaciones, no significativa con corrección).
Para salir de dudas se juntaron las capturas A-D de cada chip, donde la
prueba ya está calibrada y tiene más potencia, y se miraron las parejas de
bytes alineadas con la palabra de 32 bits (desfase 0) y desplazadas un byte
(desfase 1), con p empírico frente a 1000 ficheros buenos del mismo tamaño:

| Chip | Datos | p, desfase 0 | p, desfase 1 |
|---|---|---|---|
| a0:dd:6c:0e:fb:4c | 12 capturas, 1,5 MB | 0,84 | 0,94 |
| ec:e3:34:9a:d1:18 | 12 capturas, 1,5 MB | 0,53 | 0,66 |
| f8:b3:b7:2a:09:28 | 12 capturas, 1,5 MB | 0,42 | 0,22 |

(Rehecho el 20-10-2026 con el tercer chip; `results/chi2_90b/agrupado_1000.csv`
y su log. Los p empíricos varían en la segunda cifra de una ejecución a
otra porque la referencia se genera de nuevo cada vez: el 13-10 salieron
0,81/0,96 y 0,53/0,68 para los dos primeros.)

No hay dependencia entre bytes vecinos en ningún chip: los p bajos de las
capturas sueltas eran el defecto de la prueba más el azar.

**Tercer chip, las cuatro χ² frente a la referencia** (`analysis/chi2_90b.py
--compara`, 5000 ficheros buenos de 125 000 B). En la χ² de independencia
en bytes, el tercer chip queda donde la referencia: p < 0,05 en 4 de 12
(esperadas 2,9), una por debajo de 10⁻³ (la de 0928_condB_rep2; esperadas
0,20, P(≥ 1) = 0,19), Mann-Whitney p = 0,27. Con los 36 ficheros A-D de los
tres chips: 11 por debajo de 0,05 (esperadas 8,8) y 2 por debajo de 10⁻³
(esperadas 0,61, P(≥ 2) = 0,13). Lo único que llama la atención es la χ²
de ajuste en bytes de este chip (§5.2.2, si la distribución de bytes se
mantiene entre diez trozos de la captura): ninguna de sus 12 p baja de
0,05 (la menor, 0,069), pero su mediana es 0,21 frente a 0,51 de la
referencia. Mann-Whitney unilateral p = 0,00309; son 16 comparaciones
(4 pruebas × los 3 chips y el conjunto) y el umbral de Bonferroni es
0,05/16 = 0,00313, así que queda justo por debajo; bilateral, 0,006, por
encima. En los otros dos chips esa misma prueba está en su sitio
(medianas 0,73 y 0,68). Es una señal en el límite, de un chip, en una
prueba que ninguna captura suelta falla: no basta para afirmar un efecto.
**Segunda tanda (21-10-2026).** Se hizo otra tanda de tres ciclos en el
mismo chip (`mac_f8b3b72a0928/tanda2/`, nombres `0928t2_*`, fuera de los
ANOVA para no desequilibrarlos; mismo fuente, binario recompilado, SHA-256
97b0cc2d…). Su χ² de ajuste en bytes da mediana 0,34 y Mann-Whitney
p = 0,13; la de independencia, mediana 0,17, 4 de 12 bajo 0,05 y ninguna
bajo 10⁻³ (p = 0,39). **La señal no se repite: era azar.** En la vía IID
de la tanda fallan dos de 24 ejecuciones (0928t2_condB_rep3 en bits y
0928t2_condC_rep1 en bytes), dentro de lo que dan los datos buenos; su
mínimo no-IID va de 0,817 a 0,910.

**SP 800-22 de segundo nivel** (`analysis/nist_segundo_nivel.py`,
`results/nist_segundo_nivel/resumen.md`): 59 secuencias de 10⁶ bits (las
48 A-D de los tres chips con la tanda 2 y 11 trozos de las dos largas), 48
estadísticos (cada plantilla, cada estado de las excursiones y los dos
sentidos de las sumas acumuladas por separado). Todos cumplen la proporción
(≥ 0,951; 0,939 en las excursiones, que se aplican a 34 secuencias) y la
uniformidad (P-value_T mínimo 0,0075 frente a 10⁻⁴); 18 de 2182 p bajo
0,01, esperadas 21,8.

**El fallo de ajuste de condD_rep1** es el más raro de los cuatro: esa
prueba falla con datos buenos en el 0,04 % de los casos, y que caiga al
menos una de 26 por azar tiene una probabilidad de ≈ 1 %. No se repite:
las otras cinco capturas D la pasan (p = 0,32-0,96), y las dos largas sin
radio también (0,27 y 0,28). Se atribuye al azar, no a la condición "RF
apagada": la advertencia de Espressif (sin RF ni ADC el generador no
garantiza aleatoriedad verdadera) sigue en pie como advertencia, pero estas
pruebas no la ven.

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

### 3.4 Nueve repeticiones por condición: ¿hay efecto de la condición?

Tabla completa de las treinta y ocho capturas, estimador a estimador, en
`results/entropia_90b_resumen.md` (la genera `analysis/resumen_90b.py`).
Por condición, media ± desviación (poblacional, n = 9, tres por chip) y
ANOVA de un factor, F(3, 32); con once
estimadores el umbral de Bonferroni es p < 0,0045:

| Estimador | A (n=9) | B (n=9) | C (n=9) | D (n=9) | F | p |
|---|---|---|---|---|---|---|
| MCV | 0,9950 ± 0,0010 | 0,9952 ± 0,0008 | 0,9948 ± 0,0013 | 0,9955 ± 0,0004 | 0,83 | 0,488 |
| Collision | 0,9159 ± 0,0187 | 0,9260 ± 0,0209 | 0,9088 ± 0,0309 | 0,9084 ± 0,0169 | 1,07 | 0,376 |
| Markov | 0,9981 ± 0,0008 | 0,9982 ± 0,0007 | 0,9974 ± 0,0017 | 0,9984 ± 0,0012 | 1,06 | 0,381 |
| Compression | 0,8501 ± 0,0398 | 0,8600 ± 0,0390 | 0,8474 ± 0,0306 | 0,8542 ± 0,0267 | 0,20 | 0,893 |
| t-Tuple | 0,9302 ± 0,0093 | 0,9265 ± 0,0088 | 0,9338 ± 0,0092 | 0,9303 ± 0,0096 | 0,85 | 0,478 |
| LRS | 0,9733 ± 0,0248 | 0,9665 ± 0,0381 | 0,9732 ± 0,0196 | 0,9846 ± 0,0162 | 0,66 | 0,580 |
| MultiMCW | 0,9957 ± 0,0017 | 0,9961 ± 0,0012 | 0,9974 ± 0,0013 | 0,9970 ± 0,0009 | 3,00 | 0,045 |
| Lag | 0,9835 ± 0,0377 | 0,9966 ± 0,0017 | 0,9964 ± 0,0009 | 0,9959 ± 0,0010 | 0,93 | 0,438 |
| MultiMMC | 0,9943 ± 0,0042 | 0,9965 ± 0,0016 | 0,9964 ± 0,0024 | 0,9963 ± 0,0015 | 1,24 | 0,310 |
| LZ78Y | 0,9823 ± 0,0372 | 0,9962 ± 0,0013 | 0,9957 ± 0,0020 | 0,9966 ± 0,0013 | 1,11 | 0,360 |
| **mínimo (H no-IID)** | 0,8428 ± 0,0273 | 0,8565 ± 0,0336 | 0,8474 ± 0,0306 | 0,8532 ± 0,0241 | 0,35 | 0,788 |

Ningún estimador separa las condiciones al nivel corregido: la p más
pequeña es 0,045 (MultiMCW), que con once pruebas es lo esperable por azar
(0,55 de media por debajo de 0,05), y el orden de sus medias (A < B < D < C)
no es el de ninguna hipótesis física. Con las dieciocho capturas de antes
la menor era 0,083, del mismo estimador. El mínimo no-IID de las treinta y
seis capturas A-D va de 0,809 a 0,918, media 0,850; lo fija Compression,
Collision o LRS salvo en una captura (condA_rep3, el predictor Lag con
0,877), y en las veinticuatro de los chips a0:dd:6c:0e:fb:4c y
f8:b3:b7:2a:09:28, Compression salvo una (0928_condA_rep1, Collision con
0,893). Los extremos son los dos del tercer chip: 0,809 en
0928_condB_rep2 y 0,918 en 0928_condC_rep2. Los valores de los predictores
por encima del techo del MCV (hasta 1,0000) no son un error: su cota usa la
misma σ pero su acierto puede quedar por debajo de 0,5, y entonces
devuelven 1 bit. Con n = 9 la desviación sigue teniendo poca precisión (un
solo valor atípico, como el Lag 0,877 de condA_rep3 o el LZ78Y 0,877 de
0928_condA_rep2, la domina), pero la conclusión no depende de ella: las
medias de condición se cruzan de un estimador a otro sin ningún orden
estable.

### 3.5 Tres chips: ¿se distinguen?

Capturas A-D con las condiciones agrupadas (no hay efecto de condición).
ANOVA de un factor entre los tres chips, doce capturas de cada uno,
F(2, 33):

| Estimador | ec:e3:34:9a:d1:18 (n=12) | a0:dd:6c:0e:fb:4c (n=12) | f8:b3:b7:2a:09:28 (n=12) | F | p |
|---|---|---|---|---|---|
| MCV | 0,9950 ± 0,0010 | 0,9957 ± 0,0005 | 0,9947 ± 0,0010 | 3,83 | 0,032 |
| Collision | 0,9162 ± 0,0166 | 0,9089 ± 0,0239 | 0,9193 ± 0,0277 | 0,59 | 0,561 |
| Markov | 0,9980 ± 0,0011 | 0,9986 ± 0,0006 | 0,9975 ± 0,0015 | 2,82 | 0,074 |
| Compression | 0,8598 ± 0,0427 | 0,8471 ± 0,0169 | 0,8518 ± 0,0380 | 0,38 | 0,684 |
| t-Tuple | 0,9296 ± 0,0080 | 0,9304 ± 0,0103 | 0,9305 ± 0,0103 | 0,03 | 0,973 |
| LRS | 0,9732 ± 0,0274 | 0,9718 ± 0,0302 | 0,9782 ± 0,0218 | 0,18 | 0,839 |
| MultiMCW | 0,9961 ± 0,0012 | 0,9969 ± 0,0016 | 0,9967 ± 0,0015 | 0,96 | 0,394 |
| Lag | 0,9864 ± 0,0330 | 0,9964 ± 0,0013 | 0,9965 ± 0,0012 | 1,00 | 0,377 |
| MultiMMC | 0,9960 ± 0,0020 | 0,9967 ± 0,0012 | 0,9950 ± 0,0041 | 1,07 | 0,353 |
| LZ78Y | 0,9961 ± 0,0015 | 0,9966 ± 0,0012 | 0,9855 ± 0,0327 | 1,21 | 0,310 |
| **mínimo (H no-IID)** | **0,8518** ± 0,0311 | **0,8471** ± 0,0169 | **0,8509** ± 0,0369 | 0,08 | 0,924 |

Ningún estimador distingue los chips al nivel corregido (p < 0,0045). Uno
queda por debajo de 0,05 sin corregir (MCV, 0,032, como ya pasaba con dos
chips: 0,047), y lo que separa es una diferencia de 0,001 bit/bit pegada
al techo de resolución del MCV. La cifra que importa, el mínimo no-IID, es
la misma en los tres chips: 0,852, 0,847 y 0,851 (p = 0,92).
**Con tres chips del mismo modelo, la línea base del ESP32 no depende del
chip a la resolución de estos estimadores.**

## 4. Lectura

1. **Shannon ≠ min-entropía, con números.** La primera campaña dio 0,99999 bit/bit
   de Shannon. Las mismas capturas, por la letra de SP 800-90B, valen
   0,993-0,996 bit/bit si se admite IID y **0,81-0,92 bit/bit** (media 0,85
   sobre treinta y seis capturas de tres chips) si no. El orden H_min ≤ H_Shannon se cumple siempre;
   lo que cambia es cuánto crédito se puede dar a cada bit al contar entropía
   para una clave. Con la cifra no-IID más baja (0,809), 256 bits de entropía
   requieren 317 bits de salida; con la Shannon, 256. Es la diferencia entre
   "pasa los tests" y "está acotado".

2. **El mínimo lo fijan casi siempre Compression, Collision o LRS** (37 de
   38 capturas; la otra, el predictor Lag), y nunca Markov ni MCV, que
   quedan por encima de 0,99. Esos tres estimadores tienen un sesgo
   conservador conocido en fuentes casi uniformes: el de compresión (Maurer)
   y el de colisión están calibrados para fuentes con sesgo apreciable y,
   sobre datos de entropía plena, devuelven sistemáticamente ≈ 0,85-0,93
   (Zhu et al., ToSC 2017(3):151-168 [VERIFICADO-META por Crossref]; Kelsey
   et al., CHES 2015 [VERIFICADO], que introdujeron los predictores
   justamente porque los estimadores anteriores fallaban en ese tipo de
   fuente). Prueba interna de que es sesgo y no señal: la dispersión del
   estimador de compresión **dentro de una misma condición** (desviación
   0,027-0,040 con nueve repeticiones; 0,83-0,92 entre las capturas sin
   radio) es mayor que la separación entre las medias de las cuatro
   condiciones (0,013), y el ANOVA de §3.4 no encuentra efecto en ningún
   estimador. Con nueve repeticiones por condición, **ningún estimador
   resuelve diferencias entre A, B, C y D**, y con tres chips (§3.5)
   tampoco entre chips.

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

4. **Coste de evaluación.** Ciento cincuenta y dos ejecuciones (38
   capturas × 2 vías × 2 modos); las 48 del chip a0:dd:6c:0e:fb:4c, 284 s
   en serie con la herramienta oficial, y las 48 del f8:b3:b7:2a:09:28,
   240 s; el
   cuello no es el cómputo sino la captura: 125 kB por condición tardan
   unos 25 s con `firmware/esp32_rng` (hex a 115200 baudios) y un ciclo
   de cuatro condiciones, unos dos minutos con arranque incluido.

## 5. Pendiente

- ~~El firmware de la campaña se queda parado en el *harvester* tras el
  primer ciclo.~~ No se queda parado (§1, tercer chip): las semillas tardan
  unos dos minutos y el ciclo siguiente empieza solo.
- Prueba de reinicios (§3.1.4 de la norma): **hecha** el 12-10-2026 en el
  chip a0:dd:6c:0e:fb:4c, `docs/esp32_reinicios.md`. Con el bootloader de
  serie la pasa; sin el ruido que mete el bootloader, la falla: el
  generador no tiene ruido propio en condición D, y la entropía física de
  las capturas D es como mucho la que siembra el arranque, que estos
  estimadores no ven. Con el Wi-Fi encendido la pasa incluso sin el ruido
  del bootloader, y un control con la misma espera sin radio la falla: la
  radio sí mete ruido en el generador (condición B).
- Cuando exista la placa: la misma batería sobre los bits crudos del ERO
  (registro CAPTURA, modo test) a K_D de diseño, y sobre la salida del
  DRBG; contrastar con la cota del modelo (`analysis/ero_model.py`).
