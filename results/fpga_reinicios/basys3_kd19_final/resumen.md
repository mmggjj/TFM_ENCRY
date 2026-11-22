# Reinicios de la FPGA: basys3_kd19_final

1000 arranques; 128 bytes por arranque; H_I = 0.852733

## Comprobacion directa (como reinicios_90b.py)

- arranques distintos: 1000 de 1000 (primeros 8 bytes: 1000)
- distancia de Hamming entre arranques: minima 436 (esperada ~438), media 512.0 (esperada 512), desviacion 15.98 (esperada 16.00)
- columna mas desviada: 447 (|z| 3.23, p corregida 1)
- primer byte uniforme: p = 0.472
- arranques que son el mismo flujo desde otro punto: 0 relaciones, 1000 componentes (mayor 1); repeticion maxima 1

## ea_restart (modo bit, 1000 x 1000)

exit 0: H_I: 0.852733 / Restart Sanity Check Passed... / H_r: 0.846922 / H_c: 0.844732 / H_I: 0.852733 / Validation Test Passed... / min(H_r, H_c, H_I): 0.844732
(log integro en ea_restart_b1.log)
