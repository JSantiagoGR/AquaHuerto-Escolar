#include "driver/pulse_cnt.h"
#include "driver/gpio.h"
#include "esp_log.h"

#include "board.h"
#include "flow_sensor.h"

static const char *TAG = "flow";
static pcnt_unit_handle_t s_unit;
static volatile uint32_t s_sim_pulses;

#define PCNT_HIGH 30000
#define PCNT_LOW  (-30000)

#define TRY(x) do { esp_err_t e_ = (x); if (e_ != ESP_OK) { \
        ESP_LOGE(TAG, "%s fallo: %s", #x, esp_err_to_name(e_)); goto fail; } } while (0)

bool flow_sensor_init(void)
{
    /* accum_count: el driver acumula al llegar a los límites (contador de 32 bits) */
    const pcnt_unit_config_t ucfg = {
        .low_limit = PCNT_LOW,
        .high_limit = PCNT_HIGH,
        .flags.accum_count = 1,
    };
    const pcnt_glitch_filter_config_t fcfg = { .max_glitch_ns = 10000 };
    const pcnt_chan_config_t ccfg = {
        .edge_gpio_num = PIN_FLOW,
        .level_gpio_num = -1,
    };
    pcnt_channel_handle_t ch = NULL;

    TRY(pcnt_new_unit(&ucfg, &s_unit));
    TRY(pcnt_unit_set_glitch_filter(s_unit, &fcfg));
    TRY(pcnt_new_channel(s_unit, &ccfg, &ch));
    TRY(pcnt_channel_set_edge_action(ch, PCNT_CHANNEL_EDGE_ACTION_INCREASE,
                                     PCNT_CHANNEL_EDGE_ACTION_HOLD));
    TRY(pcnt_unit_add_watch_point(s_unit, PCNT_HIGH));
    TRY(pcnt_unit_add_watch_point(s_unit, PCNT_LOW));

    /* Pull-up interno a 3.3 V: con el diodo, el sensor solo lleva la línea a 0 */
    gpio_set_pull_mode(PIN_FLOW, GPIO_PULLUP_ONLY);

    TRY(pcnt_unit_enable(s_unit));
    TRY(pcnt_unit_clear_count(s_unit));
    TRY(pcnt_unit_start(s_unit));
    ESP_LOGI(TAG, "YF-S201 en GPIO%d (PCNT)", PIN_FLOW);
    return true;

fail:
    /* Sin contador no hay pulsos: cualquier riego terminará por NO_FLOW (seguro) */
    s_unit = NULL;
    ESP_LOGE(TAG, "Caudalimetro NO disponible");
    return false;
}

uint32_t flow_sensor_total_pulses(void)
{
    int count = 0;
    if (s_unit) {
        pcnt_unit_get_count(s_unit, &count);
    }
    if (count < 0) {
        count = 0;
    }
    return (uint32_t)count + s_sim_pulses;
}

void flow_sensor_add_sim_pulses(uint32_t n)
{
    s_sim_pulses += n;
}
