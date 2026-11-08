#!/usr/bin/env bash
# Inicia el broker propio (1884) y el Node-RED propio (1881) de Equipo 2 Proyecto.
# Solo procesos de este usuario; no toca el Node-RED 1880 ni el broker 1883.
set -uo pipefail
P="$(cd "$(dirname "$0")/.." && pwd)"
ENVF="$P/configs/secrets/credenciales_final.env"
mkdir -p "$P/run" "$P/logs"
MQ_BIN="$(command -v mosquitto || echo /usr/sbin/mosquitto)"
[ -f "$P/run/rutas.env" ] && . "$P/run/rutas.env"

vivo() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }
puerto() { ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1\$"; }

if vivo "$P/run/mosquitto.pid"; then
  echo "Broker propio ya corriendo (PID $(cat "$P/run/mosquitto.pid"))"
else
  nohup "$MQ_BIN" -c "$P/mqtt/mosquitto_equipo2.conf" >> "$P/logs/mosquitto_salida.log" 2>&1 &
  echo $! > "$P/run/mosquitto.pid"
  sleep 2
  vivo "$P/run/mosquitto.pid" && echo "Broker propio iniciado en 1884 (PID $(cat "$P/run/mosquitto.pid"))" \
    || { echo "ERROR: el broker no arrancó; ver $P/logs/mosquitto_salida.log"; tail -5 "$P/logs/mosquitto_salida.log"; exit 1; }
fi

if vivo "$P/run/nodered.pid"; then
  echo "Node-RED propio ya corriendo (PID $(cat "$P/run/nodered.pid"))"
else
  RIEGO_ENV_FILE="$ENVF" RIEGO_ENV=final PORT=1881 nohup node "$P/nodered/runtime/node_modules/node-red/red.js" \
    --userDir "$P/nodered/userdata" --settings "$P/nodered/userdata/settings.js" --port 1881 \
    >> "$P/logs/nodered.log" 2>&1 &
  echo $! > "$P/run/nodered.pid"
  for i in $(seq 1 60); do puerto 1881 && break; sleep 2; done
  puerto 1881 && echo "Node-RED propio iniciado en 1881 (PID $(cat "$P/run/nodered.pid"))" \
    || { echo "ERROR: Node-RED no abrió el puerto 1881; ver $P/logs/nodered.log"; tail -20 "$P/logs/nodered.log"; exit 1; }
fi

[ -f "$P/telegram/iniciar_bot.sh" ] && bash "$P/telegram/iniciar_bot.sh"   # Bot de Telegram (solo lectura)
