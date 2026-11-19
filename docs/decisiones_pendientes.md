# Decisiones pendientes de Mario (18-11-2026)

Revisado por un agente independiente el 18-11 por la noche (correcciones
aplicadas; `docs/basys3.md`, "Revisión de la tarde del 18-11").

## Decidido el 19-11-2026 (Mario) y aplicado

| Punto | Decisión | Aplicado |
|---|---|---|
| 6. Biestable | **ro1 de 11 etapas** | `motor_top` `G_ETAPAS_RO1` 7 → 11. Ojo: el SPICE simulaba 5 etapas y el RTL llevaba 7; la corrección es ×2,2 de periodo respecto a lo simulado. Monte Carlo con 11 etapas en marcha (`results/biestable_ihp_mc24_e11_*`), primero sf 1,08 V, sf 1,2 V y ff −40 °C 1,32 V, luego ff y tt a 125 °C |
| 9. Tiempos de ro2 en el integrado | **ro2 de 13 etapas + preescalador ÷16** (13 y no 11, como se aplicó primero: con ro1 también de 11, los dos anillos serían iguales y tienden a engancharse) | Estimación [Yosys + ABC, biblioteca típica 1,2 V 25 °C]: el contador de 26 bits tarda 1,53 ns y un biestable sg13g2 necesita ~0,37 ns para conmutar (clk→Q 0,22 + setup 0,11 + inversor), frente a 0,366 ns de ro2 con 5 etapas: no cerraba nada. Ahora ro2 de 13 etapas (~0,95 ns, el primer biestable cierra con ×2,6 de margen) y `G_PRESC_RO2` = 4: el dominio del anillo (ERO, cruce, captura) corre a ro2/16 (~13 ns). `CFG_KD` sigue contando periodos de ro2. Sin biblioteca lenta en el PDK local: la esquina 1,08 V 125 °C queda sin comprobar |
| 7. `G_KD_MIN` | **25 integrado, 19 FPGA** | `motor_top` 25 (y `G_KD_RESET` 25, `G_KD_MAX` 26 con el contador ensanchado; un `CFG_KD` > máximo se ignora y levanta `DIAG.rechazada`); `basys3_top` 19/19 con `G_KD_MAX` 24 (con 26 el camino de ro2 subía a 4,41 ns); variante de caracterización con `GENERICOS="... G_KD_MIN=6"` |
| `CFG_KD` de la FPGA | **19** (H_∞ ≥ 0,99 con la cota baja 0,6·10⁻⁶) | recalibración con la ν y el sesgo de cada captura: 0,59-1,13·10⁻⁶ (18-11) y 0,95-1,35·10⁻⁶ (bitstream del 19-11) por banda |
| 8. Restricción de ro2 | **4,5 ns + comprobación** | `basys3.xdc` 4,5 ns; `build.tcl` para la silenciosa si el camino supera 0,9 × `RO2_MEDIDO_NS` (4,88). La paró una vez (4,407 > 4,392 ns, con el contador de 26 bits); con 24, camino 3,98 ns, WNS +0,524 ns |

Área [Yosys, biblioteca típica, celdas sin rutar]: `motor_top` 95,53 kGE (ro2 de 13; 95,52 con 11) frente a
95,09 kGE con la configuración anterior en la misma tanda (+0,5 %;
`results/sintesis_19_11.log`; el CSV no se toca hasta actualizar el cap. 6).

### Validación con SPICE (noche del 19-11; Monte Carlo parcial)

**Divisor** [SIMULADO → ESTIMADO; `docs/anillo_ihp.md` §4.4]: ro1 de 11
etapas en ss, −40 °C, 1,08 V, 8 realizaciones: Q por periodo
2,65-3,41·10⁻⁸. Con ro2 de 13 etapas (13/11 estimado) y el factor de peor
chip, `CFG_KD` 24 da H_∞ 0,9997 y 25 ≈ 1: **`G_KD_MIN` 25 tiene un factor 2
de margen**.

**Biestable** [SIMULADO, sin ruido; `results/biestable_mc_e11.md`,
`analysis/biestable_mc.py --fuentes biestable_ihp_mc24_e11_criticas.log
--salida biestable_mc_e11.md`]: Monte Carlo de las esquinas críticas parado
a las 22:45 con 11 chips de 24 por esquina. Con el criterio fijado (μ ∓ 3σ,
todos los chips):

| Esquina | n | P(1) μ ± σ | H en μ − 3σ | peor chip |
|---|---|---|---|---|
| sf, 125 °C, 1,08 V | 11 | 0,4691 ± 0,0201 | **0,759** | 0,4166 |
| sf, 125 °C, 1,2 V | 11 | 0,4700 ± 0,0069 | 0,861 | 0,4592 |
| ff, −40 °C, 1,32 V | 11 | 0,4789 ± 0,0095 | 0,864 | 0,4568 |

H declarable 0,759 ≥ 0,60 (con 5 etapas, 0,532). **Ojo:** dos chips de sf a
1,08 V (rep 5: 0,5000; rep 7: 0,4166) tienen huecos de fase de 0,082 y 0,068
(~12 fases distintas, P(1) con resolución ~±0,04): con desapareamiento el
periodo de la simulación previa es de otro chip y el reloj puede caer cerca
de una razón racional. Son los que inflan la σ (Shapiro-Wilk p 0,00); sin
ellos la esquina da 0,874 (9 chips). Ningún otro chip pasa de 0,05 de hueco.
El Monte Carlo de 5 etapas también tenía huecos de hasta 0,077 y se contaron.
Con cualquiera de las dos lecturas se pasa el 0,60; la cifra válida es la de
24 chips.

**Para seguir** (otro día): completar las críticas hasta 24 chips con otra
etiqueta (los sorteos son independientes; `biestable_mc.py --fuentes` junta
logs y CSV):

    ~/eda/venv/bin/python analysis/biestable_ihp.py --montajes uno_buf --casos ffm40_v132 \
      --mismatch-n 13 --mm-casos sf125_v108,sf125,ffm40_v132 --procesos 4 \
      --etiqueta mc24_e11_criticas_b --etapas 11 > results/biestable_ihp_mc24_e11_criticas_b.log 2>&1

y después ff y tt a 125 °C (`--mm-casos ff125_v132,tt125 --casos tt27
--etiqueta mc24_e11_resto`; Mario lo deja para otro momento). Desde esta
noche `biestable_ihp.py` escribe además `<csv>.parcial.csv` fila a fila.
Mejora pendiente: rechazar o repetir los chips con hueco de fase > 0,05.

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
| **ro1 de 11 etapas** (en vez de 5; T ×2,2) | ≈ 0,77 (0,72 con σ alta) [ESTIMADO, ley 1/T sobre μ y σ] | 6 inversores; divisor ×4,8 (peor chip 2^24,4 → `kd 25`) | bajo: el SPICE con 9 y 11 etapas ya muestra el 1/T |
| ro1 de 13 etapas (T ×2,6) | algo más que con 11 [ESTIMADO] | 8 inversores; divisor ×6,8 (peor chip 2^24,86: `kd 25` justo) | margen de divisor escaso |
| ro1/2 (biestable T tras ro1; T ×2) | ≈ 0,72-0,74 [ESTIMADO] | un biestable; divisor ×4 (`kd 25`) | el biestable T a 2,7 GHz tiene su propia asimetría, sin simular |
| XOR de pares de bits | ≈ 0,80 [ESTIMADO] | ×2 de caudal | no arregla los cortes de salud, que miran los bits crudos |
| Bajar H a 0,50, semilla de 640 bits | — | nada en el circuito | rompe el criterio fijado de antemano |

Corrección de la revisión de la tarde: con la misma ley 1/T, más etapas no
pueden dar menos H que ro1/2 (antes ponía 0,66-0,72 para 11-13 etapas).
**Las tres opciones llevan el divisor a `kd 25`**: el RTL actual no lo
admite (contador de 24 bits, `G_CNT_BITS`; con `kd` ≥ 25 la máscara da la
vuelta sin avisar), así que hay que ensanchar el contador, subir
`G_KD_RESET` y abrir el rango de `cmd_kd` en el firmware (hoy 0-24).

**Recomendación (coincide con la revisión): ro1 de 11 etapas**, validado con
el mismo Monte Carlo y añadiendo la esquina ff a −40 °C y 1,32 V (la de
periodo más corto, que el Monte Carlo no tiene). Se decide junto con el 9.

## 7. `G_KD_MIN` (hoy 6)

**Dato**: los tests de salud no ven el régimen de poco jitter: en la Basys 3
con colocación fija no saltan ni a `kd 8`, donde SP 800-90B da 0,186 (bits
que alternan, ρ₁ −0,54); la batería tampoco distingue `kd 16` (H del modelo
0,47) de `kd 19` (0,9996). `CFG_KD` lo escribe el maestro por I2C: con el
mínimo en 6, un maestro erróneo o malicioso siembra con bits casi
deterministas sin alarma. El mínimo se comprueba al sembrar y resembrar
(`motor_top.vhd` línea 496) **y al arrancar el flujo** (línea 565): con 19 en
`basys3_top` no habría flujo a `kd` ≤ 18, ni campañas SP 800-90B ni
reinicios por debajo (la captura por trozos, `capturar`, sí sigue
disponible). Para caracterizar haría falta una variante con el mínimo bajo.

| Opción | Efecto |
|---|---|
| `G_KD_MIN` = 23 en el integrado (25 si ro1 se alarga, que exige ensanchar el contador: punto 6) | siembra imposible por debajo del divisor que pide el SPICE (2²³ con ±10 % de V_DD) |
| `G_KD_MIN` = 19 en `basys3_top` | el divisor que pide el jitter térmico medido en la placa |
| test de autocorrelación en línea | no protege: a `kd 10`, ρ₁ 0,053 queda a 1,7σ en 1 024 bits con α 2⁻³⁰ |

**Recomendación: subir `G_KD_MIN`** (23/25 en `motor_top`, 19 en
`basys3_top`, con una variante de caracterización con el mínimo bajo). Coste
de área nulo con 23; con 25, el del contador más ancho. Los bancos no cambian: `tb_motor_top` y
`tb_motor_solo_fuente` ya pasan `G_KD_MIN => 4` (anillo 10× lento);
`basys2_top` pasa 7. Habría que repasar los mínimos del firmware
(`motor_i2c`, plazos con `CFG_KD` alto: con 24 el arranque llega a 687 s).

## 8. Restricción de ro2 en la FPGA (4,2 ns)

**Dato** [Vivado]: con colocación fija, −0,120 ns (silenciosa) y −0,391 ns
(normal) contra 4,2 ns; caminos de 4,32 y 4,59 ns frente a 4,88 y 4,83 ns
medidos (márgenes del 12 y del 5 %). Se dejó en 4,2 ns para no cambiar la
implementación medida.

**Recomendación**: 4,5 ns en compilaciones nuevas, más una comprobación en
`build.tcl` del camino frente al periodo medido (un fallo de tiempos en el
divisor del ERO parecería aleatoriedad). Ojo (revisión): con 4,5 ns la
variante normal (camino 4,59 ns) ya incumple, y una comprobación a 0,9 ×
4,83 = 4,35 ns la pararía; o se mejora ese camino (registro intermedio entre
`bit_stb` y la escritura de `trng_capture`) o la comprobación se hace con la
silenciosa, que es la del producto. Cambia la implementación: tras ello,
repetir una captura corta de jitter y el O5.

## 9. Tiempos del contador del ERO en el integrado

**Dato**: el contador de 24 bits de `ero_core` corre con ro2, que en el
integrado son 2,73 GHz (5 etapas, tt; más en ff). En la síntesis
(`docs/sintesis_resultados.md`) no hay análisis de tiempos a esa frecuencia;
en la FPGA, el mismo dominio obligó a pasar a 11/13 etapas.

**Recomendación**: análisis de tiempos (STA) del dominio de ro2 con la
biblioteca sg13g2 antes de cerrar el punto 6; si no cierra, preescalar ro2
(un biestable T, ÷2) o alargarlo, y recalcular K_D con el SPICE.

## 10. Aislamiento de los anillos en el integrado

**Dato** [MEDIDO, Basys 3]: una modulación de ~39,4 kHz de fuente externa
(no es el tráfico I2C durante la captura; ¿convertidor conmutado?, hay una
portadora a ~480 kHz con bandas laterales a ±39,5 kHz) entra en la fase
relativa de los anillos, y la lógica colgada cambia su potencia ×15 (su
amplitud ×4). En la FPGA no se puede aislar; en el integrado sí.

**Recomendación**: en la memoria, como requisito de implementación física:
buffer a la salida de cada anillo (el SPICE ya lo pedía), `ro_mon` sin carga
en producto, y alimentación o anillo de guarda propios para los anillos.
Sin cambio de RTL.

## Orden sugerido

9 → 6 → 7 (el divisor mínimo depende de la longitud de ro1 y de cómo se
cuente ro2), 8 en paralelo, 10 en la redacción.
