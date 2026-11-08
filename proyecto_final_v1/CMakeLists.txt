# Proyecto Final v1 — Riego automatizado inteligente (ESP32 + ESP-IDF 6.0.2)
cmake_minimum_required(VERSION 3.16)

# Credenciales (Wi-Fi / MQTT) en un archivo local que NO se versiona.
# Si no existe, el firmware compila igual y funciona sin red.
# (La compilación de pruebas para QEMU define SDKCONFIG_DEFAULTS desde la línea de comandos.)
if(NOT SDKCONFIG_DEFAULTS)
    if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/sdkconfig.secrets")
        set(SDKCONFIG_DEFAULTS "sdkconfig.defaults;sdkconfig.secrets")
    else()
        set(SDKCONFIG_DEFAULTS "sdkconfig.defaults")
    endif()
endif()

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
idf_build_set_property(MINIMAL_BUILD ON)
project(riego_proyecto_final_v1)
