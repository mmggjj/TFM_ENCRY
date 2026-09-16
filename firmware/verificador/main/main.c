/* Verificador independiente del motor de claves, para ESP32 (ESP-IDF 5.x).
 *
 * El ESP32 es el juez: habla con el motor por I2C segun
 * docs/mapa_registros.md, provisiona la clave en modo test y comprueba
 * el reto-respuesta recalculando el CMAC con mbedtls, que es una
 * implementacion independiente del VHDL. Tambien vuelca al PC bits
 * crudos y salidas del DRBG en tramas con CRC32, el mismo formato que el
 * trabajo previo del autor (TFM_RNG), para que la cadena de analisis
 * estadistico sea la misma para el motor y para el propio ESP32.
 *
 * Reglas del proyecto: nada de credenciales, salida sin filtrar, y los
 * fallos se registran integros, nunca se descartan.
 *
 * Comandos por consola (UART 115200):
 *   id        lee ID y STATUS
 *   sembrar   ordena sembrar y espera
 *   generar   pide una clave nueva, la provisiona (modo test) y la muestra
 *   reto N    hace N retos-respuesta con nonces de esp_random() y cuenta
 *   aleatorio N  vuelca N bloques de 32 bytes del DRBG al PC
 *   crudo N   vuelca N trozos del buffer de captura al PC
 *   esp N     vuelca N bloques de esp_random() al PC (comparacion)
 */

#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/i2c_master.h"
#include "esp_log.h"
#include "esp_random.h"
#include "esp_rom_crc.h"
#include "mbedtls/cipher.h"
#include "mbedtls/cmac.h"

static const char *TAG = "verificador";

/* ---- mapa de registros (docs/mapa_registros.md) ---------------------- */
#define MOTOR_DIR        0x30
#define REG_ID           0x00
#define REG_STATUS       0x02
#define REG_CONTROL      0x03
#define REG_CFG_KD       0x04
#define REG_CFG_PAG      0x05
#define REG_CLAVE        0x10
#define REG_RETO         0x20
#define REG_ETIQUETA     0x30
#define REG_ALEATORIO    0x40
#define REG_CAPTURA      0x80

#define ST_SEMBRADO      (1u << 0)
#define ST_OCUPADO       (1u << 1)
#define ST_ALM_RCT       (1u << 2)
#define ST_ALM_APT       (1u << 3)
#define ST_CLAVE_VALIDA  (1u << 4)
#define ST_CAPTURA_LLENA (1u << 5)
#define ST_ETIQ_LISTA    (1u << 6)
#define ST_MODO_TEST     (1u << 7)

#define CTL_SEMBRAR      (1u << 0)
#define CTL_GENERAR      (1u << 1)
#define CTL_AUTENTICAR   (1u << 2)
#define CTL_BORRAR_ALM   (1u << 3)
#define CTL_CAPTURAR     (1u << 4)
#define CTL_RESEMBRAR    (1u << 5)
#define CTL_ALEATORIO    (1u << 6)

/* ---- pines: I2C por defecto del ESP32 clasico ------------------------- */
#define PIN_SDA          21
#define PIN_SCL          22
#define I2C_HZ           400000

static i2c_master_bus_handle_t bus;
static i2c_master_dev_handle_t motor;

static uint8_t clave_provisionada[16];
static bool hay_clave = false;

/* Un fallo del bus no es un fallo criptografico, y el verificador existe
 * para contar los segundos. Cualquier acceso que falle lo marca aqui, y
 * quien cuente resultados separa los dos casos en vez de sumarlos. */
static bool io_ok = true;

/* Comparacion sin salida temprana. En este banco no hay adversario que
 * mida tiempos, pero es codigo criptografico y no cuesta nada. */
static bool iguales(const uint8_t *a, const uint8_t *b, size_t n)
{
    uint8_t d = 0;
    for (size_t i = 0; i < n; i++) d |= (uint8_t)(a[i] ^ b[i]);
    return d == 0;
}

/* ---- acceso a registros ---------------------------------------------- */
static esp_err_t reg_escribir(uint8_t dir, const uint8_t *datos, size_t n)
{
    uint8_t buf[1 + 32];
    if (n > 32) return ESP_ERR_INVALID_SIZE;
    buf[0] = dir;
    memcpy(buf + 1, datos, n);
    esp_err_t e = i2c_master_transmit(motor, buf, 1 + n, 100);
    if (e != ESP_OK) io_ok = false;
    return e;
}

static esp_err_t reg_leer(uint8_t dir, uint8_t *datos, size_t n)
{
    esp_err_t e = i2c_master_transmit_receive(motor, &dir, 1, datos, n, 100);
    if (e != ESP_OK) {
        io_ok = false;
        memset(datos, 0, n);   /* nunca dejar el buffer del llamante sin tocar */
    }
    return e;
}

static esp_err_t reg_escribir1(uint8_t dir, uint8_t v)
{
    return reg_escribir(dir, &v, 1);
}

static uint8_t leer_status(void)
{
    uint8_t s = 0;
    /* Si la lectura falla se devuelve 0, no 0xFF: con 0xFF quedaban a uno
     * sembrado, clave_valida, etiqueta_lista y modo_test, o sea que un bus
     * caido se leia como "todo listo". Falla cerrado. */
    reg_leer(REG_STATUS, &s, 1);
    return s;
}

/* Sondea hasta que baje "ocupado". Devuelve el STATUS final. */
static uint8_t esperar_libre(int max_ms)
{
    uint8_t s;
    for (int t = 0; t < max_ms; t += 2) {
        s = leer_status();
        if (!(s & ST_OCUPADO)) return s;
        vTaskDelay(pdMS_TO_TICKS(2));
    }
    ESP_LOGE(TAG, "el motor no se libera en %d ms", max_ms);
    return leer_status();
}

static void imprimir_hex(const char *etiqueta, const uint8_t *d, size_t n)
{
    printf("%s ", etiqueta);
    for (size_t i = 0; i < n; i++) printf("%02x", d[i]);
    printf("\n");
}

/* Trama al PC: 'F' tipo len[2] payload crc32[4], en hex por linea. */
static void trama_pc(char tipo, const uint8_t *d, size_t n)
{
    uint32_t crc = esp_rom_crc32_le(0, d, n);
    printf("F%c%04zx", tipo, n);
    for (size_t i = 0; i < n; i++) printf("%02x", d[i]);
    printf("%08" PRIx32 "\n", crc);
}

/* ---- comandos --------------------------------------------------------- */
static void cmd_id(void)
{
    uint8_t id = 0, st;
    if (reg_leer(REG_ID, &id, 1) != ESP_OK) { ESP_LOGE(TAG, "sin respuesta I2C"); return; }
    if (id != 0xA5) ESP_LOGE(TAG, "ID inesperado 0x%02x, se esperaba 0xA5", id);
    st = leer_status();
    printf("id 0x%02x status 0x%02x sembrado=%d ocupado=%d alm_rct=%d alm_apt=%d "
           "clave=%d captura=%d etiqueta=%d test=%d\n", id, st,
           !!(st & ST_SEMBRADO), !!(st & ST_OCUPADO), !!(st & ST_ALM_RCT),
           !!(st & ST_ALM_APT), !!(st & ST_CLAVE_VALIDA), !!(st & ST_CAPTURA_LLENA),
           !!(st & ST_ETIQ_LISTA), !!(st & ST_MODO_TEST));
}

static void cmd_sembrar(void)
{
    reg_escribir1(REG_CONTROL, CTL_SEMBRAR);
    uint8_t st = esperar_libre(5000);
    printf("sembrar: %s%s%s\n", (st & ST_SEMBRADO) ? "ok" : "FALLO",
           (st & ST_ALM_RCT) ? " ALARMA_RCT" : "", (st & ST_ALM_APT) ? " ALARMA_APT" : "");
}

static void cmd_generar(void)
{
    reg_escribir1(REG_CONTROL, CTL_GENERAR);
    uint8_t st = esperar_libre(2000);
    if (!(st & ST_CLAVE_VALIDA)) { printf("generar: FALLO, sin clave valida\n"); return; }
    if (st & ST_MODO_TEST) {
        static const uint8_t cero[16] = {0};
        if (reg_leer(REG_CLAVE, clave_provisionada, 16) != ESP_OK) {
            printf("generar: ERROR I2C al leer la clave\n");
            hay_clave = false;
            return;
        }
        hay_clave = !iguales(clave_provisionada, cero, 16);
        imprimir_hex("clave", clave_provisionada, 16);
        printf("provision: %s\n", hay_clave ? "ok" : "FALLO, clave nula");
    } else {
        printf("generar: ok, clave no exportable sin modo test\n");
    }
}

/* Aleatorio del DRBG hacia el PC. Es una generacion independiente de la
 * clave: el registro ALEATORIO nunca contiene la clave. */
static void cmd_aleatorio(int n)
{
    uint8_t b[32];
    for (int i = 0; i < n; i++) {
        reg_escribir1(REG_CONTROL, CTL_ALEATORIO);
        uint8_t st = esperar_libre(500);
        if (!(st & ST_SEMBRADO)) { printf("aleatorio: el motor no esta sembrado\n"); return; }
        reg_leer(REG_ALEATORIO, b, 32);
        trama_pc('D', b, 32);
    }
}

static void cmd_reto(int n)
{
    if (!hay_clave) { printf("reto: primero 'generar' en modo test\n"); return; }
    const mbedtls_cipher_info_t *ci = mbedtls_cipher_info_from_type(MBEDTLS_CIPHER_AES_128_ECB);
    if (ci == NULL) {
        printf("reto: mbedtls sin AES-128-ECB; falta CONFIG_MBEDTLS_CMAC_C\n");
        return;
    }
    /* Tres cuentas, no dos: un fallo del bus no dice nada del motor, y
     * sumarlo a los fallos de etiqueta falsea la estadistica que este
     * verificador existe para producir. */
    int aciertos = 0, fallos = 0, errores = 0;
    for (int i = 0; i < n; i++) {
        uint8_t nonce[16] = {0}, etiqueta[16] = {0}, esperada[16] = {0};
        /* El nonce sale del RNG del ESP32: aqui solo hace falta que no se
         * repita, no que sea impredecible. No es material de clave. */
        esp_fill_random(nonce, 16);
        io_ok = true;
        reg_escribir(REG_RETO, nonce, 16);
        reg_escribir1(REG_CONTROL, CTL_AUTENTICAR);
        uint8_t st = esperar_libre(500);
        reg_leer(REG_ETIQUETA, etiqueta, 16);
        int r = mbedtls_cipher_cmac(ci, clave_provisionada, 128, nonce, 16, esperada);
        if (r != 0) {
            printf("reto: mbedtls_cipher_cmac fallo (%d); el roto es el "
                   "verificador, no el motor\n", r);
            return;
        }
        if (!io_ok) {
            errores++;
            imprimir_hex("ERROR I2C nonce", nonce, 16);
        } else if (!(st & ST_ETIQ_LISTA)) {
            fallos++;
            printf("FALLO etiqueta no lista, status 0x%02x\n", st);
            imprimir_hex("      nonce   ", nonce, 16);
        } else if (!iguales(etiqueta, esperada, 16)) {
            fallos++;
            imprimir_hex("FALLO nonce   ", nonce, 16);
            imprimir_hex("      motor   ", etiqueta, 16);
            imprimir_hex("      mbedtls ", esperada, 16);
        } else {
            aciertos++;
        }
    }
    printf("reto-respuesta: %d aciertos, %d fallos criptograficos, "
           "%d errores de bus, de %d\n", aciertos, fallos, errores, n);
}

static void cmd_crudo(int n)
{
    uint8_t trozo[512];
    for (int t = 0; t < n; t++) {
        reg_escribir1(REG_CONTROL, CTL_CAPTURAR);
        uint8_t st = 0;
        for (int k = 0; k < 2000 && !(st & ST_CAPTURA_LLENA); k++) {
            st = leer_status();
            if (!(st & ST_CAPTURA_LLENA)) vTaskDelay(1);
        }
        if (!(st & ST_CAPTURA_LLENA)) { printf("crudo: captura no llena\n"); return; }
        for (uint8_t pag = 0; pag < 4; pag++) {
            reg_escribir1(REG_CFG_PAG, pag);
            reg_leer(REG_CAPTURA, trozo + 128 * pag, 128);
        }
        trama_pc('R', trozo, 512);
    }
}

static void cmd_esp(int n)
{
    uint8_t b[32];
    for (int i = 0; i < n; i++) {
        esp_fill_random(b, 32);
        trama_pc('E', b, 32);
    }
}

/* ---- consola minima --------------------------------------------------- */
static void bucle_consola(void)
{
    char linea[64];
    printf("verificador listo. comandos: id sembrar generar reto N aleatorio N crudo N esp N\n");
    for (;;) {
        if (!fgets(linea, sizeof linea, stdin)) { vTaskDelay(pdMS_TO_TICKS(50)); continue; }
        char cmd[16] = {0}; int arg = 1;
        sscanf(linea, "%15s %d", cmd, &arg);
        if      (!strcmp(cmd, "id"))      cmd_id();
        else if (!strcmp(cmd, "sembrar")) cmd_sembrar();
        else if (!strcmp(cmd, "generar")) cmd_generar();
        else if (!strcmp(cmd, "reto"))    cmd_reto(arg);
        else if (!strcmp(cmd, "aleatorio")) cmd_aleatorio(arg);
        else if (!strcmp(cmd, "crudo"))   cmd_crudo(arg);
        else if (!strcmp(cmd, "esp"))     cmd_esp(arg);
        else if (cmd[0])                  printf("comando desconocido: %s\n", cmd);
    }
}

void app_main(void)
{
    i2c_master_bus_config_t bcfg = {
        .i2c_port = I2C_NUM_0, .sda_io_num = PIN_SDA, .scl_io_num = PIN_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT, .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    ESP_ERROR_CHECK(i2c_new_master_bus(&bcfg, &bus));
    i2c_device_config_t dcfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7, .device_address = MOTOR_DIR,
        .scl_speed_hz = I2C_HZ,
    };
    ESP_ERROR_CHECK(i2c_master_bus_add_device(bus, &dcfg, &motor));
    cmd_id();
    bucle_consola();
}
