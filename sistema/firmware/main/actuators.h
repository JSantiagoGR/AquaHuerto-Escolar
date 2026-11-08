/*
 * Bomba y electroválvula (ON/OFF, sin PWM). La salida física solo se activa si:
 *   - las salidas de potencia están habilitadas (config power_enabled),
 *   - no está activo el modo simulación,
 *   - no hay un paro de emergencia enclavado,
 *   - y, para la bomba, la válvula también está activa (enclavamiento).
 * En cualquier otro caso los GPIO quedan en el nivel INACTIVO.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

void actuators_init(void);                         /* Primera llamada en app_main */
void actuators_set(bool pump, bool valve);         /* Orden lógica del controlador */
void actuators_set_enable(bool power_enabled, bool simulation);
void actuators_emergency_off(void);                /* Apagado inmediato desde cualquier tarea */
void actuators_clear_latch(void);
bool actuators_latched(void);

bool actuators_pump_cmd(void);                     /* Estado lógico pedido */
bool actuators_valve_cmd(void);
bool actuators_pump_physical(void);                /* GPIO realmente activo */
bool actuators_valve_physical(void);
bool actuators_outputs_enabled(void);              /* power_enabled y no simulación */
uint32_t actuators_pump_physical_on_ms(void);      /* Tiempo continuo con bomba física activa */
