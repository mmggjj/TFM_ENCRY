/**
 * @file temp_monitor.c
 * @brief Legacy ROM temperature sensor access (original ESP32).
 */
#include "temp_monitor.h"
#include <stdint.h>

extern uint8_t temprature_sens_read(void); /* ROM, Fahrenheit, sic */

float temp_read_internal(void)
{
    return ((float)temprature_sens_read() - 32.0f) / 1.8f;
}
