/**
 * @file adc_noise.c
 * @brief ADC LSB noise harvesting with Von Neumann debiasing.
 */
#include "adc_noise.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"
#include "esp_log.h"

static const char *TAG = "adc_noise";

static adc_oneshot_unit_handle_t s_unit = NULL;

esp_err_t adc_noise_init(void)
{
    if (s_unit != NULL) {
        return ESP_OK;
    }
    adc_oneshot_unit_init_cfg_t ucfg = {
        .unit_id = ADC_UNIT_1,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    ESP_RETURN_ON_ERROR(adc_oneshot_new_unit(&ucfg, &s_unit), TAG, "unit");
    adc_oneshot_chan_cfg_t ccfg = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_12,
    };
    ESP_RETURN_ON_ERROR(
        adc_oneshot_config_channel(s_unit, ADC_CHANNEL_0, &ccfg),
        TAG, "chan");
    ESP_LOGI(TAG, "ADC noise source ready (GPIO36 floating expected)");
    return ESP_OK;
}

esp_err_t adc_noise_read_raw(int *raw)
{
    ESP_RETURN_ON_ERROR(adc_noise_init(), TAG, "init");
    return adc_oneshot_read(s_unit, ADC_CHANNEL_0, raw);
}

void von_neumann_correct(const uint8_t *input, size_t in_len,
                         uint8_t *output, size_t *out_len)
{
    size_t cap = *out_len;
    size_t out_bits = 0;
    for (size_t i = 0; i < in_len && (out_bits >> 3) < cap; i++) {
        uint8_t byte = input[i];
        for (int p = 6; p >= 0; p -= 2) {          /* 4 bit-pairs per byte */
            uint8_t pair = (byte >> p) & 0x3;
            if (pair == 0x1 || pair == 0x2) {      /* 01 -> 0, 10 -> 1 */
                uint8_t bit = (pair == 0x2) ? 1 : 0;
                if (bit) {
                    output[out_bits >> 3] |= (uint8_t)(0x80 >> (out_bits & 7));
                } else {
                    output[out_bits >> 3] &= (uint8_t)~(0x80 >> (out_bits & 7));
                }
                out_bits++;
                if ((out_bits >> 3) >= cap) {
                    break;
                }
            }
        }
    }
    *out_len = out_bits >> 3;                       /* whole bytes only */
}

esp_err_t adc_noise_generate_entropy(uint8_t *buffer, size_t len)
{
    ESP_RETURN_ON_ERROR(adc_noise_init(), TAG, "init");

    size_t produced = 0;
    uint8_t rawbits[256];
    while (produced < len) {
        /* collect 2048 raw LSBs = 256 bytes of bit stream */
        for (size_t i = 0; i < sizeof(rawbits); i++) {
            uint8_t b = 0;
            for (int k = 0; k < 8; k++) {
                int raw = 0;
                adc_oneshot_read(s_unit, ADC_CHANNEL_0, &raw);
                b = (uint8_t)((b << 1) | (raw & 1));
            }
            rawbits[i] = b;
        }
        size_t out_cap = len - produced;
        von_neumann_correct(rawbits, sizeof(rawbits),
                            buffer + produced, &out_cap);
        produced += out_cap;
        vTaskDelay(1); /* watchdog courtesy */
    }
    return ESP_OK;
}
