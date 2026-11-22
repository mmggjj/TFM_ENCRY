# Decisiones pendientes de Mario (18-11-2026)

Revisado por un agente independiente el 18-11 por la noche (correcciones
aplicadas; `docs/basys3.md`, "Revisión de la tarde del 18-11").

## Decidido el 19-11-2026 (Mario) y aplicado

| Punto | Decisión | Aplicado |
|---|---|---|
| 6. Biestable | **ro1 de 11 etapas** | `motor_top` `G_ETAPAS_RO1` 7 → 11. Ojo: el SPICE simulaba 5 etapas y el RTL llevaba 7; la corrección es ×2,2 de periodo respecto a lo simulado. Monte Carlo con 11 etapas, cinco esquinas a 24 chips: H declarable 0,757 ≥ 0,60 (22-11, abajo) |
| 9. Tiempos de ro2 en el integrado | **ro2 de 13 etapas + preescalador ÷16** (13 y no 11, como se aplicó primero: con ro1 también de 11, los dos anillos serían iguales y tienden a engancharse) | Estimación [Yosys + ABC, biblioteca típica 1,2 V 25 °C]: el contador de 26 bits tarda 1,53 ns y un biestable sg13g2 necesita ~0,37 ns para conmutar (clk→Q 0,22 + setup 0,11 + inversor), frente a 0,366 ns de ro2 con 5 etapas: no cerraba nada. Ahora ro2 de 13 etapas (~0,95 ns, el primer biestable cierra con ×2,6 de margen) y `G_PRESC_RO2` = 4: el dominio del anillo (ERO, cruce, captura) corre a ro2/16 (~13 ns). `CFG_KD` sigue contando periodos de ro2. Sin biblioteca lenta en el PDK local: la esquina 1,08 V 125 °C queda sin comprobar |
| 7. `G_KD_MIN` | **25 integrado, 19 FPGA** | `motor_top` 25 (y `G_KD_RESET` 25, `G_KD_MAX` 26 con el contador ensanchado; un `CFG_KD` > máximo se ignora y levanta `DIAG.rechazada`); `basys3_top` 19/19 con `G_KD_MAX` 24 (con 26 el camino de ro2 subía a 4,41 ns); variante de caracterización con `GENERICOS="... G_KD_MIN=6"` |
| `CFG_KD` de la FPGA | **19** (H_∞ ≥ 0,99 con la cota baja 0,6·10⁻⁶) | recalibración con la ν y el sesgo de cada captura: 0,59-1,13·10⁻⁶ (18-11) y 0,95-1,35·10⁻⁶ (bitstream del 19-11) por banda |
| 8. Restricción de ro2 | **4,5 ns + comprobación** | `basys3.xdc` 4,5 ns; `build.tcl` para la silenciosa si el camino supera 0,9 × `RO2_MEDIDO_NS` (4,88). La paró una vez (4,407 > 4,392 ns, con el contador de 26 bits); con 24, camino 3,98 ns, WNS +0,524 ns |

Área [Yosys, biblioteca típica, celdas sin rutar]: `motor_top` 95,53 kGE (ro2 de 13; 95,52 con 11) frente a
95,09 kGE con la configuración anterior en la misma tanda (+0,5 %;
`results/sintesis_19_11.log`; el CSV no se toca hasta actualizar el cap. 6).

### Validación con SPICE (noche del 19-11; Monte Carlo completado el 22-11)

**Divisor** [SIMULADO → ESTIMADO; `docs/anillo_ihp.md` §4.4]: ro1 de 11
etapas en ss, −40 °C, 1,08 V, 8 realizaciones: Q por periodo
2,65-3,41·10⁻⁸. Con ro2 de 13 etapas (razón de periodos 1,175 simulada el
22-11; 13/11 = 1,182 estimada antes) y el factor de peor
chip, `CFG_KD` 24 da H_∞ 0,9997 y 25 ≈ 1: **`G_KD_MIN` 25 tiene un factor 2
de margen**.

**Biestable** [SIMULADO, sin ruido; `results/biestable_mc_e11.md` y
`results/biestable_mc_e11_sin_hueco.md`, `analysis/biestable_mc.py --fuentes
biestable_ihp_mc24_e11_criticas.log,biestable_ihp_mc24_e11_criticas_b.log,biestable_ihp_mc24_e11_resto.log`]:
**Monte Carlo completo, cinco esquinas, 24 chips por esquina**: críticas
en dos tandas (`mc24_e11_criticas`, 11, parada el 19-11 a las 22:45;
`mc24_e11_criticas_b`, 13, acabada el 22-11 a las 13:57) y ff/tt a 125 °C en
una (`mc24_e11_resto`, 22-11, 14:57-18:51). Leído con la regla de abajo,
fijada antes del resultado:

| Esquina | n | P(1) μ ± σ (IC 95 % de σ) | H en μ − 3σ | H con σ alta | peor chip (H) |
|---|---|---|---|---|---|
| sf, 125 °C, 1,08 V | 24 | 0,4631 ± 0,0183 (0,0142-0,0257) | **0,757** | 0,704 | 0,4166 (0,777) |
| sf, 125 °C, 1,2 V | 24 | 0,4642 ± 0,0100 (0,0078-0,0140) | 0,822 | 0,791 | 0,4355 (0,825) |
| ff, −40 °C, 1,32 V | 24 | 0,4784 ± 0,0088 (0,0068-0,0123) | 0,868 | 0,840 | 0,4568 (0,880) |
| ff, 125 °C, 1,32 V | 24 | 0,4700 ± 0,0098 (0,0076-0,0137) | 0,838 | 0,808 | 0,4447 (0,849) |
| tt, 125 °C, 1,2 V | 24 | 0,4811 ± 0,0119 (0,0093-0,0167) | 0,851 | 0,814 | 0,4673 (0,909) |

- **Oficial (todos los chips): H declarable 0,757 ≥ 0,60**, mínimo de las
  cinco esquinas. **H 0,60 queda cerrada** (con 5 etapas daba 0,532); el circuito
  no se corrige y los cortes 51/766 no cambian (`cortes_salud.py` 11/11, con
  el peor chip y con μ − 3σ). Ni con la σ en el extremo alto de su intervalo
  baja de 0,70.
- **Sensibilidad (hueco de fase ≤ 0,025):** 0,789 (sf 1,08 V, n 22; ff
  −40 °C n 21, ff 125 °C 0,837 con n 23, tt 125 °C 0,848 con n 22, sf 1,2 V
  sin cambios). Las dos lecturas pasan: no hay discrepancia y no
  hacen falta chips nuevos (punto 4 de la regla).
- Chips con hueco > 0,025: los dos de sf 1,08 V ya conocidos (0,082 y 0,068,
  primera tanda) y tres de ff (0,047 y 0,031 de la primera, 0,065 de la
  segunda); en la tanda de 125 °C, uno de ff (0,0253) y dos de tt (0,039 y
  0,036). sf 1,2 V no tiene ninguno; en la segunda tanda de las críticas, salvo ese de ff,
  ninguno pasa de 0,022. El peor chip de sf 1,08 V (0,4166) es uno de los de
  hueco: sin él, el peor es 0,4320 (H 0,816).
- **Diferencia entre tandas:** en sf 1,2 V las dos tandas tienen medias
  distintas (0,4700 ± 0,0069 frente a 0,4592 ± 0,0097, Welch p 0,004; en sf
  1,08 V p 0,15 con todos y 0,01 sin huecos; en ff p 0,78). Son sorteos
  independientes con el mismo programa; la causa no está comprobada (la
  candidata es el `T_CLK`, que sale de la simulación previa de otro chip y
  cambia de una tanda a otra). La cifra oficial junta las dos tandas, así que
  esa variación ya está dentro de la σ; con una sola tanda se habría
  infraestimado.
- **tt a 125 °C tiene un chip con el sesgo al revés** (rep 1, P(1) 0,5278,
  hueco 0,0025): el único de los 120 chips por encima de 0,5 (otro, de sf
  1,08 V con hueco 0,082, da 0,5000). Hace que
  Shapiro-Wilk rechace la normalidad (p 0,00) e infla la σ, lo que hace la
  cifra de esa esquina más conservadora, no menos. Causa sin mirar.
- Los avisos "bordes ff N, ideal 2" del log son del recuento por bordes, que
  no se usa: la P(1) ponderada por fase no necesita bordes limpios.
- **Monte Carlo de 5 etapas con la misma lectura de sensibilidad** (punto 5,
  `results/biestable_mc_sin_hueco.md`): 0,530 frente a 0,532 oficial. Quitar
  los chips con hueco no habría cambiado aquella decisión.

### Regla para leer los 24 chips del Monte Carlo (fijada el 22-11-2026, antes del resultado)

Propuesta de un revisor independiente (`results/revision_hueco_20261122.md`,
sin mirar P(1) de ningún chip), **aprobada por Mario el 22-11 a mediodía**,
con la tanda `mc24_e11_criticas_b` aún en marcha (15 de 39 chips):

1. **Muestra:** por esquina crítica, los 24 chips de `mc24_e11_criticas` (11)
   y `mc24_e11_criticas_b` (13), ni más ni menos; un chip que falle sin dar
   fila se repone y se anota. ff y tt a 125 °C, cuando se lancen, igual.
2. **Cifra oficial:** el criterio del 16-11 sin cambios, con todos los chips
   (`biestable_mc.py --fuentes ...` sin `--hueco-max`). Decide "≥ 0,60 o
   corregir el circuito".
3. **Sensibilidad** (se da siempre al lado, nunca decide sola): el mismo
   cálculo sin los chips con hueco de fase > **0,025**
   (`--hueco-max 0.025`), con el n que queda. El umbral sale del error de
   `p1_ponderada` (≈ hueco/√6 de desviación; ≤ 0,01 con 0,025, la resolución
   ya aceptada para la ventana de apertura), no de los datos. El 0,05 que se
   escribió arriba antes de esta regla queda sustituido.
4. **Discrepancia:** si una lectura da ≥ 0,60 y la otra < 0,60 en una
   esquina, no decide ninguna: se simulan chips nuevos de esa esquina hasta
   tener 24 con hueco ≤ 0,025, y esos deciden.
5. El Monte Carlo de 5 etapas se queda como está; se le añade la misma
   lectura de sensibilidad para comparar.
6. Esta campaña no cambia cómo se elige `T_CLK`; para las siguientes, reloj
   con intervalos al azar (validarlo antes sin desapareamiento). Indicio, sin
   comprobar, de enganche del anillo al reloj en algunos chips (otra razón para
   que ninguna cifra dependa de ellos).

### Factor de peor chip del divisor con 11 etapas: regla fijada el 22-11-2026 a las 19:00, antes de simular

Hoy el divisor del integrado (`docs/anillo_ihp.md` §4.4) usa como peor chip
la Q mínima de las 8 realizaciones nominales de 11 etapas dividida por 1,175,
el cociente peor/medio de K_D de los 23 chips de 5 etapas (§4.3). Se sustituye
por un Monte Carlo de 11 etapas en el mismo punto. Regla:

1. **Muestra:** 24 chips en ss, −40 °C, 1,08 V (el peor punto), ro1 de 11
   etapas, `--mismatch`, 900 ns (~704 periodos, igual que las 8 nominales),
   con la histéresis:

       ~/eda/venv/bin/python analysis/anillo_ihp_repeticiones.py --n 24 --procesos 5 \
         --tstop 900n --esquina mos_ss --temp -40 --vdd 1.08 --etapas 11 --mismatch \
         --escalas-primera 1 --prefijo mc_ss_m40_v108_e11_

2. **Exclusión:** solo por inconsistencia de los cruces, no por el valor: un
   chip cuyos cruces ocupan, (cruces + 10) · T, más de un 1 % fuera de la
   mediana de los 24 (el criterio del chip 9 de §4.3). Se anota y se repone
   con otro hasta tener 24.
3. **Cifras:** K_D de cada chip = 0,2286 / Q del chip (periodos de ro1).
   **Factor = K_D peor / K_D medio**, la misma definición que con 5 etapas
   (4 494 997 / 3 824 707 = 1,175). Se da también la dispersión de Q entre
   chips frente a la de las 8 nominales (10,5 %).
4. **Divisor:** H_∞ para `CFG_KD` 22-26 con la razón 1,1754, con Q media de
   los 24 y con el peor chip **directamente** (la Q mínima de los 24; ya no
   hace falta dividir por un factor), y la columna de antes (Q mínima nominal
   ÷ factor nuevo) para comparar.
5. **Decisión:** si el peor chip da H_∞ ≥ 0,98 con `CFG_KD` 24, `G_KD_MIN` 25
   conserva el factor 2 de margen y no cambia nada. Si 24 da < 0,98 y 25 da
   ≥ 0,98, el margen baja de 2 y decide Mario (subir `G_KD_MIN` a 26, que es
   `G_KD_MAX`). Si 25 da < 0,98, hay que subir el divisor. Como referencia,
   para que 24 no llegue el peor chip tendría que tener Q < 1,16·10⁻⁸ por
   periodo, 2,6 veces por debajo de la media nominal (3,00·10⁻⁸); para 25,
   Q < 0,58·10⁻⁸.

Duración [ESTIMADO]: ~2,1 h por chip, 5 a la vez, unas 11 h.

### Revisión independiente del RTL del 19-11 (22-11-2026)

Agente sin las conclusiones de la sesión; informe, bancos propios, mutante y
logs en `results/revision_rtl_20261122/`. **El requisito se cumple**
[SIMULADO]: la ventana es 2^`CFG_KD` periodos de ro2 (medida de 4 a 19;
de 20 a 26 por la máscara del contador) y nada siembra por debajo de
`G_KD_MIN`. Hallazgos y qué se hizo:

| # | Gravedad | Hallazgo | Hecho |
|---|---|---|---|
| 1 | medio | el medidor escribía `CFG_KD` 24 antes de sembrar: con `G_KD_MIN` 25 no sembraba nunca en el integrado (falla cerrado) | el medidor siembra con el `CFG_KD` de reset (`G_KD_RESET`, el mínimo de cada versión); banco en PC 0 fallos |
| 2 | medio | `CFG_KD` ≥ 32 se truncaba a 5 bits (32 → 0) sin `rechazada` | se compara el byte entero |
| 3 | medio | `CFG_KD` 0-3 se aceptaba con ventana real 2^4 | se rechaza por debajo de `G_PRESC_RO2`, con `rechazada`; modelo en PC igual |
| 4 | menor | una escritura válida de `CFG_KD` no baja `rechazada` | documentado en `mapa_registros.md` |
| 5 | menor | el límite del cruce de dominio pasa a `CFG_KD` ≥ 7 | `mapa_registros.md` y cabecera de `bit_cdc` |
| 6 | menor | ningún banco medía la ventana (un mutante con la mitad pasaba `tb_motor_top`, que además se colgaba en 9c) | banco nuevo `tb_ventana_ero` (2^`CFG_KD` exacto de 4 a 14 y rechazos, 47/47); plazo en el bucle de 9c; `tb_motor_top` comprueba 32, 255 y < preescalador (con `G_PRESC_RO2` = 2 solo en ese banco) |
| 7-8 | nota | restos del máximo 24 en `crudoq`, `campana_motor.py` y comentarios | corregidos |
| 9 | nota | sin SDC del reloj dividido (los 1,53 ns siguen sin STA); la cadena de biestables T añade ruido de muestreo no simulado; `kd_ero` entra sin sincronizar al dominio dividido (solo cambia con el motor libre) | abierto, para la implementación física |
| 10 | nota (previo) | la primera ventana tras cambiar `CFG_KD` es más corta (afecta a lo sumo a un bit); `CFG_KD` se puede cambiar con una captura en curso | abierto |

La comparación nueva de `CFG_KD` también está en `basys3_top` (sin
preescalador solo cambia el rechazo de ≥ 32); el bitstream de la placa es el
del 19-11, anterior a este cambio: sus medidas no se ven afectadas (solo
difiere ante escrituras fuera de rango).

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
