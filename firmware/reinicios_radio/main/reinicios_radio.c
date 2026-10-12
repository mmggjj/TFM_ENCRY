/* Prueba de reinicios del RNG del ESP32 con la radio encendida.
 *
 * Como firmware/reinicios, pero con dos lecturas de RST_BYTES por arranque:
 *  - "antes": lo primero de app_main, con la radio apagada (igual que en
 *    firmware/reinicios). Es la huella del estado del RNG al arrancar.
 *  - "despues": tras arrancar el Wi-Fi (esp_wifi_start, sin asociarse, como
 *    el TFM_RNG en sus condiciones A y B) y esperar RADIO_ESPERA_MS. La
 *    espera es un vTaskDelay, asi que la lectura cae en un tick de FreeRTOS.
 * Las dos se leen antes de sacar nada por la UART. Cada bloque va en hex
 * con su CRC32 y al final "### RST_FIN".
 *
 * Con SIN_RADIO no se toca el Wi-Fi: se espera lo mismo con vTaskDelay y se
 * lee en un tick igual. Es el control: la misma variacion de tiempos sin
 * radio.
 *
 * firmware/reinicios_radio_sin_ruido compila este mismo fuente con el
 * bootloader que no enciende la fuente de entropia del arranque, con y sin
 * SIN_RADIO. */
#include <stdio.h>
#include <stdint.h>
#include "esp_random.h"
#include "esp_system.h"
#include "esp_mac.h"
#include "esp_timer.h"
#include "esp_cpu.h"
#include "esp_rom_crc.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define RST_BYTES 1024
#define BYTES_LINEA 64
#define RADIO_ESPERA_MS 200
#define ARRANQUE_WIFI_MS 150   /* lo que tarda en volver esp_wifi_start, aprox. */

#ifndef VARIANTE
#define VARIANTE "radio"
#endif

static uint8_t s_antes[RST_BYTES];
static uint8_t s_despues[RST_BYTES];

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

void app_main(void)
{
    uint32_t cc_antes = esp_cpu_get_cycle_count();
    int64_t t_antes = esp_timer_get_time();
    esp_fill_random(s_antes, RST_BYTES);

#ifdef SIN_RADIO
    vTaskDelay(pdMS_TO_TICKS(ARRANQUE_WIFI_MS));
    int64_t t_on = esp_timer_get_time();
#else
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
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
    int64_t t_on = esp_timer_get_time();
#endif
    vTaskDelay(pdMS_TO_TICKS(RADIO_ESPERA_MS));

    uint32_t cc_despues = esp_cpu_get_cycle_count();
    int64_t t_despues = esp_timer_get_time();
    esp_fill_random(s_despues, RST_BYTES);

    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    sacar(mac, "antes", s_antes, t_antes, cc_antes);
    sacar(mac, "despues", s_despues, t_despues, cc_despues);
    printf("### RST_FIN t_on_us=%lld espera_ms=%d\n", (long long)t_on, RADIO_ESPERA_MS);
    fflush(stdout);

    for (;;) {
        vTaskDelay(portMAX_DELAY);
    }
}
