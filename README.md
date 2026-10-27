# TFM — Diseño y caracterización de aleatoriedad de un TRNG basado en osciladores en anillos

*Design and randomness assessment of a Ring Oscillator-based TRNG*

Mario García Jiménez · Máster en Microelectrónica (US / IMSE-CNM) · 2026-27

Diseño de un motor que fabrica sus propias claves a partir de ruido físico
y las sirve a un ESP32 por I2C, pensado para acabar como circuito
integrado dedicado. Cadena: osciladores de anillo (fuente de entropía,
caracterizada desde el transistor) → tests de salud SP 800-90B →
acondicionado y CTR_DRBG con función de derivación (SP 800-90A) → AES-128 y
AES-CMAC → esclavo I2C. Una sola primitiva, el AES, para acondicionar,
generar y autenticar. El ESP32 (mbedtls + aceleradores) es el verificador
independiente. La FPGA (Basys 3) es el banco de verificación, no el
producto. La primera parte del TFM caracteriza como caja negra el
generador del propio ESP32 (SP 800-22, estimadores SP 800-90B, prueba de
reinicios) y es la justificación del diseño de caja blanca.

## Estructura

| Carpeta | Contenido |
|---|---|
| `docs/` | plan, arquitectura, mapa de registros, estados del arte (TRNG, cripto, plataforma, vía ASIC) con ~200 referencias etiquetadas, resultados del modelo y de la síntesis |
| `analysis/` | modelo estocástico del anillo, estimadores de jitter, banco SPICE, modelo de referencia del DRBG (960 vectores CAVP), verificación cruzada |
| `rtl/` | VHDL-2008 portable: `trng/`, `io/`, `aes/`, `drbg/`, `top/`; bancos en `tb/`; `run_tb.py` los ejecuta todos con GHDL |
| `synth/` | síntesis a celdas estándar abiertas (IHP SG13G2) con Yosys; área en puertas equivalentes por bloque |
| `firmware/verificador/` | proyecto ESP-IDF: maestro I2C, provisión, reto-respuesta con mbedtls, volcado de bits al PC |
| `firmware/medidor/` | proyecto ESP-IDF para ESP32-C3: el motor usado por un producto; clave ECDSA P-256 generada con aleatorio del motor, petición de certificado y lecturas de energía firmadas (`docs/lecturas_firmadas.md`) |
| `firmware/componentes/motor_i2c/` | capa de acceso al motor compartida por los dos firmwares (`docs/mapa_registros.md` en C) |
| `firmware/host_check/` | banco en el PC: los dos firmwares contra un motor simulado y mbedtls real, sin placa (`run_host.py`) |
| `sim/spice/` | descripciones de circuito del anillo a nivel de transistor |
| `tests/vectors/` | vectores oficiales de NIST usados en la verificación |
| `results/` | datos de campañas y logs íntegros |
| `memoria/` | LaTeX de la memoria (`tfm_main.tex`, en inglés) y versión de lectura en español (`tfm_main_es.tex`) |

## Estado (15-09-2026)

- Documentación y estados del arte: cerrados.
- Modelo y métodos de medida: validados sin hardware (64 comprobaciones).
- RTL: anillo, ERO, captura, salud, I2C, AES, CMAC, CTR_DRBG y nivel
  superior escritos y verificados en GHDL contra vectores oficiales
  (FIPS 197, SP 800-38A, RFC 4493, CAVP DRBG). Siete bancos, todos pasan.
- Firmware del ESP32: el verificador (esp32) y el medidor con lecturas
  firmadas (esp32c3) compilan con ESP-IDF 5.3.5 y pasan su banco en el PC
  contra el motor simulado (27-10-2026, `results/host_check.log`).
- Síntesis: los bloques digitales sobre IHP SG13G2 (motor versión 0x03, 27-10-2026); motor ≈ 69 kGE sin la captura (116 con ella),
  con camino documentado hacia ≈ 20 kGE.
- Pendiente: hardware (Basys 3 + ESP32 en la mesa), campaña de entropía,
  simulación del anillo con el kit de la tecnología real, memoria.

## Reproducir

```bash
python analysis/ero_model.py          # modelo, 24 comprobaciones
python analysis/jitter_estimator.py   # estimador, 20 comprobaciones
python analysis/ctr_drbg_ref.py       # DRBG contra 960 vectores CAVP
python rtl/run_tb.py                  # todos los bancos VHDL (GHDL)
python synth/sintetiza.py             # síntesis (Yosys + liberty IHP)
python3 firmware/host_check/run_host.py --mbedtls $IDF_PATH/components/mbedtls/mbedtls  # firmware en el PC (gcc, WSL); --sanear para ASan+UBSan
python3 analysis/fuzz_verifica_lecturas.py      # robustez del verificador de lecturas del PC
```

## Convenciones

[MEDIDO] / [SIMULADO] / [ESTIMADO] / [PENDIENTE] en toda la documentación.
La resolución del instrumento se declara antes de interpretar una
tendencia. Las salidas de síntesis, compilación y medida no se filtran.
Sin credenciales ni modelos de fábrica bajo confidencialidad en el
repositorio.
