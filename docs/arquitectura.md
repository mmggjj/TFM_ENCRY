# Arquitectura del motor criptográfico — razonamiento de diseño

**Estado:** v0.1 (2026-09-11), previa a la lectura del estado del arte;
se revisará con `estado_del_arte_trng.md`, `estado_del_arte_cripto.md` y
`plataforma_y_flujo.md`. Los comentarios del RTL serán escuetos: el porqué
de cada decisión vive aquí.

---

## 1. Vista de bloques

> **Nota (15-09-2026):** el diagrama de abajo es el del borrador inicial y
> está desfasado en dos cosas: ya **no hay SHA-256** (§9, el acondicionado
> lo hace el AES) y la interfaz de producto es **I2C**, no SPI
> (`mapa_registros.md`). El bloque real está en `rtl/top/motor_top.vhd`,
> cuyo comentario de cabecera es la vista de bloques vigente.

```
                     ┌──────────────────────── FPGA (Artix-7) ───────────────────────┐
                     │                                                               │
  ┌──────────┐       │  ┌─────────┐  ┌────────┐  ┌─────────┐  ┌─────────┐  ┌───────┐  │
  │ N anillos│──────►│  │ Muestreo│─►│ Health │─►│ SHA-256 │─►│  DRBG   │─►│ Claves│  │
  │  (LUT1)  │       │  │ + XOR   │  │ RCT/APT│  │ acond.  │  │ 800-90A │  │  K    │  │
  └────┬─────┘       │  └────┬────┘  └────────┘  └─────────┘  └─────────┘  └───┬───┘  │
       │             │       │ bits crudos (FIFO)                               │      │
  ┌────▼─────┐       │       │                                    ┌────────────▼────┐ │
  │Contadores│       │       │                                    │ AES-128 + CMAC  │ │
  │ de frec. │       │       │                                    └────────┬────────┘ │
  └────┬─────┘       │       │                                             │          │
       │             │  ┌────▼─────────────────────────────────────────────▼───────┐  │
       └────────────►│  │        Registro de comandos + esclavo SPI (modo 0)       │  │
                     │  └────────────────────────────┬─────────────────────────────┘  │
                     │  ┌──────┐                     │                                │
                     │  │ XADC │ temp/VCCINT ────────┘                                │
                     │  └──────┘                                                      │
                     └───────────────────────────────┼─────────────────────────────────┘
                                                     │ SPI 3,3 V (Pmod JA ↔ VSPI)
                                            ┌────────▼─────────┐        UART 115200
                                            │  ESP32-D0WD-V3   │──────────────────► PC
                                            │ mbedtls + HW AES │   tramas CRC32       (Python:
                                            │  verificador     │                     800-22, 90B,
                                            └──────────────────┘                     modelo, figs)
```

Reloj de sistema: 100 MHz del oscilador de placa (referencia de los
contadores de frecuencia). Los anillos son dominios asíncronos propios.

## 1b. Hechos de la plataforma que condicionan el diseño

Todos verificados en `plataforma_y_flujo.md` salvo indicación:

- **XC7A35T-1CPG236C**: 5.200 slices (20.800 LUT6, 41.600 FF), 50 BRAM36,
  90 DSP48E1, 5 CMT, 1 XADC; 106 E/S. Todo el motor (≈ 1.500–3.000
  slices [ESTIMADO]) cabe con margen.
- **Oscilador**: DSC1033CC1-100.0000T, MEMS + PLL fraccional, 95 ps jitter
  ciclo a ciclo máx., ±50 ppm, pin W5 (MRCC). No sirve como referencia de
  jitter (ver §2), sí como reloj de sistema.
- **Pmod JA/JB/JC**: LVCMOS33 con **200 Ω en serie** por señal (esquemático
  C.0); JXADC sin resistencias pero con trazas acopladas y filtro → no
  para SPI. **JA no tiene pines de reloj (MRCC/SRCC)**; los hay en JB y JC.
  Irrelevante para el SPI sobremuestreado (SCLK es un dato, no un reloj),
  pero si algún día se quisiera sacar un anillo a un pin para el
  osciloscopio, se usaría JB/JC.
- **Alimentación**: LTC3633 (1,0 V para VCCINT **y** VCCBRAM en el mismo
  riel; 1,8 V VCCAUX) y LTC3621 (3,3 V). **No hay shunt ni puente serie**;
  W1/W2/W3 son puntos de prueba de tensión. Consecuencia para O8: el
  consumo se mide en la entrada USB de 5 V con un medidor en línea y solo
  se atribuyen **diferencias** entre bitstreams (motor activo vs. FPGA
  con bitstream vacío); `report_power` de Vivado es [ESTIMADO] siempre.
- **XADC**: 12 bits, 1 MS/s; error de temperatura **±4 °C máx.** (DS181
  Tabla 65), alimentación ±1 %. T = ADC·503,975/4096 − 273,15;
  V = ADC/4096·3 V (UG480). Resolución nominal ≈ 0,123 °C por LSB pero
  exactitud ±4 °C: sirve para tendencias relativas dentro de una sesión,
  no para temperatura absoluta — se declara así antes de usarla (regla
  del proyecto).
- **FT2232HQ**: UART (B18/A18) y JTAG independientes por el mismo USB →
  se puede programar y tener consola a la vez. La UART de la Basys 3 es
  una vía alternativa de volcado si el SPI diera problemas.
- **Herramientas**: Vivado ML Standard 2026.1 (gratuito, cubre Artix-7;
  instalador web 286 MB, SFD completo 98 GB; instalación "solo Artix-7"
  ≈ 30–45 GB [ESTIMADO, no verificado oficialmente]); VHDL-2008 con
  `read_vhdl -vhdl2008`. Simulación sin Vivado: GHDL 6.0 (mcode) +
  GTKWave vía MSYS2 UCRT64, o NVC 1.22 vía winget; UNISIM no se
  distribuye fuera de Vivado → modelo propio de LUT1/LUT2 en una librería
  `unisim` local para simulación funcional.

## 2. Capa 0 — fuente de entropía

**Elección REVISADA tras el estado del arte: núcleo ERO (Elementary Ring
Oscillator) como fuente principal; el multi-anillo XOR (MURO) pasa a ser
el experimento de O7, no la fuente.** Motivo (`estado_del_arte_trng.md`
§1–2): el modelo estocástico con cota demostrable (Baudet 2011,
Killmann–Schindler 2008, Ma 2014) y el medidor de jitter embebido
(Fischer–Lubicz 2014) están formulados para el ERO —un anillo muestreado
por una referencia tras acumular jitter durante K_D periodos— y AIS 20/31
v3.0 lo usa como ejemplo canónico. El MURO, que era mi elección inicial,
tiene el problema documentado por Bochard et al. 2010 de que parte de su
aparente aleatoriedad es *pseudo*-aleatoriedad por interacción entre
anillos, y su hipótesis de independencia no se puede demostrar en FPGA:
justo lo que O7 quiere medir, pero no algo sobre lo que apoyar la cota de
min-entropía. Precio del ERO: caudal bajo (K_D ~ 10⁴–10⁵ → decenas de
kbit/s por anillo). Es aceptable porque la salida útil del motor son
semillas de 256 bits para el DRBG, no un chorro de bits; y se pueden
correr varios ERO en paralelo (cada uno con su propia cota) si hace falta
caudal. COSO/TERO/STR/ES-TRNG quedan documentados como alternativas; el
COSO (con la calibración automática de Peetermans 2019/2021, ya
demostrada en Spartan-7) sería la segunda fuente si sobra tiempo.

Decisiones concretas:

- **Anillos de 3 a 7 inversores impares** instanciados como primitivas
  `LUT1` (INIT=01) con `DONT_TOUCH`. No se escribe `q <= not q` en
  comportamental: Vivado lo optimiza o lo fusiona. Cada anillo es una
  entidad con `KEEP_HIERARCHY` para poder asignarle un pblock.
- **Parámetros genéricos** (`N_RINGS`, `N_STAGES`, `FS_DIV`): el estudio
  barre nº de anillos (1, 2, 4, 8, 16, 32) y divisor de muestreo. Con
  ~20k LUT hay recursos de sobra; el límite lo pone la interferencia,
  no el área.
- **Muestreo: anillo contra anillo, NO contra el oscilador de placa.**
  Hallazgo decisivo de `plataforma_y_flujo.md`: el oscilador de 100 MHz de
  la Basys 3 es un **DSC1033CC1-100.0000T (MEMS con PLL fraccional)** cuyo
  datasheet tabula un jitter ciclo a ciclo de **95 ps máx.** @100 MHz
  [VERIFICADO], frente a los 2–4 ps por periodo del jitter de un anillo en
  28 nm [ESTIMADO, Petura 2016]. Si el anillo se muestreara con ese reloj,
  la "entropía" medida sería mayoritariamente el ruido de fase del PLL del
  oscilador (componente global, potencialmente inducible), no el ruido
  térmico del anillo. Por tanto el ERO se construye como en la literatura:
  RO1 muestreado por un flop cuyo reloj es **RO2 dividido por K_D**; el
  oscilador de placa solo gobierna la lógica síncrona (SPI, AES, SHA,
  DRBG, FIFO) y la medida de frecuencia media (donde su jitter, acotado
  por el PLL, se promedia). El bit muestreado cruza al dominio de 100 MHz
  por **dos etapas de sincronización** (`ASYNC_REG`) antes de entrar en
  la FIFO: queremos aleatoriedad en el bit, no en la máquina de estados.
  Parámetros genéricos: `K_D` (divisor, 2^10–2^18), y por anillo
  `N_STAGES`. Un `SET_CFG` permite K_D = 1 para el modo de medida de
  jitter (Fischer–Lubicz) y K_D grande para el modo generador.
- **Salida en dos vías**: (1) bits crudos tras el XOR, sin ningún
  post-procesado, a FIFO → SPI (es lo que necesita el modelo y 800-90B);
  (2) la vía acondicionada de la capa 1. Se puede leer cada anillo por
  separado (multiplexor previo al XOR) para medir correlaciones en O7.
- **Medida embebida del jitter (O2) — dos métodos, el primero es el
  principal**:
  1. **Fischer–Lubicz (CHES 2014), pares de bits a distancia M**: con el
     anillo muestreado a K_D = 1 por la referencia, en K ≈ 10⁴ bloques de
     N ≈ 100 bits se calcula la fracción de pares (b_j, b_{j+M}) distintos;
     su varianza sobre los bloques es 4·V(M)/T₁², con V la varianza del
     jitter acumulado en M periodos. Barriendo M (200–1600) y ajustando la
     zona lineal se obtiene σ_th por periodo con error < 5 % (validado por
     los autores en Cyclone III: 5,01 ps / 7,81 ns). Coste: registro de
     desplazamiento de ~M etapas + contadores; ~10⁶ bits por medida. Es
     además el **test online** natural (detecta enfriamiento y locking).
     En este TFM el cálculo de varianzas se hace en el PC sobre los bits
     crudos volcados por SPI; la versión en RTL (como test online) es un
     objetivo secundario.
  2. **Contador de periodos en ventana fija** (Killmann–Schindler,
     Lubicz–Bochard 2015) como contraste: la salida del anillo incrementa
     un contador que se captura en el dominio de 100 MHz cada T_w; la
     varianza de la cuenta mide el jitter acumulado. Sesgos: cuantización
     ±1 cuenta y, a ventanas largas, inflado por flicker/global (pendiente
     2 en log-log). Captura segura: contador en código Gray + registro
     doble en el dominio de la referencia. Un anillo de 3–5 LUT1 en 28 nm
     oscila a varios cientos de MHz [ESTIMADO: OpenTRNG/Peetermans; se
     mide en el primer bitstream] → 32 bits de contador no desbordan en
     ventanas de segundos.
  Ambos miden jitter **relativo** anillo–referencia; el diferencial con
  tres anillos (punto siguiente) separa lo local de lo global.
- **Referencia de medida**: todo método embebido mide jitter *relativo*
  entre dos osciladores. El oscilador de placa queda descartado como
  referencia de jitter por lo dicho arriba (DSC1033, 95 ps ciclo a ciclo
  máx. [VERIFICADO datasheet Micrel]; su jitter RMS de periodo solo está
  en gráfica, no tabulado; ±50 ppm). La componente *global* (alimentación,
  temperatura, sustrato) se separa con anillos idénticos en pblocks
  alejados. **Se instrumentan al menos TRES anillos de medida, no dos**: con dos, la medida diferencial cancela el
  jitter global pero solo entrega la *suma* de los jitters locales; con
  tres se recuperan los individuales (Lubicz–Skórski 2024, ver
  `estado_del_arte_trng.md`). La varianza acumulada se ajusta a
  σ²(t) = a·t + b·t² y la pendiente en escala log-log separa la componente
  térmica (∝ t, la única que aporta entropía impredecible) de la de
  flicker (∝ t²); solo la térmica entra en el modelo. No hay cifra
  publicada de jitter por periodo para Artix-7 (sí 2–4 ps por periodo de
  4–8 ns en Spartan-6 y Cyclone V, 28 nm, Petura 2016): medirlo aquí es un
  hueco real.
- **Números fijados por la validación del modelo** (`docs/modelo_ero_resultados.md`,
  simulación con Q conocida, 0 fallos en 44 comprobaciones):
  - **Objetivo Q ≥ 0,2286** (min-entropía ≥ 0,98 exacta, criterio más
    exigente que el de Shannon); consigna con margen **Q = 0,30**.
  - La ec. 14 de Baudet **no es cota inferior**, es un desarrollo truncado
    que sobreestima; se usa el cálculo exacto con la gaussiana envuelta.
  - **K_D entre 3·10⁴ y 5·10⁵** y **caudal de 1 a 20 kbit/s por anillo**
    para los valores de jitter esperables en 28 nm [ESTIMADO]. Un ERO da
    kbit/s, no Mbit/s: basta para sembrar el DRBG (0,03 a 0,5 s por
    semilla de 256 bits de entropía plena) y es el precio de tener
    entropía demostrable. Más caudal = más ERO independientes.
  - **FIFO de solo N + M_máx bits (2 a 8 kbit)**: el estimador admite
    bloques independientes, así que se captura un trozo a la velocidad del
    anillo, se vuelca por SPI y se repite. No hacen falta megabits
    contiguos en BRAM. Campaña de jitter ≈ 5,1 MB por punto de medida.
  - El modo de medida necesita **K_D pequeño** (el producto M·K_D·Q_raw
    debe dejar la fase lejos del vértice de la triangular), el modo
    generador K_D grande: `SET_CFG` conmuta entre ambos.
- **Objetivo de diseño de la capa 0 en números** (modelo de Baudet 2011):
  factor de calidad Q = σ²·Δt (varianza de jitter acumulada en un periodo
  de muestreo, normalizada al periodo del anillo) y cota
  H ≥ 1 − (4/(π² ln 2))·e^(−4π²Q). Para el umbral vigente de AIS 20/31
  **v3.0** (PTG.2: Shannon ≥ 0,9998 por bit, o min-entropía ≥ 0,98) hace
  falta Q ≥ 0,20; para el antiguo 0,997 de la v2.0 bastaba Q ≥ 0,134. La
  frecuencia de muestreo f_s se elige a partir del jitter MEDIDO para
  alcanzar Q ≥ 0,20 con margen, y luego se contrasta con los estimadores
  de 800-90B. Salvedad de Saarinen 2021: esa cota nunca baja de 0,415 y
  solo es válida bajo las hipótesis del modelo (ruido gaussiano
  independiente), así que el contraste empírico no es opcional.
- **Referencia de implementación abierta**: OpenTRNG (CEA-Leti, licencia
  MIT) implementa ERO/MURO/COSO en la Arty A7 **con el mismo die
  XC7A35T** de la Basys 3, con anillos de LUT1/LUT2 y área prohibida en el
  XDC; no publica cifras de entropía. Se estudia su forma de fijar los
  anillos; el RTL de este TFM es propio.

## 3. Capa 1 — acondicionamiento y DRBG

- **Health tests SP 800-90B** sobre los bits crudos, en RTL (parámetros
  de la norma, leídos del PDF — ver `estado_del_arte_trng.md`):
  Repetition Count Test con corte C = 1 + ⌈−log₂α / H⌉ y Adaptive
  Proportion Test con **ventana W = 1024 para fuentes binarias** (512 solo
  para no binarias) y corte C = 1 + CRITBINOM(W, 2^(−H), 1−α), α = 2^(−20).
  Para H = 0,98 bit/bit: RCT C = 22, APT C = 596. H se fija con la
  min-entropía estimada en O3 y los cortes se calculan en el PC y se
  cargan como constantes (o por `SET_CFG`). El fallo levanta una bandera
  leíble por SPI y bloquea la salida acondicionada. AIS 20/31 v3.0 acepta
  el RCT como "total failure test" y exige que el test online se derive
  del modelo estocástico (distribuciones A_good/A_bad): el test online
  del TFM será un monobit/póker sobre ventanas cuyo umbral se justifica
  con el modelo de O3, no con un número arbitrario.
- **SHA-256 como acondicionador** (componente "vetted" de 800-90B sec.
  3.1.5): se acumulan n_in bits crudos con min-entropía estimada h_in y se
  emiten 256 bits; la norma da la fórmula de la min-entropía de salida.
  Este mismo núcleo sirve para el DRBG, así que el coste marginal es cero.
- **DRBG: CTR_DRBG con AES-128 sin función de derivación** (decidido tras
  `estado_del_arte_cripto.md` §3.2). Motivo: reutiliza el AES ya
  presente; estado interno de solo Key 128 + V 128 + contador de reseed;
  128 bits de salida por ~11 ciclos; vectores oficiales CAVP en
  `CTR_DRBG.rsp`, sección `[AES-128 no df]`. Precio normativo (SP 800-90A
  §10.2.1.3.1): la entrada de entropía debe ser de **entropía plena y
  exactamente seedlen = 256 bits** — justo lo que produce el acondicionador
  SHA-256 si se le alimenta con h_in ≥ 2·n_out = 512 bits de min-entropía
  estimada (regla de diseño derivada de la fórmula de 90B §3.1.5.1.2: con
  h_in = 256 se pierde ≈ 1 bit; con h_in ≥ 512 la salida es plena a
  efectos prácticos). Con H_min = 0,5 bit/bit del TRNG eso son ≥ 1024 bits
  crudos por semilla. Parámetros Tabla 3 de 90A: reseed_interval 2^48
  (usaremos ≤ 2^20 o temporizador), máx. 2^19 bits por petición, Update
  obligatorio tras cada generate, Key/V nunca expuestos (Woodage–Shumow
  2019). Hash_DRBG queda documentado como alternativa (seedlen 440, sumas
  modulares de 440 bits: más caro).
- **Generación de clave**: `GEN_KEY` = 128 bits del DRBG a un registro de
  clave interno; `EXPORT_KEY` lo saca por SPI (solo en banco, para la
  provisión del ESP32); un bit de configuración puede deshabilitar la
  exportación para el modo demostración.

## 4. Capa 2 — motor AES-128 y CMAC

- **AES-128 iterativo**: una ronda por ciclo, 10 rondas + carga → ~11
  ciclos por bloque, S-box en LUT (256×8 combinacional, 16 instancias +
  4 para la expansión de clave) o en BRAM (una BRAM de 36 Kb da 4 S-box
  de doble puerto).
  > **Corregido (16-09-2026), esto estaba desfasado frente al RTL.** El
  > borrador decía "cifrado y descifrado con datapath compartido" y que
  > "la expansión de clave se precalcula y guarda (11×128 bits)". El
  > `aes_enc.vhd` implementado hace las dos cosas al revés, y bien: es
  > **solo de cifrado** (§9) y la **expansión va al vuelo**, derivando la
  > clave de cada ronda de la anterior. Lo confirman los 262 biestables
  > que da la síntesis: 128 de estado + 128 de clave de ronda + control;
  > guardar once claves serían 1408. Al vuelo es lo correcto para un
  > núcleo de solo cifrado, porque las rondas se recorren en orden
  > ascendente y nunca hace falta la clave de la última primero.
  Throughput orientativo a 100 MHz:
  128 bits / 11 ciclos ≈ 1,16 Gbit/s de núcleo — el cuello será el SPI,
  no el AES, lo que se declara.
- **AES-CMAC (SP 800-38B / RFC 4493), decidido** frente a HMAC-SHA-256
  (`estado_del_arte_cripto.md` §4.4): subclaves K1/K2 por desplazamiento y
  XOR con Rb=0x87, precomputadas al cargar la clave; un MAC de un reto de
  16 B cuesta 1 AES (~11 ciclos) frente a ≥ 2 compresiones SHA (~132
  ciclos) más gestión de ipad/opad; coste marginal ≈ 300–400 LUT/FF
  [ESTIMADO]; deja el SHA-256 dedicado al acondicionador sin arbitraje.
  Tlen = 128. Vectores: RFC 4493 §4 (cuatro ejemplos, copiados en el
  estado del arte) + `CMACGenAES128.rsp`/`CMACVerAES128.rsp` de CAVP. En
  el ESP32 hay que activar `CONFIG_MBEDTLS_CMAC_C` (por defecto
  desactivado). Límite de uso por clave: 2^48 bloques (Apéndice B).
- **Throughput de núcleo vs interfaz** (corrección al borrador inicial):
  AES iterativo a 100 MHz = 128 bits / 11 ciclos ≈ **1,16 Gbit/s**, no
  ~100 Mbit/s. Con SPI a 10–20 MHz el AES está ocupado un 1–3 %: ningún
  pipelining tiene sentido; la iterativa se elige por **verificabilidad**
  (una ronda = una función combinacional cotejable con FIPS 197 Ap. B/C)
  y porque la comparten ECB/CBC, CMAC y CTR_DRBG.
- **Verificación**: cada núcleo tiene testbench con vectores oficiales
  (FIPS 197 apéndice C, RFC 4493, CAVP) antes de integrarse. Después,
  interoperabilidad cruzada con mbedtls en el ESP32.

## 5. Interfaz SPI y protocolo

> **Nota (15-09-2026):** sección desfasada. La interfaz de producto pasó a
> ser **I2C** por decisión del autor; la especificación vigente es
> `docs/mapa_registros.md` y la implementación `rtl/io/i2c_slave.vhd`. Lo
> que sigue se conserva como registro del razonamiento sobre el SPI y el
> doble enlace (§5.0), que sigue siendo válido para la vía de volcado
> masivo por la UART propia de la Basys 3.

### 5.0 Dos enlaces, no uno (decisión revisada 12-09-2026)

El borrador hacía pasar TODO por el ESP32: FPGA → SPI → ESP32 → UART →
PC. Eso pone el cuello de botella en el sitio equivocado. Las campañas de
entropía mueven megabytes (5,1 MB por punto de jitter, y SP 800-90B exige
≥ 10⁶ muestras crudas más una matriz de 1000×1000 reinicios), y la UART
del ESP32 solo resultó fiable a 115200 bit/s en los TFM anteriores con el
CP2102, o sea 11,5 kB/s: siete minutos por punto solo de transferencia.

La Basys 3 tiene su **propio puente USB-UART (FT2232HQ)**, y su manual
dice que la UART y el JTAG funcionan de forma independiente por el mismo
cable, así que se puede programar y volcar a la vez. Se reparte el
trabajo según lo que cada enlace hace bien:

| Enlace | Para qué | Volumen | Velocidad |
|---|---|---|---|
| SPI, ESP32 maestro ↔ FPGA esclavo | comandos, verificación criptográfica, reto-respuesta, petición de claves | bytes por transacción | 10 MHz [objetivo] |
| UART FPGA → PC, por el USB de la propia Basys 3 | volcado masivo de bits crudos, cuentas de los contadores, campañas | megabytes | a determinar, el FT2232H admite mucho más que 115200 [ESTIMADO: probar 1–3 Mbaud] |

Ventajas de separarlos: el ESP32 deja de ser un simple reenviador y se
dedica a lo único para lo que es insustituible, hacer de verificador
criptográfico independiente; las campañas de entropía no dependen de que
el ESP32 esté conectado; y si un enlace falla, el otro sigue.

La UART del ESP32 al PC se mantiene, pero solo para control y resultados
de verificación, que son kilobytes.

### 5.0b Reducir el volumen: contadores embebidos

Para barridos rápidos y para el test online no hace falta sacar los bits.
El estimador solo necesita, por cada distancia M, la media y la varianza
de la fracción de pares distintos entre bloques. Eso son unos pocos
contadores en la FPGA (uno por M), y reduce el volumen unas 8 veces si se
envía una cuenta por bloque, o lo hace despreciable si se acumulan suma y
suma de cuadrados en el propio chip. Es justo lo que proponen Fischer y
Lubicz para su test embebido, que necesita 8600 veces menos datos que
sacar bits en crudo.

Los bits crudos se vuelcan igualmente para las medidas definitivas y para
SP 800-90B, que los exige, y para poder publicar los datos.

- **Esclavo SPI modo 0**, sobremuestreado con el reloj de 100 MHz (SCLK,
  MOSI y CS por sincronizadores de 2 FF + detección de flanco; un solo
  dominio de reloj): SCLK máx. de diseño ≈ f_sys/4–f_sys/5 → 20–25 MHz;
  con cables Dupont se trabaja a **10 MHz** (5 MHz si hay errores de
  CRC). El ESP32 es maestro por **VSPI/SPI3 en pines IO_MUX**: GPIO18 SCLK,
  GPIO23 MOSI, GPIO19 MISO, GPIO5 CS0 [VERIFICADO en docs.espressif,
  `estado_del_arte_cripto.md` §6.2]. El retardo MISO del esclavo
  sobremuestreado (2–3 ciclos de sistema + E/S ≈ 30 ns) se declara en
  `input_delay_ns`; la fórmula de Espressif 80/(⌊delay/12,5⌉+1) da ≈ 26,7
  MHz de techo full-duplex, coherente con los 10–20 MHz elegidos. En la
  Basys 3 el SPI va por **Pmod JA** (LVCMOS33, pines J1, L2, J2, G2, H1,
  K2, H2, G3 según el XDC oficial de Digilent), nunca por JXADC (trazas
  acopladas y filtros anti-alias). Masa común corta entre placas;
  alimentaciones USB independientes.
- **Trama**: byte de comando + longitud + payload + CRC-8 opcional (el
  CRC32 se aplica en la trama UART ESP32→PC, reutilizando el formato del
  TFM_RNG). Comandos previstos:

| Cmd | Nombre | Función |
|---|---|---|
| 0x01 | `GET_RAW` | n bytes de bits crudos post-XOR (FIFO) |
| 0x02 | `GET_RING` | bits crudos de UN anillo seleccionado (O7) |
| 0x03 | `GET_COUNTS` | cuentas de los contadores de frecuencia de la última ventana (O2) |
| 0x04 | `GET_COND` | n bytes acondicionados (salida SHA/DRBG) |
| 0x05 | `GET_STATUS` | banderas health tests, FIFO, versión, parámetros N/etapas/FS_DIV |
| 0x06 | `GEN_KEY` | genera K desde el DRBG |
| 0x07 | `EXPORT_KEY` | lee K (provisión en banco) |
| 0x10 | `AES_ENC` / 0x11 `AES_DEC` | 16 bytes ↔ 16 bytes con K |
| 0x12 | `CMAC` | CMAC de m bytes con K |
| 0x13 | `CHALLENGE` | nonce de 16 bytes → CMAC(nonce) |
| 0x20 | `SET_CFG` | selección de anillos activos, FS_DIV, ventana T_w, modo test |
| 0x21 | `GET_XADC` | temperatura del die y VCCINT |
| 0x30 | `SHA256` | digest de m bytes (para KAT cruzado) |

## 6. Firmware ESP32 (verificador)

Tres modos, elegidos por comando UART desde el PC:

1. **Campaña**: lee `GET_RAW`/`GET_RING`/`GET_COUNTS`/`GET_XADC` en bucle y
   reenvía al PC en tramas CRC32 (formato del TFM_RNG). Sin interpretar.
2. **Verificación**: ejecuta KAT (envía vectores oficiales a la FPGA y
   compara), interoperabilidad (cifra con mbedtls → descifra en FPGA y al
   revés, N bloques aleatorios), reto-respuesta (nonce de `esp_random()` →
   `CHALLENGE` → recalcula CMAC con mbedtls). Cuenta aciertos/fallos, los
   reporta al PC. Los fallos se registran íntegros, no se descartan.
3. **Referencia**: mide el throughput de mbedtls con y sin aceleración
   hardware (AES-128-ECB y SHA-256 sobre buffers grandes) para la
   comparación de O8, y vuelca `esp_random()` con el mismo formato para
   que ambos generadores pasen por la misma cadena de análisis.

UART a 115200 (la única velocidad fiable con el CP2102 en los TFM
anteriores). `CONFIG_LOG_DEFAULT_LEVEL` a ERROR para no contaminar el
stream.

## 7. Análisis en PC (Python)

- `nist_sp800_22.py` del TFM_RNG, sin cambios (ruta:
  `TFM_RNG/tfm_esp32_rng/python/`; punto de entrada
  `run_all_nist_tests(data: bytes, label) -> list[TestResult]`, 15 tests,
  con `self_test()` de autovalidación). Se importa como módulo, no se
  copia: así cualquier corrección se propaga a ambos TFM.
- Herramienta oficial NIST `SP800-90B_EntropyAssessment` (C++) para los
  estimadores no-IID; se compila en WSL. Nuestro código solo prepara los
  ficheros de entrada y agrega resultados.
- `jitter_model.py`: distribución de cuentas, σ² vs. T_w, ajuste a·t+b·t²,
  factor de calidad, cota de min-entropía, gráficas.
- `compare.py`: tablas finales ESP32 vs FPGA con incertidumbres.

Todo con captura incremental y flush por fila (lección de los TFM
anteriores), sin filtrar la salida de los instrumentos.

## 8. Preguntas abiertas para el estado del arte

1. ¿Contador ripple + captura Gray, o parar el anillo para leer? ¿Qué hace
   la literatura para medir frecuencia de anillos en la propia FPGA?
2. ¿Hash_DRBG o CTR_DRBG? ¿CMAC o HMAC?
3. ¿Especificación de jitter del XO de la Basys 3?
4. ¿Cuántos anillos y qué separación de pblocks usaron los estudios de
   injection locking publicados?
5. ¿Existe alguna publicación que use un microcontrolador comercial como
   verificador independiente de un núcleo cripto FPGA? (Si no, es un punto
   a formular con cuidado, "no hemos encontrado".)

---

## 9. Decisión de arquitectura: fuera el SHA-256 (12-09-2026)

**Se elimina el núcleo SHA-256. El motor usa AES para todo.**

Motivo. El informe de la vía a circuito integrado cifra el motor completo
en unas 25.000 puertas equivalentes, de las que el **SHA-256 se lleva el
47 %**. Y resulta que no hace falta: SP 800-90B §3.1.5.1.1 admite como
componentes de acondicionamiento autorizados, además de las funciones
hash, los construidos sobre AES, en concreto CMAC, CBC-MAC y el
**Block_Cipher_df** de SP 800-90A. Con eso el acondicionado se hace con el
AES que ya está.

Cambio respecto a la decisión anterior. Antes se eligió CTR_DRBG **sin**
función de derivación, precisamente porque el SHA-256 iba a garantizar
una entrada de entropía plena de 256 bits. Sin SHA-256 esa garantía
desaparece, así que se pasa a **CTR_DRBG con función de derivación**, que
es además la configuración habitual en la práctica y acepta entrada de
entropía no plena. La función de derivación cuesta lógica de control
sobre el mismo AES, no una primitiva nueva.

| | Antes | Ahora |
|---|---|---|
| Acondicionado | SHA-256 | Block_Cipher_df sobre AES |
| Generador | CTR_DRBG sin df | CTR_DRBG con df |
| Autenticación | AES-CMAC | AES-CMAC |
| Primitivas | AES + SHA-256 | **solo AES** |
| Área estimada | ~25 kGE | **~13 kGE** [ESTIMADO, superado] |

**El AES será solo de cifrado, no de descifrado.** El descifrado ocuparía
en torno a un 40 % más y no hace falta para nada: el generador
determinista en modo contador solo cifra, el CMAC solo cifra, y ofrecer
descifrado como servicio al ESP32 no tiene sentido porque el ESP32 lleva
su propio acelerador de AES. Lo que sí se conserva es la verificación
cruzada: la FPGA cifra y el ESP32 descifra con mbedtls, que es una
implementación independiente.

Lo que se pierde: el chip no puede ofrecer servicios de hash. No es su
trabajo. Si algún día hiciera falta, el hueco de área existe.

> **Nota (16-09-2026): la estimación de ~13 kGE no se cumplió.** La
> síntesis real sobre SG13G2 da **~62 kGE** para el motor digital, y el
> motivo es que "una sola primitiva" lo es a nivel de **algoritmo**, no de
> **hardware**: `aes_cmac` y `ctr_drbg` instancian cada uno su propio
> `aes_enc`, así que hay **dos** núcleos de 15,8 kGE, el 51 % del motor.
> El análisis correcto, con las tres optimizaciones y sus ahorros
> estimados (compartir el AES, S-box compacta, menos registros en el
> generador) está en el **capítulo 6 de la memoria**, que es la referencia
> vigente para todo lo de área. Esta tabla se conserva como registro de la
> estimación inicial, no como dato.
