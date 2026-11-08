/*
 * Nivel del tinaco con el ultrasónico Parallax PING))) #28015 (driver de la
 * Prueba 03: disparo de 5 µs y medición del eco en GPIO18 con divisor 1k/2k).
 */
#pragma once

#include <stdbool.h>
#include "configuration.h"

typedef struct {
    bool valid;             /* Distancia válida y estable              */
    bool calibrated;        /* Hay referencias de vacío y lleno        */
    float distance_cm;      /* Distancia usada (filtrada)              */
    float distance_raw;     /* Distancia de esta medición (NAN si inválida) */
    float spread_cm;
    float level_pct;        /* Solo significativo si calibrated        */
    int samples_ok;
    const char *status;     /* OK, NO_CALIBRADO, SIN_ECO, INESTABLE, FUERA_DE_RANGO, RETENIDA */
    const char *filter;     /* Resultado del filtro entre mediciones (sensor_filter) */
} tank_reading_t;

void tank_level_init(void);
/* temp_c: temperatura para corregir la velocidad del sonido (NAN = 20 °C) */
void tank_level_measure(const riego_config_t *cfg, float temp_c, tank_reading_t *out);
/* Conversión pura distancia -> % (usada también por pruebas) */
float tank_distance_to_pct(const riego_config_t *cfg, float distance_cm);
