# Monte Carlo del biestable sg13g2 (analysis/biestable_mc.py)

SIMULADO, sin ruido; P(1) ponderada por fase, montaje uno_buf. Fuentes: biestable_ihp_mc24_e11_criticas.log.
Criterio fijado antes de simular (docs/basys2.md, 16-11-2026).

| Esquina | n | μ | σ | σ IC 95 % | Shapiro-Wilk p | μ ∓ 3σ | H | H con σ alta | peor chip | H peor |
|---|---|---|---|---|---|---|---|---|---|---|
| ffm40_v132_mm (mc24_e11_criticas 11) | 11 | 0.4789 | 0.0095 | 0.0066-0.0167 | 0.14 | 0.4504 | 0.864 | 0.808 | 0.4568 | 0.880 |
| sf125_mm (mc24_e11_criticas 11) | 11 | 0.4700 | 0.0069 | 0.0048-0.0121 | 0.13 | 0.4494 | 0.861 | 0.821 | 0.4592 | 0.887 |
| sf125_v108_mm (mc24_e11_criticas 11) | 11 | 0.4691 | 0.0201 | 0.0140-0.0352 | 0.00 | 0.4090 | 0.759 | 0.652 | 0.4166 | 0.777 |

**H declarable = 0.759** (esquina sf125_v108_mm); objetivo 0.6: se cierra H 0,60.
sf 1,08 V frente a 1,2 V en media: 0.4691 frente a 0.4700 (peor: ampliar a 24 chips).
