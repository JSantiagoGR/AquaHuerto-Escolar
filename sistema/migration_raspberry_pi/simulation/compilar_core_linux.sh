#!/usr/bin/env bash
# Compila en la Raspberry Pi la misma lógica del firmware para el simulador (libriego_core.so).
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")/../.." && pwd)"
FW="$PROJECT/firmware/main"
OUT="$PROJECT/tests/host/build"
mkdir -p "$OUT"
gcc -DHOST_BUILD -std=gnu11 -O2 -Wall -Wextra -Wno-unused-parameter -shared -fPIC -I"$FW" \
  "$FW/app_types.c" "$FW/config_table.c" "$FW/irrigation_logic.c" "$FW/ia_model.c" \
  "$PROJECT/tests/host/host_api.c" -o "$OUT/libriego_core.so" -lm
gcc -DHOST_BUILD -std=gnu11 -O2 -I"$FW" "$FW/app_types.c" "$FW/config_table.c" "$FW/irrigation_logic.c" \
  "$FW/ia_model.c" "$FW/logic_tests.c" "$PROJECT/tests/host/main_logic_tests.c" -o "$OUT/logic_tests" -lm
"$OUT/logic_tests" | tail -1
echo "Simulador en la Pi: python3 simulation/simulador_huerto.py --env-file configs/secrets/credenciales_final.env"
echo "(cambie DEVICE/topics a huerto/final/sim_01 si lo usa en el entorno final)"
