#include "freertos/FreeRTOS.h"
#include "driver/gpio.h"
#include "esp_timer.h"

#include "board.h"
#include "actuators.h"

#if RELAY_ACTIVE_LOW
#define LVL_ON  0
#define LVL_OFF 1
#else
#define LVL_ON  1
#define LVL_OFF 0
#endif

static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
static bool s_pump_cmd, s_valve_cmd;
static bool s_pump_phys, s_valve_phys;
static bool s_power_enabled = false;
static bool s_simulation = false;
static bool s_latch = false;
static int64_t s_pump_on_since_us = 0;

/* Escribe los GPIO según el estado lógico y las condiciones de habilitación.
 * Debe llamarse con s_mux tomado. */
static void apply_locked(void)
{
    bool allowed = s_power_enabled && !s_simulation && !s_latch;
    bool valve = allowed && s_valve_cmd;
    bool pump = allowed && s_pump_cmd && valve;     /* Enclavamiento bomba-válvula */

    /* Orden seguro: primero apagar lo que se apaga */
    if (!pump) {
        gpio_set_level(PIN_PUMP, LVL_OFF);
    }
    if (!valve) {
        gpio_set_level(PIN_VALVE, LVL_OFF);
    }
    if (valve) {
        gpio_set_level(PIN_VALVE, LVL_ON);
    }
    if (pump) {
        gpio_set_level(PIN_PUMP, LVL_ON);
    }
    if (pump && !s_pump_phys) {
        s_pump_on_since_us = esp_timer_get_time();
    }
    s_pump_phys = pump;
    s_valve_phys = valve;
}

void actuators_init(void)
{
    /* Nivel inactivo ANTES de habilitar la salida (sin pulso de activación) */
    gpio_set_level(PIN_PUMP, LVL_OFF);
    gpio_set_level(PIN_VALVE, LVL_OFF);
    const gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << PIN_PUMP) | (1ULL << PIN_VALVE),
        .mode = GPIO_MODE_INPUT_OUTPUT,     /* Permite leer el nivel real */
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
    gpio_set_level(PIN_PUMP, LVL_OFF);
    gpio_set_level(PIN_VALVE, LVL_OFF);
}

void actuators_set(bool pump, bool valve)
{
    taskENTER_CRITICAL(&s_mux);
    s_pump_cmd = pump;
    s_valve_cmd = valve;
    apply_locked();
    taskEXIT_CRITICAL(&s_mux);
}

void actuators_set_enable(bool power_enabled, bool simulation)
{
    taskENTER_CRITICAL(&s_mux);
    s_power_enabled = power_enabled;
    s_simulation = simulation;
    apply_locked();
    taskEXIT_CRITICAL(&s_mux);
}

void actuators_emergency_off(void)
{
    taskENTER_CRITICAL(&s_mux);
    s_latch = true;
    s_pump_cmd = false;
    s_valve_cmd = false;
    apply_locked();
    taskEXIT_CRITICAL(&s_mux);
}

void actuators_clear_latch(void)
{
    taskENTER_CRITICAL(&s_mux);
    s_latch = false;
    apply_locked();
    taskEXIT_CRITICAL(&s_mux);
}

bool actuators_latched(void) { return s_latch; }
bool actuators_pump_cmd(void) { return s_pump_cmd; }
bool actuators_valve_cmd(void) { return s_valve_cmd; }
bool actuators_pump_physical(void) { return s_pump_phys; }
bool actuators_valve_physical(void) { return s_valve_phys; }
bool actuators_outputs_enabled(void) { return s_power_enabled && !s_simulation; }

uint32_t actuators_pump_physical_on_ms(void)
{
    if (!s_pump_phys) {
        return 0;
    }
    return (uint32_t)((esp_timer_get_time() - s_pump_on_since_us) / 1000);
}
