idf_component_register(SRCS "sin_ruido.c")
# bootloader_init() del ESP32 (bootloader_esp32.c) acaba llamando a
# bootloader_random_enable(), que pone el SAR ADC en modo prueba y mete su
# ruido en el RNG mientras dura el arranque. Con --wrap esa llamada va a la
# funcion vacia de sin_ruido.c; el resto del bootloader no cambia.
target_link_libraries(${COMPONENT_LIB} INTERFACE "-Wl,--wrap=bootloader_random_enable")
target_link_libraries(${COMPONENT_LIB} INTERFACE "-u bootloader_hooks_include")
