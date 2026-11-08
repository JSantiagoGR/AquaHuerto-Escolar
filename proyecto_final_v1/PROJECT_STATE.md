# Estado del proyecto (2026-10-11)

## Resumen
| Área | Estado |
|---|---|
| Firmware (software) | **Completo**: 21 módulos, compila sin warnings (ESP-IDF 6.0.2, `-Wall -Wextra -Werror`) |
| Compilación de la placa | **OK**: 1 013 188 bytes, 34 % libre en la partición de la app |
| Flasheo en la placa | **No realizado**: el ESP32 no estaba conectado durante el desarrollo |
| Lógica de riego | **Probada en software**: SELFTEST 33/33 PASS dentro del firmware emulado (QEMU) |
| Integración del firmware | **Probada en el emulador QEMU** (consola, control, NVS, simulación, comandos JSON, corte de energía). Ver [PRUEBAS_REALIZADAS.md](PRUEBAS_REALIZADAS.md) |
| Wi-Fi / MQTT | Implementado y compilado; **no verificado con broker** (otra red; QEMU no emula Wi-Fi) |
| Sensores | Drivers reutilizados de las pruebas físicas 01–03; **EC-5 pendiente de conexión física** en este proyecto |
| Etapa de potencia de la bomba | **Pendiente de certificar** (relevador SRD no apto para 6 A inductivos) |
| Dashboard Node-RED | **Solo documentado** (guía, layout, ejemplos, flow de ejemplo); nada importado ni desplegado |
| Modo actual | **A (pruebas)**, potencia deshabilitada por defecto, automático apagado al encender |

## Lo que ya se probó físicamente (Pruebas 01–03, firmware anterior)
- ESP32-D0WD-V3 rev 3.1, COM8, ESP-IDF 6.0.2, flasheo a 115200 baudios.
- GPIO26/27 activo en BAJO con el módulo SRD; secuencia válvula → 300 ms → bomba → … → bomba OFF → 300 ms → válvula OFF.
- Riego de 1 L: 450 pulsos objetivo, 19.7 s, 455 pulsos al cerrar (~1011 mL **calculados**), caudal de 3.5–4.5 L/min tras ~4 s de cebado.
- PING))) leyendo 94.9 cm; DHT22 leyendo 21.5 °C / 53.7 %HR.

Ninguno de esos litros fue medido con recipiente graduado.

## Valores configurados de ejemplo (no agronómicos)
Humedad mínima 25 / objetivo 35 / máxima 45 / crítica 18 %VWC. 1 L por ciclo, 15 min de infiltración, 3 ciclos, 3 L por evento, 10 L por día. Horarios 06:00–09:00 y 18:00–20:00, mediodía bloqueado de 11:00 a 16:00.

## Próximos pasos
1. Conectar el ESP32 → `idf.py -p COM8 -b 115200 flash` → `python tools\run_selftest.py COM8`.
2. Conectar y verificar el EC-5 (GPIO25/34 + 1 MΩ).
3. Etapa de potencia, fusibles y diodos ([PENDIENTES_HARDWARE.md](PENDIENTES_HARDWARE.md)).
4. Calibrar tinaco y caudalímetro.
5. Verificar Wi-Fi y MQTT en `RouterHuerto1`.
6. Construir el dashboard con [GUIA_DASHBOARD_NODE_RED.md](GUIA_DASHBOARD_NODE_RED.md).
7. Pruebas físicas con agua (con autorización) → modo B ([GUIA_INSTALACION_FINAL.md](GUIA_INSTALACION_FINAL.md)).
