/*
 * Concentrador de sensores: tarea en el núcleo 1 que mide EC-5, tinaco y DHT22
 * en sus intervalos y guarda una "foto" protegida por mutex. Las esperas de
 * microsegundos de los drivers no afectan al control de riego (núcleo 0).
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "soil_sensor.h"
#include "tank_level.h"

typedef struct {
    soil_reading_t soil;
    uint32_t soil_seq;          /* Aumenta con cada lectura nueva del EC-5 */
    uint32_t soil_epoch;
    uint32_t soil_age_s;

    tank_reading_t tank;
    uint32_t tank_age_s;

    bool env_valid;
    float temp_c, rh_pct;
    uint32_t env_last_valid_epoch;
    uint32_t env_last_valid_uptime_s;
    uint8_t env_fail_count;

    bool simulated;
} sensor_snapshot_t;

void sensors_start(void);
void sensors_get(sensor_snapshot_t *out);
void sensors_request_soil(void);                 /* Lectura del EC-5 lo antes posible */
void sensors_set_soil_interval_s(uint32_t s);    /* Intervalo decidido por la lógica  */
