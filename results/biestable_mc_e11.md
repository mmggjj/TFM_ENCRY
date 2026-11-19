# Monte Carlo del biestable sg13g2 (analysis/biestable_mc.py)

SIMULADO, sin ruido; P(1) ponderada por fase, montaje uno_buf. Fuentes: biestable_ihp_mc24_e11_criticas.log.
Criterio fijado antes de simular (docs/basys2.md, 16-11-2026).

| Esquina | n | μ | σ | σ IC 95 % | Shapiro-Wilk p | μ ∓ 3σ | H | H con σ alta | peor chip | H peor |
|---|---|---|---|---|---|---|---|---|---|---|
| ffm40_v132_mm (mc24_e11_criticas 7) | 7 | 0.4821 | 0.0055 | 0.0036-0.0122 | 0.73 | 0.4655 | 0.904 | 0.851 | 0.4741 | 0.927 |
| sf125_mm (mc24_e11_criticas 8) | 8 | 0.4693 | 0.0071 | 0.0047-0.0145 | 0.42 | 0.4479 | 0.857 | 0.800 | 0.4592 | 0.887 |
| sf125_v108_mm (mc24_e11_criticas 8) | 8 | 0.4670 | 0.0235 | 0.0156-0.0479 | 0.10 | 0.3963 | 0.728 | 0.563 | 0.4166 | 0.777 |

**H declarable = 0.728** (esquina sf125_v108_mm); objetivo 0.6: se cierra H 0,60.
sf 1,08 V frente a 1,2 V en media: 0.4670 frente a 0.4693 (peor: ampliar a 24 chips).
