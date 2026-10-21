/* Prueba de reinicios del RNG del ESP32: que fuente mete ruido y cuanto.
 *
 * Bootloader sin la fuente de entropia del arranque (como
 * firmware/reinicios_sin_ruido). En cada arranque:
 *  - "antes": RST_BYTES leidos lo primero de app_main (huella del estado).
 *  - se aplica la FUENTE del binario durante FUENTE_MS:
 *      CONTROL      nada
 *      WIFI_INIT    nvs + netif + eventos + esp_wifi_init, sin esp_wifi_start
 *                   (la misma actividad de software sin encender la radio;
 *                   esp_wifi_init si enciende el dominio de alimentacion del
 *                   modem, pero no la PHY)
 *      RADIO        lo anterior + esp_wifi_start; FUENTE_MS con la radio
 *                   encendida contados desde que vuelve esp_wifi_start; luego
 *                   esp_wifi_stop. Con sta_disconnected_pm = false: si no, la
 *                   estacion sin conectar duerme la radio antes de que vuelva
 *                   esp_wifi_start y FUENTE_MS no anadiria tiempo de radio.
 *                   esp_phy_rf_get_on_ts() tras start y tras stop dice
 *                   cuando se encendio de verdad (y si stop la desperto).
 *      ADC          lecturas seguidas de adc_oneshot en ADC1 canal 0 (GPIO36),
 *                   igual que la condicion C de firmware/esp32_rng
 *      BOOTRAND     bootloader_random_enable() (SAR ADC en modo prueba hacia
 *                   el RNG, la fuente documentada) y bootloader_random_disable()
 *  - "despues": RST_BYTES leidos en un instante fijo, T_LECTURA_US desde que
 *    arranco el programa, por espera activa sobre esp_timer. Asi el
 *    instante de lectura no depende de lo que tarde la fuente.
 * Cada bloque va en hex con su CRC32 y al final "### RST_FIN".
 *
 * Se compila con: idf.py -B build_<v> -DFUENTE=<n> -DFUENTE_MS=<ms> build
 * (ver main/CMakeLists.txt). */
#include <stdio.h>
#include <stdint.h>
#include "esp_random.h"
#include "esp_system.h"
#include "esp_mac.h"
#include "esp_timer.h"
#include "esp_cpu.h"
#include "esp_rom_crc.h"
#include "esp_wifi.h"
#include "esp_phy_init.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "nvs_flash.h"
#include "esp_adc/adc_oneshot.h"
#include "bootloader_random.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define RST_BYTES 1024
#define BYTES_LINEA 64
#define T_LECTURA_US 800000          /* 800 ms desde el arranque del programa */

#define F_CONTROL 0
#define F_WIFI_INIT 1
#define F_RADIO 2
#define F_ADC 3
#define F_BOOTRAND 4

#ifndef FUENTE
#define FUENTE F_CONTROL
#endif
#ifndef FUENTE_MS
#define FUENTE_MS 0
#endif
#ifndef VARIANTE
#define VARIANTE "fuente_control"
#endif

static uint8_t s_antes[RST_BYTES];
static uint8_t s_despues[RST_BYTES];

static void __attribute__((unused)) espera_us(int64_t us)
{
    int64_t fin = esp_timer_get_time() + us;
    while (esp_timer_get_time() < fin) {
    }
}

static void sacar(const uint8_t mac[6], const char *bloque, const uint8_t *buf,
                  int64_t t_us, uint32_t ccount)
{
    printf("### RST_BEGIN mac=%02x:%02x:%02x:%02x:%02x:%02x variante=%s bloque=%s "
           "bytes=%d reset=%d t_us=%lld ccount=%lu\n",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], VARIANTE, bloque,
           RST_BYTES, (int)esp_reset_reason(), (long long)t_us, (unsigned long)ccount);
    for (int i = 0; i < RST_BYTES; i += BYTES_LINEA) {
        for (int j = 0; j < BYTES_LINEA; j++) {
            printf("%02x", buf[i + j]);
        }
        printf("\n");
    }
    printf("### RST_END bloque=%s crc32=0x%08lx\n", bloque,
           (unsigned long)esp_rom_crc32_le(0, buf, RST_BYTES));
}

#if FUENTE == F_WIFI_INIT || FUENTE == F_RADIO
static void wifi_init(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    cfg.sta_disconnected_pm = false;     /* la radio no duerme sin conexion */
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
}
#endif

void app_main(void)
{
    uint32_t cc_antes = esp_cpu_get_cycle_count();
    int64_t t_antes = esp_timer_get_time();
    esp_fill_random(s_antes, RST_BYTES);

    int64_t t_on = -1, t_off = -1;
    int64_t rf_ini = -1, rf_fin = -1;    /* esp_phy_rf_get_on_ts tras start y tras stop */
    int n_adc = -1, adc_ultimo = -1;     /* lecturas del ADC correctas y la ultima */
#if FUENTE == F_WIFI_INIT
    wifi_init();
    t_on = t_off = esp_timer_get_time();
#elif FUENTE == F_RADIO
    wifi_init();
    ESP_ERROR_CHECK(esp_wifi_start());
    t_on = esp_timer_get_time();
    rf_ini = esp_phy_rf_get_on_ts();
    espera_us((int64_t)FUENTE_MS * 1000);
    ESP_ERROR_CHECK(esp_wifi_stop());
    t_off = esp_timer_get_time();
    rf_fin = esp_phy_rf_get_on_ts();
#elif FUENTE == F_ADC
    adc_oneshot_unit_handle_t unidad;
    adc_oneshot_unit_init_cfg_t ucfg = {.unit_id = ADC_UNIT_1, .ulp_mode = ADC_ULP_MODE_DISABLE};
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&ucfg, &unidad));
    adc_oneshot_chan_cfg_t ccfg = {.atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_12};
    ESP_ERROR_CHECK(adc_oneshot_config_channel(unidad, ADC_CHANNEL_0, &ccfg));
    t_on = esp_timer_get_time();
    int crudo;
    n_adc = 0;
    while (esp_timer_get_time() - t_on < (int64_t)FUENTE_MS * 1000) {
        if (adc_oneshot_read(unidad, ADC_CHANNEL_0, &crudo) == ESP_OK) {
            n_adc++;
            adc_ultimo = crudo;
        }
    }
    ESP_ERROR_CHECK(adc_oneshot_del_unit(unidad));
    t_off = esp_timer_get_time();
#elif FUENTE == F_BOOTRAND
    bootloader_random_enable();
    t_on = esp_timer_get_time();
    espera_us((int64_t)FUENTE_MS * 1000);
    bootloader_random_disable();
    t_off = esp_timer_get_time();
#endif

    int64_t falta = T_LECTURA_US - esp_timer_get_time();
    int tarde = falta < 0;
    while (esp_timer_get_time() < T_LECTURA_US) {
    }
    uint32_t cc_despues = esp_cpu_get_cycle_count();
    int64_t t_despues = esp_timer_get_time();
    esp_fill_random(s_despues, RST_BYTES);

    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    sacar(mac, "antes", s_antes, t_antes, cc_antes);
    sacar(mac, "despues", s_despues, t_despues, cc_despues);
    printf("### RST_FIN t_on_us=%lld t_off_us=%lld fuente_ms=%d tarde=%d "
           "rf_ts_ini=%lld rf_ts_fin=%lld n_adc=%d adc_ultimo=%d\n",
           (long long)t_on, (long long)t_off, FUENTE_MS, tarde,
           (long long)rf_ini, (long long)rf_fin, n_adc, adc_ultimo);
    fflush(stdout);

    for (;;) {
        vTaskDelay(portMAX_DELAY);
    }
}
