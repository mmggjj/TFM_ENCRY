# mismo programa que firmware/reinicios_radio; solo cambia el bootloader.
# idf.py -B build_espera -DSIN_RADIO=1 build  compila el control sin radio.
idf_component_register(SRCS "../../reinicios_radio/main/reinicios_radio.c"
                       PRIV_REQUIRES esp_wifi esp_netif esp_event nvs_flash esp_timer)
if(SIN_RADIO)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE SIN_RADIO=1 VARIANTE="espera_sin_ruido")
else()
    target_compile_definitions(${COMPONENT_LIB} PRIVATE VARIANTE="radio_sin_ruido")
endif()
