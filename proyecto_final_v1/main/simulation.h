/*
 * Modo simulación: la lógica completa funciona con valores ficticios de los
 * sensores, flujo y hora, y las SALIDAS DE POTENCIA PERMANECEN INACTIVAS
 * (actuators lo garantiza). Se usa para probar sin activar cargas reales.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

typedef enum { SIM_TANK_OK = 0, SIM_TANK_FAIL, SIM_TANK_UNCAL } sim_tank_mode_t;

typedef struct {
    volatile bool active;
    volatile bool soil_valid;
    volatile float soil_vwc;
    volatile int tank_mode;         /* sim_tank_mode_t                         */
    volatile float tank_pct;
    volatile bool env_valid;
    volatile float temp_c;
    volatile float rh;
    volatile float flow_lpm;        /* Caudal simulado cuando la bomba está ON */
    volatile bool time_override;
    volatile bool time_valid;
    volatile int minute;            /* Minuto del día simulado                 */
    volatile uint32_t speed;        /* Aceleración del tiempo (1..120)         */
    volatile float soil_gain_per_l; /* %VWC que sube por litro aplicado        */
} sim_state_t;

sim_state_t *sim(void);
void sim_reset(void);
