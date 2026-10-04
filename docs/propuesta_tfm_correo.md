# Propuesta de TFM (versión corta para el correo)

**Título provisional:** Diseño de un motor criptográfico de generación de
claves para su implementación como circuito integrado: fuente de entropía
caracterizada a nivel de transistor y verificación en FPGA frente a un
ESP32.

**Idea.** Diseñar la cadena completa *ruido físico → bits → claves →
autenticación* como un circuito integrado dedicado que sirve claves a un
microcontrolador por I2C. La fuente de entropía es un oscilador de anillo
muestreado por otro, diseñado a nivel de transistor y simulado con ruido;
su jitter se convierte en una cota de min-entropía con un modelo
estocástico, y esa cota fija el divisor de muestreo. La parte digital
(pruebas de salud SP 800-90B, acondicionado y CTR_DRBG con AES-128,
AES-CMAC e interfaz I2C) va en VHDL independiente de la tecnología,
verificada con vectores oficiales y sintetizada sobre celdas estándar. La
Basys 3 sirve de vehículo de verificación y un ESP32 de comprobador
independiente y de referencia. No se fabrica el circuito; se deja el
diseño, el área y el camino de fabricación documentados.

**Por qué.** Mi TFM anterior mostró que el generador del ESP32 pasa la
batería NIST SP 800-22 en todas sus condiciones de funcionamiento, incluida
la que el fabricante desaconseja: esos tests no miden entropía. Aplicando
ahora SP 800-90B a catorce capturas reales sale 0,81-0,92 bit por bit por
la vía no-IID y ninguna cota posible, porque la fuente es una caja negra.
El trabajo construye la caja blanca, y encaja en la línea del área de
seguridad hardware del IMSE, que ya llevó generadores de osciladores de
anillo de FPGA serie 7 a silicio de 65 nm.

**Objetivos.** (1) Fuente de entropía a nivel de transistor simulada con
ruido; (2) extracción del jitter separando térmico y flicker; (3) modelo
estocástico y divisor para AIS 20/31 con margen; (4) motor digital en RTL
verificado con vectores oficiales; (5) verificación en FPGA con el ESP32
como comprobador; (6) campaña de entropía con los estimadores SP 800-90B;
(7) área en celdas estándar; (8) comparación con el ESP32 y con elementos
seguros comerciales. Mínimo defendible: 1, 2, 3 y 5.

**Estado.** Hecho sin hardware: modelo y estimador validados, banco SPICE
con modelos genéricos, RTL completo con siete bancos que pasan y 960
vectores CAVP, síntesis sobre IHP SG13G2 (≈ 62 kGE), firmware del ESP32
probado en placa, línea base del ESP32 bajo SP 800-90B, memoria con los
capítulos 1 a 7 en borrador. Pendiente: puesta en marcha en la Basys 3 y
campaña de entropía; fuente de entropía con un PDK real en Cadence; cierre
de la memoria.

**Lo que pediría:** dirección desde el área de seguridad hardware y acceso
a Cadence Virtuoso/Spectre con un PDK del instituto (los modelos quedarían
en el instituto; el repositorio público solo tiene modelos genéricos).
Repositorio: https://github.com/mmggjj/TFM_ENCRY
