/*
 * Hora local por NTP. Zona por defecto "CST6": Chihuahua (capital) usa UTC-6
 * todo el año desde oct-2022. Para Cd. Juárez usar "MST7MDT,M3.2.0,M11.1.0".
 * Sin hora válida no se ejecutan riegos basados en horario.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

void time_init(const char *tz);
void time_set_tz(const char *tz);
void time_start_sntp(void);            /* Llamar al obtener IP */
bool time_is_valid(void);
uint32_t time_epoch(void);             /* 0 si no es válida */
int time_minute_of_day(void);          /* -1 si no es válida */
int32_t time_day_key(void);            /* AAAA*1000+día del año, o negativo por uptime */
void time_format_now(char *out, int len);  /* "AAAA-MM-DD HH:MM:SS" o "SIN_HORA" */
