/*
 * Almacenamiento de la configuración en NVS (blob con CRC32) protegido por
 * mutex. La tabla, los valores por defecto y la validación están en
 * config_table.c (lógica pura, probada también en la PC).
 */
#include <stdio.h>
#include <string.h>
#include <math.h>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_rom_crc.h"
#include "nvs.h"

#include "configuration.h"

static const char *TAG = "config";
#define NVS_NS   "riego"
#define NVS_KEY  "cfg"

static riego_config_t s_cfg;
static SemaphoreHandle_t s_mtx;
static uint32_t s_generation;

static uint32_t calc_crc(const riego_config_t *c)
{
    return esp_rom_crc32_le(0, (const uint8_t *)c, offsetof(riego_config_t, crc));
}

static esp_err_t save_locked(void)
{
    s_cfg.crc = calc_crc(&s_cfg);
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NS, NVS_READWRITE, &h);
    if (err != ESP_OK) {
        return err;
    }
    err = nvs_set_blob(h, NVS_KEY, &s_cfg, sizeof(s_cfg));
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }
    nvs_close(h);
    return err;
}

void config_init(bool *was_reset)
{
    s_mtx = xSemaphoreCreateMutex();
    *was_reset = false;

    riego_config_t tmp;
    size_t sz = sizeof(tmp);
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NS, NVS_READONLY, &h);
    if (err == ESP_OK) {
        err = nvs_get_blob(h, NVS_KEY, &tmp, &sz);
        nvs_close(h);
    }

    char msg[120];
    if (err == ESP_OK && sz == sizeof(tmp) && tmp.magic == CONFIG_MAGIC &&
        tmp.version == CONFIG_VERSION && tmp.crc == calc_crc(&tmp) &&
        config_validate(&tmp, msg, sizeof(msg))) {
        s_cfg = tmp;
        ESP_LOGI(TAG, "Configuracion cargada de NVS (perfil %s v%lu)", s_cfg.crop_id,
                 (unsigned long)s_cfg.profile_version);
    } else {
        bool first_boot = (err == ESP_ERR_NVS_NOT_FOUND);
        bool old_version = (err == ESP_OK && sz != sizeof(tmp));
        config_defaults(&s_cfg);
        save_locked();
        if (!first_boot && !old_version) {
            *was_reset = true;
            ESP_LOGW(TAG, "Configuracion NVS invalida (%s): valores por defecto", esp_err_to_name(err));
        } else {
            ESP_LOGI(TAG, "%s: configuracion por defecto guardada",
                     first_boot ? "Primer arranque" : "Version anterior de configuracion");
        }
    }
    s_generation = 1;
}

void config_get(riego_config_t *out)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    *out = s_cfg;
    xSemaphoreGive(s_mtx);
}

uint32_t config_generation(void)
{
    return s_generation;
}

esp_err_t config_apply(const riego_config_t *cand, char *msg, size_t len)
{
    if (!config_validate(cand, msg, len)) {
        return ESP_ERR_INVALID_ARG;
    }
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    s_cfg = *cand;
    s_cfg.magic = CONFIG_MAGIC;
    s_cfg.version = CONFIG_VERSION;
    esp_err_t err = save_locked();
    s_generation++;
    xSemaphoreGive(s_mtx);
    if (err != ESP_OK) {
        snprintf(msg, len, "Error al guardar en NVS: %s", esp_err_to_name(err));
    }
    return err;
}

esp_err_t config_factory_reset(void)
{
    riego_config_t d;
    config_defaults(&d);
    char msg[64];
    return config_apply(&d, msg, sizeof(msg));
}

esp_err_t config_set(const char *key, const char *value, bool remote, char *msg, size_t len)
{
    const config_param_t *p = config_param_find(key);
    if (p == NULL) {
        snprintf(msg, len, "Parametro desconocido: %s", key);
        return ESP_ERR_NOT_FOUND;
    }
    if (remote && !p->remote) {
        snprintf(msg, len, "%s solo se puede cambiar por consola serial", p->key);
        return ESP_ERR_NOT_ALLOWED;
    }
    riego_config_t cand;
    config_get(&cand);
    if (config_param_set_str(&cand, p, value, msg, len) != 0) {
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t err = config_apply(&cand, msg, len);
    if (err == ESP_OK) {
        char buf[48];
        config_param_format(&cand, p, buf, sizeof(buf));
        snprintf(msg, len, "%s = %s %s", p->key, buf, p->unit);
    }
    return err;
}

esp_err_t config_set_humidity_range(float mn, float tg, float mx, char *msg, size_t len)
{
    riego_config_t cand;
    config_get(&cand);
    cand.hum_min = mn;
    cand.hum_target = tg;
    cand.hum_max = mx;
    /* La reserva se mantiene dentro del nuevo rango si quedó fuera */
    if (cand.hum_reserve < tg + 0.5f || cand.hum_reserve > mx) {
        cand.hum_reserve = fminf(mx, tg + (mx - tg) / 2.0f);
    }
    esp_err_t err = config_apply(&cand, msg, len);
    if (err == ESP_OK) {
        snprintf(msg, len, "Humedad: minima %.1f / objetivo %.1f / reserva %.1f / maxima %.1f %%VWC",
                 mn, tg, cand.hum_reserve, mx);
    }
    return err;
}
