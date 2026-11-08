#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_timer.h"
#include "esp_task_wdt.h"
#include "esp_system.h"
#include "esp_heap_caps.h"
#include "esp_idf_version.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "cJSON.h"

#include "actuators.h"
#include "app_version.h"
#include "configuration.h"
#include "flow_sensor.h"
#include "ia_model.h"
#include "irrigation_logic.h"
#include "mqtt_manager.h"
#include "net_config.h"
#include "safety.h"
#include "sensors.h"
#include "simulation.h"
#include "storage.h"
#include "timekeeping.h"
#include "weather.h"
#include "wifi_manager.h"
#include "wdt_diag.h"
#include "irrigation_controller.h"

static const char *TAG = "control";

#define LOOP_MS             20
#define STATE_PERIOD_MS     30000
#define STATE_FAST_MS       1000
#define IA_PERIOD_MS        60000
#define PLAN_PERIOD_MS      5000
#define DIAG_PERIOD_MS      300000
#define BUF_PERIOD_MS       600000      /* Muestra del búfer sin conexión cada 10 min */
#define BUF_MAX             144         /* 24 h de muestras                           */
#define RISE_COOLDOWN_MS    (2u * 3600u * 1000u)
#define RISE_WINDOW_MS      (3u * 3600u * 1000u)    /* Ventana del mínimo de referencia */

static QueueHandle_t s_q;
static irr_ctx_t s_ctx;
static irr_inputs_t s_in;
static persist_t s_p;
static riego_config_t s_cfg;
static uint32_t s_cfg_gen;
static bool s_log = true;
static bool s_config_was_reset;
static bool s_reboot_during_watering;

static uint32_t s_virt_ms;
static int64_t s_last_us;
static float s_sim_acc;

static bool s_state_dirty = true;
static uint32_t s_last_state_ms, s_last_tel_ms, s_last_ia_ms, s_last_plan_ms, s_last_diag_ms, s_last_buf_ms;
static uint32_t s_tel_pulses;
static int64_t s_tel_us;
static float s_tel_lpm;
static uint32_t s_tel_seq;

/* ------------------------------- IA ------------------------------------- */
static ia_model_t s_ia;
static ia_plan_t s_plan;
static bool s_plan_uses_fc;
static bool s_ia_dirty = true;
static uint8_t s_b_updates_unsaved;
static float s_pred_dv;                 /* Predicción del riego en curso */
static char s_event_id[40];

typedef struct {                        /* Observación pendiente del modelo A */
    bool active;
    float liters, v0, temp, rh, hours_since, dv_pred;
    bool env;
    uint32_t t_end;
    uint32_t seq_ref;
    char event_id[40];
} pend_a_t;
static pend_a_t s_pend;

typedef struct {                        /* Ancla para aprender el secado (modelo B) */
    bool active;
    float v;
    uint32_t t;
    float temp, rh;
    bool env;
} anchor_b_t;
static anchor_b_t s_anchor;
static uint32_t s_last_water_end_ms;
static bool s_have_water_end;
static float s_last_pred_next_h = NAN;

/* Aumento de humedad no explicado (lluvia / riego externo / sensor) */
static float s_rise_ref = NAN;
static uint32_t s_rise_ref_ms;
static int s_rise_pending;
static uint32_t s_rise_last_ms;
static bool s_rise_have;
static uint32_t s_last_soil_seq_seen;

/* Pronóstico */
static weather_t s_wx;
static uint32_t s_wx_published;

/* Búfer sin conexión (no se escribe en NVS) */
typedef struct {
    uint32_t ts;
    int16_t vwc_x10, temp_x10, rh_x10, tank_x10;
    uint16_t today_cl;                  /* centilitros */
    uint8_t mode, state;
} buf_entry_t;
static buf_entry_t s_buf[BUF_MAX];
static int s_buf_head, s_buf_count;
static bool s_was_connected;

/* ----------------------------- Utilidades -------------------------------- */

static uint32_t real_ms(void)
{
    return (uint32_t)(esp_timer_get_time() / 1000);
}

static void add_num(cJSON *o, const char *k, float v, int dec)
{
    if (!isfinite(v)) {
        cJSON_AddNullToObject(o, k);
    } else {
        double p = pow(10, dec);
        cJSON_AddNumberToObject(o, k, round((double)v * p) / p);
    }
}

static void add_ts(cJSON *o)
{
    uint32_t e = time_epoch();
    if (e) {
        cJSON_AddNumberToObject(o, "ts", e);
    } else {
        cJSON_AddNullToObject(o, "ts");
    }
    cJSON_AddNumberToObject(o, "uptime_s", real_ms() / 1000);
    cJSON_AddStringToObject(o, "device", mqtt_manager_device());
    cJSON_AddBoolToObject(o, "simulated", sim()->active);
}

static void publish_json(const char *sub, cJSON *o, int qos, bool retain)
{
    char *s = cJSON_PrintUnformatted(o);
    if (s) {
        mqtt_publish(sub, s, qos, retain);
        cJSON_free(s);
    }
    cJSON_Delete(o);
}

static void next_window_str(char *out, size_t len)
{
    int m = s_in.time_valid ? s_in.minute_of_day : -1;
    int nw = irr_next_window_start(&s_cfg, m);
    if (nw < 0) {
        snprintf(out, len, "SIN_HORARIOS");
    } else {
        config_format_time((float)nw, out, len);
    }
}

static float hour_of_day(void)
{
    return s_in.minute_of_day >= 0 ? (float)s_in.minute_of_day / 60.0f : 12.0f;
}

/* ------------------------------ Reportes JSON ---------------------------- */

static cJSON *build_telemetry(void)
{
    sensor_snapshot_t sn;
    sensors_get(&sn);
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    cJSON_AddNumberToObject(o, "seq", ++s_tel_seq);
    cJSON_AddNumberToObject(o, "boot", s_p.boot_count);
    cJSON_AddStringToObject(o, "mode", ctrl_mode_name(s_ctx.ctrl_mode));
    cJSON_AddStringToObject(o, "state", state_name(s_ctx.state));
    cJSON_AddStringToObject(o, "crop", s_cfg.crop_id);
    cJSON_AddStringToObject(o, "stage", s_cfg.stage);
    cJSON_AddNumberToObject(o, "data_version", s_cfg.data_version);

    cJSON *soil = cJSON_AddObjectToObject(o, "soil");
    cJSON_AddBoolToObject(soil, "valid", sn.soil.valid);
    add_num(soil, "vwc_pct", sn.soil.valid ? sn.soil.vwc_pct : NAN, 1);
    cJSON_AddNumberToObject(soil, "mv", sn.soil.mv);
    cJSON_AddBoolToObject(soil, "in_cal_range", sn.soil.in_cal_range);
    cJSON_AddStringToObject(soil, "status", sn.soil.status ? sn.soil.status : "SIN_LECTURA");
    add_num(soil, "vwc_raw", sn.soil.vwc_raw, 1);
    if (sn.soil.filter) {
        cJSON_AddStringToObject(soil, "filter", sn.soil.filter);
    }
    cJSON_AddNumberToObject(soil, "age_s", sn.soil_age_s);

    cJSON *tank = cJSON_AddObjectToObject(o, "tank");
    cJSON_AddBoolToObject(tank, "valid", sn.tank.valid);
    cJSON_AddBoolToObject(tank, "calibrated", sn.tank.calibrated);
    add_num(tank, "distance_cm", sn.tank.valid ? sn.tank.distance_cm : NAN, 1);
    add_num(tank, "level_pct", (sn.tank.valid && sn.tank.calibrated) ? sn.tank.level_pct : NAN, 0);
    cJSON_AddBoolToObject(tank, "below_min", (s_ctx.alarms & ALARM_BIT(ALM_TANK_LOW)) != 0);
    cJSON_AddStringToObject(tank, "status", sn.tank.status ? sn.tank.status : "SIN_LECTURA");
    add_num(tank, "distance_raw", sn.tank.distance_raw, 1);
    if (sn.tank.filter) {
        cJSON_AddStringToObject(tank, "filter", sn.tank.filter);
    }

    cJSON *env = cJSON_AddObjectToObject(o, "env");
    cJSON_AddBoolToObject(env, "valid", sn.env_valid);
    add_num(env, "temp_c", sn.env_valid ? sn.temp_c : NAN, 1);
    add_num(env, "rh_pct", sn.env_valid ? sn.rh_pct : NAN, 1);
    add_num(env, "vpd_kpa", sn.env_valid ? vpd_kpa(sn.temp_c, sn.rh_pct) : NAN, 2);
    if (sn.env_last_valid_epoch) {
        cJSON_AddNumberToObject(env, "last_valid_ts", sn.env_last_valid_epoch);
    } else {
        cJSON_AddNullToObject(env, "last_valid_ts");
    }
    cJSON_AddStringToObject(env, "status", sn.env_valid ? (sim()->active ? "SIMULADO" : "OK") : "SIN_LECTURA");

    cJSON *fl = cJSON_AddObjectToObject(o, "flow");
    add_num(fl, "lpm", irr_is_watering(&s_ctx) ? s_ctx.w_flow_lpm : s_tel_lpm, 2);
    add_num(fl, "session_l", irr_is_watering(&s_ctx) ? s_ctx.w_delivered_ml / 1000.0f : 0.0f, 3);
    add_num(fl, "today_l", s_ctx.daily_ml / 1000.0f, 3);
    add_num(fl, "total_l", (float)(s_ctx.total_ml / 1000.0), 3);
    cJSON_AddNumberToObject(fl, "pulses", s_in.flow_pulses);
    add_num(fl, "pulses_per_liter", s_cfg.pulses_per_liter, 1);
    return o;
}

static cJSON *build_state(void)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    cJSON_AddStringToObject(o, "fw", APP_VERSION);
    cJSON_AddStringToObject(o, "state", state_name(s_ctx.state));
    cJSON_AddStringToObject(o, "phase", phase_name(s_ctx.phase));
    cJSON_AddStringToObject(o, "mode", ctrl_mode_name(s_ctx.ctrl_mode));
    cJSON_AddStringToObject(o, "install_profile", s_cfg.mode == MODE_B_FINAL ? "B" : "A");
    cJSON_AddBoolToObject(o, "auto_enabled", s_ctx.auto_enabled);
    cJSON_AddBoolToObject(o, "power_outputs", s_cfg.power_enabled != 0);
    cJSON_AddBoolToObject(o, "pump", sim()->active ? s_ctx.pump_cmd : actuators_pump_physical());
    cJSON_AddBoolToObject(o, "valve", sim()->active ? s_ctx.valve_cmd : actuators_valve_physical());
    cJSON_AddBoolToObject(o, "pump_cmd", s_ctx.pump_cmd);
    cJSON_AddBoolToObject(o, "valve_cmd", s_ctx.valve_cmd);
    cJSON_AddBoolToObject(o, "emergency_latch", actuators_latched());
    cJSON_AddStringToObject(o, "ia_status", ia_status_name((ia_status_t)s_ia.status));
    cJSON_AddStringToObject(o, "crop", s_cfg.crop_id);
    cJSON_AddStringToObject(o, "crop_name", s_cfg.crop_name);
    cJSON_AddStringToObject(o, "stage", s_cfg.stage);
    cJSON_AddNumberToObject(o, "profile_version", s_cfg.profile_version);

    bool w = irr_is_watering(&s_ctx);
    cJSON *wt = cJSON_AddObjectToObject(o, "watering");
    cJSON_AddBoolToObject(wt, "active", w);
    cJSON_AddStringToObject(wt, "type", w ? reason_name(s_ctx.w_reason) : "NONE");
    cJSON_AddStringToObject(wt, "event_id", w ? s_event_id : "");
    add_num(wt, "target_l", w ? s_ctx.w_target_ml / 1000.0f : 0.0f, 3);
    add_num(wt, "delivered_l", w ? s_ctx.w_delivered_ml / 1000.0f : 0.0f, 3);
    add_num(wt, "remaining_l", w ? fmaxf(0, s_ctx.w_target_ml - s_ctx.w_delivered_ml) / 1000.0f : 0.0f, 3);
    add_num(wt, "progress_pct", (w && s_ctx.w_target_ml > 0) ?
            fminf(100.0f, 100.0f * s_ctx.w_delivered_ml / s_ctx.w_target_ml) : 0.0f, 0);
    cJSON_AddNumberToObject(wt, "elapsed_s", w ? (s_in.now_ms - s_ctx.w_t_start) / 1000 : 0);
    add_num(wt, "flow_lpm", w ? s_ctx.w_flow_lpm : 0.0f, 2);
    cJSON_AddNumberToObject(wt, "pulses", w ? (double)(s_in.flow_pulses - s_ctx.w_p0) : 0);

    cJSON *ev = cJSON_AddObjectToObject(o, "event");
    cJSON_AddBoolToObject(ev, "active", s_ctx.ev_active);
    cJSON_AddStringToObject(ev, "kind", event_kind_name(s_ctx.ev_kind));
    cJSON_AddBoolToObject(ev, "emergency", s_ctx.ev_active && s_ctx.ev_emergency);
    cJSON_AddNumberToObject(ev, "cycles", s_ctx.ev_cycles);
    add_num(ev, "liters", s_ctx.ev_ml / 1000.0f, 3);
    add_num(ev, "goal_vwc", s_ctx.ev_active ? s_ctx.ev_goal : NAN, 1);
    if (s_ctx.state == ST_INFILTRATION_WAIT && !s_ctx.infil_waiting_sample) {
        uint32_t wait = (uint32_t)(s_cfg.infilt_min * 60000.0f);
        uint32_t el = s_in.now_ms - s_ctx.infil_t_start;
        uint32_t speed = (sim()->active && sim()->speed) ? sim()->speed : 1;
        cJSON_AddNumberToObject(ev, "infiltration_remaining_s", el < wait ? (wait - el) / 1000 / speed : 0);
    } else {
        cJSON_AddNumberToObject(ev, "infiltration_remaining_s", 0);
    }

    cJSON *al = cJSON_AddArrayToObject(o, "alarms");
    for (int a = 0; a < ALM__COUNT; a++) {
        if (s_ctx.alarms & ALARM_BIT(a)) {
            cJSON_AddItemToArray(al, cJSON_CreateString(alarm_info((alarm_t)a)->code));
        }
    }
    cJSON *dc = cJSON_AddObjectToObject(o, "decision");
    cJSON_AddStringToObject(dc, "code", decision_name(s_ctx.decision));
    cJSON_AddStringToObject(dc, "text", decision_text(s_ctx.decision));
    char nw[16];
    next_window_str(nw, sizeof(nw));
    cJSON_AddStringToObject(o, "next_window", nw);
    cJSON_AddBoolToObject(o, "time_valid", s_in.time_valid);
    char now[24];
    time_format_now(now, sizeof(now));
    cJSON_AddStringToObject(o, "local_time", now);
    cJSON_AddBoolToObject(o, "wifi", wifi_manager_connected());
    cJSON_AddBoolToObject(o, "mqtt", mqtt_manager_connected());
    cJSON_AddNumberToObject(o, "rssi", wifi_manager_rssi());
    cJSON_AddNumberToObject(o, "free_heap", (double)esp_get_free_heap_size());
    cJSON_AddBoolToObject(o, "rain_expected", s_in.rain_expected);
    return o;
}

static cJSON *build_config(void)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    cJSON_AddNumberToObject(o, "profile_version", s_cfg.profile_version);
    cJSON *p = cJSON_AddObjectToObject(o, "params");
    for (int i = 0; i < config_param_count(); i++) {
        const config_param_t *pp = config_param_at(i);
        char buf[48];
        switch (pp->type) {
        case PT_BOOL:
            cJSON_AddBoolToObject(p, pp->key, config_param_get_float(&s_cfg, pp) != 0.0f);
            break;
        case PT_TIME:
        case PT_STRING:
            config_param_format(&s_cfg, pp, buf, sizeof(buf));
            cJSON_AddStringToObject(p, pp->key, buf);
            break;
        default:
            add_num(p, pp->key, config_param_get_float(&s_cfg, pp), pp->decimals);
            break;
        }
    }
    cJSON_AddBoolToObject(o, "tank_calibrated", config_tank_calibrated(&s_cfg));
    cJSON_AddBoolToObject(o, "flow_calibrated", false);     /* 450 p/L provisional: sin contraste físico */
    return o;
}

static cJSON *build_decision(void)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    cJSON_AddStringToObject(o, "code", decision_name(s_ctx.decision));
    cJSON_AddStringToObject(o, "text", decision_text(s_ctx.decision));
    cJSON_AddStringToObject(o, "mode", ctrl_mode_name(s_ctx.ctrl_mode));
    add_num(o, "soil_vwc", s_in.soil_valid ? s_in.soil_vwc : NAN, 1);
    add_num(o, "hum_critical", s_cfg.hum_critical, 1);
    add_num(o, "hum_min", s_cfg.hum_min, 1);
    add_num(o, "hum_target", s_cfg.hum_target, 1);
    add_num(o, "hum_reserve", s_cfg.hum_reserve, 1);
    add_num(o, "hum_max", s_cfg.hum_max, 1);
    char nw[16];
    next_window_str(nw, sizeof(nw));
    cJSON_AddStringToObject(o, "next_window", nw);
    cJSON_AddBoolToObject(o, "in_window", s_in.time_valid && irr_in_window(&s_cfg, s_in.minute_of_day));
    cJSON_AddBoolToObject(o, "in_midday", s_in.time_valid && irr_in_midday(&s_cfg, s_in.minute_of_day));
    cJSON_AddBoolToObject(o, "rain_expected", s_in.rain_expected);
    cJSON_AddBoolToObject(o, "ia_active", s_in.ia_active);
    cJSON_AddStringToObject(o, "state", state_name(s_ctx.state));
    return o;
}

static cJSON *build_ia(void)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    cJSON_AddStringToObject(o, "status", ia_status_name((ia_status_t)s_ia.status));
    cJSON_AddBoolToObject(o, "mode_ia_selected", s_ctx.ctrl_mode == CM_IA);
    cJSON_AddBoolToObject(o, "controls_watering", s_ctx.ctrl_mode == CM_IA && s_ia.status == IA_ACTIVE);
    cJSON_AddStringToObject(o, "fallback", (s_ctx.ctrl_mode == CM_IA && s_ia.status != IA_ACTIVE) ?
                            "AUTOMATICO_CONSERVADOR" : "NINGUNO");
    cJSON_AddNumberToObject(o, "model_version", s_ia.model_version);
    cJSON_AddNumberToObject(o, "data_version", s_ia.data_version);
    cJSON_AddNumberToObject(o, "events_learned", s_ia.a.n);
    cJSON_AddNumberToObject(o, "events_outliers", s_ia.a.outliers);
    add_num(o, "drying_hours_learned", s_ia.hours_b, 0);
    cJSON_AddNumberToObject(o, "drying_outliers", s_ia.b.outliers);
    add_num(o, "mae_response_pp", ia_mae_a(&s_ia), 2);
    add_num(o, "mae_drying_pph", ia_mae_b(&s_ia), 3);
    add_num(o, "last_response_error_pp", s_ia.a.n ? s_ia.last_err_a : NAN, 2);
    cJSON_AddBoolToObject(o, "change_detected", s_ia.change_flag != 0);
    add_num(o, "min_events", s_cfg.ia_min_events, 0);
    add_num(o, "min_hours", s_cfg.ia_min_hours, 0);
    add_num(o, "tolerance_pp", s_cfg.ia_tol_pp, 1);
    cJSON *wa = cJSON_AddArrayToObject(o, "coef_response");
    for (int i = 0; i < IA_NA; i++) {
        cJSON_AddItemToArray(wa, cJSON_CreateNumber(round(s_ia.a.w[i] * 1000.0) / 1000.0));
    }
    cJSON *wb = cJSON_AddArrayToObject(o, "coef_drying");
    for (int i = 0; i < IA_NB; i++) {
        cJSON_AddItemToArray(wb, cJSON_CreateNumber(round(s_ia.b.w[i] * 10000.0) / 10000.0));
    }
    cJSON *pl = cJSON_AddObjectToObject(o, "plan");
    cJSON_AddBoolToObject(pl, "valid", s_plan.valid);
    cJSON_AddStringToObject(pl, "code", ia_plan_name(s_plan.code));
    add_num(pl, "vwc_now", s_plan.valid ? s_plan.vwc_now : NAN, 1);
    add_num(pl, "horizon_h", s_plan.horizon_h, 1);
    add_num(pl, "loss_pred_pp", s_plan.valid ? s_plan.loss_pred : NAN, 2);
    add_num(pl, "vwc_end_no_water", s_plan.valid ? s_plan.vwc_end_no_water : NAN, 1);
    add_num(pl, "goal_vwc", s_plan.valid ? s_plan.goal : NAN, 1);
    add_num(pl, "liters", s_plan.valid ? s_plan.liters : NAN, 2);
    add_num(pl, "gain_pp_per_l", s_plan.valid ? s_plan.gain_per_l : NAN, 2);
    add_num(pl, "rate_now_pph", s_plan.valid ? s_plan.rate_now : NAN, 3);
    add_num(pl, "autonomy_h", s_plan.valid ? s_plan.autonomy_h : NAN, 1);
    cJSON_AddBoolToObject(pl, "uses_forecast", s_plan_uses_fc);
    add_num(pl, "pred_next_hour_vwc", s_last_pred_next_h, 2);
    cJSON *tr = cJSON_AddArrayToObject(pl, "trajectory");
    if (s_plan.valid) {
        for (int i = 0; i < IA_TRAJ; i++) {
            cJSON_AddItemToArray(tr, cJSON_CreateNumber(round(s_plan.traj[i] * 100.0) / 100.0));
        }
    }
    cJSON *vars = cJSON_AddArrayToObject(o, "variables");
    const char *const V[] = { "humedad_suelo", "litros", "temperatura", "humedad_relativa", "VPD",
                              "ET0_pronostico", "Kc_etapa", "hora_del_dia", "horas_desde_riego" };
    for (size_t i = 0; i < sizeof(V) / sizeof(V[0]); i++) {
        cJSON_AddItemToArray(vars, cJSON_CreateString(V[i]));
    }
    return o;
}

static cJSON *build_weather(void)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    uint32_t now = time_epoch();
    cJSON_AddStringToObject(o, "source", "open-meteo.com (modelo meteorologico, no medicion local)");
    cJSON_AddBoolToObject(o, "valid", s_wx.valid);
    cJSON_AddBoolToObject(o, "fresh", weather_fresh(&s_wx, now));
    uint32_t age = weather_age_s(&s_wx, now);
    if (age != UINT32_MAX) {
        cJSON_AddNumberToObject(o, "age_s", age);
        cJSON_AddNumberToObject(o, "fetch_ts", s_wx.fetch_epoch);
    } else {
        cJSON_AddNullToObject(o, "age_s");
        cJSON_AddNullToObject(o, "fetch_ts");
    }
    add_num(o, "temp_c", s_wx.valid ? s_wx.cur_temp : NAN, 1);
    add_num(o, "rh_pct", s_wx.valid ? s_wx.cur_rh : NAN, 0);
    add_num(o, "precip_mm", s_wx.valid ? s_wx.cur_precip : NAN, 1);
    add_num(o, "past6h_precip_mm", s_wx.valid ? s_wx.past_precip_6h : NAN, 1);
    add_num(o, "next6h_precip_mm", s_wx.valid ? s_wx.next6_precip : NAN, 1);
    add_num(o, "next6h_prob_max_pct", s_wx.valid ? s_wx.next6_pprob_max : NAN, 0);
    add_num(o, "et0_24h_mm", s_wx.valid ? s_wx.et0_24h : NAN, 2);
    cJSON_AddBoolToObject(o, "rain_expected", s_in.rain_expected);
    cJSON_AddNumberToObject(o, "ok_count", s_wx.ok_count);
    cJSON_AddNumberToObject(o, "fail_count", s_wx.fail_count);
    cJSON_AddStringToObject(o, "last_error", s_wx.last_error);
    add_num(o, "lat", s_cfg.lat, 4);
    add_num(o, "lon", s_cfg.lon, 4);
    return o;
}

static cJSON *build_diag(void)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    wifi_diag_t d;
    wifi_manager_diag(&d);
    cJSON_AddStringToObject(o, "fw", APP_VERSION);
    cJSON_AddStringToObject(o, "idf", esp_get_idf_version());
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    char ms[20];
    snprintf(ms, sizeof(ms), "%02x:%02x:%02x:%02x:%02x:%02x", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    cJSON_AddStringToObject(o, "mac", ms);
    net_config_t nc;
    net_config_get(&nc);
    cJSON_AddStringToObject(o, "env", nc.env_name);
    cJSON_AddStringToObject(o, "base_topic", nc.base_topic);
    cJSON *w = cJSON_AddObjectToObject(o, "wifi");
    cJSON_AddBoolToObject(w, "connected", d.connected);
    cJSON_AddStringToObject(w, "network", d.slot);
    cJSON_AddStringToObject(w, "ssid", d.ssid);
    cJSON_AddStringToObject(w, "ip", d.ip);
    cJSON_AddNumberToObject(w, "rssi", d.rssi);
    cJSON_AddNumberToObject(w, "channel", d.channel);
    cJSON_AddNumberToObject(w, "last_reason", d.last_reason);
    cJSON_AddStringToObject(w, "last_reason_text", wifi_reason_text(d.last_reason));
    cJSON_AddNumberToObject(w, "reconnects", d.reconnects);
    cJSON *n = cJSON_AddArrayToObject(w, "saved_networks");
    for (int i = 0; i < NET_SLOTS; i++) {
        cJSON *e = cJSON_CreateObject();
        cJSON_AddStringToObject(e, "name", nc.slot[i].name);
        cJSON_AddStringToObject(e, "ssid", nc.slot[i].ssid);
        cJSON_AddBoolToObject(e, "enabled", nc.slot[i].enabled);
        cJSON_AddBoolToObject(e, "preferred", i == nc.preferred);
        cJSON_AddItemToArray(n, e);     /* Nunca se publica la contraseña */
    }
    cJSON *m = cJSON_AddObjectToObject(o, "mqtt");
    cJSON_AddStringToObject(m, "broker", mqtt_manager_broker());
    cJSON_AddStringToObject(m, "client_id", mqtt_manager_client_id());
    cJSON_AddBoolToObject(m, "connected", mqtt_manager_connected());
    cJSON_AddNumberToObject(m, "connects", mqtt_manager_connect_count());
    cJSON_AddStringToObject(m, "broker_change", mqtt_manager_broker_change_state());
    cJSON_AddNumberToObject(o, "free_heap", (double)esp_get_free_heap_size());
    cJSON_AddNumberToObject(o, "min_free_heap", (double)esp_get_minimum_free_heap_size());
    cJSON_AddNumberToObject(o, "reset_reason", (int)esp_reset_reason());
    cJSON_AddNumberToObject(o, "uptime_s", (double)(esp_timer_get_time() / 1000000));
    cJSON_AddNumberToObject(o, "boot_count", s_p.boot_count);
    cJSON_AddNumberToObject(o, "mqtt_dropped", mqtt_manager_dropped());
    if (wdt_diag_last()[0]) {
        cJSON_AddStringToObject(o, "last_wdt", wdt_diag_last());
    }
    cJSON_AddNumberToObject(o, "offline_buffer", s_buf_count);
    return o;
}

static cJSON *hist_to_json(const hist_entry_t *h)
{
    cJSON *e = cJSON_CreateObject();
    if (h->epoch) {
        cJSON_AddNumberToObject(e, "ts", h->epoch);
    } else {
        cJSON_AddNullToObject(e, "ts");
    }
    cJSON_AddStringToObject(e, "reason", reason_name((water_reason_t)h->reason));
    cJSON_AddStringToObject(e, "result", result_name((water_result_t)h->result));
    add_num(e, "liters", h->ml / 1000.0f, 3);
    cJSON_AddNumberToObject(e, "duration_s", h->duration_s);
    cJSON_AddNumberToObject(e, "pulses", h->pulses);
    add_num(e, "vwc_before", h->vwc_before_x10 <= -1000 ? NAN : h->vwc_before_x10 / 10.0f, 1);
    add_num(e, "vwc_after", h->vwc_after_x10 <= -1000 ? NAN : h->vwc_after_x10 / 10.0f, 1);
    return e;
}

static cJSON *build_history(void)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    cJSON *arr = cJSON_AddArrayToObject(o, "entries");
    for (int i = 0; i < s_p.hist_count; i++) {
        cJSON_AddItemToArray(arr, hist_to_json(storage_hist_get(&s_p, i)));
    }
    return o;
}

/* ------------------------------ Consola ---------------------------------- */

static void print_status(void)
{
    sensor_snapshot_t sn;
    sensors_get(&sn);
    char now[24], nw[16];
    time_format_now(now, sizeof(now));
    next_window_str(nw, sizeof(nw));
    printf("---------------- ESTADO (%s) ----------------\n", APP_VERSION);
    printf("Hora: %s | Perfil %s | Potencia %s | Simulacion %s\n", now,
           s_cfg.mode == MODE_B_FINAL ? "B (instalacion)" : "A (pruebas)",
           s_cfg.power_enabled ? "HABILITADA" : "DESHABILITADA", sim()->active ? "SI" : "NO");
    printf("MODO: %s | Estado: %s (%s) | IA: %s\n", ctrl_mode_name(s_ctx.ctrl_mode), state_name(s_ctx.state),
           phase_name(s_ctx.phase), ia_status_name((ia_status_t)s_ia.status));
    printf("Cultivo: %s / etapa %s (perfil v%lu)\n", s_cfg.crop_name, s_cfg.stage, (unsigned long)s_cfg.profile_version);
    printf("Bomba: logica %s / fisica %s | Valvula: logica %s / fisica %s | Latch: %s\n",
           s_ctx.pump_cmd ? "ON" : "OFF", actuators_pump_physical() ? "ON" : "OFF",
           s_ctx.valve_cmd ? "ON" : "OFF", actuators_valve_physical() ? "ON" : "OFF",
           actuators_latched() ? "SI" : "NO");
    printf("Suelo: %s %.1f %%VWC (%d mV, %s)\n", sn.soil.valid ? "OK" : "INVALIDO",
           sn.soil.vwc_pct, sn.soil.mv, sn.soil.status ? sn.soil.status : "-");
    printf("Tinaco: %s dist %.1f cm nivel %s (%s)\n", sn.tank.valid ? "OK" : "INVALIDO",
           sn.tank.distance_cm, sn.tank.calibrated ? "calibrado" : "SIN CALIBRAR",
           sn.tank.status ? sn.tank.status : "-");
    printf("Ambiente: %s %.1f C %.1f %%HR\n", sn.env_valid ? "OK" : "INVALIDO", sn.temp_c, sn.rh_pct);
    printf("Flujo: %.2f L/min | Hoy %.3f L | Total %.3f L | Pulsos %lu\n",
           irr_is_watering(&s_ctx) ? s_ctx.w_flow_lpm : s_tel_lpm, s_ctx.daily_ml / 1000.0f,
           s_ctx.total_ml / 1000.0, (unsigned long)s_in.flow_pulses);
    printf("Humedad: emergencia %.1f / minima %.1f / objetivo %.1f / reserva %.1f / maxima %.1f %%VWC\n",
           s_cfg.hum_critical, s_cfg.hum_min, s_cfg.hum_target, s_cfg.hum_reserve, s_cfg.hum_max);
    printf("Decision: %s - %s | Proximo horario: %s | Lluvia prevista: %s\n", decision_name(s_ctx.decision),
           decision_text(s_ctx.decision), nw, s_in.rain_expected ? "SI" : "NO");
    printf("Alarmas:");
    bool any = false;
    for (int a = 0; a < ALM__COUNT; a++) {
        if (s_ctx.alarms & ALARM_BIT(a)) {
            printf(" %s", alarm_info((alarm_t)a)->code);
            any = true;
        }
    }
    printf("%s\n", any ? "" : " ninguna");
    wifi_diag_t d;
    wifi_manager_diag(&d);
    printf("Red: Wi-Fi %s %s %s | MQTT %s (%s) | topic %s\n",
           wifi_manager_configured() ? (d.connected ? "CONECTADO" : "DESCONECTADO") : "SIN CONFIGURAR",
           d.ssid, d.ip, mqtt_manager_configured() ? (mqtt_manager_connected() ? "CONECTADO" : "DESCONECTADO") :
           "SIN CONFIGURAR", mqtt_manager_broker(), mqtt_manager_base());
    printf("----------------------------------------\n");
}

static void print_config(void)
{
    printf("------------- CONFIGURACION -------------\n");
    for (int i = 0; i < config_param_count(); i++) {
        const config_param_t *p = config_param_at(i);
        char buf[48];
        config_param_format(&s_cfg, p, buf, sizeof(buf));
        printf("%-18s = %-12s %-6s %s%s\n", p->key, buf, p->unit, p->desc, p->remote ? "" : " [solo consola]");
    }
    printf("-----------------------------------------\n");
}

static void print_history(void)
{
    printf("-------------- HISTORIAL (mas reciente primero) --------------\n");
    for (int i = 0; i < s_p.hist_count; i++) {
        const hist_entry_t *h = storage_hist_get(&s_p, i);
        printf("%2d) ts=%lu %-13s %-12s %.3f L %u s antes=%.1f despues=%.1f\n", i + 1,
               (unsigned long)h->epoch, reason_name((water_reason_t)h->reason),
               result_name((water_result_t)h->result), h->ml / 1000.0f, h->duration_s,
               h->vwc_before_x10 / 10.0f, h->vwc_after_x10 / 10.0f);
    }
    if (s_p.hist_count == 0) {
        printf("(sin riegos registrados)\n");
    }
}

static void print_ia(void)
{
    printf("-------------- IA (%s) --------------\n", ia_status_name((ia_status_t)s_ia.status));
    printf("Riegos aprendidos %lu (atipicos %lu) | horas de secado %.0f | MAE respuesta %.2f pp | MAE secado %.3f pp/h\n",
           (unsigned long)s_ia.a.n, (unsigned long)s_ia.a.outliers, s_ia.hours_b, ia_mae_a(&s_ia), ia_mae_b(&s_ia));
    printf("Plan: %s | humedad %.1f -> sin regar %.1f en %.1f h | meta %.1f | %.2f L | autonomia %.1f h | %s\n",
           ia_plan_name(s_plan.code), s_plan.vwc_now, s_plan.vwc_end_no_water, s_plan.horizon_h, s_plan.goal,
           s_plan.liters, s_plan.autonomy_h, s_plan_uses_fc ? "con pronostico" : "sin pronostico");
    printf("Ganancia prevista %.2f %%VWC/L | perdida actual %.3f %%VWC/h | cambio detectado: %s\n",
           s_plan.gain_per_l, s_plan.rate_now, s_ia.change_flag ? "SI" : "NO");
}

static void print_weather(void)
{
    uint32_t now = time_epoch();
    uint32_t age = weather_age_s(&s_wx, now);
    printf("-------------- PRONOSTICO Open-Meteo --------------\n");
    if (!s_wx.valid) {
        printf("Sin datos (consultas OK %lu, fallidas %lu, ultimo error: %s)\n", (unsigned long)s_wx.ok_count,
               (unsigned long)s_wx.fail_count, s_wx.last_error[0] ? s_wx.last_error : "-");
        return;
    }
    printf("Edad %lu min (%s) | %.1f C %.0f %%HR | lluvia ult. 6 h %.1f mm | prox. 6 h %.1f mm (prob max %.0f%%) | ET0 24 h %.2f mm\n",
           (unsigned long)(age / 60), weather_fresh(&s_wx, now) ? "VIGENTE" : "VENCIDO", s_wx.cur_temp, s_wx.cur_rh,
           s_wx.past_precip_6h, s_wx.next6_precip, s_wx.next6_pprob_max, s_wx.et0_24h);
}

static void print_telemetry_line(void)
{
    sensor_snapshot_t sn;
    sensors_get(&sn);
    char now[24];
    time_format_now(now, sizeof(now));
    printf("[%s] %s | SUELO %s %.1f%% (%d mV) | TINACO %s %.1f cm | AMB %.1fC %.1f%% | "
           "FLUJO %.2f L/min HOY %.3f L | %s | B:%s V:%s%s\n",
           now, ctrl_mode_name(s_ctx.ctrl_mode), sn.soil.valid ? "OK" : "INV", sn.soil.vwc_pct, sn.soil.mv,
           sn.tank.status ? sn.tank.status : "-", sn.tank.distance_cm, sn.temp_c, sn.rh_pct,
           irr_is_watering(&s_ctx) ? s_ctx.w_flow_lpm : s_tel_lpm, s_ctx.daily_ml / 1000.0f,
           state_name(s_ctx.state), s_ctx.pump_cmd ? "ON" : "OFF", s_ctx.valve_cmd ? "ON" : "OFF",
           sim()->active ? " [SIM]" : "");
}

/* ------------------------- Eventos de la lógica -------------------------- */

static int16_t vwc_x10(float v)
{
    return isnan(v) ? -1000 : (int16_t)lroundf(v * 10.0f);
}

static void on_logic_event(const irr_event_t *ev, void *user)
{
    cJSON *o;
    switch (ev->type) {
    case EV_STATE:
        s_state_dirty = true;
        printf("ESTADO -> %s\n", state_name((irr_state_t)ev->code));
        break;

    case EV_WATER_START: {
        s_p.watering_active = 1;
        s_p.active_reason = (uint8_t)ev->code;
        s_p.active_start_epoch = time_epoch();
        s_p.active_target_ml = ev->target_ml;
        s_p.event_seq++;
        storage_save(&s_p);
        snprintf(s_event_id, sizeof(s_event_id), "%s-%lu", mqtt_manager_device(), (unsigned long)s_p.event_seq);
        s_pend.active = false;              /* Otro riego antes de observar: se descarta */
        s_anchor.active = false;
        s_pred_dv = isfinite(ev->vwc_before) ?
                    ia_predict_response(&s_ia, ev->target_ml / 1000.0f, ev->vwc_before, s_in.env_valid,
                                        s_in.temp_c, s_in.rh_pct,
                                        s_have_water_end ? (s_in.now_ms - s_last_water_end_ms) / 3600000.0f : 24.0f) :
                    NAN;
        printf("RIEGO %s INICIADO (%s): objetivo %.3f L (ciclo %d)%s\n", reason_name((water_reason_t)ev->code),
               s_event_id, ev->target_ml / 1000.0f, ev->cycles,
               sim()->active ? " [SIMULACION: salidas fisicas inactivas]" : "");
        o = cJSON_CreateObject();
        add_ts(o);
        cJSON_AddStringToObject(o, "type", "WATERING_START");
        cJSON_AddStringToObject(o, "event_id", s_event_id);
        cJSON_AddStringToObject(o, "reason", reason_name((water_reason_t)ev->code));
        cJSON_AddStringToObject(o, "mode", ctrl_mode_name(s_ctx.ctrl_mode));
        cJSON_AddStringToObject(o, "crop", s_cfg.crop_id);
        cJSON_AddStringToObject(o, "stage", s_cfg.stage);
        add_num(o, "target_l", ev->target_ml / 1000.0f, 3);
        add_num(o, "vwc_before", ev->vwc_before, 1);
        add_num(o, "goal_vwc", s_ctx.ev_active ? s_ctx.ev_goal : NAN, 1);
        add_num(o, "ia_pred_dvwc", s_pred_dv, 2);
        cJSON_AddNumberToObject(o, "cycle", ev->cycles);
        publish_json("event", o, 1, false);
        s_state_dirty = true;
        break;
    }

    case EV_WATER_END: {
        hist_entry_t h = {
            .epoch = time_epoch(), .uptime_s = real_ms() / 1000,
            .reason = (uint8_t)ev->code, .result = (uint8_t)ev->code2,
            .duration_s = (uint16_t)(ev->duration_ms / 1000), .ml = (uint32_t)lroundf(ev->delivered_ml),
            .vwc_before_x10 = vwc_x10(ev->vwc_before), .vwc_after_x10 = vwc_x10(ev->vwc_after),
            .pulses = (uint16_t)(ev->pulses > 65535 ? 65535 : ev->pulses),
        };
        storage_hist_add(&s_p, &h);
        s_p.watering_active = 0;
        s_p.daily_ml = s_ctx.daily_ml;
        s_p.total_ml = s_ctx.total_ml;
        s_p.day_key = s_ctx.day_key;
        storage_save(&s_p);
        if (sim()->active && sim()->soil_valid) {
            sim()->soil_vwc += sim()->soil_gain_per_l * ev->delivered_ml / 1000.0f;
        }
        float hours_since = s_have_water_end ? (s_in.now_ms - s_last_water_end_ms) / 3600000.0f : 24.0f;
        s_last_water_end_ms = s_in.now_ms;
        s_have_water_end = true;
        /* Observación pendiente para el modelo A (tras la infiltración) */
        if (ev->delivered_ml >= 100.0f && isfinite(ev->vwc_before)) {
            s_pend = (pend_a_t){
                .active = true, .liters = ev->delivered_ml / 1000.0f, .v0 = ev->vwc_before,
                .temp = s_in.temp_c, .rh = s_in.rh_pct, .env = s_in.env_valid,
                .hours_since = hours_since, .dv_pred = s_pred_dv, .t_end = s_in.now_ms,
                .seq_ref = s_in.soil_seq,
            };
            strlcpy(s_pend.event_id, s_event_id, sizeof(s_pend.event_id));
        }
        float dur_pump = ev->duration_ms / 60000.0f;
        printf("RIEGO TERMINADO (%s): %.3f L calculados (%lu pulsos) en %.1f s, objetivo %.3f L\n",
               result_name((water_result_t)ev->code2), ev->delivered_ml / 1000.0f,
               (unsigned long)ev->pulses, ev->duration_ms / 1000.0f, ev->target_ml / 1000.0f);
        o = cJSON_CreateObject();
        add_ts(o);
        cJSON_AddStringToObject(o, "type", "WATERING_END");
        cJSON_AddStringToObject(o, "event_id", s_event_id);
        cJSON_AddStringToObject(o, "reason", reason_name((water_reason_t)ev->code));
        cJSON_AddStringToObject(o, "result", result_name((water_result_t)ev->code2));
        cJSON_AddStringToObject(o, "mode", ctrl_mode_name(s_ctx.ctrl_mode));
        cJSON_AddStringToObject(o, "crop", s_cfg.crop_id);
        cJSON_AddStringToObject(o, "stage", s_cfg.stage);
        add_num(o, "target_l", ev->target_ml / 1000.0f, 3);
        add_num(o, "delivered_l", ev->delivered_ml / 1000.0f, 3);
        cJSON_AddNumberToObject(o, "pulses", ev->pulses);
        add_num(o, "pulses_per_liter", s_cfg.pulses_per_liter, 1);
        add_num(o, "avg_flow_lpm", dur_pump > 0 ? (ev->delivered_ml / 1000.0f) / dur_pump : NAN, 2);
        add_num(o, "duration_s", ev->duration_ms / 1000.0f, 1);
        add_num(o, "vwc_before", ev->vwc_before, 1);
        add_num(o, "vwc_after_immediate", ev->vwc_after, 1);
        add_num(o, "today_l", s_ctx.daily_ml / 1000.0f, 3);
        add_num(o, "ia_pred_dvwc", s_pred_dv, 2);
        cJSON_AddStringToObject(o, "safety", (ev->code2 == RES_TARGET || ev->code2 == RES_STOP_CMD) ? "OK" :
                                result_name((water_result_t)ev->code2));
        publish_json("event", o, 1, false);
        s_state_dirty = true;
        break;
    }

    case EV_EVENT_END:
        if (s_p.hist_count > 0) {
            hist_entry_t *last = (hist_entry_t *)storage_hist_get(&s_p, 0);
            last->vwc_after_x10 = vwc_x10(ev->vwc_after);
            storage_save(&s_p);
        }
        printf("EVENTO TERMINADO: %s | %d ciclo(s), %.3f L, humedad %.1f -> %.1f %%VWC\n",
               decision_name((decision_t)ev->code), ev->cycles, ev->delivered_ml / 1000.0f,
               ev->vwc_before, ev->vwc_after);
        o = cJSON_CreateObject();
        add_ts(o);
        cJSON_AddStringToObject(o, "type", "EVENT_END");
        cJSON_AddStringToObject(o, "event_id", s_event_id);
        cJSON_AddStringToObject(o, "why", decision_name((decision_t)ev->code));
        cJSON_AddStringToObject(o, "why_text", decision_text((decision_t)ev->code));
        cJSON_AddNumberToObject(o, "cycles", ev->cycles);
        add_num(o, "liters", ev->delivered_ml / 1000.0f, 3);
        add_num(o, "vwc_before", ev->vwc_before, 1);
        add_num(o, "vwc_after_infiltration", ev->vwc_after, 1);
        add_num(o, "goal_vwc", s_ctx.ev_goal, 1);
        add_num(o, "duration_s", ev->duration_ms / 1000.0f, 0);
        publish_json("event", o, 1, false);
        break;

    case EV_DECISION:
        printf("DECISION: %s - %s\n", decision_name((decision_t)ev->code), decision_text((decision_t)ev->code));
        publish_json("decision", build_decision(), 1, true);
        s_state_dirty = true;
        break;

    case EV_ALARM_SET:
    case EV_ALARM_CLEAR: {
        const alarm_info_t *ai = alarm_info((alarm_t)ev->code);
        bool on = (ev->type == EV_ALARM_SET);
        if (ai->sev != SEV_INFO || on) {
            printf("ALARMA %s %s (%s): %s\n", ai->code, on ? "ACTIVA" : "RESUELTA",
                   severity_name(ai->sev), ai->text);
        }
        o = cJSON_CreateObject();
        add_ts(o);
        cJSON_AddStringToObject(o, "code", ai->code);
        cJSON_AddStringToObject(o, "severity", severity_name(ai->sev));
        cJSON_AddBoolToObject(o, "active", on);
        cJSON_AddBoolToObject(o, "latched", ai->latched);
        cJSON_AddStringToObject(o, "message", ai->text);
        publish_json("alarm", o, 1, false);
        s_state_dirty = true;
        break;
    }

    case EV_COUNTERS:
        s_p.daily_ml = s_ctx.daily_ml;
        s_p.day_key = s_ctx.day_key;
        s_p.total_ml = s_ctx.total_ml;
        storage_save(&s_p);
        break;
    }
}

/* ------------------------------ Comandos --------------------------------- */

static void ack_ex(const command_t *cmd, const char *status, const char *msg, cJSON *extra)
{
    if (cmd->src == SRC_MQTT) {
        cJSON *o = extra ? extra : cJSON_CreateObject();
        cJSON_AddStringToObject(o, "id", cmd->id);
        cJSON_AddStringToObject(o, "cmd", cmd->name);
        cJSON_AddStringToObject(o, "status", status);
        cJSON_AddStringToObject(o, "message", msg);
        cJSON_AddStringToObject(o, "state", state_name(s_ctx.state));
        cJSON_AddStringToObject(o, "mode", ctrl_mode_name(s_ctx.ctrl_mode));
        add_ts(o);
        publish_json("ack", o, 1, false);
        printf("MQTT %s (%s): %s - %s\n", cmd->name, cmd->id, status, msg);
    } else {
        cJSON_Delete(extra);
        printf("%s: %s\n", status, msg);
    }
}

void controller_ack(const command_t *cmd, const char *status, const char *msg)
{
    ack_ex(cmd, status, msg, NULL);
}

bool controller_post(const command_t *cmd)
{
    return s_q && xQueueSend(s_q, cmd, 0) == pdTRUE;
}

void controller_emergency_stop(const command_t *cmd)
{
    actuators_emergency_off();          /* GPIO apagados YA, antes de encolar */
    if (s_q) {
        xQueueSendToFront(s_q, cmd, 0);
    }
}

void controller_set_console_log(bool on)
{
    s_log = on;
}

static const char *cmdres(cmd_result_t r)
{
    return r == CMD_OK ? "OK" : (r == CMD_INVALID ? "INVALID" : "REJECTED");
}

/* Guarda el modo elegido (en ambos perfiles) para restaurarlo después de un reinicio o apagón */
static void save_mode_if_final(void)
{
    if (s_cfg.auto_saved != (uint8_t)s_ctx.ctrl_mode) {
        char m2[64], v[4];
        snprintf(v, sizeof(v), "%d", (int)s_ctx.ctrl_mode);
        config_set("auto_saved", v, false, m2, sizeof(m2));
    }
}

static void ia_reset_model(void)
{
    ia_init(&s_ia, &s_cfg);
    storage_ia_save(&s_ia);
    s_pend.active = false;
    s_anchor.active = false;
    s_ia_dirty = true;
}

static void execute(const command_t *c)
{
    char msg[200] = "";
    esp_err_t err;
    riego_config_t cand;
    cmd_result_t r;
    bool remote = (c->src == SRC_MQTT);

    switch (c->type) {
    case C_GET_STATUS:
        if (remote) {
            publish_json("state", build_state(), 1, true);
            publish_json("telemetry", build_telemetry(), 0, false);
            publish_json("decision", build_decision(), 1, true);
            publish_json("ia", build_ia(), 1, true);
            publish_json("weather", build_weather(), 1, true);
        } else {
            print_status();
        }
        controller_ack(c, "OK", "Estado publicado");
        break;
    case C_GET_CONFIG:
        if (remote) {
            publish_json("config", build_config(), 1, true);
        } else {
            print_config();
        }
        controller_ack(c, "OK", "Configuracion publicada");
        break;
    case C_GET_HISTORY:
        if (remote) {
            publish_json("history", build_history(), 1, false);
        } else {
            print_history();
        }
        controller_ack(c, "OK", "Historial publicado");
        break;
    case C_GET_IA:
        if (remote) {
            publish_json("ia", build_ia(), 1, true);
        } else {
            print_ia();
        }
        controller_ack(c, "OK", "Estado de la IA publicado");
        break;
    case C_NET_DIAG:
        publish_json("diag", build_diag(), 1, false);
        if (!remote) {
            net_config_print();
            print_weather();
        }
        controller_ack(c, "OK", "Diagnostico de red publicado");
        break;
    case C_WEATHER_REFRESH:
        weather_request_refresh();
        controller_ack(c, "OK", "Consulta a Open-Meteo solicitada");
        break;
    case C_START_MANUAL:
        r = irr_cmd_start_manual(&s_ctx, &s_in, c->f1, (c->b1 ? IRR_FORCE_HUM_MAX : 0u) | (c->b2 ? IRR_OVER_DAILY : 0u),
                                 msg, sizeof(msg));
        controller_ack(c, cmdres(r), msg);
        break;
    case C_START_TO_TARGET:
        r = irr_cmd_start_to_target(&s_ctx, &s_in, c->f1, c->b2 ? IRR_OVER_DAILY : 0u, msg, sizeof(msg));
        controller_ack(c, cmdres(r), msg);
        break;
    case C_STOP:
        irr_cmd_stop(&s_ctx, &s_in);
        actuators_set(false, false);
        actuators_clear_latch();
        controller_ack(c, "OK", "STOP ejecutado: bomba y electrovalvula apagadas");
        break;
    case C_SET_MODE:
    case C_ENABLE_AUTO:
    case C_DISABLE_AUTO: {
        ctrl_mode_t m = (c->type == C_SET_MODE) ? (ctrl_mode_t)c->i1 :
                        (c->type == C_ENABLE_AUTO ? CM_AUTO : CM_MANUAL);
        r = irr_cmd_set_mode(&s_ctx, &s_in, m, msg, sizeof(msg));
        if (r == CMD_OK) {
            save_mode_if_final();
            s_ia_dirty = true;
        }
        cJSON *x = cJSON_CreateObject();
        cJSON_AddStringToObject(x, "mode_applied", ctrl_mode_name(s_ctx.ctrl_mode));
        cJSON_AddStringToObject(x, "ia_status", ia_status_name((ia_status_t)s_ia.status));
        ack_ex(c, cmdres(r), msg, x);
        break;
    }
    case C_APPLY_CONFIG: {
        riego_config_t *nc = (riego_config_t *)c->blob;
        if (irr_is_watering(&s_ctx)) {
            controller_ack(c, "REJECTED", "Riego en curso: la configuracion anterior se mantiene. Reintente al terminar");
            break;
        }
        /* Los campos solo de consola no cambian por MQTT aunque el candidato se haya leído antes */
        config_get(&cand);
        nc->mode = cand.mode;
        nc->power_enabled = cand.power_enabled;
        nc->auto_saved = cand.auto_saved;
        bool dv_changed = fabsf(nc->data_version - cand.data_version) > 0.1f;
        err = config_apply(nc, msg, sizeof(msg));
        cJSON *x = cJSON_CreateObject();
        cJSON_AddStringToObject(x, "txn", c->id);
        cJSON_AddNumberToObject(x, "version_requested", c->u1);
        if (err == ESP_OK) {
            cJSON_AddNumberToObject(x, "version_applied", c->u1);
            cJSON_AddNumberToObject(x, "params_changed", c->i1);
            snprintf(msg, sizeof(msg), "Configuracion v%lu aplicada y guardada (%d parametros)%s",
                     (unsigned long)c->u1, c->i1, dv_changed ? "; nueva version de datos: la IA reinicia su modelo" : "");
        } else {
            cJSON_AddNumberToObject(x, "version_applied", cand.profile_version);
        }
        ack_ex(c, err == ESP_OK ? "OK" : "REJECTED", msg, x);
        break;
    }
    case C_SET_PARAM:
        if (irr_is_watering(&s_ctx) &&
            (!strcasecmp(c->key, "pulses_per_liter") || !strcasecmp(c->key, "overrun_ml"))) {
            controller_ack(c, "REJECTED", "No se cambia la calibracion de flujo durante un riego");
            break;
        }
        err = config_set(c->key, c->sval, remote, msg, sizeof(msg));
        controller_ack(c, err == ESP_OK ? "OK" : "REJECTED", msg);
        break;
    case C_SET_HUM_RANGE:
        err = config_set_humidity_range(c->f1, c->f2, c->f3, msg, sizeof(msg));
        controller_ack(c, err == ESP_OK ? "OK" : "REJECTED", msg);
        break;
    case C_SET_MAX_LITERS:
        config_get(&cand);
        if (!isnan(c->f1)) {
            cand.max_liters_event = c->f1;
        }
        if (!isnan(c->f2)) {
            cand.max_liters_daily = c->f2;
        }
        err = config_apply(&cand, msg, sizeof(msg));
        if (err == ESP_OK) {
            snprintf(msg, sizeof(msg), "Maximos: %.2f L por evento, %.2f L por dia",
                     cand.max_liters_event, cand.max_liters_daily);
        }
        controller_ack(c, err == ESP_OK ? "OK" : "REJECTED", msg);
        break;
    case C_SET_FLOW_CAL: {
        if (irr_is_watering(&s_ctx)) {
            controller_ack(c, "REJECTED", "No se cambia la calibracion durante un riego");
            break;
        }
        float ppl = isnan(c->f1) ? c->f2 / (c->f3 / 1000.0f) : c->f1;
        char v[24];
        snprintf(v, sizeof(v), "%.2f", ppl);
        err = config_set("pulses_per_liter", v, remote, msg, sizeof(msg));
        controller_ack(c, err == ESP_OK ? "OK" : "REJECTED", msg);
        break;
    }
    case C_SET_TANK_CAL:
        config_get(&cand);
        cand.tank_empty_cm = c->f1;
        cand.tank_full_cm = c->f2;
        err = config_apply(&cand, msg, sizeof(msg));
        if (err == ESP_OK) {
            snprintf(msg, sizeof(msg), "Tinaco: vacio %.1f cm, lleno %.1f cm (altura util %.1f cm)",
                     c->f1, c->f2, c->f1 - c->f2);
        }
        controller_ack(c, err == ESP_OK ? "OK" : "REJECTED", msg);
        break;
    case C_SET_SCHEDULE: {
        float st, en;
        if (!config_parse_time(c->key, &st) || !config_parse_time(c->sval, &en)) {
            controller_ack(c, "INVALID", "Horas invalidas (formato HH:MM)");
            break;
        }
        config_get(&cand);
        if (c->i1 == 1) {
            cand.win1_en = c->b1;
            cand.win1_start = st;
            cand.win1_end = en;
        } else {
            cand.win2_en = c->b1;
            cand.win2_start = st;
            cand.win2_end = en;
        }
        err = config_apply(&cand, msg, sizeof(msg));
        if (err == ESP_OK) {
            snprintf(msg, sizeof(msg), "Horario %d %s: %s - %s", c->i1, c->b1 ? "habilitado" : "deshabilitado",
                     c->key, c->sval);
        }
        controller_ack(c, err == ESP_OK ? "OK" : "REJECTED", msg);
        break;
    }
    case C_SET_BROKER: {
        broker_req_t *b = (broker_req_t *)c->blob;
        if (irr_is_watering(&s_ctx)) {
            controller_ack(c, "REJECTED", "Riego en curso: cambie el broker al terminar");
            break;
        }
        /* El ack se envía por el broker ACTUAL antes de cambiar */
        controller_ack(c, "PENDING", "Probando el broker nuevo; si no conecta en 90 s se vuelve al anterior");
        vTaskDelay(pdMS_TO_TICKS(300));
        if (!mqtt_manager_try_broker(b->uri, b->has_cred ? b->user : NULL, b->has_cred ? b->pass : NULL, 90)) {
            printf("SET_BROKER rechazado: datos invalidos\n");
        }
        break;
    }
    case C_IA_RESET:
        ia_reset_model();
        controller_ack(c, "OK", "Modelo IA reiniciado (el historial completo se conserva en la base de datos del servidor)");
        break;
    case C_CLEAR_ALARM:
        r = irr_cmd_clear_alarm(&s_ctx, &s_in, c->i1, msg, sizeof(msg));
        if (!irr_has_blocking_alarm(&s_ctx)) {
            actuators_clear_latch();
        }
        controller_ack(c, cmdres(r), msg);
        break;
    case C_POWER: {
        if (!c->b1 && irr_is_watering(&s_ctx)) {
            irr_cmd_stop(&s_ctx, &s_in);
        }
        err = config_set("power_enabled", c->b1 ? "1" : "0", false, msg, sizeof(msg));
        controller_ack(c, err == ESP_OK ? "OK" : "REJECTED",
                       c->b1 ? "SALIDAS DE POTENCIA HABILITADAS: la bomba y la valvula pueden activarse" :
                               "Salidas de potencia deshabilitadas");
        break;
    }
    case C_MODE:
        if (irr_is_watering(&s_ctx) || s_ctx.state == ST_INFILTRATION_WAIT) {
            controller_ack(c, "REJECTED", "Detenga el riego antes de cambiar de perfil");
            break;
        }
        config_get(&cand);
        if (c->i1 == MODE_B_FINAL) {
            if (!cand.power_enabled || !config_tank_calibrated(&cand)) {
                controller_ack(c, "REJECTED", "Perfil B requiere POWER ON y el tinaco calibrado");
                break;
            }
            cand.mode = MODE_B_FINAL;
            cand.auto_saved = (uint8_t)s_ctx.ctrl_mode;
        } else {
            cand.mode = MODE_A_TEST;
            irr_cmd_set_mode(&s_ctx, &s_in, CM_MANUAL, msg, sizeof(msg));
        }
        err = config_apply(&cand, msg, sizeof(msg));
        controller_ack(c, err == ESP_OK ? "OK" : "REJECTED",
                       c->i1 == MODE_B_FINAL ? "PERFIL B (instalacion final) activo" : "PERFIL A (pruebas) activo");
        break;
    case C_SIM:
        if (irr_is_watering(&s_ctx) || s_ctx.state == ST_INFILTRATION_WAIT) {
            irr_cmd_stop(&s_ctx, &s_in);
        }
        if (c->b1) {
            sim_reset();
        }
        sim()->active = c->b1;
        actuators_set_enable(s_cfg.power_enabled, c->b1);
        s_rise_ref = NAN;
        s_anchor.active = false;
        controller_ack(c, "OK", c->b1 ? "SIMULACION ACTIVA: salidas fisicas inactivas, sensores simulados" :
                                        "Simulacion desactivada: sensores reales");
        break;
    case C_FACTORY:
        if (irr_is_watering(&s_ctx)) {
            irr_cmd_stop(&s_ctx, &s_in);
        }
        config_factory_reset();
        controller_ack(c, "OK", "Configuracion de fabrica restaurada (potencia deshabilitada, perfil A)");
        break;
    case C_REBOOT:
        irr_cmd_stop(&s_ctx, &s_in);
        actuators_emergency_off();
        controller_ack(c, "OK", "Reiniciando...");
        vTaskDelay(pdMS_TO_TICKS(200));
        esp_restart();
        break;
    default:
        controller_ack(c, "INVALID", "Comando no soportado");
        break;
    }
    free(c->blob);
    s_state_dirty = true;
}

/* ------------------------------ IA y clima -------------------------------- */

static void ia_save_if_needed(bool force)
{
    if (force || s_b_updates_unsaved >= 1) {      /* Cada hora de secado se guarda: un reinicio no la pierde */
        storage_ia_save(&s_ia);
        s_b_updates_unsaved = 0;
    }
}

static void publish_ia_obs(const char *kind, const char *event_id, float pred, float obs, int res, float x1, float x2)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    cJSON_AddStringToObject(o, "type", "IA_OBSERVATION");
    cJSON_AddStringToObject(o, "model", kind);
    cJSON_AddStringToObject(o, "event_id", event_id ? event_id : "");
    add_num(o, "predicted", pred, 3);
    add_num(o, "observed", obs, 3);
    add_num(o, "error", (isfinite(pred) && isfinite(obs)) ? obs - pred : NAN, 3);
    cJSON_AddStringToObject(o, "used", res == 0 ? "APRENDIDO" : (res == 1 ? "ATIPICO_DESCARTADO" : "INVALIDO"));
    add_num(o, "x1", x1, 2);
    add_num(o, "x2", x2, 2);
    cJSON_AddNumberToObject(o, "model_version", s_ia.model_version);
    cJSON_AddStringToObject(o, "status", ia_status_name((ia_status_t)s_ia.status));
    publish_json("event", o, 1, false);
}

static void publish_rise(const char *cls, float from, float to)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    cJSON_AddStringToObject(o, "type", "UNEXPLAINED_RISE");
    cJSON_AddStringToObject(o, "classification", cls);
    add_num(o, "vwc_from", from, 1);
    add_num(o, "vwc_to", to, 1);
    add_num(o, "rise_pp", to - from, 1);
    cJSON_AddBoolToObject(o, "weather_fresh", weather_fresh(&s_wx, time_epoch()));
    add_num(o, "past6h_precip_mm", s_wx.valid ? s_wx.past_precip_6h : NAN, 1);
    cJSON_AddStringToObject(o, "note", "No se atribuye a litros de la bomba. Confirme la causa en el dashboard.");
    publish_json("event", o, 1, false);
    printf("AUMENTO DE HUMEDAD NO EXPLICADO: %.1f -> %.1f %%VWC (%s)\n", from, to, cls);
}

/* Aprendizaje y detección sobre cada lectura NUEVA del EC-5 */
static void on_new_soil_sample(void)
{
    if (!s_in.soil_valid) {
        s_anchor.active = false;
        s_rise_pending = 0;
        return;
    }
    {
        /* Una lectura retenida por el filtro (salto sin confirmar o falla aislada) no es una
         * observación nueva: ni la IA ni la detección de lluvia aprenden de ella. */
        sensor_snapshot_t fs;
        sensors_get(&fs);
        if (fs.soil.filter && (!strcmp(fs.soil.filter, "SALTO_IGNORADO") || !strcmp(fs.soil.filter, "RETENIDA"))) {
            return;
        }
    }
    float v = s_in.soil_vwc;
    uint32_t now = s_in.now_ms;
    bool watering_recent = irr_is_watering(&s_ctx) || s_ctx.ev_active ||
        (s_have_water_end && now - s_last_water_end_ms < (uint32_t)((s_cfg.infilt_min + 30.0f) * 60000.0f));

    /* Modelo A: humedad después de la infiltración */
    if (s_pend.active && now - s_pend.t_end >= (uint32_t)(s_cfg.infilt_min * 60000.0f) &&
        s_in.soil_seq != s_pend.seq_ref) {
        float dv = v - s_pend.v0;
        float pred = NAN;
        int res = ia_learn_response(&s_ia, s_pend.liters, s_pend.v0, s_pend.env, s_pend.temp, s_pend.rh,
                                    s_pend.hours_since, dv, &pred);
        ia_update_status(&s_ia, &s_cfg);
        publish_ia_obs("RESPUESTA_RIEGO", s_pend.event_id, pred, dv, res, s_pend.liters, s_pend.v0);
        if (s_log) {
            printf("IA aprende respuesta: %.2f L, %.1f -> %.1f (real %+.2f, predicho %+.2f) %s\n", s_pend.liters,
                   s_pend.v0, v, dv, pred, res == 0 ? "" : (res == 1 ? "[ATIPICO]" : "[INVALIDO]"));
        }
        s_pend.active = false;
        ia_save_if_needed(true);
        s_ia_dirty = true;
    }

    /* Aumento no explicado (sin riego reciente). La referencia es el MÍNIMO de las
     * últimas horas: una lluvia que sube poco a poco también se detecta. */
    if (watering_recent || !isfinite(s_rise_ref) || v < s_rise_ref || now - s_rise_ref_ms > RISE_WINDOW_MS) {
        s_rise_ref = v;
        s_rise_ref_ms = now;
    }
    bool cooldown = s_rise_have && now - s_rise_last_ms < RISE_COOLDOWN_MS;
    if (!watering_recent && !cooldown && v - s_rise_ref >= s_cfg.rise_pp) {
        if (++s_rise_pending >= 2) {            /* Confirmado con una segunda lectura */
            const char *cls;
            sensor_snapshot_t sn;
            sensors_get(&sn);
            uint32_t ep = time_epoch();
            if (v - s_rise_ref > 15.0f || (sn.soil.status && strcmp(sn.soil.status, "OK") &&
                                            strcmp(sn.soil.status, "SIMULADO") &&
                                            strcmp(sn.soil.status, "OK_FUERA_DE_CALIBRACION"))) {
                cls = "POSIBLE_ERROR_SENSOR";
            } else if (weather_fresh(&s_wx, ep) && (s_wx.past_precip_6h >= 0.5f || s_wx.cur_precip > 0.0f)) {
                cls = "POSIBLE_LLUVIA";
            } else if (weather_fresh(&s_wx, ep)) {
                cls = "POSIBLE_RIEGO_EXTERNO";
            } else {
                cls = "AUMENTO_NO_EXPLICADO";
            }
            publish_rise(cls, s_rise_ref, v);
            s_rise_have = true;
            s_rise_last_ms = now;
            s_rise_pending = 0;
            s_anchor.active = false;            /* No se aprende secado con agua externa */
            s_rise_ref = v;
            s_rise_ref_ms = now;
        }
        s_anchor.active = false;
        return;
    }
    s_rise_pending = 0;

    /* Modelo B: secado entre lecturas, solo en periodos sin agua */
    if (watering_recent) {
        s_anchor.active = false;
        return;
    }
    if (!s_anchor.active) {
        s_anchor = (anchor_b_t){ .active = true, .v = v, .t = now, .temp = s_in.temp_c, .rh = s_in.rh_pct,
                                 .env = s_in.env_valid };
        return;
    }
    uint32_t dt = now - s_anchor.t;
    if (dt >= 3600000u) {
        float dh = dt / 3600000.0f;
        float rate = (s_anchor.v - v) / dh;
        float mid_v = 0.5f * (s_anchor.v + v);
        float t = s_in.env_valid ? 0.5f * (s_anchor.temp + s_in.temp_c) : s_in.temp_c;
        float rh = s_in.env_valid ? 0.5f * (s_anchor.rh + s_in.rh_pct) : s_in.rh_pct;
        ia_env_t e;
        memset(&e, 0, sizeof(e));
        weather_fill_ia_env(&s_wx, time_epoch(), &e);
        float et0 = e.n_fc > 0 ? e.fc_et0[0] : NAN;
        float hour = fmodf(hour_of_day() - dh / 2.0f + 24.0f, 24.0f);
        float pred = NAN;
        int res = ia_learn_drying(&s_ia, mid_v, t, rh, s_in.env_valid && s_anchor.env, s_cfg.kc, et0, hour, rate, &pred);
        ia_update_status(&s_ia, &s_cfg);
        if (res == 0) {
            s_b_updates_unsaved++;
            ia_save_if_needed(false);
        }
        publish_ia_obs("SECADO", NULL, pred, rate, res, mid_v, hour);
        s_anchor = (anchor_b_t){ .active = true, .v = v, .t = now, .temp = s_in.temp_c, .rh = s_in.rh_pct,
                                 .env = s_in.env_valid };
        s_ia_dirty = true;
    }
}

static void update_plan(void)
{
    ia_env_t e;
    memset(&e, 0, sizeof(e));
    e.env_valid = s_in.env_valid;
    e.temp_c = s_in.temp_c;
    e.rh_pct = s_in.rh_pct;
    e.hour = hour_of_day();
    e.kc = s_cfg.kc;
    e.hours_since_water = s_have_water_end ? (s_in.now_ms - s_last_water_end_ms) / 3600000.0f : 24.0f;
    weather_fill_ia_env(&s_wx, time_epoch(), &e);
    s_plan_uses_fc = e.n_fc > 0;
    float horizon = irr_hours_to_following_window(&s_cfg, s_in.time_valid ? s_in.minute_of_day : -1);
    ia_plan(&s_ia, &e, &s_cfg, s_in.soil_valid ? s_in.soil_vwc : NAN, horizon, &s_plan);
    s_last_pred_next_h = s_plan.valid ? s_plan.traj[1] : NAN;

    s_in.ia_active = (s_ia.status == IA_ACTIVE);
    s_in.ia_need = s_plan.valid && (s_plan.code == IA_PLAN_WATER || s_plan.code == IA_PLAN_LIMITED);
    s_in.ia_limited = s_plan.code == IA_PLAN_LIMITED;
    s_in.ia_liters = s_plan.liters;
    s_in.ia_goal = s_plan.goal;
    s_in.ia_corr_liters = (s_ctx.ev_active && s_ctx.ev_kind == EVK_IA && s_in.soil_valid) ?
        ia_correction_liters(&s_ia, &s_cfg, s_in.soil_vwc, s_ctx.ev_goal, s_in.env_valid, s_in.temp_c, s_in.rh_pct) :
        0.0f;
}

/* ---------------------------- Búfer sin red ------------------------------- */

static void buffer_sample(void)
{
    sensor_snapshot_t sn;
    sensors_get(&sn);
    buf_entry_t *b = &s_buf[s_buf_head];
    b->ts = time_epoch();
    b->vwc_x10 = sn.soil.valid ? (int16_t)lroundf(sn.soil.vwc_pct * 10) : INT16_MIN;
    b->temp_x10 = sn.env_valid ? (int16_t)lroundf(sn.temp_c * 10) : INT16_MIN;
    b->rh_x10 = sn.env_valid ? (int16_t)lroundf(sn.rh_pct * 10) : INT16_MIN;
    b->tank_x10 = (sn.tank.valid && sn.tank.calibrated) ? (int16_t)lroundf(sn.tank.level_pct * 10) : INT16_MIN;
    b->today_cl = (uint16_t)fminf(65535.0f, s_ctx.daily_ml / 10.0f);
    b->mode = (uint8_t)s_ctx.ctrl_mode;
    b->state = (uint8_t)s_ctx.state;
    s_buf_head = (s_buf_head + 1) % BUF_MAX;
    if (s_buf_count < BUF_MAX) {
        s_buf_count++;
    }
}

static float x10(int16_t v)
{
    return v == INT16_MIN ? NAN : v / 10.0f;
}

static void buffer_flush(void)
{
    while (s_buf_count > 0) {
        cJSON *o = cJSON_CreateObject();
        add_ts(o);
        cJSON *arr = cJSON_AddArrayToObject(o, "samples");
        int n = s_buf_count > 24 ? 24 : s_buf_count;
        int start = (s_buf_head - s_buf_count + BUF_MAX) % BUF_MAX;
        for (int i = 0; i < n; i++) {
            const buf_entry_t *b = &s_buf[(start + i) % BUF_MAX];
            cJSON *e = cJSON_CreateObject();
            if (b->ts) {
                cJSON_AddNumberToObject(e, "ts", b->ts);
            } else {
                cJSON_AddNullToObject(e, "ts");
            }
            add_num(e, "vwc_pct", x10(b->vwc_x10), 1);
            add_num(e, "temp_c", x10(b->temp_x10), 1);
            add_num(e, "rh_pct", x10(b->rh_x10), 1);
            add_num(e, "tank_pct", x10(b->tank_x10), 1);
            add_num(e, "today_l", b->today_cl / 100.0f, 2);
            cJSON_AddStringToObject(e, "mode", ctrl_mode_name((ctrl_mode_t)b->mode));
            cJSON_AddStringToObject(e, "state", state_name((irr_state_t)b->state));
            cJSON_AddItemToArray(arr, e);
        }
        publish_json("telemetry_buffer", o, 1, false);
        s_buf_count -= n;
    }
}

/* ------------------------------ Bucle ------------------------------------ */

static void refresh_config(void)
{
    uint32_t g = config_generation();
    if (g == s_cfg_gen) {
        return;
    }
    char old_tz[sizeof(s_cfg.tz)];
    strlcpy(old_tz, s_cfg.tz, sizeof(old_tz));
    float old_dv = s_cfg.data_version;
    config_get(&s_cfg);
    s_cfg_gen = g;
    s_ctx.cfg = s_cfg;
    safety_set_pump_limit_ms((uint32_t)(s_cfg.pump_max_s * 1000.0f));
    if (strcmp(old_tz, s_cfg.tz) != 0) {
        time_set_tz(s_cfg.tz);
    }
    if (fabsf(old_dv - s_cfg.data_version) > 0.1f) {
        /* Nueva calibración o suelo: no se mezclan datos incompatibles */
        ia_reset_model();
        printf("IA: nueva version de datos %.0f -> modelo reiniciado\n", s_cfg.data_version);
    }
    ia_update_status(&s_ia, &s_cfg);
    publish_json("config", build_config(), 1, true);
    s_state_dirty = true;
    s_ia_dirty = true;
}

static void build_inputs(void)
{
    sensor_snapshot_t sn;
    sensors_get(&sn);
    sim_state_t *sm = sim();

    s_in.now_ms = s_virt_ms;
    if (sm->active && sm->time_override) {
        s_in.time_valid = sm->time_valid;
        s_in.minute_of_day = sm->time_valid ? sm->minute : -1;
    } else {
        s_in.time_valid = time_is_valid();
        s_in.minute_of_day = time_minute_of_day();
    }
    s_in.day_key = time_day_key();
    s_in.epoch = time_epoch();
    s_in.soil_valid = sn.soil.valid;
    s_in.soil_vwc = sn.soil.vwc_pct;
    s_in.soil_seq = sn.soil_seq;
    s_in.tank_valid = sn.tank.valid;
    s_in.tank_calibrated = sn.tank.calibrated;
    s_in.tank_pct = sn.tank.level_pct;
    s_in.env_valid = sn.env_valid;
    s_in.temp_c = sn.temp_c;
    s_in.rh_pct = sn.rh_pct;
    s_in.flow_pulses = flow_sensor_total_pulses();
    s_in.outputs_enabled = (s_cfg.power_enabled != 0) || sm->active;
    s_in.sensors_ready = sn.soil_seq > 0;
    s_in.rain_expected = weather_rain_expected(&s_wx, s_cfg.rain_prob_pct, s_cfg.rain_mm, time_epoch());
    s_in.rain_mm6 = s_in.rain_expected ? s_wx.next6_precip : 0.0f;
}

static void control_task(void *arg)
{
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    s_last_us = esp_timer_get_time();
    s_tel_us = s_last_us;
    s_tel_pulses = flow_sensor_total_pulses();

    while (true) {
        esp_task_wdt_reset();
        safety_heartbeat();
        WDT_STAGE("inicio_ciclo");

        /* Reloj virtual: en simulación el tiempo corre "speed" veces más rápido */
        int64_t now_us = esp_timer_get_time();
        uint32_t dt = (uint32_t)((now_us - s_last_us) / 1000);
        s_last_us += (int64_t)dt * 1000;
        sim_state_t *sm = sim();
        uint32_t speed = (sm->active && sm->speed > 0) ? sm->speed : 1;
        uint32_t vdt = dt * speed;
        s_virt_ms += vdt;

        refresh_config();
        actuators_set_enable(s_cfg.power_enabled != 0, sm->active);

        if (sm->active) {
            /* Flujo simulado mientras la bomba lógica está encendida */
            if (s_ctx.pump_cmd && s_ctx.valve_cmd) {
                s_sim_acc += sm->flow_lpm * s_cfg.pulses_per_liter / 60000.0f * (float)vdt;
                if (s_sim_acc >= 1.0f) {
                    uint32_t n = (uint32_t)s_sim_acc;
                    flow_sensor_add_sim_pulses(n);
                    s_sim_acc -= (float)n;
                }
            }
            /* Secado simulado del suelo */
            if (sm->soil_valid && sm->dry_pph > 0) {
                sm->soil_vwc -= sm->dry_pph * (float)vdt / 3600000.0f;
                if (sm->soil_vwc < 2.0f) {
                    sm->soil_vwc = 2.0f;
                }
            }
            /* Reloj simulado del día */
            if (sm->time_override && sm->time_valid) {
                static uint32_t acc_ms;
                acc_ms += vdt;
                while (acc_ms >= 60000) {
                    acc_ms -= 60000;
                    sm->minute = (sm->minute + 1) % 1440;
                }
            }
        }

        WDT_STAGE("entradas");
        weather_get(&s_wx);
        build_inputs();

        if (s_reboot_during_watering) {
            s_reboot_during_watering = false;
            irr_raise_alarm(&s_ctx, &s_in, ALM_REBOOT_DURING_WATERING);
        }
        if (s_config_was_reset) {
            s_config_was_reset = false;
            irr_raise_alarm(&s_ctx, &s_in, ALM_CONFIG_RESET);
        }
        char why[64];
        if (safety_take_trip(why, sizeof(why))) {
            printf("SEGURIDAD: corte de salidas (%s)\n", why);
            irr_raise_alarm(&s_ctx, &s_in, ALM_SAFETY_TRIP);
        }

        WDT_STAGE("comandos");
        command_t cmd;
        while (xQueueReceive(s_q, &cmd, 0) == pdTRUE) {
            execute(&cmd);
            build_inputs();
        }

        uint32_t rm = real_ms();
        if (rm - s_last_plan_ms >= PLAN_PERIOD_MS || s_in.soil_seq != s_last_soil_seq_seen) {
            s_last_plan_ms = rm;
            WDT_STAGE("plan_ia");
            update_plan();
        }

        WDT_STAGE("logica_riego");
        irr_step(&s_ctx, &s_in);
        actuators_set(s_ctx.pump_cmd, s_ctx.valve_cmd);

        if (s_in.soil_seq != s_last_soil_seq_seen) {
            s_last_soil_seq_seen = s_in.soil_seq;
            WDT_STAGE("lectura_suelo_ia");
            on_new_soil_sample();
        }

        if (wifi_manager_configured()) {
            irr_set_condition(&s_ctx, ALM_COMMS, !(wifi_manager_connected() && mqtt_manager_connected()));
        }
        if (s_ctx.want_soil_sample || (s_pend.active && s_in.now_ms - s_pend.t_end >=
                                       (uint32_t)(s_cfg.infilt_min * 60000.0f) && s_in.soil_seq == s_pend.seq_ref)) {
            sensors_request_soil();
        }
        sensors_set_soil_interval_s(s_ctx.soil_interval_s);

        /* Publicaciones */
        WDT_STAGE("publicaciones");
        bool conn = mqtt_manager_connected();
        if (mqtt_manager_take_connected_flag()) {
            publish_json("config", build_config(), 1, true);
            publish_json("decision", build_decision(), 1, true);
            publish_json("ia", build_ia(), 1, true);
            publish_json("weather", build_weather(), 1, true);
            publish_json("diag", build_diag(), 1, false);
            buffer_flush();
            s_state_dirty = true;
        }
        if (!conn && rm - s_last_buf_ms >= BUF_PERIOD_MS) {
            s_last_buf_ms = rm;
            buffer_sample();
        }
        if (conn && !s_was_connected) {
            s_last_buf_ms = rm;
        }
        s_was_connected = conn;
        if (rm - s_last_tel_ms >= (uint32_t)(s_cfg.telemetry_s * 1000.0f)) {
            uint32_t p = flow_sensor_total_pulses();
            float mins = (float)(now_us - s_tel_us) / 60e6f;
            s_tel_lpm = (mins > 0) ? ((float)(p - s_tel_pulses) / s_cfg.pulses_per_liter) / mins * speed : 0;
            s_tel_pulses = p;
            s_tel_us = now_us;
            s_last_tel_ms = rm;
            publish_json("telemetry", build_telemetry(), 0, false);
            if (s_log) {
                print_telemetry_line();
            }
        }
        if (s_wx.valid && s_wx.fetch_epoch != s_wx_published) {
            s_wx_published = s_wx.fetch_epoch;
            publish_json("weather", build_weather(), 1, true);
            s_state_dirty = true;
        }
        if (s_ia_dirty || rm - s_last_ia_ms >= IA_PERIOD_MS) {
            if (rm - s_last_ia_ms >= 2000) {
                publish_json("ia", build_ia(), 1, true);
                s_last_ia_ms = rm;
                s_ia_dirty = false;
            }
        }
        if (rm - s_last_diag_ms >= DIAG_PERIOD_MS) {
            s_last_diag_ms = rm;
            publish_json("diag", build_diag(), 1, false);
        }
        uint32_t period = irr_is_watering(&s_ctx) ? STATE_FAST_MS : STATE_PERIOD_MS;
        if (s_state_dirty || rm - s_last_state_ms >= period) {
            if (rm - s_last_state_ms >= 200) {
                publish_json("state", build_state(), 1, true);
                s_last_state_ms = rm;
                s_state_dirty = false;
            }
        }
        if (irr_is_watering(&s_ctx) && s_log && (rm / 1000) != ((rm - LOOP_MS) / 1000)) {
            printf("RIEGO %s: %.3f / %.3f L | %.2f L/min | %lu s\n", reason_name(s_ctx.w_reason),
                   s_ctx.w_delivered_ml / 1000.0f, s_ctx.w_target_ml / 1000.0f, s_ctx.w_flow_lpm,
                   (unsigned long)((s_in.now_ms - s_ctx.w_t_start) / 1000));
        }

        vTaskDelay(pdMS_TO_TICKS(LOOP_MS));
    }
}

void controller_start(bool config_was_reset)
{
    s_config_was_reset = config_was_reset;
    config_get(&s_cfg);
    s_cfg_gen = config_generation();
    safety_set_pump_limit_ms((uint32_t)(s_cfg.pump_max_s * 1000.0f));

    bool had = storage_load(&s_p);
    s_p.boot_count++;
    if (had && s_p.watering_active) {
        /* Reinicio durante un riego: no se reanuda, se registra y se alarma */
        s_reboot_during_watering = true;
        hist_entry_t h = {
            .epoch = s_p.active_start_epoch, .reason = s_p.active_reason, .result = RES_REBOOT,
            .ml = 0, .vwc_before_x10 = -1000, .vwc_after_x10 = -1000,
        };
        storage_hist_add(&s_p, &h);
        s_p.watering_active = 0;
        ESP_LOGW(TAG, "El ESP32 se reinicio durante un riego (%s); no se reanuda",
                 reason_name((water_reason_t)s_p.active_reason));
    }
    storage_save(&s_p);

    if (!storage_ia_load(&s_ia) || fabsf(s_ia.data_version - s_cfg.data_version) > 0.1f) {
        ia_init(&s_ia, &s_cfg);
        storage_ia_save(&s_ia);
        ESP_LOGI(TAG, "Modelo IA nuevo (sin datos: APRENDIZAJE)");
    } else {
        ESP_LOGI(TAG, "Modelo IA cargado: %lu riegos, %.0f h de secado", (unsigned long)s_ia.a.n, s_ia.hours_b);
    }
    ia_update_status(&s_ia, &s_cfg);
    memset(&s_plan, 0, sizeof(s_plan));

    irr_init(&s_ctx, &s_cfg, on_logic_event, NULL);
    s_ctx.daily_ml = s_p.daily_ml;
    s_ctx.total_ml = s_p.total_ml;
    s_ctx.day_key = s_p.day_key;
    /* Se restaura el último modo elegido (MANUAL, AUTOMATICO o IA) si la potencia está habilitada;
     * sin potencia arranca en MANUAL. Nunca se riega al arrancar: se espera el intervalo mínimo
     * entre riegos y lecturas nuevas confirmadas del EC-5. */
    ctrl_mode_t m = CM_MANUAL;
    if (s_cfg.power_enabled && s_cfg.auto_saved < CM__COUNT) {
        m = (ctrl_mode_t)s_cfg.auto_saved;
    }
    s_ctx.ctrl_mode = m;
    s_ctx.auto_enabled = (m != CM_MANUAL);
    s_ctx.have_last_event = true;
    s_ctx.last_event_end_ms = 0;

    s_q = xQueueCreate(16, sizeof(command_t));
    xTaskCreatePinnedToCore(control_task, "control", 12288, NULL, 5, NULL, 0);
    ESP_LOGI(TAG, "Control iniciado: perfil %s, modo %s, potencia %s, arranque #%lu",
             s_cfg.mode == MODE_B_FINAL ? "B" : "A", ctrl_mode_name(m),
             s_cfg.power_enabled ? "HABILITADA" : "DESHABILITADA", (unsigned long)s_p.boot_count);
}
