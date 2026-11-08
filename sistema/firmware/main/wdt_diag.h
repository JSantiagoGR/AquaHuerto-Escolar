/*
 * Diagnóstico de reinicios por watchdog de tareas.
 * Si el watchdog dispara, guarda en memoria RTC (sobrevive al reinicio por software)
 * qué tareas no respondieron y en qué etapa iba la tarea de control; al arrancar
 * se recupera y se publica en "diag" (last_wdt) para diagnosticar sin cable USB.
 */
#pragma once

/* Etapa actual de la tarea de control (cadena literal); se guarda si el watchdog dispara */
extern volatile const char *g_wdt_stage;
#define WDT_STAGE(s) (g_wdt_stage = (s))

/* Llamar al inicio de app_main: recupera el registro del reinicio anterior */
void wdt_diag_boot(void);
/* Texto del último reinicio por watchdog ("" si el último arranque no fue por watchdog) */
const char *wdt_diag_last(void);
