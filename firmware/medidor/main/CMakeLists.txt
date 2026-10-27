idf_component_register(SRCS "main.c" "lectura.c"
                       INCLUDE_DIRS "."
                       REQUIRES motor_i2c mbedtls esp_rom esp_hw_support)
