# Prueba de reinicios del RNG del ESP32 (SP 800-90B, §3.1.4)

Fecha: 2026-10-12. Chip ESP32-D0WD-V3 rev. 3.1, MAC a0:dd:6c:0e:fb:4c.
ESP-IDF 5.3.2. Datos en `results/esp32_reinicios/mac_a0dd6c0efb4c/`,
resumen en `results/esp32_reinicios/resumen_mac_a0dd6c0efb4c.md`.
Todo lo de aquí es **medido** salvo donde se dice.

## 1. La pregunta

Espressif dice que su RNG da números aleatorios de verdad solo con la
radio encendida o con su fuente interna (el SAR ADC, que el bootloader
enciende mientras arranca con `bootloader_random_enable()`), y que si no,
"the output of the RNG should be considered as pseudo-random only"
[espressif_idf_random]. Las pruebas estadísticas sobre un flujo continuo
no pueden comprobarlo: un buen generador pseudoaleatorio las pasa igual
(`docs/esp32_linea_base_90b.md`: la condición D, todo apagado, sale igual
que las demás). La prueba de reinicios de la norma sí puede: si el
generador no tiene ruido propio, tras un reinicio en frío tiene que
repetirse.

## 2. Montaje

- `firmware/reinicios`: nada más entrar en `app_main`, sin Wi-Fi ni ADC
  (condición D), lee 1024 B con `esp_fill_random` y los saca por UART con
  su CRC32. La lectura es lo primero que hace el programa, unos 3,2 ms
  después de que arranque (unos 180 ms después del reset).
- Dos variantes con el **mismo programa** y distinto bootloader:
  - **normal**: el bootloader de serie. Según su propio log enciende la
    fuente de ruido a los ≈ 53 ms y la apaga a los ≈ 179 ms (SAR ADC en
    modo prueba sobre la referencia de 1,1 V, volcado al RNG por I2S;
    `bootloader_random_esp32.c`).
  - **sin_ruido** (`firmware/reinicios_sin_ruido`): el mismo bootloader
    con la llamada a `bootloader_random_enable()` desviada a una función
    vacía (`-Wl,--wrap` en el enlazado; nada de ESP-IDF se modifica).
    Comprobado en el desensamblado: `bootloader_enable_random` llama a
    `__wrap_bootloader_random_enable`, y la función original ya no está en
    el binario. El bootloader lo avisa en cada arranque, y las 1000 filas
    lo registran.
- Reinicio por la patilla EN (RTS del adaptador USB): la ROM informa
  `POWERON_RESET` en los 2000 arranques, es decir, reinicio en frío.
- 1000 reinicios por variante, 0,40 s cada uno
  (`analysis/reinicios_esp32.py`). Variante normal: 4 bloques llegaron
  corruptos por la UART y se repitieron (son errores de transmisión: el
  CRC no cuadra; no dependen del contenido). En un arranque (nº 551) se
  perdieron bytes del log del bootloader, entre ellos la línea de la fuente
  de ruido; el binario es el mismo en los 1000.
- Matrices de la norma (`analysis/reinicios_90b.py`): 1000 reinicios ×
  1000 muestras, en modo bit (los primeros 1000 bits de cada arranque) y
  en modo byte (los primeros 1000 bytes). H_I = 0,8382 bit/bit, la
  estimación no-IID más baja de las tres capturas D de este chip (×8 en
  modo byte). Con una H_I menor la comprobación de la norma es menos
  exigente, no más.

Al final se volvió a grabar la variante normal: el chip queda con el
bootloader de serie.

## 3. Resultados

| | normal | sin_ruido |
|---|---|---|
| Prueba de la norma, modo bit: comprobación de cordura (límite ≈ 628; la herramienta lo calcula por simulación y varía ±2 entre ejecuciones) | pasa (554) | pasa (580) |
| Prueba de la norma, modo bit: H_r / H_c | 0,898 / 0,854 | **0,024** / 0,813 |
| Prueba de la norma, modo bit: veredicto | **pasa**, entropía validada 0,838 | **falla** (H_r < H_I/2) |
| Prueba de la norma, modo byte: H_r / H_c | 7,31 / 6,64 | **0,020** / 7,13 |
| Prueba de la norma, modo byte: veredicto | **pasa**, 6,64 bit/byte | **falla** |
| Secuencias distintas en 1000 arranques | 1000 | **759** (una sale 5 veces) |
| Distancia de Hamming entre arranques (esperado 4096 ± 45,3; mínimo ≈ 3887) | 4096,0 ± 45,3; mínimo 3891 | 4093,7 ± 109,1; **mínimo 0** |
| Arranques cuyo principio aparece desplazado dentro de otro | 0 | **5424 relaciones, todas con el solape idéntico palabra a palabra** |
| Grupos de arranques alineables | 1000 (ninguno se alinea) | 87 (el mayor, 21 arranques) |
| Primer byte de cada arranque frente a uniforme (χ²) | p = 0,59 | p = 6,7·10⁻⁶ |
| Min-entropía por arranque (cota inferior al 99 %) | ≥ 8,1 bits: es el techo con 1000 arranques, no una medida | **6,5 bits** |
| Estados equiprobables que darían esas repeticiones | sin repeticiones | 1725, ≈ 10,8 bits |

Las dos estimaciones de la última fila de sin_ruido miden cosas
distintas: 6,5 bits es la cota de la norma (sale de la secuencia más
repetida, sin suponer nada); 10,8 bits supone que todos los estados son
igual de probables. La entropía de un arranque sin ruido está entre las
dos. **De 8192 bits leídos, solo entre 6,5 y 11 son impredecibles.**

En la variante normal, que no haya ni una repetición en 1000 arranques
dice, con un 95 % de confianza, que el arranque elige entre más de unos
167 000 estados (≈ 17 bits; sale de 1000·999 / (2·ln 20)). Con 1000 arranques no se puede decir más.

## 4. Lectura

1. **Con el bootloader de serie, el ESP32 pasa la prueba de reinicios**,
   en modo bit y en modo byte: arranques distintos entre sí exactamente
   como lo serían datos al azar. No hemos encontrado publicada esta prueba
   para el ESP32 (`docs/estado_del_arte_trng.md`, §6, punto 3).
2. **Sin el ruido del arranque, la falla de forma rotunda**, y los datos
   dicen por qué: cada arranque es un trozo de **una misma secuencia
   fija**, leída desde un punto un poco distinto. Los 5424 solapes entre
   arranques coinciden palabra por palabra, sin una sola diferencia. Lo
   único que cambia es en qué momento empieza a leer el programa, que
   varía unos miles de ciclos de un arranque a otro (el contador de ciclos
   en la lectura va de 33 365 566 a 33 370 508). Con la radio y el ADC
   apagados, **el generador no tiene ruido propio**. Esto confirma con
   datos lo que dice Espressif: sin esas fuentes, la salida es
   pseudoaleatoria.
3. **Consecuencia para la línea base.** En condición D, la salida del
   ESP32 es la de un generador determinista sembrado durante el arranque.
   Los estimadores de la norma sobre esas capturas dan 0,85 bit/bit, igual
   que con la radio encendida, porque no pueden ver la diferencia. La
   entropía física de una captura D de 10⁶ bits es como mucho la que metió
   el arranque, que esas pruebas no miden. Es el caso práctico de lo que la
   memoria llama caja negra: los números dicen "nada raro" y el generador
   no tiene ruido.
4. **Consecuencia práctica.** Un programa que saque una clave nada más
   arrancar, con la radio apagada, depende por completo del ruido que mete
   el bootloader de serie. Con un bootloader que no lo haga, esa clave
   tendría entre 6,5 y 11 bits: se adivina en unos miles de intentos. Encaja
   con el problema de arranque en frío que describen Blanco-Romero et al.
   [blancoromero_2026_entropy].

## 5. Con la radio encendida (12-10-2026, mismo chip)

### 5.1 Montaje

- `firmware/reinicios_radio`: dos lecturas de 1024 B por arranque.
  "antes": lo primero de `app_main`, radio apagada, igual que arriba.
  "después": tras arrancar el Wi-Fi como `firmware/esp32_rng` en sus condiciones A y
  B (NVS, `esp_netif`, bucle de eventos, `esp_wifi_init`, modo estación,
  `esp_wifi_start`, sin asociarse a ninguna red) y esperar 200 ms con
  `vTaskDelay`. Por esa espera, la lectura cae en un tick de FreeRTOS
  (10 ms): 797 de los 1000 arranques leen a los 350 ms y el resto entre
  360 y 410 ms, según lo que tarde en arrancar el Wi-Fi.
- Tres variantes más (1000 reinicios cada una, ningún bloque rechazado):
  - **radio_sin_ruido**: bootloader sin ruido + Wi-Fi. Es la que dice si la
    radio mete ruido por sí sola.
  - **espera_sin_ruido**: el control. Bootloader sin ruido y la misma espera
    con `vTaskDelay`, pero sin tocar el Wi-Fi (el binario ni siquiera
    enlaza `esp_wifi_start`). La lectura cae en el mismo tick. Separa el
    efecto de la radio del de la simple variación de tiempos.
  - **radio**: bootloader de serie + Wi-Fi, para completar el cuadro.
- Los tres bootloaders se comprobaron en el desensamblado igual que antes.
  No son idénticos byte a byte a los de §2 porque llevan grabada la fecha
  de compilación.
- H_I de las variantes con Wi-Fi: 0,8586 bit/bit, la estimación no-IID
  más baja de las capturas de este chip con Wi-Fi (condición B), como pide
  la norma (mismo generador, mismas condiciones). El control usa la de D.

### 5.2 Resultados (lectura "después")

| Variante | Prueba de la norma, bit: H_r / H_c | Veredicto (bit y byte) | Distintas en 1000 | Trozos compartidos (solapes idénticos) | Min-entropía por arranque |
|---|---|---|---|---|---|
| radio_sin_ruido | 0,831 / 0,845 | **pasa** (0,831 bit/bit; 6,64 bit/byte) | 1000 | 0 | ≥ 8,1 bits (techo) |
| espera_sin_ruido (control) | **0,024** / 0,808 | **falla** | 760 | 5632 | 6,5 bits |
| radio | 0,844 / 0,807 | **pasa** (0,807 bit/bit; 6,87 bit/byte) | 1000 | 0 | ≥ 8,1 bits (techo) |

Y dos comprobaciones más:

| | Arranques del mismo tick | Variación del instante de lectura | Distintas | Trozos compartidos |
|---|---|---|---|---|
| sin_ruido (§3), nada más arrancar | 1000 | 4942 ciclos | 759 | 5424 |
| espera_sin_ruido, a los 352 ms | 1000 | 3824 ciclos | 760 | 5632 |
| radio_sin_ruido, a los 352 ms | 797 | 5260 ciclos | **797** | **0** |

- En radio_sin_ruido, **289 parejas de arranques tenían la lectura "antes"
  idéntica** (el generador estaba en el mismo estado antes de encender la
  radio) **y las 289 dieron lecturas "después" distintas**. En el control,
  de 303 parejas con la misma lectura "antes", 275 repiten también la de
  "después"; las otras 28 caen en otro de los mismos ≈ 1700 estados por
  una pequeña diferencia de tiempos durante la espera (el número de
  secuencias distintas no crece: 765 antes, 760 después).
- La lectura "antes" de las variantes nuevas repite lo de §3: con el
  bootloader sin ruido, 774 y 765 secuencias distintas en 1000 (≈ 1800
  estados); con el de serie (variante radio), 1000 distintas.

### 5.3 Lectura

1. **La radio mete ruido en el generador por sí sola.** Con el
   bootloader sin ruido, encender el Wi-Fi basta para que cada arranque
   sea distinto: la prueba de la norma pasa, no hay ningún trozo
   compartido, y arranques que partían del mismo estado acaban en
   lecturas distintas.
2. **No es la variación de tiempos.** El control lee en el mismo tick y
   con una variación del instante de lectura del mismo orden (3824 frente
   a 5260 ciclos), y repite como nada más arrancar: 760 distintas, 5632
   solapes idénticos, ≈ 1734 estados. Con tan pocos estados, 797 arranques
   del mismo tick darían del orden de 180 repeticiones por puro azar de
   tiempos; con la radio salen 0.
3. **Sin radio, el generador no recibe ruido de ninguna parte en todo ese
   tiempo.** En el control, 350 ms después de arrancar, la salida sigue
   siendo la misma secuencia fija.
4. Esto confirma la otra mitad de lo que dice Espressif: con la radio
   encendida, el generador recibe ruido físico. Lo que la prueba no dice
   es **cuánto por bit**: la cifra validada (0,83 bit/bit) es la de los
   estimadores de la norma, con su sesgo de siempre, no una medida del
   ruido de la radio.

## 6. Tercer chip y comparación entre chips (20-10-2026)

### 6.1 Montaje

Chip ESP32-D0WD-V3 rev. 3.1, MAC f8:b3:b7:2a:09:28 (una placa del autor de
otro uso; su flash se copió entera antes y se restauró al terminar). Los
mismos binarios de §2, grabados con esptool desde los mismos directorios de
build sin recompilar: `reinicios_sin_ruido.bin` SHA-256 c36baa13…,
bootloader e24cbe35… (los del 12-10, fecha de compilación del bootloader
"Oct 12 2026 10:59:11" en los dos logs). El de la variante normal es el
mismo fuente, pero recompilado el 12-10 a las 13:10 al dejar el primer chip
con el bootloader de serie (`reinicios.bin` SHA-256 4ca904ad…): no es
byte a byte el que se usó en aquel chip. Datos en
`results/esp32_reinicios/mac_f8b3b72a0928/`, resumen en
`resumen_mac_f8b3b72a0928.md`.

El enlace serie de esta placa estropea a veces lo que llega al PC: se ve en
los logs un trozo de 32 caracteres repetido decenas de veces. Es del lado
del PC (USB o controlador), no del chip, y el CRC32 de cada bloque lo
detecta: normal, 0 rechazos en 1000; sin_ruido, 5 rechazos, repetidos con
un reinicio nuevo cada uno. Los rechazos dependen de la carga del PC: en
fuente_radio_1 hubo 23 en los primeros 79 reinicios, mientras el PC
compilaba, y 7 en los 145 siguientes, con el PC en reposo. Desde entonces
no se lanza nada pesado durante una captura, y el script reintenta hasta
diez veces (antes, tres). Nada indica que el rechazo dependa de lo que
lleva el bloque (sigue a la carga del PC y es raro en reposo en todas las
variantes, con o sin ruido), pero no se ha comprobado; si dependiera, en
las variantes sin ruido algunos estados saldrían algo menos de lo que les
toca, y las cuentas de estados serían un poco más altas, no más bajas.

### 6.2 Resultados

| | normal | sin_ruido | (primer chip, §3: normal / sin_ruido) |
|---|---|---|---|
| Prueba de la norma, bit: H_r / H_c | 0,892 / 0,848 | **0,016** / 0,844 | 0,898 / 0,854; **0,024** / 0,813 |
| Veredicto (bit y byte) | **pasa** (0,833 bit/bit; 6,64 bit/byte) | **falla** (H_r < H_I/2) | pasa; falla |
| Secuencias distintas en 1000 | 1000 | **746** (una sale 5 veces) | 1000; 759 |
| Distancia de Hamming, media ± desv.; mínimo (esperado ≈ 3887) | 4096,0 ± 45,3; 3883 | 4093,6 ± 112,4; **0** | 4096,0 ± 45,3; 3891 / 0 |
| Solapes desplazados, todos idénticos | 0 | **5444** | 0; 5424 |
| Grupos alineables / el mayor | 1000 / 1 | **87** / 23 | 1000 / 1; 87 / 21 |
| Primer byte frente a uniforme (χ²) | p = 0,23 | p = 2,2·10⁻¹¹ | 0,59; 6,7·10⁻⁶ |
| Min-entropía por arranque (cota al 99 %) | ≥ 8,1 (techo) | **6,5 bits** | ≥ 8,1; 6,5 |
| Estados equiprobables equivalentes | — | 1618 (≈ 10,7 bits) | —; 1725 |

H_I = 0,8332 bit/bit, la no-IID más baja de las capturas D de este chip
(0928_condD_rep1). El tercer chip repite el primero cifra a cifra.

### 6.3 Los dos chips sacan la misma secuencia

Sin el ruido del arranque, los dos chips no solo se repiten cada uno: se
repiten **entre sí** (`analysis/reinicios_entre_chips.py`,
`results/esp32_reinicios/entre_chips.md`):

- 256 contenidos de 1024 B distintos salen en los dos chips; cubren 352 de
  los 1000 bloques del primero y 347 de los 1000 del tercero.
- 988 de los 1000 bloques del tercer chip empiezan, con un desfase de un
  número entero de palabras de 32 bits, dentro de algún bloque del primero:
  8369 relaciones (7891 con desfase > 0), y en las 8369 el solape entero
  coincide palabra a palabra; en el otro sentido, 760 bloques y 3704
  relaciones, también sin una diferencia.
- Juntando los 2000 bloques con la lectura "antes" de espera_sin_ruido
  (primer chip, otro binario), los 3000 caen en los mismos **87 grupos**, y
  cada grupo tiene bloques de las tres capturas. La lectura "antes" de
  fuente_control (tercer chip, otro binario más, §7) cae en 85 de ellos.
- Con el bootloader de serie no se alinea ningún bloque con ningún otro, ni
  dentro de un chip ni entre los dos (2000 grupos de un bloque).

Comprobado aparte por tres revisiones independientes (procedencia de los
datos, reimplementación propia y bibliografía): la MAC sale del chip por
dos vías (esptool y el propio firmware), los dos ficheros se reconstruyen
íntegros desde sus logs serie, y las cifras se reproducen con código
distinto. **Sin el ruido del arranque, la salida de los dos chips probados
es una función determinista de un estado de partida pequeño, y esa función
es la misma en los dos.** Con el mismo firmware, lo que saca un chip lo
puede precalcular cualquiera que tenga otro. No se ha encontrado publicado
en las fuentes consultadas: Espressif dice que sin fuente la salida es
pseudoaleatoria, pero no que sea igual en todos los chips; Blanco-Romero et
al. [blancoromero_2026_entropy] reinician un solo chip y con el bootloader
de serie. Con dos chips de la misma revisión no se puede decir "todos los
ESP32".

**Qué son los 87 grupos.** Una palabra de `esp_fill_random` tarda 174
ciclos de CPU (160 MHz), 87 de APB (80 MHz). Si el generador da un paso por
ciclo de APB y las lecturas no lo mueven, dos arranques que empiezan a leer
en instantes que difieren en un número entero de palabras sacan la misma
secuencia desplazada, y los que difieren en otro número de ciclos sacan otra
distinta: 87 desfases posibles, 87 grupos. Lo apoyan dos datos: en
espera_sin_ruido el hueco entre las dos lecturas es exactamente de
55 861 272 ciclos en los 1000 arranques y la segunda nunca continúa a la
primera (si las lecturas movieran el estado, 901 deberían hacerlo); y en
fuente_control (§7), en los 7 pares de arranques alineables a la vez en las
dos lecturas, el desfase en palabras es la diferencia de tiempo dividida
por 174,00 ciclos exactos. §8 lo pone a prueba directamente. Si se
confirma, 87 es una propiedad de este firmware y de esta frecuencia, no del
chip. Berlekamp-Massey sobre cada posición de bit de 20 bloques sin ruido
(secuencias de 256 bits, una por palabra) da una complejidad lineal media
de 128,2 (124-132), la misma que con datos de `numpy` al azar (128,3,
124-134): lo que sale por `esp_random` no deja ver un LFSR pequeño.

## 7. Qué fuente mete ruido (tercer chip, 20/21-10-2026)

`firmware/reinicios_fuentes`: bootloader sin ruido; lectura "antes" lo
primero; una fuente; lectura "despues" en un instante fijo, a los 800 ms,
por espera activa sobre `esp_timer`. Lo que decide es si las lecturas
"despues" siguen siendo trozos de la secuencia fija (solapes desplazados,
todos idénticos) y se repiten, o no. Que dos arranques con el mismo "antes"
repitan el "despues" **no** sirve aquí: la espera de 800 ms acumula unos
3000 ciclos de variación y el generador avanza con el reloj (§8), así que
ni el control repite (0 de 20). Resumen en `resumen_mac_f8b3b72a0928.md`.

| Variante (entre las dos lecturas) | Arranques | "despues" distintas | Solapes | ¿Ruido? |
|---|---|---|---|---|
| control (nada) | 300 | 284 | 475 | no |
| wifi_init (NVS, netif, eventos, `esp_wifi_init`, modo; sin `esp_wifi_start`) | 300 | 284 | 461 | no |
| radio_0 / 1 / 10 / 100 (`esp_wifi_start`, N ms, `esp_wifi_stop`) | 300 cada una | 300 | 0 | sí |
| adc_0 (unidad del ADC creada y borrada, 0 lecturas) | 300 | 274 | 0 | no (repite) |
| adc_1 (1 ms de `adc_oneshot`, 17 lecturas) | 300 | 300 | 0 | sí |
| adc_200 (200 ms, 4392-4399 lecturas) | 1000 | 1000 | 0 | sí; prueba de la norma: pasa (H_r 0,864 / H_c 0,877) |
| bootrand_200 (`bootloader_random_enable()` desde el programa, 200 ms) | 1000 | 1000 | 0 | sí; pasa (0,840 / 0,842) |

- **Radio.** Con `sta_disconnected_pm = false` (si no, la estación sin
  conectar duerme la radio antes de que vuelva `esp_wifi_start` y la
  espera no añadiría tiempo de radio). La PHY se enciende a los 49,0-49,1
  ms y `esp_wifi_start` no vuelve hasta los 131-241 ms (calibración): hasta
  `esp_wifi_stop` la radio está encendida 84,8-194,2 ms en radio_0 y
  184,1-261,9 ms en radio_100; `esp_wifi_stop` no la volvió a encender en
  ningún arranque. La exposición más corta posible ya basta, así que el
  barrido no puede encontrar un umbral por debajo de la calibración.
- **ADC.** Las conversiones normales de `adc_oneshot` (ADC1, canal 0,
  GPIO36) **sí meten ruido**, con solo 17. Lo contrario de lo que se
  esperaba leyendo las fuentes y la documentación de ESP-IDF 5.3.2 (no hay
  camino documentado de esas conversiones al RNG; la fuente SAR documentada
  es el modo prueba de `bootloader_random_enable` hacia I2S); encaja con el
  manual técnico, que da el SAR ADC como entrada de ruido. Crear y borrar
  la unidad sin convertir (que cambia el modo de alimentación del SAR) no
  mete nada: hay repeticiones exactas (274 distintas de 300), aunque en esa
  compilación sin solapes desplazados (ver la nota de abajo).
- **bootrand.** La fuente documentada funciona encendida desde el programa
  (el `--wrap` solo afecta al bootloader; el programa enlaza la función real).
- **Nota.** En algunas compilaciones (radio_0, radio_1, radio_10 y adc_0;
  en el primer chip, radio_sin_ruido) las lecturas sin ruido se repiten
  exactas pero nunca desplazadas. Pasaría en el modelo de §8 si en esas
  compilaciones una palabra no durase un número entero de ciclos de APB;
  no se ha medido. Por eso el indicador robusto de "sin ruido" son las
  repeticiones exactas de 1024 B, imposibles con ruido.
- Rechazos por el enlace (CRC): 1-36 por variante en la primera pasada
  (con el PC cargado), 0 en todas tras reiniciar el PC.

## 8. El generador avanza con el reloj (prueba del paso)

`firmware/reinicios_paso`, `analysis/reinicios_paso.py`,
`mac_f8b3b72a0928/paso/resumen.md`. Bootloader sin ruido; con las
interrupciones apagadas: "antes" (1024 B), un número fijo de NOP en un
bucle `loop` de Xtensa desde IRAM (comprobado en el desensamblado: `loop` y
un `nop.n`), y "despues". La espera se elige en cada arranque con dos bits
del contador de ciclos al empezar (no depende de lo que salga en "antes"):
N0 = 1 740 000 NOP, N0 + 2, N0 + 174, N0 + 17 400. Los ciclos medidos son
exactamente constantes en cada variante (retardo 1 742 547 / 1 742 549 /
1 742 721 / 1 759 947; "antes" 46 482; "despues" 44 565, 174,1 por
palabra). 800 arranques, 0 rechazos.

| Parejas con el mismo "antes" | Parejas | Resultado | Predicción (paso por ciclo de APB) |
|---|---|---|---|
| misma espera | 52 | "despues" idéntico en las 52 | idéntico |
| + 174 ciclos (una palabra) | 21 | desplazado +1 palabra en las 21 | +1 |
| + 17 400 ciclos | 41 | +100 palabras en las 41 | +100 |
| + 17 226 ciclos | 23 | +99 en las 23 | +99 |
| la variante 1 frente a las otras (+2, +172 o +17 398 ciclos; no es múltiplo de 174) | 67 | sin ninguna alineación en las 67 (25 de ellas, +2 ciclos exactos) | sin alinear |

204 de 204 parejas como predice el modelo. **Sin ruido, la salida solo
depende del instante en que empieza la lectura, con resolución de un ciclo
de APB**, y en 11 ms con las interrupciones apagadas no entra nada más. Con
espera_sin_ruido (el estado no avanza con las lecturas: la segunda lectura
nunca continúa a la primera con el mismo hueco exacto de 55 861 272 ciclos)
y los dos chips de §6.3: el generador da un paso por ciclo de APB desde un
estado de reset fijo, igual en los dos chips. Los 87 grupos son las 87
fases de un ciclo de APB en una palabra de 174 ciclos de CPU: una propiedad
de este firmware y de este reloj, no del chip.

## 9. Límites

- Dos chips (a0:dd:6c:0e:fb:4c y f8:b3:b7:2a:09:28), los dos ESP32-D0WD-V3
  rev. 3.1; el primero se reinició con todas las variantes de §2 y §5, el
  tercero con las de §2 y las de §7-8.
- Condiciones D, B y, en el tercer chip, cada fuente por separado (§7). No
  se ha hecho con Bluetooth ni con el Wi-Fi asociado a una red, ni se ha
  medido cuánta entropía mete cada fuente (solo si mete).
- La variante sin_ruido es un montaje de laboratorio: el bootloader de
  serie siempre enciende la fuente. Lo que mide es el generador sin
  ninguna de sus fuentes, no un fallo de ESP-IDF.
- Los 87 grupos son fases del reloj (§8), medido en un solo binario y a
  160 MHz; no se ha probado con otra frecuencia de CPU.
- Cuánta entropía mete el arranque normal queda acotada solo por abajo
  (> 17 bits); el tamaño del estado interno del generador no está
  documentado.

## 10. Reproducir

Primer chip (12-10-2026):

```
. C:\esp\esp-idf\export.ps1
cd firmware\reinicios; idf.py -p COM7 flash
python analysis/reinicios_esp32.py --variante normal --n 1000
cd ..\reinicios_sin_ruido; idf.py -p COM7 flash
python analysis/reinicios_esp32.py --variante sin_ruido --n 1000
cd ..\reinicios_radio_sin_ruido; idf.py -p COM7 flash
python analysis/reinicios_esp32.py --variante radio_sin_ruido --n 1000
idf.py -B build_espera -DSIN_RADIO=1 -p COM7 flash
python analysis/reinicios_esp32.py --variante espera_sin_ruido --n 1000
cd ..\reinicios_radio; idf.py -p COM7 flash
python analysis/reinicios_esp32.py --variante radio --n 1000
python analysis/reinicios_90b.py --mac a0dd6c0efb4c
```

Tercer chip (20/21-10-2026), grabando cada build con esptool a 115200
baudios (a más velocidad el enlace de esa placa falla):

```
cd firmware\reinicios_fuentes
idf.py -B build_<variante> -DFUENTE=<0..4> -DFUENTE_MS=<ms> -DVARIANTE=<variante> build
cd build_<variante>; python -m esptool --chip esp32 -p COM7 -b 115200 write_flash "@flash_args"
python analysis/reinicios_esp32.py --variante <variante> --n 300
(igual con firmware\reinicios_paso y --variante paso --n 800)
python analysis/reinicios_90b.py --mac f8b3b72a0928
python analysis/reinicios_paso.py --mac f8b3b72a0928
python analysis/reinicios_entre_chips.py
```
