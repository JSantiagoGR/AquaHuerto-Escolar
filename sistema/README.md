# Riego inteligente — Pruebas en casa (ESP32 + MQTT + Node-RED + Dashboard 2.0 + SQLite + Open-Meteo + IA)

Proyecto **independiente** para probar en casa el sistema completo de riego y migrarlo después
a la Raspberry Pi del huerto **sin reconstruir nada**. Una sola base de código de firmware
sirve para casa y huerto: solo cambia la configuración (red, broker, topic, perfil).

> Los proyectos anteriores (`Proyecto_Final_v1`, `Practica4_MQTT`, Pruebas 01–03, EPANET)
> **no se modificaron**: este proyecto solo los usó como base (copia).

## Qué hay y dónde

| Carpeta | Contenido |
|---|---|
| `firmware/` | Firmware ESP-IDF 6.0.2 (archivo principal `firmware/main/main.c`) |
| `nodered/` | Node-RED 5.0.8 **local y aislado** (`runtime/`) y su directorio de usuario (`userdata/`) |
| `dashboard/` | Generador del flujo + 14 funciones (`funciones/*.js`) + 10 páginas Vue (`plantillas/*.vue`) |
| `mqtt/` | Configuración de Mosquitto, ACL y archivo de usuarios (contraseñas cifradas) |
| `database/` | Esquema SQLite, catálogo de 10 cultivos con fuentes, base `riego_casa.db` |
| `simulation/` | Simulador `sim_01` (misma lógica en C del firmware vía DLL) |
| `tests/` | Pruebas de lógica en PC, integración y resultados |
| `configs/` | Scripts de administrador, Wi-Fi del ESP32 y **secretos locales** (`configs/secrets/`, no se exporta) |
| `scripts/` | `iniciar_todo.ps1`, `detener_todo.ps1`, `empaquetar_para_pi.ps1` |
| `migration_raspberry_pi/` | Todo lo necesario para instalarlo en la Raspberry Pi |
| `backups/` | Respaldo de la flash original de la ESP32, respaldos de SQLite y flujos |
| `docs/` | Documentación completa (empiece por [docs/ESTADO_FINAL.md](docs/ESTADO_FINAL.md)) |

## Inicio rápido

```bash
powershell -ExecutionPolicy Bypass -File C:\ESP32_Riego_Automatico\Pruebas_Casa_ESP32_v1\scripts\iniciar_todo.ps1 -Simulador -Abrir
```

- Dashboard: <http://localhost:1880/dashboard> (en esta PC no pide contraseña; desde el celular sí).
- Editor de Node-RED: <http://localhost:1880> (usuario y contraseña en `configs/secrets/credenciales_casa.env`).
- Detener: `scripts\detener_todo.ps1`.

## Documentación

| | |
|---|---|
| [ESTADO_FINAL](docs/ESTADO_FINAL.md) | Resumen verificable de lo que funciona y lo que falta |
| [INSTALACION_WINDOWS](docs/INSTALACION_WINDOWS.md) | Qué se instaló, versiones y comandos |
| [CONEXION_ESP32_USB_C](docs/CONEXION_ESP32_USB_C.md) | Detección de la segunda ESP32 y flasheo |
| [CONFIGURACION_WIFI](docs/CONFIGURACION_WIFI.md) / [CONFIGURACION_MQTT](docs/CONFIGURACION_MQTT.md) | Redes, broker, topics |
| [INSTALACION_NODE_RED](docs/INSTALACION_NODE_RED.md) / [DASHBOARD_COMPLETO](docs/DASHBOARD_COMPLETO.md) | Servidor y dashboard |
| [GUIA_DE_USO](docs/GUIA_DE_USO.md) | Uso diario del dashboard |
| [FIRMWARE_ESP32](docs/FIRMWARE_ESP32.md) / [PINOUT_VERIFICADO](docs/PINOUT_VERIFICADO.md) / [CALIBRACIONES](docs/CALIBRACIONES.md) | Firmware y hardware |
| [CULTIVOS](docs/CULTIVOS.md) / [CULTIVOS_PERSONALIZADOS](docs/CULTIVOS_PERSONALIZADOS.md) / [ETAPAS_DE_CRECIMIENTO](docs/ETAPAS_DE_CRECIMIENTO.md) | Perfiles agronómicos |
| [MODELO_PREDICTIVO_IA](docs/MODELO_PREDICTIVO_IA.md) / [OPEN_METEO](docs/OPEN_METEO.md) / [ALMACENAMIENTO_HISTORICO](docs/ALMACENAMIENTO_HISTORICO.md) | IA, clima y datos |
| [SEGURIDAD](docs/SEGURIDAD.md) / [PRUEBAS](docs/PRUEBAS.md) | Protecciones y resultados de pruebas |
| [MIGRACION_RASPBERRY_PI](docs/MIGRACION_RASPBERRY_PI.md) | Migración al huerto |
| [COMO_INICIAR_TODO](docs/COMO_INICIAR_TODO.md) / [COMO_DETENER_TODO](docs/COMO_DETENER_TODO.md) | Operación |
