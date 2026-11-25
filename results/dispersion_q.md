# Dispersión de Q entre realizaciones (analysis/dispersion_q.py)

SIMULADO. "blanco" = dispersión del mismo estimador con jitter blanco iid y el mismo número de cruces (800 Monte Carlo); p de chi-cuadrado de la dispersión observada.

| Tanda | etapas | n | cruces | dispersión Q | blanco | cociente | p | exponente medio |
|---|---|---|---|---|---|---|---|---|
| esq_ff_125 | 5 | 4 | 1270 | 0.039 | 0.045 | 0.86 | 0.532 | 1.03 |
| esq_ff_27 | 5 | 4 | 1330 | 0.068 | 0.041 | 1.66 | 0.041 | 0.93 |
| esq_ff_m40 | 5 | 4 | 1360 | 0.100 | 0.040 | 2.53 | 0.000 | 0.96 |
| esq_fs_m40 | 5 | 4 | 1100 | 0.009 | 0.045 | 0.21 | 0.988 | 1.03 |
| esq_fs_m40_v108 | 5 | 4 | 840 | 0.022 | 0.052 | 0.42 | 0.912 | 0.93 |
| esq_sf_m40 | 5 | 4 | 1090 | 0.021 | 0.046 | 0.46 | 0.889 | 0.93 |
| esq_sf_m40_v108 | 5 | 4 | 830 | 0.085 | 0.053 | 1.61 | 0.050 | 0.93 |
| esq_ss_125 | 5 | 4 | 830 | 0.080 | 0.053 | 1.52 | 0.075 | 1.03 |
| esq_ss_27 | 5 | 4 | 860 | 0.045 | 0.052 | 0.86 | 0.528 | 0.94 |
| esq_ss_m40 | 5 | 4 | 890 | 0.038 | 0.052 | 0.73 | 0.658 | 1.04 |
| esq_ss_m40_v108 | 5 | 8 | 660 | 0.073 | 0.060 | 1.22 | 0.169 | 1.00 |
| esq_ss_m40_v132 | 5 | 4 | 1120 | 0.041 | 0.045 | 0.91 | 0.479 | 0.99 |
| esq_tt_125 | 5 | 4 | 1030 | 0.054 | 0.049 | 1.10 | 0.302 | 0.98 |
| esq_tt_m40 | 5 | 4 | 1100 | 0.017 | 0.045 | 0.37 | 0.938 | 0.97 |
| esq_tt_m40_v108 | 5 | 4 | 840 | 0.029 | 0.052 | 0.56 | 0.812 | 1.02 |
| mc_ss_m40_v108_hist | 5 | 8 | 660 | 0.075 | 0.060 | 1.25 | 0.140 | 0.98 |
| mc_tt_27 | 5 | 48 | 1070 | 0.051 | 0.047 | 1.10 | 0.163 | 0.99 |
| rep400n | 5 | 8 | 1070 | 0.065 | 0.047 | 1.40 | 0.058 | 0.99 |
| ss_m40_v108_e11 | 11 | 8 | 700 | 0.105 | 0.056 | 1.88 | 0.001 | 0.96 |

Tandas de 5 etapas juntas: χ² 148.4 con 110 gl, p 0.009; factor medio sobre el blanco 1.16.
ss_m40_v108_e11 frente al blanco ya escalado por ese factor: p 0.010. Q media 2.999e-08 ± 2.64e-09 (IC 95 %), mínima 2.651e-08.
