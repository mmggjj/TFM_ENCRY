idf_component_register(SRCS "main.c"
                       INCLUDE_DIRS "."
                       REQUIRES motor_i2c mbedtls esp_rom)
