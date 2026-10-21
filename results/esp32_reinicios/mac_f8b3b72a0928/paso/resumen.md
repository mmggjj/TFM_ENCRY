# Paso del RNG sin ruido, chip f8b3b72a0928

Generado por analysis/reinicios_paso.py. Cada arranque: "antes", un retardo de N NOP con las interrupciones apagadas y "despues".

| Variante | NOP extra | Arranques | Ciclos del retardo (medidos) | Ciclos de "antes" | Ciclos de "despues" |
|---|---|---|---|---|---|
| 0 | 0 | 194 | 1742547-1742547 | 46482-46482 | 44565-44565 |
| 1 | 2 | 193 | 1742549-1742549 | 46482-46482 | 44565-44565 |
| 2 | 174 | 205 | 1742721-1742721 | 46482-46482 | 44565-44565 |
| 3 | 17400 | 208 | 1759947-1759947 | 46482-46482 | 44565-44565 |

800 arranques; 646 lecturas "antes" distintas; 204 parejas con el "antes" idéntico. Desplazamiento del "despues" de la segunda variante respecto del de la primera, en palabras de 32 bits:

| Variantes | Parejas | Desplazamientos observados | Predicción (paso por ciclo de APB) |
|---|---|---|---|
| 0 y 0 | 15 | +0: 15 | 0 |
| 0 y 1 | 25 | sin alinear: 25 | sin alinear |
| 0 y 2 | 21 | +1: 21 | +1 |
| 0 y 3 | 41 | +100: 41 | +100 |
| 1 y 1 | 6 | +0: 6 | 0 |
| 1 y 2 | 27 | sin alinear: 27 | sin alinear |
| 1 y 3 | 15 | sin alinear: 15 | sin alinear |
| 2 y 2 | 11 | +0: 11 | 0 |
| 2 y 3 | 23 | +99: 23 | +99 |
| 3 y 3 | 20 | +0: 20 | 0 |

