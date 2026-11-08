#include <string.h>

#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "sdkconfig.h"

#include "mqtt_manager.h"
#include "timekeeping.h"
#include "wifi_manager.h"

static const char *TAG = "wifi";

static volatile bool s_connected;
static esp_timer_handle_t s_retry_timer;
static uint32_t s_backoff_ms = 1000;

static void retry_cb(void *arg)
{
    esp_wifi_connect();
}

static void on_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        bool was = s_connected;
        s_connected = false;
        if (was) {
            ESP_LOGW(TAG, "Wi-Fi desconectado");
            mqtt_manager_network(false);
        }
        esp_timer_stop(s_retry_timer);
        esp_timer_start_once(s_retry_timer, (uint64_t)s_backoff_ms * 1000);
        s_backoff_ms = (s_backoff_ms * 2 > 60000) ? 60000 : s_backoff_ms * 2;
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *ev = (ip_event_got_ip_t *)data;
        ESP_LOGI(TAG, "Conectado, IP " IPSTR, IP2STR(&ev->ip_info.ip));
        s_connected = true;
        s_backoff_ms = 1000;
        time_start_sntp();
        mqtt_manager_network(true);
    }
}

bool wifi_manager_configured(void)
{
#if CONFIG_RIEGO_SIN_RED
    return false;
#else
    return strlen(CONFIG_RIEGO_WIFI_SSID) > 0;
#endif
}

void wifi_manager_start(void)
{
#if CONFIG_RIEGO_SIN_RED
    ESP_LOGW(TAG, "Compilacion para emulador QEMU: Wi-Fi deshabilitado");
    return;
#endif
    if (!wifi_manager_configured()) {
        ESP_LOGW(TAG, "Sin SSID configurado: funcionamiento local sin red");
        return;
    }
    /* Una falla de red nunca debe reiniciar el sistema: se registra y se sigue
     * funcionando en local con todas las protecciones. */
#define NET_TRY(x) do { esp_err_t e_ = (x); if (e_ != ESP_OK) { \
        ESP_LOGE(TAG, "%s fallo: %s (sin red)", #x, esp_err_to_name(e_)); return; } } while (0)
    NET_TRY(esp_netif_init());
    NET_TRY(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t icfg = WIFI_INIT_CONFIG_DEFAULT();
    NET_TRY(esp_wifi_init(&icfg));
    NET_TRY(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_event, NULL));
    NET_TRY(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_event, NULL));

    const esp_timer_create_args_t targs = { .callback = retry_cb, .name = "wifi_retry" };
    NET_TRY(esp_timer_create(&targs, &s_retry_timer));

    wifi_config_t wc = { 0 };
    strlcpy((char *)wc.sta.ssid, CONFIG_RIEGO_WIFI_SSID, sizeof(wc.sta.ssid));
    strlcpy((char *)wc.sta.password, CONFIG_RIEGO_WIFI_PASSWORD, sizeof(wc.sta.password));
    wc.sta.threshold.authmode = strlen(CONFIG_RIEGO_WIFI_PASSWORD) ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;
    NET_TRY(esp_wifi_set_mode(WIFI_MODE_STA));
    NET_TRY(esp_wifi_set_config(WIFI_IF_STA, &wc));
    NET_TRY(esp_wifi_start());
#undef NET_TRY
    /* No se registra la contraseña en el log */
    ESP_LOGI(TAG, "Conectando a la red configurada (SSID de %d caracteres)", (int)strlen(CONFIG_RIEGO_WIFI_SSID));
}

bool wifi_manager_connected(void)
{
    return s_connected;
}

int wifi_manager_rssi(void)
{
    wifi_ap_record_t ap;
    if (s_connected && esp_wifi_sta_get_ap_info(&ap) == ESP_OK) {
        return ap.rssi;
    }
    return 0;
}
