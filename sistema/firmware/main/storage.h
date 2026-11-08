/*
 * Datos persistentes de operación (NVS): litros acumulados, litros del día,
 * marca de "riego en curso" (para detectar reinicios durante un riego) e
 * historial de los últimos riegos. Se escribe solo al iniciar/terminar un
 * riego y al cambiar de día, para no desgastar la flash.
 */
#pragma once

#include <stdint.h>
#include <stdbool.h>

#define HIST_MAX 16

typedef struct {
    uint32_t epoch;             /* 0 si la hora no era válida      */
    uint32_t uptime_s;
    uint8_t reason;             /* water_reason_t                  */
    uint8_t result;             /* water_result_t                  */
    uint16_t duration_s;
    uint32_t ml;                /* Volumen calculado por pulsos    */
    int16_t vwc_before_x10;     /* -1000 = sin dato                */
    int16_t vwc_after_x10;
    uint16_t pulses;
    uint16_t reserved;
} hist_entry_t;

typedef struct {
    uint32_t magic;
    uint32_t version;
    double total_ml;            /* Litros acumulados (calculados)  */
    float daily_ml;
    int32_t day_key;
    uint8_t watering_active;    /* 1 mientras hay un riego en curso */
    uint8_t active_reason;
    uint8_t hist_head;
    uint8_t hist_count;
    uint32_t active_start_epoch;
    float active_target_ml;
    uint32_t boot_count;
    uint32_t event_seq;         /* Contador de riegos (ID único con el dispositivo) */
    hist_entry_t hist[HIST_MAX];
    uint32_t crc;
} persist_t;

void storage_init(void);                       /* nvs_flash_init (con borrado si hace falta) */
bool storage_load(persist_t *p);               /* false = datos nuevos/por defecto */
void storage_save(persist_t *p);
void storage_hist_add(persist_t *p, const hist_entry_t *e);
/* i = 0 es el más reciente */
const hist_entry_t *storage_hist_get(const persist_t *p, int i);

/* Modelo compacto de la IA (se guarda tras aprender, no con cada muestra) */
#include "ia_model.h"
bool storage_ia_load(ia_model_t *m);
void storage_ia_save(ia_model_t *m);
void storage_ia_erase(void);
