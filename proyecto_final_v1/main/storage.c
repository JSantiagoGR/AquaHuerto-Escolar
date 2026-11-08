#include <string.h>
#include <stddef.h>

#include "esp_log.h"
#include "esp_rom_crc.h"
#include "nvs_flash.h"
#include "nvs.h"

#include "storage.h"

static const char *TAG = "storage";
#define NVS_NS      "riego"
#define NVS_KEY     "persist"
#define P_MAGIC     0x50455253u     /* "PERS" */
#define P_VERSION   1u

void storage_init(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS requiere borrado (%s)", esp_err_to_name(err));
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
}

static uint32_t calc_crc(const persist_t *p)
{
    return esp_rom_crc32_le(0, (const uint8_t *)p, offsetof(persist_t, crc));
}

bool storage_load(persist_t *p)
{
    size_t sz = sizeof(*p);
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NS, NVS_READONLY, &h);
    if (err == ESP_OK) {
        err = nvs_get_blob(h, NVS_KEY, p, &sz);
        nvs_close(h);
    }
    if (err == ESP_OK && sz == sizeof(*p) && p->magic == P_MAGIC &&
        p->version == P_VERSION && p->crc == calc_crc(p) && p->hist_count <= HIST_MAX) {
        return true;
    }
    memset(p, 0, sizeof(*p));
    p->magic = P_MAGIC;
    p->version = P_VERSION;
    return false;
}

void storage_save(persist_t *p)
{
    p->magic = P_MAGIC;
    p->version = P_VERSION;
    p->crc = calc_crc(p);
    nvs_handle_t h;
    if (nvs_open(NVS_NS, NVS_READWRITE, &h) != ESP_OK) {
        ESP_LOGE(TAG, "No se pudo abrir NVS");
        return;
    }
    esp_err_t err = nvs_set_blob(h, NVS_KEY, p, sizeof(*p));
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }
    nvs_close(h);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error guardando datos: %s", esp_err_to_name(err));
    }
}

void storage_hist_add(persist_t *p, const hist_entry_t *e)
{
    p->hist[p->hist_head] = *e;
    p->hist_head = (uint8_t)((p->hist_head + 1) % HIST_MAX);
    if (p->hist_count < HIST_MAX) {
        p->hist_count++;
    }
}

const hist_entry_t *storage_hist_get(const persist_t *p, int i)
{
    if (i < 0 || i >= p->hist_count) {
        return NULL;
    }
    int idx = ((int)p->hist_head - 1 - i + HIST_MAX) % HIST_MAX;
    return &p->hist[idx];
}
