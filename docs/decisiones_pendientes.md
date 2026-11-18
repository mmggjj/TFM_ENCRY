# Decisiones pendientes de Mario (18-11-2026)

Una página para decidir las tareas 6-10 de `docs/basys3.md` ("Tareas
pendientes"). Cada punto: qué hay que decidir, opciones, coste, lo que dicen
los datos y una recomendación. Las cifras llevan su origen; nada de aquí está
aplicado. Recomendaciones de Claude salvo donde dice "revisión" (Fable,
`results/revision_fable_20261118/LEEME.md`).

## 6. Biestable del integrado: H declarable 0,532 < 0,60

**Dato** [SIMULADO, `results/biestable_mc.md`]: el biestable sg13g2 que muestrea
ro1 sesga el bit por capturar con distinto retardo la subida y la bajada
(26-30 ps en sf, 13-15 ps en ff, fijo al cambiar el número de etapas); el
sesgo baja como 1/T del anillo muestreado. Peor esquina sf a 125 °C y 1,08 V:
μ − 3σ de P(1) = 0,308 → H = 0,532. El criterio fijado antes del Monte Carlo
(commit 403c860) dice: por debajo de 0,60, se corrige el circuito, no se baja H.

| Opción | H esperada en la peor esquina | Coste | Riesgo |
|---|---|---|---|
| **ro1 de 11-13 etapas** (en vez de 5) | ≈ 0,66-0,72 [ESTIMADO, ley 1/T; 0,66 con σ alta] | ~6-8 inversores; divisor ×~5 (2²⁵), siembra ×4-5 más lenta | bajo: el SPICE con 9 y 11 etapas ya muestra el 1/T |
| ro1/2 (biestable T tras ro1) | ≈ 0,72-0,74 [ESTIMADO] | un biestable; divisor ×4 | el biestable T a 2,7 GHz tiene su propia asimetría, sin simular |
| XOR de pares de bits | ≈ 0,80 [ESTIMADO] | ×2 de caudal | no arregla los cortes de salud, que miran los bits crudos |
| Bajar H a 0,50, semilla de 640 bits | — | nada en el circuito | rompe el criterio fijado de antemano |

**Recomendación (coincide con la revisión): ro1 de 11-13 etapas**, validado
con el mismo Monte Carlo y añadiendo la esquina ff a −40 °C y 1,32 V (la de
periodo más corto, que el Monte Carlo no tiene). Se decide junto con el 9.

## 7. `G_KD_MIN` (hoy 6)

**Dato**: los tests de salud no ven el régimen de poco jitter: en la Basys 3
con colocación fija no saltan ni a `kd 8`, donde SP 800-90B da 0,186 (bits
que alternan, ρ₁ −0,54); la batería tampoco distingue `kd 16` (H del modelo
0,47) de `kd 19` (0,9996). `CFG_KD` lo escribe el maestro por I2C: con el
mínimo en 6, un maestro erróneo o malicioso siembra con bits casi
deterministas sin alarma. El mínimo solo se comprueba al sembrar y
resembrar (`motor_top.vhd` línea 496): la captura a divisores bajos sigue
disponible para caracterizar.

| Opción | Efecto |
|---|---|
| `G_KD_MIN` = 23 en el integrado (25 si ro1 se alarga) | siembra imposible por debajo del divisor que pide el SPICE (2²³ con ±10 % de V_DD) |
| `G_KD_MIN` = 19 en `basys3_top` | el divisor que pide el jitter térmico medido en la placa |
| test de autocorrelación en línea | no protege: a `kd 10`, ρ₁ 0,053 queda a 1,7σ en 1 024 bits con α 2⁻³⁰ |

**Recomendación: subir `G_KD_MIN`** (23/25 en `motor_top`, 19 en
`basys3_top`). Coste de área nulo. Los bancos no cambian: `tb_motor_top` y
`tb_motor_solo_fuente` ya pasan `G_KD_MIN => 4` (anillo 10× lento);
`basys2_top` pasa 7. Habría que repasar los mínimos del firmware
(`motor_i2c`, plazos con `CFG_KD` alto: con 24 el arranque llega a 687 s).

## 8. Restricción de ro2 en la FPGA (4,2 ns)

**Dato** [Vivado]: con colocación fija, −0,120 ns (silenciosa) y −0,391 ns
(normal) contra 4,2 ns; caminos de 4,32 y 4,59 ns frente a 4,88 y 4,83 ns
medidos (márgenes del 12 y del 5 %). Se dejó en 4,2 ns para no cambiar la
implementación medida.

**Recomendación**: 4,5 ns en compilaciones nuevas, más una comprobación en
`build.tcl` que pare si el camino supera 0,9 × el periodo medido (un fallo
de tiempos en el divisor del ERO parecería aleatoriedad). Cambia la
implementación: tras ello, repetir una captura corta de jitter y el O5.

## 9. Tiempos del contador del ERO en el integrado

**Dato**: el contador de 24 bits de `ero_core` corre con ro2, que en el
integrado son 2,73 GHz (5 etapas, tt; más en ff). En la síntesis
(`docs/sintesis_resultados.md`) no hay análisis de tiempos a esa frecuencia;
en la FPGA, el mismo dominio obligó a pasar a 11/13 etapas.

**Recomendación**: análisis de tiempos (STA) del dominio de ro2 con la
biblioteca sg13g2 antes de cerrar el punto 6; si no cierra, preescalar ro2
(un biestable T, ÷2) o alargarlo, y recalcular K_D con el SPICE.

## 10. Aislamiento de los anillos en el integrado

**Dato** [MEDIDO, Basys 3]: una modulación de ~38-40 kHz de fuente externa
(no es el I2C) entra en la fase relativa de los anillos, y la lógica colgada
cambia su amplitud ×15. En la FPGA no se puede aislar; en el integrado sí.

**Recomendación**: en la memoria, como requisito de implementación física:
buffer a la salida de cada anillo (el SPICE ya lo pedía), `ro_mon` sin carga
en producto, y alimentación o anillo de guarda propios para los anillos.
Sin cambio de RTL.

## Orden sugerido

9 → 6 → 7 (el divisor mínimo depende de la longitud de ro1 y de cómo se
cuente ro2), 8 en paralelo, 10 en la redacción.
