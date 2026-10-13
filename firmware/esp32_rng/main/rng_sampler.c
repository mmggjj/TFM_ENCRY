/**
 * @file rng_sampler.c
 * @brief Condition control and raw capture of the ESP32 hardware RNG.
 */
#include "rng_sampler.h"

#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "nvs_flash.h"

static const char *TAG = "rng_sampler";

#include "adc_noise.h"

static bool s_wifi_inited = false;
static bool s_wifi_on = false;
static TaskHandle_t s_adc_task = NULL;
static volatile bool s_adc_run = false;

char rng_condition_letter(rng_condition_t c)
{
    switch (c) {
    case COND_A: return 'A';
    case COND_B: return 'B';
    case COND_C: return 'C';
    case COND_D: return 'D';
    default:     return '?';
    }
}

/* ------------------------------------------------------------- ADC ----- */

/* Background task keeping the SAR ADC busy: per the vendor documentation,
 * SAR ADC activity feeds the RNG entropy pool. Reads as fast as the
 * oneshot driver allows on ADC1_CH0 (GPIO36, floating). */
static void adc_pump_task(void *arg)
{
    int raw;
    while (s_adc_run) {
        for (int i = 0; i < 256 && s_adc_run; i++) {
            adc_noise_read_raw(&raw);
        }
        vTaskDelay(1); /* let the IDLE task feed the watchdog */
    }
    vTaskDelete(NULL);
}

static esp_err_t adc_pump_start(void)
{
    if (s_adc_task != NULL) {
        return ESP_OK;
    }
    ESP_RETURN_ON_ERROR(adc_noise_init(), TAG, "adc unit");
    s_adc_run = true;
    xTaskCreatePinnedToCore(adc_pump_task, "adc_pump", 2048, NULL, 3,
                            &s_adc_task, 0);
    vTaskDelay(pdMS_TO_TICKS(50));
    return ESP_OK;
}

static void adc_pump_stop(void)
{
    if (s_adc_task == NULL) {
        return;
    }
    s_adc_run = false;
    vTaskDelay(pdMS_TO_TICKS(50)); /* task self-deletes */
    s_adc_task = NULL;
}

/* ------------------------------------------------------------ WiFi ----- */

static esp_err_t wifi_radio_on(void)
{
    if (s_wifi_on) {
        return ESP_OK;
    }
    if (!s_wifi_inited) {
        esp_err_t err = nvs_flash_init();
        if (err == ESP_ERR_NVS_NO_FREE_PAGES ||
            err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
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
        s_wifi_inited = true;
    }
    /* Starting the radio is enough for the RNG entropy source; no
     * association is attempted here (see mqtt_reporter for that). */
    ESP_ERROR_CHECK(esp_wifi_start());
    s_wifi_on = true;
    vTaskDelay(pdMS_TO_TICKS(200)); /* RF calibration settle */
    return ESP_OK;
}

static void wifi_radio_off(void)
{
    if (!s_wifi_on) {
        return;
    }
    esp_wifi_stop();
    s_wifi_on = false;
    vTaskDelay(pdMS_TO_TICKS(100));
}

/* ------------------------------------------------------- public API ---- */

esp_err_t rng_apply_condition(rng_condition_t c)
{
    bool want_wifi = (c == COND_A || c == COND_B);
    bool want_adc = (c == COND_A || c == COND_C);

    if (want_wifi) {
        ESP_RETURN_ON_ERROR(wifi_radio_on(), TAG, "wifi on");
    } else {
        wifi_radio_off();
    }
    if (want_adc) {
        ESP_RETURN_ON_ERROR(adc_pump_start(), TAG, "adc on");
    } else {
        adc_pump_stop();
    }
    ESP_LOGI(TAG, "condition %c applied (wifi=%d adc=%d)",
             rng_condition_letter(c), want_wifi, want_adc);
    /* settling time so the entropy source reaches steady state */
    vTaskDelay(pdMS_TO_TICKS(500));
    return ESP_OK;
}

void rng_pause_adc(void)
{
    adc_pump_stop();
}

void rng_generate_sequence(uint8_t *buffer, size_t length)
{
    esp_fill_random(buffer, length);
}

uint32_t rng_measure_throughput(void)
{
    static uint8_t buf[4096];
    const int loops = 16; /* 64 KiB total */
    int64_t t0 = esp_timer_get_time();
    for (int i = 0; i < loops; i++) {
        esp_fill_random(buf, sizeof(buf));
    }
    int64_t dt = esp_timer_get_time() - t0;
    return (uint32_t)((uint64_t)sizeof(buf) * loops * 1000000ULL /
                      (uint64_t)dt);
}
