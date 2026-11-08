# Equipo 2 Proyecto — instancia propia en la Raspberry Pi

Migración del proyecto que funciona en la laptop (mismo flujo, dashboard, base SQLite, cama, suelo y perfiles), sin reconstruirlo.

| | Equipo 2 Proyecto | Ya existente (NO se toca) |
|---|---|---|
| Node-RED | **1881**, `~/equipo2_proyecto/nodered` | 1880 (Equipos 1–6) |
| Dashboard | **http://IP:1881/dashboard** (Dashboard 2.0) | http://IP:1880/ui |
| Broker MQTT | **1884**, propio, usuarios + ACL | 1883 (GreenBroker) |
| Topics | `huerto/final/esp32_principal/...` | `equipo1/…` a `equipo6/…`, `huerto1/…`, `clima/…` |
| Base | `database/riego_final.db` | — |

## Instalación (sin sudo)

```bash
cd ~/equipo2_proyecto
bash scripts/instalar_equipo2.sh --autoarranque
```

No instala paquetes del sistema, no modifica `/etc`, no reinicia servicios. Con `--autoarranque` agrega una sola línea `@reboot` al crontab del usuario.

## Uso diario

| Acción | Comando |
|---|---|
| Iniciar | `bash scripts/iniciar_equipo2.sh` |
| Detener | `bash scripts/detener_equipo2.sh` |
| Estado (incluye 1880/1883) | `bash scripts/estado_equipo2.sh` |
| Respaldo | `bash scripts/respaldar_equipo2.sh` |
| Desinstalar | `bash scripts/desinstalar_equipo2.sh` (conserva la carpeta) |

## Acceso

- **Dashboard:** abierto sin contraseña dentro de la red (`DASHBOARD_PUBLIC=1` en el archivo de credenciales); cualquiera puede usar todos los controles, incluido el modo manual. Para volver a pedir usuario y contraseña (`DASHBOARD_USER` / `DASHBOARD_PASS`), quitar esa línea y reiniciar con los scripts.
- **Editor de Node-RED:** `NODERED_ADMIN_USER` / `NODERED_ADMIN_PASS` (solo el equipo; con la contraseña del dashboard no se puede editar la programación).
- Solo dentro de la red `RouterHuerto1`; no se expone a internet.
