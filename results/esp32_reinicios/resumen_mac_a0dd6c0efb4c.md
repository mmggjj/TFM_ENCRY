# Prueba de reinicios del RNG del ESP32, chip a0dd6c0efb4c

Generado por analysis/reinicios_90b.py. H_I: estimación no-IID de la captura en condición D más baja del chip (fb4c_condD_rep2): 0.8382 bit/bit, 6.706 bit/byte.

## Variante normal

1000 reinicios de 1024 B; motivo de reset ['1'] (1 = encendido); ruido del arranque encendido: ['0', '1']; instante de la lectura 3192-3204 µs desde el arranque del programa.

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

1000 reinicios de 1024 B; motivo de reset ['1'] (1 = encendido); ruido del arranque encendido: ['0']; instante de la lectura 3197-3209 µs desde el arranque del programa.

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

