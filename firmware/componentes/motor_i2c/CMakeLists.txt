# esp_driver_i2c va explicito: hasta ESP-IDF 5.x el componente "driver" era
# monolitico y arrastraba el I2C, pero en 6.0 esta partido y el include de
# driver/i2c_master.h deja de resolverse. Declararlo funciona en 5.2 en
# adelante y en 6.x, asi que el componente compila en las dos ramas.
idf_component_register(SRCS "motor_i2c.c"
                       INCLUDE_DIRS "include"
                       REQUIRES driver esp_driver_i2c)
