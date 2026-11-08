#include "simulation.h"

static sim_state_t s_sim;

sim_state_t *sim(void)
{
    return &s_sim;
}

void sim_reset(void)
{
    bool was_active = s_sim.active;
    s_sim.active = was_active;
    s_sim.soil_valid = true;
    s_sim.soil_vwc = 30.0f;
    s_sim.tank_mode = SIM_TANK_OK;
    s_sim.tank_pct = 80.0f;
    s_sim.env_valid = true;
    s_sim.temp_c = 22.0f;
    s_sim.rh = 50.0f;
    s_sim.flow_lpm = 4.0f;          /* Similar a lo observado (3.5–4.5 L/min) */
    s_sim.time_override = true;
    s_sim.time_valid = true;
    s_sim.minute = 7 * 60;          /* 07:00, dentro del horario 1 */
    s_sim.speed = 60;               /* 1 s real = 1 min simulado */
    s_sim.soil_gain_per_l = 4.0f;
}
