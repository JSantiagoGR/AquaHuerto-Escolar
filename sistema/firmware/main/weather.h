/*
 * Pronóstico meteorológico de Open-Meteo (https://open-meteo.com/en/docs)
 * por HTTPS con verificación de certificados (paquete de CA de ESP-IDF).
 * Datos de MODELO meteorológico, no mediciones locales. Se consulta cada
 * weather_min (30–180 min). Un pronóstico con más de 3 h de antigüedad se
 * considera VENCIDO y no se usa para decidir. Sin internet el riego sigue
 * funcionando con los sensores locales.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "ia_model.h"

#define WX_HOURS 30

typedef struct {
    bool valid;                 /* Hubo al menos una consulta correcta       */
    uint32_t fetch_epoch;       /* Momento de la consulta (hora del ESP32)   */
    uint32_t model_epoch;       /* "current.time" de Open-Meteo              */
    float cur_temp, cur_rh, cur_precip, cur_rain;
    int n;
    uint32_t time[WX_HOURS];
    float temp[WX_HOURS], rh[WX_HOURS], pprob[WX_HOURS], precip[WX_HOURS];
    float vpd[WX_HOURS], et0[WX_HOURS];
    float past_precip_6h;       /* Lluvia estimada por el modelo, últimas 6 h */
    float next6_precip;         /* Lluvia prevista próximas 6 h               */
    float next6_pprob_max;      /* Probabilidad máxima próximas 6 h           */
    float et0_24h;              /* ET0 FAO prevista próximas 24 h (mm)        */
    uint32_t ok_count, fail_count;
    int last_http;
    char last_error[64];
} weather_t;

void weather_start(void);
void weather_get(weather_t *out);
void weather_request_refresh(void);
/* Edad del pronóstico en segundos (UINT32_MAX si no hay) */
uint32_t weather_age_s(const weather_t *w, uint32_t now_epoch);
bool weather_fresh(const weather_t *w, uint32_t now_epoch);
/* Lluvia probable según configuración (solo con pronóstico vigente) */
bool weather_rain_expected(const weather_t *w, float prob_pct, float mm, uint32_t now_epoch);
/* Copia el pronóstico horario a partir de 'now' en el entorno de la IA */
void weather_fill_ia_env(const weather_t *w, uint32_t now_epoch, ia_env_t *env);
