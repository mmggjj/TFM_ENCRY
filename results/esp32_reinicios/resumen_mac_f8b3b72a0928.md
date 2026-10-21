# Prueba de reinicios del RNG del ESP32, chip f8b3b72a0928

Generado por analysis/reinicios_90b.py. H_I: estimación no-IID más baja de las capturas de la campaña de este chip en la misma condición (D sin radio, B con Wi-Fi).

## Variante normal

1000 reinicios de 1024 B, lectura nada más arrancar, radio apagada; motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 1000 de 1000; instante de la lectura 3196-3212 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 1000 de 1000 | 1000 |
| primeros 8 bytes distintos | 1000 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4096.0 ± 45.3 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3883 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 3.79, p corregida = 1 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.231 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 1000 / 1 |
| secuencias distintas; la más repetida sale | 1000; 1 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 8.1 bits |
| estados equiprobables que darían esas repeticiones | sin repeticiones: no se puede estimar |

Prueba oficial (ea_restart, no-IID), salida íntegra en `normal/ea_restart_b1.log` y `ea_restart_b8.log`:

- bit: H_I: 0.833175 / Restart Sanity Check Passed... / H_r: 0.891756 / H_c: 0.848461 / H_I: 0.833175 / Validation Test Passed... / min(H_r, H_c, H_I): 0.833175
- byte: H_I: 6.665401 / Restart Sanity Check Passed... / H_r: 6.638405 / H_c: 7.522373 / H_I: 6.665401 / Validation Test Passed... / min(H_r, H_c, H_I): 6.638405

## Variante sin_ruido

1000 reinicios de 1024 B, lectura nada más arrancar, radio apagada; motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 1000; instante de la lectura 3197-3209 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 746 de 1000 | 1000 |
| primeros 8 bytes distintos | 746 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4093.6 ± 112.4 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 4.81, p corregida = 0.0141 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 2.24e-11 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 5444 relaciones |
| de ellas, con el solape entero idéntico | 5444 |
| grupos de arranques alineables / el mayor | 87 / 23 |
| secuencias distintas; la más repetida sale | 746; 5 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.5 bits |
| estados equiprobables que darían esas repeticiones | 1618 (≈ 10.7 bits) |

Prueba oficial (ea_restart, no-IID), salida íntegra en `sin_ruido/ea_restart_b1.log` y `ea_restart_b8.log`:

- bit: H_I: 0.833175 / Restart Sanity Check Passed... / H_r: 0.016016 / H_c: 0.843873 / H_I: 0.833175 / *** min(H_r, H_c) < H_I/2, Validation Testing Failed ***
- byte: H_I: 6.665401 / Restart Sanity Check Passed... / H_r: 0.016016 / H_c: 6.938561 / H_I: 6.665401 / *** min(H_r, H_c) < H_I/2, Validation Testing Failed ***

## Variante radio_sin_ruido

Sin capturar.

## Variante espera_sin_ruido

Sin capturar.

## Variante radio

Sin capturar.

## Variante fuente_control

300 reinicios de 1024 B, lectura a los 800 ms, sin ninguna fuente (control); motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 300; instante de la lectura 800004-800005 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 284 de 300 | 300 |
| primeros 8 bytes distintos | 284 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4094.4 ± 89.5 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.16, p corregida = 0.314 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.118 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 475 relaciones |
| de ellas, con el solape entero idéntico | 475 |
| grupos de arranques alineables / el mayor | 87 / 9 |
| secuencias distintas; la más repetida sale | 284; 2 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.7 bits |
| estados equiprobables que darían esas repeticiones | 2703 (≈ 11.4 bits) |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 281 de 300 | 300 |
| primeros 8 bytes distintos | 281 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4094.1 ± 97.5 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.04, p corregida = 0.518 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.0926 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 474 relaciones |
| de ellas, con el solape entero idéntico | 474 |
| grupos de arranques alineables / el mayor | 87 / 9 |
| secuencias distintas; la más repetida sale | 281; 3 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.3 bits |
| estados equiprobables que darían esas repeticiones | 2261 (≈ 11.1 bits) |

Fuente encendida de -1 a -1 µs y apagada de -1 a -1 µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: 0; contador de ciclos en la lectura "despues": 160876839-160880319 (variación 3480 ciclos).

Pares de arranques con la lectura "antes" idéntica: 20; de ellos con la lectura "despues" también idéntica: 0.

## Variante fuente_wifi_init

300 reinicios de 1024 B, lectura a los 800 ms, tras iniciar el Wi-Fi sin encender la radio (sin esp_wifi_start); motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 300; instante de la lectura 800004-800005 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 284 de 300 | 300 |
| primeros 8 bytes distintos | 284 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4095.1 ± 91.6 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 3.93, p corregida = 0.843 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.118 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 461 relaciones |
| de ellas, con el solape entero idéntico | 461 |
| grupos de arranques alineables / el mayor | 93 / 8 |
| secuencias distintas; la más repetida sale | 284; 3 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.3 bits |
| estados equiprobables que darían esas repeticiones | 2703 (≈ 11.4 bits) |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 289 de 300 | 300 |
| primeros 8 bytes distintos | 289 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4094.4 ± 78.7 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.16, p corregida = 0.314 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.118 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 480 relaciones |
| de ellas, con el solape entero idéntico | 480 |
| grupos de arranques alineables / el mayor | 86 / 8 |
| secuencias distintas; la más repetida sale | 289; 2 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.7 bits |
| estados equiprobables que darían esas repeticiones | 3978 (≈ 12.0 bits) |

Fuente encendida de 48559 a 48594 µs y apagada de 48559 a 48594 µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: 0; contador de ciclos en la lectura "despues": 191854187-191857093 (variación 2906 ciclos).

Pares de arranques con la lectura "antes" idéntica: 11; de ellos con la lectura "despues" también idéntica: 0.

## Variante fuente_radio_0

300 reinicios de 1024 B, lectura a los 800 ms, tras 0 ms con la radio encendida (desde que vuelve esp_wifi_start hasta esp_wifi_stop); motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 300; instante de la lectura 800000-800001 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 300 de 300 | 300 |
| primeros 8 bytes distintos | 300 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4096.0 ± 45.1 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3916 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.73, p corregida = 0.0209 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.271 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 300 / 1 |
| secuencias distintas; la más repetida sale | 300; 1 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.4 bits |
| estados equiprobables que darían esas repeticiones | sin repeticiones: no se puede estimar |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 282 de 300 | 300 |
| primeros 8 bytes distintos | 282 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4093.8 ± 95.7 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.16, p corregida = 0.314 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.166 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 300 / 1 |
| secuencias distintas; la más repetida sale | 282; 3 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.3 bits |
| estados equiprobables que darían esas repeticiones | 2392 (≈ 11.2 bits) |

Fuente encendida de 131493 a 240925 µs y apagada de 133802 a 243252 µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: 0; contador de ciclos en la lectura "despues": 191868728-191872158 (variación 3430 ciclos).

Radio encendida según la PHY a los 49036-49112 µs; tiempo con la radio encendida hasta que vuelve esp_wifi_stop: 84.8-194.2 ms; arranques en que esp_wifi_stop la volvió a encender: 0 de 300.

Pares de arranques con la lectura "antes" idéntica: 19; de ellos con la lectura "despues" también idéntica: 0.

## Variante fuente_radio_1

300 reinicios de 1024 B, lectura a los 800 ms, tras 1 ms con la radio encendida (desde que vuelve esp_wifi_start hasta esp_wifi_stop); motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 300; instante de la lectura 800000-800001 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 300 de 300 | 300 |
| primeros 8 bytes distintos | 300 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4096.3 ± 45.1 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3908 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 3.81, p corregida = 1 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.405 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 300 / 1 |
| secuencias distintas; la más repetida sale | 300; 1 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.4 bits |
| estados equiprobables que darían esas repeticiones | sin repeticiones: no se puede estimar |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 286 de 300 | 300 |
| primeros 8 bytes distintos | 286 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4094.0 ± 87.7 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.39, p corregida = 0.111 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.184 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 300 / 1 |
| secuencias distintas; la más repetida sale | 286; 3 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.3 bits |
| estados equiprobables que darían esas repeticiones | 3104 (≈ 11.6 bits) |

Fuente encendida de 131400 a 210957 µs y apagada de 134278 a 213838 µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: 0; contador de ciclos en la lectura "despues": 191868780-191871884 (variación 3104 ciclos).

Radio encendida según la PHY a los 49038-49115 µs; tiempo con la radio encendida hasta que vuelve esp_wifi_stop: 85.2-164.8 ms; arranques en que esp_wifi_stop la volvió a encender: 0 de 300.

Pares de arranques con la lectura "antes" idéntica: 15; de ellos con la lectura "despues" también idéntica: 0.

## Variante fuente_radio_10

300 reinicios de 1024 B, lectura a los 800 ms, tras 10 ms con la radio encendida (desde que vuelve esp_wifi_start hasta esp_wifi_stop); motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 300; instante de la lectura 800000-800001 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 300 de 300 | 300 |
| primeros 8 bytes distintos | 300 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4095.9 ± 45.3 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3906 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.62, p corregida = 0.0369 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.7 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 300 / 1 |
| secuencias distintas; la más repetida sale | 300; 1 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.4 bits |
| estados equiprobables que darían esas repeticiones | sin repeticiones: no se puede estimar |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 284 de 300 | 300 |
| primeros 8 bytes distintos | 284 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4094.3 ± 91.6 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.16, p corregida = 0.314 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.133 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 300 / 1 |
| secuencias distintas; la más repetida sale | 284; 3 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.3 bits |
| estados equiprobables que darían esas repeticiones | 2703 (≈ 11.4 bits) |

Fuente encendida de 131732 a 209048 µs y apagada de 143622 a 220922 µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: 0; contador de ciclos en la lectura "despues": 191868634-191871594 (variación 2960 ciclos).

Radio encendida según la PHY a los 49038-49114 µs; tiempo con la radio encendida hasta que vuelve esp_wifi_stop: 94.5-171.9 ms; arranques en que esp_wifi_stop la volvió a encender: 0 de 300.

Pares de arranques con la lectura "antes" idéntica: 17; de ellos con la lectura "despues" también idéntica: 0.

## Variante fuente_radio_100

300 reinicios de 1024 B, lectura a los 800 ms, tras 100 ms con la radio encendida (desde que vuelve esp_wifi_start hasta esp_wifi_stop); motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 300; instante de la lectura 800000-800001 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 300 de 300 | 300 |
| primeros 8 bytes distintos | 300 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4095.7 ± 45.0 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3890 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.04, p corregida = 0.518 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.184 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 300 / 1 |
| secuencias distintas; la más repetida sale | 300; 1 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.4 bits |
| estados equiprobables que darían esas repeticiones | sin repeticiones: no se puede estimar |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 272 de 300 | 300 |
| primeros 8 bytes distintos | 272 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4092.8 ± 115.3 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.27, p corregida = 0.187 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.225 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 522 relaciones |
| de ellas, con el solape entero idéntico | 522 |
| grupos de arranques alineables / el mayor | 83 / 11 |
| secuencias distintas; la más repetida sale | 272; 3 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.3 bits |
| estados equiprobables que darían esas repeticiones | 1501 (≈ 10.6 bits) |

Fuente encendida de 131242 a 209153 µs y apagada de 233117 a 311004 µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: 0; contador de ciclos en la lectura "despues": 191866979-191870335 (variación 3356 ciclos).

Radio encendida según la PHY a los 49050-49113 µs; tiempo con la radio encendida hasta que vuelve esp_wifi_stop: 184.1-261.9 ms; arranques en que esp_wifi_stop la volvió a encender: 0 de 300.

Pares de arranques con la lectura "antes" idéntica: 30; de ellos con la lectura "despues" también idéntica: 0.

## Variante fuente_adc_200

1000 reinicios de 1024 B, lectura a los 800 ms, tras 200 ms de lecturas normales del ADC (adc_oneshot, ADC1 canal 0); motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 1000; instante de la lectura 800000-800001 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 1000 de 1000 | 1000 |
| primeros 8 bytes distintos | 1000 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4095.9 ± 45.2 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3888 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 3.79, p corregida = 1 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.701 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 1000 / 1 |
| secuencias distintas; la más repetida sale | 1000; 1 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 8.1 bits |
| estados equiprobables que darían esas repeticiones | sin repeticiones: no se puede estimar |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 797 de 1000 | 1000 |
| primeros 8 bytes distintos | 797 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4094.0 ± 99.6 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 5.06, p corregida = 0.00385 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 3.54e-05 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 5441 relaciones |
| de ellas, con el solape entero idéntico | 5441 |
| grupos de arranques alineables / el mayor | 87 / 24 |
| secuencias distintas; la más repetida sale | 797; 5 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.5 bits |
| estados equiprobables que darían esas repeticiones | 2116 (≈ 11.0 bits) |

Fuente encendida de 3904 a 4017 µs y apagada de 203974 a 204124 µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: 0; contador de ciclos en la lectura "despues": 162735747-162740515 (variación 4768 ciclos).

Lecturas correctas del ADC por arranque: 4392-4399; última lectura cruda 0-1520 (12 bits).

Pares de arranques con la lectura "antes" idéntica: 235; de ellos con la lectura "despues" también idéntica: 0.

Prueba oficial (ea_restart, no-IID), salida íntegra en `fuente_adc_200/ea_restart_b1.log` y `ea_restart_b8.log`:

- bit: H_I: 0.833175 / Restart Sanity Check Passed... / H_r: 0.864112 / H_c: 0.876603 / H_I: 0.833175 / Validation Test Passed... / min(H_r, H_c, H_I): 0.833175
- byte: H_I: 6.665401 / Restart Sanity Check Passed... / H_r: 6.638399 / H_c: 7.353758 / H_I: 6.665401 / Validation Test Passed... / min(H_r, H_c, H_I): 6.638399

## Variante fuente_bootrand_200

1000 reinicios de 1024 B, lectura a los 800 ms, tras 200 ms con la fuente del arranque (bootloader_random_enable) encendida desde el programa; motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 1000; instante de la lectura 800000-800001 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 1000 de 1000 | 1000 |
| primeros 8 bytes distintos | 1000 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4095.9 ± 45.3 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3872 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 3.73, p corregida = 1 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.302 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 1000 / 1 |
| secuencias distintas; la más repetida sale | 1000; 1 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 8.1 bits |
| estados equiprobables que darían esas repeticiones | sin repeticiones: no se puede estimar |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 847 de 1000 | 1000 |
| primeros 8 bytes distintos | 847 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4094.5 ± 88.5 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 4.68, p corregida = 0.0263 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.000662 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 5552 relaciones |
| de ellas, con el solape entero idéntico | 5552 |
| grupos de arranques alineables / el mayor | 87 / 20 |
| secuencias distintas; la más repetida sale | 847; 3 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 7.1 bits |
| estados equiprobables que darían esas repeticiones | 2923 (≈ 11.5 bits) |

Fuente encendida de 3546 a 3567 µs y apagada de 203664 a 203685 µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: 0; contador de ciclos en la lectura "despues": 160973274-160977530 (variación 4256 ciclos).

Pares de arranques con la lectura "antes" idéntica: 172; de ellos con la lectura "despues" también idéntica: 0.

Prueba oficial (ea_restart, no-IID), salida íntegra en `fuente_bootrand_200/ea_restart_b1.log` y `ea_restart_b8.log`:

- bit: H_I: 0.833175 / Restart Sanity Check Passed... / H_r: 0.839679 / H_c: 0.841619 / H_I: 0.833175 / Validation Test Passed... / min(H_r, H_c, H_I): 0.833175
- byte: H_I: 6.665401 / Restart Sanity Check Passed... / H_r: 7.353758 / H_c: 7.876484 / H_I: 6.665401 / Validation Test Passed... / min(H_r, H_c, H_I): 6.665401

## Variante fuente_adc_0

300 reinicios de 1024 B, lectura a los 800 ms, tras crear y borrar la unidad del ADC sin ninguna lectura; motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 300; instante de la lectura 800000-800001 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 274 de 300 | 300 |
| primeros 8 bytes distintos | 274 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4093.8 ± 108.4 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.39, p corregida = 0.111 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.0188 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 300 / 1 |
| secuencias distintas; la más repetida sale | 274; 2 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.7 bits |
| estados equiprobables que darían esas repeticiones | 1625 (≈ 10.7 bits) |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 275 de 300 | 300 |
| primeros 8 bytes distintos | 275 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4093.6 ± 113.6 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.50, p corregida = 0.0643 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.105 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 495 relaciones |
| de ellas, con el solape entero idéntico | 495 |
| grupos de arranques alineables / el mayor | 85 / 8 |
| secuencias distintas; la más repetida sale | 275; 4 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.0 bits |
| estados equiprobables que darían esas repeticiones | 1694 (≈ 10.7 bits) |

Fuente encendida de 3919 a 3929 µs y apagada de 3985 a 3994 µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: 0; contador de ciclos en la lectura "despues": 162734638-162737898 (variación 3260 ciclos).

Lecturas correctas del ADC por arranque: 0-0; última lectura cruda -1--1 (12 bits).

Pares de arranques con la lectura "antes" idéntica: 29; de ellos con la lectura "despues" también idéntica: 2.

## Variante fuente_adc_1

300 reinicios de 1024 B, lectura a los 800 ms, tras 1 ms de lecturas normales del ADC (adc_oneshot, ADC1 canal 0); motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 300; instante de la lectura 800000-800001 µs desde el arranque del programa. H_I = 0.8332 bit/bit (0928_condD_rep1).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 300 de 300 | 300 |
| primeros 8 bytes distintos | 300 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4096.0 ± 45.4 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3905 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 3.46, p corregida = 1 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.204 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 300 / 1 |
| secuencias distintas; la más repetida sale | 300; 1 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.4 bits |
| estados equiprobables que darían esas repeticiones | sin repeticiones: no se puede estimar |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 285 de 300 | 300 |
| primeros 8 bytes distintos | 285 de 300 | 300 |
| distancia de Hamming entre arranques, media ± desv. | 4094.1 ± 87.5 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3911 |
| posición más sesgada (unos en 300 arranques) | z = 4.39, p corregida = 0.111 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.92 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 552 relaciones |
| de ellas, con el solape entero idéntico | 552 |
| grupos de arranques alineables / el mayor | 82 / 10 |
| secuencias distintas; la más repetida sale | 285; 2 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 5.7 bits |
| estados equiprobables que darían esas repeticiones | 2890 (≈ 11.5 bits) |

Fuente encendida de 3931 a 3947 µs y apagada de 5001 a 5017 µs (−1: no hay fuente); lecturas que llegaron tarde a los 800 ms: 0; contador de ciclos en la lectura "despues": 162735484-162739370 (variación 3886 ciclos).

Lecturas correctas del ADC por arranque: 17-17; última lectura cruda 0-2544 (12 bits).

Pares de arranques con la lectura "antes" idéntica: 15; de ellos con la lectura "despues" también idéntica: 0.

## Comparación de fuentes (firmware/reinicios_fuentes, lectura "despues" a los 800 ms)

| Variante | Arranques | Distintas "antes" | Distintas "despues" | Trozos compartidos (solapes idénticos) | Pares con "antes" idéntica | de ellos, "despues" idéntica | Min-entropía por arranque (bits) | Variación del instante (ciclos) |
|---|---|---|---|---|---|---|---|---|
| fuente_control | 300 | 281 | 284 | 475 (475) | 20 | 0 | 5.7 | 3480 |
| fuente_wifi_init | 300 | 289 | 284 | 461 (461) | 11 | 0 | 5.3 | 2906 |
| fuente_radio_0 | 300 | 282 | 300 | 0 (0) | 19 | 0 | 6.4 | 3430 |
| fuente_radio_1 | 300 | 286 | 300 | 0 (0) | 15 | 0 | 6.4 | 3104 |
| fuente_radio_10 | 300 | 284 | 300 | 0 (0) | 17 | 0 | 6.4 | 2960 |
| fuente_radio_100 | 300 | 272 | 300 | 0 (0) | 30 | 0 | 6.4 | 3356 |
| fuente_adc_200 | 1000 | 797 | 1000 | 0 (0) | 235 | 0 | 8.1 | 4768 |
| fuente_bootrand_200 | 1000 | 847 | 1000 | 0 (0) | 172 | 0 | 8.1 | 4256 |
| fuente_adc_0 | 300 | 275 | 274 | 0 (0) | 29 | 2 | 5.7 | 3260 |
| fuente_adc_1 | 300 | 285 | 300 | 0 (0) | 15 | 0 | 6.4 | 3886 |

