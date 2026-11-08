#include <math.h>
#include <string.h>

#include "ia_model.h"

#define PI_F            3.14159265f
#define LAMBDA_A        0.995f      /* Memoria efectiva ~200 riegos            */
#define LAMBDA_B        0.999f      /* Memoria efectiva ~1000 h (~6 semanas)   */
#define OUTLIER_K       4.0f        /* Residuo > 4 desviaciones: atípico       */
#define CUSUM_K         0.5f
#define CUSUM_H         6.0f
#define EWMA_ALPHA      0.05f
#define RATE_MAX        3.0f        /* pp/h: pérdida máxima creíble            */
#define VAL_B_TOL       0.4f        /* pp/h: error medio aceptable modelo B    */

static float clampf(float v, float lo, float hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

const char *ia_status_name(ia_status_t s)
{
    switch (s) {
    case IA_LEARNING:   return "APRENDIZAJE";
    case IA_VALIDATING: return "VALIDACION";
    case IA_ACTIVE:     return "PREDICTIVO_ACTIVO";
    default:            return "?";
    }
}

const char *ia_plan_name(ia_plan_code_t c)
{
    static const char *const N[] = { "NONE", "NOT_NEEDED", "WATER", "LIMITED", "ABOVE_RESERVE", "NO_SOIL" };
    return (c <= IA_PLAN_NO_SOIL) ? N[c] : "?";
}

float vpd_kpa(float temp_c, float rh_pct)
{
    if (!isfinite(temp_c) || !isfinite(rh_pct) || rh_pct < 0 || rh_pct > 100) {
        return NAN;
    }
    float es = 0.6108f * expf(17.27f * temp_c / (temp_c + 237.3f));
    return es * (1.0f - rh_pct / 100.0f);
}

/* ------------------------------- RLS ------------------------------------ */

static void rls_init(ia_rls_t *r, int dim, const float *w0, const float *p0, float noise, float lambda)
{
    memset(r, 0, sizeof(*r));
    r->dim = (uint8_t)dim;
    r->r = noise;
    r->s2 = noise;
    r->lambda = lambda;
    for (int i = 0; i < dim; i++) {
        r->w[i] = r->w0[i] = w0[i];
        r->p0[i] = p0[i];
        r->P[i][i] = p0[i];
    }
}

static float dot(const float *a, const float *b, int n)
{
    float s = 0;
    for (int i = 0; i < n; i++) {
        s += a[i] * b[i];
    }
    return s;
}

static float rls_predict(const ia_rls_t *r, const float *x)
{
    return dot(r->w, x, r->dim);
}

/* Varianza de la predicción (incertidumbre de parámetros) */
static float rls_xpx(const ia_rls_t *r, const float *x)
{
    float px[IA_NMAX];
    for (int i = 0; i < r->dim; i++) {
        px[i] = dot(r->P[i], x, r->dim);
    }
    return dot(x, px, r->dim);
}

/* 0 = actualizado, 1 = atípico */
static int rls_update(ia_rls_t *r, const float *x, float y, float *resid, bool force)
{
    int n = r->dim;
    float pred = rls_predict(r, x);
    float e = y - pred;
    float xpx = rls_xpx(r, x);
    *resid = e;
    if (!force && r->n >= 6 && fabsf(e) > OUTLIER_K * sqrtf(r->s2 + xpx)) {
        r->outliers++;
        return 1;
    }
    float px[IA_NMAX];
    for (int i = 0; i < n; i++) {
        px[i] = dot(r->P[i], x, n);
    }
    float den = r->r + xpx;
    float k[IA_NMAX];
    for (int i = 0; i < n; i++) {
        k[i] = px[i] / den;
        r->w[i] += k[i] * e;
    }
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            r->P[i][j] = (r->P[i][j] - k[i] * px[j]) / r->lambda;
        }
    }
    /* Simetría y tope de la covarianza (evita "wind-up" con el olvido) */
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            float m = 0.5f * (r->P[i][j] + r->P[j][i]);
            r->P[i][j] = r->P[j][i] = m;
        }
        float cap = 10.0f * r->p0[i];
        if (r->P[i][i] > cap) {
            float s = sqrtf(cap / r->P[i][i]);
            for (int j = 0; j < n; j++) {
                r->P[i][j] *= s;
                r->P[j][i] *= s;
            }
        }
        if (r->P[i][i] < 1e-7f) {
            r->P[i][i] = 1e-7f;
        }
    }
    r->s2 = (1.0f - EWMA_ALPHA) * r->s2 + EWMA_ALPHA * e * e;
    r->n++;
    return 0;
}

static void rls_inflate(ia_rls_t *r, float f)
{
    for (int i = 0; i < r->dim; i++) {
        for (int j = 0; j < r->dim; j++) {
            r->P[i][j] *= f;
        }
    }
}

/* ------------------------------ Modelos --------------------------------- */

void ia_init(ia_model_t *m, const riego_config_t *c)
{
    memset(m, 0, sizeof(*m));
    m->magic = IA_MAGIC;
    m->version = IA_VERSION;
    m->data_version = c->data_version;
    const float g0 = c->ia_gain_prior;
    const float wa[IA_NA] = { g0, 0, 0, 0, 0 };
    const float pa[IA_NA] = { (0.75f * g0) * (0.75f * g0), 0.25f * g0 * g0, 0.1f * g0 * g0,
                              0.1f * g0 * g0, 0.1f * g0 * g0 };
    rls_init(&m->a, IA_NA, wa, pa, 1.0f, LAMBDA_A);
    /* Previa de secado: ~0.1 pp/h, más con VPD/ET0 altos (supuesto débil) */
    const float wb[IA_NB] = { 0.05f, 0.02f, 0.05f, 0.05f, 0.0f, 0.0f };
    const float pb[IA_NB] = { 0.04f, 0.01f, 0.04f, 0.04f, 0.01f, 0.01f };
    rls_init(&m->b, IA_NB, wb, pb, 0.04f, LAMBDA_B);
    m->status = IA_LEARNING;
}

bool ia_check(const ia_model_t *m)
{
    return m->magic == IA_MAGIC && m->version == IA_VERSION && m->a.dim == IA_NA && m->b.dim == IA_NB;
}

static void feat_a(float *x, float L, float v0, bool env, float t, float rh, float hs)
{
    float u1 = (v0 - 25.0f) / 10.0f;
    float u2 = env ? (t - 20.0f) / 10.0f : 0.0f;
    float u3 = env ? (rh - 50.0f) / 50.0f : 0.0f;
    float u4 = clampf(isfinite(hs) ? hs : 24.0f, 0.0f, 48.0f) / 24.0f;
    x[0] = L;
    x[1] = L * u1;
    x[2] = L * u2;
    x[3] = L * u3;
    x[4] = L * u4;
}

static void feat_b(float *z, float v, float t, float rh, bool env, float kc, float et0, float hour)
{
    float vpd = env ? vpd_kpa(t, rh) : NAN;
    if (!isfinite(vpd)) {
        vpd = 1.0f;                     /* Sin sensor: valor típico, se marca en el plan */
    }
    if (!isfinite(et0) || et0 < 0) {
        et0 = 0.12f * vpd;              /* Aproximación si no hay pronóstico */
    }
    z[0] = 1.0f;
    z[1] = (v - 25.0f) / 10.0f;
    z[2] = kc * vpd;
    z[3] = kc * et0 * 10.0f;
    z[4] = sinf(2.0f * PI_F * hour / 24.0f);
    z[5] = cosf(2.0f * PI_F * hour / 24.0f);
}

float ia_predict_response(const ia_model_t *m, float liters, float vwc0, bool env_valid,
                          float temp_c, float rh_pct, float hours_since)
{
    float x[IA_NA];
    feat_a(x, liters, vwc0, env_valid, temp_c, rh_pct, hours_since);
    /* Nunca se predice que el agua seque el suelo */
    return fmaxf(0.0f, rls_predict(&m->a, x));
}

static void push_err(float *ring, uint8_t *n, uint8_t *i, int cap, float e)
{
    ring[*i] = e;
    *i = (uint8_t)((*i + 1) % cap);
    if (*n < cap) {
        (*n)++;
    }
}

/* Cambio sostenido del sistema (suelo, sensor, cultivo): se vuelve a validar
 * y se permite adaptar más rápido SIN borrar lo aprendido */
static void change_detected(ia_model_t *m)
{
    m->change_flag = 1;
    m->since_change = 0;
    m->cusum_pos = m->cusum_neg = 0.0f;
    rls_inflate(&m->a, 2.0f);
    rls_inflate(&m->b, 2.0f);
}

static void cusum(ia_model_t *m, float z)
{
    m->cusum_pos = fmaxf(0.0f, m->cusum_pos + z - CUSUM_K);
    m->cusum_neg = fmaxf(0.0f, m->cusum_neg - z - CUSUM_K);
    if (m->cusum_pos > CUSUM_H || m->cusum_neg > CUSUM_H) {
        change_detected(m);
    }
}

/* Un atípico aislado se descarta; tres seguidos indican un cambio real y se
 * aprende de ellos (con la covarianza ampliada) */
static int learn_with_outliers(ia_model_t *m, ia_rls_t *r, uint8_t *consec, const float *x, float y,
                               float *resid)
{
    int res = rls_update(r, x, y, resid, false);
    if (res == 1) {
        if (++(*consec) >= 3) {
            *consec = 0;
            change_detected(m);
            res = rls_update(r, x, y, resid, true);
        }
    } else {
        *consec = 0;
    }
    return res;
}

int ia_learn_response(ia_model_t *m, float liters, float vwc0, bool env_valid, float temp_c,
                      float rh_pct, float hours_since, float dvwc_obs, float *pred_out)
{
    if (!(liters >= 0.05f) || !isfinite(vwc0) || !isfinite(dvwc_obs) || dvwc_obs < -1.0f || dvwc_obs > 40.0f) {
        return -1;
    }
    float x[IA_NA];
    feat_a(x, liters, vwc0, env_valid, temp_c, rh_pct, hours_since);
    float pred = fmaxf(0.0f, rls_predict(&m->a, x));
    if (pred_out) {
        *pred_out = pred;
    }
    float resid;
    /* El error de validación se registra SIEMPRE (también atípicos) y antes
     * de aprender: es un error fuera de muestra, honesto */
    push_err(m->err_a, &m->err_a_n, &m->err_a_i, IA_VAL_A, fabsf(dvwc_obs - pred));
    m->last_err_a = dvwc_obs - pred;
    int r = learn_with_outliers(m, &m->a, &m->consec_out_a, x, dvwc_obs, &resid);
    if (r == 0) {
        cusum(m, resid / sqrtf(m->a.s2 + 1e-6f));
        if (m->since_change < 65535) {
            m->since_change++;
        }
        m->model_version++;
    }
    return r;
}

float ia_predict_rate(const ia_model_t *m, float vwc, float temp_c, float rh_pct, bool env_valid,
                      float kc, float et0_h, float hour)
{
    float z[IA_NB];
    feat_b(z, vwc, temp_c, rh_pct, env_valid, kc, et0_h, hour);
    return clampf(rls_predict(&m->b, z), 0.0f, RATE_MAX);
}

int ia_learn_drying(ia_model_t *m, float vwc_mid, float temp_c, float rh_pct, bool env_valid,
                    float kc, float et0_h, float hour, float rate_obs, float *pred_out)
{
    if (!isfinite(rate_obs) || rate_obs < -0.5f || rate_obs > RATE_MAX) {
        return -1;
    }
    float z[IA_NB];
    feat_b(z, vwc_mid, temp_c, rh_pct, env_valid, kc, et0_h, hour);
    float pred = clampf(rls_predict(&m->b, z), 0.0f, RATE_MAX);
    if (pred_out) {
        *pred_out = pred;
    }
    float resid;
    push_err(m->err_b, &m->err_b_n, &m->err_b_i, IA_VAL_B, fabsf(rate_obs - pred));
    int r = learn_with_outliers(m, &m->b, &m->consec_out_b, z, rate_obs, &resid);
    if (r == 0) {
        m->hours_b += 1.0f;
    }
    return r;
}

static float mean(const float *v, int n)
{
    if (n <= 0) {
        return NAN;
    }
    float s = 0;
    for (int i = 0; i < n; i++) {
        s += v[i];
    }
    return s / (float)n;
}

float ia_mae_a(const ia_model_t *m) { return mean(m->err_a, m->err_a_n); }
float ia_mae_b(const ia_model_t *m) { return mean(m->err_b, m->err_b_n); }

void ia_update_status(ia_model_t *m, const riego_config_t *c)
{
    if ((float)m->a.n < c->ia_min_events || m->hours_b < c->ia_min_hours) {
        m->status = IA_LEARNING;
        return;
    }
    float ma = ia_mae_a(m), mb = ia_mae_b(m);
    bool ok = isfinite(ma) && isfinite(mb) && ma <= c->ia_tol_pp && mb <= VAL_B_TOL &&
              m->err_a_n >= 4 && m->err_b_n >= 12;
    if (m->change_flag) {
        if (ok && m->since_change >= 4) {
            m->change_flag = 0;
        } else {
            ok = false;
        }
    }
    m->status = ok ? IA_ACTIVE : IA_VALIDATING;
}

/* ------------------------------- Plan ----------------------------------- */

static void env_at(const ia_env_t *e, int h, float *t, float *rh, float *et0, bool *valid)
{
    if (h < e->n_fc && isfinite(e->fc_temp[h]) && isfinite(e->fc_rh[h])) {
        *t = e->fc_temp[h];
        *rh = e->fc_rh[h];
        *et0 = e->fc_et0[h];
        *valid = true;
    } else {
        *t = e->temp_c;
        *rh = e->rh_pct;
        *et0 = NAN;
        *valid = e->env_valid;
    }
}

void ia_plan(const ia_model_t *m, const ia_env_t *env, const riego_config_t *c, float vwc,
             float horizon_h, ia_plan_t *out)
{
    memset(out, 0, sizeof(*out));
    out->vwc_now = vwc;
    out->horizon_h = horizon_h;
    if (!isfinite(vwc)) {
        out->code = IA_PLAN_NO_SOIL;
        return;
    }
    out->valid = true;
    float kc = env->kc > 0 ? env->kc : 1.0f;

    /* Trayectoria sin regar, hora por hora */
    float v = vwc;
    float loss = 0.0f;
    float autonomy = -1.0f;
    out->traj[0] = v;
    int H = (int)ceilf(fmaxf(horizon_h, 0.0f));
    int Hmax = H > 48 ? H : 48;
    for (int h = 0; h < Hmax; h++) {
        float t, rh, et0;
        bool ev;
        env_at(env, h, &t, &rh, &et0, &ev);
        float hour = fmodf(env->hour + (float)h + 0.5f, 24.0f);
        float rate = ia_predict_rate(m, v, t, rh, ev, kc, et0, hour);
        if (h == 0) {
            out->rate_now = rate;
        }
        float step = rate;
        if (h < H) {
            float frac = fminf(1.0f, horizon_h - (float)h);
            loss += step * frac;
        }
        v -= step;
        if (h + 1 < IA_TRAJ) {
            out->traj[h + 1] = v;
        }
        if (autonomy < 0 && v <= c->hum_min) {
            autonomy = (float)h + 1.0f;
        }
    }
    out->loss_pred = loss;
    out->vwc_end_no_water = vwc - loss;
    out->autonomy_h = autonomy < 0 ? 99.0f : autonomy;
    out->gain_per_l = clampf(ia_predict_response(m, 1.0f, vwc, env->env_valid, env->temp_c,
                                                 env->rh_pct, env->hours_since_water), 0.05f, 30.0f);

    if (vwc >= c->hum_reserve) {
        out->code = IA_PLAN_ABOVE_RESERVE;
        out->goal = vwc;
        return;
    }
    float floor_v = c->hum_min + c->ia_margin_pp;
    if (out->vwc_end_no_water >= floor_v) {
        out->code = IA_PLAN_NOT_NEEDED;
        out->goal = vwc;
        return;
    }
    /* Menor meta que mantiene la banda hasta el siguiente horario preferido */
    float goal = floor_v + loss;
    out->code = IA_PLAN_WATER;
    if (goal > c->hum_reserve) {
        goal = c->hum_reserve;
        out->code = IA_PLAN_LIMITED;
    }
    out->goal = goal;
    float L = (goal - vwc) / out->gain_per_l;
    out->liters = clampf(L, 0.0f, c->max_liters_event);
    if (out->liters < 0.1f) {
        out->code = IA_PLAN_NOT_NEEDED;
        out->liters = 0.0f;
    }
}

float ia_correction_liters(const ia_model_t *m, const riego_config_t *c, float vwc_now, float goal,
                           bool env_valid, float temp_c, float rh_pct)
{
    float err = goal - vwc_now;
    if (err <= c->ia_tol_pp * 0.5f) {
        return 0.0f;
    }
    float g = clampf(ia_predict_response(m, 1.0f, vwc_now, env_valid, temp_c, rh_pct, 0.5f), 0.05f, 30.0f);
    return clampf(c->ia_kp * err / g, 0.0f, c->liters_per_cycle);
}
