#!/usr/bin/env bash
# Respaldo consistente del entorno final: SQLite (.backup en caliente), flujos y contexto.
# Uso: bash respaldar_pi.sh            (recomendado en cron diario: 0 3 * * *)
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")/../.." && pwd)"
STAMP=$(date +%Y%m%d_%H%M)
DEST="$PROJECT/backups/pi_$STAMP"
mkdir -p "$DEST"
sqlite3 "$PROJECT/database/riego_final.db" ".backup '$DEST/riego_final.db'"
cp "$PROJECT/nodered/userdata/flows_riego.json" "$DEST/" 2>/dev/null || true
cp -r "$PROJECT/nodered/userdata/context" "$DEST/context" 2>/dev/null || true
sqlite3 "$DEST/riego_final.db" "PRAGMA integrity_check;" | grep -q ok && echo "Respaldo verificado: $DEST"
