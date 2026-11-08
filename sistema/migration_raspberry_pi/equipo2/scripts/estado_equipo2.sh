#!/usr/bin/env bash
# Estado de Equipo 2 Proyecto y verificación de que lo existente sigue igual.
P="$(cd "$(dirname "$0")/.." && pwd)"
puerto() { ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1\$" && echo "escuchando" || echo "CERRADO"; }
echo "Equipo 2 Proyecto:"
echo "  Node-RED propio 1881: $(puerto 1881)   PID $(cat "$P/run/nodered.pid" 2>/dev/null || echo -)"
echo "  Broker propio   1884: $(puerto 1884)   PID $(cat "$P/run/mosquitto.pid" 2>/dev/null || echo -)"
echo "Servicios existentes (no se tocan):"
echo "  Node-RED de los equipos 1880: $(puerto 1880)"
echo "  Broker del sistema      1883: $(puerto 1883)"
echo "Base: $(du -h "$P/database/riego_final.db" 2>/dev/null | cut -f1)  ·  Último registro de Node-RED:"
tail -3 "$P/logs/nodered.log" 2>/dev/null
