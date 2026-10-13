/**
 * @file entropy_harvester.c
 * @brief SHA-256-conditioned multi-source entropy pool.
 */
#include "entropy_harvester.h"

#include <string.h>

#include "esp_log.h"
#include "esp_random.h"
#include "mbedtls/sha256.h"

#include "adc_noise.h"

static const char *TAG = "harvester";

static void sha256(const uint8_t *in, size_t len, uint8_t out[32])
{
    mbedtls_sha256(in, len, out, 0 /* SHA-256, not SHA-224 */);
}

esp_err_t harvester_init(entropy_pool_t *pool,
                         const uint8_t *sram_pattern, size_t sram_len)
{
    if (pool == NULL || sram_pattern == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    memset(pool, 0, sizeof(*pool));

    /* Source 1: hardware RNG (quality is condition-dependent) */
    esp_fill_random(pool->rng_contribution,
                    sizeof(pool->rng_contribution));

    /* Source 2: SRAM power-up pattern, compressed to 256 bits */
    sha256(sram_pattern, sram_len, pool->puf_contribution);

    /* Source 3: ADC noise through Von Neumann */
    esp_err_t err = adc_noise_generate_entropy(
        pool->adc_contribution, sizeof(pool->adc_contribution));
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "ADC source unavailable (%d); pool degraded to 2 "
                      "sources", err);
        memset(pool->adc_contribution, 0, sizeof(pool->adc_contribution));
    }

    /* Condition: pool = SHA256(rng || puf || adc || tag) */
    uint8_t material[32 * 3 + 4];
    memcpy(material, pool->rng_contribution, 32);
    memcpy(material + 32, pool->puf_contribution, 32);
    memcpy(material + 64, pool->adc_contribution, 32);
    memcpy(material + 96, "TFM0", 4);
    sha256(material, sizeof(material), pool->combined_seed);
    pool->generate_count = 0;

    ESP_LOGI(TAG, "entropy pool initialized (3 sources)");
    return ESP_OK;
}

esp_err_t harvester_generate(entropy_pool_t *pool,
                             uint8_t *output, size_t len)
{
    if (pool == NULL || output == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t block[32 + 4 + 32];
    size_t produced = 0;
    while (produced < len) {
        memcpy(block, pool->combined_seed, 32);
        memcpy(block + 32, &pool->generate_count, 4);
        esp_fill_random(block + 36, 32);        /* fresh RNG each block */
        uint8_t digest[32];
        sha256(block, sizeof(block), digest);

        size_t n = (len - produced < 32) ? (len - produced) : 32;
        memcpy(output + produced, digest, n);
        produced += n;
        pool->generate_count++;

        /* ratchet the pool forward so past outputs cannot be recovered */
        memcpy(block, pool->combined_seed, 32);
        memcpy(block + 32, digest, 32);
        sha256(block, 64, pool->combined_seed);
    }
    return ESP_OK;
}

esp_err_t harvester_reseed(entropy_pool_t *pool)
{
    if (pool == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t material[32 + 32 + 32];
    memcpy(material, pool->combined_seed, 32);
    esp_fill_random(material + 32, 32);
    esp_err_t err = adc_noise_generate_entropy(material + 64, 32);
    if (err != ESP_OK) {
        memset(material + 64, 0, 32);
    }
    sha256(material, sizeof(material), pool->combined_seed);
    ESP_LOGI(TAG, "pool reseeded");
    return ESP_OK;
}
