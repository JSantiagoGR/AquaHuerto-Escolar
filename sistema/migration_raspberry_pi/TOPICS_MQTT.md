# Configuración MQTT

## Broker de casa

| | |
|---|---|
| Software | Mosquitto 2.1.2 |
| Dirección | `mqtt://IP_DE_LA_LAPTOP:1883` (IP actual de la laptop) · `127.0.0.1:1883` para Node-RED |
| Configuración | `mqtt/mosquitto_casa.conf` (proceso del usuario) — idéntica a `mqtt/conf.d/riego_casa.conf` (servicio) |
| Anónimos | **Prohibidos** (`allow_anonymous false`) — verificado: conexión rechazada |
| Usuarios | `esp32_casa_01`, `nodered_casa`, `simulador_casa`, `admin_casa` (contraseñas aleatorias en `configs/secrets/credenciales_casa.env`; en el broker solo el hash en `mqtt/passwd`) |
| ACL | `mqtt/acl.conf`: cada cliente solo su árbol; el simulador **no puede** escribir en `huerto/casa/esp32_01/#` (verificado) |
| Persistencia | Retenidos y sesiones en `mqtt/data_usuario/` |
| Firewall | Entrada 1883 solo subred local, perfil Privado. **No expuesto a internet** |
| Registro | `mqtt/log/broker_usuario.log` |

## Topics

Base por dispositivo, configurable en el ESP32 (NVS): `huerto/<entorno>/<dispositivo>/`

| Entorno | Base |
|---|---|
| Casa, ESP32 de pruebas | `huerto/casa/esp32_01/` |
| Casa, simulador | `huerto/casa/sim_01/` |
| Huerto (Raspberry Pi) | `huerto/final/esp32_principal/` |

Los topics de casa y del huerto **nunca se mezclan** (otro broker, otro árbol, otros usuarios). El ESP32 original nunca recibe comandos de pruebas.

| Subtopic | Dirección | QoS / retenido | Contenido |
|---|---|---|---|
| `status` | ESP32 → | 1 / sí (LWT) | `{"online":true\|false}` |
| `telemetry` | ESP32 → | 0 / no, cada 10 s | Suelo (%VWC, mV, estado), tinaco, ambiente (T, HR, VPD), flujo, modo, estado, cultivo |
| `state` | ESP32 → | 1 / sí | Máquina de estados, bomba/válvula, riego en curso, evento, alarmas, decisión |
| `config` | ESP32 → | 1 / sí | Todos los parámetros y `profile_version` |
| `decision` | ESP32 → | 1 / sí | Código y justificación de la decisión |
| `event` | ESP32 → | 1 / no | `WATERING_START/END`, `EVENT_END`, `IA_OBSERVATION`, `UNEXPLAINED_RISE` |
| `alarm` | ESP32 → | 1 / no | Alarmas activas/resueltas |
| `ia` | ESP32 → | 1 / sí | Estado del modelo, plan, trayectoria, coeficientes |
| `weather` | ESP32 → | 1 / sí | Resumen del pronóstico que usa el ESP32 |
| `diag` | ESP32 → | 1 / no | Wi-Fi, broker, memoria (sin contraseñas) |
| `telemetry_buffer` | ESP32 → | 1 / no | Muestras guardadas en RAM mientras no había MQTT |
| `ack` | ESP32 → | 1 / no | Respuesta a cada comando (`id`, `status`, `message`, versión) |
| `command` | → ESP32 | 1 / **no** | Comandos JSON |

## Comandos (JSON en `command`)

Todos llevan `id` único (1–39 caracteres) y se recomienda `ts` (Unix). Protecciones verificadas:
- `id` repetido → `DUPLICATE` (anillo de 32 ids).
- Mensaje con marca **retenido** → `RETAINED` (no se ejecuta). STOP sí se ejecuta siempre.
- `ts` con más de 60 s de diferencia → `STALE`.
- JSON inválido o campos faltantes → `INVALID`.

| Comando | Campos |
|---|---|
| `SET_MODE` | `mode`: `MANUAL` \| `AUTOMATICO` \| `IA` |
| `START_MANUAL` | `liters`, `force` (opcional) |
| `START_TO_TARGET` | — (riego por dosis hacia la humedad óptima) |
| `STOP` | — |
| `APPLY_CONFIG` / `APPLY_PROFILE` | `version`, `params` {parámetro: valor...}: se valida TODO junto; si algo falla no cambia nada |
| `CLEAR_ALARM` | `alarm` (o `ALL`) |
| `SET_BROKER` | `uri`, `user`, `pass` (vuelve al anterior si no conecta en 90 s) |
| `IA_RESET` | `confirm`: `BORRAR_MODELO` |
| `GET_STATUS`, `GET_CONFIG`, `GET_IA`, `GET_HISTORY`, `NET_DIAG`, `WEATHER_REFRESH` | — |
| `SIM_CONTROL` | Solo simulador: `action`, `value` |

## Reconexión y operación sin MQTT

- esp-mqtt reconecta solo (5 s); el ESP32 publica `status` retenido al conectar y deja LWT `{"online":false}`.
- Sin MQTT el ESP32 sigue regando/protegiendo con sus límites locales y guarda una muestra cada 10 min en RAM (hasta 24 h) que envía al reconectar (`telemetry_buffer`). No se escribe en NVS de forma continua.
- Verificado con el simulador: corte "sucio" → LWT `offline` → reconexión → `online`, ambos registrados en SQLite.

## Identificación única

Cada ESP32 usa `client_id = riego-<dispositivo>-<3 bytes de su MAC>` (dos placas nunca se desconectan entre sí).
