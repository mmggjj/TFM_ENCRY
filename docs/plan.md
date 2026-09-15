# Plan del TFM — Motor criptográfico de generación de claves

**Título de trabajo:** *Diseño de un motor criptográfico de generación de
claves para integración en circuito integrado: fuente de entropía
caracterizada desde el transistor y verificada en FPGA.*

**Versión:** v2 (12-09-2026). Sustituye a `plan_v1_fpga.md.bak`, que
planteaba el trabajo como un diseño en FPGA. El objetivo declarado por el
autor es ahora **un circuito integrado dedicado que entregue claves al
ESP32 por I2C**, y la FPGA pasa de ser el producto a ser el banco de
verificación. El resto del contenido técnico se conserva.

**Convención:** [MEDIDO] dato del banco con su incertidumbre; [SIMULADO]
dato de simulación, con la herramienta y los modelos declarados;
[ESTIMADO] dato de datasheet o literatura, con fuente; [PENDIENTE]
decisión bloqueada. Antes de interpretar una tendencia se declara la
resolución del instrumento que la produjo, incluida la resolución
numérica de un simulador.

---

## 1. Idea en una frase

Diseñar la cadena completa *ruido físico → bits → claves → cifrado y
autenticación* como un circuito integrado dedicado, con la entropía
justificada desde el transistor y no supuesta, y verificarla
funcionalmente en FPGA con un ESP32 como comprobador independiente.

## 2. Por qué este trabajo

- **Encaja en una línea viva del propio instituto.** El IMSE-CNM tiene un
  área formal de seguridad hardware, con laboratorio de canal lateral y
  circuitos criptográficos ya fabricados. Un grupo de ese área llevó
  generadores basados en osciladores de anillo desde FPGA de la serie 7,
  la misma familia de la Basys 3, hasta silicio de 65 nm caracterizado
  (NorCAS 2024, con continuación en 2026). Este TFM no abre camino: se
  incorpora a uno trazado, lo que además resuelve la cuestión de tutela y
  de continuidad. Detalle y referencias en `via_asic.md`.
- **Continúa el trabajo previo del autor.** El estudio de caja negra del
  generador del ESP32 (repo `TFM_RNG`) demostró que los tests
  estadísticos no distinguen entropía real. NIST lo respalda: en abril de
  2022 anunció la revisión de SP 800-22 rechazando su uso para evaluar
  generadores criptográficos. Aquel trabajo pasa a ser el capítulo de
  referencia; aquí se construye la caja blanca.
- **El hueco real del sector es la transparencia, no el precio.** Un
  elemento seguro comercial cuesta 0,90 $ y uno de ellos aporta
  certificado oficial de su fuente de entropía, pero dos de sus
  competidores directos no mencionan la norma de entropía en toda su hoja
  de datos. El argumento del trabajo es poder demostrar de dónde sale
  cada bit, no competir en coste.

## 3. Objetivos

| Id | Objetivo | Entregable verificable |
|---|---|---|
| O1 | **Fuente de entropía a nivel de transistor**: oscilador de anillo con habilitación y biestable de muestreo, dimensionado y simulado con análisis de ruido transitorio | Esquema paramétrico, frecuencia, consumo y forma de onda [SIMULADO], con el suelo de ruido numérico del banco declarado |
| O2 | **Extracción del jitter** por varianza de Allan sobre los instantes de cruce, separando cuantización, componente térmica y flicker | σ por periodo con incertidumbre, exponente de acumulación, dependencia con tensión y temperatura |
| O3 | **Del jitter a la min-entropía**: modelo estocástico y elección justificada del divisor | Tabla H_min frente a divisor; consigna de diseño Q ≥ 0,23 y margen |
| O4 | **RTL independiente de la tecnología**: acondicionado, generador determinista, AES-128, autenticación, tests de salud y **esclavo I2C** con vía de test separable | Código sintetizable, banco de pruebas por bloque con vectores oficiales |
| O5 | **Verificación funcional en FPGA** con el ESP32 de comprobador independiente | Vectores oficiales, interoperabilidad cruzada en ambos sentidos y reto-respuesta, con tasa de acierto y latencias |
| O6 | **Campaña de entropía sobre silicio real** (el anillo en la propia FPGA), con los estimadores de min-entropía de SP 800-90B y los requisitos de AIS 20/31 v3.0 | Entropía medida frente a la cota del modelo; comparación con el ESP32 bajo la misma metodología |
| O7 | **Camino a circuito integrado**: síntesis lógica sobre celdas estándar abiertas | Área en puertas equivalentes y en mm², con biblioteca, esquina y restricción declaradas, y el factor de crecimiento a área de núcleo citado |
| O8 | **Comparación y cierre**: diseño propio frente al generador del ESP32, frente a los elementos seguros comerciales y frente a los circuitos publicados | Tabla con calidad, min-entropía demostrable, caudal, área y consumo, con incertidumbres |

**Fuera de alcance, con motivo:**

- **Fabricación.** No por dinero ni por área: una tirada académica
  compartida cuesta entre 3.400 y 5.000 €, y el motor entero ocupa entre
  0,18 y 0,76 mm², que cabe de sobra. El impedimento es el plazo, de
  meses a más de un año, más el encapsulado, que no va incluido. Se
  documenta el coste y el camino como capítulo, no se ejecuta.
- **Criptografía asimétrica.** Un multiplicador en curva elíptica es un
  proyecto entero y ocuparía todo el presupuesto de área.
- **Resistencia a canal lateral.** Se declara el modelo de amenaza
  (atacante lógico y remoto, no físico) y se evitan fugas triviales de
  tiempo, pero no se persigue enmascaramiento ni campaña de trazas. Se
  menciona que el instituto tiene laboratorio para ello, como
  continuación natural.
- **Certificación formal.** Se usan los criterios de AIS 20/31 y
  SP 800-90B y los vectores oficiales, sin reclamar validación.

## 4. Criterios de éxito

- **Mínimo defendible:** O1, O2, O3 y O5. Es decir, una fuente de
  entropía diseñada desde el transistor, con su jitter extraído y
  convertido en una cota de min-entropía, y un motor digital verificado
  contra una implementación independiente.
- **Completo:** los ocho objetivos.
- Un resultado negativo bien medido cierra el trabajo igual que uno
  positivo. Ejemplo real: si el exponente de acumulación sale 2 en vez de
  1, significa que domina el flicker y que el divisor no puede crecer
  indefinidamente, y eso es un resultado.

## 5. Paquetes de trabajo

1. **WP0 Documentación.** Hecho. Cuatro estados del arte con unas 200
   referencias etiquetadas por estado de verificación.
2. **WP1 Modelo y métodos de medida.** Hecho y autovalidado sin hardware:
   modelo estocástico, estimador de jitter para la FPGA y extractor de
   jitter para simulación. 64 comprobaciones, 0 fallos.
3. **WP2 Fuente de entropía a nivel de transistor** (O1, O2). En curso.
   Primero con simulador libre y modelos genéricos para depurar el flujo,
   después en Cadence con el PDK real cambiando solo la cabecera.
4. **WP3 RTL digital** (O4). Anillo y muestreador escritos. Faltan el
   buffer de captura, el esclavo I2C, el acondicionado, el generador
   determinista, el AES y la autenticación.
5. **WP4 Verificación en FPGA** (O5) con firmware del ESP32.
6. **WP5 Campaña de entropía** (O6).
7. **WP6 Síntesis a celdas estándar** (O7).
8. **WP7 Comparación y memoria** (O8), en inglés, con la plantilla común
   de los trabajos anteriores del autor.

## 6. Decisiones ya tomadas y justificadas

| Decisión | Elección | Dónde está el razonamiento |
|---|---|---|
| Arquitectura de la fuente | ERO, anillo muestreado por otro anillo dividido | `arquitectura.md` §2 |
| Referencia de jitter | Nunca el oscilador de la placa, que es un MEMS con lazo de enganche y 95 ps de jitter máximo | `arquitectura.md` §1b |
| Objetivo de calidad | Q ≥ 0,2286 por el criterio de min-entropía, consigna 0,30 | `modelo_ero_resultados.md` §3 |
| Método de extracción de jitter | Varianza de Allan, diferencias de segundo orden | `estado_del_arte_trng.md` §8.2 |
| Generador determinista | CTR_DRBG con AES-128 sin función de derivación | `estado_del_arte_cripto.md` §3.2 |
| Autenticación | AES-CMAC | `estado_del_arte_cripto.md` §4.4 |
| Interfaz de producto | I2C, con vía de test separada y deshabilitable | decisión del autor, 12-09-2026 |
| Nivel de transistor | Solo la fuente de entropía; el resto por síntesis | `via_asic.md` |

**Abierta y relevante:** el SHA-256 se lleva el 47 % del área del motor.
Si el generador determinista acondiciona directamente, como hace Intel en
el suyo, el SHA-256 sobra y el motor baja de unas 25.000 a unas 13.000
puertas equivalentes. Hay que decidirlo antes de escribir ese bloque.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| Sin acceso a PDK ni a análisis de ruido transitorio | Flujo desarrollado con simulador libre y modelos genéricos; alternativa con PDK abierto (IHP SG13G2, con tirada gratuita para diseños abiertos) |
| El ruido numérico del simulador tapa el jitter | Toda campaña lleva una repetición con el ruido desactivado, que fija la resolución del banco |
| Los anillos se enganchan entre sí o a la alimentación | Es objetivo de estudio, no fallo. Hay ataque publicado que reduce el espacio de claves de 2⁶⁴ a 3300, y contramedida publicada con filtro |
| Alcance excesivo | Criterio de éxito escalonado (§4); cada bloque se integra solo tras pasar sus vectores |
| Tiempo del autor, que trabaja a jornada completa | Campañas automatizadas; todo simulable sin hardware; documentación incremental |

## 8. Reglas de trabajo

Español; comentarios de código escuetos y razonamiento en los documentos;
no filtrar la salida al compilar, sintetizar o medir; distinguir medido,
simulado y estimado con su incertidumbre; declarar la resolución del
instrumento antes de interpretar una tendencia; nada de credenciales ni
de modelos de fábrica bajo acuerdo de confidencialidad en el repositorio;
GitLab de la empresa solo como observador.

## 9. Correcciones heredadas del trabajo anterior

1. El sensor de temperatura interno del ESP32 entrega un entero de 8 bits
   en grados Fahrenheit, luego su resolución es 0,556 °C. El rango
   observado en aquella campaña era un solo escalón, así que la
   correlación entre temperatura y entropía allí publicada carece de
   resolución instrumental.
2. Medir, no inferir. La fracción de celdas estables se midió directamente
   en 87,64 %, frente al 93 % que se había inferido.
3. La novedad se formula como "no hemos encontrado", nunca como "no
   existe". Ya ha hecho falta aplicarlo una vez, ver `estado_del_arte_trng.md` §8.1.
4. Entropía de Shannon y min-entropía se distinguen siempre; toda cuenta
   de claves usa min-entropía.
