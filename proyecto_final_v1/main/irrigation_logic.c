#include <math.h>
#include <stdio.h>
#include <string.h>

#include "irrigation_logic.h"

#define IDLE_GRACE_MS        5000u      /* Agua que escurre tras cerrar la válvula */
#define IDLE_WINDOW_MS       60000u
#define FLOW_HIGH_WINDOWS    3          /* Ventanas de 1 s seguidas sobre el máximo */
#define REEVAL_MS            60000u     /* Reevaluar decisiones al menos cada minuto */
#define MIN_USEFUL_ML        100.0f
#define TANK_HYST_PCT        3.0f
#define TANK_ABORT_MARGIN    2.0f

/* ----------------------------- Utilidades -------------------------------- */

static void emit(irr_ctx_t *ctx, const irr_event_t *ev)
{
    if (ctx->cb) {
        ctx->cb(ev, ctx->cb_user);
    }
}

static void emit_simple(irr_ctx_t *ctx, irr_ev_type_t t, int code)
{
    irr_event_t ev = { .type = t, .code = code };
    emit(ctx, &ev);
}

static void set_state(irr_ctx_t *ctx, irr_state_t s)
{
    if (ctx->state != s) {
        ctx->state = s;
        emit_simple(ctx, EV_STATE, s);
    }
}

static void set_decision(irr_ctx_t *ctx, decision_t d)
{
    if (ctx->decision != d) {
        ctx->decision = d;
        emit_simple(ctx, EV_DECISION, d);
    }
}

static void alarm_on(irr_ctx_t *ctx, alarm_t a)
{
    if (!(ctx->alarms & ALARM_BIT(a))) {
        ctx->alarms |= ALARM_BIT(a);
        emit_simple(ctx, EV_ALARM_SET, a);
    }
}

static void alarm_off(irr_ctx_t *ctx, alarm_t a)
{
    if (ctx->alarms & ALARM_BIT(a)) {
        ctx->alarms &= ~ALARM_BIT(a);
        emit_simple(ctx, EV_ALARM_CLEAR, a);
    }
}

void irr_set_condition(irr_ctx_t *ctx, alarm_t a, bool active)
{
    if (active) {
        alarm_on(ctx, a);
    } else {
        alarm_off(ctx, a);
    }
}

bool irr_has_blocking_alarm(const irr_ctx_t *ctx)
{
    for (int a = 0; a < ALM__COUNT; a++) {
        const alarm_info_t *ai = alarm_info((alarm_t)a);
        if ((ctx->alarms & ALARM_BIT(a)) && ai->blocks_all) {
            return true;
        }
    }
    return false;
}

static bool auto_locked(const irr_ctx_t *ctx)
{
    for (int a = 0; a < ALM__COUNT; a++) {
        const alarm_info_t *ai = alarm_info((alarm_t)a);
        if ((ctx->alarms & ALARM_BIT(a)) && ai->latched && ai->blocks_auto) {
            return true;
        }
    }
    return false;
}

bool irr_is_watering(const irr_ctx_t *ctx)
{
    return ctx->state == ST_MANUAL_WATERING || ctx->state == ST_AUTO_WATERING;
}

static irr_state_t rest_state(const irr_ctx_t *ctx)
{
    if (irr_has_blocking_alarm(ctx)) {
        return ST_FAULT;
    }
    return ctx->auto_enabled ? ST_MONITORING : ST_IDLE;
}

static float pulses_to_ml(const irr_ctx_t *ctx, uint32_t pulses)
{
    return (float)pulses * 1000.0f / ctx->cfg.pulses_per_liter;
}

static bool is_fault_result(water_result_t r)
{
    return r == RES_NO_FLOW || r == RES_FLOW_HIGH || r == RES_PUMP_TIMEOUT || r == RES_SAFETY;
}

/* ------------------------------ Horarios --------------------------------- */

static bool in_range(int m, float start, float end)
{
    int s = (int)start, e = (int)end;
    if (s < e) {
        return m >= s && m < e;
    }
    return m >= s || m < e;           /* Horario que cruza la medianoche */
}

bool irr_in_window(const riego_config_t *c, int minute)
{
    if (minute < 0) {
        return false;
    }
    return (c->win1_en && in_range(minute, c->win1_start, c->win1_end)) ||
           (c->win2_en && in_range(minute, c->win2_start, c->win2_end));
}

bool irr_in_midday(const riego_config_t *c, int minute)
{
    return minute >= 0 && in_range(minute, c->midday_start, c->midday_end);
}

int irr_next_window_start(const riego_config_t *c, int minute)
{
    int best = -1, best_delta = 100000;
    const float starts[2] = { c->win1_start, c->win2_start };
    const bool en[2] = { c->win1_en != 0, c->win2_en != 0 };
    for (int i = 0; i < 2; i++) {
        if (!en[i]) {
            continue;
        }
        int s = (int)starts[i];
        int delta = (minute < 0) ? s : ((s - minute + 1440) % 1440);
        if (delta < best_delta) {
            best_delta = delta;
            best = s;
        }
    }
    return best;
}

/* ------------------------------- Riego ----------------------------------- */

static void start_watering(irr_ctx_t *ctx, const irr_inputs_t *in, water_reason_t reason, float target_ml)
{
    ctx->w_reason = reason;
    ctx->w_target_ml = target_ml;
    ctx->w_p0 = in->flow_pulses;
    ctx->w_t_start = in->now_ms;
    ctx->w_t_phase = in->now_ms;
    ctx->w_t_pump_on = 0;
    ctx->w_last_pulses = in->flow_pulses;
    ctx->w_last_pulse_change = in->now_ms;
    ctx->w_high_count = 0;
    ctx->w_flow_lpm = 0.0f;
    ctx->w_delivered_ml = 0.0f;
    ctx->w_result = RES_NONE;
    ctx->w_vwc_before = in->soil_valid ? in->soil_vwc : NAN;
    ctx->phase = PH_OPENING;
    ctx->valve_cmd = true;              /* 1) Abrir electroválvula */
    ctx->pump_cmd = false;
    set_state(ctx, reason == WR_MANUAL ? ST_MANUAL_WATERING : ST_AUTO_WATERING);

    irr_event_t ev = { .type = EV_WATER_START, .code = reason, .target_ml = target_ml,
                       .vwc_before = ctx->w_vwc_before, .cycles = ctx->ev_cycles + 1 };
    emit(ctx, &ev);
}

/* Pide el apagado ordenado: bomba OFF ahora, válvula OFF tras valve_lag_ms */
static void finish_watering(irr_ctx_t *ctx, const irr_inputs_t *in, water_result_t result)
{
    if (ctx->phase == PH_CLOSING || ctx->phase == PH_NONE) {
        return;
    }
    ctx->pump_cmd = false;
    ctx->w_result = result;
    ctx->phase = PH_CLOSING;
    ctx->w_t_phase = in->now_ms;
    switch (result) {
    case RES_NO_FLOW:      alarm_on(ctx, ALM_NO_FLOW); break;
    case RES_FLOW_HIGH:    alarm_on(ctx, ALM_FLOW_HIGH); break;
    case RES_PUMP_TIMEOUT: alarm_on(ctx, ALM_PUMP_TIMEOUT); break;
    default: break;
    }
}

static void end_event(irr_ctx_t *ctx, const irr_inputs_t *in, decision_t why)
{
    if (!ctx->ev_active) {
        return;
    }
    ctx->ev_active = false;
    ctx->infil_waiting_sample = false;
    ctx->last_event_end_ms = in->now_ms;
    ctx->have_last_event = true;
    ctx->dry_count = 0;
    irr_event_t ev = {
        .type = EV_EVENT_END, .code = why, .delivered_ml = ctx->ev_ml,
        .vwc_before = ctx->ev_vwc_start, .vwc_after = in->soil_valid ? in->soil_vwc : NAN,
        .duration_ms = in->now_ms - ctx->ev_t_start, .cycles = ctx->ev_cycles,
    };
    emit(ctx, &ev);
    set_decision(ctx, why);
    set_state(ctx, rest_state(ctx));
}

/* Cierra la contabilidad de un riego (la válvula ya se cerró) */
static void complete_watering(irr_ctx_t *ctx, const irr_inputs_t *in)
{
    ctx->pump_cmd = false;
    ctx->valve_cmd = false;
    ctx->phase = PH_NONE;
    uint32_t pulses = in->flow_pulses - ctx->w_p0;
    float d = pulses_to_ml(ctx, pulses);
    ctx->w_delivered_ml = d;
    ctx->daily_ml += d;
    ctx->total_ml += d;
    ctx->closed_at_ms = in->now_ms;
    ctx->idle_ref_pulses = in->flow_pulses;
    ctx->idle_ref_ms = in->now_ms;

    irr_event_t ev = {
        .type = EV_WATER_END, .code = ctx->w_reason, .code2 = ctx->w_result,
        .target_ml = ctx->w_target_ml, .delivered_ml = d,
        .vwc_before = ctx->w_vwc_before, .vwc_after = in->soil_valid ? in->soil_vwc : NAN,
        .duration_ms = in->now_ms - ctx->w_t_start, .pulses = pulses,
        .cycles = ctx->ev_cycles + 1,
    };
    emit(ctx, &ev);

    water_result_t r = ctx->w_result;
    if (ctx->w_reason == WR_MANUAL) {
        ctx->last_event_end_ms = in->now_ms;      /* El automático respeta el intervalo */
        ctx->have_last_event = true;
        set_state(ctx, rest_state(ctx));
        return;
    }

    /* Riego automático */
    ctx->ev_cycles++;
    ctx->ev_ml += d;
    if (is_fault_result(r)) {
        end_event(ctx, in, DEC_WATERING_FAILED);
    } else if (r == RES_STOP_CMD) {
        end_event(ctx, in, DEC_STOPPED);
    } else if (r == RES_DAILY_LIMIT) {
        end_event(ctx, in, DEC_DAILY_LIMIT);
    } else if (r == RES_EVENT_LIMIT) {
        end_event(ctx, in, DEC_MAX_EVENT_L);
    } else if (r == RES_TANK_LOW) {
        end_event(ctx, in, DEC_TANK_LOW);
    } else {
        /* Ciclo completo: esperar infiltración antes de volver a medir */
        ctx->infil_t_start = in->now_ms;
        ctx->infil_waiting_sample = false;
        set_state(ctx, ST_INFILTRATION_WAIT);
        set_decision(ctx, DEC_INFILTRATING);
    }
}

static void watering_step(irr_ctx_t *ctx, const irr_inputs_t *in)
{
    const riego_config_t *c = &ctx->cfg;
    uint32_t now = in->now_ms;

    switch (ctx->phase) {
    case PH_OPENING:
        ctx->valve_cmd = true;
        ctx->pump_cmd = false;
        if (now - ctx->w_t_phase >= (uint32_t)c->valve_lead_ms) {
            ctx->pump_cmd = true;               /* 2) Encender bomba */
            ctx->phase = PH_PUMPING;
            ctx->w_t_pump_on = now;
            ctx->w_last_pulse_change = now;
            ctx->w_last_pulses = in->flow_pulses;
            ctx->w_rate_t = now;
            ctx->w_rate_p = in->flow_pulses;
        }
        break;

    case PH_PUMPING: {
        uint32_t pulses = in->flow_pulses - ctx->w_p0;
        ctx->w_delivered_ml = pulses_to_ml(ctx, pulses);

        if (in->flow_pulses != ctx->w_last_pulses) {
            ctx->w_last_pulses = in->flow_pulses;
            ctx->w_last_pulse_change = now;
        }
        if (now - ctx->w_rate_t >= 1000) {
            uint32_t dp = in->flow_pulses - ctx->w_rate_p;
            float dt_min = (float)(now - ctx->w_rate_t) / 60000.0f;
            ctx->w_flow_lpm = ((float)dp / c->pulses_per_liter) / dt_min;
            ctx->w_rate_t = now;
            ctx->w_rate_p = in->flow_pulses;
            ctx->w_high_count = (ctx->w_flow_lpm > c->flow_max_lpm) ? ctx->w_high_count + 1 : 0;
        }

        float remaining_daily = c->max_liters_daily * 1000.0f - ctx->daily_ml;
        float event_used = ctx->ev_active ? ctx->ev_ml : 0.0f;

        if (ctx->w_delivered_ml >= ctx->w_target_ml - c->overrun_ml) {
            finish_watering(ctx, in, RES_TARGET);            /* 3) Volumen alcanzado */
        } else if (ctx->w_high_count >= FLOW_HIGH_WINDOWS) {
            finish_watering(ctx, in, RES_FLOW_HIGH);
        } else if (now - ctx->w_last_pulse_change >= (uint32_t)(c->no_flow_s * 1000.0f)) {
            finish_watering(ctx, in, RES_NO_FLOW);
        } else if (now - ctx->w_t_pump_on >= (uint32_t)(c->pump_max_s * 1000.0f)) {
            finish_watering(ctx, in, RES_PUMP_TIMEOUT);
        } else if (ctx->w_delivered_ml >= remaining_daily) {
            finish_watering(ctx, in, RES_DAILY_LIMIT);
        } else if (event_used + ctx->w_delivered_ml >= c->max_liters_event * 1000.0f) {
            finish_watering(ctx, in, RES_EVENT_LIMIT);
        } else if (in->tank_calibrated && in->tank_valid &&
                   in->tank_pct < c->tank_min_pct - TANK_ABORT_MARGIN) {
            finish_watering(ctx, in, RES_TANK_LOW);
        }
        break;
    }

    case PH_CLOSING:
        ctx->pump_cmd = false;
        ctx->valve_cmd = true;
        if (now - ctx->w_t_phase >= (uint32_t)c->valve_lag_ms) {
            ctx->valve_cmd = false;             /* 4) Cerrar electroválvula */
            complete_watering(ctx, in);
        }
        break;

    default:
        break;
    }
}

/* -------------------------- Decisión automática -------------------------- */

static void start_event(irr_ctx_t *ctx, const irr_inputs_t *in, bool emergency, float ml)
{
    ctx->ev_active = true;
    ctx->ev_emergency = emergency;
    ctx->ev_cycles = 0;
    ctx->ev_ml = 0.0f;
    ctx->ev_vwc_start = in->soil_vwc;
    ctx->ev_t_start = in->now_ms;
    if (emergency) {
        ctx->last_emergency_ms = in->now_ms;
        ctx->have_last_emergency = true;
    }
    set_decision(ctx, emergency ? DEC_START_EMERGENCY : DEC_START_SCHEDULED);
    start_watering(ctx, in, emergency ? WR_EMERGENCY : WR_SCHEDULED, ml);
}

/* Devuelve la decisión; si corresponde, inicia el evento de riego */
static decision_t auto_decide(irr_ctx_t *ctx, const irr_inputs_t *in)
{
    const riego_config_t *c = &ctx->cfg;
    uint32_t now = in->now_ms;

    if (!in->outputs_enabled) {
        return DEC_OUTPUTS_DISABLED;
    }
    if (!in->soil_valid) {
        return DEC_SOIL_INVALID;
    }
    float v = in->soil_vwc;
    if (v >= c->hum_max) {
        return DEC_TOO_WET;
    }
    if (v >= c->hum_min) {
        return DEC_HUMIDITY_OK;
    }
    if (ctx->dry_count < (int)c->dry_confirm) {
        return DEC_CONFIRMING_DRY;
    }
    if (auto_locked(ctx)) {
        return DEC_AUTO_LOCKED;
    }
    if (!in->tank_calibrated) {
        return DEC_TANK_UNCALIBRATED;
    }
    if (!in->tank_valid) {
        return DEC_TANK_INVALID;
    }
    if (in->tank_pct < c->tank_min_pct) {
        return DEC_TANK_LOW;
    }
    float remaining_daily = c->max_liters_daily * 1000.0f - ctx->daily_ml;
    if (remaining_daily < MIN_USEFUL_ML) {
        return DEC_DAILY_LIMIT;
    }
    if (ctx->have_last_event && now - ctx->last_event_end_ms < (uint32_t)(c->min_event_gap_min * 60000.0f)) {
        return DEC_MIN_GAP;
    }

    bool emerg_blocked = false;
    if (c->emergency_en && v < c->hum_critical) {
        if (ctx->have_last_emergency &&
            now - ctx->last_emergency_ms < (uint32_t)(c->emergency_gap_min * 60000.0f)) {
            emerg_blocked = true;
        } else {
            float ml = fminf(c->emergency_liters * 1000.0f, remaining_daily);
            start_event(ctx, in, true, ml);
            return DEC_START_EMERGENCY;
        }
    }

    decision_t d;
    if (!in->time_valid) {
        d = DEC_TIME_INVALID;
    } else if (irr_in_midday(c, in->minute_of_day)) {
        d = DEC_MIDDAY;
    } else if (!irr_in_window(c, in->minute_of_day)) {
        d = DEC_OUTSIDE_WINDOW;
    } else if (in->env_valid && in->temp_c > c->temp_postpone_c) {
        d = DEC_HOT;
    } else {
        float ml = fminf(c->liters_per_cycle * 1000.0f,
                         fminf(c->max_liters_event * 1000.0f, remaining_daily));
        start_event(ctx, in, false, ml);
        return DEC_START_SCHEDULED;
    }
    return emerg_blocked ? DEC_EMERGENCY_GAP : d;
}

static void monitoring_step(irr_ctx_t *ctx, const irr_inputs_t *in)
{
    const riego_config_t *c = &ctx->cfg;
    bool new_sample = (in->soil_seq != ctx->last_soil_seq);
    if (new_sample) {
        ctx->last_soil_seq = in->soil_seq;
        if (in->soil_valid && in->soil_vwc < c->hum_min) {
            ctx->dry_count++;
        } else {
            ctx->dry_count = 0;
        }
    }
    if (!new_sample && in->now_ms - ctx->last_eval_ms < REEVAL_MS) {
        return;
    }
    ctx->last_eval_ms = in->now_ms;
    decision_t d = auto_decide(ctx, in);
    if (d != DEC_START_SCHEDULED && d != DEC_START_EMERGENCY) {
        set_decision(ctx, d);
    }
}

static void infiltration_step(irr_ctx_t *ctx, const irr_inputs_t *in)
{
    const riego_config_t *c = &ctx->cfg;
    ctx->pump_cmd = false;
    ctx->valve_cmd = false;

    if (!ctx->infil_waiting_sample) {
        if (in->now_ms - ctx->infil_t_start < (uint32_t)(c->infilt_min * 60000.0f)) {
            return;
        }
        /* Terminó la espera: pedir una lectura NUEVA del EC-5 */
        ctx->infil_waiting_sample = true;
        ctx->infil_sample_ref = in->soil_seq;
        ctx->want_soil_sample = true;
        return;
    }
    if (in->soil_seq == ctx->infil_sample_ref) {
        ctx->want_soil_sample = true;
        return;
    }
    ctx->want_soil_sample = false;
    ctx->infil_waiting_sample = false;
    ctx->last_soil_seq = in->soil_seq;

    if (!in->outputs_enabled) {
        end_event(ctx, in, DEC_OUTPUTS_DISABLED);
        return;
    }
    if (!in->soil_valid) {
        end_event(ctx, in, DEC_SOIL_INVALID);
        return;
    }
    float v = in->soil_vwc;
    if (v >= c->hum_target) {
        end_event(ctx, in, DEC_TARGET_REACHED);
        return;
    }
    if (v >= c->hum_max) {
        end_event(ctx, in, DEC_TOO_WET);
        return;
    }
    if (ctx->ev_emergency) {
        end_event(ctx, in, DEC_EMERGENCY_DONE);
        return;
    }
    if (ctx->ev_cycles >= (int)c->response_cycles &&
        (v - ctx->ev_vwc_start) < c->min_response_pp) {
        alarm_on(ctx, ALM_SOIL_NO_RESPONSE);
        end_event(ctx, in, DEC_NO_RESPONSE);
        return;
    }
    if (ctx->ev_cycles >= (int)c->max_cycles) {
        end_event(ctx, in, DEC_MAX_CYCLES);
        return;
    }
    float rem_event = c->max_liters_event * 1000.0f - ctx->ev_ml;
    float rem_daily = c->max_liters_daily * 1000.0f - ctx->daily_ml;
    if (rem_event < MIN_USEFUL_ML) {
        end_event(ctx, in, DEC_MAX_EVENT_L);
        return;
    }
    if (rem_daily < MIN_USEFUL_ML) {
        end_event(ctx, in, DEC_DAILY_LIMIT);
        return;
    }
    if (!in->tank_calibrated || !in->tank_valid || in->tank_pct < c->tank_min_pct) {
        end_event(ctx, in, !in->tank_calibrated ? DEC_TANK_UNCALIBRATED :
                           (!in->tank_valid ? DEC_TANK_INVALID : DEC_TANK_LOW));
        return;
    }
    if (!in->time_valid || !irr_in_window(c, in->minute_of_day) || irr_in_midday(c, in->minute_of_day)) {
        end_event(ctx, in, DEC_WINDOW_ENDED);
        return;
    }
    if (in->env_valid && in->temp_c > c->temp_postpone_c) {
        end_event(ctx, in, DEC_HOT);
        return;
    }
    float ml = fminf(c->liters_per_cycle * 1000.0f, fminf(rem_event, rem_daily));
    set_decision(ctx, DEC_CONTINUE_CYCLE);
    start_watering(ctx, in, WR_SCHEDULED, ml);
}

/* Flujo con bomba apagada y válvula cerrada: posible contacto pegado o fuga */
static void idle_flow_check(irr_ctx_t *ctx, const irr_inputs_t *in)
{
    uint32_t now = in->now_ms;
    if (now - ctx->closed_at_ms < IDLE_GRACE_MS) {
        ctx->idle_ref_pulses = in->flow_pulses;
        ctx->idle_ref_ms = now;
        return;
    }
    if (in->flow_pulses != ctx->idle_ref_pulses) {
        ctx->last_idle_pulse_ms = now;
    }
    if (in->flow_pulses - ctx->idle_ref_pulses >= (uint32_t)ctx->cfg.idle_flow_pulses) {
        alarm_on(ctx, ALM_FLOW_WHEN_IDLE);
        ctx->idle_ref_pulses = in->flow_pulses;
        ctx->idle_ref_ms = now;
        if (ctx->state == ST_INFILTRATION_WAIT) {
            end_event(ctx, in, DEC_FAULT);
        }
        set_state(ctx, ST_FAULT);
        set_decision(ctx, DEC_FAULT);
        return;
    }
    if (now - ctx->idle_ref_ms >= IDLE_WINDOW_MS) {
        ctx->idle_ref_pulses = in->flow_pulses;
        ctx->idle_ref_ms = now;
    }
}

static void update_conditions(irr_ctx_t *ctx, const irr_inputs_t *in)
{
    const riego_config_t *c = &ctx->cfg;
    irr_set_condition(ctx, ALM_TIME_INVALID, !in->time_valid);
    irr_set_condition(ctx, ALM_DAILY_LIMIT, ctx->daily_ml >= c->max_liters_daily * 1000.0f - 1.0f);
    if (!in->sensors_ready) {
        return;
    }
    irr_set_condition(ctx, ALM_SOIL_SENSOR, !in->soil_valid);
    irr_set_condition(ctx, ALM_TANK_SENSOR, !in->tank_valid);
    irr_set_condition(ctx, ALM_ENV_SENSOR, !in->env_valid);
    if (in->tank_calibrated && in->tank_valid) {
        if (in->tank_pct < c->tank_min_pct) {
            alarm_on(ctx, ALM_TANK_LOW);
        } else if (in->tank_pct >= c->tank_min_pct + TANK_HYST_PCT) {
            alarm_off(ctx, ALM_TANK_LOW);
        }
    } else {
        alarm_off(ctx, ALM_TANK_LOW);
    }
}

/* ------------------------------ API pública ------------------------------ */

void irr_init(irr_ctx_t *ctx, const riego_config_t *cfg, irr_event_cb_t cb, void *user)
{
    memset(ctx, 0, sizeof(*ctx));
    ctx->cfg = *cfg;
    ctx->cb = cb;
    ctx->cb_user = user;
    ctx->state = ST_INIT;
    ctx->decision = DEC_NONE;
    ctx->soil_interval_s = (uint32_t)cfg->soil_interval_s;
    ctx->w_vwc_before = NAN;
}

void irr_step(irr_ctx_t *ctx, const irr_inputs_t *in)
{
    const riego_config_t *c = &ctx->cfg;

    /* Cambio de día: reinicia litros diarios (no al pasar de "sin hora" a "con hora") */
    if (in->day_key != ctx->day_key) {
        bool from_unknown = (ctx->day_key < 0 && in->day_key > 0);
        bool first = (ctx->day_key == 0);
        ctx->day_key = in->day_key;
        if (!from_unknown && !first) {
            ctx->daily_ml = 0.0f;
        }
        emit_simple(ctx, EV_COUNTERS, 0);
    }

    update_conditions(ctx, in);

    if (in->soil_valid) {
        ctx->last_vwc = in->soil_vwc;
        ctx->last_vwc_valid = true;
    }

    /* Intervalo de lectura del EC-5 ajustado por condiciones ambientales */
    uint32_t interval = (uint32_t)c->soil_interval_s;
    if (in->env_valid && (in->temp_c >= c->hot_temp_c || in->rh_pct <= c->dry_rh_pct)) {
        interval /= 2;
        if (interval < 60) {
            interval = 60;
        }
    }
    ctx->soil_interval_s = interval;

    switch (ctx->state) {
    case ST_INIT:
        ctx->closed_at_ms = in->now_ms;
        ctx->last_soil_seq = in->soil_seq;
        set_state(ctx, rest_state(ctx));
        set_decision(ctx, ctx->auto_enabled ? DEC_NONE : DEC_AUTO_DISABLED);
        break;
    case ST_IDLE:
        ctx->pump_cmd = ctx->valve_cmd = false;
        idle_flow_check(ctx, in);
        break;
    case ST_MONITORING:
        ctx->pump_cmd = ctx->valve_cmd = false;
        idle_flow_check(ctx, in);
        if (ctx->state == ST_MONITORING) {
            monitoring_step(ctx, in);
        }
        break;
    case ST_MANUAL_WATERING:
    case ST_AUTO_WATERING:
        watering_step(ctx, in);
        break;
    case ST_INFILTRATION_WAIT:
        idle_flow_check(ctx, in);
        if (ctx->state == ST_INFILTRATION_WAIT) {
            infiltration_step(ctx, in);
        }
        break;
    case ST_FAULT:
        ctx->pump_cmd = ctx->valve_cmd = false;
        idle_flow_check(ctx, in);
        set_decision(ctx, DEC_FAULT);
        if (!irr_has_blocking_alarm(ctx)) {
            set_state(ctx, rest_state(ctx));
        }
        break;
    default:
        set_state(ctx, ST_IDLE);
        break;
    }

    /* Invariante de seguridad: fuera de un riego no hay salidas activas */
    if (!irr_is_watering(ctx)) {
        ctx->pump_cmd = false;
        ctx->valve_cmd = false;
        ctx->phase = PH_NONE;
    }
    if (ctx->pump_cmd && !ctx->valve_cmd) {
        ctx->pump_cmd = false;          /* Nunca bomba contra válvula cerrada */
    }
}

cmd_result_t irr_cmd_start_manual(irr_ctx_t *ctx, const irr_inputs_t *in, float liters,
                                  bool force, char *msg, int len)
{
    const riego_config_t *c = &ctx->cfg;
    if (!(liters >= 0.1f) || liters > c->max_liters_event || liters > 10.0f) {
        snprintf(msg, len, "Volumen invalido: debe estar entre 0.10 y %.2f L (max_liters_event)",
                 c->max_liters_event);
        return CMD_INVALID;
    }
    if (irr_is_watering(ctx)) {
        snprintf(msg, len, "Ya hay un riego en curso (%s)", state_name(ctx->state));
        return CMD_REJECTED;
    }
    if (ctx->state == ST_INFILTRATION_WAIT) {
        snprintf(msg, len, "Conflicto: evento automatico en curso; envie STOP primero");
        return CMD_REJECTED;
    }
    if (ctx->state == ST_FAULT || irr_has_blocking_alarm(ctx)) {
        snprintf(msg, len, "Sistema en FALLA: revise y envie CLEAR_ALARM");
        return CMD_REJECTED;
    }
    if (!in->outputs_enabled) {
        snprintf(msg, len, "Salidas de potencia deshabilitadas (POWER ON por consola serial o SIM ON)");
        return CMD_REJECTED;
    }
    float remaining = c->max_liters_daily * 1000.0f - ctx->daily_ml;
    if (liters * 1000.0f > remaining) {
        snprintf(msg, len, "Excede el maximo diario: quedan %.2f L", remaining / 1000.0f);
        return CMD_REJECTED;
    }
    if (in->tank_calibrated) {
        if (!in->tank_valid) {
            snprintf(msg, len, "Sensor de nivel sin datos validos: riego bloqueado");
            return CMD_REJECTED;
        }
        if (in->tank_pct < c->tank_min_pct) {
            snprintf(msg, len, "Tinaco bajo el minimo (%.0f%% < %.0f%%)", in->tank_pct, c->tank_min_pct);
            return CMD_REJECTED;
        }
    } else if (c->mode == MODE_B_FINAL) {
        snprintf(msg, len, "Modo B: el tinaco debe estar calibrado para regar");
        return CMD_REJECTED;
    }
    if (in->soil_valid && in->soil_vwc >= c->hum_max && !force) {
        snprintf(msg, len, "Suelo en o sobre la humedad maxima (%.1f%%); use force=true para forzar",
                 in->soil_vwc);
        return CMD_REJECTED;
    }
    start_watering(ctx, in, WR_MANUAL, liters * 1000.0f);
    snprintf(msg, len, "Riego manual de %.2f L iniciado%s", liters,
             in->tank_calibrated ? "" : " (ADVERTENCIA: tinaco sin calibrar)");
    return CMD_OK;
}

void irr_cmd_stop(irr_ctx_t *ctx, const irr_inputs_t *in)
{
    /* STOP tiene prioridad: todo apagado de inmediato, sin esperas */
    ctx->pump_cmd = false;
    ctx->valve_cmd = false;
    if (irr_is_watering(ctx)) {
        ctx->w_result = RES_STOP_CMD;
        complete_watering(ctx, in);
    } else if (ctx->state == ST_INFILTRATION_WAIT) {
        end_event(ctx, in, DEC_STOPPED);
    }
    ctx->phase = PH_NONE;
}

cmd_result_t irr_cmd_set_auto(irr_ctx_t *ctx, const irr_inputs_t *in, bool enable, char *msg, int len)
{
    if (enable) {
        if (irr_has_blocking_alarm(ctx)) {
            snprintf(msg, len, "No se habilita: sistema en FALLA");
            return CMD_REJECTED;
        }
        if (!in->outputs_enabled) {
            snprintf(msg, len, "No se habilita: salidas de potencia deshabilitadas");
            return CMD_REJECTED;
        }
        ctx->auto_enabled = true;
        ctx->last_eval_ms = in->now_ms - REEVAL_MS;   /* Evaluar de inmediato */
        if (ctx->state == ST_IDLE) {
            set_state(ctx, ST_MONITORING);
        }
        snprintf(msg, len, "Riego automatico habilitado");
        return CMD_OK;
    }
    ctx->auto_enabled = false;
    if (ctx->state == ST_AUTO_WATERING) {
        irr_cmd_stop(ctx, in);
    } else if (ctx->state == ST_INFILTRATION_WAIT) {
        end_event(ctx, in, DEC_AUTO_DISABLED);
    }
    if (ctx->state == ST_MONITORING) {
        set_state(ctx, ST_IDLE);
    }
    set_decision(ctx, DEC_AUTO_DISABLED);
    snprintf(msg, len, "Riego automatico deshabilitado");
    return CMD_OK;
}

void irr_raise_alarm(irr_ctx_t *ctx, const irr_inputs_t *in, alarm_t a)
{
    alarm_on(ctx, a);
    const alarm_info_t *ai = alarm_info(a);
    if (ai && ai->blocks_all) {
        if (irr_is_watering(ctx)) {
            ctx->pump_cmd = false;
            ctx->valve_cmd = false;
            ctx->w_result = RES_SAFETY;
            complete_watering(ctx, in);
        } else if (ctx->state == ST_INFILTRATION_WAIT) {
            end_event(ctx, in, DEC_FAULT);
        }
        set_state(ctx, ST_FAULT);
        set_decision(ctx, DEC_FAULT);
    }
}

static bool clear_one(irr_ctx_t *ctx, const irr_inputs_t *in, alarm_t a, char *why, int len)
{
    const alarm_info_t *ai = alarm_info(a);
    if (!(ctx->alarms & ALARM_BIT(a))) {
        return true;
    }
    if (!ai->latched) {
        snprintf(why, len, "%s se borra sola cuando se resuelve la causa", ai->code);
        return false;
    }
    if (a == ALM_FLOW_WHEN_IDLE && in->now_ms - ctx->last_idle_pulse_ms < 10000) {
        snprintf(why, len, "FLOW_WHEN_IDLE: siguen llegando pulsos con todo apagado");
        return false;
    }
    if (a == ALM_SOIL_NO_RESPONSE && !in->soil_valid) {
        snprintf(why, len, "SOIL_NO_RESPONSE: el EC-5 no tiene lectura valida");
        return false;
    }
    alarm_off(ctx, a);
    return true;
}

cmd_result_t irr_cmd_clear_alarm(irr_ctx_t *ctx, const irr_inputs_t *in, int alarm, char *msg, int len)
{
    if (irr_is_watering(ctx)) {
        snprintf(msg, len, "No se borran alarmas durante un riego");
        return CMD_REJECTED;
    }
    char why[96] = "";
    bool ok = true;
    if (alarm < 0) {
        for (int a = 0; a < ALM__COUNT; a++) {
            const alarm_info_t *ai = alarm_info((alarm_t)a);
            if (ai->latched && !clear_one(ctx, in, (alarm_t)a, why, sizeof(why))) {
                ok = false;
            }
        }
    } else if (alarm < ALM__COUNT) {
        ok = clear_one(ctx, in, (alarm_t)alarm, why, sizeof(why));
    } else {
        snprintf(msg, len, "Alarma desconocida");
        return CMD_INVALID;
    }
    if (ctx->state == ST_FAULT && !irr_has_blocking_alarm(ctx)) {
        set_state(ctx, rest_state(ctx));
        set_decision(ctx, ctx->auto_enabled ? DEC_NONE : DEC_AUTO_DISABLED);
        ctx->last_eval_ms = in->now_ms - REEVAL_MS;
    }
    if (!ok) {
        snprintf(msg, len, "%s", why);
        return CMD_REJECTED;
    }
    snprintf(msg, len, "Alarmas borradas; estado %s", state_name(ctx->state));
    return CMD_OK;
}
