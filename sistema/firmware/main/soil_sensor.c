#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_rom_sys.h"
#include "esp_log.h"

#include "board.h"
#include "soil_sensor.h"

static const char *TAG = "ec5";

#define N_PULSES        9       /* Pulsos de excitación por medición (mediana robusta) */
#define READS_PER_PULSE 4       /* Lecturas ADC promediadas al final del pulso */
#define EXCITE_US       10000   /* 10 ms, como en la Actividad 2.2            */
#define PULSE_GAP_MS    200
#define MAX_SPREAD_MV   150

#if EC5_POWER_ACTIVE_HIGH
#define PWR_ON  1
#define PWR_OFF 0
#else
#define PWR_ON  0
#define PWR_OFF 1
#endif

static adc_oneshot_unit_handle_t s_adc;
static adc_cali_handle_t s_cali;
static bool s_cali_ok;

bool soil_sensor_init(void)
{
    /* Excitación apagada por defecto */
    gpio_set_level(PIN_EC5_POWER, PWR_OFF);
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << PIN_EC5_POWER,
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&io);
    gpio_set_level(PIN_EC5_POWER, PWR_OFF);
    /* El EC-5 consume ~10 mA: máxima capacidad de corriente del pin */
    gpio_set_drive_capability(PIN_EC5_POWER, GPIO_DRIVE_CAP_3);

    adc_oneshot_unit_init_cfg_t ucfg = { .unit_id = EC5_ADC_UNIT };
    if (adc_oneshot_new_unit(&ucfg, &s_adc) != ESP_OK) {
        ESP_LOGE(TAG, "No se pudo iniciar ADC1");
        return false;
    }
    /* 12 dB: rango hasta ~3.1 V para detectar también lecturas imposibles */
    adc_oneshot_chan_cfg_t ccfg = { .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT };
    adc_oneshot_config_channel(s_adc, EC5_ADC_CHANNEL, &ccfg);

    adc_cali_line_fitting_config_t cal = {
        .unit_id = EC5_ADC_UNIT,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    s_cali_ok = (adc_cali_create_scheme_line_fitting(&cal, &s_cali) == ESP_OK);
    ESP_LOGI(TAG, "EC-5: excitacion GPIO%d, ADC1_CH6 (GPIO%d), calibracion ADC %s",
             PIN_EC5_POWER, PIN_EC5_ADC, s_cali_ok ? "OK" : "NO DISPONIBLE");
    return s_cali_ok;
}

float soil_mv_to_vwc(const riego_config_t *cfg, float mv)
{
    return ec5_mv_to_vwc(cfg, mv);
}

static int cmp_int(const void *a, const void *b)
{
    return (*(const int *)a) - (*(const int *)b);
}

void soil_sensor_measure(const riego_config_t *cfg, soil_reading_t *out)
{
    int mv[N_PULSES];
    int n = 0;
    memset(out, 0, sizeof(*out));

    /* Sin calibración del ADC los mV no son confiables: no se mide.
     * (Además evita esperar una conversión que nunca termina en el emulador QEMU,
     * que no emula el ADC y bloquearía las escrituras en flash del otro núcleo.) */
    if (!s_cali_ok || s_adc == NULL) {
        out->status = "ADC_ERROR";
        return;
    }

    for (int p = 0; p < N_PULSES; p++) {
        gpio_set_level(PIN_EC5_POWER, PWR_ON);
        esp_rom_delay_us(EXCITE_US - 400);        /* Se lee al final del pulso */
        int sum = 0, cnt = 0;
        for (int r = 0; r < READS_PER_PULSE; r++) {
            int raw = 0;
            if (adc_oneshot_read(s_adc, EC5_ADC_CHANNEL, &raw) == ESP_OK) {
                sum += raw;
                cnt++;
            }
        }
        gpio_set_level(PIN_EC5_POWER, PWR_OFF);   /* Excitación ≤ 10 ms */
        if (cnt > 0 && s_cali_ok) {
            int v = 0;
            if (adc_cali_raw_to_voltage(s_cali, sum / cnt, &v) == ESP_OK) {
                mv[n++] = v;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(PULSE_GAP_MS));
    }

    if (n < 3) {
        out->status = "ADC_ERROR";
        return;
    }
    qsort(mv, n, sizeof(int), cmp_int);
    out->mv = mv[n / 2];
    /* Dispersión sin el mayor ni el menor: un pulso raro no invalida toda la medición */
    out->spread_mv = (n >= 5) ? mv[n - 2] - mv[1] : mv[n - 1] - mv[0];
    out->vwc_pct = soil_mv_to_vwc(cfg, (float)out->mv);
    out->in_cal_range = out->mv >= (int)(cfg->ec5_cal_mv_lo * 0.95f) &&
                        out->mv <= (int)(cfg->ec5_cal_mv_hi * 1.05f);

    if (out->mv < (int)cfg->ec5_mv_min) {
        out->status = "SIN_SENAL";          /* Desconectado, cable roto o sin excitación */
    } else if (out->mv > (int)cfg->ec5_mv_max) {
        out->status = "FUERA_DE_RANGO";
    } else if (out->spread_mv > MAX_SPREAD_MV) {
        out->status = "INESTABLE";
    } else if (out->vwc_pct < -10.0f || out->vwc_pct > 70.0f) {
        out->status = "IMPOSIBLE";
    } else {
        out->status = out->in_cal_range ? "OK" : "OK_FUERA_DE_CALIBRACION";
        out->valid = true;
    }
}

/* ---------------- Diagnóstico (solo consola) ---------------- */
static int diag_read_mv(adc_channel_t ch)
{
    int sum = 0, cnt = 0;
    for (int i = 0; i < 8; i++) {
        int raw = 0;
        if (adc_oneshot_read(s_adc, ch, &raw) == ESP_OK) {
            sum += raw;
            cnt++;
        }
    }
    int mv = -1;
    if (cnt > 0 && s_cali_ok) {
        adc_cali_raw_to_voltage(s_cali, sum / cnt, &mv);
    }
    return mv;
}

void soil_sensor_diag(int seconds)
{
    static const struct { adc_channel_t ch; int gpio; } P[] = {
        {ADC_CHANNEL_6, 34}, {ADC_CHANNEL_7, 35}, {ADC_CHANNEL_4, 32},
        {ADC_CHANNEL_5, 33}, {ADC_CHANNEL_0, 36}, {ADC_CHANNEL_3, 39},
    };
    const int n = sizeof(P) / sizeof(P[0]);
    if (!s_cali_ok || s_adc == NULL) {
        printf("EC5 PRUEBA: ADC no disponible\n");
        return;
    }
    adc_oneshot_chan_cfg_t ccfg = { .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT };
    for (int i = 0; i < n; i++) {
        adc_oneshot_config_channel(s_adc, P[i].ch, &ccfg);
    }
    if (seconds < 1) seconds = 1;
    if (seconds > 30) seconds = 30;

    printf("EC5 PRUEBA: excitacion GPIO%d APAGADA (referencia)\n  ", PIN_EC5_POWER);
    for (int i = 0; i < n; i++) printf("GPIO%d=%4d mV  ", P[i].gpio, diag_read_mv(P[i].ch));
    printf("\nEC5 PRUEBA: excitacion GPIO%d ENCENDIDA %d s (mide ahora con el multimetro: blanco-GND y rojo-GND)\n",
           PIN_EC5_POWER, seconds);
    gpio_set_level(PIN_EC5_POWER, PWR_ON);
    vTaskDelay(pdMS_TO_TICKS(20));
    for (int t = 0; t < seconds * 2; t++) {
        printf("  %4.1f s  ", t / 2.0f);
        for (int i = 0; i < n; i++) printf("GPIO%d=%4d mV  ", P[i].gpio, diag_read_mv(P[i].ch));
        printf("\n");
        vTaskDelay(pdMS_TO_TICKS(500));
    }
    gpio_set_level(PIN_EC5_POWER, PWR_OFF);
    vTaskDelay(pdMS_TO_TICKS(20));
    printf("EC5 PRUEBA: excitacion APAGADA\n  ");
    for (int i = 0; i < n; i++) printf("GPIO%d=%4d mV  ", P[i].gpio, diag_read_mv(P[i].ch));
    printf("\nEC5 PRUEBA: fin. La senal del EC-5 es el pin que SUBE con la excitacion encendida "
           "(al aire ~250-400 mV, en tierra mas).\n");
}
