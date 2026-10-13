# Estado del Arte

**TFM: "Characterization of the Hardware True Random Number Generator of the ESP32 and Design of a Multi-Source Entropy Harvester for Secure IoT Applications"**
Máster en Microelectrónica — Universidad de Sevilla / IMSE-CNM
Revisión bibliográfica realizada: agosto de 2026

> Todas las fuentes fueron localizadas y verificadas mediante búsqueda web durante agosto de 2026. Las claves entre corchetes (p. ej. `[sunar2007provably]`) se corresponden con las entradas del fichero `referencias_encontradas.bib`.

---

## 1. El generador de números aleatorios del ESP32 (documentación oficial)

### 1.1 ESP32 Technical Reference Manual — capítulo *Random Number Generator (RNG)* `[espressif2026trm]`

El manual técnico de referencia de Espressif dedica un capítulo al periférico RNG. Todo valor de 32 bits leído del registro **RNG_DATA_REG (dirección 0x3FF75144)** se declara "número aleatorio verdadero", generado a partir del **ruido térmico** del sistema y del **desajuste de relojes asíncronos** (asynchronous clock mismatch). El ruido térmico procede de los ADC de alta velocidad y/o del SAR ADC: cuando alguno de ellos está habilitado, sus bits de ruido se inyectan continuamente en el RNG mediante puertas XOR. El manual recomienda no leer el registro más rápido que la tasa de acumulación de entropía (lecturas espaciadas; la documentación de ESP-IDF cuantifica los límites).
URL: https://www.espressif.com/sites/default/files/documentation/esp32_technical_reference_manual_en.pdf

### 1.2 ESP-IDF Programming Guide — página *Random Number Generation* (v5.x/estable) `[espressif2026random]`

Es la **advertencia oficial clave** para este TFM. El texto (verificado el 04/08/2026 en la versión estable de la guía) dice literalmente:

> *"The hardware RNG produces true random numbers so long as one or more of the following conditions are met: RF subsystem is enabled, i.e., Wi-Fi or Bluetooth are enabled; the internal entropy source (SAR ADC) has been enabled by calling `bootloader_random_enable()` and not yet disabled; while the ESP-IDF Second Stage Bootloader is running."*
>
> *"If none of the above conditions are true, the output of the RNG should be considered as pseudo-random only."*

Es decir: **sin WiFi/BT ni SAR ADC habilitados, la salida de `esp_random()` es solo pseudoaleatoria**. Otros puntos documentados en la misma página:

- `esp_random()` devuelve una palabra de 32 bits del RNG hardware y "busy-waits" para asegurar que se ha introducido suficiente entropía externa antes de devolver el valor; `esp_fill_random()` rellena un búfer llamando internamente a `esp_random()`.
- `bootloader_random_enable()` reactiva la fuente interna de entropía (SAR ADC) tras el arranque; debe deshabilitarse con `bootloader_random_disable()` antes de usar ADC, I2S, WiFi o BT.
- El estado interno del RNG hardware no es lo bastante grande para proporcionar un flujo continuo de números verdaderamente aleatorios: por eso se exige una fuente de entropía continua.
- Espressif afirma que una muestra de **2 GB obtenida del RNG del ESP32 con WiFi habilitado pasó todos los tests de la suite Dieharder** (no publica los datos ni el informe).
- Recomendación oficial para aplicaciones sin RF permanente: sembrar un DRBG software fuerte (CTR-DRBG o HMAC-DRBG de mbedTLS) con entropía del RNG hardware.

URL: https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/random.html
(Versión v5.0 con texto equivalente: https://docs.espressif.com/projects/esp-idf/en/v5.0/esp32/api-reference/system/random.html)

Las páginas homólogas de ESP32-S2/C3/H2 documentan además una **fuente de entropía secundaria** basada en muestrear un oscilador interno asíncrono de 8 MHz, siempre habilitada y mezclada por hardware; Espressif indica que en C3/H2 esta fuente secundaria bastó por sí sola para pasar Dieharder. El ESP32 original **no** dispone de esa fuente secundaria documentada, lo que hace más crítica la advertencia anterior.

### 1.3 Código fuente: `bootloader_random.c` y el puerto de mbedTLS `[espressif2026bootrandom]` `[espressif2026esphardware]`

- `components/bootloader_support/src/bootloader_random.c` implementa la habilitación de la fuente de entropía (configuración del SAR ADC en modo de muestreo de ruido) usada durante el segundo bootloader y por `bootloader_random_enable()`.
  URL: https://github.com/espressif/esp-idf/blob/master/components/bootloader_support/src/bootloader_random.c
- `components/mbedtls/port/esp_hardware.c` define `mbedtls_hardware_poll()`, que alimenta el módulo de entropía de mbedTLS llamando a `esp_fill_random()`. **Toda la pila TLS del ESP32 hereda por tanto la calidad (o falta de ella) del RNG hardware.**
  URL: https://github.com/espressif/esp-idf/blob/master/components/mbedtls/port/esp_hardware.c

### 1.4 Issues de GitHub sobre la calidad del RNG

- **Issue #14665 — "Clarification on the HW RNG" (oct. 2024)** `[kaell2024hwrng]`: un usuario pide precisar cuándo se considera "habilitado" el subsistema RF (¿basta con inicializar NimBLE?, ¿qué casos extremos saturan el ADC con WiFi activo?). Espressif lo resolvió aclarando la documentación; ilustra la ambigüedad práctica de las condiciones de entropía.
  URL: https://github.com/espressif/esp-idf/issues/14665
- **Issue #7598 — "boot: Disabling RNG early entropy source?" (2021)** `[espressif2021entropyissue]`: discute la fuente de entropía temprana del bootloader y las implicaciones de deshabilitarla, confirmando que la semilla inicial del estado RNG procede del SAR ADC durante el arranque.
  URL: https://github.com/espressif/esp-idf/issues/7598

### 1.5 Análisis divulgativos del RNG del ESP32

- **Programming Electronics Academy — "Just how random is the ESP32 random number generator?"** (M. Cheich, ~2025) `[cheich2025esp32]`: análisis por histogramas y comparación visual con WiFi habilitado/deshabilitado y tras reinicios (hasta ~300 000 muestras). Concluye que "parece aleatorio" incluso sin WiFi, pero **sin aplicar ninguna batería estadística formal (ni ENT, ni NIST, ni Dieharder)** — ejemplo del vacío metodológico existente.
  URL: https://www.programmingelectronics.com/esp32-random-number-generator/
- **AndroidCrypto (Medium) — "ESP32 How to generate True Random Numbers"** `[androidcrypto2026esp32]`: tutorial que recoge la advertencia de Espressif y muestra cómo activar `bootloader_random_enable()`; sin caracterización estadística.
  URL: https://medium.com/@androidcrypto/esp32-how-to-generate-true-random-numbers-true-rng-951fcda58e9b

---

## 2. Osciladores en anillo como TRNG: papers fundamentales

- **Sunar, Martin y Stinson (IEEE Trans. Computers, 56(1):109–119, 2007)** — *"A Provably Secure True Random Number Generator with Built-In Tolerance to Active Attacks"* `[sunar2007provably]`. Paper canónico: propone el TRNG de anillos de osciladores (114 anillos de 13 inversores) cuyo jitter de fase se muestrea y combina por XOR, con post-procesado por códigos resilientes. Introduce el primer marco de "seguridad demostrable" para TRNG con tolerancia a ataques activos y tasas del orden de Mbit/s. Es la referencia de partida de toda la línea RO-TRNG.
  URL: https://cs.uwaterloo.ca/~dstinson/papers/rng-IEEE.pdf

- **Wold y Tan (ReConFig 2008; Int. J. of Reconfigurable Computing, 2009)** — *"Analysis and Enhancement of Random Number Generator in FPGA Based on Oscillator Rings"* `[wold2009analysis]`. Analiza el diseño de Sunar et al. en FPGA real (Altera Cyclone II) y propone una mejora (un flip-flop de muestreo por anillo) que pasa los tests estadísticos **sin post-procesado**, con 100 Mbit/s y <100 elementos lógicos, usando ~25 anillos en lugar de 114. Los experimentos de reinicio ("restart experiments") demuestran comportamiento verdaderamente aleatorio (no pseudoaleatorio) tras el arranque.
  URL: https://onlinelibrary.wiley.com/doi/10.1155/2009/501672

- **Bochard, Bernard, Fischer y Valtchanov (Int. J. of Reconfigurable Computing, 2010)** — *"True-Randomness and Pseudo-Randomness in Ring Oscillator-Based True Random Number Generators"* `[bochard2010truerandomness]`. Demuestra matemática y experimentalmente que las arquitecturas de Sunar y de Wold-Tan se comportan igual con el mismo número de anillos, y que **reducir el número de anillos causa pérdida de entropía que queda enmascarada por la pseudoaleatoriedad** del XOR de relojes de frecuencias distintas: pasar los tests estadísticos no garantiza entropía real. Lección directamente aplicable al ESP32 (mezcla XOR de fuentes).
  URL: https://onlinelibrary.wiley.com/doi/10.1155/2010/879281

- **Baudet, Lubicz, Micolod y Tassiaux (Journal of Cryptology, 24:398–425, 2011)** — *"On the Security of Oscillator-Based Random Number Generators"* `[baudet2011security]`. Modelo estocástico de referencia del muestreo de un oscilador con ruido de fase: deriva la tasa de entropía y los sesgos de patrones en función de la relación jitter/periodo, y propone un test estadístico específico casi óptimo. Base matemática para estimar entropía (no solo "pasar tests") en cualquier TRNG de jitter, y fundamento de los enfoques tipo AIS-31/SP 800-90B de modelado de la fuente.
  DOI: 10.1007/s00145-010-9089-3 — URL: https://link.springer.com/article/10.1007/s00145-010-9089-3

- **Valtchanov, Aubert, Bernard y Fischer (2008)** — *"Modeling and Observing the Jitter in Ring Oscillators Implemented in FPGAs"* `[valtchanov2008modeling]`. Modela el retardo de cada puerta como suma de contribuciones de **fuentes de jitter locales (térmico, flicker) y globales (ruido de alimentación/deterministas)** y lo confirma con medidas en FPGA; advierte que el jitter global correlaciona los anillos entre sí y reduce la entropía efectiva.
  URL: https://www.researchgate.net/publication/4341841_Modeling_and_Observing_the_Jitter_in_Ring_Oscillators_Implemented_in_FPGAs

- **Hajimiri, Limotyrakis y Lee (IEEE JSSC, 34(6):790–804, 1999)** — *"Jitter and Phase Noise in Ring Oscillators"* `[hajimiri1999jitter]`. Referencia microelectrónica clásica del jitter en anillos: mediante funciones de sensibilidad al impulso deriva expresiones del jitter/ruido de fase en función del número de etapas, potencia, frecuencia y efectos de canal corto. Fundamenta la distinción **jitter térmico (acumulación ∝ √t, blanco, ideal para TRNG) vs. jitter flicker 1/f (autocorrelado)**.
  URL: http://smirc.stanford.edu/papers/JSSC99JUN-ali.pdf

- **Benea, Carmona, Fischer, Pebay-Peyroula y Wacquez (IACR TCHES, 2024(2):870–889)** — *"Impact of the Flicker Noise on the Ring Oscillator-based TRNGs"* `[benea2024flicker]`. Estado del arte reciente sobre la controversia térmico/flicker: su modelo de comportamiento muestra que el ruido flicker, tradicionalmente excluido por su autocorrelación, **suprime efectos de memoria** en el flujo de bits y podría cuadruplicar la tasa de salida manteniendo la entropía. Relevante porque el peso del flicker aumenta en nodos tecnológicos modernos y con la temperatura.
  DOI: 10.46586/tches.v2024.i2.870-889 — URL: https://tches.iacr.org/index.php/TCHES/article/view/11450

**Efecto de la temperatura:** el periodo y el jitter de los anillos dependen fuertemente de la temperatura (la frecuencia del ROSC del RP2040, p. ej., varía con ella `[raspberrypi2026rp2040]`); tanto Valtchanov et al. como la literatura AIS-31 exigen caracterizar el TRNG en el rango operativo de temperatura y tensión, lo que motiva el plan experimental de este TFM (medidas del RNG del ESP32 a distintas temperaturas y condiciones de alimentación).

---

## 3. NIST SP 800-22 Rev. 1a y NIST SP 800-90B

### 3.1 El documento SP 800-22 Rev. 1a `[rukhin2010statistical]`

Rukhin et al., *"A Statistical Test Suite for Random and Pseudorandom Number Generators for Cryptographic Applications"*, NIST Special Publication 800-22 Revision 1a, abril de 2010. Define 15 tests estadísticos sobre secuencias binarias, cada uno con hipótesis nula de aleatoriedad y un p-valor calculado mediante `erfc` (media normal) o `igamc` (chi-cuadrado incompleta).
PDF oficial: https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-22r1a.pdf
Software (STS 2.1.2) y documentación: https://csrc.nist.gov/projects/random-bit-generation/documentation-and-software

**Interpretación y requisitos** (secciones 1–4 del documento):
- Nivel de significación típico α = 0,01: una secuencia pasa un test si p ≥ 0,01.
- Para una batería de *m* secuencias se evalúan **(a) la proporción de secuencias que pasan** — intervalo de aceptación p̂ ± 3·√(p̂(1−p̂)/m) con p̂ = 1−α (p. ej., con m = 1000 y α = 0,01, mínimo ≈ 0,9806) — y **(b) la uniformidad de los p-valores** (χ² sobre 10 intervalos; se exige P-value_T ≥ 0,0001).
- Longitud recomendada: **secuencias de n = 10⁶ bits** (1 Mbit); mínimos por test: Frequency n ≥ 100, Universal n ≥ 387 840, Linear Complexity y Random Excursions n ≥ 10⁶. Práctica habitual: ≥ 55–1000 secuencias de 1 Mbit.

### 3.2 Tabla: los 15 tests de NIST SP 800-22

| # | Test | Qué evalúa | Estadístico / distribución de referencia |
|---|------|------------|------------------------------------------|
| 1 | Frequency (Monobit) | Proporción global de unos y ceros | s_obs = \|Σ±1\|/√n; p = erfc(s_obs/√2) (semi-normal) |
| 2 | Frequency within a Block | Proporción de unos en bloques de M bits | χ²(obs) = 4M·Σ(π_i−½)²; p = igamc(N/2, χ²/2) |
| 3 | Runs | Número total de rachas (oscilación rápida/lenta) | V_n(obs); p vía erfc (aprox. normal) |
| 4 | Longest Run of Ones in a Block | Longitud de la racha de unos más larga por bloque | χ² sobre categorías de longitudes; igamc |
| 5 | Binary Matrix Rank | Dependencia lineal entre subcadenas (rango de matrices 32×32) | χ² sobre frecuencias de rangos {R, R−1, ≤R−2}; igamc |
| 6 | Discrete Fourier Transform (Spectral) | Rasgos periódicos: picos espectrales por encima del umbral del 95 % | d = (N₁−N₀)/√(n·0,95·0,05/4); p = erfc(\|d\|/√2) |
| 7 | Non-overlapping Template Matching | Ocurrencias de plantillas aperiódicas de m bits (sin solape) | χ² sobre W_i frente a media/varianza teóricas; igamc |
| 8 | Overlapping Template Matching | Ocurrencias de plantillas (con solape); rachas de unos de longitud m | χ² con 5 grados de libertad (distr. Pólya-Aeppli); igamc |
| 9 | Maurer's Universal Statistical | Compresibilidad: distancia (log₂) entre repeticiones de patrones de L bits | f_n = (1/K)Σlog₂(distancias); aprox. normal, p vía erfc |
| 10 | Linear Complexity | Longitud del LFSR equivalente (Berlekamp–Massey) por bloque | χ² sobre 7 categorías de T_i; igamc |
| 11 | Serial (2 p-valores) | Uniformidad de frecuencias de todos los patrones de m bits | ∇ψ²_m y ∇²ψ²_m; igamc |
| 12 | Approximate Entropy | Comparación de frecuencias de patrones de m y m+1 bits | χ² = 2n[ln 2 − ApEn(m)]; igamc |
| 13 | Cumulative Sums (Cusum, forward/backward) | Excursión máxima del paseo aleatorio de sumas parciales | z = max\|S_k\|; p vía distribución normal (fórmula de sumas) |
| 14 | Random Excursions (8 p-valores) | Nº de visitas a los estados x ∈ {−4…−1, 1…4} por ciclo del paseo | χ² con 5 g.l. por estado; igamc |
| 15 | Random Excursions Variant (18 p-valores) | Nº total de visitas a los estados x ∈ {−9…9}\{0} | \|ξ(x)−J\|/√(2J(4\|x\|−2)); p vía erfc |

### 3.3 NIST SP 800-90B (2018) y su diferencia con SP 800-22 `[turan2018sp80090b]` `[nist2018entropytool]`

Turan, Barker, Kelsey, McKay, Baish y Boyle, *"Recommendation for the Entropy Sources Used for Random Bit Generation"*, NIST SP 800-90B, enero de 2018. A diferencia de SP 800-22 (tests de caja negra sobre la *salida*), 800-90B **valida la fuente de entropía**: exige justificación de diseño, estimación de **min-entropía** H_∞ = −log₂(p_max) mediante 10 estimadores (MCV, collision, Markov, compression, t-tuple, LRS, MultiMCW, lag, MultiMMC, LZ78Y), distingue rutas IID/no-IID, evalúa el *conditioning* y obliga a **health tests continuos** embarcados (Repetition Count Test y Adaptive Proportion Test) más tests de arranque y bajo demanda. Es el marco usado en las validaciones FIPS 140-3/CMVP actuales.
PDF oficial: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/nist.sp.800-90b.pdf
Herramienta oficial de evaluación: https://github.com/usnistgov/SP800-90B_EntropyAssessment

**Diferencia esencial**: SP 800-22 responde "¿la salida *parece* aleatoria?"; SP 800-90B responde "¿cuánta entropía *garantiza* la fuente y cómo se vigila en operación?". Un DRBG determinista con semilla fija puede pasar SP 800-22 y tener entropía nula.

### 3.4 Críticas conocidas a SP 800-22

- **Saarinen (IACR ePrint 2022/169)** — *"SP 800-22 and GM/T 0005-2012 Tests: Clearly Obsolete, Possibly Harmful"* `[saarinen2022obsolete]`: los tests no detectan generadores criptográficamente rotos (los "generadores de referencia" del propio documento pasan los tests sin material secreto); recomienda a NIST retirar la suite en favor del modelado estocástico (90B) y la evaluación de puertas traseras. Señala que SP 800-22 **no se usa** en la validación NIST de RNGs.
  URL: https://eprint.iacr.org/2022/169
- **Iwasaki (arXiv:1710.01441, 2017)** — *"Analysis of NIST SP800-22 focusing on randomness of each sequence"* `[iwasaki2017analysis]`: los resultados de los distintos tests **no son mutuamente independientes** y la suite carece de un criterio racional global; propone identificar un subconjunto mínimo de tests.
  URL: https://arxiv.org/abs/1710.01441
- **Comentarios públicos del Crypto Publication Review de NIST (2021)** `[nist2021comments]`: recopilación oficial de críticas (redundancia de tests, obsolescencia, mal uso como "certificación") durante el proceso de revisión de SP 800-22 Rev. 1a.
  URL: https://csrc.nist.gov/csrc/media/Projects/crypto-publication-review-project/documents/initial-comments/sp800-22r1a-initial-public-comments-2021.pdf

**Consecuencia metodológica para el TFM**: aplicar SP 800-22 como batería de caracterización comparable con la literatura, pero complementarla con estimación de min-entropía SP 800-90B (herramienta oficial) y con variación de condiciones operativas, que es donde SP 800-22 por sí sola es ciega.

---

## 4. Caracterizaciones previas de TRNGs en SoCs IoT

### 4.1 ESP32

- **Hidayatulloh, Qolbiyah, Nugroho, Mukhtar, Purnama y Simanjuntak (IEEE ICRAMET 2024)** — *"Performance Evaluation of ESP32 Random Number Generator for LoRa Communication Security"* `[hidayatulloh2024esp32]`: usa el RNG del ESP32 como generador de nonces para AES-CTR en enlaces LoRa P2P; los números generados **pasan la suite NIST**, pero el estudio no varía condiciones operativas (WiFi/ADC/temperatura) ni publica proporciones/uniformidad por test.
  DOI: 10.1109/ICRAMET62801.2024.10809333 — URL: https://ieeexplore.ieee.org/document/10809333/
- **Castillo et al. (MDPI IoT, 7(1):26, 2026)** — *"Automated Framework for Testing Random Number Generators for IoT Security Applications Using NIST SP 800-22"* `[castillo2026automated]`: framework web automatizado (backend Python + REST) para ejecutar SP 800-22; validado con **55 secuencias de 10⁶ bits extraídas de 2 GB generados por un ESP32-C3** (RISC-V, con fuente secundaria de entropía). El objetivo es la herramienta, no la caracterización del silicio: una única condición operativa y un solo chip (no el ESP32 original Xtensa).
  DOI: 10.3390/iot7010026 — URL: https://www.mdpi.com/2624-831X/7/1/26
- **Espressif (documentación oficial)** `[espressif2026random]`: muestra de 2 GB con WiFi habilitado pasó **Dieharder** (sin informe público, sin condiciones degradadas).
- **Blogs técnicos** `[cheich2025esp32]` `[androidcrypto2026esp32]`: análisis informales (histogramas, ENT ocasional), sin batería NIST completa ni control de condiciones.

### 4.2 Otros SoCs / plataformas

- **STM32 — STMicroelectronics AN4230** `[stmicro2026an4230]`: nota de aplicación oficial *"Random number generation validation using the NIST statistical test suite for STM32 MCUs and MPUs"*: firmware de volcado + validación con SP 800-22 rev1a y SP 800-90B; ST declara además haber evaluado el periférico frente a **AIS-31 clase PTG.2** (BSI). Es el ejemplo de caracterización "de fabricante" más completa entre MCUs.
  URL: https://www.st.com/resource/en/application_note/an4230-introduction-to-random-number-generation-validation-using-the-nist-statistical-test-suite-for-stm32-mcus-and-mpus-stmicroelectronics.pdf
- **STM32 — Ngo y Dubrova (ACM GLSVLSI 2022)** — *"Side-Channel Analysis of the Random Number Generator in STM32 MCUs"* `[ngo2022sidechannel]`: una red neuronal recupera el peso de Hamming de los números aleatorios a partir del consumo con >60 % de acierto (frente al 14 % base): incluso un TRNG estadísticamente bueno puede filtrar por canal lateral.
  DOI: 10.1145/3526241.3530324 — URL: https://dl.acm.org/doi/10.1145/3526241.3530324
- **nRF52840 (Nordic)** `[nordic2026nrf52840]`: la especificación de producto documenta un RNG basado en **ruido térmico interno**, sin semilla, con corrección de sesgo opcional por hardware; Nordic declara conformidad con NIST 800-90B, AIS-31 y FIPS 140-2 en la serie nRF52/53, pero no publica los datos de la evaluación.
  URL: https://infocenter.nordicsemi.com/topic/ps_nrf52840/rng.html
- **RP2040 (Raspberry Pi)** `[raspberrypi2026rp2040]` `[dmo2022rp2040]`: no tiene TRNG dedicado; el bit aleatorio del **ROSC (oscilador en anillo del sistema)** es la única fuente. El propio datasheet advierte de que **no cumple los requisitos de aleatoriedad para sistemas de seguridad** (puede comprometerse; la frecuencia depende de la temperatura). Análisis independientes muestran fuerte autocorrelación si se muestrea rápido; el SDK (`pico_rand`) mitiga mezclando ROSC (≤100 kbit/s con espaciado de 10 µs), tiempo y contadores de bus mediante hash — un mini-harvester multi-fuente.
  URLs: https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf ; https://dmo.page/2022/10/02/rp2040-randomness-and-ring-oscillator/ ; https://forums.raspberrypi.com/viewtopic.php?t=362076
- **Raspberry Pi (BCM2835/BCM2711 hwrng)** `[scruss2013raspberrypi]`: el SoC incluye un HWRNG propietario expuesto como `/dev/hwrng` (rngd/rng-tools); evaluaciones comunitarias con **ENT, rngtest (FIPS 140-2) y Dieharder** dan buenos resultados (~1 Mbit/s), pero el diseño y los filtros internos son cerrados, lo que impide un modelo estocástico.
  URL: https://scruss.com/blog/2013/06/07/well-that-was-unexpected-the-raspberry-pis-hardware-random-number-generator/
- **Chips Bluetooth Broadcom/Cypress — Tillmanns, Classen, Rohrbach y Hollick (USENIX WOOT 2020)** — *"Firmware Insider: Bluetooth Randomness is Mostly Random"* `[tillmanns2020firmware]`: ingeniería inversa del RNG en firmware BT; los HRNG presentes pasan tests avanzados, pero **muchos dispositivos populares (Samsung Galaxy S8, iPhones) carecen de HRNG dedicado y usan un PRNG de respaldo inseguro**. Demuestra el valor de auditar la aleatoriedad real de los SoC comerciales.
  URL: https://arxiv.org/abs/2006.16921

### 4.3 Tabla comparativa de caracterizaciones previas

| Plataforma / SoC | Fuente física declarada | Batería aplicada | Condiciones variadas | Resultado | Referencia |
|---|---|---|---|---|---|
| ESP32 (Xtensa) | Ruido térmico ADC RF/SAR + clocks asíncronos | Dieharder (2 GB, por Espressif) | Solo WiFi ON | Pasa (sin informe público) | `[espressif2026random]` |
| ESP32 (Xtensa) | RNG HW (esp_random) | NIST SP 800-22 | No (una condición) | Pasa (uso: nonces LoRa/AES-CTR) | `[hidayatulloh2024esp32]` |
| ESP32-C3 (RISC-V) | RNG HW + fuente secundaria 8 MHz | NIST SP 800-22 (55×10⁶ bits de 2 GB) | No | Pasa (foco: framework automatizado) | `[castillo2026automated]` |
| ESP32 (blogs) | RNG HW | Histogramas / ENT informal | WiFi ON/OFF, reinicios | "Parece aleatorio"; sin rigor estadístico | `[cheich2025esp32]` |
| STM32 (F4/L4/H7…) | RO-TRNG analógico dedicado | NIST SP 800-22, SP 800-90B; AIS-31 PTG.2 (ST) | Según nota de aplicación | Pasa (validación de fabricante) | `[stmicro2026an4230]` |
| STM32 | RNG periférico | Ataque side-channel (deep learning sobre consumo) | — | Fuga: Hamming weight recuperado >60 % | `[ngo2022sidechannel]` |
| nRF52840 | Ruido térmico, corrector de sesgo HW | NIST 800-90B, AIS-31, FIPS 140-2 (declarado) | No publicado | Conforme (sin datos públicos) | `[nordic2026nrf52840]` |
| RP2040 | Jitter del ROSC del sistema | Análisis comunitarios (autocorrelación); mitigación en pico_rand | Temperatura afecta frecuencia | **No apto cripto** según datasheet | `[raspberrypi2026rp2040]` `[dmo2022rp2040]` |
| Raspberry Pi (BCM2835) | HWRNG propietario | ENT, rngtest/FIPS 140-2, Dieharder (comunidad) | No | Pasa; diseño opaco | `[scruss2013raspberrypi]` |
| Broadcom/Cypress BT | HRNG en chip BT (si existe) | Suites avanzadas + ingeniería inversa | Multi-dispositivo | HRNG ok; fallback PRNG inseguro en S8/iPhone | `[tillmanns2020firmware]` |

---

## 5. Extractores y acondicionadores de entropía

- **Von Neumann (1951)** — *"Various techniques used in connection with random digits"*, National Bureau of Standards, Applied Mathematics Series 12, pp. 36–38 `[vonneumann1951various]`. Origen del **corrector de Von Neumann**: se toman los bits por pares, se descartan 00 y 11, y 01→0, 10→1; elimina el sesgo de una fuente Bernoulli i.i.d. a costa de un rendimiento ≤ 25 % (p(1−p) por par). No corrige correlaciones, lo que limita su uso con fuentes con memoria (flicker).
  Contexto y facsímil: http://fsaad.mit.edu/randomseed/citing-a-rare-paper-by-von-neumann-various-techniques-used-in-connection-with-random-digits/

- **Impagliazzo, Levin y Luby (ACM STOC 1989)** — *"Pseudo-random generation from one-way functions"* `[impagliazzo1989pseudorandom]`. Formula y demuestra el **Leftover Hash Lemma**: una familia de funciones hash universales aplicada a una fuente con min-entropía k produce una salida de m bits a distancia estadística ≤ 2^((m−k)/2)/... — base teórica de los **extractores por hashing universal** (extractores "seeded") y de todo acondicionamiento criptográfico moderno.
  DOI: 10.1145/73007.73009 — URL: https://dl.acm.org/doi/10.1145/73007.73009

- **Dodis, Gennaro, Håstad, Krawczyk y Rabin (CRYPTO 2004, LNCS 3152:494–510)** — *"Randomness Extraction and Key Derivation Using the CBC, Cascade and HMAC Modes"* `[dodis2004randomness]`. Analiza formalmente cuándo CBC-MAC, la construcción en cascada (base de SHA-256) y HMAC funcionan como extractores de aleatoriedad computacionales: justificación teórica de usar funciones hash estándar como acondicionadores.
  URL: https://cs.nyu.edu/~dodis/ps/hmac.pdf

- **Krawczyk (CRYPTO 2010)** — *"Cryptographic Extraction and Key Derivation: The HKDF Scheme"* `[krawczyk2010hkdf]`. Formaliza el paradigma **extract-then-expand** (HKDF, RFC 5869): extraer con HMAC una clave pseudoaleatoria de la fuente cruda y expandirla con un PRF. Es el patrón arquitectónico natural para el harvester multi-fuente del TFM.
  DOI: 10.1007/978-3-642-14623-7_34 — URL: https://link.springer.com/chapter/10.1007/978-3-642-14623-7_34

- **SHA-256 como conditioner "vetted" (NIST SP 800-90B, sección 3.1.5)** `[turan2018sp80090b]`: 800-90B admite como acondicionadores verificados HMAC, CMAC, CBC-MAC y las funciones hash aprobadas (SHA-2); si el conditioner es "vetted", la entropía de salida se acredita hasta ~0,999·n_out bits (con entrada suficiente). El ESP32 dispone de aceleración hardware SHA-256, lo que hace este conditioner especialmente adecuado.

- **Pawlowski, Jara y Ogorzalek (Sensors, 15(10):26838–26865, 2015)** — *"Harvesting Entropy for Random Number Generation for Internet of Things Constrained Devices Using On-Board Sensors"* `[pawlowski2015harvesting]`. Evalúa temperatura, humedad y dos sensores de luz como fuentes de entropía en dispositivos restringidos (concatenación de LSBs): los sensores de luz dan la mayor min-entropía/Shannon (~7,9 bits/byte tras ajuste) con ~1,3 ms/byte. Antecedente directo del harvesting multi-sensor.
  DOI: 10.3390/s151026838 — URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC4634515/

- **Zhang y Wu (Sensors, 23(20):8497, 2023)** — *"Random Number Generation Based on Heterogeneous Entropy Sources Fusion in Multi-Sensor Networks"* `[zhang2023heterogeneous]`. Pool de entropía que fusiona circuitos caóticos y eventos ambientales (ruido térmico, canal radio, vídeo) en redes de sensores; ejemplo reciente de arquitectura de fusión multi-fuente con validación estadística.
  DOI: 10.3390/s23208497 — URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC10611373/

- **Kietzmann, Schmidt y Wählisch (ACM Computing Surveys, 54(6):112, 2021)** — *"A Guideline on Pseudorandom Number Generation (PRNG) in the IoT"* `[kietzmann2021guideline]`. Survey de referencia sobre generación de aleatoriedad en IoT restringido: taxonomía de fuentes (radio, sensores, SRAM, jitter), PRNG/DRBG, y directrices de diseño seguro con presupuesto energético; documenta la escasez de entropía como problema estructural del IoT.
  DOI: 10.1145/3453159 — URL: https://dl.acm.org/doi/10.1145/3453159

- **Foreman, Yeung y Curchod (Entropy, 26(12):1053, 2024)** — *"Statistical testing of random number generators and their improvement using randomness extraction"* `[foreman2024statistical]`. Muestra empíricamente cómo extractores (Toeplitz, Trevisan…) elevan la calidad de RNGs comerciales (RDSEED, Quantis) medida con baterías estadísticas ampliadas: metodología reutilizable para validar el post-procesado del harvester.
  URL: https://arxiv.org/abs/2403.18716

---

## 6. SRAM-PUF como fuente de entropía

- **Holcomb, Burleson y Fu (IEEE Trans. Computers, 58(9):1198–1210, 2009)** — *"Power-Up SRAM State as an Identifying Fingerprint and Source of True Random Numbers"* (sistema **FERNS**) `[holcomb2009powerup]`. El estado de encendido de la SRAM combina una huella determinista (mismatch de V_th de fabricación) y ruido físico en las celdas metaestables: 512 bytes de SRAM bastan para extraer 128 bits verdaderamente aleatorios que pasan los tests NIST de runs, entropía aproximada y block frequency. Paper fundacional del uso dual identidad/entropía.
  DOI: 10.1109/TC.2008.212 — URL: https://ieeexplore.ieee.org/document/4674345/

- **Guajardo, Kumar, Schrijen y Tuyls (CHES 2007, LNCS 4727:63–80)** — *"FPGA Intrinsic PUFs and Their Use for IP Protection"* `[guajardo2007fpga]`. Primera construcción de PUF intrínseca basada en SRAM (en FPGA) con protocolos de protección de IP; establece las métricas de intra/inter-distancia de Hamming que se usan para separar huella (estable) de ruido (entropía).
  DOI: 10.1007/978-3-540-74735-2_5 — URL: https://link.springer.com/chapter/10.1007/978-3-540-74735-2_5

- **van der Leest, van der Sluis, Schrijen, Tuyls y Handschuh (2012)** — *"Efficient Implementation of True Random Number Generator Based on SRAM PUFs"* (Cryptography and Security: From Theory to Applications, LNCS 6805) `[vanderleest2012efficient]`. Cuantifica la **min-entropía del ruido** de los patrones de arranque de SRAMs comerciales y aplica un algoritmo de conditioning para obtener semillas de 256 bits con entropía completa: la referencia práctica para dimensionar cuánta SRAM se necesita por semilla.
  DOI: 10.1007/978-3-642-28368-0_20 — URL: https://link.springer.com/chapter/10.1007/978-3-642-28368-0_20

- **SRAM-PUF en el ESP32 concretamente**:
  - **esp32_puflib (D. Staníček et al., GitHub)** `[staniond2026puflib]`: librería que implementa una SRAM-PUF en la familia ESP32 leyendo RTC SLOW memory tras cortes de alimentación controlados, con corrección de errores; demuestra la viabilidad práctica en este SoC.
    URL: https://github.com/staniond/esp32_puflib
  - **Hilo del foro oficial de Espressif sobre wake stubs y SRAM no inicializada** `[esp32com2026wakestub]`: leer SRAM virgen exige un *deep sleep wake stub* muy temprano; empíricamente, los primeros 0x1320 bytes de SRAM1 y 0x6E0 de SRAM2 ya llegan inicializados por la ROM de arranque — restricción de diseño esencial para usar SRAM-PUF como fuente del harvester en el ESP32.
    URL: https://esp32.com/viewtopic.php?t=24384

No se ha localizado **ningún paper revisado por pares que caracterice la min-entropía de la SRAM del ESP32** (solo implementaciones open-source y proyectos de curso), lo que constituye parte del hueco que este TFM aborda.

---

## 7. MQTT-TLS en el ESP32 y el papel del RNG en la seguridad

- **ESP-TLS (ESP-IDF)** `[espressif2026esptls]`: capa de abstracción TLS de ESP-IDF sobre **mbedTLS** (por defecto; wolfSSL opcional); los ejemplos oficiales (https_request, MQTT sobre TLS) la utilizan. URL: https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/protocols/esp_tls.html
- **Mbed TLS en ESP-IDF** `[espressif2026mbedtls]`: mbedTLS implementa TLS 1.2/1.3 y criptografía X.509 con aceleración hardware (AES, SHA, RSA/bignum) en el ESP32; su módulo de entropía se alimenta de `mbedtls_hardware_poll()` → `esp_fill_random()` `[espressif2026esphardware]`, de modo que **las claves efímeras ECDHE, los IV/nonces y los session IDs de cada handshake TLS dependen directamente del RNG hardware objeto de este TFM**. URL: https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/protocols/mbedtls.html
- **Salles y Farias (Sensors, 23(5):2538, 2023)** — *"TLS Protocol Analysis Using IoTST — An IoT Benchmark Based on Scheduler Traces"* `[salles2023iotst]`: benchmark con trazas del planificador en ESP32; midió handshakes TLS 1.3 con distintas suites: Curve25519+RSA logra ~4× de mejora frente a la peor combinación (P-256+ECDSA) a igual nivel de seguridad. Cuantifica el coste del handshake que un RNG lento o bloqueante agravaría.
  DOI: 10.3390/s23052538 — URL: https://www.mdpi.com/1424-8220/23/5/2538
- **Evaluación empírica de MQTT sobre TLS en ESP32 (Applied Sciences, 15(15):8398, 2025)** `[mdpi2025mqttv2x]`: mide corriente instantánea, energía acumulada, latencia extremo a extremo y huella de memoria de MQTT+TLS 1.2 (mbedTLS/ESP-IDF) en nodos ESP32 para casos V2X: el sobrecoste dominante se concentra en el handshake — de nuevo, donde interviene el RNG.
  URL: https://www.mdpi.com/2076-3417/15/15/8398
- **RFC 4086 — "Randomness Requirements for Security" (Eastlake, Schiller, Crocker; BCP 106, 2005)** `[eastlake2005rfc4086]`: mejor práctica del IETF: la seguridad de claves, nonces y cookies depende de aleatoriedad impredecible; el uso de procesos pseudoaleatorios mal sembrados produce "pseudo-seguridad". Marco normativo que conecta el RNG del ESP32 con la seguridad de MQTT-TLS.
  URL: https://www.rfc-editor.org/rfc/rfc4086
- **Heninger, Durumeric, Wustrow y Halderman (USENIX Security 2012, Best Paper)** — *"Mining Your Ps and Qs: Detection of Widespread Weak Keys in Network Devices"* `[heninger2012mining]`. Escaneo de Internet completo (~22 M hosts TLS/SSH): el **0,75 % de los certificados TLS compartían claves por entropía insuficiente en el arranque** (y otro 1,70 % sospechoso), con factorización de claves RSA reales en dispositivos embebidos (routers, firewalls) que generaban claves justo tras el boot, antes de acumular entropía ("boot-time entropy hole"). Es el caso de estudio canónico de las consecuencias reales de la mala aleatoriedad en embebidos, directamente análogo al escenario "ESP32 generando claves sin WiFi/ADC habilitados".
  URL: https://www.usenix.org/conference/usenixsecurity12/technical-sessions/presentation/heninger (PDF: https://www.usenix.org/system/files/conference/usenixsecurity12/sec12-final228.pdf)

---

## 8. Gap identificado

Del análisis anterior se concluye que:

1. **Nadie ha publicado una caracterización NIST SP 800-22 completa (15 tests, proporción + uniformidad de p-valores, ≥1 Mbit×N secuencias) del RNG hardware del ESP32 original bajo condiciones operativas variables** — WiFi/BT habilitado vs. deshabilitado, `bootloader_random_enable()` activo, distintas temperaturas y tensiones, y en particular en los **modos de bajo consumo** (deep sleep / arranques en frío), que es exactamente el régimen contra el que advierte Espressif ("pseudo-random only"). Los trabajos existentes o bien prueban una única condición favorable (ICRAMET 2024; Dieharder de Espressif con WiFi ON), o bien usan otro chip de la familia con fuente secundaria de entropía (ESP32-C3, MDPI IoT 2026), o carecen de rigor estadístico (blogs).
2. **No existe una estimación pública de min-entropía SP 800-90B ni un modelo estocástico de la fuente** (a la manera de Baudet et al.) para el RNG del ESP32; la evidencia disponible es de caja negra ("pasa Dieharder").
3. **No hay ningún harvester de entropía multi-fuente validado para el ESP32 en modo bajo consumo** que combine las fuentes físicamente disponibles en el SoC — RNG hardware, ruido del SAR ADC, jitter entre relojes internos, SRAM-PUF al despertar de deep sleep, sensores — con un conditioner acreditado (SHA-256/HMAC, vetted según SP 800-90B, con aceleración hardware en el chip) y health tests embarcados; los antecedentes multi-fuente (Pawlowski 2015, Zhang-Wu 2023, pico_rand del RP2040) no se han portado ni validado sobre el ESP32.
4. La relevancia práctica del hueco está demostrada: la pila MQTT-TLS del ESP32 consume el RNG hardware en cada handshake (`mbedtls_hardware_poll`), y la historia (Heninger et al. 2012; Tillmanns et al. 2020) muestra que la aleatoriedad deficiente en el arranque de dispositivos embebidos produce compromisos masivos y silenciosos.

Este TFM cubre ese hueco: (i) caracterización sistemática SP 800-22 + SP 800-90B del RNG del ESP32 bajo matriz de condiciones operativas (RF on/off, ADC, temperatura, modos de energía), y (ii) diseño y validación de un harvester multi-fuente con conditioning acreditado y health tests para aplicaciones IoT seguras (MQTT-TLS) en bajo consumo.

---

## 9. Listado consolidado de fuentes (≥30)

| # | Clave BibTeX | Tipo | Tema |
|---|--------------|------|------|
| 1 | espressif2026trm | @misc | TRM ESP32, RNG_DATA_REG 0x3FF75144 |
| 2 | espressif2026random | @misc | Advertencia oficial ESP-IDF, esp_random() |
| 3 | espressif2026randomv50 | @misc | Versión v5.0 de la misma página |
| 4 | espressif2026bootrandom | @misc | bootloader_random.c |
| 5 | espressif2026esphardware | @misc | mbedtls_hardware_poll |
| 6 | kaell2024hwrng | @misc | Issue #14665 |
| 7 | espressif2021entropyissue | @misc | Issue #7598 |
| 8 | cheich2025esp32 | @misc | Blog: test informal ESP32 |
| 9 | androidcrypto2026esp32 | @misc | Tutorial Medium TRNG ESP32 |
| 10 | sunar2007provably | @article | RO-TRNG canónico |
| 11 | wold2009analysis | @article | Mejora Wold-Tan FPGA |
| 12 | bochard2010truerandomness | @article | True vs pseudo randomness |
| 13 | baudet2011security | @article | Modelo estocástico del jitter |
| 14 | valtchanov2008modeling | @misc | Jitter térmico/flicker/global |
| 15 | hajimiri1999jitter | @article | Jitter y ruido de fase en anillos |
| 16 | benea2024flicker | @article | Flicker en RO-TRNG (TCHES 2024) |
| 17 | rukhin2010statistical | @techreport | NIST SP 800-22 Rev 1a |
| 18 | turan2018sp80090b | @techreport | NIST SP 800-90B |
| 19 | nist2018entropytool | @misc | Herramienta 90B EntropyAssessment |
| 20 | nist2026sts | @misc | Software STS oficial |
| 21 | nist2021comments | @misc | Comentarios públicos revisión 800-22 |
| 22 | saarinen2022obsolete | @misc | Crítica "Clearly Obsolete" |
| 23 | iwasaki2017analysis | @misc | No-independencia de los tests |
| 24 | hidayatulloh2024esp32 | @inproceedings | NIST sobre ESP32 (LoRa) |
| 25 | castillo2026automated | @article | Framework NIST, ESP32-C3 |
| 26 | stmicro2026an4230 | @techreport | STM32 AN4230, AIS-31 |
| 27 | ngo2022sidechannel | @inproceedings | Side-channel RNG STM32 |
| 28 | nordic2026nrf52840 | @misc | nRF52840 RNG |
| 29 | raspberrypi2026rp2040 | @misc | RP2040 datasheet (ROSC) |
| 30 | dmo2022rp2040 | @misc | Blog ROSC RP2040 |
| 31 | raspberrypiforums2024csprng | @misc | Autocorrelación ROSC / pico_rand |
| 32 | scruss2013raspberrypi | @misc | HWRNG BCM2835 |
| 33 | tillmanns2020firmware | @inproceedings | RNG Bluetooth Broadcom |
| 34 | vonneumann1951various | @incollection | Corrector Von Neumann |
| 35 | impagliazzo1989pseudorandom | @inproceedings | Leftover Hash Lemma |
| 36 | dodis2004randomness | @inproceedings | Hash como extractores |
| 37 | krawczyk2010hkdf | @inproceedings | HKDF extract-then-expand |
| 38 | pawlowski2015harvesting | @article | Entropía de sensores IoT |
| 39 | zhang2023heterogeneous | @article | Fusión multi-fuente |
| 40 | kietzmann2021guideline | @article | Survey PRNG IoT (CSUR) |
| 41 | foreman2024statistical | @article | Extractores + tests |
| 42 | holcomb2009powerup | @article | FERNS SRAM-PUF/TRNG |
| 43 | guajardo2007fpga | @inproceedings | SRAM-PUF CHES 2007 |
| 44 | vanderleest2012efficient | @incollection | Min-entropía SRAM |
| 45 | staniond2026puflib | @misc | SRAM-PUF en ESP32 (lib) |
| 46 | esp32com2026wakestub | @misc | SRAM no inicializada ESP32 |
| 47 | espressif2026esptls | @misc | ESP-TLS |
| 48 | espressif2026mbedtls | @misc | mbedTLS en ESP-IDF |
| 49 | salles2023iotst | @article | Handshake TLS en ESP32 |
| 50 | mdpi2025mqttv2x | @misc | MQTT-TLS energía/latencia ESP32 |
| 51 | eastlake2005rfc4086 | @misc | RFC 4086 |
| 52 | heninger2012mining | @inproceedings | Mining Ps and Qs |
