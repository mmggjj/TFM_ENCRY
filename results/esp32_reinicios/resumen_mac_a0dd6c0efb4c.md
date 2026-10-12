# Prueba de reinicios del RNG del ESP32, chip a0dd6c0efb4c

Generado por analysis/reinicios_90b.py. H_I: estimación no-IID más baja de las capturas de la campaña de este chip en la misma condición (D sin radio, B con Wi-Fi).

## Variante normal

1000 reinicios de 1024 B, lectura nada más arrancar, radio apagada; motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 999 de 1000; instante de la lectura 3192-3204 µs desde el arranque del programa. H_I = 0.8382 bit/bit (fb4c_condD_rep2).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 1000 de 1000 | 1000 |
| primeros 8 bytes distintos | 1000 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4096.0 ± 45.3 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3891 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 3.79, p corregida = 1 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.589 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 1000 / 1 |
| secuencias distintas; la más repetida sale | 1000; 1 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 8.1 bits |
| estados equiprobables que darían esas repeticiones | sin repeticiones: no se puede estimar |

Prueba oficial (ea_restart, no-IID), salida íntegra en `normal/ea_restart_b1.log` y `ea_restart_b8.log`:

- bit: H_I: 0.838220 / Restart Sanity Check Passed... / H_r: 0.897916 / H_c: 0.853551 / H_I: 0.838220 / Validation Test Passed... / min(H_r, H_c, H_I): 0.838220
- byte: H_I: 6.705756 / Restart Sanity Check Passed... / H_r: 7.314320 / H_c: 6.638383 / H_I: 6.705756 / Validation Test Passed... / min(H_r, H_c, H_I): 6.638383

## Variante sin_ruido

1000 reinicios de 1024 B, lectura nada más arrancar, radio apagada; motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 1000; instante de la lectura 3197-3209 µs desde el arranque del programa. H_I = 0.8382 bit/bit (fb4c_condD_rep2).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 759 de 1000 | 1000 |
| primeros 8 bytes distintos | 759 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4093.7 ± 109.1 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 5.06, p corregida = 0.00385 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 6.71e-06 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 5424 relaciones |
| de ellas, con el solape entero idéntico | 5424 |
| grupos de arranques alineables / el mayor | 87 / 21 |
| secuencias distintas; la más repetida sale | 759; 5 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.5 bits |
| estados equiprobables que darían esas repeticiones | 1725 (≈ 10.8 bits) |

Prueba oficial (ea_restart, no-IID), salida íntegra en `sin_ruido/ea_restart_b1.log` y `ea_restart_b8.log`:

- bit: H_I: 0.838220 / Restart Sanity Check Passed... / H_r: 0.024412 / H_c: 0.813218 / H_I: 0.838220 / *** min(H_r, H_c) < H_I/2, Validation Testing Failed ***
- byte: H_I: 6.705756 / Restart Sanity Check Passed... / H_r: 0.020458 / H_c: 7.132399 / H_I: 6.705756 / *** min(H_r, H_c) < H_I/2, Validation Testing Failed ***

## Variante radio_sin_ruido

1000 reinicios de 1024 B, lectura tras encender el Wi-Fi y esperar 200 ms; motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 1000; instante de la lectura 352618-412637 µs desde el arranque del programa. H_I = 0.8586 bit/bit (fb4c_condB_rep3).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 1000 de 1000 | 1000 |
| primeros 8 bytes distintos | 1000 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4096.1 ± 45.3 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3881 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 3.67, p corregida = 1 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.0334 | p ≈ uniforme |

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
| bloques distintos | 774 de 1000 | 1000 |
| primeros 8 bytes distintos | 774 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4093.2 ± 108.4 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 5.38, p corregida = 0.000695 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 3.16e-10 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 1000 / 1 |
| secuencias distintas; la más repetida sale | 774; 5 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.5 bits |
| estados equiprobables que darían esas repeticiones | 1864 (≈ 10.9 bits) |

Lectura "despues" agrupada por el tick de FreeRTOS en que cae:

| Tick de la lectura (ms) | Arranques | Secuencias distintas | Relaciones de desplazamiento |
|---|---|---|---|
| 350 | 797 | 797 | 0 |
| 360 | 14 | 14 | 0 |
| 370 | 81 | 81 | 0 |
| 390 | 28 | 28 | 0 |
| 400 | 76 | 76 | 0 |
| 410 | 3 | 3 | 0 |

Pares de arranques con la lectura "antes" idéntica: 289; de ellos con la lectura "despues" también idéntica: 0.

Prueba oficial (ea_restart, no-IID), salida íntegra en `radio_sin_ruido/ea_restart_b1.log` y `ea_restart_b8.log`:

- bit: H_I: 0.858563 / Restart Sanity Check Passed... / H_r: 0.830771 / H_c: 0.845421 / H_I: 0.858563 / Validation Test Passed... / min(H_r, H_c, H_I): 0.830771
- byte: H_I: 6.868507 / Restart Sanity Check Passed... / H_r: 6.638399 / H_c: 7.869929 / H_I: 6.868507 / Validation Test Passed... / min(H_r, H_c, H_I): 6.638399

## Variante espera_sin_ruido

1000 reinicios de 1024 B, lectura tras la misma espera, sin encender la radio; motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 0 de 1000; instante de la lectura 352250-352259 µs desde el arranque del programa. H_I = 0.8382 bit/bit (fb4c_condD_rep2).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 760 de 1000 | 1000 |
| primeros 8 bytes distintos | 760 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4093.3 ± 112.3 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 4.87, p corregida = 0.0102 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 7.21e-10 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 5632 relaciones |
| de ellas, con el solape entero idéntico | 5632 |
| grupos de arranques alineables / el mayor | 87 / 24 |
| secuencias distintas; la más repetida sale | 760; 5 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.5 bits |
| estados equiprobables que darían esas repeticiones | 1734 (≈ 10.8 bits) |

Lectura de nada más arrancar en esta misma variante ("antes"):

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 765 de 1000 | 1000 |
| primeros 8 bytes distintos | 765 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4093.7 ± 110.5 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 0 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 4.68, p corregida = 0.0263 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 4.78e-10 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 5586 relaciones |
| de ellas, con el solape entero idéntico | 5586 |
| grupos de arranques alineables / el mayor | 87 / 24 |
| secuencias distintas; la más repetida sale | 765; 5 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 6.5 bits |
| estados equiprobables que darían esas repeticiones | 1778 (≈ 10.8 bits) |

Lectura "despues" agrupada por el tick de FreeRTOS en que cae:

| Tick de la lectura (ms) | Arranques | Secuencias distintas | Relaciones de desplazamiento |
|---|---|---|---|
| 350 | 1000 | 760 | 5632 |

Pares de arranques con la lectura "antes" idéntica: 303; de ellos con la lectura "despues" también idéntica: 275.

Prueba oficial (ea_restart, no-IID), salida íntegra en `espera_sin_ruido/ea_restart_b1.log` y `ea_restart_b8.log`:

- bit: H_I: 0.838220 / Restart Sanity Check Passed... / H_r: 0.024286 / H_c: 0.807901 / H_I: 0.838220 / *** min(H_r, H_c) < H_I/2, Validation Testing Failed ***
- byte: H_I: 6.705756 / Restart Sanity Check Passed... / H_r: 0.020458 / H_c: 7.147481 / H_I: 6.705756 / *** min(H_r, H_c) < H_I/2, Validation Testing Failed ***

## Variante radio

1000 reinicios de 1024 B, lectura tras encender el Wi-Fi y esperar 200 ms; motivo de reset ['1'] (1 = encendido); arranques con la línea de la fuente de ruido encendida en el log: 1000 de 1000; instante de la lectura 352611-402632 µs desde el arranque del programa. H_I = 0.8586 bit/bit (fb4c_condB_rep3).

| Comprobación directa | Valor | Esperado con datos al azar |
|---|---|---|
| bloques distintos | 1000 de 1000 | 1000 |
| primeros 8 bytes distintos | 1000 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4096.0 ± 45.3 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3867 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 4.11, p corregida = 0.362 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.0519 | p ≈ uniforme |

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
| bloques distintos | 1000 de 1000 | 1000 |
| primeros 8 bytes distintos | 1000 de 1000 | 1000 |
| distancia de Hamming entre arranques, media ± desv. | 4096.0 ± 45.3 | 4096 ± 45.3 |
| distancia mínima entre dos arranques | 3883 | ≈ 3887 |
| posición más sesgada (unos en 1000 arranques) | z = 4.17, p corregida = 0.275 | p corregida ≈ uniforme |
| primer byte, χ² frente a uniforme | p = 0.418 | p ≈ uniforme |

| Mismo flujo leído desde otro punto | Valor |
|---|---|
| arranques cuyo inicio aparece desplazado dentro de otro arranque | 0 relaciones |
| de ellas, con el solape entero idéntico | 0 |
| grupos de arranques alineables / el mayor | 1000 / 1 |
| secuencias distintas; la más repetida sale | 1000; 1 veces |
| min-entropía por arranque (cota inferior al 99 %, MCV; con 1000 arranques el techo es 8,1 bits) | 8.1 bits |
| estados equiprobables que darían esas repeticiones | sin repeticiones: no se puede estimar |

Lectura "despues" agrupada por el tick de FreeRTOS en que cae:

| Tick de la lectura (ms) | Arranques | Secuencias distintas | Relaciones de desplazamiento |
|---|---|---|---|
| 350 | 840 | 840 | 0 |
| 360 | 14 | 14 | 0 |
| 370 | 61 | 61 | 0 |
| 380 | 2 | 2 | 0 |
| 390 | 22 | 22 | 0 |
| 400 | 61 | 61 | 0 |

Pares de arranques con la lectura "antes" idéntica: 0; de ellos con la lectura "despues" también idéntica: 0.

Prueba oficial (ea_restart, no-IID), salida íntegra en `radio/ea_restart_b1.log` y `ea_restart_b8.log`:

- bit: H_I: 0.858563 / Restart Sanity Check Passed... / H_r: 0.844141 / H_c: 0.806812 / H_I: 0.858563 / Validation Test Passed... / min(H_r, H_c, H_I): 0.806812
- byte: H_I: 6.868507 / Restart Sanity Check Passed... / H_r: 7.718814 / H_c: 7.887593 / H_I: 6.868507 / Validation Test Passed... / min(H_r, H_c, H_I): 6.868507

