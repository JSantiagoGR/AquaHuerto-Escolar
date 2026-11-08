#!/usr/bin/env bash
# Detiene el bot de Telegram de Equipo 2 Proyecto (y su ciclo de reinicio).
P="$(cd "$(dirname "$0")/.." && pwd)"
PID="$P/run/telegram.pid"
if [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; then
  kill -- "-$(cat "$PID")" 2>/dev/null || kill "$(cat "$PID")"
  echo "Bot de Telegram detenido"
else
  echo "El bot de Telegram no estaba corriendo"
fi
rm -f "$PID"
