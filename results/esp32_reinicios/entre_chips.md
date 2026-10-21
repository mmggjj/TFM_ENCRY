# Prueba de reinicios: lecturas sin ruido de dos chips

Generado por analysis/reinicios_entre_chips.py. Un grupo es un conjunto de bloques de 1024 B que se alinean entre sí (el inicio de uno aparece desplazado dentro de otro y el solape entero coincide palabra a palabra).

7600 bloques; 72616 relaciones de desplazamiento, de ellas 0 con el solape distinto; 3035 grupos.

| Captura | Bloques | Grupos en que está | Grupos solo suyos | Bloques idénticos a alguno de otra captura |
|---|---|---|---|---|
| chip a0:dd:6c:0e:fb:4c, sin_ruido | 1000 | 87 | 0 | 535 |
| chip f8:b3:b7:2a:09:28, sin_ruido | 1000 | 87 | 0 | 630 |
| chip a0:dd:6c:0e:fb:4c, espera_sin_ruido "antes" | 1000 | 87 | 0 | 596 |
| chip a0:dd:6c:0e:fb:4c, espera_sin_ruido "despues" | 1000 | 87 | 87 | 0 |
| chip a0:dd:6c:0e:fb:4c, radio_sin_ruido "antes" | 1000 | 774 | 774 | 0 |
| chip f8:b3:b7:2a:09:28, fuente_control "antes" | 300 | 86 | 0 | 0 |
| chip f8:b3:b7:2a:09:28, fuente_control "despues" | 300 | 87 | 87 | 0 |
| chip a0:dd:6c:0e:fb:4c, normal | 1000 | 1000 | 1000 | 0 |
| chip f8:b3:b7:2a:09:28, normal | 1000 | 1000 | 1000 | 0 |

Grupos compartidos entre capturas (número de grupos con bloques de las dos):

| Captura 1 | Captura 2 | Grupos comunes | Relaciones de desplazamiento entre ellas |
|---|---|---|---|
| chip a0:dd:6c:0e:fb:4c, sin_ruido | chip f8:b3:b7:2a:09:28, sin_ruido | 87 | 12073 |
| chip a0:dd:6c:0e:fb:4c, sin_ruido | chip a0:dd:6c:0e:fb:4c, espera_sin_ruido "antes" | 87 | 11989 |
| chip a0:dd:6c:0e:fb:4c, sin_ruido | chip f8:b3:b7:2a:09:28, fuente_control "antes" | 86 | 3347 |
| chip f8:b3:b7:2a:09:28, sin_ruido | chip a0:dd:6c:0e:fb:4c, espera_sin_ruido "antes" | 87 | 12155 |
| chip f8:b3:b7:2a:09:28, sin_ruido | chip f8:b3:b7:2a:09:28, fuente_control "antes" | 86 | 3445 |
| chip a0:dd:6c:0e:fb:4c, espera_sin_ruido "antes" | chip f8:b3:b7:2a:09:28, fuente_control "antes" | 86 | 3470 |

Entre "chip a0:dd:6c:0e:fb:4c, sin_ruido" y "chip f8:b3:b7:2a:09:28, sin_ruido":

- contenidos de 1024 B distintos que salen en los dos: 256 (de 759 y 746 distintos);
- bloques idénticos a alguno del otro chip: 352 de 1000 y 347 de 1000;
- bloques de "chip f8:b3:b7:2a:09:28, sin_ruido" que empiezan dentro de alguno de "chip a0:dd:6c:0e:fb:4c, sin_ruido" (desfase ≥ 0 palabras): 988 de 1000, en 8369 relaciones (7891 con desfase > 0); 0 de 8369 con el solape distinto.
- bloques de "chip a0:dd:6c:0e:fb:4c, sin_ruido" que empiezan dentro de alguno de "chip f8:b3:b7:2a:09:28, sin_ruido" (desfase ≥ 0 palabras): 760 de 1000, en 3704 relaciones (3226 con desfase > 0); 0 de 3704 con el solape distinto.

