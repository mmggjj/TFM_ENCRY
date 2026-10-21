/* Prueba del paso del RNG del ESP32 sin ruido: ¿avanza con el reloj o con
 * las lecturas, y cuanto por ciclo?
 *
 * Bootloader sin la fuente de entropia del arranque (como
 * firmware/reinicios_sin_ruido). Con las interrupciones apagadas:
 *  - "antes": RST_BYTES con esp_fill_random, lo primero de app_main.
 *  - un retardo de un numero fijo de NOP en un bucle sin coste (instruccion
 *    loop de Xtensa, desde IRAM): el mismo numero de ciclos en cada arranque,
 *    sin depender del contador de ciclos (que no va en fase con el RNG).
 *  - "despues": otros RST_BYTES con esp_fill_random.
 * El retardo depende de la variante, que se elige en cada arranque con dos
 * bits del contador de ciclos al empezar (varia de un arranque a otro y no
 * depende de lo que salga en "antes"):
 *      0  N0           1  N0 + 2 (un ciclo de APB mas)
 *      2  N0 + 174     (lo que tarda una palabra de esp_fill_random)
 *      3  N0 + 17400   (cien palabras)
 * Si el generador da un paso por ciclo de APB desde un estado fijo y las
 * lecturas no lo mueven, dos arranques con el mismo "antes" dan el mismo
 * "despues" con la misma variante; con la 2 y la 3, el "despues" de la 0
 * desplazado 1 y 100 palabras; con la 1, otra secuencia que no se alinea.
 * Cada bloque va en hex con su CRC32 y al final "### RST_FIN". */
#include <stdio.h>
#include <stdint.h>
#include "esp_random.h"
#include "esp_system.h"
#include "esp_mac.h"
#include "esp_timer.h"
#include "esp_cpu.h"
#include "esp_rom_crc.h"
#include "esp_attr.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define RST_BYTES 1024
#define BYTES_LINEA 64
#define VARIANTE "paso"
#define N0 1740000u                      /* unos 10,9 ms a 160 MHz */

static const uint32_t s_extra[4] = {0, 2, 174, 17400};
static uint8_t s_antes[RST_BYTES];
static uint8_t s_despues[RST_BYTES];

/* n NOP en un bucle sin coste: n ciclos y un poco fijo de entrada y salida */
static void IRAM_ATTR nops(uint32_t n)
{
    __asm__ __volatile__("loop %0, 1f\n"
                         "nop\n"
                         "1:\n"
                         : "+r"(n) : : "memory");
}

static void sacar(const uint8_t mac[6], const char *bloque, const uint8_t *buf)
{
    printf("### RST_BEGIN mac=%02x:%02x:%02x:%02x:%02x:%02x variante=%s bloque=%s "
           "bytes=%d reset=%d t_us=0 ccount=0\n",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], VARIANTE, bloque,
           RST_BYTES, (int)esp_reset_reason());
    for (int i = 0; i < RST_BYTES; i += BYTES_LINEA) {
        for (int j = 0; j < BYTES_LINEA; j++) {
            printf("%02x", buf[i + j]);
        }
        printf("\n");
    }
    printf("### RST_END bloque=%s crc32=0x%08lx\n", bloque,
           (unsigned long)esp_rom_crc32_le(0, buf, RST_BYTES));
}

void app_main(void)
{
    portDISABLE_INTERRUPTS();
    uint32_t c0 = esp_cpu_get_cycle_count();
    esp_fill_random(s_antes, RST_BYTES);
    uint32_t c1 = esp_cpu_get_cycle_count();
    int var = (int)((c0 >> 4) & 3u);
    uint32_t n = N0 + s_extra[var];
    nops(n);
    uint32_t c2 = esp_cpu_get_cycle_count();
    esp_fill_random(s_despues, RST_BYTES);
    uint32_t c3 = esp_cpu_get_cycle_count();
    portENABLE_INTERRUPTS();

    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    sacar(mac, "antes", s_antes);
    sacar(mac, "despues", s_despues);
    /* ciclos: c_a = lectura "antes", c_r = retardo, c_d = lectura "despues" */
    printf("### RST_FIN var=%d n_nops=%lu c_ini=%lu c_a=%lu c_r=%lu c_d=%lu\n", var,
           (unsigned long)n, (unsigned long)c0, (unsigned long)(c1 - c0),
           (unsigned long)(c2 - c1), (unsigned long)(c3 - c2));
    fflush(stdout);
    for (;;) {
        vTaskDelay(portMAX_DELAY);
    }
}
