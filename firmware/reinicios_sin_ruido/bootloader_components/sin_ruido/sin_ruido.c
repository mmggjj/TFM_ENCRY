/* Bootloader sin la fuente de entropia del arranque (ver CMakeLists.txt). */
#include "esp_log.h"

void bootloader_hooks_include(void)
{
}

void __wrap_bootloader_random_enable(void)
{
    ESP_LOGW("sin_ruido", "fuente de entropia del arranque NO encendida");
}
