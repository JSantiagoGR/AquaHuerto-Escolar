/*
 * Caudalímetro YF-S201 con el contador de pulsos por hardware (PCNT),
 * misma configuración probada en la Prueba 02/03 (GPIO19, flanco de subida,
 * filtro de 10 µs, pull-up interno), con acumulación de 32 bits.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

/* false si el PCNT no se pudo iniciar (sin pulsos: los riegos terminan por NO_FLOW) */
bool flow_sensor_init(void);
/* Total de pulsos desde el arranque (monótono). Incluye pulsos simulados. */
uint32_t flow_sensor_total_pulses(void);
/* Solo para simulación: agrega pulsos virtuales */
void flow_sensor_add_sim_pulses(uint32_t n);
