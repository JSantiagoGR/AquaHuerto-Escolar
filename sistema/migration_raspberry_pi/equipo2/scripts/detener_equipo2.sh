#!/usr/bin/env bash
# Detiene SOLO los procesos de Equipo 2 Proyecto (los PID guardados en run/).
# Antes de detener verifica que el proceso pertenezca a esta carpeta. Node-RED
# renombra su proceso a "node-red", así que se reconoce por su línea de comandos
# o por su entorno (RIEGO_ENV_FILE apunta a esta carpeta).
set -uo pipefail
P="$(cd "$(dirname "$0")/.." && pwd)"
es_nuestro() {
  grep -qaF "$P" "/proc/$1/cmdline" "/proc/$1/environ" 2>/dev/null
}
for svc in nodered mosquitto; do
  f="$P/run/$svc.pid"
  if [ -f "$f" ]; then
    pid=$(cat "$f")
    if kill -0 "$pid" 2>/dev/null && es_nuestro "$pid"; then
      kill "$pid" && echo "$svc detenido (PID $pid)"
      for i in $(seq 1 15); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    else
      echo "$svc: no estaba corriendo (o el PID no es de esta carpeta)"
    fi
    rm -f "$f"
  else
    echo "$svc: sin PID registrado"
  fi
done
