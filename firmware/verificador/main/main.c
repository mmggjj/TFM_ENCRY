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
 *   kd [N]    escribe CFG_KD (K_D = 2^N) y lo relee; sin N solo lo lee
 *   crudo N   vuelca N trozos del buffer de captura al PC (4096 bits cada uno,
 *             no contiguos entre si) con su tiempo de llenado
 *   flujo N   vuelca N bytes CONSECUTIVOS de bits crudos (captura continua,
 *             registro FLUJO) en tramas C numeradas; si la FIFO del motor se
 *             desborda o falla el bus, lo dice y la tira no vale
 *   esp N     vuelca N bloques de esp_random() al PC (comparacion)
 *   cero      zeroiza el motor (clave, DRBG, RETO, ALEATORIO)
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
    if (ver < MOTOR_VERSION_MIN) ESP_LOGE(TAG, "VERSION 0x%02x: motor sin DIAG ni test de arranque", ver);
    motor_reg_leer(REG_DIAG, &diag, 1);
    st = motor_status();
    printf("id 0x%02x version 0x%02x status 0x%02x sembrado=%d ocupado=%d alm_rct=%d "
           "alm_apt=%d clave=%d captura=%d etiqueta=%d test=%d arrancado=%d rechazada=%d agotado=%d\n",
           id, ver, st,
           !!(st & ST_SEMBRADO), !!(st & ST_OCUPADO), !!(st & ST_ALM_RCT),
           !!(st & ST_ALM_APT), !!(st & ST_CLAVE_VALIDA), !!(st & ST_CAPTURA_LLENA),
           !!(st & ST_ETIQ_LISTA), !!(st & ST_MODO_TEST),
           !!(diag & DG_ARRANCADO), !!(diag & DG_RECHAZADA), !!(diag & DG_AGOTADO));
}

/* Zeroizacion del motor: clave, estado del DRBG, RETO y ALEATORIO a cero.
 * La clave provisionada deja de valer. */
static void cmd_cero(void)
{
    uint8_t st;
    esp_err_t e = motor_orden(CTL_BORRAR_TODO, T_ORDEN_MS, &st);
    hay_clave = false;
    printf("cero: %s%s\n", e == ESP_OK ? "ok, motor borrado; hay que sembrar de nuevo" : motor_texto_err(e),
           (e == ESP_OK && ((st & ST_SEMBRADO) || (st & ST_CLAVE_VALIDA))) ? " PERO STATUS sigue con estado" : "");
}

static void cmd_sembrar(void)
{
    uint8_t st = 0, diag = 0;
    /* El motor no siembra hasta pasar el test de arranque: 1024 muestras sin
     * alarma desde el reset o el ultimo borrado. */
    /* Los plazos salen del CFG_KD actual: con el anillo lento de la FPGA y
     * CFG_KD = 24 el test de arranque puede tardar minutos. */
    const uint32_t plazo = motor_plazo_arranque_ms();
    if (plazo > T_ARRANQUE_MS) printf("sembrar: esperando el test de arranque (hasta %" PRIu32 " s)\n", plazo / 1000);
    esp_err_t e = motor_esperar_arranque(plazo, &diag);
    if (e == ESP_FAIL) { printf("sembrar: FALLO, ERROR I2C\n"); return; }
    if (e != ESP_OK) {
        st = motor_status();
        printf("sembrar: FALLO, el test de arranque no pasa%s\n", motor_texto_alarmas(st));
        return;
    }
    e = motor_orden(CTL_SEMBRAR, motor_plazo_siembra_ms(), &st);
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

static void cmd_kd(int v)
{
    uint8_t leido = 0xff;
    motor_io_reiniciar();
    if (v == -1) {                      /* "kd" solo: lo lee */
        motor_reg_leer(REG_CFG_KD, &leido, 1);
        if (!motor_io_ok()) printf("kd: ERROR I2C\n");
        else printf("kd leido %u\n", leido);
        return;
    }
    if (v < 0 || v > 24) { printf("kd: fuera de rango (0 a 24)\n"); return; }
    motor_reg_escribir1(REG_CFG_KD, (uint8_t)v);
    motor_reg_leer(REG_CFG_KD, &leido, 1);
    if (!motor_io_ok()) { printf("kd: ERROR I2C\n"); return; }
    /* Con una orden en curso el motor ignora la escritura. */
    printf("kd %d leido %u %s\n", v, leido, leido == v ? "ok" : "IGNORADO");
}

static void cmd_crudo(int n)
{
    uint8_t trozo[512];
    uint8_t kd = 24;
    /* Sin modo test CAPTURA se lee como ceros: saldrian tramas de ceros con
     * CRC valido. */
    if (!(motor_status() & ST_MODO_TEST)) { printf("crudo: CAPTURA solo se lee en modo test\n"); return; }
    motor_reg_leer(REG_CFG_KD, &kd, 1);
    const uint32_t plazo = motor_plazo_bits_ms(4096, 2000);
    for (int t = 0; t < n; t++) {
        motor_io_reiniciar();
        motor_reg_escribir1(REG_CONTROL, CTL_CAPTURAR);
        uint8_t diag = 0;
        motor_reg_leer(REG_DIAG, &diag, 1);
        if (diag & DG_RECHAZADA) { printf("crudo: captura rechazada (motor ocupado?)\n"); return; }
        const TickType_t t0 = xTaskGetTickCount();
        uint8_t st = motor_status();
        while (!(st & ST_CAPTURA_LLENA)) {
            if (xTaskGetTickCount() - t0 >= pdMS_TO_TICKS(plazo)) break;
            vTaskDelay(pdMS_TO_TICKS(plazo > 10000 ? 10 : 1));
            st = motor_status();
        }
        const uint32_t ms = (uint32_t)((xTaskGetTickCount() - t0) * portTICK_PERIOD_MS);
        if (!(st & ST_CAPTURA_LLENA)) { printf("crudo: captura no llena en %" PRIu32 " ms (kd %u)\n", ms, kd); return; }
        for (uint8_t pag = 0; pag < 4; pag++) {
            motor_reg_escribir1(REG_CFG_PAG, pag);
            motor_reg_leer(REG_CAPTURA, trozo + 128 * pag, 128);
        }
        if (!motor_io_ok()) { printf("crudo: ERROR I2C en el trozo %d, no se envia\n", t); return; }
        /* El tiempo de llenado da la tasa de bits: 4096 / ms, resolucion
         * de un tick (1 ms) mas el sondeo. */
        printf("crudo %d kd %u ms %" PRIu32 "\n", t, kd, ms);
        trama_pc('R', trozo, 512);
    }
}

/* Captura continua (docs/captura_continua.md): el motor mete los bits
 * crudos en una FIFO y aqui se vacia mientras se llena. Cada trama C lleva
 * su numero (4 bytes, bajo primero) y hasta 128 bytes de la tira. La tira
 * solo vale si acaba con "flujo fin ... ok": el PC no da por buena una
 * captura cortada. El cuello es esta UART: a 115200 salen unos 5 kB/s. */
#define FLUJO_TRAMA 128
static struct { uint32_t bytes; bool ok; } ult_flujo;

static void cmd_flujo(int n_bytes)
{
    uint8_t buf[1 + MOTOR_FLUJO_MAX], trama[4 + FLUJO_TRAMA];
    uint8_t kd = 24, fl = 0, diag = 0;
    ult_flujo.bytes = 0;
    ult_flujo.ok = false;
    if (n_bytes < 1) { printf("flujo: N bytes, N >= 1\n"); return; }
    motor_io_reiniciar();
    const uint8_t st = motor_status();
    if (!motor_io_ok()) { printf("flujo: ERROR I2C al arrancar\n"); return; }
    if (!(st & ST_MODO_TEST)) { printf("flujo: solo en modo test\n"); return; }
    motor_reg_leer(REG_CFG_KD, &kd, 1);
    motor_reg_escribir1(REG_FLUJO, FL_ACTIVO);
    motor_reg_leer(REG_DIAG, &diag, 1);
    motor_reg_leer(REG_FLUJO, &fl, 1);
    if (!motor_io_ok()) { printf("flujo: ERROR I2C al arrancar\n"); return; }
    if ((diag & DG_RECHAZADA) || !(fl & FL_ACTIVO)) {
        printf("flujo: rechazado (motor ocupado, captura en curso, CFG_KD bajo o motor sin FLUJO)\n");
        return;
    }
    const uint32_t plazo = motor_plazo_bits_ms(8 * 32, 2000);
    printf("flujo inicio kd %u bytes %d\n", kd, n_bytes);
    const uint32_t pedidos = (uint32_t)n_bytes;
    uint32_t total = 0, seq = 0;
    size_t en_trama = 0;
    const char *error = NULL;
    const TickType_t t0 = xTaskGetTickCount();
    TickType_t t_ult = t0;
    while (total < pedidos) {
        motor_reg_leer(REG_FLUJO_N, buf, sizeof buf);
        if (!motor_io_ok()) { error = "ERROR I2C"; break; }
        const uint8_t n = buf[0];
        if (n > MOTOR_FLUJO_MAX) { error = "FLUJO_N fuera de rango"; break; }
        for (uint8_t i = 0; i < n && total < pedidos; i++) {
            trama[4 + en_trama++] = buf[1 + i];
            total++;
            if (en_trama == FLUJO_TRAMA || total == pedidos) {
                trama[0] = (uint8_t)seq; trama[1] = (uint8_t)(seq >> 8);
                trama[2] = (uint8_t)(seq >> 16); trama[3] = (uint8_t)(seq >> 24);
                trama_pc('C', trama, 4 + en_trama);
                seq++;
                en_trama = 0;
            }
        }
        if (n) t_ult = xTaskGetTickCount();
        if (n < MOTOR_FLUJO_MAX && total < pedidos) {      /* FIFO vacia: mirar como va y ceder */
            motor_reg_leer(REG_FLUJO, &fl, 1);
            if (!motor_io_ok()) { error = "ERROR I2C"; break; }
            if (fl & FL_DESBORDADO) { error = "DESBORDADO (el maestro no vacia a tiempo: subir CFG_KD)"; break; }
            if (!(fl & FL_ACTIVO)) { error = "el motor paro el flujo (modo test?)"; break; }
            if (xTaskGetTickCount() - t_ult >= pdMS_TO_TICKS(plazo)) { error = "sin datos"; break; }
            vTaskDelay(1);
        }
    }
    const uint32_t ms = (uint32_t)((xTaskGetTickCount() - t0) * portTICK_PERIOD_MS);
    motor_reg_escribir1(REG_FLUJO, 0);
    ult_flujo.bytes = total;
    if (error) {
        printf("flujo: %s tras %" PRIu32 " bytes (kd %u), la tira no vale\n", error, total, kd);
        return;
    }
    ult_flujo.ok = true;
    /* bytes * 8 * 2^kd / ms da la frecuencia de ro2, con la resolucion del
     * tick sobre toda la captura. */
    printf("flujo fin bytes %" PRIu32 " kd %u ms %" PRIu32 " ok\n", total, kd, ms);
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
/* Lee una linea acumulando caracter a caracter: con el stdin no bloqueante
 * de ESP-IDF, fgets devuelve trozos cuando los bytes de una orden llegan
 * con huecos por el USB-serie (visto en el medidor en placa: 'lectura 1'
 * llego como "le", "ctu", "r", "a"). En QEMU la linea llega entera. */
static bool leer_linea(char *linea, size_t n)
{
    static size_t pos;
    int c;
    while ((c = fgetc(stdin)) != EOF) {
        if (c == '\r') continue;
        if (c == '\n') { linea[pos] = '\0'; pos = 0; return true; }
        if (pos + 1 < n) linea[pos++] = (char)c;
    }
    clearerr(stdin);
    return false;
}

static void bucle_consola(void)
{
    char linea[64];
    printf("verificador listo. comandos: id sembrar borrar generar reto N aleatorio N kd N crudo N flujo N esp N cero\n");
    for (;;) {
        if (!leer_linea(linea, sizeof linea)) { vTaskDelay(pdMS_TO_TICKS(20)); continue; }
        char cmd[16] = {0}; int arg = 1;
        const int campos = sscanf(linea, "%15s %d", cmd, &arg);
        if      (!strcmp(cmd, "id"))      cmd_id();
        else if (!strcmp(cmd, "sembrar")) cmd_sembrar();
        else if (!strcmp(cmd, "borrar"))  cmd_borrar();
        else if (!strcmp(cmd, "generar")) cmd_generar();
        else if (!strcmp(cmd, "reto"))    cmd_reto(arg);
        else if (!strcmp(cmd, "aleatorio")) cmd_aleatorio(arg);
        else if (!strcmp(cmd, "kd"))      cmd_kd(campos >= 2 ? arg : -1);
        else if (!strcmp(cmd, "crudo"))   cmd_crudo(arg);
        else if (!strcmp(cmd, "flujo"))   cmd_flujo(arg);
        else if (!strcmp(cmd, "esp"))     cmd_esp(arg);
        else if (!strcmp(cmd, "cero"))    cmd_cero();
        else if (cmd[0])                  printf("comando desconocido: %s\n", cmd);
    }
}

void app_main(void)
{
    ESP_ERROR_CHECK(motor_abrir(0, PIN_SDA, PIN_SCL));
    cmd_id();
    bucle_consola();
}
