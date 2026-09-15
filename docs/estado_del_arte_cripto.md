# Estado del arte: núcleos criptográficos simétricos en FPGA, DRBG, vectores de prueba y referencia ESP32

**TFM:** Motor criptográfico ligero en FPGA (Digilent Basys 3, Artix-7 XC7A35T) validado frente al ESP32.
**Alcance de este documento:** AES-128 (cifrado/descifrado), AES-CMAC, SHA-256 (acondicionamiento y Hash_DRBG), DRBG SP 800-90A, vectores CAVP/ACVP, interfaz SPI FPGA–ESP32 y el ESP32 como verificador. **No cubre** la fuente de entropía RO-TRNG ni su validación SP 800-90B (otro investigador).
**Fecha de consulta de todas las URL:** 11-09-2026.

**Convención de marcado.** Cada referencia lleva `[VERIFICADO]` si en esta sesión se abrió la fuente y se confirmó lo citado (en el caso de los PDF de NIST, el texto se extrajo localmente con pypdf y se leyó la sección citada), o `[NO VERIFICADO]` si el dato procede de un resumen de buscador, de una cita indirecta o de memoria. Los cálculos propios se marcan como **[cálculo propio]**. Las claves entre corchetes `[clave]` remiten a `refs_cripto.bib`.

---

## 0. Resumen ejecutivo (decisiones que el TFM debe justificar)

| Decisión | Recomendación | Base |
|---|---|---|
| Arquitectura AES-128 | Iterativa, 1 ronda/ciclo (10–11 ciclos/bloque), S-box en LUT | §1.4: 128 bit / 11 ciclos × 100 MHz = **1,16 Gbit/s** de núcleo; la interfaz SPI (≤ 40 Mbit/s) es el cuello de botella real, no el núcleo |
| S-box | Tabla 256×8 en LUT (síntesis directa), no BRAM ni campo compuesto | §1.3: cero latencia añadida, sin restricciones de reloj; el campo compuesto (Canright) optimiza puertas ASIC, no LUT6 |
| Acondicionamiento TRNG | SHA-256 (componente "vetted" SP 800-90B §3.1.5.1.1) | §2.3: fórmula de §3.1.5.1.2; con h_in ≥ 2·n_out la salida es prácticamente de entropía plena **[cálculo propio]** |
| DRBG | **CTR_DRBG con AES-128, sin función de derivación** | §3.2: reutiliza el núcleo AES ya existente; estado = 256 bit; requiere entrada de entropía plena de exactamente seedlen = 256 bit (SP 800-90A §10.2.1.3.1) — que es justo lo que da el acondicionador SHA-256 |
| MAC para reto-respuesta | **AES-CMAC** (SP 800-38B / RFC 4493), Tlen = 128 | §4.4: coste marginal ≈ 2 registros de 128 bit + lógica de subclaves; HMAC-SHA-256 costaría ≥ 2 compresiones extra por MAC |
| Interfaz | Esclavo SPI modo 0, SCLK ≤ 20–25 MHz, sobremuestreo con reloj de sistema de 100 MHz | §6: límite f_SCLK ≲ f_sys/4; ESP32 con GPIO matrix ≤ 40 MHz (≈ 26,7 MHz en full-duplex) |
| Verificación | KAT (CAVP .rsp / ACVP JSON) + interoperabilidad masiva + reto-respuesta, con el ESP32 (mbedtls + aceleradores) como oráculo | §7.4 |

---

## 1. Arquitecturas AES-128 para FPGA

### 1.1 Algoritmo de referencia (FIPS 197, actualización 2023)

- FIPS 197 fue publicado el 26-11-2001 y **actualizado el 9-05-2023 (NIST FIPS 197-upd1)**. La actualización es puramente editorial: "no technical changes" al algoritmo; se modernizó el frontal, se añadieron definiciones y diagramas de los tres key schedules, y se creó el Apéndice D que resume los cambios. DOI: 10.6028/NIST.FIPS.197-upd1. `[VERIFICADO]` [nist_2023_fips197] — https://csrc.nist.gov/pubs/fips/197/final y PDF https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.197-upd1.pdf (Tabla 3 y Apéndice D leídos).
- Tabla 3 ("Key-Block-Round Combinations"): AES-128 → Nk = 4 palabras (128 bit), Nb = 4 (bloque 128 bit), **Nr = 10 rondas**. `[VERIFICADO]`
- Consecuencia arquitectural: una implementación que ejecuta una ronda por ciclo necesita 10 ciclos de ronda; con la ronda inicial AddRoundKey y/o el registro de carga se llega a 11 ciclos por bloque. El key schedule puede calcularse "al vuelo" (una palabra-clave de ronda por ciclo, en paralelo con la ronda) o precomputarse en 11×128 bit de registros/BRAM.

### 1.2 Familias arquitecturales

| Familia | Datapath | Ciclos/bloque (AES-128) | Uso típico | Comentario |
|---|---|---|---|---|
| Iterativa (round-based) | 128 bit, 16 S-box (+4 para key schedule) | 10–11 | Bloque por bloque, cualquier modo (ECB/CBC/CMAC/CTR) | Compromiso área/velocidad estándar; la única razonable si el consumidor es un enlace serie |
| Desplegada / pipelined (10 etapas) | 10×128 bit, 160–200 S-box | 1 bloque/ciclo en régimen | Modos paralelizables (ECB, CTR, GCM) a Gbit/s | Inútil para CBC/CMAC (dependencia serie); 10× área |
| Sub-pipelined | Etapas dentro de la ronda | 1 bloque/ciclo, f mayor | Récords de throughput | Ídem |
| Compacta 32 bit | 4 S-box compartidas | ~40–50 | Área mínima con throughput medio | secworks/aes usa 4 S-box y tarda 46 ciclos/bloque `[VERIFICADO]` |
| Compacta 8 bit (ASIP) | 1–2 S-box, a menudo en BRAM | Cientos | Área extrema | Good & Benaissa 2005: 124 slices + 2 BRAM en Spartan-II XC2S15, 2,2 Mbit/s `[VERIFICADO]` |

Referencias clásicas de los extremos del espacio de diseño:
- Chodowiec y Gaj, CHES 2003: cifrado + descifrado + key schedule en **222 slices y 3 Block RAM** de un Spartan-II XC2S30. DOI 10.1007/978-3-540-45238-6_26 `[VERIFICADO: título/autores/DOI/páginas por Crossref; cifras por el resumen de Springer]` [chodowiec_2003_compact].
- Good y Benaissa, CHES 2005: diseño más rápido 25 Gbit/s en Spartan-III XC3S2000 (pipelined) y el más pequeño **124 slices + 2 BRAM, 2,2 Mbit/s** en Spartan-II XC2S15. DOI 10.1007/11545262_31 `[VERIFICADO: abstract leído del PDF]` [good_2005_fastest].

### 1.3 S-box: LUT vs BRAM vs campo compuesto

**S-box como tabla en LUT.** En la serie 7 (LUT6 con dos salidas O5/O6, más multiplexores MUXF7/MUXF8 por slice) una función de 8 entradas y 1 salida requiere 4 LUT6 + muxes; una S-box completa (8 salidas) ocupa del orden de 32 LUT6 + muxes, es decir ≈ 8 slices. Con 16 S-box de datos + 4 del key schedule, la parte no lineal de un AES iterativo ronda **≈ 640–700 LUT** **[cálculo propio a partir de la estructura CLB; no hay dato publicado para XC7A35T verificado]**. Ventajas: combinacional pura (sin ciclo extra), sin restricción de reloj, síntesis trivial desde una constante `case`/ROM. Dato empírico coherente: hadipourh/AES-VHDL (S-box LUT, 1 ronda/ciclo) ocupa **1104 LUT + 264 FF** para el cifrador AES-128 completo en Artix-7 xc7a200t-3 `[VERIFICADO]` [hadipour_aesvhdl].

**S-box en BRAM.** Un BRAM36 dual-port configurado como 2×(256×8) aloja 2 S-box → 20 S-box = 10 BRAM36 de los 50 del XC7A35T. Coste: la lectura es síncrona (1 ciclo de latencia), lo que obliga a partir la ronda en dos ciclos o a usar 200 MHz de reloj BRAM; interesa cuando las LUT escasean y las BRAM sobran. Chodowiec-Gaj y Good-Benaissa usan este enfoque en Spartan-II `[VERIFICADO]`.

**Campo compuesto (tower field).** Inversión en GF(2^8) descompuesta en GF((2^4)^2) y GF(((2^2)^2)^2):
- Satoh, Morioka, Takano y Munetoh, ASIACRYPT 2001: circuito Rijndael de 128 bit en **5,4 kpuertas** (CMOS 0,11 µm) con S-box de campo compuesto. DOI 10.1007/3-540-45682-1_15 `[VERIFICADO: título/DOI por Springer Link; cifra por el resumen]` [satoh_2001_compact].
- Canright, CHES 2005: explora 432 elecciones de base (polinomiales y **normales**) para los subcampos y optimiza las matrices de isomorfismo; "the best case improves on [Satoh] by 20%". DOI 10.1007/11545262_32 `[VERIFICADO: abstract leído del PDF de IACR]` [canright_2005_compact].
- Boyar y Peralta, SEA 2010: técnica de minimización lógica en dos pasos (primero reduce puertas no lineales, después la parte lineal); obtiene "the circuit with the smallest gate count yet constructed for the AES S-box". DOI 10.1007/978-3-642-13193-6_16 `[VERIFICADO: cita y abstract en la página de NIST]` [boyar_2010_minimization]. La cifra habitual de 32 AND + 83 XOR/XNOR = 115 puertas **no** aparece en el abstract consultado `[NO VERIFICADO]`.
- Relevancia para FPGA: estas métricas son de puertas ASIC (AND/XOR de 2 entradas). Una LUT6 absorbe cualquier función de 6 entradas, así que la ventaja del campo compuesto se diluye y suele perder frente a la tabla directa en profundidad lógica (≈ 20–30 niveles XOR vs 2–3 niveles LUT). Su nicho en FPGA es el enmascaramiento contra side-channel (fuera del alcance, §8), no el área. **[razonamiento propio; no se ha encontrado una comparación LUT-a-LUT en Artix-7 verificada]**

### 1.4 Datos publicados de área/frecuencia/throughput (Artix-7 / Spartan-6 / Kintex-7)

**No se ha localizado ningún dato revisado por pares y verificable para el XC7A35T concreto de la Basys 3.** Los datos siguientes son de repositorios abiertos con tablas de implementación en Artix-7 (xc7a200t, misma arquitectura CLB que el XC7A35T, distinto speed grade y tamaño) y del propio DS180.

| Diseño | Dispositivo | Área | f_max | Ciclos/bloque | Throughput | Fuente |
|---|---|---|---|---|---|---|
| secworks/aes (enc+dec+key exp., 4 S-box compartidas) | Artix-7 200T-3 | 2298 slices, 2989 FF | 97 MHz | 46 | 128·97/46 = **270 Mbit/s** [cálculo propio] | README `[VERIFICADO]` [strombergson_aes] |
| secworks/aes | Spartan-6 LX-3 | 2576 slices, 3000 FF | 100 MHz | 46 | 278 Mbit/s [cálculo propio] | ídem `[VERIFICADO]` |
| hadipourh/AES-VHDL cifrador (1 ronda/ciclo, S-box LUT) | Artix-7 xc7a200t-3 | 1104 LUT, 264 FF | 294,4 MHz | 10 | **3,77 Gbit/s** | README `[VERIFICADO]` [hadipour_aesvhdl] |
| hadipourh/AES-VHDL descifrador | Artix-7 xc7a200t-3 | 1490 LUT, 260 FF | 253,8 MHz | 10 | 3,25 Gbit/s | ídem `[VERIFICADO]` |
| hadipourh/AES-VHDL cifrador | Spartan-6 xc6slx75-3 | 1104 LUT, 264 FF | 172,0 MHz | 10 | 2,2 Gbit/s | ídem `[VERIFICADO]` |
| Chodowiec-Gaj 2003 (enc+dec+key) | Spartan-II XC2S30 | 222 slices + 3 BRAM | — | — | — | [chodowiec_2003_compact] `[VERIFICADO parcial]` |
| Good-Benaissa 2005 (mínimo) | Spartan-II XC2S15 | 124 slices + 2 BRAM | — | — | 2,2 Mbit/s | [good_2005_fastest] `[VERIFICADO]` |
| OpenCores aes_core (Usselmann 2002) | Spartan-IIe | — | 101 MHz | — | 1,08 Gbit/s | página del proyecto `[VERIFICADO]` [usselmann_2002_aescore] |

Recursos del dispositivo objetivo (DS180 v2.6.1, Tabla 4, fila XC7A35T): **33 280 celdas lógicas, 5200 slices, 400 kbit RAM distribuida, 90 DSP48E1, 50 BRAM36 (1800 kbit), 5 CMT, 1 XADC, 250 E/S máx.** `[VERIFICADO]` [xilinx_2020_ds180]. Cada slice tiene 4 LUT6 y 8 flip-flops (manual Basys 3) `[VERIFICADO]` → 20 800 LUT y 41 600 FF **[cálculo propio]**.

### 1.5 Comprobación del cálculo de throughput y justificación de la decisión

- Núcleo iterativo a 100 MHz (reloj de la Basys 3): 128 bit / 11 ciclos × 100 MHz = **1,164 Gbit/s**; con 10 ciclos, 1,28 Gbit/s. **[cálculo propio]**
- **El enunciado "~100 Mbps" infravalora el núcleo en un factor ≈ 10**; la cifra correcta es ≈ 1,1–1,3 Gbit/s de núcleo. Incluso la variante compacta de secworks (46 ciclos, 97 MHz) da 270 Mbit/s.
- El límite real lo pone la interfaz: con SPI a 40 MHz (máximo del ESP32 vía GPIO matrix, §6.2) el enlace transporta ≤ 40 Mbit/s → un bloque de 128 bit llega cada 3,2 µs y el núcleo tarda 0,11 µs → ocupación del AES ≈ 3,4 %. **[cálculo propio]** Cualquier pipelining sería área desperdiciada; a la inversa, una arquitectura de 8/32 bit también bastaría, pero la iterativa de 128 bit es la más simple de verificar (una ronda = una función combinacional pura comprobable contra FIPS 197 Apéndice B/C) y la que hace más directo compartir el núcleo entre ECB/CBC, CMAC y CTR_DRBG.
- Presupuesto de área estimado para todo el motor (sin TRNG): AES enc+dec ≈ 2600–3000 LUT (extrapolando hadipourh: 1104 + 1490 + control) o hasta ≈ 2300 slices si se toma secworks completo; SHA-256 ≈ 750 slices (secworks, §2.2); CTR_DRBG + CMAC + SPI + control ≈ 300–600 LUT. Total ≈ 1500–3000 slices de 5200 → **cabe con margen en el XC7A35T**, pero el AES con descifrado es la partida dominante y conviene evaluar el "Equivalent Inverse Cipher" (FIPS 197 §5.3.5) frente a datapaths separados. **[estimación propia a partir de las cifras verificadas de los repositorios]**

---

## 2. SHA-256 en FPGA

### 2.1 Algoritmo (FIPS 180-4)

FIPS 180-4 (agosto 2015, DOI 10.6028/NIST.FIPS.180-4) `[VERIFICADO]` [nist_2015_fips1804]: SHA-256 procesa bloques de **512 bit** en palabras de **32 bit**, con **64 rondas** ("For t = 0 to 63", §6.2.2), y produce un resumen de 256 bit. Relleno (§5.1.1): bit '1', k ceros y la longitud del mensaje en 64 bit, de modo que la longitud total sea múltiplo de 512 `[VERIFICADO: PDF leído]`.

### 2.2 Arquitectura básica y área típica

- Núcleo iterativo: 8 registros de trabajo a…h (256 bit), planificador de mensaje W_t implementado como registro de desplazamiento de 16×32 bit con las funciones σ0/σ1, ROM de 64 constantes K_t, y las funciones Σ0/Σ1/Ch/Maj más dos cadenas de sumadores de 32 bit por ronda (T1, T2). Un bloque cuesta 64 ciclos de ronda + carga/finalización: secworks/sha256 declara **66 ciclos de latencia** `[VERIFICADO]`. El camino crítico es la cadena de sumadores de T1 (≈ 4–5 sumas de 32 bit encadenadas), lo que explica f_max de 100–150 MHz sin precomputación en la serie 7.
- El **relleno no suele implementarse en el núcleo**: secworks/sha256 indica "the core does NOT implement padding of final block. The caller is expected to handle padding" `[VERIFICADO]`. El acelerador SHA del ESP32 tampoco rellena (TRM §16.3.1, §7.1) — buena simetría para el TFM: el relleno se hace en el controlador (FPGA) y en software (ESP32).

| Diseño | Dispositivo | Área | f_max | Ciclos/bloque | Throughput | Fuente |
|---|---|---|---|---|---|---|
| secworks/sha256 (iterativo) | Artix-7 | 2471 LUT, 747 slices, 1930 FF | 108 MHz | 66 | 512·108/66 = **838 Mbit/s** [cálculo propio] | README `[VERIFICADO]` [strombergson_sha256] |
| secworks/sha256 | Spartan-6 | 2012 LUT, 1929 FF | 70 MHz | 66 | 543 Mbit/s [cálculo propio] | ídem `[VERIFICADO]` |
| Citado en Santos et al. 2024 como ref. [38] | Artix-7 xc7a200t | 1310 LUT, 881 FF, 327 slices | 141,84 MHz | — | 1404 Mbit/s | `[NO VERIFICADO: cita indirecta; el artículo original no se pudo abrir]` [santos_2024_sha256] |
| Li et al. 2019 (fully-pipelined, BRAM) | Kintex-7 | — | > 300 MHz | — | 154,88 Gbit/s; 10,94 Mbit/s/slice | resumen vía Semantic Scholar `[VERIFICADO: DOI 10.1016/j.micpro.2019.03.002 y abstract]` [li_2019_hashing] |
| Baldanzi et al. 2020 (CSPRNG SHA-2 / Hash-DRBG) | FPGA (dispositivo no confirmado) | — | — | — | 690 Mbit/s en FPGA; 19,67 Gbit/s ASIC 7 nm | Sensors 20(7):1869, DOI 10.3390/s20071869 `[VERIFICADO: DOI/título/autores por Crossref; cifras por resumen de buscador → NO VERIFICADO]` [baldanzi_2020_csprng] |

Conclusión: el SHA-256 iterativo es del mismo orden de área que el AES compacto (≈ 750 slices) y sobra en velocidad (≈ 0,8 Gbit/s frente a un TRNG que rara vez superará decenas de Mbit/s de datos brutos).

### 2.3 SHA-256 como componente de acondicionamiento (SP 800-90B §3.1.5)

SP 800-90B (enero 2018, DOI 10.6028/NIST.SP.800-90B) `[VERIFICADO: PDF extraído y §3.1.5 leído]` [turan_2018_sp80090b]:

- **§3.1.5.1.1 Lista de componentes de acondicionamiento "vetted"** (cita textual resumida): con clave — (1) HMAC (FIPS 198) con cualquier hash aprobado, (2) CMAC (SP 800-38B) con AES, (3) CBC-MAC (Apéndice F) con AES, sólo para este uso; sin clave — (1) cualquier hash aprobado de FIPS 180/202, (2) Hash_df de SP 800-90A, (3) Block_Cipher_df de SP 800-90A con AES.
- **Tabla 1 (anchura interna mínima nw y longitud de salida n_out):** para una función hash, nw = n_out = tamaño de salida del hash (256 para SHA-256); para CMAC/CBC-MAC, 128; para Block_Cipher_df, el tamaño de clave AES.
- **§3.1.5.1.2 Estimación de entropía con componente vetted** ("given the assurance of correct implementation by CAVP testing"): h_out = Output_Entropy(n_in, n_out, nw, h_in), con
  1. P_high = 2^(−h_in); P_low = (1 − P_high)/(2^(n_in) − 1)
  2. n = min(n_out, nw)
  3. ψ = 2^(n_in − n)·P_low + P_high
  4. U = 2^(n_in − n) + sqrt(2·n·2^(n_in − n)·ln 2)
  5. ω = U·P_low
  6. h_out = −log2(max(ψ, ω))
  Notas del propio documento: la fórmula deriva del Teorema 1 de [RaSt98]; "Vetted conditioning components are permitted to claim full entropy outputs"; si se trunca la salida, la entropía se reduce proporcionalmente; n_in sólo incluye la fuente de ruido primaria.
- **Componentes no vetted (§3.1.5.2):** h_out = min(Output_Entropy(·), **0,999·n_out**, h'·n_out) — el factor 0,999 sólo aplica a componentes no vetted `[VERIFICADO]`.
- **Evaluación numérica para SHA-256 (n_out = nw = 256) [cálculo propio]:**
  - n_in = 512, h_in = 256 (0,5 bit/bit): ψ ≈ 2^(−255), ω ≈ 2^(−256) → **h_out ≈ 255 bit** (se pierde ≈ 1 bit).
  - n_in = 1024, h_in = 512 (h_in ≥ 2·n_out): ψ ≈ 2^(−256)(1 + 2^(−256)), ω ≈ 2^(−256) → **h_out ≈ 256 bit** (entropía plena a efectos prácticos).
  - Regla de diseño: alimentar el SHA-256 con **al menos 2·256 = 512 bit de min-entropía estimada** por cada salida de 256 bit (por ejemplo, con H = 0,5 bit/bit del RO-TRNG, dos bloques de 512 bit = 1024 bit brutos por semilla). Esto coincide con la práctica de SP 800-90C para salidas de entropía plena, aunque aquí se justifica únicamente por la fórmula de 90B.
- Consecuencia para el TFM: el mismo núcleo SHA-256 sirve para (a) acondicionar el TRNG, (b) Hash_df si se eligiera Hash_DRBG, y (c) HMAC si hiciera falta; pero con CTR_DRBG sin df sólo se usa para (a).

### 2.4 Uso en Hash_DRBG (SP 800-90A Rev. 1, Tabla 2)

Para SHA-256: outlen = 256, **seedlen = 440 bit**, max_length de entrada de entropía y de cadenas = 2^35 bit, max_number_of_bits_per_request = **2^19**, reseed_interval = **2^48** `[VERIFICADO: Tabla 2 leída]` [barker_2015_sp80090ar1]. Hash_DRBG usa Hash_df (§10.3.1) en la instanciación y el reseed; el estado interno son V y C de 440 bit más el contador, y la generación exige una suma modular de 440 bit por bloque (V = V + H + C + reseed_counter mod 2^440), lo que en FPGA añade sumadores anchos que el CTR_DRBG no necesita.

---

## 3. DRBG según SP 800-90A Rev. 1

### 3.1 Marco normativo y estado

- **SP 800-90A Rev. 1** (junio 2015, DOI 10.6028/NIST.SP.800-90Ar1) define Hash_DRBG, HMAC_DRBG y CTR_DRBG (Dual_EC_DRBG fue retirado en esta revisión). Soporta sólo cuatro fortalezas de seguridad: **112, 128, 192 y 256 bit** (§10, texto leído). `[VERIFICADO]` [barker_2015_sp80090ar1]
- **Rev. 2 en preparación:** el 4-09-2025 NIST abrió una "pre-draft call for comments" (hasta el 4-11-2025) para una segunda revisión: alineación con SP 800-90C, DRBG basado en XOF (SHAKE), retirada de TDES y SHA-1, y sustitución de nonces por mayores requisitos de entrada de entropía `[VERIFICADO: la noticia; los cambios concretos proceden del resumen de buscador → NO VERIFICADO en detalle]` [nist_2025_sp80090a_predraft]. Nada de ello afecta a CTR_DRBG-AES-128.
- **SP 800-90C** está **final desde septiembre de 2025** (DOI 10.6028/NIST.SP.800-90C): construcciones RBG1, RBG2, RBG3 y RBGC que combinan fuentes de entropía 90B con DRBG 90A `[VERIFICADO]` [barker_2025_sp80090c]. La construcción del TFM (fuente física propia + DRBG en el mismo dispositivo) se corresponde con el espíritu de un RBG2; **no se ha verificado el detalle de los requisitos de 90C y no debe afirmarse conformidad**.
- **SP 800-108 Rev. 1 upd1** (KDF con HMAC, CMAC o KMAC; agosto 2022, actualizado 2-02-2024; DOI 10.6028/NIST.SP.800-108r1-upd1) `[VERIFICADO]` [chen_2022_sp800108r1]: relevante sólo si el TFM deriva claves de sesión a partir de una clave maestra; con CMAC ya disponible, el KDF en modo contador con PRF = CMAC-AES es gratis en área.

### 3.2 Comparación para implementación en FPGA

Parámetros normativos (Tabla 3 de SP 800-90A r1, columna AES-128) `[VERIFICADO: Tabla 3 leída]`: blocklen = 128, keylen = 128, **seedlen = outlen + keylen = 256**, ctr_len entre 4 y 128, reseed_interval = **2^48**, max_number_of_bits_per_request = min(B, 2^19) con B = (2^ctr_len − 4)·blocklen; **sin función de derivación:** min_length = max_length = seedlen (la entrada de entropía debe tener exactamente 256 bit) y las cadenas de personalización/additional_input están limitadas a seedlen. §10.2.1.3.1: "When instantiation is performed using this method, full-entropy input is required, and a nonce is not used" `[VERIFICADO]`. §8.6.x: la df es opcional "if either an approved RBG or an entropy source provides full entropy output when entropy input is requested"; §11.x exige documentar que la implementación "can only be used when full entropy input is available" `[VERIFICADO]`.

| Criterio | Hash_DRBG (SHA-256) | HMAC_DRBG (SHA-256) | CTR_DRBG (AES-128, sin df) |
|---|---|---|---|
| Primitiva | SHA-256 | SHA-256 ×2 por HMAC | AES-128 sólo cifrado |
| Estado interno | V 440 + C 440 + contador | K 256 + V 256 + contador | **Key 128 + V 128 + contador (48)** |
| Coste por 128 bit de salida | ½ compresión SHA (256 bit/compresión) + suma mod 2^440 | 1 HMAC = 2 compresiones por 256 bit | **1 AES (10–11 ciclos)** |
| Coste de Update tras generar | 1 hash + sumas anchas | ≥ 2 HMAC (4 compresiones), 4 si hay additional_input | 2 AES (seedlen/blocklen = 2 bloques) |
| Instanciación / reseed | Hash_df: varias compresiones | HMAC×2–4 | 2 AES (Update con entropía XOR) |
| Requisito de entrada | Cualquier entropía ≥ security_strength (df hace la extracción) | Ídem | **Entropía plena de exactamente 256 bit** (lo garantiza el acondicionador SHA-256, §2.3) |
| Lógica extra en FPGA | Sumadores 440 bit, mux de anchos | Padding ipad/opad, doble bloque | Contador 128 bit (incremento mod 2^ctr_len), XOR de 256 bit |
| Vectores CAVP | Hash_DRBG.rsp | HMAC_DRBG.rsp | CTR_DRBG.rsp (variantes con/sin df) `[VERIFICADO]` |
| Análisis de seguridad | Robustez probada en el ROM (con salvedad) | Robustez probada; **sin additional_input no alcanza ni forward security** | Sin prueba formal en Woodage-Shumow; análisis práctico de fuga parcial de estado |

Fuente del análisis de seguridad: Woodage y Shumow, "An Analysis of NIST SP 800-90A", EUROCRYPT 2019, LNCS 11476, DOI 10.1007/978-3-030-17656-3_6 (ePrint 2018/349) `[VERIFICADO: abstract leído del PDF de IACR; DOI por Crossref]` [woodage_2019_analysis]. Su advertencia principal para el TFM: la flexibilidad del estándar permite elecciones de implementación que agravan la fuga parcial de estado; conviene (a) no exponer nunca Key/V, (b) hacer Update tras cada generate (obligatorio) y (c) reseed periódico muy por debajo de 2^48.

**Conclusión:** si el AES ya existe, **CTR_DRBG sin df es la opción más barata** (≈ 300 bit de estado, un contador y XORs; ninguna primitiva adicional) y la más rápida (128 bit por ~11 ciclos). El precio es normativo, no de área: hay que acreditar que la entrada de entropía es de entropía plena, que es exactamente lo que aporta el acondicionador SHA-256 vetted con h_in ≥ 2·n_out (§2.3). Hash_DRBG sólo tendría sentido si el AES no existiera; HMAC_DRBG es el más caro de los tres en FPGA. Como muestra de que el CTR-DRBG-AES-128 en FPGA es una elección corriente: Xie et al. 2025 implementan justamente ese prototipo para estudiar inyección de fallos (Electronics 14(18):3702, DOI 10.3390/electronics14183702) `[VERIFICADO: DOI/abstract vía Semantic Scholar; sin cifras de área]` [xie_2025_ctrdrbg].

### 3.3 Requisitos de reseed y fortaleza para el TFM

- Fortaleza declarada: 128 bit (AES-128) — Tabla 3 remite a SP 800-57 para las fortalezas soportadas; con AES-128 la máxima es 128.
- reseed_interval ≤ 2^48 peticiones; max 2^19 bit (64 kB) por petición. Recomendación de diseño: reseed cada N ≤ 2^20 peticiones o por temporizador, alimentado por el acondicionador; prediction_resistance opcional (implica reseed antes de cada generate).
- Health tests obligatorios (§11.3): known-answer tests al arrancar de instantiate/generate/reseed con vectores fijos; en FPGA se implementan comparando contra constantes de un vector CAVP grabado en ROM.

### 3.4 Vectores de prueba oficiales

- **CAVP DRBG:** https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/drbg/drbgtestvectors.zip (13,7 MB). Contiene tres zips: `drbgvectors_no_reseed.zip`, `drbgvectors_pr_false.zip`, `drbgvectors_pr_true.zip`; cada uno con `CTR_DRBG.rsp`, `Hash_DRBG.rsp`, `HMAC_DRBG.rsp`, los `.txt` de valores intermedios y un `Readme.txt` `[VERIFICADO: zip descargado y listado]` [nist_cavp_drbg]. Los `.rsp` de CTR_DRBG incluyen secciones `[AES-128 no df]` / `[AES-128 use df]` con EntropyInput, Nonce, PersonalizationString, AdditionalInput y ReturnedBits (formato de texto clave = valor hex).
- **ACVP (formato JSON actual):** repositorio https://github.com/usnistgov/ACVP-Server, carpeta `gen-val/json-files/` con muestras para todos los algoritmos; carpetas relevantes: `ctrDRBG-1.0`, `ctrDRBG-SP800-90Ar1`, `hashDRBG-1.0`, `hmacDRBG-1.0`, `ACVP-AES-ECB-1.0`, `ACVP-AES-CBC-1.0`, `CMAC-AES-1.0`, `SHA2-256-1.0`, `HMAC-SHA2-256-1.0`, `ConditioningComponent-AES-CBC-MAC-Sp800-90B`; cada carpeta contiene `registration.json`, `prompt.json`, `internalProjection.json`, `expectedResults.json`, `validation.json` `[VERIFICADO: listado por la API de GitHub]` [nist_acvp_server]. Licencia NIST (dominio público EE. UU., "AS IS").
- Estado del programa: CAVS está "deprecated by ACVTS"; el servidor **Demo ACVTS es gratuito** para cualquier interesado, mientras que el de producción sólo lo usan laboratorios NVLAP y es la única vía para certificados `[VERIFICADO]` [nist_cavp_home]. Para el TFM basta el Demo o los JSON de muestra.

---

## 4. AES-CMAC (SP 800-38B) y alternativa HMAC-SHA-256

### 4.1 Norma

SP 800-38B (mayo 2005; **actualización 6-10-2016**, DOI 10.6028/NIST.SP.800-38B) `[VERIFICADO: PDF extraído; erratas leídas]` [nist_2016_sp80038b]. Cambios de 2016 según su tabla de erratas: reorganización del frontal (Sec. 2 pasa a "Conformance Testing"), **los ejemplos del Apéndice D se retiraron y se publican aparte** en la página de ejemplos de NIST, y se actualizó la bibliografía. NIST anunció en 2025 la intención de revisar 38B y 38C `[VERIFICADO: página CSRC]`.

### 4.2 Algoritmo

- Constante R_128 = 0^120 || 10000111 (= 0x…87), representación del polinomio irreducible x^128 + x^7 + x^2 + x + 1 (§5.3) `[VERIFICADO]`.
- **Subclaves (§6.1):** L = CIPH_K(0^128); si MSB(L) = 0, K1 = L << 1, si no K1 = (L << 1) ⊕ R_b; análogamente K2 desde K1. L, K1 y K2 son secretos; pueden precomputarse y almacenarse con la clave `[VERIFICADO]`.
- **Generación (§6.2):** dividir M en bloques; si el último es completo M_n = K1 ⊕ M_n*, si no M_n = K2 ⊕ (M_n* || 10^j); CBC-MAC con IV = 0; T = MSB_Tlen(C_n) `[VERIFICADO]`.
- **Apéndice A:** "For most applications, a value for Tlen that is at least 64 should provide sufficient protection against guessing attacks"; Tlen < 64 sólo con límites de verificación adicionales `[VERIFICADO]`. **Apéndice B:** para mayor confianza, limitar la clave a **2^48 bloques de mensaje** con bloque de 128 bit `[VERIFICADO]`.
- Coste hardware sobre un AES existente: registro L/K1/K2 (o sólo K1, derivando K2 al vuelo), un registro de encadenamiento de 128 bit, lógica de relleno del último bloque y un desplazador de 1 bit con XOR condicional. **≈ 300–400 LUT/FF** **[estimación propia]**.

### 4.3 Vectores de prueba (RFC 4493 §4, copiados literalmente; coinciden con el fichero de ejemplos de NIST)

Fuente: https://www.rfc-editor.org/rfc/rfc4493 `[VERIFICADO]` [song_2006_rfc4493] y https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/AES_CMAC.pdf `[VERIFICADO: PDF extraído]` [nist_cmac_examples].

```
K  = 2b7e1516 28aed2a6 abf71588 09cf4f3c
L  = 7df76b0c 1ab899b3 3e42f047 b91b546f        (AES_K(0^128), del fichero NIST)
K1 = fbeed618 35713366 7c85e08f 7236a8de
K2 = f7ddac30 6ae266cc f90bc11e e46d513b

Ejemplo 1, Mlen = 0:   M = <vacío>
  CMAC = bb1d6929 e9593728 7fa37d12 9b756746
Ejemplo 2, Mlen = 16:  M = 6bc1bee2 2e409f96 e93d7e11 7393172a
  CMAC = 070a16b4 6b4d4144 f79bdd9d d04a287c
Ejemplo 3, Mlen = 40:  M = 6bc1bee2 2e409f96 e93d7e11 7393172a
                           ae2d8a57 1e03ac9c 9eb76fac 45af8e51
                           30c81c46 a35ce411
  CMAC = dfa66747 de9ae630 30ca3261 1497c827
Ejemplo 4, Mlen = 64:  M = 6bc1bee2 2e409f96 e93d7e11 7393172a
                           ae2d8a57 1e03ac9c 9eb76fac 45af8e51
                           30c81c46 a35ce411 e5fbc119 1a0a52ef
                           f69f2445 df4f9b17 ad2b417b e66c3710
  CMAC = 51f0bebf 7e3b9d92 fc497417 79363cfe
```
Nota: el fichero de ejemplos de NIST usa Mlen = 20 bytes en su ejemplo 3 (tag 7d85449e a6ea19c8 23a7bf78 837dfade) en lugar de los 40 bytes del RFC; los ejemplos 1, 2 y 4 son idénticos en ambas fuentes `[VERIFICADO]`.

Vectores masivos: `cmactestvectors.zip` (8,8 MB) con `CMACGenAES128.rsp` y `CMACVerAES128.rsp` (además de 192/256 y TDES) en https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/mac/cmactestvectors.zip `[VERIFICADO: descargado y listado]` [nist_cavp_modes]. ACVP: carpeta `CMAC-AES-1.0` `[VERIFICADO]`.

### 4.4 CMAC vs HMAC-SHA-256 para el reto-respuesta

| | AES-CMAC-128 | HMAC-SHA-256 |
|---|---|---|
| Primitiva reutilizada | AES (ya presente para cifrado y CTR_DRBG) | SHA-256 (presente para acondicionamiento) |
| Coste por MAC de un reto de 16 B | 1 AES (más 1 AES para L, precomputable) ≈ 11–22 ciclos | 2 compresiones mínimo (interna + externa) ≈ 132 ciclos, más gestión de ipad/opad y relleno doble |
| Longitud de etiqueta | 128 bit (Tlen ≥ 64 recomendado) | 256 bit (truncable) |
| Verificador ESP32 | `mbedtls_cipher_cmac()` (requiere `CONFIG_MBEDTLS_CMAC_C`, por defecto `n` en ESP-IDF) `[VERIFICADO]` | `mbedtls_md_hmac()`; acelerador SHA disponible |
| Componente 90B vetted | Sí (CMAC con AES) | Sí (HMAC) |
| Estado normativo | SP 800-38B (revisión anunciada, sin cambios publicados) | FIPS 198-1 (estable) |

**Elección:** AES-CMAC. El reto-respuesta es un intercambio de bloques cortos donde la latencia y el área marginal son mínimas con CMAC; mantiene el SHA-256 dedicado al acondicionamiento (y evita compartirlo entre dos controladores con arbitraje) y da una etiqueta de 128 bit suficiente para autenticar un nonce de 128 bit. HMAC-SHA-256 queda como alternativa documentada si se prefiriese separar dominios de clave (una clave AES para confidencialidad, una clave HMAC para autenticación).

---

## 5. Implementaciones abiertas de referencia (para estudiar, no para copiar)

| Proyecto | URL | Lenguaje | Licencia | Arquitectura | Verificación declarada | Resultados FPGA | Estado |
|---|---|---|---|---|---|---|---|
| **secworks/aes** (J. Strömbergson) | https://github.com/secworks/aes | Verilog 2001 | BSD-2-Clause | Iterativo a nivel de palabra, 4 S-box compartidas entre datapath y key schedule, 46 ciclos/bloque, enc y dec separables (quitar dec ahorra ≈ 50 %) | Testbench `tb_aes.v` con vectores de **FIPS 197 Apéndice C y SP 800-38A** (clave 2b7e1516…, texto 6bc1bee2…) | Artix-7 200T-3: 2298 slices, 2989 FF, 97 MHz; Spartan-6: 2576 slices, 100 MHz; Cyclone V: 2624 ALM, 96 MHz | "well tested and mature", usado en FPGA y ASIC | `[VERIFICADO]` [strombergson_aes] |
| **secworks/sha256** | https://github.com/secworks/sha256 | Verilog 2001 | BSD-2-Clause | Iterativo, 66 ciclos/bloque, interfaz 512→256, sin relleno; variantes streaming y AXI4 | Testbench con ejemplos oficiales de NIST (SHA256.pdf: "abc" → ba7816bf…, mensaje de 2 bloques) y modelo Python | Artix-7: 2471 LUT, 747 slices, 1930 FF, 108 MHz; Spartan-6: 2012 LUT, 70 MHz; Zynq-7020: 2555 LUT, 78 MHz | "mature and ready for use" | `[VERIFICADO]` [strombergson_sha256] |
| **OpenCores aes_core** (R. Usselmann, 2002) | https://opencores.org/projects/aes_core | Verilog | no indicada en la página (los fuentes llevan BSD-style de Usselmann `[NO VERIFICADO]`) | Enc/dec separados, key expansion integrada, orientado a Spartan | Vectores "del sitio de NIST" añadidos; los autores pedían vectores "oficiales" | Spartan-IIe 101 MHz (1,08 Gbit/s); UMC 0,18 µm 265 MHz | Estable, último cambio 2009 | `[VERIFICADO]` [usselmann_2002_aescore] |
| **OpenCores tiny_aes** (Homer Hsing) | https://opencores.org/projects/tiny_aes | Verilog | Apache-2.0 | **Pipelined**, sólo cifrado, 1 bloque/ciclo, AES-128/192/256 | "FPGA proven" en XC6VLX240T | 324,6 MHz (Virtex-6); 38,4 Gbit/s a 300 MHz | Estable | `[VERIFICADO]` [hsing_tinyaes] |
| **hadipourh/AES-VHDL** | https://github.com/hadipourh/AES-VHDL | VHDL | GPL-3.0 | 1 ronda/ciclo (10 ciclos), enc y dec; también variante pipelined | Vectores NIST | Artix-7 xc7a200t-3: enc 1104 LUT/264 FF/294 MHz/3,77 Gbit/s; dec 1490 LUT/254 MHz | Académico | `[VERIFICADO]` [hadipour_aesvhdl] |
| hadipourh/CryptoHDL | https://github.com/hadipourh/CryptoHDL | VHDL | varias | Índice de implementaciones cripto en VHDL | — | — | Lista | `[NO VERIFICADO: sólo visto en resultados de búsqueda]` |

**Sobre "Bertoni":** no se ha localizado ninguna implementación abierta de AES en FPGA atribuida a G. Bertoni; su obra pública se centra en Keccak/SHA-3 y en análisis de fallos/side-channel de AES. Se omite por no poder verificarse `[NO VERIFICADO]`.

**Recomendación de uso:** leer secworks/aes y secworks/sha256 como referencia de estilo (interfaz de registros, FSM, separación datapath/control, testbench con vectores oficiales), y hadipourh/AES-VHDL como referencia de la variante 1 ronda/ciclo en VHDL. Las licencias BSD-2 permitirían incluso reutilizar código con atribución, pero el objetivo del TFM es un diseño propio; la GPL-3 de AES-VHDL desaconseja copiar fragmentos.

---

## 6. Interfaz FPGA–ESP32 (esclavo SPI en la FPGA)

### 6.1 Modos SPI y diseño del esclavo

- Modos: ESP-IDF define `mode` = (CPOL, CPHA): 0 = (0,0), 1 = (0,1), 2 = (1,0), 3 = (1,1) `[VERIFICADO]` [espressif_spimaster]. Recomendación: **modo 0** (SCLK en reposo bajo, muestreo en flanco de subida, cambio en bajada), que es el habitual en esclavos síncronos simples.
- Dos estrategias para el esclavo en FPGA:
  1. **SCLK como reloj del registro de desplazamiento** (dominio asíncrono) + cruce de dominio (CDC) hacia el reloj de sistema por FIFO o handshake de doble registro. Permite SCLK altos (un participante del hilo de EEVblog afirma que "would work fine up to at least 50 MHz on typical mid-range FPGAs"), a costa de un dominio de reloj más, restricciones de timing asíncronas y el problema de que SCLK no corre entre transacciones (no hay reloj para vaciar/limpiar estados). `[VERIFICADO: hilo leído]` [eevblog_spislave]
  2. **Sobremuestreo con el reloj de sistema (100 MHz):** SCLK, MOSI y CS pasan por sincronizadores de 2 FF y se detectan flancos de SCLK; toda la lógica queda en un solo dominio. Requiere que el reloj de sistema sea claramente más rápido: el hilo citado recomienda "at least 4–5 times faster than SPI" y considera problemático un factor 3 (20 MHz SCLK con 60 MHz de sistema) `[VERIFICADO]`. Con 100 MHz → **SCLK ≤ 20–25 MHz** (≈ f_sys/4–f_sys/5).
- Camino MISO (el crítico en el ESP32): en la opción 2 el dato de salida se actualiza en el reloj de sistema tras detectar el flanco de SCLK, así que la validez de MISO respecto al flanco de SCLK sufre 2–3 ciclos de sistema (20–30 ns) más el retardo de E/S. Ese valor es exactamente el `input_delay_ns` que hay que declarar al driver del ESP32 (§6.2), y es lo que acota la frecuencia en full-duplex.
- Recomendación: sobremuestreo, modo 0, **SCLK = 10–20 MHz**, protocolo de comando/longitud/datos con CS delimitando la transacción, y palabras de 8 bit alineadas a bloques de 16 B. A 10 Mbit/s un bloque AES viaja en 12,8 µs; sigue siendo la interfaz, no el núcleo, quien limita (§1.5).

### 6.2 ESP-IDF v5.x `spi_master`

Documentación https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32/api-reference/peripherals/spi_master.html (y v5.1, stable) `[VERIFICADO]` [espressif_spimaster]:
- API: `spi_bus_initialize()`, `spi_bus_add_device()`, `spi_device_transmit()`, `spi_device_polling_transmit()`, `spi_device_queue_trans()` / `spi_device_get_trans_result()`. Campos clave de `spi_device_interface_config_t`: `clock_speed_hz`, `mode`, `input_delay_ns` ("maximum data valid time of slave"), `cs_ena_pretrans`.
- **Pines IO_MUX vs GPIO matrix:** la GPIO matrix "allows signals with clock frequencies only up to 40 MHz, as opposed to 80 MHz if IO_MUX pins are used"; la matriz añade unos dos ciclos APB de retardo de entrada. Pines IO_MUX: SPI2 (HSPI) CS0 = GPIO15, SCLK = GPIO14, MISO = GPIO12, MOSI = GPIO13; SPI3 (VSPI) CS0 = GPIO5, SCLK = GPIO18, MISO = GPIO19, MOSI = GPIO23 `[VERIFICADO]`.
- **Límite full-duplex:** "Freq limit [MHz] = 80 / (floor(MISO delay[ns]/12.5) + 1)"; con retardo de esclavo ≈ 0 ns: 80 MHz (IO_MUX), **≈ 26,67 MHz con GPIO matrix**; en half-duplex con "dummy bits" se recuperan 40 MHz, pero "full-duplex transactions are not compatible with the dummy bit workaround" `[VERIFICADO]`. Con el `input_delay_ns` ≈ 30 ns del esclavo sobremuestreado (§6.1), el límite full-duplex queda en 80/(2+1) ≈ 26,7 MHz por IO_MUX y menos por GPIO matrix **[cálculo propio con la fórmula del documento]** — coherente con la recomendación de 10–20 MHz.
- El ESP32 tiene cuatro controladores SPI; SPI2 y SPI3 pueden ser maestro o esclavo (datasheet v5.3) `[VERIFICADO]` [espressif_datasheet].

### 6.3 Niveles eléctricos y conectores Pmod de la Basys 3

- Basys 3 rev. C (manual de referencia de Digilent, revisión 12-08-2014, copia alojada por AMD) `[VERIFICADO: PDF extraído]` [digilent_2014_basys3rm]: FPGA **XC7A35T-1CPG236C**; "33,280 logic cells in 5200 slices (each slice contains four 6-input LUTs and 8 flip-flops)", 90 DSP; **oscilador único de 100 MHz en el pin W5** (entrada MRCC del banco 34); reguladores de 3,3 V / 1,8 V / 1,0 V, con la línea de 3,3 V alimentando "FPGA I/O, USB ports, Clocks, Flash, PMODs"; **tres conectores Pmod (JA, JB, JC) y un Pmod XADC**, cada uno 2×6 con dos pines VCC de **3,3 V** (6 y 12), dos GND (5 y 11) y 8 señales; las señales "are routed using best-available tracks without impedance control or delay matching". El JXADC tiene trazas acopladas y filtros anti-alias que "might limit the data speeds when used for digital signals" → **usar JA/JB/JC para el SPI, no JXADC**. Pines de JA: J1, L2, J2, G2, H1, K2, H2, G3.
- El XDC maestro oficial (Digilent/digilent-xdc, `Basys-3-Master.xdc`) fija `IOSTANDARD LVCMOS33` para el reloj W5 (`create_clock -period 10.00`) y para todas las señales de JA/JB/JC `[VERIFICADO]` [digilent_xdc].
- **Protección:** la especificación Digilent Pmod Interface 1.2.0 dice que "the I/O pins on standard system board Pmod ports generally have ESD protection diodes and 200-ohm series resistors" para limitar cortocircuitos y conflictos de drivers, y que las señales siguen convenciones LVCMOS 3,3 V / LVTTL 3,3 V; los hosts sólo están obligados a suministrar 3,3 V `[VERIFICADO: PDF extraído]` [digilent_pmodspec]. **El manual de la Basys 3 de 2014 no menciona explícitamente las resistencias de 200 Ω** y la versión web actual del manual no se pudo abrir (Cloudflare) → el detalle debe confirmarse en el esquemático de la Basys 3 antes de fiarse de él `[NO VERIFICADO para la Basys 3 en concreto]`. En cualquier caso, la resistencia serie de 200 Ω, si existe, limita la pendiente con la capacidad del cable/GPIO y es una razón más para no pasar de 20–25 MHz.
- El ESP32 es un dispositivo de E/S a 3,3 V (datasheet) → compatible directamente con LVCMOS33 sin conversores de nivel `[VERIFICADO: datasheet v5.3 consultada; el valor 3,3 V de VDD_IO se da por conocido y no se extrajo literalmente → NO VERIFICADO literal]`.

---

## 7. El ESP32 como verificador independiente

### 7.1 Aceleradores hardware (ESP32 Technical Reference Manual v5.8)

`[VERIFICADO: PDF descargado y capítulos 14 y 16 extraídos]` [espressif_2025_trm]:
- **Cap. 14 AES Accelerator:** "supports six algorithms of FIPS PUB 197, specifically AES-128, AES-192 and AES-256 encryption and decryption"; clave en AES_KEY_0..7_REG, texto en AES_TEXT_0..3_REG, modo en AES_MODE_REG (0/1/2 cifrado 128/192/256, 4/5/6 descifrado), arranque AES_START_REG (0x3FF01000), estado AES_IDLE_REG; registros de endianness. **§14.3.5 Speed: "requires 11 to 15 clock cycles to encrypt a message block, and 21 or 22 clock cycles to decrypt a message block."** Es un motor ECB de un bloque; los modos (CBC, CTR, CMAC) los compone software.
- **Cap. 16 SHA Accelerator:** "supports four algorithms of FIPS PUB 180-4, specifically SHA-1, SHA-256, SHA-384 and SHA-512"; "can only accept one message block at a time" (512 bit para SHA-256 en SHA_TEXT_0..15_REG); **"is unable to perform the padding operation … the user software is expected to pad the message"**; resumen devuelto en SHA_TEXT_0..7_REG.
- Mapa de memoria: AES 0x3FF01000–0x3FF01FFF, SHA 0x3FF03000–0x3FF03FFF, RSA 0x3FF02800… `[VERIFICADO: registros AES listados; el rango SHA por el índice del TRM]`.

### 7.2 Integración en mbedtls (ESP-IDF v5.x)

- ESP-IDF v5.4 enlaza Mbed TLS 3.6.x (la página remite a la API 3.6.2) `[VERIFICADO]` [espressif_mbedtls]. Opciones: `CONFIG_MBEDTLS_HARDWARE_AES`, `CONFIG_MBEDTLS_HARDWARE_SHA`, `CONFIG_MBEDTLS_HARDWARE_MPI` `[VERIFICADO]`.
- Kconfig de `components/mbedtls` (rama release/v5.4) `[VERIFICADO: fichero leído]` [espressif_kconfig_mbedtls]:
  - `MBEDTLS_HARDWARE_AES`: "Enable hardware accelerated AES encryption & decryption. **Note that if the ESP32 CPU is running at 240MHz, hardware AES does not offer any speed boost over software AES.**"
  - `MBEDTLS_HARDWARE_SHA`: "Enable hardware accelerated SHA1, SHA256, SHA384 & SHA512 in mbedTLS. Due to a hardware limitation, on the ESP32 hardware acceleration is only guaranteed if SHA digests are calculated one at a time. If more than one SHA digest is calculated at the same time, one will be calculated fully in hardware and the rest will be calculated (at least partially calculated) in software."
  - `MBEDTLS_CMAC_C`: por defecto `n` → **hay que activarlo** para usar `mbedtls_cipher_cmac`.
- Implicación metodológica: el ESP32 debe medirse **en ambas configuraciones** (hardware on/off). Que ambas coincidan bit a bit entre sí y con la FPGA es en sí una validación cruzada de tres implementaciones independientes (mbedtls software, acelerador Espressif, núcleo propio).

### 7.3 Throughput publicado del AES/SHA del ESP32

Única medida de terceros verificada, publicada por wolfSSL en el foro de Espressif y en su README de Espressif `[VERIFICADO: ambas fuentes leídas]` [wolfssl_2019_esp32bench]: ESP32-WROOM-32 a 240 MHz, ESP-IDF v3.3-beta1, benchmark wolfCrypt:

| Algoritmo | Software | Hardware | Factor |
|---|---|---|---|
| AES-128-CBC cifrado | 1,146 MB/s | 5,958 MB/s | ×5,2 |
| AES-128-CBC descifrado | 1,104 MB/s | 5,287 MB/s | ×4,8 |
| SHA-256 | 1,747 MB/s | 15,234 MB/s | ×8,7 |

Notas: (1) el software de referencia es el de wolfCrypt (con `WOLFSSL_SMALL_STACK`), no el AES con tablas de mbedtls, lo que explica la aparente contradicción con la nota del Kconfig de Espressif; (2) 5,96 MB/s ≈ 48 Mbit/s = 0,37 Mbloques/s ≈ 650 ciclos de CPU por bloque a 240 MHz, muy lejos de los 11–15 ciclos del acelerador: el coste está en la escritura/lectura de registros y en la gestión de la exclusión mutua, no en el núcleo **[cálculo propio]**; (3) para el TFM, el ESP32 procesará ≥ 5 MB/s en ambos sentidos, muy por encima de los ≤ 2,5 MB/s del enlace SPI a 20 MHz, así que **el verificador nunca será el cuello de botella**. No se han encontrado medidas académicas revisadas por pares del acelerador AES del ESP32 clásico `[NO ENCONTRADO]`.

### 7.4 API de mbedtls a usar en el verificador

Cabeceras de la rama `mbedtls-3.6` `[VERIFICADO: ficheros leídos]` [mbedtls_36_headers]:
```c
/* AES-ECB / CBC (aes.h) */
int mbedtls_aes_setkey_enc(mbedtls_aes_context *ctx, const unsigned char *key, unsigned int keybits);
int mbedtls_aes_setkey_dec(mbedtls_aes_context *ctx, const unsigned char *key, unsigned int keybits);
int mbedtls_aes_crypt_ecb(mbedtls_aes_context *ctx, int mode, const unsigned char input[16], unsigned char output[16]);
int mbedtls_aes_crypt_cbc(mbedtls_aes_context *ctx, int mode, size_t length, unsigned char iv[16], const unsigned char *input, unsigned char *output);
/* MBEDTLS_AES_ENCRYPT = 1, MBEDTLS_AES_DECRYPT = 0 */

/* CMAC (cmac.h, requiere MBEDTLS_CMAC_C) */
int mbedtls_cipher_cmac_starts(mbedtls_cipher_context_t *ctx, const unsigned char *key, size_t keybits);
int mbedtls_cipher_cmac_update(mbedtls_cipher_context_t *ctx, const unsigned char *input, size_t ilen);
int mbedtls_cipher_cmac_finish(mbedtls_cipher_context_t *ctx, unsigned char *output);
int mbedtls_cipher_cmac_reset(mbedtls_cipher_context_t *ctx);
int mbedtls_cipher_cmac(const mbedtls_cipher_info_t *cipher_info, const unsigned char *key, size_t keylen,
                        const unsigned char *input, size_t ilen, unsigned char *output);
int mbedtls_aes_cmac_prf_128(const unsigned char *key, size_t key_len, const unsigned char *input, size_t in_len, unsigned char output[16]);

/* SHA-256 (sha256.h); is224 = 0 para SHA-256 */
int mbedtls_sha256_starts(mbedtls_sha256_context *ctx, int is224);
int mbedtls_sha256_update(mbedtls_sha256_context *ctx, const unsigned char *input, size_t ilen);
int mbedtls_sha256_finish(mbedtls_sha256_context *ctx, unsigned char *output);
int mbedtls_sha256(const unsigned char *input, size_t ilen, unsigned char *output, int is224);
```
Para CMAC-AES-128: `mbedtls_cipher_cmac(mbedtls_cipher_info_from_type(MBEDTLS_CIPHER_AES_128_ECB), key, 128, msg, len, tag)`.

### 7.5 Metodología de validación cruzada propuesta

1. **KAT (Known Answer Tests) con vectores oficiales.** Parsear los `.rsp` de CAVP en el PC (o en el ESP32 desde SPIFFS) y enviarlos por SPI a la FPGA: AES: `KAT_AES.zip` (ECBGFSbox128, ECBKeySbox128, ECBVarKey128, ECBVarTxt128 y sus equivalentes CBC) y `aesmmt.zip` (ECBMMT128, CBCMMT128, multibloque) `[VERIFICADO: zips descargados y listados]` [nist_cavp_blockciphers]; opcionalmente el Monte Carlo `aesmct.zip`. SHA-256: `shabytetestvectors.zip` → `SHA256ShortMsg.rsp`, `SHA256LongMsg.rsp`, `SHA256Monte.rsp` `[VERIFICADO]` [nist_cavp_shs]. CMAC: `CMACGenAES128.rsp`, `CMACVerAES128.rsp`. DRBG: `CTR_DRBG.rsp` (`no_reseed` y `pr_false`, sección AES-128 no df). El ESP32 ejecuta los mismos vectores con mbedtls y compara ambos resultados con el esperado del fichero → tres vías independientes.
2. **Interoperabilidad masiva aleatoria.** El ESP32 genera (con `esp_random()`/mbedtls) claves y textos aleatorios, la FPGA cifra y el ESP32 descifra (y viceversa), en ECB y CBC; se registran ≥ 10^5–10^6 bloques y se comprueba igualdad bit a bit y estadísticas de latencia por transacción. Para el DRBG: el ESP32 instancia un CTR_DRBG software (`mbedtls_ctr_drbg` con entropía forzada al mismo seed) y compara la secuencia con la de la FPGA.
3. **Reto-respuesta.** El ESP32 envía un nonce de 128 bit (y un identificador de sesión); la FPGA devuelve CMAC_K(nonce || id || contador) y opcionalmente 256 bit del DRBG; el ESP32 verifica con `mbedtls_cipher_cmac` en tiempo constante y registra la tasa de aciertos y la latencia. Se repite con claves erróneas y nonces repetidos para verificar que el MAC falla cuando debe.
4. **Métricas a reportar:** tasa de acierto (debe ser 100 % en 1–3), throughput efectivo del enlace vs teórico, latencia por comando, utilización post-implementación (LUT/FF/BRAM) y f_max de cada bloque, consumo estimado por Vivado.

### 7.6 Antecedentes de "microcontrolador como verificador de un núcleo cripto en FPGA"

**No se ha encontrado ninguna publicación revisada por pares que use explícitamente un microcontrolador (ESP32, STM32, Arduino) como oráculo de verificación de un núcleo AES/SHA en FPGA.** Lo más cercano localizado: (a) la práctica industrial de validar IP cores con vectores NIST desde un host (Design Gateway, blog de 2025, AES-GCM) `[NO VERIFICADO: sólo resultado de búsqueda]`; (b) el coprocesador RISC-V Crypto-RV (arXiv 2026) que informa de 10^7 casos de prueba dirigidos desde software en un ZCU102 `[NO VERIFICADO]`. La novedad metodológica del TFM (verificador embebido independiente, con y sin aceleradores, sobre un enlace real) parece, por tanto, defendible, pero debe formularse con cautela ("no hemos localizado…", no "no existe").

---

## 8. Lo que este TFM NO debe hacer y por qué

1. **Criptografía asimétrica (RSA/ECC).** La multiplicación escalar en curvas de 256 bit es, por sí sola, un proyecto de máster: E²CSM (Javeed, El-Moursy y Gregg, J. Supercomputing 2023/2024, DOI 10.1007/s11227-023-05428-4) y Cui et al. (Microprocessors and Microsystems 2023, DOI 10.1016/j.micpro.2023.104944) dedican artículos completos a un solo acelerador de ECSM sobre GF(p) `[VERIFICADO: título/autores/DOI por Crossref; cifras de área no verificadas]` [javeed_2023_e2csm] [cui_2023_ecsm]. Las cifras que circulan para Artix-7 (del orden de 6–7 k slices o ≈ 20 k LUT por acelerador, según resúmenes de búsqueda `[NO VERIFICADO]`) ocuparían **todo** el XC7A35T (5200 slices / 20 800 LUT). Además exigiría aritmética modular de 256 bit, protección contra fugas de tiempo y una validación (CAVP ECDSA/KAS) de otro orden. El ESP32 sí tiene acelerador RSA (TRM cap. 15) y mbedtls ECC, pero eso no justifica añadirlo a la FPGA.
2. **Resistencia a ataques de canal lateral (DPA/CPA/EM).** Desde Kocher, Jaffe y Jun (CRYPTO '99, DOI 10.1007/3-540-48405-1_25) `[VERIFICADO: DOI/páginas por Crossref]` [kocher_1999_dpa] se sabe que un AES sin protección en FPGA filtra la clave con miles de trazas de consumo; protegerlo exige enmascaramiento (p. ej. S-box enmascarada de Canright-Batina, CHES 2008, DOI 10.1007/978-3-540-68914-0_27 `[NO VERIFICADO]`), duplicación/ocultación, un banco de medida (osciloscopio, sonda, tarjeta con resistencia de shunt) y una campaña de evaluación (TVLA). Es un TFM distinto; aquí basta **declarar** el modelo de amenaza (atacante remoto/lógico, no físico) y evitar fugas triviales de tiempo (latencia constante del núcleo, comparación de MAC en tiempo constante en el ESP32).
3. **Certificación formal (FIPS 140-3 / CMVP, o validación 90B del TRNG).** El manual de gestión del CMVP describe un proceso con laboratorio acreditado, fases de "Cost Recovery", "Coordination" y "Finalization" y fichero de módulo "IUT" con plazo de 18 meses `[NO VERIFICADO: sólo resumen de búsqueda]`; los proveedores de servicios hablan de hasta ≈ 16 meses de proceso convencional `[NO VERIFICADO]`. El servidor ACVTS de producción "is only available to NVLAP-accredited testing laboratories" `[VERIFICADO]`. El TFM debe limitarse a la **conformidad funcional** demostrada con vectores CAVP/ACVP (servidor Demo gratuito) y a documentar qué requisitos normativos (health tests, df/no-df, reseed) se cumplen, sin reclamar validación.
4. **Modos autenticados de alto throughput (GCM/CCM) o pipelining.** Ni el enlace SPI ni el caso de uso los necesitan (§1.5); GCM añadiría un multiplicador GF(2^128) y su propia batería de vectores. CMAC + CBC cubren autenticación y confidencialidad de forma separada y verificable.

---

## 9. Tabla final de referencias y estado de verificación

| Clave BibTeX | Referencia | Estado |
|---|---|---|
| nist_2023_fips197 | FIPS 197-upd1, AES, mayo 2023, DOI 10.6028/NIST.FIPS.197-upd1 | [VERIFICADO] página CSRC + PDF (Tabla 3, Ap. D) |
| nist_2015_fips1804 | FIPS 180-4, SHS, agosto 2015, DOI 10.6028/NIST.FIPS.180-4 | [VERIFICADO] página + PDF (§5.1.1, §6.2.2) |
| nist_2016_sp80038b | SP 800-38B upd1, CMAC, 2005/2016, DOI 10.6028/NIST.SP.800-38B | [VERIFICADO] PDF (erratas, §5.3, §6.1–6.2, Ap. A–B) |
| song_2006_rfc4493 | RFC 4493, AES-CMAC, IETF 2006 | [VERIFICADO] vectores §4; autores/fecha de memoria |
| nist_cmac_examples | NIST, ejemplos CMAC (AES_CMAC.pdf) | [VERIFICADO] PDF extraído |
| barker_2015_sp80090ar1 | SP 800-90A Rev. 1, junio 2015, DOI 10.6028/NIST.SP.800-90Ar1 | [VERIFICADO] PDF (Tablas 2–3, §8.6, §10.2.1.3.1, §11) ; autores de memoria |
| turan_2018_sp80090b | SP 800-90B, enero 2018, DOI 10.6028/NIST.SP.800-90B | [VERIFICADO] PDF (§3.1.5 completo, Tabla 1) ; autores de memoria |
| barker_2025_sp80090c | SP 800-90C final, septiembre 2025, DOI 10.6028/NIST.SP.800-90C | [VERIFICADO] página CSRC ; autores de memoria |
| chen_2022_sp800108r1 | SP 800-108 Rev. 1 upd1, 2022/2024, DOI 10.6028/NIST.SP.800-108r1-upd1 | [VERIFICADO] página CSRC ; autor de memoria |
| nist_2025_sp80090a_predraft | NIST, pre-draft call for comments SP 800-90A Rev. 2, 4-09-2025 | [VERIFICADO] noticia; detalle de cambios NO VERIFICADO |
| nist_cavp_blockciphers | CAVP Block Ciphers: KAT_AES.zip, aesmmt.zip, aesmct.zip | [VERIFICADO] página + zips descargados |
| nist_cavp_modes | CAVP Block Cipher Modes: cmactestvectors.zip | [VERIFICADO] página + zip descargado |
| nist_cavp_shs | CAVP Secure Hashing: shabytetestvectors.zip | [VERIFICADO] página + zip descargado |
| nist_cavp_drbg | CAVP DRBG: drbgtestvectors.zip | [VERIFICADO] página + zip descargado |
| nist_cavp_home | CAVP home (estado ACVTS, Demo/Prod) | [VERIFICADO] |
| nist_acvp_server | usnistgov/ACVP-Server, gen-val/json-files | [VERIFICADO] README + API GitHub |
| canright_2005_compact | Canright, CHES 2005, DOI 10.1007/11545262_32 | [VERIFICADO] PDF IACR (abstract) |
| satoh_2001_compact | Satoh et al., ASIACRYPT 2001, DOI 10.1007/3-540-45682-1_15 | [VERIFICADO] título/DOI Springer; 5,4 kgates por resumen |
| boyar_2010_minimization | Boyar y Peralta, SEA 2010, DOI 10.1007/978-3-642-13193-6_16 | [VERIFICADO] página NIST; cifra 115 puertas NO VERIFICADA |
| chodowiec_2003_compact | Chodowiec y Gaj, CHES 2003, DOI 10.1007/978-3-540-45238-6_26 | [VERIFICADO] Crossref; 222 slices por resumen Springer |
| good_2005_fastest | Good y Benaissa, CHES 2005, DOI 10.1007/11545262_31 | [VERIFICADO] PDF (abstract) |
| strombergson_aes | secworks/aes (GitHub) | [VERIFICADO] README + tb_aes.v |
| strombergson_sha256 | secworks/sha256 (GitHub) | [VERIFICADO] README + tb_sha256.v |
| usselmann_2002_aescore | OpenCores aes_core | [VERIFICADO] página; licencia NO VERIFICADA |
| hsing_tinyaes | OpenCores tiny_aes | [VERIFICADO] página |
| hadipour_aesvhdl | hadipourh/AES-VHDL (GitHub) | [VERIFICADO] README |
| woodage_2019_analysis | Woodage y Shumow, EUROCRYPT 2019, DOI 10.1007/978-3-030-17656-3_6 | [VERIFICADO] PDF IACR + Crossref |
| xie_2025_ctrdrbg | Xie et al., Electronics 14(18):3702, 2025, DOI 10.3390/electronics14183702 | [VERIFICADO] Semantic Scholar (abstract) |
| baldanzi_2020_csprng | Baldanzi et al., Sensors 20(7):1869, 2020, DOI 10.3390/s20071869 | [VERIFICADO] Crossref; 690 Mbit/s NO VERIFICADO |
| santos_2024_sha256 | Santos et al., Sensors 24(12):3908, 2024, DOI 10.3390/s24123908 | [VERIFICADO] Semantic Scholar; cifra Artix-7 citada como ref. [38] NO VERIFICADA |
| li_2019_hashing | Li et al., Microprocessors and Microsystems 2019, DOI 10.1016/j.micpro.2019.03.002 | [VERIFICADO] Semantic Scholar (abstract con cifras) |
| kocher_1999_dpa | Kocher, Jaffe y Jun, CRYPTO '99, DOI 10.1007/3-540-48405-1_25 | [VERIFICADO] Crossref |
| javeed_2023_e2csm | Javeed, El-Moursy y Gregg, J. Supercomputing, DOI 10.1007/s11227-023-05428-4 | [VERIFICADO] Crossref; cifras NO VERIFICADAS |
| cui_2023_ecsm | Cui et al., Microprocessors and Microsystems 2023, DOI 10.1016/j.micpro.2023.104944 | [VERIFICADO] Crossref; cifras NO VERIFICADAS |
| espressif_2025_trm | ESP32 Technical Reference Manual v5.8, cap. 14 y 16 | [VERIFICADO] PDF descargado |
| espressif_datasheet | ESP32 Series Datasheet v5.3 | [VERIFICADO] |
| espressif_spimaster | ESP-IDF v5.4 / v5.1, SPI Master Driver | [VERIFICADO] |
| espressif_mbedtls | ESP-IDF v5.4, Mbed TLS | [VERIFICADO] |
| espressif_kconfig_mbedtls | esp-idf release/v5.4 components/mbedtls/Kconfig | [VERIFICADO] |
| mbedtls_36_headers | Mbed TLS 3.6: aes.h, cmac.h, sha256.h | [VERIFICADO] |
| wolfssl_2019_esp32bench | wolfSSL, benchmark ESP32 (foro esp32.com t=3080 y README Espressif) | [VERIFICADO] |
| digilent_2014_basys3rm | Digilent, Basys3 FPGA Board Reference Manual, rev. 12-08-2014 (copia AMD) | [VERIFICADO] PDF extraído |
| digilent_pmodspec | Digilent Pmod Interface Specification 1.2.0 | [VERIFICADO] PDF extraído |
| digilent_xdc | Digilent/digilent-xdc, Basys-3-Master.xdc | [VERIFICADO] |
| xilinx_2020_ds180 | Xilinx DS180 v2.6.1, 7 Series FPGAs Data Sheet: Overview | [VERIFICADO] PDF extraído (fila XC7A35T) |
| eevblog_spislave | EEVblog forum, "How to create SPI slave in FPGA when SCLK frequency similar to FPGA system clock" | [VERIFICADO] |

Referencias mencionadas pero **no incluidas en el .bib por no poder verificarse**: Canright-Batina 2008 (S-box enmascarada), CryptoHDL, Design Gateway (blog AES-GCM), Crypto-RV (arXiv 2026), manual de gestión CMVP, artículo original de la cifra 1310 LUT/1404 Mbit/s en xc7a200t, implementaciones AES atribuidas a "Bertoni".
