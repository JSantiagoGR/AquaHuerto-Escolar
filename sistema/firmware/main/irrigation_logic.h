/*
 * Lógica de riego PURA: máquina de estados sin acceso a hardware ni a FreeRTOS.
 * Recibe entradas (sensores, pulsos, hora) y produce órdenes ON/OFF para
 * bomba y válvula más eventos. La misma lógica se ejecuta en el equipo real y
 * en el autodiagnóstico (selftest) con entradas simuladas y reloj virtual.
 *
 * No hay control PI/PID ni PWM: el agua se dosifica contando pulsos del
 * YF-S201 y cortando al alcanzar el volumen programado.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "app_types.h"
#include "configuration.h"

typedef struct {
    uint32_t now_ms;            /* Reloj monótono (virtual en simulación)        */
    bool time_valid;
    int minute_of_day;          /* Hora local en minutos (-1 si no es válida)    */
    int32_t day_key;
    uint32_t epoch;

    bool soil_valid;
    float soil_vwc;
    uint32_t soil_seq;

    bool tank_valid;
    bool tank_calibrated;
    float tank_pct;

    bool env_valid;
    float temp_c;
    float rh_pct;

    uint32_t flow_pulses;       /* Total monótono de pulsos                      */
    bool outputs_enabled;       /* Potencia habilitada o simulación              */
    bool sensors_ready;         /* Ya hubo una primera ronda de mediciones       */

    bool rain_expected;         /* Pronóstico vigente con lluvia probable        */

    /* Plan del modelo predictivo (lo calcula el controlador con ia_model) */
    bool ia_active;             /* Modelo validado: PREDICTIVO_ACTIVO            */
    bool ia_need;               /* Hace falta regar para llegar al próximo horario */
    bool ia_limited;            /* Meta recortada a la reserva superior          */
    float ia_liters;            /* Litros totales previstos                      */
    float ia_goal;              /* Humedad meta                                  */
    float ia_corr_liters;       /* Corrección proporcional acotada tras una dosis */

    float rain_mm6;             /* Lluvia prevista en 6 h (mm); 0 sin pronóstico vigente */
} irr_inputs_t;

typedef enum {
    EV_STATE = 0,               /* Cambio de estado                              */
    EV_WATER_START,
    EV_WATER_END,
    EV_EVENT_END,               /* Fin de un evento automático (uno o más ciclos) */
    EV_DECISION,
    EV_ALARM_SET,
    EV_ALARM_CLEAR,
    EV_COUNTERS,                /* Cambio de día / contadores a guardar          */
} irr_ev_type_t;

typedef struct {
    irr_ev_type_t type;
    int code;                   /* estado, alarma, decisión o motivo             */
    int code2;                  /* resultado del riego                           */
    float target_ml;
    float delivered_ml;
    float vwc_before;
    float vwc_after;
    uint32_t duration_ms;
    uint32_t pulses;
    int cycles;
} irr_event_t;

typedef void (*irr_event_cb_t)(const irr_event_t *ev, void *user);

typedef struct {
    /* Configuración vigente (la copia el controlador antes de cada paso) */
    riego_config_t cfg;

    irr_state_t state;
    water_phase_t phase;
    ctrl_mode_t ctrl_mode;      /* MANUAL / AUTOMATICO / IA                       */
    bool auto_enabled;          /* = ctrl_mode != CM_MANUAL                       */

    bool pump_cmd;
    bool valve_cmd;

    /* Riego en curso */
    water_reason_t w_reason;
    float w_target_ml;
    uint32_t w_p0;
    uint32_t w_t_start;
    uint32_t w_t_phase;
    uint32_t w_t_pump_on;
    uint32_t w_last_pulses;
    uint32_t w_last_pulse_change;
    uint32_t w_rate_t;
    uint32_t w_rate_p;
    uint8_t w_high_count;
    float w_flow_lpm;
    float w_delivered_ml;
    float w_vwc_before;
    water_result_t w_result;

    /* Evento automático (uno o varios ciclos con infiltración) */
    bool ev_active;
    bool ev_emergency;
    event_kind_t ev_kind;
    float ev_goal;              /* Humedad meta del evento                       */
    int ev_cycles;
    float ev_ml;
    float ev_vwc_start;
    uint32_t ev_t_start;
    uint32_t infil_t_start;
    bool infil_waiting_sample;
    uint32_t infil_sample_ref;

    uint32_t last_event_end_ms;
    bool have_last_event;
    uint32_t last_emergency_ms;
    bool have_last_emergency;

    int dry_count;
    uint32_t last_soil_seq;
    uint32_t last_eval_ms;
    float last_vwc;
    bool last_vwc_valid;

    /* Contadores (el controlador los persiste) */
    float daily_ml;
    double total_ml;
    int32_t day_key;

    /* Alarmas activas (bits ALARM_BIT) */
    uint32_t alarms;

    /* Última decisión publicada */
    decision_t decision;

    /* Vigilancia de flujo con todo apagado */
    uint32_t idle_ref_pulses;
    uint32_t idle_ref_ms;
    uint32_t closed_at_ms;
    uint32_t last_idle_pulse_ms;

    /* Salidas auxiliares para el controlador */
    bool want_soil_sample;
    uint32_t soil_interval_s;

    irr_event_cb_t cb;
    void *cb_user;

    bool over_daily;            /* El usuario autorizó pasar el máximo diario en ESTE riego manual */
} irr_ctx_t;

/* Banderas de los riegos manuales */
#define IRR_FORCE_HUM_MAX   0x01u   /* Regar aunque el suelo esté en la humedad máxima */
#define IRR_OVER_DAILY      0x02u   /* Pasar el máximo diario de litros (botón de autorización) */

typedef enum { CMD_OK = 0, CMD_REJECTED, CMD_INVALID } cmd_result_t;

void irr_init(irr_ctx_t *ctx, const riego_config_t *cfg, irr_event_cb_t cb, void *user);
void irr_step(irr_ctx_t *ctx, const irr_inputs_t *in);

/* Solo en modo MANUAL. flags: IRR_FORCE_HUM_MAX | IRR_OVER_DAILY */
cmd_result_t irr_cmd_start_manual(irr_ctx_t *ctx, const irr_inputs_t *in, float liters,
                                  unsigned flags, char *msg, int len);
void irr_cmd_stop(irr_ctx_t *ctx, const irr_inputs_t *in);
cmd_result_t irr_cmd_set_auto(irr_ctx_t *ctx, const irr_inputs_t *in, bool enable, char *msg, int len);
/* Cambia el modo de operación (MANUAL / AUTOMATICO / IA) */
cmd_result_t irr_cmd_set_mode(irr_ctx_t *ctx, const irr_inputs_t *in, ctrl_mode_t mode, char *msg, int len);
/* Riego manual hacia la humedad óptima: dosis limitadas con infiltración */
/* goal <= 0: humedad óptima del cultivo; si no, la humedad elegida (por dosis con pausa y nueva lectura). */
cmd_result_t irr_cmd_start_to_target(irr_ctx_t *ctx, const irr_inputs_t *in, float goal, unsigned flags,
                                     char *msg, int len);
cmd_result_t irr_cmd_clear_alarm(irr_ctx_t *ctx, const irr_inputs_t *in, int alarm, char *msg, int len);

/* Alarmas externas (supervisor de seguridad, reinicio, configuración, red) */
void irr_raise_alarm(irr_ctx_t *ctx, const irr_inputs_t *in, alarm_t a);
void irr_set_condition(irr_ctx_t *ctx, alarm_t a, bool active);

/* Utilidades de horario (también usadas para publicar el próximo riego) */
bool irr_in_window(const riego_config_t *c, int minute);
bool irr_in_midday(const riego_config_t *c, int minute);
int irr_next_window_start(const riego_config_t *c, int minute);   /* -1 si no hay */
/* Horas desde 'minute' hasta el inicio del SIGUIENTE horario preferido después
 * del actual (horizonte del plan IA). 24 si solo hay un horario. */
float irr_hours_to_following_window(const riego_config_t *c, int minute);

bool irr_is_watering(const irr_ctx_t *ctx);
bool irr_has_blocking_alarm(const irr_ctx_t *ctx);
