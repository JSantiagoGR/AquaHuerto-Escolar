/*
 * IA ligera para el ESP32 (lógica PURA, también compilada en la PC).
 *
 * Dos modelos lineales con aprendizaje incremental por mínimos cuadrados
 * recursivos (RLS) con previa bayesiana (regularización hacia el supuesto
 * inicial), factor de olvido cercano a 1, rechazo de atípicos y detección de
 * cambios (CUSUM). No es PID ni PWM: solo calcula CUÁNTOS LITROS dosificar.
 *
 *  Modelo A (respuesta al riego): Δ%VWC tras la infiltración =
 *      L · (a0 + a1·u1 + a2·u2 + a3·u3 + a4·u4)
 *      u1 = (θ0-25)/10   u2 = (T-20)/10   u3 = (HR-50)/50   u4 = min(h_desde_riego,48)/24
 *
 *  Modelo B (pérdida de humedad): pérdida %VWC/h =
 *      b0 + b1·(θ-25)/10 + b2·Kc·VPD + b3·Kc·ET0_h·10 + b4·sin(2πh/24) + b5·cos(2πh/24)
 *
 * Estados: APRENDIZAJE -> VALIDACION -> PREDICTIVO_ACTIVO. Solo en
 * PREDICTIVO_ACTIVO el modo IA dosifica por modelo; antes se usa el
 * automático conservador y las predicciones solo se registran (modo sombra).
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "configuration.h"

#define IA_NA       5
#define IA_NB       6
#define IA_NMAX     6
#define IA_VAL_A    8
#define IA_VAL_B    24
#define IA_TRAJ     25
#define IA_FC_MAX   24
#define IA_MAGIC    0x49414D31u     /* "IAM1" */
#define IA_VERSION  1u

typedef enum { IA_LEARNING = 0, IA_VALIDATING, IA_ACTIVE } ia_status_t;

typedef struct {
    float w[IA_NMAX];
    float P[IA_NMAX][IA_NMAX];
    float w0[IA_NMAX];          /* Supuesto inicial (previa)                 */
    float p0[IA_NMAX];          /* Varianza previa (diagonal)                */
    float r;                    /* Varianza de medición supuesta             */
    float s2;                   /* Varianza de residuos observada (EWMA)     */
    float lambda;               /* Factor de olvido                          */
    uint32_t n;                 /* Observaciones usadas                      */
    uint32_t outliers;          /* Observaciones rechazadas                  */
    uint8_t dim;
    uint8_t pad[3];
} ia_rls_t;

typedef struct {
    uint32_t magic;
    uint32_t version;
    float data_version;         /* Versión de calibración del suelo          */
    uint32_t model_version;     /* Aumenta con cada actualización guardada   */
    ia_rls_t a, b;
    float err_a[IA_VAL_A];      /* |predicho - real| (pp) antes de aprender  */
    float err_b[IA_VAL_B];      /* |predicho - real| (pp/h)                  */
    uint8_t err_a_n, err_a_i, err_b_n, err_b_i;
    float hours_b;              /* Horas de secado aprendidas                */
    float cusum_pos, cusum_neg;
    uint16_t since_change;
    uint8_t change_flag;
    uint8_t status;             /* ia_status_t                               */
    uint8_t consec_out_a;       /* Atípicos seguidos (3 = cambio del sistema) */
    uint8_t consec_out_b;
    uint8_t pad2[2];
    float last_err_a;           /* Último error de respuesta (con signo)     */
    uint32_t crc;
} ia_model_t;

/* Condiciones para predecir */
typedef struct {
    bool env_valid;
    float temp_c, rh_pct;       /* Sensor local                              */
    float hour;                 /* Hora local (0..24, fraccional)            */
    float kc;
    float hours_since_water;
    int n_fc;                   /* Horas de pronóstico disponibles (0 = sin pronóstico) */
    float fc_temp[IA_FC_MAX];
    float fc_rh[IA_FC_MAX];
    float fc_vpd[IA_FC_MAX];    /* kPa                                       */
    float fc_et0[IA_FC_MAX];    /* mm/h                                      */
} ia_env_t;

typedef enum {
    IA_PLAN_NONE = 0,
    IA_PLAN_NOT_NEEDED,         /* Se mantiene sobre el mínimo hasta el horizonte */
    IA_PLAN_WATER,              /* Regar 'liters' hasta 'goal'                   */
    IA_PLAN_LIMITED,            /* Meta > reserva: se riega solo hasta la reserva */
    IA_PLAN_ABOVE_RESERVE,
    IA_PLAN_NO_SOIL,
} ia_plan_code_t;

typedef struct {
    bool valid;
    ia_plan_code_t code;
    float vwc_now;
    float horizon_h;            /* Horas hasta el siguiente horario preferido */
    float loss_pred;            /* Pérdida prevista en el horizonte (pp)      */
    float vwc_end_no_water;     /* Humedad al final del horizonte sin regar   */
    float goal;                 /* Humedad meta tras el riego                 */
    float gain_per_l;           /* Δ%VWC por litro previsto                   */
    float liters;               /* Litros totales previstos                   */
    float autonomy_h;           /* Horas hasta llegar a la mínima (sin regar) */
    float rate_now;             /* Pérdida actual prevista (pp/h)             */
    float traj[IA_TRAJ];        /* Humedad prevista hora a hora sin regar     */
} ia_plan_t;

void ia_init(ia_model_t *m, const riego_config_t *c);
bool ia_check(const ia_model_t *m);                 /* Integridad (magic/versión) */
float vpd_kpa(float temp_c, float rh_pct);          /* Tetens; NAN si inválido  */

/* Modelo A */
float ia_predict_response(const ia_model_t *m, float liters, float vwc0, bool env_valid,
                          float temp_c, float rh_pct, float hours_since);
/* Devuelve 0 aprendido, 1 atípico (descartado), -1 datos inválidos */
int ia_learn_response(ia_model_t *m, float liters, float vwc0, bool env_valid, float temp_c,
                      float rh_pct, float hours_since, float dvwc_obs, float *pred_out);

/* Modelo B */
float ia_predict_rate(const ia_model_t *m, float vwc, float temp_c, float rh_pct, bool env_valid,
                      float kc, float et0_h, float hour);
int ia_learn_drying(ia_model_t *m, float vwc_mid, float temp_c, float rh_pct, bool env_valid,
                    float kc, float et0_h, float hour, float rate_obs, float *pred_out);

/* Estado y métricas */
void ia_update_status(ia_model_t *m, const riego_config_t *c);
float ia_mae_a(const ia_model_t *m);                /* NAN si no hay datos */
float ia_mae_b(const ia_model_t *m);
const char *ia_status_name(ia_status_t s);
const char *ia_plan_name(ia_plan_code_t c);

/* Plan de riego para mantener la banda hasta el horizonte */
void ia_plan(const ia_model_t *m, const ia_env_t *env, const riego_config_t *c, float vwc,
             float horizon_h, ia_plan_t *out);
/* Litros de corrección proporcional acotada tras una dosis */
float ia_correction_liters(const ia_model_t *m, const riego_config_t *c, float vwc_now, float goal,
                           bool env_valid, float temp_c, float rh_pct);
