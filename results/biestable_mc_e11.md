# Monte Carlo del biestable sg13g2 (analysis/biestable_mc.py)

SIMULADO, sin ruido; P(1) ponderada por fase, montaje uno_buf. Fuentes: biestable_ihp_mc24_e11_criticas.log, biestable_ihp_mc24_e11_criticas_b.log, biestable_ihp_mc24_e11_resto.log.
**Lectura oficial:** todos los chips.
Criterio fijado antes de simular (docs/basys2.md, 16-11-2026).

| Esquina | n | μ | σ | σ IC 95 % | Shapiro-Wilk p | μ ∓ 3σ | H | H con σ alta | peor chip | H peor |
|---|---|---|---|---|---|---|---|---|---|---|
| ff125_v132_mm (mc24_e11_resto 24) | 24 | 0.4700 | 0.0098 | 0.0076-0.0137 | 0.16 | 0.4406 | 0.838 | 0.808 | 0.4447 | 0.849 |
| ffm40_v132_mm (mc24_e11_criticas 11, mc24_e11_criticas_b 13) | 24 | 0.4784 | 0.0088 | 0.0068-0.0123 | 0.10 | 0.4521 | 0.868 | 0.840 | 0.4568 | 0.880 |
| sf125_mm (mc24_e11_criticas 11, mc24_e11_criticas_b 13) | 24 | 0.4642 | 0.0100 | 0.0078-0.0140 | 0.08 | 0.4342 | 0.822 | 0.791 | 0.4355 | 0.825 |
| sf125_v108_mm (mc24_e11_criticas 11, mc24_e11_criticas_b 13) | 24 | 0.4631 | 0.0183 | 0.0142-0.0257 | 0.39 | 0.4081 | 0.757 | 0.704 | 0.4166 | 0.777 |
| tt125_mm (mc24_e11_resto 24) | 24 | 0.4811 | 0.0119 | 0.0093-0.0167 | 0.00 | 0.4454 | 0.851 | 0.814 | 0.4673 | 0.909 |

Tandas independientes de la misma esquina (sorteos distintos):

- ffm40_v132_mm: tandas 0.4789 (n 11) y 0.4779 (n 13), Welch p = 0.78
- sf125_mm: tandas 0.4700 (n 11) y 0.4592 (n 13), Welch p = 0.00
- sf125_v108_mm: tandas 0.4691 (n 11) y 0.4579 (n 13), Welch p = 0.15

**H declarable = 0.757** (esquina sf125_v108_mm); objetivo 0.6: se cierra H 0,60.
sf 1,08 V frente a 1,2 V en media: 0.4631 frente a 0.4642 (peor, ya con 24 chips).
