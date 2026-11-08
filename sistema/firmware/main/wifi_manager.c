#include <stdio.h>
#include <string.h>

#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "sdkconfig.h"

#include "mqtt_manager.h"
#include "net_config.h"
#include "timekeeping.h"
#include "wifi_manager.h"

static const char *TAG = "wifi";

#define FAILS_BEFORE_SWITCH 4

static volatile bool s_connected;
static bool s_started;
static esp_timer_handle_t s_retry_timer;
static uint32_t s_backoff_ms = 1000;
static int s_slot = -1;
static uint32_t s_fails, s_reconnects;
static int s_last_reason;
static char s_ip[16] = "";
static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;

const char *wifi_reason_text(int r)
{
    switch (r) {
    case 0:   return "sin error";
    case 2:   return "autenticacion expirada";
    case 8:   return "el ESP32 se desconecto";
    case 15:  return "handshake de 4 vias expiro (contrasena incorrecta?)";
    case 201: return "red no encontrada (SSID incorrecto o red de 5 GHz)";
    case 202: return "autenticacion fallida (contrasena incorrecta?)";
    case 203: return "asociacion fallida";
    case 204: return "handshake fallido (contrasena incorrecta?)";
    case 205: return "conexion fallida";
    default:  return "otro motivo";
    }
}

/* Siguiente red habilitada después de 'from' (puede volver a la misma) */
static int next_slot(const net_config_t *c, int from)
{
    for (int k = 1; k <= NET_SLOTS; k++) {
        int i = (from + k) % NET_SLOTS;
        if (c->slot[i].enabled && c->slot[i].ssid[0]) {
            return i;
        }
    }
    return -1;
}

static int first_slot(const net_config_t *c)
{
    if (c->slot[c->preferred].enabled && c->slot[c->preferred].ssid[0]) {
        return c->preferred;
    }
    return next_slot(c, c->preferred);
}

static void apply_slot(int i)
{
    net_config_t c;
    net_config_get(&c);
    if (i < 0 || !c.slot[i].ssid[0]) {
        s_slot = -1;
        return;
    }
    s_slot = i;
    wifi_config_t wc = { 0 };
    strlcpy((char *)wc.sta.ssid, c.slot[i].ssid, sizeof(wc.sta.ssid));
    strlcpy((char *)wc.sta.password, c.slot[i].pass, sizeof(wc.sta.password));
    wc.sta.threshold.authmode = c.slot[i].pass[0] ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;
    wc.sta.pmf_cfg.capable = true;
    esp_wifi_set_config(WIFI_IF_STA, &wc);
    /* No se registra la contraseña */
    ESP_LOGI(TAG, "Intentando red '%s' (SSID '%s')", c.slot[i].name, c.slot[i].ssid);
}

static void retry_cb(void *arg)
{
    if (s_slot >= 0) {
        esp_wifi_connect();
    }
}

static void on_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        if (s_slot >= 0) {
            esp_wifi_connect();
        }
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        wifi_event_sta_disconnected_t *ev = (wifi_event_sta_disconnected_t *)data;
        bool was = s_connected;
        s_connected = false;
        s_last_reason = ev ? ev->reason : -1;
        taskENTER_CRITICAL(&s_mux);
        s_ip[0] = '\0';
        taskEXIT_CRITICAL(&s_mux);
        if (was) {
            ESP_LOGW(TAG, "Wi-Fi desconectado (%d: %s)", s_last_reason, wifi_reason_text(s_last_reason));
            mqtt_manager_network(false);
        }
        if (s_slot < 0) {
            return;
        }
        s_fails++;
        if (s_fails % FAILS_BEFORE_SWITCH == 0) {
            net_config_t c;
            net_config_get(&c);
            int n = next_slot(&c, s_slot);
            ESP_LOGW(TAG, "Sin exito en '%s' (%d: %s)%s", c.slot[s_slot].name, s_last_reason,
                     wifi_reason_text(s_last_reason), (n >= 0 && n != s_slot) ? "; se prueba otra red" : "");
            if (n >= 0 && n != s_slot) {
                apply_slot(n);
            }
        }
        esp_timer_stop(s_retry_timer);
        esp_timer_start_once(s_retry_timer, (uint64_t)s_backoff_ms * 1000);
        s_backoff_ms = (s_backoff_ms * 2 > 30000) ? 30000 : s_backoff_ms * 2;
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *ev = (ip_event_got_ip_t *)data;
        taskENTER_CRITICAL(&s_mux);
        snprintf(s_ip, sizeof(s_ip), IPSTR, IP2STR(&ev->ip_info.ip));
        taskEXIT_CRITICAL(&s_mux);
        ESP_LOGI(TAG, "Conectado, IP " IPSTR, IP2STR(&ev->ip_info.ip));
        s_connected = true;
        s_fails = 0;
        s_reconnects++;
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
    net_config_t c;
    net_config_get(&c);
    return net_config_has_any_ssid(&c);
#endif
}

void wifi_manager_start(void)
{
#if CONFIG_RIEGO_SIN_RED
    ESP_LOGW(TAG, "Compilacion para emulador QEMU: Wi-Fi deshabilitado");
    return;
#else
    /* Una falla de red nunca debe reiniciar el sistema */
#define NET_TRY(x) do { esp_err_t e_ = (x); if (e_ != ESP_OK) { \
        ESP_LOGE(TAG, "%s fallo: %s (sin red)", #x, esp_err_to_name(e_)); return; } } while (0)
    NET_TRY(esp_netif_init());
    NET_TRY(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t icfg = WIFI_INIT_CONFIG_DEFAULT();
    NET_TRY(esp_wifi_init(&icfg));
    NET_TRY(esp_wifi_set_storage(WIFI_STORAGE_RAM));    /* Las credenciales viven en net_config */
    NET_TRY(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_event, NULL));
    NET_TRY(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_event, NULL));
    const esp_timer_create_args_t targs = { .callback = retry_cb, .name = "wifi_retry" };
    NET_TRY(esp_timer_create(&targs, &s_retry_timer));
    NET_TRY(esp_wifi_set_mode(WIFI_MODE_STA));
#undef NET_TRY
    net_config_t c;
    net_config_get(&c);
    int first = first_slot(&c);
    apply_slot(first);
    if (esp_wifi_start() != ESP_OK) {
        ESP_LOGE(TAG, "esp_wifi_start fallo (sin red)");
        return;
    }
    s_started = true;
    /* Sin ahorro de energía del radio: con señal débil el modo de suspensión pierde paquetes
     * (ARP y MQTT) y el broker termina desconectando al ESP32 */
    esp_wifi_set_ps(WIFI_PS_NONE);
    if (first < 0) {
        ESP_LOGW(TAG, "Sin redes Wi-Fi configuradas: use WIFI <red> <ssid> <contrasena> en la consola");
    }
#endif
}

void wifi_manager_reconfigure(void)
{
    if (!s_started) {
        return;
    }
    net_config_t c;
    net_config_get(&c);
    esp_timer_stop(s_retry_timer);
    s_fails = 0;
    s_backoff_ms = 1000;
    int first = first_slot(&c);
    esp_wifi_disconnect();
    apply_slot(first);
    if (first >= 0) {
        esp_timer_start_once(s_retry_timer, 500 * 1000);
    }
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

void wifi_manager_diag(wifi_diag_t *out)
{
    memset(out, 0, sizeof(*out));
    out->connected = s_connected;
    net_config_t c;
    net_config_get(&c);
    if (s_slot >= 0) {
        strlcpy(out->slot, c.slot[s_slot].name, sizeof(out->slot));
        strlcpy(out->ssid, c.slot[s_slot].ssid, sizeof(out->ssid));
    }
    taskENTER_CRITICAL(&s_mux);
    strlcpy(out->ip, s_ip, sizeof(out->ip));
    taskEXIT_CRITICAL(&s_mux);
    wifi_ap_record_t ap;
    if (s_connected && esp_wifi_sta_get_ap_info(&ap) == ESP_OK) {
        out->rssi = ap.rssi;
        out->channel = ap.primary;
    }
    out->last_reason = s_last_reason;
    out->attempts = s_fails;
    out->reconnects = s_reconnects;
}

void wifi_manager_scan_print(void)
{
    if (!s_started) {
        printf("Wi-Fi no iniciado\n");
        return;
    }
    wifi_scan_config_t sc = { .show_hidden = false };
    if (esp_wifi_scan_start(&sc, true) != ESP_OK) {
        printf("No se pudo escanear (reintente en unos segundos)\n");
        return;
    }
    uint16_t n = 20;
    static wifi_ap_record_t recs[20];
    esp_wifi_scan_get_ap_records(&n, recs);
    printf("Redes visibles (el ESP32 solo usa 2.4 GHz):\n");
    for (int i = 0; i < n; i++) {
        printf("  %-32s canal %2d  %4d dBm  %s\n", (char *)recs[i].ssid, recs[i].primary, recs[i].rssi,
               recs[i].authmode == WIFI_AUTH_OPEN ? "ABIERTA" :
               (recs[i].authmode == WIFI_AUTH_WPA2_ENTERPRISE ? "EMPRESARIAL 802.1X (no soportada)" :
                "WPA/WPA2/WPA3 personal"));
    }
}
