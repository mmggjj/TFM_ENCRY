# Revisión independiente del RTL: commits 9f86162 y c9dc7d6 (22-11-2026)

Alcance: `git diff fc7452b c9dc7d6` (anillos 11/13, preescalador de ro2
`G_PRESC_RO2`, `G_KD_MIN`/`G_KD_RESET`/`G_KD_MAX` 25/25/26, rechazo de
`CFG_KD` > máximo, envoltorios de FPGA, bancos, firmware, `build.tcl` y XDC).
HEAD (7b3704e al empezar; 46660d6 al acabar) no cambia nada de `rtl/`,
`firmware/` ni `synth/` respecto a c9dc7d6; los números de línea de
`docs/mapa_registros.md` son los de 46660d6. Nada del repositorio se ha modificado salvo esta carpeta; los
mutantes y las copias del firmware se hicieron en `/tmp/claude-1000/revision_rtl/`.

Herramientas: GHDL 5.0.1 de apt (`/usr/bin/ghdl`, mcode), un banco cada vez.
Todo lo que sigue es **SIMULADO** (GHDL o modelo en PC) o **RAZONADO** (lectura
del código); nada medido en placa.

## Requisito central: ventana de 2^CFG_KD periodos de ro2

Banco propio `tb_rev_ventana.vhd` (en esta carpeta): `motor_top` del
repositorio sin tocar, valores por defecto (presc 4, mín 25, reset 25, máx 26)
con anillos de 3 etapas para acelerar; escribe `CFG_KD` por I2C, para el
reloj de sistema y cuenta flancos de subida de `ro2` entre dos muestras
válidas (flanco de `ro2c` con `u_ero.tic` a 1, que es la muestra que sale por
`bit_stb` dos flancos después).

| CFG_KD | periodos de ro2 entre muestras | ¿= 2^CFG_KD? |
|---|---|---|
| 0, 1, 2, 3 | 16 (dos ventanas cada uno) | **no**: 2^4 (hallazgo 3) |
| 4 … 19 | 2^CFG_KD exacto (dos ventanas cada uno) | sí |
| 20 … 26 | no simulable entera (~8 000 periodos de ro2 por segundo de CPU; 2^26 serían horas) | ver abajo |

Para 17-26 `tb_rev_mascara.vhd` comprueba `kd_ero` = CFG_KD − 4, que
`mascara` tiene CFG_KD − 4 unos (22 unos, todo el contador, con 26: el
`shift_left` desborda a 0 y la resta da todo unos, como debe) y que `tic`
salta con la cuenta a 2^kd_ero − 1 y no con 2^(kd_ero−1) − 1 (cuenta forzada
con `force`). 0 fallos en 0-26. Con lo anterior (cuenta +1 por cada 16
periodos de ro2, medido de 4 a 19) la ventana es 2^CFG_KD exacta de 4 a 26.
Logs: `tb_rev_ventana_kd0-16.log`, `tb_rev_ventana_kd17-20_parado.log` (17-19
completos, parado en 20 por tiempo) y `tb_rev_mascara.log`.

**Sembrar por debajo de `G_KD_MIN`: no es posible.** La condición de
`sembrar`/`resembrar` y la de FLUJO comparan `kd_sel` (el valor que de verdad
usa el ERO a través de `kd_ero`) con `G_KD_MIN`; con `kd_sel` ≥ 25 la ventana
es exactamente 2^kd_sel. Ni el truncado del hallazgo 2 ni el suelo del
hallazgo 3 lo cambian: el primero produce un `kd_sel` real y el segundo solo
alarga ventanas (dirección segura para la entropía).

## Hallazgos

### 1. [MEDIO, el más importante] El medidor no puede sembrar con el motor por defecto

- `firmware/medidor/main/main.c:57` `#define CFG_KD_SIEMBRA 24` y
  `main.c:121` lo escribe antes de `sembrar`. Con el motor por defecto
  (`G_KD_MIN` 25) `sembrar` se rechaza siempre: el medidor, que es "el
  ejemplo para usar el motor como fuente de claves en un producto", nunca
  tiene clave en el integrado. Falla cerrado (no hay riesgo de seguridad),
  pero el producto no funciona. En la Basys 3 (mín 19, máx 24) sí funciona,
  por eso no se ha visto.
- El banco en PC no lo puede ver: `firmware/host_check/motor_sim.c:125`
  `KD_MIN 6` ("el del banco"), cuando el RTL por defecto va a 25.
- **Comprobado (SIMULADO, modelo en PC):** copia del firmware con `KD_MIN 25`
  en el modelo; `test_medidor` da 30 fallos, todos por
  `sembrar: RECHAZADA por el motor` (`test_medidor_kdmin25.log`). El
  `run_host.py` completo con el mismo cambio (`run_host_kdmin25.log`) muestra
  además que el banco del verificador está escrito con `kd 7`, y por tanto
  tampoco ejercita nunca el mínimo real (36 fallos esperables; el verificador
  en sí no escribe `CFG_KD` antes de sembrar y usaría el 25 de reset).
- También `motor_rearmar()` (componente) reutiliza el `CFG_KD` que haya: en
  el medidor seguiría en 24 y el rearme se rechazaría.
- Arreglo sugerido: que el medidor no escriba `CFG_KD` (el de reset ya es el
  caracterizado) o que escriba `max(CFG_KD_SIEMBRA, leído)`; y una pasada del
  banco en PC con el `KD_MIN` del RTL por defecto.

### 2. [MEDIO] `CFG_KD` ≥ 32 no se rechaza: se trunca a 5 bits y se acepta

- `rtl/top/motor_top.vhd:607-611`: la comprobación es
  `to_integer(unsigned(reg_wdato(4 downto 0))) <= G_KD_MAX`, sobre los 5 bits
  bajos. Escribir 32 deja `CFG_KD` = 0, 33 → 1, …, 57 → 25, sin
  `DIAG.rechazada`.
- Contradice `docs/mapa_registros.md:16` ("Escribir un valor mayor que
  `G_KD_MAX` se ignora y levanta `DIAG.rechazada`") y el modelo
  (`motor_sim.c:386` compara el byte entero y rechaza 32). El banco en PC solo
  prueba 27 (`test_verificador.c:186`) y `tb_motor_top` solo 27.
- **Comprobado (SIMULADO):** `tb_rev_ventana_kd0-16.log`: 27-31 se rechazan
  (se lee 25); 32-40 se leen 0-8.
- No permite sembrar por debajo del mínimo (ver arriba) ni lo usa el firmware
  (`cmd_kd` limita a 0-26). Arreglo: comparar `unsigned(reg_wdato)` entero.

### 3. [MEDIO] `CFG_KD` 0-3 se aceptan y se releen, pero la ventana es 2^4

- `rtl/top/motor_top.vhd:285-286`: con `kd_sel` < `G_PRESC_RO2`, `kd_ero` = 0
  y la ventana es 16 periodos de ro2 sea cual sea `CFG_KD`. El registro se
  relee con el valor escrito. **Comprobado (SIMULADO)**: 16 periodos para
  `CFG_KD` 0, 1, 2 y 3.
- `docs/mapa_registros.md:16` lo dice ("por debajo de 4 el divisor efectivo
  es 2^4"), pero no se ha propagado: `mapa_registros.md:294` (también tras
  46660d6) sigue diciendo que `trng_capture` "admite cualquier K_D, incluido 1";
  `ero_core.vhd` (cabecera) presenta K_D pequeño como el modo de medida de
  jitter; el modelo (`motor_sim.c:338-340`) y el plazo de `crudo` del
  verificador (`main.c:293`) usan 2^kd; y las tramas `crudo i kd K` /
  `jitter_estimator.py --kd-captura K` etiquetarían una captura a `CFG_KD`
  0-3 con un divisor 2^(4−K) veces menor que el real, es decir, una Q por
  periodo de ro2 equivocada en ese factor.
- Consecuencia de diseño: en el integrado desaparece la medida de jitter
  embebida con K_D 1-8, que era una de las razones del ERO (cabecera de
  `ero_core.vhd`). En la FPGA (presc 0) no pasa.
- Arreglo sugerido: rechazar `CFG_KD` < `G_PRESC_RO2` con `DIAG.rechazada`
  (igual que > máximo), o releer el efectivo; y corregir los documentos.

### 4. [MENOR] `DIAG.rechazada` y las escrituras de `CFG_KD`

- Una escritura de `CFG_KD` rechazada sube `rechazada`, pero una escritura
  válida posterior no la baja (solo la baja una orden aceptada), y una
  escritura ignorada por orden en curso o flujo activo no la sube
  (`motor_top.vhd:606-612`). **Comprobado (SIMULADO):** tras escribir 0x1F y
  luego 25, `DIAG.rechazada` = 1.
- La tabla de DIAG (`mapa_registros.md:60`) solo habla de órdenes de CONTROL
  y de FLUJO; no menciona el caso de `CFG_KD`. Un maestro que escriba
  `CFG_KD` y mire `DIAG` para saber si se aceptó no puede distinguirlo; el
  firmware actual relee `CFG_KD` (correcto) y no se ve afectado.

### 5. [MENOR] La restricción de tasa del cruce de dominio ya no es K_D ≥ 64

- Con el preescalador, el origen de `bit_cdc` corre a ro2/16 (10,6-23 ns con
  los periodos de ro2 de 13 etapas, 0,66-1,46 ns [SIMULADO, commit 9940210]),
  más lento que el reloj de sistema. `bit_cdc` pide ≥ 8 ciclos de destino por
  bit: 2^CFG_KD · T_ro2 ≥ 80 ns → **`CFG_KD` ≥ 7** en el integrado (antes 6
  con ro2 a ~700 MHz). RAZONADO.
- No afecta a semilla ni a FLUJO (mínimo 25), pero los tests de salud reciben
  siempre `bit_s`: a `CFG_KD` < 7 ven una tira con bits perdidos en silencio.
- Mientras se hacía esta revisión entró el commit 46660d6, que ya corrige la
  sección "Restricción de tasa" de `mapa_registros.md` (CFG_KD ≥ 7). Siguen
  desactualizados `mapa_registros.md:251` ("necesita `CFG_KD >= 6` (K_D >=
  64)"), `mapa_registros.md:294` ("admite cualquier K_D, incluido 1", ver
  hallazgo 3) y la cabecera de `bit_cdc.vhd` ("Con K_D >= 64 se cumple").

### 6. [MENOR] Ningún banco comprueba la longitud de la ventana

`tb_ero_core` solo exige un mínimo de bits (> 1000/2^kd en 400 µs) y
`tb_motor_top` no mide la ventana, aunque su comentario dice "el
preescalador se prueba aquí". Mutante en copia
(`motor_top_mutante_ventana.vhd`: `kd_ero <= kd_sel - (G_PRESC_RO2 + 1)`,
es decir, ventana de 2^(CFG_KD−1), la mitad del jitter acumulado),
`tb_motor_top` del repositorio sin tocar (log
`tb_motor_top_mutante_ventana.log`, **SIMULADO**):

- Los pasos 1 a 9b pasan **todos** (`[ok ]` en las 88 comprobaciones que
  llegan a imprimirse, incluidas siembra, clave, capturas y rechazos).
- La simulación se queda colgada en el paso 9c, el bucle
  `while total < 400 loop leer_flujo; end loop;`
  (`tb_motor_top.vhd:684-686`), a 19,0 ms simulados; la paré tras 69 min de
  CPU (rc 143). Explicación probable (RAZONADA, no comprobada con sondas): a
  `CFG_KD` 7 el mutante saca los bits al doble de tasa, la FIFO de 64 bytes
  se desborda, el flujo se para solo y `total` no llega nunca a 400.
- O sea, el banco solo "caza" este mutante por un efecto lateral del caudal
  del flujo, y lo hace colgándose (sin plazo en ese bucle; `run_tb.py` lo
  cortaría a las 2 h), no con un `[FALLO]`. Un mutante que **alargue** la
  ventana (p. ej. `kd_sel − 3`) no cambiaría ningún resultado del banco, y
  uno que la acorte solo por debajo de `CFG_KD` 7 tampoco.
- Sugerencia: una comprobación directa en `tb_motor_top` como la de
  `tb_rev_ventana.vhd` (flancos de `ro2` entre muestras con `tic`, para dos o
  tres `CFG_KD`, incluido uno < 4) y un plazo en el bucle de 9c.

### 7. [NOTA] Firmware y scripts con el 24 antiguo

- `firmware/verificador/main/main.c:286,293`: `crudoq` limita a 24 el `kd`
  con que calcula la espera callada. Inofensivo: supone 10 ns por periodo de
  ro2 y en el integrado (0,66-1,46 ns [SIMULADO]) la espera para 24 sigue siendo
  mayor que la captura real a 25-26; en la Basys 3 el máximo es 24.
- `analysis/campana_motor.py:392-393` rechaza `kd` > 24: correcto para la
  Basys 3, no para el integrado (25-26).

### 8. [NOTA] Comentarios y documentos desactualizados

- `CLAUDE.md:983` ("`G_KD_MIN`, 6 por defecto") y `CLAUDE.md:992` ("CFG_KD
  arranca en 24"), en la sección para quien integre un ESP32.
- `rtl/fpga/basys3_top.vhd:31` "El integrado sigue con 5/7" (ahora 11/13).
- `rtl/tb/tb_motor_top.vhd:414,658` "K_D = 4 < mínimo (16)": con el
  preescalador `CFG_KD` 2 da K_D efectivo 16, igual que el mínimo del banco;
  la prueba sigue siendo válida (el rechazo es por el valor del registro).
- `firmware/medidor/main/main.c:56` "del rango caracterizado" (ver 1).

### 9. [NOTA] El preescalador en el integrado

- No hay SDC para el flujo de integrado: `ro2c` es un reloj generado en
  cascada (`div(1..4)` son relojes) y haría falta
  `create_generated_clock -divide_by 16` (o uno por etapa), grupos asíncronos
  clk/ro2c y comprobar con STA los 1,53 ns [ESTIMADO, ABC] y el primer
  biestable a 0,7-1,5 GHz (periodo de ro2 0,66-1,46 ns [SIMULADO], frente a
  ~0,37 ns que necesita [ESTIMADO, biblioteca típica, sin esquina lenta]). Hoy `sintetiza.py` no hace STA.
- Los instantes de muestreo pasan por cuatro clk→Q de la cadena: su ruido es
  entropía extra y su sensibilidad a la alimentación es modulación
  determinista; ninguna de las dos está en el SPICE de los anillos.
- `kd_ero` es combinacional sobre `kd_sel` (dominio clk) y entra sin
  sincronizar en la máscara del dominio ro2c (antes entraba `kd_sel`
  directo). Un cambio puede dar una ventana espuria, solo al cambiar
  `CFG_KD`, que exige motor libre y sin flujo. RAZONADO.

### 10. [NOTA, anterior a estos commits] Primera ventana tras cambiar `CFG_KD`

`ero_core` no reinicia `cuenta` al cambiar `kd_sel`: la primera muestra tras
el cambio llega tras menos de 2^CFG_KD periodos (de 1 a 2^CFG_KD). Si el
maestro escribe `CFG_KD` y siembra enseguida, a lo sumo un bit de 512 tiene
menos jitter. Además `CFG_KD` puede cambiarse con una `capturar` en curso
(solo lo bloquean orden y flujo): ese trozo mezcla dos divisores. Ninguno de
los dos viene de estos commits.

## Revisado sin encontrar fallo

- **Reset y liberación en el dominio dividido** (RAZONADO): `rst_n` baja
  `div` (por `rst_n_r2`, sincronizado con ro2) y `rst_n_ro` asíncronamente;
  al soltar, `en_anillos` arranca ro2, `rst_n_r2` se suelta en un flanco de
  ro2 y el primer flanco de `div(1)` llega un periodo entero después
  (recuperación de un periodo para `div(1)`; `div(2..4)` se relojan después);
  `ro2c` sale de un biestable, sin glitches; `u_rst_ro` se suelta tras dos
  flancos de `ro2c`. Sin anillo no hay reloj y el dominio queda en reset, como
  antes.
- **Cruces ro2/16 → clk**: `bit_cdc` (conmutación + 3 biestables) y
  `trng_capture` (conmutación en los dos sentidos) no dependen de que el
  origen sea más rápido que el destino; `arranca` es un nivel conmutado y
  `cap_en_curso` no cambia. Solo la tasa (hallazgo 5).
- **Captura, flujo y salud**: mismos bits del ERO; con `CFG_KD` ≥ 4 el
  significado es el mismo (ventana 2^CFG_KD). FLUJO y siembra comparten el
  mínimo y no se puede cambiar `CFG_KD` con el flujo activo.
- **Anchos**: contador de `G_KD_MAX − G_PRESC_RO2` = 22 bits; `kd_ero` 5 bits;
  máscara a todo unos con 26 (simulado); `kd_sel` nunca supera `G_KD_MAX`
  (reset por aserción, escritura por el rechazo, salvo el truncado del
  hallazgo 2, que da 0-31 y se compara igual). Firmware: `bits << 26` en
  `uint64_t` sin desbordar; plazo de arranque a `CFG_KD` 26 = 2 749 s, siembra
  3 436 s, dentro de `uint32_t` en ms.
- **Reset 25 y rango 0-26** en RTL (simulado: se lee 25 tras el reset; 26 se
  acepta; 27-31 se rechazan con `DIAG.rechazada`), en `motor_sim.c` y en
  `MOTOR_KD_MAX` del componente. Basys 3 19/19/24 y Basys 2 7/24/24, ambos
  sin preescalador, cumplen la aserción `MIN ≤ RESET ≤ MAX ≤ 31`.
- **`build.tcl`**: la comprobación corre tras rutar y antes del bitstream; en
  `synth/basys3/build/build_quieto_1911_14016.backup.log` paró con
  4,407 > 4,392 ns (contador de 26 bits) y en `build_quieto_1911.log` pasó con
  3,976 ns. `REQUIREMENT − SLACK` es el periodo mínimo del camino (incluye
  setup, incertidumbre y sesgo de reloj), comparado en la esquina lenta con el
  periodo medido: conservador. Matices sin efecto hoy: el `string match`
  distingue mayúsculas (`G_QUIETO=TRUE` solo avisaría) y con `SIN_BEL=1` ro2 va
  más lento que 4,88 ns, así que el límite sobra. El pin del reloj
  (`g_inv[10]`) corresponde a ro2 de 11 etapas en `basys3_top`.
- Los bancos del repositorio no se han vuelto a correr enteros (orden de no
  saturar la máquina); `results/run_tb_todos.log` es de 9f86162 y c9dc7d6 solo
  cambia comentarios de los bancos y valores por defecto que los bancos fijan.
