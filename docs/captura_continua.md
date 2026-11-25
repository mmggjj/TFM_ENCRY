# Captura continua de bits crudos (FLUJO)

Hecho el 10-11-2026, sin placa. **Nada de esto se ha ejecutado en
hardware**: lo que hay es simulación del RTL (GHDL), el modelo del motor en
el PC y síntesis. La especificación del registro está en
`mapa_registros.md`; aquí va el porqué, lo comprobado y cómo se usa.

## 1. Qué problema resuelve

`capturar` (`trng_capture`) llena un buffer de 4096 bits a la velocidad del
anillo y el ESP32 lo vuelca después. Entre dos capturas se pierden los bits
que llegan mientras se lee, así que una campaña de 10⁶ bits eran 245 trozos
sin relación entre sí. SP 800-90B §3.1.1 pide 10⁶ muestras **consecutivas**:
una deriva lenta (1/f, temperatura) entre trozos quedaba cortada en parte.

Para el estimador de jitter los trozos independientes siguen siendo lo que
hace falta (`trng_capture.vhd`), y con divisores bajos (CFG_KD 0-10) no hay
otra forma: el bus no puede con esa tasa. Las dos capturas conviven.

## 2. Cómo funciona

- `rtl/trng/flujo_crudo.vhd`: una FIFO de bytes en el dominio de sistema.
  Entran los bits **después de `bit_cdc`**, los mismos que evalúan los tests
  de salud y que recoge la siembra, así que la tira que se pasa por la
  batería es la que consume el DRBG, no una vía paralela.
- El maestro la vacía por I2C mientras se llena: puntero a 0x60 y 32 bytes
  por transacción (`n` y hasta 31 datos). Leer `n` fija un crédito; un byte
  que entra a mitad de la lectura se queda para la siguiente.
- Si llega un byte con la FIFO llena, no se pisa nada: sube `desbordado` y
  el flujo se para. La tira deja de valer y el verificador lo dice.
- Reglas de seguridad, las de `capturar`: solo en modo test y nunca a la vez
  que una siembra (ni captura), en los dos sentidos. Con el flujo activo
  CFG_KD no cambia. Quitar modo test o `borrar_todo` lo paran.
- `G_FLUJO_BYTES`: 256 en `basys3_top`, **0 por defecto en `motor_top`**
  (sin FIFO). Es instrumentación de caracterización, como `ro_mon`.

## 3. Tasas [ESTIMADO, ro2 a 300 MHz; el anillo real, 170-330 MHz]

| CFG_KD | bits/s | bytes/s | 10⁶ bits | FIFO de 256 B se llena en |
|---|---|---|---|---|
| 12 | 73 200 | 9 160 | 14 s | 28 ms |
| 13 | 36 600 | 4 580 | 27 s | 56 ms |
| 14 | 18 300 | 2 290 | 55 s | 112 ms |
| 17 | 2 290 | 286 | 7,3 min | 0,9 s |
| 20 | 286 | 36 | 58 min | 7,2 s |
| 23 | 36 | 4,5 | 7,8 h | 57 s |

Dos cuellos, los dos del lado del ESP32:

- **I2C a 400 kHz:** una transacción de 35 bytes son ~0,8 ms, unos
  31 kB/s. Daría para CFG_KD ≥ 11.
- **UART a 115 200:** cada trama C son 280 caracteres para 128 bytes, unos
  5 kB/s. Es el que manda: **el flujo sirve desde CFG_KD 13-14**. Con 12
  se desborda, y el verificador lo detecta y lo dice. Para SP 800-90B
  interesan los divisores de trabajo (17-23), muy por encima.

Mientras el ESP32 imprime una trama (~24 ms) la FIFO acumula: con CFG_KD 14
son ~55 bytes de 256. Por debajo de 13 hay que usar los trozos.

## 4. Cómo se usa

Verificador: `kd N`, y `flujo B` vuelca B bytes consecutivos:

```
flujo inicio kd 17 bytes 125000
FC0084<seq 4 B, bajo primero><128 B><crc32>      una por cada 128 bytes
flujo fin bytes 125000 kd 17 ms 437012 ok
```

Si algo falla sale `flujo: <motivo> tras N bytes (kd K), la tira no vale`
(DESBORDADO, ERROR I2C, el motor paró el flujo, sin datos, rechazado).

En el PC:

```
python analysis/campana_motor.py --puerto /dev/ttyUSB0 --flujo --kd 17 20 --bits 1000000 --90b
```

`kdNN_flujo.bin` solo se escribe si la tira llega entera: numeración de
tramas sin saltos, todos los CRC buenos, tantos bytes como se pidieron y la
línea `flujo fin ... ok`. `resumen.csv` lleva una columna `modo` (trozos o
flujo) y `f_ro2_MHz` = bits · 2^kd / tiempo sobre toda la tira (resolución
de 1 ms sobre minutos: mucho mejor que la del llenado de un trozo, pero la
referencia sigue siendo el display). `compara_modelo_campana.py` lee ese
resumen igual que el de trozos.

## 5. Qué se ha comprobado y con qué

| Qué | Con qué | Resultado |
|---|---|---|
| RTL: reglas de arranque (sin modo test, CFG_KD bajo, durante una siembra), exclusión con siembra y captura, CFG_KD congelado, **400 bytes seguidos iguales bit a bit a los que cruzan `bit_cdc`** (más de seis vueltas de una FIFO de 64), crédito, desbordamiento y parada, rearranque, las tres paradas | `tb_motor_top` paso 9, 21 comprobaciones; la referencia se apunta desde fuera del DUT | pasa; el banco entero, 85 comprobaciones |
| Propiedades en toda la simulación: nunca recogida de semilla con flujo activo, nunca arranque con el motor ocupado ni sin modo test; coberturas de arranque y desbordamiento | PSL en el mismo banco | 14/14 aserciones, 8/8 coberturas |
| Que el banco caza un fallo: mutante que saca bytes sin crédito (copia aparte) | el mismo banco | ver `results/tb_motor_top_mutante_flujo.log` |
| Modelo en el PC con las mismas reglas; orden `flujo` del verificador: 1000 bytes en 8 tramas y el tiempo que toca, desbordamiento con CFG_KD 6, sin modo test, bus caído, CFG_KD bajo | `test_verificador` paso 15, 15 comprobaciones | 0 fallos |
| Cadena completa hasta el fichero: 2500 bytes por divisor idénticos a los del modelo; una trama quitada del log descarta la tira y da rc = 1 | `run_host.py`, paso de campaña con `--flujo` | 0 fallos |
| Compila para el chip | ESP-IDF 5.3.2, esp32 | sin avisos del compilador |
| Área | Yosys + IHP SG13G2, misma herramienta antes y después | abajo |

**Lo que no está comprobado:** nada en placa. En particular, que la UART y
el I2C reales aguanten las tasas de §3 (los plazos del modelo son ticks, no
tiempo de CPU), y la inferencia de la FIFO en Vivado.

## 6. Área [SINTETIZADO, celdas sin rutar: cota inferior]

Yosys con el plugin de GHDL (OSS CAD Suite, Linux), biblioteca IHP SG13G2:

| Bloque | kGE | Biestables |
|---|---|---|
| `flujo_crudo` (256 bytes en biestables) | 23,67 | 2103 |
| `motor_top` con `G_FLUJO_BYTES = 256` | 116,63 | 10 270 |
| `motor_top` por defecto (sin FIFO), tras el cambio | 93,09 | 8164 |
| `motor_top` del commit anterior (383d7c0), misma herramienta | 93,20 | 8164 |

Con el generic a 0 el motor no cambia de forma medible (−0,1 kGE, dentro de
lo que se mueve `abc` de una pasada a otra; la variante con el AES de 11
ciclos se movió +0,3 en la misma tanda). La FIFO cuesta **23,5 kGE**.

Las cifras de la memoria (92,53 kGE) salen de otra pasada, por el camino
GHDL → Verilog → yowasp-yosys; con el plugin sale un 0,6 % más. En
`results/sintesis_sg13g2.csv` las filas antiguas se dejan como estaban y
solo se añaden `flujo_crudo` y `motor_top_flujo`, que son de esta pasada.

## 7. Decisiones

- **FIFO en el dominio de sistema y no en el del anillo.** Limita el flujo
  a CFG_KD ≥ `G_KD_MIN` (6), que no aprieta: el bus no llega ni de lejos a
  esa tasa. A cambio no hay cruce nuevo y los bits son los del DRBG.
- **Arrancar el flujo cuenta como orden** para `DIAG.rechazada`: sin eso el
  maestro tendría que deducir el rechazo de `activo`.
- **Al desbordarse se para.** Seguir metiendo bytes daría una tira con un
  hueco que el PC no puede ver.
- **La UART no se sube de 115 200**: es la única velocidad que fue fiable
  con el puente de las campañas del ESP32. Si hicieran falta divisores de
  12 o menos en continuo, el camino es guardar en RAM y enviar después.
