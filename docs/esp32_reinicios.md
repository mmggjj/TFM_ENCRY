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

## 6. Límites

- Un solo chip (a0:dd:6c:0e:fb:4c); el otro no estaba conectado.
- Condiciones D (todo apagado) y B (Wi-Fi sin asociarse). No se ha hecho
  con el ADC (condición C), con Bluetooth, ni con el Wi-Fi asociado a una
  red.
- La variante sin_ruido es un montaje de laboratorio: el bootloader de
  serie siempre enciende la fuente. Lo que mide es el generador sin
  ninguna de sus fuentes, no un fallo de ESP-IDF.
- Los 87 grupos que no se alinean entre sí pueden ser trozos lejanos de la
  misma secuencia o fases distintas entre la lectura y el reloj del
  generador. No se ha investigado, y no cambia la conclusión.
- Cuánta entropía mete el arranque normal queda acotada solo por abajo
  (> 17 bits); el tamaño del estado interno del generador no está
  documentado.

## 7. Reproducir

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
