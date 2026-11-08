#pragma once

#include <stdbool.h>

/* Conecta en modo estación con las credenciales de sdkconfig.secrets.
 * Reconecta sola con espera creciente (1 s a 60 s). Si no hay SSID, no hace nada. */
void wifi_manager_start(void);
bool wifi_manager_connected(void);
bool wifi_manager_configured(void);
int wifi_manager_rssi(void);
