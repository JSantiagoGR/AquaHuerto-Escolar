#include <math.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_timer.h"
#include "esp_task_wdt.h"
#include "esp_system.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "cJSON.h"

#include "actuators.h"
#include "configuration.h"
#include "flow_sensor.h"
#include "irrigation_logic.h"
#include "mqtt_manager.h"
#include "safety.h"
#include "sensors.h"
#include "simulation.h"
#include "storage.h"
#include "timekeeping.h"
#include "wifi_manager.h"
#include "irrigation_controller.h"

static const char *TAG = "control";

#define LOOP_MS             20
#define STATE_PERIOD_MS     30000
#define STATE_FAST_MS       1000

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
static uint32_t s_last_state_ms, s_last_tel_ms;
static uint32_t s_tel_pulses;
static int64_t s_tel_us;
static float s_tel_lpm;

/* ----------------------------- Utilidades -------------------------------- */

static uint32_t real_ms(void)
{
    return (uint32_t)(esp_timer_get_time() / 1000);
}

static void add_num(cJSON *o, const char *k, float v, int dec)
{
    if (isnan(v)) {
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

/* ------------------------------ Reportes JSON ---------------------------- */

static cJSON *build_telemetry(void)
{
    sensor_snapshot_t sn;
    sensors_get(&sn);
    cJSON *o = cJSON_CreateObject();
    add_ts(o);

    cJSON *soil = cJSON_AddObjectToObject(o, "soil");
    cJSON_AddBoolToObject(soil, "valid", sn.soil.valid);
    add_num(soil, "vwc_pct", sn.soil.valid ? sn.soil.vwc_pct : NAN, 1);
    cJSON_AddNumberToObject(soil, "mv", sn.soil.mv);
    cJSON_AddBoolToObject(soil, "in_cal_range", sn.soil.in_cal_range);
    cJSON_AddStringToObject(soil, "status", sn.soil.status ? sn.soil.status : "SIN_LECTURA");
    cJSON_AddNumberToObject(soil, "age_s", sn.soil_age_s);

    cJSON *tank = cJSON_AddObjectToObject(o, "tank");
    cJSON_AddBoolToObject(tank, "valid", sn.tank.valid);
    cJSON_AddBoolToObject(tank, "calibrated", sn.tank.calibrated);
    add_num(tank, "distance_cm", sn.tank.valid ? sn.tank.distance_cm : NAN, 1);
    add_num(tank, "level_pct", (sn.tank.valid && sn.tank.calibrated) ? sn.tank.level_pct : NAN, 0);
    cJSON_AddBoolToObject(tank, "below_min", (s_ctx.alarms & ALARM_BIT(ALM_TANK_LOW)) != 0);
    cJSON_AddStringToObject(tank, "status", sn.tank.status ? sn.tank.status : "SIN_LECTURA");

    cJSON *env = cJSON_AddObjectToObject(o, "env");
    cJSON_AddBoolToObject(env, "valid", sn.env_valid);
    add_num(env, "temp_c", sn.env_valid ? sn.temp_c : NAN, 1);
    add_num(env, "rh_pct", sn.env_valid ? sn.rh_pct : NAN, 1);
    if (sn.env_last_valid_epoch) {
        cJSON_AddNumberToObject(env, "last_valid_ts", sn.env_last_valid_epoch);
    } else {
        cJSON_AddNullToObject(env, "last_valid_ts");
    }
    cJSON_AddStringToObject(env, "status", sn.env_valid ? "OK" : "SIN_LECTURA");

    cJSON *fl = cJSON_AddObjectToObject(o, "flow");
    add_num(fl, "lpm", irr_is_watering(&s_ctx) ? s_ctx.w_flow_lpm : s_tel_lpm, 2);
    add_num(fl, "session_l", irr_is_watering(&s_ctx) ? s_ctx.w_delivered_ml / 1000.0f : 0.0f, 3);
    add_num(fl, "today_l", s_ctx.daily_ml / 1000.0f, 3);
    add_num(fl, "total_l", (float)(s_ctx.total_ml / 1000.0), 3);
    cJSON_AddNumberToObject(fl, "pulses", s_in.flow_pulses);
    add_num(fl, "pulses_per_liter", s_cfg.pulses_per_liter, 1);

    cJSON_AddBoolToObject(o, "simulation", sim()->active);
    return o;
}

static cJSON *build_state(void)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    cJSON_AddStringToObject(o, "state", state_name(s_ctx.state));
    cJSON_AddStringToObject(o, "phase", phase_name(s_ctx.phase));
    cJSON_AddStringToObject(o, "mode", s_cfg.mode == MODE_B_FINAL ? "B" : "A");
    cJSON_AddBoolToObject(o, "auto_enabled", s_ctx.auto_enabled);
    cJSON_AddBoolToObject(o, "power_outputs", s_cfg.power_enabled != 0);
    cJSON_AddBoolToObject(o, "simulation", sim()->active);
    cJSON_AddBoolToObject(o, "pump", sim()->active ? s_ctx.pump_cmd : actuators_pump_physical());
    cJSON_AddBoolToObject(o, "valve", sim()->active ? s_ctx.valve_cmd : actuators_valve_physical());
    cJSON_AddBoolToObject(o, "pump_cmd", s_ctx.pump_cmd);
    cJSON_AddBoolToObject(o, "valve_cmd", s_ctx.valve_cmd);
    cJSON_AddBoolToObject(o, "emergency_latch", actuators_latched());

    bool w = irr_is_watering(&s_ctx);
    cJSON *wt = cJSON_AddObjectToObject(o, "watering");
    cJSON_AddBoolToObject(wt, "active", w);
    cJSON_AddStringToObject(wt, "type", w ? reason_name(s_ctx.w_reason) : "NONE");
    add_num(wt, "target_l", w ? s_ctx.w_target_ml / 1000.0f : 0.0f, 3);
    add_num(wt, "delivered_l", w ? s_ctx.w_delivered_ml / 1000.0f : 0.0f, 3);
    add_num(wt, "remaining_l", w ? fmaxf(0, s_ctx.w_target_ml - s_ctx.w_delivered_ml) / 1000.0f : 0.0f, 3);
    add_num(wt, "progress_pct", (w && s_ctx.w_target_ml > 0) ?
            fminf(100.0f, 100.0f * s_ctx.w_delivered_ml / s_ctx.w_target_ml) : 0.0f, 0);
    cJSON_AddNumberToObject(wt, "elapsed_s", w ? (s_in.now_ms - s_ctx.w_t_start) / 1000 : 0);
    add_num(wt, "flow_lpm", w ? s_ctx.w_flow_lpm : 0.0f, 2);

    cJSON *ev = cJSON_AddObjectToObject(o, "event");
    cJSON_AddBoolToObject(ev, "active", s_ctx.ev_active);
    cJSON_AddBoolToObject(ev, "emergency", s_ctx.ev_active && s_ctx.ev_emergency);
    cJSON_AddNumberToObject(ev, "cycles", s_ctx.ev_cycles);
    add_num(ev, "liters", s_ctx.ev_ml / 1000.0f, 3);
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
    return o;
}

static cJSON *build_config(void)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
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
    return o;
}

static cJSON *build_decision(void)
{
    cJSON *o = cJSON_CreateObject();
    add_ts(o);
    cJSON_AddStringToObject(o, "code", decision_name(s_ctx.decision));
    cJSON_AddStringToObject(o, "text", decision_text(s_ctx.decision));
    add_num(o, "soil_vwc", s_in.soil_valid ? s_in.soil_vwc : NAN, 1);
    add_num(o, "hum_min", s_cfg.hum_min, 1);
    add_num(o, "hum_target", s_cfg.hum_target, 1);
    char nw[16];
    next_window_str(nw, sizeof(nw));
    cJSON_AddStringToObject(o, "next_window", nw);
    cJSON_AddBoolToObject(o, "in_window", s_in.time_valid && irr_in_window(&s_cfg, s_in.minute_of_day));
    cJSON_AddBoolToObject(o, "auto_enabled", s_ctx.auto_enabled);
    cJSON_AddStringToObject(o, "state", state_name(s_ctx.state));
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
    printf("---------------- ESTADO ----------------\n");
    printf("Hora: %s | Modo %s | Potencia %s | Simulacion %s\n", now,
           s_cfg.mode == MODE_B_FINAL ? "B (instalacion)" : "A (pruebas)",
           s_cfg.power_enabled ? "HABILITADA" : "DESHABILITADA", sim()->active ? "SI" : "NO");
    printf("Estado: %s (%s) | Automatico: %s\n", state_name(s_ctx.state), phase_name(s_ctx.phase),
           s_ctx.auto_enabled ? "SI" : "NO");
    printf("Bomba: logica %s / fisica %s | Valvula: logica %s / fisica %s | Latch: %s\n",
           s_ctx.pump_cmd ? "ON" : "OFF", actuators_pump_physical() ? "ON" : "OFF",
           s_ctx.valve_cmd ? "ON" : "OFF", actuators_valve_physical() ? "ON" : "OFF",
           actuators_latched() ? "SI" : "NO");
    printf("Suelo: %s %.1f %%VWC (%d mV, %s)\n", sn.soil.valid ? "OK" : "INVALIDO",
           sn.soil.vwc_pct, sn.soil.mv, sn.soil.status ? sn.soil.status : "-");
    printf("Tinaco: %s dist %.1f cm nivel %s (%s)\n", sn.tank.valid ? "OK" : "INVALIDO",
           sn.tank.distance_cm, sn.tank.calibrated ? "calibrado" : "SIN CALIBRAR",
           sn.tank.status ? sn.tank.status : "-");
    if (sn.tank.calibrated && sn.tank.valid) {
        printf("        nivel %.0f %% (minimo %.0f %%)\n", sn.tank.level_pct, s_cfg.tank_min_pct);
    }
    printf("Ambiente: %s %.1f C %.1f %%HR\n", sn.env_valid ? "OK" : "INVALIDO", sn.temp_c, sn.rh_pct);
    printf("Flujo: %.2f L/min | Hoy %.3f L | Total %.3f L | Pulsos %lu\n",
           irr_is_watering(&s_ctx) ? s_ctx.w_flow_lpm : s_tel_lpm, s_ctx.daily_ml / 1000.0f,
           s_ctx.total_ml / 1000.0, (unsigned long)s_in.flow_pulses);
    if (irr_is_watering(&s_ctx)) {
        printf("Riego %s: %.3f de %.3f L\n", reason_name(s_ctx.w_reason),
               s_ctx.w_delivered_ml / 1000.0f, s_ctx.w_target_ml / 1000.0f);
    }
    printf("Humedad: minima %.1f / objetivo %.1f / maxima %.1f / critica %.1f %%VWC\n",
           s_cfg.hum_min, s_cfg.hum_target, s_cfg.hum_max, s_cfg.hum_critical);
    printf("Decision: %s - %s | Proximo horario: %s\n", decision_name(s_ctx.decision),
           decision_text(s_ctx.decision), nw);
    printf("Alarmas:");
    bool any = false;
    for (int a = 0; a < ALM__COUNT; a++) {
        if (s_ctx.alarms & ALARM_BIT(a)) {
            printf(" %s", alarm_info((alarm_t)a)->code);
            any = true;
        }
    }
    printf("%s\n", any ? "" : " ninguna");
    printf("Red: Wi-Fi %s | MQTT %s\n",
           wifi_manager_configured() ? (wifi_manager_connected() ? "CONECTADO" : "DESCONECTADO") : "SIN CONFIGURAR",
           mqtt_manager_configured() ? (mqtt_manager_connected() ? "CONECTADO" : "DESCONECTADO") : "SIN CONFIGURAR");
    printf("----------------------------------------\n");
}

static void print_config(void)
{
    printf("------------- CONFIGURACION -------------\n");
    for (int i = 0; i < config_param_count(); i++) {
        const config_param_t *p = config_param_at(i);
        char buf[48];
        config_param_format(&s_cfg, p, buf, sizeof(buf));
        printf("%-18s = %-10s %-6s %s%s\n", p->key, buf, p->unit, p->desc, p->remote ? "" : " [solo consola]");
    }
    printf("-----------------------------------------\n");
}

static void print_history(void)
{
    printf("-------------- HISTORIAL (mas reciente primero) --------------\n");
    for (int i = 0; i < s_p.hist_count; i++) {
        const hist_entry_t *h = storage_hist_get(&s_p, i);
        printf("%2d) ts=%lu %-9s %-12s %.3f L %u s antes=%.1f despues=%.1f\n", i + 1,
               (unsigned long)h->epoch, reason_name((water_reason_t)h->reason),
               result_name((water_result_t)h->result), h->ml / 1000.0f, h->duration_s,
               h->vwc_before_x10 / 10.0f, h->vwc_after_x10 / 10.0f);
    }
    if (s_p.hist_count == 0) {
        printf("(sin riegos registrados)\n");
    }
}

static void print_telemetry_line(void)
{
    sensor_snapshot_t sn;
    sensors_get(&sn);
    char now[24];
    time_format_now(now, sizeof(now));
    printf("[%s] SUELO %s %.1f%% (%d mV) | TINACO %s %.1f cm | AMB %.1fC %.1f%% | "
           "FLUJO %.2f L/min HOY %.3f L | %s | B:%s V:%s%s\n",
           now, sn.soil.valid ? "OK" : "INV", sn.soil.vwc_pct, sn.soil.mv,
           sn.tank.status ? sn.tank.status : "-", sn.tank.distance_cm,
           sn.temp_c, sn.rh_pct,
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

    case EV_WATER_START:
        s_p.watering_active = 1;
        s_p.active_reason = (uint8_t)ev->code;
        s_p.active_start_epoch = time_epoch();
        s_p.active_target_ml = ev->target_ml;
        storage_save(&s_p);
        printf("RIEGO %s INICIADO: objetivo %.3f L (ciclo %d)%s\n", reason_name((water_reason_t)ev->code),
               ev->target_ml / 1000.0f, ev->cycles, s_cfg.power_enabled && !sim()->active ? "" :
               (sim()->active ? " [SIMULACION: salidas fisicas inactivas]" : ""));
        o = cJSON_CreateObject();
        add_ts(o);
        cJSON_AddStringToObject(o, "type", "WATERING_START");
        cJSON_AddStringToObject(o, "reason", reason_name((water_reason_t)ev->code));
        add_num(o, "target_l", ev->target_ml / 1000.0f, 3);
        add_num(o, "vwc_before", ev->vwc_before, 1);
        cJSON_AddNumberToObject(o, "cycle", ev->cycles);
        publish_json("event", o, 1, false);
        s_state_dirty = true;
        break;

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
        printf("RIEGO TERMINADO (%s): %.3f L calculados (%lu pulsos) en %.1f s, objetivo %.3f L\n",
               result_name((water_result_t)ev->code2), ev->delivered_ml / 1000.0f,
               (unsigned long)ev->pulses, ev->duration_ms / 1000.0f, ev->target_ml / 1000.0f);
        o = cJSON_CreateObject();
        add_ts(o);
        cJSON_AddStringToObject(o, "type", "WATERING_END");
        cJSON_AddStringToObject(o, "reason", reason_name((water_reason_t)ev->code));
        cJSON_AddStringToObject(o, "result", result_name((water_result_t)ev->code2));
        add_num(o, "target_l", ev->target_ml / 1000.0f, 3);
        add_num(o, "delivered_l", ev->delivered_ml / 1000.0f, 3);
        cJSON_AddNumberToObject(o, "pulses", ev->pulses);
        add_num(o, "duration_s", ev->duration_ms / 1000.0f, 1);
        add_num(o, "vwc_before", ev->vwc_before, 1);
        add_num(o, "vwc_after", ev->vwc_after, 1);
        add_num(o, "today_l", s_ctx.daily_ml / 1000.0f, 3);
        publish_json("event", o, 1, false);
        s_state_dirty = true;
        break;
    }

    case EV_EVENT_END:
        if (s_p.hist_count > 0) {
            /* "Humedad después" del evento: lectura tras la infiltración */
            hist_entry_t *last = (hist_entry_t *)storage_hist_get(&s_p, 0);
            last->vwc_after_x10 = vwc_x10(ev->vwc_after);
            storage_save(&s_p);
        }
        printf("EVENTO AUTOMATICO TERMINADO: %s | %d ciclo(s), %.3f L, humedad %.1f -> %.1f %%VWC\n",
               decision_name((decision_t)ev->code), ev->cycles, ev->delivered_ml / 1000.0f,
               ev->vwc_before, ev->vwc_after);
        o = cJSON_CreateObject();
        add_ts(o);
        cJSON_AddStringToObject(o, "type", "AUTO_EVENT_END");
        cJSON_AddStringToObject(o, "why", decision_name((decision_t)ev->code));
        cJSON_AddNumberToObject(o, "cycles", ev->cycles);
        add_num(o, "liters", ev->delivered_ml / 1000.0f, 3);
        add_num(o, "vwc_before", ev->vwc_before, 1);
        add_num(o, "vwc_after", ev->vwc_after, 1);
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

void controller_ack(const command_t *cmd, const char *status, const char *msg)
{
    if (cmd->src == SRC_MQTT) {
        cJSON *o = cJSON_CreateObject();
        cJSON_AddStringToObject(o, "id", cmd->id);
        cJSON_AddStringToObject(o, "cmd", cmd->name);
        cJSON_AddStringToObject(o, "status", status);
        cJSON_AddStringToObject(o, "message", msg);
        cJSON_AddStringToObject(o, "state", state_name(s_ctx.state));
        add_ts(o);
        publish_json("ack", o, 1, false);
        printf("MQTT %s (%s): %s - %s\n", cmd->name, cmd->id, status, msg);
    } else {
        printf("%s: %s\n", status, msg);
    }
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

static void execute(const command_t *c)
{
    char msg[160] = "";
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
    case C_START_MANUAL:
        r = irr_cmd_start_manual(&s_ctx, &s_in, c->f1, c->b1, msg, sizeof(msg));
        controller_ack(c, cmdres(r), msg);
        break;
    case C_STOP:
        irr_cmd_stop(&s_ctx, &s_in);
        actuators_set(false, false);
        actuators_clear_latch();
        controller_ack(c, "OK", "STOP ejecutado: bomba y electrovalvula apagadas");
        break;
    case C_ENABLE_AUTO:
    case C_DISABLE_AUTO: {
        bool en = (c->type == C_ENABLE_AUTO);
        r = irr_cmd_set_auto(&s_ctx, &s_in, en, msg, sizeof(msg));
        if (r == CMD_OK && s_cfg.mode == MODE_B_FINAL) {
            char m2[64];
            config_set("auto_saved", en ? "1" : "0", false, m2, sizeof(m2));
        }
        controller_ack(c, cmdres(r), msg);
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
            controller_ack(c, "REJECTED", "Detenga el riego antes de cambiar de modo");
            break;
        }
        config_get(&cand);
        if (c->i1 == MODE_B_FINAL) {
            if (!cand.power_enabled || !config_tank_calibrated(&cand)) {
                controller_ack(c, "REJECTED", "Modo B requiere POWER ON y el tinaco calibrado");
                break;
            }
            cand.mode = MODE_B_FINAL;
            cand.auto_saved = s_ctx.auto_enabled;
        } else {
            cand.mode = MODE_A_TEST;
            irr_cmd_set_auto(&s_ctx, &s_in, false, msg, sizeof(msg));
        }
        err = config_apply(&cand, msg, sizeof(msg));
        controller_ack(c, err == ESP_OK ? "OK" : "REJECTED",
                       c->i1 == MODE_B_FINAL ? "MODO B (instalacion final) activo" : "MODO A (pruebas) activo");
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
        controller_ack(c, "OK", c->b1 ? "SIMULACION ACTIVA: salidas fisicas inactivas, sensores simulados" :
                                        "Simulacion desactivada: sensores reales");
        break;
    case C_FACTORY:
        if (irr_is_watering(&s_ctx)) {
            irr_cmd_stop(&s_ctx, &s_in);
        }
        config_factory_reset();
        controller_ack(c, "OK", "Configuracion de fabrica restaurada (potencia deshabilitada, modo A)");
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
    s_state_dirty = true;
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
    config_get(&s_cfg);
    s_cfg_gen = g;
    s_ctx.cfg = s_cfg;
    safety_set_pump_limit_ms((uint32_t)(s_cfg.pump_max_s * 1000.0f));
    if (strcmp(old_tz, s_cfg.tz) != 0) {
        time_set_tz(s_cfg.tz);
    }
    publish_json("config", build_config(), 1, true);
    s_state_dirty = true;
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

        /* Flujo simulado mientras la bomba lógica está encendida */
        if (sm->active && s_ctx.pump_cmd && s_ctx.valve_cmd) {
            s_sim_acc += sm->flow_lpm * s_cfg.pulses_per_liter / 60000.0f * (float)vdt;
            if (s_sim_acc >= 1.0f) {
                uint32_t n = (uint32_t)s_sim_acc;
                flow_sensor_add_sim_pulses(n);
                s_sim_acc -= (float)n;
            }
        }

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

        command_t cmd;
        while (xQueueReceive(s_q, &cmd, 0) == pdTRUE) {
            execute(&cmd);
            build_inputs();
        }

        irr_step(&s_ctx, &s_in);
        actuators_set(s_ctx.pump_cmd, s_ctx.valve_cmd);

        if (wifi_manager_configured()) {
            irr_set_condition(&s_ctx, ALM_COMMS, !(wifi_manager_connected() && mqtt_manager_connected()));
        }
        if (s_ctx.want_soil_sample) {
            sensors_request_soil();
        }
        sensors_set_soil_interval_s(s_ctx.soil_interval_s);

        /* Publicaciones */
        uint32_t rm = real_ms();
        if (mqtt_manager_take_connected_flag()) {
            publish_json("config", build_config(), 1, true);
            publish_json("decision", build_decision(), 1, true);
            s_state_dirty = true;
        }
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

    irr_init(&s_ctx, &s_cfg, on_logic_event, NULL);
    s_ctx.daily_ml = s_p.daily_ml;
    s_ctx.total_ml = s_p.total_ml;
    s_ctx.day_key = s_p.day_key;
    /* Modo A: el automático SIEMPRE inicia deshabilitado. Modo B: se restaura. */
    s_ctx.auto_enabled = (s_cfg.mode == MODE_B_FINAL) && s_cfg.auto_saved && s_cfg.power_enabled;
    /* Tras un arranque se espera el intervalo mínimo antes del primer evento automático */
    s_ctx.have_last_event = true;
    s_ctx.last_event_end_ms = 0;

    s_q = xQueueCreate(16, sizeof(command_t));
    xTaskCreatePinnedToCore(control_task, "control", 8192, NULL, 5, NULL, 0);
    ESP_LOGI(TAG, "Control iniciado: modo %s, automatico %s, potencia %s, arranque #%lu",
             s_cfg.mode == MODE_B_FINAL ? "B" : "A", s_ctx.auto_enabled ? "ON" : "OFF",
             s_cfg.power_enabled ? "HABILITADA" : "DESHABILITADA", (unsigned long)s_p.boot_count);
}
