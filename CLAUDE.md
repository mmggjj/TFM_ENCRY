# Contexto del proyecto para Claude Code

Este repositorio es el TFM de Mario García Jiménez (Máster en
Microelectrónica, US / IMSE-CNM): un **motor criptográfico de generación
de claves** pensado para acabar como circuito integrado dedicado, que
sirve claves a un ESP32 por I2C. Hoy existe como RTL portable verificado
en simulación (GHDL) y sintetizado a celdas estándar; la FPGA (Basys 3)
es el vehículo de verificación, no el producto. Este fichero existe para
que otra sesión de Claude, en otro PC, pueda trabajar con él sin releer
todo. Léelo entero antes de tocar nada.

## Reglas de trabajo de Mario (no negociables)

- **Español** en conversación y documentación de trabajo; la memoria
  (`memoria/`) va en inglés.
- **Comentarios de código escuetos.** El razonamiento va en `docs/*.md`.
- **No filtrar salidas** de compilación, simulación o medida con
  `tail`/`grep`/`head` antes de leerlas: se lee el recuento completo. Un
  filtro esconde justo el aviso que importaba. Esto ya ha tapado
  resultados dos veces en este proyecto.
- **Medido / simulado / estimado**, siempre distinguido y con
  incertidumbre. **Declarar la resolución del instrumento antes de
  interpretar una tendencia.**
- **Nada de credenciales, tokens ni modelos de fábrica bajo
  confidencialidad** en el repo. Los comandos que necesiten credenciales
  los lanza Mario.
- El GitLab de Airzone (`gitlab2.airzonesl.es`) es **solo de lectura**
  para Claude: nada de commits, push, MRs ni issues allí. Lo interno de
  Airzone (WSBUS, esquemáticos, códigos) es confidencial y no se publica.
- Windows 11 + PowerShell 5.1 (sin `&&`); los proyectos ESP32 pueden ir
  en WSL o en Windows con `C:\esp\esp-idf` (v5.3.2). Commits con autor
  `MarioGarciaJimenez <mariogj.03@gmail.com>` y coautoría de Claude.
- Push por **HTTPS** (`https://github.com/mmggjj/TFM_ENCRY.git`): las
  claves SSH de sus máquinas no están dadas de alta en GitHub.

## Pendiente inmediato al retomar (parado el 15-09-2026 por la noche)

- La corrección de la fuga de clave por `ALEATORIO` está aplicada en RTL,
  banco, verificación, firmware y memoria, y el firmware recompila, pero
  **el banco `tb_motor_top` no se llegó a re-ejecutar** con el cambio: la
  sesión se paró a mitad. Antes de nada, desde la raíz del repo:
  `python rtl/run_tb.py motor_top` (unos 8 minutos) y después
  `python analysis/verifica_top.py`. Si algo falla, el cambio está en el
  estado `GENERANDO_ALEATORIO` de `rtl/top/motor_top.vhd` y en el paso 3b
  de `rtl/tb/tb_motor_top.vhd`.
- `results/run_tb_todos.log` puede estar vacío o truncado por ese corte;
  no es un resultado.

## Qué hay y qué está verificado

| Carpeta | Contenido | Estado |
|---|---|---|
| `docs/` | plan, arquitectura, **`mapa_registros.md`**, 4 estados del arte, resultados | cerrado |
| `analysis/` | modelo del anillo, estimadores, banco SPICE, **`ctr_drbg_ref.py`** (960 vectores CAVP), `verifica_top.py` | autovalidado |
| `rtl/` | VHDL-2008: anillo, ERO, captura, salud, I2C, AES, CMAC, CTR_DRBG, `top/motor_top.vhd` | 7 bancos pasan (`python rtl/run_tb.py`) |
| `synth/` | síntesis Yosys sobre IHP SG13G2, área en kGE | hecho |
| `firmware/verificador/` | ESP-IDF 5: maestro I2C + verificación con mbedtls | compila, no probado en placa |
| `memoria/` | LaTeX con la plantilla común | caps. 1–6 borrador, 7–8 pendientes de hardware |

**Pendiente de hardware:** puesta en marcha en la Basys 3, campaña de
entropía, ESP32 en el bucle. Nada de eso se ha ejecutado aún.

## Cómo integra un ESP32 el motor (lo que le importa al otro Claude)

La especificación es **`docs/mapa_registros.md`**. Resumen:

- I2C, dirección **0x30**, puntero de registro con autoincremento,
  400 kHz, 3,3 V. Sin estiramiento de reloj: las órdenes largas
  (sembrar, generar) se lanzan escribiendo `CONTROL` (0x03) y se sondea
  `STATUS` (0x02) hasta que baje el bit `ocupado`.
- Secuencia: leer `ID` (0x00) = 0xA5 → `CONTROL ← sembrar` → sondear →
  comprobar `sembrado` y sin alarmas → `CONTROL ← generar` → sondear →
  hay clave. Reto-respuesta: escribir 16 bytes en `RETO` (0x20),
  `CONTROL ← autenticar`, sondear, leer `ETIQUETA` (0x30) y comparar con
  `mbedtls_cipher_cmac(AES-128-ECB, clave, reto)`.
- **La clave solo es legible (0x10) con el pin `modo_test` activo.** Es
  para provisionar en banco. En producto la clave no sale del chip; el
  ESP32 solo obtiene etiquetas y aleatorio.
- Aleatorio para el host: `CONTROL ← aleatorio` (bit 6), sondear, leer
  `ALEATORIO` (0x40, 32 bytes). Es una generación del DRBG **independiente
  de la clave**. Hasta el 15-09 `generar` dejaba la clave en ese registro
  (fuga corregida en la revisión de traspaso): si ves código o notas
  antiguas que lean la clave desde ALEATORIO, están obsoletas.
- mbedtls en ESP-IDF **no trae CMAC activado por defecto**: hace falta
  `CONFIG_MBEDTLS_CMAC_C=y` (ver `firmware/verificador/sdkconfig.defaults`).
- Referencia de código: `firmware/verificador/main/main.c` (driver
  `i2c_master` nuevo de IDF 5, comandos de consola, tramas al PC con
  CRC32). Reutilizable tal cual como capa de acceso.
- El motor **no descifra** ni ofrece hash: solo genera claves, sirve
  aleatorio y autentica con CMAC. El ESP32 ya tiene aceleradores AES y
  SHA propios para lo demás.

## Cosas que no son obvias y conviene saber

- El oscilador de la Basys 3 es un MEMS con PLL (95 ps de jitter):
  **nunca** se usa como referencia de jitter; el anillo se muestrea con
  otro anillo.
- El generador determinista es CTR_DRBG **con** función de derivación y
  entrada fija de 256 bits de entropía + 128 de nonce; si se cambia esa
  disposición hay que regenerar los vectores con
  `analysis/gen_drbg_vectores.py`.
- Los tests de salud (RCT C=22, APT W=1024 C=596) están calculados para
  min-entropía 0,98; son genéricos y se fijan con la min-entropía
  **medida**.
- Con anillos a velocidad física la simulación del sistema completo no
  termina; `tb_motor_top` usa un modelo de anillo 10× más lento, y lo
  dice en el propio banco.
- Para editar `.tex` no usar `sed` en Git Bash (`\t` se vuelve
  tabulador): usar Python. `memoria/saneabib.py` sanea el `.bib` para
  pdfLaTeX. Las claves de acrónimo del paquete `acronym` no admiten `_`.

## Memoria de trabajo de la sesión original

Las decisiones y el porqué de cada una están en `docs/plan.md`,
`docs/arquitectura.md` (incluida la §9 sobre quitar el SHA-256),
`docs/modelo_ero_resultados.md`, `docs/sintesis_resultados.md` y
`docs/via_asic.md`. Si algo de este fichero contradice esos documentos,
mandan los documentos, que son más recientes en detalle.
