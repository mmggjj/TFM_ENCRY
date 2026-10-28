# Mapa de registros del motor (interfaz I2C)

**Dirección I2C:** 0x30 (7 bits). Protocolo de puntero de registro con
autoincremento, ver `rtl/io/i2c_slave.vhd`. Este documento es la
especificación que comparten `rtl/top/motor_top.vhd` y el firmware del
ESP32; si cambia uno, cambian los tres.

## Registros

| Dir | Nombre | Acceso | Contenido |
|---|---|---|---|
| 0x00 | ID | R | 0xA5, para saber que hay alguien al otro lado |
| 0x01 | VERSION | R | 0x03 (0x02: DIAG y test de arranque; 0x01 hasta el 27-10-2026). 0x03 anade `borrar_todo`, `DIAG.agotado`, las reglas de `capturar` y CFG_KD de reset 24 |
| 0x02 | STATUS | R | ver bits abajo |
| 0x03 | CONTROL | W | órdenes, ver bits abajo; se autolimpian |
| 0x04 | CFG_KD | R/W | divisor del anillo, K_D = 2^valor. Rango efectivo 0 a 24 (el contador del ERO tiene 24 bits desde el 08-10-2026; antes 20, que con el anillo de IHP solo dejaba un 11 % de margen, ver `anillo_ihp.md`; valores mayores equivalen a 24). **Tras el reset vale 24** (generico `G_KD_RESET`; hasta la version 0x02 era 7): un maestro que no lo escriba siembra con la tasa mas lenta, nunca con una por debajo de la caracterizada. Cambiarlo solo con el motor libre |
| 0x05 | CFG_PAG | R/W | página del buffer de captura, 0 a 3 |
| 0x06 | RCT_MAX_L | R | racha máxima vista, byte bajo |
| 0x07 | RCT_MAX_H | R | racha máxima vista, byte alto |
| 0x08 | APT_MAX_L | R | proporción máxima vista, byte bajo |
| 0x09 | APT_MAX_H | R | proporción máxima vista, byte alto |
| 0x0A–0x0D | PETICIONES | R | contador de peticiones del DRBG (`reseed_counter`), 32 bits, byte bajo primero. **No da la vuelta**: en 2^32−1 el motor rechaza `generar` y `aleatorio` hasta resembrar (`DIAG.agotado`) |
| 0x0E | DIAG | R | ver bits abajo |
| 0x10–0x1F | CLAVE | R | clave actual, 16 bytes. **Solo legible en modo test** |
| 0x20–0x2F | RETO | W | nonce de 16 bytes para el reto-respuesta |
| 0x30–0x3F | ETIQUETA | R | CMAC(RETO) con la clave actual, 16 bytes. Se lee como ceros mientras `etiqueta_lista` = 0 (reto nuevo a medias, tras `generar` o tras `borrar_todo`) |
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

Con alarma levantada **no sale nada del motor**: `sembrar`, `resembrar`,
`generar` y `aleatorio` se rechazan hasta que se borre. `autenticar` sí se
atiende, porque usa la clave ya generada y no consume entropía. Hasta el
27-10-2026 solo se rechazaban `sembrar` y `resembrar`, y con la alarma
puesta seguían saliendo clave y ALEATORIO.

## DIAG (0x0E)

| Bit | Nombre | Significado |
|---|---|---|
| 0 | arrancado | el test de arranque ha pasado: una ventana completa del APT (1024 muestras) sin alarma desde el reset o desde el último `borrar_alarmas` |
| 1 | rechazada | la última orden escrita en CONTROL se ignoró (motor ocupado, alarma, sin arrancar, CFG_KD bajo, sin sembrar, sin clave, contador agotado, captura en curso o sin modo test) o, si era una siembra, se abortó. Se baja con la siguiente orden aceptada. `borrar_alarmas` no la toca |
| 2 | agotado | el contador de peticiones está en su tope (2^32−1): `generar` y `aleatorio` se rechazan hasta `resembrar` o `sembrar` (SP 800-90A, `reseed_interval`) |

## Tests de salud y siembra

Los tests de salud (SP 800-90B §4.4) vigilan los bits crudos de forma
continua. Tres reglas, impuestas por hardware desde el 27-10-2026:

1. **Test de arranque (SP 800-90B §4.3).** Tras el reset, y tras cada
   `borrar_alarmas`, el motor no siembra hasta que se cierra sin alarma una
   ventana completa del APT. Borrar las alarmas reinicia la ventana, así que
   esa ventana solo contiene muestras posteriores al borrado. El maestro
   sondea `DIAG.arrancado` antes de sembrar; con K_D = 2^24 y el anillo a
   ~700 MHz son unos 25 s.
2. **La semilla se valida entera.** El APT solo da veredicto al cerrar su
   ventana de 1024 muestras y la semilla son 384 bits, así que antes la
   primera semilla entraba en el DRBG sin que el APT la hubiera evaluado.
   Ahora, tras recoger los 384 bits, el motor espera a que se cierre la
   ventana que contiene el último y solo instancia el DRBG si se cierra sin
   alarma. Una alarma, o un `borrar_alarmas`, durante la recogida o la
   espera aborta la siembra: el DRBG queda como estaba y `DIAG.rechazada`
   sube. Una siembra tarda como mucho 384 + 1024 bits.
3. **Alarma bloquea la salida**, ver STATUS arriba.

## CONTROL (0x03)

| Bit | Orden | Qué hace |
|---|---|---|
| 0 | sembrar | recoge 384 bits crudos del anillo (256 de entropía + 128 de nonce), espera a que los tests de salud los hayan evaluado enteros y **instancia** el DRBG desde cero |
| 1 | generar | pide 256 bits al DRBG; los 128 primeros pasan a ser la CLAVE, los otros 128 se descartan; recarga el autenticador. **No deja nada legible** |
| 2 | autenticar | calcula ETIQUETA = CMAC_CLAVE(RETO) |
| 3 | borrar_alarmas | baja las alarmas de salud |
| 4 | capturar | llena el buffer de captura con un trozo de bits crudos. **Solo en modo test** (sin él el buffer no se lee), con el motor libre y sin otra captura en marcha. Mientras hay una captura en curso se rechazan `sembrar` y `resembrar`, y al revés: el buffer recoge los mismos bits crudos que la semilla, y hasta la versión 0x02 una captura lanzada durante una siembra dejaba la semilla legible en modo test |
| 5 | resembrar | como sembrar pero **sobre** el estado actual, sin borrarlo |
| 6 | aleatorio | pide otros 256 bits al DRBG y los deja en ALEATORIO. Generación independiente: el DRBG ya actualizó su estado tras `generar`, así que no hay relación calculable con la clave |
| 7 | borrar_todo | zeroización: CLAVE, el estado del DRBG (clave, V, contador y todos sus registros intermedios, incluido el núcleo AES), RETO, ALEATORIO, ETIQUETA y la semilla recogida a cero, y la clave nula cargada en el autenticador (que también borra su encadenamiento). Se atiende siempre que el motor esté libre, también con alarma. Después hay que `sembrar` (no `resembrar`: no hay estado) y `generar`. El buffer de captura no se borra: por la regla de `capturar`, nunca contiene bits de una semilla |

**Historial:** hasta el 15-09-2026 `generar` dejaba sus 256 bits en
ALEATORIO, legible sin modo test, y los 128 primeros eran la clave: **el
registro filtraba la clave**. Se detectó en la revisión previa al
traspaso y se separó en dos órdenes. El banco `tb_motor_top` comprueba
ahora que ALEATORIO no contiene la clave en ninguna de sus mitades.

Una orden por escritura: si llegan varios bits a la vez se atiende el de mayor prioridad, en este orden: `borrar_todo`, `sembrar`/`resembrar` (si van los dos, `resembrar`), `generar`, `aleatorio`, `autenticar`, `capturar`. `borrar_alarmas` va aparte y se atiende siempre, junto con la orden que acompañe; pero **no combinarlo con `sembrar`/`resembrar` en la misma escritura**: la siembra se acepta y se aborta en el ciclo siguiente, porque borrar las alarmas reinicia la ventana del test de arranque (queda `rechazada = 1` y hay que repetir el test).

Las órdenes largas (sembrar, generar) no estiran el reloj I2C: el maestro
las lanza, sondea `ocupado` en STATUS y recoge el resultado después. Es
como trabajan los elementos seguros comerciales.

## Secuencia típica del ESP32

1. Leer ID, comprobar 0xA5. Leer VERSION, comprobar 0x02.
2. Escribir CFG_KD con el divisor decidido en la caracterización.
3. Sondear DIAG hasta `arrancado = 1`. CONTROL ← sembrar. Sondear STATUS
   hasta `ocupado = 0`. Comprobar `DIAG.rechazada = 0`, `sembrado = 1` y
   sin alarmas.
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

## Obligaciones del maestro y lo que el hardware impone

Tres reglas. Dos las impone ya el hardware desde el 19-09-2026, porque eran
baratas de imponer y su incumplimiento era silencioso; la tercera sigue
siendo del maestro.

1. **Suelo de `CFG_KD`, impuesto por hardware.** La vía que lleva los bits
   del dominio del anillo al de sistema necesita `CFG_KD >= 6` (K_D >= 64).
   Por debajo, el cruce pierde bits **en silencio** y los que pasan tienen
   muy poco jitter acumulado, o sea muy poca entropía, y los tests de salud
   no lo detectan: el RCT busca fuente pegada y el APT busca sesgo, no
   correlación. Por eso `sembrar` y `resembrar` **se rechazan** (la orden se
   ignora y `ocupado` no llega a subir) si `CFG_KD` está por debajo del
   mínimo, fijado por el genérico `G_KD_MIN` de `motor_top` (6 por defecto).
   El maestro comprueba tras cada orden `DIAG.rechazada`, que distingue el
   rechazo de una orden que acabó enseguida (antes había que deducirlo de
   `sembrado`, que se queda a 1 de la siembra anterior). El banco
   `tb_motor_top` (paso 2a) comprueba el rechazo.
2. **Política de resembrado, del maestro, con tope en el hardware.**
   `PETICIONES` (0x0A–0x0D) es el `reseed_counter` de SP 800-90A: vale 1
   tras sembrar y sube en cada `generar` o `aleatorio`. Desde la versión
   0x03 el contador no da la vuelta y en 2^32−1 el motor rechaza `generar` y
   `aleatorio` (`DIAG.agotado`) hasta resembrar; es el tope que cabe en 32
   bits, por debajo del 2^48 de la norma. Sigue siendo el maestro quien
   decide cuándo resembrar antes de llegar ahí.
3. **`CFG_KD` solo con el motor libre, impuesto por hardware.** Una escritura
   de `CFG_KD` con una orden en curso **se ignora**: cambiar la tasa de
   muestreo a mitad de un sembrado invalidaría el modelo estocástico de esa
   semilla. `CFG_PAG` sí se atiende siempre, porque solo afecta a la lectura
   del buffer de captura. El banco (paso 2c) comprueba que la escritura se
   ignora.

## Restricción de tasa

La vía que alimenta los tests de salud y la recogida de semilla cruza del
dominio del anillo al de sistema bit a bit, y necesita que cada bit dure
al menos 8 ciclos de sistema. Con reloj de 100 MHz y anillo de muestreo a
~700 MHz, eso exige K_D ≥ 64 (CFG_KD ≥ 6). En modo generador K_D es
mucho mayor, así que no aprieta. La captura de bits crudos para medir
jitter no pasa por esta vía: `trng_capture` escribe en el dominio del
anillo y admite cualquier K_D, incluido 1.
