/* Verificador independiente del motor de claves, para ESP32 (ESP-IDF 5.x).
 *
 * El ESP32 es el juez: habla con el motor por I2C segun
 * docs/mapa_registros.md, provisiona la clave en modo test y comprueba
 * el reto-respuesta recalculando el CMAC con mbedtls, que es una
 * implementacion independiente del VHDL. Tambien vuelca al PC bits
 * crudos y salidas del DRBG en tramas con CRC32, el mismo formato que las
 * capturas del generador del ESP32 en la primera parte del TFM, para que
 * la cadena de analisis estadistico sea la misma para el motor y para el
 * propio ESP32.
 *
 * El acceso al motor (mapa de registros, ordenes, plazos) esta en el
 * componente motor_i2c, compartido con el medidor.
 *
 * Reglas del proyecto: nada de credenciales, salida sin filtrar, y los
 * fallos se registran integros, nunca se descartan.
 *
 * Comandos por consola (UART 115200):
 *   id        lee ID, VERSION, STATUS y DIAG
 *   sembrar   espera al test de arranque, ordena sembrar y espera
 *   borrar    baja las alarmas de salud (obliga a repetir el test de arranque)
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
#include "esp_log.h"
#include "esp_random.h"
#include "esp_rom_crc.h"
#include "mbedtls/cipher.h"
#include "mbedtls/cmac.h"
#include "motor_i2c.h"

static const char *TAG = "verificador";

/* ---- pines: I2C por defecto del ESP32 clasico ------------------------- */
#define PIN_SDA          21
#define PIN_SCL          22

static uint8_t clave_provisionada[16];
static bool hay_clave = false;

/* Comparacion sin salida temprana. En este banco no hay adversario que
 * mida tiempos, pero es codigo criptografico y no cuesta nada. */
static bool iguales(const uint8_t *a, const uint8_t *b, size_t n)
{
    uint8_t d = 0;
    for (size_t i = 0; i < n; i++) d |= (uint8_t)(a[i] ^ b[i]);
    return d == 0;
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
    uint8_t id = 0, ver = 0, diag = 0, st;
    if (motor_reg_leer(REG_ID, &id, 1) != ESP_OK) { ESP_LOGE(TAG, "sin respuesta I2C"); return; }
    if (id != MOTOR_ID) ESP_LOGE(TAG, "ID inesperado 0x%02x, se esperaba 0x%02x", id, MOTOR_ID);
    motor_reg_leer(REG_VERSION, &ver, 1);
    if (ver < MOTOR_VERSION) ESP_LOGE(TAG, "VERSION 0x%02x: motor sin DIAG ni test de arranque", ver);
    motor_reg_leer(REG_DIAG, &diag, 1);
    st = motor_status();
    printf("id 0x%02x version 0x%02x status 0x%02x sembrado=%d ocupado=%d alm_rct=%d "
           "alm_apt=%d clave=%d captura=%d etiqueta=%d test=%d arrancado=%d rechazada=%d\n",
           id, ver, st,
           !!(st & ST_SEMBRADO), !!(st & ST_OCUPADO), !!(st & ST_ALM_RCT),
           !!(st & ST_ALM_APT), !!(st & ST_CLAVE_VALIDA), !!(st & ST_CAPTURA_LLENA),
           !!(st & ST_ETIQ_LISTA), !!(st & ST_MODO_TEST),
           !!(diag & DG_ARRANCADO), !!(diag & DG_RECHAZADA));
}

static void cmd_sembrar(void)
{
    uint8_t st = 0, diag = 0;
    /* El motor no siembra hasta pasar el test de arranque: 1024 muestras sin
     * alarma desde el reset o el ultimo borrado. */
    esp_err_t e = motor_esperar_arranque(T_ARRANQUE_MS, &diag);
    if (e == ESP_FAIL) { printf("sembrar: FALLO, ERROR I2C\n"); return; }
    if (e != ESP_OK) {
        st = motor_status();
        printf("sembrar: FALLO, el test de arranque no pasa%s\n", motor_texto_alarmas(st));
        return;
    }
    e = motor_orden(CTL_SEMBRAR, T_SIEMBRA_MS, &st);
    printf("sembrar: %s%s\n",
           (e == ESP_OK && (st & ST_SEMBRADO)) ? "ok" : motor_texto_err(e), motor_texto_alarmas(st));
}

static void cmd_borrar(void)
{
    if (motor_reg_escribir1(REG_CONTROL, CTL_BORRAR_ALM) != ESP_OK) { printf("borrar: ERROR I2C\n"); return; }
    uint8_t st = motor_status();
    printf("borrar: alarmas%s; hay que repetir el test de arranque\n",
           motor_texto_alarmas(st)[0] ? motor_texto_alarmas(st) : " bajadas");
}

static void cmd_generar(void)
{
    uint8_t st;
    esp_err_t e = motor_orden(CTL_GENERAR, T_ORDEN_MS, &st);
    if (e != ESP_OK) {
        printf("generar: FALLO, %s%s\n", motor_texto_err(e), motor_texto_alarmas(st));
        /* Rechazada: la clave del motor no cambio. En otro caso ya no se sabe. */
        if (e != ESP_ERR_INVALID_STATE) hay_clave = false;
        return;
    }
    if (!(st & ST_CLAVE_VALIDA)) {
        printf("generar: FALLO, sin clave valida\n");
        hay_clave = false;
        return;
    }
    if (st & ST_MODO_TEST) {
        static const uint8_t cero[16] = {0};
        if (motor_reg_leer(REG_CLAVE, clave_provisionada, 16) != ESP_OK) {
            printf("generar: ERROR I2C al leer la clave\n");
            hay_clave = false;
            return;
        }
        hay_clave = !iguales(clave_provisionada, cero, 16);
        imprimir_hex("clave", clave_provisionada, 16);
        printf("provision: %s\n", hay_clave ? "ok" : "FALLO, clave nula");
    } else {
        /* El motor cambio de clave y la provisionada ya no vale: seguir con
         * ella contaria todos los retos como fallos criptograficos. */
        hay_clave = false;
        printf("generar: ok, clave no exportable sin modo test\n");
    }
}

/* Aleatorio del DRBG hacia el PC. Es una generacion independiente de la
 * clave: el registro ALEATORIO nunca contiene la clave. */
static void cmd_aleatorio(int n)
{
    uint8_t b[32];
    for (int i = 0; i < n; i++) {
        /* Un rechazo o un fallo de bus no pueden llegar al PC con un CRC
         * valido y entrar en la estadistica. */
        esp_err_t e = motor_aleatorio(b);
        if (e != ESP_OK) {
            uint8_t st = motor_status();
            printf("aleatorio: FALLO en el bloque %d, %s%s%s\n", i, motor_texto_err(e),
                   (st & ST_SEMBRADO) ? "" : " (sin sembrar)", motor_texto_alarmas(st));
            return;
        }
        trama_pc('D', b, 32);
    }
}

/* Cuentas del ultimo cmd_reto, para el banco en host. */
static struct { int aciertos, fallos, errores; } ult_reto;

static void cmd_reto(int n)
{
    ult_reto.aciertos = ult_reto.fallos = ult_reto.errores = 0;
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
        /* En este banco basta con que el nonce no se repita. En un producto
         * tiene que ser impredecible, o se pueden pedir respuestas por
         * adelantado: sin radio ni ruido de arranque esp_fill_random no lo
         * es (docs/esp32_reinicios.md, seccion 8). */
        esp_fill_random(nonce, 16);
        motor_io_reiniciar();
        uint8_t st = 0;
        esp_err_t e = ESP_FAIL;
        if (motor_reg_escribir(REG_RETO, nonce, 16) == ESP_OK)
            e = motor_orden(CTL_AUTENTICAR, T_ORDEN_MS, &st);
        motor_reg_leer(REG_ETIQUETA, etiqueta, 16);
        /* Sin respuesta tampoco es criptografia. */
        bool bus_ok = motor_io_ok() && e != ESP_ERR_TIMEOUT;
        int r = mbedtls_cipher_cmac(ci, clave_provisionada, 128, nonce, 16, esperada);
        if (r != 0) {
            printf("reto: mbedtls_cipher_cmac fallo (%d); el roto es el "
                   "verificador, no el motor\n", r);
            return;
        }
        if (!bus_ok) {
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
    ult_reto.aciertos = aciertos;
    ult_reto.fallos = fallos;
    ult_reto.errores = errores;
}

static void cmd_crudo(int n)
{
    uint8_t trozo[512];
    /* Sin modo test CAPTURA se lee como ceros: saldrian tramas de ceros con
     * CRC valido. */
    if (!(motor_status() & ST_MODO_TEST)) { printf("crudo: CAPTURA solo se lee en modo test\n"); return; }
    for (int t = 0; t < n; t++) {
        motor_io_reiniciar();
        motor_reg_escribir1(REG_CONTROL, CTL_CAPTURAR);
        uint8_t st = 0;
        for (int k = 0; k < 2000 && !(st & ST_CAPTURA_LLENA); k++) {
            st = motor_status();
            if (!(st & ST_CAPTURA_LLENA)) vTaskDelay(1);
        }
        if (!(st & ST_CAPTURA_LLENA)) { printf("crudo: captura no llena\n"); return; }
        for (uint8_t pag = 0; pag < 4; pag++) {
            motor_reg_escribir1(REG_CFG_PAG, pag);
            motor_reg_leer(REG_CAPTURA, trozo + 128 * pag, 128);
        }
        if (!motor_io_ok()) { printf("crudo: ERROR I2C en el trozo %d, no se envia\n", t); return; }
        trama_pc('R', trozo, 512);
    }
}

static void cmd_esp(int n)
{
    uint8_t b[32];
    for (int i = 0; i < n; i++) {
        esp_fill_random(b, 32);
        trama_pc('E', b, 32);
        /* Sin ceder la CPU el task watchdog salta cada 5 s y su mensaje se
         * mezcla con una trama (40 tramas perdidas en 32768 el 19-09). */
        if ((i & 31) == 31) vTaskDelay(1);
    }
}

/* ---- consola minima --------------------------------------------------- */
static void bucle_consola(void)
{
    char linea[64];
    printf("verificador listo. comandos: id sembrar borrar generar reto N aleatorio N crudo N esp N\n");
    for (;;) {
        if (!fgets(linea, sizeof linea, stdin)) { vTaskDelay(pdMS_TO_TICKS(50)); continue; }
        char cmd[16] = {0}; int arg = 1;
        sscanf(linea, "%15s %d", cmd, &arg);
        if      (!strcmp(cmd, "id"))      cmd_id();
        else if (!strcmp(cmd, "sembrar")) cmd_sembrar();
        else if (!strcmp(cmd, "borrar"))  cmd_borrar();
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
    ESP_ERROR_CHECK(motor_abrir(0, PIN_SDA, PIN_SCL));
    cmd_id();
    bucle_consola();
}
