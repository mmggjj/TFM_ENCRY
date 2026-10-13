/**
 * @file adc_noise.h
 * @brief ADC sampling noise as entropy source 3 of the harvester.
 *
 * With no signal driving GPIO36 (ADC1_CH0 floating), each conversion's
 * LSBs carry amplifier/reference noise. Raw LSBs are biased and
 * correlated, so a Von Neumann corrector is applied to LSB pairs:
 * (0,1)->0, (1,0)->1, (0,0)/(1,1)->discarded. The corrector provably
 * removes bias at the cost of >=75% throughput loss.
 *
 * TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
 */
#ifndef ADC_NOISE_H
#define ADC_NOISE_H

#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Initialize ADC1_CH0 for noise capture (idempotent; this module owns
 *  the single ADC1 oneshot unit shared by the whole firmware). */
esp_err_t adc_noise_init(void);

/** One raw conversion on the shared unit (used by rng_sampler's pump). */
esp_err_t adc_noise_read_raw(int *raw);

/** Fill @p buffer with @p len bytes of Von-Neumann-corrected entropy
 *  harvested from ADC LSB noise. Blocking; throughput is limited by the
 *  corrector discard rate (~4 raw bits per output bit minimum). */
esp_err_t adc_noise_generate_entropy(uint8_t *buffer, size_t len);

/** Von Neumann corrector over a bit stream packed in bytes.
 *  Consumes bit pairs from @p input (in_len bytes) and writes unbiased
 *  bits to @p output; *out_len is in/out: capacity in, bytes written out. */
void von_neumann_correct(const uint8_t *input, size_t in_len,
                         uint8_t *output, size_t *out_len);

#ifdef __cplusplus
}
#endif

#endif /* ADC_NOISE_H */
