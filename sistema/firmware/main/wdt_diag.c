#include <stdio.h>
#include <string.h>

#include "esp_attr.h"
#include "esp_system.h"
#include "esp_task_wdt.h"

#include "wdt_diag.h"

#define WDT_MAGIC 0x57445447u

RTC_NOINIT_ATTR static uint32_t s_magic;
RTC_NOINIT_ATTR static char s_tasks[96];
RTC_NOINIT_ATTR static char s_stage[32];
static char s_last[160];
static int s_calls;

volatile const char *g_wdt_stage = "inicio";

static void append(char *dst, size_t cap, const char *m)
{
    size_t n = 0;
    while (n < cap - 1 && dst[n]) {
        n++;
    }
    while (*m && n < cap - 1) {
        dst[n++] = *m++;
    }
    dst[n] = '\0';
}

/* Recibe el encabezado y luego " - tarea (CPU n)" por cada tarea que no respondió */
static void on_msg(void *opaque, const char *msg)
{
    if (s_calls++ == 0) {
        return;                                 /* El encabezado en inglés no se guarda */
    }
    if (msg[0] == '\n') {
        msg += 1;
    }
    append(s_tasks, sizeof(s_tasks), msg);
}

/* La llama el ISR del watchdog justo antes del reinicio */
void esp_task_wdt_isr_user_handler(void)
{
    s_calls = 0;
    s_tasks[0] = '\0';
    esp_task_wdt_print_triggered_tasks(on_msg, NULL, NULL);
    const char *st = (const char *)g_wdt_stage;
    s_stage[0] = '\0';
    append(s_stage, sizeof(s_stage), st ? st : "?");
    s_magic = WDT_MAGIC;
}

void wdt_diag_boot(void)
{
    s_last[0] = '\0';
    if (s_magic == WDT_MAGIC && esp_reset_reason() == ESP_RST_TASK_WDT) {
        s_tasks[sizeof(s_tasks) - 1] = '\0';
        s_stage[sizeof(s_stage) - 1] = '\0';
        snprintf(s_last, sizeof(s_last), "tareas:%s | etapa del control: %s", s_tasks, s_stage);
        printf("Reinicio anterior por watchdog: %s\n", s_last);
    }
    s_magic = 0;
}

const char *wdt_diag_last(void)
{
    return s_last;
}
