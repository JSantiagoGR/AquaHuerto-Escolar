/*
 * Sensor de humedad del suelo METER/Decagon ECH2O EC-5.
 * Excitación por pulso de 10 ms (hoja de datos: 2.5–3.6 V, 10 mA, ≤ 10 ms),
 * lectura ADC1 con calibración de ESP-IDF (line fitting), conversión a mV y a
 * %VWC con la regresión experimental de la Actividad 2.2.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "configuration.h"

typedef struct {
    bool valid;
    bool in_cal_range;      /* mV dentro del intervalo experimental calibrado */
    int mv;                 /* Mediana de las muestras (mV)                   */
    int spread_mv;          /* Diferencia máx-mín entre muestras              */
    float vwc_pct;          /* %VWC estimada (puede quedar fuera de 0-45 %)   */
    const char *status;     /* OK, SIN_SENAL, FUERA_DE_RANGO, INESTABLE, IMPOSIBLE, ADC_ERROR */
} soil_reading_t;

bool soil_sensor_init(void);
void soil_sensor_measure(const riego_config_t *cfg, soil_reading_t *out);
/* Conversión pura mV -> %VWC (usada también por la simulación y las pruebas) */
float soil_mv_to_vwc(const riego_config_t *cfg, float mv);
