/**
 * @file entropy_harvester.h
 * @brief Multi-source entropy harvester: RNG + SRAM-PUF + ADC noise.
 *
 * Construction (sponge-lite, SHA-256 as conditioner per SP 800-90B):
 *   pool_0   = SHA256( RNG[32] || PUF[4096] || ADC[32] || counter )
 *   output_i = SHA256( pool || i || RNG[32] )        (forward secrecy)
 *   reseed   = SHA256( pool || fresh RNG || fresh ADC )
 *
 * The three sources have complementary availability: the hardware RNG is
 * always on (quality condition-dependent), the SRAM pattern only at
 * power-up (device-unique + metastable noise), the ADC only when the
 * peripheral is powered. XOR-combining before hashing guarantees the
 * result is at least as strong as the strongest source.
 *
 * TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
 */
#ifndef ENTROPY_HARVESTER_H
#define ENTROPY_HARVESTER_H

#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"

typedef struct {
    uint8_t rng_contribution[32];
    uint8_t puf_contribution[32];   /* SHA-256 of the 4 KiB pattern */
    uint8_t adc_contribution[32];
    uint8_t combined_seed[32];      /* current pool state */
    uint32_t generate_count;
} entropy_pool_t;

#ifdef __cplusplus
extern "C" {
#endif

/** Initialize the pool from the three sources. The SRAM pattern must be
 *  captured beforehand (puf_read_startup_pattern) and passed in. */
esp_err_t harvester_init(entropy_pool_t *pool,
                         const uint8_t *sram_pattern, size_t sram_len);

/** Generate @p len cryptographically mixed bytes into @p output. */
esp_err_t harvester_generate(entropy_pool_t *pool,
                             uint8_t *output, size_t len);

/** Fold fresh RNG + ADC entropy into the pool. */
esp_err_t harvester_reseed(entropy_pool_t *pool);

#ifdef __cplusplus
}
#endif

#endif /* ENTROPY_HARVESTER_H */
