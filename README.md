# TFM — Motor criptográfico ligero en FPGA validado frente al ESP32

Mario García Jiménez · Máster en Microelectrónica (US / IMSE-CNM) · 2026

Cadena completa en una Digilent Basys 3 (Artix-7 XC7A35T): fuente de
entropía por osciladores de anillo caracterizada físicamente → SHA-256 →
DRBG SP 800-90A → AES-128 / CMAC → SPI. El ESP32 (mbedtls + aceleradores
hardware) actúa como verificador independiente. El estudio previo del RNG
del ESP32 (repo `TFM_RNG`) es el capítulo baseline.

## Estructura

| Carpeta | Contenido |
|---|---|
| `docs/` | plan, arquitectura, estado del arte (3 frentes), referencias `.bib`, razonamiento de diseño |
| `rtl/` | VHDL-2008: `trng/`, `sha256/`, `drbg/`, `aes/`, `spi/`, `top/`, `tb/`; constraints `.xdc`; scripts Tcl de Vivado |
| `firmware/` | proyecto ESP-IDF del verificador / host de campaña |
| `analysis/` | Python: modelo de jitter, integración de SP 800-22 (del TFM_RNG) y SP 800-90B, comparación |
| `results/` | datos crudos de campaña (CSV/bin, inmutables) |
| `memoria/` | LaTeX (plantilla común de los TFM del autor) |

## Estado

- 2026-09-11 — WP0 documentación completado: tres estados del arte
  (TRNG/modelo estocástico, núcleos cripto/DRBG/vectores, plataforma y
  flujo) con ~140 referencias etiquetadas por estado de verificación;
  `docs/plan.md` y `docs/arquitectura.md` revisados con sus hallazgos.
  Vivado sin instalar; placa Basys 3 pendiente de confirmar visualmente.
  Siguiente: WP1 entorno (GHDL) y WP2 RTL capa 0.

## Convenciones

[MEDIDO] / [ESTIMADO] / [PENDIENTE] en toda la documentación. La
resolución del instrumento se declara antes de interpretar una tendencia.
Salidas de síntesis, compilación y medida no se filtran. Sin credenciales
en el repositorio.
