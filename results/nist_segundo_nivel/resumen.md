# SP 800-22, análisis de segundo nivel (§4.2)

Generado por analysis/nist_segundo_nivel.py. 59 secuencias de 10^6 bits; α = 0,01; proporción aceptable p̂ ± 3·√(p̂(1−p̂)/m) con p̂ = 0,99; uniformidad: χ² sobre 10 intervalos, P-value_T ≥ 10⁻⁴ (la norma pide m ≥ 55).

| Estadístico | m | Pasan | Proporción | Mínimo aceptable | P-value_T | Veredicto |
|---|---|---|---|---|---|---|
| Frequency | 59 | 59 | 1.0000 | 0.9511 | 0.9190 | pasa |
| Block Frequency | 59 | 59 | 1.0000 | 0.9511 | 0.8431 | pasa |
| Runs | 59 | 58 | 0.9831 | 0.9511 | 0.0651 | pasa |
| Longest Run | 59 | 59 | 1.0000 | 0.9511 | 0.7484 | pasa |
| Matrix Rank | 59 | 58 | 0.9831 | 0.9511 | 0.7815 | pasa |
| Spectral DFT | 59 | 57 | 0.9661 | 0.9511 | 0.2532 | pasa |
| Non-overlapping Template 1 | 59 | 57 | 0.9661 | 0.9511 | 0.0987 | pasa |
| Non-overlapping Template 2 | 59 | 59 | 1.0000 | 0.9511 | 0.7142 | pasa |
| Non-overlapping Template 3 | 59 | 59 | 1.0000 | 0.9511 | 0.3250 | pasa |
| Non-overlapping Template 4 | 59 | 59 | 1.0000 | 0.9511 | 0.3519 | pasa |
| Non-overlapping Template 5 | 59 | 59 | 1.0000 | 0.9511 | 0.7815 | pasa |
| Non-overlapping Template 6 | 59 | 58 | 0.9831 | 0.9511 | 0.4096 | pasa |
| Non-overlapping Template 7 | 59 | 59 | 1.0000 | 0.9511 | 0.1464 | pasa |
| Non-overlapping Template 8 | 59 | 58 | 0.9831 | 0.9511 | 0.9971 | pasa |
| Overlapping Template | 59 | 59 | 1.0000 | 0.9511 | 0.7142 | pasa |
| Universal | 59 | 59 | 1.0000 | 0.9511 | 0.5054 | pasa |
| Linear Complexity | 59 | 58 | 0.9831 | 0.9511 | 0.5739 | pasa |
| Serial 1 | 59 | 58 | 0.9831 | 0.9511 | 0.8431 | pasa |
| Serial 2 | 59 | 59 | 1.0000 | 0.9511 | 0.4404 | pasa |
| Approximate Entropy | 59 | 58 | 0.9831 | 0.9511 | 0.8431 | pasa |
| Cumulative Sums fwd | 59 | 58 | 0.9831 | 0.9511 | 0.8963 | pasa |
| Cumulative Sums bwd | 59 | 58 | 0.9831 | 0.9511 | 0.5393 | pasa |
| Random Excursions 1 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.7399 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions 2 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.8953 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions 3 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.6799 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions 4 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.5580 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions 5 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.7399 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions 6 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.2964 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions 7 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.6188 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions 8 (25 no aplicables) | 34 | 33 | 0.9706 | 0.9388 | 0.7399 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 1 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.6799 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 2 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.7399 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 3 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.6188 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 4 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.0556 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 5 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.8494 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 6 (25 no aplicables) | 34 | 33 | 0.9706 | 0.9388 | 0.8953 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 7 (25 no aplicables) | 34 | 33 | 0.9706 | 0.9388 | 0.0959 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 8 (25 no aplicables) | 34 | 33 | 0.9706 | 0.9388 | 0.0075 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 9 (25 no aplicables) | 34 | 33 | 0.9706 | 0.9388 | 0.5580 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 10 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.7399 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 11 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.8494 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 12 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.7970 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 13 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.6188 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 14 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.3899 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 15 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.1142 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 16 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.3899 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 17 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.1142 | pasa (m < 55: uniformidad orientativa) |
| Random Excursions Variant 18 (25 no aplicables) | 34 | 34 | 1.0000 | 0.9388 | 0.1881 | pasa (m < 55: uniformidad orientativa) |

48 estadísticos, 2182 p en total; 18 por debajo de 0,01 (esperadas 21.8). Estadísticos que no pasan el segundo nivel: ninguno.

