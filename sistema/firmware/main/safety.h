/*
 * Supervisor de seguridad independiente de la lógica de riego.
 * Un temporizador de alta prioridad (esp_timer, cada 100 ms) apaga las salidas si:
 *   - la bomba física lleva encendida más que el límite duro, o
 *   - la tarea de control dejó de dar señales de vida con alguna salida activa.
 * Además la tarea de control está suscrita al watchdog de tareas (reinicio).
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

void safety_start(void);
void safety_heartbeat(void);
void safety_set_pump_limit_ms(uint32_t ms);     /* Límite lógico (pump_max_s) */
/* Devuelve true una vez si hubo un corte; copia el motivo */
bool safety_take_trip(char *reason, size_t len);
