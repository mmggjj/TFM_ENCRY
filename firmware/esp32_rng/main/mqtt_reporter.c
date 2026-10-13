/**
 * @file mqtt_reporter.c
 * @brief Optional MQTT telemetry (inactive with default credentials).
 */
#include "mqtt_reporter.h"

#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

#include "esp_log.h"
#include "esp_wifi.h"
#include "mqtt_client.h"

static const char *TAG = "mqtt_rep";

#define CONNECTED_BIT BIT0

static esp_mqtt_client_handle_t s_client = NULL;
static EventGroupHandle_t s_events = NULL;
static bool s_active = false;

static void ip_handler(void *arg, esp_event_base_t base, int32_t id,
                       void *data)
{
    if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        xEventGroupSetBits(s_events, CONNECTED_BIT);
    }
}

esp_err_t mqtt_reporter_try_init(void)
{
    if (strcmp(CONFIG_TFM_WIFI_SSID, "myssid") == 0) {
        ESP_LOGW(TAG, "WiFi credentials not configured; MQTT disabled "
                      "(campaign runs over UART)");
        return ESP_FAIL;
    }
    if (s_events == NULL) {
        s_events = xEventGroupCreate();
    }

    /* The radio is already initialized/started by rng_sampler (condition
     * A/B); here we only add credentials and connect. */
    wifi_config_t wc = { 0 };
    strlcpy((char *)wc.sta.ssid, CONFIG_TFM_WIFI_SSID,
            sizeof(wc.sta.ssid));
    strlcpy((char *)wc.sta.password, CONFIG_TFM_WIFI_PASSWORD,
            sizeof(wc.sta.password));
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, ip_handler,
                               NULL);
    esp_wifi_set_config(WIFI_IF_STA, &wc);
    esp_wifi_connect();

    EventBits_t bits = xEventGroupWaitBits(s_events, CONNECTED_BIT,
                                           pdFALSE, pdTRUE,
                                           pdMS_TO_TICKS(15000));
    if (!(bits & CONNECTED_BIT)) {
        ESP_LOGW(TAG, "association timeout; MQTT disabled");
        return ESP_FAIL;
    }

    esp_mqtt_client_config_t cfg = {
        .broker.address.uri = CONFIG_TFM_MQTT_BROKER_URI,
    };
    s_client = esp_mqtt_client_init(&cfg);
    if (s_client == NULL || esp_mqtt_client_start(s_client) != ESP_OK) {
        ESP_LOGW(TAG, "broker unreachable; MQTT disabled");
        return ESP_FAIL;
    }
    s_active = true;
    ESP_LOGI(TAG, "MQTT telemetry active");
    return ESP_OK;
}

bool mqtt_reporter_active(void)
{
    return s_active;
}

static void pub(const char *topic, const char *payload)
{
    if (s_active) {
        esp_mqtt_client_publish(s_client, topic, payload, 0, 0, 0);
    }
}

void mqtt_publish_condition(char cond)
{
    char p[2] = { cond, 0 };
    pub("esp32/rng/condition", p);
}

void mqtt_publish_metrics(float temperature_c, uint32_t throughput_bps)
{
    char p[64];
    snprintf(p, sizeof(p), "%.1f", temperature_c);
    pub("esp32/rng/temperature", p);
    snprintf(p, sizeof(p), "%lu", (unsigned long)throughput_bps);
    pub("esp32/rng/throughput", p);
}

void mqtt_publish_harvester_seed(const uint8_t *seed, size_t len)
{
    char hex[2 * 32 + 1] = { 0 };
    size_t n = len < 32 ? len : 32;
    for (size_t i = 0; i < n; i++) {
        snprintf(hex + 2 * i, 3, "%02x", seed[i]);
    }
    pub("esp32/harvester/seed", hex);
}
