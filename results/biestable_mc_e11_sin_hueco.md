# Monte Carlo del biestable sg13g2 (analysis/biestable_mc.py)

SIMULADO, sin ruido; P(1) ponderada por fase, montaje uno_buf. Fuentes: biestable_ihp_mc24_e11_criticas.log, biestable_ihp_mc24_e11_criticas_b.log, biestable_ihp_mc24_e11_resto.log.
**Lectura de sensibilidad, no oficial:** sin los chips con hueco de fase > 0.025.
Criterio fijado antes de simular (docs/basys2.md, 16-11-2026).

| Esquina | n | μ | σ | σ IC 95 % | Shapiro-Wilk p | μ ∓ 3σ | H | H con σ alta | peor chip | H peor |
|---|---|---|---|---|---|---|---|---|---|---|
| ff125_v132_mm (mc24_e11_resto 23) | 23 | 0.4701 | 0.0100 | 0.0077-0.0141 | 0.14 | 0.4402 | 0.837 | 0.805 | 0.4447 | 0.849 |
| ffm40_v132_mm (mc24_e11_criticas 9, mc24_e11_criticas_b 12) | 21 | 0.4803 | 0.0071 | 0.0054-0.0103 | 0.03 | 0.4590 | 0.886 | 0.861 | 0.4697 | 0.915 |
| sf125_mm (mc24_e11_criticas 11, mc24_e11_criticas_b 13) | 24 | 0.4642 | 0.0100 | 0.0078-0.0140 | 0.08 | 0.4342 | 0.822 | 0.791 | 0.4355 | 0.825 |
| sf125_v108_mm (mc24_e11_criticas 9, mc24_e11_criticas_b 13) | 22 | 0.4635 | 0.0141 | 0.0109-0.0202 | 0.20 | 0.4211 | 0.789 | 0.744 | 0.4320 | 0.816 |
| tt125_mm (mc24_e11_resto 22) | 22 | 0.4814 | 0.0124 | 0.0095-0.0177 | 0.00 | 0.4443 | 0.848 | 0.807 | 0.4673 | 0.909 |

Tandas independientes de la misma esquina (sorteos distintos):

- ffm40_v132_mm: tandas 0.4819 (n 9) y 0.4790 (n 12), Welch p = 0.35
- sf125_mm: tandas 0.4700 (n 11) y 0.4592 (n 13), Welch p = 0.00
- sf125_v108_mm: tandas 0.4715 (n 9) y 0.4579 (n 13), Welch p = 0.01

**H declarable = 0.789** (esquina sf125_v108_mm); objetivo 0.6: se cierra H 0,60.
sf 1,08 V frente a 1,2 V en media: 0.4635 frente a 0.4642 (peor: ampliar a 24 chips).
