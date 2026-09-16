"""Cabeceras simuladas del ESP-IDF para comprobar main.c sin ESP-IDF.

No emula comportamiento: declara lo justo para que un gcc de escritorio
valide sintaxis, tipos y cadenas de formato del verificador. Sirve para
cazar roturas en cualquier maquina, sin toolchain de Espressif ni placa.

    python host_check/mk_stubs.py /tmp/stubs
    gcc -fsyntax-only -Wall -Wextra -Wno-unused-parameter -std=gnu11         -I /tmp/stubs main/main.c

Encontro una cadena partida que la inspeccion visual no vio, asi que se
queda. NO forma parte de la compilacion del proyecto: idf.py no mira en
host_check/.
"""
import sys
from pathlib import Path

raiz = Path(sys.argv[1])
raiz.mkdir(parents=True, exist_ok=True)


def esc(rel, texto):
    f = raiz / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto, encoding="utf-8")


esc("esp_err.h", """
#pragma once
#include <stdint.h>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_ERR_INVALID_SIZE 0x104
#define ESP_ERROR_CHECK(x) do { (void)(x); } while (0)
""")

esc("freertos/FreeRTOS.h", """
#pragma once
#include <stdint.h>
typedef uint32_t TickType_t;
#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
""")

esc("freertos/task.h", """
#pragma once
#include "freertos/FreeRTOS.h"
void vTaskDelay(TickType_t t);
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

print(f"cabeceras simuladas en {raiz}")
