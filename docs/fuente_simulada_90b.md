# La fuente simulada bajo SP 800-90B (31-10-2026)

**Todo lo de este documento es SIMULADO.** Son bits del modelo estocástico
del ERO (`ero_model.simular_bits`) con el jitter que da ngspice para los
transistores de IHP SG13G2, no bits de un anillo físico. Sirve para tres
cosas: ver qué haría la batería del NIST con la fuente del motor, saber
contra qué se compara el ESP32 a la misma longitud, y tener la
referencia preparada para cuando la campaña en la Basys 3 dé bits reales.
No sustituye a esa campaña.

Scripts: `analysis/fuente_simulada_90b.py` (genera y pasa la batería) y
`analysis/fuente_simulada_figura.py` (figura y tabla). Datos:
`results/fuente_simulada_90b.csv`, `results/fuente_simulada_90b_resumen.md`,
logs completos `results/fuente_simulada_90b.log` (no-IID) y
`results/fuente_simulada_90b_iid.log` (IID). Las secuencias se regeneran
(semilla = CRC32 del nombre) y no van a git.

## 1. Qué se ha hecho

- Tres casos de jitter, con Q por periodo de las tablas de `anillo_ihp.md`:
  tt a 27 °C (Q = 2,33·10⁻⁷, media de 8 realizaciones), ss a −40 °C y
  1,08 V (6,00·10⁻⁸, media de 8) y el peor chip con desapareamiento en ese
  punto (5,09·10⁻⁸).
- Divisores 2¹⁴, 2¹⁶, 2¹⁸ … 2²⁴; Q de muestreo = Q·K_D. Tres semillas por
  punto, 10⁶ bits por secuencia: la misma N que las capturas del ESP32.
- Referencia "ideal": bits uniformes e independientes de `numpy`, tres
  semillas, misma N.
- Batería: los mismos binarios y opciones que para el ESP32
  (`entropia_90b.ejecutar`: `ea_non_iid`/`ea_iid -i -a -v`). No-IID en bit
  y en byte para todo; IID en byte para 2²⁰-2²⁴ y el ideal. **La vía IID
  en bit no se ha corrido**: tarda ~28 min por secuencia (10 000
  permutaciones sobre 10⁶ símbolos) frente a 1-150 s en byte.
- Min-entropía del modelo: `entropias_exactas(Q)[1]`, el peor caso
  condicionado a la fase anterior (Baudet), exacta con la gaussiana
  envuelta. Es la que fija el divisor en el resto del TFM.

Dos fallos del propio script, encontrados al leer el log y corregidos
antes de dar ningún resultado: (1) la semilla salía de los cuatro primeros
bytes del nombre, así que las tres repeticiones eran la misma secuencia
(mismo SHA-256 en el log); ahora es el CRC32 del nombre completo, y las 84
secuencias tienen hashes distintos. (2) La columna `IID` del CSV es el
tipo de prueba, no el veredicto; el veredicto está en
`testCases.0.passed*`, que es lo que ya leía `resumen_90b.py` para el
ESP32 (su análisis no está afectado).

## 2. Resultados

Estimación no-IID en bits (`testCases.10.hAssessed`), media ± desviación
de tres semillas. En byte, dividida entre 8, da lo mismo salvo en un punto
(ss 2²⁴ r1: el predictor MultiMCW sobre los bytes da 5,89 bit/byte, 0,74
bit/bit, frente a 0,84 en bits, con el modelo en H_∞ = 1; es el estimador
el que fluctúa, con 1,25·10⁵ símbolos de 256 valores).
El estimador que limita es siempre la compresión.

| log₂ K_D | tt: modelo | tt: NIST | ss 1,08 V: modelo | ss: NIST | peor chip: modelo | peor: NIST |
|---|---|---|---|---|---|---|
| 14 | 0,0001 | 0,110 | 0,0000 | 0,074 | 0,0000 | 0,071 |
| 16 | 0,064 | 0,210 | 0,0001 | 0,111 | 0,0000 | 0,105 |
| 18 | 0,534 | 0,503 | 0,068 | 0,214 | 0,045 | 0,195 |
| 19 | 0,844 | 0,750 ± 0,015 | 0,249 | 0,323 | 0,194 | 0,292 |
| 20 | 0,985 | 0,855 ± 0,042 | 0,548 | 0,508 | 0,470 | 0,457 |
| 21 | 1,000 | 0,868 ± 0,013 | 0,855 | 0,764 ± 0,012 | 0,792 | 0,702 ± 0,007 |
| 22 | 1,000 | 0,873 ± 0,006 | 0,987 | 0,832 ± 0,019 | 0,973 | 0,823 ± 0,010 |
| 23 | 1,000 | 0,849 ± 0,031 | 1,000 | 0,840 ± 0,031 | 1,000 | 0,848 ± 0,031 |
| 24 | 1,000 | 0,830 ± 0,016 | 1,000 | 0,837 ± 0,019 | 1,000 | 0,842 ± 0,018 |

Sin desviación indicada: < 0,002.

- **Ideal (bits uniformes):** 0,839 ± 0,021 (0,815-0,854).
- **ESP32, medido** (36 capturas A-D, tres chips, misma herramienta y N):
  media 0,850, 0,809-0,918.

Vía IID en byte (pasan las tres pruebas: χ², permutaciones, LRS):

| | 2²⁰ | 2²¹ | 2²² | 2²³ | 2²⁴ |
|---|---|---|---|---|---|
| tt | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| ss 1,08 V | 0/3 | **3/3** | 3/3 | 3/3 | 3/3 |
| peor chip | 0/3 | **2/3** | 3/3 | 3/3 | 3/3 |
| ideal | | | | | 3/3 |

Donde falla, lo detecta la χ² (en una sola secuencia también la de
permutaciones, por la compresión).

Figura: `memoria/figures/fuente_simulada_90b.pdf`.

## 3. Lectura

1. **A 10⁶ bits la batería se satura en ~0,84 bit/bit.** Bits perfectos
   sacan 0,839 ± 0,021 y todo punto en el que el modelo da ≥ 0,97 sale
   entre 0,82 y 0,87. Es el sesgo del estimador de compresión a esta
   longitud, no la fuente. Por encima de ese techo la batería no distingue
   nada.
2. **El ESP32 y la fuente simulada a 2²² o 2²³ son indistinguibles para la
   batería a esta N.** El 0,85 del ESP32 cae en la banda del ideal. No se
   puede decir con SP 800-90B que una sea mejor que la otra; la diferencia
   entre ellas no está en ese número sino en que la del motor tiene una
   cota del modelo físico y la del ESP32 no (cap. 7, "the asymmetry is the
   comparison").
3. **Con poca entropía la batería sobreestima.** Con 2¹⁴ el modelo da ≈ 0
   y la batería 0,07-0,11; en 2¹⁶-2¹⁹ del peor caso, 0,10-0,32 frente a
   0,00-0,25. La fuente es casi determinista: la fase avanza ν = 0,4771
   ciclos por muestra con un ruido pequeño, los bits casi alternan
   (P(0→1) ≈ 0,89 en 2¹⁴) y los predictores genéricos no explotan del
   todo esa estructura. El modelo sí, porque supone un atacante que conoce
   la fase anterior. **La batería no es una cota inferior de la fuente**:
   un divisor mal elegido no se habría visto con ella sola. Es el
   argumento de AIS 31 para exigir un modelo estocástico, ahora con
   números del propio diseño.
4. **La vía IID da por buenos datos que no lo son.** En 2²¹ el peor caso
   tiene H_∞ = 0,79-0,85 según el modelo y pasa las pruebas IID en 5 de 6
   secuencias. Si se aceptara la vía IID, el crédito sería el MCV en byte
   (6,84-7,18 bit/byte, 0,86-0,90 bit/bit), por encima del modelo. Con 2²⁰
   (0,47-0,55) ya falla siempre. Refuerza la decisión de llevar la cifra
   no-IID como la del ESP32 y aplicar a los bits del motor el mismo
   criterio.
5. **En la zona intermedia la batería queda por debajo del modelo**
   (H_∞ entre ~0,5 y 0,95: 0,70 frente a 0,79, 0,76 frente a 0,85), que
   es lo esperable de un estimador conservador. El cruce está hacia 0,5.
6. **El divisor recomendado (2²³ con ±10 % de V_DD) da en los tres casos
   una estimación indistinguible del ideal**, y es el mismo divisor que
   pide el modelo: la batería no lo contradice, pero tampoco lo habría
   elegido (ver 1 y 3).

## 4. Qué no dice esto y qué falta

- Son bits de un modelo con ruido blanco gaussiano por periodo. El ruido
  de parpadeo, el acoplamiento entre anillos, la alimentación compartida y
  las derivas lentas no están, y son justo lo que la batería no ve y la
  campaña en la FPGA tiene que medir.
- Tres semillas por punto: la desviación es indicativa (con 3 muestras,
  el intervalo del 95 % de σ va de 0,5σ a 6,3σ).
- Falta la vía IID en bit (≈ 28 min por secuencia; para 2²¹ peor caso e
  ideal serían ~3 h). Las longitudes mayores están en la §5: el techo sube,
  pero la batería sigue sin separar el ESP32 de un 2²³.

## 5. Más bits: la longitud de las capturas largas del ESP32 (01-11-2026)

La esperanza de la §4 era que con más bits el techo del ideal subiera y
la batería separase el ESP32 del motor. Se ha probado a las dos longitudes
de las capturas largas sin radio del ESP32: `esp_rf_off_1` tiene
**3 523 072 bits** y `esp_rf_off_2` **8 378 368** (no las dos ~8,4·10⁶,
como decía una nota anterior). Solo 2²³, los tres casos y el ideal, tres
semillas; no-IID en bit y en byte a las dos N, IID en byte solo a 8,4·10⁶.

    python analysis/fuente_simulada_90b.py --n 8378368 --kd 23 --tests noniid
    python analysis/fuente_simulada_90b.py --n 3523072 --kd 23 --tests noniid
    ... --casos ideal --kd 0 / --tests iid --modos b8

`--n` añade el sufijo `_n<N>` al nombre (y la columna `n_bits` al CSV), así
que las filas de 10⁶ no se tocan; `fuente_simulada_figura.py` solo lee esas.
Logs completos: `results/fuente_simulada_90b_n8378368.log` (no-IID e IID,
36 ejecuciones) y `results/fuente_simulada_90b_n3523072.log` (no-IID, 24),
todas con exit 0. El ideal de 3,5·10⁶ lleva `kd23` en el nombre (el ideal
no usa el divisor; a 10⁶ y 8,4·10⁶ es `kd0`). En byte a 3,5·10⁶ son 440 384
símbolos y la herramienta avisa de que hay menos de 10⁶ muestras; lo mismo
pasa en byte con las secuencias de 10⁶ bits y con `esp_rf_off_1`.

No-IID en bit, media ± desviación de tres semillas (SIMULADO salvo el
ESP32, MEDIDO, una captura por longitud):

| N | ideal | tt 2²³ | ss 1,08 V 2²³ | peor chip 2²³ | todas (12) | ESP32 sin radio |
|---|---|---|---|---|---|---|
| 10⁶ | 0,839 ± 0,021 | 0,849 ± 0,031 | 0,840 ± 0,031 | 0,848 ± 0,031 | | 0,850 (36 capturas A-D) |
| 3,52·10⁶ | 0,869 ± 0,003 | 0,889 ± 0,033 | 0,886 ± 0,013 | 0,881 ± 0,002 | 0,881, 0,860-0,925 | **0,867** (`rf_off_1`) |
| 8,38·10⁶ | 0,926 ± 0,016 | 0,899 ± 0,009 | 0,901 ± 0,007 | 0,921 ± 0,009 | 0,912, 0,889-0,935 | **0,911** (`rf_off_2`) |

El modelo da H_∞ ≥ 0,9996 en los tres casos a 2²³: para la batería, las
doce secuencias de cada fila son la misma fuente que el ideal.

- En byte (dividido entre 8) sale lo mismo que en bit salvo en cuatro
  secuencias: a 8,4·10⁶ el ideal r3 y el peor chip r2 dan 0,832, y a
  3,5·10⁶ el ideal r2 y ss r2 dan 0,793. No es la fuente: es la cota local
  de los predictores sobre bytes (Lag, LZ78Y, MultiMCW), que sale de la
  racha más larga de aciertos (r = 4 en ~10⁶ predicciones, 6,655 bit/byte)
  y toma valores discretos. El ESP32 en byte: 0,867 y 0,911, igual que en bit.
- Estimador limitante en bit: la compresión en 33 de las 36 secuencias de
  bit de las tres longitudes del 2²³ y el ideal; el t-Tuple en el resto
  (dos ideales y un peor chip a 8,4·10⁶, que dan 0,931-0,935).
- IID en byte a 8,4·10⁶: pasan las tres pruebas las 12 secuencias (crédito
  8 bit/byte), igual que `esp_rf_off_2`.

Lectura:

1. **El techo sube con N, pero sube para todos.** Media de las secuencias
   con H_∞ ≈ 1: 0,84 → 0,88 → 0,91. El ESP32 lo sigue: 0,850 → 0,867 →
   0,911, y a cada longitud cae dentro de la nube de bits perfectos y de la
   fuente simulada (a 8,4·10⁶ está a 0,001 de la media de las doce).
2. **A ninguna de las tres longitudes la batería separa el ESP32 del
   motor.** Lo que limita es el sesgo del estimador de compresión (y del
   t-Tuple), que se encoge despacio con N. Ir a 10⁸ bits no cambiaría la
   conclusión de fondo: por encima de su techo la batería solo dice que las
   dos fuentes están por encima de su techo.
3. **Consecuencia para la memoria:** la comparación del objetivo O8 no puede
   apoyarse en la diferencia de las cifras SP 800-90B. Donde sí difieren las
   dos fuentes es en lo que hay detrás de la cifra: la del motor tiene una
   cota del modelo físico (y un divisor elegido con él) y la del ESP32 no,
   y el ESP32 sin ruido de arranque repite secuencias entre chips
   (`esp32_reinicios.md`). Separarlas con datos exigirá la campaña en la
   FPGA con otras pruebas (reinicios, condiciones adversas), no más bits.
