# Monte Carlo del biestable sg13g2 (analysis/biestable_mc.py)

SIMULADO, sin ruido; P(1) ponderada por fase, montaje uno_buf, 125 °C.
Criterio fijado antes de simular (docs/basys2.md, 16-11-2026).

| Esquina | n | μ | σ | σ IC 95 % | Shapiro-Wilk p | μ ∓ 3σ | H | H con σ alta | peor chip | H peor |
|---|---|---|---|---|---|---|---|---|---|---|
| ff125_v132_mm (sf_ff_mm 4, mc24 24) | 28 | 0.4458 | 0.0273 | 0.0216-0.0372 | 0.09 | 0.3639 | 0.653 | 0.587 | 0.3724 | 0.672 |
| sf125_mm (sf_ff_mm 4, mc24 24) | 28 | 0.4201 | 0.0316 | 0.0250-0.0430 | 0.84 | 0.3254 | 0.568 | 0.497 | 0.3507 | 0.623 |
| sf125_v108_mm (mc8_v108 8, mc16_v108 16) | 24 | 0.4167 | 0.0361 | 0.0281-0.0507 | 0.17 | 0.3083 | 0.532 | 0.443 | 0.3385 | 0.596 |
| tt125_mm (mc24 24) | 24 | 0.4747 | 0.0159 | 0.0124-0.0224 | 0.06 | 0.4269 | 0.803 | 0.755 | 0.4259 | 0.801 |

Tandas independientes de la misma esquina (sorteos distintos):

- ff125_v132_mm: tandas 0.4165 (n 4) y 0.4507 (n 24), Welch p = 0.21
- sf125_mm: tandas 0.4190 (n 4) y 0.4203 (n 24), Welch p = 0.90
- sf125_v108_mm: tandas 0.4173 (n 8) y 0.4164 (n 16), Welch p = 0.96

**H declarable = 0.532** (esquina sf125_v108_mm); objetivo 0.6: por debajo: corregir el circuito, no bajar H.
sf 1,08 V frente a 1,2 V en media: 0.4167 frente a 0.4201 (peor, ya con 24 chips).
