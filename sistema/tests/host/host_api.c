/*
 * API para la PC (DLL riego_core) sobre la MISMA lógica pura del firmware:
 * irrigation_logic.c, config_table.c, ia_model.c y app_types.c.
 * La usa el simulador (simulation/simulador_huerto.py) mediante ctypes, para
 * que las decisiones simuladas sean exactamente las del ESP32.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "configuration.h"
#include "ia_model.h"
#include "irrigation_logic.h"

#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API
#endif

#define EVQ 64

typedef struct {
    irr_ctx_t ctx;
    riego_config_t cand;
    ia_model_t ia;
    irr_event_t q[EVQ];
    int qh, qt;
} handle_t;

typedef struct {                /* Foto del estado para Python */
    int state, phase, mode, pump, valve, decision;
    unsigned int alarms;
    int w_reason;
    float w_target_ml, w_delivered_ml, w_flow_lpm;
    unsigned int w_t_start, w_p0;
    int ev_active, ev_kind, ev_cycles, ev_emergency;
    float ev_ml, ev_goal;
    unsigned int infil_t_start;
    int infil_waiting, want_soil;
    float daily_ml;
    double total_ml;
    int soil_interval_s;
    int have_last_event;
} rc_state_t;

typedef struct {
    int status, change_flag;
    unsigned int n_a, out_a, n_b, out_b, model_version;
    float hours_b, mae_a, mae_b, last_err_a, data_version;
    float wa[IA_NA], wb[IA_NB];
} rc_ia_info_t;

static void cb(const irr_event_t *ev, void *user)
{
    handle_t *h = (handle_t *)user;
    int n = (h->qt + 1) % EVQ;
    if (n == h->qh) {
        h->qh = (h->qh + 1) % EVQ;      /* Descarta el más viejo si se llena */
    }
    h->q[h->qt] = *ev;
    h->qt = n;
}

API void *rc_new(void)
{
    handle_t *h = calloc(1, sizeof(handle_t));
    riego_config_t c;
    config_defaults(&c);
    irr_init(&h->ctx, &c, cb, h);
    ia_init(&h->ia, &c);
    return h;
}

API void rc_free(void *p) { free(p); }

API int rc_sizeof_inputs(void) { return (int)sizeof(irr_inputs_t); }
API int rc_sizeof_env(void) { return (int)sizeof(ia_env_t); }
API int rc_sizeof_plan(void) { return (int)sizeof(ia_plan_t); }
API int rc_sizeof_event(void) { return (int)sizeof(irr_event_t); }

API void rc_step(void *p, const irr_inputs_t *in) { irr_step(&((handle_t *)p)->ctx, in); }

API int rc_pop_event(void *p, irr_event_t *out)
{
    handle_t *h = (handle_t *)p;
    if (h->qh == h->qt) {
        return 0;
    }
    *out = h->q[h->qh];
    h->qh = (h->qh + 1) % EVQ;
    return 1;
}

API void rc_get_state(void *p, rc_state_t *o)
{
    irr_ctx_t *c = &((handle_t *)p)->ctx;
    memset(o, 0, sizeof(*o));
    o->state = c->state; o->phase = c->phase; o->mode = c->ctrl_mode;
    o->pump = c->pump_cmd; o->valve = c->valve_cmd; o->decision = c->decision; o->alarms = c->alarms;
    o->w_reason = c->w_reason; o->w_target_ml = c->w_target_ml; o->w_delivered_ml = c->w_delivered_ml;
    o->w_flow_lpm = c->w_flow_lpm; o->w_t_start = c->w_t_start; o->w_p0 = c->w_p0;
    o->ev_active = c->ev_active; o->ev_kind = c->ev_kind; o->ev_cycles = c->ev_cycles; o->ev_emergency = c->ev_emergency;
    o->ev_ml = c->ev_ml; o->ev_goal = c->ev_goal; o->infil_t_start = c->infil_t_start;
    o->infil_waiting = c->infil_waiting_sample; o->want_soil = c->want_soil_sample;
    o->daily_ml = c->daily_ml; o->total_ml = c->total_ml; o->soil_interval_s = (int)c->soil_interval_s;
    o->have_last_event = c->have_last_event;
}

API void rc_set_counters(void *p, float daily_ml, double total_ml, int day_key)
{
    irr_ctx_t *c = &((handle_t *)p)->ctx;
    c->daily_ml = daily_ml;
    c->total_ml = total_ml;
    c->day_key = day_key;
}

API void rc_allow_auto_now(void *p) { ((handle_t *)p)->ctx.have_last_event = false; }

/* -------------------------- Configuración ------------------------------- */
API void rc_cand_begin(void *p) { handle_t *h = (handle_t *)p; h->cand = h->ctx.cfg; }

API int rc_cand_set(void *p, const char *key, const char *val, int remote_only, char *msg, int len)
{
    handle_t *h = (handle_t *)p;
    const config_param_t *pp = config_param_find(key);
    if (!pp) { snprintf(msg, len, "Parametro desconocido: %s", key); return -1; }
    if (remote_only && !pp->remote) { snprintf(msg, len, "%s no se puede cambiar por MQTT", pp->key); return -1; }
    return config_param_set_str(&h->cand, pp, val, msg, (size_t)len);
}

API void rc_cand_set_version(void *p, unsigned int v) { ((handle_t *)p)->cand.profile_version = v; }

API int rc_cand_commit(void *p, char *msg, int len)
{
    handle_t *h = (handle_t *)p;
    if (!config_validate(&h->cand, msg, (size_t)len)) {
        return -1;
    }
    float old_dv = h->ctx.cfg.data_version;
    h->ctx.cfg = h->cand;
    if (fabsf(old_dv - h->cand.data_version) > 0.1f) {
        ia_init(&h->ia, &h->ctx.cfg);
    }
    ia_update_status(&h->ia, &h->ctx.cfg);
    return 0;
}

API int rc_param_count(void) { return config_param_count(); }

API int rc_param_info(int i, char *key, int klen, int *type, int *remote)
{
    const config_param_t *p = config_param_at(i);
    if (!p) return -1;
    snprintf(key, klen, "%s", p->key);
    *type = p->type;
    *remote = p->remote;
    return 0;
}

API void rc_param_format(void *p, int i, char *out, int len)
{
    const config_param_t *pp = config_param_at(i);
    config_param_format(&((handle_t *)p)->ctx.cfg, pp, out, (size_t)len);
}

API float rc_param_float(void *p, const char *key)
{
    const config_param_t *pp = config_param_find(key);
    return pp ? config_param_get_float(&((handle_t *)p)->ctx.cfg, pp) : NAN;
}

/* ----------------------------- Comandos --------------------------------- */
API int rc_cmd_start_manual(void *p, const irr_inputs_t *in, float liters, int force, char *msg, int len)
{ return irr_cmd_start_manual(&((handle_t *)p)->ctx, in, liters, (unsigned)force, msg, len); }
API void rc_cmd_stop(void *p, const irr_inputs_t *in) { irr_cmd_stop(&((handle_t *)p)->ctx, in); }
API int rc_cmd_set_mode(void *p, const irr_inputs_t *in, int mode, char *msg, int len)
{ return irr_cmd_set_mode(&((handle_t *)p)->ctx, in, (ctrl_mode_t)mode, msg, len); }
API int rc_cmd_to_target(void *p, const irr_inputs_t *in, float goal, int flags, char *msg, int len)
{ return irr_cmd_start_to_target(&((handle_t *)p)->ctx, in, goal, (unsigned)flags, msg, len); }
API int rc_cmd_clear(void *p, const irr_inputs_t *in, int alarm, char *msg, int len)
{ return irr_cmd_clear_alarm(&((handle_t *)p)->ctx, in, alarm, msg, len); }
API void rc_raise_alarm(void *p, const irr_inputs_t *in, int alarm) { irr_raise_alarm(&((handle_t *)p)->ctx, in, (alarm_t)alarm); }
API void rc_set_condition(void *p, int alarm, int on) { irr_set_condition(&((handle_t *)p)->ctx, (alarm_t)alarm, on != 0); }

/* ------------------------------ Horarios -------------------------------- */
API int rc_next_window(void *p, int minute) { return irr_next_window_start(&((handle_t *)p)->ctx.cfg, minute); }
API float rc_hours_following(void *p, int minute) { return irr_hours_to_following_window(&((handle_t *)p)->ctx.cfg, minute); }
API int rc_in_window(void *p, int minute) { return irr_in_window(&((handle_t *)p)->ctx.cfg, minute); }
API int rc_in_midday(void *p, int minute) { return irr_in_midday(&((handle_t *)p)->ctx.cfg, minute); }

/* -------------------------------- Nombres ------------------------------- */
API const char *rc_state_name(int s) { return state_name((irr_state_t)s); }
API const char *rc_phase_name(int s) { return phase_name((water_phase_t)s); }
API const char *rc_reason_name(int s) { return reason_name((water_reason_t)s); }
API const char *rc_result_name(int s) { return result_name((water_result_t)s); }
API const char *rc_decision_name(int s) { return decision_name((decision_t)s); }
API const char *rc_decision_text(int s) { return decision_text((decision_t)s); }
API const char *rc_mode_name(int s) { return ctrl_mode_name((ctrl_mode_t)s); }
API int rc_mode_from_name(const char *n) { return ctrl_mode_from_name(n); }
API const char *rc_kind_name(int s) { return event_kind_name((event_kind_t)s); }
API int rc_alarm_count(void) { return ALM__COUNT; }
API const char *rc_alarm_code(int a) { const alarm_info_t *i = alarm_info((alarm_t)a); return i ? i->code : "?"; }
API const char *rc_alarm_text(int a) { const alarm_info_t *i = alarm_info((alarm_t)a); return i ? i->text : "?"; }
API const char *rc_alarm_sev(int a) { const alarm_info_t *i = alarm_info((alarm_t)a); return i ? severity_name(i->sev) : "?"; }
API int rc_alarm_latched(int a) { const alarm_info_t *i = alarm_info((alarm_t)a); return i ? i->latched : 0; }
API int rc_alarm_from_name(const char *n) { return alarm_from_name(n); }

/* ---------------------------------- IA ---------------------------------- */
API float rc_vpd(float t, float rh) { return vpd_kpa(t, rh); }
API void rc_ia_reset(void *p) { handle_t *h = (handle_t *)p; ia_init(&h->ia, &h->ctx.cfg); }
API float rc_ia_predict_response(void *p, float L, float v0, int env, float t, float rh, float hs)
{ return ia_predict_response(&((handle_t *)p)->ia, L, v0, env != 0, t, rh, hs); }
API int rc_ia_learn_response(void *p, float L, float v0, int env, float t, float rh, float hs, float dv, float *pred)
{
    handle_t *h = (handle_t *)p;
    int r = ia_learn_response(&h->ia, L, v0, env != 0, t, rh, hs, dv, pred);
    ia_update_status(&h->ia, &h->ctx.cfg);
    return r;
}
API int rc_ia_learn_drying(void *p, float v, float t, float rh, int env, float kc, float et0, float hour, float rate, float *pred)
{
    handle_t *h = (handle_t *)p;
    int r = ia_learn_drying(&h->ia, v, t, rh, env != 0, kc, et0, hour, rate, pred);
    ia_update_status(&h->ia, &h->ctx.cfg);
    return r;
}
API void rc_ia_plan(void *p, const ia_env_t *env, float vwc, float horizon, ia_plan_t *out)
{ handle_t *h = (handle_t *)p; ia_plan(&h->ia, env, &h->ctx.cfg, vwc, horizon, out); }
API float rc_ia_correction(void *p, float vwc, float goal, int env, float t, float rh)
{ handle_t *h = (handle_t *)p; return ia_correction_liters(&h->ia, &h->ctx.cfg, vwc, goal, env != 0, t, rh); }
API const char *rc_ia_status_name(int s) { return ia_status_name((ia_status_t)s); }
API const char *rc_ia_plan_name(int s) { return ia_plan_name((ia_plan_code_t)s); }
API void rc_ia_info(void *p, rc_ia_info_t *o)
{
    ia_model_t *m = &((handle_t *)p)->ia;
    o->status = m->status; o->change_flag = m->change_flag;
    o->n_a = m->a.n; o->out_a = m->a.outliers; o->n_b = m->b.n; o->out_b = m->b.outliers;
    o->model_version = m->model_version; o->hours_b = m->hours_b;
    o->mae_a = ia_mae_a(m); o->mae_b = ia_mae_b(m); o->last_err_a = m->last_err_a; o->data_version = m->data_version;
    for (int i = 0; i < IA_NA; i++) o->wa[i] = m->a.w[i];
    for (int i = 0; i < IA_NB; i++) o->wb[i] = m->b.w[i];
}
/* Guardar / cargar el modelo (para que el simulador no pierda lo aprendido) */
API int rc_ia_size(void) { return (int)sizeof(ia_model_t); }
API void rc_ia_export(void *p, void *buf) { memcpy(buf, &((handle_t *)p)->ia, sizeof(ia_model_t)); }
API int rc_ia_import(void *p, const void *buf)
{
    handle_t *h = (handle_t *)p;
    ia_model_t tmp;
    memcpy(&tmp, buf, sizeof(tmp));
    if (!ia_check(&tmp)) return -1;
    h->ia = tmp;
    ia_update_status(&h->ia, &h->ctx.cfg);
    return 0;
}
