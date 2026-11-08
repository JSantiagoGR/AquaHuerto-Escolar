/*
 * Wi-Fi en modo estación con las redes guardadas en NVS (net_config).
 * Intenta la red preferida; tras varios fallos prueba la siguiente red
 * habilitada. Reconecta sola con espera creciente (1 s a 30 s).
 * El riego NUNCA depende de la red: todas las protecciones son locales.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool connected;
    char slot[12];
    char ssid[33];
    char ip[16];
    int rssi;
    int channel;
    int last_reason;            /* Código de desconexión de ESP-IDF          */
    uint32_t attempts;          /* Intentos fallidos seguidos                */
    uint32_t reconnects;        /* Conexiones logradas desde el arranque     */
} wifi_diag_t;

void wifi_manager_start(void);
void wifi_manager_reconfigure(void);    /* Recarga net_config y reconecta */
bool wifi_manager_connected(void);
bool wifi_manager_configured(void);
int wifi_manager_rssi(void);
void wifi_manager_diag(wifi_diag_t *out);
void wifi_manager_scan_print(void);     /* Lista redes visibles (2.4 GHz) */
const char *wifi_reason_text(int reason);
