/* Lecturas firmadas y clave del equipo. Solo mbedtls: ni I2C ni FreeRTOS,
 * para que el mismo codigo se pruebe en el PC contra el motor simulado y
 * se flashee tal cual.
 *
 * La clave es ECDSA P-256 y se genera con el f_rng que se le pase, que en
 * el equipo es motor_rng(): asi la clave privada nace de la entropia del
 * motor y nunca sale del chip; lo que sale es la publica (o una peticion
 * de certificado firmada con ella). La firma de cada lectura usa ECDSA
 * determinista (RFC 6979): el nonce k sale de la clave y del mensaje, no
 * de ningun generador, asi que una fuente mala en el momento de firmar no
 * puede filtrar la clave, que es el fallo clasico de ECDSA. El f_rng que
 * reciben las funciones de firma solo sirve para el cegado contra canales
 * laterales, y no afecta al valor de la firma; pero mbedtls lo exige (NULL
 * o un f_rng que devuelva error hacen fallar la firma), asi que hay que
 * pasarle uno que no falle, como esp_fill_random.
 *
 * Seguridad: la fuerza de la clave la acota el DRBG del motor, CTR_DRBG
 * con AES-128 (128 bits), que es lo que ofrece P-256. Una curva mayor no
 * ganaria nada con esta semilla.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "mbedtls/pk.h"

#define LECTURA_BYTES   24      /* registro serializado */
#define FIRMA_MAX       80      /* ECDSA P-256 en DER: 70 a 72 bytes */
#define PUBLICA_MAX     96      /* SubjectPublicKeyInfo DER de P-256: 91 bytes */
#define CSR_MAX         1024    /* PEM de la peticion de certificado */

/* Una lectura de energia. Es el registro que se firma, serializado en
 * LECTURA_BYTES con los enteros en big-endian:
 *   0..7   id del equipo       8..11  secuencia (monotona, contra repeticion)
 *   12..15 instante (s)        16..19 energia acumulada (Wh)
 *   20..23 potencia (W) */
typedef struct {
    uint8_t  id[8];
    uint32_t secuencia;
    uint32_t instante;
    uint32_t energia_wh;
    uint32_t potencia_w;
} lectura_t;

void lectura_serializar(const lectura_t *l, uint8_t salida[LECTURA_BYTES]);
void lectura_deserializar(const uint8_t entrada[LECTURA_BYTES], lectura_t *l);

typedef int (*lectura_rng_t)(void *ctx, unsigned char *salida, size_t n);

typedef struct {
    mbedtls_pk_context pk;
    bool valida;
} clave_equipo_t;

void clave_iniciar(clave_equipo_t *c);

/* Genera una clave P-256 nueva con f_rng. Si f_rng falla (el motor no da
 * aleatorio) devuelve el error de mbedtls y la clave anterior, si la
 * habia, sigue valiendo: una siembra fallida no deja al equipo sin firmar. */
int clave_generar(clave_equipo_t *c, lectura_rng_t f_rng, void *p_rng);

/* Clave publica en SubjectPublicKeyInfo DER. */
int clave_publica(const clave_equipo_t *c, uint8_t *salida, size_t max, size_t *n);

/* Firma ECDSA (DER) de SHA-256(registro). f_rng solo para el cegado. */
int clave_firmar(clave_equipo_t *c, const uint8_t registro[LECTURA_BYTES],
                 uint8_t *firma, size_t max, size_t *n,
                 lectura_rng_t f_rng, void *p_rng);

/* Comprueba una firma con una publica en DER. 0 si es valida. */
int clave_verificar(const uint8_t *publica, size_t npub,
                    const uint8_t registro[LECTURA_BYTES],
                    const uint8_t *firma, size_t nfirma);

/* Peticion de certificado (PKCS#10, PEM) para el sujeto dado, firmada
 * con la clave. Es lo que saldria del equipo hacia la CA. */
int clave_csr(clave_equipo_t *c, const char *sujeto, char *pem, size_t max,
              lectura_rng_t f_rng, void *p_rng);

/* Clave privada en DER (SEC1 ECPrivateKey), para guardarla; quien la
 * reciba la borra en cuanto la haya escrito. Y la operacion inversa. */
#define PRIVADA_MAX     160     /* ECPrivateKey DER de P-256: 121 bytes */
int clave_exportar(const clave_equipo_t *c, uint8_t *salida, size_t max, size_t *n);
int clave_importar(clave_equipo_t *c, const uint8_t *der, size_t n);

/* Borra la clave privada de memoria. */
void clave_borrar(clave_equipo_t *c);
