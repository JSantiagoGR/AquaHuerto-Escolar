/*
 * Cliente MQTT (esp-mqtt). Topics bajo CONFIG_RIEGO_MQTT_BASE_TOPIC:
 *   status (retenido, LWT), telemetry, state (retenido), config (retenido),
 *   decision (retenido), event, alarm, ack, history; suscripción a command.
 * Las publicaciones se ponen en cola (no bloquean la tarea de control).
 */
#pragma once

#include <stdbool.h>

void mqtt_manager_init(void);
void mqtt_manager_network(bool up);            /* Llamado por wifi_manager */
bool mqtt_manager_connected(void);
bool mqtt_manager_configured(void);
/* sub = "telemetry", "state", ... ; devuelve false si no está conectado */
bool mqtt_publish(const char *sub, const char *json, int qos, bool retain);
/* Se pone en true al conectar; el controlador lo consume para republicar */
bool mqtt_manager_take_connected_flag(void);
const char *mqtt_manager_base(void);
