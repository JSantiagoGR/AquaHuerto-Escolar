/*
 * Tarea de control (núcleo 0, cada 20 ms): reúne entradas, ejecuta la lógica
 * pura, aplica las salidas, atiende comandos, guarda contadores e historial y
 * publica telemetría, estado, decisiones, eventos y alarmas.
 */
#pragma once

#include <stdbool.h>
#include "commands.h"

void controller_start(bool config_was_reset);
bool controller_post(const command_t *cmd);
/* STOP inmediato desde cualquier tarea (apaga GPIO antes de encolar) */
void controller_emergency_stop(const command_t *cmd);
/* Respuesta directa (errores de formato detectados antes de encolar) */
void controller_ack(const command_t *cmd, const char *status, const char *msg);
void controller_set_console_log(bool on);
