# Monte Carlo del biestable sg13g2 (analysis/biestable_mc.py)

SIMULADO, sin ruido; P(1) ponderada por fase, montaje uno_buf. Fuentes: biestable_ihp_sf_ff_mm.csv, biestable_ihp_mc24.csv, biestable_ihp_mc8_v108.csv, biestable_ihp_mc16_v108.csv.
**Lectura de sensibilidad, no oficial:** sin los chips con hueco de fase > 0.025.
Criterio fijado antes de simular (docs/basys2.md, 16-11-2026).

| Esquina | n | μ | σ | σ IC 95 % | Shapiro-Wilk p | μ ∓ 3σ | H | H con σ alta | peor chip | H peor |
|---|---|---|---|---|---|---|---|---|---|---|
| ff125_v132_mm (sf_ff_mm 4, mc24 22) | 26 | 0.4446 | 0.0280 | 0.0220-0.0387 | 0.21 | 0.3606 | 0.645 | 0.575 | 0.3724 | 0.672 |
| sf125_mm (sf_ff_mm 4, mc24 22) | 26 | 0.4183 | 0.0318 | 0.0250-0.0440 | 0.81 | 0.3228 | 0.562 | 0.487 | 0.3507 | 0.623 |
| sf125_v108_mm (mc8_v108 7, mc16_v108 15) | 22 | 0.4184 | 0.0369 | 0.0284-0.0527 | 0.10 | 0.3076 | 0.530 | 0.435 | 0.3385 | 0.596 |
| tt125_mm (mc24 22) | 22 | 0.4747 | 0.0167 | 0.0128-0.0238 | 0.11 | 0.4247 | 0.798 | 0.745 | 0.4259 | 0.801 |

Tandas independientes de la misma esquina (sorteos distintos):

- ff125_v132_mm: tandas 0.4165 (n 4) y 0.4497 (n 22), Welch p = 0.22
- sf125_mm: tandas 0.4190 (n 4) y 0.4182 (n 22), Welch p = 0.94
- sf125_v108_mm: tandas 0.4173 (n 7) y 0.4188 (n 15), Welch p = 0.94

**H declarable = 0.530** (esquina sf125_v108_mm); objetivo 0.6: por debajo: corregir el circuito, no bajar H.
sf 1,08 V frente a 1,2 V en media: 0.4184 frente a 0.4183 (no peor).
