#include "sensor_filter.h"

#include <math.h>
#include <string.h>

void sfilt_init(sfilt_t *f, float max_jump, float agree, int confirm_n, int grace_n)
{
    memset(f, 0, sizeof(*f));
    f->max_jump = max_jump;
    f->agree = agree;
    f->confirm_n = confirm_n < 1 ? 1 : confirm_n;
    f->grace_n = grace_n < 0 ? 0 : grace_n;
}

static float median3(const sfilt_t *f)
{
    if (f->n == 1) {
        return f->hist[0];
    }
    if (f->n == 2) {
        return (f->hist[0] + f->hist[1]) / 2.0f;
    }
    float a = f->hist[0], b = f->hist[1], c = f->hist[2];
    return fmaxf(fminf(a, b), fminf(fmaxf(a, b), c));
}

static void reseed(sfilt_t *f, float x)
{
    f->hist[0] = x;
    f->n = 1;
    f->idx = 1;
    f->out = x;
    f->have = true;
    f->pend_n = 0;
}

static void add(sfilt_t *f, float x)
{
    f->hist[f->idx] = x;
    f->idx = (f->idx + 1) % SFILT_N;
    if (f->n < SFILT_N) {
        f->n++;
    }
    f->out = median3(f);
}

sfilt_result_t sfilt_push(sfilt_t *f, bool valid, float x)
{
    if (!valid || !isfinite(x)) {
        f->bad_n++;
        if (f->have && f->bad_n <= f->grace_n) {
            return SF_GRACE;
        }
        f->have = false;
        f->n = 0;
        f->pend_n = 0;
        return SF_INVALID;
    }
    f->bad_n = 0;
    if (!f->have) {                         /* Primera lectura (o tras una falla larga) */
        reseed(f, x);
        return SF_ACCEPTED;
    }
    if (fabsf(x - f->out) <= f->max_jump) {
        f->pend_n = 0;
        add(f, x);
        return SF_ACCEPTED;
    }
    /* Salto grande: solo se cree si se repite */
    if (f->pend_n > 0 && fabsf(x - f->pend) <= f->agree) {
        f->pend = (f->pend * (float)f->pend_n + x) / (float)(f->pend_n + 1);
        f->pend_n++;
    } else {
        f->pend = x;
        f->pend_n = 1;
    }
    if (f->pend_n >= f->confirm_n) {
        reseed(f, f->pend);
        return SF_JUMP_CONFIRMED;
    }
    return SF_HELD;
}

const char *sfilt_result_name(sfilt_result_t r)
{
    static const char *const N[] = { "ACEPTADA", "SALTO_CONFIRMADO", "SALTO_IGNORADO", "RETENIDA", "INVALIDA" };
    return (r <= SF_INVALID) ? N[r] : "?";
}
