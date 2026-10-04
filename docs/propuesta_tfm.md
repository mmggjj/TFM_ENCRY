# Propuesta de Trabajo Fin de Máster

**Máster en Microelectrónica (Universidad de Sevilla / IMSE-CNM)**
**Alumno:** Mario García Jiménez
**Fecha:** octubre de 2026

## Título provisional

Diseño de un motor criptográfico de generación de claves para su
implementación como circuito integrado: fuente de entropía caracterizada a
nivel de transistor y verificación en FPGA frente a un ESP32.

(*Design of a Key-Generation Cryptographic Engine for Integrated-Circuit
Implementation: a Transistor-Level Characterized Entropy Source with FPGA
Verification against an ESP32.*)

## Resumen

Se propone diseñar la cadena completa *ruido físico → bits → claves →
autenticación* como un circuito integrado dedicado que sirve claves a un
microcontrolador por I2C. La fuente de entropía es un oscilador de anillo
muestreado por otro oscilador de anillo, diseñado a nivel de transistor y
simulado con ruido; su jitter se convierte en una cota de min-entropía
mediante un modelo estocástico comprobado, y esa cota fija el divisor de
muestreo. La parte digital (pruebas de salud, acondicionado, generador
determinista, autenticación e interfaz) se escribe en VHDL independiente de
la tecnología, se verifica con vectores oficiales y se sintetiza sobre una
biblioteca de celdas estándar abierta. Una FPGA Basys 3 sirve como vehículo
de verificación funcional y un ESP32 actúa como comprobador independiente y
como generador de referencia. El trabajo no fabrica el circuito (el plazo no
lo permite) pero deja el diseño, su área y el camino de fabricación
documentados.

## Motivación

En el TFM anterior del alumno se caracterizó como caja negra el generador
hardware del ESP32, el microcontrolador que usa en su trabajo en productos
de IoT. El hallazgo central fue que la batería NIST SP 800-22 no distingue
entropía real: la salida pasó los 15 tests en las cuatro condiciones de
funcionamiento, incluida aquella en la que el fabricante advierte que el
generador no garantiza aleatoriedad. El propio NIST anunció en 2022 que
SP 800-22 no debe usarse para evaluar generadores criptográficos.

Como preparación de esta propuesta se ha aplicado a ese mismo generador la
norma que sí mide entropía, SP 800-90B, con la herramienta oficial del NIST
sobre catorce capturas reales (tres repeticiones por condición). El
resultado confirma el problema desde el otro lado: por la vía IID la salida
es indistinguible de una fuente perfecta al límite de resolución de los
estimadores, y por la vía no-IID vale entre 0,81 y 0,92 bit por bit, sin
que ninguna condición se distinga de las demás. Pero ningún número de esos
es una cota: la fuente física y el post-procesado del ESP32 no están
documentados, y lo que una aplicación de seguridad necesita es saber de
dónde sale cada bit y cuánta entropía puede acreditarle. Ese es el hueco
que cubre el trabajo: construir la caja blanca.

El tema encaja en una línea viva del IMSE-CNM. El área de seguridad
hardware del instituto ha llevado generadores basados en osciladores de
anillo desde FPGA de la serie 7 de Xilinx, la misma familia de la Basys 3,
hasta silicio de 65 nm caracterizado (NorCAS 2024). Este TFM se incorpora a
ese camino.

## Objetivos

| Id | Objetivo | Entregable comprobable |
|---|---|---|
| O1 | Fuente de entropía a nivel de transistor: oscilador de anillo con habilitación y biestable de muestreo, simulado con ruido | Esquema paramétrico, frecuencia y jitter simulados, con el suelo de ruido numérico del banco declarado antes de leer ninguna cifra |
| O2 | Extracción del jitter de las formas de onda, separando cuantización, componente térmica y flicker | σ por periodo con incertidumbre y exponente de acumulación; estimador validado antes sobre datos sintéticos de jitter conocido |
| O3 | Del jitter a la min-entropía: modelo estocástico y elección justificada del divisor de muestreo | Tabla H_min frente a divisor; consigna de diseño para cumplir AIS 20/31 (PTG.2, H_min ≥ 0,98) con margen |
| O4 | Motor digital independiente de la tecnología: pruebas de salud, acondicionado y generador determinista basados en AES, AES-CMAC e interfaz I2C con vía de test separable | Código sintetizable y banco de pruebas por bloque con vectores oficiales (FIPS 197, SP 800-38, RFC 4493, CAVP) |
| O5 | Verificación funcional en FPGA con el ESP32 como comprobador independiente | Vectores conocidos, interoperabilidad cruzada y reto-respuesta, con tasa de acierto |
| O6 | Campaña de entropía sobre silicio real (los anillos de la FPGA) con los estimadores SP 800-90B, y comparación con el ESP32 bajo la misma metodología | Jitter medido, divisor resultante, estimaciones de la norma frente a la cota del modelo |
| O7 | Síntesis sobre una biblioteca de celdas estándar abierta | Área por bloque en puertas equivalentes y factores de crecimiento a área de núcleo |
| O8 | Comparación con el ESP32, con elementos seguros comerciales y con circuitos publicados, con incertidumbres declaradas | Capítulo de comparación de la memoria |

El resultado mínimo defendible es O1, O2, O3 y O5: una fuente diseñada
desde el transistor con su jitter convertido en cota, y un motor digital
verificado frente a una implementación independiente. Un resultado
negativo bien medido (por ejemplo, que el flicker domine y el divisor no
pueda crecer indefinidamente) cierra el trabajo igual que uno positivo.

## Arquitectura propuesta

- **Fuente de entropía.** Oscilador de anillo (RO1) muestreado por un
  segundo anillo (RO2) dividido por K_D (estructura ERO). El modelo
  estocástico de Baudet et al. (2011) da la min-entropía por bit en
  función de la varianza de fase acumulada; se usa el cálculo exacto, no
  la serie truncada del artículo, que no es una cota inferior. Objetivo de
  diseño: calidad Q ≥ 0,23, que da H_min ≥ 0,98 con margen. El reloj de
  placa no interviene como referencia de jitter (es un MEMS con PLL).
- **Pruebas de salud** RCT y APT de SP 800-90B, con umbrales calculados
  para la min-entropía medida.
- **Acondicionado y generador determinista** con AES-128 únicamente:
  función de derivación por cifrador de bloque y CTR_DRBG con función de
  derivación según SP 800-90A. Se ha descartado el SHA-256 (era casi la
  mitad del área y la norma admite acondicionadores basados en AES).
- **Autenticación** por reto-respuesta con AES-CMAC. El motor no descifra
  ni ofrece hash: el microcontrolador ya tiene aceleradores para eso.
- **Interfaz** esclavo I2C con mapa de registros, órdenes sondeables y una
  entrada de modo de test que es lo único que permite leer la clave o los
  bits crudos; en producto se inutilizaría.
- **Reparto de niveles.** Solo la fuente de entropía (anillos y
  muestreador) se diseña a nivel de transistor, que es donde el jitter y
  la metaestabilidad son efectos físicos. Todo lo digital va por síntesis
  sobre celdas estándar, como en cualquier circuito real.

## Estado actual y plan de trabajo

Trabajo ya realizado sin hardware (todo reproducible desde el repositorio):

- Modelo estocástico y estimador de jitter escritos y autovalidados;
  banco SPICE del anillo con modelos genéricos de transistor (suelo de
  ruido numérico 1,4 fs; la ley de raíz cuadrada del ruido se cumple a
  menos del 1 %; se identifica dónde deja de valer el modelo).
- RTL completo en VHDL-2008: anillo, ERO, captura, pruebas de salud,
  esclavo I2C, AES-128, AES-CMAC, CTR_DRBG y nivel superior. Siete bancos
  de pruebas pasan; el generador determinista reproduce los 960 vectores
  CAVP del NIST; una implementación Python independiente verifica la
  secuencia completa del motor.
- Síntesis sobre la biblioteca abierta IHP SG13G2 (130 nm): el motor
  digital ocupa unas 62 kGE, con un camino identificado hacia unas 20 kGE
  (compartir el AES, S-box compacta).
- Firmware de comprobador para el ESP32 (ESP-IDF, mbedtls), compilado y
  probado en placa.
- Línea base del ESP32 bajo SP 800-90B (catorce capturas, estimadores
  oficiales, análisis de varianza por condición).
- Memoria en inglés con la plantilla común, capítulos 1 a 7 en borrador.

Pendiente, por orden:

1. **Puesta en marcha en la Basys 3** (Vivado) y campaña de entropía (O5,
   O6): comprobar que los anillos oscilan, medir el jitter por el método de
   Fischer–Lubicz, fijar el divisor, recoger bits crudos y pasarles los
   mismos estimadores que al ESP32.
2. **Fuente de entropía con un PDK real** (O1, O2): sustituir los modelos
   genéricos por los de una tecnología del instituto en Cadence Virtuoso y
   Spectre, con análisis de ruido transitorio; si el tiempo lo permite,
   trazado y simulación post-trazado del bloque analógico. Los modelos del
   PDK quedarían en el instituto; el repositorio público solo contiene los
   genéricos.
3. **Cierre** (O7, O8): tabla de área final, comparación con incertidumbres
   y capítulo de conclusiones. La fabricación se documenta (coste y vía de
   acceso a un servicio multiproyecto) pero no se ejecuta.

Calendario orientativo: punto 1 en octubre y noviembre; punto 2 de
noviembre a enero; punto 3 en febrero, con la memoria cerrada para la
convocatoria siguiente.

## Lo que se pide a los tutores

- Dirección desde el área de seguridad hardware del instituto, donde ya se
  ha recorrido el camino FPGA serie 7 → silicio con generadores de
  osciladores de anillo.
- Acceso a Cadence Virtuoso/Spectre y a un PDK bajo la licencia del
  instituto para el punto 2 del plan.
- Si fuera posible, acceso puntual a un osciloscopio del laboratorio, solo
  para confirmar oscilación y frecuencia de los anillos (el jitter se mide
  dentro del chip, no con el osciloscopio).

El alumno aporta la Basys 3, los ESP32 y las herramientas libres ya
instaladas (GHDL, ngspice, Yosys, ESP-IDF).

## Repositorio

Código, modelos, firmware, resultados y memoria:
https://github.com/mmggjj/TFM_ENCRY (público).

## Referencias principales

- BSI, *AIS 20/31 v3.0: A proposal for functionality classes for random
  number generators*, 2024.
- M. Sönmez Turan et al., *NIST SP 800-90B: Recommendation for the Entropy
  Sources Used for Random Bit Generation*, 2018; *NIST SP 800-90A Rev. 1*.
- M. Baudet, D. Lubicz, J. Micolod, A. Tassiaux, "On the security of
  oscillator-based random number generators", *J. Cryptology*, 2011.
- V. Fischer, D. Lubicz, "Embedded evaluation of randomness in oscillator
  based elementary TRNG", *CHES 2014*.
- L. Benea et al., sobre jitter y flicker en osciladores de anillo medidos
  en Artix-7 y en ASIC de 28 nm, *TCHES 2024*.
- J. Kelsey, K. McKay, M. Sönmez Turan, "Predictive models for min-entropy
  estimation", *CHES 2015*; S. Zhu et al., "Analysis and improvement of
  entropy estimators in NIST SP 800-90B for non-IID entropy sources",
  *ToSC 2017*.
- Trabajos del grupo de seguridad hardware del IMSE-CNM sobre PUF/TRNG de
  osciladores de anillo en FPGA serie 7 y en 65 nm (*NorCAS 2024*).
