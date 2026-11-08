#!/usr/bin/env bash
# Restaura un respaldo creado con respaldar_pi.sh (o un .db de backups/db).
# Uso: bash restaurar_pi.sh <carpeta_o_archivo_de_respaldo>
# La base actual NO se borra: se renombra a riego_final.db.antes_<fecha>.
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="${1:?Indique el respaldo}"
DB="$SRC"
[ -d "$SRC" ] && DB="$SRC/riego_final.db"
sqlite3 "$DB" "PRAGMA integrity_check;" | grep -q ok || { echo "El respaldo no pasa integrity_check"; exit 1; }
sudo systemctl stop riego-nodered || true
mv "$PROJECT/database/riego_final.db" "$PROJECT/database/riego_final.db.antes_$(date +%Y%m%d_%H%M)" 2>/dev/null || true
cp "$DB" "$PROJECT/database/riego_final.db"
[ -d "$SRC/context" ] && cp -r "$SRC/context" "$PROJECT/nodered/userdata/"
sudo systemctl start riego-nodered || true
echo "Restaurado desde $SRC"
