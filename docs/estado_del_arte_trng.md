# Estado del arte: TRNG de osciladores de anillo en FPGA, modelo estocástico y estimación de min-entropía

**TFM:** Motor criptográfico ligero en FPGA (Digilent Basys 3, Artix-7 XC7A35T) validado frente al ESP32.
**Alcance de este documento:** la fuente de entropía (RO-TRNG), su modelo estocástico, la medida embebida del jitter, los problemas de implementación en Xilinx 7-series/Vivado, los tests de salud y estimadores de min-entropía de SP 800-90B / AIS 20/31, y la literatura sobre el RNG del ESP32.
**Fecha de redacción:** 11 de septiembre de 2026.

**Convención de verificación.** Cada referencia lleva una etiqueta:
- **[VERIFICADO]** — se ha abierto el documento (PDF o página) y se ha confirmado que existe y contiene lo que se cita.
- **[VERIFICADO-META]** — se han confirmado título, autores, revista/congreso, año y DOI mediante la API de Crossref o la página del editor, pero **no** se ha leído el contenido; lo que se afirma del contenido procede del resumen (abstract) o de citas en otros trabajos leídos.
- **[NO VERIFICADO]** — conocido de memoria o solo por un fragmento de buscador; tratar con cautela.

Las claves entre corchetes `[autor_anio_palabra]` corresponden a las entradas de `refs_trng.bib`.

---

## 0. Dos correcciones previas al planteamiento del TFM

1. **La versión vigente de la referencia matemático-técnica de AIS 20/31 no es la 2.0 sino la 3.0.** *A Proposal for Functionality Classes for Random Number Generators, Version 3.0*, Matthias Peter y Werner Schindler (BSI), fechada el 10 de septiembre de 2024 en portada y publicada en la web del BSI el 17 de septiembre de 2024 [peter_2024_ais31] **[VERIFICADO]**. La versión 2.0 (Killmann y Schindler, 18 de septiembre de 2011) [killmann_2011_ais31] **[VERIFICADO]** es la que exigía en PTG.2.7 "Shannon entropy per internal random bit exceeds 0.997". La 3.0 sustituye ese requisito por una **selección** en PTG.2.2: Shannon ≥ 0,9998 y/o **min-entropía ≥ 0,98** por bit interno, más la condición Prob(Y_j = 1) ∈ (0,493, 0,507). El BSI publicó una *Transition Policy* (v1.0, 15/04/2025) [bsi_2025_transition] **[VERIFICADO]**: las certificaciones nuevas con la AIS antigua pueden iniciarse solo hasta el 31/03/2026; a partir de ahí, la 3.0 es la única referencia para nuevas evaluaciones. Para un TFM que se defiende en 2026/27 lo correcto es evaluar contra la 3.0 y mencionar la 2.0 como antecedente.

2. **NIST ha declarado formalmente que SP 800-22 no sirve para evaluar RNG criptográficos.** La decisión de revisar SP 800-22 Rev. 1a (19/04/2022) dice literalmente que la revisión debe "clarify the purpose and use of the statistical test suite, in particular rejecting its use for assessing cryptographic random number generators" [nist_2022_decision] **[VERIFICADO]**. Esto refuerza el enfoque del TFM (modelo estocástico + 800-90B) y debe citarse en la introducción.

---

## 1. Arquitecturas RO-TRNG en FPGA

Terminología común (AIS 20/31 v3.0 y [lubicz_2024_recommendations]): *fuente de ruido física* → *digitalizador* → *raw random numbers* → (post-procesado algorítmico opcional) → *internal random numbers*. El **jitter** de fase de un oscilador de anillo (RO) es la fuente de ruido; lo que cambia entre arquitecturas es cómo se **acumula** y cómo se **muestrea**.

### 1.1 ERO — Elementary Ring Oscillator TRNG
Dos RO libres; el primero (RO1) se muestrea con un flip-flop D cuyo reloj es el segundo (RO2) dividido por K_D. El divisor fija el tiempo de acumulación del jitter (K_D·T_2). Es la arquitectura con modelo estocástico más maduro [baudet_2011_security] [killmann_2008_design] [ma_2014_entropy] y la que se usa como ejemplo canónico en AIS 31 y en las *Recommendations* de Lubicz y Fischer [lubicz_2024_recommendations] **[VERIFICADO]**.
- Ventajas: área mínima, modelo con cota inferior de entropía demostrable, medida de jitter embebida disponible [fischer_2014_embedded].
- Inconvenientes: caudal muy bajo (K_D ~ 10^4–10^5; Petura et al. usan K = 80 000 en Spartan-6, 135 000 en Cyclone V y 20 000 en SmartFusion2 [petura_2016_survey] **[VERIFICADO]**; Fischer–Lubicz obtienen K_D ≈ 430 000 para H ≥ 0,997 con σ = 5,01 ps [fischer_2014_embedded] **[VERIFICADO]**). Sensible al jitter global (alimentación) porque los dos anillos lo comparten pero no de forma idéntica.

### 1.2 MURO — Multi-Ring Oscillator (Sunar–Martin–Stinson; Wold–Tan)
Sunar, Martin y Stinson [sunar_2007_provably] **[VERIFICADO-META]** proponen XOR de muchos RO muestreado por un reloj de referencia, con una *resilient function* como post-procesado, y una prueba de seguridad "bajo hipótesis suaves" con caudal en el rango de Mbit/s (abstract). Wold y Tan [wold_2009_analysis] **[VERIFICADO-META]** añaden un flip-flop a la salida de cada anillo antes del XOR (evita que el árbol XOR no pueda seguir los flancos) y reportan 100 Mbit/s con menos de 100 LE en Cyclone II pasando NIST y DIEHARD sin post-procesado; además observan que anillos de igual longitud no oscilan a la misma frecuencia por la colocación/rutado. Bochard, Bernard, Fischer y Valtchanov [bochard_2010_true] **[VERIFICADO-META]** muestran que parte de la aparente aleatoriedad de estos diseños es **pseudo-aleatoriedad** debida a la interacción entre anillos (frecuencias distintas, acoplos), no a jitter, y que las hipótesis de independencia de Sunar no se cumplen en FPGA. Petura et al. [petura_2016_survey] **[VERIFICADO]** implementan la variante Wold–Tan "modificada" y advierten que el modelo solo es válido con los flip-flops adicionales.
- Ventajas: caudal alto; producto entropía×caudal alto.
- Inconvenientes: área grande (521 LUT/131 reg en Spartan-6), consumo alto (54,7 mW), riesgo de *locking* entre anillos, difícil demostrar independencia.

### 1.3 COSO — Coherent Sampling Oscillator TRNG
Dos RO de periodos muy próximos; RO1 muestreado directamente por RO0 genera una señal de "batido" cuya duración en periodos de RO0 se cuenta; el LSB del contador es el bit aleatorio. Origen: Kohlbrenner y Gaj [kohlbrenner_2004_embedded] **[VERIFICADO]** (Virtex XCV1000, ROs de un CLB a ~130 MHz, diferencias de periodo de 22–35 ps, hasta 0,5 Mbit/s); Valtchanov, Fischer y Aubert [valtchanov_2009_enhanced] **[VERIFICADO-META]** mejoran la extracción. Modelo estocástico y optimización: Yang et al. (citado en Peetermans) y Peetermans, Rožić y Verbauwhede [peetermans_2019_portable] **[VERIFICADO]**, [peetermans_2021_configurable] **[VERIFICADO]**, con **calibración dinámica** que elige la configuración de ROs reconfigurables (GateVar, WireVar, LUTVar) para garantizar la entropía incluso con *placement* automático; resultados: 3,30 Mbit/s en Spartan-6 y 1,47 Mbit/s en SmartFusion2 pasando AIS-31 sin post-procesado (FPL 2019); 4,65 Mbit/s en Spartan-7 (TRETS 2021). El modelo da E[CSCnt] = E[T_RO0]/E[Δ], Var[CSCnt] = E[CSCnt]·Var[Δ]/E[Δ]², Var[Δ] = Var[T_RO0] + Var[T_RO1], y la min-entropía H_∞ = −log2 max_i p_i con p_i = Σ_j Pr(CSCnt = 2j+i) [peetermans_2021_configurable] **[VERIFICADO]**. Implementación abierta de referencia: `KULeuven-COSIC/COSO-TRNG` (GitHub) y OpenTRNG (CEA-Leti).
- Ventajas: área mínima (18 LUT/3 reg en Spartan-6), alarma de fallo intrínseca (el contador se sale de rango), caudal medio.
- Inconvenientes: exige que Δ = |T_RO0 − T_RO1| sea del orden de decenas de ps; Petura et al. señalan que "requiere intervención manual (placement & routing) para cada dispositivo" y que "incluso anillos idénticos..." no dan el Δ deseado sin ajuste [petura_2016_survey] **[VERIFICADO]**; la calibración automática de Peetermans resuelve esto a costa de lógica adicional.

### 1.4 TERO — Transition Effect Ring Oscillator
Varchola y Drutarovský [varchola_2010_new] **[VERIFICADO]**: estructura biestable con dos ramas (NAND + inversores) que, al excitarse, oscila un número aleatorio de veces antes de resolverse a un estado estable; la variable aleatoria es el número de oscilaciones. Implementado en Spartan-3E en un solo CLB. Modelo físico→estocástico completo en Bernard, Haddad, Fischer y Nicolai [bernard_2019_physical] **[VERIFICADO-META]** (J. Cryptology 32(2):435–458).
- Ventajas: área pequeña (39 LUT/12 reg en Spartan-6), entropía alta por bit, "stateless" (cada bit es un experimento nuevo).
- Inconvenientes: las dos ramas deben estar **desequilibradas de forma controlada**; Petura et al.: "la necesidad de ajuste manual de la celda TERO representa un inconveniente", una celda perfectamente equilibrada oscila indefinidamente [petura_2016_survey] **[VERIFICADO]**.

### 1.5 STR — Self-Timed Ring TRNG
Cherkaoui, Fischer, Fesquet y Aubert [cherkaoui_2013_very] **[VERIFICADO]**: anillo asíncrono de L etapas (puerta de Muller + inversor) por el que circulan varios "eventos" sin colisión, produciendo L fases equidistantes cuya separación T/L puede hacerse del orden del jitter; cada fase se muestrea y se XORean. Cota inferior de entropía: P(u)_{t=0} = 1 − 2φ(T/(4Lσ)) + 2φ(T/(4Lσ))², H_m = −P log2 P − (1−P) log2(1−P) (ecs. 8–9). Medidas: jitter ≈ 2 ps en Cyclone III y 2,5 ps en Virtex-5; hasta 200 Mbit/s con L = 255 y 511. En [petura_2016_survey]: 154 Mbit/s, 346 LUT/256 reg, 65,9 mW en Spartan-6, entropía 0,998.
- Ventajas: caudal máximo entre las arquitecturas AIS-compatibles; la frecuencia no depende de L.
- Inconvenientes: área y consumo altos; anillos con muchas etapas presentan problemas prácticos de arranque/estabilidad (Petura: "if the STR has too many stages...").

### 1.6 ES-TRNG y DC-TRNG (KU Leuven)
Rožić, Yang, Dehaene y Verbauwhede [rozic_2015_highly] **[VERIFICADO-META]** usan la cadena de acarreo (CARRY4) como TDC de alta resolución para digitalizar la posición del flanco (DC-TRNG; resolución ~17 ps según las diapositivas de ES-TRNG [yang_2018_estrng_slides] **[VERIFICADO]**). Yang, Rožić, Grujić, Mentens y Verbauwhede [yang_2018_estrng] **[VERIFICADO]** (TCHES 2018(3):267–292) proponen ES-TRNG: *variable-precision phase encoding* (alta resolución solo alrededor de los flancos) y *repetitive sampling*; **10 LUT + 5 FF, 1,15 Mbit/s, Shannon 0,997 en Spartan-6**; 10 LUT + 6 FF, 1,07 Mbit/s en Cyclone V. Parámetros medidos en Spartan-6 (diapositivas): periodos de RO 2,172 ns y 2,740 ns, "jitter strength" σ_m²/t_m = 2,9 fs. Grujić y Verbauwhede [grujic_2022_trot] **[VERIFICADO-META]** (TROT, IEEE TCAS-I 69(6):2435–2448) extienden la idea con un anillo de tres flancos y TDC.
- Nota: el usuario pedía "Grujić & Verbauwhede TCHES 2021/2022 *Optimizing the transition sampling TRNG / delay-chain TRNG*". **No se ha encontrado** ningún artículo con ese título en TCHES. Lo más cercano verificado es TROT (TCAS-I 2022) y, no verificado, Grujić, Rožić, Yang, Verbauwhede, "A closer look at the delay-chain based TRNG", ISCAS 2018 [grujic_2018_closer] **[NO VERIFICADO]**.

### 1.7 PLL-TRNG (para contexto)
Fischer y Drutarovský [fischer_2002_true] **[VERIFICADO-META]** (CHES 2002): muestreo coherente usando la relación racional exacta de dos PLL. Petura et al. lo implementan pero advierten que en Spartan-6 la salida de los PLL va por red de reloj dedicada y no puede rutarse a un flip-flop arbitrario, y que los PLL no pueden apagarse [petura_2016_survey] **[VERIFICADO]**. Para el Artix-7 (MMCM/PLL de 7-series) aplican restricciones análogas; no se ha buscado literatura específica.

### 1.8 Tabla comparativa (Xilinx Spartan-6, 45 nm), de la Tabla II de [petura_2016_survey] **[VERIFICADO]**

| Núcleo | Área (LUT/Reg) | Potencia (mW) | Caudal (Mbit/s) | Entropía/bit | Entropía×caudal | Feasib./Repet. (1 mejor) |
|---|---|---|---|---|---|---|
| ERO  | 46/19   | 2,16  | 0,0042 | 0,999 | 0,004   | 5 |
| COSO | 18/3    | 1,22  | 0,54   | 0,999 | 0,539   | 1 |
| MURO | 521/131 | 54,72 | 2,57   | 0,999 | 2,567   | 4 |
| PLL  | 34/14   | 10,6  | 0,44   | 0,981 | 0,431   | 3 |
| TERO | 39/12   | 3,312 | 0,625  | 0,999 | 0,624   | 1 |
| STR  | 346/256 | 65,9  | 154    | 0,998 | 154,121 | 2 |

Nota sobre "entropía/bit": Petura et al. la estiman con el test T8 de AIS 31 (Coron), es decir, es una **estimación estadística**, no la cota del modelo. La columna "Feasib./Repet." es una nota cualitativa de los autores (1 = mejor); COSO y TERO reciben 1 porque requieren ajuste manual por dispositivo.

Otros puntos de referencia en Xilinx: ES-TRNG 10 LUT + 5 FF, 1,15 Mbit/s, Spartan-6 [yang_2018_estrng] **[VERIFICADO]**; COSO con calibración automática 3,30 Mbit/s en Spartan-6 [peetermans_2019_portable] **[VERIFICADO]** y 4,65 Mbit/s en Spartan-7 (28 nm, misma fábrica que Artix-7) [peetermans_2021_configurable] **[VERIFICADO]**; Kohlbrenner–Gaj 0,5 Mbit/s en Virtex (2004) [kohlbrenner_2004_embedded] **[VERIFICADO]**. No se ha encontrado una tabla comparativa publicada **en Artix-7** con estas seis arquitecturas; el proyecto OpenTRNG (CEA-Leti, licencia MIT) implementa ERO/MURO/COSO sobre Arty A7 (xc7a35ticsg324-1L, mismo die XC7A35T que la Basys 3) pero su documentación no publica cifras de entropía o caudal [opentrng_2025_docs] **[VERIFICADO]**.

---

## 2. Modelo estocástico: jitter, factor de calidad y cota de entropía

### 2.1 El jitter como proceso de fase
Baudet, Lubicz, Micolod y Tassiaux [baudet_2011_security] **[VERIFICADO]** (J. Cryptology 24(2):398–425; ePrint 2009/299) modelan la fase ϕ(t) del oscilador muestreado como un **proceso de Wiener con deriva µ > 0 y volatilidad σ² > 0** (ambas son frecuencias): condicionada a ϕ(t_0), ϕ(t) es gaussiana de media ϕ(t_0) + µ(t − t_0) y varianza σ²(t − t_0) (ec. 1). El bit es s(t) = g_1(ϕ(t) mod 1) con g_1 = 1 en ]1/2, 1[ y 0 en ]0, 1/2[ (ec. 3). Se supone σ² ≪ µ. El modelo equivale a un proceso de renovación alternado con semiperiodos X_k de distribución inversa gaussiana (Wald) de parámetros m_X = 1/(2µ) y λ = 1/(4σ²) (ecs. 4–5).

Fischer y Lubicz [fischer_2014_embedded] **[VERIFICADO]** generalizan: la fase Φ(t) es un proceso de Markov estacionario con media ξ(t_0) + µ(Δt) y **varianza V(Δt)**; distinguen:
- la componente de **paseo aleatorio** (ruido térmico/blanco, transiciones independientes): varianza **σ_0²·Δt** (lineal en Δt);
- las componentes **1/f^β, 0 < β < 2** (flicker): autocorreladas y con varianza que "depende cuadráticamente del intervalo de acumulación", de modo que **a tiempos largos dominan** al ruido térmico; por eso "el tiempo de acumulación debe ser tan corto como sea posible, pero suficiente para obtener un jitter medible", y un diagrama log-log de V(Δt) permite separar las regiones de pendiente 1 y 2.

En notación compacta (la que pide el guion del TFM): **σ²(t) ≈ a·t + b·t²**, donde solo el término *a·t* (térmico) puede contabilizarse como entropía; el término *b·t²* incluye flicker y, sobre todo, el **jitter determinista global** (alimentación, sustrato, acoplos), que un atacante puede conocer o inducir. Fischer et al. [fischer_2008_enhancing] **[VERIFICADO-META]** (FPL 2008) muestran que "el jitter aleatorio se acumula más lentamente que el determinista", que es exactamente el motivo por el que no se puede compensar poco jitter térmico alargando K_D indefinidamente. Saarinen [saarinen_2021_entropy] **[VERIFICADO]** recoge el modelo físico de Hajimiri: σ_t² = κ²·t ≈ (8/3η)·(kT/P)·(V_DD/V_char)·t (ec. 1), que solo cubre las "inevitable noise sources", no la alimentación ni el sustrato.

### 2.2 Factor de calidad y probabilidad de bit
Con Δt el periodo de muestreo, Baudet et al. definen (§2.4) el **factor de calidad**

  **Q = σ²·Δt = s_X²·Δt / (4 m_X³)**  (varianza de fase acumulada entre dos muestras)

y la **relación de frecuencias ν = µ·Δt = Δt/(2 m_X)**. Nota: en muchos textos posteriores (y en el guion del TFM) se escribe Q = σ_jit²·f_s con σ_jit² la varianza del jitter por periodo; es la misma cantidad reescalada. Proposición 1 de [baudet_2011_security]:

1. **P[s(t) = 1 | ϕ(0) = x] = 1/2 − (2/π)·sin(2π(µt + x))·e^{−2π²σ²t} + O(e^{−4π²σ²t})**  (ec. 8)
2. probabilidad de un vector b = (b_1..b_n) muestreado en 0, Δt, …, (n−1)Δt:
   **p(b) = 1/2^n + (8/(2^n π²))·[Σ_{j=1}^{n−1} (−1)^{b_j+b_{j+1}}]·cos(2πν)·e^{−2π²Q} + O(e^{−4π²Q})**  (ec. 10)
3. entropía del vector: **H_n = n − (32(n−1)/(π⁴ ln 2))·cos²(2πν)·e^{−4π²Q} + O(e^{−6π²Q})**  (ec. 12)

Y el Corolario 1 (cota **inferior** de la tasa de entropía de Shannon, basada en la entropía condicionada a la fase anterior):

  **H ≥ H(s(Δt) | ϕ(0)) = 1 − (4/(π² ln 2))·e^{−4π²Q} + O(e^{−6π²Q})**  (ec. 14)

Valores numéricos (cálculo propio con la ec. 14 sin el término O(·)): Q = 0,05 → H ≥ 0,919; Q = 0,10 → 0,989; Q = 0,15 → 0,998; Q = 0,20 → 0,9998. Para el antiguo umbral 0,997 hace falta Q ≥ 0,134; para el umbral Shannon 0,9998 de la v3.0, Q ≥ 0,202. Baudet et al. estiman experimentalmente Q ≈ 0,01 y 0,11 en dos configuraciones de su prototipo (§4). La Proposición 2 da además una cota exacta del sesgo de vectores: |ε(b)| ≤ ϑ(B)^{n−1} − 1 con B = e^{−2π²Q} y ϑ la función theta, útil para fijar n_max.

Petura et al. [petura_2016_survey] **[VERIFICADO]** reescriben la ec. 14 en términos de magnitudes de diseño del ERO:

  **H_min = 1 − (4/(π² ln 2))·exp(−π² σ_th² K T_2 / T_1³)**  (ec. 1 de Petura)

con σ_th² la varianza de jitter **térmico** por periodo, K el divisor y T_1, T_2 los periodos de RO1 y RO2. Fischer–Lubicz [fischer_2014_embedded] **[VERIFICADO]** la invierten para obtener el divisor:

  **K_D = −ln((π/2)·√((1−H_min) ln 2)) / (2π²·(T_2/T_1)·(σ_c²/T_1²))**  (ec. 2)

y con T_1 = 8,9 ns, T_2 = 8,7 ns, σ_c = 5,01 ps, H_min = 0,997 obtienen K_D ≈ 430 000 (reproducido: 431 153).

Killmann y Schindler [killmann_2008_design] **[VERIFICADO-META]** (CHES 2008) es el antecedente: modelo estocástico para un RNG de diodos ruidosos con un teorema que da "tight lower bounds for the entropy per random bit" y que también "aplica a otros diseños de RNG"; es la base de la exigencia de *stochastic model* de AIS 31 (AIS 31 v3.0 §5.4 lo desarrolla como ejemplo [KiSc08]). Ma et al. [ma_2014_entropy] **[VERIFICADO-META]** (CHES 2014) dan un modelo alternativo para el ERO usado por KU Leuven. Haddad, Teglia, Bernard y Fischer [haddad_2014_assumption] **[VERIFICADO-META]** (DATE 2014) cuestionan la hipótesis de independencia mutua de las realizaciones de jitter y proponen un enfoque multinivel transistor→jitter→generador.

### 2.3 De la medida de jitter a una cota INFERIOR de min-entropía
El encadenamiento que exige AIS 31 v3.0 (PTG.2.1–2.2, pars. 328–335) y que recomiendan [lubicz_2024_recommendations] **[VERIFICADO]** es:

1. **Medir** la varianza de jitter *térmico* por periodo σ_th² (o σ_0²) **dentro del dispositivo**, descontando la parte determinista/global (§3). Tomar el valor **mínimo** sobre el rango de tensión/temperatura y sobre varios ejemplares.
2. **Calcular Q** = σ_th²·(tiempo de acumulación)/T_1² (o su equivalente en fase) para la configuración K_D elegida.
3. **Aplicar la cota** del modelo (ec. 14 de Baudet; ec. 1 de Petura). La ec. 14 es una cota de **entropía de Shannon**. Para **min-entropía**, la ruta más directa es usar la probabilidad condicionada de la ec. 8: el sesgo máximo del bit dada la fase anterior es ε_max ≈ (2/π)·e^{−2π²Q} (primer armónico), de modo que **H_∞(s(Δt) | ϕ(0)) ≥ −log2(1/2 + ε_max)**. Cálculo propio: Q = 0,15 → ε_max ≈ 0,033 → H_∞ ≥ 0,908; Q = 0,20 → 0,965; Q = 0,30 → 0,995. Esta derivación es **propia**, aproximada (desprecia armónicos superiores) y debe validarse numéricamente en el TFM (por ejemplo con el método de Saarinen [saarinen_2021_entropy], que calcula distribuciones exactas de patrones con la gaussiana envuelta f_s(x) = (1/√(2πσ²)) Σ_i e^{−(x−F+i)²/(2σ²)} y avisa de que la cota de Baudet "is never lower than 0.415 even when Q approaches zero" y "is safe to use only under some additional assumptions").
4. **Fijar K_D** con margen (Fischer–Lubicz), y usar la **misma medida de jitter como test online** que dispara alarma si σ cae por debajo del valor usado en el paso 3.
5. **Confrontar** la cota del modelo con los estimadores de SP 800-90B sobre los *raw bits* (§5): la estimación estadística debe ser ≥ la cota del modelo; si es menor, el modelo está mal.

Requisitos numéricos vigentes (AIS 31 v3.0, PTG.2.2 [peter_2024_ais31] **[VERIFICADO]**): Shannon ≥ 0,9998 **o** min-entropía ≥ 0,98 (o ambas), y Prob(Y_j=1) ∈ (0,493; 0,507). Obsérvese que −log2(0,507) = 0,9799, es decir, la banda de sesgo permitida y la min-entropía 0,98 son coherentes por construcción. El par. 335 aclara que PTG.2 "solo permite valores fijos de clase" y que "la verificación de la afirmación de min-entropía puede requerir esfuerzos adicionales"; las diapositivas de Schindler (ECW 2024) [schindler_2024_ecw] **[VERIFICADO]** añaden: "At most 0.9998 bit Shannon entropy / 0.98 bit min-entropy can be claimed on the basis of the stochastic model. Higher entropy claims require data compression". Para PTG.3 (post-procesado criptográfico con memoria) la min-entropía puede reclamarse hasta 1 − 2^{−32} ("full entropy" de SP 800-90).

---

## 3. Medida del jitter dentro de la FPGA (sin osciloscopio)

### 3.1 Método de contador (varianza del número de periodos en ventana fija)
Se cuenta cuántos periodos de RO1 caben en N periodos de RO2 (ventana fija); la varianza del contador crece con la varianza acumulada del jitter relativo. Es la base del modelo de [killmann_2008_design] (variable "Z(t)", proceso de renovación) y del estimador embebido de Lubicz y Bochard [lubicz_2015_towards] **[VERIFICADO-META]** (IEEE TC 64(4):1191–1200), que describe "a practical and efficient method to estimate the entropy rate of a TRNG based on free running oscillators, relying on simple computations that can be embedded in logic devices such as FPGA or ASIC" (abstract). Sesgos: (i) cuantización de ±1 cuenta (necesita ventanas largas o muchas repeticiones); (ii) a ventanas largas el flicker y el jitter global inflan la varianza (pendiente 2) y se sobreestima el jitter útil; (iii) la varianza medida es la del **jitter relativo** de los dos anillos, no la de uno.

### 3.2 Método de Fischer–Lubicz (CHES 2014) — pares de bits a distancia M
[fischer_2014_embedded] **[VERIFICADO]**. Con el ERO sin divisor (K_D = 1), se toma la secuencia de bits muestreados b_j y se calcula, en K bloques de N bits consecutivos, la fracción c[i] de pares (b_j, b_{j+M}) **distintos**; por el "Fact 1" del artículo, c[i] aproxima (2(M·T_2 + ξ(t_i) − ξ(t_{i+M}))/T_1) mod 1, es decir, la posición de fase acumulada en M periodos; su **varianza sobre los K bloques** es V_0 = 4V/T_1², con V la varianza del jitter acumulado en M·T_2 (Algoritmo 1). Parámetros: K ≈ 10 000, N ≈ 100, M entre 200 y 1600 (en hardware 250–1200 en pasos de 50). Se ajusta V(M) a una recta en la zona lineal (térmica) y de la pendiente sale σ por periodo. Resultados: error < 5 % en simulación (2 %, 3 %, 5 % para σ_c = 10, 15, 20 ps); en Cyclone III: σ = 5,01 ps por periodo T_1 = 7,81 ns; con el TRNG y el medidor en FPGAs separadas, 4,9 ps / 7,69 ns (la circuitería de medida no perturba). Coste: el propio ERO más un registro de desplazamiento de ~M etapas (registros de menos de 200 etapas no dan precisión; registros grandes dejan entrar el flicker), contadores y un bloque de varianza. Como **test online** requiere ~N·K ≈ 10^6 bits del muestreador, unas 8 600 veces menos que obtener 20 000 bits post-divisor para los tests FIPS 140-1. Demuestran la detección de reducción de jitter al enfriar el chip. Sesgos: la fórmula del "Fact 1" falla cuando la fase cae cerca de min(α, 1−α) (semiperiodos desbalanceados), casos "raros y fáciles de detectar"; a M grande domina el flicker; el jitter medido es el **relativo** entre los dos anillos.

### 3.3 Coherent sampling como medidor
En COSO, la propia distribución de CSCnt mide el jitter acumulado en un periodo de batido: Var[CSCnt] = E[CSCnt]·Var[Δ]/E[Δ]² [peetermans_2021_configurable] **[VERIFICADO]**. Peetermans et al. usan E[CSCnt] y su varianza medidos en línea para elegir la configuración de ROs (calibración dinámica). Ventaja: no requiere hardware adicional; inconveniente: resolución de Δ (decenas de ps) y de nuevo mide jitter **relativo**.

### 3.4 Separar jitter global/determinista del local: medidas diferenciales con anillos idénticos
Idea (Bochard et al. 2010; Fischer 2012 [fischer_2012_closer] **[VERIFICADO-META]**): si dos anillos idénticos y adyacentes comparten la alimentación, el jitter **global** afecta a ambos casi igual y se cancela en la fase **relativa**; lo que queda es (aprox.) la suma de los jitters **locales** (térmicos) de ambos. Por eso todos los métodos embebidos anteriores son *diferenciales* y por eso miden Var[local_1] + Var[local_2], no la de uno. Lubicz y Skórski [lubicz_2024_jitter] **[VERIFICADO]** (arXiv 2410.08259, 2024) formalizan el **"jitter transfer principle"** (equivalencia entre dos osciladores con jitter y uno sin jitter que muestrea a otro con jitter combinado), dan cotas de error y proponen **dos métodos con tres osciladores** para recuperar los jitters individuales a partir de las tres medidas diferenciales por pares: el Método 1 supone varianza lineal con el periodo; el Método 2 no lo supone pero necesita un multiplexor/flip-flop extra. Experimento en Cyclone V con anillos de 32 elementos (65,5 / 58,0 / 70,6 MHz), 1 Mbit por par, medidos con el método de [FL14]: jitter relativo total σ'/T entre 1,5·10⁻³ y 3,3·10⁻³ por periodo; los jitters individuales difieren hasta en un factor 2 entre métodos en un experimento, lo que "muestra que la hipótesis de varianza lineal con el periodo, aunque razonable y a veces cierta, está en general en contradicción con los hechos". Conclusión práctica para el TFM: la medida diferencial con dos anillos es **necesaria** para eliminar el global pero **no basta** para conocer el jitter de cada anillo; con tres anillos y el Método 2 sí.

Haddad et al. [haddad_2014_assumption] **[VERIFICADO-META]** (DATE 2014) discuten precisamente la hipótesis de independencia de las realizaciones de jitter en que descansan todas estas cancelaciones.

### 3.5 Órdenes de magnitud del jitter por periodo en FPGA
Todas las cifras son de **jitter de periodo** (σ_T) medido **externamente** salvo indicación:
- Spartan-6 (45 nm) y Cyclone V (**28 nm**): "comparable period jitter ranging from **2 to 4 ps** for clock periods between 4 and 8 ns"; SmartFusion2 (65 nm flash): 8–10 ps; medido con osciloscopio LeCroy y sonda diferencial WaveLink 4 GHz [petura_2016_survey] **[VERIFICADO]**. Jitter útil asumido: ≈ 4, 3 y 8 ps respectivamente con T ≈ 3 ns.
- Cyclone III: 5,01 ps por periodo de 7,81 ns, medida **embebida** [fischer_2014_embedded] **[VERIFICADO]**.
- Cyclone III 2 ps y Virtex-5 2,5 ps (STR ~300 MHz), osciloscopio [cherkaoui_2013_very] **[VERIFICADO]**.
- Spartan-6: "jitter strength" σ²/t = 2,9 fs (variancia por unidad de tiempo), ROs de 2,17–2,74 ns [yang_2018_estrng_slides] **[VERIFICADO]**; equivale a σ_T ≈ √(2,9 fs × 2,2 ns) ≈ 2,5 ps por periodo (cálculo propio).
- Cyclone V, anillos de 32 elementos (~15 ns): σ'/T ≈ 1,0–2,3·10⁻³ individual (≈ 15–35 ps), medida embebida [lubicz_2024_jitter] **[VERIFICADO]**; la diferencia con los 2–4 ps de Petura se explica por anillos mucho más largos (más etapas ⇒ más jitter por periodo).
- **Artix-7 (28 nm): no se ha encontrado ninguna publicación con una medida de σ por periodo específica.** Lo más próximo es Cyclone V (28 nm, Petura) y Spartan-7 (misma fábrica 7-series que Artix-7; Peetermans 2021 publica caudal y min-entropía pero no σ). Es un dato que el TFM puede aportar (§7). Regla práctica derivada: con T_1 ≈ 3–5 ns y σ_th ≈ 2–4 ps se tiene σ_th/T_1 ≈ 10⁻³, y para Q ≥ 0,2 hace falta acumular del orden de (0,2/(10⁻³)²) ≈ 2·10⁵ periodos, coherente con los K de 8·10⁴–4·10⁵ de la literatura.

Sobre la dependencia con tensión y temperatura: Fischer–Lubicz muestran que enfriar reduce σ (test que dispara) [fischer_2014_embedded] **[VERIFICADO]**; Martín, Peris-Lopez, Tapiador y San Millán [martin_2016_new] **[VERIFICADO]** (IEEE TII 12(1):91–100) validan su COSO con STR "under supply voltage and temperature variations" en Spartan-3E (el texto leído usa XC3S500E; el resumen del buscador decía Spartan-6, se toma el texto); Barbareschi et al. [barbareschi_2016_ring] **[VERIFICADO-META]** caracterizan estadísticamente ROs en muchos Spartan-6 para PUF, incluyendo el efecto de parámetros externos.

---

## 4. Implementación en Xilinx 7-series con Vivado

### 4.1 Lazos combinacionales: DRC, atributos y excepciones de timing
- Un anillo de inversores es un **lazo combinacional**; Vivado lo detecta en el DRC **LUTLP-1** ("LUT cells form a combinatorial loop... can create a race condition and timing analysis may not be accurate"). Según los artículos de soporte de AMD [amd_support_lutlp], **[VERIFICADO-META: existencia de los hilos confirmada por buscador; el texto de la respuesta no se ha podido abrir por bloqueo anti-bot]**, la forma sancionada es `set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets <ruta/net>]` sobre **cualquier net del lazo**, con lo que la comprobación pasa a **LUTLP-2 "Combinatorial Loop Allowed"**; rebajar la severidad con `set_property SEVERITY {Warning} [get_drc_checks LUTLP-1]` se documenta como "not recommended". **No se ha encontrado `ALLOW_COMBINATORIAL_LOOPS` en la lista de atributos de UG901** (2022.1 PDF ni 2026.1 web) ni existe página propia en UG912 (404); parece documentarse solo en respuestas de soporte y en el mensaje del DRC. Conviene decirlo así en el TFM.
- **DONT_TOUCH** (UG912 2026.1) [amd_ug912_dont_touch] **[VERIFICADO]**: "directs the tool to not optimize a user hierarchy, instantiated component, or signal"; y, crucial: "Unlike KEEP and KEEP_HIERARCHY, DONT_TOUCH is forward-annotated to place and route to prevent logic optimization during implementation". Aplicable a celdas y nets; puede ponerse en RTL o XDC.
- **KEEP** (UG912 2026.1) [amd_ug912_keep] **[VERIFICADO]**: "instructs the synthesis tool to keep the signal it was placed on"; "Affected steps: synthesis" **solo**; "Recommended: Set this attribute in the RTL only". Conclusión: para un RO, KEEP no basta (opt_design puede colapsarlo); usar DONT_TOUCH en las LUT y nets del anillo.
- **set_disable_timing** (UG835 2026.1) [amd_ug835_set_disable_timing] **[VERIFICADO]**: `set_disable_timing -from <pin> -to <pin> [objeto]`; ejemplo del manual: `set_disable_timing -from A6 -to O [get_cells my_lut_instance]` "disables the timing path from the A6 input pin to the O output pin... effectively breaking the loop". Es la forma correcta de que el STA no recorra el lazo; `set_false_path` (UG835) [amd_ug835_set_false_path] **[VERIFICADO-META]** no rompe el lazo, solo excluye caminos con origen/destino sincronizados, y el reloj generado por el RO **no debe** declararse con `create_clock` salvo para analizar el camino RO→FF del muestreador (que sí conviene restringir o marcar asíncrono con ASYNC_REG en el sincronizador).
- UG903 (constraints) y UG949 (metodología) son las referencias naturales para estas excepciones, pero **no se han podido abrir** las páginas concretas en esta investigación [amd_ug903] [amd_ug949] **[NO VERIFICADO]**; citar solo las URL raíz `https://docs.amd.com/r/en-US/ug903-vivado-using-constraints` y `.../ug949-vivado-design-methodology`.

### 4.2 Fusión de anillos idénticos: instanciar primitivas y fijar posición
- La síntesis elimina inversores en cascada (`not(not x)` = x) y **fusiona lógica equivalente**; dos anillos descritos con la misma RTL y sin estado son candidatos a fusionarse. El tutorial de tseng.engineering [tseng_ring_oscillators] **[VERIFICADO]** lo resume: "The optimizer removes ring oscillators as useless logic" y la solución es `dont_touch = "yes"` en las nets, `KEEP_HIERARCHY` en la instancia, e instanciar **LUT1 con INIT** (LUT1 con INIT = 2'b01 es un inversor) y colocar con `LOC`. OpenTRNG (CEA-Leti) hace lo mismo: "one LUT2 for the NAND gate and several LUT1 units for the inverters", con `constraints.xdc` que aísla cada RO "within their respective bank" y lo rodea de "a forbidden area to ensure isolation" [opentrng_2025_docs] **[VERIFICADO]**. Peetermans et al. construyen sus ROs solo con LUTs y explotan la variabilidad **intra-LUT** (qué pin físico A1..A6 lleva la señal) para ajustar el periodo con resolución fina [peetermans_2021_configurable] **[VERIFICADO]**.
- **LOC** (UG912 2026.1) [amd_ug912_loc] **[VERIFICADO]**: "specifies the placement assignment of a logic cell to the SITE resources"; en Verilog `(* LOC = "SLICE_X0Y0" *)`, en VHDL `attribute LOC of ... : signal is "SLICE_X0Y0";`, en XDC `set_property LOC SLICE_X0Y0 [get_cells ...]`. **BEL** (UG912 2026.1) [amd_ug912_bel] **[VERIFICADO]**: "specifies the placement of a leaf-level Cell within a SLICE/CLB", p. ej. `set_property BEL A5FF [get_cells ...]` (para LUT: A6LUT, B6LUT, ...). Con LOC+BEL se fija cada LUT1 del anillo; el rutado sigue siendo libre (Wold–Tan ya observaron que la frecuencia depende del rutado [wold_2009_analysis] **[VERIFICADO-META]**), así que dos anillos "idénticos" no tendrán la misma frecuencia, lo cual para ERO/MURO es deseable (evita locking) y para COSO obliga a calibrar Δ.
- Pblocks: sirven para acotar la región pero, como recuerda el tutorial citado, son guías "no estrictas"; la reproducibilidad exige LOC/BEL.

### 4.3 Injection locking y acoplamiento entre anillos
- Markettos y Moore [markettos_2009_frequency] **[VERIFICADO]** (CHES 2009): inyectando una frecuencia en la alimentación, los anillos se enganchan (condición de Adler) y el jitter útil desaparece; con anillos discretos 74HC04 de 3 y 5 inversores, 24 MHz a 900 mV pk-pk producen enganche; en un microcontrolador seguro, ~1,8 MHz a 500 mV pk-pk reducen el espacio de claves de 2^64 a ~3 300; atacan una tarjeta EMV de 2004. Explican que el enganche depende de la **asimetría** entre anillos y que "the frequency injection attack is much more powerful, since it can attack all bits" del TRNG.
- Bayon et al. [bayon_2012_contactless] **[VERIFICADO-META]** (COSADE 2012): ataque electromagnético **sin contacto** que engancha 50 ROs de un TRNG en FPGA y controla el sesgo monobit incluso con campos débiles.
- Bochard et al. [bochard_2010_true] **[VERIFICADO-META]** (IJRC 2010): evidencia experimental en FPGA de que los anillos de un MURO interactúan y producen pseudo-aleatoriedad; Petura et al. [petura_2016_survey] **[VERIFICADO]** comentan que colocaron los dos anillos del ERO "manually in order to ensure repeatability" y que "although both rings were placed in close vicinity, apparently, they did not lock", pero que en COSO "even rings that..." son difíciles de ajustar. Fischer–Lubicz [fischer_2014_embedded] recuerdan que "(locking of rings)" es una de las debilidades que el medidor de jitter puede detectar y que "the jitter needs to be evaluated for all ring oscillators exploited in the generator".
- Medidas de mitigación con soporte en la literatura leída: (i) anillos de longitudes distintas/no armónicas; (ii) separación física y área prohibida (OpenTRNG); (iii) medir el jitter en línea y disparar alarma (Fischer–Lubicz); (iv) usar la medida diferencial para no contar el global como entropía (Lubicz–Skórski); (v) preferir arquitecturas con alarma intrínseca (COSO: el contador se sale de rango si los anillos se enganchan).

### 4.4 Alimentación y temperatura
Enfriar reduce el ruido térmico y por tanto σ; Fischer–Lubicz lo usan como ataque de prueba [fischer_2014_embedded] **[VERIFICADO]**. La tensión cambia la frecuencia de los anillos (y por tanto ν y Δ) más que σ; en COSO esto puede sacar Δ del rango y en ERO desplaza cos(2πν) (ec. 10 de Baudet: el sesgo de pares es proporcional a cos(2πν)). Martín et al. [martin_2016_new] **[VERIFICADO]** argumentan que los STR son más robustos a variaciones de tensión que los RO y que su jitter de periodo no depende del número de etapas. Para la Basys 3 (alimentación USB de 5 V regulada en placa a 1,0 V para el core) no se ha encontrado caracterización publicada.

---

## 5. Tests de salud, tests online y estimadores de min-entropía

### 5.1 SP 800-90B (enero 2018) — health tests aprobados
[turan_2018_sp80090b] **[VERIFICADO]** (DOI 10.6028/NIST.SP.800-90B). §4.4: dos tests aprobados; "if these two health tests are included ... no other tests are required"; probabilidad de falso positivo recomendada **α = 2⁻²⁰**.

**Repetition Count Test (RCT, §4.4.1).** Detecta fallos catastróficos ("stuck"). Dada la min-entropía evaluada H, la probabilidad de n muestras idénticas consecutivas es ≤ 2^{−H(n−1)}. Umbral:

  **C = 1 + ⌈−log₂(α) / H⌉**

(el menor entero con α ≥ 2^{−H(C−1)}). Ejemplo del documento: α = 2⁻²⁰, H = 2,0 → C = 1 + 20/2 = 11. Algoritmo: A = next(); B = 1; X = next(); si X = A entonces B++ y si B ≥ C fallo; si no A = X, B = 1. El propio NIST advierte que "this test is not very powerful". Cálculo propio: fuente binaria H = 1 → C = 21; H = 0,98 → C = 22.

**Adaptive Proportion Test (APT, §4.4.2).** Detecta pérdidas grandes de entropía. Toma una muestra A y cuenta cuántas veces reaparece en las siguientes W−1; si el contador B ≥ C, fallo. **W = 1024 si la fuente es binaria, W = 512 si no** (nota: el guion del TFM tenía los valores intercambiados). C es el menor valor con Pr(B ≥ C) ≤ α, calculable como **C = 1 + CRITBINOM(W, 2^{−H}, 1−α)** (nota 10 del documento). Tabla 2 del documento (α = 2⁻²⁰): binario W = 1024: H = 0,2 → 941; 0,4 → 840; 0,6 → 748; 0,8 → 664; 1,0 → 589. No binario W = 512: H = 0,5 → 410; 1 → 311; 2 → 177; 4 → 62; 8 → 13. Cálculo propio (scipy.binom.ppf) reproduce 589 y 664 y da **C = 596 para H = 0,98**, C = 625 para H = 0,9. Para fuentes binarias se permite además comprobar W − B ≥ C.

Requisitos de datos (§3.1.1): un **dataset secuencial de al menos 1 000 000 muestras** *raw*; para los **restart tests**, 1 000 reinicios × 1 000 muestras (matriz 1000×1000). Dos pistas: **IID track** (solo si el solicitante justifica IID y los tests de permutación/χ² no lo refutan) que usa únicamente el estimador **Most Common Value**; y **non-IID track** con **diez estimadores** (§6.3.1–6.3.10): Most Common Value; Collision; Markov; Compression; t-Tuple; Longest Repeated Substring (LRS); Multi Most Common in Window (MultiMCW) prediction; Lag prediction; MultiMMC prediction; LZ78Y prediction. La estimación es el **mínimo** de todos ellos (y, para alfabetos no binarios, también se evalúa la secuencia como cadena de bits). Definición: min-entropía H = −log₂ max_i p_i (§2; "the probability of observing any particular value for X is no greater than 2^{−H}"). El documento reconoce (§6.3.1, nota 11) que el estimador MCV puede subestimar la min-entropía verdadera.

### 5.2 Herramienta oficial `SP800-90B_EntropyAssessment`
[nist_ea_github] **[VERIFICADO]** (https://github.com/usnistgov/SP800-90B_EntropyAssessment). C++11 con OpenMP (GCC recomendado); dependencias en Ubuntu: `libbz2-dev libdivsufsort-dev libjsoncpp-dev libssl-dev libmpfr-dev` (y GMP). Compilación: `make` (o `make iid`, `make non_iid`, `make restart`, `make conditioning`; soporta `make ARCH=aarch64 CROSS_COMPILE=...`). Ejecutables: `ea_iid`, `ea_non_iid`, `ea_restart`, `ea_conditioning`, `ea_transpose`. Uso: `./ea_non_iid [-i|-c] [-a|-t] [-v] [-l <index>,<samples>] <file> [bits_per_symbol]`; `./ea_restart [-i|-n] [-v] <file> [bits_per_symbol] <H_I>`; `./ea_conditioning [-v] <n_in> <n_out> <nw> <h_in>`. **Formato de entrada:** fichero **binario**, un símbolo por byte, con `bits_per_symbol` entre 1 y 8 (para bits *raw* de un TRNG: 1 bit/símbolo, cada byte 0x00/0x01, o bien empaquetados y `-b`? — comprobar en el README de la versión usada; la extracción realizada confirma "binary data files with configurable bits-per-symbol (fits within single byte)"). Para el TFM: ≥ 1 000 000 símbolos raw (mejor varios millones) y la matriz de reinicios. Turan (NIST, 2023) [turan_2023_slides] **[VERIFICADO]** confirma la estructura de dos pistas, el restart dataset y anuncia un plan de revisión de 800-90B.

### 5.3 AIS 20/31 v3.0 — tests online, test de fallo total, test de arranque y suite T_irn
[peter_2024_ais31] **[VERIFICADO]**.
- **Start-up test** (PTG.2.3): tras el arranque, detecta fallo total y debilidades estadísticas severas; no se emite nada antes de pasarlo.
- **Online test** (PTG.2.4; §4.5.3, pars. 808–819): "shall detect non-tolerable entropy defects of the raw random numbers sufficiently soon"; debe estar **adaptado al modelo estocástico**: el modelo define el conjunto de parámetros admisibles A_good y el test debe fallar con alta probabilidad si el parámetro verdadero cae en A_bad (par. 809–812). Ejemplo del par. 829: un monobit es adecuado para un modelo iid de moneda pero no para otros. Diferencia esencial con 800-90B: aquí el test online no es genérico sino derivado del modelo (para el ERO, la medida embebida de jitter de Fischer–Lubicz es un test online *ad hoc* ideal, y así lo plantean sus autores).
- **Total failure test** (PTG.2.5; §4.5.4, pars. 841–849): detecta que "the entropy per raw random number bit has decreased to (essentially) 0"; puede ser un sensor o un test estadístico; ejemplo del par. 847: fallo si los últimos 40 bits raw son constantes, y se acepta explícitamente "the repetition count test defined in [SP800-90B], Subsection 4.4.1". Debe impedir la salida de números internos que dependan de raw generados tras el fallo.
- **Suite de caja negra T_irn** (PTG.2.6; §4.6.3–4.6.4): T1 monobit, T2 póker, **T3 MultiMMC Prediction Estimate** y **T4 LZ78Y Prediction Estimate** (tomados de SP 800-90B como parte de la armonización BSI–NIST); requiere 2 040 000 bits.
- **Stochastic model** obligatorio (par. 328): "The evaluation of a PTRNG shall be based on a verifiable, substantiated stochastic model", con un único nivel de detalle independiente del EAL.

### 5.4 Relación entre SP 800-22 y SP 800-90B
- SP 800-22 Rev. 1a [bassham_2010_sp80022] **[VERIFICADO-META]** es una batería de tests de hipótesis de uniformidad/independencia sobre secuencias de bits. Un DRBG (AES-CTR, ChaCha) con **cero entropía** pasa 800-22 por construcción; también lo pasa un TRNG con post-procesado criptográfico aunque su fuente tenga min-entropía baja (Saarinen: "Cryptographic post-processing methods such as the SHA2 hash completely mask statistical defects while still allowing guessing attacks" [saarinen_2021_entropy] **[VERIFICADO]**). Por eso 800-90B (i) exige datos **raw** de la fuente de ruido, (ii) estima **min-entropía** (adversarial: probabilidad del valor más probable), no uniformidad, y (iii) usa **predictores** (MultiMCW, Lag, MultiMMC, LZ78Y) que intentan adivinar la muestra siguiente.
- NIST lo ha dicho explícitamente al decidir revisar 800-22: "rejecting its use for assessing cryptographic random number generators" [nist_2022_decision] **[VERIFICADO]**. AIS 31 v3.0 relega los tests de caja negra a la suite T_irn complementaria y basa la evaluación en el modelo estocástico.
- Evidencia empírica de que tests estadísticos aprueban fuentes malas: Hurley-Smith y Hernández-Castro [hurleysmith_2018_certifiably] **[VERIFICADO-META]** (IEEE TIFS 13(4):1031–1041) analizan el TRNG certificado EAL4+ de la tarjeta DESFire EV1 y encuentran "clear and consistent biases, despite good performance in most randomness tests"; su crítica general en [hurleysmith_2018_great] **[VERIFICADO-META]**. Blanco-Romero et al. [blancoromero_2026_entropy] **[VERIFICADO]** (arXiv 2607.08865) muestran que el RNG del ESP32 con la radio apagada "continues returning statistically plausible bytes... producing pure pseudorandomness by design" y pasa los mismos cribados estadísticos que con la radio activa.
- Nota histórica: 800-22 incluye un test de "complejidad lineal" que comprueba si un LFSR es "suficientemente largo", algo criptográficamente irrelevante (Saarinen, §I.B).
- Consecuencia para el TFM: usar 800-22 solo como *sanity check* sobre la salida post-procesada (y decirlo), y 800-90B + modelo sobre los bits raw.

### 5.5 Tests de min-entropía ligeros para hardware
Grujić, Rožić, Yang y Verbauwhede [grujic_2017_lightweight] **[VERIFICADO-META]** (IEEE ESL 9(2):45–48): primera implementación ligera integrada de los tests de predicción de 800-90B para estimación de min-entropía en línea. Rožić et al. [rozic_2016_iterating] **[VERIFICADO-META]** (HOST 2016) sobre post-procesado de Von Neumann iterado bajo restricciones de hardware. Ambos son relevantes si el TFM quiere un health test más informativo que RCT/APT.

---

## 6. Trabajos previos: TRNG de FPGA frente a RNG de microcontroladores; el RNG del ESP32

### 6.1 Documentación de Espressif (fuente primaria)
- **ESP32 Technical Reference Manual v5.8, cap. 18 "Random Number Generator (RNG)"** [espressif_trm_esp32] **[VERIFICADO]**: "Every 32-bit value that the system reads from the RNG_DATA_REG register... is a true random number. These true random numbers are generated based on the thermal noise in the system and the asynchronous clock mismatch. Thermal noise comes from the high-speed ADC or SAR ADC or both... fed into the random number generator through an XOR logic gate as random seeds." Con ruido del SAR ADC "the random number generator is fed with a 2-bit entropy in one clock cycle of RC_FAST_CLK (8 MHz)... it is advisable to read the RNG_DATA_REG register at a maximum rate of 500 kHz"; con el ADC de alta velocidad (RF), 2 bits por ciclo APB (80 MHz) → lectura máxima 5 MHz. "A data sample of 2 GB... read... at a rate of 5 MHz with only the high-speed ADC being enabled, has been tested using the Dieharder Random Number Testsuite (version 3.31.1). The sample passed all tests." Y: "make sure at least either the SAR ADC or high-speed ADC is enabled. Otherwise, **pseudo-random numbers will be returned**"; con Wi-Fi activo el ADC de alta velocidad "can be saturated in some extreme cases, which lowers the entropy", por lo que se aconseja habilitar también el SAR ADC.
- **ESP-IDF Programming Guide, "Random Number Generation" (ESP32)** [espressif_idf_random] **[VERIFICADO]**: el RNG produce números verdaderamente aleatorios si "RF subsystem is enabled, i.e., Wi-Fi or Bluetooth are enabled", o si se ha llamado a `bootloader_random_enable()` (SAR ADC) y no se ha deshabilitado, o durante el bootloader de segunda etapa; "If none of the above conditions are true, the output of the RNG should be considered as pseudo-random only". `esp_random()` "automatically busy-waits to ensure enough external entropy has been introduced into the hardware RNG state... This delay makes sure the reading frequency does not exceed 15–75 KHz" (texto de la página en su versión actual). La documentación de otros SoC (ESP32-S2 y posteriores) describe una **fuente secundaria basada en muestrear el oscilador RC de 8 MHz**, "siempre habilitada" y que por sí sola pasa Dieharder (extracto del buscador; página no abierta) **[NO VERIFICADO]**.
- Conclusión de diseño: el RNG del ESP32 es un **mezclador hardware (estado interno + XOR) alimentado por LSB de ADC y por un reloj asíncrono**; Espressif no publica **modelo estocástico ni estimación de min-entropía**; su validación pública es Dieharder (caja negra). La calidad depende del **estado del sistema** (radio encendida, ADC), no es una propiedad fija del periférico.

### 6.2 Literatura académica sobre el RNG del ESP32
- Castillo et al. [castillo_2026_automated] **[VERIFICADO-META]** (*IoT* 7(1):26, MDPI, 2026, DOI 10.3390/iot7010026): marco automatizado web para ejecutar **SP 800-22** sobre RNG de IoT; validación con 2 GB del TRNG hardware del **ESP32-C3** (1 000 secuencias de 10⁶ bits): pasan los 15 tests. Según el resumen consultado, **no** aplica SP 800-90B ni estima min-entropía (la página del editor devolvió 403; afirmación basada en el resumen del buscador).
- Hidayatulloh et al. [hidayatulloh_2024_performance] **[VERIFICADO-META]** (ICRAMET 2024, IEEE, pp. 44–49, DOI 10.1109/ICRAMET62801.2024.10809333): usan el RNG del ESP32 como nonce para AES-CTR sobre LoRa y comprueban con la NIST STS (800-22) que "pass".
- Blanco-Romero, Almenares, Díaz-Sánchez y Marín-López [blancoromero_2026_entropy] **[VERIFICADO]** (arXiv 2607.08865, jul.–sep. 2026): identifican el problema de arranque en frío del ESP32 (RNG pseudoaleatorio con RF apagada que pasa los cribados estadísticos) y proponen **admitir la salida del RNG solo mientras la RF está activa**, combinándola con ruido de SRAM no inicializada y "cápsulas de entropía" firmadas post-cuánticamente. No publican (en el resumen) min-entropía 800-90B del ESP32.
- **No se ha encontrado** ningún trabajo académico que (a) aplique los estimadores no-IID de SP 800-90B a los bits *raw* del RNG del ESP32 clásico (Xtensa, 2016) en sus distintos estados (RF on/off, SAR ADC on/off, distintas tasas de lectura), ni (b) compare de forma controlada un RO-TRNG en FPGA con el RNG de un microcontrolador comercial usando la **misma** metodología (800-90B + AIS 31 v3.0) y las mismas condiciones ambientales. Los hilos del foro esp32.com sobre calidad del RNG con Dieharder [esp32forum_rng] **[NO VERIFICADO]** no se han podido abrir (protección anti-bot) y no deben citarse como evidencia.
- Comparativas FPGA vs microcontrolador en general: no se ha encontrado literatura que compare directamente ambos; lo más próximo son comparativas de TRNG comerciales certificados (Hurley-Smith) y las notas de aplicación de fabricantes (p. ej. la AN4230 de STMicroelectronics sobre validación del RNG de STM32 con la NIST STS, aparecida en búsquedas, **[NO VERIFICADO]**).

---

## 7. Qué hueco llenaría este TFM (formulación honesta)

No se reclama novedad absoluta: el ERO/COSO/MURO, su modelo (Baudet 2011; Ma 2014), la medida embebida de jitter (Fischer–Lubicz 2014; Lubicz–Bochard 2015; Lubicz–Skórski 2024), la comparativa de núcleos AIS-compatibles en FPGA (Petura 2016), la calibración automática de COSO en 7-series (Peetermans 2019/2021) y la implementación de referencia abierta sobre Arty A7 (OpenTRNG, CEA-Leti) existen. Lo que **no hemos encontrado** en la literatura consultada, y que el TFM puede aportar de forma modesta pero verificable, es:

1. **Una medida publicada de jitter térmico por periodo en Artix-7** (XC7A35T) obtenida **dentro de la FPGA** con un método diferencial (Fischer–Lubicz y/o Lubicz–Skórski con tres anillos), separando explícitamente la componente lineal (térmica) de la cuadrática (flicker/global) en el diagrama log-log, con barras de error y dependencia con la temperatura y la tensión del núcleo.
2. **El encadenamiento completo medida → Q → cota inferior de min-entropía → parámetros (K_D) → health tests dimensionados**, aplicado a la Basys 3 y confrontado con los diez estimadores no-IID de SP 800-90B sobre bits raw y con la suite T_irn y los requisitos PTG.2 de **AIS 20/31 v3.0 (2024)**, versión que la mayoría de la literatura anterior a 2024 no pudo usar.
3. **Una caracterización del RNG del ESP32 con SP 800-90B** (estimadores no-IID y restart tests) en sus estados operativos (RF on/off, SAR ADC on/off, tasa de lectura) — no hemos encontrado ninguna; las evaluaciones publicadas usan solo 800-22 o Dieharder.
4. **La comparación controlada FPGA vs ESP32 con la misma metodología y el mismo banco de pruebas**, discutiendo por qué 800-22 no discrimina (y mostrando, si ocurre, un caso en que el ESP32 pasa 800-22 con min-entropía 800-90B baja, en línea con Blanco-Romero et al. 2026 y con la decisión de NIST de 2022).
5. Como subproducto, un **flujo Vivado reproducible** (LUT1/LUT2 instanciados, DONT_TOUCH, LOC/BEL, ALLOW_COMBINATORIAL_LOOPS, set_disable_timing) documentado con las referencias oficiales UG912/UG835, señalando explícitamente que ALLOW_COMBINATORIAL_LOOPS no aparece en UG901.

Limitaciones que conviene declarar: un solo ejemplar de FPGA (no hay estadística entre dispositivos como en Barbareschi 2016); sin osciloscopio de alta velocidad para validar externamente el jitter (la validación cruzada será entre métodos embebidos y con la coherencia modelo/estimadores); las medidas de temperatura serán las que permita el laboratorio; y la cota de min-entropía derivada del primer armónico (§2.3) es una aproximación propia que debe contrastarse numéricamente.

---

## 8. Tabla resumen de referencias y estado de verificación

| Clave BibTeX | Referencia | Estado |
|---|---|---|
| turan_2018_sp80090b | NIST SP 800-90B (2018) | VERIFICADO (PDF completo) |
| nist_ea_github | usnistgov/SP800-90B_EntropyAssessment | VERIFICADO |
| turan_2023_slides | Turan, "SP 800-90B in Depth and Revision", NIST 2023 | VERIFICADO (PDF) |
| bassham_2010_sp80022 | NIST SP 800-22 Rev. 1a (2010) | VERIFICADO-META (Crossref) |
| nist_2022_decision | NIST, Decision to Revise SP 800-22 Rev. 1a (19/04/2022) | VERIFICADO |
| peter_2024_ais31 | BSI AIS 20/31 Functionality classes v3.0 (10/09/2024) | VERIFICADO (PDF completo) |
| killmann_2011_ais31 | BSI AIS 20/31 Functionality classes v2.0 (18/09/2011) | VERIFICADO (PDF) |
| bsi_2025_transition | BSI Transition Policy to v3.0 (15/04/2025) | VERIFICADO (PDF) |
| schindler_2024_ecw | Schindler, "The New AIS 20/31", ECW 2024 (diapositivas) | VERIFICADO (PDF) |
| schindler_2023_nist | Schindler, "Overview of AIS 20/31", NIST 2023 | VERIFICADO (PDF) |
| lubicz_2024_recommendations | Lubicz & Fischer, Recommendations… PTRNG v1.0, ePrint 2024/301 | VERIFICADO (PDF) |
| baudet_2011_security | Baudet, Lubicz, Micolod, Tassiaux, J. Cryptology 2011 | VERIFICADO (ePrint PDF + Crossref) |
| killmann_2008_design | Killmann & Schindler, CHES 2008 | VERIFICADO-META (Crossref) |
| schindler_2002_evaluation | Schindler & Killmann, CHES 2002 | VERIFICADO-META (Crossref) |
| sunar_2007_provably | Sunar, Martin, Stinson, IEEE TC 2007 | VERIFICADO-META (Crossref) |
| wold_2009_analysis | Wold & Tan, IJRC 2009 | VERIFICADO-META (Crossref) |
| bochard_2010_true | Bochard, Bernard, Fischer, Valtchanov, IJRC 2010 | VERIFICADO-META (Crossref) |
| fischer_2008_enhancing | Fischer, Bernard, Bochard, Varchola, FPL 2008 | VERIFICADO-META (Crossref) |
| valtchanov_2008_modeling | Valtchanov, Aubert, Bernard, Fischer, DDECS 2008 | VERIFICADO-META (Crossref) |
| valtchanov_2009_enhanced | Valtchanov, Fischer, Aubert, ICSCS 2009 | VERIFICADO-META (Crossref) |
| fischer_2012_closer | Fischer, COSADE 2012 | VERIFICADO-META (Crossref) |
| fischer_2014_embedded | Fischer & Lubicz, CHES 2014 | VERIFICADO (PDF completo) |
| ma_2014_entropy | Ma, Lin, Chen, Xu, Liu, Jing, CHES 2014 | VERIFICADO-META (Crossref) |
| haddad_2014_assumption | Haddad, Teglia, Bernard, Fischer, DATE 2014 | VERIFICADO-META (Crossref) |
| lubicz_2015_towards | Lubicz & Bochard, IEEE TC 2015 | VERIFICADO-META (Crossref) |
| petura_2016_survey | Petura, Mureddu, Bochard, Fischer, Bossuet, FPL 2016 | VERIFICADO (PDF HAL completo) |
| bernard_2019_physical | Bernard, Haddad, Fischer, Nicolai, J. Cryptology 2019 | VERIFICADO-META (Crossref) |
| lubicz_2024_jitter | Lubicz & Skórski, arXiv 2410.08259 (2024) | VERIFICADO (PDF completo) |
| saarinen_2021_entropy | Saarinen, arXiv 2102.02196 (2021) | VERIFICADO (PDF) |
| kohlbrenner_2004_embedded | Kohlbrenner & Gaj, FPGA 2004 | VERIFICADO (PDF + Crossref) |
| varchola_2010_new | Varchola & Drutarovský, CHES 2010 | VERIFICADO (PDF + Crossref) |
| cherkaoui_2013_very | Cherkaoui, Fischer, Fesquet, Aubert, CHES 2013 | VERIFICADO (PDF + Crossref) |
| martin_2016_new | Martín, Peris-Lopez, Tapiador, San Millán, IEEE TII 2016 | VERIFICADO (PDF repositorio + Crossref) |
| rozic_2015_highly | Rožić, Yang, Dehaene, Verbauwhede, DAC 2015 | VERIFICADO-META (Crossref) |
| rozic_2016_iterating | Rožić, Yang, Dehaene, Verbauwhede, HOST 2016 | VERIFICADO-META (Crossref) |
| grujic_2017_lightweight | Grujić, Rožić, Yang, Verbauwhede, IEEE ESL 2017 | VERIFICADO-META (Crossref) |
| yang_2018_estrng | Yang, Rožić, Grujić, Mentens, Verbauwhede, TCHES 2018 | VERIFICADO (página TCHES) |
| yang_2018_estrng_slides | Diapositivas CHES 2018 de ES-TRNG | VERIFICADO (PDF) |
| grujic_2018_closer | Grujić, Rožić, Yang, Verbauwhede, ISCAS 2018 | NO VERIFICADO |
| grujic_2022_trot | Grujić & Verbauwhede, IEEE TCAS-I 2022 | VERIFICADO-META (Crossref) |
| peetermans_2019_portable | Peetermans, Rožić, Verbauwhede, FPL 2019 | VERIFICADO (PDF Lirias + Crossref) |
| peetermans_2021_configurable | Peetermans, Rožić, Verbauwhede, ACM TRETS 2021 | VERIFICADO (PDF COSIC + Crossref) |
| fischer_2002_true | Fischer & Drutarovský, CHES 2002 | VERIFICADO-META (Crossref) |
| markettos_2009_frequency | Markettos & Moore, CHES 2009 | VERIFICADO (PDF + Crossref) |
| bayon_2012_contactless | Bayon et al., COSADE 2012 | VERIFICADO-META (Crossref) |
| barbareschi_2016_ring | Barbareschi, Di Natale, Bruguier, Benoit, Torres, Micpro 2016 | VERIFICADO-META (Crossref) |
| hurleysmith_2018_certifiably | Hurley-Smith & Hernández-Castro, IEEE TIFS 2018 | VERIFICADO-META (Crossref) |
| hurleysmith_2018_great | Hurley-Smith & Hernández-Castro, SSR 2018 | VERIFICADO-META (Crossref) |
| amd_ug912_dont_touch / _keep / _loc / _bel | UG912 Vivado Properties (2026.1) | VERIFICADO |
| amd_ug835_set_disable_timing | UG835 Tcl Command Reference (2026.1) | VERIFICADO |
| amd_ug835_set_false_path | UG835 set_false_path | VERIFICADO-META (URL listada, no abierta) |
| amd_ug901_synthesis | UG901 Synthesis, capítulo Synthesis Attributes (2026.1) | VERIFICADO (no lista ALLOW_COMBINATORIAL_LOOPS) |
| amd_support_lutlp | AMD Adaptive Support, hilos sobre DRC LUTLP-1 / ALLOW_COMBINATORIAL_LOOPS | VERIFICADO-META (existencia; texto no abierto) |
| amd_ug903 / amd_ug949 | UG903 / UG949 | NO VERIFICADO (solo URL raíz) |
| tseng_ring_oscillators | tseng.engineering, "Motifs of Ring Oscillators" | VERIFICADO |
| opentrng_2025_docs | OpenTRNG (CEA-Leti), docs hardware + GitHub | VERIFICADO |
| espressif_trm_esp32 | ESP32 TRM v5.8, cap. 18 | VERIFICADO (PDF) |
| espressif_idf_random | ESP-IDF, Random Number Generation (ESP32) | VERIFICADO |
| castillo_2026_automated | Castillo et al., IoT (MDPI) 2026 | VERIFICADO-META (Crossref) |
| hidayatulloh_2024_performance | Hidayatulloh et al., ICRAMET 2024 | VERIFICADO-META (Crossref) |
| blancoromero_2026_entropy | Blanco-Romero et al., arXiv 2607.08865 | VERIFICADO (página abs) |
| esp32forum_rng | Hilos esp32.com sobre RNG/Dieharder | NO VERIFICADO |

---

## 8. Correcciones posteriores (12-09-2026)

Al investigar la vía a circuito integrado apareció un trabajo que obliga a
matizar dos afirmaciones de este documento. Se dejan escritas las dos
versiones, la original y la corregida, porque la diferencia importa.

**8.1 Sí hay jitter de anillo medido en Artix-7 publicado.** La sección 3.5
decía que no se había encontrado ninguna medida de sigma por periodo
específica de Artix-7. Es incorrecto tal cual está. Benea, Carmona,
Fischer, Pebay-Peyroula y Wacquez, *Impact of the Flicker Noise on the
Ring Oscillator-based TRNGs*, TCHES 2024, miden el jitter de anillos **en
Artix-7 100T (el mismo die de la Basys 3)** y, en el mismo artículo, en un
ASIC de 28 nm FD-SOI, con datos y scripts abiertos bajo licencia MIT en
`github.com/opentrng/papers`. Lo que sigue siendo cierto, y es lo que debe
decir la memoria, es que **los coeficientes de Artix-7 están publicados en
unidades de contador, no en segundos**, mientras que los del ASIC sí están
en segundos; los propios autores advierten de que la precisión en FPGA es
menor. Una medida en unidades absolutas para el XC7A35T sigue sin
aparecer, pero la formulación honesta ya no es "no hay datos de Artix-7"
sino "no hay datos absolutos para este dispositivo concreto".

**8.2 El método de referencia es la varianza de Allan.** Benea et al.
ajustan `sigma^2(t) = a0 + a1*t + a2*t^2`, donde a0 es cuantización, a1 es
ruido térmico y a2 es flicker. Es una separación más completa que el
ajuste lineal de la sección 3, porque aísla además el suelo de
cuantización del instrumento. El análisis de este TFM adopta ese método
(ver `analysis/spice_ring.py`, que usa diferencias de segundo orden por
esta razón). Conviene señalar que el autor ya usó desviación de Allan en
su trabajo previo sobre el sensor de CO2, así que la herramienta no es
nueva para él.

**8.3 Dato de jitter comparable entre plataformas.** Mismo observable
(varianza de fase acumulada por unidad de tiempo): Spartan-6 45 nm,
0,0029 ps; Cyclone V 28 nm, 0,020 ps; ASIC 28 nm FD-SOI, 0,0256 ps. Los
tres proceden de métodos de medida distintos, así que se presentan como
mismo orden de magnitud, nunca como comparación calibrada.

**8.4 Hallazgo contraintuitivo sobre el flicker.** Benea et al. concluyen
que incluir el ruido de flicker como fuente legítima puede **multiplicar
por cuatro el caudal** para la misma tasa de entropía, y que la
autocorrelación de la salida **disminuye** cuando crece la amplitud del
flicker. Contradice la práctica habitual de descartarlo entero, que es lo
que hace la sección 2 de este documento. Merece discutirse en la memoria
en lugar de darlo por zanjado.
