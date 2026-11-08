/*
 * Filtro de lecturas lentas (humedad del suelo, distancia del tinaco). Lógica PURA, también
 * compilada en la PC para las pruebas.
 *  - Mediana de las últimas 3 lecturas aceptadas (quita picos sueltos).
 *  - Rechazo de saltos: si una lectura se aleja más de 'max_jump' del valor filtrado se
 *    retiene (se sigue usando el valor anterior) hasta que 'confirm_n' lecturas seguidas
 *    coincidan entre sí (± 'agree'); entonces el cambio es real y se acepta.
 *  - Gracia ante fallas: una lectura inválida aislada conserva el último valor bueno hasta
 *    'grace_n' lecturas seguidas; después el valor se declara inválido.
 */
#pragma once
#include <stdbool.h>

#define SFILT_N 3

typedef struct {
    float max_jump;     /* Salto máximo aceptado sin confirmación              */
    float agree;        /* Coincidencia entre lecturas que confirman un salto  */
    int confirm_n;      /* Lecturas seguidas que confirman un salto            */
    int grace_n;        /* Lecturas inválidas toleradas con el último valor    */

    float hist[SFILT_N];
    int n, idx;
    float out;          /* Valor filtrado vigente                              */
    bool have;          /* Hay un valor filtrado válido                        */
    float pend;         /* Candidato de salto en confirmación                  */
    int pend_n;
    int bad_n;          /* Lecturas inválidas seguidas                         */
} sfilt_t;

typedef enum {
    SF_ACCEPTED = 0,    /* Lectura dentro de lo esperado                       */
    SF_JUMP_CONFIRMED,  /* Cambio grande confirmado: se adopta                 */
    SF_HELD,            /* Salto sin confirmar: se conserva el valor anterior  */
    SF_GRACE,           /* Lectura inválida: se conserva el último valor bueno */
    SF_INVALID,         /* Demasiadas inválidas seguidas                       */
} sfilt_result_t;

void sfilt_init(sfilt_t *f, float max_jump, float agree, int confirm_n, int grace_n);
/* valid = la lectura cruda pasó las verificaciones del sensor. Devuelve qué se hizo;
 * el valor a usar queda en f->out (solo si f->have). */
sfilt_result_t sfilt_push(sfilt_t *f, bool valid, float x);
const char *sfilt_result_name(sfilt_result_t r);
