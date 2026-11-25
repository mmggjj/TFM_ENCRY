# Sensibilidad de los anillos a V_DD (analysis/sensibilidad_vdd.py)

SIMULADO, sin ruido, PDK IHP SG13G2; escalón de ±10 mV dentro del mismo transitorio. S = (1/T) dT/dV (negativa: al subir V_DD el anillo va más deprisa). Rechazo del modo común = |S2 − S1| / |S1|.

## Sin desapareamiento

| Esquina | T(ro1) ps | T(ro2) ps | S1 (1/V) | S2 (1/V) | S2 − S1 (1/V) | rechazo |
|---|---|---|---|---|---|---|
| tt27 | 770.2 | 904.8 | -1.6766 | -1.6826 | -0.00597 | 0.0036 |
| ss_m40_v108 | 1241.0 | 1458.6 | -2.7468 | -2.7581 | -0.01136 | 0.0041 |
| ffm40_v132 | 506.1 | 594.4 | -1.3387 | -1.3439 | -0.00513 | 0.0038 |
| ff125_v132 | 560.9 | 658.7 | -1.0690 | -1.0729 | -0.00386 | 0.0036 |

## Con desapareamiento

| Esquina | n por anillo | S1 μ ± σ (1/V) | S2 μ ± σ (1/V) | S2 − S1: μ ± σ (1/V) | rechazo típico (μ + 2σ de |S2 − S1|, / |S1|) |
|---|---|---|---|---|---|
| tt27 | 8/8 | -1.6840 ± 0.0078 | -1.6808 ± 0.0134 | +0.00325 ± 0.01546 | 0.0203 |
| ss_m40_v108 | 8/8 | -2.7455 ± 0.0238 | -2.7647 ± 0.0254 | -0.01915 ± 0.03479 | 0.0323 |
