#include <math.h>
#include <stdio.h>
#include <string.h>

#include "configuration.h"
#include "ia_model.h"
#include "sensor_filter.h"
#include "irrigation_logic.h"
#include "logic_tests.h"

#ifdef HOST_BUILD
#define LT_YIELD() do { } while (0)
#else
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#define LT_YIELD() vTaskDelay(1)
#endif

#define DT_MS 20

typedef struct {
    irr_ctx_t ctx;
    irr_inputs_t in;
    float lpm;                  /* Caudal simulado con bomba y válvula ON */
    float acc;
    float gain;                 /* %VWC que sube por litro aplicado       */
    int starts, ends, event_ends, alarm_sets;
    water_result_t last_result;
    water_reason_t last_reason;
    decision_t last_event_why;
    float last_delivered, last_target;
    uint32_t t_valve_on, t_pump_on, t_pump_off, t_valve_off;
    bool prev_pump, prev_valve;
} harness_t;

static harness_t H;
static int s_fail, s_pass;
static char s_detail[200];

static void cb(const irr_event_t *ev, void *user)
{
    harness_t *h = (harness_t *)user;
    switch (ev->type) {
    case EV_WATER_START:
        h->starts++;
        h->last_reason = (water_reason_t)ev->code;
        h->last_target = ev->target_ml;
        break;
    case EV_WATER_END:
        h->ends++;
        h->last_result = (water_result_t)ev->code2;
        h->last_delivered = ev->delivered_ml;
        if (h->in.soil_valid) {
            h->in.soil_vwc += h->gain * ev->delivered_ml / 1000.0f;
        }
        break;
    case EV_EVENT_END:
        h->event_ends++;
        h->last_event_why = (decision_t)ev->code;
        break;
    case EV_ALARM_SET:
        h->alarm_sets++;
        break;
    default:
        break;
    }
}

static void setup(void)
{
    riego_config_t c;
    config_defaults(&c);
    c.power_enabled = 1;
    memset(&H, 0, sizeof(H));
    irr_init(&H.ctx, &c, cb, &H);
    H.ctx.day_key = 2026284;
    H.in.now_ms = 1000;
    H.in.time_valid = true;
    H.in.minute_of_day = 7 * 60;
    H.in.day_key = 2026284;
    H.in.epoch = 1791700000;
    H.in.soil_valid = true;
    H.in.soil_vwc = 30.0f;
    H.in.soil_seq = 1;
    H.in.tank_valid = true;
    H.in.tank_calibrated = true;
    H.in.tank_pct = 80.0f;
    H.in.env_valid = true;
    H.in.temp_c = 22.0f;
    H.in.rh_pct = 50.0f;
    H.in.flow_pulses = 1000;
    H.in.outputs_enabled = true;
    H.in.sensors_ready = true;
    H.lpm = 4.0f;
    H.gain = 4.0f;
    irr_step(&H.ctx, &H.in);
}

/* Avanza el reloj virtual ms milisegundos */
static void run(uint32_t ms)
{
    uint32_t steps = 0;
    for (uint32_t t = 0; t < ms; t += DT_MS) {
        if (++steps % 2000 == 0) {
            LT_YIELD();                 /* Simulaciones largas: no dejar sin CPU a la tarea ociosa (watchdog) */
        }
        H.in.now_ms += DT_MS;
        if (H.ctx.pump_cmd && H.ctx.valve_cmd) {
            H.acc += H.lpm * H.ctx.cfg.pulses_per_liter / 60000.0f * DT_MS;
            uint32_t n = (uint32_t)H.acc;
            H.in.flow_pulses += n;
            H.acc -= (float)n;
        }
        if (H.ctx.want_soil_sample) {
            H.in.soil_seq++;            /* El hub entrega una lectura nueva */
        }
        irr_step(&H.ctx, &H.in);
        if (H.ctx.valve_cmd && !H.prev_valve) H.t_valve_on = H.in.now_ms;
        if (H.ctx.pump_cmd && !H.prev_pump) H.t_pump_on = H.in.now_ms;
        if (!H.ctx.pump_cmd && H.prev_pump) H.t_pump_off = H.in.now_ms;
        if (!H.ctx.valve_cmd && H.prev_valve) H.t_valve_off = H.in.now_ms;
        H.prev_pump = H.ctx.pump_cmd;
        H.prev_valve = H.ctx.valve_cmd;
        if (H.ctx.pump_cmd && !H.ctx.valve_cmd) {
            snprintf(s_detail, sizeof(s_detail), "INVARIANTE ROTA: bomba ON con valvula OFF");
        }
    }
}

static void soil(float v)
{
    H.in.soil_vwc = v;
    H.in.soil_seq++;
    run(DT_MS);
}

static void mode(ctrl_mode_t m)
{
    char msg[160];
    irr_cmd_set_mode(&H.ctx, &H.in, m, msg, sizeof(msg));
    H.ctx.have_last_event = false;
}

static void auto_on(void)
{
    mode(CM_AUTO);
}

static int manual(float l, bool force)
{
    char m[160];
    int r = irr_cmd_start_manual(&H.ctx, &H.in, l, force, m, sizeof(m));
    if (r == CMD_OK && H.ctx.valve_cmd && !H.prev_valve) {
        H.t_valve_on = H.in.now_ms;
        H.prev_valve = true;
    }
    return r;
}

static bool alarm_on(alarm_t a)
{
    return (H.ctx.alarms & ALARM_BIT(a)) != 0;
}

static void report(int n, const char *name, bool ok)
{
    if (ok && strncmp(s_detail, "INVARIANTE", 10) == 0) {
        ok = false;
    }
    printf("SELFTEST %02d %-48s %s%s%s\n", n, name, ok ? "PASS" : "FAIL",
           ok ? "" : " -> ", ok ? "" : s_detail);
    if (ok) {
        s_pass++;
    } else {
        s_fail++;
    }
    s_detail[0] = '\0';
    LT_YIELD();
}

#define EXPECT(cond, ...) do { if (!(cond)) { snprintf(s_detail, sizeof(s_detail), __VA_ARGS__); ok = false; } } while (0)

/* Ruido pseudoaleatorio reproducible para las pruebas de la IA */
static uint32_t s_lcg = 12345;
static float noise(float amp)
{
    s_lcg = s_lcg * 1664525u + 1013904223u;
    return amp * (((float)((s_lcg >> 8) & 0xFFFF) / 32767.5f) - 1.0f);
}

/* Entrena un modelo con un "suelo verdadero" conocido (solo para pruebas) */
static void train(ia_model_t *m, const riego_config_t *c, float true_gain, int events, int hours)
{
    for (int i = 0; i < events; i++) {
        float L = 0.5f + (float)(i % 5) * 0.25f;
        float v0 = 18.0f + (float)((i * 7) % 15);
        float t = 15.0f + (float)((i * 3) % 20);
        float rh = 20.0f + (float)((i * 11) % 50);
        float dv = L * (true_gain - 0.3f * (v0 - 25.0f) / 10.0f) + noise(0.3f);
        ia_learn_response(m, L, v0, true, t, rh, 12.0f, dv, NULL);
    }
    for (int h = 0; h < hours; h++) {
        float t = 15.0f + 10.0f * sinf((float)h / 24.0f * 6.283f);
        float rh = 40.0f;
        float v = 30.0f - (float)(h % 20) * 0.2f;
        float vpd = vpd_kpa(t, rh);
        float rate = 0.08f + 0.1f * c->kc * vpd + noise(0.03f);
        ia_learn_drying(m, v, t, rh, true, c->kc, NAN, (float)(h % 24), rate, NULL);
    }
    ia_update_status(m, c);
}

int logic_tests_run(int *passed)
{
    bool ok;
    s_fail = s_pass = 0;
    s_detail[0] = '\0';
    printf("SELFTEST INICIO (logica pura, entradas y reloj virtuales, sin GPIO)\n");

    /* 1 Tierra seca -> riego automático */
    setup(); auto_on(); ok = true;
    soil(20); soil(20);
    EXPECT(H.ctx.state == ST_AUTO_WATERING, "estado %s", state_name(H.ctx.state));
    EXPECT(H.ctx.decision == DEC_START_SCHEDULED, "decision %s", decision_name(H.ctx.decision));
    report(1, "Tierra seca inicia riego automatico", ok);

    /* 2 Humedad dentro de la histéresis bajo el objetivo */
    setup(); auto_on(); ok = true;
    soil(34); soil(34); run(2000);
    EXPECT(H.starts == 0 && H.ctx.decision == DEC_HUMIDITY_OK, "decision %s", decision_name(H.ctx.decision));
    report(2, "Humedad adecuada no riega", ok);

    /* 3 Sobre el máximo */
    setup(); auto_on(); ok = true;
    soil(50); soil(50);
    EXPECT(H.ctx.decision == DEC_TOO_WET, "decision %s", decision_name(H.ctx.decision));
    mode(CM_MANUAL);
    EXPECT(manual(1.0f, false) == CMD_REJECTED, "manual sin force no rechazado");
    EXPECT(manual(1.0f, true) == CMD_OK, "manual con force rechazado");
    irr_cmd_stop(&H.ctx, &H.in);
    report(3, "Tierra sobre el maximo bloquea agua", ok);

    /* 4 Tinaco lleno */
    setup(); auto_on(); ok = true;
    H.in.tank_pct = 95; soil(20); soil(20);
    EXPECT(H.starts == 1, "no inicio con tinaco lleno");
    report(4, "Tinaco lleno permite riego", ok);

    /* 5 Tinaco en el mínimo: riega pero avisa (decisión del equipo) */
    setup(); auto_on(); ok = true;
    H.in.tank_pct = 10; soil(20); soil(20);
    EXPECT(H.starts == 1 && alarm_on(ALM_TANK_LOW), "decision %s", decision_name(H.ctx.decision));
    irr_cmd_stop(&H.ctx, &H.in);
    mode(CM_MANUAL);
    {
        char m[200];
        EXPECT(irr_cmd_start_manual(&H.ctx, &H.in, 1.0f, false, m, sizeof(m)) == CMD_OK && strstr(m, "MINIMO"),
               "manual: %.120s", m);
    }
    /* Reinicio sin hora: conserva los litros del día */
    {
        irr_ctx_t k; irr_init(&k, &H.ctx.cfg, NULL, NULL);
        k.day_key = 2026287; k.daily_ml = 4200.0f;
        irr_inputs_t in2 = H.in; in2.day_key = -1; in2.now_ms = 1000;
        irr_step(&k, &in2);
        EXPECT(k.daily_ml == 4200.0f && k.day_key == 2026287, "sin hora borro el dia: %.0f mL", k.daily_ml);
        in2.day_key = 2026287; irr_step(&k, &in2);
        EXPECT(k.daily_ml == 4200.0f, "con hora del mismo dia borro: %.0f", k.daily_ml);
        in2.day_key = 2026288; irr_step(&k, &in2);
        EXPECT(k.daily_ml == 0.0f, "dia nuevo no reinicio: %.0f", k.daily_ml);
    }
    report(5, "Tinaco en el minimo: riega y avisa (y litros del dia sobreviven a un reinicio)", ok);

    /* 6 Sensor del tinaco sin datos: riega y avisa */
    setup(); auto_on(); ok = true;
    H.in.tank_valid = false; soil(20); soil(20);
    EXPECT(H.starts == 1 && alarm_on(ALM_TANK_SENSOR), "decision %s", decision_name(H.ctx.decision));
    irr_cmd_stop(&H.ctx, &H.in);
    mode(CM_MANUAL);
    EXPECT(manual(1.0f, false) == CMD_OK, "manual rechazado sin sensor de nivel");
    report(6, "Sensor de tinaco sin datos: riega y avisa", ok);

    /* 7 EC-5 inválido */
    setup(); auto_on(); ok = true;
    H.in.soil_valid = false; soil(5); soil(5);
    EXPECT(H.starts == 0 && H.ctx.decision == DEC_SOIL_INVALID && alarm_on(ALM_SOIL_SENSOR),
           "decision %s", decision_name(H.ctx.decision));
    report(7, "EC-5 invalido no riega", ok);

    /* 8 Caudal normal: 1 L */
    setup(); ok = true;
    EXPECT(manual(1.0f, false) == CMD_OK, "manual rechazado");
    run(30000);
    EXPECT(H.last_result == RES_TARGET, "resultado %s", result_name(H.last_result));
    EXPECT(H.last_delivered >= 1000 && H.last_delivered <= 1025, "entregado %.1f mL", H.last_delivered);
    report(8, "Caudal normal entrega 1 L por pulsos", ok);

    /* 9 Ausencia de flujo */
    setup(); ok = true; H.lpm = 0;
    manual(1.0f, false); run(15000);
    EXPECT(H.last_result == RES_NO_FLOW && H.ctx.state == ST_FAULT, "res %s estado %s",
           result_name(H.last_result), state_name(H.ctx.state));
    EXPECT(!H.ctx.pump_cmd && !H.ctx.valve_cmd && alarm_on(ALM_NO_FLOW), "salidas activas o sin alarma");
    report(9, "Sin flujo -> falla NO_FLOW y todo apagado", ok);

    /* 10 Pulsos erráticos */
    setup(); ok = true; H.lpm = 30;
    manual(2.0f, false); run(8000);
    EXPECT(H.last_result == RES_FLOW_HIGH && alarm_on(ALM_FLOW_HIGH), "res %s", result_name(H.last_result));
    report(10, "Pulsos erraticos -> falla FLOW_HIGH", ok);

    /* 11 Secuencia de riego manual */
    setup(); ok = true;
    manual(1.0f, false); run(30000);
    EXPECT(H.t_pump_on - H.t_valve_on >= 300 && H.t_pump_on - H.t_valve_on <= 340,
           "valvula->bomba %lu ms", (unsigned long)(H.t_pump_on - H.t_valve_on));
    EXPECT(H.t_valve_off - H.t_pump_off >= 300 && H.t_valve_off - H.t_pump_off <= 340,
           "bomba->valvula %lu ms", (unsigned long)(H.t_valve_off - H.t_pump_off));
    report(11, "Manual 1 L: valvula antes, bomba, cierre", ok);

    /* 12 Riego automático completo */
    setup(); auto_on(); ok = true; H.gain = 2;
    soil(20); soil(20); run(25000);
    EXPECT(H.ends == 1 && H.ctx.state == ST_INFILTRATION_WAIT, "estado %s", state_name(H.ctx.state));
    report(12, "Automatico por humedad baja completa ciclo", ok);

    /* 13 Espera de infiltración */
    run(14 * 60000);
    ok = (H.ctx.state == ST_INFILTRATION_WAIT && !H.ctx.pump_cmd && !H.ctx.valve_cmd);
    if (!ok) snprintf(s_detail, sizeof(s_detail), "estado %s", state_name(H.ctx.state));
    report(13, "Espera de infiltracion con salidas apagadas", ok);

    /* 14 Segundo ciclo si sigue seco */
    run(70000);
    ok = (H.starts == 2 && H.ctx.ev_active && H.ctx.ev_cycles >= 1);
    if (!ok) snprintf(s_detail, sizeof(s_detail), "inicios %d ciclos %d", H.starts, H.ctx.ev_cycles);
    report(14, "Segundo ciclo si continua seco", ok);

    /* 15 Parada al alcanzar objetivo */
    setup(); auto_on(); ok = true; H.gain = 16;
    soil(20); soil(20); run(25000); run(16 * 60000);
    EXPECT(H.event_ends == 1 && H.last_event_why == DEC_TARGET_REACHED && H.ctx.state == ST_MONITORING,
           "fin %s estado %s", decision_name(H.last_event_why), state_name(H.ctx.state));
    report(15, "Fin del evento al alcanzar objetivo", ok);

    /* 16 Máximo de ciclos */
    setup(); auto_on(); ok = true; H.gain = 3;
    soil(20); soil(20); run(3 * 17 * 60000);
    EXPECT(H.last_event_why == DEC_MAX_CYCLES && H.starts == 3, "fin %s inicios %d",
           decision_name(H.last_event_why), H.starts);
    report(16, "Maximo de ciclos por evento", ok);

    /* 17 Máximo diario */
    setup(); auto_on(); ok = true;
    H.ctx.daily_ml = 9500;
    EXPECT(manual(1.0f, false) == CMD_REJECTED, "manual excede diario y no fue rechazado");
    H.ctx.daily_ml = 9950; soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_DAILY_LIMIT && alarm_on(ALM_DAILY_LIMIT) == false,
           "decision %s", decision_name(H.ctx.decision));
    H.ctx.daily_ml = 10000; run(100);
    EXPECT(alarm_on(ALM_DAILY_LIMIT), "sin alarma DAILY_LIMIT");
    report(17, "Maximo de litros diarios", ok);

    /* 18 STOP durante un riego */
    setup(); ok = true;
    manual(2.0f, false); run(5000);
    irr_cmd_stop(&H.ctx, &H.in);
    EXPECT(!H.ctx.pump_cmd && !H.ctx.valve_cmd && H.last_result == RES_STOP_CMD && H.ctx.state == ST_IDLE,
           "res %s estado %s", result_name(H.last_result), state_name(H.ctx.state));
    report(18, "STOP inmediato durante riego", ok);

    /* 19 Pérdida de MQTT */
    setup(); ok = true;
    irr_set_condition(&H.ctx, ALM_COMMS, true);
    manual(1.0f, false); run(30000);
    EXPECT(H.last_result == RES_TARGET, "res %s", result_name(H.last_result));
    report(19, "Sin MQTT el riego termina con limites locales", ok);

    /* 20 Parámetros inválidos */
    {
        riego_config_t c;
        char m[160];
        ok = true;
        config_defaults(&c);
        EXPECT(config_validate(&c, m, sizeof(m)), "defaults invalidos: %s", m);
        c.hum_min = 40;
        EXPECT(!config_validate(&c, m, sizeof(m)), "MIN>OBJETIVO aceptado");
        config_defaults(&c); c.hum_max = 80;
        EXPECT(!config_validate(&c, m, sizeof(m)), "MAX fuera de limite aceptado");
        config_defaults(&c); c.tank_empty_cm = 50; c.tank_full_cm = 60;
        EXPECT(!config_validate(&c, m, sizeof(m)), "tinaco vacio<lleno aceptado");
        config_defaults(&c); c.pump_max_s = 900;
        EXPECT(!config_validate(&c, m, sizeof(m)), "pump_max_s 900 aceptado");
        setup();
        EXPECT(manual(0.0f, false) == CMD_INVALID && manual(50.0f, false) == CMD_INVALID, "volumen invalido aceptado");
        report(20, "Parametros invalidos rechazados", ok);
    }

    /* 21 Reinicio durante un riego */
    setup(); ok = true;
    irr_raise_alarm(&H.ctx, &H.in, ALM_REBOOT_DURING_WATERING);
    EXPECT(alarm_on(ALM_REBOOT_DURING_WATERING) && H.ctx.state == ST_IDLE && !H.ctx.pump_cmd,
           "estado %s", state_name(H.ctx.state));
    {
        char m[160];
        EXPECT(irr_cmd_clear_alarm(&H.ctx, &H.in, ALM_REBOOT_DURING_WATERING, m, sizeof(m)) == CMD_OK, "%s", m);
    }
    report(21, "Reinicio durante riego: no reanuda y alarma", ok);

    /* 22 Fallo del sensor ambiental */
    setup(); auto_on(); ok = true;
    H.in.env_valid = false; soil(20); soil(20);
    EXPECT(alarm_on(ALM_ENV_SENSOR) && H.starts == 1, "alarma %d inicios %d", alarm_on(ALM_ENV_SENSOR), H.starts);
    report(22, "Falla del sensor ambiental alarma pero no bloquea", ok);

    /* 23 Recuperación después de un error */
    setup(); ok = true; H.lpm = 0;
    manual(1.0f, false); run(15000);
    {
        char m[160];
        H.lpm = 4;
        EXPECT(irr_cmd_clear_alarm(&H.ctx, &H.in, -1, m, sizeof(m)) == CMD_OK, "%s", m);
        EXPECT(H.ctx.state == ST_IDLE, "estado %s", state_name(H.ctx.state));
        EXPECT(manual(1.0f, false) == CMD_OK, "manual rechazado tras CLEAR");
        run(30000);
        EXPECT(H.last_result == RES_TARGET, "res %s", result_name(H.last_result));
    }
    report(23, "Recuperacion tras CLEAR_ALARM", ok);

    /* 24 Hora no válida */
    setup(); auto_on(); ok = true;
    H.in.time_valid = false; H.in.minute_of_day = -1;
    soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_TIME_INVALID && H.starts == 0, "decision %s", decision_name(H.ctx.decision));
    soil(15); soil(15);
    EXPECT(H.ctx.decision == DEC_START_EMERGENCY && H.ctx.w_target_ml <= 500.0f, "decision %s",
           decision_name(H.ctx.decision));
    report(24, "Sin hora: no hay horario; emergencia limitada", ok);

    /* 25 Fuera de horario y mediodía */
    setup(); auto_on(); ok = true;
    H.in.minute_of_day = 13 * 60; soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_MIDDAY, "13:00 decision %s", decision_name(H.ctx.decision));
    H.in.minute_of_day = 10 * 60; soil(20);
    EXPECT(H.ctx.decision == DEC_BELOW_MIN_WAIT, "10:00 con 20%% decision %s", decision_name(H.ctx.decision));
    soil(30);
    EXPECT(H.ctx.decision == DEC_OUTSIDE_WINDOW, "10:00 con 30%% decision %s", decision_name(H.ctx.decision));
    EXPECT(irr_next_window_start(&H.ctx.cfg, 10 * 60) == 18 * 60, "proximo horario incorrecto");
    report(25, "Mediodia y fuera de horario posponen", ok);

    /* 26 Temperatura alta */
    setup(); auto_on(); ok = true;
    H.in.temp_c = 38; soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_HOT && H.starts == 0, "decision %s", decision_name(H.ctx.decision));
    report(26, "Temperatura alta pospone riego rutinario", ok);

    /* 27 Suelo que no responde */
    setup(); auto_on(); ok = true; H.gain = 0;
    soil(20); soil(20); run(2 * 17 * 60000);
    EXPECT(alarm_on(ALM_SOIL_NO_RESPONSE) && H.last_event_why == DEC_NO_RESPONSE, "fin %s",
           decision_name(H.last_event_why));
    H.ctx.have_last_event = false; soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_AUTO_LOCKED, "decision %s", decision_name(H.ctx.decision));
    mode(CM_MANUAL);
    EXPECT(manual(0.5f, false) == CMD_OK, "manual bloqueado por SOIL_NO_RESPONSE");
    irr_cmd_stop(&H.ctx, &H.in);
    report(27, "Suelo sin respuesta bloquea el automatico", ok);

    /* 28 Emergencia limitada */
    setup(); auto_on(); ok = true; H.gain = 1;
    H.in.minute_of_day = 13 * 60;
    soil(15); soil(15); run(20000); run(16 * 60000);
    EXPECT(H.last_event_why == DEC_EMERGENCY_DONE && H.starts == 1, "fin %s inicios %d",
           decision_name(H.last_event_why), H.starts);
    run(61 * 60000); soil(15); soil(15);
    EXPECT(H.ctx.decision == DEC_EMERGENCY_GAP && H.starts == 1, "decision %s inicios %d",
           decision_name(H.ctx.decision), H.starts);
    report(28, "Emergencia: un ciclo y espera entre emergencias", ok);

    /* 29 Flujo con bomba apagada */
    setup(); ok = true;
    run(6000);
    H.in.flow_pulses += 40; run(100);
    EXPECT(alarm_on(ALM_FLOW_WHEN_IDLE) && H.ctx.state == ST_FAULT, "estado %s", state_name(H.ctx.state));
    {
        char m[160];
        H.in.flow_pulses += 5;
        run(100);
        EXPECT(irr_cmd_clear_alarm(&H.ctx, &H.in, ALM_FLOW_WHEN_IDLE, m, sizeof(m)) == CMD_REJECTED,
               "CLEAR aceptado con pulsos activos");
    }
    report(29, "Flujo con todo apagado -> falla", ok);

    /* 30 Conflicto manual / automático */
    setup(); auto_on(); ok = true; H.gain = 1;
    soil(20); soil(20); run(25000);
    EXPECT(H.ctx.state == ST_INFILTRATION_WAIT, "estado %s", state_name(H.ctx.state));
    EXPECT(manual(1.0f, false) == CMD_REJECTED, "manual aceptado durante evento automatico");
    report(30, "Manual rechazado durante evento automatico", ok);

    /* 31 Salidas de potencia deshabilitadas: el modo se acepta pero no riega */
    setup(); ok = true;
    H.in.outputs_enabled = false;
    {
        char m[160];
        EXPECT(manual(1.0f, false) == CMD_REJECTED, "manual aceptado sin potencia");
        EXPECT(irr_cmd_set_mode(&H.ctx, &H.in, CM_AUTO, m, sizeof(m)) == CMD_OK, "modo AUTO rechazado");
        H.ctx.have_last_event = false;
        soil(15); soil(15); run(2000);
        EXPECT(H.starts == 0 && H.ctx.decision == DEC_OUTPUTS_DISABLED, "decision %s inicios %d",
               decision_name(H.ctx.decision), H.starts);
    }
    report(31, "Sin potencia: decide pero nunca riega", ok);

    /* 32 Modo MANUAL: nunca riego automático */
    setup(); ok = true;
    soil(15); soil(15); run(120000);
    EXPECT(H.starts == 0 && H.ctx.state == ST_IDLE && H.ctx.ctrl_mode == CM_MANUAL,
           "inicios %d estado %s", H.starts, state_name(H.ctx.state));
    report(32, "Modo MANUAL no inicia riegos solo", ok);

    /* 33 Reserva superior segura */
    setup(); auto_on(); ok = true;
    soil(42); soil(42);
    EXPECT(H.ctx.decision == DEC_ABOVE_RESERVE, "decision %s", decision_name(H.ctx.decision));
    setup(); auto_on(); H.gain = 22;            /* Un ciclo sube de 30 a 52 */
    soil(32); soil(32); run(25000); run(16 * 60000);
    EXPECT(H.last_event_why == DEC_TOO_WET || H.last_event_why == DEC_TARGET_REACHED,
           "fin %s", decision_name(H.last_event_why));
    EXPECT(H.starts == 1, "inicios %d", H.starts);
    report(33, "Reserva/maximo detienen nuevos ciclos", ok);

    /* 34 Histéresis bajo el objetivo */
    setup(); auto_on(); ok = true;
    soil(33.5f); soil(33.5f);
    EXPECT(H.starts == 0, "inicio con 33.5 (umbral 33)");
    soil(32.5f); soil(32.5f);
    EXPECT(H.starts == 1 && H.ctx.decision == DEC_START_SCHEDULED, "decision %s", decision_name(H.ctx.decision));
    report(34, "Histeresis: solo bajo (objetivo - histeresis)", ok);

    /* 35 Lluvia pronosticada: solo la usa el modo IA */
    setup(); auto_on(); ok = true;
    H.in.rain_expected = true; soil(25); soil(25);
    EXPECT(H.starts == 1 && H.ctx.decision == DEC_START_SCHEDULED, "AUTOMATICO con lluvia: %s", decision_name(H.ctx.decision));
    setup(); mode(CM_IA); ok = ok && true;
    H.ctx.cfg.ia_gain_prior = 0.27f;          /* Cama real: 1 L sube 0.27 %VWC */
    H.in.rain_expected = true; H.in.rain_mm6 = 2.0f; soil(25); soil(25);
    EXPECT(H.starts == 1, "IA con lluvia chica (2 mm no cubren 10 pp): %s", decision_name(H.ctx.decision));
    setup(); mode(CM_IA);
    H.ctx.cfg.ia_gain_prior = 0.27f;
    H.in.rain_expected = true; H.in.rain_mm6 = 50.0f; soil(25); soil(25);
    EXPECT(H.ctx.decision == DEC_RAIN_EXPECTED && H.starts == 0, "IA con lluvia grande: %s", decision_name(H.ctx.decision));
    soil(15); soil(15);
    EXPECT(H.ctx.decision == DEC_START_EMERGENCY, "emergencia con lluvia: %s", decision_name(H.ctx.decision));
    report(35, "Lluvia por balance: la IA pospone solo si cubre el deficit (no emergencias); AUTOMATICO no", ok);

    /* 36 Manual hacia la humedad óptima (ignora horario, respeta límites) */
    setup(); ok = true; H.gain = 6;
    H.in.minute_of_day = 13 * 60;
    {
        char m[200];
        soil(24);
        EXPECT(irr_cmd_start_to_target(&H.ctx, &H.in, 0, 0u, m, sizeof(m)) == CMD_OK, "%s", m);
        run(25000);
        EXPECT(H.ctx.state == ST_INFILTRATION_WAIT, "estado %s", state_name(H.ctx.state));
        run(3 * 17 * 60000);
        EXPECT(H.last_event_why == DEC_TARGET_REACHED || H.last_event_why == DEC_MAX_CYCLES,
               "fin %s", decision_name(H.last_event_why));
        EXPECT(H.in.soil_vwc >= 35.0f && H.in.soil_vwc < 45.0f, "humedad final %.1f", H.in.soil_vwc);
        soil(36);
        EXPECT(irr_cmd_start_to_target(&H.ctx, &H.in, 0, 0u, m, sizeof(m)) == CMD_REJECTED, "aceptado en objetivo");
        /* Humedad elegida por el usuario: 40 % -> riega por dosis hasta 40 */
        EXPECT(irr_cmd_start_to_target(&H.ctx, &H.in, 40.0f, 0u, m, sizeof(m)) == CMD_OK, "meta 40: %.120s", m);
        EXPECT(H.ctx.ev_goal == 40.0f, "meta guardada %.1f", H.ctx.ev_goal);
        irr_cmd_stop(&H.ctx, &H.in);
        EXPECT(irr_cmd_start_to_target(&H.ctx, &H.in, 60.0f, 0u, m, sizeof(m)) == CMD_INVALID, "acepto meta sobre la maxima");
    }
    report(36, "Manual hacia objetivo (optima o elegida) por dosis e infiltracion", ok);

    /* 37 Modo IA sin modelo validado -> respaldo automático conservador */
    setup(); mode(CM_IA); ok = true;
    H.in.ia_active = false;
    soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_START_SCHEDULED && H.last_reason == WR_SCHEDULED,
           "decision %s", decision_name(H.ctx.decision));
    report(37, "IA en aprendizaje usa el automatico", ok);

    /* 38 IA activa: no hace falta regar */
    setup(); mode(CM_IA); ok = true;
    H.in.ia_active = true; H.in.ia_need = false;
    soil(30); soil(30); run(2000);
    EXPECT(H.starts == 0 && H.ctx.decision == DEC_IA_NOT_NEEDED, "decision %s", decision_name(H.ctx.decision));
    report(38, "IA activa: no riega si no hace falta", ok);

    /* 39 IA activa: dosis calculada y corrección acotada */
    setup(); mode(CM_IA); ok = true; H.gain = 2;
    H.in.ia_active = true; H.in.ia_need = true; H.in.ia_liters = 0.8f; H.in.ia_goal = 31.0f;
    H.in.ia_corr_liters = 0.6f;
    soil(28); soil(28);
    EXPECT(H.ctx.decision == DEC_START_IA && fabsf(H.last_target - 800.0f) < 1.0f && H.last_reason == WR_IA,
           "decision %s objetivo %.0f mL", decision_name(H.ctx.decision), H.last_target);
    run(25000); run(16 * 60000);                     /* 28 + 1.6 = 29.6 < 30 -> corrección */
    EXPECT(H.starts == 2 && fabsf(H.last_target - 600.0f) < 1.0f, "inicios %d dosis %.0f",
           H.starts, H.last_target);
    run(25000); run(16 * 60000);                     /* 29.6 + 1.2 = 30.8 >= 30 */
    EXPECT(H.last_event_why == DEC_IA_GOAL_REACHED, "fin %s", decision_name(H.last_event_why));
    report(39, "IA: dosis del modelo y correccion acotada", ok);

    /* 40 IA activa: emergencia a mediodía */
    setup(); mode(CM_IA); ok = true;
    H.in.ia_active = true; H.in.ia_need = false; H.in.minute_of_day = 13 * 60;
    soil(15); soil(15);
    EXPECT(H.ctx.decision == DEC_START_EMERGENCY, "decision %s", decision_name(H.ctx.decision));
    report(40, "IA: emergencia aun fuera de horario", ok);

    /* 41 Cambio de modo durante evento */
    setup(); auto_on(); ok = true; H.gain = 1;
    soil(20); soil(20); run(25000);
    {
        char m[160];
        EXPECT(irr_cmd_set_mode(&H.ctx, &H.in, CM_IA, m, sizeof(m)) == CMD_REJECTED, "IA aceptado en evento");
        EXPECT(irr_cmd_set_mode(&H.ctx, &H.in, CM_MANUAL, m, sizeof(m)) == CMD_OK, "MANUAL rechazado");
        EXPECT(!H.ctx.ev_active && H.ctx.state == ST_IDLE, "evento sigue activo, estado %s", state_name(H.ctx.state));
    }
    report(41, "Cambio de modo seguro durante un evento", ok);

    /* 42 Horizonte hasta el siguiente horario preferido */
    {
        riego_config_t c;
        config_defaults(&c);
        ok = true;
        EXPECT(fabsf(irr_hours_to_following_window(&c, 7 * 60) - 11.0f) < 0.01f, "07:00 -> %.2f",
               irr_hours_to_following_window(&c, 7 * 60));
        EXPECT(fabsf(irr_hours_to_following_window(&c, 19 * 60) - 11.0f) < 0.01f, "19:00 -> %.2f",
               irr_hours_to_following_window(&c, 19 * 60));
        EXPECT(fabsf(irr_hours_to_following_window(&c, 10 * 60) - 8.0f) < 0.01f, "10:00 -> %.2f",
               irr_hours_to_following_window(&c, 10 * 60));
        c.win2_en = 0;
        EXPECT(fabsf(irr_hours_to_following_window(&c, 7 * 60) - 23.0f) < 0.01f, "solo matutino -> %.2f",
               irr_hours_to_following_window(&c, 7 * 60));
        report(42, "Horizonte del plan hasta el siguiente horario", ok);
    }

    /* 43 Orden de umbrales */
    {
        riego_config_t c;
        char m[160];
        ok = true;
        config_defaults(&c); c.hum_reserve = 34;
        EXPECT(!config_validate(&c, m, sizeof(m)), "reserva < objetivo aceptada");
        config_defaults(&c); c.hum_reserve = 46;
        EXPECT(!config_validate(&c, m, sizeof(m)), "reserva > maxima aceptada");
        config_defaults(&c); c.hum_critical = 25;
        EXPECT(!config_validate(&c, m, sizeof(m)), "emergencia >= minima aceptada");
        config_defaults(&c); c.hum_target = 30; c.hum_critical = 22; c.auto_hyst_pp = 9;
        EXPECT(!config_validate(&c, m, sizeof(m)), "histeresis excesiva aceptada");
        report(43, "Orden emergencia<min<obj<reserva<=max", ok);
    }

    /* 44 IA: aprende la ganancia real del suelo */
    {
        riego_config_t c;
        config_defaults(&c);
        ia_model_t m;
        ia_init(&m, &c);
        ok = true;
        EXPECT(m.status == IA_LEARNING, "estado inicial %s", ia_status_name((ia_status_t)m.status));
        s_lcg = 12345;
        train(&m, &c, 3.5f, 14, 72);
        float g = ia_predict_response(&m, 1.0f, 25.0f, true, 20.0f, 50.0f, 12.0f);
        EXPECT(fabsf(g - 3.5f) < 0.5f, "ganancia aprendida %.2f (real 3.5)", g);
        EXPECT(m.status != IA_LEARNING, "sigue en APRENDIZAJE (n=%lu h=%.0f)", (unsigned long)m.a.n, m.hours_b);
        float mb = ia_mae_b(&m);
        EXPECT(isfinite(mb) && mb < 0.4f, "MAE secado %.3f", mb);
        report(44, "IA aprende ganancia y secado (RLS)", ok);

        /* 45 Un atípico aislado no destruye lo aprendido */
        ok = true;
        float before = ia_predict_response(&m, 1.0f, 25.0f, true, 20.0f, 50.0f, 12.0f);
        int r = ia_learn_response(&m, 1.0f, 25.0f, true, 20.0f, 50.0f, 12.0f, 30.0f, NULL);
        float after = ia_predict_response(&m, 1.0f, 25.0f, true, 20.0f, 50.0f, 12.0f);
        EXPECT(r == 1 && fabsf(after - before) < 0.05f, "r=%d antes %.2f despues %.2f", r, before, after);
        report(45, "IA descarta atipicos aislados", ok);

        /* 46 Cambio sostenido: se detecta, se revalida y se adapta */
        ok = true;
        for (int i = 0; i < 12; i++) {
            ia_learn_response(&m, 1.0f, 25.0f, true, 20.0f, 50.0f, 12.0f, 1.2f + noise(0.1f), NULL);
        }
        ia_update_status(&m, &c);
        float g2 = ia_predict_response(&m, 1.0f, 25.0f, true, 20.0f, 50.0f, 12.0f);
        EXPECT(fabsf(g2 - 1.2f) < 0.8f, "no se adapto: %.2f", g2);
        EXPECT(m.status != IA_ACTIVE || m.change_flag == 0, "estado %s", ia_status_name((ia_status_t)m.status));
        report(46, "IA detecta cambio y se adapta sin borrar", ok);
    }

    /* 47 Plan IA: no regar / regar lo mínimo / meta limitada */
    {
        riego_config_t c;
        config_defaults(&c);
        ia_model_t m;
        ia_init(&m, &c);
        ia_env_t e;
        memset(&e, 0, sizeof(e));
        e.env_valid = true; e.temp_c = 25; e.rh_pct = 40; e.hour = 7; e.kc = 1; e.hours_since_water = 24;
        ia_plan_t p;
        ok = true;
        ia_plan(&m, &e, &c, 34.0f, 11.0f, &p);
        EXPECT(p.code == IA_PLAN_NOT_NEEDED, "34%%: %s (fin %.1f)", ia_plan_name(p.code), p.vwc_end_no_water);
        ia_plan(&m, &e, &c, 26.0f, 11.0f, &p);
        EXPECT(p.code == IA_PLAN_WATER && p.liters > 0.1f && p.liters <= c.max_liters_event &&
               p.goal > 26.0f && p.goal <= c.hum_reserve, "26%%: %s L=%.2f meta %.1f",
               ia_plan_name(p.code), p.liters, p.goal);
        EXPECT(fabsf(p.goal - (c.hum_min + c.ia_margin_pp + p.loss_pred)) < 0.01f, "meta no es la minima necesaria");
        c.hum_reserve = 27.0f;
        ia_plan(&m, &e, &c, 26.0f, 11.0f, &p);
        EXPECT(p.code == IA_PLAN_LIMITED && fabsf(p.goal - 27.0f) < 0.01f, "limitado: %s meta %.1f",
               ia_plan_name(p.code), p.goal);
        EXPECT(p.autonomy_h > 0 && p.autonomy_h < 99, "autonomia %.1f", p.autonomy_h);
        report(47, "Plan IA: minima dosis y limites", ok);
    }

    /* 50 Riego manual solo en MANUAL; pasar el máximo diario solo con autorización (un riego) */
    {
        char m[200];
        setup(); auto_on(); ok = true;
        EXPECT(irr_cmd_start_manual(&H.ctx, &H.in, 1.0f, 0u, m, sizeof(m)) == CMD_REJECTED && strstr(m, "MANUAL"),
               "AUTOMATICO acepto riego manual: %.120s", m);
        mode(CM_IA);
        EXPECT(irr_cmd_start_to_target(&H.ctx, &H.in, 0, 0u, m, sizeof(m)) == CMD_REJECTED, "IA acepto riego hasta humedad");
        mode(CM_MANUAL);
        float lim = H.ctx.cfg.max_liters_daily * 1000.0f;
        H.ctx.daily_ml = lim - 200.0f;                       /* Quedan 0.2 L */
        EXPECT(manual(1.0f, false) == CMD_REJECTED, "manual paso el maximo diario sin autorizacion");
        EXPECT(irr_cmd_start_manual(&H.ctx, &H.in, 1.0f, IRR_OVER_DAILY, m, sizeof(m)) == CMD_OK && strstr(m, "EXTRA"),
               "riego extra autorizado rechazado: %.120s", m);
        run(120000);
        EXPECT(H.last_result == RES_TARGET && H.ctx.daily_ml > lim, "extra no termino en TARGET (%s, %.0f mL)",
               result_name(H.last_result), H.ctx.daily_ml);
        EXPECT(!H.ctx.over_daily, "la autorizacion quedo activa despues del riego");
        EXPECT(manual(0.5f, false) == CMD_REJECTED, "sin nueva autorizacion acepto otro riego");
        soil(20); soil(20);
        EXPECT(irr_cmd_start_to_target(&H.ctx, &H.in, 0, 0u, m, sizeof(m)) == CMD_REJECTED, "hasta humedad sin autorizacion");
        EXPECT(irr_cmd_start_to_target(&H.ctx, &H.in, 0, IRR_OVER_DAILY, m, sizeof(m)) == CMD_OK, "hasta humedad autorizado: %.120s", m);
        irr_cmd_stop(&H.ctx, &H.in);
        report(50, "Manual solo en MANUAL; extra sobre el maximo diario solo autorizado", ok);
    }

    /* 51 Filtro de lecturas: picos ignorados, cambios reales aceptados, fallas aisladas toleradas */
    {
        ok = true;
        sfilt_t f;
        sfilt_init(&f, 3.0f, 2.0f, 2, 2);
        float seq[] = { 25.0f, 25.4f, 24.8f };
        for (int i = 0; i < 3; i++) sfilt_push(&f, true, seq[i]);
        EXPECT(fabsf(f.out - 25.0f) < 0.01f, "mediana %.2f", f.out);
        /* Pico de +9 pp sin confirmar (como el falso riego externo de la noche del 21-oct) */
        EXPECT(sfilt_push(&f, true, 34.0f) == SF_HELD && fabsf(f.out - 25.0f) < 0.01f, "pico aceptado: %.2f", f.out);
        EXPECT(sfilt_push(&f, true, 25.2f) == SF_ACCEPTED && fabsf(f.out - 25.2f) < 0.3f, "no volvio: %.2f", f.out);
        /* Cambio real grande (lluvia fuerte): dos lecturas seguidas que coinciden */
        EXPECT(sfilt_push(&f, true, 31.0f) == SF_HELD, "salto 1");
        EXPECT(sfilt_push(&f, true, 31.5f) == SF_JUMP_CONFIRMED && fabsf(f.out - 31.25f) < 0.01f, "salto real no aceptado: %.2f", f.out);
        /* Falla aislada (contacto flojo): conserva el valor 2 lecturas y luego se declara inválido */
        EXPECT(sfilt_push(&f, false, 0) == SF_GRACE && f.have, "gracia 1");
        EXPECT(sfilt_push(&f, false, 0) == SF_GRACE && f.have, "gracia 2");
        EXPECT(sfilt_push(&f, false, 0) == SF_INVALID && !f.have, "no invalido tras 3 fallas");
        EXPECT(sfilt_push(&f, true, 28.0f) == SF_ACCEPTED && fabsf(f.out - 28.0f) < 0.01f, "no se recupero");
        /* Ruido alternado grande nunca se adopta (no coincide entre sí) */
        sfilt_init(&f, 3.0f, 2.0f, 2, 2);
        sfilt_push(&f, true, 25.0f);
        float zig[] = { 33.0f, 18.0f, 34.0f, 17.0f };
        for (int i = 0; i < 4; i++) sfilt_push(&f, true, zig[i]);
        EXPECT(fabsf(f.out - 25.0f) < 0.01f, "ruido adoptado: %.2f", f.out);
        /* IA: un riego que "baja" la humedad no se aprende */
        ia_model_t ia;
        ia_init(&ia, &H.ctx.cfg);
        float pred;
        EXPECT(ia_learn_response(&ia, 1.5f, 24.0f, true, 25, 50, 12, -3.8f, &pred) != 0, "IA aprendio una bajada");
        report(51, "Filtro de lecturas (picos, saltos reales, fallas aisladas) e IA sin bajadas", ok);
    }

    printf("SELFTEST FIN: %d PASS, %d FAIL\n", s_pass, s_fail);
    if (passed) {
        *passed = s_pass;
    }
    return s_fail;
}
