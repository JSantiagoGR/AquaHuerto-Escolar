#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "mqtt_client.h"
#include "esp_mac.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "sdkconfig.h"

#include "commands.h"
#include "net_config.h"
#include "mqtt_manager.h"

static const char *TAG = "mqtt";

#define MAX_CMD_LEN 1536

static esp_mqtt_client_handle_t s_client;
static volatile bool s_connected;
static volatile bool s_connected_flag;
static volatile bool s_net_up;
static char s_base[64];
static char s_device[24];
static char s_uri[100];
static char s_topic_status[96], s_topic_cmd[96];
static char s_client_id[48];
static char s_lwt[128];
static uint32_t s_connects;

/* Cola de publicaciones: la tarea de control solo deja el mensaje aquí y sigue.
 * esp_mqtt_client_enqueue toma el candado del cliente, que esp-mqtt retiene mientras
 * reconecta (hasta network.timeout_ms = 10 s con señal débil); si la tarea de control
 * lo llamara directo, el watchdog de 5 s la reiniciaría. La tarea "mqtt_pub" no está
 * vigilada por el watchdog y es la única que espera ese candado. */
#define PUB_QUEUE_LEN 24
typedef struct {
    char *topic;
    char *data;
    uint8_t qos;
    uint8_t retain;
} pub_item_t;
static QueueHandle_t s_pubq;
static SemaphoreHandle_t s_cl_mtx;      /* Protege s_client entre mqtt_pub y stop_client */
static volatile uint32_t s_pub_dropped;

/* Cambio de broker con reversión */
static net_config_t s_prev;
static esp_timer_handle_t s_revert_timer;
static volatile int s_change_state;     /* 0 NONE, 1 TESTING, 2 OK, 3 REVERTED */
static const char *const CHANGE_NAMES[] = { "NONE", "TESTING", "OK", "REVERTED" };

const char *mqtt_manager_base(void) { return s_base; }
const char *mqtt_manager_device(void) { return s_device; }
const char *mqtt_manager_client_id(void) { return s_client_id; }
const char *mqtt_manager_broker(void) { return s_uri; }
uint32_t mqtt_manager_connect_count(void) { return s_connects; }
uint32_t mqtt_manager_dropped(void) { return s_pub_dropped; }
const char *mqtt_manager_broker_change_state(void) { return CHANGE_NAMES[s_change_state & 3]; }

bool mqtt_manager_configured(void)
{
    return s_uri[0] != '\0';
}

static void load(void)
{
    net_config_t c;
    net_config_get(&c);
    strlcpy(s_base, c.base_topic, sizeof(s_base));
    strlcpy(s_device, c.device_id, sizeof(s_device));
    strlcpy(s_uri, c.mqtt_uri, sizeof(s_uri));
    snprintf(s_topic_status, sizeof(s_topic_status), "%s/status", s_base);
    snprintf(s_topic_cmd, sizeof(s_topic_cmd), "%s/command", s_base);
    uint8_t mac[6] = {0};
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    /* Identificador único por dispositivo: evita que dos ESP32 se desconecten mutuamente */
    snprintf(s_client_id, sizeof(s_client_id), "riego-%s-%02x%02x%02x", s_device, mac[3], mac[4], mac[5]);
    snprintf(s_lwt, sizeof(s_lwt), "{\"online\":false,\"reason\":\"LWT\",\"device\":\"%s\"}", s_device);
}

static void on_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    esp_mqtt_event_handle_t ev = (esp_mqtt_event_handle_t)data;
    switch ((esp_mqtt_event_id_t)id) {
    case MQTT_EVENT_CONNECTED: {
        s_connected = true;
        s_connected_flag = true;
        s_connects++;
        ESP_LOGI(TAG, "Conectado al broker %s", s_uri);
        esp_mqtt_client_subscribe(s_client, s_topic_cmd, 1);
        char st[160];
        snprintf(st, sizeof(st), "{\"online\":true,\"device\":\"%s\",\"client_id\":\"%s\"}", s_device, s_client_id);
        esp_mqtt_client_publish(s_client, s_topic_status, st, 0, 1, 1);
        if (s_change_state == 1) {
            /* El broker nuevo funciona: se guarda definitivamente */
            esp_timer_stop(s_revert_timer);
            s_change_state = 2;
            ESP_LOGI(TAG, "Broker nuevo confirmado y guardado");
        }
        break;
    }
    case MQTT_EVENT_DISCONNECTED:
        if (s_connected) {
            ESP_LOGW(TAG, "Desconectado del broker (reintento automatico)");
        }
        s_connected = false;
        break;
    case MQTT_EVENT_DATA: {
        /* Mensajes fragmentados o demasiado largos no son comandos válidos */
        if (ev->data_len != ev->total_data_len || ev->current_data_offset != 0 ||
            ev->data_len <= 0 || ev->data_len >= MAX_CMD_LEN) {
            ESP_LOGW(TAG, "Comando descartado (tamano %d)", ev->total_data_len);
            break;
        }
        if (ev->topic_len != (int)strlen(s_topic_cmd) ||
            strncmp(ev->topic, s_topic_cmd, ev->topic_len) != 0) {
            break;
        }
        commands_handle_mqtt(ev->data, ev->data_len, ev->retain);
        break;
    }
    case MQTT_EVENT_ERROR:
        if (ev && ev->error_handle && ev->error_handle->connect_return_code) {
            ESP_LOGW(TAG, "Broker rechazo la conexion (codigo %d: usuario/contrasena o permisos)",
                     ev->error_handle->connect_return_code);
        } else {
            ESP_LOGW(TAG, "Error MQTT (broker inaccesible?)");
        }
        break;
    default:
        break;
    }
}

static void stop_client(void)
{
    xSemaphoreTake(s_cl_mtx, portMAX_DELAY);
    if (s_client) {
        esp_mqtt_client_stop(s_client);
        esp_mqtt_client_destroy(s_client);
        s_client = NULL;
    }
    s_connected = false;
    xSemaphoreGive(s_cl_mtx);
}

static void pub_task(void *arg)
{
    pub_item_t it;
    while (true) {
        if (xQueueReceive(s_pubq, &it, portMAX_DELAY) != pdTRUE) {
            continue;
        }
        xSemaphoreTake(s_cl_mtx, portMAX_DELAY);
        if (s_client && s_connected) {
            /* store=true conserva QoS1 en la bandeja si hay reconexión */
            if (esp_mqtt_client_enqueue(s_client, it.topic, it.data, 0, it.qos, it.retain, true) < 0) {
                s_pub_dropped++;
            }
        } else {
            s_pub_dropped++;
        }
        xSemaphoreGive(s_cl_mtx);
        free(it.topic);
        free(it.data);
    }
}

static void start_client(void)
{
    load();
    if (!mqtt_manager_configured()) {
        ESP_LOGW(TAG, "Sin URI de broker: MQTT deshabilitado (use MQTT URI ... en la consola)");
        return;
    }
    net_config_t c;
    net_config_get(&c);
    esp_mqtt_client_config_t cfg = {
        .broker.address.uri = s_uri,
        .credentials.client_id = s_client_id,
        .session.keepalive = 30,                  /* Tolera más pérdida de paquetes con señal débil */
        .session.disable_clean_session = false,   /* Sin cola de comandos viejos */
        .session.last_will = {
            .topic = s_topic_status,
            .msg = s_lwt,
            .msg_len = 0,
            .qos = 1,
            .retain = 1,
        },
        .network.reconnect_timeout_ms = 5000,
        .network.timeout_ms = 10000,
        .buffer.size = 2048,
        .outbox.limit = 24 * 1024,
    };
    static char user[33], pass[65];
    strlcpy(user, c.mqtt_user, sizeof(user));
    strlcpy(pass, c.mqtt_pass, sizeof(pass));
    if (user[0]) {
        cfg.credentials.username = user;
        cfg.credentials.authentication.password = pass;
    }
    s_client = esp_mqtt_client_init(&cfg);
    if (s_client == NULL) {
        ESP_LOGE(TAG, "No se pudo crear el cliente MQTT");
        return;
    }
    esp_mqtt_client_register_event(s_client, ESP_EVENT_ANY_ID, on_event, NULL);
    esp_mqtt_client_start(s_client);
    ESP_LOGI(TAG, "Cliente MQTT iniciado (id %s, topic %s)", s_client_id, s_base);
}

static void revert_cb(void *arg)
{
    if (s_change_state != 1) {
        return;
    }
    ESP_LOGW(TAG, "El broker nuevo no respondio: se vuelve al anterior");
    net_config_save(&s_prev);
    s_change_state = 3;
    stop_client();
    if (s_net_up) {
        start_client();
    }
}

void mqtt_manager_init(void)
{
    load();
    const esp_timer_create_args_t targs = { .callback = revert_cb, .name = "mqtt_revert" };
    esp_timer_create(&targs, &s_revert_timer);
    s_cl_mtx = xSemaphoreCreateMutex();
    s_pubq = xQueueCreate(PUB_QUEUE_LEN, sizeof(pub_item_t));
    xTaskCreatePinnedToCore(pub_task, "mqtt_pub", 4096, NULL, 3, NULL, 1);
}

void mqtt_manager_network(bool up)
{
    s_net_up = up;
    if (up && s_client == NULL) {
        start_client();
    }
    /* Con la red caída esp-mqtt reintenta solo; no hace falta detenerlo */
}

void mqtt_manager_reconfigure(void)
{
    stop_client();
    load();
    if (s_net_up) {
        start_client();
    }
}

bool mqtt_manager_try_broker(const char *uri, const char *user, const char *pass, int timeout_s)
{
    net_config_t c;
    net_config_get(&c);
    s_prev = c;
    strlcpy(c.mqtt_uri, uri, sizeof(c.mqtt_uri));
    if (user) {
        strlcpy(c.mqtt_user, user, sizeof(c.mqtt_user));
    }
    if (pass) {
        strlcpy(c.mqtt_pass, pass, sizeof(c.mqtt_pass));
    }
    if (!net_config_save(&c)) {
        return false;
    }
    s_change_state = 1;
    esp_timer_stop(s_revert_timer);
    esp_timer_start_once(s_revert_timer, (uint64_t)timeout_s * 1000000ULL);
    mqtt_manager_reconfigure();
    return true;
}

bool mqtt_manager_connected(void)
{
    return s_connected;
}

bool mqtt_manager_take_connected_flag(void)
{
    bool f = s_connected_flag;
    s_connected_flag = false;
    return f;
}

bool mqtt_publish(const char *sub, const char *json, int qos, bool retain)
{
    if (!s_connected || s_client == NULL || s_pubq == NULL) {
        return false;
    }
    char topic[112];
    snprintf(topic, sizeof(topic), "%s/%s", s_base, sub);
    pub_item_t it = { .topic = strdup(topic), .data = strdup(json), .qos = (uint8_t)qos, .retain = retain ? 1 : 0 };
    /* Nunca espera: si la cola está llena (red muy lenta) el mensaje se descarta y se cuenta */
    if (it.topic == NULL || it.data == NULL || xQueueSend(s_pubq, &it, 0) != pdTRUE) {
        free(it.topic);
        free(it.data);
        s_pub_dropped++;
        return false;
    }
    return true;
}
