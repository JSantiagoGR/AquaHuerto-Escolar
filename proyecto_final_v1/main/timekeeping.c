#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/time.h>

#include "esp_netif_sntp.h"
#include "esp_timer.h"
#include "esp_log.h"

#include "timekeeping.h"

static const char *TAG = "time";
static bool s_sntp_started;

void time_set_tz(const char *tz)
{
    setenv("TZ", tz, 1);
    tzset();
}

void time_init(const char *tz)
{
    time_set_tz(tz);
}

void time_start_sntp(void)
{
    if (s_sntp_started) {
        return;
    }
    esp_sntp_config_t cfg = ESP_NETIF_SNTP_DEFAULT_CONFIG("pool.ntp.org");
    cfg.start = true;
    if (esp_netif_sntp_init(&cfg) == ESP_OK) {
        s_sntp_started = true;
        ESP_LOGI(TAG, "SNTP iniciado (pool.ntp.org)");
    }
}

bool time_is_valid(void)
{
    time_t now = time(NULL);
    return now > 1735689600;    /* Posterior a 2025-01-01: la hora fue sincronizada */
}

uint32_t time_epoch(void)
{
    return time_is_valid() ? (uint32_t)time(NULL) : 0;
}

int time_minute_of_day(void)
{
    if (!time_is_valid()) {
        return -1;
    }
    time_t now = time(NULL);
    struct tm tm;
    localtime_r(&now, &tm);
    return tm.tm_hour * 60 + tm.tm_min;
}

int32_t time_day_key(void)
{
    if (!time_is_valid()) {
        /* Sin hora: el "día" se cuenta por tiempo de funcionamiento */
        return -(int32_t)(esp_timer_get_time() / 86400000000LL) - 1;
    }
    time_t now = time(NULL);
    struct tm tm;
    localtime_r(&now, &tm);
    return (tm.tm_year + 1900) * 1000 + tm.tm_yday;
}

void time_format_now(char *out, int len)
{
    if (!time_is_valid()) {
        snprintf(out, len, "SIN_HORA");
        return;
    }
    time_t now = time(NULL);
    struct tm tm;
    localtime_r(&now, &tm);
    strftime(out, len, "%Y-%m-%d %H:%M:%S", &tm);
}
