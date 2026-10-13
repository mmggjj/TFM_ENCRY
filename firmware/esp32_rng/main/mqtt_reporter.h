/**
 * @file mqtt_reporter.h
 * @brief Optional MQTT telemetry for the RNG test campaign.
 *
 * Topics:
 *   esp32/rng/condition    current condition letter
 *   esp32/rng/temperature  die temperature [C]
 *   esp32/rng/throughput   RNG throughput [bytes/s]
 *   esp32/harvester/seed   harvester seed (hex)
 *
 * Requires WiFi ASSOCIATION (Kconfig credentials). If the SSID is left
 * at its default, the module stays inactive and the campaign proceeds
 * over UART only. Raw sequences travel over UART regardless (1 Mbit
 * frames over MQTT would be needlessly slow and lossy).
 *
 * TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
 */
#ifndef MQTT_REPORTER_H
#define MQTT_REPORTER_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Try to associate and connect to the broker. Returns ESP_FAIL (without
 *  blocking the campaign) if credentials are default or unreachable. */
esp_err_t mqtt_reporter_try_init(void);

bool mqtt_reporter_active(void);

void mqtt_publish_condition(char cond);
void mqtt_publish_metrics(float temperature_c, uint32_t throughput_bps);
void mqtt_publish_harvester_seed(const uint8_t *seed, size_t len);

#ifdef __cplusplus
}
#endif

#endif /* MQTT_REPORTER_H */
