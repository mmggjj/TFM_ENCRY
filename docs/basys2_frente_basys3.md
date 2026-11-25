# Basys 2 frente a Basys 3

Comparación de las dos placas en las que se ha probado la fuente (22-11-2026).
No hay medidas nuevas: todo sale de `docs/basys2.md`, `docs/basys3.md`,
`docs/puesta_en_marcha_fpga.md` §9, `docs/decisiones_pendientes.md` y de
`results/`. Cuando un número es un cálculo de este documento a partir de
cifras medidas, se dice ("cálculo aquí"). Si dos fuentes discrepan, está en
§7.

Convenciones: [MEDIDO] en placa, [SIMULADO], [ESTIMADO]. `kd N` es
`CFG_KD = N` (`K_D = 2^N` periodos de ro2 por bit). "Q" es la varianza de
fase relativa entre ro1 y ro2 acumulada por periodo de ro2, en ciclos de ro1
al cuadrado (la que usa `jitter_autocorrelacion.py`).

Resolución de los instrumentos:

- Display de las dos placas: ±0,1 MHz de lectura (una cuenta en 640 µs).
  Escala: en la Basys 2, ±2 % (el reloj de 50 MHz se comprobó con LED y
  cronómetro); en la Basys 3, ±50 ppm del oscilador de 100 MHz.
- Frecuencia por la duración de un flujo: la duración la da el ESP32 en pasos
  de 10 ms hasta el 18-11 por la tarde (`CONFIG_FREERTOS_HZ=100`,
  `docs/basys3.md` "Hallazgo del firmware"); ±0,12 % a `kd 13`. Que las
  medidas de la Basys 2 (14-16-11) tuvieran la misma resolución es una
  inferencia (mismo verificador, mismo `sdkconfig` del 29-10), no
  comprobado.
- Repetibilidad de Q (misma variante, capturas seguidas): ±3-5 % en la Basys 2
  con el ajuste conjunto; ±0,3-4 % en la Basys 3 con los dos ajustes de
  autocorrelación, ±10-25 % con el estimador por varianza (§3.1).

---

## 1. Resumen

**Qué es cada placa.** La **Basys 2** lleva un **XC3S100E** (Spartan-3E,
90 nm, 1 920 LUT4); la **Basys 3**, un **XC7A35T** (Artix-7, 28 nm; el
motor entero ocupa el 19 % de sus LUT6). En la Basys 2 solo cabe la fuente (anillos, ERO, tests de salud,
I2C y la FIFO del flujo); en la Basys 3 cabe el motor entero.

**Por qué se usaron.** El diseño se preparó para la Basys 3, pero la placa
que había el 14-11 era una Basys 2. Se trabajó con ella del 14 al 16-11. El
mismo 14-11 Mario decidió que esos resultados son **provisionales** y que la
memoria no se cierra con ellos. La Basys 3 llegó el 17-11 y se repitió casi
todo (`docs/basys2.md` §"Estado al 14-11-2026"; `docs/basys3.md`).

**Qué vale de cada una.**

- **Basys 3:** es la evidencia de la memoria. Tiene el motor entero con el
  ESP32 (O5, 40/40 retos tres veces), el jitter a `kd 0-2` con el buffer, el
  suelo blanco de Q (0,6-1,1·10⁻⁶ por periodo de ro2) del que sale
  `CFG_KD` = 19, SP 800-90B hasta `kd 19`, la captura larga, los reinicios
  §3.1.4 y la raya de ~39 kHz.
- **Basys 2 (provisional):** vale sobre todo por lo que enseñó, aplicado
  luego en la Basys 3 (§4): los anillos pueden desaparecer en la
  implementación, el display y la lógica colgada modulan los anillos, la Q
  depende de la implementación, y la batería se satura. Además tiene **el
  único experimento con y sin habilitación (CE)** del biestable de muestreo
  (ρ₁ 0,003-0,006 con CE, ~0 sin CE), que no se puede repetir en la Basys 3
  porque allí no hay variante con CE. Sus cifras de Q, sesgo y divisor no
  sustituyen a las de la Basys 3.

**Conclusión principal.** Las dos placas, en dos familias y dos nodos, dan el
mismo cuadro cualitativo:

1. El ruido de fase relativo entre anillos, ajustado con c(M), es del orden
   de 10⁻⁵ por periodo de ro2. El modelo del ERO deja residuos de varias
   veces a decenas de veces el ruido binomial, y la Q cambia ×2,5-4,4 con la
   lógica colgada de los anillos o con la implementación.
2. SP 800-90B se satura (0,82-0,88 a 10⁶ bits) y no separa FPGA, ESP32 y bits
   ideales. En la Basys 3 tampoco separa un divisor con H_∞ 0,47 de uno con
   0,9996.
3. Hay un sesgo del 0,2-1,9 % que depende de la implementación (en las dos
   placas cambia de signo entre variantes). No hay correlación a retardo 1
   sin CE.
4. Los tests de salud no ven el régimen de poco jitter.
5. La prueba de reinicios pasa.

La diferencia cuantitativa que importa es el divisor. Solo la Basys 3 tiene
una estimación del jitter blanco separada de la modulación (método espectral
del 18-11), y con ella `CFG_KD` pasó de ≥ 16 a 19. Con el mismo criterio, el
≥ 16 de la Basys 2 no se puede confirmar ni descartar, porque allí no se
midió el suelo blanco.

---

## 2. Plataforma

| | Basys 2 | Basys 3 | Fuente |
|---|---|---|---|
| Dispositivo | XC3S100E-4CP132 (IDCODE `0x11C10093`) | XC7A35T-1CPG236C (IDCODE `0x0362D093`) | `docs/basys2.md` §"Adept 2"; `docs/basys3.md` cabecera |
| Familia, nodo | Spartan-3E, 90 nm | Artix-7, 28 nm | ídem |
| Recursos del chip | 1 920 LUT4, 1 920 FF, 4 BRAM de 18 kbit | el total del chip no está en `docs/`; según Vivado, 4 011 LUT6 son el 19 % y 4 561 FF el 11 % | `docs/basys2.md` cabecera; `docs/basys3.md` §"Implementación" |
| Ocupación | 818/960 slices (85 %), 1 516 LUT4 (78 %), 451 FF (23 %) [ISE, implementado] | 4 011 LUT (19 %, 144 como RAM distribuida), 4 561 FF (11 %), sin BRAM ni DSP [Vivado, implementado, variante normal] | `results/basys2_ise_build.log`; `docs/basys3.md` §"Implementación" |
| Qué cabe | solo la fuente (`G_SOLO_FUENTE`, sin `trng_capture`, FIFO de 256 B); la criptografía sola pide ~6 800 LUT4 [ESTIMADO, Yosys `xc3se`], 3,5 veces el chip | el motor entero (DRBG, AES, CMAC, captura de 4 096 bits, FIFO de 256 B) | `docs/basys2.md` §"Qué cabe"; `docs/basys3.md` |
| Herramientas | ISE 14.7 WebPACK; XST no lee VHDL-2008 → GHDL a Verilog y XST sobre esa netlist; `KEEP` en el UCF; grabación con `djtgcfg` (Adept 2) | Vivado 2025.2 (non-project, `build.tcl`); `DONT_TOUCH`; grabación con `openFPGALoader` o `djtgcfg` | `docs/basys2.md` §"Flujo de ISE"; `docs/basys3.md` §"Herramientas" |
| Reloj de sistema | 50 MHz (LTC6905, JP4 sin soldar), comprobado: 60 parpadeos en 60 s, ±2 % [MEDIDO] | 100 MHz (MEMS con PLL, nunca referencia de jitter) | `docs/basys2.md` §"Primer día"; `CLAUDE.md` |
| Etapas ro2 / ro1 | 5/7 al principio; **7/9** desde el 14-11 por la tarde | 5/7 al principio; **11/13** desde el 17-11 | `docs/basys2.md` §"Anillos colocados"; `docs/basys3.md` §"Implementación" |
| Por qué esas etapas | colocados y con 5/7, ro2 subió a 204,8 MHz, por encima de los ~203 MHz que `trce` daba para el contador de `ero_core` (comparación con la máscara por el CE) | con 5/7 (357,8 MHz) y 7/9 (293 MHz) el dominio de ro2 no cerraba (`bit_stb` → escritura de la RAM distribuida de `trng_capture`, 3,3-3,9 ns) | ídem |
| ro2 / ro1 [MEDIDO] | 5/7 sin colocar: 167,8 / 105,8 MHz; 5/7 colocados: 204,8 / 145,8; **7/9 colocados: 143,8 / 108,7** (display); por flujo 143,1-143,9 según implementación | 5/7: 357,8 / 291,8 (display); 7/9: 293 (flujo); 11/13 sin `ro_bel`: **130,0** / sin medir (flujo; inversores combinados en LUT6); **11/13 con `ro_bel.xdc`: 207,2 / 167,2** (display), 205,0-205,8 por flujo en la silenciosa | `docs/basys2.md`; `docs/basys3.md` §"Frecuencias" |
| Colocación | `AREA_GROUP` por anillo en bordes opuestos (`SLICE_X0Y20`, `X28Y20`); desde el 15-11, LOC/BEL/patas de anillos y biestable sacados del XDL (`basys2_sin_medidor_fijo.ucf`); prueba con halo de dos CLB (`halo_anillos.ucf`) | pblocks sin `CONTAIN_ROUTING` (`ro_pblocks.xdc`); desde el 18-11, **`ro_bel.xdc`** (LOC y BEL `*6LUT` por etapa, sin combinar; fija los LUT, no el rutado ni el biestable de muestreo) | `docs/basys2.md` §"Anillos colocados", §"Muestreo sin habilitación", §"Residuo del jitter"; `docs/basys3.md` §"Colocación fija" |
| Restricción del reloj de ro2 | `TS_ro2` 5 ns (camino mejor caso 4,65-4,68 ns) | 4,2 ns hasta el 18-11; 4,5 ns con comprobación en `build.tcl` desde el 19-11 (camino ≤ 0,9 × 4,88 ns) | `docs/basys2.md`; `docs/decisiones_pendientes.md` §8 |
| Muestreo de ro1 | con CE (14-11, `_fijo`) y sin CE (`_libre`, `_libre_t7`, `_libre_c51`, `_libre_halo`); `basys2_top` sigue con `G_MUESTREO_LIBRE = false` por defecto | siempre sin CE (por defecto en `motor_top` desde el 15-11); no hay variante con CE | `docs/basys2.md` §"Muestreo sin habilitación"; `docs/basys3.md` §"Sesgo y correlación" |
| Cortes de salud en las campañas | 22/596 (14-11), 39/683 (15-11), 51/766 (`_libre_c51`, 16-11) | 51/766 siempre | `docs/basys2.md`; `docs/basys3.md` |
| `G_KD_MIN` / `G_KD_RESET` | 7 / 24 (a 50 MHz el cruce de dominio pide el doble de divisor) | 6 / 24 (los del motor) hasta el 18-11; **19 / 19** desde el 19-11 | `rtl/fpga/basys2_top.vhd`; `docs/basys3.md` §"19-11-2026" |
| Variantes del envoltorio | normal; `G_QUIETO` (display apagado); `G_QUIETO` sin medidor | normal (display y frecuencímetro); silenciosa (`G_QUIETO` y sin medidor a la vez); `G_CARGA` | ídem |
| Buffer de captura (`kd 0`) | no (no cabe) | sí (4 096 bits por trozo) | ídem |
| Flujo consecutivo a 115 200 baudios | desde `kd 12` (ro2 ~143 MHz) | desde `kd 12` a 130 MHz; desde `kd 13` a 205 MHz | `docs/puesta_en_marcha_fpga.md` §9.6; `docs/basys3.md` §"Campaña con la colocación fija" |

---

## 3. Resultados lado a lado

Placa: B2 = Basys 2, B3 = Basys 3. "Libre" en la B3 es sin `ro_bel.xdc`
(130 MHz); "bel", con `ro_bel.xdc` (205-207 MHz).

### 3.1 Jitter (Q por periodo de ro2)

| Medida | Placa | Valor | Condición | Fuente |
|---|---|---|---|---|
| Ajuste conjunto (un ν por trozo) | B2 | 3,9 / 5,0 / 5,3·10⁻⁵ (`kd 7/8/9`); 6,9·10⁻⁵ a `kd 10` | normal (display y medidor), con CE, 14-11, M = 1..30 | `docs/basys2.md` §"Jitter: primeros resultados"; `results/motor_campana/basys2_jitter_kd07_12/jitter_conjunto_kd*.txt` |
| | B2 | 1,6 / 2,0 / 2,1·10⁻⁵ | `G_QUIETO` con medidor, con CE | `docs/basys2.md` §"El display modula"; `basys2_quieto_kd07_09/` |
| | B2 | 4,1-4,5 / 4,4-4,7 / 4,7-4,9·10⁻⁵ (tres capturas); 3,44 / 3,85 / 3,91 regrabada el 16-11 | `G_QUIETO` sin medidor, con CE, implementación del 14-11 | ídem, §"Residuo del jitter"; `basys2_quieto_sin_medidor_kd07_09{,_r2,_r3,_r4}/` |
| | B2 | 1,31 / 1,66 / 1,87·10⁻⁵ | `_fijo` (con CE, colocación fija) | `basys2_fijo_kd07_09/` |
| | B2 | 0,98-1,12 / 1,39-1,67 / 1,55-1,78·10⁻⁵ | `_libre`, `_libre_c51`, `_libre_halo` (sin CE, colocación fija) | `basys2_libre*_kd07_09/` |
| | B3 | 9,37 / 9,21 / 9,31·10⁻⁶ (tres capturas) | normal, libre, `kd 2`, M = 1..100 | `docs/basys3.md` §"Repetibilidad"; `basys3_jitter_kd00_02_normal/jitter_conjunto_m.txt`, `basys3_jitter_kd02_normal_r{2,3}/` |
| | B3 | 2,754 / 2,750 / 2,764·10⁻⁵ | silenciosa, libre, `kd 2`, M = 1..100 | ídem; `basys3_jitter_kd00_02_quieto{,_r2,_r3}/` |
| | B3 | 3,22 y 3,16·10⁻⁶ | normal, bel, `kd 2` | `docs/basys3.md` §"Colocación fija"; `basys3_jitter_kd02_normal_bel{,_r2}/` |
| | B3 | 1,42 y 1,43·10⁻⁵ | silenciosa, bel, `kd 2` | ídem; `basys3_jitter_kd02_quieto_bel{,_r2}/` |
| Autocorrelación global (b = 1) | B2 | 6,7 / 6,5 / 6,1·10⁻⁵ (`kd 7/8/9`); `kd 9` y `10` con ν en el borde (0,5 y 0): no fiables | normal, con CE; **no recogido en `docs/basys2.md`** | `results/motor_campana/basys2_jitter_kd07_12/jitter_kd0{7,8,9}.txt` |
| | B3 | 5,0 / 5,5·10⁻⁵ (`kd 0/2`); `kd 2` en tres capturas 5,45-5,91 | normal, libre | `docs/basys3.md` §"Jitter con el buffer", §"Repetibilidad" |
| | B3 | 8,2-8,5·10⁻⁵ (`kd 0` y `2`, tres capturas) | silenciosa, libre | ídem |
| | B3 | 4,86 / 5,75·10⁻⁵ | normal / silenciosa, bel, `kd 2` | `docs/basys3.md` §"Colocación fija" |
| Exponente b libre | B2 | 2,55 / 2,51 (`kd 7/8`) | normal, global | `basys2_jitter_kd07_12/jitter_kd0{7,8}.txt` |
| | B3 | 1,61-2,10 | las dos variantes, libre, `kd 0-2` | `docs/basys3.md` §"Jitter con el buffer" |
| Estimador por varianza | B2 | no se usa: infraestima un 65-100 % a divisores altos [SIMULADO, autotest] | — | `docs/basys2.md`; `results/jitter_autocorrelacion_autotest.log` |
| | B3 | 1,69-3,26·10⁻⁵ a `kd 0` (no fiable, κ < 0); 1,48-2,41·10⁻⁵ a `kd 2` (±10-25 %); bel: 1,23 / 1,98·10⁻⁵ | libre y bel | `docs/basys3.md` |
| **Suelo blanco** (espectro de la frecuencia instantánea) | B2 | **no medido** (sin trozos a `kd 0-2`; no se pasó `espectro_fase.py`) | — | — |
| | B3 | **0,80-0,88·10⁻⁶** (tres modelos de calibración), por banda 0,59-1,13·10⁻⁶ (véase §7, punto 2); al divisor, la cota baja **0,6·10⁻⁶**; σ ≈ 4-5 ps por periodo de 4,9 ns [MEDIDO, calibración SIMULADA] | silenciosa, bel, `kd 2`, dos capturas | `docs/basys3.md` §"Suelo blanco medido"; `basys3_jitter_kd02_quieto_bel{,_r2}/espectro_fase_calibra.txt` |
| | B3 | 0,95-1,35·10⁻⁶ por banda | bitstream del 19-11 (silenciosa, bel, 4,5 ns) | `basys3_jitter_kd02_quieto_1911/espectro_fase_calibra.txt` |
| | B3 | 0,74-1,47·10⁻⁶ (silenciosa) y 1,06-1,9·10⁻⁶ (normal) [ESTIMADO, revisión]; normal bel no determinable (ν 0,227) | libre | `docs/basys3.md` §"Suelo blanco medido" |
| Residuo del modelo / ruido binomial | B2 | 45 / 31 / 13 (normal); 7,1 / 7,0 / 4,3 (`G_QUIETO`); 8-11 / 5-7 / 2,6-3,3 (sin medidor); 4,4-11,9 en `_fijo` y `_libre*` | ajuste conjunto, `kd 7/8/9` | `docs/basys2.md` |
| | B3 | 5,3-5,9 (M ≤ 100); 5-250 creciendo con M (100, 300, 1 000) | ajuste conjunto, `kd 2` | `docs/basys3.md` §"Jitter con el buffer", §"Repetibilidad" |
| Efecto del display | B2 | apagarlo baja el residuo de 45 a ~7 a `kd 7` y Q ×0,4 (3,9 → 1,6·10⁻⁵); con display, ν bimodal por trozo | `G_QUIETO` frente a normal | `docs/basys2.md` §"El display modula" |
| | B3 | no separado del frecuencímetro (la silenciosa quita los dos a la vez) | — | `docs/basys3.md` §"Jitter con el buffer", punto 3 |
| Efecto del frecuencímetro / lógica colgada | B2 | quitar el medidor sube Q ×2,5 (1,6-2,1 → 4,1-4,7·10⁻⁵) y mueve la fracción de unos (0,517 → 0,498) | con CE, misma colocación de los anillos (mismos CLB) | `docs/basys2.md` §"El display modula" |
| | B3 | silenciosa / normal: ×2,95 (conjunto), ×1,5 (global), libre; con los anillos en los mismos LUT6: ×4,4 (conjunto), ×1,2 (global), ×1,6 (varianza) | libre y bel | `docs/basys3.md` §"Repetibilidad", §"Colocación fija" |
| Efecto del rutado / colocación | B2 | la implementación cambia Q ×2,5-3,5 con las redes internas de los anillos idénticas pip a pip; cambia el rutado del reloj ro2 (21 cargas); el halo no cambia nada (±0,4 %); quitar el CE no quita el residuo | `G_QUIETO` sin medidor, 14-11 frente a `_fijo`/`_libre*` | `docs/basys2.md` §"Residuo del jitter" |
| | B3 | sin `ro_bel`, Vivado combinaba inversores de ro2 en una LUT6 (130 MHz); con `ro_bel`, 207 MHz. La diferencia entre variantes se mantiene con la colocación fija: es la lógica colgada | — | `docs/basys3.md` §"Implementación", §"Colocación fija" |
| Repetibilidad | B2 | ±3-5 % (`kd 7`), ±3 % (`kd 8` y `9`), tres capturas | ajuste conjunto, sin medidor | `docs/basys2.md` §"El display modula" |
| | B3 | conjunto ±0,3 %, global ±1-2 %, varianza ±10 % (`kd 2`) y ×1,9 (`kd 0`), tres capturas; bel, segunda captura ±1 % | silenciosa y normal | `docs/basys3.md` §"Repetibilidad", §"Colocación fija" |
| Raya de ~38-39 kHz | B2 | **no buscada** (`espectro_fase.py` es del 18-11 y no se ha pasado por los trozos de la Basys 2). En la Basys 2 se vio otra modulación, la del display (dígitos de 1,3 ms) | — | `docs/basys2.md` §"El display modula" |
| | B3 | línea estrecha a ~39,4 kHz (37,7-39,9 kHz según captura), pico 1,13-1,31 en la silenciosa, 0,07 en la normal bel (×15 en potencia); no es el sondeo I2C (bus callado: mismo pico); una carga de 4 000 FF no cambia la amplitud y la mueve un 0,9 %; portadora a ~480 kHz con bandas a ±39,5 kHz (¿regulador?, hipótesis abierta) | silenciosa y normal, libre y bel | `docs/basys3.md` §"Tarde del 18-11"; `basys3_bus_*`, `basys3_carga_*` |

### 3.2 SP 800-90B (no-IID en bits, cifra asignada = mínimo)

| Medida | Placa | Valor | Condición | Fuente |
|---|---|---|---|---|
| Trozos no consecutivos | B2 | no medido | — | — |
| | B3 | `kd 8` 0,125, `kd 10` 0,558, `kd 11` 0,786 | silenciosa libre, 245 trozos de 4 096 bits | `docs/basys3.md` §"Campaña SP 800-90B"; `basys3_campana_90b_trozos/` |
| | B3 | `kd 8` 0,186, `kd 10` 0,430, `kd 11` 0,695, `kd 12` 0,848 | silenciosa bel | `docs/basys3.md` §"Campaña con la colocación fija"; `basys3_campana_90b_trozos_bel/` |
| Flujo 10⁶ bits consecutivos | B2 | `kd 12` **0,760**; `kd 13-16` 0,863 / 0,846 / 0,821 / 0,845 | `G_QUIETO` sin medidor, con CE, 22/596, ro2 143,2 MHz | `docs/basys2.md` §"Campaña SP 800-90B"; `basys2_campana_90b_kd12_16/` |
| | B3 | `kd 12-16` 0,879 / 0,847 / 0,829 / 0,877 / 0,819 | silenciosa libre, ro2 130,3 MHz | `docs/basys3.md` §"Campaña SP 800-90B"; `basys3_campana_90b_flujo/` |
| | B3 | `kd 13-16` 0,815 / 0,876 / 0,854 / 0,850 | silenciosa bel, ro2 205,2 MHz | `basys3_campana_90b_flujo_bel/` |
| | B3 | `kd 17-19` 0,864 / 0,833 / 0,857 (H_∞ del modelo 0,80 / 0,974 / 0,9996) | silenciosa bel | `docs/basys3.md` §"SP 800-90B y reinicios al divisor nuevo"; `basys3_campana_90b_flujo_kd17_19/` |
| 2²² bits, con y sin CE | B2 | 0,860 (0,843-0,876) con CE; 0,883 (0,878-0,885) sin CE | `_fijo` / `_libre`, `_libre_t7`, `kd 13-14` | `results/tabla_o8.md` |
| | B3 | no medido (no hay variante con CE) | — | — |
| Tabla O8 a 10⁶ (mediana de `kd 13-16`) | B2 / B3 libre / B3 bel | 0,845 / 0,838 / 0,852; ESP32 0,848; ideal 0,847 | — | `results/tabla_o8.md` |
| Captura larga, 8 378 368 bits | B2 | **0,890** (colisión) | `kd 14`, 16 min, ro2 143,2 MHz | `docs/basys2.md` §"Captura larga"; `basys2_larga_kd14_n8378368/` |
| | B3 | **0,932** (colisión) | silenciosa libre, `kd 16`, 70 min | `docs/basys3.md` §"A 8 378 368 bits"; `basys3_larga_kd16_n8378368/` |
| | B3 | **0,880** (compresión; colisión 0,948) | silenciosa bel, `kd 16`, 45 min | `basys3_larga_kd16_n8378368_bel/` |
| | referencia | ESP32 0,911; ideal 0,935 (0,907-0,935) | `esp_rf_off_2` | `results/tabla_o8.md` |
| Contraste batería–modelo | B2 | `kd 12` en el borde de la banda con Q 4,5·10⁻⁵ ("por debajo" por 0,002); con 2·10⁻⁵, "por encima" | — | `docs/basys2.md` §"Campaña SP 800-90B" |
| | B3 | compatible con Q 6-10·10⁻⁵ (`kd 10-11`); "por encima" con 1-4·10⁻⁵, y con la Q blanca la batería puntúa 0,82-0,88 bits con H_∞ ≤ 0,47 | — | `docs/basys3.md` |

### 3.3 Sesgo y correlación a retardo 1

| Medida | Placa | Valor | Condición | Fuente |
|---|---|---|---|---|
| Fracción de unos | B2 | 0,4970-0,4981 (`kd 12-16`), 0,4979 en la larga (z −12) | 14-11, con CE, sin medidor | `results/sesgo_correlacion.md` |
| | B2 | 0,4957-0,4959 (con CE) y 0,4962 (sin CE); 0,4971 la segunda libre | `_fijo`, `_libre`, `_libre_t7`, `kd 13-14` | `results/muestreo_libre_ce.md`; `docs/basys2.md` |
| | B2 | 0,5195 / 0,5192 (`kd 13/14`) | **normal** (display y medidor) | `basys2_jitter_kd13_14/jitter_kd1{3,4}.txt` |
| | B3 | 0,4951-0,4963 (z −7 a −10); larga 0,4955 (z −26) | silenciosa libre | `docs/basys3.md` §"Sesgo y correlación" |
| | B3 | 0,512-0,513 (z +76 en 8,2·10⁶ bits) | normal libre | ídem |
| | B3 | 0,5054-0,5064 (z +10,9 a +12,8); larga 0,5054 (z +31); 0,5055-0,5060 a `kd 17-19` | silenciosa bel | `basys3_campana_90b_flujo_bel/sesgo_correlacion.txt`, `..._kd17_19/sesgo_correlacion.txt` |
| | B3 | 0,519 | normal bel (`kd 2`) | `docs/basys3.md` §"Colocación fija" |
| | B3 | 0,4966 | bitstream del 19-11 (`kd 2`) | `docs/basys3.md` §"19-11-2026" |
| Cota −log₂ max(p, 1−p) [cálculo aquí] | B2 | 0,988-0,995 (sin medidor); 0,945 (normal) | — | de las fracciones de arriba |
| | B3 | 0,986-0,990 (silenciosa libre), 0,982-0,985 (silenciosa bel), 0,946-0,962 (normal) | — | ídem |
| ρ₁ | B2 | +0,0032 a +0,0060, z 3,2-13,1 | con CE (dos implementaciones) | `results/sesgo_correlacion.md`, `results/muestreo_libre_ce.md` |
| | B2 | +0,0005 / +0,0000 / +0,0002, z 1,0 / 0,1 / 0,4 | sin CE (`_libre` `kd 13/14`, `_libre_t7` `kd 14`) | ídem |
| | B3 | −0,0011 a +0,0014 (\|z\| ≤ 1,4); larga −0,0004 (z −1,1) | sin CE, libre, `kd 12-16` | `docs/basys3.md` §"Sesgo y correlación" |
| | B3 | −0,0008 a +0,0021 (z ≤ 2,1); larga +0,0004 (z 1,1); `kd 17-19` ≤ +0,0008 (z ≤ 0,8) | sin CE, bel | `docs/basys3.md` |
| ρ₁ a divisores bajos (fase determinista) | B2 | `kd 12` por bloques de −0,011 a +0,021 | 14-11 | `docs/basys2.md` §"Tabla O8" |
| | B3 | libre: `kd 8` +0,71, `kd 10` +0,053; bel: `kd 8` −0,536, `kd 10` −0,241, `kd 11` −0,010, `kd 12` +0,0045 | trozos | `docs/basys3.md` |

### 3.4 Tests de salud

| Medida | Placa | Valor | Condición | Fuente |
|---|---|---|---|---|
| Alarmas en placa (`kd`, `borrar`, escucha, `id`) | B2 | RCT a `kd 12` y `11`; RCT + APT a `kd 8`; nada a `kd 14, 13, 10, 9, 7, 6` | 14-11, 22/596, con CE, 30 s | `docs/basys2.md` §"Los tests de salud en hardware" |
| | B2 | solo RCT a `kd 10` | 16-11, 51/766, sin CE (`_libre_c51`), 30 s | `docs/basys2.md` §"Tests de salud 51/766" |
| | B3 | RCT a `kd 8`; nada a `kd 6` ni a `kd 10` (allí la batería da 0,558 < 0,60) | silenciosa libre, 51/766, ~40 s | `docs/basys3.md` §"Tests de salud en placa" |
| | B3 | nada a `kd 6, 8, 10, 11` (a `kd 8` la batería da 0,186) | silenciosa bel, 51/766, 40 s | `docs/basys3.md` §"Campaña con la colocación fija" |
| | B3 | desde el 19-11 `sembrar` se rechaza a `kd 18` (`G_KD_MIN` 19); a `kd` bajo hace falta la variante de caracterización | — | `docs/basys3.md` §"19-11-2026" |
| En software sobre los bits | B2 | a `kd 7-9` ningún juego de cortes (22/596, 39/683, 51/766) detecta nada: racha máxima 4-17, APT máximo 534-576 | tres implementaciones | `results/salud_offline.md` |
| | B3 | racha máxima 8 / 16 / 20 / 21 y APT máximo 546 / 554 / 573 / 570 a `kd 8 / 10 / 11 / 12` | bel; el régimen es anticorrelado | `docs/basys3.md` §"Campaña con la colocación fija" |
| Falsas alarmas | B2 | con 22/596 a `kd 14`: 1 racha ≥ 22 (máximo 23) en 8,4·10⁶ bits, ~2 esperadas con bits ideales → **una cada ~8 min a 8,7 kbit/s** [ESTIMADO, no observada como alarma]; APT máximo 571 (corte 596). Con 51/766 [ESTIMADO, iid, 8,7 kbit/s]: ninguna con bits ideales, ~8 al año del RCT con el peor chip SPICE, ~89 al año con un chip en H 0,60 | — | `docs/basys2.md` §"Los tests de salud", §"Decisión del 16-11-2026" |
| | B3 | no estimadas a su tasa. A `kd 19` y 205 MHz la tasa es ~0,39 kbit/s [cálculo aquí], ~22 veces menos que la de la Basys 2 a `kd 14` | — | — |

### 3.5 Reinicios, O5, divisor

| Medida | Placa | Valor | Condición | Fuente |
|---|---|---|---|---|
| Reinicios §3.1.4 (`ea_restart` en bit, 1000 × 1000) | B2 | pasa: H_I 0,845, H_r 0,855, H_c 0,873; 1 000 arranques distintos; Hamming 512,0 ± 16,02 (mínima 425); 3 ciclos repetidos | `kd 14`, sin medidor, con CE, 0,6 s por reprogramación | `results/fpga_reinicios/basys2_kd14/resumen.md` |
| | B3 | pasa: H_I 0,819, H_r 0,843, H_c 0,892; 1 000 distintos; Hamming 511,9 ± 15,98 (mínima 430); 0 descartados | `kd 16`, silenciosa libre, 1,1 s por reprogramación | `results/fpga_reinicios/basys3_kd16/resumen.md` |
| | B3 | pasa: H_I 0,857, H_r 0,854, H_c 0,830 (el criterio es ≥ H_I/2); 1 000 distintos; Hamming 511,9 ± 16,02 (mínima 439) | `kd 19`, silenciosa bel, ~4 s por ciclo | `results/fpga_reinicios/basys3_kd19_bel/resumen.md` |
| | ambas | mismo matiz: son los primeros bits del flujo, cientos de ms tras configurar | — | `docs/basys2.md`, `docs/basys3.md` |
| O5 (motor entero con el ESP32 de oráculo) | B2 | **no cabe** | — | `docs/basys2.md` §"Qué cubre" |
| | B3 | **40/40** retos CMAC iguales a mbedtls, dos claves (`cero` entre medias), aleatorio con CRC correcto: 17-11 (libre, `kd 16`), 18-11 (bel, `kd 16`), 19-11 (4,5 ns, `G_KD_MIN` 19, `kd 19`) | — | `results/basys3_o5_consola_20261117.txt`, `_20261118_bel.txt`, `_20261119.txt` |
| `CFG_KD` provisional | B2 | **≥ 14** (14-11): Q ≈ 4,5·10⁻⁵ → K\* ≈ 2^12,3, factor 2; **≥ 16** (16-11): Q más baja 9,8·10⁻⁶ (`_libre_halo`, `kd 7`) → K\* ≈ 2^14,5, factor 2 | ajuste conjunto | `docs/basys2.md` §"Campaña SP 800-90B", §"Residuo del jitter" |
| | B3 | **≥ 16** (17-11): 0,93·10⁻⁵ → 2^14,6 ×2; se mantiene el 18-11 con la silenciosa bel (1,42·10⁻⁵; con frecuencímetro haría falta ≥ 18); la revisión de Fable lo pone en duda (≥ 18-19); **19** desde la tarde del 18-11 (Q blanca, cota baja 0,6·10⁻⁶ → H_∞ 0,996 a `kd 19`; ≥ 20 con factor 2 en Q), aplicado el 19-11 (`G_KD_MIN` y `G_KD_RESET` 19) | — | `docs/basys3.md`; `results/cfg_kd_suelo_blanco.txt`; `docs/decisiones_pendientes.md` |

**Por qué cambió el divisor.** No fue la placa, sino el método. Con el ajuste
de c(M), la modulación (la raya, el display) se cuenta como jitter, y la Q
sale por arriba. El método espectral separa el suelo blanco: en la misma
variante (silenciosa con `ro_bel`), de 1,42·10⁻⁵ a 0,6-1,1·10⁻⁶, ×13-24
menos. Además, `CFG_KD` cuenta
periodos de ro2 y ro2 cambió:

- `kd 16` a 143,8 MHz (Basys 2) son 456 µs por bit;
- `kd 19` a 205 MHz (Basys 3) son 2,56 ms [cálculo aquí].

Por eso los divisores de las dos placas no se comparan número a número.

---

## 4. Lecciones y lo que no es comparable

### 4.1 Lecciones de la Basys 2 aplicadas en la Basys 3

| Lección (Basys 2) | Cómo se aplicó en la Basys 3 | Fuente |
|---|---|---|
| XST conservó los anillos y map los colapsó: comprobar las etapas en la netlist **implementada** | `build.tcl` lista tras rutar cada celda y red de los anillos, y se para si los relojes no existen tras la síntesis. En Vivado se encontró otro problema que `DONT_TOUCH` no impide: combinaba inversores en una LUT6. Se resolvió con `ro_bel.xdc` | `docs/basys2.md` §"Primera implementación"; `docs/basys3.md` §"Implementación" |
| Colocados, los anillos van más deprisa y superan el contador de `ero_core`: medir y cerrar tiempos con la frecuencia medida; alargar con `G_ETAPAS_RO1/RO2` | 5/7 → 7/9 → 11/13 etapas; restricción de ro2 ajustada a lo medido (4,2 → 4,5 ns) con comprobación automática en `build.tcl` | `docs/puesta_en_marcha_fpga.md` §9.2; `docs/decisiones_pendientes.md` §8 |
| El display modula los anillos: capturas con el display apagado | variante silenciosa de `basys3_top` (`G_QUIETO`, `G_MEDIDOR`) para todas las campañas | §9.3 |
| La lógica colgada cambia Q: hacer la campaña con la variante que se defiende y decirlo | campañas con la silenciosa (la que se parece al integrado, que no lleva frecuencímetro) | §9.3; `docs/basys3.md` §"Colocación fija" |
| El estimador por varianza no vale a divisores altos; usar c(M) con `--conjunto` | en la B3 se usaron los tres; la varianza solo de contraste | §9.4 |
| Repetibilidad antes que conclusiones (tres capturas) | tres capturas por variante el 18-11 | §9.5; `docs/basys3.md` §"Repetibilidad" |
| Contraste batería–modelo | `compara_modelo_campana.py` a `kd 8-14` en la B3 | §9.7 |
| La habilitación del biestable correlaciona los bits | `G_MUESTREO_LIBRE = true` por defecto en `motor_top`; la B3 no tiene ρ₁ | `docs/basys2.md` §"Decisión del 15-11-2026" |
| α = 2⁻²⁰ da falsas alarmas frecuentes; los tests no ven el régimen de poco jitter | cortes con α = 2⁻³⁰ (51/766); `G_KD_MIN` 19 en `basys3_top` | `docs/basys2.md`; `docs/decisiones_pendientes.md` §7 |
| Separar colocación de lógica colgada fijando los anillos (`_fijo.ucf` desde el XDL) | `ro_bel.xdc` con las dos variantes: con los anillos fijos la diferencia sigue (×4,4) | `docs/basys3.md` §"Colocación fija" |
| Reinicios con `reinicios_fpga.py` y `djtgcfg` | mismo script, a `kd 16` y `kd 19` | `docs/basys3.md` §"Prueba de reinicios" |

### 4.2 Qué no se repitió o no es comparable

- **Número de etapas y frecuencias.** 7/9 a ~144 MHz frente a 11/13 a 130 MHz
  (LUT combinadas) o 205-207 MHz (`ro_bel`). La Q depende de los periodos de
  ro1 y ro2 (en ciclos de ro1, va como κ²·T2/T1², `docs/basys3.md` §"Suelo
  blanco medido", punto 1), y el mismo `kd` acumula tiempos distintos.
- **Divisores del jitter.** Basys 2: `kd 7-11` (no hay buffer). Basys 3:
  `kd 0-2`. El ajuste conjunto va a M = 1..30 en la Basys 2 y a M = 1..100
  (y 300 y 1 000) en la Basys 3. Las Q del ajuste conjunto no son la misma
  medida.
- **σ en picosegundos.** La Basys 2 la calcula con el periodo de ro1 (9,2 ns),
  la Basys 3 con el de ro2 (7,7 o 4,9 ns). Solo se compara Q.
- **CE.** Solo en la Basys 2 se comparó con y sin habilitación. La Basys 3 no
  tiene variante con CE, así que "la correlación la produce el CE" sigue
  siendo un resultado de una sola familia.
- **Halo.** Solo en la Basys 2 (sin efecto).
- **Display solo, frente a frecuencímetro solo.** Solo la Basys 2 los separa
  (`G_QUIETO` con medidor). La silenciosa de la Basys 3 quita los dos a la
  vez.
- **Cortes de salud.** Las campañas de la Basys 2 del 14-11 se hicieron con
  22/596 y CE. Las de la Basys 3, con 51/766 y sin CE.
- **Solo en la Basys 3:** suelo blanco y método espectral, raya de ~39 kHz,
  bus callado, prueba de carga, SP 800-90B por trozos y a `kd 17-19`,
  reinicios a `kd 19`, O5, comprobación de `G_KD_MIN` en placa.
- **No medido en ninguna:** temperatura (frío y calor; pendiente 3 de la
  Basys 2), reinicios con muestreo con CE en la Basys 3, display separado del
  frecuencímetro en la Basys 3, raya en la Basys 2.

---

## 5. Los anillos en 90 y 28 nm

Lo comparable es la frecuencia por número de etapas. El retardo por etapa
(LUT más rutado) se calcula aquí como 1/(2·N·f), con las frecuencias
[MEDIDAS] de §2:

| Anillo | Basys 2 (90 nm) | Basys 3 (28 nm) |
|---|---|---|
| 5 etapas | 0,596 ns sin colocar (167,8 MHz); 0,488 ns colocado (204,8 MHz) | 0,280 ns (357,8 MHz) |
| 7 etapas | 0,675 ns sin colocar (105,8 MHz); 0,490 ns colocado (145,8); 0,497 ns colocado en 1 CLB (143,8) | 0,245 ns (291,8 MHz, ro1); 0,244 ns (293 MHz, ro2) |
| 9 etapas | 0,511 ns colocado (108,7 MHz) | — |
| 11 etapas | — | 0,350 ns (130,0 MHz, LUT combinadas: no es un retardo por etapa); **0,219 ns** con `ro_bel` (207,2 MHz) |
| 13 etapas | — | **0,230 ns** con `ro_bel` (167,2 MHz) |

- Colocados, la Artix-7 es unas 2-2,3 veces más rápida por etapa [cálculo
  aquí: 0,488-0,511 ns frente a 0,219-0,245 ns]. Salvedades: no se sabe si
  las implementaciones de 5/7 y 7/9 de la Basys 3 tenían inversores
  combinados (solo se comprobó en la de 11/13), y el rutado entre etapas no
  está fijado en ninguna de las dos placas.
- Razón ro2/ro1 frente a la de etapas: 1,32 frente a 9/7 = 1,29 en la Basys 2
  colocada; 1,24 frente a 13/11 = 1,18 en la Basys 3 con `ro_bel`.
- **Ruido de fase.** En las dos placas, el ajuste de c(M) da 10⁻⁶-10⁻⁵ por
  periodo de ro2: Basys 2 0,98-5,3·10⁻⁵ (`kd 7-9`), Basys 3 0,32-2,75·10⁻⁵
  (`kd 2`). El global da 6,1-6,7·10⁻⁵ en la Basys 2 frente a 4,9-8,5·10⁻⁵ en
  la Basys 3. Es el mismo orden, pero con frecuencias, divisores, alcances M y
  envoltorios distintos, y con el modelo sin describir la forma en ninguna de
  las dos. **No se puede concluir que un nodo tenga más jitter que el otro.**
  El único número que aspira a ser térmico (el suelo blanco, 0,6-1,1·10⁻⁶,
  σ ≈ 4-5 ps por periodo de 4,9 ns) solo existe en la Basys 3. Es del orden
  de los 2-4 ps por periodo de 3-5 ns de la bibliografía
  (`docs/modelo_ero_resultados.md` §5).
- **Sensibilidad a lo que cuelga.** Es la misma en las dos (×2,5 y ×2,95-4,4
  en el ajuste conjunto), y va en el mismo sentido: **sin el frecuencímetro la
  Q es mayor** (Basys 2: quitarlo sube Q; Basys 3: la silenciosa tiene más Q
  que la normal). Hipótesis común sin demostrar: acoplamiento entre anillos a
  través de esa lógica.
- **Sesgo.** Es del orden del 0,2-1,9 % en las dos, y el signo cambia con la
  implementación en las dos. En la Basys 2 la variante normal (0,519) frente a
  la sin medidor (0,496-0,498). En la Basys 3, la silenciosa libre (0,495), la
  silenciosa bel (0,506), la normal (0,513-0,519) y la del 19-11 (0,497).
- **Frente al IHP de 130 nm [SIMULADO].** El anillo de 5 etapas oscila a
  2,73 GHz (36,6 ps por etapa, cálculo aquí) con σ/T 4,8·10⁻⁴ por periodo
  (tt 27 °C, `memoria/chapters/ch7_results.tex` tabla de ruido). Es el jitter
  de un anillo solo, no la fase relativa de dos, así que no se compara con la
  Q de las FPGA. El sesgo del biestable sg13g2 llega al 13 % (peor chip,
  125 °C, sin ruido) y es de otra naturaleza que el 0,2-1,9 % de los
  biestables de FPGA (`docs/basys2.md` §"El biestable real").

---

## 6. Cifras de la Basys 2 en la memoria hoy

Líneas de la rama `feat/lecturas-firmadas` (46660d6). EN es la de
referencia, ES su traducción. No se ha editado la memoria.

| Dónde (EN; ES) | Qué dice | Origen real | Qué hacer |
|---|---|---|---|
| `memoria/chapters/ch4_engine.tex:157-158`; `memoria/chapters_es/ch4_engine.tex:167-168` | "At 2⁻²⁰ the FPGA prototype raised a repetition false alarm every few minutes" | Basys 2, `kd 14`, 22/596, con CE. Es una **estimación** a partir de las rachas (1 racha ≥ 22 en 8,4·10⁶ bits → ~1 cada 8 min a 8,7 kbit/s). En placa, a `kd 14` no saltó en 30 s; las alarmas observadas fueron a `kd 8, 11, 12` | **Decir que es la Basys 2 y que es estimado** ("would raise one about every eight minutes \est{}" en el primer prototipo). La Basys 3 no puede sustituirla: nunca corrió con 22/596. Alternativa: quitar la referencia a la placa y dar el argumento general (con α = 2⁻²⁰, unos 2²¹ bits entre falsas alarmas, minutos a kbit/s) |
| `memoria/chapters/ch4_engine.tex:211-216`; `memoria/chapters_es/ch4_engine.tex:225-230` | "independent bits at 8.7 kbit/s, the FPGA rate", con ~8 alarmas al año del peor chip y 0,24 al día en H 0,60 | 8,7 kbit/s es la Basys 2 a `kd 14` (143,2 MHz / 2¹⁴). Las tasas de alarma son [ESTIMADO] a ese caudal (`docs/basys2.md` §"Decisión del 16-11-2026") | **Sustituir** por la Basys 3 a `kd 19` (~0,39 kbit/s, cálculo aquí) y recalcular las tasas (`analysis/cortes_salud.py`), o dar el caudal como parámetro. El "worst simulated die" y los "0.2-0.4 kbit/s" del integrado también están desfasados (biestable de 11 etapas, `kd 25`), pero no son de la Basys 2 (`docs/plan_memoria_cierre.md`) |
| `memoria/chapters/ch4_engine.tex:218-225`; `memoria/chapters_es/ch4_engine.tex:232-239` | "On the FPGA ... ρ₁ ≈ 0.005, z up to 13 ... z ≤ 1 in two implementations with the same placement" | Basys 2 (XC3S100E): ρ₁ 0,003-0,006, z 13,1 en la larga; sin CE z 1,0/0,1 (`_libre`) y 0,4 (`_libre_t7`, que comparte con la regenerada el rutado de ro1). Cifras correctas | **Mantener y atribuir a la Basys 2**: es el único experimento con y sin CE. Añadir la confirmación en otra familia: la Basys 3 sin CE no tiene ρ₁ (\|z\| ≤ 1,4 en flujos, 1,1 en las largas, ≤ 0,8 a `kd 17-19`). Si la Basys 2 no entra en la memoria, la frase tiene que perder sus cifras |
| `memoria/chapters/ch7_results.tex:265-266`; `memoria/chapters_es/ch7_results_a.tex:274-275` | "on the FPGA, where the measured bias is 0.4 %, it is 0.989" | Basys 2, `_fijo`/`_libre` (0,4957-0,4962 → 0,988-0,989). La implementación del 14-11 daba 0,4979 (0,2 %, 0,994) | **Sustituir por la Basys 3**, diciendo la variante: silenciosa con `ro_bel` (la de por defecto) 0,5054-0,5064 → 0,982-0,985; silenciosa libre 0,4951-0,4966 → 0,986-0,990; normal 0,513-0,519 → 0,946-0,962. Y añadir que el signo cambia con la implementación. O dar el rango de las dos placas (0,2-1,9 %) |
| `memoria/chapters/ch8_concl.tex:76-83`; `memoria/chapters_es/ch8_concl.tex:82-89` | nota no impresa con el resumen de la Basys 2 (ro2 143,8 MHz, Q ~4,5·10⁻⁵, `kd 12` = 0,760, `CFG_KD` ≥ 14) | Basys 2, 14-11 | **Quitar** al escribir el párrafo de O5/O6 con la Basys 3. La nota está desfasada incluso para la Basys 2 (luego ≥ 16; la Q depende ×2,5-3,5 de la implementación) |

Relacionado, sin cifras de la Basys 2 (decisión de la tarea 11, ya en
`docs/plan_memoria_cierre.md`):

- `memoria/chapters/ch5_verification.tex:84-92` (tabla `tab:tb`):
  `tb_basys2_top` y `tb_motor_solo_fuente`, si entra la Basys 2.
- `memoria/chapters/appendices.tex` (`tab:app_diag`): bit 3 `solo_fuente`.
- Comentarios `% PROVISIONAL` en `memoria/chapters/ch4_engine.tex:150-153` y
  `memoria/chapters/ch7_results.tex:268-271`: apuntan a `docs/basys2.md` por
  el Monte Carlo del biestable, que es SPICE y no de la placa (hoy también en
  `results/biestable_mc*.md`).

---

## 7. Discrepancias y huecos encontrados

1. **`docs/basys3.md` §"Basys 2 frente a Basys 3" (líneas 41-52) y el
   resumen (líneas 24-39) están desfasados:**
   - ro2 "130 MHz" (con `ro_bel`, 205-207);
   - sesgo de la Basys 3 "0,495-0,496" (con `ro_bel`, 0,505-0,506);
   - divisor "≥ 16" en las dos placas (la Basys 3 está en 19 desde el 18/19-11);
   - Q de la Basys 3 "~1-8·10⁻⁵", que deja fuera el 3,2·10⁻⁶ de la normal con
     `ro_bel` y el suelo blanco;
   - sesgo de la Basys 2 "0,496-0,498", que solo es la implementación del
     14-11 (las del 15-11, 0,4957-0,4962);
   - "reinicios sin repetir" con `ro_bel` (líneas 37 y 407), cuando se
     repitieron a `kd 19` (§"SP 800-90B y reinicios al divisor nuevo").
2. **Q blanca por banda:** `docs/basys3.md` (líneas 617 y 666) da
   0,63-1,14·10⁻⁶ (recálculo de la revisión, no versionado). Las
   recalibraciones versionadas
   `results/motor_campana/basys3_jitter_kd02_quieto_bel{,_r2}/espectro_fase_calibra.txt`
   dan 0,593-1,133·10⁻⁶, como `docs/decisiones_pendientes.md:13`
   (0,59-1,13). La cota de 0,6·10⁻⁶ que va al divisor no cambia.
3. **`docs/basys2.md` no está al día consigo mismo.** El resumen (líneas
   27-30) da Q ≈ 4,5·10⁻⁵ y `CFG_KD` ≥ 14. Más abajo (líneas 934-951) la Q
   depende ×2,5-3,5 de la implementación y el divisor pasa a ≥ 16.
4. **Q global de la Basys 2 sin documentar.**
   `results/motor_campana/basys2_jitter_kd07_12/jitter_kd*.txt` tiene la
   autocorrelación global (6,1-6,7·10⁻⁵ a `kd 7-9`, b libre 2,5), que
   `docs/basys2.md` no recoge. A `kd 9` y `10` la ν ajustada está en el borde
   (0,5 y 0), así que esas dos no valen.
5. **Fracción de unos a `kd` bajo.** `_fijo` da 0,475-0,480 a `kd 7-9` y
   0,4957-0,4959 a `kd 13-14` con el mismo bitstream (`docs/basys2.md` líneas
   919 y 583). A divisores bajos la fracción la fija la fase determinista: no
   es una medida del sesgo.
6. **Huecos:**
   - suelo blanco de la Basys 2 (no medido: no hay `kd 0-2`);
   - raya de ~39 kHz en la Basys 2 (no buscada);
   - ro1 de la Basys 3 con 11/13 sin `ro_bel` (sin medir);
   - display y frecuencímetro por separado en la Basys 3;
   - variante con CE en la Basys 3;
   - temperatura en las dos placas;
   - falsas alarmas a la tasa de la Basys 3;
   - si las implementaciones de 5/7 y 7/9 de la Basys 3 tenían inversores
     combinados.
7. **Captura del 19-11 sin resultado.** Hay una carpeta
   `results/motor_campana/basys3_final_1911_kd19/` (con `serie.log`) y un
   `results/motor_campana_basys3_final_1911_kd19.log` vacío y sin versionar:
   no se ha usado aquí.
