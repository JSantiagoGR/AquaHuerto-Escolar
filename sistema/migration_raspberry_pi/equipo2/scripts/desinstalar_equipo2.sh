#!/usr/bin/env bash
# Desinstala Equipo 2 Proyecto: detiene SUS procesos y quita SU línea del crontab.
# La carpeta (con la base de datos y respaldos) se conserva; bórrala a mano si ya no la necesitas.
set -uo pipefail
P="$(cd "$(dirname "$0")/.." && pwd)"
bash "$P/scripts/detener_equipo2.sh"
if crontab -l 2>/dev/null | grep -qF "$P/scripts/iniciar_equipo2.sh"; then
  crontab -l | grep -vF "$P/scripts/iniciar_equipo2.sh" | crontab -
  echo "Línea @reboot de Equipo 2 Proyecto retirada del crontab (las demás se conservan)."
fi
echo "Listo. Nada fuera de $P fue modificado."
