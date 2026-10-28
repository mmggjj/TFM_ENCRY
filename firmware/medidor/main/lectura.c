/* Lecturas firmadas y clave del equipo. Ver lectura.h. */
#include <string.h>
#include "mbedtls/build_info.h"
#include "mbedtls/ecp.h"
#include "mbedtls/platform_util.h"
#include "mbedtls/sha256.h"
#include "mbedtls/x509_csr.h"
#include "lectura.h"

/* Sin esto mbedtls saca k de f_rng al firmar y la clave depende de la
 * calidad del generador en cada firma. En ESP-IDF es
 * CONFIG_MBEDTLS_ECDSA_DETERMINISTIC (sdkconfig.defaults). */
#ifndef MBEDTLS_ECDSA_DETERMINISTIC
#error "hace falta ECDSA determinista (MBEDTLS_ECDSA_DETERMINISTIC)"
#endif

static void poner_u32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);  p[3] = (uint8_t)v;
}

static uint32_t coger_u32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | p[3];
}

void lectura_serializar(const lectura_t *l, uint8_t s[LECTURA_BYTES])
{
    memcpy(s, l->id, 8);
    poner_u32(s + 8, l->secuencia);
    poner_u32(s + 12, l->instante);
    poner_u32(s + 16, l->energia_wh);
    poner_u32(s + 20, l->potencia_w);
}

void lectura_deserializar(const uint8_t e[LECTURA_BYTES], lectura_t *l)
{
    memcpy(l->id, e, 8);
    l->secuencia  = coger_u32(e + 8);
    l->instante   = coger_u32(e + 12);
    l->energia_wh = coger_u32(e + 16);
    l->potencia_w = coger_u32(e + 20);
}

void clave_iniciar(clave_equipo_t *c)
{
    mbedtls_pk_init(&c->pk);
    c->valida = false;
}

int clave_generar(clave_equipo_t *c, lectura_rng_t f_rng, void *p_rng)
{
    mbedtls_pk_context nueva;
    mbedtls_pk_init(&nueva);
    int r = mbedtls_pk_setup(&nueva, mbedtls_pk_info_from_type(MBEDTLS_PK_ECKEY));
    if (r == 0)
        r = mbedtls_ecp_gen_key(MBEDTLS_ECP_DP_SECP256R1, mbedtls_pk_ec(nueva), f_rng, p_rng);
    if (r != 0) {
        mbedtls_pk_free(&nueva);   /* la anterior sigue en pie */
        return r;
    }
    mbedtls_pk_free(&c->pk);
    c->pk = nueva;                 /* se mueve: no liberar "nueva" */
    c->valida = true;
    return 0;
}

int clave_publica(const clave_equipo_t *c, uint8_t *salida, size_t max, size_t *n)
{
    if (!c->valida) return MBEDTLS_ERR_PK_BAD_INPUT_DATA;
    /* mbedtls escribe DER desde el final del buffer. */
    int r = mbedtls_pk_write_pubkey_der(&c->pk, salida, max);
    if (r < 0) return r;
    *n = (size_t)r;
    memmove(salida, salida + max - *n, *n);
    return 0;
}

int clave_firmar(clave_equipo_t *c, const uint8_t registro[LECTURA_BYTES],
                 uint8_t *firma, size_t max, size_t *n,
                 lectura_rng_t f_rng, void *p_rng)
{
    uint8_t hash[32];
    if (!c->valida) return MBEDTLS_ERR_PK_BAD_INPUT_DATA;
    int r = mbedtls_sha256(registro, LECTURA_BYTES, hash, 0);
    if (r != 0) return r;
    return mbedtls_pk_sign(&c->pk, MBEDTLS_MD_SHA256, hash, sizeof hash,
                           firma, max, n, f_rng, p_rng);
}

int clave_verificar(const uint8_t *publica, size_t npub,
                    const uint8_t registro[LECTURA_BYTES],
                    const uint8_t *firma, size_t nfirma)
{
    uint8_t hash[32];
    mbedtls_pk_context pk;
    mbedtls_pk_init(&pk);
    int r = mbedtls_pk_parse_public_key(&pk, publica, npub);
    if (r == 0) r = mbedtls_sha256(registro, LECTURA_BYTES, hash, 0);
    if (r == 0) r = mbedtls_pk_verify(&pk, MBEDTLS_MD_SHA256, hash, sizeof hash, firma, nfirma);
    mbedtls_pk_free(&pk);
    return r;
}

int clave_csr(clave_equipo_t *c, const char *sujeto, char *pem, size_t max,
              lectura_rng_t f_rng, void *p_rng)
{
    if (!c->valida) return MBEDTLS_ERR_PK_BAD_INPUT_DATA;
    mbedtls_x509write_csr csr;
    mbedtls_x509write_csr_init(&csr);
    mbedtls_x509write_csr_set_md_alg(&csr, MBEDTLS_MD_SHA256);
    mbedtls_x509write_csr_set_key(&csr, &c->pk);
    int r = mbedtls_x509write_csr_set_subject_name(&csr, sujeto);
    if (r == 0) r = mbedtls_x509write_csr_pem(&csr, (unsigned char *)pem, max, f_rng, p_rng);
    mbedtls_x509write_csr_free(&csr);
    return r;
}

int clave_exportar(const clave_equipo_t *c, uint8_t *salida, size_t max, size_t *n)
{
    if (!c->valida) return MBEDTLS_ERR_PK_BAD_INPUT_DATA;
    int r = mbedtls_pk_write_key_der(&c->pk, salida, max);   /* desde el final */
    if (r < 0) return r;
    *n = (size_t)r;
    memmove(salida, salida + max - *n, *n);
    mbedtls_platform_zeroize(salida + *n, max - *n);
    return 0;
}

int clave_importar(clave_equipo_t *c, const uint8_t *der, size_t n)
{
    mbedtls_pk_context nueva;
    mbedtls_pk_init(&nueva);
    /* Sin f_rng: la clave no se cega al importar, solo al usarla. */
    int r = mbedtls_pk_parse_key(&nueva, der, n, NULL, 0, NULL, NULL);
    if (r == 0 && mbedtls_pk_get_type(&nueva) != MBEDTLS_PK_ECKEY) r = MBEDTLS_ERR_PK_TYPE_MISMATCH;
    if (r != 0) { mbedtls_pk_free(&nueva); return r; }
    mbedtls_pk_free(&c->pk);
    c->pk = nueva;
    c->valida = true;
    return 0;
}

void clave_borrar(clave_equipo_t *c)
{
    /* mbedtls_pk_free pone a cero los mpi de la clave antes de soltarlos. */
    mbedtls_pk_free(&c->pk);
    mbedtls_pk_init(&c->pk);
    c->valida = false;
}
