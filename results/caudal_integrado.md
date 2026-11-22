# Caudal y falsas alarmas del integrado (analysis/caudal_integrado.py)

`CFG_KD` 25 (`G_KD_MIN` = `G_KD_RESET`), ro2 de 13 etapas. Periodo de ro2 SIMULADO sin ruido, sin desapareamiento y con 1 fF de carga; caudal y tiempos ESTIMADOS.

| Esquina | T(ro2) ps | bit cada (ms) | bit/s | arranque, 1024 bits (s) | siembra, 512-1535 bits (s) | bit/s con `CFG_KD` 26 |
|---|---|---|---|---|---|---|
| ff, −40 °C, 1,32 V | 594.4 | 19.9 | 50.1 | 20 | 10-31 | 25.1 |
| ff, 125 °C, 1,32 V | 658.7 | 22.1 | 45.2 | 23 | 11-34 | 22.6 |
| tt, 27 °C, 1,2 V | 904.8 | 30.4 | 32.9 | 31 | 16-47 | 16.5 |
| ss, −40 °C, 1,08 V | 1458.6 | 48.9 | 20.4 | 50 | 25-75 | 10.2 |

Arranque tras reset o `borrar_alarmas`: una ventana completa del APT. Siembra: 512 bits y la espera al cierre de la ventana que contiene el último (de 0 a 1023 bits más); si se ordena justo al acabar el arranque, 1024. El DRBG y el CMAC (cientos de ciclos de reloj) no cuentan.

## Falsas alarmas [ESTIMADO, bits iid], cortes RCT 51 / APT 766 de 1024

Cota: integrado a 50.1 bit/s (la esquina más rápida, con el sesgo de la peor). Basys 3 a `kd 19`: 390 bit/s [MEDIDO].

| Fuente | P(1) | H | RCT por bit | APT por ventana | integrado, alarmas/año | P(≥ 4 en 24 h) | Basys 3, alarmas/año |
|---|---|---|---|---|---|---|---|
| bits ideales | 0.5000 | 1.000 | 4.44e-16 | 5.15e-59 | 7.03e-07 | 5.7e-37 | 5.46e-06 |
| peor chip de 120 (0.4166) | 0.4166 | 0.777 | 4.83e-13 | 2.40e-28 | 7.64e-04 | 8.0e-25 | 5.94e-03 |
| μ − 3σ de sf125_v108 (0.4081) | 0.4081 | 0.757 | 9.90e-13 | 7.92e-26 | 1.57e-03 | 1.4e-23 | 1.22e-02 |
| justo en H 0,60 | 0.6598 | 0.600 | 2.09e-10 | 6.15e-10 | 3.32e-01 | 2.8e-14 | 2.58e+00 |
| Basys 3, sesgo medido (0.4959) | 0.4959 | 0.988 | 4.80e-16 | 1.56e-57 | 7.60e-07 | 7.8e-37 | 5.91e-06 |

El rearme del maestro (`motor_rearmar()`, 3 en 24 h) se agota con 4 alarmas en un día. El RCT domina; el APT queda por debajo de 10⁻²⁰ por ventana en todos los casos del biestable.
