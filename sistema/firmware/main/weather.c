#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_http_client.h"
#include "esp_crt_bundle.h"
#include "esp_log.h"
#include "cJSON.h"

#include "configuration.h"
#include "timekeeping.h"
#include "wifi_manager.h"
#include "weather.h"

static const char *TAG = "clima";

#define BUF_MAX         8192
#define STALE_S         (3 * 3600)

static weather_t s_wx;
static SemaphoreHandle_t s_mtx;
static volatile bool s_refresh;
static char *s_buf;
static int s_len;

static esp_err_t http_evt(esp_http_client_event_t *e)
{
    if (e->event_id == HTTP_EVENT_ON_DATA && e->data_len > 0) {
        if (s_len + e->data_len < BUF_MAX - 1) {
            memcpy(s_buf + s_len, e->data, e->data_len);
            s_len += e->data_len;
        } else {
            s_len = BUF_MAX;            /* Respuesta demasiado grande */
        }
    }
    return ESP_OK;
}

static float num_at(const cJSON *arr, int i)
{
    const cJSON *it = cJSON_GetArrayItem(arr, i);
    return cJSON_IsNumber(it) ? (float)it->valuedouble : NAN;
}

static float num(const cJSON *o, const char *k)
{
    const cJSON *it = cJSON_GetObjectItemCaseSensitive(o, k);
    return cJSON_IsNumber(it) ? (float)it->valuedouble : NAN;
}

static void set_error(const char *msg, int http)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    s_wx.fail_count++;
    s_wx.last_http = http;
    strlcpy(s_wx.last_error, msg, sizeof(s_wx.last_error));
    xSemaphoreGive(s_mtx);
    ESP_LOGW(TAG, "Open-Meteo: %s (HTTP %d)", msg, http);
}

static void fetch(const riego_config_t *c)
{
    char url[512];
    snprintf(url, sizeof(url),
             "https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
             "&current=temperature_2m,relative_humidity_2m,precipitation,rain"
             "&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,"
             "vapour_pressure_deficit,et0_fao_evapotranspiration"
             "&past_hours=6&forecast_hours=24&timeformat=unixtime&timezone=auto",
             (double)c->lat, (double)c->lon);
    s_len = 0;
    esp_http_client_config_t hc = {
        .url = url,
        .event_handler = http_evt,
        .crt_bundle_attach = esp_crt_bundle_attach,   /* TLS con verificación de certificado */
        .timeout_ms = 15000,
        .buffer_size = 2048,
    };
    esp_http_client_handle_t h = esp_http_client_init(&hc);
    if (h == NULL) {
        set_error("no se pudo crear el cliente HTTP", 0);
        return;
    }
    esp_err_t err = esp_http_client_perform(h);
    int status = esp_http_client_get_status_code(h);
    esp_http_client_cleanup(h);
    if (err != ESP_OK) {
        set_error(esp_err_to_name(err), status);
        return;
    }
    if (status != 200 || s_len <= 0 || s_len >= BUF_MAX) {
        set_error(s_len >= BUF_MAX ? "respuesta demasiado grande" : "respuesta HTTP no valida", status);
        return;
    }
    s_buf[s_len] = '\0';
    cJSON *root = cJSON_Parse(s_buf);
    const cJSON *cur = cJSON_GetObjectItemCaseSensitive(root, "current");
    const cJSON *hr = cJSON_GetObjectItemCaseSensitive(root, "hourly");
    const cJSON *times = hr ? cJSON_GetObjectItemCaseSensitive(hr, "time") : NULL;
    if (!cJSON_IsObject(cur) || !cJSON_IsArray(times)) {
        cJSON_Delete(root);
        set_error("JSON inesperado", status);
        return;
    }
    weather_t w;
    memset(&w, 0, sizeof(w));
    w.valid = true;
    w.fetch_epoch = time_epoch();
    w.model_epoch = (uint32_t)num(cur, "time");
    w.cur_temp = num(cur, "temperature_2m");
    w.cur_rh = num(cur, "relative_humidity_2m");
    w.cur_precip = num(cur, "precipitation");
    w.cur_rain = num(cur, "rain");
    const cJSON *a_t = cJSON_GetObjectItemCaseSensitive(hr, "temperature_2m");
    const cJSON *a_rh = cJSON_GetObjectItemCaseSensitive(hr, "relative_humidity_2m");
    const cJSON *a_pp = cJSON_GetObjectItemCaseSensitive(hr, "precipitation_probability");
    const cJSON *a_pr = cJSON_GetObjectItemCaseSensitive(hr, "precipitation");
    const cJSON *a_vpd = cJSON_GetObjectItemCaseSensitive(hr, "vapour_pressure_deficit");
    const cJSON *a_et = cJSON_GetObjectItemCaseSensitive(hr, "et0_fao_evapotranspiration");
    int n = cJSON_GetArraySize(times);
    if (n > WX_HOURS) {
        n = WX_HOURS;
    }
    w.n = n;
    uint32_t now = w.fetch_epoch;
    w.next6_pprob_max = 0;
    for (int i = 0; i < n; i++) {
        w.time[i] = (uint32_t)num_at(times, i);
        w.temp[i] = num_at(a_t, i);
        w.rh[i] = num_at(a_rh, i);
        w.pprob[i] = num_at(a_pp, i);
        w.precip[i] = num_at(a_pr, i);
        w.vpd[i] = num_at(a_vpd, i);
        w.et0[i] = num_at(a_et, i);
        float p = isfinite(w.precip[i]) ? w.precip[i] : 0.0f;
        if (w.time[i] + 3600 <= now) {
            w.past_precip_6h += p;
        } else if (w.time[i] < now + 6 * 3600) {
            w.next6_precip += p;
            if (isfinite(w.pprob[i]) && w.pprob[i] > w.next6_pprob_max) {
                w.next6_pprob_max = w.pprob[i];
            }
        }
        if (w.time[i] + 3600 > now && w.time[i] < now + 24 * 3600 && isfinite(w.et0[i])) {
            w.et0_24h += w.et0[i];
        }
    }
    cJSON_Delete(root);
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    w.ok_count = s_wx.ok_count + 1;
    w.fail_count = s_wx.fail_count;
    w.last_http = status;
    s_wx = w;
    xSemaphoreGive(s_mtx);
    ESP_LOGI(TAG, "Pronostico actualizado: %.1f C %.0f%%HR, lluvia 6 h %.1f mm (prob max %.0f%%), ET0 24 h %.1f mm",
             w.cur_temp, w.cur_rh, w.next6_precip, w.next6_pprob_max, w.et0_24h);
}

static void weather_task(void *arg)
{
    uint32_t last_try = 0;
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(5000));
        riego_config_t c;
        config_get(&c);
        if (!c.weather_en || !config_location_set(&c) || !wifi_manager_connected() || !time_is_valid()) {
            continue;
        }
        uint32_t now = time_epoch();
        uint32_t period = (uint32_t)(c.weather_min * 60.0f);
        bool fail_backoff = (s_wx.fail_count > 0 && now - last_try < 300);   /* 5 min tras un error */
        if (s_refresh || (!fail_backoff && (last_try == 0 || now - last_try >= period))) {
            s_refresh = false;
            last_try = now;
            fetch(&c);
        }
    }
}

void weather_start(void)
{
    s_mtx = xSemaphoreCreateMutex();
    s_buf = malloc(BUF_MAX);
    if (s_buf == NULL) {
        ESP_LOGE(TAG, "Sin memoria para el pronostico");
        return;
    }
    xTaskCreatePinnedToCore(weather_task, "clima", 8192, NULL, 2, NULL, 1);
}

void weather_get(weather_t *out)
{
    if (s_mtx == NULL) {
        memset(out, 0, sizeof(*out));
        return;
    }
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    *out = s_wx;
    xSemaphoreGive(s_mtx);
}

void weather_request_refresh(void)
{
    s_refresh = true;
}

uint32_t weather_age_s(const weather_t *w, uint32_t now_epoch)
{
    if (!w->valid || now_epoch == 0 || now_epoch < w->fetch_epoch) {
        return UINT32_MAX;
    }
    return now_epoch - w->fetch_epoch;
}

bool weather_fresh(const weather_t *w, uint32_t now_epoch)
{
    return weather_age_s(w, now_epoch) <= STALE_S;
}

bool weather_rain_expected(const weather_t *w, float prob_pct, float mm, uint32_t now_epoch)
{
    if (!weather_fresh(w, now_epoch)) {
        return false;                   /* Un pronóstico vencido no se usa */
    }
    return w->next6_pprob_max >= prob_pct && w->next6_precip >= mm;
}

void weather_fill_ia_env(const weather_t *w, uint32_t now_epoch, ia_env_t *env)
{
    env->n_fc = 0;
    if (!weather_fresh(w, now_epoch)) {
        return;
    }
    for (int i = 0; i < w->n && env->n_fc < IA_FC_MAX; i++) {
        if (w->time[i] + 3600 <= now_epoch) {
            continue;
        }
        int k = env->n_fc++;
        env->fc_temp[k] = w->temp[i];
        env->fc_rh[k] = w->rh[i];
        env->fc_vpd[k] = w->vpd[i];
        env->fc_et0[k] = w->et0[i];
    }
}
