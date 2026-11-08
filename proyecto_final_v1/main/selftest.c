#include <math.h>
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"

#include "commands.h"
#include "configuration.h"
#include "irrigation_logic.h"
#include "soil_sensor.h"
#include "tank_level.h"
#include "selftest.h"

#define DT_MS 20

typedef struct {
    irr_ctx_t ctx;
    irr_inputs_t in;
    float lpm;                  /* Caudal simulado con bomba y válvula ON */
    float acc;
    float gain;                 /* %VWC que sube por litro aplicado       */
    int starts, ends, event_ends, alarm_sets;
    water_result_t last_result;
    decision_t last_event_why;
    float last_delivered;
    uint32_t t_valve_on, t_pump_on, t_pump_off, t_valve_off;
    bool prev_pump, prev_valve;
} harness_t;

static harness_t H;
static int s_fail, s_pass;
static char s_detail[160];

static void cb(const irr_event_t *ev, void *user)
{
    harness_t *h = (harness_t *)user;
    switch (ev->type) {
    case EV_WATER_START:
        h->starts++;
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
    for (uint32_t t = 0; t < ms; t += DT_MS) {
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
        /* Invariante de seguridad en todo momento */
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

static void auto_on(void)
{
    char m[96];
    irr_cmd_set_auto(&H.ctx, &H.in, true, m, sizeof(m));
    H.ctx.have_last_event = false;
}

static int manual(float l, bool force)
{
    char m[128];
    int r = irr_cmd_start_manual(&H.ctx, &H.in, l, force, m, sizeof(m));
    if (r == CMD_OK && H.ctx.valve_cmd && !H.prev_valve) {
        /* La válvula se abre en el instante del comando, no en el siguiente paso */
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
    printf("SELFTEST %02d %-46s %s%s%s\n", n, name, ok ? "PASS" : "FAIL",
           ok ? "" : " -> ", ok ? "" : s_detail);
    if (ok) {
        s_pass++;
    } else {
        s_fail++;
    }
    s_detail[0] = '\0';
    vTaskDelay(1);
}

#define EXPECT(cond, ...) do { if (!(cond)) { snprintf(s_detail, sizeof(s_detail), __VA_ARGS__); ok = false; } } while (0)

int selftest_run(void)
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

    /* 2 Tierra húmeda */
    setup(); auto_on(); ok = true;
    soil(30); soil(30); run(2000);
    EXPECT(H.starts == 0 && H.ctx.decision == DEC_HUMIDITY_OK, "decision %s", decision_name(H.ctx.decision));
    report(2, "Tierra humeda no riega", ok);

    /* 3 Sobre el máximo */
    setup(); auto_on(); ok = true;
    soil(50); soil(50);
    EXPECT(H.ctx.decision == DEC_TOO_WET, "decision %s", decision_name(H.ctx.decision));
    EXPECT(manual(1.0f, false) == CMD_REJECTED, "manual sin force no rechazado");
    EXPECT(manual(1.0f, true) == CMD_OK, "manual con force rechazado");
    irr_cmd_stop(&H.ctx, &H.in);
    report(3, "Tierra sobre el maximo bloquea agua", ok);

    /* 4 Tinaco lleno */
    setup(); auto_on(); ok = true;
    H.in.tank_pct = 95; soil(20); soil(20);
    EXPECT(H.starts == 1, "no inicio con tinaco lleno");
    report(4, "Tinaco lleno permite riego", ok);

    /* 5 Tinaco vacío */
    setup(); auto_on(); ok = true;
    H.in.tank_pct = 10; soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_TANK_LOW && alarm_on(ALM_TANK_LOW), "decision %s", decision_name(H.ctx.decision));
    EXPECT(manual(1.0f, false) == CMD_REJECTED, "manual permitido con tinaco vacio");
    report(5, "Tinaco vacio bloquea riego", ok);

    /* 6 Sensor del tinaco desconectado */
    setup(); auto_on(); ok = true;
    H.in.tank_valid = false; soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_TANK_INVALID && alarm_on(ALM_TANK_SENSOR), "decision %s", decision_name(H.ctx.decision));
    EXPECT(manual(1.0f, false) == CMD_REJECTED, "manual permitido sin sensor de nivel");
    report(6, "Sensor de tinaco sin datos bloquea", ok);

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

    /* 11 Secuencia de riego manual de 1 L */
    setup(); ok = true;
    manual(1.0f, false); run(30000);
    EXPECT(H.t_pump_on - H.t_valve_on >= 300 && H.t_pump_on - H.t_valve_on <= 340,
           "valvula->bomba %lu ms", (unsigned long)(H.t_pump_on - H.t_valve_on));
    EXPECT(H.t_valve_off - H.t_pump_off >= 300 && H.t_valve_off - H.t_pump_off <= 340,
           "bomba->valvula %lu ms", (unsigned long)(H.t_valve_off - H.t_pump_off));
    report(11, "Manual 1 L: valvula antes, bomba, cierre", ok);

    /* 12 Riego automático completo por humedad baja */
    setup(); auto_on(); ok = true; H.gain = 2;
    soil(20); soil(20); run(25000);
    EXPECT(H.ends == 1 && H.ctx.state == ST_INFILTRATION_WAIT, "estado %s", state_name(H.ctx.state));
    report(12, "Automatico por humedad baja completa ciclo", ok);

    /* 13 Espera de infiltración (15 min) */
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

    /* 19 Pérdida de MQTT: la lógica no depende de la red */
    setup(); ok = true;
    irr_set_condition(&H.ctx, ALM_COMMS, true);
    manual(1.0f, false); run(30000);
    EXPECT(H.last_result == RES_TARGET, "res %s", result_name(H.last_result));
    report(19, "Sin MQTT el riego termina con limites locales", ok);

    /* 20 Comandos duplicados (ids únicos: no se borra la lista real de MQTT) */
    {
        char id1[40], id2[40];
        uint32_t u = (uint32_t)esp_timer_get_time();
        snprintf(id1, sizeof(id1), "selftest-%08lx-a", (unsigned long)u);
        snprintf(id2, sizeof(id2), "selftest-%08lx-b", (unsigned long)u);
        ok = true;
        EXPECT(!commands_seen_id(id1), "primer id marcado como repetido");
        EXPECT(commands_seen_id(id1), "id repetido no detectado");
        EXPECT(!commands_seen_id(id2), "id nuevo marcado como repetido");
        report(20, "Comandos MQTT duplicados se descartan", ok);
    }

    /* 21 Parámetros inválidos */
    {
        riego_config_t c;
        char m[128];
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
        report(21, "Parametros invalidos rechazados", ok);
    }

    /* 22 Reinicio durante un riego (alarma de recuperación) */
    setup(); ok = true;
    irr_raise_alarm(&H.ctx, &H.in, ALM_REBOOT_DURING_WATERING);
    EXPECT(alarm_on(ALM_REBOOT_DURING_WATERING) && H.ctx.state == ST_IDLE && !H.ctx.pump_cmd,
           "estado %s", state_name(H.ctx.state));
    {
        char m[96];
        EXPECT(irr_cmd_clear_alarm(&H.ctx, &H.in, ALM_REBOOT_DURING_WATERING, m, sizeof(m)) == CMD_OK, "%s", m);
    }
    report(22, "Reinicio durante riego: no reanuda y alarma", ok);

    /* 23 Fallo del sensor ambiental (informativo) */
    setup(); auto_on(); ok = true;
    H.in.env_valid = false; soil(20); soil(20);
    EXPECT(alarm_on(ALM_ENV_SENSOR) && H.starts == 1, "alarma %d inicios %d", alarm_on(ALM_ENV_SENSOR), H.starts);
    report(23, "Falla DHT22 alarma pero no bloquea", ok);

    /* 24 Recuperación después de un error */
    setup(); ok = true; H.lpm = 0;
    manual(1.0f, false); run(15000);
    {
        char m[96];
        H.lpm = 4;
        EXPECT(irr_cmd_clear_alarm(&H.ctx, &H.in, -1, m, sizeof(m)) == CMD_OK, "%s", m);
        EXPECT(H.ctx.state == ST_IDLE, "estado %s", state_name(H.ctx.state));
        EXPECT(manual(1.0f, false) == CMD_OK, "manual rechazado tras CLEAR");
        run(30000);
        EXPECT(H.last_result == RES_TARGET, "res %s", result_name(H.last_result));
    }
    report(24, "Recuperacion tras CLEAR_ALARM", ok);

    /* 25 Hora no válida: sin riego por horario, emergencia sí */
    setup(); auto_on(); ok = true;
    H.in.time_valid = false; H.in.minute_of_day = -1;
    soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_TIME_INVALID && H.starts == 0, "decision %s", decision_name(H.ctx.decision));
    soil(15); soil(15);
    EXPECT(H.ctx.decision == DEC_START_EMERGENCY && H.ctx.w_target_ml <= 500.0f, "decision %s",
           decision_name(H.ctx.decision));
    report(25, "Sin hora: no hay horario; emergencia limitada", ok);

    /* 26 Fuera de horario y mediodía */
    setup(); auto_on(); ok = true;
    H.in.minute_of_day = 13 * 60; soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_MIDDAY, "13:00 decision %s", decision_name(H.ctx.decision));
    H.in.minute_of_day = 10 * 60; soil(20);
    EXPECT(H.ctx.decision == DEC_OUTSIDE_WINDOW, "10:00 decision %s", decision_name(H.ctx.decision));
    EXPECT(irr_next_window_start(&H.ctx.cfg, 10 * 60) == 18 * 60, "proximo horario incorrecto");
    report(26, "Mediodia y fuera de horario posponen", ok);

    /* 27 Temperatura alta */
    setup(); auto_on(); ok = true;
    H.in.temp_c = 38; soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_HOT && H.starts == 0, "decision %s", decision_name(H.ctx.decision));
    report(27, "Temperatura alta pospone riego rutinario", ok);

    /* 28 Suelo que no responde */
    setup(); auto_on(); ok = true; H.gain = 0;
    soil(20); soil(20); run(2 * 17 * 60000);
    EXPECT(alarm_on(ALM_SOIL_NO_RESPONSE) && H.last_event_why == DEC_NO_RESPONSE, "fin %s",
           decision_name(H.last_event_why));
    H.ctx.have_last_event = false; soil(20); soil(20);
    EXPECT(H.ctx.decision == DEC_AUTO_LOCKED, "decision %s", decision_name(H.ctx.decision));
    EXPECT(manual(0.5f, false) == CMD_OK, "manual bloqueado por SOIL_NO_RESPONSE");
    irr_cmd_stop(&H.ctx, &H.in);
    report(28, "Suelo sin respuesta bloquea el automatico", ok);

    /* 29 Emergencia limitada */
    setup(); auto_on(); ok = true; H.gain = 1;
    H.in.minute_of_day = 13 * 60;
    soil(15); soil(15); run(20000); run(16 * 60000);
    EXPECT(H.last_event_why == DEC_EMERGENCY_DONE && H.starts == 1, "fin %s inicios %d",
           decision_name(H.last_event_why), H.starts);
    run(61 * 60000); soil(15); soil(15);     /* dry_confirm = 2 lecturas */
    EXPECT(H.ctx.decision == DEC_EMERGENCY_GAP && H.starts == 1, "decision %s inicios %d",
           decision_name(H.ctx.decision), H.starts);
    report(29, "Emergencia: un ciclo y espera entre emergencias", ok);

    /* 30 Flujo con bomba apagada (contacto pegado / fuga) */
    setup(); ok = true;
    run(6000);
    H.in.flow_pulses += 40; run(100);
    EXPECT(alarm_on(ALM_FLOW_WHEN_IDLE) && H.ctx.state == ST_FAULT, "estado %s", state_name(H.ctx.state));
    {
        char m[96];
        H.in.flow_pulses += 5;
        run(100);
        EXPECT(irr_cmd_clear_alarm(&H.ctx, &H.in, ALM_FLOW_WHEN_IDLE, m, sizeof(m)) == CMD_REJECTED,
               "CLEAR aceptado con pulsos activos");
    }
    report(30, "Flujo con todo apagado -> falla", ok);

    /* 31 Conflicto manual / automático */
    setup(); auto_on(); ok = true; H.gain = 1;
    soil(20); soil(20); run(25000);
    EXPECT(H.ctx.state == ST_INFILTRATION_WAIT, "estado %s", state_name(H.ctx.state));
    EXPECT(manual(1.0f, false) == CMD_REJECTED, "manual aceptado durante evento automatico");
    report(31, "Manual rechazado durante evento automatico", ok);

    /* 32 Salidas de potencia deshabilitadas */
    setup(); ok = true;
    H.in.outputs_enabled = false;
    {
        char m[96];
        EXPECT(manual(1.0f, false) == CMD_REJECTED, "manual aceptado sin potencia");
        EXPECT(irr_cmd_set_auto(&H.ctx, &H.in, true, m, sizeof(m)) == CMD_REJECTED, "auto aceptado sin potencia");
    }
    report(32, "Sin potencia no se puede regar", ok);

    /* 33 Conversiones de calibración */
    {
        riego_config_t c;
        config_defaults(&c);
        ok = true;
        float v630 = soil_mv_to_vwc(&c, 630);
        EXPECT(fabsf(v630 - 27.388f) < 0.05f, "630 mV -> %.3f", v630);
        c.tank_empty_cm = 120; c.tank_full_cm = 20;
        float p = tank_distance_to_pct(&c, 70);
        EXPECT(fabsf(p - 50.0f) < 0.01f, "70 cm -> %.2f %%", p);
        report(33, "Conversiones EC-5 (Act. 2.2) y nivel", ok);
    }

    printf("SELFTEST FIN: %d PASS, %d FAIL\n", s_pass, s_fail);
    return s_fail;
}
