/*
 * PROYECTO FINAL v1 — RIEGO AUTOMATIZADO INTELIGENTE
 * ESP32-WROOM-32U (ESP32-D0WD-V3 rev 3.1) · ESP-IDF 6.0.2
 *
 * Bomba 12 V y electroválvula NC en ON/OFF (sin PWM, sin PI/PID).
 * El agua se dosifica contando pulsos del YF-S201. La necesidad de riego la
 * decide la humedad volumétrica del EC-5, con horarios, nivel del tinaco y
 * condiciones ambientales. Supervisión y control por MQTT/Node-RED y consola.
 *
 * Arquitectura (ver ARQUITECTURA.md):
 *   actuators  -> GPIO de potencia, enclavamiento y paro de emergencia
 *   safety     -> supervisor independiente (tope duro y vigilancia de la tarea)
 *   sensors    -> EC-5, PING))), DHT22 (núcleo 1) + simulación
 *   flow_sensor-> YF-S201 por PCNT
 *   irrigation_logic      -> máquina de estados PURA (probada con SELFTEST)
 *   irrigation_controller -> tarea de control (núcleo 0)
 *   configuration/storage -> NVS con validación y CRC
 *   wifi_manager/mqtt_manager/commands/console -> comunicación
 */
#include <stdio.h>

#include "esp_log.h"
#include "esp_system.h"

#include "actuators.h"
#include "board.h"
#include "configuration.h"
#include "console.h"
#include "flow_sensor.h"
#include "irrigation_controller.h"
#include "mqtt_manager.h"
#include "safety.h"
#include "sensors.h"
#include "simulation.h"
#include "storage.h"
#include "timekeeping.h"
#include "wifi_manager.h"

static const char *TAG = "main";

void app_main(void)
{
    /* 1) LO PRIMERO: bomba y electroválvula en estado seguro (inactivas) */
    actuators_init();

    printf("\n==============================================================\n");
    printf(" RIEGO AUTOMATIZADO INTELIGENTE - PROYECTO FINAL v1\n");
    printf(" ESP32 + EC-5 + YF-S201 + PING))) + DHT22 + MQTT\n");
    printf("==============================================================\n");
    esp_reset_reason_t rr = esp_reset_reason();
    printf("Motivo de reinicio: %d%s\n", (int)rr,
           rr == ESP_RST_TASK_WDT ? " (WATCHDOG DE TAREAS)" :
           rr == ESP_RST_BROWNOUT ? " (CAIDA DE ALIMENTACION)" :
           rr == ESP_RST_PANIC ? " (PANICO)" : "");

    if (!board_check_pins(false)) {
        ESP_LOGE(TAG, "Conflicto de pines: revise board.h");
    }

    /* 2) Configuración y datos persistentes */
    storage_init();
    bool cfg_reset = false;
    config_init(&cfg_reset);
    riego_config_t cfg;
    config_get(&cfg);
    time_init(cfg.tz);
    sim_reset();
    sim()->active = false;

    actuators_set_enable(cfg.power_enabled != 0, false);
    printf("Modo %s | Salidas de potencia %s\n",
           cfg.mode == MODE_B_FINAL ? "B (INSTALACION FINAL)" : "A (PRUEBAS)",
           cfg.power_enabled ? "HABILITADAS" : "DESHABILITADAS (version segura)");

    /* 3) Sensores y seguridad */
    flow_sensor_init();
    sensors_start();
    safety_start();

    /* 4) Control y consola */
    controller_start(cfg_reset);
    console_start();

    /* 5) Red (opcional: todo lo crítico funciona sin red) */
    mqtt_manager_init();
    wifi_manager_start();

    printf("Escriba AYUDA en el monitor serial para ver los comandos.\n");
}
