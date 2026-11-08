#include <stdio.h>
#include <string.h>
#include <strings.h>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_rom_crc.h"
#include "nvs.h"
#include "sdkconfig.h"

#include "net_config.h"

static const char *TAG = "netcfg";
#define NVS_NS      "net"
#define NVS_KEY     "cfg"
#define NET_MAGIC   0x4E455431u     /* "NET1" */
#define NET_VERSION 1u

static net_config_t s_cfg;
static SemaphoreHandle_t s_mtx;

static uint32_t calc_crc(const net_config_t *c)
{
    return esp_rom_crc32_le(0, (const uint8_t *)c, offsetof(net_config_t, crc));
}

static void defaults(net_config_t *c)
{
    memset(c, 0, sizeof(*c));
    c->magic = NET_MAGIC;
    c->version = NET_VERSION;
    strlcpy(c->slot[0].name, "casa", sizeof(c->slot[0].name));
    strlcpy(c->slot[1].name, "tec", sizeof(c->slot[1].name));
    strlcpy(c->slot[2].name, "huerto", sizeof(c->slot[2].name));
#ifdef CONFIG_RIEGO_WIFI_SSID
    strlcpy(c->slot[0].ssid, CONFIG_RIEGO_WIFI_SSID, sizeof(c->slot[0].ssid));
    strlcpy(c->slot[0].pass, CONFIG_RIEGO_WIFI_PASSWORD, sizeof(c->slot[0].pass));
#endif
    c->slot[0].enabled = c->slot[0].ssid[0] != '\0';
    c->preferred = 0;
    strlcpy(c->mqtt_uri, CONFIG_RIEGO_MQTT_URI, sizeof(c->mqtt_uri));
    strlcpy(c->mqtt_user, CONFIG_RIEGO_MQTT_USERNAME, sizeof(c->mqtt_user));
    strlcpy(c->mqtt_pass, CONFIG_RIEGO_MQTT_PASSWORD, sizeof(c->mqtt_pass));
    strlcpy(c->base_topic, CONFIG_RIEGO_MQTT_BASE_TOPIC, sizeof(c->base_topic));
    strlcpy(c->device_id, CONFIG_RIEGO_DEVICE_ID, sizeof(c->device_id));
    strlcpy(c->env_name, CONFIG_RIEGO_ENV_NAME, sizeof(c->env_name));
}

static bool terminated(const char *s, size_t n)
{
    return memchr(s, '\0', n) != NULL;
}

static bool valid(const net_config_t *c)
{
    if (c->magic != NET_MAGIC || c->version != NET_VERSION || c->preferred >= NET_SLOTS) {
        return false;
    }
    for (int i = 0; i < NET_SLOTS; i++) {
        if (!terminated(c->slot[i].name, sizeof(c->slot[i].name)) ||
            !terminated(c->slot[i].ssid, sizeof(c->slot[i].ssid)) ||
            !terminated(c->slot[i].pass, sizeof(c->slot[i].pass))) {
            return false;
        }
        size_t pl = strlen(c->slot[i].pass);
        if (pl != 0 && (pl < 8 || pl > 63)) {       /* WPA2-PSK: 8 a 63 caracteres */
            return false;
        }
    }
    if (!terminated(c->mqtt_uri, sizeof(c->mqtt_uri)) || !terminated(c->mqtt_user, sizeof(c->mqtt_user)) ||
        !terminated(c->mqtt_pass, sizeof(c->mqtt_pass)) || !terminated(c->base_topic, sizeof(c->base_topic)) ||
        !terminated(c->device_id, sizeof(c->device_id)) || !terminated(c->env_name, sizeof(c->env_name))) {
        return false;
    }
    /* El topic base no puede tener comodines ni terminar en '/' */
    size_t bl = strlen(c->base_topic);
    if (bl == 0 || strpbrk(c->base_topic, "#+ ") != NULL || c->base_topic[bl - 1] == '/') {
        return false;
    }
    if (c->mqtt_uri[0] != '\0' && strncmp(c->mqtt_uri, "mqtt://", 7) != 0 && strncmp(c->mqtt_uri, "mqtts://", 8) != 0) {
        return false;
    }
    return c->device_id[0] != '\0';
}

void net_config_init(void)
{
    s_mtx = xSemaphoreCreateMutex();
    net_config_t tmp;
    size_t sz = sizeof(tmp);
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NS, NVS_READONLY, &h);
    if (err == ESP_OK) {
        err = nvs_get_blob(h, NVS_KEY, &tmp, &sz);
        nvs_close(h);
    }
    if (err == ESP_OK && sz == sizeof(tmp) && tmp.crc == calc_crc(&tmp) && valid(&tmp)) {
        s_cfg = tmp;
        ESP_LOGI(TAG, "Red cargada de NVS: dispositivo %s, topic %s", s_cfg.device_id, s_cfg.base_topic);
    } else {
        defaults(&s_cfg);
        if (!valid(&s_cfg)) {
            ESP_LOGW(TAG, "Valores de red por defecto incompletos (revise sdkconfig.secrets)");
        }
        net_config_save(&s_cfg);
        ESP_LOGI(TAG, "Configuracion de red inicial creada (dispositivo %s)", s_cfg.device_id);
    }
}

void net_config_get(net_config_t *out)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    *out = s_cfg;
    xSemaphoreGive(s_mtx);
}

bool net_config_save(const net_config_t *c)
{
    net_config_t tmp = *c;
    tmp.magic = NET_MAGIC;
    tmp.version = NET_VERSION;
    if (!valid(&tmp)) {
        return false;
    }
    tmp.crc = calc_crc(&tmp);
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NS, NVS_READWRITE, &h);
    if (err == ESP_OK) {
        err = nvs_set_blob(h, NVS_KEY, &tmp, sizeof(tmp));
        if (err == ESP_OK) {
            err = nvs_commit(h);
        }
        nvs_close(h);
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "No se pudo guardar la red: %s", esp_err_to_name(err));
        return false;
    }
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    s_cfg = tmp;
    xSemaphoreGive(s_mtx);
    return true;
}

int net_config_slot_find(const net_config_t *c, const char *name)
{
    for (int i = 0; i < NET_SLOTS; i++) {
        if (strcasecmp(c->slot[i].name, name) == 0) {
            return i;
        }
    }
    return -1;
}

bool net_config_has_any_ssid(const net_config_t *c)
{
    for (int i = 0; i < NET_SLOTS; i++) {
        if (c->slot[i].enabled && c->slot[i].ssid[0]) {
            return true;
        }
    }
    return false;
}

void net_config_print(void)
{
    net_config_t c;
    net_config_get(&c);
    printf("--------------- RED (sin contrasenas) ---------------\n");
    printf("Dispositivo: %s | Entorno: %s | Topic base: %s\n", c.device_id, c.env_name, c.base_topic);
    for (int i = 0; i < NET_SLOTS; i++) {
        printf(" Wi-Fi %-7s %s SSID '%s' contrasena %s%s\n", c.slot[i].name,
               c.slot[i].enabled ? "[ON] " : "[OFF]", c.slot[i].ssid,
               c.slot[i].pass[0] ? "guardada" : "(vacia)", i == c.preferred ? "  <- preferida" : "");
    }
    printf(" Broker: %s | usuario %s | contrasena %s\n", c.mqtt_uri[0] ? c.mqtt_uri : "(sin configurar)",
           c.mqtt_user[0] ? c.mqtt_user : "(ninguno)", c.mqtt_pass[0] ? "guardada" : "(vacia)");
    printf("------------------------------------------------------\n");
}
