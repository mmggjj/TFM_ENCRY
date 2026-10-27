/* Motor de claves simulado en software, para probar el verificador sin
 * placa ni FPGA.
 *
 * Implementa el mapa de registros de docs/mapa_registros.md como segunda
 * implementacion independiente del VHDL. Si el verificador y este modelo
 * se entienden, el mapa de registros esta bien escrito como
 * especificacion; eso es algo que ningun banco VHDL puede demostrar,
 * porque alli el banco y el disenho salen de la misma cabeza y del mismo
 * documento leido una sola vez.
 *
 * LIMITE, que hay que declarar al usar esto: si el verificador se enlaza
 * con mbedtls_stub.c, el AES-CMAC del "motor" y el que usa el verificador
 * para comprobarlo son EL MISMO codigo, y la verificacion cruzada deja de
 * ser independiente; esa prueba valida el PROTOCOLO y la LOGICA, no la
 * criptografia. Con mbedtls de verdad en el PC (run_host.py --mbedtls) el
 * CMAC del verificador ya es otra implementacion. La independencia frente
 * al VHDL solo la da mbedtls en el ESP32 contra la FPGA.
 *
 * El AES y el CMAC se autovalidan al arrancar contra FIPS-197 apendice B
 * y RFC 4493, para que un fallo del modelo no se confunda con un fallo
 * del verificador.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>

#include "esp_err.h"
#include "driver/i2c_master.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

/* ---------------------------------------------------------------- AES -- */

static const uint8_t SBOX[256] = {
0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16 };

static uint8_t xtime(uint8_t b) { return (uint8_t)((b << 1) ^ ((b >> 7) * 0x1b)); }

static void aes128_encrypt(const uint8_t k[16], const uint8_t in[16], uint8_t out[16])
{
    uint8_t s[16], rk[16], rcon = 1;
    memcpy(s, in, 16);
    memcpy(rk, k, 16);
    for (int i = 0; i < 16; i++) s[i] ^= rk[i];

    for (int ronda = 1; ronda <= 10; ronda++) {
        for (int i = 0; i < 16; i++) s[i] = SBOX[s[i]];
        uint8_t t[16];
        for (int c = 0; c < 4; c++)
            for (int r = 0; r < 4; r++)
                t[4 * c + r] = s[4 * ((c + r) % 4) + r];   /* ShiftRows */
        memcpy(s, t, 16);
        if (ronda != 10) {
            for (int c = 0; c < 4; c++) {                   /* MixColumns */
                uint8_t *p = s + 4 * c, a0 = p[0], a1 = p[1], a2 = p[2], a3 = p[3];
                uint8_t x = a0 ^ a1 ^ a2 ^ a3;
                p[0] ^= x ^ xtime((uint8_t)(a0 ^ a1));
                p[1] ^= x ^ xtime((uint8_t)(a1 ^ a2));
                p[2] ^= x ^ xtime((uint8_t)(a2 ^ a3));
                p[3] ^= x ^ xtime((uint8_t)(a3 ^ a0));
            }
        }
        /* expansion al vuelo, igual que aes_enc.vhd */
        rk[0] ^= (uint8_t)(SBOX[rk[13]] ^ rcon);
        rk[1] ^= SBOX[rk[14]];
        rk[2] ^= SBOX[rk[15]];
        rk[3] ^= SBOX[rk[12]];
        for (int i = 4; i < 16; i++) rk[i] ^= rk[i - 4];
        rcon = xtime(rcon);
        for (int i = 0; i < 16; i++) s[i] ^= rk[i];
    }
    memcpy(out, s, 16);
}

static void subclave(const uint8_t in[16], uint8_t out[16])
{
    uint8_t acarreo = (uint8_t)(in[0] >> 7);
    for (int i = 0; i < 15; i++) out[i] = (uint8_t)((in[i] << 1) | (in[i + 1] >> 7));
    out[15] = (uint8_t)(in[15] << 1);
    if (acarreo) out[15] ^= 0x87;
}

/* CMAC de un mensaje de un bloque completo o vacio, que es lo unico que
 * necesita el reto-respuesta (SP 800-38B). */
void motor_sim_cmac16(const uint8_t clave[16], const uint8_t msg[16], uint8_t tag[16])
{
    uint8_t L[16], k1[16], k2[16], b[16], cero[16] = {0};
    aes128_encrypt(clave, cero, L);
    subclave(L, k1);
    subclave(k1, k2);
    for (int i = 0; i < 16; i++) b[i] = (uint8_t)(msg[i] ^ k1[i]);
    aes128_encrypt(clave, b, tag);
}

/* --------------------------------------------------- estado del motor -- */

#define ST_SEMBRADO      (1u << 0)
#define ST_OCUPADO       (1u << 1)
#define ST_ALM_RCT       (1u << 2)
#define ST_CLAVE_VALIDA  (1u << 4)
#define ST_CAPTURA_LLENA (1u << 5)
#define ST_ETIQ_LISTA    (1u << 6)
#define ST_MODO_TEST     (1u << 7)

/* Como el RTL: test de arranque, minimo de CFG_KD y "ocupado" que dura. El
 * tiempo es el tick del sistema (1 ms, FREERTOS_HZ = 1000): en el PC lo
 * avanza el vTaskDelay de plataforma_sim.c; en el chip es el de verdad. */
#define KD_MIN           6
#define T_ARRANQUE       30u      /* ticks hasta pasar el test de arranque */
#define T_SIEMBRA        20u
#define T_ORDEN          1u

static struct {
    uint8_t status, cfg_kd, cfg_pag;
    uint8_t clave[16], reto[16], etiqueta[16], aleatorio[32];
    uint8_t captura[512];
    uint8_t drbg_key[16], drbg_v[16];
    uint32_t peticiones;
    uint8_t siembras;
    bool sembrado, alarma, rechazada;
    bool siembra_en_curso, siembra_nueva;
    uint32_t arranque_en, libre_en;
} m;

static uint32_t ahora(void) { return (uint32_t)xTaskGetTickCount(); }

bool motor_modo_test = true;      /* el banco lo maneja */
int  motor_fallo_bus = 0;         /* >0: las proximas N transacciones fallan */
bool motor_colgado = false;       /* "ocupado" no baja nunca */
int  motor_n_tramas = 0;          /* tramas al PC: una llamada al CRC cada una */
int  motor_n_aleatorio = 0;       /* ordenes "aleatorio" aceptadas */
int  motor_fallo_tras_aleatorio = 0; /* >0: falla la transaccion siguiente a la N-esima orden aleatorio aceptada */
uint32_t motor_pet_max = 0xFFFFFFFFu; /* tope del contador de peticiones (2^32-1 en el RTL; el banco lo baja) */
bool motor_capturando = false;     /* captura en curso: no se siembra */
static bool iniciado;             /* motor_reset() hecho */

static bool arrancado(void) { return !m.alarma && ahora() >= m.arranque_en; }
static bool agotado(void) { return m.peticiones >= motor_pet_max; }
static bool ocupado(void) { return motor_colgado || ahora() < m.libre_en; }

void motor_alarma(bool a) { m.alarma = a; }
const uint8_t *motor_clave(void) { return m.clave; }
uint32_t motor_ticks(void) { return ahora(); }

static void inc_v(void) { for (int i = 15; i >= 0; i--) if (++m.drbg_v[i]) break; }

/* Generacion del DRBG: dos bloques y actualizacion del estado, de forma
 * que dos generaciones seguidas nunca coinciden. Es lo que sostiene que
 * ALEATORIO no pueda contener la clave. */
static void drbg_generar(uint8_t salida[32])
{
    for (int b = 0; b < 2; b++) { inc_v(); aes128_encrypt(m.drbg_key, m.drbg_v, salida + 16 * b); }
    uint8_t nk[16], nv[16];
    inc_v(); aes128_encrypt(m.drbg_key, m.drbg_v, nk);
    inc_v(); aes128_encrypt(m.drbg_key, m.drbg_v, nv);
    memcpy(m.drbg_key, nk, 16);
    memcpy(m.drbg_v, nv, 16);
    if (m.peticiones < motor_pet_max) m.peticiones++;
}

/* La siembra es la unica orden que acaba despues: como en el RTL,
 * "sembrado" sube al terminar, no al aceptarla, y una alarma a mitad la
 * aborta dejando el DRBG como estaba y "rechazada" arriba. Se resuelve en
 * cada acceso al bus, que es cuando el maestro puede verlo. */
static void resolver_siembra(void)
{
    if (!m.siembra_en_curso) return;
    if (m.alarma) {
        m.siembra_en_curso = false;
        m.rechazada = true;
        m.libre_en = ahora();
    } else if (ahora() >= m.libre_en) {
        m.siembra_en_curso = false;
        /* Semilla fija pero distinta en cada siembra, como lo seria una
         * entropia nueva: asi dos claves generadas tras resembrar no
         * coinciden, y el banco sigue siendo reproducible. */
        if (m.siembra_nueva) {
            m.siembras++;
            for (int i = 0; i < 16; i++) { m.drbg_key[i] = (uint8_t)(0x5a ^ i ^ m.siembras); m.drbg_v[i] = (uint8_t)i; }
        }
        m.sembrado = true;
        m.peticiones = 1;
        m.status |= ST_SEMBRADO;
    }
}

/* Zeroizacion (borrar_todo): clave, DRBG, RETO, ALEATORIO y contador. */
static void borrar_todo(void)
{
    memset(m.clave, 0, sizeof m.clave);
    memset(m.reto, 0, sizeof m.reto);
    memset(m.aleatorio, 0, sizeof m.aleatorio);
    memset(m.drbg_key, 0, sizeof m.drbg_key);
    memset(m.drbg_v, 0, sizeof m.drbg_v);
    m.peticiones = 0;
    m.sembrado = false;
    m.siembra_en_curso = false;
    m.status &= (uint8_t)~(ST_SEMBRADO | ST_CLAVE_VALIDA | ST_ETIQ_LISTA);
}

/* Una orden por escritura, con la misma prioridad y las mismas condiciones
 * que motor_top.vhd. El resultado se aplica al aceptarla (salvo la
 * siembra, ver arriba); "ocupado" dura despues unos ticks para que el
 * verificador tenga que sondear. */
static void ejecutar_control(uint8_t v)
{
    if (v & (1u << 3)) {                       /* borrar alarmas */
        m.alarma = false;
        m.arranque_en = ahora() + T_ARRANQUE;    /* se repite el test de arranque */
    }
    if (!(v & 0xF7)) return;                   /* ninguna orden */
    if (ocupado()) { m.rechazada = true; return; }

    if (v & (1u << 7)) {                       /* borrar_todo: siempre */
        borrar_todo();
        m.libre_en = ahora() + T_ORDEN;
    } else if (v & ((1u << 0) | (1u << 5))) {  /* sembrar / resembrar */
        if (!arrancado() || m.cfg_kd < KD_MIN || motor_capturando) { m.rechazada = true; return; }
        if ((v & (1u << 5)) && !m.sembrado) { m.rechazada = true; return; }  /* resembrar actua sobre un estado */
        m.siembra_en_curso = true;
        m.siembra_nueva = (v & (1u << 0)) != 0;
        m.libre_en = ahora() + T_SIEMBRA;
    } else if (v & (1u << 1)) {                /* generar: solo la clave */
        if (!m.sembrado || m.alarma || agotado()) { m.rechazada = true; return; }
        uint8_t s[32];
        drbg_generar(s);
        memcpy(m.clave, s, 16);
        m.status |= ST_CLAVE_VALIDA;
        m.status &= (uint8_t)~ST_ETIQ_LISTA;
        m.libre_en = ahora() + T_ORDEN;
    } else if (v & (1u << 6)) {                /* aleatorio: generacion aparte */
        if (!m.sembrado || m.alarma || agotado()) { m.rechazada = true; return; }
        drbg_generar(m.aleatorio);
        motor_n_aleatorio++;
        if (motor_fallo_tras_aleatorio > 0 && motor_n_aleatorio == motor_fallo_tras_aleatorio)
            motor_fallo_bus = 1;               /* el bus cae antes de poder leer el bloque */
        m.libre_en = ahora() + T_ORDEN;
    } else if (v & (1u << 2)) {                /* autenticar */
        if (!(m.status & ST_CLAVE_VALIDA)) { m.rechazada = true; return; }
        motor_sim_cmac16(m.clave, m.reto, m.etiqueta);
        m.status |= ST_ETIQ_LISTA;
        m.libre_en = ahora() + T_ORDEN;
    } else {                                   /* capturar: solo en modo test, una a la vez */
        if (!motor_modo_test || motor_capturando) { m.rechazada = true; return; }
        /* El modelo llena el buffer al instante; motor_capturando lo pone
         * el banco cuando quiere una captura "larga". */
        for (size_t i = 0; i < sizeof m.captura; i++) m.captura[i] = (uint8_t)(rand() & 0xff);
        m.status |= ST_CAPTURA_LLENA;
    }
    m.rechazada = false;
}

static uint8_t leer_reg(uint8_t d)
{
    resolver_siembra();
    if (d == 0x00) return 0xA5;
    if (d == 0x01) return 0x03;
    if (d == 0x02) return (uint8_t)(m.status | (ocupado() ? ST_OCUPADO : 0) |
                                    (m.alarma ? ST_ALM_RCT : 0) |
                                    (motor_modo_test ? ST_MODO_TEST : 0));
    if (d == 0x04) return m.cfg_kd;
    if (d == 0x05) return m.cfg_pag;
    if (d >= 0x0A && d <= 0x0D) return (uint8_t)(m.peticiones >> (8 * (d - 0x0A)));
    if (d == 0x0E) return (uint8_t)((agotado() ? 4 : 0) | (m.rechazada ? 2 : 0) | (arrancado() ? 1 : 0));
    if (d >= 0x10 && d <= 0x1F) return motor_modo_test ? m.clave[d - 0x10] : 0x00;
    if (d >= 0x30 && d <= 0x3F) return m.etiqueta[d - 0x30];
    if (d >= 0x40 && d <= 0x5F) return m.aleatorio[d - 0x40];
    if (d >= 0x80) return motor_modo_test ? m.captura[m.cfg_pag * 128 + (d - 0x80)] : 0x00;
    return 0x00;
}

static void escribir_reg(uint8_t d, uint8_t v)
{
    resolver_siembra();
    if (d == 0x03) ejecutar_control(v);
    else if (d == 0x04) { if (!ocupado()) m.cfg_kd = v; }
    else if (d == 0x05) m.cfg_pag = (uint8_t)(v & 3);
    else if (d >= 0x20 && d <= 0x2F) { m.reto[d - 0x20] = v; m.status &= (uint8_t)~ST_ETIQ_LISTA; }
}

void motor_reset(void)
{
    iniciado = true;
    memset(&m, 0, sizeof m);
    m.cfg_kd = 24;                             /* G_KD_RESET */
    m.arranque_en = ahora() + T_ARRANQUE;
    motor_colgado = false;
}

/* ----------------------------------------- el "bus": punteros y trama -- */

/* En el PC estas funciones SON el driver (las cabeceras simuladas solo las
 * declaran). En el chip, compilado con MOTOR_SIM_EN_CHIP, el enlazador las
 * pone en lugar de las del driver de verdad con --wrap, y el I2C real se
 * inicializa pero no se usa: asi el firmware completo corre en QEMU con el
 * motor simulado detras del mismo bus. */
#ifdef MOTOR_SIM_EN_CHIP
#define SIM_TRANSMIT          __wrap_i2c_master_transmit
#define SIM_TRANSMIT_RECEIVE  __wrap_i2c_master_transmit_receive
#else
#define SIM_TRANSMIT          i2c_master_transmit
#define SIM_TRANSMIT_RECEIVE  i2c_master_transmit_receive
#endif

static void iniciar_si_hace_falta(void)
{
    if (!iniciado) { motor_reset(); iniciado = true; }
}

esp_err_t SIM_TRANSMIT(i2c_master_dev_handle_t d, const uint8_t *buf,
                       size_t n, int timeout_ms)
{
    (void)d; (void)timeout_ms;
    iniciar_si_hace_falta();
    if (motor_fallo_bus > 0) { motor_fallo_bus--; return -1; }
    if (n < 1) return -1;
    for (size_t i = 1; i < n; i++) escribir_reg((uint8_t)(buf[0] + i - 1), buf[i]);
    return ESP_OK;
}

esp_err_t SIM_TRANSMIT_RECEIVE(i2c_master_dev_handle_t d,
                               const uint8_t *w, size_t wn,
                               uint8_t *r, size_t rn, int timeout_ms)
{
    (void)d; (void)timeout_ms;
    iniciar_si_hace_falta();
    if (motor_fallo_bus > 0) { motor_fallo_bus--; return -1; }
    if (wn < 1) return -1;
    for (size_t i = 0; i < rn; i++) r[i] = leer_reg((uint8_t)(w[0] + i));
    return ESP_OK;
}

/* ---------------------------------------- autovalidacion del modelo ---- */

bool motor_sim_autotest(void)
{
    /* FIPS-197 apendice B */
    const uint8_t k[16] = {0x2b,0x7e,0x15,0x16,0x28,0xae,0xd2,0xa6,
                           0xab,0xf7,0x15,0x88,0x09,0xcf,0x4f,0x3c};
    const uint8_t p[16] = {0x32,0x43,0xf6,0xa8,0x88,0x5a,0x30,0x8d,
                           0x31,0x31,0x98,0xa2,0xe0,0x37,0x07,0x34};
    const uint8_t c[16] = {0x39,0x25,0x84,0x1d,0x02,0xdc,0x09,0xfb,
                           0xdc,0x11,0x85,0x97,0x19,0x6a,0x0b,0x32};
    uint8_t got[16];
    aes128_encrypt(k, p, got);
    if (memcmp(got, c, 16) != 0) { printf("  [FALLO] AES contra FIPS-197\n"); return false; }
    printf("  [ok ] AES-128 reproduce el vector de FIPS-197 apendice B\n");

    /* RFC 4493, mensaje de un bloque */
    const uint8_t m1[16] = {0x6b,0xc1,0xbe,0xe2,0x2e,0x40,0x9f,0x96,
                            0xe9,0x3d,0x7e,0x11,0x73,0x93,0x17,0x2a};
    const uint8_t t1[16] = {0x07,0x0a,0x16,0xb4,0x6b,0x4d,0x41,0x44,
                            0xf7,0x9b,0xdd,0x9d,0xd0,0x4a,0x28,0x7c};
    motor_sim_cmac16(k, m1, got);
    if (memcmp(got, t1, 16) != 0) { printf("  [FALLO] CMAC contra RFC 4493\n"); return false; }
    printf("  [ok ] AES-CMAC reproduce el vector de RFC 4493\n");
    return true;
}
