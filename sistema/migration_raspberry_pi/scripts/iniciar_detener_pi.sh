#!/usr/bin/env bash
# Control del servicio en la Raspberry Pi.  Uso: bash iniciar_detener_pi.sh iniciar|detener|estado|logs
case "${1:-estado}" in
  iniciar) sudo systemctl start mosquitto riego-nodered ;;
  detener) sudo systemctl stop riego-nodered ;;      # El broker se deja activo (lo usa Equipo 2)
  estado)  systemctl --no-pager status mosquitto riego-nodered | head -30 ;;
  logs)    journalctl -u riego-nodered -n 100 --no-pager ;;
  *) echo "Uso: $0 iniciar|detener|estado|logs" ;;
esac
