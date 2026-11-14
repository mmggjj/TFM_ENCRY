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
- Los repositorios internos de la empresa del autor son **solo de
  lectura** para Claude: nada de commits, push, MRs ni issues allí. Nada
  interno de la empresa (protocolos propietarios, esquemáticos, código,
  nombres de servidores) se copia a este repositorio, que es público.
- Windows 11 + PowerShell 5.1 (sin `&&`); los proyectos ESP32 pueden ir
  en WSL o en Windows con `C:\esp\esp-idf` (v5.3.2). Commits con autor
  `MarioGarciaJimenez <mariogj.03@gmail.com>`, **sin** línea de coautoría
  de Claude (`Co-Authored-By`) ni ninguna otra atribución (Mario, 30-10-2026).
- **También hay un PC con Linux (Ubuntu)** desde el 30-10-2026. Los scripts
  de análisis que llamaban a `wsl.exe` usan `bash()`/`a_wsl()` (y
  `sintetiza.py`, `sh()`/`EN_WINDOWS`): en Windows pasan por WSL y en Linux
  van directos. Herramientas: GHDL 5.0.1 de apt (mcode, el mismo que la CI);
  Yosys en `~/eda/oss-cad-suite/bin`; Python con numpy/scipy en `~/eda/venv`
  (el `python3` del sistema no los tiene); batería del NIST en
  `~/SP800-90B_EntropyAssessment/cpp`; tectonic en `~/eda/bin`; ngspice 47 +
  OpenVAF + PDK IHP con `~/eda/instala_ngspice_ihp.sh` (la 47 está en
  `ng-spice-rework/47/` de SourceForge, no en `ng-spice-rel`). **No usar el
  GHDL 7.0-dev de oss-cad-suite** (LLVM): `tb_motor_top` muere con SIGSEGV
  en las propiedades PSL sobre nombres externos (gdb: `c_agotado`; quitada
  esa, `c_captura`); los otros seis bancos pasan con él. `run_tb.py` admite
  GHDL LLVM/GCC (elabora a ejecutable) por si se arregla. Comprobado en
  Linux con el motor 0x03: 7 bancos (175 [ok]; 177 desde el 31-10, con
  K1/K2 de RFC 4493 comparadas en `tb_aes_cmac`, PSL 11/11 y 6/6 coberturas,
  volcado idéntico al de la rama), `verifica_top` 5/5, `ea_iid` corre, y la
  densidad de ruido del inversor IHP idéntica bit a bit a la de Windows.
- Push por **HTTPS** (`https://github.com/mmggjj/TFM_ENCRY.git`): las
  claves SSH de sus máquinas no están dadas de alta en GitHub.

## Estado al 14-11-2026: la placa es una Basys 2 (XC3S100E)

Lectura, resultados y riesgos en **`docs/basys2.md`** (resumen arriba del
todo). **Decisión de Mario (14-11, final del día): intenta conseguir una
Basys 3; los resultados de la Basys 2 son PROVISIONALES y la memoria no se
cierra con ellos** (nota no impresa en el cap. 8, EN y ES; los [PENDIENTE]
siguen). Qué se repite en la Basys 3 y las lecciones: `docs/basys2.md` y
`docs/puesta_en_marcha_fpga.md` §9. Commits del día f09ed89, 90c32a9,
3113dfa y el de la documentación (locales, sin push).

- La placa que hay es una **Basys 2 con XC3S100E** (1 920 LUT4; serigrafía
  leída por Mario), no la Basys 3. El motor entero no cabe (cripto ~6 800
  LUT4, estimación Yosys `-family xc3se`); la fuente sí. Mario no quiere
  pedir placa a los tutores. **Lo de la Basys 3 se conserva intacto** (si
  algún día hay una, se comparan los anillos en 90 y 28 nm). O5 (motor
  entero en FPGA) habrá que reformularlo en la memoria; el objetivo oficial
  y O6 se cubren con la fuente.
- `motor_top`: genéricos **`G_SOLO_FUENTE`** (sin DRBG/CMAC/AES; órdenes
  criptográficas rechazadas; **`DIAG.solo_fuente` = bit 3**) y
  **`G_CAPTURA_BYTES`** (0 quita `trng_capture`; `capturar` rechazada). Mismo
  mapa y VERSION 0x04. Con los valores por defecto la lógica es idéntica a
  la del commit 33b0b70 en cuatro variantes: **`synth/equivalencia.sh`**
  (AIG plana de Yosys comparada byte a byte, y ABC `cec` si solo cambia la
  numeración; control negativo con `G_KD_MIN=5`). Los kGE de abc se mueven
  un 0,2 % solo por los nombres (92,91 frente a 93,09) y las LUT xc7 de
  `basys3_top` de 5 125 a 5 057, con los mismos biestables: no son cambios
  de diseño. Cuidado: con el genérico directo en la condición de sembrar,
  GHDL `--synth` saca un latch (`siembra_es_reseed`); por eso `sin_cripto`
  es una señal.
- **`rtl/fpga/basys2_top.vhd`** + **`synth/basys2/basys2.ucf`** (pines del
  manual de Digilent): reloj B8 a 50 MHz esperados (JP4 sin soldar),
  `G_KD_MIN => 7`, latido a 1 Hz para medir el reloj con cronómetro, mismo
  frecuencímetro y display. Yosys xc3se: ~1 250 LUT4 (65 %), 452 FF.
- **XST no lee VHDL-2008**: `synth/basys2/a_verilog.sh` pasa el diseño a
  Verilog con GHDL y `synth/basys2/build.sh` hace xst, ngdbuild, map, par,
  trce, bitgen (`StartUpClk:JtagClk`) y `programar` con `djtgcfg`. Sin
  probar: ISE 14.7 (Linux, en `~/Xilinx`) y Adept 2 los está descargando
  Mario. La placa sale en USB como `1443:0007` (FX2): openFPGALoader no
  sirve.
- Bancos nuevos **`tb_motor_solo_fuente`** (21/21, PSL 4/4 y 2/2; mutante
  que acepta sembrar cazado a 552 µs,
  `results/tb_motor_solo_fuente_mutante.log`) y **`tb_basys2_top`**
  (frecuencímetro, JA3, latido e I2C por el pin bidireccional). Firmware:
  `DG_SOLO_FUENTE`, `id` lo muestra y `sembrar` lo dice sin esperar al
  arranque; `motor_sim.c` con `motor_solo_fuente`, banco host paso 16;
  0 fallos también con ASan/UBSan; verificador compilado con ESP-IDF 5.3.2
  sin avisos.
- **Herramientas en el Linux:** ISE 14.7 WebPACK en `~/Xilinx` (instalador
  por lotes; los acuerdos los acepta Mario), `~/eda/ise_compat` con
  `libncurses.so.5 -> .so.6` (lo usa `build.sh`), licencia **HOSTID=ANY** en
  `~/.Xilinx/Xilinx.lic` (el FlexLM de ISE ve el host ID `000000000000`
  porque solo mira `eth0`). Adept 2 (Runtime 2.30.1 + Utilities 2.6.1): la
  placa es "Basys2-100" con el nombre de usuario corrupto, se elige por
  `SN:`; cadena JTAG 0 = XC3S100E (0x11C10093), 1 = XCF02S. XST y ngdbuild
  no piden licencia; map sí.
- **ISE completo:** 818/960 slices (85 %), 1 516 LUT4 (78 %), 451 FF; todas
  las restricciones cumplen (`TS_ro2` mejor caso 4,65 ns: el contador de
  `ero_core` aguanta ro2 hasta ~215 MHz). **El primer bitstream no tenía
  anillos**: XST llevó los relojes a la salida de la NAND (par de
  inversores detrás) y map colapsó la cadena de LUT1; se vio en el XDL.
  Arreglado con `KEEP` en el UCF; comprobar siempre las etapas en la netlist
  implementada.
- **Primer día en placa (medido, 14-11-2026):** reloj 50 MHz (60 parpadeos
  de ld7 en 60 s, ±2 %), **ro2 167,8 MHz y ro1 105,8 MHz** (±0,1 MHz de
  lectura, ±2 % de escala), ld0 (alarma) apagado.
- **Tarde:** `AREA_GROUP` por anillo (bordes opuestos). Con 5/7 etapas
  compactas ro2 subió a 204,8 MHz, por encima de los ~203 MHz del contador
  de `ero_core`: `basys2_top` usa ahora **7 y 9 etapas** (ro2 143,8 MHz,
  ro1 108,7 MHz, margen 33 %). **ESP32 a0:dd:6c:0e:fb:4c en el bus**
  (GPIO22→JA1, GPIO21→JA2, GND→pin 5, pull-ups internos): `id` da
  `solo_fuente=1`; flujo de 10⁶ bits a `kd 13` y `14` sin errores.
- **Jitter (PRELIMINAR):** sin buffer no hay `kd 0`; `flujo_desborde.py`
  junta trozos consecutivos a `kd 7-11` aprovechando el desbordamiento, y
  `jitter_autocorrelacion.py` ajusta c(M) con el modelo del ERO (el
  estimador por varianza infraestima un 65-100 % a divisores altos;
  validado todo con bits simulados). Resultado: Q por periodo de ro2
  4-7·10⁻⁵ (σ ≈ 60-70 ps, ~10× lo térmico típico), los bits ya salen
  descorrelados a `kd 13`, **pero el modelo deja residuos 13-45× el ruido**
  en los divisores bajos: hay ruido no gaussiano (¿modulación, alimentación
  común?); detalle y lectura en `docs/basys2.md`.
- **El display modula los anillos** (ν bimodal por trozo a `kd 7`):
  variantes de `basys2_top` `G_QUIETO` (display apagado, LED fijo) y
  `G_MEDIDOR=false` (`GENERICOS` y `UCF` en `build.sh`). Apagado, el residuo
  baja de 45 a ~7 veces el ruido. La lógica colgada de los anillos cambia Q
  ×2,5 (con medidor 2·10⁻⁵, sin él 4,5·10⁻⁵); **repetibilidad ±3-5 %** en
  tres capturas de la misma variante, así que el ×2,5 es real.
- **Campaña SP 800-90B** (variante sin display ni medidor, flujo de 10⁶ bits,
  `kd 12-16`): `kd 13-16` saturadas (0,82-0,86), `kd 12` = 0,760, en el borde
  de lo que predice el modelo con Q 4,5·10⁻⁵ y por encima de lo que daría
  2·10⁻⁵: batería y estimador de jitter coherentes. **`CFG_KD` provisional
  ≥ 14** (K\* ≈ 2^12,3 con factor 2).
- **Más pruebas en placa (14-11, final):** captura larga de 8 378 368 bits
  a `kd 14` → SP 800-90B 0,890 (ESP32 0,911, ideal 0,889-0,935: no se
  separan, dato para O8). **Tests de salud en hardware**: saltan (RCT en
  `kd 8, 11, 12`; APT en `kd 8`), patrón no monótono por la fase
  determinista; **hallazgo de diseño: con α = 2⁻²⁰ el RCT da una falsa
  alarma cada ~8 min a `kd 14`** (rachas ≥ 22 iguales a las de bits ideales)
  y cada alarma bloquea el motor: decisión pendiente de Mario (subir el
  corte a 32 con α = 2⁻³⁰, o rearme automático en el maestro). **Prueba de
  reinicios §3.1.4** (`analysis/reinicios_fpga.py`, 1000 reprogramaciones
  por JTAG): `ea_restart` pasa (H_r 0,855, H_c 0,873 ≥ H_I 0,845), 1000
  arranques distintos, Hamming 512,0 ± 16,02; al contrario que el ESP32 sin
  ruido de arranque. Matiz: bits del flujo ~0,4 s tras configurar.
- La placa quedó con la variante sin display ni medidor grabada (volátil:
  al apagarla vuelve la demo de la Platform Flash). El ESP32
  a0:dd:6c:0e:fb:4c quedó con el verificador; `/dev/ttyUSB0` necesita
  `chmod` tras reconectarlo.

## Estado al 10-11-2026: captura continua (motor 0x04), sin placa

La placa se retrasa. Hecho ese día, nada en hardware:

- **Captura continua** (`rtl/trng/flujo_crudo.vhd`, registros FLUJO 0x0F,
  FLUJO_N 0x60 y FLUJO_DATO 0x61-0x7F; `docs/captura_continua.md` y
  `docs/mapa_registros.md`): FIFO de bytes en el dominio de sistema con los
  bits de después de `bit_cdc` (los de la semilla), que el ESP32 vacía por
  I2C mientras se llena; lectura con crédito (32 bytes desde 0x60: `n` y
  hasta 31 datos); si se llena, `desbordado` y se para. Mismas reglas que
  `capturar` (solo modo test, excluyente con siembra y captura, CFG_KD
  congelado). **VERSION 0x04.** Generic `G_FLUJO_BYTES`: **0 por defecto en
  `motor_top`** (sin FIFO, el área del integrado no cambia), 256 en
  `basys3_top`, 64 en el banco. Resuelve el pendiente de los 10⁶ bits
  consecutivos de SP 800-90B.
- `tb_motor_top` paso 9 (21 comprobaciones: 400 bytes seguidos iguales a
  los bits crudos apuntados desde fuera del DUT, crédito, desbordamiento,
  las tres paradas) y 3 propiedades PSL más: **85/85, PSL 14/14 y 8/8**.
  Mutante sin crédito cazado (`results/tb_motor_top_mutante_flujo.log`).
  Los nueve bancos en `results/run_tb_todos.log`.
- Firmware: `MOTOR_VERSION 0x04`, `MOTOR_VERSION_MIN 0x03` (lo que exigen
  verificador y medidor); orden **`flujo N`** del verificador (N bytes
  consecutivos en tramas `C` numeradas, `flujo fin ... ok` o
  `flujo: <motivo> ... la tira no vale`). `motor_sim.c` con las mismas
  reglas (byte i = `motor_flujo_byte(i)`); banco host paso 15 y paso de
  campaña con `--flujo`, 0 fallos. Compila con ESP-IDF 5.3.2 sin avisos.
- `analysis/campana_motor.py --flujo`: `kdNN_flujo.bin` solo si la tira
  llega entera (numeración, CRC, longitud y línea de fin); `resumen.csv`
  con columna `modo`. **El flujo sirve desde CFG_KD 13-14** [ESTIMADO, ro2 a
  300 MHz]: el cuello es la UART a 115200 (~5 kB/s); por debajo, trozos.
- Síntesis (Yosys con plugin, Linux): `flujo_crudo` 23,67 kGE,
  `motor_top` con FIFO 116,63; sin FIFO 93,09 frente a 93,20 del commit
  anterior con la misma herramienta (sin cambio medible). Las filas
  antiguas del CSV (92,53; otro camino de herramienta) no se han tocado.
  Yosys xc7 de `basys3_top`: 5125 LUT, 4292 FF, 36 RAM64M (~25 %).
- **ESP32, radio en A/B** (`docs/esp32_linea_base_90b.md`, aviso al final):
  `rng_sampler.c` arrancaba el Wi-Fi sin asociar y sin
  `sta_disconnected_pm = false` ni `WIFI_PS_NONE`: la radio pudo estar
  dormida y el "ningún efecto de condición" no dice nada de la radio.
  Firmware corregido y **repetido el mismo día** en el chip
  f8:b3:b7:2a:09:28 (12 capturas `0928rd_*`, carpeta
  `mac_f8b3b72a0928_radio_despierta`, fuera de los ANOVA de la campaña): con
  la radio despierta sigue sin haber efecto (ANOVA p = 0,41; radio frente a
  sin radio p = 0,80; frente a A+B de octubre p = 0,91), 3 por condición y
  un solo chip. Indicio de radio activa: B queda 1,1-2,2 °C sobre C (en
  octubre, 0,0). Esa placa lleva un firmware de alarma de Mario: copia en
  `~/esp32_alarma_backup_f8b3b72a0928.bin`, restaurada y verificada por
  SHA-256. `entropia_90b.py` admite ya ejecuciones en paralelo (cerrojo).
- **Revisión de la memoria** (`docs/revision_memoria_2026-11-10.md`):
  aplicados G1-G4, M4, M5, M8 y los recuentos (nueve bancos); pendientes
  M1-M3, M6, M7, los menores y los ocho puntos frente al objetivo oficial.
  Memoria con la captura continua (apéndice A, cap. 4 §cruces, cap. 7
  protocolo, cap. 8), EN y ES, PDF regenerados.
- Sin Vivado todavía: `build.tcl` sigue sin ejecutarse nunca.

## Estado al 08-11-2026: el primer día de placa, preparado sin placa

Detalle y checklist en **`docs/puesta_en_marcha_fpga.md`**. Nada probado en
hardware todavía.

- **Frecuencímetro de los anillos** (`rtl/fpga/medidor_frec.vhd`,
  `siete_seg.vhd`): `basys3_top` muestra en el display la frecuencia de
  ro2 (sw1 abajo) o ro1 (sw1 arriba) en MHz con un decimal (ventana de
  640 µs, prescaler 64, ±1 cuenta = 0,1 MHz); JA3 saca el anillo / 64 solo
  en modo test (un anillo visible deja seguir su fase). `motor_top` tiene
  un puerto nuevo `ro_mon` (en el ASIC no va a pad); generic `G_MEDIDOR`
  del envoltorio para quitarlo. Bancos nuevos `tb_medidor_frec` (10/10) y
  `tb_basys3_top` (4/4, 7 min). XDC: pines de sw1, JA3 y display; ro1 es
  ahora reloj (2,0 ns estimados). **`build.tcl` no cargaba
  `aes_enc_32.vhd`**: Vivado no habría elaborado; corregido.
- Yosys `synth_xilinx` de `basys3_top` (`synth/basys3/yosys_xc7.sh`): 4769
  LUT y 4234 FF, ~23 % y ~10 % del XC7A35T (estimación de otra herramienta).
- Verificador: `kd [N]` y `crudo` con plazo según CFG_KD (antes ~2 s
  fijos) y línea `crudo i kd K ms M`. Modelo `motor_sim.c`: la captura
  tarda 4096·2^kd periodos de ro2 a 300 MHz. Banco host paso 13 y paso de
  campaña; `consola_verificador.c` = `main.c` del verificador en el PC.
  **GCC 15**: mbedtls necesita `MBEDTLS_FATAL_WARNINGS=OFF` (`run_host.py`).
  Compilado con ESP-IDF 5.3.2 en el Linux (`~/esp/esp-idf-v5.3.2`).
- `analysis/campana_motor.py` (captura por lotes, log íntegro, CRC,
  `kdNN.bin`, `--90b`) y `jitter_estimator.py --trozos kdNN.bin
  --kd-captura K` (Q_raw, b y CFG_KD). Los análisis con numpy se lanzan con
  `~/eda/venv/bin/python`.
- CFG_KD de partida en Artix-7 [ESTIMADO, 2-4 ps / 3-5 ns]: 17-21. ro2
  real probablemente 170-330 MHz, no los 714 del XDC.
- **Plazos según CFG_KD** (`motor_plazo_bits_ms`, `motor_plazo_arranque_ms`,
  `motor_plazo_siembra_ms` en `motor_i2c`): `bits · 2^CFG_KD / 100 MHz · 2`,
  con 30/40 s de mínimo; con CFG_KD 24, arranque hasta 687 s.
  `motor_esperar_arranque` se rinde en cuanto hay alarma. Banco host pasos 8
  y 14 (`motor_arranque_lento` en el modelo, solo para el banco).
- `analysis/compara_modelo_campana.py`: cifra SP 800-90B de cada divisor
  frente a la calibración de `fuente_simulada_90b.csv` (lo que da la
  batería con bits del modelo de esa H_∞), no frente a H_∞ directamente;
  veredicto compatible / por debajo / por encima / saturada.
  `prueba_compara_modelo.py` (Q conocida): 0 fallos; con Q_raw ×4 solo el
  divisor más bajo lo detecta, así que la campaña necesita divisores bien
  por debajo de K*.
- Los trozos de `crudo` no son contiguos (SP 800-90B pide 10⁶
  consecutivos): resuelto el 10-11 con la captura continua (arriba).
  El commit `21b95b7` (curl con reintentos en `verifica.yml`) lo sube Mario:
  el token de Claude no tiene ámbito `workflow`.
- Cap. 8 (EN y ES) en borrador, con [PENDING]/[PENDIENTE] donde van los
  resultados de la placa; PDF regenerados.
- **8 chips más en el peor punto** (ss, −40 °C, 1,08 V, `--mismatch`, con
  la histéresis; `results/anillo_ihp_mc_ss_m40_v108_hist_*`, 49 min con 4
  procesos): 0 dobles cruces, cruces en 392,4-393,5 ns, K_D 3,44-4,23 M.
  Con los 15 anteriores, 23 chips: 4 piden más de 2²², el peor 4,49 M
  (H_∞ 0,973 con 2²²) y 2²³ cubre todos (≥ 0,9996). El chip 9 excluido no
  se puede repetir (sin semilla); era un caso aislado. `anillo_ihp.md`
  §4.3, cap. 7 y cap. 8 (EN y ES).

## Estado al 31-10-2026: la fuente simulada bajo SP 800-90B

`analysis/fuente_simulada_90b.py` genera bits **simulados** del ERO (modelo
estocástico con el Q de los transistores IHP: tt 27 °C, ss −40 °C 1,08 V y
el peor chip con desapareamiento) para divisores 2¹⁴-2²⁴, tres semillas,
10⁶ bits, más bits uniformes de referencia, y los pasa por la batería del
NIST con la misma vía que el ESP32. Lectura en **`docs/fuente_simulada_90b.md`**,
figura y tabla con `analysis/fuente_simulada_figura.py`, cap. 7 §"The
simulated source under the same battery" (EN y ES). Resultados:

- A 10⁶ bits la batería **se satura en 0,839 ± 0,021** (bits uniformes); todo
  punto con H_∞ ≥ 0,97 del modelo da 0,82-0,87. El ESP32 (0,85) y el motor
  a 2²³ (0,84-0,85) son **indistinguibles** a esta N.
- Con poca entropía la batería **sobreestima** (2¹⁴: modelo ≈ 0, NIST
  0,07-0,11): no es una cota; el divisor lo fija el modelo.
- La vía IID en byte **acepta** 2²¹ del peor caso (H_∞ 0,79) en 2 de 3 y ss
  (0,85) en 3 de 3, con crédito 0,86-0,90: refuerza llevar la cifra no-IID.
- `ea_iid` en bits tarda ~28 min por secuencia de 10⁶: no se ha corrido.
  La columna `IID` del CSV de la herramienta es el tipo de prueba, no el
  veredicto (`testCases.0.passed*`).
- **01-11: más bits** (`--n`, sufijo `_n<N>` en el nombre y columna
  `n_bits`; `fuente_simulada_figura.py` solo lee las filas de 10⁶). 2²³ en
  los tres casos e ideal, 3 semillas, a las longitudes de las capturas
  largas sin radio: **`esp_rf_off_1` = 3 523 072 bits y `esp_rf_off_2` =
  8 378 368** (no las dos ~8,4·10⁶). Las doce secuencias con H_∞ ≈ 1 dan
  0,881 (0,860-0,925) y 0,912 (0,889-0,935); el ESP32, 0,867 y 0,911:
  **el techo sube con N para todos y la batería sigue sin separarlos**.
  IID en byte a 8,4·10⁶: 12/12 pasan. Limita la compresión (33 de 36) o el
  t-Tuple. En byte, 4 secuencias bajan a 0,79-0,83 por la cota local
  (racha r = 4) de los predictores sobre bytes, no por la fuente. Logs
  `results/fuente_simulada_90b_n{3523072,8378368}.log`; docs §5; cap. 7 EN
  y ES con un párrafo (O8 no puede apoyarse en la diferencia de cifras SP
  800-90B); PDF regenerados.

## Estado al 28-10-2026: AES de 32 bits, I2C bajo abuso, placa y CI

- **`rtl/aes/aes_enc_32.vhd`**: segundo núcleo AES, ruta de 32 bits (4
  S-boxes compartidas entre SubBytes y el SubWord de la clave, un
  MixColumns, ShiftRows como permutación del registro, una columna por
  ciclo; 51 ciclos/bloque). Mismo interfaz que `aes_enc` con `borrar`.
  `aes_pkg` gana `sub_word` y `mix_columna` (y `mix_columns` se apoya en
  ella). `motor_top` lo elige con `G_AES_COMPACTO` (true por defecto;
  solo cuenta con `G_AES_COMPARTIDO`). `tb_aes_enc` ejecuta los dos
  núcleos con los mismos estímulos, exige que coincidan y prueba `borrar`
  a mitad (18/18). **Síntesis: núcleo 6,67 kGE frente a 16,06; motor
  92,53 frente a 101,83** (`motor_top_aes11` = variante con
  `-gG_AES_COMPACTO=false`, `VARIANTES` en `sintetiza.py`). Motor
  digital sin captura ≈ 46 kGE. Los 20-25 kGE del estado del arte ya no se
  prometen: con la tercera optimización quedaría en ≈ 42.
- **`tb_i2c_slave` bajo abuso** (pasos 5-13, 49/49): espurios bajo el
  filtro dentro de un byte (SDA con SCL alto, SCL en fase baja), STOP y
  START repetido a mitad de byte, bytes tras dirección ajena, puntero que
  sobrevive al STOP y da la vuelta en 0xFF, maestro que desaparece con el
  esclavo tirando de SDA (la guarda lo suelta a los `G_GUARDA` ciclos,
  medido), STOP tras ACK de lectura (si el byte siguiente empieza por 0 el
  esclavo retiene SDA, como cualquier esclavo I2C, y la guarda resuelve),
  bus a 1 MHz y 100 kHz. Cuenta pulsos de escritura (`n_we`) y una
  propiedad PSL (nunca tira de SDA en reposo). Sin fallos del RTL.
- **Medidor en un ESP32-C3 real** (COM25, `MOTOR_SIMULADO`, flasheado con
  esptool desde Windows; `analysis/placa_medidor.py`,
  `results/placa_medidor_esp32c3.log`, 0 fallos; `verifica_lecturas.py` 9
  válidas + CSR). Tiempos: clave 0,16-0,19 s, CSR 0,2 s, firma ~0,2 s. La
  clave en NVS y el contador de arranques sobreviven a reinicios por RTS.
  **Fallo real encontrado:** la consola con `fgets` sobre stdin no
  bloqueante troceaba las órdenes por USB-serie (`lectura 1` → `le`,
  `ctu`, `r`, `a`); corregido en los dos firmwares con `leer_linea`
  (acumula hasta `\n`). Con el motor simulado, la clave tras `olvidar` sale
  igual (rand() sin semilla): documentado como demostración, no fallo.
- **`.github/workflows/verifica.yml`**: modelo/estimadores, bancos GHDL
  (apt `ghdl`) + `verifica_top`, síntesis (`--verilog`, yowasp-yosys),
  banco en host con mbedtls 3.6 clonado (+ `--sanear`), ESP-IDF 5.3.5 en
  contenedor (los dos proyectos, normal y `MOTOR_SIMULADO`), memoria con
  tectonic (PDF como artefacto). `sintetiza.py` ya corre en Linux sin
  `wsl.exe` (`EN_WINDOWS`). Primera ejecución (push de 6330180): 7/7
  trabajos en verde, bancos GHDL en 6 min, memoria compilada por primera
  vez; la síntesis del runner coincide con la local dentro del 0,5 %. El
  banco en host salió verde **a medias**: el clon git de mbedtls no
  trae los ficheros generados y `run_host.py` degradaba en silencio al
  modo sin mbedtls. Arreglado: tarball de release en la CI y error si se
  pide `--mbedtls` y no compila. Subir un flujo exige un token con ámbito
  `workflow` (el PAT anterior no lo tenía).
- `rtl/run_tb.py` busca también `~/eda/ghdl/bin/ghdl.exe`.

## Estado al 27-10-2026 (noche): motor versión 0x03

Cuatro reglas nuevas en el RTL, salidas de los pendientes de la revisión
(`rtl/top/motor_top.vhd`, `rtl/drbg/ctr_drbg.vhd`; especificación en
`docs/mapa_registros.md`):

- **`capturar` ya no puede exponer la semilla.** Es una orden más del
  secuenciador: solo en modo test, con el motor libre y sin otra captura en
  marcha (`cap_en_curso`); `sembrar`/`resembrar` se rechazan mientras hay
  una captura en curso. Antes una captura lanzada durante una siembra dejaba
  los bits de la semilla en el buffer, legible al activar modo test.
- **`PETICIONES` no da la vuelta.** Generic `G_PET_BITS` (32 en hardware; el
  banco usa 4): con el contador a todo unos el DRBG ignora `generar` y el
  top rechaza `generar`/`aleatorio` con **`DIAG.agotado` (bit 2)** hasta
  resembrar.
- **`borrar_todo` (CONTROL bit 7)**, zeroización: clave, estado del DRBG y
  contador (`ctr_drbg.borrar`), RETO, ALEATORIO y semilla a cero, clave nula
  cargada en el CMAC (estado `ZEROIZANDO`). Se atiende también con alarma.
- **CFG_KD de reset = 24** (generic `G_KD_RESET`; antes 7).
- VERSION pasa a **0x03**. Prioridad de órdenes en una misma escritura:
  borrar_todo, sembrar/resembrar, generar, aleatorio, autenticar, capturar.
- Bancos: `tb_motor_top` pasos nuevos 5d (agotado, con `G_PET_BITS => 4`),
  6a-6c (captura) y 8 (zeroización); `tb_ctr_drbg` con los puertos nuevos.
  **Los siete bancos pasan** (`tb_motor_top` 64/64 comprobaciones tras la revisión y el AES compartido) y
  `verifica_top.py` 5/5 (`results/tb_motor_top.log`). Ojo al leer `PETICIONES` con `leer_bloque`:
  el byte bajo queda a la izquierda del vector (`x"05000000"` = 5).
- Modelo en host (`motor_sim.c`): mismas reglas, `motor_pet_max` y
  `motor_capturando` para el banco; `test_verificador` pasos 11 (agotado) y
  12 (`cero`); firmware: `CTL_BORRAR_TODO`, `DG_AGOTADO`, `MOTOR_VERSION 3`,
  comando `cero` en el verificador. Banco host 0 fallos, firmware compila
  (0 avisos). **Síntesis repetida** (camino Verilog + yowasp, abajo):
  motor_top 115,68 kGE con dos AES (+0,76 respecto a la 0x02; el DRBG
  +0,99 por el contador saturado y el borrado) y **101,56 kGE con el AES
  compartido** (abajo), motor digital sin captura ≈ 55 kGE.
  `docs/sintesis_resultados.md`, `results/sintesis_sg13g2.{csv,log}` y el
  cap. 6 de la memoria (EN y ES) al día.
- Memoria: cap. 4 (EN y ES) con el párrafo de las cuatro reglas; PDF sin
  regenerar (en este PC no hay tectonic).
- **Segunda revisión independiente, del RTL 0x03** (otra sesión, con
  banco extendido y mutantes en copias): un hallazgo grave y tres medios,
  todos corregidos. **H1**: `cap_en_curso` se perdía un ciclo después de
  lanzar cualquier captura que no fuera la primera (`cap_lleno` de la
  anterior aún a 1), la siembra se aceptaba y la semilla volvía al buffer;
  ahora `cap_en_curso` solo se baja con `cap_lleno = '1' and cap_arranca =
  '0'`, y el banco (6d) hace una segunda captura, comprueba `cap_en_curso`,
  el rechazo de `resembrar` y que la semilla no está en los 4096 bits del
  buffer a ningún desplazamiento. **H2**: `borrar_todo` dejaba Key
  recuperable en `temp_hi`/`kdf`/`x_df`/`aes_clave` y en la clave de ronda
  del `aes_enc`; `ctr_drbg.borrar` limpia ahora todos los intermedios, se
  atiende en cualquier fase (aborta) y `aes_enc` tiene entrada `borrar`.
  **H3**: ETIQUETA seguía legible tras borrar; `aes_cmac` pone `x` a cero al
  cargar clave y el top lee 0x30 como ceros sin `etiqueta_lista` (modelo
  host igual). **H4**: `resembrar` sin estado se aceptaba; ahora exige
  `drbg_sembrado`. **H7**: `modo_test` pasa por dos biestables
  (`modo_test_s`). **H6** (documentado): `borrar_alarmas` + siembra en la
  misma escritura aborta la siembra; bits 0 y 5 a la vez → resembrar.
  `tb_ctr_drbg` cubre ahora `borrar` (en reposo y a mitad) y la saturación
  con una segunda instancia `G_PET_BITS => 2`.
- **AES compartido** (`G_AES_COMPARTIDO`, por defecto true): `aes_cmac` y
  `ctr_drbg` tienen generic `G_AES_EXTERNO` y puertos `aes_*_o/_i`; el
  único `aes_enc` vive en `motor_top` (`g_nucleo_unico`) y se reparte por
  `arranca` (el núcleo captura clave y dato en ese ciclo); salida y `listo`
  van a los dos. PSL `p_aes_uno` en el banco: nunca arrancan a la vez.
  Síntesis: **101,56 kGE** (−14,1 respecto a los 115,68 con dos núcleos;
  la estimación era 15,8: el reparto y la entrada `borrar` del AES se
  comen el resto); motor digital sin captura ≈ 55 kGE. Cuidado con las
  etiquetas de `generate`: VHDL no distingue mayúsculas y `g_aes_externo`
  chocaba con el generic `G_AES_EXTERNO`.
- **Reset sincronizado** (`rtl/trng/reset_sync.vhd`): activación asíncrona
  y liberación síncrona, uno por dominio (`rst_n_s` para clk, `rst_n_ro`
  para ro2). `bit_cdc` tiene reset también en origen y `trng_capture` un
  reset por dominio (`rst_n_ro`). El reset de la placa ya no llega crudo a
  ningún biestable. Siete bancos en verde tras el cambio.
- **Propiedades PSL en `tb_motor_top`** (bloque `propiedades`, VHDL-2008 en
  línea, no en comentarios: GHDL solo las evalúa así): con alarma no hay
  generación ni siembra, sin test de arranque no se recoge semilla, con el
  contador agotado no se genera, captura y siembra excluyentes, captura
  solo en modo test, sin clave no se autentica, `borrar_todo` deja la clave
  a cero en el ciclo, y el motor nunca se queda ocupado (`eventually!`);
  más cuatro `cover`. Se vigilan en toda la simulación, no solo en los
  pasos que las provocan. `run_tb.py` pasa `--psl-report` y falla si hay
  aserción violada o cobertura sin alcanzar. Resultado: 11/11 aserciones
  y 6/6 coberturas. Mutante (copia aparte, `generar` sin mirar la alarma):
  lo caza `p_alm_gen` 90 µs antes que el paso 5b del banco
  (`results/tb_motor_top_mutante.log`). **Formal con sby descartado**
  por ahora: GHDL `--synth --out=verilog` vuelca los `cover` con sintaxis
  VHDL que Yosys no lee, y el anillo es un segundo reloj.
- **Basys 3 sin placa**: `rtl/fpga/basys3_top.vhd` (envoltorio: btnC como
  reset, SDA en colector abierto, LED de latido), `synth/basys3/basys3.xdc`
  (pines, reloj del anillo ro2 con periodo estimado 1,4 ns,
  `ALLOW_COMBINATORIAL_LOOPS`, `DONT_TOUCH`, `set_disable_timing`),
  `ro_pblocks.xdc` (un pblock por anillo) y `build.tcl` (flujo non-project,
  `-tclargs programar` para grabar). Solo analizado con GHDL; **sin Vivado
  en este PC**, sin probar. Instalación de Vivado en el Windows de Mario y
  grabación (también con `openFPGALoader` desde Linux):
  `docs/instalacion_vivado_windows.md` (31-10, sin ejecutar). El Ubuntu
  26.04 no está entre los Linux que soporta AMD (22.04 y 24.04).
- **Medidor**: la clave privada se guarda en NVS (`nvs_clave()`), se
  recupera al arrancar y `olvidar` la borra; el firmware avisa de que sin
  cifrado de flash/NVS va en claro. Banco host paso 11.
- **Síntesis sin OSS CAD Suite**: `synth/sintetiza.py` tiene un segundo
  camino, GHDL de Windows `--synth --out=verilog` + `yowasp-yosys` (Yosys
  por pip en WSL, `pip install --user yowasp-yosys`), mismo flujo y misma
  biblioteca; con `aes_enc` da −0,9 % respecto al plugin. Se elige solo
  según la herramienta que haya (`--verilog` lo fuerza).

## Estado al 27-10-2026 (tarde): el motor usado por un producto

Rama `feat/lecturas-firmadas` (sobre `fix/salud-bloquea-salida`). Diseño y
porqués en **`docs/lecturas_firmadas.md`**.

- **`firmware/componentes/motor_i2c/`**: la capa de acceso al motor
  (mapa, `motor_orden()` con `DIAG.rechazada`, plazos en tiempo real,
  `motor_rng()` como `f_rng` de mbedtls que **falla cerrado**) sale del
  verificador a un componente compartido. El verificador usa el componente
  (`set(EXTRA_COMPONENT_DIRS ../componentes)`).
- **`firmware/medidor/`** (ESP32-C3): el motor usado, no juzgado. Clave
  ECDSA P-256 generada con bloques `ALEATORIO` del motor (2 por clave), que
  no sale del chip; `publica` (trama `P`, SPKI DER), `csr` (PKCS#10 PEM),
  `lectura N` (trama `L`: 24 bytes + firma DER). ECDSA determinista
  (RFC 6979, `lectura.c` no compila sin `MBEDTLS_ECDSA_DETERMINISTIC`): el
  motor solo entra en la generación de la clave; con alarma se sigue
  firmando y no hay clave nueva, y una generación fallida mantiene la
  anterior. Seguridad acotada a 128 bits por el CTR_DRBG AES-128.
- **`firmware/host_check/`** (antes dentro del verificador): `run_host.py`
  compila y corre `test_verificador.c` y `test_medidor.c` contra
  `motor_sim.c` + `plataforma_sim.c` con **mbedtls real** (`--mbedtls`, vale
  el árbol de ESP-IDF; lo compila con cmake) y pasa la salida del medidor
  por `analysis/verifica_lecturas.py --permitir-cambio` (verifica con
  `cryptography`): 9 válidas, 1 manipulada, 1 repetida y 2 cambios de clave
  plantados, CSR válida. Sin mbedtls real el verificador usa
  `mbedtls_stub.c` (CMAC del modelo, no independiente) y el medidor se
  salta. `motor_sim.c` es solo el modelo (siembra diferida hasta que acaba,
  abortada por alarma, resembrar sin estado rechazado, semilla distinta en
  cada siembra, `motor_fallo_tras_aleatorio` para fallos a mitad);
  `plataforma_sim.c` tiene ticks, rand, CRC32 real, MAC fija y una NVS de un
  valor. Log: `results/host_check.log`, 0 fallos.
- **Revisión independiente** del primer commit (otra sesión, sin mis
  conclusiones): 13 hallazgos, todos corregidos o documentados. Los que
  importan: el `memset` final de `motor_rng()` lo eliminaba el compilador
  (ahora bucle `volatile`); `motor_orden()` espera a que el motor esté libre
  **antes** de escribir CONTROL (tras un fallo de bus a mitad de orden la
  siguiente se rechazaba); la secuencia de las lecturas lleva en el byte
  alto un contador de arranques en NVS; `verifica_lecturas.py` va en una
  sola pasada, cuenta y avisa de los cambios de pública (`clave_cambiada`,
  fallo salvo `--permitir-cambio`) y un log vacío no pasa; con el bus caído
  `clave` dice "ERROR I2C" y no "sin sembrar"; `lectura N` tope 1000. El
  revisor señaló también un nombre en los agradecimientos de
  `memoria/tfm_main*.tex`: es anterior a esta rama y decisión de Mario.
- **Compilado con ESP-IDF 5.3.5** (WSL): verificador esp32 y medidor esp32c3,
  0 avisos (`results/verificador_build_esp32.log`,
  `results/medidor_build_esp32c3.log`; `$HOME`/`$IDF_PATH` enmascarados).
- **QEMU** (`qemu-system-riscv32`/`-xtensa` de Espressif): sin motor el
  medidor arranca y falla cerrado (`results/qemu_medidor_sin_motor.log`);
  con `idf.py -B build_sim -DMOTOR_SIMULADO=1 build` (medidor y verificador)
  el modelo del banco va dentro del firmware suplantando al driver I2C con
  `--wrap` (+ `-u`, porque el objeto está en `libmain.a` y nadie lo llama) y
  la secuencia completa corre en el chip emulado con el mbedtls del objetivo
  y la NVS real; dos arranques sobre la misma flash y `verifica_lecturas.py`
  sobre el log: `results/qemu_medidor_esp32c3*.log`. Pila mínima libre de la
  tarea principal 10 568 B de 12 288. Verificador en QEMU esp32: 20 retos,
  20 aciertos (`results/qemu_verificador_esp32.log`). En QEMU hay que dar
  tiempo entre órdenes: la consola no es por interrupción y lo que llega
  mientras firma se pierde. Nada en placa.
- `run_host.py --sanear` (ASan+UBSan, `results/host_check_sanear.log`; ASan
  encontró una fuga de la clave al "reiniciar") y
  `analysis/fuzz_verifica_lecturas.py` (`results/fuzz_verifica_lecturas.log`;
  encontró una excepción con una trama P que no era DER). Los dos en verde.
- Memoria: cap. 5, sección nueva "The engine in a product" en inglés y
  español; PDF no regenerados. README actualizado.
- Pendiente: guardar la clave (NVS cifrado o el motor como elemento seguro,
  que hoy solo guarda una AES-128 y no firma), hora real, resembrado por
  `PETICIONES`, lecturas reales, contador de arranques de un byte; y la
  lista de la revisión de abajo.

## Estado al 27-10-2026: la alarma de salud bloquea la salida

Revisión externa del RTL y del firmware. Fallo grave corregido (rama
`fix/salud-bloquea-salida`):

- **Antes**, con alarma levantada seguían saliendo clave y ALEATORIO
  (`generar`/`aleatorio` solo miraban `sembrado`), el APT nunca evaluaba la
  primera semilla (384 bits < ventana de 1024) y no había test de arranque.
- **Ahora** (`rtl/top/motor_top.vhd`, `rtl/trng/health_tests.vhd`): con
  alarma se rechazan sembrar, resembrar, generar y aleatorio; test de
  arranque de SP 800-90B §4.3 (una ventana completa del APT sin alarma tras
  el reset o tras borrar, y borrar reinicia la ventana); la semilla solo
  entra en el DRBG cuando se cierra limpia la ventana que contiene su último
  bit (estado `VALIDANDO`); registro nuevo **DIAG (0x0E)** con `arrancado` y
  `rechazada`; VERSION pasa a 0x02. Especificación en `docs/mapa_registros.md`.
- `tb_health_tests` (caso 6) y `tb_motor_top` (2.0, 5b, 5c; la alarma se
  fuerza con `force` sobre un nombre externo) cubren todo. Los siete bancos
  pasan con GHDL 6.0.0 (`results/tb_motor_top.log`). Si el Python es el de
  Microsoft Store no ve `%LOCALAPPDATA%\ghdl`: poner GHDL en otra carpeta y
  su `bin` en el PATH al lanzar `run_tb.py`.
- Verificador (`firmware/verificador`): `orden()` comprueba
  `DIAG.rechazada`; plazos en tiempo real con `CONFIG_FREERTOS_HZ=1000` (a
  100 Hz `pdMS_TO_TICKS(2)` era 0); `sembrar` espera al test de arranque;
  comando `borrar`; ni rechazos ni fallos de bus llegan al PC como tramas
  con CRC válido; `generar` sin modo test invalida la clave provisionada.
  `host_check/motor_sim.c` modela ahora `ocupado`, arranque, rechazos y
  alarma, y `test_verificador.c` comprueba cuentas reales (antes había
  `chk(true, …)`). Sin compilar con ESP-IDF en este PC.
- Memoria: cap. 4 actualizado en inglés y en español; **los PDF no están
  regenerados**.
- Pendiente de la misma revisión: sin XDC/SDC; sincronizador de reset y
  `bit_cdc` sin reset; condiciones A/B del ESP32 posiblemente con la radio
  dormida (`rng_sampler.c` sin `sta_disconnected_pm = false`). Lo demás
  (captura y semilla, `CFG_KD` de reset, `reseed_interval`, zeroización) se
  resolvió en la versión 0x03 (sección de arriba).

## Estado al cierre del 19-09-2026

- `tb_motor_top` re-ejecutado con la corrección de la fuga y el
  endurecimiento de CFG_KD: **18/18** comprobaciones y `verifica_top.py`
  5/5 (log íntegro en `results/tb_motor_top.log`). El banco tarda unos
  4 min de simulación; ahora termina solo con `std.env.stop` (antes los
  anillos seguían oscilando y GHDL no acababa nunca).
- Hecho sin placa: línea base del ESP32 bajo SP 800-90B (abajo), con
  **treinta y ocho capturas**: nueve repeticiones por condición A-D (la de
  agosto, primera campaña, y dos del 19-09 en el chip ec:e3:34:9a:d1:18;
  tres del 12-10 en el chip a0:dd:6c:0e:fb:4c; tres del 20-10 en el chip
  f8:b3:b7:2a:09:28, prefijo `0928_`; todas con `firmware/esp32_rng`; los
  datos de cada chip van en su carpeta) y dos largas sin radio; una segunda
  tanda del tercer chip (`0928t2_`) queda fuera de los ANOVA. ANOVA por
  estimador: ningún efecto de condición (p ≥ 0,045) ni de chip
  (12 + 12 + 12, p ≥ 0,032, Bonferroni 0,0045). SP 800-22 de segundo nivel
  con 59 secuencias (`analysis/nist_segundo_nivel.py`): pasa todo.
  La placa de agosto ES el chip ec:e3:34:9a:d1:18 (lo recoge el informe de
  agosto; su CSV no tenía columna de MAC). Resumen en
  `results/entropia_90b_resumen.md`; lectura en `docs/esp32_linea_base_90b.md`.
  Los chips se nombran por su MAC ("tres chips del mismo modelo").
  Calibración de la vía IID con datos buenos del mismo tamaño
  (`analysis/calibra_iid.py`, `analysis/chi2_90b.py`): la χ² de
  independencia en modo byte de `ea_iid` falla el 1,7 % con datos
  perfectos a 125 000 B; los fallos sueltos del ESP32 caben en eso.
- Prueba de reinicios del ESP32 (SP 800-90B §3.1.4, 12-10-2026, chip
  a0:dd:6c:0e:fb:4c, `docs/esp32_reinicios.md`): `firmware/reinicios` y
  `firmware/reinicios_sin_ruido` (mismo programa; el segundo desvía
  `bootloader_random_enable()` con `--wrap`), captura con
  `analysis/reinicios_esp32.py`, análisis con `analysis/reinicios_90b.py`.
  Bootloader de serie: pasa. Sin el ruido del bootloader: falla (H_r 0,024),
  759 secuencias distintas en 1000 y todas trozos de una secuencia fija:
  6,5-10,8 bits por arranque. Con radio (`firmware/reinicios_radio*`,
  dos lecturas por arranque; control `-DSIN_RADIO=1` en `build_espera`):
  Wi-Fi encendido sin ruido de arranque → pasa (0 repeticiones; 289
  parejas con el mismo estado inicial divergen); control con la misma
  espera sin radio → falla igual que en D. La radio mete ruido; sin ella
  el RNG no recibe nada en 350 ms. El chip queda con `firmware/reinicios`
  (bootloader de serie).
- Tercer chip (f8:b3:b7:2a:09:28, 20/21-10-2026; placa de otro uso de Mario,
  su flash se copió y se restauró al acabar): normal pasa, sin_ruido falla
  igual; **sin ruido de arranque los dos chips sacan la misma secuencia**
  (`analysis/reinicios_entre_chips.py`, `results/esp32_reinicios/entre_chips.md`,
  verificado por tres revisiones). `firmware/reinicios_paso`: el generador
  avanza un paso por ciclo de APB desde un estado fijo (204/204 parejas).
  `firmware/reinicios_fuentes`: meten ruido la radio, `bootloader_random_enable`
  desde el programa y las conversiones normales del ADC (bastan 17); no lo
  meten `esp_wifi_init` sin arrancar ni crear/borrar la unidad del ADC.
  Detalle en `docs/esp32_reinicios.md` §6-8. El enlace serie de esa placa
  falla si el PC está cargado: grabar a 115200 y no compilar mientras captura.

## Estado al 08-10-2026

- Tutores asignados (IMSE-CNM). **Sus nombres no se ponen todavía en el
  repositorio ni en la memoria** (Mario, 10-10-2026). Título oficial del
  acuerdo tutor-alumno firmado el
  9-10-2026: *Diseño y caracterización de aleatoriedad de un TRNG basado
  en osciladores en anillos* / *Design and randomness assessment of a Ring
  Oscillator-based TRNG*. La memoria ya lleva la portada oficial del máster
  con ese título. Normas, calendario (entrega 16-06-2027, defensa semana
  del 28-06-2027) y lo que se entrega: **`docs/normas_tfm.md`**. Resumen
  para la reunión en `docs/resumen_reunion_tutores.md`.
- **13-10-2026: TFM publicado en Términus** con objetivo oficial (texto
  literal en `docs/normas_tfm.md`): motor de claves para ASIC, anillos a
  nivel de transistor simulados con ruido, jitter → entropía por modelo
  estocástico, integración en FPGA con ESP32, y comparar las secuencias de
  la fuente con las del ESP32. Departamento Electrónica y
  Electromagnetismo, área Electrónica. La memoria se revisa contra ese
  texto.
- **Versión en español de la memoria** (13-10-2026, para que Mario la lea):
  `memoria/tfm_main_es.tex` + `memoria/chapters_es/` (cap. 7 partido en
  `ch7_results_a/_b`), PDF `memoria/tfm_main_es.pdf`. La inglesa sigue
  siendo la de referencia hasta confirmar el idioma con los tutores.
  **Todo cambio en un capítulo inglés se traslada al español.** Trampas
  de babel spanish: opciones `es-noshorthands` (si no, TikZ se rompe) y
  `es-nodecimaldot`; decimales con coma en texto y `{,}` en fórmulas;
  `\%` fuera de las fórmulas (`$0{,}6$\,\%`), dentro da "Incompatible glue
  units". Vocabulario fijado: reto-respuesta, ruido de parpadeo, tasa de
  bits, bancos de pruebas, `Q_{\mathrm{bruto}}`, "Capítulo~/Sección~/
  Tabla~" con mayúscula.
- **Anillo con transistores reales del PDK abierto IHP SG13G2**
  (`analysis/anillo_ihp.py`, `docs/anillo_ihp.md`): el ruido inyectado sale
  del propio modelo; 5 etapas a 2,73 GHz, σ = 176,7 ± 2,0 fs por periodo
  (media de 8 realizaciones, dispersión 3,3 %; 30-10-2026, antes 180 fs de
  una sola), K_D = 981 095 (959 000 – 1 004 000), 2,79 kbit/s; con 2²⁰,
  H_∞ = 0,9853. Eso es tt a 27 °C. **Esquinas ss/tt/ff a −40/27/125 °C
  (30-10, `anillo_ihp.md` §4.2): el peor caso es el frío y la esquina
  lenta; ss a −40 °C pide K_D = 2 306 215, así que un divisor fijo para
  todo el rango es 2²² (`CFG_KD` = 22, H_∞ = 0,9995, 0,51-0,82 kbit/s);
  2²¹ se queda en 0,970.** Con V_DD ± 10 % y sf/fs a −40 °C (30-10): la
  tensión baja manda; ss a −40 °C y 1,08 V pide K_D = 3 808 445 (ocho
  realizaciones; tt/sf/fs a 1,08 V piden la mitad), 2²² da 0,9873 con solo
  un 10 % de margen, así que **con ±10 % el divisor fijo
  recomendado es 2²³** (0,9999, 0,20-0,41 kbit/s); sf/fs a −40 °C piden
  1,32 y 1,55 M. **Desapareamiento** (`--mismatch`, §4.3, 31-10): 48 chips
  en tt a 27 °C, periodo con dispersión 1,31 % (RO1 y RO2 difieren ~1,4 %),
  σ = 177,2 ± 0,7 fs y la dispersión de σ/T (2,6 %) no supera la del ruido
  solo: Q no cambia de forma medible; K_D por chip 0,87-1,09 M. En ss, −40 °C, 1,08 V (16
  chips, uno excluido por cruces espurios: `cruces_subida` no tiene
  histéresis) K_D medio 3,89 M y el peor chip 4,49 M > 2²² (H_∞ 0,973);
  2²³ lo cubre (0,9996): se mantiene 2²³ con ±10 %. ngspice
  tampoco deja fijar la semilla del sorteo. `anillo_ihp.py` y
  `anillo_ihp_repeticiones.py` admiten `--esquina`, `--temp`, `--vdd` y
  `--mismatch`; a 1,08 V cada realización tarda ~29 min.
  `spice_ring.simular()` borra su directorio temporal: `/tmp` es un tmpfs
  de 5,5 GB en RAM y los `.raw` lo llenaron.
  **ngspice 47 no deja fijar la realización de `trnoise`**
  (Wallace sembrado con `getpid()`; `rndseed`, `setseed` y
  `.options seed` no le llegan): la incertidumbre sale de repetir
  (`analysis/anillo_ihp_repeticiones.py`). Necesita ngspice 47 y
  OpenVAF-Reloaded, compilados en WSL o en Linux (`~/eda/ngspice47`,
  `~/eda/bin/openvaf-r`); el ngspice 41 de conda-forge no carga estos
  modelos. Receta en el documento.
- Contador del divisor del ERO de **20 a 24 bits** (`G_CNT_BITS`): con 20
  el K_D máximo dejaba solo un 11 % de margen. CFG_KD efectivo 0-24.
- Las notas internas de la bibliografía van en `annote` (antes `note`, y
  se imprimían en la memoria). Al añadir referencias, usar `annote`.

## Qué hay y qué está verificado

| Carpeta | Contenido | Estado |
|---|---|---|
| `docs/` | plan, arquitectura, **`mapa_registros.md`**, 4 estados del arte, resultados | cerrado |
| `analysis/` | modelo del anillo, estimadores, banco SPICE, **`ctr_drbg_ref.py`** (960 vectores CAVP), `verifica_top.py`, `consola_esp32.py` (consola serie + tramas), `campana_rng.py` (captura con el firmware del TFM_RNG, log íntegro), `entropia_90b.py` (batería SP 800-90B del NIST vía WSL), `resumen_90b.py` (tablas + ANOVA por condición), `anillo_ihp.py` (anillo con el PDK de IHP, separador térmico/1/f validado) | autovalidado |
| `rtl/` | VHDL-2008: anillo, ERO, captura, salud, I2C, AES, CMAC, CTR_DRBG, `top/motor_top.vhd` | 7 bancos pasan (`python rtl/run_tb.py`) |
| `synth/` | síntesis Yosys sobre IHP SG13G2, área en kGE | hecho |
| `firmware/verificador/` | ESP-IDF 5: maestro I2C + verificación con mbedtls, sobre `componentes/motor_i2c` | compilado (27-10, 5.3.5) y flasheado (19-09) en un ESP32 sin motor: consola, tramas `esp` con CRC ok, "sin respuesta I2C" limpio; banco en PC 0 fallos |
| `firmware/medidor/` | ESP-IDF 5, ESP32-C3: clave P-256 del motor, CSR, lecturas firmadas (`docs/lecturas_firmadas.md`) | compilado (27-10, 5.3.5); banco en PC + `verifica_lecturas.py` 0 fallos; nada en placa |
| `firmware/host_check/` | `run_host.py`: los dos firmwares contra `motor_sim.c` y mbedtls real | `results/host_check.log` |
| `memoria/` | LaTeX con la plantilla común; compila con tectonic (`results/memoria_compila.log`) | caps. 1–7 borrador (7 con la línea base del ESP32 y la fuente simulada bajo SP 800-90B) y apéndices A-C; 8 pendiente |

**Pendiente de hardware:** puesta en marcha en la Basys 3, campaña de
entropía del motor, ESP32 en el bucle con el motor. Lo que sí está hecho
sin placa: la **línea base del ESP32 bajo SP 800-90B** (5 capturas reales,
`docs/esp32_linea_base_90b.md`, `results/entropia_90b.csv`), que cierra
la mitad del objetivo O8.

## Cómo integra un ESP32 el motor (lo que le importa al otro Claude)

La especificación es **`docs/mapa_registros.md`**. Resumen:

- I2C, dirección **0x30**, puntero de registro con autoincremento,
  400 kHz, 3,3 V. Sin estiramiento de reloj: las órdenes largas
  (sembrar, generar) se lanzan escribiendo `CONTROL` (0x03) y se sondea
  `STATUS` (0x02) hasta que baje el bit `ocupado`.
- Secuencia: leer `ID` (0x00) = 0xA5 y `VERSION` (0x01) = 0x04 (vale 0x03 o mayor) → sondear
  `DIAG` (0x0E) hasta `arrancado` → `CONTROL ← sembrar` → sondear →
  comprobar `DIAG.rechazada = 0`, `sembrado` y sin alarmas →
  `CONTROL ← generar` → sondear → `DIAG.rechazada = 0` → hay clave. Reto-respuesta: escribir 16 bytes en `RETO` (0x20),
  `CONTROL ← autenticar`, sondear, leer `ETIQUETA` (0x30) y comparar con
  `mbedtls_cipher_cmac(AES-128-ECB, clave, reto)`.
- **La clave solo es legible (0x10) con el pin `modo_test` activo.** Es
  para provisionar en banco. En producto la clave no sale del chip; el
  ESP32 solo obtiene etiquetas y aleatorio.
- El hardware **rechaza** `sembrar`/`resembrar` si `CFG_KD` está por debajo
  del mínimo (genérico `G_KD_MIN`, 6 por defecto): la orden se ignora y
  `ocupado` no llega a subir. Escribir `CFG_KD` con una orden en curso se
  ignora. Ambas cosas desde el 19-09; antes eran obligaciones del maestro
  sin comprobar. Desde el 27-10 **con alarma no sale nada** (se rechazan
  sembrar, resembrar, generar y aleatorio) y no se siembra sin pasar el test
  de arranque. Toda orden ignorada o siembra abortada levanta
  `DIAG.rechazada`. Desde la versión 0x03: `capturar` solo en modo test y
  nunca durante una siembra (ni siembra durante una captura); `PETICIONES`
  se para en 2^32−1 y `DIAG.agotado` pide resembrar; `borrar_todo` (bit 7)
  zeroiza; CFG_KD arranca en 24. Detalle en `docs/mapa_registros.md`.
- Aleatorio para el host: `CONTROL ← aleatorio` (bit 6), sondear, leer
  `ALEATORIO` (0x40, 32 bytes). Es una generación del DRBG **independiente
  de la clave**. Hasta el 15-09 `generar` dejaba la clave en ese registro
  (fuga corregida en la revisión de traspaso): si ves código o notas
  antiguas que lean la clave desde ALEATORIO, están obsoletas.
- mbedtls en ESP-IDF **no trae CMAC activado por defecto**: hace falta
  `CONFIG_MBEDTLS_CMAC_C=y` (ver `firmware/verificador/sdkconfig.defaults`).
- Referencia de código: `firmware/componentes/motor_i2c/` (driver
  `i2c_master` nuevo de IDF 5, órdenes, plazos, `motor_rng()` para
  mbedtls) es la capa de acceso, reutilizable tal cual; los comandos de
  consola y las tramas al PC con CRC32 están en `verificador/main/main.c` y
  `medidor/main/main.c`. Para usar el motor como fuente de claves en un
  producto, el ejemplo es el medidor.
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
- Para editar `.tex` o `.bib` usar las herramientas Write/Edit de Claude
  Code, **nunca** `sed` en Git Bash (`\t` se vuelve tabulador) ni heredocs
  de Bash con Python dentro: la capa Bash colapsa `\\` seguido de salto de
  línea en `\`, y las filas de una tabla pierden el terminador (comprobado
  el 19-09: 100 errores "Misplaced \noalign"). `memoria/saneabib.py` sanea
  el `.bib` para pdfLaTeX. Las claves de acrónimo del paquete `acronym` no
  admiten `_`. Compilador: tectonic 0.15 en
  `%LOCALAPPDATA%\tectonic\tectonic.exe` (`cd memoria; tectonic
  tfm_main.tex`; tras un fallo borrar `tfm_main.bbl` y `tfm_main.aux`).

## Memoria de trabajo de la sesión original

Las decisiones y el porqué de cada una están en `docs/plan.md`,
`docs/arquitectura.md` (incluida la §9 sobre quitar el SHA-256),
`docs/modelo_ero_resultados.md`, `docs/sintesis_resultados.md` y
`docs/via_asic.md`. Si algo de este fichero contradice esos documentos,
mandan los documentos, que son más recientes en detalle.
