# Puesta en marcha en la FPGA: lo que se preparó sin placa y el primer día

Escrito el 08-11-2026, la víspera de tener la placa (se espera una Basys 3,
XC7A35T-1CPG236C; si es otra, ver §6). Nada de esto se ha ejecutado en
hardware. Lo que sí está probado, y con qué, se dice en cada punto.

## 1. Qué se ha añadido y cómo se ha comprobado

| Pieza | Para qué | Comprobado con |
|---|---|---|
| `rtl/fpga/medidor_frec.vhd` | frecuencímetro de un anillo: ro / 64 en su dominio, flancos contados en BCD durante 64 000 ciclos de 100 MHz (640 µs) | `tb_medidor_frec`: 10/10 (5 frecuencias con jitter ±2 %, desborde, vuelta tras desborde, display, prescaler) |
| `rtl/fpga/siete_seg.vhd` | los 4 dígitos de la placa, multiplexados | el mismo banco: un ánodo a la vez, cifras = BCD, punto en el dígito 1 |
| `basys3_top` con medidor | display = frecuencia de ro2 (sw1 abajo) o de ro1 (sw1 arriba) en MHz con un decimal; JA3 = anillo / 64 **solo en modo test**; generic `G_MEDIDOR` | `tb_basys3_top`: 4/4 con el motor y los anillos del modelo de LUT (0,3 ns por etapa): display 3333 para un periodo medido de 3,000 ns, 2381 para 4,200 ns; JA3 quieto sin modo test y a 64 × T con él. 7 min de simulación |
| `motor_top.ro_mon` | saca los dos anillos para el medidor del envoltorio | los siete bancos de antes siguen pasando (§5) |
| `build.tcl` | **faltaba `aes_enc_32.vhd`**: con `G_AES_COMPACTO = true` (por defecto) Vivado no habría elaborado. Añadidos también los dos módulos nuevos | síntesis con Yosys (abajo) |
| `basys3.xdc` | pines de sw1, JA3, display; ro1 pasa a ser reloj (del prescaler) con periodo estimado 2,0 ns | sin Vivado: solo revisado contra el XDC maestro (`plataforma_y_flujo.md` §1.5) |
| verificador: `kd [N]` y `crudo` | `kd` escribe y relee CFG_KD; `crudo` espera según el divisor (antes ~2 s fijos: con CFG_KD ≥ 12 a 300 MHz la captura no llegaba) e imprime `crudo i kd K ms M` antes de cada trama | banco en el PC, paso 13 (6 comprobaciones); el modelo tarda ahora 4096·2^kd periodos de ro2 a 300 MHz por captura |
| `analysis/campana_motor.py` | la campaña: `kd`, `crudo` por lotes, log íntegro, tramas con CRC, `kdNN.bin`, resumen y, con `--90b`, la batería del NIST | banco en el PC (paso nuevo): con el verificador compilado en el PC sobre el modelo (`consola_verificador.c`), 3 divisores, 0 CRC malos, y un log con una trama alterada da CRC malo y rc = 1. A mano: 2 × 10⁶ bits en < 1 s y `--90b` da H = 0,837 y 0,839 (el `rand()` del modelo; el techo de la batería a 10⁶ bits es 0,839 ± 0,021, `fuente_simulada_90b.md`) |
| `jitter_estimator.py --trozos` | Q_raw, exponente b y CFG_KD a partir de las capturas reales | trozos simulados de 4096 bits con Q conocida: 1,94·10⁻⁶ para 2·10⁻⁶ (−3 %) y 4,82·10⁻⁷ para 5·10⁻⁷ (−4 %); b = 1,03 y 1,21 |

**Síntesis sin Vivado** (Yosys 0.70 `synth_xilinx -family xc7`, GHDL de
OSS CAD Suite, LUT1/LUT2 como cajas negras): `basys3_top` entero da
4769 LUT, 4234 biestables, 134 CARRY4, 24 RAM64M (el buffer de captura) y
3 BUFG. El XC7A35T tiene 20 800 LUT y 41 600 biestables: **≈ 23 % y 10 %**.
Es una estimación de otra herramienta, no la de Vivado; sirve para saber
que cabe y que el VHDL elabora para Xilinx. Log en
`results/basys3_yosys_xc7.log` y receta en `synth/basys3/yosys_xc7.sh`.

**10-11, con la FIFO de la captura continua** (`G_FLUJO_BYTES = 256`):
5125 LUT (suma de LUT1-LUT6 del informe), 4292 biestables, 144 CARRY4 y
36 RAM64M: la FIFO se infiere como RAM distribuida (12 RAM64M más) y
añade 248 LUT y 58 biestables. ≈ 25 % y 10 % del XC7A35T. Ojo: con ese
mismo criterio el log anterior daba 4877 LUT, no los 4769 de arriba; no he
encontrado de dónde salía esa cifra.

## 2. Qué se espera de los anillos [ESTIMADO]

- **Frecuencia.** El XDC supone 1,4 ns para ro2 (714 MHz), que pide
  0,14 ns por etapa. Una LUT de Artix-7 -1 más el rutado local se acerca
  más a 0,3-0,6 ns por etapa: ro2 (5 etapas) entre ~170 y ~330 MHz y ro1
  (7) entre ~120 y ~240 MHz [ESTIMADO, sin fuente medida para este chip].
  Si es así, el informe de tiempos del primer bitstream saldrá **peor de
  lo real** en el dominio de ro2 (restricción más dura que la realidad).
  Se mide con el display y se corrige el XDC.
- **Jitter.** No hay cifra publicada para Artix-7; la referencia de la
  familia es 2-4 ps por periodo de 3-5 ns (Spartan-6 y Cyclone V,
  Petura 2016, `modelo_ero_resultados.md` §5). Con Q ≥ 0,2286
  (H_∞ ≥ 0,98) y Q_raw = (σ/T)²:

  | σ / T | Q_raw | K_D | CFG_KD |
  |---|---|---|---|
  | 4 ps / 3 ns = 1,3·10⁻³ | 1,8·10⁻⁶ | 1,3·10⁵ | 17 |
  | 4 ps / 5 ns = 8,0·10⁻⁴ | 6,4·10⁻⁷ | 3,6·10⁵ | 19 |
  | 2 ps / 3 ns = 6,7·10⁻⁴ | 4,4·10⁻⁷ | 5,1·10⁵ | 19 |
  | 2 ps / 5 ns = 4,0·10⁻⁴ | 1,6·10⁻⁷ | 1,4·10⁶ | 21 |

  **CFG_KD de partida: entre 17 y 21.** Ojo: `modelo_ero_resultados.md`
  §5 decía "K_D entre 3·10⁴ y 5·10⁵" para el mismo rango; su extremo bajo
  sale de σ/T = 2,8·10⁻³, fuera de 2-4 ps / 3-5 ns. Con el cálculo de la
  tabla el rango es 1,3·10⁵-1,4·10⁶. El valor bueno lo da la medida (§3,
  paso 5), no esta tabla. En FPGA, además, el jitter relativo de dos
  anillos incluye el de los dos y el acoplamiento por la alimentación.

## 3. Checklist del primer día

Cada paso dice qué se mira y cuándo se da por bueno. Los logs, enteros.

1. **Identificar la placa.** Modelo y referencia serigrafiada del chip. Si
   no es XC7A35T-1CPG236C, parar y ver §6.
2. **Bitstream** (Windows, `docs/instalacion_vivado_windows.md` §5):
   `cd synth/basys3; vivado -mode batch -source build.tcl -log build.log`.
   Leer completos `build.log`, `util_hier.rpt` (u_ro1 = 7 LUT, u_ro2 = 5
   LUT: si faltan, la síntesis ha tocado los anillos), `drc.rpt` (LUTLP-1
   como aviso, nada más), `method.rpt` y `timing.rpt`. Con el periodo
   estimado de ro2 es probable que el dominio de ro2 no cierre: anotarlo,
   no arreglarlo todavía.
3. **Grabar** (`-tclargs programar` o `openFPGALoader -b basys3`). Bueno
   si: ld15 parpadea (~0,7 s), el display marca una frecuencia y sw1 la
   cambia (ro1 < ro2). Anotar las dos lecturas, la temperatura de la sala
   y repetir a los 5 y a los 30 min. **Resolución del display: 0,1 MHz
   (±1 cuenta) más ±50 ppm del oscilador de placa**; variaciones de una
   cuenta no son tendencia. Si marca `----`, el anillo pasa de 999,9 MHz.
   Con osciloscopio, JA3 en modo test da el anillo / 64 (contraste).
4. **XDC con la frecuencia real.** Cambiar `-period` de ro2_clk y ro1_clk
   al medido con un 10 % de margen, repetir el paso 2 y leer el tiempo del
   dominio de ro2. El contador de 24 bits del ERO va a la frecuencia del
   anillo: si no cierra, es un problema real (bits del divisor erróneos) y
   hay que decidir cómo partirlo antes de medir entropía.
5. **ESP32 en el bus.** JA1 = SCL (GPIO22 del ESP32 clásico), JA2 = SDA
   (GPIO21), masa común, pull-ups de 2,2-4,7 kΩ a 3,3 V; el ESP32 no
   alimenta la placa ni al revés. Verificador normal (sin
   `MOTOR_SIMULADO`). `id` debe dar `id 0xa5 version 0x04`; sw0 arriba,
   `test=1`.
   **Test de arranque:** tras el reset CFG_KD = 24. Con ro2 a 300 MHz un
   bit tarda 56 ms y la ventana de 1024 bits ~57 s. Desde el 08-11 los
   plazos de `sembrar` salen del CFG_KD del motor (§7): con 24 espera hasta
   687 s y lo dice (`sembrar: esperando el test de arranque (hasta 687 s)`);
   con una alarma levantada se rinde enseguida. Para no esperar, `kd 18`
   antes (≈ 0,9 s por ventana a 300 MHz).
6. **Jitter (modo medida).** `kd 0` y unas 2000 capturas:
   `python analysis/campana_motor.py --puerto /dev/ttyUSB0 --kd 0 --bits 8192000`
   (2000 trozos; ~4 min de serie a 115 200 baudios) y
   `python analysis/jitter_estimator.py --trozos results/motor_campana/<sesion>/kd00.bin --kd-captura 0`.
   Da Q_raw por periodo de ro2, el exponente b y el CFG_KD para
   H_∞ ≥ 0,98. **Si b se acerca a 2**, manda el flicker o el jitter
   global y el divisor no puede subir sin más (`modelo_ero_resultados.md`
   §6). Las medias por distancia M van en la salida: guardarla entera.
   Repetir con kd 2 para ver que Q escala con 2^kd.
7. **Campaña de entropía.** Con el CFG_KD del paso 6 (K*), barrer
   K* − 6, K* − 4, K* − 2, K* y K* + 2, 10⁶ bits cada uno, con `--90b`
   **y `--flujo`** (desde el 10-11: 10⁶ bits consecutivos, como pide SP
   800-90B; `captura_continua.md`). El flujo sirve desde CFG_KD 13-14; si
   K* − 6 queda por debajo, ese divisor va por trozos (sin `--flujo`) y se
   dice. Antes de la campaña, una tira corta (`--bits 100000`) para ver que
   no desborda ni hay errores de bus. Tiempo por divisor con ro2 a 300 MHz
   [ESTIMADO]: kd 14 ≈ 1 min, 16 ≈ 4 min, 18 ≈ 15 min, 20 ≈ 1 h,
   22 ≈ 4 h, 23 ≈ 8 h. **Lo informativo son los divisores bajos**: a 10⁶
   bits la batería se satura en 0,839 ± 0,021 y no distingue nada con
   H_∞ ≥ 0,97 (`fuente_simulada_90b.md`); donde el modelo predice
   H_∞ < 0,8 la batería sí puede contradecirlo. La comparación la hace
   `analysis/compara_modelo_campana.py --campana <sesion> --jitter
   <sesion>/kd00.bin` (§8): tabla, figura y un veredicto por divisor.
8. **El medidor no debe tocar la fuente.** Repetir el paso 6 y un punto
   del 7 con `G_MEDIDOR = false` (`synth_design ... -generic G_MEDIDOR=false`
   en `build.tcl`). Si Q o H cambian más que la dispersión entre
   repeticiones, el prescaler de ro1 (carga y ruido de conmutación junto
   al anillo) altera la medida y la campaña se hace sin él.
9. **Motor completo.** `sembrar`, `generar`, `reto 20` (20 aciertos con
   el CMAC de mbedtls), `aleatorio 10`, `cero`. Es la integración
   FPGA + ESP32 del objetivo oficial.

## 4. Limitaciones que hay que decir al escribirlo

- **Los trozos no son contiguos** (resuelto el 10-11 con la captura
  continua, `captura_continua.md`; lo que sigue vale para las capturas por
  trozos, que siguen siendo las del jitter). Cada `crudo` da 4096 bits seguidos;
  entre trozos se pierden los bits que llegan mientras el ESP32 lee el
  buffer y los manda al PC (~0,1 s). SP 800-90B §3.1.1 pide 10⁶ muestras
  **consecutivas**: aquí son 245 bloques de 4096. Las dependencias dentro
  de 4096 bits se ven; una deriva lenta (1/f, temperatura) entre bloques
  queda en parte cortada. Para el estimador de jitter es al revés: los
  trozos independientes son lo que pide (`trng_capture.vhd`). Si hiciera
  falta una tira continua, el buffer tendría que vaciarse más rápido de
  lo que se llena (posible a CFG_KD ≥ ~10 con I2C a 400 kHz) con un modo
  de captura continua en el RTL: hecho el 10-11 (registro FLUJO, motor
  0x04), sin probar en placa.
- La frecuencia que `campana_motor.py` deduce del tiempo de llenado
  (`f_ro2_MHz`) tiene la resolución del tick del ESP32 (1 ms) más el
  sondeo; solo se calcula con capturas de ≥ 100 ms. La buena es la del
  display.
- La entropía medida es la del ERO **en FPGA**. El divisor del ASIC sale
  del modelo con el jitter IHP (`anillo_ihp.md`), no de esta campaña.

## 5. Estado de los bancos tras estos cambios

- GHDL 5.0.1 (mcode): `tb_medidor_frec` 10/10, `tb_basys3_top` 4/4, los
  siete de antes sin cambios en su código; los nueve en
  `results/run_tb_todos.log`. En la CI (GHDL 4.1) `tb_basys3_top` no
  analizaba: `wait on` sobre el alias de un nombre externo; ahora copia los
  anillos a una señal del banco en un bloque tras `dut`.
- `run_host.py` con mbedtls de ESP-IDF 5.3.2: 0 fallos (`results/host_check.log`).
  Con GCC 15 hubo que pasar `MBEDTLS_FATAL_WARNINGS=OFF` al compilar
  mbedtls: la parte TLS, que no se usa, tiene avisos nuevos en GCC 15.
- Verificador compilado con ESP-IDF 5.3.2 en el Linux (`kd`, `crudo` y los plazos según CFG_KD): sin avisos del compilador, `results/verificador_build_esp32_idf532.log` (incremental sobre la compilación completa anterior). El medidor (esp32c3) no se compila en este PC: falta la toolchain `riscv32-esp-elf`; lo compila la CI.

## 6. Si la placa no es una Basys 3

- **Basys 2 (Spartan-3E XC3S100E)**: lo que pasó el 14-11-2026. El motor
  entero no cabe: variante de solo fuente, ISE 14.7 vía GHDL → Verilog.
  Todo en `docs/basys2.md`.

- **Otra AMD de la serie 7** (Arty A7, Nexys A7, Cmod A7...): mismo
  flujo; cambian `set part` en `build.tcl`, los pines del XDC, las
  coordenadas de `ro_pblocks.xdc` y el envoltorio si no hay display (el
  frecuencímetro puede ir a LEDs en binario o solo a un pin).
- **Intel/Lattice/Gowin**: `ring_osc.vhd` es el único módulo atado a la
  tecnología (LUT1/LUT2 de Xilinx); habría que escribir su equivalente,
  restricciones nuevas y otra herramienta (Quartus, o el flujo libre de
  OSS CAD Suite para Lattice/Gowin).

## 7. Plazos del firmware según CFG_KD (08-11)

`T_ARRANQUE_MS` (30 s) y `T_SIEMBRA_MS` (40 s) estaban calculados para el
anillo del integrado (~700 MHz en la cuenta de entonces). En la FPGA, con
ro2 a 170-330 MHz [ESTIMADO] y CFG_KD = 24, el test de arranque tarda
~1 min y `sembrar` fallaba por plazo. Ahora `motor_i2c` lee CFG_KD y
calcula el plazo de `bits` bits como `bits · 2^CFG_KD / 100 MHz · 2`
(`motor_plazo_bits_ms`), con los valores de antes como mínimo:

| Espera | Bits | CFG_KD 24 | CFG_KD 18 | CFG_KD ≤ 13 |
|---|---|---|---|---|
| test de arranque | 2 × 1024 (la ventana a medias y una entera) | 687 s | 30 s (mínimo) | 30 s |
| siembra | 384 + 2 × 1024 | 816 s | 40 s (mínimo) | 40 s |
| captura (`crudo`) | 4096 | 1374 s | 21,5 s | 2 s |

100 MHz es un suelo para ro2, no una estimación: el plazo solo se agota
si algo va mal. Para que un fallo no cueste diez minutos,
`motor_esperar_arranque` se rinde en cuanto STATUS tiene una alarma (con
alarma el test no pasa hasta `borrar`). Banco en el PC: paso 8 (con alarma,
`sembrar` se rinde en < 1 s) y paso 14 (el modelo con el arranque de una
ventana a 300 MHz y CFG_KD = 24: siembra en 57,3 s, más que los 30 s del
plazo fijo). El modelo solo hace el arranque lento si el banco lo pide
(`motor_arranque_lento`), para que el firmware simulado en placa o QEMU no
tarde un minuto en arrancar.

## 8. Modelo frente a campaña

`analysis/compara_modelo_campana.py` toma el `resumen.csv` de la campaña
(con `--90b`) y Q_raw (medido de `kd00.bin` o dado) y, por divisor, compara
la cifra de SP 800-90B **no con H_∞ del modelo, sino con lo que da la
batería para bits del propio modelo con esa H_∞**: la calibración de
`results/fuente_simulada_90b.csv` (tres casos IHP × tres semillas, 10⁶
bits). Hace falta porque la batería no es una cota: se satura en ~0,84,
con poca entropía sobreestima (H_∞ ≈ 0 → 0,07-0,11) y en medio da algo
menos que el modelo (0,854 → 0,75-0,78). La banda es el mínimo y máximo de
la calibración, ensanchada por la incertidumbre de Q_raw (10 % por
defecto) y una tolerancia de 0,03. Veredictos: compatible, por debajo
(menos entropía de la que el modelo da con esa Q_raw), por encima, y
saturada (H_∞ ≥ 0,97: se informa, no se juzga). Escribe
`compara_modelo.csv` y `compara_modelo.png` en la carpeta de la sesión.

Prueba (`analysis/prueba_compara_modelo.py`, 0 fallos, 40 s): campaña
simulada con Q_raw = 2,4·10⁻⁷, 245 trozos de 4096 bits con fase
independiente por divisor (17-21) y `kd00.bin` de 3000 trozos.
`jitter_estimator` recupera 2,285·10⁻⁷ (−4,8 %). Con ese valor: 17, 18 y
19 compatibles (batería 0,323 / 0,509 / 0,764 frente a 0,313 / 0,496 /
0,743 esperados) y 20-21 saturados. Diciendo 4 veces más jitter del real,
solo el 17 sale "por debajo": los demás ya están saturados. **Por eso la
campaña necesita divisores bien por debajo de K*.** Diciendo 4 veces
menos, los cinco salen "por encima". Los trozos de 4096 bits con fase
independiente dan lo mismo que la secuencia continua de la calibración.

## 9. Lecciones de la Basys 2 para la Basys 3 (14-11-2026)

Lo que salió en la placa real con la Basys 2 (`docs/basys2.md`) y cambia
esta checklist:

1. **Comprobar que los anillos existen en la netlist implementada.** En la
   Basys 2 XST conservó las LUT1 y map las colapsó (la NAND quedó
   realimentada consigo misma; el display marcaba 000.0). En Vivado el
   `DONT_TOUCH` llega a la implementación, pero se comprueba igual: tras
   `route_design`, `get_cells -hier -filter {NAME =~ *u_ro*}` debe dar
   N+1 LUT por anillo y el lazo cerrado.
2. **Los anillos compactos van más deprisa.** Al colocarlos en un CLB, ro2
   pasó de 167,8 a 204,8 MHz y superó lo que aguantaba el contador de
   `ero_core`. Las frecuencias se miden después de fijar los pblocks, y el
   periodo de `ro2_clk` del XDC se ajusta a lo medido (paso 4). Si no
   cierra, los genéricos `G_ETAPAS_RO1/RO2` alargan los anillos.
3. **El display modula los anillos.** Con el display multiplexado el ν de
   cada trozo era bimodal y el modelo dejaba residuos 45 veces el ruido;
   apagado, ~7. Para las capturas de entropía, display apagado: añadir a
   `basys3_top` un genérico como `G_QUIETO` de `basys2_top`. Y lo que cuelga
   de los anillos (el frecuencímetro) cambia su ruido de fase relativo (×2,5
   en la Basys 2): la campaña se hace con la variante que se va a defender, y
   se dice cuál.
4. **El estimador por varianza no vale a divisores altos.**
   `jitter_estimator.py` necesita M ≫ N y M·Q diminuto (`kd 0`). En la
   Basys 3 hay buffer de captura y `kd 0` es posible, así que vale; pero
   como contraste, y para cualquier medida a `kd` > 0, usar
   `analysis/jitter_autocorrelacion.py` (ajuste de c(M) con el modelo del
   ERO, `--conjunto` para un ν por trozo) sobre trozos de
   `analysis/flujo_desborde.py`. Los dos están validados con bits
   simulados de Q conocida (`results/jitter_autocorrelacion_autotest.log`).
5. **Repetibilidad antes que conclusiones.** Tres capturas de la misma
   variante dieron ±3-5 % en Q; sin eso no se puede atribuir una diferencia
   entre variantes al diseño.
6. **El flujo a 115 200 baudios sirve desde `kd 12`** con ro2 ~143 MHz (con
   ro2 más rápido, un divisor más). Por debajo, `flujo_desborde.py`.
7. **Contraste cruzado.** La batería SP 800-90B solo informa por debajo de
   K\*; en la Basys 2 `kd 12` cayó donde predecía el modelo con la Q medida y
   no con la de otra variante. Repetirlo: es la prueba de que el estimador
   de jitter y la batería cuentan lo mismo.

