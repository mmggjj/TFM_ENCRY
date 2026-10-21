# Una variante por directorio de build:
#   idf.py -B build_<v> -DFUENTE=<0..4> -DFUENTE_MS=<ms> -DVARIANTE=<nombre> build
# FUENTE: 0 control, 1 wifi_init, 2 radio, 3 adc, 4 bootrand (ver reinicios_fuentes.c)
idf_component_register(SRCS "reinicios_fuentes.c"
                       PRIV_REQUIRES esp_wifi esp_netif esp_event nvs_flash esp_timer
                                     esp_adc bootloader_support esp_phy)
if(NOT DEFINED FUENTE)
    set(FUENTE 0)
endif()
if(NOT DEFINED FUENTE_MS)
    set(FUENTE_MS 0)
endif()
if(NOT DEFINED VARIANTE)
    set(VARIANTE "fuente_control")
endif()
target_compile_definitions(${COMPONENT_LIB} PRIVATE FUENTE=${FUENTE} FUENTE_MS=${FUENTE_MS}
                           VARIANTE="${VARIANTE}")
