# Mapa de registros del motor (interfaz I2C)

**Dirección I2C:** 0x30 (7 bits). Protocolo de puntero de registro con
autoincremento, ver `rtl/io/i2c_slave.vhd`. Este documento es la
especificación que comparten `rtl/top/motor_top.vhd` y el firmware del
ESP32; si cambia uno, cambian los tres.

## Registros

| Dir | Nombre | Acceso | Contenido |
|---|---|---|---|
| 0x00 | ID | R | 0xA5, para saber que hay alguien al otro lado |
| 0x01 | VERSION | R | 0x01 |
| 0x02 | STATUS | R | ver bits abajo |
| 0x03 | CONTROL | W | órdenes, ver bits abajo; se autolimpian |
| 0x04 | CFG_KD | R/W | divisor del anillo, K_D = 2^valor. Rango efectivo 0 a 20 (el contador del ERO tiene 20 bits; valores mayores equivalen a 20). Cambiarlo solo con el motor libre |
| 0x05 | CFG_PAG | R/W | página del buffer de captura, 0 a 3 |
| 0x06 | RCT_MAX_L | R | racha máxima vista, byte bajo |
| 0x07 | RCT_MAX_H | R | racha máxima vista, byte alto |
| 0x08 | APT_MAX_L | R | proporción máxima vista, byte bajo |
| 0x09 | APT_MAX_H | R | proporción máxima vista, byte alto |
| 0x0A–0x0D | PETICIONES | R | contador de peticiones del DRBG, 32 bits, byte bajo primero |
| 0x10–0x1F | CLAVE | R | clave actual, 16 bytes. **Solo legible en modo test** |
| 0x20–0x2F | RETO | W | nonce de 16 bytes para el reto-respuesta |
| 0x30–0x3F | ETIQUETA | R | CMAC(RETO) con la clave actual, 16 bytes |
| 0x40–0x5F | ALEATORIO | R | 32 bytes de la última orden `aleatorio`: una generación del DRBG **independiente de la clave**. Nunca contiene la clave |
| 0x80–0xFF | CAPTURA | R | 128 bytes de la página CFG_PAG del buffer de bits crudos. **Solo en modo test** |

Lecturas de direcciones no definidas devuelven 0x00; escrituras a
direcciones de solo lectura se ignoran.

## STATUS (0x02)

| Bit | Nombre | Significado |
|---|---|---|
| 0 | sembrado | el DRBG tiene estado válido |
| 1 | ocupado | hay una orden en curso; no mandar otra |
| 2 | alarma_rct | test de repetición disparado (fuente pegada) |
| 3 | alarma_apt | test de proporción disparado (fuente sesgada) |
| 4 | clave_valida | hay clave cargada en el autenticador |
| 5 | captura_llena | el buffer de captura tiene un trozo listo |
| 6 | etiqueta_lista | ETIQUETA corresponde al RETO actual |
| 7 | modo_test | el pin de test está activo |

Con alarma levantada, `sembrar` y `resembrar` se rechazan hasta que se
borre: nunca se siembra con una fuente que se sabe degradada.

## CONTROL (0x03)

| Bit | Orden | Qué hace |
|---|---|---|
| 0 | sembrar | recoge 384 bits crudos del anillo (256 de entropía + 128 de nonce), pasa los tests de salud y **instancia** el DRBG desde cero |
| 1 | generar | pide 256 bits al DRBG; los 128 primeros pasan a ser la CLAVE, los otros 128 se descartan; recarga el autenticador. **No deja nada legible** |
| 2 | autenticar | calcula ETIQUETA = CMAC_CLAVE(RETO) |
| 3 | borrar_alarmas | baja las alarmas de salud |
| 4 | capturar | llena el buffer de captura con un trozo de bits crudos |
| 5 | resembrar | como sembrar pero **sobre** el estado actual, sin borrarlo |
| 6 | aleatorio | pide otros 256 bits al DRBG y los deja en ALEATORIO. Generación independiente: el DRBG ya actualizó su estado tras `generar`, así que no hay relación calculable con la clave |

**Historial:** hasta el 15-09-2026 `generar` dejaba sus 256 bits en
ALEATORIO, legible sin modo test, y los 128 primeros eran la clave: **el
registro filtraba la clave**. Se detectó en la revisión previa al
traspaso y se separó en dos órdenes. El banco `tb_motor_top` comprueba
ahora que ALEATORIO no contiene la clave en ninguna de sus mitades.

Las órdenes largas (sembrar, generar) no estiran el reloj I2C: el maestro
las lanza, sondea `ocupado` en STATUS y recoge el resultado después. Es
como trabajan los elementos seguros comerciales.

## Secuencia típica del ESP32

1. Leer ID, comprobar 0xA5.
2. Escribir CFG_KD con el divisor decidido en la caracterización.
3. CONTROL ← sembrar. Sondear STATUS hasta `ocupado = 0`. Comprobar
   `sembrado = 1` y sin alarmas.
4. CONTROL ← generar. Sondear. Ahora hay clave.
5. Provisión (solo en banco, modo test): leer CLAVE y guardarla en el
   ESP32.
6. Reto-respuesta: escribir RETO con un nonce, CONTROL ← autenticar,
   sondear, leer ETIQUETA y compararla con el CMAC que calcula mbedtls
   con la clave provisionada.
7. Aleatorio para el host: CONTROL ← aleatorio, sondear, leer ALEATORIO
   (32 bytes). Repetir cuantas veces haga falta; cada orden es una
   generación nueva.

## Modo test

El pin `modo_test` habilita la lectura de CLAVE y de CAPTURA. En la FPGA
es un interruptor de la placa. En un circuito integrado sería un fusible
que se quema en producción, porque exponer la clave o la entropía cruda
es un agujero. En la memoria se describe así.

## Obligaciones del maestro que el hardware NO impone

Tres reglas que el motor documenta pero no obliga. Quien escriba el driver
tiene que cumplirlas, porque nada le va a avisar si no lo hace.

1. **Suelo de `CFG_KD`.** La vía que lleva los bits del dominio del anillo al
   de sistema necesita `CFG_KD >= 6` (K_D >= 64). Por debajo, el cruce pierde
   bits **en silencio** y los que pasan tienen muy poco jitter acumulado, o
   sea muy poca entropía. El registro admite hoy cualquier valor de 0 a 31.
   Sembrar con `CFG_KD < 6` produce claves de calidad no garantizada y los
   tests de salud no lo detectan de forma fiable: el RCT busca fuente pegada
   y el APT busca sesgo, no correlación.
2. **Política de resembrado.** `PETICIONES` (0x0A–0x0D) es el `reseed_counter`
   de SP 800-90A: vale 1 tras sembrar y sube en cada `generar`. El motor
   **no** lo compara con ningún umbral ni rechaza generar por contador. Es el
   maestro quien debe vigilarlo y lanzar `resembrar` muy por debajo del
   límite de 2^48 de la norma.
3. **Cambiar la configuración solo con el motor libre.** `CFG_KD` y `CFG_PAG`
   se atienden aunque haya una orden en curso. Cambiar `CFG_KD` a mitad de un
   sembrado altera la tasa de muestreo a medio camino, y entonces el modelo
   estocástico que justifica la min-entropía **no aplica a esa semilla**.
   Sondear `ocupado` antes de escribirlos.

## Restricción de tasa

La vía que alimenta los tests de salud y la recogida de semilla cruza del
dominio del anillo al de sistema bit a bit, y necesita que cada bit dure
al menos 8 ciclos de sistema. Con reloj de 100 MHz y anillo de muestreo a
~700 MHz, eso exige K_D ≥ 64 (CFG_KD ≥ 6). En modo generador K_D es
mucho mayor, así que no aprieta. La captura de bits crudos para medir
jitter no pasa por esta vía: `trng_capture` escribe en el dominio del
anillo y admite cualquier K_D, incluido 1.
