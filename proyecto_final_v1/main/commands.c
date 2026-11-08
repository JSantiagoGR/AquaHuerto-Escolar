#include <math.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>

#include "freertos/FreeRTOS.h"
#include "cJSON.h"
#include "sdkconfig.h"

#include "app_types.h"
#include "irrigation_controller.h"
#include "timekeeping.h"
#include "commands.h"

#define ID_RING        24
#define MAX_AGE_S      60       /* Comandos con "ts" más viejos se rechazan */

static char s_ids[ID_RING][40];
static int s_id_head;
static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;

typedef struct {
    const char *name;
    cmd_type_t type;
    bool actuating;             /* Requiere token si está configurado */
} cmd_map_t;

static const cmd_map_t MAP[] = {
    {"GET_STATUS",            C_GET_STATUS,     false},
    {"GET_CONFIG",            C_GET_CONFIG,     false},
    {"GET_HISTORY",           C_GET_HISTORY,    false},
    {"START_MANUAL",          C_START_MANUAL,   true},
    {"STOP",                  C_STOP,           false},     /* STOP nunca se bloquea */
    {"ENABLE_AUTO",           C_ENABLE_AUTO,    true},
    {"DISABLE_AUTO",          C_DISABLE_AUTO,   false},
    {"SET_HUMIDITY_MIN",      C_SET_PARAM,      true},
    {"SET_HUMIDITY_TARGET",   C_SET_PARAM,      true},
    {"SET_HUMIDITY_MAX",      C_SET_PARAM,      true},
    {"SET_HUMIDITY_RANGE",    C_SET_HUM_RANGE,  true},
    {"SET_LITERS_PER_CYCLE",  C_SET_PARAM,      true},
    {"SET_INFILT_WAIT",       C_SET_PARAM,      true},
    {"SET_MAX_LITERS",        C_SET_MAX_LITERS, true},
    {"SET_FLOW_CALIBRATION",  C_SET_FLOW_CAL,   true},
    {"SET_TANK_MIN_LEVEL",    C_SET_PARAM,      true},
    {"SET_TANK_CALIBRATION",  C_SET_TANK_CAL,   true},
    {"SET_SCHEDULE",          C_SET_SCHEDULE,   true},
    {"SET_CONFIG",            C_SET_PARAM,      true},
    {"CLEAR_ALARM",           C_CLEAR_ALARM,    true},
};

cmd_type_t commands_type_from_name(const char *name)
{
    for (size_t i = 0; i < sizeof(MAP) / sizeof(MAP[0]); i++) {
        if (strcasecmp(name, MAP[i].name) == 0) {
            return MAP[i].type;
        }
    }
    return C_NONE;
}

static const cmd_map_t *find(const char *name)
{
    for (size_t i = 0; i < sizeof(MAP) / sizeof(MAP[0]); i++) {
        if (strcasecmp(name, MAP[i].name) == 0) {
            return &MAP[i];
        }
    }
    return NULL;
}

bool commands_seen_id(const char *id)
{
    bool seen = false;
    taskENTER_CRITICAL(&s_mux);
    for (int i = 0; i < ID_RING; i++) {
        if (s_ids[i][0] != '\0' && strcmp(s_ids[i], id) == 0) {
            seen = true;
            break;
        }
    }
    if (!seen) {
        strlcpy(s_ids[s_id_head], id, sizeof(s_ids[0]));
        s_id_head = (s_id_head + 1) % ID_RING;
    }
    taskEXIT_CRITICAL(&s_mux);
    return seen;
}

void commands_reset_ids(void)
{
    taskENTER_CRITICAL(&s_mux);
    memset(s_ids, 0, sizeof(s_ids));
    s_id_head = 0;
    taskEXIT_CRITICAL(&s_mux);
}

static bool get_num(const cJSON *o, const char *k, float *out)
{
    const cJSON *it = cJSON_GetObjectItemCaseSensitive(o, k);
    if (!cJSON_IsNumber(it) || !isfinite(it->valuedouble)) {
        return false;
    }
    *out = (float)it->valuedouble;
    return true;
}

static const char *get_str(const cJSON *o, const char *k)
{
    const cJSON *it = cJSON_GetObjectItemCaseSensitive(o, k);
    return cJSON_IsString(it) ? it->valuestring : NULL;
}

/* Convierte el número a texto para config_set (que valida límites) */
static void num_to_sval(command_t *c, float v)
{
    snprintf(c->sval, sizeof(c->sval), "%.6g", v);
}

void commands_handle_mqtt(const char *data, int len, bool retained)
{
    command_t c = { .src = SRC_MQTT, .i1 = -1 };
    strlcpy(c.name, "?", sizeof(c.name));

    cJSON *root = cJSON_ParseWithLength(data, (size_t)len);
    if (root == NULL || !cJSON_IsObject(root)) {
        controller_ack(&c, "INVALID", "JSON invalido");
        cJSON_Delete(root);
        return;
    }
    const char *id = get_str(root, "id");
    const char *cmd = get_str(root, "cmd");
    if (cmd) {
        strlcpy(c.name, cmd, sizeof(c.name));
    }
    if (id == NULL || strlen(id) == 0 || strlen(id) >= sizeof(c.id)) {
        controller_ack(&c, "INVALID", "Falta 'id' (texto de 1 a 39 caracteres)");
        cJSON_Delete(root);
        return;
    }
    strlcpy(c.id, id, sizeof(c.id));

    const cmd_map_t *m = cmd ? find(cmd) : NULL;
    if (m == NULL) {
        controller_ack(&c, "INVALID", "Comando desconocido");
        cJSON_Delete(root);
        return;
    }
    c.type = m->type;

    /* Un STOP se ejecuta aunque venga repetido o retenido: es la orden segura */
    if (c.type == C_STOP) {
        controller_emergency_stop(&c);
        cJSON_Delete(root);
        return;
    }
    if (retained) {
        controller_ack(&c, "RETAINED", "Comando retenido ignorado: publique comandos con retain=false");
        cJSON_Delete(root);
        return;
    }
    /* "ts" en segundos Unix: se usa double (un float pierde precisión) */
    const cJSON *jts = cJSON_GetObjectItemCaseSensitive(root, "ts");
    if (cJSON_IsNumber(jts) && time_is_valid()) {
        double age = (double)time_epoch() - jts->valuedouble;
        if (fabs(age) > MAX_AGE_S) {
            controller_ack(&c, "STALE", "Comando antiguo o con hora incorrecta");
            cJSON_Delete(root);
            return;
        }
    }
    if (m->actuating && strlen(CONFIG_RIEGO_CMD_TOKEN) > 0) {
        const char *tok = get_str(root, "token");
        if (tok == NULL || strcmp(tok, CONFIG_RIEGO_CMD_TOKEN) != 0) {
            controller_ack(&c, "UNAUTHORIZED", "Token invalido o ausente");
            cJSON_Delete(root);
            return;
        }
    }
    if (commands_seen_id(c.id)) {
        controller_ack(&c, "DUPLICATE", "Comando con id repetido: no se ejecuta otra vez");
        cJSON_Delete(root);
        return;
    }

    bool ok = true;
    float v;
    const char *s;
    switch (c.type) {
    case C_START_MANUAL: {
        ok = get_num(root, "liters", &c.f1);
        const cJSON *f = cJSON_GetObjectItemCaseSensitive(root, "force");
        c.b1 = cJSON_IsTrue(f);
        break;
    }
    case C_SET_PARAM:
        if (strcasecmp(cmd, "SET_CONFIG") == 0) {
            s = get_str(root, "key");
            const cJSON *val = cJSON_GetObjectItemCaseSensitive(root, "value");
            ok = (s != NULL);
            if (ok) {
                strlcpy(c.key, s, sizeof(c.key));
                if (cJSON_IsNumber(val)) {
                    num_to_sval(&c, (float)val->valuedouble);
                } else if (cJSON_IsBool(val)) {
                    strlcpy(c.sval, cJSON_IsTrue(val) ? "true" : "false", sizeof(c.sval));
                } else if (cJSON_IsString(val)) {
                    strlcpy(c.sval, val->valuestring, sizeof(c.sval));
                } else {
                    ok = false;
                }
            }
        } else {
            ok = get_num(root, "value", &v);
            if (ok) {
                num_to_sval(&c, v);
                if (!strcasecmp(cmd, "SET_HUMIDITY_MIN")) strlcpy(c.key, "hum_min", sizeof(c.key));
                else if (!strcasecmp(cmd, "SET_HUMIDITY_TARGET")) strlcpy(c.key, "hum_target", sizeof(c.key));
                else if (!strcasecmp(cmd, "SET_HUMIDITY_MAX")) strlcpy(c.key, "hum_max", sizeof(c.key));
                else if (!strcasecmp(cmd, "SET_LITERS_PER_CYCLE")) strlcpy(c.key, "liters_per_cycle", sizeof(c.key));
                else if (!strcasecmp(cmd, "SET_INFILT_WAIT")) strlcpy(c.key, "infilt_min", sizeof(c.key));
                else if (!strcasecmp(cmd, "SET_TANK_MIN_LEVEL")) strlcpy(c.key, "tank_min_pct", sizeof(c.key));
            }
        }
        break;
    case C_SET_HUM_RANGE:
        ok = get_num(root, "min", &c.f1) && get_num(root, "target", &c.f2) && get_num(root, "max", &c.f3);
        break;
    case C_SET_MAX_LITERS:
        c.f1 = NAN;
        c.f2 = NAN;
        get_num(root, "event", &c.f1);
        get_num(root, "daily", &c.f2);
        ok = !(isnan(c.f1) && isnan(c.f2));
        break;
    case C_SET_FLOW_CAL:
        c.f1 = NAN;
        if (!get_num(root, "pulses_per_liter", &c.f1)) {
            ok = get_num(root, "pulses", &c.f2) && get_num(root, "measured_ml", &c.f3) &&
                 c.f2 > 0 && c.f3 > 0;
        }
        break;
    case C_SET_TANK_CAL:
        ok = get_num(root, "empty_cm", &c.f1) && get_num(root, "full_cm", &c.f2);
        break;
    case C_SET_SCHEDULE: {
        float w = 0;
        const char *st = get_str(root, "start"), *en = get_str(root, "end");
        const cJSON *e = cJSON_GetObjectItemCaseSensitive(root, "enabled");
        ok = get_num(root, "window", &w) && (w == 1 || w == 2) && cJSON_IsBool(e) && st && en;
        if (ok) {
            c.i1 = (int)w;
            c.b1 = cJSON_IsTrue(e);
            strlcpy(c.key, st, sizeof(c.key));
            strlcpy(c.sval, en, sizeof(c.sval));
        }
        break;
    }
    case C_CLEAR_ALARM:
        s = get_str(root, "alarm");
        if (s == NULL || strcasecmp(s, "ALL") == 0) {
            c.i1 = -1;
        } else {
            c.i1 = alarm_from_name(s);
            ok = (c.i1 >= 0);
        }
        break;
    default:
        break;
    }
    cJSON_Delete(root);

    if (!ok) {
        controller_ack(&c, "INVALID", "Faltan campos o tienen tipo/valor incorrecto");
        return;
    }
    if (!controller_post(&c)) {
        controller_ack(&c, "REJECTED", "Cola de comandos llena");
    }
}
