/*
 * Cliente MQTT (esp-mqtt). Broker, credenciales y topic base salen de
 * net_config (NVS): se cambian sin recompilar.
 * Topics bajo <base> (p. ej. huerto/casa/esp32_01):
 *   status (retenido, LWT), telemetry, state (retenido), config (retenido),
 *   decision (retenido), event, alarm, ack, history, ia (retenido),
 *   weather (retenido), diag, telemetry_buffer; suscripción a command.
 * Las publicaciones se ponen en cola (no bloquean la tarea de control).
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

void mqtt_manager_init(void);
void mqtt_manager_network(bool up);            /* Llamado por wifi_manager */
bool mqtt_manager_connected(void);
bool mqtt_manager_configured(void);
/* sub = "telemetry", "state", ... ; devuelve false si no está conectado */
bool mqtt_publish(const char *sub, const char *json, int qos, bool retain);
/* Se pone en true al conectar; el controlador lo consume para republicar */
bool mqtt_manager_take_connected_flag(void);
/* Publicaciones descartadas (cola llena o sin conexión al momento de enviar) */
uint32_t mqtt_manager_dropped(void);
const char *mqtt_manager_base(void);
const char *mqtt_manager_device(void);
const char *mqtt_manager_client_id(void);
const char *mqtt_manager_broker(void);          /* URI sin credenciales */
uint32_t mqtt_manager_connect_count(void);
/* Recarga net_config y reconecta (tras cambiar broker o topic) */
void mqtt_manager_reconfigure(void);
/* Prueba un broker nuevo: si no conecta en 'timeout_s' vuelve al anterior.
 * Si conecta, lo guarda en NVS. Devuelve false si los datos son inválidos. */
bool mqtt_manager_try_broker(const char *uri, const char *user, const char *pass, int timeout_s);
/* Estado del último cambio de broker: "NONE", "TESTING", "OK", "REVERTED" */
const char *mqtt_manager_broker_change_state(void);
