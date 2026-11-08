/*
 * Comandos del sistema (desde MQTT o consola serial). Los comandos MQTT se
 * validan aquí (JSON, id obligatorio, duplicados, retenidos, antigüedad,
 * token opcional) y se envían a la tarea de control, que es la única que
 * modifica la lógica de riego. STOP apaga las salidas inmediatamente.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    C_NONE = 0,
    C_GET_STATUS, C_GET_CONFIG, C_GET_HISTORY,
    C_START_MANUAL, C_STOP,
    C_ENABLE_AUTO, C_DISABLE_AUTO,
    C_SET_PARAM,                /* key + sval                       */
    C_SET_HUM_RANGE,            /* f1 min, f2 objetivo, f3 máximo   */
    C_SET_MAX_LITERS,           /* f1 evento, f2 diario (NAN = sin cambio) */
    C_SET_FLOW_CAL,             /* f1 pulsos/L  ó  f2 pulsos + f3 mL */
    C_SET_TANK_CAL,             /* f1 vacío cm, f2 lleno cm          */
    C_SET_SCHEDULE,             /* i1 ventana, b1 habilitada, key inicio, sval fin */
    C_CLEAR_ALARM,              /* i1 alarma (-1 = todas)            */
    /* Solo consola serial */
    C_POWER, C_MODE, C_SIM, C_FACTORY, C_REBOOT, C_SELFTEST,
} cmd_type_t;

typedef enum { SRC_SERIAL = 0, SRC_MQTT } cmd_source_t;

typedef struct {
    cmd_type_t type;
    cmd_source_t src;
    char id[40];
    char name[28];              /* Nombre del comando para el ack   */
    float f1, f2, f3;
    bool b1;
    int i1;
    char key[32];
    char sval[48];
} command_t;

/* Procesa un mensaje del topic de comandos */
void commands_handle_mqtt(const char *data, int len, bool retained);

/* Anti-duplicados (expuesto para el autodiagnóstico) */
bool commands_seen_id(const char *id);     /* true si ya se recibió (y lo registra) */
void commands_reset_ids(void);

/* Nombre del comando MQTT -> tipo (C_NONE si no existe) */
cmd_type_t commands_type_from_name(const char *name);
