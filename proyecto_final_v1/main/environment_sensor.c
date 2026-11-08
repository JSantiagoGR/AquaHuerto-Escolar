#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_rom_sys.h"

#include "board.h"
#include "environment_sensor.h"

static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;

void environment_sensor_init(void)
{
    gpio_reset_pin(PIN_DHT22);
    gpio_set_direction(PIN_DHT22, GPIO_MODE_INPUT_OUTPUT_OD);
    gpio_set_pull_mode(PIN_DHT22, GPIO_PULLUP_ONLY);
    gpio_set_level(PIN_DHT22, 1);
}

static bool wait_level(int level, int64_t limit_us)
{
    int64_t t0 = esp_timer_get_time();
    while (gpio_get_level(PIN_DHT22) != level) {
        if (esp_timer_get_time() - t0 > limit_us) {
            return false;
        }
    }
    return true;
}

bool environment_sensor_read(float *temp_c, float *rh_pct)
{
    uint8_t d[5] = {0};
    bool ok = true;

    gpio_set_level(PIN_DHT22, 0);           /* Inicio: ≥ 1 ms en bajo */
    esp_rom_delay_us(2000);

    taskENTER_CRITICAL(&s_mux);
    gpio_set_level(PIN_DHT22, 1);
    if (!wait_level(0, 100) || !wait_level(1, 120) || !wait_level(0, 120)) {
        ok = false;
    }
    for (int i = 0; ok && i < 40; i++) {
        if (!wait_level(1, 80)) {
            ok = false;
            break;
        }
        int64_t t = esp_timer_get_time();
        if (!wait_level(0, 100)) {
            ok = false;
            break;
        }
        if (esp_timer_get_time() - t > 45) {
            d[i / 8] |= (uint8_t)(0x80 >> (i % 8));
        }
    }
    taskEXIT_CRITICAL(&s_mux);

    if (!ok || (uint8_t)(d[0] + d[1] + d[2] + d[3]) != d[4]) {
        return false;
    }
    float h = (float)((d[0] << 8) | d[1]) / 10.0f;
    float t = (float)(((d[2] & 0x7F) << 8) | d[3]) / 10.0f;
    if (d[2] & 0x80) {
        t = -t;
    }
    if (h < 0.0f || h > 100.0f || t < -40.0f || t > 80.0f) {
        return false;
    }
    *temp_c = t;
    *rh_pct = h;
    return true;
}
