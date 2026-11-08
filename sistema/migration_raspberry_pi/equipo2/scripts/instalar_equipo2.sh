#!/usr/bin/env bash
# =====================================================================
# INSTALACIÓN DE "EQUIPO 2 PROYECTO" EN LA RASPBERRY PI
#
# Todo vive en ESTA carpeta (por ejemplo ~/equipo2_proyecto):
#   - Node-RED propio en el puerto 1881 (userDir y runtime propios)
#   - Broker Mosquitto propio en el puerto 1884 (usuarios + ACL)
#   - Base SQLite migrada desde la laptop, respaldos y registros
#
# NO usa sudo, NO instala paquetes del sistema, NO modifica /etc,
# NO reinicia servicios y NO toca el Node-RED del puerto 1880 ni el
# broker del puerto 1883 (los de los 6 equipos).
#
# Uso:  bash scripts/instalar_equipo2.sh [--autoarranque]
#   --autoarranque  agrega UNA línea @reboot al crontab de este usuario
#                   (las demás líneas del crontab se conservan)
# =====================================================================
set -euo pipefail
P="$(cd "$(dirname "$0")/.." && pwd)"
ENVF="$P/configs/secrets/credenciales_final.env"
NR_PORT=1881
MQ_PORT=1884
AUTO=0
for a in "$@"; do [ "$a" = "--autoarranque" ] && AUTO=1; done
log() { echo; echo "== $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

log "Carpeta del proyecto: $P"
[ -f "$ENVF" ] || fail "Falta $ENVF (se copia aparte, no viene en el zip)"
chmod 700 "$P/configs/secrets"
chmod 600 "$ENVF"

log "1. Verificaciones (solo lectura)"
command -v node >/dev/null || fail "Node.js no está instalado (este script no instala nada del sistema)"
command -v npm >/dev/null || fail "npm no está disponible"
command -v python3 >/dev/null || fail "Falta python3"
MQ_BIN="$(command -v mosquitto || true)"
[ -z "$MQ_BIN" ] && [ -x /usr/sbin/mosquitto ] && MQ_BIN=/usr/sbin/mosquitto
[ -n "$MQ_BIN" ] || fail "No se encontró el programa mosquitto"
MQ_PASSWD="$(command -v mosquitto_passwd || true)"
[ -z "$MQ_PASSWD" ] && [ -x /usr/bin/mosquitto_passwd ] && MQ_PASSWD=/usr/bin/mosquitto_passwd
[ -n "$MQ_PASSWD" ] || fail "No se encontró mosquitto_passwd"
for port in $NR_PORT $MQ_PORT; do
  if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${port}\$"; then
    fail "El puerto $port ya está en uso. Si es esta instancia, deténla con scripts/detener_equipo2.sh"
  fi
done
NODE_MAJOR=$(node -p 'process.versions.node.split(".")[0]')
NODE_MINOR=$(node -p 'process.versions.node.split(".")[1]')
if [ "$NODE_MAJOR" -gt 22 ] || { [ "$NODE_MAJOR" -eq 22 ] && [ "$NODE_MINOR" -ge 9 ]; }; then
  NR_VERSION=5.0.8
elif [ "$NODE_MAJOR" -ge 18 ]; then
  NR_VERSION=4.1.6          # misma versión que el Node-RED de los equipos (compatible con este Node.js)
else
  fail "Node $(node -v) es demasiado antiguo para Dashboard 2.0 (requiere >= 18)"
fi
echo "Node $(node -v) · npm $(npm -v) · mosquitto: $MQ_BIN · Node-RED propio: $NR_VERSION"

log "2. Node-RED propio (solo dentro de $P/nodered)"
mkdir -p "$P/nodered/runtime" "$P/logs" "$P/run" "$P/backups/db"
cd "$P/nodered/runtime"
[ -f package.json ] || echo '{"name":"equipo2-nodered-runtime","private":true}' > package.json
npm install --no-fund --no-audit --loglevel=error "node-red@$NR_VERSION"
cd "$P/nodered/userdata"
npm install --no-fund --no-audit --loglevel=error
node -e "const s=require('sqlite3');new s.Database(':memory:').get('select sqlite_version() v',(e,r)=>{if(e){console.error(e);process.exit(1)}console.log('SQLite',r.v)})"

log "3. Broker propio (puerto $MQ_PORT, archivos en $P/mqtt)"
set -a; . "$ENVF"; set +a
mkdir -p "$P/mqtt/data"
rm -f "$P/mqtt/passwd"
touch "$P/mqtt/passwd"; chmod 600 "$P/mqtt/passwd"
"$MQ_PASSWD" -b "$P/mqtt/passwd" "$MQTT_ESP32_USER" "$MQTT_ESP32_PASS"
"$MQ_PASSWD" -b "$P/mqtt/passwd" "$MQTT_NODERED_USER" "$MQTT_NODERED_PASS"
"$MQ_PASSWD" -b "$P/mqtt/passwd" "$MQTT_SIM_USER" "$MQTT_SIM_PASS"
"$MQ_PASSWD" -b "$P/mqtt/passwd" "$MQTT_ADMIN_USER" "$MQTT_ADMIN_PASS"
chmod 600 "$P/mqtt/acl_final.conf"
cat > "$P/mqtt/mosquitto_equipo2.conf" <<EOF
# Broker PROPIO de Equipo 2 Proyecto. NO es el broker del sistema (puerto 1883).
listener $MQ_PORT 0.0.0.0
allow_anonymous false
password_file $P/mqtt/passwd
acl_file $P/mqtt/acl_final.conf
persistence true
persistence_location $P/mqtt/data/
autosave_interval 300
max_packet_size 262144
max_queued_messages 500
max_inflight_messages 20
max_keepalive 120
log_dest file $P/logs/mosquitto.log
log_type error
log_type warning
log_type notice
connection_messages true
log_timestamp_format %Y-%m-%dT%H:%M:%S
EOF
echo "MQ_BIN=$MQ_BIN" > "$P/run/rutas.env"

log "4. Base de datos migrada (se completa el esquema sin borrar datos)"
python3 "$P/database/inicializar_db.py" "$P/database/riego_final.db" | tail -2

log "5. Arranque"
bash "$P/scripts/iniciar_equipo2.sh"

log "6. Despliegue del flujo 'Equipo 2 Proyecto' en la instancia propia (puerto $NR_PORT)"
python3 "$P/nodered/desplegar_flows.py" --entorno final --url "http://127.0.0.1:$NR_PORT" --env-file "$ENVF"

if [ "$AUTO" = 1 ]; then
  log "7. Arranque automático: una línea @reboot en el crontab de $(whoami)"
  LINE="@reboot sleep 30 && bash $P/scripts/iniciar_equipo2.sh >> $P/logs/arranque.log 2>&1"
  { crontab -l 2>/dev/null | grep -vF "$P/scripts/iniciar_equipo2.sh" || true; echo "$LINE"; } | crontab -
  crontab -l | grep -F "$P/scripts/iniciar_equipo2.sh"
fi

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
echo "LISTO."
echo "  Dashboard (compartible):  http://${IP:-<IP de la Pi>}:$NR_PORT/dashboard   usuario/contraseña DASHBOARD_* del archivo de credenciales"
echo "  Editor (solo el equipo):  http://${IP:-<IP de la Pi>}:$NR_PORT          usuario/contraseña NODERED_ADMIN_*"
echo "  Broker propio:            mqtt://${IP:-<IP de la Pi>}:$MQ_PORT  (usuarios y ACL)"
echo "  El Node-RED del puerto 1880 y el broker del 1883 no se modificaron."
