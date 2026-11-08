/*
 * Configuración de red persistente (NVS, espacio "net"), separada de la
 * configuración de riego: redes Wi-Fi (casa, Tec, huerto), broker MQTT,
 * topic base e identidad del dispositivo. Se cambia por consola serial sin
 * recompilar. Las contraseñas NUNCA se imprimen ni se publican.
 *
 * Valores iniciales (primer arranque): los de sdkconfig.secrets (Kconfig).
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#define NET_SLOTS       3
#define NET_SSID_MAX    33
#define NET_PASS_MAX    65

typedef struct {
    char name[12];              /* "casa", "tec", "huerto"                   */
    char ssid[NET_SSID_MAX];
    char pass[NET_PASS_MAX];
    uint8_t enabled;
    uint8_t pad[1];
} wifi_slot_t;

typedef struct {
    uint32_t magic;
    uint32_t version;
    wifi_slot_t slot[NET_SLOTS];
    uint8_t preferred;          /* Red que se intenta primero                */
    uint8_t pad[3];
    char mqtt_uri[100];         /* mqtt://IP:1883                            */
    char mqtt_user[33];
    char mqtt_pass[65];
    char base_topic[64];        /* huerto/casa/esp32_01                      */
    char device_id[24];         /* esp32_01                                  */
    char env_name[12];          /* casa | final                              */
    uint32_t crc;
} net_config_t;

void net_config_init(void);
void net_config_get(net_config_t *out);
bool net_config_save(const net_config_t *c);        /* Valida y guarda */
int net_config_slot_find(const net_config_t *c, const char *name);   /* -1 si no existe */
bool net_config_has_any_ssid(const net_config_t *c);
/* Muestra la configuración SIN contraseñas */
void net_config_print(void);
