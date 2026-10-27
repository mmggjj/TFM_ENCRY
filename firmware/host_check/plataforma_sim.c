/* Plataforma simulada para el banco en el PC: el tiempo lo avanza
 * vTaskDelay, el aleatorio del chip es rand(), el CRC32 es el normal y la
 * MAC es fija. En el chip nada de esto se compila: lo da ESP-IDF. */
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "esp_err.h"
#include "driver/i2c_master.h"
#include "nvs_flash.h"
#include "nvs.h"

extern int motor_n_tramas;
void motor_reset(void);

static uint32_t ticks;

/* NVS: una sola clave u32, que es lo que usa el medidor (contador de
 * arranques). Sobrevive a iniciar_medidor(), que es el "reinicio" del
 * banco. plataforma_nvs_rota la deja inaccesible. */
static uint32_t nvs_valor;
static bool nvs_guardado;
bool plataforma_nvs_rota = false;

esp_err_t nvs_flash_init(void) { return plataforma_nvs_rota ? ESP_FAIL : ESP_OK; }
esp_err_t nvs_flash_erase(void) { nvs_guardado = false; return ESP_OK; }
esp_err_t nvs_open(const char *ns, nvs_open_mode_t m, nvs_handle_t *h)
{ (void)ns; (void)m; *h = 1; return plataforma_nvs_rota ? ESP_FAIL : ESP_OK; }
esp_err_t nvs_get_u32(nvs_handle_t h, const char *k, uint32_t *v)
{ (void)h; (void)k; if (!nvs_guardado) return ESP_ERR_NVS_NOT_FOUND; *v = nvs_valor; return ESP_OK; }
esp_err_t nvs_set_u32(nvs_handle_t h, const char *k, uint32_t v)
{ (void)h; (void)k; nvs_valor = v; nvs_guardado = true; return ESP_OK; }
esp_err_t nvs_commit(nvs_handle_t h) { (void)h; return ESP_OK; }
void nvs_close(nvs_handle_t h) { (void)h; }

void vTaskDelay(uint32_t t) { ticks += t; }
uint32_t xTaskGetTickCount(void) { return ticks; }
uint32_t uxTaskGetStackHighWaterMark(void *t) { (void)t; return 0; }   /* en el PC no hay dato */

esp_err_t i2c_new_master_bus(const i2c_master_bus_config_t *c, i2c_master_bus_handle_t *h)
{ (void)c; *h = NULL; motor_reset(); return ESP_OK; }

esp_err_t i2c_master_bus_add_device(i2c_master_bus_handle_t b,
                                    const i2c_device_config_t *c,
                                    i2c_master_dev_handle_t *h)
{ (void)b; (void)c; *h = NULL; return ESP_OK; }

void esp_fill_random(void *buf, size_t len)
{ for (size_t i = 0; i < len; i++) ((uint8_t *)buf)[i] = (uint8_t)(rand() & 0xff); }
uint32_t esp_random(void) { return (uint32_t)rand(); }
/* CRC-32 normal (el de zlib), que es lo que da la ROM con crc inicial 0:
 * asi verifica_lecturas.py acepta las tramas de este banco. */
uint32_t esp_rom_crc32_le(uint32_t crc, const uint8_t *buf, uint32_t len)
{
    motor_n_tramas++;
    crc = ~crc;
    for (uint32_t i = 0; i < len; i++) {
        crc ^= buf[i];
        for (int b = 0; b < 8; b++) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}
esp_err_t esp_efuse_mac_get_default(uint8_t *mac)
{ static const uint8_t m[6] = {0x7c, 0xdf, 0xa1, 0x00, 0x11, 0x22}; memcpy(mac, m, 6); return ESP_OK; }

