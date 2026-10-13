/**
 * @file rng_sampler.h
 * @brief Hardware RNG capture under controlled operating conditions.
 *
 * The ESP32 hardware RNG (RNG_DATA_REG) derives its entropy from ring
 * oscillator jitter, but Espressif documents that the output is only
 * truly random while an RF subsystem (WiFi/BT) or the SAR ADC is active.
 * This module captures raw RNG sequences under the four test conditions:
 *
 *   COND_A  WiFi ON  + ADC ON    (maximum documented entropy)
 *   COND_B  WiFi ON  + ADC OFF
 *   COND_C  WiFi OFF + ADC ON
 *   COND_D  WiFi OFF + ADC OFF   (documented worst case: pseudo-random)
 *
 * "WiFi ON" means the radio is started (esp_wifi_start), association is
 * not required for the entropy source. "ADC ON" means a background task
 * is continuously reading the SAR ADC.
 *
 * TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
 */
#ifndef RNG_SAMPLER_H
#define RNG_SAMPLER_H

#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"

typedef enum {
    COND_D = 0,   /* WiFi OFF + ADC OFF -- capture first from cold boot */
    COND_C,       /* WiFi OFF + ADC ON                                  */
    COND_B,       /* WiFi ON  + ADC OFF                                 */
    COND_A,       /* WiFi ON  + ADC ON                                  */
    COND_COUNT
} rng_condition_t;

#ifdef __cplusplus
extern "C" {
#endif

/** Human-readable single letter for a condition. */
char rng_condition_letter(rng_condition_t c);

/** Apply a test condition (start/stop WiFi radio, start/stop the ADC
 *  background sampler). Blocks until the state is settled. */
esp_err_t rng_apply_condition(rng_condition_t c);

/** Fill @p buffer with @p length bytes from the hardware RNG. */
void rng_generate_sequence(uint8_t *buffer, size_t length);

/** Measure generation throughput in bytes/second (64 KiB burst). */
uint32_t rng_measure_throughput(void);

/** Pause the background ADC pump (if running) WITHOUT changing the WiFi
 *  state. Used to quiesce the SoC while streaming a captured buffer over
 *  UART: the entropy condition only needs to hold during generation. */
void rng_pause_adc(void);

#ifdef __cplusplus
}
#endif

#endif /* RNG_SAMPLER_H */
