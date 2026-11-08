#include <stdio.h>
#include <string.h>

#include "esp_timer.h"
#include "esp_log.h"

#include "actuators.h"
#include "safety.h"

static const char *TAG = "safety";

#define HARD_PUMP_LIMIT_MS   330000u    /* Tope absoluto (5.5 min), no configurable */
#define PUMP_LIMIT_MARGIN_MS 10000u     /* Margen sobre el límite lógico            */
#define HEARTBEAT_LIMIT_US   3000000    /* 3 s sin señales de la tarea de control   */

static esp_timer_handle_t s_timer;
static volatile int64_t s_last_beat_us;
static volatile uint32_t s_pump_limit_ms = 90000;
static volatile bool s_trip;
static char s_reason[64];

static void trip(const char *why)
{
    actuators_emergency_off();
    if (!s_trip) {
        strncpy(s_reason, why, sizeof(s_reason) - 1);
        s_trip = true;
    }
}

static void check_cb(void *arg)
{
    bool any_on = actuators_pump_physical() || actuators_valve_physical();
    uint32_t on_ms = actuators_pump_physical_on_ms();
    uint32_t limit = s_pump_limit_ms + PUMP_LIMIT_MARGIN_MS;
    if (limit > HARD_PUMP_LIMIT_MS) {
        limit = HARD_PUMP_LIMIT_MS;
    }
    if (on_ms > limit) {
        trip("BOMBA_SUPERO_LIMITE_DURO");
    }
    if (any_on && (esp_timer_get_time() - s_last_beat_us) > HEARTBEAT_LIMIT_US) {
        trip("TAREA_DE_CONTROL_SIN_RESPUESTA");
    }
}

void safety_start(void)
{
    s_last_beat_us = esp_timer_get_time();
    const esp_timer_create_args_t args = {
        .callback = check_cb,
        .name = "safety",
        .dispatch_method = ESP_TIMER_TASK,
    };
    ESP_ERROR_CHECK(esp_timer_create(&args, &s_timer));
    ESP_ERROR_CHECK(esp_timer_start_periodic(s_timer, 100000));
    ESP_LOGI(TAG, "Supervisor de seguridad activo (limite duro %u s)", (unsigned)(HARD_PUMP_LIMIT_MS / 1000));
}

void safety_heartbeat(void)
{
    s_last_beat_us = esp_timer_get_time();
}

void safety_set_pump_limit_ms(uint32_t ms)
{
    s_pump_limit_ms = ms;
}

bool safety_take_trip(char *reason, size_t len)
{
    if (!s_trip) {
        return false;
    }
    snprintf(reason, len, "%s", s_reason);
    s_trip = false;
    return true;
}
