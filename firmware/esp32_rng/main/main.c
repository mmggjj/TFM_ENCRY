/**
 * @file main.c
 * @brief RNG characterization campaign controller.
 *
 * Boot sequence:
 *   1. Capture the SRAM power-up pattern BEFORE anything else and stream
 *      it as a framed hex block (### PUF_BEGIN/END, CRC32).
 *   2. Cycle through the four test conditions in order D -> C -> B -> A
 *      (D first: at cold boot the radio has never run, giving the purest
 *      documented worst case). For each condition, stream 125000 bytes
 *      (1 Mbit) of raw RNG output as a framed hex block with CRC32,
 *      preceded by a STATUS line (temperature, throughput).
 *   3. After each full cycle, initialize the multi-source harvester and
 *      stream 100 seeds of 32 bytes (### SEEDS_BEGIN/END).
 *   4. Repeat forever; the host captures as many repetitions as needed.
 *
 * All frames go over UART0 (see sdkconfig.defaults: 921600 baud).
 * MQTT telemetry is optional and never blocks the campaign.
 *
 * TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
 */
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_log.h"
#include "esp_mac.h"
#include "esp_rom_crc.h"
#include "esp_timer.h"

#include "adc_noise.h"
#include "entropy_harvester.h"
#include "mqtt_reporter.h"
#include "rng_sampler.h"
#include "sram_puf.h"
#include "temp_monitor.h"

static const char *TAG = "rng_main";

#define SEQ_BYTES        125000      /* 1 Mbit per condition            */
#define CHUNK            4096
#define HEX_PER_LINE     64          /* 64 bytes -> 128 hex chars/line  */
#define SEEDS_PER_CYCLE  100

static uint8_t s_puf[PUF_SIZE_BYTES];
static uint8_t s_seq[SEQ_BYTES];   /* whole 1 Mbit sequence buffered:
                                    * generate under the condition, then
                                    * stream with the SoC quiesced */
static entropy_pool_t s_pool;

static const char HEX[] = "0123456789abcdef";

/* Stream a buffer as fixed-width hex lines, updating a running CRC32. */
static void stream_hex(const uint8_t *buf, size_t len, uint32_t *crc)
{
    static char line[2 * HEX_PER_LINE + 2];
    *crc = esp_rom_crc32_le(*crc, buf, len);
    size_t i = 0;
    while (i < len) {
        size_t n = (len - i < HEX_PER_LINE) ? (len - i) : HEX_PER_LINE;
        for (size_t j = 0; j < n; j++) {
            line[2 * j] = HEX[buf[i + j] >> 4];
            line[2 * j + 1] = HEX[buf[i + j] & 0xF];
        }
        line[2 * n] = '\n';
        line[2 * n + 1] = 0;
        fputs(line, stdout);
        i += n;
    }
}

static void stream_puf_frame(void)
{
    uint32_t crc = 0;
    printf("### PUF_BEGIN bytes=%d entropy=%.4f weight=%lu\n",
           PUF_SIZE_BYTES, puf_calculate_entropy(s_puf, PUF_SIZE_BYTES),
           (unsigned long)puf_hamming_weight(s_puf, PUF_SIZE_BYTES));
    stream_hex(s_puf, PUF_SIZE_BYTES, &crc);
    printf("### PUF_END crc32=0x%08lx\n", (unsigned long)crc);
}

static void capture_condition(rng_condition_t cond, int rep)
{
    char letter = rng_condition_letter(cond);
    if (rng_apply_condition(cond) != ESP_OK) {
        printf("### ERROR cond=%c rep=%d apply failed\n", letter, rep);
        return;
    }
    uint32_t tput = rng_measure_throughput();
    float temp = temp_read_internal();
    mqtt_publish_condition(letter);
    mqtt_publish_metrics(temp, tput);

    /* 1. Generate the FULL sequence while the condition holds. */
    rng_generate_sequence(s_seq, SEQ_BYTES);
    float temp_end = temp_read_internal();

    /* 2. Quiesce the ADC pump (WiFi state untouched) and stream: the
     * pump's bus activity was observed to corrupt long UART bursts. */
    rng_pause_adc();
    vTaskDelay(pdMS_TO_TICKS(100));

    printf("### RNG_BEGIN cond=%c rep=%d bytes=%d temp_c=%.1f "
           "throughput_Bps=%lu\n",
           letter, rep, SEQ_BYTES, temp, (unsigned long)tput);
    uint32_t crc = 0;
    for (size_t off = 0; off < SEQ_BYTES; off += CHUNK) {
        size_t n = (SEQ_BYTES - off) < CHUNK ? (SEQ_BYTES - off) : CHUNK;
        stream_hex(s_seq + off, n, &crc);
        vTaskDelay(1); /* watchdog + UART drain */
    }
    printf("### RNG_END cond=%c rep=%d crc32=0x%08lx temp_c=%.1f\n",
           letter, rep, (unsigned long)crc, temp_end);
}

static void stream_harvester_seeds(void)
{
    if (harvester_init(&s_pool, s_puf, PUF_SIZE_BYTES) != ESP_OK) {
        printf("### ERROR harvester init failed\n");
        return;
    }
    printf("### SEEDS_BEGIN n=%d bytes=32\n", SEEDS_PER_CYCLE);
    uint8_t seed[32];
    uint32_t crc = 0;
    for (int i = 0; i < SEEDS_PER_CYCLE; i++) {
        harvester_generate(&s_pool, seed, sizeof(seed));
        stream_hex(seed, sizeof(seed), &crc);
        if ((i % 10) == 0) {
            vTaskDelay(1);
        }
    }
    printf("### SEEDS_END crc32=0x%08lx\n", (unsigned long)crc);
    mqtt_publish_harvester_seed(seed, sizeof(seed));
    harvester_reseed(&s_pool);
}

static void campaign_task(void *arg)
{
    /* Condition order: D first from cold boot (purest worst case). */
    static const rng_condition_t order[COND_COUNT] = {
        COND_D, COND_C, COND_B, COND_A
    };

    for (int rep = 1;; rep++) {
        printf("### CYCLE_BEGIN rep=%d uptime_ms=%lld\n", rep,
               esp_timer_get_time() / 1000);
        for (int i = 0; i < COND_COUNT; i++) {
            capture_condition(order[i], rep);
        }
        stream_harvester_seeds();
        printf("### CYCLE_END rep=%d\n", rep);

        if (rep == 1) {
            /* after the first full cycle, optionally bring up MQTT (needs
             * the radio, which condition A left running) */
            mqtt_reporter_try_init();
        }
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}

void app_main(void)
{
    /* 1. SRAM pattern before any heap/WiFi activity touches memory. */
    size_t n = puf_read_startup_pattern(s_puf, sizeof(s_puf));

    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    printf("\n### DEVICE mac=%02x:%02x:%02x:%02x:%02x:%02x idf=%s "
           "puf_bytes=%u\n",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], IDF_VER,
           (unsigned)n);

    stream_puf_frame();

    ESP_LOGI(TAG, "starting campaign task");
    xTaskCreatePinnedToCore(campaign_task, "campaign", 8192, NULL, 5,
                            NULL, 1);
}
