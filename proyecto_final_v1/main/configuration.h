/*
 * Configuración persistente (NVS). Todos los parámetros importantes se pueden
 * cambiar sin recompilar (consola serial o MQTT) dentro de límites duros que
 * ninguna orden remota puede superar.
 */
#pragma once

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "esp_err.h"

#define CONFIG_MAGIC    0x52494547u     /* "RIEG" */
#define CONFIG_VERSION  1u

typedef enum { MODE_A_TEST = 0, MODE_B_FINAL = 1 } op_mode_t;

typedef struct {
    uint32_t magic;
    uint32_t version;

    /* Humedad volumétrica del suelo (%VWC estimada con la regresión del EC-5) */
    float hum_min;              /* Bajo este valor el suelo necesita agua        */
    float hum_target;           /* Humedad a recuperar con los riegos            */
    float hum_max;              /* En o sobre este valor no se agrega agua       */
    float hum_critical;         /* Umbral de emergencia (debe ser < hum_min)     */

    /* Volúmenes */
    float liters_per_cycle;
    float max_liters_event;
    float max_liters_daily;
    float emergency_liters;

    /* Protecciones de bomba y flujo */
    float pump_max_s;           /* Tiempo máximo de bomba por ciclo              */
    float no_flow_s;            /* Segundos sin pulsos con bomba encendida       */
    float flow_max_lpm;         /* Caudal máximo creíble (bomba anuncia 6 L/min) */
    float valve_lead_ms;        /* Válvula abierta antes de encender bomba       */
    float valve_lag_ms;         /* Bomba apagada antes de cerrar válvula         */
    float idle_flow_pulses;     /* Pulsos con todo apagado para alarma           */

    /* Lógica automática */
    float infilt_min;           /* Espera de infiltración entre ciclos (min)     */
    float min_event_gap_min;    /* Intervalo mínimo entre eventos de riego       */
    float emergency_gap_min;    /* Intervalo mínimo entre emergencias            */
    float max_cycles;           /* Máximo de ciclos por evento                   */
    float dry_confirm;          /* Lecturas consecutivas bajo el mínimo          */
    float response_cycles;      /* Ciclos tras los que se exige respuesta        */
    float min_response_pp;      /* Aumento mínimo de %VWC esperado               */

    /* Caudalímetro */
    float pulses_per_liter;     /* 450 = valor usado en pruebas (sin calibrar)   */
    float overrun_ml;           /* Compensación de sobrepaso al cortar           */

    /* EC-5 */
    float soil_interval_s;      /* Intervalo base entre lecturas de humedad      */
    float ec5_slope;            /* %VWC por mV  (Actividad 2.2: 0.08146067)      */
    float ec5_offset;           /* %VWC         (Actividad 2.2: -23.932584)      */
    float ec5_mv_min;           /* Bajo esto: sensor desconectado / sin señal    */
    float ec5_mv_max;           /* Sobre esto: lectura imposible                 */
    float ec5_cal_mv_lo;        /* Intervalo experimental de la calibración      */
    float ec5_cal_mv_hi;

    /* Tinaco (PING))) */
    float tank_empty_cm;        /* Distancia sensor -> agua con tinaco vacío (0 = sin calibrar) */
    float tank_full_cm;         /* Distancia sensor -> agua con tinaco lleno (0 = sin calibrar) */
    float tank_min_pct;         /* Nivel mínimo de seguridad para regar          */
    float tank_interval_s;

    /* Horarios (minutos desde medianoche, hora local) */
    float win1_start, win1_end;
    float win2_start, win2_end;
    float midday_start, midday_end;

    /* Condiciones ambientales */
    float temp_postpone_c;      /* Sobre esta temperatura se pospone el riego rutinario */
    float hot_temp_c;           /* Desde aquí se acorta el intervalo de lectura         */
    float dry_rh_pct;           /* Bajo esta HR ambiental se acorta el intervalo        */

    float telemetry_s;

    uint8_t win1_en;
    uint8_t win2_en;
    uint8_t emergency_en;
    uint8_t auto_saved;         /* Estado del automático guardado (solo se usa en modo B) */
    uint8_t mode;               /* op_mode_t                                    */
    uint8_t power_enabled;      /* Salidas de potencia habilitadas (solo por consola) */
    uint8_t reserved[2];

    char tz[40];                /* Zona horaria POSIX (Chihuahua: "CST6")        */

    uint32_t crc;
} riego_config_t;

typedef enum { PT_FLOAT, PT_BOOL, PT_TIME, PT_STRING } param_type_t;

typedef struct {
    const char *key;
    param_type_t type;
    size_t offset;
    float min, max;
    uint8_t decimals;
    bool remote;                /* false: solo por consola serial                */
    const char *unit;
    const char *desc;
} config_param_t;

/* Inicializa y carga desde NVS. *was_reset = true si se cargaron valores por
 * defecto por datos inválidos/corruptos (no en el primer arranque). */
void config_init(bool *was_reset);

void config_defaults(riego_config_t *c);
bool config_validate(const riego_config_t *c, char *msg, size_t len);

void config_get(riego_config_t *out);
uint32_t config_generation(void);

/* Cambia un parámetro por nombre. remote = viene de MQTT. */
esp_err_t config_set(const char *key, const char *value, bool remote, char *msg, size_t len);
/* Cambia los tres umbrales de humedad de forma atómica */
esp_err_t config_set_humidity_range(float mn, float tg, float mx, char *msg, size_t len);
/* Valida y guarda un candidato completo */
esp_err_t config_apply(const riego_config_t *cand, char *msg, size_t len);
esp_err_t config_factory_reset(void);

int config_param_count(void);
const config_param_t *config_param_at(int i);
const config_param_t *config_param_find(const char *key);
void config_param_format(const riego_config_t *c, const config_param_t *p, char *out, size_t len);
float config_param_get_float(const riego_config_t *c, const config_param_t *p);

/* Utilidades de horario */
bool config_parse_time(const char *s, float *minutes);
void config_format_time(float minutes, char *out, size_t len);
bool config_tank_calibrated(const riego_config_t *c);
