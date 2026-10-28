/* Medidor con lecturas firmadas: demostracion de uso del motor de claves
 * en un producto con ESP32-C3 (ESP-IDF 5.x).
 *
 * El equipo es un medidor de energia generico. Pide al motor aleatorio
 * por I2C para generar su clave ECDSA P-256, que nunca sale del chip;
 * publica la clave publica y, si hace falta certificado, una peticion
 * (CSR) firmada con ella; y firma cada lectura de energia, de forma que
 * quien la reciba (nube, servidor, PC) comprueba integridad y origen sin
 * fiarse del transporte ni del almacenamiento intermedio. El motor solo
 * entra en la generacion de la clave: si esta en alarma o sin sembrar, no
 * hay clave; la firma de lecturas no depende de el.
 *
 * El acceso al motor esta en el componente motor_i2c; la firma y el
 * formato de lectura en lectura.c (solo mbedtls). En el PC,
 * analysis/verifica_lecturas.py comprueba las tramas.
 *
 * Comandos por consola (UART 115200):
 *   id         lee ID, VERSION, STATUS y DIAG del motor
 *   sembrar    espera al test de arranque y siembra el DRBG del motor
 *   borrar     baja las alarmas de salud del motor
 *   clave      genera la clave del equipo con aleatorio del motor
 *   publica    manda la clave publica al PC (trama P)
 *   csr        imprime una peticion de certificado PEM para el equipo
 *   lectura N  manda N lecturas firmadas al PC (tramas L), una por segundo
 *   olvidar    borra la clave privada
 */

#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_random.h"
#include "esp_rom_crc.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "mbedtls/platform_util.h"
#include "motor_i2c.h"
#include "lectura.h"

static const char *TAG = "medidor";

/* Pines I2C. En el ESP32-C3 no hay pines por defecto; estos son los de
 * los ejemplos de ESP-IDF. En el ESP32 clasico, los de siempre. */
#if CONFIG_IDF_TARGET_ESP32
#define PIN_SDA          21
#define PIN_SCL          22
#else
#define PIN_SDA          5
#define PIN_SCL          6
#endif

/* Divisor del anillo con el que se siembra, del rango caracterizado. */
#define CFG_KD_SIEMBRA   24

#define INTERVALO_MS     1000u   /* entre lecturas; un medidor real, 60 s */

static clave_equipo_t clave;
static lectura_t actual;          /* la ultima lectura emitida */
static uint64_t energia_mwh;      /* acumulado con mas resolucion que Wh */
static uint32_t ult_instante_ms;

/* La secuencia tiene que crecer tambien a traves de los reinicios, o el
 * receptor rechazaria todo lo posterior a un reinicio como repetido (si
 * guarda la ultima) o aceptaria reinyecciones de antes (si no la guarda).
 * Byte alto: contador de arranques en NVS; 24 bits bajos: lecturas desde
 * el arranque. */
static uint32_t arranques;
static uint32_t n_lecturas;
#define MAX_LECTURAS_ARRANQUE 0xFFFFFFu

static int rng_chip(void *ctx, unsigned char *salida, size_t n)
{
    (void)ctx;
    esp_fill_random(salida, n);
    return 0;
}

/* Trama al PC: 'F' tipo len[2] payload crc32[4], en hex por linea. */
static void trama_pc(char tipo, const uint8_t *d, size_t n)
{
    uint32_t crc = esp_rom_crc32_le(0, d, n);
    printf("F%c%04zx", tipo, n);
    for (size_t i = 0; i < n; i++) printf("%02x", d[i]);
    printf("%08" PRIx32 "\n", crc);
}

static uint32_t ahora_ms(void)
{
    return (uint32_t)(xTaskGetTickCount() * portTICK_PERIOD_MS);
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
    /* pila_libre: minimo de pila que le ha quedado a esta tarea desde el
     * arranque (bytes en ESP-IDF); dice si los 12 KiB del sdkconfig sobran. */
    printf("id 0x%02x version 0x%02x status 0x%02x sembrado=%d ocupado=%d alm_rct=%d "
           "alm_apt=%d arrancado=%d rechazada=%d agotado=%d clave_equipo=%d bloques_rng=%" PRIu32
           " arranques=%" PRIu32 " pila_libre=%u\n",
           id, ver, st,
           !!(st & ST_SEMBRADO), !!(st & ST_OCUPADO), !!(st & ST_ALM_RCT),
           !!(st & ST_ALM_APT), !!(diag & DG_ARRANCADO), !!(diag & DG_RECHAZADA),
           !!(diag & DG_AGOTADO), clave.valida, motor_rng_bloques(), arranques,
           (unsigned)uxTaskGetStackHighWaterMark(NULL));
}

static void cmd_sembrar(void)
{
    uint8_t st = 0, diag = 0;
    if (motor_reg_escribir1(REG_CFG_KD, CFG_KD_SIEMBRA) != ESP_OK) { printf("sembrar: FALLO, ERROR I2C\n"); return; }
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

static void cmd_publica(void)
{
    uint8_t der[PUBLICA_MAX];
    size_t n = 0;
    int r = clave_publica(&clave, der, sizeof der, &n);
    if (r != 0) { printf("publica: FALLO, sin clave (%d)\n", r); return; }
    trama_pc('P', der, n);
}

/* La clave privada se guarda en NVS para que sobreviva al reinicio: sin
 * eso cada arranque pediria una clave nueva al motor y la publica
 * registrada dejaria de valer. OJO: NVS a secas la guarda en claro en la
 * flash. En producto hay que activar el cifrado de flash y de NVS
 * (CONFIG_NVS_ENCRYPTION, misma API), o dejar la clave en el motor cuando
 * haga de elemento seguro. Aqui se avisa en vez de fingir que no pasa. */
static bool nvs_clave(bool guardar)
{
    nvs_handle_t h;
    uint8_t der[PRIVADA_MAX];
    size_t n = sizeof der;
    bool ok = false;
    if (nvs_open("medidor", NVS_READWRITE, &h) != ESP_OK) return false;
    if (guardar) {
        ok = clave_exportar(&clave, der, sizeof der, &n) == 0 &&
             nvs_set_blob(h, "clave", der, n) == ESP_OK && nvs_commit(h) == ESP_OK;
    } else {
        ok = nvs_get_blob(h, "clave", der, &n) == ESP_OK && clave_importar(&clave, der, n) == 0;
    }
    nvs_close(h);
    mbedtls_platform_zeroize(der, sizeof der);
    return ok;
}

static void nvs_olvidar_clave(void)
{
    nvs_handle_t h;
    if (nvs_open("medidor", NVS_READWRITE, &h) != ESP_OK) return;
    nvs_erase_key(h, "clave");
    nvs_commit(h);
    nvs_close(h);
}

static void cmd_clave(void)
{
    uint32_t antes = motor_rng_bloques();
    /* Toda la entropia de la clave sale del motor. Si el motor rechaza
     * (sin sembrar, alarma) o el bus falla, no hay clave nueva: no se
     * rellena con otra fuente. */
    motor_io_reiniciar();
    int r = clave_generar(&clave, motor_rng, NULL);
    if (r != 0) {
        const char *sigue = clave.valida ? "sigue la clave anterior" : "no hay clave";
        if (!motor_io_ok()) {
            /* Con el bus caido STATUS se lee como 0 y pareceria "sin sembrar". */
            printf("clave: FALLO, ERROR I2C (%d); %s\n", r, sigue);
            return;
        }
        uint8_t st = motor_status(), diag = 0;
        motor_reg_leer(REG_DIAG, &diag, 1);
        printf("clave: FALLO, el motor no da aleatorio (%d)%s%s%s; %s\n", r,
               (st & ST_SEMBRADO) ? "" : " (sin sembrar)", motor_texto_alarmas(st),
               (diag & DG_AGOTADO) ? " (contador agotado: resembrar)" : "", sigue);
        return;
    }
    printf("clave: ok, P-256 con %" PRIu32 " bloques de 32 bytes del motor; %s\n",
           motor_rng_bloques() - antes,
           nvs_clave(true) ? "guardada en NVS (en claro si la flash no va cifrada)"
                           : "NO guardada: sin NVS, se pierde al reiniciar");
    cmd_publica();
}

static void cmd_csr(void)
{
    static char pem[CSR_MAX];
    char sujeto[64];
    snprintf(sujeto, sizeof sujeto, "CN=medidor-%02x%02x%02x%02x%02x%02x%02x%02x",
             actual.id[0], actual.id[1], actual.id[2], actual.id[3],
             actual.id[4], actual.id[5], actual.id[6], actual.id[7]);
    int r = clave_csr(&clave, sujeto, pem, sizeof pem, rng_chip, NULL);
    if (r != 0) { printf("csr: FALLO (%d)%s\n", r, clave.valida ? "" : ", sin clave"); return; }
    printf("%s", pem);
}

/* Modelo del medidor: una carga que oscila entre 1000 y 1300 W. */
static void siguiente_lectura(void)
{
    uint32_t t = ahora_ms();
    energia_mwh += (uint64_t)actual.potencia_w * (t - ult_instante_ms) / 3600u;
    ult_instante_ms = t;
    n_lecturas++;
    actual.secuencia = (arranques << 24) | n_lecturas;
    actual.instante = t / 1000u;
    actual.energia_wh = (uint32_t)(energia_mwh / 1000u);
    actual.potencia_w = 1000u + 50u * (n_lecturas % 7u);
}

static void cmd_lectura(int n)
{
    uint8_t trama[LECTURA_BYTES + FIRMA_MAX];
    size_t nf = 0;
    if (!clave.valida) { printf("lectura: primero 'clave'\n"); return; }
    if (n > 1000) { printf("lectura: como mucho 1000 de una vez\n"); return; }
    for (int i = 0; i < n; i++) {
        if (n_lecturas >= MAX_LECTURAS_ARRANQUE) { printf("lectura: secuencia agotada, reiniciar\n"); return; }
        siguiente_lectura();
        lectura_serializar(&actual, trama);
        int r = clave_firmar(&clave, trama, trama + LECTURA_BYTES, FIRMA_MAX, &nf, rng_chip, NULL);
        if (r != 0) { printf("lectura: FALLO al firmar (%d)\n", r); return; }
        trama_pc('L', trama, LECTURA_BYTES + nf);
        if (i + 1 < n) vTaskDelay(pdMS_TO_TICKS(INTERVALO_MS));
    }
}

static void cmd_olvidar(void)
{
    clave_borrar(&clave);
    nvs_olvidar_clave();
    printf("olvidar: clave borrada de la RAM y de la NVS\n");
}

/* ---- consola minima --------------------------------------------------- */
/* Lee una linea de la consola acumulando caracter a caracter. Con el
 * stdin no bloqueante de ESP-IDF, fgets devuelve lo que haya llegado
 * cuando se queda sin bytes, y por un USB-serie real los bytes de una
 * orden llegan con huecos: en la placa 'lectura 1' llego como "le",
 * "ctu", "r", "a" y cada trozo era un comando desconocido. En QEMU y en
 * el banco en host la linea llega entera y el fallo no se ve. */
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
    printf("medidor listo. comandos: id sembrar borrar clave publica csr lectura N olvidar\n");
    for (;;) {
        if (!leer_linea(linea, sizeof linea)) { vTaskDelay(pdMS_TO_TICKS(20)); continue; }
        char cmd[16] = {0}; int arg = 1;
        sscanf(linea, "%15s %d", cmd, &arg);
        if      (!strcmp(cmd, "id"))      cmd_id();
        else if (!strcmp(cmd, "sembrar")) cmd_sembrar();
        else if (!strcmp(cmd, "borrar"))  cmd_borrar();
        else if (!strcmp(cmd, "clave"))   cmd_clave();
        else if (!strcmp(cmd, "publica")) cmd_publica();
        else if (!strcmp(cmd, "csr"))     cmd_csr();
        else if (!strcmp(cmd, "lectura")) cmd_lectura(arg);
        else if (!strcmp(cmd, "olvidar")) cmd_olvidar();
        else if (cmd[0])                  printf("comando desconocido: %s\n", cmd);
    }
}

/* Contador de arranques en NVS. Sin NVS se avisa y la secuencia solo vale
 * dentro del arranque: nunca se firma con una secuencia que parezca
 * persistente sin serlo. */
static void contar_arranque(void)
{
    nvs_handle_t h;
    uint32_t n = 0;
    arranques = 0;
    esp_err_t e = nvs_flash_init();
    if (e == ESP_ERR_NVS_NO_FREE_PAGES || e == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        e = nvs_flash_init();
    }
    if (e == ESP_OK) e = nvs_open("medidor", NVS_READWRITE, &h);
    if (e != ESP_OK) {
        ESP_LOGE(TAG, "sin NVS (0x%x): la secuencia no sobrevive al reinicio", e);
        return;
    }
    e = nvs_get_u32(h, "arranques", &n);
    if (e != ESP_OK && e != ESP_ERR_NVS_NOT_FOUND) n = 0;
    n++;
    if (nvs_set_u32(h, "arranques", n) != ESP_OK || nvs_commit(h) != ESP_OK) {
        ESP_LOGE(TAG, "NVS no guarda el contador de arranques");
        n = 0;
    }
    nvs_close(h);
    arranques = n & 0xFFu;
}

static void iniciar_medidor(void)
{
    /* clave_borrar y no clave_iniciar: si hubiera una clave (el banco
     * "reinicia" llamando aqui otra vez) se borra y se libera; sobre el
     * estatico a cero es lo mismo que iniciar. Lo encontro ASan. */
    clave_borrar(&clave);
    memset(&actual, 0, sizeof actual);
    /* id del equipo: la MAC base del chip, que es unica, rellena a 8 bytes */
    esp_efuse_mac_get_default(actual.id);
    actual.potencia_w = 1000;
    energia_mwh = 0;
    n_lecturas = 0;
    ult_instante_ms = ahora_ms();
    contar_arranque();
    /* Si hay clave guardada se recupera: el equipo sigue firmando con la
     * misma identidad que registro. Si no, hace falta 'clave'. */
    if (nvs_clave(false)) printf("clave recuperada de la NVS\n");
}

void app_main(void)
{
    iniciar_medidor();
    ESP_ERROR_CHECK(motor_abrir(0, PIN_SDA, PIN_SCL));
    cmd_id();
    bucle_consola();
}
