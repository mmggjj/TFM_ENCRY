/* Prueba de reinicios del RNG del ESP32 (SP 800-90B, 3.1.4).
 *
 * Nada mas arrancar, sin radio ni ADC (condicion D), lee RST_BYTES con
 * esp_fill_random y los saca por UART en hex con su CRC32. El PC resetea
 * el chip por EN y repite (analysis/reinicios_esp32.py). La lectura va lo
 * primero de app_main para que nada del programa toque el RNG antes.
 *
 * El mismo fuente se compila en firmware/reinicios_sin_ruido, cuyo
 * bootloader no enciende la fuente de entropia del arranque. */
#include <stdio.h>
#include <stdint.h>
#include "esp_random.h"
#include "esp_system.h"
#include "esp_mac.h"
#include "esp_timer.h"
#include "esp_cpu.h"
#include "esp_rom_crc.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define RST_BYTES 1024
#define BYTES_LINEA 64

#ifndef VARIANTE
#define VARIANTE "normal"
#endif

static uint8_t s_buf[RST_BYTES];

void app_main(void)
{
    uint32_t ccount = esp_cpu_get_cycle_count();
    int64_t t_us = esp_timer_get_time();
    esp_fill_random(s_buf, RST_BYTES);

    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    printf("### RST_BEGIN mac=%02x:%02x:%02x:%02x:%02x:%02x variante=%s bytes=%d "
           "reset=%d t_us=%lld ccount=%lu\n",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], VARIANTE, RST_BYTES,
           (int)esp_reset_reason(), (long long)t_us, (unsigned long)ccount);
    for (int i = 0; i < RST_BYTES; i += BYTES_LINEA) {
        for (int j = 0; j < BYTES_LINEA; j++) {
            printf("%02x", s_buf[i + j]);
        }
        printf("\n");
    }
    printf("### RST_END crc32=0x%08lx\n",
           (unsigned long)esp_rom_crc32_le(0, s_buf, RST_BYTES));
    fflush(stdout);

    for (;;) {
        vTaskDelay(portMAX_DELAY);
    }
}
