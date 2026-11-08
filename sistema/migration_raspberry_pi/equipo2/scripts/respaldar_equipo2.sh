#!/usr/bin/env bash
# Respaldo de Equipo 2 Proyecto: base SQLite (copia consistente), flujos, contexto y configuración del broker.
# No incluye contraseñas en texto (el archivo de credenciales queda fuera).
set -euo pipefail
P="$(cd "$(dirname "$0")/.." && pwd)"
TS=$(date +%Y%m%d_%H%M)
mkdir -p "$P/backups/db"
python3 - "$P/database/riego_final.db" "$P/backups/db/riego_final_$TS.db" <<'EOF'
import sqlite3, sys
s = sqlite3.connect(sys.argv[1]); d = sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()
EOF
tar -czf "$P/backups/equipo2_config_$TS.tar.gz" -C "$P" \
  nodered/userdata/flows_riego.json nodered/userdata/flows_riego_cred.json nodered/userdata/context \
  nodered/userdata/settings.js nodered/userdata/package.json mqtt/mosquitto_equipo2.conf mqtt/acl_final.conf 2>/dev/null || true
ls -lh "$P/backups/db/riego_final_$TS.db" "$P/backups/equipo2_config_$TS.tar.gz"
