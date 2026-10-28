"""Cabeceras simuladas del ESP-IDF para compilar el firmware en el PC.

No emulan comportamiento: declaran lo justo para que un gcc de escritorio
compile el verificador, el medidor y el componente motor_i2c contra el
motor simulado (motor_sim.c). Sirve para cazar roturas en cualquier
maquina, sin toolchain de Espressif ni placa.

    python3 mk_stubs.py DESTINO [--sin-mbedtls]

Con --sin-mbedtls no se generan las cabeceras falsas de mbedtls: se usan
las de verdad (run_host.py las pasa con -I y enlaza la biblioteca). Las
falsas solo cubren el CMAC del verificador.

Encontro una cadena partida que la inspeccion visual no vio, asi que se
queda. NO forma parte de la compilacion del proyecto: idf.py no mira en
host_check/.
"""
import sys
from pathlib import Path

raiz = Path(sys.argv[1])
con_mbedtls_falso = "--sin-mbedtls" not in sys.argv[2:]
raiz.mkdir(parents=True, exist_ok=True)


def esc(rel, texto):
    f = raiz / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto, encoding="utf-8")


esc("sdkconfig.h", """
#pragma once
/* En el PC no hay objetivo: main.c del medidor toma los pines del C3. */
""")

esc("esp_err.h", """
#pragma once
#include <stdint.h>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_FAIL -1
#define ESP_ERR_INVALID_STATE 0x103
#define ESP_ERR_INVALID_SIZE 0x104
#define ESP_ERR_TIMEOUT 0x107
#define ESP_ERROR_CHECK(x) do { (void)(x); } while (0)
""")

esc("freertos/FreeRTOS.h", """
#pragma once
#include <stdint.h>
typedef uint32_t TickType_t;
#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
#define portTICK_PERIOD_MS 1
""")

esc("freertos/task.h", """
#pragma once
#include "freertos/FreeRTOS.h"
typedef uint32_t UBaseType_t;
typedef void *TaskHandle_t;
void vTaskDelay(TickType_t t);
TickType_t xTaskGetTickCount(void);
UBaseType_t uxTaskGetStackHighWaterMark(TaskHandle_t t);
""")

esc("driver/i2c_master.h", """
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
typedef struct i2c_master_bus_t *i2c_master_bus_handle_t;
typedef struct i2c_master_dev_t *i2c_master_dev_handle_t;
typedef enum { I2C_NUM_0 = 0 } i2c_port_num_t;
typedef enum { I2C_CLK_SRC_DEFAULT = 0 } i2c_clock_source_t;
typedef enum { I2C_ADDR_BIT_LEN_7 = 0 } i2c_addr_bit_len_t;
typedef struct {
    i2c_port_num_t i2c_port;
    int sda_io_num;
    int scl_io_num;
    i2c_clock_source_t clk_source;
    int glitch_ignore_cnt;
    struct { bool enable_internal_pullup; } flags;
} i2c_master_bus_config_t;
typedef struct {
    i2c_addr_bit_len_t dev_addr_length;
    uint16_t device_address;
    uint32_t scl_speed_hz;
} i2c_device_config_t;
esp_err_t i2c_new_master_bus(const i2c_master_bus_config_t *c,
                             i2c_master_bus_handle_t *h);
esp_err_t i2c_master_bus_add_device(i2c_master_bus_handle_t b,
                                    const i2c_device_config_t *c,
                                    i2c_master_dev_handle_t *h);
esp_err_t i2c_master_transmit(i2c_master_dev_handle_t d, const uint8_t *buf,
                              size_t n, int timeout_ms);
esp_err_t i2c_master_transmit_receive(i2c_master_dev_handle_t d,
                                      const uint8_t *w, size_t wn,
                                      uint8_t *r, size_t rn, int timeout_ms);
""")

esc("esp_log.h", """
#pragma once
#include <stdio.h>
#define ESP_LOGE(tag, fmt, ...) printf("E %s: " fmt "\\n", tag, ##__VA_ARGS__)
#define ESP_LOGW(tag, fmt, ...) printf("W %s: " fmt "\\n", tag, ##__VA_ARGS__)
#define ESP_LOGI(tag, fmt, ...) printf("I %s: " fmt "\\n", tag, ##__VA_ARGS__)
""")

esc("esp_random.h", """
#pragma once
#include <stddef.h>
#include <stdint.h>
uint32_t esp_random(void);
void esp_fill_random(void *buf, size_t len);
""")

esc("esp_rom_crc.h", """
#pragma once
#include <stddef.h>
#include <stdint.h>
uint32_t esp_rom_crc32_le(uint32_t crc, const uint8_t *buf, uint32_t len);
""")

esc("nvs_flash.h", """
#pragma once
#include "esp_err.h"
#define ESP_ERR_NVS_NOT_FOUND 0x1102
#define ESP_ERR_NVS_INVALID_LENGTH 0x1109
#define ESP_ERR_NVS_NO_FREE_PAGES 0x110d
#define ESP_ERR_NVS_NEW_VERSION_FOUND 0x1110
esp_err_t nvs_flash_init(void);
esp_err_t nvs_flash_erase(void);
""")

esc("nvs.h", """
#pragma once
#include <stdint.h>
#include "esp_err.h"
typedef uint32_t nvs_handle_t;
typedef enum { NVS_READONLY, NVS_READWRITE } nvs_open_mode_t;
esp_err_t nvs_open(const char *ns, nvs_open_mode_t m, nvs_handle_t *h);
esp_err_t nvs_get_u32(nvs_handle_t h, const char *k, uint32_t *v);
esp_err_t nvs_set_u32(nvs_handle_t h, const char *k, uint32_t v);
esp_err_t nvs_get_blob(nvs_handle_t h, const char *k, void *v, size_t *n);
esp_err_t nvs_set_blob(nvs_handle_t h, const char *k, const void *v, size_t n);
esp_err_t nvs_erase_key(nvs_handle_t h, const char *k);
esp_err_t nvs_commit(nvs_handle_t h);
void nvs_close(nvs_handle_t h);
""")

esc("esp_mac.h", """
#pragma once
#include <stdint.h>
#include "esp_err.h"
esp_err_t esp_efuse_mac_get_default(uint8_t *mac);
""")

if con_mbedtls_falso:
    esc("mbedtls/cipher.h", """
#pragma once
typedef enum { MBEDTLS_CIPHER_AES_128_ECB = 2 } mbedtls_cipher_type_t;
typedef struct mbedtls_cipher_info_t mbedtls_cipher_info_t;
const mbedtls_cipher_info_t *mbedtls_cipher_info_from_type(mbedtls_cipher_type_t t);
""")

    esc("mbedtls/cmac.h", """
#pragma once
#include <stddef.h>
#include "mbedtls/cipher.h"
int mbedtls_cipher_cmac(const mbedtls_cipher_info_t *ci,
                        const unsigned char *key, size_t keybits,
                        const unsigned char *input, size_t ilen,
                        unsigned char *output);
""")

print(f"cabeceras simuladas en {raiz}" + ("" if con_mbedtls_falso else " (sin mbedtls falso)"))
