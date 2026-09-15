# TFM — Motor criptográfico de generación de claves para circuito integrado

Mario García Jiménez · Máster en Microelectrónica (US / IMSE-CNM) · 2026

Diseño de un motor que fabrica sus propias claves a partir de ruido físico
y las sirve a un ESP32 por I2C, pensado para acabar como circuito
integrado dedicado. Cadena: osciladores de anillo (fuente de entropía,
caracterizada desde el transistor) → tests de salud SP 800-90B →
acondicionado y CTR_DRBG con función de derivación (SP 800-90A) → AES-128 y
AES-CMAC → esclavo I2C. Una sola primitiva, el AES, para acondicionar,
generar y autenticar. El ESP32 (mbedtls + aceleradores) es el verificador
independiente. La FPGA (Basys 3) es el banco de verificación, no el
producto. El estudio previo del RNG del ESP32 (repo `TFM_RNG`) es el
capítulo de referencia.

## Estructura

| Carpeta | Contenido |
|---|---|
| `docs/` | plan, arquitectura, mapa de registros, estados del arte (TRNG, cripto, plataforma, vía ASIC) con ~200 referencias etiquetadas, resultados del modelo y de la síntesis |
| `analysis/` | modelo estocástico del anillo, estimadores de jitter, banco SPICE, modelo de referencia del DRBG (960 vectores CAVP), verificación cruzada |
| `rtl/` | VHDL-2008 portable: `trng/`, `io/`, `aes/`, `drbg/`, `top/`; bancos en `tb/`; `run_tb.py` los ejecuta todos con GHDL |
| `synth/` | síntesis a celdas estándar abiertas (IHP SG13G2) con Yosys; área en puertas equivalentes por bloque |
| `firmware/verificador/` | proyecto ESP-IDF: maestro I2C, provisión, reto-respuesta con mbedtls, volcado de bits al PC |
| `sim/spice/` | descripciones de circuito del anillo a nivel de transistor |
| `tests/vectors/` | vectores oficiales de NIST usados en la verificación |
| `results/` | datos de campañas y logs íntegros |
| `memoria/` | LaTeX, plantilla común de los TFM del autor |

## Estado (15-09-2026)

- Documentación y estados del arte: cerrados.
- Modelo y métodos de medida: validados sin hardware (64 comprobaciones).
- RTL: anillo, ERO, captura, salud, I2C, AES, CMAC, CTR_DRBG y nivel
  superior escritos y verificados en GHDL contra vectores oficiales
  (FIPS 197, SP 800-38A, RFC 4493, CAVP DRBG). Siete bancos, todos pasan.
- Firmware del ESP32: compila con ESP-IDF 5.3.2.
- Síntesis: los ocho bloques digitales sobre IHP SG13G2; motor ≈ 62 kGE,
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
```

## Convenciones

[MEDIDO] / [SIMULADO] / [ESTIMADO] / [PENDIENTE] en toda la documentación.
La resolución del instrumento se declara antes de interpretar una
tendencia. Las salidas de síntesis, compilación y medida no se filtran.
Sin credenciales ni modelos de fábrica bajo confidencialidad en el
repositorio.
