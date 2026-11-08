/*
 * Tabla de parámetros, valores por defecto y validación de la configuración.
 * Lógica PURA (sin ESP-IDF): se compila igual en el ESP32 y en la PC
 * (pruebas automáticas y simulador).
 */
#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "configuration.h"

#ifdef HOST_BUILD
static size_t strlcpy_h(char *d, const char *s, size_t n)
{
    size_t l = strlen(s);
    if (n) {
        size_t c = (l >= n) ? n - 1 : l;
        memcpy(d, s, c);
        d[c] = '\0';
    }
    return l;
}
#define strlcpy strlcpy_h
#endif

#define OFF(f) offsetof(riego_config_t, f)

/* Nombre, tipo, ubicación, límites DUROS, decimales, remoto, unidad, descripción */
static const config_param_t PARAMS[] = {
    {"hum_critical",      PT_FLOAT, OFF(hum_critical),      0,    55,   1, true,  "%VWC", "Umbral de emergencia"},
    {"hum_min",           PT_FLOAT, OFF(hum_min),           5,    60,   1, true,  "%VWC", "Humedad mínima normal"},
    {"hum_target",        PT_FLOAT, OFF(hum_target),        5,    65,   1, true,  "%VWC", "Humedad recomendada / óptima"},
    {"hum_reserve",       PT_FLOAT, OFF(hum_reserve),       5,    70,   1, true,  "%VWC", "Reserva superior segura"},
    {"hum_max",           PT_FLOAT, OFF(hum_max),           5,    70,   1, true,  "%VWC", "Humedad máxima permitida"},
    {"auto_hyst_pp",      PT_FLOAT, OFF(auto_hyst_pp),      0.5f, 10,   1, true,  "%VWC", "Histéresis bajo el objetivo para iniciar"},
    {"liters_per_cycle",  PT_FLOAT, OFF(liters_per_cycle),  0.1f, 5,    2, true,  "L",    "Litros máximos por ciclo"},
    {"max_liters_event",  PT_FLOAT, OFF(max_liters_event),  0.1f, 10,   2, true,  "L",    "Máximo de litros por evento"},
    {"max_liters_daily",  PT_FLOAT, OFF(max_liters_daily),  0.5f, 50,   2, true,  "L",    "Máximo de litros por día"},
    {"emergency_liters",  PT_FLOAT, OFF(emergency_liters),  0.1f, 2,    2, true,  "L",    "Litros del riego de emergencia"},
    {"pump_max_s",        PT_FLOAT, OFF(pump_max_s),        10,   300,  0, true,  "s",    "Tiempo máximo de bomba por ciclo"},
    {"no_flow_s",         PT_FLOAT, OFF(no_flow_s),         3,    60,   0, true,  "s",    "Tiempo máximo sin pulsos con bomba encendida"},
    {"flow_max_lpm",      PT_FLOAT, OFF(flow_max_lpm),      1,    15,   1, true,  "L/min","Caudal máximo creíble"},
    {"valve_lead_ms",     PT_FLOAT, OFF(valve_lead_ms),     100,  3000, 0, true,  "ms",   "Válvula abierta antes de la bomba"},
    {"valve_lag_ms",      PT_FLOAT, OFF(valve_lag_ms),      100,  3000, 0, true,  "ms",   "Bomba apagada antes de cerrar válvula"},
    {"idle_flow_pulses",  PT_FLOAT, OFF(idle_flow_pulses),  5,    500,  0, true,  "pulsos","Pulsos con todo apagado para alarma (por minuto)"},
    {"infilt_min",        PT_FLOAT, OFF(infilt_min),        1,    120,  0, true,  "min",  "Espera de infiltración"},
    {"min_event_gap_min", PT_FLOAT, OFF(min_event_gap_min), 0,    1440, 0, true,  "min",  "Intervalo mínimo entre eventos"},
    {"emergency_gap_min", PT_FLOAT, OFF(emergency_gap_min), 30,   1440, 0, true,  "min",  "Intervalo mínimo entre emergencias"},
    {"max_cycles",        PT_FLOAT, OFF(max_cycles),        1,    6,    0, true,  "",     "Máximo de ciclos por evento"},
    {"dry_confirm",       PT_FLOAT, OFF(dry_confirm),       1,    5,    0, true,  "",     "Lecturas bajo el umbral para confirmar"},
    {"response_cycles",   PT_FLOAT, OFF(response_cycles),   1,    6,    0, true,  "",     "Ciclos tras los que se exige respuesta del suelo"},
    {"min_response_pp",   PT_FLOAT, OFF(min_response_pp),   0.2f, 10,   1, true,  "%VWC", "Aumento mínimo de humedad esperado"},
    {"pulses_per_liter",  PT_FLOAT, OFF(pulses_per_liter),  200,  1000, 1, true,  "p/L",  "Pulsos por litro del YF-S201"},
    {"overrun_ml",        PT_FLOAT, OFF(overrun_ml),        0,    200,  0, true,  "mL",   "Compensación de sobrepaso"},
    {"soil_interval_s",   PT_FLOAT, OFF(soil_interval_s),   30,   3600, 0, true,  "s",    "Intervalo base de lectura del EC-5"},
    {"ec5_slope",         PT_FLOAT, OFF(ec5_slope),         0.001f, 1,  8, true,  "%/mV", "Pendiente de calibración EC-5"},
    {"ec5_offset",        PT_FLOAT, OFF(ec5_offset),        -100, 100,  6, true,  "%",    "Ordenada de calibración EC-5"},
    {"ec5_scale",         PT_FLOAT, OFF(ec5_scale),         0,    1,    0, true,  "",     "1 = recta en agua/(tierra+agua) (Act. 2.2), se convierte a agua/suelo"},
    {"ec5_mv_min",        PT_FLOAT, OFF(ec5_mv_min),        50,   600,  0, true,  "mV",   "mV mínimo válido del EC-5"},
    {"ec5_mv_max",        PT_FLOAT, OFF(ec5_mv_max),        900,  3000, 0, true,  "mV",   "mV máximo válido del EC-5"},
    {"ec5_cal_mv_lo",     PT_FLOAT, OFF(ec5_cal_mv_lo),     0,    3000, 0, true,  "mV",   "Límite inferior del intervalo calibrado"},
    {"ec5_cal_mv_hi",     PT_FLOAT, OFF(ec5_cal_mv_hi),     0,    3000, 0, true,  "mV",   "Límite superior del intervalo calibrado"},
    {"data_version",      PT_FLOAT, OFF(data_version),      1,    9999, 0, true,  "",     "Versión de calibración/suelo de los datos"},
    {"tank_empty_cm",     PT_FLOAT, OFF(tank_empty_cm),     0,    300,  1, true,  "cm",   "Distancia al agua con tinaco vacío (0=sin calibrar)"},
    {"tank_full_cm",      PT_FLOAT, OFF(tank_full_cm),      0,    300,  1, true,  "cm",   "Distancia al agua con tinaco lleno (0=sin calibrar)"},
    {"tank_min_pct",      PT_FLOAT, OFF(tank_min_pct),      5,    90,   0, true,  "%",    "Nivel mínimo de seguridad del tinaco"},
    {"tank_interval_s",   PT_FLOAT, OFF(tank_interval_s),   5,    600,  0, true,  "s",    "Intervalo de lectura del tinaco"},
    {"win1_en",           PT_BOOL,  OFF(win1_en),           0,    1,    0, true,  "",     "Horario matutino habilitado"},
    {"win1_start",        PT_TIME,  OFF(win1_start),        0,    1439, 0, true,  "HH:MM","Inicio horario matutino"},
    {"win1_end",          PT_TIME,  OFF(win1_end),          0,    1439, 0, true,  "HH:MM","Fin horario matutino"},
    {"win2_en",           PT_BOOL,  OFF(win2_en),           0,    1,    0, true,  "",     "Horario vespertino habilitado"},
    {"win2_start",        PT_TIME,  OFF(win2_start),        0,    1439, 0, true,  "HH:MM","Inicio horario vespertino"},
    {"win2_end",          PT_TIME,  OFF(win2_end),          0,    1439, 0, true,  "HH:MM","Fin horario vespertino"},
    {"midday_start",      PT_TIME,  OFF(midday_start),      0,    1439, 0, true,  "HH:MM","Inicio de bloqueo de mediodía"},
    {"midday_end",        PT_TIME,  OFF(midday_end),        0,    1439, 0, true,  "HH:MM","Fin de bloqueo de mediodía"},
    {"emergency_en",      PT_BOOL,  OFF(emergency_en),      0,    1,    0, true,  "",     "Riegos de emergencia habilitados"},
    {"temp_postpone_c",   PT_FLOAT, OFF(temp_postpone_c),   20,   50,   1, true,  "C",    "Temperatura para posponer riego rutinario"},
    {"hot_temp_c",        PT_FLOAT, OFF(hot_temp_c),        15,   50,   1, true,  "C",    "Temperatura para acortar el intervalo de lectura"},
    {"dry_rh_pct",        PT_FLOAT, OFF(dry_rh_pct),        5,    80,   0, true,  "%HR",  "HR ambiental para acortar el intervalo"},
    {"weather_en",        PT_BOOL,  OFF(weather_en),        0,    1,    0, true,  "",     "Consultar Open-Meteo"},
    {"lat",               PT_FLOAT, OFF(lat),               -90,  90,   4, true,  "°",    "Latitud del huerto"},
    {"lon",               PT_FLOAT, OFF(lon),               -180, 180,  4, true,  "°",    "Longitud del huerto"},
    {"weather_min",       PT_FLOAT, OFF(weather_min),       30,   180,  0, true,  "min",  "Intervalo de consulta del pronóstico"},
    {"rain_postpone_en",  PT_BOOL,  OFF(rain_postpone_en),  0,    1,    0, true,  "",     "Posponer riego rutinario si se pronostica lluvia"},
    {"rain_prob_pct",     PT_FLOAT, OFF(rain_prob_pct),     10,   100,  0, true,  "%",    "Probabilidad de lluvia para posponer"},
    {"rain_mm",           PT_FLOAT, OFF(rain_mm),           0.2f, 50,   1, true,  "mm",   "Lluvia prevista (6 h) para posponer"},
    {"rise_pp",           PT_FLOAT, OFF(rise_pp),           1,    20,   1, true,  "%VWC", "Aumento no explicado de humedad a reportar"},
    {"ia_gain_prior",     PT_FLOAT, OFF(ia_gain_prior),     0.1f, 30,   2, true,  "%/L",  "Ganancia supuesta inicial (NO calibrada)"},
    {"ia_tol_pp",         PT_FLOAT, OFF(ia_tol_pp),         0.5f, 10,   1, true,  "%VWC", "Tolerancia de la meta IA"},
    {"ia_margin_pp",      PT_FLOAT, OFF(ia_margin_pp),      0,    10,   1, true,  "%VWC", "Margen sobre la mínima al planear"},
    {"ia_kp",             PT_FLOAT, OFF(ia_kp),             0.1f, 1,    2, true,  "",     "Corrección proporcional acotada"},
    {"ia_min_events",     PT_FLOAT, OFF(ia_min_events),     3,    50,   0, true,  "",     "Riegos observados antes de validar"},
    {"ia_min_hours",      PT_FLOAT, OFF(ia_min_hours),      12,   720,  0, true,  "h",    "Horas de secado observadas antes de validar"},
    {"kc",                PT_FLOAT, OFF(kc),                0.1f, 1.5f, 2, true,  "",     "Coeficiente de cultivo de la etapa"},
    {"telemetry_s",       PT_FLOAT, OFF(telemetry_s),       2,    600,  0, true,  "s",    "Intervalo de telemetría MQTT"},
    {"tz",                PT_STRING,OFF(tz),                0,    40,   0, true,  "",     "Zona horaria POSIX"},
    {"crop_id",           PT_STRING,OFF(crop_id),           0,    24,   0, true,  "",     "Identificador del cultivo activo"},
    {"crop_name",         PT_STRING,OFF(crop_name),         0,    32,   0, true,  "",     "Nombre del cultivo activo"},
    {"stage",             PT_STRING,OFF(stage),             0,    24,   0, true,  "",     "Etapa activa"},
    {"profile_version",   PT_U32,   OFF(profile_version),   0,    4e9f, 0, true,  "",     "Versión del perfil aplicado"},
    /* Solo por consola serial (presencia física) */
    {"mode",              PT_U8,    OFF(mode),              0,    1,    0, false, "",     "Perfil 0=A pruebas, 1=B instalación"},
    {"power_enabled",     PT_BOOL,  OFF(power_enabled),     0,    1,    0, false, "",     "Salidas de potencia habilitadas"},
    {"auto_saved",        PT_U8,    OFF(auto_saved),        0,    2,    0, false, "",     "Modo de operación guardado (perfil B)"},
};

#define NPARAMS (sizeof(PARAMS) / sizeof(PARAMS[0]))

void config_defaults(riego_config_t *c)
{
    memset(c, 0, sizeof(*c));
    c->magic = CONFIG_MAGIC;
    c->version = CONFIG_VERSION;

    /* Ejemplos de demostración, NO recomendaciones agronómicas: los valores
     * reales salen del perfil de cultivo y de la calibración del suelo. */
    c->hum_critical = 18.0f;
    c->hum_min = 25.0f;
    c->hum_target = 35.0f;
    c->hum_reserve = 40.0f;
    c->hum_max = 45.0f;
    c->auto_hyst_pp = 2.0f;

    c->liters_per_cycle = 1.0f;
    c->max_liters_event = 3.0f;
    c->max_liters_daily = 10.0f;
    c->emergency_liters = 0.5f;

    c->pump_max_s = 180.0f;         /* Caudal real ~1.3 L/min: permite riegos manuales de ~3.9 L */
    c->no_flow_s = 10.0f;
    c->flow_max_lpm = 8.0f;
    c->valve_lead_ms = 300.0f;
    c->valve_lag_ms = 300.0f;
    c->idle_flow_pulses = 20.0f;

    c->infilt_min = 15.0f;
    c->min_event_gap_min = 60.0f;
    c->emergency_gap_min = 240.0f;
    c->max_cycles = 3.0f;
    c->dry_confirm = 2.0f;
    c->response_cycles = 2.0f;
    c->min_response_pp = 1.0f;

    c->pulses_per_liter = 450.0f;   /* Provisional: sin contraste con recipiente */
    c->overrun_ml = 0.0f;

    c->soil_interval_s = 300.0f;
    c->ec5_slope = 0.08146067f;     /* Actividad 2.2 */
    c->ec5_offset = -23.932584f;
    c->ec5_mv_min = 200.0f;
    c->ec5_mv_max = 1500.0f;
    c->ec5_cal_mv_lo = 360.0f;
    c->ec5_cal_mv_hi = 870.0f;
    c->ec5_scale = 1.0f;            /* La Act. 2.2 definió %VWC = agua/(tierra+agua) */
    c->data_version = 1.0f;

    c->tank_empty_cm = 0.0f;        /* Sin calibrar: no se inventan medidas */
    c->tank_full_cm = 0.0f;
    c->tank_min_pct = 20.0f;
    c->tank_interval_s = 10.0f;

    c->win1_en = 1;
    c->win1_start = 6 * 60;
    c->win1_end = 9 * 60;
    c->win2_en = 1;
    c->win2_start = 18 * 60;
    c->win2_end = 20 * 60;
    c->midday_start = 11 * 60;
    c->midday_end = 16 * 60;
    c->emergency_en = 1;

    c->temp_postpone_c = 35.0f;
    c->hot_temp_c = 30.0f;
    c->dry_rh_pct = 30.0f;

    /* Ubicación aproximada (centro de Chihuahua). Ajustar a las coordenadas
     * reales del huerto desde el dashboard o la consola. */
    c->weather_en = 1;
    c->lat = 28.6598f;              /* Esc. Prim. Fed. Belisario Domínguez (huerto) */
    c->lon = -106.0741f;
    c->weather_min = 60.0f;
    c->rain_postpone_en = 1;
    c->rain_prob_pct = 70.0f;
    c->rain_mm = 2.0f;
    c->rise_pp = 3.0f;

    c->ia_gain_prior = 2.0f;        /* Supuesto inicial: se reemplaza al aprender */
    c->ia_tol_pp = 2.0f;
    c->ia_margin_pp = 1.0f;
    c->ia_kp = 0.8f;
    c->ia_min_events = 6.0f;
    c->ia_min_hours = 48.0f;
    c->kc = 1.0f;

    c->telemetry_s = 10.0f;

    c->auto_saved = 0;
    c->mode = MODE_A_TEST;
    c->power_enabled = 0;           /* Versión segura: potencia deshabilitada */
    c->profile_version = 0;
    strlcpy(c->crop_id, "sin_perfil", sizeof(c->crop_id));
    strlcpy(c->crop_name, "Sin perfil (valores de ejemplo)", sizeof(c->crop_name));
    strlcpy(c->stage, "-", sizeof(c->stage));
    strlcpy(c->tz, "CST6", sizeof(c->tz));   /* Chihuahua: UTC-6 sin horario de verano */
}

bool config_tank_calibrated(const riego_config_t *c)
{
    return c->tank_empty_cm > 0.0f && c->tank_full_cm > 0.0f &&
           c->tank_empty_cm > c->tank_full_cm;
}

bool config_location_set(const riego_config_t *c)
{
    return !(fabsf(c->lat) < 0.0001f && fabsf(c->lon) < 0.0001f);
}

static bool str_ok(const char *s, size_t n)
{
    return memchr(s, '\0', n) != NULL;
}

bool config_validate(const riego_config_t *c, char *msg, size_t len)
{
    for (size_t i = 0; i < NPARAMS; i++) {
        const config_param_t *p = &PARAMS[i];
        if (p->type == PT_STRING) {
            if (!str_ok((const char *)c + p->offset, (size_t)p->max)) {
                snprintf(msg, len, "%s: texto sin terminar", p->key);
                return false;
            }
            continue;
        }
        float v = config_param_get_float(c, p);
        if (isnan(v) || v < p->min || v > p->max) {
            snprintf(msg, len, "%s fuera de limites [%g, %g]", p->key, p->min, p->max);
            return false;
        }
    }
    if (!(c->hum_critical + 1.0f <= c->hum_min)) {
        snprintf(msg, len, "Debe cumplirse EMERGENCIA < MINIMA (al menos 1 punto): %.1f / %.1f",
                 c->hum_critical, c->hum_min);
        return false;
    }
    if (!(c->hum_min + 1.0f <= c->hum_target && c->hum_target + 0.5f <= c->hum_reserve &&
          c->hum_reserve <= c->hum_max)) {
        snprintf(msg, len, "Debe cumplirse MINIMA < OBJETIVO < RESERVA <= MAXIMA: %.1f / %.1f / %.1f / %.1f",
                 c->hum_min, c->hum_target, c->hum_reserve, c->hum_max);
        return false;
    }
    if (c->hum_target - c->auto_hyst_pp <= c->hum_critical) {
        snprintf(msg, len, "La histeresis es demasiado grande: OBJETIVO - histeresis debe superar la emergencia");
        return false;
    }
    if (c->liters_per_cycle > c->max_liters_event) {
        snprintf(msg, len, "liters_per_cycle no puede superar max_liters_event");
        return false;
    }
    if (c->max_liters_event > c->max_liters_daily) {
        snprintf(msg, len, "max_liters_event no puede superar max_liters_daily");
        return false;
    }
    if (c->emergency_liters > c->max_liters_event) {
        snprintf(msg, len, "emergency_liters no puede superar max_liters_event");
        return false;
    }
    if (c->ec5_mv_min >= c->ec5_mv_max) {
        snprintf(msg, len, "ec5_mv_min debe ser menor que ec5_mv_max");
        return false;
    }
    if ((c->tank_empty_cm > 0.0f) != (c->tank_full_cm > 0.0f)) {
        snprintf(msg, len, "Calibre ambos niveles del tinaco (vacio y lleno) o ninguno");
        return false;
    }
    if (c->tank_empty_cm > 0.0f) {
        if (c->tank_full_cm < 2.0f || c->tank_empty_cm < c->tank_full_cm + 5.0f) {
            snprintf(msg, len, "Tinaco: se requiere full_cm >= 2 y empty_cm >= full_cm + 5");
            return false;
        }
    }
    if (c->win1_start == c->win1_end || c->win2_start == c->win2_end) {
        snprintf(msg, len, "Un horario no puede iniciar y terminar a la misma hora");
        return false;
    }
    if (c->tz[0] == '\0') {
        snprintf(msg, len, "Zona horaria invalida");
        return false;
    }
    if (msg && len) {
        msg[0] = '\0';
    }
    return true;
}

int config_param_count(void) { return (int)NPARAMS; }

const config_param_t *config_param_at(int i)
{
    return (i >= 0 && i < (int)NPARAMS) ? &PARAMS[i] : NULL;
}

const config_param_t *config_param_find(const char *key)
{
    for (size_t i = 0; i < NPARAMS; i++) {
        if (strcasecmp(key, PARAMS[i].key) == 0) {
            return &PARAMS[i];
        }
    }
    return NULL;
}

float config_param_get_float(const riego_config_t *c, const config_param_t *p)
{
    const uint8_t *base = (const uint8_t *)c;
    switch (p->type) {
    case PT_BOOL:
    case PT_U8:
        return (float)*(const uint8_t *)(base + p->offset);
    case PT_U32:
        return (float)*(const uint32_t *)(base + p->offset);
    case PT_FLOAT:
    case PT_TIME:
        return *(const float *)(base + p->offset);
    default:
        return 0.0f;
    }
}

static void param_set_float(riego_config_t *c, const config_param_t *p, float v)
{
    uint8_t *base = (uint8_t *)c;
    switch (p->type) {
    case PT_BOOL:
        *(uint8_t *)(base + p->offset) = (v != 0.0f) ? 1 : 0;
        break;
    case PT_U8:
        *(uint8_t *)(base + p->offset) = (uint8_t)v;
        break;
    case PT_U32:
        *(uint32_t *)(base + p->offset) = (uint32_t)v;
        break;
    default:
        *(float *)(base + p->offset) = v;
        break;
    }
}

void config_format_time(float minutes, char *out, size_t len)
{
    int m = (int)lroundf(minutes);
    snprintf(out, len, "%02d:%02d", (m / 60) % 24, m % 60);
}

bool config_parse_time(const char *s, float *minutes)
{
    int h = 0, m = 0;
    if (s == NULL) {
        return false;
    }
    if (strchr(s, ':') != NULL) {
        if (sscanf(s, "%d:%d", &h, &m) != 2) {
            return false;
        }
    } else {
        char *end = NULL;
        long v = strtol(s, &end, 10);
        if (end == s || *end != '\0') {
            return false;
        }
        *minutes = (float)v;
        return v >= 0 && v < 1440;
    }
    if (h < 0 || h > 23 || m < 0 || m > 59) {
        return false;
    }
    *minutes = (float)(h * 60 + m);
    return true;
}

void config_param_format(const riego_config_t *c, const config_param_t *p, char *out, size_t len)
{
    switch (p->type) {
    case PT_STRING:
        snprintf(out, len, "%s", (const char *)((const uint8_t *)c + p->offset));
        break;
    case PT_TIME:
        config_format_time(config_param_get_float(c, p), out, len);
        break;
    case PT_BOOL:
        snprintf(out, len, "%s", config_param_get_float(c, p) != 0.0f ? "true" : "false");
        break;
    case PT_U8:
    case PT_U32:
        snprintf(out, len, "%lu", (unsigned long)config_param_get_float(c, p));
        break;
    default:
        snprintf(out, len, "%.*f", p->decimals, config_param_get_float(c, p));
        break;
    }
}

static bool parse_bool(const char *s, float *v)
{
    if (!strcasecmp(s, "1") || !strcasecmp(s, "true") || !strcasecmp(s, "on") || !strcasecmp(s, "si")) {
        *v = 1.0f;
        return true;
    }
    if (!strcasecmp(s, "0") || !strcasecmp(s, "false") || !strcasecmp(s, "off") || !strcasecmp(s, "no")) {
        *v = 0.0f;
        return true;
    }
    return false;
}

static bool printable(const char *s)
{
    for (; *s; s++) {
        unsigned char ch = (unsigned char)*s;
        if (ch < 0x20 || ch == '"' || ch == '\\') {
            return false;
        }
    }
    return true;
}

int config_param_set_str(riego_config_t *c, const config_param_t *p, const char *value, char *msg, size_t len)
{
    if (value == NULL) {
        snprintf(msg, len, "Valor ausente para %s", p->key);
        return -1;
    }
    if (p->type == PT_STRING) {
        size_t cap = (size_t)p->max;
        if (strlen(value) == 0 || strlen(value) >= cap || !printable(value)) {
            snprintf(msg, len, "%s: texto vacio, demasiado largo (max %u) o con caracteres no validos",
                     p->key, (unsigned)(cap - 1));
            return -1;
        }
        strlcpy((char *)((uint8_t *)c + p->offset), value, cap);
        return 0;
    }
    float v = 0.0f;
    bool ok;
    if (p->type == PT_BOOL) {
        ok = parse_bool(value, &v);
    } else if (p->type == PT_TIME) {
        ok = config_parse_time(value, &v);
    } else {
        char *end = NULL;
        v = strtof(value, &end);
        ok = (end != value && *end == '\0' && isfinite(v));
    }
    if (!ok) {
        snprintf(msg, len, "Valor invalido para %s: '%s'", p->key, value);
        return -1;
    }
    if (v < p->min || v > p->max) {
        snprintf(msg, len, "%s fuera de limites [%g, %g] %s", p->key, p->min, p->max, p->unit);
        return -1;
    }
    param_set_float(c, p, v);
    return 0;
}

/* EC-5: la Actividad 2.2 preparó 600 mL de tierra seca con 0/105/257/490 mL de agua y
 * definió %VWC = agua / (tierra + agua). Al mojar la tierra el agua ocupa los poros y el
 * volumen casi no cambia, así que la humedad volumétrica estándar (la de FAO-56, la de
 * capacidad de campo y la que relaciona litros con puntos) es theta = agua / tierra:
 *     theta = s / (1 - s),  con s = fracción que da la recta.
 * Con ec5_scale = 0 la recta se usa tal cual (para una recalibración ya en theta). */
float ec5_mv_to_vwc(const riego_config_t *c, float mv)
{
    float s = c->ec5_slope * mv + c->ec5_offset;
    if (c->ec5_scale < 0.5f || s <= 0.0f) {
        return s;
    }
    float f = s / 100.0f;
    if (f >= 0.95f) {
        return 1900.0f;                 /* Imposible: lo marca la validación */
    }
    return 100.0f * f / (1.0f - f);
}

float ec5_vwc_to_mv(const riego_config_t *c, float vwc)
{
    float s = vwc;
    if (c->ec5_scale >= 0.5f && vwc > 0.0f) {
        float t = vwc / 100.0f;
        s = 100.0f * t / (1.0f + t);
    }
    return (s - c->ec5_offset) / c->ec5_slope;
}
