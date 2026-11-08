/*
 * Sensor ambiental DHT22/AM2302 (temperatura y humedad RELATIVA del aire),
 * driver de la Prueba 03 en GPIO4. Es informativo: no cambia por sí solo la
 * humedad objetivo del suelo.
 */
#pragma once

#include <stdbool.h>

void environment_sensor_init(void);
/* Devuelve true si la lectura es válida (suma de verificación y rango) */
bool environment_sensor_read(float *temp_c, float *rh_pct);
