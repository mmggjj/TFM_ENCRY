# Resumen de lo hecho — reunión con los tutores

Mario García Jiménez · Máster en Microelectrónica (US / IMSE-CNM) · octubre de 2026
Tutores: Antonio J. Acosta y Alejandro Casado
Título propuesto: *Diseño y caracterización de aleatoriedad de un TRNG basado en osciladores en anillos*

Todo lo que sigue está en el repositorio público https://github.com/mmggjj/TFM_ENCRY
y se reproduce con herramientas libres (GHDL, ngspice, Yosys, ESP-IDF, Python).
Cada cifra lleva su etiqueta: **[medido]** en silicio real, **[simulado]** o **[estimado]**.

## 1. La idea en una frase

Diseñar la cadena completa *ruido físico → bits → claves → autenticación* como un
circuito integrado dedicado, con la entropía **justificada desde el transistor** y no
supuesta, y verificarla en FPGA con un ESP32 como comprobador independiente.

## 2. De dónde viene: el generador del ESP32 como caja negra

- TFM anterior (agosto de 2026): el RNG hardware del ESP32 pasa **15/15** tests de
  SP 800-22 en las cuatro condiciones (Wi-Fi + ADC, solo Wi-Fi, solo ADC, nada), incluida
  la que el fabricante desaconseja. Conclusión: SP 800-22 no mide entropía. NIST lo dijo
  en 2022.
- Hecho ahora para este TFM, con la herramienta oficial del NIST para SP 800-90B sobre
  **14 capturas reales** (3 repeticiones por condición + 2 largas sin radio) **[medido]**:

| | Vía IID | Vía no-IID (mínimo de 10 estimadores) |
|---|---|---|
| Resultado | 0,993-0,998 bit/bit, pegado al techo de resolución del MCV (0,9963 con 1 Mbit) | **0,81-0,92 bit/bit**, media 0,85 |
| Quién manda | — | Compression / Collision / LRS (sesgo conservador conocido en fuentes casi uniformes) |
| Efecto de la condición | ninguno | ninguno: ANOVA por estimador, p mínima 0,063 |

- Lo importante no es el número: **ninguno es una cota**. La fuente física y el
  post-procesado del ESP32 no están documentados. Esto es lo que el TRNG propio resuelve.

## 3. Fuente de entropía: del transistor a la min-entropía

**Estructura:** ERO, un anillo (RO1) muestreado por otro anillo (RO2) dividido por K_D.
El reloj de la placa no interviene (es un MEMS con PLL, 95 ps de jitter: inservible como
referencia).

**Modelo estocástico** (Baudet et al. 2011), escrito y autovalidado (24 comprobaciones):
- Se usa el cálculo exacto con gaussiana envuelta. Hallazgo: la ecuación 14 del artículo
  **no es cota inferior** (serie truncada con términos negativos); se dedujo el término de
  orden 2 y se validó numéricamente.
- Objetivo de diseño: **Q ≥ 0,2286** para H_min ≥ 0,98 (AIS 20/31 v3.0, PTG.2); consigna
  Q = 0,30 → H_min = 0,9951.

**Estimador de jitter** (Fischer–Lubicz, CHES 2014), con dos correcciones propias (efecto
vértice de la onda triangular y ruido de estimación no constante): error < 2 % sobre un
rango de 150× en Q (20 comprobaciones sobre datos sintéticos). Permite captura por trozos
independientes de 2-8 kbit, no megabits en memoria.

**Banco SPICE** (ngspice, anillo de 5 etapas, modelos genéricos de transistor) **[simulado]**:

| Ruido inyectado (A²/Hz) | Periodo (ps) | σ (fs) | Lectura |
|---|---|---|---|
| ninguno | 230,30 | 1,38 | suelo numérico del banco (870× por debajo de la señal) |
| 1·10⁻²⁰ | 230,37 | 1 200 | punto de referencia |
| 4·10⁻²⁰ | 229,98 | 2 416 | ×2,01 frente a ×2,00 de la ley √S: el banco mide lo que inyecta |
| 1,6·10⁻¹⁹ | 227,77 | 25 588 | fuera del régimen: el periodo medio se mueve; se reporta, no se usa |

**Punto de operación** (RO2 a 500 MHz) **[estimado]**: σ/T de 7·10⁻⁴ a 2,8·10⁻³ →
K_D entre 457 000 y 28 600 → 1 a 17 kbit/s por anillo. Suficiente: el producto es una
semilla de 256 bits, no un flujo.

**Con transistores reales: PDK abierto IHP SG13G2 (130 nm, 1,2 V)** [simulado]
(`docs/anillo_ihp.md`). El ruido inyectado ya no se elige: sale del modelo del propio
transistor (ruido de un inversor en su punto de conmutación): térmico
4,13·10⁻²⁴ A²/Hz y 1/f con esquina en 19,8 MHz. Herramientas compiladas para ello:
ngspice 47 y OpenVAF-Reloaded.

| Anillo de 5 etapas, 400 ns | Resultado |
|---|---|
| Periodo y potencia | 366 ps (2,73 GHz), 143 µW |
| Resolución del banco | 0,70 fs |
| Jitter con el ruido del PDK | 180 fs por periodo, σ/T = 4,9·10⁻⁴, exponente 1,05 |
| Ley de la raíz | ruido ×4 → jitter ×1,988 (teórico ×2,000) |
| Contraste con Abidi (JSSC 2006) | mismo orden: la simulación da 0,42 veces su fórmula |
| Divisor para H_min ≥ 0,98 | K_D ≈ 941 000 → 2,9 kbit/s por anillo |

- Contador del divisor ampliado de 20 a 24 bits: con 20, el K_D máximo dejaba solo un
  11 % de margen.
- **Ruido 1/f:** con la función de sensibilidad al impulso (Hajimiri y Lee) y el 1/f de
  cada transistor (el pMOS tiene 3 veces más que el nMOS), el 1/f iguala al térmico
  entre los 185 y los 27 000 periodos según cómo actúe el ruido en el periodo; en el
  punto de trabajo domina el jitter acumulado entre 35 y 5 000 veces. La medida que
  fija la entropía en la FPGA tiene que hacerse con acumulaciones cortas (< ~100
  periodos) y separando componentes. Cerrar la horquilla pide ruido transitorio
  cicloestacionario (Spectre).

## 4. Motor digital (RTL portable, VHDL-2008)

```
RO1, RO2 → ERO (÷K_D) → cruce de dominio → pruebas de salud RCT/APT → 384 bits
   → Block_Cipher_df (AES) → CTR_DRBG AES-128 con df → clave 128 b → AES-CMAC (reto-respuesta)
   esclavo I2C (dir. 0x30, mapa de registros, órdenes sondeables, pin modo_test)
```

- **Decisiones:** solo AES-128 de cifrado (sin SHA-256, que era el 47 % del área y la
  norma admite acondicionadores basados en AES; sin descifrado: el ESP32 ya tiene
  aceleradores). Pruebas de salud SP 800-90B: RCT C = 22, APT W = 1024 / C = 596 para
  H = 0,98 y α = 2⁻²⁰.
- **Seguridad por construcción:** la clave solo es legible con el pin de modo de test;
  el divisor por debajo del mínimo se rechaza en hardware; en revisión se encontró y
  corrigió una **fuga de clave** (el registro de aleatorio exponía los primeros 128 bits
  del DRBG, que eran la clave).

**Verificación, tres patas independientes** **[simulado]**:

| Qué | Resultado |
|---|---|
| 7 bancos VHDL (anillo, I2C, AES, CMAC, DRBG, salud, nivel superior) | todos pasan; nivel superior 18/18 |
| Vectores oficiales | FIPS 197, SP 800-38A, RFC 4493; **CTR_DRBG 960/960 vectores CAVP** |
| Modelo Python independiente (AES propio, sin nada del VHDL) | reproduce las etiquetas CMAC y las claves del banco, 5/5 |

## 5. Síntesis a celdas estándar (IHP SG13G2, 130 nm, Yosys) [simulado]

| Bloque | kGE | Bloque | kGE |
|---|---|---|---|
| AES-128 (cifrado) | 15,8 | pruebas de salud | 1,24 |
| AES-CMAC | 23,4 | esclavo I2C | 1,02 |
| CTR_DRBG | 36,8 | ERO (divisor de 24 bits) + cruce de dominio | 0,39 |
| captura de test (RAM como FF) | 46,8 | **nivel superior** | **114,9** |

Motor digital sin la vía de test ≈ 68 kGE (62,9 en bloques + 5,2 de control del nivel
superior). Camino identificado a ≈ 20-25 kGE: compartir un único AES entre DRBG y CMAC,
S-box compacta, menos registros. 1 GE = NAND2 = 7,26 µm².

## 6. ESP32 como comprobador [medido]

Firmware ESP-IDF 5.3 (maestro I2C + mbedtls): compilado, flasheado y probado en placa
(sin motor todavía): consola, tramas con CRC32 al PC, rechazo correcto de órdenes sin
clave. Recalcula el CMAC de cada reto y lleva tres cuentas separadas (aciertos, fallos
criptográficos, errores de bus).

## 7. Vía ASIC, investigada

- IMSE-CNM: área de seguridad hardware; el camino FPGA serie 7 → TSMC 65 nm con
  PUF/TRNG de anillos ya está recorrido en la casa (NorCAS 2024).
- Costes públicos de multiproyecto: UMC L180 3 430 €, TSMC 65 nm 3 691 €, IHP SG13G2
  5 110 €/mm² (y MPW gratuito de IHP para < 2 mm² en abierto). US e IMSE son socios
  Full-IC.
- Competencia: ATECC608B (0,90 $) tiene certificado ESV de su fuente (anillos,
  0,507 bit/muestra); dos competidores directos no mencionan SP 800-90 en su hoja de
  datos. El argumento del trabajo es la transparencia, no el precio.
- Ataques conocidos a tener en cuenta: inyección por alimentación (Markettos–Moore) y
  radiada (Bayon); contramedida de filtro RC medida en la literatura.
- Fabricar queda fuera de alcance por plazo, no por coste.

## 8. Memoria

En inglés, con la plantilla común: capítulos 1 a 7 en borrador (introducción, estado del
arte, fuente de entropía, motor digital, verificación, camino a ASIC, resultados y
comparación), más de 200 referencias con estado de verificación, compila sin errores.
Falta el capítulo 8 y los apéndices.

## 9. Lo que falta y dónde necesito orientación

1. **Puesta en marcha en la Basys 3** (Vivado) y campaña de entropía: confirmar que los
   anillos oscilan, medir el jitter, fijar K_D, pasar los estimadores de la norma a los
   bits crudos y contrastarlos con la cota del modelo.
2. **Anillo con un PDK real**: sustituir los modelos genéricos por los de una tecnología
   del instituto (Virtuoso/Spectre, ruido transitorio); si da tiempo, trazado y
   simulación post-trazado del bloque analógico.
3. **Alcance y título**: el título propuesto centra el trabajo en el TRNG y su
   caracterización; el motor digital puede quedar como contexto de aplicación y vehículo
   de verificación. Conviene fijar el peso de cada parte en la memoria.

## 10. Preguntas para la reunión

- ¿Tecnología y PDK con los que trabajar el anillo? ¿Acceso a herramientas?
- ¿Alcance: TRNG solo, o TRNG + motor como aplicación? ¿Qué debe medirse en la FPGA
  para que la caracterización sea completa a su juicio (colocación, acoplamiento entre
  anillos, temperatura, tensión)?
- ¿Memoria en inglés con la plantilla común: correcto?
- ¿Convocatoria objetivo y calendario de reuniones?
- ¿Alguna posibilidad de MPW más adelante, aunque sea fuera del TFM?
