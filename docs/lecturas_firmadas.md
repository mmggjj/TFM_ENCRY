# Lecturas firmadas: el motor en un producto con ESP32-C3

**Estado:** 27-10-2026. Diseño y código hechos y probados en el PC contra el
motor simulado; sin placa. Firmware en `firmware/medidor`, acceso al motor en
`firmware/componentes/motor_i2c`, verificación en el PC en
`analysis/verifica_lecturas.py`, banco en `firmware/host_check`.

## 1. Qué se demuestra

Hasta ahora el ESP32 era el *juez* del motor (el verificador): provisiona la
clave en modo test y comprueba el reto-respuesta. Esto es lo otro: el motor
**usado** por un producto. El producto es un medidor de energía genérico con
un ESP32-C3, que es el chip de los equipos pequeños con Wi-Fi, y el motor
cuelga del mismo bus I2C que sus periféricos (dirección 0x30).

Dos usos, los dos con la entropía del motor:

1. **Clave del equipo generada en el equipo.** Una clave ECDSA P-256 que nace
   de bloques `ALEATORIO` del motor y no sale nunca del chip. Lo que sale es
   la clave pública (trama `P`) o una **petición de certificado** (CSR,
   PKCS#10) firmada con ella, que es lo que un equipo mandaría a la CA del
   fabricante para obtener su certificado TLS sin que nadie, ni el
   fabricante, tenga la privada.
2. **Lecturas firmadas.** Cada lectura de energía (identificador del equipo,
   secuencia, instante, energía acumulada, potencia) sale con su firma ECDSA
   (trama `L`). Quien la reciba comprueba integridad y origen con la pública,
   sin fiarse del transporte (TLS) ni del almacenamiento intermedio (las
   lecturas guardadas sin conexión y reenviadas después). Para datos de
   facturación es el argumento que importa.

El motor solo interviene en la **generación de la clave**. La firma de cada
lectura no le pide nada, ver §3.

## 2. Por qué así

**ECDSA P-256 y no el CMAC del motor.** El CMAC es simétrico: quien verifica
tiene la misma clave que quien firma, así que la nube tendría la clave de
cada equipo y una firma no prueba quién la hizo. Con ECDSA la nube solo tiene
públicas. P-256 con SHA-256 es lo que entienden las CA, los certificados
X.509 y `cryptography`/OpenSSL en el PC.

**Cuánta seguridad tiene la clave.** La fuerza de una clave la acota lo que
la generó. El DRBG del motor es CTR_DRBG con AES-128: 128 bits de seguridad
(SP 800-90A, tabla 2). P-256 ofrece 128 bits. Una curva mayor con esta
semilla no ganaría nada, y P-256 es la que más barata sale en el C3, que
hace la curva por software (el ESP32-C3 no tiene acelerador ECC; el C6 y el
H2 sí). mbedtls pide al `f_rng` 32 bytes y algo más para el cegado: en el
banco salen **2 bloques** del motor por clave.

**ECDSA determinista (RFC 6979).** ECDSA normal necesita un nonce `k`
aleatorio y secreto en **cada firma**; si `k` se repite o se predice, la
clave privada se calcula a partir de dos firmas (PlayStation 3, 2010; las
carteras de Bitcoin en Android, 2013). Con RFC 6979, `k` se deriva de la
clave y del mensaje con HMAC-DRBG: dos firmas del mismo mensaje son
idénticas (el banco lo comprueba) y la calidad del generador en el momento
de firmar no puede filtrar la clave. Por eso la firma no depende del motor:
si el motor está en alarma, el medidor sigue firmando con la clave que
tiene, y lo que no puede hacer es generar una nueva. El `f_rng` que reciben
las funciones de firma solo se usa para el **cegado** contra canales
laterales y no cambia el valor de la firma; ahí vale `esp_fill_random`.
`lectura.c` no compila sin `MBEDTLS_ECDSA_DETERMINISTIC`.

**Falla cerrado.** `motor_rng()` (componente `motor_i2c`) es el `f_rng` de
mbedtls para generar la clave: cada 32 bytes son una orden `aleatorio` y
una lectura de `ALEATORIO`. Si el motor rechaza la orden (sin sembrar, en
alarma, sin pasar el test de arranque) o el bus falla, devuelve
`MOTOR_ERR_RNG` (el valor de `MBEDTLS_ERR_ENTROPY_SOURCE_FAILED`) y mbedtls
aborta; **no se rellena con `esp_random`**. Y `clave_generar()` genera en
una clave aparte y solo la pone en servicio si acaba bien: una siembra
fallida no deja al equipo sin firmar ni con una clave a medias. Es la misma
regla que se impuso al RTL el 27-10 (con alarma no sale nada), llevada al
producto.

**Secuencia contra repetición.** Una firma válida no impide reinyectar una
lectura vieja. La lectura lleva un número de secuencia monótono y el
verificador rechaza la que no supere a la última del mismo equipo. El banco
planta una lectura manipulada (un bit de la energía) y una repetida, y el
script del PC tiene que encontrar exactamente esas dos.

**Qué clave se cree el verificador.** `verifica_lecturas.py` usa la última
pública anunciada en el log antes de cada lectura, o la que se le pase con
`--publica`. Lo primero es *confianza en el primer uso* y vale para el
banco; en un despliegue la pública se fija al registrar el equipo
(`--publica`) y las tramas `P` del canal solo sirven para avisar si
cambian.

## 3. Formatos

Lectura (24 bytes, enteros big-endian; `lectura.h`):

| Bytes | Campo |
|---|---|
| 0–7 | identificador del equipo (MAC base del chip, rellena a 8) |
| 8–11 | secuencia (monótona) |
| 12–15 | instante (s desde el arranque; en producto, hora real) |
| 16–19 | energía acumulada (Wh) |
| 20–23 | potencia (W) |

Trama `L` = lectura (24) ‖ firma ECDSA en DER sobre SHA-256 (70–72 bytes).
Trama `P` = SubjectPublicKeyInfo DER (91 bytes). CSR en PEM por la consola.
Las tramas son las `F` de siempre (tipo, longitud, carga, CRC32), así que
`consola_esp32.py` las guarda y las comprueba igual que las del generador.

## 4. Qué está verificado y qué no

**Verificado en el PC** (`results/host_check.log`, `run_host.py`, 0 fallos):

- `test_medidor.c` incluye `main.c` del medidor tal cual y lo corre contra
  `motor_sim.c` con **mbedtls 3.6.7 de verdad** (el mismo árbol que
  ESP-IDF 5.3). Comprueba: sin sembrar no hay clave y no se consume ningún
  bloque; cada bloque de la clave es una orden `aleatorio` aceptada; con
  alarma o con el bus caído se mantiene la clave anterior y se sigue
  firmando; la firma es determinista; un bit cambiado no verifica; la CSR se
  parsea y lleva la pública del equipo; ni pública, ni firma, ni CSR
  contienen 8 bytes seguidos de la privada; tras `olvidar` no sale nada.
- La salida del banco pasa por `analysis/verifica_lecturas.py`, que verifica
  con `cryptography`, **otra implementación que mbedtls**: 8 válidas, 1 firma
  inválida y 1 repetida, exactamente las plantadas; la CSR, firma válida y
  misma pública.
- El verificador sigue pasando su banco sobre el componente común, y ahora
  con mbedtls real su CMAC ya no es el mismo código que el del modelo.

**Compilado con ESP-IDF 5.3.5** (ver los logs en `results/`): el
verificador para `esp32` y el medidor para `esp32c3`.

**No verificado:** nada en placa. El motor no existe aún fuera de la
simulación (pendiente la Basys 3), y la entropía del modelo del banco es
un AES con semilla fija, no una medida.

## 5. Cómo se usa

Banco en el PC (hace falta gcc, cmake y el paquete `cryptography`; en este
proyecto, desde WSL):

```
python3 firmware/host_check/run_host.py --mbedtls $IDF_PATH/components/mbedtls/mbedtls
```

Firmware (`idf.py build` en `firmware/medidor`; el objetivo por defecto es
`esp32c3`, `idf.py set-target esp32` para el clásico). Pines I2C: 5/6 en el
C3, 21/22 en el ESP32, al principio de `main.c`.

Con placa y motor: `consola_esp32.py --ordenes sembrar clave csr "lectura 20"`
y después `verifica_lecturas.py results/esp32_consola_X.log`.

## 6. Dónde encaja en un producto y qué le falta

Un equipo pequeño con ESP32-C3 ya tiene un I2C con pantalla o expansores;
el motor entra en el mismo bus a 3,3 V y la capa `motor_i2c` sirve tal cual.
El cambio en el equipo es: generar la clave en el arranque de fábrica (tras
sembrar), mandar la CSR en el aprovisionamiento, guardar la privada, y
firmar cada lectura antes de guardarla o enviarla. En la nube: guardar la
pública por equipo y verificar al recibir.

Siendo honestos, el C3 ya trae HMAC, firma digital (DS) y cifrado de flash:
el motor no sustituye nada de eso. Lo que aporta es una **fuente de entropía
auditable** (el TFM entero) y una clave que nace fuera del SoC. Como prueba
de concepto para presentar la idea, encaja; como producto, la decisión es
de coste y de certificación.

Lo que esta demo no hace y un producto tendría que hacer:

- **Guardar la clave.** Aquí vive en RAM y se borra con `olvidar`; en
  producto iría a NVS cifrado (con cifrado de flash) o, mejor, el motor
  haría de elemento seguro y guardaría él la clave, que es la segunda fase
  del diseño (hoy el motor solo guarda una clave AES-128 y no firma).
- **Hora real** en vez de segundos desde el arranque.
- **Resembrado** del motor por política (`PETICIONES`), que sigue siendo
  obligación del maestro.
- **Lecturas reales** en vez del modelo de carga de `siguiente_lectura()`.
