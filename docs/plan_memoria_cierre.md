# Plan para cerrar la memoria (22-11-2026)

Qué hay que cambiar en la memoria (`memoria/`, EN de referencia y ES) para
que diga lo que hoy dicen `docs/` y `results/`, con qué evidencia, qué falta
y en qué orden. **No se ha tocado nada de `memoria/`.** Regla de Mario: la
memoria solo se toca con la evidencia cerrada; lo provisional se queda en
`docs/` o como nota no impresa.

Fuentes leídas: `memoria/tfm_main.tex`, `memoria/chapters/*.tex` (enteros,
salvo `ch2_soa` y `esp32_blackbox`, revisados por búsqueda),
`memoria/chapters_es/*.tex` (comparados con un script, §5),
`docs/basys3.md`, `docs/decisiones_pendientes.md`, `docs/anillo_ihp.md` §4.4,
`docs/basys2.md` (resumen, Monte Carlo), `docs/mapa_registros.md`,
`docs/sintesis_resultados.md`, `docs/revision_memoria_2026-11-10.md`,
`results/{tabla_o8.md, biestable_mc.md, biestable_mc_e11.md,
sintesis_19_11*.log, anillo_ihp_divisor_e11.txt, run_tb_todos.log,
run_tb_basys3_top_1911.log}`, `analysis/cortes_salud.py`.

Las líneas citadas son las de hoy (rama `feat/lecturas-firmadas`, 7b3704e).
Estado de cada cambio: **C** = evidencia cerrada, se puede escribir ya;
**P** = provisional (se dice qué falta); **D** = falta una decisión de
Mario; **H** = hay que corregir antes `docs/` o un script (la memoria no
debe citar algo que `docs/` no recoge).

---

## 0. Resumen

**Se puede cerrar ya** (todo medido o decidido y aplicado): la Basys 3
entera (implementación, frecuencias, O5 40/40 tres veces, jitter, SP
800-90B, tabla O8, reinicios, tests de salud, raya de ~39,4 kHz como hecho
medido con origen abierto), las decisiones del 19-11 en el RTL (ro1 de 11 y
ro2 de 13 etapas, ÷16, `G_KD_MIN`/`G_KD_RESET`/`G_KD_MAX` 25/25/26 y
19/19/24 en la FPGA), el apéndice A, el recuento de bancos (tras repetirlos
en una sola tanda) y el área del motor (tras regenerar la tabla por bloque).

**No se puede cerrar todavía** (actualizado el 22-11 por la noche): H 0,60,
el periodo de ro2 y `cortes_salud.py` ya están cerrados (0,757 con 24 chips
en las cinco esquinas; T(ro2)/T(ro1) 1,175 simulado; peor chip de 11
etapas). Queda el factor de peor chip del divisor, heredado del Monte Carlo
de 5 etapas, y el caudal y las falsas alarmas del integrado (E16, E17)
escritos en la memoria.

**Hallazgos que no estaban en la lista de tareas:**

1. La memoria ya contiene resultados de la **Basys 2** sin decir que lo son:
   `ch4_engine.tex:157-158` (falsa alarma "every few minutes"), `:212`
   ("8.7 kbit/s, the FPGA rate", que es la Basys 2 a `kd 14`), `:220-224`
   (correlación por el CE), `ch7_results.tex:266` (sesgo del 0,4 % "on the
   FPGA"). Hay que atribuirlos o sustituirlos al decidir qué va de la Basys 2
   (tarea 11).
2. `ch4_engine.tex:202-204` dice que el divisor arranca en su **máximo**;
   ya no: arranca en 25 con máximo 26 (FPGA: 19 con máximo 24).
3. `ch5_verification.tex:89` dice "70 % biased" en la tabla de bancos; el
   banco usa el 80 % desde el 16-11 (`ch4_engine.tex:230` ya dice 80).
4. `ch5_verification.tex:60-61`: "instantiate with 32 bytes of entropy" →
   son 48 (384 bits) desde el 16-11.
5. `ch7_results.tex:337`: "a 256-bit seed" → 512 bits (384 + 128).
6. `analysis/cortes_salud.py:50` fija `P_PEOR_CHIP = 1 - 0.372` (8 chips de
   5 etapas): la comprobación "el peor chip queda sobre la H declarada" que
   cita `ch7_results.tex:389-391` hay que rehacerla con el Monte Carlo de 11
   etapas (con el de 5 etapas de 24-28 chips habría fallado: peor chip
   0,3385, H 0,596).
7. `results/run_tb_todos.log` (19-11) tiene `tb_basys3_top` en fallo ("file
   has changed and must be reanalysed"); pasó aparte
   (`run_tb_basys3_top_1911.log`, 4/4). Para citar "12 bancos" hace falta una
   tanda limpia.
8. `docs/mapa_registros.md` sigue desfasado en dos sitios que la memoria
   copiaría: "Restricción de tasa" (anillo a ~700 MHz, sin preescalador) y
   "Rearme" (ritmos con 2²³ y ≤ 0,41 kbit/s). Línea 16 ("con V_DD ± 10 % es
   23") es del anillo de 5 etapas.
9. La captura larga de la Basys 3 (8 378 368 bits) es a `kd 16`, que con la
   Q blanca medida es H_∞ ≈ 0,47: para O8 a esa longitud falta una captura a
   `kd 19` (unas 6 h a 205 MHz) o decir explícitamente que esa columna habla
   de la batería, no de la fuente.
10. El protocolo de `ch7_results.tex:624-660` se fijó antes de los datos y
    no se siguió en tres pasos (§2, cap. 7): hay que declararlo.

---

## 1. Evidencia: estado de cada bloque

Las filas del §2 remiten a estas claves.

| Clave | Qué | Cifra y fuente | Estado |
|---|---|---|---|
| E1 | Implementación en la Basys 3 | Vivado 2025.2 en Ubuntu 26.04 (`LOCPATH`, `LD_LIBRARY_PATH`); tres arreglos (pblocks sin `CONTAIN_ROUTING`, anillos 11/13, APT sin restas); 4 011 LUT (19 %), 4 561 FF, sin BRAM (variante normal, 17-11); 19-11 silenciosa con restricción de 4,5 ns y comprobación en `build.tcl`: WNS +0,524 ns (`docs/basys3.md`, "Implementación con Vivado", "19-11-2026") | C. Releer la utilización del bitstream del 19-11 (`synth/basys3/build/G_QUIETO_true_G_MEDIDOR_false/`) para que la tabla sea del diseño final |
| E2 | O5 en placa | 40/40 CMAC = mbedtls, dos claves, `aleatorio`, `cero`: 17-11 (libre), 18-11 (`ro_bel`), 19-11 (`G_KD_MIN` 19; `kd 18` rechazada, `kd 25` ignorado con `DIAG.rechazada`) (`docs/basys3.md`; `results/basys3_o5_consola_*.txt`) | C. Vectores de respuesta conocida en placa: imposibles por el mapa (no se carga clave ni semilla); cubiertos en simulación |
| E3 | Frecuencias de los anillos | 5/7: 357,8 / 291,8 MHz; 11/13 con LUT combinadas: ro2 130,0 MHz; `ro_bel.xdc`: ro2 207,2 / ro1 167,2 MHz (display), 205-207 MHz (flujo) (`docs/basys3.md`, "Frecuencias") | C (ro1 de la variante libre 11/13 sin medir) |
| E4 | Jitter en la FPGA | Q por periodo de ro2 1-8·10⁻⁵ según método (repetible ±0,3-4 %), b 1,6-2,1, residuo 5-250× el ruido; frecuencímetro ×4,4 con colocación fija; **Q blanca (espectro de fase) 0,6-1,1·10⁻⁶** (silenciosa `ro_bel`; revisada 0,80-0,88, por banda 0,63-1,14), 19-11: 0,95-1,35·10⁻⁶ (`docs/basys3.md`, "Suelo blanco medido") | Medida C; interpretación P: el suelo incluye componentes del estimador (Q por arriba); la Q de la variante normal no es determinable; `espectro_fase.py --calibra` sin `--nu/--sdnu` ni sesgo (las cifras revisadas salen de scripts no versionados de la revisión): **H** llevar ese cálculo al script antes de citar la cifra |
| E5 | Divisor de la FPGA | `CFG_KD` 19 (H_∞ 0,996 con la cota 0,6·10⁻⁶; ≥ 20 con factor 2 en Q) (`docs/basys3.md` lectura 4; `results/cfg_kd_suelo_blanco.txt`) | C como decisión de Mario (19-11) |
| E6 | SP 800-90B en la Basys 3 | libre: `kd 8/10/11` (trozos) 0,125 / 0,558 / 0,786, `kd 12-16` 0,819-0,879; `ro_bel`: `kd 10/11` 0,430 / 0,695, `kd 13-16` 0,815-0,876, **`kd 17-19` 0,864 / 0,833 / 0,857**; larga `kd 16` 0,932 (libre) y 0,880 (`ro_bel`) | C. Lectura cerrada: la batería no distingue `kd 16` (H_∞ 0,47) de `kd 19` (0,9996) |
| E7 | Tabla O8 | `results/tabla_o8.md`: H asignada a 10⁶ Basys 3 `ro_bel` `kd 17-19` 0,857 (0,833-0,864), ESP32 0,848, ideal 0,847; MCV, Markov, MultiMMC, LZ78Y separan la FPGA por el sesgo (z 11-12) | C a 10⁶. A 8,4·10⁶ solo hay `kd 16` (ver hallazgo 9): D/P |
| E8 | Reinicios §3.1.4 en la FPGA | `kd 16` libre: H_r 0,843, H_c 0,892 ≥ H_I/2; `kd 19` `ro_bel`: H_r 0,854, H_c 0,830; 1 000 arranques distintos, Hamming 511,9 ± 16,0 (`results/fpga_reinicios/`) | C |
| E9 | Tests de salud en placa | libre: RCT a `kd 8`; `ro_bel`: ninguna alarma ni a `kd 8` (H 0,186, ρ₁ −0,54) | C. Justifica `G_KD_MIN` |
| E10 | Sesgo y correlación Basys 3 | unos 0,4951-0,4963 (libre), 0,5054-0,5060 (`ro_bel`), 0,4966 (19-11); normal 0,513 / 0,519; ρ₁ ≈ 0 (\|z\| ≤ 1,4) con muestreo libre | C |
| E11 | Raya de ~39,4 kHz | línea estrecha, no es el tráfico I2C durante la captura (`crudoq`), la carga no cambia su amplitud y la mueve 0,9 %; portadora ~480 kHz ± 39,5 kHz; origen sin identificar | C como medida; origen abierto (se dice así) |
| E12 | Decisiones del 19-11 en el RTL | ro1 11, ro2 13, `G_PRESC_RO2` 4 (÷16), `G_KD_MIN/RESET/MAX` 25/25/26 (`basys3_top` 19/19/24); bancos y FPGA en verde (`docs/decisiones_pendientes.md`) | C. Los bancos del motor fijan ro2 en 5 etapas (tiempo de simulación): decirlo |
| E13 | SPICE de ro1 de 11 etapas | ss −40 °C 1,08 V, 8 realizaciones: T 1 240,9 ps, σ 214,9 ± 4,0 fs, Q 2,65-3,41·10⁻⁸; `CFG_KD` 24 → H_∞ 0,99973 peor chip, 25 ≈ 1 (`docs/anillo_ihp.md` §4.4, `results/anillo_ihp_divisor_e11.txt`) | **P**: T(ro2)/T(ro1) = 13/11 estimado (hoy, 22-11, corren `anillo_ihp_periodo_*_e11/e13` en tt27, ff125 y ss −40: sin documentar); factor de peor chip 1,175 del Monte Carlo de 5 etapas; solo la peor esquina |
| E14 | Monte Carlo del biestable, 11 etapas | 24 chips en cada esquina: sf 125 °C 1,08 V / 1,2 V, ff −40 °C 1,32 V, ff 125 °C 1,32 V, tt 125 °C: H 0,757 / 0,822 / 0,868 / 0,838 / 0,851; **H declarable 0,757** (oficial, todos los chips; 0,704 con σ alta); sensibilidad sin hueco > 0,025: 0,789 (`results/biestable_mc_e11.md`, `_sin_hueco.md`; regla en `docs/decisiones_pendientes.md`) | **C** (22-11). Decirlo: las tandas de sf 1,2 V difieren en media (Welch p 0,004) y un chip de tt 125 °C sale con P(1) 0,5278 |
| E15 | Monte Carlo del biestable, 5 etapas | H declarable 0,532 (sf 1,08 V, 24 chips), 0,568 (sf 1,2 V, 28), 0,653 (ff), 0,803 (tt) (`results/biestable_mc.md`); sin huecos > 0,025, 0,530 (`results/biestable_mc_sin_hueco.md`) | C. Es lo que obligó a alargar ro1; la memoria no lo recoge |
| E16 | Caudal y tiempos del integrado con `CFG_KD` 25 | no está en `docs/`. Cuenta mía [ESTIMADO]: 2²⁵ periodos de ro2 de 13 etapas = 49 ms en ss −40 °C 1,08 V (T(ro2) ≈ 13/11 × 1 240,9 ps) → ~20 bit/s; tt 27 °C ≈ 33 bit/s y ff 125 °C ≈ 45 bit/s con los periodos sin ruido de las tandas de hoy. Siembra de 512 bits 11-25 s; test de arranque (1 024 bits) 23-50 s. Frente a 0,20-0,41 kbit/s y 2,6 s que dice la memoria | **H + P**: calcularlo en `docs/anillo_ihp.md` §4.4 con los periodos simulados de ro2 de 13 etapas cuando acaben |
| E17 | Falsas alarmas con 51/766 | memoria: peor chip ~8/año a 8,7 kbit/s (P(1) 0,372) | **H + P**: rehacer con el Monte Carlo de 11 etapas, la Basys 3 a `kd 19` (~0,39 kbit/s) y E16; actualizar `cortes_salud.py` y `docs/mapa_registros.md` "Rearme" |
| E18 | Área | `motor_top` **95,53 kGE** (ro2 13), `motor_top_aes11` 104,60, con FIFO 119,10; antes del 19-11 95,09 (+0,5 %) (`results/sintesis_19_11_ro2_13.log`) | C para el motor. **H**: regenerar la tabla por bloque y `results/sintesis_sg13g2.csv` con el RTL actual (semilla de 512, contador de 26 bits, ÷16); el CSV no se tocó a propósito |
| E19 | Tiempos del dominio de ro2 en el integrado | contador de 26 bits 1,53 ns; biestable sg13g2 ~0,37 ns frente a 0,366 ns de ro2 de 5 etapas; con 13 etapas (~0,95 ns) ×2,6 de margen [ESTIMADO, Yosys + ABC, biblioteca típica] | P: sin biblioteca lenta, 1,08 V 125 °C sin comprobar; se dice como estimación |
| E20 | Bancos | 12 bancos, 255 comprobaciones [ok] (motor 88, solo fuente 21, ERO 12, Basys 2 7, Basys 3 4...), PSL 14/14 y 8/8 (motor), 4/4 y 2/2 (solo fuente), 1/1 (I2C) | **H**: repetir los 12 en una tanda (`tb_basys3_top` falló por reanálisis en `run_tb_todos.log`) |
| E21 | Esquemático y plano | `results/basys3_esquema/`, `results/basys3_plano/` (18-11, antes de los cambios del 19-11) | C con la fecha; mejor regenerarlos del bitstream del 19-11 (`esquema.tcl` necesita `-mode gui`). Foto del montaje: la hace Mario |
| E22 | Basys 2 | todo en `docs/basys2.md`, provisional por decisión del 14-11 | **D** (tarea 11): qué entra |
| E23 | Medidor (ESP32-C3) con el motor real | no hecho | Opcional; si no se hace, se dice |

---

## 2. Por capítulo: qué está desfasado

Columnas: dónde (EN), qué dice, qué debería decir y fuente, evidencia (§1)
y estado. Las equivalencias en español van en §5.

### Resumen / Abstract (`tfm_main.tex`)

| Dónde | Dice | Debe decir | Ev. | Estado |
|---|---|---|---|---|
| `:109`, `:139` | comentarios "[DRAFT -- to be finalized with measured results]" | quitar al cerrar | — | al final |
| `:113-118` | jitter "extracted from simulation" | y medido en la FPGA (suelo blanco) | E4 | C |
| `:130-132` | "so far on a model of the engine; a Basys 3 FPGA is the vehicle prepared for the run on hardware" | el motor entero corre en una Basys 3 y el ESP32 recalcula 40/40 etiquetas; campaña de entropía en la FPGA y comparación con el ESP32 | E2, E6-E8 | C |
| `:163-165` (Resumen ES dentro del fichero EN) | lo mismo en español | idem | | C |

### Capítulo 1 (`ch1_intro.tex`)

| Dónde | Dice | Debe decir | Ev. | Estado |
|---|---|---|---|---|
| `:4` | comentario de borrador | quitar | — | al final |
| `:80-83` | "millions of test vectors ... in minutes" (menor de la revisión del 10-11) | ajustar a lo que se hizo | — | C |
| `:101-103` (O5) | "known-answer tests, cross interoperability and challenge-response" en la FPGA | los KAT en placa no caben en el mapa (no se carga clave ni semilla): reformular O5 o decir en la tabla de estado que los KAT se cubren en simulación | E2 | **D** (punto 5 de la revisión del 10-11 frente al objetivo oficial) |
| `:113-119` | mínimo defendible O1-O3 + O5; "if the accumulation exponent on hardware is two ... that is a finding" | O5 cumplido; enlazar con lo medido: b 1,6-2,1 y residuo del modelo, explicado en parte por una modulación de ~39,4 kHz; el suelo blanco se saca en frecuencia | E2, E4, E11 | C (medida) / P (interpretación: decirlo así) |

### Capítulo 2 (`ch2_soa.tex`)

| Dónde | Dice | Debe decir | Ev. | Estado |
|---|---|---|---|---|
| `:563-582` (hueco) | ítem 1: jitter del XC7A35T en unidades absolutas "with the thermal and flicker components separated" | el ítem promete; lo medido es un suelo blanco por espectro de fase con el modelo sin describir la forma de c(M). O se suaviza el ítem o el cap. 8 dice qué parte se cumplió | E4 | D (redacción) |

### Capítulo 3 (`ch3_entropy.tex`)

| Dónde | Dice | Debe decir | Ev. | Estado |
|---|---|---|---|---|
| `:4` | "[DRAFT v1 -- theory and simulation only; hardware figures pending]" | quitar | — | al final |
| `:36-45` | jitter de un anillo en 28 nm "2-4 ps [EST]" | añadir lo medido: σ ≈ 4-5 ps por periodo de 4,9 ns (Q blanca 0,6-1,1·10⁻⁶ por periodo de ro2) [MEDIDO, calibración SIMULADA] | E4 | C (con la salvedad de E4) |
| `:178-181` | b = 1 térmico, b = 2 flicker/global | referencia adelante al cap. 7: en placa b 1,6-2,1 | E4 | C |
| `:270-283` (§`sec:kd`) | divisor 3·10⁴-5·10⁵ y 1-20 kbit/s en 28 nm; "seeding ... 256 bits ... about 512 raw bits at H 0,98 ... 0.03 and 0.5 s per seed" | lo medido cae en el extremo alto del rango: K* = 0,2286 / 0,6·10⁻⁶ ≈ 3,8·10⁵ → `CFG_KD` 19 (5,2·10⁵), 391 bit/s con ro2 a 205 MHz; semilla de 512 bits crudos (384 + 128) con H declarada 0,60; 1,3 s por siembra en la FPGA (+2,6 s de test de arranque), 11-25 s en el integrado | E4, E5, E16 | C (FPGA) / P (integrado, E16). Es también M7 de la revisión del 10-11 |
| `:275-276` | "K_D ≈ 430 000 for σ = 5.01 ps over T = 7.81 ns" | rehacer la cuenta (la revisión del 10-11 saca ≈ 555 500, M6) | — | H (cuenta) |

### Capítulo 4 (`ch4_engine.tex`)

| Dónde | Dice | Debe decir | Ev. | Estado |
|---|---|---|---|---|
| `:31-46` (fig. `fig:engine`) | RO1, RO2 → ERO ÷K_D; sin flujo | añadir el preescalador ÷16 de RO2 (integrado) y la cola del flujo continuo (instrumentación) | E12 | C |
| `:56-69`, `:82-84`, `:125-126` | restos de M1 (SHA "~25 to ~13", "the ESP32 decrypts", 1,16 Gbit/s con el núcleo de 51 ciclos, ciclos 209/53 sin verificar con el AES de 32 bits) | según la revisión del 10-11 | — | H (comprobar ciclos) |
| `:150-153` | nota no impresa PROVISIONAL (H 0,60 sobre 8 chips) | se quita: el Monte Carlo de 11 etapas cerró el 22-11 (24 chips, cinco esquinas, H 0,757) | E14 | C |
| `:157-158` | "At 2⁻²⁰ the FPGA prototype raised a repetition false alarm every few minutes" | atribuirlo a la Basys 2 (`kd 14`, ~8 min) o quitar "FPGA" genérico | E22 | D |
| `:159-163` | sesgo del biestable: "worst of eight dies at 125 °C down to 0.67 [SIM]", "A first revision to H = 0.80 ... five of those eight dies" | Monte Carlo de 5 etapas (24-28 chips por esquina) → H declarable 0,532 < 0,60 → criterio fijado → se alarga ro1 a 11 etapas → Monte Carlo de 11 etapas H 0,757 (24 chips, críticas) | E14, E15 | **P** |
| `:164-172` | semilla de 512 bits, 214 bits de entropía al límite del APT | sigue valiendo (depende solo de los cortes) | — | C |
| `:202-204` | "the sampling divider resets to its maximum" | arranca en 2²⁵ (máximo 2²⁶; FPGA 2¹⁹, máximo 2²⁴); un valor por encima del máximo se ignora con `DIAG.rejected` | E12 | C |
| tras `:204` (regla nueva) | — | **divisor mínimo en hardware**: `sembrar`, `resembrar` y el flujo se rechazan por debajo de 2²⁵ (2¹⁹ en la FPGA). Porqué medido: con colocación fija los tests de salud no saltan ni a 2⁸ (SP 800-90B 0,186, bits que alternan, ρ₁ −0,54): el mínimo es la única protección frente a un maestro que escriba un divisor bajo | E9, E12 | C |
| `:211-216` | "independent bits at 8.7 kbit/s, the FPGA rate", "worst simulated die about eight ... a year", "integrated circuit's 0.2-0.4 kbit/s, twenty to forty times fewer" | 8,7 kbit/s es la Basys 2; Basys 3 a 2¹⁹ ~0,39 kbit/s; integrado ~0,02-0,045 kbit/s; rehacer las tasas con el biestable de 11 etapas | E16, E17 | **H + P** |
| `:218-225` | muestreo sin habilitación: "On the FPGA ... ρ₁ ≈ 0.005 ... two implementations" | es la Basys 2 (XC3S100E); añadir la confirmación en otra familia: Basys 3 sin ρ₁ (\|z\| ≤ 1,4 en flujos, 0,8 a `kd 17-19`, 1,1 en la larga) | E10, E22 | C (+ D sobre cómo nombrar la Basys 2) |
| `:241-248` | el cruce bit a bit exige "K_D ≥ 64 for a ~700 MHz sampling ring" | en el integrado el dominio del anillo corre a RO2/16 (divisor efectivo mínimo 2⁴; `docs/mapa_registros.md` línea 16); en la FPGA, sin preescalador, ro2 a 205 MHz. El mínimo que manda ya no es el del cruce sino el de entropía | E12 | **H** (`docs/mapa_registros.md` "Restricción de tasa" está desfasado) |
| `:248-251` | buffer escrito "in the ring domain at full rate" | a RO2/16 en el integrado, a RO2 en la FPGA | E12 | C |
| `:268-270` | flujo usable "at dividers of about 2¹³ and above [EST]" | medido: desde 2¹³ con ro2 a 205 MHz (2¹² desborda la UART a 115 200 baudios; con 130 MHz cabía); con el mínimo de 2¹⁹ el flujo por debajo pide la variante de caracterización (`G_KD_MIN=6`) | E6, E12 | C |
| `:317-323` | "the same cross-check the ESP32 will perform on hardware" | lo hizo: 40/40 en tres sesiones | E2 | C |

### Capítulo 5 (`ch5_verification.tex`)

| Dónde | Dice | Debe decir | Ev. | Estado |
|---|---|---|---|---|
| `:6` | "FPGA bring-up section pending hardware" | quitar | — | al final |
| `:30-33` | "the ESP32 recomputes ... every result" (M2) | lo que recalcula: etiquetas CMAC; la clave se lee en modo test | E2 | C |
| `:60-61` | "instantiate with 32 bytes of entropy and 16 of nonce" | 48 bytes (384 bits) y 16 | — | C (error actual) |
| `:72-73` | "summarizes the nine benches" | doce | E20 | **H** (tanda limpia) |
| `:84-92` (tabla `tab:tb`) | 9 filas; "Health tests ... 70 % biased ... 15/15"; "Whole engine ... 85/85"; "Board wrapper 4/4" | añadir `tb_ero_core` 12/12 (las dos formas de muestrear, mismo bit), `tb_motor_solo_fuente` 21/21 (PSL 4/4, 2/2), `tb_basys2_top` 7/7 (si entra la Basys 2); salud: **80 %**; motor **88/88** (CFG_KD arranca en 25, > máximo ignorado y rechazado, 26 aceptado); decir que los bancos del motor fijan ro2 en 5 etapas | E12, E20 | H |
| `:163-168` | dos obligaciones del maestro pasadas al hardware | tres: añadir el máximo de `CFG_KD` | E12 | C |
| `:189-211` | órdenes del verificador; "builds with ESP-IDF 5.3.5 into a 231 kB image; running it awaits the hardware"; `:194-196` relectura de la clave (M2) | órdenes nuevas (`kd`, `flujo`, `crudoq`, `cero`, `borrar`, `rearmar`); grabado y usado en la Basys 3 (compilado con 5.3.2); el hallazgo de `CONFIG_FREERTOS_HZ=100` (duraciones con resolución de 10 ms; ninguna medida afectada salvo esa resolución) como resolución de instrumento | E2 | C |
| `:262-266` | "among eight valid ones" (M2) | comprobar el número en `results/host_check.log` (CLAUDE.md dice 9 válidas) | — | H |
| `:294-297` | "What remains unverified is the engine itself on a board" | el motor está verificado en placa; lo que no: el medidor (ESP32-C3) con el motor real | E2, E23 | C |
| `:299-313` (§`sec:bringup`) | "Pending hardware" | sección nueva: Vivado 2025.2 en Linux, los tres arreglos y su porqué (lazo sin rutar, dominio de ro2 que no cerraba con 5/7 etapas, LUT combinadas → `ro_bel.xdc`), comprobación de los anillos en la netlist implementada (lección de la Basys 2: XST los quitó), utilización y tiempos, frecuencias medidas, restricción de 4,5 ns con su comprobación, O5. Con el esquemático, el plano y la foto | E1-E3, E12, E21 | C |

### Capítulo 6 (`ch6_asic.tex`)

| Dónde | Dice | Debe decir | Ev. | Estado |
|---|---|---|---|---|
| `:39-55` | motor digital ≈ 46 kGE; el búfer "occupies a block RAM at no logic cost" en la FPGA | recalcular con la tabla nueva (≈ 95,53 − 46,76 ≈ 48,8 [ESTIMADO hasta regenerar]); en Vivado `trng_capture` va a RAM distribuida (156 LUT / 44 FF), sin BRAM | E1, E18 | H |
| `:57-81` (tabla `tab:synth`) | filas del 28-10: motor 92,53, ERO "24-bit divider" 0,33 | regenerar todas con el RTL actual: motor 95,53, `aes11` 104,60, ERO con contador de 26 bits y ÷16 | E18 | **H** |
| `:102-107` | "The table predates the 512-bit seed ... 95.1 kGE" | desaparece al regenerar; decir el +0,5 % del 19-11 (95,09 → 95,53) | E18 | H |
| `:142-147` | 2355 (2483) biestables del generador | de la tabla nueva | E18 | H |
| `:150-162` | 69 → 46 → ≈ 42 kGE; "0.72 mm² ... fits several times over" (M3: el bloque mínimo de IHP es 0,8 mm²) | rehacer con las cifras nuevas | E18 | H |
| §`sec:ro_silicon` `:164-192` | tres puntos de la bibliografía | añadir lo que el diseño ya aplica o pide: ro1 de 11 y ro2 de 13 (distintos para que no se enganchen), ÷16 y los tiempos del contador [ESTIMADO, sin esquina lenta], buffer a la salida del anillo (el biestable tira del nudo 2-3 ps), `ro_mon` sin carga, alimentación o anillo de guarda propios (en la FPGA la lógica colgada cambia el ruido de fase ×4,4 y hay una raya de ~39,4 kHz que viene de fuera) | E11, E12, E19 | C (decisiones) / P (tiempos, como estimación) |
| `:219-221` | jitter "that the device itself can measure (simulated in this work)" | medido en el prototipo FPGA; simulado para el integrado | E4 | C |

### Capítulo 7 (`ch7_results.tex`)

| Dónde | Dice | Debe decir | Ev. | Estado |
|---|---|---|---|---|
| `:4-10` | "it has not yet run on the FPGA ... the entropy campaign ... is stated as a protocol" | ha corrido; la campaña tiene datos | todos | C |
| `:27-47` (tabla `tab:status`) | O1 met (5 etapas); O4 "nine testbenches"; **O5 partial**; **O6 pending**; O7 met (92,5); **O8 partial** | O1: añadir ro1 de 11 etapas en la peor esquina y el biestable sg13g2 (el "sampler" de O1 a nivel de transistor, sin ruido); O4: doce; **O5 met** (salvo KAT en placa, D); **O6 met** con la salvedad del modelo; O7 95,5; **O8 met** (tabla O8 y reinicios) | E2, E4-E8, E13, E14, E18, E20 | C (O4 tras E20; O1 con E13/E14 como P) |
| `:52-54` | "What O5 still lacks is the bring-up" | alcanzado | E2 | C |
| §`sec:ihp_ring` `:117-178` | anillo de 5 etapas | se queda como caracterización; **subsección nueva "Eleven-stage ring"** con §4.4: T 1 240,9 ps, σ 214,9 ± 4,0 fs, Q 2,65-3,41·10⁻⁸, ley 1/N comprobada (6,0 × 5/11 = 2,7), tabla `CFG_KD` 22-25; ro2 13/11 [ESTIMADO] | E13 | **P** |
| `:174-178` | "It now has 24 bits" | 26 bits (`G_KD_MAX`) | E12 | C |
| `:190-204` | divisor fijo 2²², 2²³ con ±10 %; "0.20 to 0.41 kbit/s, about 2.6 s for the 512 bits" | con 5 etapas; el diseño ya no lo usa: con 11/13 basta `CFG_KD` 24 y el mínimo es 25 (factor 2); caudal ~20-45 bit/s, siembra 11-25 s | E13, E16 | **P + H** |
| `:217-220` | "The divider register resets to 2²⁴" | 2²⁵ | E12 | C |
| `:245-253` | "the 24-bit counter covers it" (factor 2 cicloestacionario) | 26 bits; ojo: el factor 2 de `G_KD_MIN` 25 sobre 24 y el posible factor 2 cicloestacionario son el mismo margen, no dos | E13 | C |
| `:255-266` (ciclo de trabajo) | anillo de 5 etapas; "on the FPGA, where the measured bias is 0.4 %, it is 0.989" | ese 0,4 % es la Basys 2; Basys 3: 0,4954-0,5060 (silenciosa) → 0,983; 0,513-0,519 la normal; el signo cambia con la implementación. El ciclo de trabajo del anillo de 11 etapas no está simulado aparte (el Monte Carlo del biestable lo incluye: decirlo) | E10, E14 | C (FPGA) |
| `:268-291` (biestable) + nota `:268-271` | 8 chips, 0,672, "A slower ring or RO1/2 would cure it ... The design instead declares H = 0.60" | reescribir: Monte Carlo de 5 etapas → 0,532 < 0,60 → criterio → ro1 de 11 etapas → 0,757 con 24 chips; el diseño hace las dos cosas (anillo más lento **y** H 0,60). Quitar la nota cuando cierre | E14, E15 | **P** |
| §`sec:opoint` `:293-339` | tabla con RO2 a 500 MHz [EST]; "a 256-bit seed" | mantener la tabla como diseño; añadir los puntos reales: FPGA 2¹⁹ (391 bit/s), integrado 2²⁵; semilla de 512 bits | E5, E16 | C / P |
| `:357-368` (tabla `tab:verif`) | "9/9 pass"; `cortes_salud.py` 7/7 | 12/12; `cortes_salud.py` 9/9 hoy, pero hay que actualizarlo (hallazgo 6) y repetir; repetir `ero_model.py` y `jitter_estimator.py`; añadir `espectro_fase.py --valida` | E17, E20 | H |
| `:389-391` | "the worst simulated die of the sampling flip-flop stays above the declared H" | con el Monte Carlo de 11 etapas | E14 | **P + H** |
| `:416` (tabla `tab:se`) | "bound derived from the jitter (simulated here, measurable in the device)" | medido en el prototipo FPGA; simulado para el integrado | E4 | C |
| `:463-472` | "the engine's raw bits, when the campaign ... produces them, must be run through the same battery" | hecho: tabla O8 | E7 | C |
| `:519-520` | "the engine at the recommended 2²³" | 2²³ era el divisor con 5 etapas; o se repite `fuente_simulada_90b.py` con la Q de 11 etapas a 2²⁴-2²⁵, o se dice que la simulación se hizo con el anillo anterior. Añadir la confirmación en placa: `kd 16` (H_∞ 0,47) y `kd 19` (0,9996) dan lo mismo | E6 | C (confirmación) / D (repetir o no) |
| §`sec:uncertainty` `:570-622` | "Min-entropy of the built device. Not yet bounded." | FPGA: Q blanca medida con su incertidumbre y la salvedad del estimador; integrado: simulado (11 etapas, ro2 estimado, biestable parcial). Añadir una entrada "sesgo del biestable" | E4, E13, E14 | C / P |
| §`sec:protocol` `:624-660` | "The pending campaign", cinco pasos fijados de antemano | "The FPGA campaign": resultados por paso y **desviaciones declaradas**: (2) el ajuste σ²(t) = at + bt² no describe los datos; el suelo blanco sale de un método espectral introducido tras ver los datos (revisión del 18-11), validado con bits simulados, y se lleva al divisor la cota baja; (3) los cortes no salen de la H de la FPGA: H 0,60 la fija el biestable del integrado; (5) no se comparó "separados frente a adyacentes" sino colocación fija frente a libre, variante normal frente a silenciosa y la prueba de carga | E4-E9, E11 | C |
| sección nueva | — | **comparación O8** con la tabla O8 reducida y el cuadro de reinicios ESP32/FPGA | E7, E8 | C (10⁶) / D (8,4·10⁶) |

### Capítulo 8 (`ch8_concl.tex`)

| Dónde | Dice | Debe decir | Ev. | Estado |
|---|---|---|---|---|
| `:4-6` | comentario [DRAFT] con [PENDING] | quitar | — | al final |
| `:18-32` (O1-O3) | anillo de 5 etapas; "a fixed divider of 2²³ ... 0.20-0.41 kbit/s" | los 176,7 fs de 5 etapas se quedan como caracterización; divisor del integrado con ro1 11 / ro2 13: `CFG_KD` 24 basta, mínimo 25; caudal nuevo | E13, E16 | **P** |
| `:34-44` | la batería no sustituye al modelo (simulado) | añadir la confirmación en placa (`kd 16` frente a `kd 19`) | E6 | C |
| `:59-65` (O7) | 92,5 / 46 / 23 / 42 kGE | 95,5 y el resto con la tabla nueva | E18 | H |
| `:76-83` | nota no impresa de la Basys 2 | sustituir según la decisión de la tarea 11 | E22 | D |
| `:84-91` (O5, O6) | [PENDING] | O5: 40/40 en tres sesiones, dos claves, zeroización, rechazos del divisor en placa; O6: jitter (por método, residuo, suelo blanco, raya), SP 800-90B, salud, reinicios, divisor 2¹⁹ | E1-E11 | C |
| `:93-97` (O8) | [PENDING]; "the informative points are the low dividers, where the battery can contradict it" | la H asignada no separa FPGA, ESP32 ni ideal; los estimadores sensibles al sesgo sí separan la FPGA; en divisores bajos la batería **sobreestima** (como predecía la simulación); lo que separa las fuentes es el modelo y el test de reinicios | E6-E8 | C |
| `:101-116` (aportaciones) | cuatro | añadir: suelo de jitter blanco del Artix-7 medido dentro del chip (hueco 1 del cap. 2, con su salvedad); tests de salud ciegos al régimen anticorrelado → divisor mínimo en hardware; Monte Carlo del biestable → longitud del anillo; reinicios de la FPGA frente al ESP32 | E4, E8, E9, E14 | C / P |
| `:121-139` (trabajo futuro) | "Continuous capture on the board ... not yet run" | hecho; añadir: origen de la raya, modelo de la forma de c(M), ro2 de 13 etapas y esquina lenta, `T_CLK` al azar en el Monte Carlo del biestable, medidor con el motor real | E11, E13, E14, E23 | C |

### Apéndices (`appendices.tex`)

| Dónde | Dice | Debe decir | Ev. | Estado |
|---|---|---|---|---|
| `:35-38` (`CFG_KD`) | "effective range 0-24 (larger values act as 24). Resets to 24." | rango 0-26; mayor que el máximo se ignora y levanta `DIAG.rejected`; arranca en 25 (FPGA 19, máximo 24); en el integrado ÷16: por debajo de 4 el divisor efectivo es 2⁴; sigue contando periodos de RO2 | E12 | C (fuente: `docs/mapa_registros.md` línea 16) |
| `:93-100` (`tab:app_diag`) | bits 0-2 | bit 3 `solo_fuente` (constante; 0 en el motor entero) si entra la variante de la Basys 2; si no, "reserved, reads 0" | E22 | D |
| `:146-149` | `G_KD_MIN` "6 by default, below which the bit-level clock-domain crossing loses bits" | 25 (integrado), 19 (FPGA); la razón es la entropía (los tests de salud no ven el régimen de poco jitter); vale también para el flujo | E9, E12 | C |
| `:219-221` | "212 in total over nine benches" | 255 en doce, con las PSL de los tres bancos que las tienen | E20 | H |
| `:274`, `:294` | "seven jobs", "9 benches" | comprobar qué corre `.github/workflows/verifica.yml` (`rtl/run_tb.py` sin filtro: los doce) y que la CI de la rama esté en verde | E20 | H |
| `:325-332` | SPICE: `anillo_ihp_repeticiones.py` | añadir `--etapas`, `anillo_ihp_divisor.py`, `biestable_ihp.py` y `biestable_mc.py` | E13, E14 | C |
| `:339-341` | FPGA: Vivado "free tier" y `docs/instalacion_vivado_windows.md` (nunca ejecutado) | Vivado 2025.2 en Linux con los dos ajustes de entorno, `build.tcl` (`GENERICOS`, `ro_bel.xdc`, `SIN_BEL`), `openFPGALoader`/`djtgcfg`, y los scripts de campaña (`campana_motor.py`, `reinicios_fpga.py`, `espectro_fase.py`, `sesgo_correlacion.py`, `tabla_o8.py`); remitir a `docs/basys3.md` | E1 | C |

El capítulo del ESP32 (`esp32_blackbox.tex`) no necesita cambios por esto.

---

## 3. Figuras y tablas nuevas

| Qué | Origen | Dónde | Estado |
|---|---|---|---|
| Esquemático de bloques del motor en Vivado | `results/basys3_esquema/esquema_motor_top.pdf` | cap. 5 §`sec:bringup` (o junto a `fig:engine` en el cap. 4, como "lo mismo, elaborado") | C; mejor regenerado del 19-11 |
| Esquemático del envoltorio `basys3_top` | `results/basys3_esquema/esquema_basys3_top.pdf` | apéndice C o cap. 5 | C, opcional |
| Plano del XC7A35T (motor arriba a la izquierda, ro2 y ro1 en sus pblocks) | `results/basys3_plano/plano_basys3.pdf` | cap. 5 §`sec:bringup` | C; regenerar del 19-11 o fechar |
| Foto del montaje Basys 3 + ESP32 | Mario | cap. 5 | falta |
| `fig:engine` actualizada (÷16, cola del flujo) | TikZ en `ch4_engine.tex:25-51` | cap. 4 | C |
| Espectro de la frecuencia instantánea (raya de ~39,4 kHz, suelo blanco) | `analysis/espectro_fase.py` (hoy saca texto: hace falta un script de figura) | cap. 7, sección de la campaña | C tras E4-H |
| H SP 800-90B frente a `CFG_KD` medida en la Basys 3, sobre la curva H_∞ del modelo con la Q blanca y la banda de saturación | ampliar `analysis/fuente_simulada_figura.py` | cap. 7, junto a `fig:sim_90b` (es su contraste en placa) | C |
| P(1) del biestable por esquina, 5 frente a 11 etapas | `results/biestable_mc*.md` / CSV | cap. 7 §`sec:ihp_ring` | **P** (24 chips) |
| Tabla: implementación en Vivado (utilización por bloque, tiempos por reloj) | `docs/basys3.md`; releer el informe del 19-11 | cap. 5 | C |
| Tabla: frecuencias de los anillos por configuración | E3 | cap. 5 | C |
| Tabla: Q por método (conjunto, global, varianza, blanca) y repetibilidad | E4 | cap. 7 | C |
| Tabla: `CFG_KD` 16-20 → H_∞ con Q blanca 0,82·10⁻⁶ y cota 0,6·10⁻⁶ | `results/cfg_kd_suelo_blanco.txt` | cap. 7 | C |
| Tabla: SP 800-90B de la Basys 3 (trozos y flujos, libre y `ro_bel`, `kd 17-19`) con fracción de unos y ρ₁ | E6, E10 | cap. 7 | C |
| **Tabla O8** reducida: H asignada, MCV, Markov, MultiMMC, LZ78Y, p̂, z; columnas ESP32, Basys 3 `ro_bel` `kd 17-19`, ideal, iid con el sesgo | `results/tabla_o8.md` | cap. 7, sección O8 | C a 10⁶; la de 8,4·10⁶ según D (hallazgo 9) |
| Tabla: reinicios ESP32 (normal, sin ruido) frente a FPGA (`kd 16`, `kd 19`) | E8, `tab:esp32_restart` | cap. 7 | C |
| Tabla: anillo de 11 etapas, `CFG_KD` 22-25 | `results/anillo_ihp_divisor_e11.txt` | cap. 7 §`sec:ihp_ring` | **P** |
| Tabla: Monte Carlo del biestable, 5 y 11 etapas | E14, E15 | cap. 7 | **P** |
| `tab:synth` regenerada | E18 | cap. 6 | H |
| `tab:tb` con doce bancos | E20 | cap. 5 | H |
| `tab:status`, `tab:verif`, `tab:app_regs`, `tab:app_vectors` | §2 | caps. 7 y apéndices | C/H |
| Basys 2 frente a Basys 3 (si entra la Basys 2) | `docs/basys3.md`, "Basys 2 frente a Basys 3" | cap. 7 o apéndice | D |

---

## 4. "kd" y la notación del divisor

**Dónde está "kd" suelto en la memoria:** en el texto impreso, en ningún
sitio. Solo en la nota no impresa del cap. 8 (`ch8_concl.tex:80-81`; ES
`ch8_concl.tex:86-87`) y en la etiqueta `\label{sec:kd}`
(`ch3_entropy.tex:268`; ES `:282`), que no se ve. `CFG_KD` solo aparece en
el apéndice A (`appendices.tex:35, 147, 153, 172`). El problema vendrá al
pasar los resultados de la Basys 3, que en `docs/` van todos como "`kd N`".

**Ambigüedades que ya existen y que la Basys 3 agrava:**

- `K_D` cuenta periodos de **RO2** (`ch3_entropy.tex:24-26`), pero `Q_raw`
  se define como (σ/T)² "per period" sin decir de qué anillo
  (`ch3_entropy.tex:270`, `ch7_results.tex:308`). Con anillos iguales daba
  igual; con ro1 de 11 y ro2 de 13 etapas no: si solo se cuenta el jitter de
  RO1, Q = K_D · (T₂/T₁) · (σ₁/T₁)². `docs/anillo_ihp.md` §4.4 da Q por
  periodo de ro1; `docs/basys3.md` da Q "por periodo de ro2".
- `kd 0` en `docs/` es K_D = 1 (el método de Fischer y Lubicz,
  `ch3_entropy.tex:150`, `ch7_results.tex:636`), `kd 2` es K_D = 4.
- Hay tres H distintas: la del modelo (H_∞), la cifra de SP 800-90B y la H
  declarada para los cortes (0,60).
- En el integrado hay preescalador: el registro sigue contando periodos de
  RO2, no flancos del reloj preescalado.

**Propuesta** (para Mario; una vez en el cap. 3 y en el apéndice A, y el
mismo criterio en ES):

1. **K_D** es el número de periodos de RO2 entre dos muestras. **CFG_KD**
   es el valor del registro, n, con K_D = 2ⁿ. En el texto se escribe el
   divisor como potencia, "$K_D = 2^{19}$", y la primera vez de cada
   capítulo "$K_D = 2^{19}$ (\texttt{CFG\_KD} = 19)". En tablas, la columna
   se titula "$\log_2 K_D$" con una nota "= \texttt{CFG\_KD}". Nunca "kd".
   Un macro en el preámbulo (p. ej. `\newcommand{\kd}[1]{$K_D = 2^{#1}$}`)
   evita erratas; el nombre del macro no se imprime.
2. **Q** siempre con su anillo: $q_2$ = varianza de fase por periodo de RO2
   (lo que mide la FPGA), $Q = K_D\,q_2$; en el integrado se pasa de la
   σ de RO1 con el cociente de periodos, escrito una vez. Reservar
   $Q_{\mathrm{raw}}$ para el cap. 3 o retirarlo.
3. **H**: $H_\infty$ (modelo), $\hat H_{90B}$ (cifra de la batería),
   $H_{\mathrm{decl}}$ = 0,60 (cortes y semilla).
4. Los mínimos y máximos del divisor se nombran por su función ("minimum
   divider", "maximum divider"); los genéricos (`G_KD_MIN`, `G_KD_RESET`,
   `G_KD_MAX`, `G_PRESC_RO2`) solo en el apéndice A.
5. Al copiar de `docs/`: "`kd 19`" → "$K_D = 2^{19}$"; "`kd 13-16`" →
   "$K_D = 2^{13}$ to $2^{16}$"; "`kd 0`" → "$K_D = 1$".

---

## 5. Alineación del español con el inglés

Comprobado hoy sin compilar:

- **Cifras:** script que extrae todos los números de cada capítulo (sin
  comentarios, decimal normalizado) y compara EN con ES: **idénticos** en
  los caps. 1, 3, 4, 5, 6, 7 (EN `ch7_results` frente a ES
  `ch7_results_a` + `_b`) y 8. Diferencias solo de maquetación: apéndice
  (anchos de columna 0,53/0,66 en EN y 0,54/0,64 en ES) y un
  `\setlength{\tabcolsep}{4pt}` en la tabla `tab:ihp_ring` del ES.
- **Etiquetas, referencias y citas:** idénticas, en el mismo orden, en
  todos los capítulos citados y en los apéndices.
- **Notas no impresas:** las mismas en los dos (PROVISIONAL en cap. 4 y
  cap. 7, NOTA de la Basys 2 en cap. 8, comentarios de borrador en caps.
  3, 5, 8 y en el resumen).
- **Consecuencia:** todos los desfases del §2 están también en el ES. Las
  erratas del hallazgo 3 (70 % frente a 80 %), 4 (32 bytes) y 5 (semilla de
  256) están en los dos.
- **Dónde caen en ES** (las líneas del ES van entre 5 y 20 por detrás):
  - Resumen: `tfm_main_es.tex:116, 141-142, 157, 180`.
  - Cap. 4: nota PROVISIONAL `:160-163`, H 0,60 `:164`, falsas alarmas
    `:226-228`, cola del flujo `:292`.
  - Cap. 5: `:6`, §puesta en marcha `:327-343`.
  - Cap. 6: `:42-165`.
  - Cap. 7: estado `ch7_results_a.tex:25-56`, anillo de 5 etapas `:63-224`
    (2²³ y 2²⁴ en `:209, 222-224`), nota PROVISIONAL `:277-280`, biestable
    `:281-300`, verificación `:380-394`; `ch7_results_b.tex`: referencia del
    ESP32 desde `:1`, fuente simulada `:43-98`, "La campaña pendiente"
    `:180`.
  - Cap. 8: `:4-6`, nota de la Basys 2 `:82-89`, [PENDIENTE] `:90-104`.
  - Apéndices: `CFG_KD` `:33-36`, `G_KD_MIN` `:148-150`, recuento `:226`.
- **Al escribir:** el cap. 7 ES está partido en dos ficheros; las secciones
  nuevas de la campaña y de O8 van en `ch7_results_b.tex` (que empieza en
  `sec:esp32_ref`), la del anillo de 11 etapas y el biestable en
  `ch7_results_a.tex`. Mismo vocabulario fijado (`Q_{\mathrm{bruto}}`,
  reto-respuesta, bancos de pruebas) y las trampas de babel de CLAUDE.md.
  Cada cambio EN se lleva al ES en el mismo commit y se repite la
  comparación de cifras (hoy un script de 20 líneas fuera del repositorio;
  conviene versionarlo junto a `memoria/chk_tex.py`).

---

## 6. Orden de trabajo propuesto

**Fase 0: decisiones de Mario** (antes de escribir nada en `memoria/`)

1. Tarea 11: qué entra de la Basys 2 (propuesta: un apartado corto de
   contraste, con lo que ya está implícito en la memoria atribuido —
   correlación por el CE, falsa alarma del RCT a 2⁻²⁰, sesgo— y la tabla
   Basys 2 / Basys 3; el resto en `docs/`).
2. O5: reformular o anotar que los KAT en placa se cubren en simulación.
3. La notación del §4.
4. Captura larga a `kd 19` para O8 (~6 h de placa) o columna de 8,4·10⁶ a
   `kd 16` con su salvedad.
5. ~~Tratamiento de los chips con hueco de fase en el Monte Carlo~~:
   regla fijada el 22-11 antes del resultado (`docs/decisiones_pendientes.md`).
6. Repetir o no la fuente simulada con la Q de 11 etapas.

**Fase 1: dejar `docs/` y los scripts a la altura** (sin CPU pesada salvo
los bancos y la síntesis, que pueden esperar a que acaben las simulaciones)

7. `docs/mapa_registros.md`: "Restricción de tasa" con el ÷16 y "Rearme"
   con los ritmos nuevos (tras el paso 13).
8. `espectro_fase.py --calibra` con `--nu`, `--sdnu` y el sesgo; repetir la
   calibración y comprobar que da las Q revisadas.
9. Bancos: los doce en una tanda (`python rtl/run_tb.py`), log limpio;
   `verifica_top.py`; CI en verde.
10. Síntesis completa por bloque (`synth/sintetiza.py`), actualizar
    `results/sintesis_sg13g2.csv` y `docs/sintesis_resultados.md`.
11. Vivado: releer utilización y tiempos del bitstream del 19-11; regenerar
    esquemático y plano de ese bitstream (o fechar los del 18-11).
12. Cuentas M6 (Fischer y Lubicz) y M7 (tiempos de siembra), y ciclos del
    DRBG con el AES de 32 bits (M1).

**Fase 2: escribir lo cerrado** (EN y ES en el mismo commit por capítulo)

13. Cap. 5: `sec:bringup` nueva, `tab:tb`, firmware, erratas (32 → 48 bytes,
    70 → 80 %), con las figuras de esquemático, plano y foto.
14. Cap. 7: sección de la campaña FPGA (sustituye a `sec:protocol`, con las
    desviaciones declaradas), sección O8 con la tabla O8 y la de reinicios,
    confirmación en placa en `sec:sim_90b`, `tab:status`, `tab:se`,
    `sec:uncertainty` (parte FPGA), ciclo de trabajo con la Basys 3.
15. Cap. 4: figura, regla del divisor mínimo y del máximo, arranque en 2²⁵,
    ÷16 en el cruce, flujo medido, muestreo libre con la Basys 3.
16. Cap. 6: tabla regenerada, área, §`ro_silicon` con lo del integrado.
17. Apéndices A y C; cap. 3 (lo medido en `:36-45`, `:178-181`, la parte
    FPGA de `sec:kd`); cap. 1 y resumen; cap. 8 (O5, O6, O8, aportaciones,
    trabajo futuro).
18. Pendientes de la revisión del 10-11 que no dependen de evidencia (M1-M3,
    menores, puntos frente al objetivo oficial).

**Fase 3: lo que espera al SPICE** (cuando acaben las tandas en marcha)

19. ~~Monte Carlo de 11 etapas a 24 chips en las cinco esquinas~~ (22-11: H
    declarable 0,757, sensibilidad 0,789; `cortes_salud.py` al día; 5 etapas
    con sensibilidad, 0,530). Con H
    declarable ≥ 0,60 en todas: H 0,60 cerrada, se quitan las notas
    PROVISIONAL de los caps. 4 y 7 y se escribe la historia 5 → 11 etapas.
    Si saliera < 0,60, según el criterio, se corrige el circuito otra vez.
20. Periodo de ro2 de 13 etapas (tandas de hoy) → `docs/anillo_ihp.md` §4.4
    sin el 13/11; caudal y tiempos de siembra (E16); `cortes_salud.py` con
    el chip nuevo y falsas alarmas (E17) → cap. 4 `:206-216`, cap. 7
    `:180-220` y `:389-391`, cap. 3 `sec:kd` (integrado), cap. 8 O1-O3,
    `sec:uncertainty` (parte integrado), O1 en `tab:status`.

**Fase 4: cierre**

21. Quitar los comentarios de borrador; script de cifras EN/ES y
    `chk_tex.py`; compilar los dos PDF con tectonic cuando la CPU esté libre
    (leer el log entero; tras un fallo, borrar `.bbl` y `.aux`).
22. Revisión independiente de la memoria (agente sin las conclusiones,
    con el código y los datos), aplicar correcciones.
23. PR de `feat/lecturas-firmadas` a `main` con la CI en verde.

Lo de la Fase 2 no depende de la Fase 3: se puede escribir ya y dejar las
frases del integrado (divisor, caudal, H) como están, con su nota no
impresa, hasta el paso 19-20.

## Hecho el 22-11-2026

- Apéndice D, "The Two FPGA Boards: Basys 2 and Basys 3" (`memoria/chapters/app_fpga.tex` y `memoria/chapters_es/app_fpga.tex`), a partir de `docs/basys2_frente_basys3.md`, a petición de Mario. Sin referencias desde el texto principal todavía; las cifras de la Basys 2 en los caps. 4, 7 y 8 siguen pendientes (tabla de `docs/basys2_frente_basys3.md` §6).
