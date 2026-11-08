#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include <strings.h>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_rom_crc.h"
#include "nvs.h"

#include "configuration.h"

static const char *TAG = "config";
#define NVS_NS   "riego"
#define NVS_KEY  "cfg"

static riego_config_t s_cfg;
static SemaphoreHandle_t s_mtx;
static uint32_t s_generation;

#define OFF(f) offsetof(riego_config_t, f)

/* Tabla de parámetros: nombre, tipo, ubicación, límites DUROS, remoto, unidad */
static const config_param_t PARAMS[] = {
    {"hum_min",           PT_FLOAT, OFF(hum_min),           5,    60,   1, true,  "%VWC", "Humedad mínima"},
    {"hum_target",        PT_FLOAT, OFF(hum_target),        5,    65,   1, true,  "%VWC", "Humedad recomendada / objetivo"},
    {"hum_max",           PT_FLOAT, OFF(hum_max),           5,    70,   1, true,  "%VWC", "Humedad máxima"},
    {"hum_critical",      PT_FLOAT, OFF(hum_critical),      0,    55,   1, true,  "%VWC", "Humedad crítica (emergencia)"},
    {"liters_per_cycle",  PT_FLOAT, OFF(liters_per_cycle),  0.1f, 5,    2, true,  "L",    "Litros por ciclo automático"},
    {"max_liters_event",  PT_FLOAT, OFF(max_liters_event),  0.1f, 10,   2, true,  "L",    "Máximo de litros por evento"},
    {"max_liters_daily",  PT_FLOAT, OFF(max_liters_daily),  0.5f, 50,   2, true,  "L",    "Máximo de litros por día"},
    {"emergency_liters",  PT_FLOAT, OFF(emergency_liters),  0.1f, 2,    2, true,  "L",    "Litros del riego de emergencia"},
    {"pump_max_s",        PT_FLOAT, OFF(pump_max_s),        10,   300,  0, true,  "s",    "Tiempo máximo de bomba por ciclo"},
    {"no_flow_s",         PT_FLOAT, OFF(no_flow_s),         3,    30,   0, true,  "s",    "Tiempo máximo sin pulsos con bomba encendida"},
    {"flow_max_lpm",      PT_FLOAT, OFF(flow_max_lpm),      1,    15,   1, true,  "L/min","Caudal máximo creíble"},
    {"valve_lead_ms",     PT_FLOAT, OFF(valve_lead_ms),     100,  3000, 0, true,  "ms",   "Válvula abierta antes de la bomba"},
    {"valve_lag_ms",      PT_FLOAT, OFF(valve_lag_ms),      100,  3000, 0, true,  "ms",   "Bomba apagada antes de cerrar válvula"},
    {"idle_flow_pulses",  PT_FLOAT, OFF(idle_flow_pulses),  5,    500,  0, true,  "pulsos","Pulsos con todo apagado para alarma (por minuto)"},
    {"infilt_min",        PT_FLOAT, OFF(infilt_min),        1,    120,  0, true,  "min",  "Espera de infiltración"},
    {"min_event_gap_min", PT_FLOAT, OFF(min_event_gap_min), 0,    1440, 0, true,  "min",  "Intervalo mínimo entre eventos"},
    {"emergency_gap_min", PT_FLOAT, OFF(emergency_gap_min), 30,   1440, 0, true,  "min",  "Intervalo mínimo entre emergencias"},
    {"max_cycles",        PT_FLOAT, OFF(max_cycles),        1,    6,    0, true,  "",     "Máximo de ciclos por evento"},
    {"dry_confirm",       PT_FLOAT, OFF(dry_confirm),       1,    5,    0, true,  "",     "Lecturas bajo el mínimo para confirmar"},
    {"response_cycles",   PT_FLOAT, OFF(response_cycles),   1,    6,    0, true,  "",     "Ciclos tras los que se exige respuesta del suelo"},
    {"min_response_pp",   PT_FLOAT, OFF(min_response_pp),   0.2f, 10,   1, true,  "%VWC", "Aumento mínimo de humedad esperado"},
    {"pulses_per_liter",  PT_FLOAT, OFF(pulses_per_liter),  200,  1000, 1, true,  "p/L",  "Pulsos por litro del YF-S201"},
    {"overrun_ml",        PT_FLOAT, OFF(overrun_ml),        0,    200,  0, true,  "mL",   "Compensación de sobrepaso"},
    {"soil_interval_s",   PT_FLOAT, OFF(soil_interval_s),   30,   3600, 0, true,  "s",    "Intervalo base de lectura del EC-5"},
    {"ec5_slope",         PT_FLOAT, OFF(ec5_slope),         0.001f, 1,  8, true,  "%/mV", "Pendiente de calibración EC-5"},
    {"ec5_offset",        PT_FLOAT, OFF(ec5_offset),        -100, 100,  6, true,  "%",    "Ordenada de calibración EC-5"},
    {"ec5_mv_min",        PT_FLOAT, OFF(ec5_mv_min),        50,   600,  0, true,  "mV",   "mV mínimo válido del EC-5"},
    {"ec5_mv_max",        PT_FLOAT, OFF(ec5_mv_max),        900,  3000, 0, true,  "mV",   "mV máximo válido del EC-5"},
    {"ec5_cal_mv_lo",     PT_FLOAT, OFF(ec5_cal_mv_lo),     0,    3000, 0, true,  "mV",   "Límite inferior del intervalo calibrado"},
    {"ec5_cal_mv_hi",     PT_FLOAT, OFF(ec5_cal_mv_hi),     0,    3000, 0, true,  "mV",   "Límite superior del intervalo calibrado"},
    {"tank_empty_cm",     PT_FLOAT, OFF(tank_empty_cm),     0,    300,  1, true,  "cm",   "Distancia al agua con tinaco vacío (0=sin calibrar)"},
    {"tank_full_cm",      PT_FLOAT, OFF(tank_full_cm),      0,    300,  1, true,  "cm",   "Distancia al agua con tinaco lleno (0=sin calibrar)"},
    {"tank_min_pct",      PT_FLOAT, OFF(tank_min_pct),      5,    90,   0, true,  "%",    "Nivel mínimo de seguridad del tinaco"},
    {"tank_interval_s",   PT_FLOAT, OFF(tank_interval_s),   5,    600,  0, true,  "s",    "Intervalo de lectura del tinaco"},
    {"win1_en",           PT_BOOL,  OFF(win1_en),           0,    1,    0, true,  "",     "Horario 1 habilitado"},
    {"win1_start",        PT_TIME,  OFF(win1_start),        0,    1439, 0, true,  "HH:MM","Inicio horario 1"},
    {"win1_end",          PT_TIME,  OFF(win1_end),          0,    1439, 0, true,  "HH:MM","Fin horario 1"},
    {"win2_en",           PT_BOOL,  OFF(win2_en),           0,    1,    0, true,  "",     "Horario 2 habilitado"},
    {"win2_start",        PT_TIME,  OFF(win2_start),        0,    1439, 0, true,  "HH:MM","Inicio horario 2"},
    {"win2_end",          PT_TIME,  OFF(win2_end),          0,    1439, 0, true,  "HH:MM","Fin horario 2"},
    {"midday_start",      PT_TIME,  OFF(midday_start),      0,    1439, 0, true,  "HH:MM","Inicio de bloqueo de mediodía"},
    {"midday_end",        PT_TIME,  OFF(midday_end),        0,    1439, 0, true,  "HH:MM","Fin de bloqueo de mediodía"},
    {"emergency_en",      PT_BOOL,  OFF(emergency_en),      0,    1,    0, true,  "",     "Riegos de emergencia habilitados"},
    {"temp_postpone_c",   PT_FLOAT, OFF(temp_postpone_c),   20,   50,   1, true,  "C",    "Temperatura para posponer riego rutinario"},
    {"hot_temp_c",        PT_FLOAT, OFF(hot_temp_c),        15,   50,   1, true,  "C",    "Temperatura para acortar el intervalo de lectura"},
    {"dry_rh_pct",        PT_FLOAT, OFF(dry_rh_pct),        5,    80,   0, true,  "%HR",  "HR ambiental para acortar el intervalo"},
    {"telemetry_s",       PT_FLOAT, OFF(telemetry_s),       2,    600,  0, true,  "s",    "Intervalo de telemetría MQTT"},
    {"tz",                PT_STRING,OFF(tz),                0,    0,    0, true,  "",     "Zona horaria POSIX"},
    /* Solo por consola serial (presencia física) */
    {"mode",              PT_FLOAT, OFF(mode),              0,    1,    0, false, "",     "Modo 0=A pruebas, 1=B instalación"},
    {"power_enabled",     PT_BOOL,  OFF(power_enabled),     0,    1,    0, false, "",     "Salidas de potencia habilitadas"},
    {"auto_saved",        PT_BOOL,  OFF(auto_saved),        0,    1,    0, false, "",     "Automático guardado (modo B)"},
};

#define NPARAMS (sizeof(PARAMS) / sizeof(PARAMS[0]))

void config_defaults(riego_config_t *c)
{
    memset(c, 0, sizeof(*c));
    c->magic = CONFIG_MAGIC;
    c->version = CONFIG_VERSION;

    /* Ejemplos de demostración, NO recomendaciones agronómicas */
    c->hum_min = 25.0f;
    c->hum_target = 35.0f;
    c->hum_max = 45.0f;
    c->hum_critical = 18.0f;

    c->liters_per_cycle = 1.0f;
    c->max_liters_event = 3.0f;
    c->max_liters_daily = 10.0f;
    c->emergency_liters = 0.5f;

    c->pump_max_s = 90.0f;          /* 1 L tardó ~20 s (incluye ~4 s de cebado) */
    c->no_flow_s = 10.0f;           /* El agua tardó ~4 s en llegar             */
    c->flow_max_lpm = 8.0f;
    c->valve_lead_ms = 300.0f;      /* Secuencia probada físicamente            */
    c->valve_lag_ms = 300.0f;
    c->idle_flow_pulses = 20.0f;

    c->infilt_min = 15.0f;
    c->min_event_gap_min = 60.0f;
    c->emergency_gap_min = 240.0f;
    c->max_cycles = 3.0f;
    c->dry_confirm = 2.0f;
    c->response_cycles = 2.0f;
    c->min_response_pp = 1.0f;

    c->pulses_per_liter = 450.0f;   /* Pendiente de calibración física          */
    c->overrun_ml = 0.0f;

    c->soil_interval_s = 300.0f;
    c->ec5_slope = 0.08146067f;     /* Actividad 2.2 */
    c->ec5_offset = -23.932584f;
    c->ec5_mv_min = 200.0f;
    c->ec5_mv_max = 1500.0f;
    c->ec5_cal_mv_lo = 360.0f;
    c->ec5_cal_mv_hi = 870.0f;

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

    c->telemetry_s = 10.0f;

    c->auto_saved = 0;
    c->mode = MODE_A_TEST;
    c->power_enabled = 0;           /* Versión segura: potencia deshabilitada */
    strlcpy(c->tz, "CST6", sizeof(c->tz));   /* Chihuahua: UTC-6 sin horario de verano */
}

static uint32_t calc_crc(const riego_config_t *c)
{
    return esp_rom_crc32_le(0, (const uint8_t *)c, offsetof(riego_config_t, crc));
}

bool config_tank_calibrated(const riego_config_t *c)
{
    return c->tank_empty_cm > 0.0f && c->tank_full_cm > 0.0f &&
           c->tank_empty_cm > c->tank_full_cm;
}

bool config_validate(const riego_config_t *c, char *msg, size_t len)
{
    /* Límites individuales */
    for (size_t i = 0; i < NPARAMS; i++) {
        const config_param_t *p = &PARAMS[i];
        if (p->type == PT_STRING) {
            continue;
        }
        float v = config_param_get_float(c, p);
        if (isnan(v) || v < p->min || v > p->max) {
            snprintf(msg, len, "%s fuera de limites [%g, %g]", p->key, p->min, p->max);
            return false;
        }
    }
    /* Relaciones entre parámetros */
    if (!(c->hum_min + 1.0f <= c->hum_target && c->hum_target + 1.0f <= c->hum_max)) {
        snprintf(msg, len, "Debe cumplirse MINIMA < OBJETIVO < MAXIMA (al menos 1 punto): %.1f / %.1f / %.1f",
                 c->hum_min, c->hum_target, c->hum_max);
        return false;
    }
    if (c->hum_critical >= c->hum_min) {
        snprintf(msg, len, "hum_critical (%.1f) debe ser menor que hum_min (%.1f)", c->hum_critical, c->hum_min);
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
    if (c->tz[0] == '\0' || memchr(c->tz, '\0', sizeof(c->tz)) == NULL) {
        snprintf(msg, len, "Zona horaria invalida");
        return false;
    }
    if (msg && len) {
        msg[0] = '\0';
    }
    return true;
}

static esp_err_t save_locked(void)
{
    s_cfg.crc = calc_crc(&s_cfg);
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NS, NVS_READWRITE, &h);
    if (err != ESP_OK) {
        return err;
    }
    err = nvs_set_blob(h, NVS_KEY, &s_cfg, sizeof(s_cfg));
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }
    nvs_close(h);
    return err;
}

void config_init(bool *was_reset)
{
    s_mtx = xSemaphoreCreateMutex();
    *was_reset = false;

    riego_config_t tmp;
    size_t sz = sizeof(tmp);
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NS, NVS_READONLY, &h);
    if (err == ESP_OK) {
        err = nvs_get_blob(h, NVS_KEY, &tmp, &sz);
        nvs_close(h);
    }

    char msg[96];
    if (err == ESP_OK && sz == sizeof(tmp) && tmp.magic == CONFIG_MAGIC &&
        tmp.version == CONFIG_VERSION && tmp.crc == calc_crc(&tmp) &&
        config_validate(&tmp, msg, sizeof(msg))) {
        s_cfg = tmp;
        ESP_LOGI(TAG, "Configuracion cargada de NVS");
    } else {
        bool first_boot = (err == ESP_ERR_NVS_NOT_FOUND);
        config_defaults(&s_cfg);
        save_locked();
        if (!first_boot) {
            *was_reset = true;
            ESP_LOGW(TAG, "Configuracion NVS invalida (%s): valores por defecto", esp_err_to_name(err));
        } else {
            ESP_LOGI(TAG, "Primer arranque: configuracion por defecto guardada");
        }
    }
    s_generation = 1;
}

void config_get(riego_config_t *out)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    *out = s_cfg;
    xSemaphoreGive(s_mtx);
}

uint32_t config_generation(void)
{
    return s_generation;
}

esp_err_t config_apply(const riego_config_t *cand, char *msg, size_t len)
{
    if (!config_validate(cand, msg, len)) {
        return ESP_ERR_INVALID_ARG;
    }
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    s_cfg = *cand;
    s_cfg.magic = CONFIG_MAGIC;
    s_cfg.version = CONFIG_VERSION;
    esp_err_t err = save_locked();
    s_generation++;
    xSemaphoreGive(s_mtx);
    if (err != ESP_OK) {
        snprintf(msg, len, "Error al guardar en NVS: %s", esp_err_to_name(err));
    }
    return err;
}

esp_err_t config_factory_reset(void)
{
    riego_config_t d;
    config_defaults(&d);
    char msg[64];
    return config_apply(&d, msg, sizeof(msg));
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
        return (float)*(const uint8_t *)(base + p->offset);
    case PT_FLOAT:
    case PT_TIME:
        if (p->offset == OFF(mode)) {
            return (float)c->mode;
        }
        return *(const float *)(base + p->offset);
    default:
        return 0.0f;
    }
}

static void param_set_float(riego_config_t *c, const config_param_t *p, float v)
{
    uint8_t *base = (uint8_t *)c;
    if (p->type == PT_BOOL) {
        *(uint8_t *)(base + p->offset) = (v != 0.0f) ? 1 : 0;
    } else if (p->offset == OFF(mode)) {
        c->mode = (uint8_t)v;
    } else {
        *(float *)(base + p->offset) = v;
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

esp_err_t config_set(const char *key, const char *value, bool remote, char *msg, size_t len)
{
    const config_param_t *p = config_param_find(key);
    if (p == NULL) {
        snprintf(msg, len, "Parametro desconocido: %s", key);
        return ESP_ERR_NOT_FOUND;
    }
    if (remote && !p->remote) {
        snprintf(msg, len, "%s solo se puede cambiar por consola serial", p->key);
        return ESP_ERR_NOT_ALLOWED;
    }
    riego_config_t cand;
    config_get(&cand);

    if (p->type == PT_STRING) {
        if (value == NULL || strlen(value) == 0 || strlen(value) >= sizeof(cand.tz)) {
            snprintf(msg, len, "Valor de texto invalido");
            return ESP_ERR_INVALID_ARG;
        }
        strlcpy((char *)((uint8_t *)&cand + p->offset), value, sizeof(cand.tz));
    } else {
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
            return ESP_ERR_INVALID_ARG;
        }
        if (v < p->min || v > p->max) {
            snprintf(msg, len, "%s fuera de limites [%g, %g] %s", p->key, p->min, p->max, p->unit);
            return ESP_ERR_INVALID_ARG;
        }
        param_set_float(&cand, p, v);
    }
    esp_err_t err = config_apply(&cand, msg, len);
    if (err == ESP_OK) {
        char buf[48];
        config_param_format(&cand, p, buf, sizeof(buf));
        snprintf(msg, len, "%s = %s %s", p->key, buf, p->unit);
    }
    return err;
}

esp_err_t config_set_humidity_range(float mn, float tg, float mx, char *msg, size_t len)
{
    riego_config_t cand;
    config_get(&cand);
    cand.hum_min = mn;
    cand.hum_target = tg;
    cand.hum_max = mx;
    esp_err_t err = config_apply(&cand, msg, len);
    if (err == ESP_OK) {
        snprintf(msg, len, "Humedad: minima %.1f / objetivo %.1f / maxima %.1f %%VWC", mn, tg, mx);
    }
    return err;
}
