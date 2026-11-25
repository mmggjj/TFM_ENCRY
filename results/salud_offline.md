# Tests de salud en software sobre bits capturados (analysis/salud_offline.py)

Alarmas (rachas >= C del RCT; ventanas de 1024 con cuenta o complemento
>= C del APT) con cada juego de cortes, sobre los mismos bits.

| Fuente | kd | tipo | bits | racha máx | APT máx | RCT 22/596 | RCT 39/683 | RCT 51/766 | APT 22/596 | APT 39/683 | APT 51/766 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 14-11 (CE), hoy | 7 | trozos | 1001472 | 4 | 535 | 0 | 0 | 0 | 0 | 0 | 0 |
| 14-11 (CE), hoy | 8 | trozos | 1001472 | 17 | 574 | 0 | 0 | 0 | 0 | 0 | 0 |
| 14-11 (CE), hoy | 9 | trozos | 1001472 | 7 | 544 | 0 | 0 | 0 | 0 | 0 | 0 |
| fijo (CE) | 7 | trozos | 1001472 | 14 | 567 | 0 | 0 | 0 | 0 | 0 | 0 |
| fijo (CE) | 8 | trozos | 1001472 | 8 | 569 | 0 | 0 | 0 | 0 | 0 | 0 |
| fijo (CE) | 9 | trozos | 1001472 | 8 | 576 | 0 | 0 | 0 | 0 | 0 | 0 |
| libre 51/766 (sin CE) | 7 | trozos | 1000448 | 6 | 534 | 0 | 0 | 0 | 0 | 0 | 0 |
| libre 51/766 (sin CE) | 8 | trozos | 1001472 | 4 | 549 | 0 | 0 | 0 | 0 | 0 | 0 |
| libre 51/766 (sin CE) | 9 | trozos | 1001472 | 6 | 535 | 0 | 0 | 0 | 0 | 0 | 0 |
| 14-11 (CE), campaña 90B | 12 | tira | 1000000 | 21 | 580 | 0 | 0 | 0 | 0 | 0 | 0 |
| 14-11 (CE), campaña 90B | 13 | tira | 1000000 | 19 | 568 | 0 | 0 | 0 | 0 | 0 | 0 |
| 14-11 (CE), campaña 90B | 14 | tira | 1000000 | 21 | 563 | 0 | 0 | 0 | 0 | 0 | 0 |
| 14-11 (CE), campaña 90B | 15 | tira | 1000000 | 22 | 568 | 1 | 0 | 0 | 0 | 0 | 0 |
| 14-11 (CE), campaña 90B | 16 | tira | 1000000 | 21 | 567 | 0 | 0 | 0 | 0 | 0 | 0 |
| 14-11 (CE), larga | 14 | tira | 8378368 | 23 | 577 | 1 | 0 | 0 | 0 | 0 | 0 |
| libre 39/683 (sin CE) | 13 | tira | 4194304 | 23 | 581 | 2 | 0 | 0 | 0 | 0 | 0 |
| libre 39/683 (sin CE) | 14 | tira | 4194304 | 20 | 582 | 0 | 0 | 0 | 0 | 0 | 0 |
| iid p1=0.5 | - | tira | 8388608 | 26 | 575 | 3 | 0 | 0 | 0 | 0 | 0 |
| iid p1=0.4962 | - | tira | 8388608 | 25 | 571 | 2 | 0 | 0 | 0 | 0 | 0 |
