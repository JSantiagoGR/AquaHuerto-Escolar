#include <string.h>
#include "app_types.h"

static const char *const STATE_NAMES[ST__COUNT] = {
    "INIT", "IDLE", "MONITORING", "MANUAL_WATERING", "AUTO_WATERING",
    "INFILTRATION_WAIT", "FAULT",
};

static const char *const PHASE_NAMES[] = { "NONE", "OPENING", "PUMPING", "CLOSING" };

static const char *const REASON_NAMES[WR__COUNT] = { "MANUAL", "SCHEDULED", "EMERGENCY", "MANUAL_TARGET", "IA" };
static const char *const MODE_NAMES[CM__COUNT] = { "MANUAL", "AUTOMATICO", "IA" };
static const char *const KIND_NAMES[] = { "NONE", "AUTO", "EMERGENCY", "MANUAL_TARGET", "IA" };

static const char *const RESULT_NAMES[RES__COUNT] = {
    "NONE", "TARGET", "STOP_CMD", "NO_FLOW", "FLOW_HIGH", "PUMP_TIMEOUT",
    "DAILY_LIMIT", "EVENT_LIMIT", "TANK_LOW", "SAFETY", "REBOOT",
};

typedef struct { const char *code; const char *text; } dec_info_t;

static const dec_info_t DECISIONS[DEC__COUNT] = {
    [DEC_NONE]              = {"NONE", "Sin decisión todavía"},
    [DEC_AUTO_DISABLED]     = {"AUTO_DISABLED", "Modo MANUAL: no se inician riegos automáticos"},
    [DEC_OUTPUTS_DISABLED]  = {"OUTPUTS_DISABLED", "Salidas de potencia deshabilitadas: no se puede regar"},
    [DEC_FAULT]             = {"FAULT", "Sistema en falla: requiere revisar y CLEAR_ALARM"},
    [DEC_SOIL_INVALID]      = {"SOIL_INVALID", "Lectura del EC-5 inválida: no se riega"},
    [DEC_TOO_WET]           = {"TOO_WET", "Humedad del suelo en o sobre el máximo: no se agrega agua"},
    [DEC_HUMIDITY_OK]       = {"HUMIDITY_OK", "Humedad dentro del rango adecuado (con histéresis): no hace falta regar"},
    [DEC_CONFIRMING_DRY]    = {"CONFIRMING_DRY", "Humedad bajo el objetivo: confirmando con más lecturas"},
    [DEC_AUTO_LOCKED]       = {"AUTO_LOCKED", "Riego automático bloqueado: el suelo no respondió a riegos previos"},
    [DEC_TANK_UNCALIBRATED] = {"TANK_UNCALIBRATED", "Tinaco sin calibrar: el riego automático requiere nivel calibrado"},
    [DEC_TANK_INVALID]      = {"TANK_INVALID", "Sensor de nivel sin datos válidos: riego bloqueado"},
    [DEC_TANK_LOW]          = {"TANK_LOW", "Nivel del tinaco bajo el mínimo: riego bloqueado"},
    [DEC_DAILY_LIMIT]       = {"DAILY_LIMIT", "Se alcanzó el máximo diario de litros"},
    [DEC_MIN_GAP]           = {"MIN_GAP", "Pospuesto: no ha pasado el intervalo mínimo desde el último riego"},
    [DEC_EMERGENCY_GAP]     = {"EMERGENCY_GAP", "Emergencia pospuesta: intervalo mínimo entre emergencias"},
    [DEC_TIME_INVALID]      = {"TIME_INVALID", "Hora no sincronizada: no se ejecutan riegos por horario"},
    [DEC_OUTSIDE_WINDOW]    = {"OUTSIDE_WINDOW", "Pospuesto hasta el próximo horario de riego"},
    [DEC_MIDDAY]            = {"MIDDAY", "Pospuesto: horario de mediodía con alta evaporación"},
    [DEC_HOT]               = {"HOT", "Pospuesto: temperatura ambiental sobre el límite configurado"},
    [DEC_START_SCHEDULED]   = {"START_SCHEDULED", "Inicio de riego automático en horario preferido (humedad bajo el objetivo)"},
    [DEC_START_EMERGENCY]   = {"START_EMERGENCY", "Riego de emergencia por humedad crítica"},
    [DEC_INFILTRATING]      = {"INFILTRATING", "Esperando infiltración antes de volver a medir"},
    [DEC_CONTINUE_CYCLE]    = {"CONTINUE_CYCLE", "Humedad aún bajo el objetivo: nuevo ciclo controlado"},
    [DEC_TARGET_REACHED]    = {"TARGET_REACHED", "Humedad objetivo alcanzada: fin del evento de riego"},
    [DEC_MAX_CYCLES]        = {"MAX_CYCLES", "Fin del evento: máximo de ciclos alcanzado"},
    [DEC_MAX_EVENT_L]       = {"MAX_EVENT_LITERS", "Fin del evento: máximo de litros por evento"},
    [DEC_WINDOW_ENDED]      = {"WINDOW_ENDED", "Fin del evento: terminó el horario de riego"},
    [DEC_NO_RESPONSE]       = {"NO_RESPONSE", "El suelo no aumentó su humedad: automático bloqueado"},
    [DEC_EMERGENCY_DONE]    = {"EMERGENCY_DONE", "Riego de emergencia aplicado (un solo ciclo)"},
    [DEC_STOPPED]           = {"STOPPED", "Evento de riego detenido por STOP"},
    [DEC_WATERING_FAILED]   = {"WATERING_FAILED", "El riego terminó por una falla"},
    [DEC_MODE_MANUAL]       = {"MODE_MANUAL", "Modo MANUAL activo: solo se riega por solicitud del usuario"},
    [DEC_ABOVE_RESERVE]     = {"ABOVE_RESERVE", "Humedad sobre la reserva superior segura: no se agrega agua"},
    [DEC_BELOW_MIN_WAIT]    = {"BELOW_MIN_WAIT", "Humedad bajo el mínimo normal pero sobre la emergencia: se espera el horario preferido"},
    [DEC_RAIN_EXPECTED]     = {"RAIN_EXPECTED", "Pospuesto: el pronóstico vigente indica lluvia probable"},
    [DEC_IA_NOT_NEEDED]     = {"IA_NOT_NEEDED", "IA: la humedad predicha se mantiene sobre el mínimo hasta el próximo horario"},
    [DEC_START_IA]          = {"START_IA", "IA: riego con volumen calculado por el modelo predictivo"},
    [DEC_IA_GOAL_REACHED]   = {"IA_GOAL_REACHED", "IA: humedad meta alcanzada dentro de la tolerancia"},
    [DEC_IA_LIMITED]        = {"IA_LIMITED", "IA: la meta no es alcanzable sin exceder límites; se riega solo hasta el límite"},
    [DEC_START_TO_TARGET]   = {"START_TO_TARGET", "Riego manual hacia la humedad óptima (dosis limitadas con infiltración)"},
};

static const alarm_info_t ALARMS[ALM__COUNT] = {
    [ALM_NO_FLOW]           = {"NO_FLOW", SEV_CRITICAL, true, true, false,
                               "Bomba encendida sin pulsos del caudalímetro (sin agua, cebado, obstrucción o sensor)"},
    [ALM_FLOW_HIGH]         = {"FLOW_HIGH", SEV_CRITICAL, true, true, false,
                               "Caudal fuera de límites o pulsos erráticos"},
    [ALM_PUMP_TIMEOUT]      = {"PUMP_TIMEOUT", SEV_CRITICAL, true, true, false,
                               "La bomba superó el tiempo máximo de funcionamiento"},
    [ALM_SAFETY_TRIP]       = {"SAFETY_TRIP", SEV_CRITICAL, true, true, false,
                               "El supervisor de seguridad cortó las salidas"},
    [ALM_FLOW_WHEN_IDLE]    = {"FLOW_WHEN_IDLE", SEV_CRITICAL, true, true, false,
                               "Flujo con bomba apagada: posible contacto pegado, fuga o válvula abierta"},
    [ALM_SOIL_NO_RESPONSE]  = {"SOIL_NO_RESPONSE", SEV_WARNING, true, false, true,
                               "La humedad del suelo no aumentó tras varios riegos"},
    [ALM_REBOOT_DURING_WATERING] = {"REBOOT_DURING_WATERING", SEV_WARNING, true, false, false,
                               "El ESP32 se reinició durante un riego; no se reanuda"},
    [ALM_CONFIG_RESET]      = {"CONFIG_RESET", SEV_WARNING, true, false, false,
                               "Configuración en NVS inválida o corrupta: se cargaron valores por defecto"},
    [ALM_SOIL_SENSOR]       = {"SOIL_SENSOR", SEV_WARNING, false, false, true,
                               "Sensor EC-5 sin lectura válida"},
    [ALM_TANK_SENSOR]       = {"TANK_SENSOR", SEV_WARNING, false, false, false,
                               "Sensor ultrasónico sin lectura válida"},
    [ALM_TANK_LOW]          = {"TANK_LOW", SEV_WARNING, false, false, false,
                               "Tinaco en el mínimo: casi sin agua (el riego sigue; rellenar el tinaco)"},
    [ALM_ENV_SENSOR]        = {"ENV_SENSOR", SEV_INFO, false, false, false,
                               "Sensor ambiental DHT22 sin lectura válida"},
    [ALM_TIME_INVALID]      = {"TIME_INVALID", SEV_INFO, false, false, false,
                               "Hora no sincronizada por NTP"},
    [ALM_DAILY_LIMIT]       = {"DAILY_LIMIT", SEV_INFO, false, false, false,
                               "Se alcanzó el máximo diario de litros"},
    [ALM_COMMS]             = {"COMMS", SEV_INFO, false, false, false,
                               "Sin conexión Wi-Fi o MQTT"},
};

const char *state_name(irr_state_t s) { return (s < ST__COUNT) ? STATE_NAMES[s] : "?"; }
const char *phase_name(water_phase_t p) { return (p <= PH_CLOSING) ? PHASE_NAMES[p] : "?"; }
const char *reason_name(water_reason_t r) { return (r < WR__COUNT) ? REASON_NAMES[r] : "?"; }
const char *ctrl_mode_name(ctrl_mode_t m) { return (m < CM__COUNT) ? MODE_NAMES[m] : "?"; }
const char *event_kind_name(event_kind_t k) { return (k <= EVK_IA) ? KIND_NAMES[k] : "?"; }

int ctrl_mode_from_name(const char *name)
{
    if (name == NULL) {
        return -1;
    }
    if (!strcmp(name, "MANUAL")) return CM_MANUAL;
    if (!strcmp(name, "AUTOMATICO") || !strcmp(name, "AUTO") || !strcmp(name, "AUTOMÁTICO")) return CM_AUTO;
    if (!strcmp(name, "IA")) return CM_IA;
    return -1;
}
const char *result_name(water_result_t r) { return (r < RES__COUNT) ? RESULT_NAMES[r] : "?"; }
const char *decision_name(decision_t d) { return (d < DEC__COUNT) ? DECISIONS[d].code : "?"; }
const char *decision_text(decision_t d) { return (d < DEC__COUNT) ? DECISIONS[d].text : "?"; }
const alarm_info_t *alarm_info(alarm_t a) { return (a < ALM__COUNT) ? &ALARMS[a] : NULL; }

const char *severity_name(alarm_severity_t s)
{
    switch (s) {
    case SEV_CRITICAL: return "CRITICAL";
    case SEV_WARNING:  return "WARNING";
    default:           return "INFO";
    }
}

int alarm_from_name(const char *code)
{
    if (code == NULL) {
        return -1;
    }
    for (int i = 0; i < ALM__COUNT; i++) {
        if (strcmp(code, ALARMS[i].code) == 0) {
            return i;
        }
    }
    return -1;
}
