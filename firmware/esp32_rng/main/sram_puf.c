/**
 * @file sram_puf.c
 * @brief SRAM power-up capture and pattern statistics.
 */
#include "sram_puf.h"

#include <math.h>
#include <string.h>

#include "esp_attr.h"

static __NOINIT_ATTR uint8_t puf_buffer[PUF_SIZE_BYTES];

size_t puf_read_startup_pattern(uint8_t *output, size_t len)
{
    if (output == NULL) {
        return 0;
    }
    size_t n = (len < PUF_SIZE_BYTES) ? len : PUF_SIZE_BYTES;
    memcpy(output, puf_buffer, n);
    return n;
}

uint32_t puf_hamming_weight(const uint8_t *data, size_t len)
{
    uint32_t w = 0;
    for (size_t i = 0; i < len; i++) {
        w += (uint32_t)__builtin_popcount(data[i]);
    }
    return w;
}

float puf_calculate_entropy(const uint8_t *data, size_t len)
{
    if (data == NULL || len == 0) {
        return 0.0f;
    }
    float p1 = (float)puf_hamming_weight(data, len) / (float)(len * 8);
    if (p1 <= 0.0f || p1 >= 1.0f) {
        return 0.0f;
    }
    return -(p1 * log2f(p1) + (1.0f - p1) * log2f(1.0f - p1));
}

uint32_t puf_hamming_distance(const uint8_t *a, const uint8_t *b, size_t len)
{
    uint32_t d = 0;
    for (size_t i = 0; i < len; i++) {
        d += (uint32_t)__builtin_popcount(a[i] ^ b[i]);
    }
    return d;
}
