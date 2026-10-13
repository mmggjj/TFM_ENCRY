/**
 * @file temp_monitor.h
 * @brief Die temperature readout (legacy ROM call on the original ESP32).
 *
 * The original ESP32 has no official temperature-sensor driver in
 * ESP-IDF v5 (the driver covers S2/S3/C series only); the sensor remains
 * reachable through the undocumented ROM function temprature_sens_read()
 * (sic), returning uncalibrated Fahrenheit. Valid as a RELATIVE
 * indicator, which is what the temperature-correlation experiment needs.
 *
 * TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
 */
#ifndef TEMP_MONITOR_H
#define TEMP_MONITOR_H

#ifdef __cplusplus
extern "C" {
#endif

/** @return die temperature in Celsius (uncalibrated absolute value). */
float temp_read_internal(void);

#ifdef __cplusplus
}
#endif

#endif /* TEMP_MONITOR_H */
