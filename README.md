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
| `analysis/` | modelo estocástico del anillo, estimadores de jitter, banco SPICE, modelo de referencia del DRBG (960 vectores CAVP), verificación cruzada, verificador de lecturas firmadas del PC y sesión con el medidor en placa (`placa_medidor.py`) |
| `.github/workflows/` | CI: modelo y estimadores, siete bancos GHDL con PSL, síntesis Yosys, banco en host con mbedtls real (y con ASan), compilación ESP-IDF de los dos firmwares y memoria en PDF con tectonic |
| `rtl/` | VHDL-2008 portable: `trng/`, `io/`, `aes/`, `drbg/`, `top/`; bancos en `tb/`; `run_tb.py` los ejecuta todos con GHDL |
| `synth/` | síntesis a celdas estándar abiertas (IHP SG13G2) con Yosys; área en puertas equivalentes por bloque. `synth/basys3/`: XDC, pblocks de los anillos y flujo Tcl de Vivado para la placa (probado en Linux con Vivado 2025.2, `docs/basys3.md`) |
| `rtl/fpga/` | envoltorio del motor para la Basys 3 (reset, SDA en colector abierto, LED de latido) |
| `firmware/verificador/` | proyecto ESP-IDF: maestro I2C, provisión, reto-respuesta con mbedtls, volcado de bits al PC |
| `firmware/medidor/` | proyecto ESP-IDF para ESP32-C3: el motor usado por un producto; clave ECDSA P-256 generada con aleatorio del motor, petición de certificado y lecturas de energía firmadas (`docs/lecturas_firmadas.md`) |
| `firmware/componentes/motor_i2c/` | capa de acceso al motor compartida por los dos firmwares (`docs/mapa_registros.md` en C) |
| `firmware/host_check/` | banco en el PC: los dos firmwares contra un motor simulado y mbedtls real, sin placa (`run_host.py`) |
| `sim/spice/` | descripciones de circuito del anillo a nivel de transistor |
| `tests/vectors/` | vectores oficiales de NIST usados en la verificación |
| `results/` | datos de campañas y logs íntegros |
| `memoria/` | LaTeX de la memoria (`tfm_main.tex`, en inglés) y versión de lectura en español (`tfm_main_es.tex`) |

## Estado (18-11-2026)

- Documentación y estados del arte: cerrados.
- Modelo y métodos de medida: validados sin hardware.
- RTL: anillo, ERO, captura, salud, I2C, AES (dos núcleos), CMAC, CTR_DRBG y
  nivel superior verificados en GHDL contra vectores oficiales (FIPS 197,
  SP 800-38A, RFC 4493, CAVP DRBG). Doce bancos, todos pasan
  (`results/run_tb_todos.log`; `tb_motor_top` con 14 propiedades PSL).
  Motor versión 0x04, semilla de 512 bits.
- **En FPGA** (`docs/basys3.md`): el motor entero en una **Basys 3**
  (XC7A35T, Vivado 2025.2) con el ESP32 de oráculo: siembra, clave, 40/40
  retos AES-CMAC iguales a los de mbedtls, aleatorio y zeroización
  [MEDIDO, 17-11-2026]. Jitter y campaña SP 800-90B en placa. Antes, la
  fuente sola en una Basys 2 (`docs/basys2.md`).
- Línea base del ESP32 bajo SP 800-90B y prueba de reinicios
  (`docs/esp32_linea_base_90b.md`, `docs/esp32_reinicios.md`).
- Firmware del ESP32: verificador (esp32) y medidor con lecturas firmadas
  (esp32c3), banco en el PC con mbedtls real (`results/host_check.log`).
- Síntesis sobre IHP SG13G2 (`docs/sintesis_resultados.md`).
- Abierto: el residuo del modelo de jitter en FPGA, la H declarada del
  integrado (sesgo del biestable sg13g2, `docs/basys2.md`), la memoria.

## Reproducir

```bash
python analysis/ero_model.py          # modelo, 24 comprobaciones
python analysis/jitter_estimator.py   # estimador, 20 comprobaciones
python analysis/ctr_drbg_ref.py       # DRBG contra 960 vectores CAVP
python rtl/run_tb.py                  # todos los bancos VHDL (GHDL)
python synth/sintetiza.py             # síntesis (Yosys + liberty IHP)
python3 firmware/host_check/run_host.py --mbedtls $IDF_PATH/components/mbedtls/mbedtls  # firmware en el PC (gcc, WSL); --sanear para ASan+UBSan
python3 analysis/fuzz_verifica_lecturas.py      # robustez del verificador de lecturas del PC
python analysis/placa_medidor.py COM25          # medidor en un ESP32-C3 por USB (firmware build_sim flasheado)
```

## Convenciones

[MEDIDO] / [SIMULADO] / [ESTIMADO] / [PENDIENTE] en toda la documentación.
La resolución del instrumento se declara antes de interpretar una
tendencia. Las salidas de síntesis, compilación y medida no se filtran.
Sin credenciales ni modelos de fábrica bajo confidencialidad en el
repositorio.
