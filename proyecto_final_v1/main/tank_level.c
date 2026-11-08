#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_rom_sys.h"

#include "board.h"
#include "tank_level.h"

#define N_PINGS        5
#define PING_GAP_MS    60
#define MAX_SPREAD_CM  5.0f

void tank_level_init(void)
{
    gpio_reset_pin(PIN_PING);
    gpio_set_direction(PIN_PING, GPIO_MODE_INPUT);
    gpio_set_pull_mode(PIN_PING, GPIO_PULLDOWN_ONLY);
}

static bool wait_level(int level, int64_t limit_us)
{
    int64_t t0 = esp_timer_get_time();
    while (gpio_get_level(PIN_PING) != level) {
        if (esp_timer_get_time() - t0 > limit_us) {
            return false;
        }
    }
    return true;
}

/* Hoja de datos: disparo ≥ 2 µs (5 µs típ.), eco de 115 µs a 18.5 ms */
static bool ping_echo_us(int64_t *echo)
{
    gpio_set_direction(PIN_PING, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_PING, 0);
    esp_rom_delay_us(2);
    gpio_set_level(PIN_PING, 1);
    esp_rom_delay_us(5);
    gpio_set_level(PIN_PING, 0);
    gpio_set_direction(PIN_PING, GPIO_MODE_INPUT);
    if (!wait_level(1, 2000)) {
        return false;
    }
    int64_t t = esp_timer_get_time();
    if (!wait_level(0, 25000)) {
        return false;
    }
    *echo = esp_timer_get_time() - t;
    return true;
}

static int cmp_float(const void *a, const void *b)
{
    float x = *(const float *)a, y = *(const float *)b;
    return (x > y) - (x < y);
}

float tank_distance_to_pct(const riego_config_t *cfg, float d)
{
    float span = cfg->tank_empty_cm - cfg->tank_full_cm;
    if (span <= 0.0f) {
        return NAN;
    }
    float pct = (cfg->tank_empty_cm - d) / span * 100.0f;
    if (pct < 0.0f) {
        pct = 0.0f;
    }
    if (pct > 100.0f) {
        pct = 100.0f;
    }
    return pct;
}

void tank_level_measure(const riego_config_t *cfg, float temp_c, tank_reading_t *out)
{
    memset(out, 0, sizeof(*out));
    out->level_pct = NAN;
    out->calibrated = config_tank_calibrated(cfg);

    float t = isnan(temp_c) ? 20.0f : temp_c;
    float c_cm_us = (331.3f + 0.606f * t) * 100.0f / 1e6f;   /* cm/µs */

    float d[N_PINGS];
    int n = 0;
    for (int i = 0; i < N_PINGS; i++) {
        int64_t e = 0;
        if (ping_echo_us(&e)) {
            float dist = (float)e * c_cm_us / 2.0f;
            if (dist >= 2.0f && dist <= 300.0f) {
                d[n++] = dist;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(PING_GAP_MS));
    }
    out->samples_ok = n;
    if (n < 3) {
        out->status = "SIN_ECO";
        return;
    }
    qsort(d, n, sizeof(float), cmp_float);
    out->distance_cm = d[n / 2];
    out->spread_cm = d[n - 1] - d[0];
    if (out->spread_cm > MAX_SPREAD_CM) {
        out->status = "INESTABLE";
        return;
    }
    out->valid = true;
    if (out->calibrated) {
        out->level_pct = tank_distance_to_pct(cfg, out->distance_cm);
        /* Más lejos que "vacío" + margen: el sensor apunta mal o el tinaco cambió */
        if (out->distance_cm > cfg->tank_empty_cm + 10.0f) {
            out->status = "FUERA_DE_RANGO";
            out->valid = false;
            return;
        }
        out->status = "OK";
    } else {
        out->status = "NO_CALIBRADO";
    }
}
