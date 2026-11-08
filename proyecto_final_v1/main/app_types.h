/*
 * Tipos comunes del sistema de riego: estados, motivos, resultados,
 * decisiones del riego automático y alarmas. Sin dependencias de ESP-IDF
 * para que la lógica de riego sea comprobable con el autodiagnóstico.
 */
#pragma once

#include <stdint.h>
#include <stdbool.h>

/* Estados principales de la máquina de riego */
typedef enum {
    ST_INIT = 0,
    ST_IDLE,                /* Sin riego automático: solo supervisión y riego manual */
    ST_MONITORING,          /* Riego automático habilitado, vigilando humedad        */
    ST_MANUAL_WATERING,     /* Riego manual por volumen en curso                     */
    ST_AUTO_WATERING,       /* Ciclo de riego automático en curso                    */
    ST_INFILTRATION_WAIT,   /* Espera de infiltración entre ciclos automáticos       */
    ST_FAULT,               /* Falla crítica: todo apagado hasta CLEAR_ALARM         */
    ST__COUNT
} irr_state_t;

/* Fases internas de un riego (manual o automático) */
typedef enum {
    PH_NONE = 0,
    PH_OPENING,             /* Válvula abierta, esperando antes de encender bomba */
    PH_PUMPING,             /* Bomba encendida, contando pulsos                   */
    PH_CLOSING,             /* Bomba apagada, esperando antes de cerrar válvula   */
} water_phase_t;

/* Motivo por el que empezó un riego */
typedef enum {
    WR_MANUAL = 0,
    WR_SCHEDULED,           /* Automático por humedad baja dentro del horario */
    WR_EMERGENCY,           /* Automático por humedad crítica fuera de horario */
    WR__COUNT
} water_reason_t;

/* Resultado con el que terminó un riego */
typedef enum {
    RES_NONE = 0,
    RES_TARGET,             /* Se alcanzó el volumen objetivo        */
    RES_STOP_CMD,           /* Orden STOP                            */
    RES_NO_FLOW,            /* Sin pulsos del caudalímetro           */
    RES_FLOW_HIGH,          /* Caudal fuera de límites / errático    */
    RES_PUMP_TIMEOUT,       /* Bomba demasiado tiempo encendida      */
    RES_DAILY_LIMIT,        /* Se alcanzó el máximo diario           */
    RES_EVENT_LIMIT,        /* Se alcanzó el máximo por evento       */
    RES_TANK_LOW,           /* Nivel del tinaco bajo durante riego   */
    RES_SAFETY,             /* Corte del supervisor de seguridad     */
    RES_REBOOT,             /* El ESP32 se reinició durante el riego */
    RES__COUNT
} water_result_t;

/* Decisiones / razones publicadas por el riego automático */
typedef enum {
    DEC_NONE = 0,
    DEC_AUTO_DISABLED,
    DEC_OUTPUTS_DISABLED,
    DEC_FAULT,
    DEC_SOIL_INVALID,
    DEC_TOO_WET,
    DEC_HUMIDITY_OK,
    DEC_CONFIRMING_DRY,
    DEC_AUTO_LOCKED,
    DEC_TANK_UNCALIBRATED,
    DEC_TANK_INVALID,
    DEC_TANK_LOW,
    DEC_DAILY_LIMIT,
    DEC_MIN_GAP,
    DEC_EMERGENCY_GAP,
    DEC_TIME_INVALID,
    DEC_OUTSIDE_WINDOW,
    DEC_MIDDAY,
    DEC_HOT,
    DEC_START_SCHEDULED,
    DEC_START_EMERGENCY,
    DEC_INFILTRATING,
    DEC_CONTINUE_CYCLE,
    DEC_TARGET_REACHED,
    DEC_MAX_CYCLES,
    DEC_MAX_EVENT_L,
    DEC_WINDOW_ENDED,
    DEC_NO_RESPONSE,
    DEC_EMERGENCY_DONE,
    DEC_STOPPED,
    DEC_WATERING_FAILED,
    DEC__COUNT
} decision_t;

/* Alarmas */
typedef enum {
    ALM_NO_FLOW = 0,
    ALM_FLOW_HIGH,
    ALM_PUMP_TIMEOUT,
    ALM_SAFETY_TRIP,
    ALM_FLOW_WHEN_IDLE,
    ALM_SOIL_NO_RESPONSE,
    ALM_REBOOT_DURING_WATERING,
    ALM_CONFIG_RESET,
    ALM_SOIL_SENSOR,
    ALM_TANK_SENSOR,
    ALM_TANK_LOW,
    ALM_ENV_SENSOR,
    ALM_TIME_INVALID,
    ALM_DAILY_LIMIT,
    ALM_COMMS,
    ALM__COUNT
} alarm_t;

typedef enum { SEV_INFO = 0, SEV_WARNING, SEV_CRITICAL } alarm_severity_t;

typedef struct {
    const char *code;       /* Nombre publicado por MQTT              */
    alarm_severity_t sev;
    bool latched;           /* true: queda activa hasta CLEAR_ALARM    */
    bool blocks_all;        /* bloquea todo riego (estado FAULT)       */
    bool blocks_auto;       /* bloquea solo el riego automático        */
    const char *text;       /* Descripción en español                  */
} alarm_info_t;

#define ALARM_BIT(a) (1UL << (a))

const char *state_name(irr_state_t s);
const char *phase_name(water_phase_t p);
const char *reason_name(water_reason_t r);
const char *result_name(water_result_t r);
const char *decision_name(decision_t d);
const char *decision_text(decision_t d);
const alarm_info_t *alarm_info(alarm_t a);
const char *severity_name(alarm_severity_t s);
int alarm_from_name(const char *code);   /* -1 si no existe */
