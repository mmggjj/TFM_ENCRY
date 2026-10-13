/**
 * @file sram_puf.h
 * @brief SRAM power-up pattern capture (entropy source 2 of the harvester).
 *
 * A 4 KiB buffer in .noinit holds the SRAM power-up state after a full
 * POWER cycle (soft resets preserve the previous contents). The pattern
 * combines a device-unique bias (PUF component, stable bits) with
 * thermal-noise-driven metastable cells (entropy component, flipping
 * bits) -- the harvester consumes both, the future-work PUF application
 * only the stable part.
 *
 * TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
 */
#ifndef SRAM_PUF_H
#define SRAM_PUF_H

#include <stdint.h>
#include <stddef.h>

#define PUF_SIZE_BYTES 4096

#ifdef __cplusplus
extern "C" {
#endif

/** Copy up to @p len bytes of the power-up pattern into @p output.
 *  Call as early as possible in app_main. @return bytes copied. */
size_t puf_read_startup_pattern(uint8_t *output, size_t len);

/** Shannon entropy of the pattern in bits per bit (ideal 1.0),
 *  estimated from the global ones-density. */
float puf_calculate_entropy(const uint8_t *data, size_t len);

/** Hamming distance in bits between two buffers. */
uint32_t puf_hamming_distance(const uint8_t *a, const uint8_t *b,
                              size_t len);

/** Hamming weight (number of set bits) of a buffer. */
uint32_t puf_hamming_weight(const uint8_t *data, size_t len);

#ifdef __cplusplus
}
#endif

#endif /* SRAM_PUF_H */
