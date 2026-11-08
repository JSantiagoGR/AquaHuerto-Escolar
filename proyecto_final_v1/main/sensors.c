#include <math.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_timer.h"
#include "esp_log.h"

#include "configuration.h"
#include "environment_sensor.h"
#include "simulation.h"
#include "timekeeping.h"
#include "sensors.h"

static const char *TAG = "sensors";

#define ENV_INTERVAL_MS   10000
#define ENV_FAIL_LIMIT    3        /* Fallos seguidos antes de marcar inválido */

static SemaphoreHandle_t s_mtx;
static sensor_snapshot_t s_snap;
static volatile bool s_soil_request;
static volatile uint32_t s_soil_interval_s = 300;
static int64_t s_soil_ms, s_tank_ms, s_env_ms;

static uint32_t now_ms(void)
{
    return (uint32_t)(esp_timer_get_time() / 1000);
}

void sensors_get(sensor_snapshot_t *out)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    *out = s_snap;
    uint32_t n = now_ms();
    out->soil_age_s = (uint32_t)((n - s_soil_ms) / 1000);
    out->tank_age_s = (uint32_t)((n - s_tank_ms) / 1000);
    xSemaphoreGive(s_mtx);
}

void sensors_request_soil(void)
{
    s_soil_request = true;
}

void sensors_set_soil_interval_s(uint32_t s)
{
    s_soil_interval_s = s;
}

static void measure_soil(const riego_config_t *cfg)
{
    soil_reading_t r;
    sim_state_t *sm = sim();
    if (sm->active) {
        memset(&r, 0, sizeof(r));
        r.valid = sm->soil_valid;
        r.vwc_pct = sm->soil_vwc;
        r.mv = (int)lroundf((sm->soil_vwc - cfg->ec5_offset) / cfg->ec5_slope);
        r.in_cal_range = r.mv >= (int)cfg->ec5_cal_mv_lo && r.mv <= (int)cfg->ec5_cal_mv_hi;
        r.status = sm->soil_valid ? "SIMULADO" : "SIMULADO_FALLA";
    } else {
        soil_sensor_measure(cfg, &r);
    }
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    s_snap.soil = r;
    s_snap.soil_seq++;
    s_snap.soil_epoch = time_epoch();
    s_snap.simulated = sm->active;
    xSemaphoreGive(s_mtx);
}

static void measure_tank(const riego_config_t *cfg, float temp)
{
    tank_reading_t r;
    sim_state_t *sm = sim();
    if (sm->active) {
        memset(&r, 0, sizeof(r));
        r.calibrated = (sm->tank_mode != SIM_TANK_UNCAL);
        r.valid = (sm->tank_mode != SIM_TANK_FAIL);
        r.samples_ok = r.valid ? 5 : 0;
        r.level_pct = r.calibrated ? sm->tank_pct : NAN;
        r.distance_cm = r.valid ? 100.0f - sm->tank_pct * 0.8f : 0.0f;
        r.status = !r.valid ? "SIMULADO_SIN_ECO" : (r.calibrated ? "SIMULADO" : "SIMULADO_NO_CALIBRADO");
    } else {
        tank_level_measure(cfg, temp, &r);
    }
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    s_snap.tank = r;
    xSemaphoreGive(s_mtx);
}

static void measure_env(void)
{
    float t = NAN, h = NAN;
    bool ok;
    sim_state_t *sm = sim();
    if (sm->active) {
        ok = sm->env_valid;
        t = sm->temp_c;
        h = sm->rh;
    } else {
        ok = environment_sensor_read(&t, &h);
        if (!ok) {
            vTaskDelay(pdMS_TO_TICKS(2100));       /* Un reintento (mínimo 2 s) */
            ok = environment_sensor_read(&t, &h);
        }
    }
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    if (ok) {
        s_snap.temp_c = t;
        s_snap.rh_pct = h;
        s_snap.env_fail_count = 0;
        s_snap.env_valid = true;
        s_snap.env_last_valid_epoch = time_epoch();
        s_snap.env_last_valid_uptime_s = now_ms() / 1000;
    } else {
        if (s_snap.env_fail_count < 255) {
            s_snap.env_fail_count++;
        }
        if (s_snap.env_fail_count >= ENV_FAIL_LIMIT || sm->active) {
            s_snap.env_valid = false;
        }
    }
    xSemaphoreGive(s_mtx);
}

static void sensors_task(void *arg)
{
    riego_config_t cfg;
    /* El DHT22 necesita ~2 s tras energizarse */
    vTaskDelay(pdMS_TO_TICKS(2000));
    config_get(&cfg);
    measure_env();
    s_env_ms = now_ms();
    measure_tank(&cfg, s_snap.env_valid ? s_snap.temp_c : NAN);
    s_tank_ms = now_ms();
    measure_soil(&cfg);
    s_soil_ms = now_ms();

    while (true) {
        config_get(&cfg);
        uint32_t n = now_ms();
        sim_state_t *sm = sim();
        uint32_t speed = (sm->active && sm->speed > 0) ? sm->speed : 1;

        uint32_t soil_ms = s_soil_interval_s * 1000 / speed;
        if (s_soil_request || (n - s_soil_ms) >= soil_ms) {
            s_soil_request = false;
            measure_soil(&cfg);
            s_soil_ms = now_ms();
        }
        if ((n - s_tank_ms) >= (uint32_t)(cfg.tank_interval_s * 1000) / speed) {
            float temp = s_snap.env_valid ? s_snap.temp_c : NAN;
            measure_tank(&cfg, temp);
            s_tank_ms = now_ms();
        }
        if ((n - s_env_ms) >= ENV_INTERVAL_MS / (speed > 4 ? 4 : speed)) {
            measure_env();
            s_env_ms = now_ms();
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void sensors_start(void)
{
    s_mtx = xSemaphoreCreateMutex();
    memset(&s_snap, 0, sizeof(s_snap));
    s_snap.soil.status = "SIN_LECTURA";
    s_snap.tank.status = "SIN_LECTURA";
    s_snap.tank.level_pct = NAN;
    s_snap.temp_c = NAN;
    s_snap.rh_pct = NAN;
    environment_sensor_init();
    tank_level_init();
    soil_sensor_init();
    xTaskCreatePinnedToCore(sensors_task, "sensors", 4096, NULL, 4, NULL, 1);
    ESP_LOGI(TAG, "Tarea de sensores iniciada en el nucleo 1");
}
