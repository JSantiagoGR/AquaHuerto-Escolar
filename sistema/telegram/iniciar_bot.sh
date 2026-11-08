#!/usr/bin/env bash
# Inicia el bot de Telegram (solo lectura) de Equipo 2 Proyecto. Solo procesos de este usuario.
# Si el bot se cae, se reinicia solo a los 30 s.   Uso: bash telegram/iniciar_bot.sh
set -uo pipefail
P="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$P/run" "$P/logs"
PID="$P/run/telegram.pid"

if [ ! -f "$P/configs/secrets/telegram.env" ]; then
  echo "Bot de Telegram no configurado (falta configs/secrets/telegram.env); no se inicia."
  exit 0
fi
if [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; then
  echo "Bot de Telegram ya corriendo (PID $(cat "$PID"))"
  exit 0
fi
setsid nohup bash -c "while true; do python3 -u '$P/telegram/bot_huerto.py'; echo \"[\$(date '+%F %T')] el bot terminó; reinicio en 30 s\"; sleep 30; done" \
  >> "$P/logs/telegram.log" 2>&1 < /dev/null &
echo $! > "$PID"
sleep 3
if kill -0 "$(cat "$PID")" 2>/dev/null; then
  echo "Bot de Telegram iniciado (PID $(cat "$PID")); registro en logs/telegram.log"
else
  echo "ERROR: el bot no arrancó"; tail -5 "$P/logs/telegram.log"; exit 1
fi
