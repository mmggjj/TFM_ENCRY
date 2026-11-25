# Reinicios de la FPGA: basys3_kd19_bel

1000 arranques; 128 bytes por arranque; H_I = 0.857

## Comprobacion directa (como reinicios_90b.py)

- arranques distintos: 1000 de 1000 (primeros 8 bytes: 1000)
- distancia de Hamming entre arranques: minima 439 (esperada ~438), media 511.9 (esperada 512), desviacion 16.02 (esperada 16.00)
- columna mas desviada: 195 (|z| 3.92, p corregida 0.101)
- primer byte uniforme: p = 0.668
- arranques que son el mismo flujo desde otro punto: 0 relaciones, 1000 componentes (mayor 1); repeticion maxima 1

## ea_restart (modo bit, 1000 x 1000)

exit 0: H_I: 0.857000 / Restart Sanity Check Passed... / H_r: 0.853843 / H_c: 0.829526 / H_I: 0.857000 / Validation Test Passed... / min(H_r, H_c, H_I): 0.829526
(log integro en ea_restart_b1.log)
