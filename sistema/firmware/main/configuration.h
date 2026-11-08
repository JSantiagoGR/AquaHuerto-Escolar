/*
 * Configuración persistente (NVS). Todos los parámetros importantes se pueden
 * cambiar sin recompilar (consola serial o MQTT) dentro de límites duros que
 * ninguna orden remota puede superar.
 *
 * config_table.c  -> tabla, valores por defecto y validación (lógica PURA,
 *                    también se compila en la PC para pruebas y simulador)
 * configuration.c -> almacenamiento en NVS con mutex y CRC
 */
#pragma once

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define CONFIG_MAGIC    0x52494547u     /* "RIEG" */
#define CONFIG_VERSION  3u              /* v3: escala del EC-5 (agua/volumen de suelo) */

/* Perfil de instalación (antes "modo A/B"): no confundir con el modo de operación */
typedef enum { MODE_A_TEST = 0, MODE_B_FINAL = 1 } op_mode_t;

typedef struct {
    uint32_t magic;
    uint32_t version;

    /* Humedad volumétrica del suelo (%VWC estimada con la calibración del EC-5).
     * Orden obligatorio: crítica < mínima < objetivo < reserva <= máxima      */
    float hum_min;              /* Mínima normal                                  */
    float hum_target;           /* Humedad recomendada / óptima                   */
    float hum_max;              /* Máxima: en o sobre este valor no se agrega agua */
    float hum_critical;         /* Umbral de emergencia                           */
    float hum_reserve;          /* Reserva superior segura (techo de las dosis)   */
    float auto_hyst_pp;         /* Histéresis bajo el objetivo para iniciar       */

    /* Volúmenes */
    float liters_per_cycle;
    float max_liters_event;
    float max_liters_daily;
    float emergency_liters;

    /* Protecciones de bomba y flujo */
    float pump_max_s;
    float no_flow_s;
    float flow_max_lpm;
    float valve_lead_ms;
    float valve_lag_ms;
    float idle_flow_pulses;

    /* Lógica automática */
    float infilt_min;
    float min_event_gap_min;
    float emergency_gap_min;
    float max_cycles;
    float dry_confirm;
    float response_cycles;
    float min_response_pp;

    /* Caudalímetro */
    float pulses_per_liter;     /* 450 = valor provisional (sin contraste)        */
    float overrun_ml;

    /* EC-5 */
    float soil_interval_s;
    float ec5_slope;
    float ec5_offset;
    float ec5_mv_min;
    float ec5_mv_max;
    float ec5_cal_mv_lo;
    float ec5_cal_mv_hi;
    float ec5_scale;            /* 1: la recta de la Act. 2.2 da agua/(tierra+agua) y se
                                   convierte a %VWC estándar = agua/volumen de suelo      */
    float data_version;         /* Versión de calibración/suelo: separa datos incompatibles */

    /* Tinaco */
    float tank_empty_cm;
    float tank_full_cm;
    float tank_min_pct;
    float tank_interval_s;

    /* Horarios (minutos desde medianoche, hora local) */
    float win1_start, win1_end;
    float win2_start, win2_end;
    float midday_start, midday_end;

    /* Condiciones ambientales */
    float temp_postpone_c;
    float hot_temp_c;
    float dry_rh_pct;

    /* Pronóstico (Open-Meteo) */
    float lat, lon;             /* 0/0 = sin ubicación: no se consulta            */
    float weather_min;          /* Intervalo de consulta                          */
    float rain_prob_pct;        /* Probabilidad para posponer                     */
    float rain_mm;              /* Lluvia prevista (próximas 6 h) para posponer   */
    float rise_pp;              /* Aumento no explicado de humedad a reportar     */

    /* IA (control predictivo adaptativo, sin PID ni PWM) */
    float ia_gain_prior;        /* %VWC por litro supuesto al inicio (NO calibrado) */
    float ia_tol_pp;            /* Tolerancia meta tras infiltración (±)           */
    float ia_margin_pp;         /* Margen sobre la mínima al planear               */
    float ia_kp;                /* Corrección proporcional acotada (0..1)          */
    float ia_min_events;        /* Riegos observados antes de validar              */
    float ia_min_hours;         /* Horas de secado observadas antes de validar     */
    float kc;                   /* Coeficiente de cultivo de la etapa (FAO-56)     */

    float telemetry_s;

    uint8_t win1_en;
    uint8_t win2_en;
    uint8_t emergency_en;
    uint8_t auto_saved;         /* Modo de operación guardado (solo perfil B)      */
    uint8_t mode;               /* op_mode_t (perfil de instalación)               */
    uint8_t power_enabled;      /* Salidas de potencia (solo por consola)          */
    uint8_t weather_en;
    uint8_t rain_postpone_en;

    uint32_t profile_version;   /* Versión del perfil aplicado desde el dashboard */
    char crop_id[24];
    char crop_name[32];
    char stage[24];
    char tz[40];                /* Zona horaria POSIX (Chihuahua: "CST6")          */

    uint32_t crc;
} riego_config_t;

typedef enum { PT_FLOAT, PT_BOOL, PT_TIME, PT_STRING, PT_U8, PT_U32 } param_type_t;

typedef struct {
    const char *key;
    param_type_t type;
    size_t offset;
    float min, max;             /* PT_STRING: max = tamaño del campo              */
    uint8_t decimals;
    bool remote;                /* false: solo por consola serial                 */
    const char *unit;
    const char *desc;
} config_param_t;

/* ---------------- Parte pura (config_table.c) ---------------- */
void config_defaults(riego_config_t *c);
bool config_validate(const riego_config_t *c, char *msg, size_t len);
int config_param_count(void);
const config_param_t *config_param_at(int i);
const config_param_t *config_param_find(const char *key);
void config_param_format(const riego_config_t *c, const config_param_t *p, char *out, size_t len);
float config_param_get_float(const riego_config_t *c, const config_param_t *p);
/* Cambia un parámetro en un candidato (límites individuales, sin relaciones). 0 = OK */
int config_param_set_str(riego_config_t *c, const config_param_t *p, const char *value, char *msg, size_t len);
bool config_parse_time(const char *s, float *minutes);
void config_format_time(float minutes, char *out, size_t len);
bool config_tank_calibrated(const riego_config_t *c);
bool config_location_set(const riego_config_t *c);
/* EC-5: mV <-> %VWC estándar (agua / volumen de suelo) */
float ec5_mv_to_vwc(const riego_config_t *c, float mv);
float ec5_vwc_to_mv(const riego_config_t *c, float vwc);

/* ---------------- Parte NVS (configuration.c) ---------------- */
#ifndef HOST_BUILD
#include "esp_err.h"
void config_init(bool *was_reset);
void config_get(riego_config_t *out);
uint32_t config_generation(void);
esp_err_t config_set(const char *key, const char *value, bool remote, char *msg, size_t len);
esp_err_t config_set_humidity_range(float mn, float tg, float mx, char *msg, size_t len);
esp_err_t config_apply(const riego_config_t *cand, char *msg, size_t len);
esp_err_t config_factory_reset(void);
#endif
