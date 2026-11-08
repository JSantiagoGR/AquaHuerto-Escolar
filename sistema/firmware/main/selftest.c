/*
 * SELFTEST del ESP32: ejecuta los escenarios comunes de logic_tests.c (los
 * mismos que corren en la PC) y añade las pruebas que dependen del firmware
 * (anti-duplicados MQTT y conversiones de los drivers). Nunca toca los GPIO
 * ni el estado real del sistema.
 */
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"

#include "commands.h"
#include "configuration.h"
#include "logic_tests.h"
#include "soil_sensor.h"
#include "tank_level.h"
#include "selftest.h"

static void report(int n, const char *name, bool ok, const char *detail)
{
    printf("SELFTEST %02d %-48s %s%s%s\n", n, name, ok ? "PASS" : "FAIL",
           ok ? "" : " -> ", ok ? "" : detail);
    vTaskDelay(1);
}

int selftest_run(void)
{
    int passed = 0;
    int failed = logic_tests_run(&passed);
    char d[120] = "";
    bool ok;

    /* 48 Comandos duplicados (ids únicos: no se borra la lista real de MQTT) */
    {
        char id1[40], id2[40];
        uint32_t u = (uint32_t)esp_timer_get_time();
        snprintf(id1, sizeof(id1), "selftest-%08lx-a", (unsigned long)u);
        snprintf(id2, sizeof(id2), "selftest-%08lx-b", (unsigned long)u);
        ok = !commands_seen_id(id1) && commands_seen_id(id1) && !commands_seen_id(id2);
        snprintf(d, sizeof(d), "deteccion de duplicados incorrecta");
        report(48, "Comandos MQTT duplicados se descartan", ok, d);
        ok ? passed++ : failed++;
    }

    /* 49 Conversiones de calibración */
    {
        riego_config_t c;
        config_defaults(&c);
        float v630 = soil_mv_to_vwc(&c, 630);       /* recta 27.388 -> agua/suelo 37.718 */
        float back = ec5_vwc_to_mv(&c, v630);
        c.ec5_scale = 0;
        float lin = soil_mv_to_vwc(&c, 630);
        c.tank_empty_cm = 120;
        c.tank_full_cm = 20;
        float p = tank_distance_to_pct(&c, 70);
        ok = fabsf(v630 - 37.718f) < 0.05f && fabsf(back - 630.0f) < 0.5f && fabsf(lin - 27.388f) < 0.05f && fabsf(p - 50.0f) < 0.01f;
        snprintf(d, sizeof(d), "630 mV -> %.3f (recta %.3f, inversa %.1f mV), 70 cm -> %.2f %%", v630, lin, back, p);
        report(49, "Conversiones EC-5 (Act. 2.2) y nivel", ok, d);
        ok ? passed++ : failed++;
    }

    printf("SELFTEST TOTAL: %d PASS, %d FAIL\n", passed, failed);
    return failed;
}
