# Revisión de la memoria, 10-11-2026

Revisión de coherencia de `memoria/` (EN y ES) contra las fuentes del
repositorio, hecha por una sesión aparte de solo lectura. Leídos enteros los
capítulos ingleses, `ch1` y `ch8` españoles; el resto del español,
comparado por script (cifras, `\ref`, `\cite`, tablas) y por los pasajes con
hallazgo. Las líneas son las del commit 383d7c0. Lo aplicado ese mismo día
está al final; lo demás queda pendiente de Mario.

## Grave

- **G1.** Abstract y Resumen dan por hecha la verificación en FPGA y con el
  ESP32 (`tfm_main.tex:129-132`, `:165-168`; ES `:137-140`, `:173-176`):
  "verified three ways ... in simulation on a Basys 3 FPGA ... and against
  an ESP32 that recomputes every result". Nada ha corrido en FPGA; el ESP32
  solo ha corrido contra `motor_sim.c` y solo recalcula el CMAC.
- **G2.** La cota del motor se presenta como derivada de una medida física;
  el jitter es simulado. `ch7_results.tex:372`, `:399-402`, `:439-441`;
  `ch6_asic.tex:210-212`; `ch1_intro.tex:66-67` (y sus pares ES).
- **G3.** Verificación con cifras antiguas: "seven benches"
  (`ch5:72-73`, `ch7:35`, `ch7:320`, `appendices:263`), tabla `tab:tb` sin
  `tb_medidor_frec` ni `tb_basys3_top`, AES-CMAC 5/5 (son 7/7),
  `ero_model.py` 24/24 (da 26), "177 in total" (`appendices:190`),
  "sixteen checks" (`ch4:251`), "eighteen checks" (`ch5:154,161`), "four
  cover directives" (`ch5:174`).
- **G4.** `\ac{ADC}` sin definir: el PDF imprime "ADC!" (`ch8_concl.tex:69,74`).

## Medio

- **M1.** Cap. 4 con restos de la arquitectura antigua: SHA-256 "∼25 to ∼13
  GEs (thousands)" (`:56-62`); "the engine encrypts and the ESP32 decrypts"
  (`:68-69`); "1.16 Gbit/s" con el núcleo de 51 ciclos (`:82-84`); "183
  cycles ... 53 cycles" son del AES de 11 ciclos (`:125-126`); "the same
  cross-check the ESP32 performs on hardware" en presente (`:255-256`).
- **M2.** Cap. 5: "the ESP32 recomputes ... every result" (`:30-33`);
  "generar also reads back the key and checks that it equals the first
  sixteen bytes" (`:190-192`, anterior al arreglo de la fuga); "eight valid"
  lecturas, son 10 (`:259-260`); "FPGA bring-up" no recoge lo preparado sin
  placa (`:295-309`).
- **M3.** Cap. 6: "0.72 mm² ... fits several times over in the smallest
  academic block" (`:150-153`; el bloque mínimo de IHP son 0,8 mm²);
  "0.3–0.4 mm²" (`:194-196`); `ch1:125-127`; "growth factor of ≈2.35" sin
  cita; "optimization savings ... not claimed as measured" (`ch7:549-550`,
  dos ya están medidos); "block RAM at no logic cost" (`:52-53`; Yosys lo
  mapea a RAM distribuida, Vivado sin ejecutar); tres versiones del "estado
  del arte" de área (`ch6:144`, `ch8:64`, `ch4:61`).
- **M4.** `ch8_concl.tex:21-22`: "rather than injected"; los caps. 3 y 7
  dicen que el ruido se inyecta con la densidad de los modelos.
- **M5.** `ch8_concl.tex:71-73`: "the same sequence after every reset"; lo
  medido son 759 salidas distintas en 1000, ventanas de una secuencia fija.
- **M6.** "K_D ≈ 430 000 for σ = 5.01 ps over T = 7.81 ns"
  (`ch3:275-276`, `ch7:292-295`): con esos datos salen ≈ 555 500.
- **M7.** "about 512 raw bits ... 0.03 and 0.5 s per seed"
  (`ch3:277-279`): el motor recoge 384 y con 2²³ son ≈ 1,9 s.
- **M8.** "with at least three rings" (`ch7:593-594`): el RTL tiene dos.

## Menor

- `ch6:88-90` 7,6 kGE (7,3 con la tabla), `:135` 2355 biestables (2357);
  `ch6:95-97` frente a `:115` (101,8 y 101,6 sin explicar).
- "GHDL 6" (`ch5:70,77`) frente a 5.0.1 en el apéndice; mbedtls 3.6.7 y
  3.6.2 sin aclarar que son dos árboles.
- "∼700 MHz sampling ring" (`ch4:201`); "up to 316" (`ch7:432`, es 317);
  "one to six digits" frente a "10⁻⁴ bit"; "1 and 20 kbit/s" frente a
  1,09–17,5.
- Fila O5 de `tab:status` se queda corta; "testbenches reproduce CAVP
  vectors" (los pasa el modelo Python); tres versiones de los elementos
  seguros (`ch1:77-79`, `ch6:207-208`, `ch7:371`, `ch2:491-499`).
- "Chapter 7 reports the hardware campaign" (`ch1:171-172`, `ch3:16-17`);
  "millions of test vectors ... in minutes" (`ch1:80-82`).
- Acrónimos SPI y XADC sin uso; referencias a `docs/*.md` en español;
  vocabulario ES en `ch8` (`Q_raw`, "cargador de arranque", "shuttle").
- EN sin "Palabras clave" en el Resumen; ES sí.

## Frente al objetivo oficial

1. La integración FPGA + ESP32 no es un objetivo O1–O8 con nombre propio.
2. La comparación de secuencias es la meta literal y el "mínimo defendible"
   de `ch1:113-116` la deja fuera; falta decir con qué pruebas se compara si
   SP 800-90B no separa las fuentes (reinicios del motor no está en el
   protocolo de `ch7:586-607`).
3. "The ESP32 changes role from subject to judge" (`ch1:69`) choca con la
   meta oficial.
4. O1 "with enable and sampler" a nivel de transistor: lo simulado es NAND
   + 4 inversores.
5. O5 promete "known-answer tests, cross interoperability" en FPGA.
6-8. Destino ASIC y modelo estocástico, bien cubiertos; palabras clave sin
   "randomness assessment".

## Sin verificar por la revisión

`jitter_estimator.py` 20/20 y `cortes_salud.py` 6/6; "−18 %" de
`ch7:545`; "eight later captures (p = 0.14 to 0.96)" de
`esp32_blackbox:847-848`; ciclos de siembra y generación con el AES de 32
bits; que ESP-IDF 5.3.5 traiga mbedtls 3.6.7.

## Aplicado el 10-11-2026 (EN y ES)

- **G1:** Abstract y Resumen: verificación "en simulación, con las reglas
  como propiedades, y frente al firmware de un ESP32 ... por ahora sobre un
  modelo del motor"; la Basys 3 es el vehículo preparado.
- **G2:** "measured jitter" → jitter medible en el dispositivo, aquí
  simulado (`ch1`, `ch6`, tabla y dos frases de `ch7`).
- **G3:** nueve bancos, tabla `tab:tb` con las dos filas nuevas, CMAC 7/7,
  `ero_model.py` 26/26, sin "sixteen/eighteen checks" ni "four cover",
  GHDL 5.0.1, recuento del apéndice.
- **G4:** `ADC` en la lista de acrónimos de las dos versiones.
- **M1 (una frase):** el contraste con mbedtls en hardware, en futuro.
- **M4, M5, M8:** corregidos como propone la revisión.
- Además, por la captura continua: apéndice A (versión 0x04, registros
  FLUJO), párrafo en la sección de cruces de dominio del cap. 4, paso 4
  del protocolo del cap. 7 y trabajo futuro del cap. 8.

**Pendiente** (cambian el discurso o necesitan una decisión): el resto de
M1, M2, M3, M6, M7, todos los menores, y los ocho puntos frente al objetivo
oficial. M6 y M7 son cuentas que hay que rehacer antes de tocar el texto.
