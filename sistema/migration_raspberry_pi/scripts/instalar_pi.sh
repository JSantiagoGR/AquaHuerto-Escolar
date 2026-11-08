#!/usr/bin/env bash
# =====================================================================
# INSTALACIÓN DEL SISTEMA DE RIEGO EN LA RASPBERRY PI (entorno "final")
#
# - Instancia de Node-RED INDEPENDIENTE (puerto 1881, userDir propio).
#   NO modifica el Node-RED existente ni el flujo "Equipo 2" ni su dashboard /ui.
# - Base SQLite propia: database/riego_final.db
# - Broker: por defecto NO toca Mosquitto. Con --broker agrega un listener
#   autenticado (puerto 1884) en un archivo aparte de /etc/mosquitto/conf.d/.
#
# Uso (desde la copia del proyecto en la Pi):
#   bash migration_raspberry_pi/scripts/instalar_pi.sh [--broker] [--servicio]
# Requisitos previos: configs/secrets/credenciales_final.env (desde la plantilla)
# =====================================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MIG="$(dirname "$HERE")"
PROJECT="$(dirname "$MIG")"
ENVF="$PROJECT/configs/secrets/credenciales_final.env"
PORT_NR=1881
DO_BROKER=0
DO_SERVICE=0
for a in "$@"; do
  case "$a" in
    --broker) DO_BROKER=1 ;;
    --servicio) DO_SERVICE=1 ;;
  esac
done

echo "== Proyecto: $PROJECT"
[ -f "$ENVF" ] || { echo "Falta $ENVF (copie configs/credenciales_final.env.ejemplo y cambie TODAS las contraseñas)"; exit 1; }
if grep -q "=CAMBIAR" "$ENVF"; then echo "El archivo de credenciales aún tiene valores CAMBIAR"; exit 1; fi
chmod 600 "$ENVF"

echo "== 1. Paquetes del sistema (no se actualiza Node.js automáticamente)"
sudo apt-get update
sudo apt-get install -y mosquitto mosquitto-clients sqlite3 python3 python3-venv build-essential

echo "== 2. Versión de Node.js"
if ! command -v node >/dev/null; then echo "Node.js no está instalado: ver MIGRACION_RASPBERRY_PI.md"; exit 1; fi
NODE_MAJOR=$(node -p 'process.versions.node.split(".")[0]')
NODE_MINOR=$(node -p 'process.versions.node.split(".")[1]')
if [ "$NODE_MAJOR" -gt 22 ] || { [ "$NODE_MAJOR" -eq 22 ] && [ "$NODE_MINOR" -ge 9 ]; }; then
  NR_VERSION=5.0.8
elif [ "$NODE_MAJOR" -ge 18 ]; then
  # Node-RED 5 requiere Node >= 22.9. Para no tocar el Node.js que usa Equipo 2
  # se usa la última 4.x (compatible con Node 18/20).
  NR_VERSION=$(npm view node-red@4 version | tail -1 | awk '{print $NF}' | tr -d "'")
  echo "Node $(node -v): se usará Node-RED $NR_VERSION"
else
  echo "Node $(node -v) es demasiado antiguo para Dashboard 2.0 (requiere >= 18)"; exit 1
fi

echo "== 3. Node-RED independiente ($NR_VERSION) y Dashboard 2.0"
mkdir -p "$PROJECT/nodered/runtime" "$PROJECT/nodered/userdata" "$PROJECT/nodered/logs" "$PROJECT/backups"
cd "$PROJECT/nodered/runtime"
[ -f package.json ] || echo '{"name":"riego-nodered-runtime","private":true}' > package.json
npm install --no-fund --no-audit "node-red@$NR_VERSION"
cd "$PROJECT/nodered/userdata"
cp "$MIG/nodered/package.json" package.json
[ -f settings.js ] || cp "$MIG/nodered/settings.js" settings.js
npm install --no-fund --no-audit
npm approve-scripts sqlite3 >/dev/null 2>&1 || true
npm rebuild sqlite3
node -e "const s=require('sqlite3');new s.Database(':memory:').get('select sqlite_version() v',(e,r)=>console.log('SQLite',e||r.v))"

echo "== 4. Base de datos"
python3 "$PROJECT/database/inicializar_db.py" "$PROJECT/database/riego_final.db"

echo "== 5. Python (simulador y herramientas, opcional)"
python3 -m venv "$PROJECT/.venv"
"$PROJECT/.venv/bin/pip" install --quiet paho-mqtt pyserial

if [ "$DO_BROKER" = 1 ]; then
  echo "== 6. Broker: listener autenticado 1884 (archivo aparte, Equipo 2 intacto)"
  set -a; . "$ENVF"; set +a
  sudo cp "$MIG/mqtt/acl_final.conf" /etc/mosquitto/riego_acl.conf
  sudo rm -f /etc/mosquitto/riego_passwd
  sudo mosquitto_passwd -c -b /etc/mosquitto/riego_passwd "$MQTT_ESP32_USER" "$MQTT_ESP32_PASS"
  sudo mosquitto_passwd -b /etc/mosquitto/riego_passwd "$MQTT_NODERED_USER" "$MQTT_NODERED_PASS"
  sudo mosquitto_passwd -b /etc/mosquitto/riego_passwd "$MQTT_SIM_USER" "$MQTT_SIM_PASS"
  sudo mosquitto_passwd -b /etc/mosquitto/riego_passwd "$MQTT_ADMIN_USER" "$MQTT_ADMIN_PASS"
  sudo chown mosquitto:mosquitto /etc/mosquitto/riego_passwd /etc/mosquitto/riego_acl.conf
  sudo chmod 640 /etc/mosquitto/riego_passwd
  sudo cp "$MIG/mqtt/mosquitto_riego_final.conf" /etc/mosquitto/conf.d/riego_final.conf
  sudo cp /etc/mosquitto/mosquitto.conf "$PROJECT/backups/mosquitto.conf.antes_$(date +%Y%m%d_%H%M)"
  sudo mosquitto -c /etc/mosquitto/mosquitto.conf -t 2>/dev/null || true
  sudo systemctl restart mosquitto
  sleep 2
  systemctl is-active mosquitto || { echo "Mosquitto no arrancó: se retira el archivo nuevo"; sudo rm -f /etc/mosquitto/conf.d/riego_final.conf; sudo systemctl restart mosquitto; exit 1; }
fi

if [ "$DO_SERVICE" = 1 ]; then
  echo "== 7. Servicio systemd riego-nodered (puerto $PORT_NR)"
  sudo tee /etc/systemd/system/riego-nodered.service >/dev/null <<EOF
[Unit]
Description=Node-RED del riego inteligente (entorno final, independiente de Equipo 2)
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
User=$USER
Environment=PORT=$PORT_NR
Environment=RIEGO_ENV_FILE=$ENVF
Environment=RIEGO_ENV=final
WorkingDirectory=$PROJECT/nodered/userdata
ExecStart=$(command -v node) $PROJECT/nodered/runtime/node_modules/node-red/red.js --userDir $PROJECT/nodered/userdata --settings $PROJECT/nodered/userdata/settings.js
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable --now riego-nodered
  sleep 15
  systemctl is-active riego-nodered
fi

echo "== 8. Despliegue del flujo 'final'"
cp "$MIG/flows/flows_riego_final.json" "$PROJECT/dashboard/export/flows_riego_final.json" 2>/dev/null || true
python3 "$PROJECT/nodered/desplegar_flows.py" --entorno final --url "http://127.0.0.1:$PORT_NR" --env-file "$ENVF"
echo "LISTO. Dashboard: http://<IP de la Pi>:$PORT_NR/dashboard  (el /ui de Equipo 2 en 1880 no cambia)"
