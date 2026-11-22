# Mapa de registros del motor (interfaz I2C)

**Dirección I2C:** 0x30 (7 bits). Protocolo de puntero de registro con
autoincremento, ver `rtl/io/i2c_slave.vhd`. Este documento es la
especificación que comparten `rtl/top/motor_top.vhd` y el firmware del
ESP32; si cambia uno, cambian los tres.

## Registros

| Dir | Nombre | Acceso | Contenido |
|---|---|---|---|
| 0x00 | ID | R | 0xA5, para saber que hay alguien al otro lado |
| 0x01 | VERSION | R | 0x04 (0x02: DIAG y test de arranque; 0x01 hasta el 27-10-2026). 0x03 anade `borrar_todo`, `DIAG.agotado`, las reglas de `capturar` y CFG_KD de reset 24. 0x04 (10-11-2026) añade la captura continua (FLUJO); lo demás no cambia, y un maestro escrito para la 0x03 funciona igual |
| 0x02 | STATUS | R | ver bits abajo |
| 0x03 | CONTROL | W | órdenes, ver bits abajo; se autolimpian |
| 0x04 | CFG_KD | R/W | divisor del anillo, K_D = 2^valor (periodos de ro2). **Desde el 19-11-2026 el rango es 0 a 26** (genérico `G_KD_MAX` de `motor_top`, que fija también el ancho del contador del ERO; antes 0 a 24, y 20 hasta el 08-10-2026). **Escribir un valor mayor que `G_KD_MAX` se ignora y levanta `DIAG.rechazada`.** En el integrado ro2 pasa por un preescalador ÷16 (`G_PRESC_RO2` = 4): el ERO cuenta 2^(valor − 4) flancos del reloj preescalado, que son los mismos 2^valor periodos de ro2; por debajo de 4 el divisor efectivo es 2^4. En la FPGA no hay preescalador. Con el anillo de IHP en ss/tt/ff de −40 a 125 °C a 1,2 V, el valor fijo que cubre todo el rango es 22 (peor caso ss a −40 °C); **con V_DD ± 10 % es 23** (peor caso ss, −40 °C, 1,08 V, donde 22 deja un 10 % de margen y no cubre el peor de quince chips con desapareamiento; `anillo_ihp.md` §4.2-4.3). **Tras el reset vale 25** (genérico `G_KD_RESET`; 24 hasta el 19-11-2026, 7 hasta la versión 0x02; en la Basys 3, 19): un maestro que no lo escriba siembra con la tasa mas lenta, nunca con una por debajo de la caracterizada. Cambiarlo solo con el motor libre y sin flujo activo |
| 0x05 | CFG_PAG | R/W | página del buffer de captura, 0 a 3 |
| 0x06 | RCT_MAX_L | R | racha máxima vista, byte bajo |
| 0x07 | RCT_MAX_H | R | racha máxima vista, byte alto |
| 0x08 | APT_MAX_L | R | proporción máxima vista, byte bajo |
| 0x09 | APT_MAX_H | R | proporción máxima vista, byte alto |
| 0x0A–0x0D | PETICIONES | R | contador de peticiones del DRBG (`reseed_counter`), 32 bits, byte bajo primero. **No da la vuelta**: en 2^32−1 el motor rechaza `generar` y `aleatorio` hasta resembrar (`DIAG.agotado`) |
| 0x0E | DIAG | R | ver bits abajo |
| 0x0F | FLUJO | R/W | captura continua de bits crudos, ver abajo. Bit 0 `activo`, bit 1 `desbordado` (solo lectura) |
| 0x10–0x1F | CLAVE | R | clave actual, 16 bytes. **Solo legible en modo test** |
| 0x20–0x2F | RETO | W | nonce de 16 bytes para el reto-respuesta |
| 0x30–0x3F | ETIQUETA | R | CMAC(RETO) con la clave actual, 16 bytes. Se lee como ceros mientras `etiqueta_lista` = 0 (reto nuevo a medias, tras `generar` o tras `borrar_todo`) |
| 0x40–0x5F | ALEATORIO | R | 32 bytes de la última orden `aleatorio`: una generación del DRBG **independiente de la clave**. Nunca contiene la clave |
| 0x60 | FLUJO_N | R | bytes disponibles en la FIFO del flujo, con tope 31. Leerlo fija el crédito de la transacción. **Solo en modo test** |
| 0x61–0x7F | FLUJO_DATO | R | cada lectura con crédito saca un byte de la FIFO; sin crédito devuelve 0x00 y no saca nada. **Solo en modo test** |
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
| 1 | rechazada | la última orden escrita en CONTROL se ignoró (motor ocupado, alarma, sin arrancar, CFG_KD bajo, sin sembrar, sin clave, contador agotado, captura o flujo en curso o sin modo test) o, si era una siembra, se abortó. Se baja con la siguiente orden aceptada. `borrar_alarmas` no la toca. Arrancar el flujo (escribir 1 en FLUJO) cuenta como una orden: la sube si se rechaza y la baja si se acepta |
| 2 | agotado | el contador de peticiones está en su tope (2^32−1): `generar` y `aleatorio` se rechazan hasta `resembrar` o `sembrar` (SP 800-90A, `reseed_interval`) |
| 3 | solo_fuente | el motor se sintetizó sin criptografía (genérico `G_SOLO_FUENTE`, la variante de la Basys 2; ver abajo). Constante. Hasta el 14-11-2026 era un bit reservado que se leía 0, y en el motor entero sigue leyéndose 0, así que un maestro de la 0x04 no se confunde |

## Tests de salud y siembra

Los tests de salud (SP 800-90B §4.4) vigilan los bits crudos de forma
continua. Tres reglas, impuestas por hardware desde el 27-10-2026:

1. **Test de arranque (SP 800-90B §4.3).** Tras el reset, y tras cada
   `borrar_alarmas`, el motor no siembra hasta que se cierra sin alarma una
   ventana completa del APT. Borrar las alarmas reinicia la ventana, así que
   esa ventana solo contiene muestras posteriores al borrado. El maestro
   sondea `DIAG.arrancado` antes de sembrar. En el integrado (`CFG_KD` 25,
   ro2 de 13 etapas a 0,66-1,46 ns por periodo [SIMULADO, ff 125 °C a ss
   −40 °C, `results/anillo_ihp_periodo_*`]) el bit sale cada 22-49 ms
   (20-45 bit/s) y la ventana de 1024 tarda 23-50 s; en la Basys 3
   (`CFG_KD` 19, ro2 a 207 MHz [MEDIDO]) unos 2,6 s.
2. **La semilla se valida entera.** El APT solo da veredicto al cerrar su
   ventana de 1024 muestras y la semilla son 512 bits, así que antes la
   primera semilla entraba en el DRBG sin que el APT la hubiera evaluado.
   Ahora, tras recoger los 512 bits, el motor espera a que se cierre la
   ventana que contiene el último y solo instancia el DRBG si se cierra sin
   alarma. Una alarma, o un `borrar_alarmas`, durante la recogida o la
   espera aborta la siembra: el DRBG queda como estaba y `DIAG.rechazada`
   sube. Una siembra tarda como mucho 512 + 1024 bits: 34-75 s en el
   integrado con `CFG_KD` 25 [ESTIMADO con los periodos de arriba], ~4 s en
   la Basys 3 a `CFG_KD` 19.
3. **Alarma bloquea la salida**, ver STATUS arriba.

**Cortes (desde el 16-11-2026):** RCT C = 51 y APT C = 766 (W = 1024),
calculados para una min-entropía de diseño H = 0,60 y α = 2⁻³⁰
(`analysis/cortes_salud.py`), y semilla de 512 bits. El biestable real de
sg13g2 sesga el bit hasta P(1) = 0,372 a 125 °C con desapareamiento
[SIMULADO, `analysis/biestable_ihp.py`]: con H 0,80, cinco de ocho chips
quedaban por debajo. Del 15-11 al 16-11, H = 0,80 (39 y 683) con semilla
de 384 bits; antes, H = 0,98 y α = 2⁻²⁰ (22 y 596), con una falsa alarma
del RCT cada ~8 min en la Basys 2 a CFG_KD 14. Con 766, lo peor que deja
pasar el APT (p ≈ 0,748, H ≈ 0,419) aún da 214 bits de entropía en los 512
de la semilla, por encima de los 192 que pide un CTR_DRBG AES-128 (SP
800-90A Rev. 1: §8.6.3 y tabla 3, entropía de entrada ≥ 128; §8.6.7, nonce
≥ 64, o 192 juntos si salen de la misma fuente a la vez, como aquí). Por
separado no: el campo de 384 lleva ~161 (≥ 128) pero el de 128 solo ~54
(< 64), así que el diseño se apoya en la regla conjunta de §8.6.7. Con 384
bits y H 0,60 tampoco se cumplía esa (161 < 192): por eso la semilla crece. Son genéricos
de `motor_top` (`G_RCT_C`, `G_APT_C`). Razonamiento en `docs/basys2.md`,
"Decisión del 16-11-2026".

**Rearme:** con los anillos y los tests corriendo siempre, una fuente sana
acaba dando alguna falsa alarma en la vida del equipo, y cada alarma
bloquea el motor hasta `borrar_alarmas`. El motor no se rearma solo. La
política va en el maestro (`motor_rearmar()` de
`firmware/componentes/motor_i2c`): borrar las alarmas, esperar el test de
arranque y volver a sembrar (resembrar si el DRBG tenía estado), como
mucho 3 veces en 24 h; a la cuarta, fallo permanente hasta reiniciar el
ESP32. Con estos cortes y bits iid [ESTIMADO, `cortes_salud.py` y
`docs/basys2.md`], a 8,7 kbit/s (Basys 2, `kd 14`): con bits ideales,
ninguna en la vida del equipo; con el peor chip simulado (P(1) 0,372), ~8
al año del RCT; con un chip justo en H = 0,60, ~89 al año (0,24 al día). Al
ritmo del integrado con `CFG_KD` 25 y ro2 de 13 etapas (≤ 45 bit/s; hasta el
19-11, 2²³ con 5 etapas, ≤ 0,41 kbit/s), ≤ 0,05 y ≤ 0,5 al año (las tasas
escalan con el caudal). El peor chip de 0,372 es del biestable con ro1 de 5
etapas; con 11 etapas el Monte Carlo (en curso, `docs/decisiones_pendientes.md`)
da P(1) ≥ 0,41. Tres en un día no son azar.

## CONTROL (0x03)

| Bit | Orden | Qué hace |
|---|---|---|
| 0 | sembrar | recoge 512 bits crudos del anillo (los campos de entropía, 384, y nonce, 128, de la entrada del DRBG; la entropía que llevan es H × 512, ver "Cortes" arriba), espera a que los tests de salud los hayan evaluado enteros y **instancia** el DRBG desde cero |
| 1 | generar | pide 256 bits al DRBG; los 128 primeros pasan a ser la CLAVE, los otros 128 se descartan; recarga el autenticador. **No deja nada legible** |
| 2 | autenticar | calcula ETIQUETA = CMAC_CLAVE(RETO) |
| 3 | borrar_alarmas | baja las alarmas de salud |
| 4 | capturar | llena el buffer de captura con un trozo de bits crudos. **Solo en modo test** (sin él el buffer no se lee), con el motor libre, sin otra captura en marcha y sin flujo activo. Mientras hay una captura en curso se rechazan `sembrar` y `resembrar`, y al revés: el buffer recoge los mismos bits crudos que la semilla, y hasta la versión 0x02 una captura lanzada durante una siembra dejaba la semilla legible en modo test |
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

## Captura continua: FLUJO (0x0F), FLUJO_N (0x60) y FLUJO_DATO (0x61–0x7F)

Desde la versión 0x04. `capturar` da trozos de 4096 bits sin relación entre
sí; SP 800-90B pide 10⁶ bits **consecutivos**. El flujo es una FIFO de bytes
en el dominio de sistema (`rtl/trng/flujo_crudo.vhd`), alimentada por los
mismos bits que ven los tests de salud y la recogida de semilla (después de
`bit_cdc`), que el maestro vacía por I2C mientras se llena. El primer bit
que llega va al bit alto del primer byte. Razonamiento, tasas y cómo se usa
en `docs/captura_continua.md`.

| Bit de FLUJO | Nombre | Significado |
|---|---|---|
| 0 | activo | escribir 1 vacía la FIFO, baja `desbordado` y arranca; escribir 0 para y vacía. Se lee el estado |
| 1 | desbordado | llegó un byte con la FIFO llena. El flujo **se para solo**; lo que quedaba dentro sigue siendo consecutivo, pero la tira acaba ahí. Solo lectura |

- **Arrancar** exige modo test, motor libre, ninguna captura en curso y
  `CFG_KD ≥ G_KD_MIN` (los bits pasan por `bit_cdc`). Si no, la escritura se
  ignora y sube `DIAG.rechazada`.
- **Con el flujo activo** se rechazan `sembrar`, `resembrar` y `capturar`, y
  se ignoran las escrituras a `CFG_KD`: el flujo saca los mismos bits crudos
  que la semilla, y una tira con dos divisores no sirve. `generar`,
  `aleatorio` y `autenticar` se atienden.
- **Se para** al escribir 0, al desbordarse, al quitar modo test y con
  `borrar_todo`; en los tres últimos casos sin que el maestro lo pida, así
  que el maestro mira `activo` y `desbordado` cuando la FIFO le llega vacía.
- **Lectura, en una transacción:** puntero a 0x60 y 32 bytes. El primero es
  `n` (0 a 31) y fija el crédito; los `n` siguientes son datos y el resto
  ceros. El crédito evita perder un byte que entre en la FIFO a mitad de la
  lectura. Una lectura de FLUJO_DATO sin haber leído antes FLUJO_N en la
  misma transacción no saca nada.
- La FIFO tiene `G_FLUJO_BYTES` bytes (genérico de `motor_top`): **256 en la
  FPGA y 0 por defecto**, que la quita. Es instrumentación de
  caracterización, como `ro_mon`, y no entra en el área del integrado. Sin
  ella FLUJO se lee 0 y arrancar se rechaza: así lo detecta el maestro.

## Variantes sintetizables con el mismo mapa

Dos genéricos de `motor_top` quitan bloques sin cambiar ni el mapa ni
VERSION (desde el 14-11-2026); otro cambia el muestreo de la fuente (desde
el 15-11-2026). Con sus valores por defecto el motor es el
de siempre: `synth/equivalencia.sh` comprueba que la lógica es idéntica
bit a bit a la de antes.

- **`G_CAPTURA_BYTES`** (512 por defecto): bytes del buffer de captura por
  trozos. Con 0 no hay buffer, `capturar` se rechaza (`DIAG.rechazada`),
  `captura_llena` se queda a 0 y CAPTURA se lee como ceros. El flujo
  continuo cubre lo mismo con bits consecutivos.
- **`G_SOLO_FUENTE`** (false por defecto): sin DRBG, CMAC ni AES.
  `DIAG.solo_fuente` = 1; `sembrar`, `resembrar`, `generar`, `aleatorio` y
  `autenticar` se rechazan (`DIAG.rechazada`); `sembrado`, `clave_valida` y
  `etiqueta_lista` se quedan a 0; CLAVE, ETIQUETA, ALEATORIO y PETICIONES se
  leen como ceros; `borrar_todo` se acepta y acaba en un ciclo. Fuente,
  tests de salud (con el test de arranque), CFG_KD, FLUJO y el resto del
  mapa funcionan igual. Es la variante de la Basys 2 (XC3S100E, 1 920 LUT4),
  donde la criptografía no cabe (`docs/basys2.md`). Banco:
  `tb_motor_solo_fuente`.

- **`G_MUESTREO_LIBRE`** (true por defecto desde el 15-11-2026): el
  biestable que muestrea ro1 lo toma en cada flanco de ro2 y el divisor
  solo marca qué muestra vale, en vez de tomarlo con habilitación. Mismos
  bits en simulación (`tb_ero_core`); en la Basys 2, con habilitación el
  bit salía correlado con el anterior (ρ₁ ≈ 0,005, z hasta 13) y sin ella
  no (z ≤ 1, dos implementaciones). `basys2_top` lo deja en false para
  seguir siendo comparable con sus campañas. Con `G_MUESTREO_LIBRE=false`
  y los cortes antiguos (`G_RCT_C=22`, `G_APT_C=596`) el motor es
  equivalente al anterior (`GEN_ACT` de `synth/equivalencia.sh`).

Un maestro que encuentre `DIAG.solo_fuente` = 1 no intenta sembrar: usa el
motor como fuente de bits crudos (flujo, en modo test) y tests de salud.

## Secuencia típica del ESP32

1. Leer ID, comprobar 0xA5. Leer VERSION, comprobar que es 0x03 o mayor.
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

El pin `modo_test` habilita la lectura de CLAVE, de CAPTURA y del flujo. En la FPGA
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
   mínimo, fijado por el genérico `G_KD_MIN` de `motor_top`: **25 por
   defecto desde el 19-11-2026** (el divisor caracterizado del integrado con
   ro1 de 11 etapas; antes 6, solo el cruce de dominio) y **19 en la Basys
   3** (el que pide el jitter térmico medido, `docs/basys3.md`). El mismo
   mínimo vale para arrancar el flujo. Por qué tan alto: en placa los tests
   de salud no saltan ni con H 0,19 (`kd 8`, bits que alternan), así que el
   mínimo es la única protección frente a un maestro que escriba un divisor
   bajo. Para caracterizar se compila una variante con el mínimo bajo.
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
al menos 8 ciclos de sistema (80 ns a 100 MHz), es decir 2^CFG_KD
periodos de ro2 ≥ 80 ns: con ro2 de 13 etapas (≥ 0,66 ns) basta CFG_KD ≥ 7,
y con el preescalador ÷16 (`G_PRESC_RO2` = 4) el dominio del anillo corre a
ro2/16 y el ERO cuenta 2^(CFG_KD−4) de esos periodos. `G_KD_MIN` (25 en el
integrado, 19 en la Basys 3) queda muy por encima, así que no aprieta
(hasta el 19-11 el texto suponía ro2 a ~700 MHz y pedía CFG_KD ≥ 6). La captura de bits crudos para medir
jitter no pasa por esta vía: `trng_capture` escribe en el dominio del
anillo y admite cualquier K_D, incluido 1.
