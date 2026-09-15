# Modelo del ERO y estimador de jitter: resultados de la validación

**Fecha:** 12-09-2026. **Código:** `analysis/ero_model.py`,
`analysis/jitter_estimator.py`. Ambos traen `autotest()`; reproducir con
`python ero_model.py` y `python jitter_estimator.py` (0 fallos a fecha de
hoy: 24 y 20 comprobaciones respectivamente).

Todo lo de este documento es **teoría y simulación**, no hay hardware por
medio. Su función es exactamente esa: comprobar que el método de medida
funciona *antes* de aplicarlo a la placa, igual que la suite NIST del
TFM_RNG se autovalidó contra los vectores del estándar antes de tocar el
ESP32. Si el estimador no recupera un jitter que le inyectamos nosotros,
no sirve para medir el que no conocemos.

---

## 1. La ecuación 14 de Baudet no es una cota inferior

La literatura cita el Corolario 1 de Baudet et al. (2011) como *cota
inferior* de la entropía por bit:

> H ≥ H(s(Δt) | φ(0)) = 1 − (4/(π² ln2))·e^(−4π²Q) + O(e^(−6π²Q))

Leído con cuidado, la desigualdad es solo la primera parte: la tasa de
entropía de la secuencia es al menos la del bit condicionado a la fase
anterior exacta. La **expresión de la derecha es un desarrollo asintótico
de esa entropía condicionada, no una cota de ella**. Y todos los términos
omitidos son negativos, así que el truncamiento la sobreestima.

Comprobación numérica (entropía exacta calculada con la gaussiana
envuelta, rejilla de 8192 fases):

| Q | Exacta | Orden 2 | Orden 1 (ec. 14) | Error de la ec. 14 |
|---|---|---|---|---|
| 0,02 | 0,7013194 | 0,7100952 | 0,7345213 | +3,3·10⁻² |
| 0,05 | 0,9163001 | 0,9164920 | 0,9187783 | +2,5·10⁻³ |
| 0,10 | 0,9886728 | 0,9886733 | 0,9887174 | +4,5·10⁻⁵ |
| 0,15 | 0,9984319 | 0,9984319 | 0,9984327 | +8,5·10⁻⁷ |
| 0,20 | 0,9997823 | 0,9997823 | 0,9997823 | +1,6·10⁻⁸ |

**Término de orden 2.** Desarrollando la entropía binaria en el sesgo,
h₂(½+ε) = 1 − (1/ln2)·Σ_{n≥1} (2ε)^{2n}/(2n(2n−1)), y promediando sobre
la fase con ε = A·sin(2πφ), A = (2/π)·e^(−2π²Q):

  E[ε²] = A²/2, E[ε⁴] = 3A⁴/8
  H(s|φ₀) = 1 − (1/ln2)·[A² + A⁴/2 + …]
          = 1 − (4/(π² ln2))·e^(−4π²Q) − (8/(π⁴ ln2))·e^(−8π²Q) − …

El siguiente término va como e^(−8π²Q), **no** como e^(−6π²Q). Añadirlo
reduce el error de la ec. 14 en un factor 95 a Q = 0,10, 690 a Q = 0,15 y
4970 a Q = 0,20 (apartado 2 del autotest), lo que confirma la deducción.

**Consecuencia práctica:** en la zona de trabajo (Q ≈ 0,2) el error de la
ec. 14 es de 10⁻⁸ y da igual. En la zona de un generador mal dimensionado
(Q ≈ 0,02) la ec. 14 regala un 3,3 % de entropía que no existe. La memoria
usará el **cálculo exacto** como valor conservador y citará la ec. 14 como
lo que es, una aproximación asintótica excelente para Q ≳ 0,1.

## 2. La min-entropía del primer armónico sí es válida

El estado del arte dejaba pendiente validar la derivación de min-entropía
a partir del sesgo del primer armónico (era una deducción propia,
aproximada). Queda validada: H_min = −log₂(½ + (2/π)e^(−2π²Q)) coincide
con el cálculo exacto con error < 10⁻⁴ bits en todo el rango Q ∈ [0,05;
0,30], y el sesgo máximo del primer armónico coincide con el exacto con
error < 0,02 % (apartados 3 y 4 del autotest). Los armónicos superiores
van como e^(−18π²Q) y son despreciables.

## 3. Objetivo de diseño: Q ≥ 0,23

AIS 20/31 v3.0 (PTG.2.2) admite dos criterios alternativos. Resueltos por
bisección sobre las entropías exactas:

| Criterio | Q mínima |
|---|---|
| Shannon ≥ 0,9998 | 0,2022 |
| **min-entropía ≥ 0,98** | **0,2286** |
| Shannon ≥ 0,9998 según la ec. 14 | 0,2021 (optimista) |

El criterio de min-entropía es el más exigente, y además es el que usa
NIST SP 800-90B, así que es el que adopta el TFM. **Objetivo de diseño:
Q ≥ 0,23; consigna con margen, Q = 0,30** (que da H_min = 0,9951 y
Shannon = 0,999996). El margen cubre la caída de jitter térmico al
enfriar el chip, que es el ataque de prueba de Fischer y Lubicz.

## 4. El estimador de jitter necesita dos correcciones

El método de Fischer y Lubicz mide la fracción c de pares de bits
(b_j, b_{j+M}) distintos dentro de un bloque y ajusta Var(c) = 4·M·Q_raw.
Aplicado tal cual, con un ajuste de recta, **subestima Q_raw entre un
13 % y un 38 %** según el jitter. Dos causas, ambas identificadas y
corregidas:

**a) Efecto vértice.** c no es lineal en la fase acumulada: es una onda
*triangular* de periodo 1, con pendiente ±2. Cuando la fase determinista
(M·ν mod 1) cae cerca de un vértice, la distribución lo cruza, la
pendiente cambia de signo dentro de la distribución y la varianza se
comprime hasta la mitad. Medido: con Q_raw = 2·10⁻⁶, la razón entre la
varianza observada y 4·M·Q vale 1,03 cuando la media de c está en la
banda central y cae a **0,38** cuando la media vale 0,910.

El vértice se detecta con la **propia media medida**, sin conocer nada del
anillo: c̄ ≈ 0 o c̄ ≈ 1 es vértice, c̄ ≈ ½ es el centro de la rampa. El
estimador descarta las distancias M con c̄ fuera de la banda [0,15; 0,85] y
aquellas en que 3·√(M·Q) alcanza el vértice, iterando sobre su propia
estimación de Q.

**b) El ruido de estimación no es constante con M.** Estimar una fracción
con N pares introduce una varianza que escala con c̄(1−c̄), y c̄ cambia con
M. Ajustarlo como ordenada en el origen constante sesga la pendiente. Se
ajusta como segundo regresor: Var(c) = Q·(4M) + κ·c̄(1−c̄)/N.

El coeficiente κ ajustado sale ≈ 0,3, no 1: la media dentro de un bloque
no es un muestreo aleatorio sino una secuencia equidistribuida (la fase
avanza ν irracional por muestra), y su convergencia es mejor que la
binomial. Es un parámetro de estorbo, no un resultado.

**Resultado tras corregir** (20.000 bloques de 100 pares, 2 Mbit):

| Q_raw real | Estimada | Error | σ/T | Distancias usadas |
|---|---|---|---|---|
| 2,0·10⁻⁷ | 1,979·10⁻⁷ | −1,07 % | 4,45·10⁻⁴ | 19 |
| 5,0·10⁻⁷ | 5,060·10⁻⁷ | +1,21 % | 7,11·10⁻⁴ | 18 |
| 2,0·10⁻⁶ | 2,037·10⁻⁶ | +1,86 % | 1,43·10⁻³ | 16 |
| 8,0·10⁻⁶ | 8,039·10⁻⁶ | +0,48 % | 2,84·10⁻³ | 9 |
| 3,0·10⁻⁵ | 2,977·10⁻⁵ | −0,78 % | 5,46·10⁻³ | 5 |

Error < 2 % en un rango de 150× en Q, coherente con el < 5 % que declaran
los autores del método. Repetibilidad con 8 semillas: sesgo −0,56 %,
dispersión 4,0 %. El exponente de acumulación ajustado vale 1,009, como
debe ser en un simulador sin flicker: ese mismo exponente, medido en la
placa, es el que separará la componente térmica (b = 1, cuenta como
entropía) de la de flicker o jitter global (b = 2, no cuenta).

## 5. Lo que esto fija del diseño en la FPGA

**La captura puede ser por trozos, y eso abarata mucho la FIFO.** Los
bloques del estimador no necesitan ser consecutivos: cada uno solo
necesita N + M bits contiguos. Validado en el apartado 4 del autotest con
20.000 trozos independientes de 2100 bits: error −0,30 %. Por tanto la
FPGA captura a la velocidad del anillo en una FIFO de **N + M_máx bits,
del orden de 2–8 kbit**, la vuelca despacio por SPI y repite. No hacen
falta los 2 Mbit contiguos, que no cabrían cómodamente en BRAM.

**Coste de la campaña de jitter:** 20.000 trozos × 2100 bits ≈ 5,1 MB por
punto de medida. A 10 Mbit/s de SPI son unos 4 s de transferencia por
punto; el límite lo pone la sobrecarga por trozo, no el volumen.

**Divisor y caudal.** Con Q_gen = K_D · Q_raw y el objetivo Q ≥ 0,2286:

| σ/T por periodo | Q_raw | K_D | Caudal con RO2 a 500 MHz |
|---|---|---|---|
| 7,1·10⁻⁴ | 5·10⁻⁷ | 457.200 | 1,09 kbit/s |
| 1,4·10⁻³ | 2·10⁻⁶ | 114.300 | 4,37 kbit/s |
| 2,8·10⁻³ | 8·10⁻⁶ | 28.575 | 17,5 kbit/s |

Estas cifras encajan con la literatura: Fischer y Lubicz obtienen
K_D ≈ 430.000 con σ = 5,01 ps sobre T = 7,81 ns, y el modelo de aquí
reproduce ese número. Órdenes de magnitud esperables en Artix-7 (28 nm,
2–4 ps por periodo de 3–5 ns [ESTIMADO, Petura 2016]): **K_D entre 3·10⁴ y
5·10⁵, caudal entre 1 y 20 kbit/s por anillo**.

**Consecuencia de arquitectura:** un solo ERO da kbit/s, no Mbit/s. Para
sembrar el DRBG con 256 bits de entropía plena hacen falta ≥ 512 bits de
min-entropía, es decir ~0,5 kbit crudos con H_min ≈ 0,98, o sea **entre
0,03 y 0,5 s por semilla**. Es de sobra para el caso de uso (una semilla
cada muchos bloques cifrados), y confirma que la elección del ERO frente a
arquitecturas de más caudal es correcta aquí: el TFM necesita entropía
*demostrable*, no rápida. Si se quisiera más caudal, la vía limpia es
instanciar varios ERO independientes, cada uno con su propia cota.

## 6. Lo que queda por validar (necesita hardware)

1. σ real por periodo en el XC7A35T, que no está publicado para esta
   familia.
2. El exponente b: si en la placa sale 2 en vez de 1, hay flicker o
   jitter global dominante y K_D no puede crecer indefinidamente.
3. Separación local/global con tres anillos (Lubicz–Skórski 2024).
4. Contraste de la cota del modelo con los diez estimadores no-IID de
   SP 800-90B sobre los bits crudos.
5. Que los anillos no se enganchen entre sí (injection locking), lo que
   invalidaría la independencia entre instancias.

---

## 7. Validación del banco de transistores (12-09-2026)

Primera campaña con ngspice sobre el anillo de cinco etapas, modelos
genéricos de marcador de posición. Los valores absolutos no valen para la
memoria; lo que se valida aquí es **el banco**, no la tecnología.
Datos en `results/spice_ruido_s1.csv`, comando en
`analysis/campana_ruido.py`.

### 7.1 Resolución del banco

| Ruido inyectado | Jitter por periodo medido |
|---|---|
| Ninguno | **1,383 fs** |
| 10⁻²⁰ A²/Hz | 1200 fs |

Con las fuentes de ruido apagadas, todo jitter que aparezca es numérico.
Sale 1,38 fs, unas 870 veces por debajo de la señal más pequeña que
queremos medir. El banco tiene resolución de sobra.

**Ojo con el arranque.** La primera medida daba un suelo de 0,33 ps, del
mismo orden que el jitter a medir. No era ruido: era el transitorio de
arranque del oscilador, que tarda un ciclo en estabilizarse. Con los
primeros veinte cruces descartados el suelo baja tres órdenes de
magnitud. Es un ejemplo claro de por qué hay que medir la resolución del
instrumento antes de interpretar nada, y de que un dato malo puede venir
de la ventana de análisis y no del circuito.

### 7.2 Ley de escalado, y dónde se rompe

El jitter debe escalar con la raíz de la densidad espectral inyectada.

| Densidad relativa | σ medido | Escalado observado | Escalado teórico | Corriente de ruido / corriente de etapa |
|---|---|---|---|---|
| ×1 (10⁻²⁰) | 1200 fs | referencia | referencia | 0,20 |
| ×4 | 2416 fs | **×2,01** | ×2,00 | 0,40 |
| ×16 | 25588 fs | ×21,3 | ×4,00 | 0,81 |

El tramo ×1 a ×4 cumple la ley con un 0,5 % de error. El punto ×16 se
sale por un factor cinco, y la causa está medida: la corriente eficaz de
las fuentes de ruido llega al 81 % de la corriente con la que la etapa
carga su capacidad (783 µA estimados). A ese nivel ya no es una
perturbación pequeña sino que compite con el propio funcionamiento del
circuito, y se nota además en que el periodo medio cae de 230,3 a
227,8 ps, cosa que un ruido de media nula no debería hacer.

**Criterio de validez para futuras campañas:** mantener la corriente
eficaz de ruido por debajo de ~40 % de la corriente de carga de la etapa,
y comprobar siempre que el periodo medio no se desplaza al activar el
ruido. Ese desplazamiento es la señal de alarma de que se ha salido del
régimen lineal.

Nota: en Cadence con el PDK real esto no se plantea igual, porque el
análisis de ruido transitorio inyecta el ruido propio de los dispositivos
y su amplitud no la elige uno. El criterio sigue valiendo como
comprobación de cordura.

### 7.3 Exponente de acumulación

Los exponentes salen 0,82 y 0,89 en los dos puntos válidos, frente al 1,00
que corresponde a ruido blanco. La desviación es de estadística: 500
ciclos simulados dan una dispersión del orden del 3 % en σ, pero el
exponente necesita más. Para las medidas definitivas hay que alargar el
transitorio, que en esta campaña costaba unos tres minutos por punto.
