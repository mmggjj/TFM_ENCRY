# Revisión metodológica: chips con hueco de fase grande en el Monte Carlo del biestable (22-11-2026)

Revisor independiente (agente). Pregunta: qué hacer con los chips cuyo reloj de
muestreo cubre mal el ciclo del anillo (hueco de fase máximo 0,05-0,08),
decidido **antes** de ver el resultado de 24 chips por esquina crítica.

**Lo que he mirado:** `analysis/biestable_ihp.py`, `analysis/biestable_mc.py`,
`docs/basys2.md` (secciones "El biestable real", "H 0,60: provisional",
"Resultado del Monte Carlo"), `docs/decisiones_pendientes.md`, los logs
`results/biestable_ihp_*.log` (solo periodo y hueco, quitando la P(1) de cada
línea) y los 145 `.npz` con desapareamiento de `results/biestable_ihp_crudo/`
(solo `tk`, `t_clk`, cruces del anillo y fases; ni bits ni P(1)).
**No he calculado ni mirado la P(1) de ningún chip.** Aviso: en
`docs/decisiones_pendientes.md` (lectura obligada para el contexto) están
escritas la P(1) de los dos chips de hueco grande de sf a 1,08 V y las cifras
0,759 (todos) y 0,874 (sin ellos) con 11 chips. Las he visto; no las he usado
para nada de lo que sigue. Lo que sí importa: **quien decide ya sabe que
excluir sube la H**, y eso pesa en la recomendación.

Cuentas propias: solo con datos sintéticos, en
`/tmp/claude-1000/revision_hueco/` (`ratios.py`, `lock.py`, `sintetico.py`;
`~/eda/venv/bin/python`). Todo lo numérico de abajo es [SINTÉTICO] salvo los
huecos y las razones de reloj, que salen de los `.npz` [SIMULADO, SPICE].

## Recomendación

**(a) como cifra oficial, con una lectura de sensibilidad fijada ahora y una
regla para el único caso en que las dos discrepen.** No excluir chips de la
cifra oficial.

### Regla exacta

1. **Muestra.** Por esquina crítica (sf 125 °C 1,08 V; sf 125 °C 1,2 V; ff
   −40 °C 1,32 V), los 24 chips de las dos tandas planeadas
   (`mc24_e11_criticas`, 11, y `mc24_e11_criticas_b`, 13), en orden de
   lanzamiento: ni más ni menos (salvo una ejecución que falle sin producir
   fila, que se repone con un chip nuevo y se anota). Las esquinas de después
   (ff y tt a 125 °C) siguen la misma regla con el mismo script.
2. **Cifra oficial = criterio del 16-11 sin tocar**: `p1w_ff` de todos los
   chips, μ ∓ 3σ, H por esquina, mínimo sobre esquinas
   (`analysis/biestable_mc.py` tal cual). Es la que decide "≥ 0,60 / corregir
   el circuito" y la única que puede usarse si algún día se quiere **subir** la
   H declarada (y recalcular cortes RCT/APT).
3. **Sensibilidad (se publica siempre al lado, nunca decide sola):** el mismo
   cálculo sin los chips con `hueco_fase` > **0,025**, dando el n que queda y
   el IC de σ. El umbral sale del presupuesto de error, no de los datos:
   con hueco g el error de `p1_ponderada` tiene desviación ≈ g/√6 y máximo
   ≈ g (dos bordes, cada uno a ±g/2). g ≤ 0,025 deja el error en ≤ 0,010 de
   desviación, la misma resolución (±0,01) que ya se aceptó para la ventana de
   apertura (`docs/basys2.md`, 15-11). La cifra 0,05 que propone
   `decisiones_pendientes.md` se escribió después de ver los dos chips y no
   cumple ese presupuesto (en 0,025-0,05 la desviación sintética es 0,012).
   Columna informativa adicional: el hueco de cada chip.
4. **Discrepancia.** Si la oficial queda < 0,60 y la de sensibilidad ≥ 0,60
   en la misma esquina, no se decide con ninguna de las dos: se simulan chips
   nuevos de esa esquina (mismo script; ngspice no deja repetir un chip) hasta
   tener 24 con hueco ≤ 0,025, y **esos 24** deciden. Si la oficial es ≥ 0,60,
   H 0,60 se cierra con la oficial, aunque la sensibilidad salga más alta.
   El caso contrario (oficial ≥ 0,60 y sensibilidad < 0,60) es muy improbable
   (excluir es neutro en media); si pasa, se trata igual: 24 chips limpios.
5. **Mismo tratamiento hacia atrás:** el Monte Carlo de 5 etapas
   (`biestable_mc.md`) se queda como está (oficial con todos los chips, como
   se hizo); para la comparación 5 → 11 etapas se da también su lectura de
   sensibilidad con el mismo umbral, para que las dos columnas sean homogéneas.
6. **No cambiar ahora cómo se elige T_CLK** en lo que queda de las críticas ni
   en ff/tt a 125 °C (homogeneidad dentro de la campaña). La mejora del reloj
   (abajo) es para campañas futuras y se valida antes.

## Argumentos

### Qué hace el código

- `un_caso()` mide el periodo con una simulación previa (otro sorteo de
  desapareamiento) y pone `T_CLK = t_prev·(2 + 0,618)`. La razón real
  `r = T_CLK/T_chip` es `2,618·t_prev/T_chip`; en los 145 chips,
  `t_prev/T_chip` va de 0,956 a 1,035, es decir, la parte fraccionaria de r
  barre 0,50-0,71: la razón áurea no se conserva y r cae a veces junto a
  4/7, 7/12, 3/5, 8/13, 5/8, 7/11, 9/14, 2/3.
- Con N = 400 flancos, si |frac(r) − p/q| ≲ 1/(Nq) las fases se agrupan en q
  bandas y el hueco es ≈ 1/q. Todos los chips con hueco > 0,05 tienen
  |frac(r) − p/q| ≤ 1·10⁻⁴ con q = 11-14 (q = 5 en uno de 5 etapas); los que
  tienen hueco 0,02-0,05 están algo más lejos del racional.
- `hueco_fase` se calcula solo con `tk` y los cruces del anillo: **no depende
  de la salida del biestable**. Por eso es un criterio de calidad de la medida
  que no mira la respuesta.
- `p1_ponderada` reparte a cada muestra medio hueco a cada lado: en cada borde
  de captura pone la frontera en el punto medio entre las dos muestras
  vecinas. Error por borde uniforme en ±g_borde/2; en P(1), suma de los dos.

### Error de la medida frente al hueco [SINTÉTICO]

Respuesta de escalón con P(1) 0,47, racimos de apertura de 0,015 en cada
borde, fases con los 145 r reales y fase inicial al azar (4 000 casos):

| hueco | casos | error medio | desviación | máx. abs. |
|---|---|---|---|---|
| < 0,010 | 3 161 | −0,0001 | 0,0050 | 0,019 |
| 0,010-0,025 | 467 | −0,0003 | 0,0088 | 0,023 |
| 0,025-0,050 | 195 | −0,0017 | 0,0124 | 0,031 |
| 0,050-0,100 | 177 | −0,0021 | 0,0272 | 0,085 |

9,3 % de los chips con hueco > 0,025 y 4,4 % con > 0,05 (en los reales,
críticas de 11 etapas hasta ahora: 5 de 48 y 3 de 48). Un chip con hueco
0,08 trae un error de ±0,03 típico y hasta ±0,08: del orden de la σ entre
chips que se quiere medir, o mayor.

### Qué hace eso con μ − 3σ [SINTÉTICO]

24 chips, P(1) verdadera ~ N(0,47; σ), r tomado de los 145 reales, sin
racimos (para aislar el hueco), 1 000 repeticiones por fila. Media de H
(desviación) y probabilidad de que la H estimada supere la de la población:

| σ verdadera | H población | todos | sin hueco > 0,05 | sin hueco > 0,025 | P(1) verdadera |
|---|---|---|---|---|---|
| 0,007 | 0,860 | 0,842 (0,022); 0,16 | 0,854 (0,011); 0,29 | 0,857 (0,010); 0,37 | 0,860 (0,009); 0,53 |
| 0,010 | 0,837 | 0,824 (0,020); 0,28 | 0,833 (0,014); 0,41 | 0,835 (0,014); 0,47 | 0,838 (0,012); 0,54 |
| 0,020 | 0,761 | 0,756 (0,027); 0,43 | 0,761 (0,026); 0,51 | 0,762 (0,027); 0,52 | 0,763 (0,025); 0,55 |
| 0,035 | 0,655 | 0,654 (0,039); 0,48 | 0,657 (0,039); 0,51 | 0,658 (0,040); 0,52 | 0,659 (0,038); 0,54 |

Lectura:

- **Contarlos todos es conservador en media** (el error de medida se suma a
  la varianza entre chips e infla σ) y el sesgo crece cuanto menor es la σ
  verdadera (−0,018 de H con σ 0,007). Pero no es conservador en cada
  realización (16-48 % de las veces sale por encima) y duplica la dispersión
  cuando σ es pequeña: una cifra peor medida, no solo más prudente.
- **Excluir por hueco no sesga** (la media queda en la de la población, salvo
  una fracción de la propia dispersión) y cuesta poco en precisión.
- Para la decisión ≥ 0,60 la regla casi nunca importa: con σ 0,035, que es
  donde se estaría cerca de 0,60, las tres reglas dan lo mismo en ±0,004.
  Importa para la **cifra** que se declare y para una futura subida de H.

### ¿Excluir puede sesgar la muestra?

- El hueco depende solo de `t_prev/T_chip` (dos sorteos del periodo del
  anillo), no del biestable. Los huecos grandes aparecen en `t_prev/T_chip`
  0,987-1,010, en el centro de la distribución: no seleccionan chips de
  periodo extremo. Y aunque lo hicieran, el sesgo va como retardo
  asimétrico/T, y el periodo varía ±1-2 % entre chips: ≲ 10⁻³ en P(1).
- El desapareamiento del anillo y el del biestable son sorteos de
  transistores distintos (local, no global): la exclusión es "al azar"
  respecto a la P(1) a primer orden. El único lazo posible es el acoplo
  biestable/buffer → anillo (siguiente punto), débil.
- Conclusión: excluir sería estadísticamente defendible. No lo recomiendo
  como cifra oficial por otra razón: la regla de exclusión se propone después
  de saber que sube la H (decisiones_pendientes.md, 0,759 → 0,874), y el
  criterio del 16-11 se fijó precisamente para que el resultado no eligiera la
  regla. La cifra con todos los chips es la fijada, va del lado seguro en
  media y es la que se usó con 5 etapas.

### Indicio de enganche del anillo al reloj [SIMULADO, inferido]

En dos chips (sf 1,08 V rep 5 de 11 etapas; ff 1,32 V rep 21 de 5 etapas)
frac(r) coincide con 7/12 y 8/13 a 2,5·10⁻⁶ y 1,6·10⁻⁷; con la dispersión de
periodos observada, por azar se esperarían 0,06 casos así en 145
(P(≥ 2) ≈ 0,002). Con |d| < 5·10⁻⁵ hay 5 frente a 1,05 esperados. Es
compatible con que el reloj ideal, a través del biestable y el buffer
("modulación 0,01 ps" en el log), engancha el anillo cuando la razón está a
~10⁻⁵ de un racional. Consecuencias:

- En los chips enganchados la rejilla de fases no está al azar respecto a los
  bordes del anillo: la fase de enganche la fija el circuito, así que el error
  de `p1_ponderada` puede no ser de media cero en ellos. Otra razón para no
  apoyar ninguna cifra en un chip con hueco grande, y para que la cifra
  oficial (que los incluye) vaya acompañada de la de sensibilidad.
- Es un artefacto del montaje (reloj ideal, sin ruido); no dice nada directo
  del integrado, donde ro2 tiene jitter. Sí recuerda que el acoplo existe
  (ro1 de 11 y ro2 de 13 se eligieron distintos por eso). Sin comprobar:
  bastaría mirar si la fase de cada clase de residuo deriva a lo largo de la
  simulación en esos `.npz`.

### Corregir la medida con lo guardado: no

Los `.npz` guardan fases y bits de las 400 muestras, y el simulador no deja
repetir el chip. Dentro de un hueco no hay información: lo único que se puede
sacar es una **cota** por chip, [P(1) con cada hueco de borde asignado entero
a 0, ídem a 1], de anchura ≈ suma de los huecos en los bordes. Sirve como
columna de incertidumbre (opcional), no para corregir. Restar la varianza de
medida a σ² (errores en variables) mete un modelo del error (uniforme,
independiente) que el enganche pone en duda: no lo recomiendo como cifra.

### Lo que se hizo antes

- Campaña del 15-11 descartada entera: el motivo principal fue el montaje
  (cinco biestables tirando del anillo); los huecos del 6-12 % iban con él. No
  es precedente de excluir chips sueltos por hueco.
- Monte Carlo de 5 etapas: se contaron todos, con huecos hasta 0,077 (8 chips
  > 0,025 de 104; 4 > 0,05). Cambiar la regla solo para 11 etapas rompería la
  comparación 5 → 11; por eso el punto 5 de la regla.

## Mejora del método para campañas futuras (no para esta)

El fallo es elegir un periodo fijo con una razón "muy irracional" a partir de
un periodo que se conoce con ±2 %: a esa tolerancia la razón áurea no existe.
Dos arreglos, por orden de preferencia:

1. **Reloj PWL con intervalos al azar** (semilla fija de numpy):
   `T_k = t_prev·(2 + u_k)`, u_k uniforme en [0, 1). Las fases salen
   uniformes sea cual sea el periodo del chip, el hueco máximo típico con
   N = 400 es ≈ ln N / N ≈ 0,015 (P(> 0,025) ≈ 2 %, sin cola de 0,08) y no hay
   inyección periódica que enganche el anillo. `tk` ya se guarda, así que el
   análisis no cambia. Validar antes en esquinas **sin** desapareamiento
   (deterministas: mismo chip): P(1) con reloj fijo de hueco pequeño frente a
   reloj al azar, diferencia ≤ 0,005.
2. Mínimo: comprobar `hueco_fase` al acabar y relanzar un chip nuevo si
   supera 0,025 (es la regla 4 hecha siempre). Coste ~10 % más de CPU.

`biestable_mc.py` lee los logs con una regex que no recoge el hueco; para la
columna de sensibilidad hay que leerlo (está en la misma línea del log y en
`hueco_fase` del CSV / `.parcial.csv`). No lo he tocado.

## Riesgos

- **La cifra oficial puede quedar por debajo de la verdadera** (hasta
  −0,02 de H con σ pequeñas) y, una de cada seis veces o más, por encima. Con
  H lejos de 0,60 no cambia la decisión; sí la cifra que se escriba en la
  memoria: escribir las dos, diciendo cuál decide.
- **Bifurcación de caminos:** cualquier umbral fijado ahora está fijado con
  dos chips conocidos. Por eso el umbral se justifica con el presupuesto de
  error (0,025) y no con lo que separa a esos dos (0,05), y la sensibilidad
  nunca decide sola.
- **n efectivo:** con 24 chips y ~10 % excluidos, la sensibilidad queda en
  n ≈ 21-22; el IC de σ se ensancha poco.
- **Normalidad:** los chips con error grande dan colas pesadas
  (Shapiro-Wilk p 0,00 con 11 chips según decisiones_pendientes). μ ∓ 3σ
  supone normalidad; dar Shapiro-Wilk en las dos lecturas.
- Todo lo cuantitativo de esta revisión es sintético con un modelo de
  escalón + racimos; los racimos reales de la apertura no son mi patrón
  arbitrario. El orden de magnitud (error ≈ g/√6) no depende de eso.
