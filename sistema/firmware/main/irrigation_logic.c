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

float irr_hours_to_following_window(const riego_config_t *c, int minute)
{
    if (minute < 0) {
        return 24.0f;
    }
    /* Si estamos dentro de un horario, el horizonte llega al inicio del
     * siguiente horario distinto; si no, al inicio del próximo horario */
    const float starts[2] = { c->win1_start, c->win2_start };
    const float ends[2] = { c->win1_end, c->win2_end };
    const bool en[2] = { c->win1_en != 0, c->win2_en != 0 };
    int cur = -1;
    for (int i = 0; i < 2; i++) {
        if (en[i] && in_range(minute, starts[i], ends[i])) {
            cur = i;
        }
    }
    int best = -1;
    for (int i = 0; i < 2; i++) {
        if (!en[i] || i == cur) {
            continue;
        }
        int d = ((int)starts[i] - minute + 1440) % 1440;
        if (best < 0 || d < best) {
            best = d;
        }
    }
    if (best < 0) {
        if (cur < 0) {
            return 24.0f;
        }
        best = ((int)starts[cur] - minute + 1440) % 1440;   /* mismo horario mañana */
        if (best == 0) {
            best = 1440;
        }
    }
    return (float)best / 60.0f;
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
    set_state(ctx, (reason == WR_MANUAL || reason == WR_MANUAL_TARGET) ? ST_MANUAL_WATERING : ST_AUTO_WATERING);

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
    ctx->ev_kind = EVK_NONE;
    ctx->over_daily = false;
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
        ctx->over_daily = false;                  /* La autorización extra era solo para este riego */
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
        } else if (!ctx->over_daily && ctx->w_delivered_ml >= remaining_daily) {
            finish_watering(ctx, in, RES_DAILY_LIMIT);
        } else if (event_used + ctx->w_delivered_ml >= c->max_liters_event * 1000.0f) {
            finish_watering(ctx, in, RES_EVENT_LIMIT);
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

static water_reason_t kind_reason(event_kind_t k)
{
    switch (k) {
    case EVK_EMERGENCY:     return WR_EMERGENCY;
    case EVK_MANUAL_TARGET: return WR_MANUAL_TARGET;
    case EVK_IA:            return WR_IA;
    default:                return WR_SCHEDULED;
    }
}

static void start_event(irr_ctx_t *ctx, const irr_inputs_t *in, event_kind_t kind, float ml, float goal,
                        decision_t why)
{
    bool emergency = (kind == EVK_EMERGENCY);
    ctx->ev_active = true;
    ctx->ev_kind = kind;
    ctx->ev_goal = goal;
    ctx->ev_emergency = emergency;
    ctx->ev_cycles = 0;
    ctx->ev_ml = 0.0f;
    ctx->ev_vwc_start = in->soil_vwc;
    ctx->ev_t_start = in->now_ms;
    if (emergency) {
        ctx->last_emergency_ms = in->now_ms;
        ctx->have_last_emergency = true;
    }
    set_decision(ctx, why);
    start_watering(ctx, in, kind_reason(kind), ml);
}

/* Devuelve la decisión; si corresponde, inicia el evento de riego.
 * AUTOMATICO: riega en horario preferido si la humedad está bajo
 *   (objetivo - histéresis), confirmado con varias lecturas.
 * IA (modelo validado): riega en horario solo si el plan predice que no se
 *   mantendrá sobre la mínima hasta el siguiente horario; dosis calculada.
 * Ambos: emergencia (humedad crítica) a cualquier hora con un ciclo limitado. */
/* Aviso del tinaco para los mensajes de riego (no bloquea). */
static const char *tank_warning(const riego_config_t *c, const irr_inputs_t *in)
{
    if (!in->tank_calibrated) {
        return " (ADVERTENCIA: tinaco sin calibrar)";
    }
    if (!in->tank_valid) {
        return " (ADVERTENCIA: sensor del tinaco sin lectura)";
    }
    if (in->tank_pct < c->tank_min_pct) {
        return " (ADVERTENCIA: TINACO EN EL MINIMO, casi sin agua)";
    }
    return "";
}

/* Lluvia por balance: pospone solo si la lluvia efectiva (80 % de la prevista) alcanza para subir
 * la humedad hasta la meta. Cama de 1 m²: 1 mm de lluvia = 1 L, que sube ia_gain_prior %VWC. */
static bool rain_covers(const riego_config_t *c, const irr_inputs_t *in, float v, float goal)
{
    return 0.8f * in->rain_mm6 * c->ia_gain_prior >= goal - v;
}

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
    if (v >= c->hum_reserve) {
        return DEC_ABOVE_RESERVE;
    }
    bool ia = (ctx->ctrl_mode == CM_IA) && in->ia_active;
    bool critical = c->emergency_en && v < c->hum_critical;
    bool below = v < c->hum_target - c->auto_hyst_pp;
    if (!critical) {
        if (ia) {
            if (!in->ia_need) {
                return DEC_IA_NOT_NEEDED;
            }
        } else if (!below) {
            return DEC_HUMIDITY_OK;
        }
    }
    if ((!ia || critical) && ctx->dry_count < (int)c->dry_confirm) {
        return DEC_CONFIRMING_DRY;
    }
    if (auto_locked(ctx)) {
        return DEC_AUTO_LOCKED;
    }
    /* Tinaco: NO bloquea (decisión del equipo). Si está bajo el mínimo o sin lectura se avisa con
     * las alarmas TANK_LOW / TANK_SENSOR; si de verdad no hay agua, el corte por falta de flujo
     * (no_flow_s) protege la bomba. */
    float remaining_daily = c->max_liters_daily * 1000.0f - ctx->daily_ml;
    if (remaining_daily < MIN_USEFUL_ML) {
        return DEC_DAILY_LIMIT;
    }
    if (ctx->have_last_event && now - ctx->last_event_end_ms < (uint32_t)(c->min_event_gap_min * 60000.0f)) {
        return DEC_MIN_GAP;
    }

    bool emerg_blocked = false;
    if (critical) {
        if (ctx->have_last_emergency &&
            now - ctx->last_emergency_ms < (uint32_t)(c->emergency_gap_min * 60000.0f)) {
            emerg_blocked = true;
        } else {
            float ml = fminf(c->emergency_liters * 1000.0f, remaining_daily);
            start_event(ctx, in, EVK_EMERGENCY, ml, c->hum_min, DEC_START_EMERGENCY);
            return DEC_START_EMERGENCY;
        }
    }

    decision_t d;
    if (!in->time_valid) {
        d = DEC_TIME_INVALID;
    } else if (irr_in_midday(c, in->minute_of_day)) {
        d = DEC_MIDDAY;
    } else if (!irr_in_window(c, in->minute_of_day)) {
        d = (v < c->hum_min) ? DEC_BELOW_MIN_WAIT : DEC_OUTSIDE_WINDOW;
    } else if (in->env_valid && in->temp_c > c->temp_postpone_c) {
        d = DEC_HOT;
    } else if (c->rain_postpone_en && in->rain_expected && ctx->ctrl_mode == CM_IA &&
               rain_covers(c, in, v, c->hum_target)) {
        d = DEC_RAIN_EXPECTED;            /* Solo modo IA, y solo si la lluvia cubre el déficit */
    } else if (ia) {
        float ml = fminf(in->ia_liters * 1000.0f, c->liters_per_cycle * 1000.0f);
        ml = fminf(ml, fminf(c->max_liters_event * 1000.0f, remaining_daily));
        if (ml < MIN_USEFUL_ML) {
            return DEC_IA_NOT_NEEDED;
        }
        decision_t why = in->ia_limited ? DEC_IA_LIMITED : DEC_START_IA;
        start_event(ctx, in, EVK_IA, ml, in->ia_goal, why);
        return why;
    } else {
        float ml = fminf(c->liters_per_cycle * 1000.0f,
                         fminf(c->max_liters_event * 1000.0f, remaining_daily));
        start_event(ctx, in, EVK_AUTO, ml, c->hum_target, DEC_START_SCHEDULED);
        return DEC_START_SCHEDULED;
    }
    return emerg_blocked ? DEC_EMERGENCY_GAP : d;
}

static bool is_start(decision_t d)
{
    return d == DEC_START_SCHEDULED || d == DEC_START_EMERGENCY || d == DEC_START_IA || d == DEC_IA_LIMITED;
}

static void monitoring_step(irr_ctx_t *ctx, const irr_inputs_t *in)
{
    const riego_config_t *c = &ctx->cfg;
    bool new_sample = (in->soil_seq != ctx->last_soil_seq);
    if (new_sample) {
        ctx->last_soil_seq = in->soil_seq;
        if (in->soil_valid && in->soil_vwc < c->hum_target - c->auto_hyst_pp) {
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
    if (!is_start(d)) {
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
    if (v >= c->hum_max) {
        end_event(ctx, in, DEC_TOO_WET);
        return;
    }
    if (ctx->ev_kind == EVK_IA) {
        if (v >= ctx->ev_goal - c->ia_tol_pp * 0.5f) {
            end_event(ctx, in, DEC_IA_GOAL_REACHED);
            return;
        }
    } else if (v >= ctx->ev_goal) {
        end_event(ctx, in, DEC_TARGET_REACHED);
        return;
    }
    if (v >= c->hum_reserve) {
        end_event(ctx, in, DEC_ABOVE_RESERVE);
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
    if (ctx->over_daily) {
        rem_daily = c->max_liters_event * 1000.0f;   /* Autorizado: solo limitan el evento y las protecciones */
    }
    if (rem_daily < MIN_USEFUL_ML) {
        end_event(ctx, in, DEC_DAILY_LIMIT);
        return;
    }
    bool manual_req = (ctx->ev_kind == EVK_MANUAL_TARGET);   /* Pedido explícito del usuario */
    if (!manual_req) {
        if (!in->time_valid || !irr_in_window(c, in->minute_of_day) || irr_in_midday(c, in->minute_of_day)) {
            end_event(ctx, in, DEC_WINDOW_ENDED);
            return;
        }
        if (in->env_valid && in->temp_c > c->temp_postpone_c) {
            end_event(ctx, in, DEC_HOT);
            return;
        }
        if (c->rain_postpone_en && in->rain_expected && ctx->ctrl_mode == CM_IA &&
            rain_covers(c, in, in->soil_vwc, c->hum_target)) {
            end_event(ctx, in, DEC_RAIN_EXPECTED);
            return;
        }
    }
    float dose = c->liters_per_cycle * 1000.0f;
    if (ctx->ev_kind == EVK_IA) {
        /* Corrección proporcional ACOTADA sobre el error de humedad (no PID) */
        dose = fminf(dose, in->ia_corr_liters * 1000.0f);
        if (dose < MIN_USEFUL_ML) {
            end_event(ctx, in, DEC_IA_GOAL_REACHED);
            return;
        }
    }
    float ml = fminf(dose, fminf(rem_event, rem_daily));
    set_decision(ctx, DEC_CONTINUE_CYCLE);
    start_watering(ctx, in, kind_reason(ctx->ev_kind), ml);
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

    /* Cambio de día: reinicia litros diarios (no al pasar de "sin hora" a "con hora").
     * Tras un reinicio sin hora todavía (day_key < 0) se CONSERVA el día guardado y sus litros:
     * antes se reiniciaban y el límite diario se perdía con cada apagón. */
    if (in->day_key != ctx->day_key && !(in->day_key < 0 && ctx->day_key > 0)) {
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
        set_decision(ctx, ctx->auto_enabled ? DEC_NONE : DEC_MODE_MANUAL);
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

static bool require_manual_mode(const irr_ctx_t *ctx, char *msg, int len)
{
    if (ctx->ctrl_mode == CM_MANUAL) {
        return true;
    }
    snprintf(msg, len, "Modo %s activo: cambie a MANUAL para regar manualmente", ctrl_mode_name(ctx->ctrl_mode));
    return false;
}

cmd_result_t irr_cmd_start_manual(irr_ctx_t *ctx, const irr_inputs_t *in, float liters,
                                  unsigned flags, char *msg, int len)
{
    const riego_config_t *c = &ctx->cfg;
    bool force = (flags & IRR_FORCE_HUM_MAX) != 0;
    bool over = (flags & IRR_OVER_DAILY) != 0;
    if (!require_manual_mode(ctx, msg, len)) {
        return CMD_REJECTED;
    }
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
    if (!over && liters * 1000.0f > remaining) {
        snprintf(msg, len, "Excede el maximo diario: quedan %.2f L (autorice el riego extra para continuar)",
                 fmaxf(remaining, 0.0f) / 1000.0f);
        return CMD_REJECTED;
    }
    if (in->soil_valid && in->soil_vwc >= c->hum_max && !force) {
        snprintf(msg, len, "Suelo en o sobre la humedad maxima (%.1f%%); use force=true para forzar",
                 in->soil_vwc);
        return CMD_REJECTED;
    }
    ctx->over_daily = over && liters * 1000.0f > remaining;
    start_watering(ctx, in, WR_MANUAL, liters * 1000.0f);
    snprintf(msg, len, "Riego manual de %.2f L iniciado%s%s", liters,
             ctx->over_daily ? " (EXTRA sobre el maximo diario, autorizado)" : "", tank_warning(c, in));
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

cmd_result_t irr_cmd_set_mode(irr_ctx_t *ctx, const irr_inputs_t *in, ctrl_mode_t mode, char *msg, int len)
{
    if (mode >= CM__COUNT) {
        snprintf(msg, len, "Modo desconocido");
        return CMD_INVALID;
    }
    bool event_busy = ctx->ev_active && ctx->ev_kind != EVK_MANUAL_TARGET;
    if (mode != CM_MANUAL && event_busy && mode != ctx->ctrl_mode) {
        snprintf(msg, len, "Hay un evento automatico en curso: envie STOP o espere a que termine");
        return CMD_REJECTED;
    }
    ctrl_mode_t old = ctx->ctrl_mode;
    ctx->ctrl_mode = mode;
    ctx->auto_enabled = (mode != CM_MANUAL);
    if (mode == CM_MANUAL) {
        /* Al pasar a MANUAL se detiene cualquier evento automático */
        if (event_busy && irr_is_watering(ctx)) {
            irr_cmd_stop(ctx, in);
        } else if (event_busy && ctx->state == ST_INFILTRATION_WAIT) {
            end_event(ctx, in, DEC_MODE_MANUAL);
        }
        if (ctx->state == ST_MONITORING) {
            set_state(ctx, ST_IDLE);
        }
        set_decision(ctx, DEC_MODE_MANUAL);
    } else {
        ctx->last_eval_ms = in->now_ms - REEVAL_MS;   /* Evaluar de inmediato */
        if (old != mode) {
            ctx->dry_count = 0;
        }
        if (ctx->state == ST_IDLE) {
            set_state(ctx, ST_MONITORING);
        }
        if (!in->outputs_enabled) {
            set_decision(ctx, DEC_OUTPUTS_DISABLED);
        }
    }
    snprintf(msg, len, "Modo %s activo%s", ctrl_mode_name(mode),
             (mode != CM_MANUAL && !in->outputs_enabled) ?
             " (salidas de potencia deshabilitadas: solo decide, no riega)" :
             (old == mode ? " (sin cambios)" : ""));
    return CMD_OK;
}

cmd_result_t irr_cmd_set_auto(irr_ctx_t *ctx, const irr_inputs_t *in, bool enable, char *msg, int len)
{
    return irr_cmd_set_mode(ctx, in, enable ? CM_AUTO : CM_MANUAL, msg, len);
}

cmd_result_t irr_cmd_start_to_target(irr_ctx_t *ctx, const irr_inputs_t *in, float goal, unsigned flags,
                                     char *msg, int len)
{
    const riego_config_t *c = &ctx->cfg;
    bool over = (flags & IRR_OVER_DAILY) != 0;
    if (!require_manual_mode(ctx, msg, len)) {
        return CMD_REJECTED;
    }
    /* goal <= 0: la humedad óptima del cultivo. Si no, la humedad que pidió el usuario (sin pasar la máxima). */
    if (!(goal > 0.0f)) {
        goal = c->hum_target;
    }
    if (goal > c->hum_max) {
        snprintf(msg, len, "La humedad pedida (%.1f%%) supera la maxima permitida (%.1f%%)", goal, c->hum_max);
        return CMD_INVALID;
    }
    if (irr_is_watering(ctx) || ctx->state == ST_INFILTRATION_WAIT || ctx->ev_active) {
        snprintf(msg, len, "Ya hay un riego o evento en curso (%s)", state_name(ctx->state));
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
    if (!in->soil_valid) {
        snprintf(msg, len, "Sin lectura valida del EC-5: no se puede regar hacia una humedad");
        return CMD_REJECTED;
    }
    if (in->soil_vwc >= goal - 0.5f) {
        snprintf(msg, len, "La humedad (%.1f%%) ya esta en el objetivo (%.1f%%)", in->soil_vwc, goal);
        return CMD_REJECTED;
    }
    float remaining = c->max_liters_daily * 1000.0f - ctx->daily_ml;
    if (!over && remaining < c->liters_per_cycle * 1000.0f) {
        snprintf(msg, len, "Excede el maximo diario: quedan %.2f L (autorice el riego extra para continuar)",
                 fmaxf(remaining, 0.0f) / 1000.0f);
        return CMD_REJECTED;
    }
    if (over) {
        remaining = c->max_liters_event * 1000.0f;
    }
    float ml = fminf(c->liters_per_cycle * 1000.0f, fminf(c->max_liters_event * 1000.0f, remaining));
    start_event(ctx, in, EVK_MANUAL_TARGET, ml, goal, DEC_START_TO_TARGET);
    ctx->over_daily = over;
    snprintf(msg, len, "Riego hasta %.1f%% por pulsos: dosis de %.2f L, pausa de %.0f min, nueva lectura, max %d dosis%s",
             goal, ml / 1000.0f, c->infilt_min, (int)c->max_cycles, tank_warning(c, in));
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
        set_decision(ctx, ctx->auto_enabled ? DEC_NONE : DEC_MODE_MANUAL);
        ctx->last_eval_ms = in->now_ms - REEVAL_MS;
    }
    if (!ok) {
        snprintf(msg, len, "%s", why);
        return CMD_REJECTED;
    }
    snprintf(msg, len, "Alarmas borradas; estado %s", state_name(ctx->state));
    return CMD_OK;
}
