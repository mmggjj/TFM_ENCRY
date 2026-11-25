# Revisión independiente de la memoria (23-11-2026)

Alcance: `memoria/tfm_main.tex` y `memoria/chapters/*.tex` (caps. 1-8, capítulo del
ESP32 y apéndices A-D), rama `feat/lecturas-firmadas`, commit 86f1939. La versión
española se ha revisado con `memoria/cmp_cifras.py` y por muestreo (cap. 8 y
búsqueda de los pasajes afectados en caps. 5-7 y apéndice D). Solo lectura: no se ha
tocado nada del repositorio salvo este fichero.

Método: seis lecturas completas en paralelo (una por bloque de capítulos), cada una
contrastando con datos y código y recalculando donde se podía. Los doce hallazgos
graves los he vuelto a comprobar yo en la fuente (columna "Comprobación propia").
Los medios y menores proceden de esas lecturas, con fichero y línea de la fuente,
y no los he repetido uno a uno.

## Resumen

**12 graves, 47 medios, 46 menores.**

Lo primero que hay que saber: **no hay cifras inventadas ni resultados de placa o de
simulación que contradigan sus datos de forma que cambie una conclusión.** Las tablas
de resultados (SPICE, Monte Carlo del biestable con H declarable 0,757, campaña
SP 800-90B, reinicios, O8, síntesis, 307 comprobaciones en 13 bancos, cortes 51/766,
falsas alarmas, caudal) se han rehecho desde los CSV, los `.bin` y los logs y
coinciden. Los graves son de otro tipo: una omisión, una cifra mal derivada en el
presupuesto de incertidumbre, y frases que afirman más de lo que sostiene la fuente.

Los cinco más importantes:

1. **El aviso de la radio dormida del ESP32 no está en la memoria (G1).** Las 36
   capturas A-D se hicieron con un firmware que podía dejar la RF apagada;
   `docs/esp32_linea_base_90b.md` dice que la comparación de radio debe apoyarse en
   la repetición del 10-11 (12 capturas con la radio despierta), que la memoria ni
   menciona. Afecta al capítulo del ESP32, al cap. 7 y al cap. 8 ("cuatro condiciones
   de radio y ADC no muestran efecto").
2. **"Un factor dos en q₂ llevaría la cota a 0,974" es falso para la cota que se da
   (G2).** `ch7_results.tex:1264`. La cota usa el borde inferior 0,6·10⁻⁶; su mitad
   da H_∞ = **0,920** a 2¹⁹ (recalculado con `ero_model.entropias_exactas`). 0,974
   es la mitad del valor central. El error va en el sentido no conservador y está en
   el párrafo que acota la incertidumbre.
3. **La memoria da por establecido que la raya de ~39 kHz "explica la mayor parte"
   del desacuerdo con el modelo (G4).** `ch1:123-126`, `ch8:121-123`. La bitácora
   (`docs/basys3.md:657-660, 686-688`) retiró esa lectura: "no está establecido". No
   hay ninguna simulación que lo demuestre, y "de origen externo" tampoco está
   identificado.
4. **La estimación previa del divisor no sale de los datos que se citan (G3).**
   `ch3_entropy.tex:302-305`: con 2-4 ps sobre 3-5 ns y la fórmula del propio
   capítulo salen K_D 1,3·10⁵ a 1,4·10⁶ y 0,35-3,9 kbit/s, no 3·10⁴-5·10⁵ y
   1-20 kbit/s. De ahí cuelgan "what was measured falls at the upper end" (ch3:313),
   "at or below the first row" (ch7:535, que además es falso: 0,6-1,1·10⁻⁶ está por
   encima de 5·10⁻⁷) y "a hundred times slower than the first estimates" (ch8).
5. **Promesas de alcance que la memoria no cumple o pruebas descritas con más alcance
   del real (G7, G8, G9, G11):** el complemento del APT "permitido por la norma"
   cuando el propio repo lo llama adición propia; el banco del sistema con
   `G_KD_MIN => 4`, `G_PET_BITS => 4` y `G_PRESC_RO2 => 2` sin declararlo, y "the
   requirement holds" para una ventana medida solo de n = 4 a 14; el contraste con
   PTG.2 anunciado en los caps. 1-2 y no hecho (los bits crudos del integrado, con
   P(1) ≈ 0,47, no lo cumplirían); y `tab:status` da O2 por cumplido con "térmico y
   1/f separados" cuando el propio cap. 7 dice que el 1/f solo queda acotado entre
   dos límites.

Sobre el objetivo oficial (`docs/normas_tfm.md`): la memoria lo cubre entero (O1-O8,
recogido en `ch8:6-10`) y O5/O8 se cuentan igual en `tab:status`, cap. 5, cap. 8 y
resumen, sin presentar la batería SP 800-90B como prueba de entropía. No hay nombres
de tutores (`tfm_main.tex:107` vacío). Los agradecimientos (`tfm_main.tex:204`)
nombran a la empresa del autor; no hay nada interno copiado y CLAUDE.md lo deja a
decisión de Mario.

Versión española: `cmp_cifras.py` da 3 diferencias; dos son falsas alarmas (anchos de
columna en `appendices.tex`: 0.53/0.66 frente a 0.54/0.64) y dos sin localizar
(`tfm_main_es.tex` con un "3" y un "7" de más, `ch7` con un "4" de más; probablemente
texto, no cifras). El muestreo confirma que la española reproduce la inglesa,
incluidos los hallazgos de abajo (p. ej. `chapters_es/ch7_results_b.tex:612`,
`ch5_verification.tex:317, 336`, `ch6_asic.tex:191`, `app_fpga.tex:140`,
`ch7_results_b.tex:510-513`): toda corrección hay que trasladarla.

## Hallazgos graves

| # | Dónde (EN; ES si difiere) | Qué dice | Qué dice la fuente / cálculo | Comprobación propia | Corrección propuesta |
|---|---|---|---|---|---|
| G1 | `esp32_blackbox.tex:14-15, 76-79, 110, 236, 887-889, 1061-1063`, `tab:esp32_campaigns` (212-229); `ch7_results.tex:1239-1241`; `ch8_concl.tex:86-88` | Cuatro condiciones en cuatro campañas; "Wi-Fi on" = estación arrancada sin asociar; "the same firmware, rebuilt unchanged"; ninguna diferencia resoluble entre condiciones | `docs/esp32_linea_base_90b.md:513-573`: las 36 capturas A-D sin `sta_disconnected_pm = false` ni `WIFI_PS_NONE`; la RF pudo estar dormida, sin medir cuánto; "el ANOVA no dice nada sobre la radio mientras no se repita". Repetición del 10-11: 12 capturas `0928rd_*` (48 filas en `results/entropia_90b.csv`), ANOVA p = 0,41, radio/no radio p = 0,80, 3 por condición y un chip. `git diff 6db5911 HEAD -- firmware/esp32_rng`: 4 líneas añadidas, el firmware del repo ya no es el de las 36 capturas | `grep -i "sleep\|awake\|PS_NONE\|sta_disconnected\|dormid\|despiert"` en todos los `.tex` EN y ES: nada sobre el aviso. Doc, CSV y diff leídos | Párrafo en `sec:esp32_setup` y `sec:esp32_90b` con el aviso; añadir la quinta campaña a la tabla (3 por condición, un chip, RF no medida, solo temperatura: B 1,2-2,2 °C sobre C); apoyar en ella la comparación de radio; corregir "rebuilt unchanged"; mismas frases en ch7 y ch8. `:445` y `:453-454` (efecto de la radio sobre el caudal) dependen de lo mismo |
| G2 | `ch7_results.tex:1261-1264` (ES `ch7_results_b.tex:612`) | Cota H_∞ ≥ 0,99 a 2¹⁹ con el borde inferior; "a factor of two on q₂ would bring the bound to 0.974" | `results/cfg_kd_suelo_blanco.txt`: 0,9739 es para q = 4,1·10⁻⁷ (mitad del valor central 8,2·10⁻⁷) | `ero_model.entropias_exactas(q·2¹⁹)`: q = 3·10⁻⁷ → **0,9199**; 4,1·10⁻⁷ → 0,9739; 6·10⁻⁷ → 0,9963 | "…would bring the bound to 0.92" (o dar los dos: 0,974 con la mitad del valor central, 0,92 con la mitad del borde) |
| G3 | `ch3_entropy.tex:302-305, 313`; `ch7_results.tex:534-536`; `ch8_concl.tex:42` | "2-4 ps per period of 3-5 ns put the divider between 3×10⁴ and 5×10⁵ and the throughput between 1 and 20 kbit/s"; lo medido "at the upper end of the estimated range"; en ch7 "outside the table… at or below the first row" | q₂ = (σ/T)²: (2 ps/5 ns)² = 1,6·10⁻⁷ a (4 ps/3 ns)² = 1,78·10⁻⁶ → K_D = 0,2286/q₂ = 1,3·10⁵ a 1,4·10⁶; 0,35-3,9 kbit/s a 500 MHz. El rango 3·10⁴-5·10⁵ es el de la tabla de `docs/modelo_ero_resultados.md:151-155` (Q_raw 5·10⁻⁷ a 8·10⁻⁶, σ/T hasta 2,8·10⁻³), pegado en `:159-161` a "2-4 ps / 3-5 ns" sin corresponder. La primera fila de `tab:opoint` es 5·10⁻⁷: 0,6-1,1·10⁻⁶ queda por encima, entre la 1.ª y la 2.ª | Aritmética rehecha; doc y los tres pasajes leídos | Rehacer el rango (≈ 1·10⁵-1,5·10⁶; 0,3-4 kbit/s) o decir qué σ/T se supuso; ch3:313 "falls inside the estimated range"; ch7:535 "between the first two rows; the throughput falls below the table because RO2 runs at 205 MHz, not 500"; revisar el "hundred times" de ch8:42 |
| G4 | `ch1_intro.tex:123-126`; `ch8_concl.tex:121-123`; `ch7_results.tex:885-887` | "a deterministic modulation of external origin explains much of the difference"; "A spectrum explains most of it: a narrow line near 39.4 kHz, of external and unidentified origin" | `docs/basys3.md:657-660`: que el ×4,4 sea solo la raya "no está establecido"; `:686-688`: "Retirado… 'el ×4,4 era la modulación'"; `results/revision_fable_20261118/LEEME.md:24` en condicional ("explicaría"); `docs/plan_memoria_cierre.md:134` "explicado en parte". No hay simulación que meta la raya en el modelo y recupere b = 1,6-2,1 ni los residuos | Leídas las líneas de `basys3.md` y los tres pasajes | "…is present and is a candidate explanation, not demonstrated, for part of the difference"; "external" → "of unidentified origin (fixed in time, not tied to the ring frequency)" |
| G5 | `ch2_soa.tex:497-499`; `ch1_intro.tex:79-81` | ch2: dos competidores sin mención y "the third states that its generator is 'designed to meet' the standard". ch1: "Of three widely used parts, one… and two do not mention SP 800-90 anywhere in their documentation", citando solo el datasheet de Microchip | `docs/via_asic.md:218-238`: "is designed to meet" es la frase del datasheet del **ATECC608B** (el que tiene ESV #E46); el SE050 declara TRNG 90B / DRBG 90A, con CAVP #C886 y sin ESV. Son cuatro piezas, y el recuento es sobre los datasheets | Leído `via_asic.md` §3.1-3.2 | ch2: "the third (SE050) claims compliance in its datasheet but holds no entropy-source validation; the ATECC608B's own datasheet says only 'designed to meet', and it is certificate #E46 that covers its source". ch1: "Of the four parts…, two do not mention SP 800-90 in their datasheets", citando los de Infineon y ST |
| G6 | `ch6_asic.tex:17, 182-187, 275-281`; `ch7_results.tex:1226` (ES `ch6_asic.tex:191`) | "published growth factor of ≈2.35… for an AES on this same library", sin cita; 0,77 mm² "a third of the 2.33 mm² block of the 180 nm alternative"; 0,83 mm² "fits nearly three times in the 180 nm block and within the 1 mm² minimum of the 65 nm one" | El 2,35 no tiene fuente en el repo: solo aparece afirmado en `docs/sintesis_resultados.md:13-14`, sin referencia; no hay entrada en `references.bib`; ya señalado en `docs/revision_memoria_2026-11-10.md:42` y `docs/alineacion_objetivo_oficial.md:82`. Las áreas son kGE × 7,2576 µm² (NAND2 de sg13g2); en UMC 180 nm la NAND2 mide 9,677 µm² (`docs/via_asic.md:352`): 48,65 kGE × 9,677 × 2,35 = 1,11 mm² (cabe 2,1 veces); 45 kGE → 1,02 mm² (44 %) | grep de "2,35" en `docs/` y `.bib`; `via_asic.md:352` leído; cuentas rehechas | Citar la fuente del 2,35 o sustituirlo por los factores documentados (utilización 0,60-0,70 → 0,50-0,59 mm², [ESTIMADO] con rango); recalcular por nodo o decir que la cifra en mm² solo vale para IHP |
| G7 | `ch4_engine.tex:209-212` | "The proportion test also checks the complement of the count, which the standard permits for binary sources" | `analysis/cortes_salud.py:10-12`: "es una adición propia (la norma solo cuenta las repeticiones del primer valor de la ventana) y por tanto hay que justificar"; `results/cortes_salud.log`: "adicion propia, no de la norma" | Leídos el texto y la cabecera del script. No he podido leer SP 800-90B §4.4.2 | Redactarlo como adición propia que no relaja el test (falsa alarma a dos colas 6,15·10⁻¹⁰ ≤ 2⁻³⁰), o citar la cláusula exacta; alinear el comentario de `health_tests.vhd:15-17` |
| G8 | `ch5_verification.tex:82-85, 104 (tab:tb), 215-218` | Del banco del sistema solo se declara que los anillos son 10× más lentos y de 5 etapas. "The requirement holds: the window between two samples is 2ⁿ periods… for the register value n" | `rtl/tb/tb_motor_top.vhd:86-87`: `G_KD_MIN => 4` (producto 25), `G_PET_BITS => 4` (32), `G_PRESC_RO2 => 2` (4), `G_FLUJO_BYTES => 64`. La saturación a 2³²−1 no la ejercita ningún banco; el rechazo por divisor mínimo se prueba con mínimo 4. `tb_ventana_ero` mide n = 4..14; la revisión (`results/revision_rtl_20261122/LEEME.md:28-36`) midió 4-19 y de 17 a 26 comprobó la máscara con la cuenta forzada | Leídos los genéricos del banco y los dos pasajes | Declarar los genéricos en `:82-85` o en el pie de la tabla; "measured for n = 4 to 14 (bench) and 4 to 19 (review); from 20 to 26 by the counter mask, not by simulating the window" |
| G9 | `ch2_soa.tex:570-574`; `ch1_intro.tex:97-99` (O3) | La cadena queda "confronted… with the PTG.2 requirements of AIS 20/31 version 3.0"; O3: "meets the AIS 20/31 target with margin" | De PTG.2 solo se usa el umbral H_∞ ≥ 0,98 para fijar Q (`ch3:160`, `ch7:491`). La banda P(1) ∈ (0,493; 0,507) que cita `ch2:176` no se contrasta. El integrado declara H_decl 0,60 con P(1) media 0,46-0,48 (μ−3σ 0,408): sus bits crudos quedan fuera de PTG.2 y la memoria no lo dice | `grep "PTG\|0\.493\|0\.507"` en caps. 3-8 y apéndices: solo `ch3:160` y `ch7:491` | Rebajar el hueco n.º 2 a "con el umbral de min-entropía de PTG.2" y añadir una frase explícita (cap. 3 o `sec:health`): el objetivo Q ≥ 0,2286 cubre el jitter; el sesgo del muestreador deja los bits crudos del integrado fuera de PTG.2, y por eso se declara 0,60 y se acondiciona |
| G10 | `ch5_verification.tex:291, 308` (ES `:317, 336`) | "the same mbedtls 3.6.7 tree that ESP-IDF ships"; "two blocks per key". Bajo impacto, pero son cifras que no coinciden | ESP-IDF 5.3.2 local: `MBEDTLS_VERSION_STRING "3.6.2"`; CI: 3.6.2; `appendices.tex:375`: 3.6.2. `results/host_check.log:301, 363, 392` (22-11): "P-256 con 3 bloques de 32 bytes"; los "2 bloques" solo en los logs de octubre (QEMU y placa) | greps hechos sobre los cuatro logs, `build_info.h`, `verifica.yml` | Poner la versión realmente usada (previsiblemente 3.6.2); "two or three blocks per key, depending on the mbedtls build" (o fijarlo y repetir) |
| G11 | `ch7_results.tex:37-39` (`tab:status`, O2 "met") | "thermal and 1/f separated (bench and impulse sensitivity function)" | El propio cap. 7 (`:250-284`): en el banco el 1/f no se resuelve; la ISF solo lo acota entre dos límites (esquina 1/f³ de 36 kHz a 5,3 MHz, factor 36-5 300) y deja abierto un factor 2 en la varianza térmica. O2 (`ch1:94-96`) pide además separar la cuantización | Leídas la fila y `:264-284` | "thermal extracted; 1/f bracketed between two limits by the ISF, not resolved in the waveforms; a factor of two on the thermal variance remains open". El párrafo "Flicker noise" no lleva etiqueta: las esquinas y cruces son `\est{}` a partir de `\simu{}` |
| G12 | `app_fpga.tex:136-138` (ES `:140`); pie de `tab:fpga_q` en `ch7` | "the campaigns use the quiet wrapper, and every Q comes from three captures" | `results/motor_campana/`: tres capturas solo del bitstream sin colocación fija (`…kd00_02_quieto`, `_r2`, `_r3`); los valores que usa la memoria (1,42·10⁻⁵, 3,22·10⁻⁶, suelo blanco) son de **dos** (`_bel`, `_bel_r2`) y el del bitstream final de **una** (`_1911`). Las repetibilidades "±10 %" y "±1-2 %" de las dos primeras filas de `tab:fpga_q` son del bitstream libre | Listado del directorio | "three captures on the first bitstream, two on those with fixed placement, one on the final one"; matizar el pie de `tab:fpga_q`; decir que el 0,95-1,35·10⁻⁶ del final (`ch7:952`) es una captura |

## Hallazgos medios

### Capítulo 7 (campaña en FPGA), cap. 8 y apéndice D

| # | Dónde | Qué dice | Qué dice la fuente | Corrección |
|---|---|---|---|---|
| M1 | `ch7:872-875, 1079, 1266`; `ch8:122, 196` | Raya "at about 39.4 kHz" en la variante silenciosa | En el bitstream de la campaña (K_D = 4) los bins son de 12,56 kHz y el pico es el de 37,7 kHz; 39,41 kHz sale de `results/motor_campana/basys3_carga_frecuencia_raya.txt` (bitstream de la prueba de carga, K_D = 16, bins de 3,14 kHz, interpolado) | Dar "38-40 kHz" con la resolución y decir de qué captura es 39,4 |
| M2 | `ch7:889` | "Away from the line the spectrum is flat" | Bitstream del 18-11: ±25 % entre 100 y 400 kHz. Final (`…_1911/espectro_fase_calibra.txt`): 1,08 / 1,38 / 2,23·10⁻², sube ×2-3; pico/suelo 88, no "more than a hundred" | "roughly flat (±25 %)" y decir que en el final el suelo sube ~×3, como la calibración a su ν |
| M3 | `ch7:1109-1118` (`tab:o8`); `ch8:138` | Columna "Basys 3, 2¹⁷-2¹⁹" y 0,857 como "the FPGA source" | Mezcla divisores por debajo del de trabajo (modelo: 2¹⁷ → 0,80; 2¹⁸ → 0,974); las tres tiras son del bitstream del 18-11; la del final a 2¹⁹ (0,853) no entra | Decirlo en el pie o dar solo las tiras a 2¹⁹ |
| M4 | `ch7:801-811` | Protocolo reenunciado | El protocolo previo (`git show 383d7c0`, "The pending campaign") decía "with K_D = 1… with at least three rings"; todo `tab:fpga_q` es a K_D = 4 y con dos anillos, sin declararlo como desviación | Citar el protocolo literal y añadirlo a la primera desviación |
| M5 | cap. 7, `sec:campaign` | — | El resultado central medido (raya, suelo, bandas a 440/515 kHz, desajuste de c(M)) no tiene figura | Una figura del espectro desde `analysis/espectro_fase.py` |
| M6 | `ch7:1169-1172, 1243-1245` (ES `ch7_results_b.tex:510-513`) | "ESP32, first chip / second chip"; fuentes probadas "on the second chip" | En `esp32_blackbox.tex:239, 980, 1013` son el segundo (a0:dd…) y el tercero (f8:b3…); las fuentes se probaron en el tercero. `tab:esp32_restart` solo tiene el a0:dd | Unificar; poner la MAC en `tab:restart_cmp` y remitir a la sección |

### Capítulo 7 (simulación del integrado)

| # | Dónde | Qué dice | Qué dice la fuente | Corrección |
|---|---|---|---|---|
| M7 | `ch7:368, 410-411` | "eleven stages, 2.2 times the period"; la ley 1/N "holds" | 2,2 es el cociente de etapas; los periodos dan 2,10-2,11 (anillo) y 2,03-2,04 (con biestable). 1/N predice 2,73·10⁻⁸ y lo simulado es 3,00 ± 0,26: borde del IC | "2.0 to 2.1 times"; "holds within 10 %, at the edge of the interval" |
| M8 | `ch7:388-393` | Diferencia entre tandas solo en sf 1,2 V (Welch p 0,004) | En sf 1,08 V las tandas difieren igual (0,4691 / 0,4579; p 0,15, y 0,01 sin los dos chips de hueco): es sistemático de tanda y toca a la esquina que fija 0,757 | Decirlo |
| M9 | `ch7:328-332, 347-349` | "24 dies per corner"; la tabla muestra 28, 28 y 24 | `docs/basys2.md:1008-1024`: 24 + los 4 del 15-11 en ff y sf; sf 1,08 V con ampliación condicional de 8 a 24, fijada antes. La regla pedía informar de la normalidad (tt 125 °C, 11 etapas: p < 0,01) y no se da | Una frase con el desglose y la normalidad |
| M10 | `ch7:377-383, 600-601` | Lectura de sensibilidad "(error up to 0.01)", "fixed before the last batch finished" | `results/revision_hueco_20261122.md`: 0,010 es la desviación típica, el máximo ≈ 0,025; el umbral se fijó conociendo ya los dos chips de hueco grande; uno de ellos es el "worst of 120 dies (0.777)" y el otro una medida degenerada (P(1) = 0,5000); sin ellos σ baja de 0,0183 a 0,0141 | "standard error about 0.01" y declarar lo demás |
| M11 | `ch6_asic.tex:239-242`; `ch5:492` | "thirteen stages… about 0.95 ns… margin ×2.6"; "26-bit divider counter" (1,53 ns) | ro2 simulado tt 27 °C: 904,8 ps (×2,4); esquina rápida 594,4 ps (×1,6) (`results/caudal_integrado.md`, `ch4:316`). El contador final es de 22 bits tras el preescalador (`motor_top.vhd:294`) | Usar el periodo simulado y decir la esquina; decir que 1,53 ns es de un contador que ya no existe |

### Capítulo 4 y apéndices A-C

| # | Dónde | Qué dice | Qué dice la fuente | Corrección |
|---|---|---|---|---|
| M12 | `ch4:213-215` | Con alarma "nothing leaves the engine" | `motor_top.vhd:574-583`: `autenticar` solo exige `clave_valida`; ETIQUETA, ALEATORIO y CLAVE (modo test) siguen legibles. El apéndice lo dice bien (`appendices.tex:141-144`) | "no new key or random output is produced; authentication with the existing key is still served" |
| M13 | `ch4:198-201`; `appendices.tex:313` | En el límite del APT (p ≈ 0,748) la semilla lleva 214 bits | Aritmética correcta, pero vale solo para bits independientes sesgados; el propio capítulo (`:248-252`) documenta bits con Ĥ 0,186 y ρ₁ −0,54 que pasan los dos tests | Añadir "for a memoryless biased source; the correlated regime is covered by the minimum divider" |
| M14 | `ch4:232-235` | `borrar_todo` "honoured even under alarm" | `motor_top.vhd:527-536, 597-599`: solo con el motor libre; durante una siembra (10-75 s en el integrado) se rechaza | Decirlo y dar la secuencia `clear_alarms` → `clear_all` |
| M15 | `ch4:68-70` | "the synthesis estimates of Chapter 6 showed [SHA-256] would take almost half the digital area" | El cap. 6 no menciona SHA-256; el dato es la estimación previa de `docs/arquitectura.md:458` | "an early estimate" `\est{}`, sin remitir al cap. 6 |
| M16 | `ch4:286-292` | Ausencia de correlación en la Basys 3 | `tab:fpga_90b` (`ch7:991`): n = 12, trozos, colocación fija, ρ₁ = +0,0045 (z = +4,5), del tamaño del efecto de la Basys 2 | Decir que vale desde 2¹³ en flujo, o justificar el punto |
| M17 | `ch4:143-148` | 209 y 53 ciclos con el AES de 11 ciclos; comentario `% PENDIENTE (M1)` | Con `aes_enc_32` (el del producto) serían ≈ 849 y ≈ 213 por el mismo patrón (estimación, no simulada) | Medirlo en `tb_motor_top` o darlo con `\est{}` |

### Capítulos 5 y 6

| # | Dónde | Qué dice | Qué dice la fuente | Corrección |
|---|---|---|---|---|
| M18 | `ch5:89-90` | "one run of the thirteen, 22 November 2026" | `results/run_tb_todos.log` con 307 es del 23-11 (commit 86f1939); el del 22-11 tenía 306 | 23 November |
| M19 | `ch5:30-31`; `appendices.tex:297` | "52 seeds, each instantiated" | `gen_drbg_vectores.py`: 1 secuencia principal + `N_LOTE = 50` = 51 instanciaciones | "51 sequences (1 + 50), 153 outputs" |
| M20 | `ch6:120-122` | Los dos caminos de síntesis "agree within 0.9 %" | `aes_enc`: 16,06 kGE (Verilog) frente a 15,80 (plugin, 22-11): 1,6 % | "within about 2 %" |
| M21 | `ch6:107-119, 159` | Ruido entre tandas 0,2 %; "+0.5 %" por ro2 de 13; "saving of 9.8" | `motor_top_aes11` 104,60 / 104,81 / 105,24 (0,6 %); en la tanda del 22-11 `motor_top_antes1911` (95,60) queda por encima de `motor_top` (95,46); el ahorro va de 9,1 a 9,8 según la tanda | Ruido ≈ 0,5 %; "no measurable change"; ahorro como rango |
| M22 | `ch6:59-60` | Tampón de captura en FPGA: 156 LUT | `results/basys3_final_1911/util_hier.rpt` y `ch5:520`: 158 | 158 |
| M23 | `ch5:505-508` | Las filas no suman el total porque "Vivado shares some LUTs" | Suman 3 821 de 3 886 LUT y 4 351 de 4 392 FF: faltan bloques que el informe a profundidad 3 no lista; compartir explicaría una suma mayor | Corregir la explicación |
| M24 | `ch5:340-372` | QEMU y placa del medidor; "The same build was then flashed" | Logs del 27-10 (modelo 0x02) y 28-10 (0x03); el firmware actual es 0x04 con semilla de 512 y rearme; no son la misma compilación | Fechar, dar la versión y decir que no se han repetido |
| M25 | `ch5:98` (`tab:tb`) | "ERO sampler: divider and sampled bit" | `tb_ero_core.vhd:93-97` solo exige que salgan bits con unos y ceros para kd 0-4; no comprueba la relación de división | "bits are produced at every divider 2⁰..2⁴ and take both values" |
| M26 | `ch5:227-228` | "a mutant with half the window passed the system bench" | `revision_rtl_20261122/LEEME.md:139-155`: pasaron las 88 comprobaciones impresas y la simulación se colgó en el paso 9c | "raised no failed check; the bench hung in the stream step" |
| M27 | `ch6:273-274`; `ch2:536-538` | IHP: tirada gratuita "for open-source designs under 2 mm²" | `docs/via_asic.md:201`: IHP no publica límites ni condiciones | Citar la fuente o quitar la cifra |
| M28 | `ch6:213-215`; `ch2:525-527` | Bayon: "a few hundred microwatts… until it failed every test" | En el repo la referencia es solo de metadatos (`estado_del_arte_trng.md:176`) | Verificar en el PDF o quitar |
| M29 | `ch5:19` | "NIST example file for CMAC" | `tb_aes_cmac.vhd` usa solo los cuatro vectores de RFC 4493 más K1/K2 | Quitarlo o decir que coinciden con los de SP 800-38B |
| M30 | `ch5:569-574` | "In each one [sesión de O5]… checks that neither seed nor key remains" | En la consola del 19-11 no hay `id` tras `cero`; consta solo el 17 y el 18 | Matizar |

### Resumen y capítulos 1-3

| # | Dónde | Qué dice | Qué dice la fuente | Corrección |
|---|---|---|---|---|
| M31 | `tfm_main.tex:144-146, 189-191` | "it is the restart test that separates the two sources" | Con el bootloader de serie el ESP32 también pasa §3.1.4; `ch8:143-146` lo dice bien | "…once its boot noise is removed" |
| M32 | `tfm_main.tex:130-132, 144-146` | "validated stochastic model"; "lower bound" en la FPGA | Validado numéricamente, no en hardware (`ch7:855`: el modelo no describe la forma); la cifra de la FPGA es el borde bajo de un estimador que yerra hacia arriba | "validated numerically"; "taken from the lower edge of the white floor" |
| M33 | `ch3:44-48`; `ch7:902-903`; `app_fpga.tex:69, 146` | σ ≈ 4-5 ps por periodo; "places its own rings in that range" (2-4 ps) | Sale de √q₂·T₂; con la definición del cap. 3 (periodos de RO1) son 4,6-7 ps; es jitter relativo de dos anillos y sesgado al alza | Decir la convención; "of that order" |
| M34 | `ch2:106-108` | Fórmula de Petura con π² | Con sus datos da K = 1,72·10⁶; la de Baudet (4π²Q) da 431 153. Pendiente desde `docs/alineacion_objetivo_oficial.md:90` | Comprobar el PDF: convenio de σ o errata |
| M35 | `ch2:55, 56-58, 387-389, 529-531, 539-542, 546-549` | Varias atribuciones | 154 Mbit/s es de la tabla de Petura, no de Cherkaoui; la cadena de acarreo como TDC es el DC-TRNG, no el ES-TRNG; BER 3-8 % sin cotejar (lo dice el `annote`); BTI/HCI sin cita; `kaps2019lwc` mide Mbps/LUT, no GE; falta citar `rojas2022trngcapability` | Corregir cita a cita |
| M36 | `ch3:36-38` | 95 ps `\est{}` citando el manual de Digilent | Es un máximo de hoja de datos del DSC1033 (clave `micrel_dsc1033`); se compara ciclo a ciclo máximo con RMS de periodo | Cita y etiqueta |
| M37 | `ch1:103-105, 115-118` | O5 pide "known-answer tests, cross interoperability and challenge-response" en la FPGA | `ch8:100-107`: los KAT se quedan en simulación; la interoperabilidad se comprobó en un sentido | Una frase tras la lista remitiendo a la salvedad |
| M38 | `ch2:566-569` | Hueco n.º 1: jitter "with the thermal and flicker components separated and with stated uncertainty" | Entregado: un rango de suelo blanco separado de una raya determinista, no del flicker; variante normal "not determinable" | Alinear con `ch8:166-170` |
| M39 | `ch2:63-65, 74` | Columna "Feasib.": "higher is easier" | `docs/estado_del_arte_trng.md` §1.8 se contradice sobre el sentido | Confirmar con la Tabla II del artículo |

### Capítulo del ESP32

| # | Dónde | Qué dice | Qué dice la fuente | Corrección |
|---|---|---|---|---|
| M40 | `esp32_blackbox.tex:283-289` | El autotest de SP 800-22 con `os.urandom` "passes" | `analysis/esp32_rng/nist_sp800_22.py:546-549` exige ≤ 1 fallo y cuenta las excursiones no aplicables como dos; 2 de 5 ejecuciones abortan (≈ 38 %, la probabilidad que da la propia memoria en `:304-305`) | Decirlo o excluir del recuento las no aplicables |
| M41 | `ch2:280-281` | La prueba de reinicios "measures how much the boot noise contributes" | Solo acota por abajo (`esp32_blackbox.tex:973-976`) | "shows that without the boot noise the output repeats" |
| M42 | `esp32_blackbox.tex:1002-1009` | 174 ciclos de CPU, 87 de APB | `docs/esp32_reinicios.md` §6.3 y §9: medido a 160 MHz, un solo binario; el capítulo solo declara 240 MHz (`:118`), con el que no cuadra | Declarar los 160 MHz y el límite |
| M43 | `esp32_blackbox.tex:988-990, 1005-1007` | "the 3000 noise-free outputs… fall into the same 87 groups"; el generador avanza "whether or not it is read" | `results/esp32_reinicios/entre_chips.md` tiene 7 600 bloques; `radio_sin_ruido` "antes" cae en 774 grupos propios que no se alinean (sin explicar, `docs/esp32_reinicios.md` §7); `esp_random()` hace XOR de varias lecturas | Redactar como inferencia (204/204 parejas, un chip, un binario) y declarar lo que no encaja |
| M44 | `esp32_blackbox.tex:1011-1034` (`tab:esp32_fuentes`) | "yes/no" | Con 300 arranques sin repetición solo se excluyen < ~1,5·10⁴ estados (≈ 14 bits) | Dar la cota en el pie |
| M45 | `esp32_blackbox.tex:1070-1071`; `ch1:53` | "The generator has no noise of its own with the radio and the ADC off" | Sostenido para dos chips D0WD-V3 y hasta 0,35-0,8 s | Acotarlo |
| M46 | `esp32_blackbox.tex:52-53` | "the 15-75 kHz quoted by the guide" | La guía de la v5.3.2 no da kHz; las cifras están en comentarios de `hw_random.c:28-41` para otros chips; la entrada del `.bib` apunta a "latest" | Atribuir a `hw_random.c` o fijar versión |
| M47 | `ch8:128-130` | Los tests de salud "do not fire when the divider is lowered" | Es el caso con colocación fija; sin ella el RCT saltó a 2⁸ (racha 67 > 51); el cap. 7 lo matiza | Matizar en el cap. 8 |

## Hallazgos menores

| # | Dónde | Hallazgo y corrección |
|---|---|---|
| m1 | `ch7:945-946` | "above 0.60 while q₂ ≥ 1.3×10⁻⁷": con 1,3·10⁻⁷ sale 0,587 (recalculado); el umbral es 1,34·10⁻⁷. Poner 1,4·10⁻⁷ |
| m2 | `ch7:231-232` | "about 2.6 s" de siembra: 512 · 2²³ · 587,68 ps = 2,52 s. "about 2.5 s" |
| m3 | `ch7:314-315` | "within 0.01 of the ideal threshold": hay 0,0125 y 0,011. "within about 0.013" |
| m4 | `ch7:436-437, 464-465` | El 1,175 es peor K_D sobre K_D de la Q media, no "ratio of extremes"; coincide por azar con T(ro2)/T(ro1) = 1,1754: advertirlo |
| m5 | `ch7:406-407`; pie de `tab:ihp_ring` | σ es la raíz de la Q media (214,9), no la media de las σ (214,6): decir de qué es la media |
| m6 | `ch7:176` | "×1.99 ± 0.06" sin decir cómo sale el ±0,06 |
| m7 | `ch7:231` | "0.20 to 0.41 kbit/s" mezcla 1,08 V y 1,2 V; ff a 1,32 V no se simuló con 5 etapas |
| m8 | `ch7:330` | La regla es μ ∓ 3σ (la cola que se aleja de 0,5), no μ − 3σ |
| m9 | `ch7:500-501` | "six digits over the whole range": a Q = 0,05 son cuatro |
| m10 | `ch7:1024` | "0.5054 to 0.5064 at every divider": la tabla da 0,5050 y 0,5052 a 2⁸ y 2¹⁰ |
| m11 | `ch7:1038-1039, 1141` | H_∞ ≈ 0,47 a 2¹⁶ es del bitstream con colocación fija; para el registro largo sin ella sería 0,43-0,75 [ESTIMADO] |
| m12 | `ch7:738, 1125` | "always"/"all set by the compression estimator": 35 de 36 simuladas y 32 de 36 del ESP32. "in nearly all" |
| m13 | `ch7:844` | La fila de varianza de la silenciosa tiene κ = −2,3, régimen que `docs/basys3.md:202` da por no fiable |
| m14 | `ch7:854` | "factor of three to four between them" vale para la silenciosa; con frecuencímetro es ×15 |
| m15 | `ch7:950-951`; pie de `tab:fpga_90b` | El bitstream final difiere también en `G_KD_RESET`, `G_KD_MAX` y el RTL del 19-11; la última fila es a 204,4 MHz |
| m16 | `app_fpga.tex:33-34` | 4 011 LUT / 4 561 FF son de la variante del 17-11; el final versionado da 3 886 / 4 392 (`ch5:522`) |
| m17 | `app_fpga.tex:17-20, 62-71, 93, 100-114` | Llama Q a la varianza por periodo (el cap. 3 fija q₂); "divisor" → "divider"; "10⁻⁶-10⁻⁵" frente a 3·10⁻⁶-8·10⁻⁵ del cap. 8 |
| m18 | `ch8:72` | "out of range accepted in silence… fixed": la placa lleva el RTL anterior al 22-11 (solo lo dice `ch5:231`) |
| m19 | `ch8:86` | "Thirty-eight captures… under four conditions": son 36 + 2 largas sin radio |
| m20 | `ch6:179-181` | Nota no impresa obsoleta (el cap. 8 ya dice "13 to 25") |
| m21 | `ch6:279-281` | 0,83 mm² está por encima del mínimo de 0,8: no es "the minimum order" |
| m22 | `ch6:104-105` | "about half of which are its registers": más cerca del 60 % (estimación, sin comprobar con el liberty) |
| m23 | `ch5:103` | La fila de tests de salud omite el caso 6 del banco |
| m24 | `ch5:352` | "about 0.17 s": el log da 0,162-0,164 |
| m25 | `ch4:19-22`; `fig:engine` (`:47`) | El buffer de captura se alimenta antes del cruce (`motor_top.vhd:313`); la flecha sugiere que RO1 pasa por el preescalador |
| m26 | `ch4:346-348`; `appendices.tex:38-40` | `CFG_KD` sí se puede cambiar con una captura por trozos en marcha (`motor_top.vhd:608`) |
| m27 | `ch4` §4.6 | El cruce de `kd_sel` hacia el dominio de ro2 (`ero_core.vhd:71-74`) no se declara: "quasi-static, changed only while idle" |
| m28 | `appendices.tex:126-127, 213` | "reseed requires a seeded DRBG": con los bits 0 y 5 a la vez sin estado se acepta como resembrar (inocuo) |
| m29 | `appendices.tex:203` | `G_KD_MAX` no es el ancho del contador: es `G_KD_MAX − G_PRESC_RO2` |
| m30 | `ch4:109-110` | "the five official vectors available": son los cinco usados |
| m31 | `ch4:402-405` | Desde 86f1939 `verifica_top.py` recalcula también clave y ALEATORIO (9/9); el apéndice B ya lo dice |
| m32 | `appendices.tex:42-43, 153-154, 377` | RCT_MAX/APT_MAX son "desde el último borrado"; "1.3 to 4 s" sin etiqueta; "tectonic 0.15" y la CI no fija versión |
| m33 | `ch4:211-212` | "would otherwise score zero": la cuenta mínima es 1 |
| m34 | `ch1:17-22` | "despite passing the standard statistical suites" (la fuente: "most tests"); "every black-box test" → "every statistical test" |
| m35 | `ch1:132-133` | "no larger than the smallest area that can be ordered": 0,83 mm² estimados sin buffer frente a 0,8 |
| m36 | `ch3:122` | El O(e^{−6π²Q}) de Baudet es más holgado, no incorrecto: matizar |
| m37 | `ch3:31` | La medida embebida se cita a `petura_2016_survey`; lo natural es `fischer_2014_embedded` |
| m38 | `ch3:306-309` / `ch2:151` | El mismo σ = 5,01 ps con periodo 7,81 ns y con 8,9/8,7 ns: una frase que diga que son medida y ejemplo de diseño |
| m39 | `ch3:186-188, 262` | "in one measured case" es simulado; "three orders of magnitude" son 870× |
| m40 | `ch2:446-448, 550` | Los 25 Gbit/s de Good-Benaissa son en Spartan-III; el factor 1,7-4,6 va sin cita |
| m41 | `ch3:175`, `ch2:147` | El estimador se describe a K_D = 1 y la placa se midió a 2² (ligado a M4) |
| m42 | `esp32_blackbox.tex:445` | "by less than 0.1 %": hay +0,114 %; la dispersión entre repeticiones (0,17 %) es mayor |
| m43 | `esp32_blackbox.tex:871, 505, 938, 970-971` | "eleven estimators" son diez más el mínimo; von Neumann solo para los bits del ADC; "one fixed sequence" son 87 según la fase; "about 180 repeats" es calculado |
| m44 | `esp32_blackbox.tex:474-476, 766-768` | Rangos de temperatura por chip imprecisos; no se dice que E y F son del chip ec:e3 |
| m45 | `references.bib` | `blancoromero_2026_entropy`: arXiv 2607.xxxxx con `month = sep` |
| m46 | `tfm_main.tex:107, 204` | "Tutores / Advisors" vacío (hay que rellenarlo antes del depósito); los agradecimientos nombran a la empresa (decisión de Mario) |

Fuera de la memoria, visto al contrastar (no cuentan arriba): `rtl/trng/bit_cdc.vhd:10`
y `docs/mapa_registros.md` ("Obligaciones", punto 1) dicen `CFG_KD ≥ 7` para el cruce
y la memoria ≥ 8 (lo correcto con 0,594 ns es 8); el comentario de `motor_rearmar`
en `motor_i2c.h` sigue citando los cortes de H 0,80; `verifica.yml` rotula el paso
"nueve bancos" (son trece); `docs/modelo_ero_resultados.md:157-161` arrastra el
origen de G3; `results/tabla_o8.md` no tiene la fila de reinicios del bitstream
final (la memoria sí, y coincide con su `resumen.md`).

## Lo que resultó correcto al recalcular

- **SPICE del anillo:** `tab:spice`, `tab:ihp_ring` (176,7 ± 2,0 fs, K_D 981 095),
  todas las esquinas y tensiones, desapareamiento (48 y 23 chips), anillo de 11
  etapas (Q 3,00·10⁻⁸ ± 0,26, razón 1,1754), `tab:ihp_e11`, caudal 20-50 bit/s.
- **Biestable:** las nueve filas de `tab:ff_mc` desde los CSV; H declarable 0,532
  (5 etapas) y 0,757 (11 etapas), 0,704 con la σ alta, sensibilidad 0,789.
- **Modelo:** `tab:exact`, objetivos Q ≥ 0,2022 / 0,2286, punto de Fischer-Lubicz
  (431 153), `tab:estimator`, `tab:opoint`.
- **Motor:** mapa de registros, genéricos, VERSION, reglas y prioridades frente al
  RTL; cortes 51/766 y sus antecesores; falsas alarmas; tiempos de siembra y arranque.
- **Verificación:** 13 bancos y 307 [ok] contados en el log; PSL 14/14 y 8/8; CAVP
  960/960 (reejecutado); `verifica_top.py` 9/9; banco en PC 0 fallos.
- **Síntesis:** todas las filas iguales al CSV del 22-11 (95,456 kGE, 8 425 FF) y
  derivadas; tabla de implementación en FPGA (3 886 LUT, 4 392 FF, WNS +0,524 ns).
- **Campaña en placa:** `tab:fpga_90b` (12 filas desde los `.bin`), `tab:fpga_kd`,
  `tab:fpga_q`, suelo por banda, `tab:o8`, `tab:restart_cmp`, registros largos,
  fuente simulada bajo SP 800-90B; O5 40/40 en las tres consolas.
- **ESP32:** recuento de capturas, `tab:esp32_90b`, ANOVA por condición y por chip,
  vía IID, SP 800-22 de segundo nivel, SRAM, reinicios y fuentes.
- **Referencias:** todas las `\cite`, `\ref` y `\label` de todos los ficheros existen.

## Lo que no se pudo comprobar y por qué

- **Texto de las normas** (SP 800-90B §4.3 y §4.4, SP 800-90A §8.6.3 y §8.6.7,
  AIS 20/31): sin acceso; G7 es una contradicción interna comprobada, no un cotejo
  con la norma.
- **Artículos y hojas de datos citados** (Petura, Bayon, Yang, Holcomb, Kuon y Rose
  "27-49×", STM AN4230, TRM de Espressif, Blanco-Romero, fecha de AIS 31 v3.0, NIST
  ESV #E46): en el repo solo hay notas propias y `annote`; M34, M39 y M28 necesitan
  el PDF.
- **Lecturas sin fichero:** display de la placa (207,2 / 167,2 / 357,8 / 291,8 MHz),
  anécdotas históricas del cap. 5, el primer intento de 0,33 ps, la foto del montaje
  (no existe; ningún texto la da por hecha).
- **No reejecutado por tiempo:** batería del NIST (`ea_non_iid`, `ea_iid`,
  `ea_restart`), bancos GHDL, síntesis, SPICE, Vivado, la revisión del APT
  (34 236 958 casos), la calibración de permutación, `jitter_estimator.py` 14/14.
  En esos casos la comprobación es contra el log o el resumen existente.
- **Datos no versionados:** informes de Vivado de las compilaciones intermedias
  (3,3-3,9 ns, −0,26 ns), scripts de los "tres modelos de calibración"
  (0,80-0,88·10⁻⁶), consolas de O5 del 17 y 18-11 (solo se leyó entera la del 19-11).
- **Estado de la CI** en GitHub con el commit actual: no consultado.
- **Si la raya reproduce b ≈ 2** (G4): no hay script y no se ha simulado.
- **Versión española:** no leída entera; `cmp_cifras.py` y muestreo. Las dos
  diferencias de `tfm_main_es.tex` y `ch7` que da el script no están localizadas.
- **PDF compilado:** no se ha recompilado; `results/memoria_compila.log` es del
  22-11 y el PDF del 23-11.
