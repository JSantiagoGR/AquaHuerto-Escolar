# MQTT — Topics y esquemas JSON (implementados en el firmware)

Topic base: `huerto/esp32` (configurable en `CONFIG_RIEGO_MQTT_BASE_TOPIC`).
Todos los mensajes son JSON UTF-8. Los números que no tienen dato se publican como `null`.
Ejemplos completos: [EJEMPLOS_MQTT.json](EJEMPLOS_MQTT.json).

## Resumen

| Topic | Dirección | QoS | Retain | Cuándo |
|---|---|---|---|---|
| `huerto/esp32/status` | ESP32 → | 1 | **sí** | Al conectar `{"online":true}`; LWT `{"online":false,"reason":"LWT"}` |
| `huerto/esp32/telemetry` | ESP32 → | 0 | no | Cada `telemetry_s` (10 s por defecto) |
| `huerto/esp32/state` | ESP32 → | 1 | **sí** | Al cambiar algo, cada 1 s durante un riego y cada 30 s |
| `huerto/esp32/config` | ESP32 → | 1 | **sí** | Al conectar, al cambiar un parámetro y con `GET_CONFIG` |
| `huerto/esp32/decision` | ESP32 → | 1 | **sí** | Cuando cambia la decisión del riego automático y al conectar |
| `huerto/esp32/event` | ESP32 → | 1 | no | Inicio/fin de cada riego y fin de cada evento automático |
| `huerto/esp32/alarm` | ESP32 → | 1 | no | Al activarse o resolverse una alarma |
| `huerto/esp32/ack` | ESP32 → | 1 | no | Respuesta a cada comando |
| `huerto/esp32/history` | ESP32 → | 1 | no | Respuesta a `GET_HISTORY` |
| `huerto/esp32/command` | → ESP32 | 1 | **NO** | Comandos del dashboard |

## Reglas de los comandos (`huerto/esp32/command`)

```json
{"id": "nr-0004", "cmd": "START_MANUAL", "liters": 1.0, "ts": 1791800000, "token": "opcional"}
```

| Campo | Obligatorio | Regla en el firmware |
|---|---|---|
| `id` | sí | Texto de 1 a 39 caracteres. Se guardan los últimos 24: un `id` repetido responde `DUPLICATE` y **no se ejecuta** |
| `cmd` | sí | Uno de la tabla de comandos (mayúsculas o minúsculas) |
| `ts` | no | Segundos Unix. Si el ESP32 tiene hora válida y la diferencia es > 60 s: `STALE` |
| `token` | solo si se configuró `CONFIG_RIEGO_CMD_TOKEN` | Comandos de accionamiento y `SET_*` sin token: `UNAUTHORIZED` |

- **Mensajes retenidos se rechazan** (`RETAINED`), excepto `STOP`. Así una orden START retenida en el broker no puede regar al reconectar.
- La sesión MQTT es limpia (`clean session`): el broker no entrega comandos viejos acumulados.
- **`STOP` siempre se ejecuta** aunque venga repetido o retenido, porque solo apaga. Apaga los GPIO antes de encolarse.
- Mensajes de más de 511 bytes o fragmentados se descartan.

### Comandos

| `cmd` | Campos | Efecto |
|---|---|---|
| `GET_STATUS` | — | Publica `state` (retenido), `telemetry` y `decision` |
| `GET_CONFIG` | — | Publica `config` |
| `GET_HISTORY` | — | Publica `history` (últimos 16 riegos) |
| `START_MANUAL` | `liters` (0.10 – `max_liters_event`), `force` (bool, opcional) | Riego manual por volumen |
| `STOP` | — | Detiene todo de inmediato |
| `ENABLE_AUTO` / `DISABLE_AUTO` | — | Riego automático por humedad |
| `SET_HUMIDITY_MIN` / `_TARGET` / `_MAX` | `value` (%VWC) | Un umbral; se valida `MIN < OBJ < MAX` (≥ 1 punto) |
| `SET_HUMIDITY_RANGE` | `min`, `target`, `max` | Los tres a la vez (evita estados intermedios inválidos) |
| `SET_LITERS_PER_CYCLE` | `value` (L) | 0.1 – 5, y ≤ `max_liters_event` |
| `SET_INFILT_WAIT` | `value` (min) | 1 – 120 |
| `SET_MAX_LITERS` | `event` y/o `daily` (L) | Evento ≤ 10, diario ≤ 50 (límites duros) |
| `SET_FLOW_CALIBRATION` | `pulses_per_liter` **o** `pulses` + `measured_ml` | Rechazado durante un riego |
| `SET_TANK_MIN_LEVEL` | `value` (%) | 5 – 90 |
| `SET_TANK_CALIBRATION` | `empty_cm`, `full_cm` | Ambos 0 = sin calibrar |
| `SET_SCHEDULE` | `window` (1/2), `enabled`, `start`, `end` ("HH:MM") | Horarios preferidos |
| `SET_CONFIG` | `key`, `value` | Cualquier parámetro remoto de `config.params` |
| `CLEAR_ALARM` | `alarm` (`"ALL"` o código) | Solo si la causa está resuelta |

**No existen por MQTT:** habilitar la potencia, cambiar el modo A/B, la simulación ni la restauración de fábrica. Esas acciones solo se hacen por la consola serial, con presencia física (ver [SEGURIDAD.md](SEGURIDAD.md)).

### `huerto/esp32/ack`

```json
{"id":"nr-0004","cmd":"START_MANUAL","status":"OK","message":"Riego manual de 1.00 L iniciado","state":"MANUAL_WATERING","ts":1791800001,"uptime_s":532}
```
`status`: `OK`, `REJECTED` (válido pero no permitido ahora), `INVALID` (formato o rango), `DUPLICATE`, `STALE`, `RETAINED`, `UNAUTHORIZED`.

## Publicaciones

### `telemetry`
| Campo | Tipo | Descripción |
|---|---|---|
| `soil.valid` | bool | Lectura del EC-5 utilizable |
| `soil.vwc_pct` | número | Humedad **volumétrica** estimada del suelo (%VWC), regresión de la Actividad 2.2 |
| `soil.mv` | entero | Mediana de 5 pulsos de excitación (mV) |
| `soil.in_cal_range` | bool | mV dentro del intervalo experimental 360–870 mV (±5 %) |
| `soil.status` | texto | `OK`, `OK_FUERA_DE_CALIBRACION`, `SIN_SENAL`, `FUERA_DE_RANGO`, `INESTABLE`, `IMPOSIBLE`, `ADC_ERROR`, `SIMULADO` |
| `soil.age_s` | entero | Segundos desde la última lectura |
| `tank.distance_cm` | número | Distancia sensor → superficie del agua |
| `tank.level_pct` | número/null | **null mientras el tinaco no esté calibrado** |
| `tank.calibrated` / `below_min` / `status` | | `OK`, `NO_CALIBRADO`, `SIN_ECO`, `INESTABLE`, `FUERA_DE_RANGO` |
| `env.temp_c`, `env.rh_pct` | número | DHT22: temperatura y humedad **relativa del aire** |
| `env.last_valid_ts` | número/null | Hora de la última lectura válida |
| `flow.lpm` | número | Caudal (durante riego: ventana de 1 s; fuera: promedio del intervalo) |
| `flow.session_l` | número | Litros del riego en curso |
| `flow.today_l`, `flow.total_l` | número | Litros calculados del día y acumulados |
| `flow.pulses`, `flow.pulses_per_liter` | | Pulsos totales y constante vigente |
| `simulation` | bool | `true` = valores simulados, salidas físicas inactivas |

### `state`
Campos: `state` (`INIT`, `IDLE`, `MONITORING`, `MANUAL_WATERING`, `AUTO_WATERING`, `INFILTRATION_WAIT`, `FAULT`), `phase` (`NONE`, `OPENING`, `PUMPING`, `CLOSING`), `mode` (`A`/`B`), `auto_enabled`, `power_outputs`, `simulation`, `pump`/`valve` (estado físico; en simulación, el lógico), `pump_cmd`/`valve_cmd` (lógico), `emergency_latch`, `watering{active,type,target_l,delivered_l,remaining_l,progress_pct,elapsed_s,flow_lpm}`, `event{active,emergency,cycles,liters,infiltration_remaining_s}`, `alarms[]`, `decision{code,text}`, `next_window`, `time_valid`, `local_time`, `wifi`, `mqtt`, `rssi`, `free_heap`.

### `decision`
`code`, `text`, `soil_vwc`, `hum_min`, `hum_target`, `next_window` ("HH:MM" o `SIN_HORARIOS`), `in_window`, `auto_enabled`, `state`.

Códigos: `AUTO_DISABLED`, `OUTPUTS_DISABLED`, `FAULT`, `SOIL_INVALID`, `TOO_WET`, `HUMIDITY_OK`, `CONFIRMING_DRY`, `AUTO_LOCKED`, `TANK_UNCALIBRATED`, `TANK_INVALID`, `TANK_LOW`, `DAILY_LIMIT`, `MIN_GAP`, `EMERGENCY_GAP`, `TIME_INVALID`, `OUTSIDE_WINDOW`, `MIDDAY`, `HOT`, `START_SCHEDULED`, `START_EMERGENCY`, `INFILTRATING`, `CONTINUE_CYCLE`, `TARGET_REACHED`, `MAX_CYCLES`, `MAX_EVENT_LITERS`, `WINDOW_ENDED`, `NO_RESPONSE`, `EMERGENCY_DONE`, `STOPPED`, `WATERING_FAILED`.

### `event`
- `WATERING_START`: `reason` (`MANUAL`, `SCHEDULED`, `EMERGENCY`), `target_l`, `vwc_before`, `cycle`.
- `WATERING_END`: `reason`, `result` (`TARGET`, `STOP_CMD`, `NO_FLOW`, `FLOW_HIGH`, `PUMP_TIMEOUT`, `DAILY_LIMIT`, `EVENT_LIMIT`, `TANK_LOW`, `SAFETY`), `target_l`, `delivered_l`, `pulses`, `duration_s`, `vwc_before`, `vwc_after`, `today_l`.
- `AUTO_EVENT_END`: `why` (código de decisión), `cycles`, `liters`, `vwc_before`, `vwc_after` (tras la infiltración), `duration_s`.

### `alarm`
`code`, `severity` (`INFO`, `WARNING`, `CRITICAL`), `active`, `latched`, `message`.

| Código | Severidad | Enclavada | Bloquea |
|---|---|---|---|
| `NO_FLOW` | CRITICAL | sí | todo (FAULT) |
| `FLOW_HIGH` | CRITICAL | sí | todo |
| `PUMP_TIMEOUT` | CRITICAL | sí | todo |
| `SAFETY_TRIP` | CRITICAL | sí | todo |
| `FLOW_WHEN_IDLE` | CRITICAL | sí | todo (posible contacto pegado) |
| `SOIL_NO_RESPONSE` | WARNING | sí | automático |
| `REBOOT_DURING_WATERING` | WARNING | sí | — |
| `CONFIG_RESET` | WARNING | sí | — |
| `SOIL_SENSOR` | WARNING | no | automático (por falta de dato) |
| `TANK_SENSOR` | WARNING | no | riego si el tinaco está calibrado |
| `TANK_LOW` | WARNING | no | riego |
| `ENV_SENSOR` | INFO | no | — |
| `TIME_INVALID` | INFO | no | riego por horario |
| `DAILY_LIMIT` | INFO | no | más riego ese día |
| `COMMS` | INFO | no | — |

### `history`
`entries[]` (más reciente primero, máx. 16): `ts`, `reason`, `result` (incluye `REBOOT`), `liters`, `duration_s`, `pulses`, `vwc_before`, `vwc_after`.

### `config`
`params` contiene **todos** los parámetros con su clave, por ejemplo `hum_min`, `hum_target`, `hum_max`, `hum_critical`, `liters_per_cycle`, `max_liters_event`, `max_liters_daily`, `emergency_liters`, `pump_max_s`, `no_flow_s`, `flow_max_lpm`, `valve_lead_ms`, `valve_lag_ms`, `idle_flow_pulses`, `infilt_min`, `min_event_gap_min`, `emergency_gap_min`, `max_cycles`, `dry_confirm`, `response_cycles`, `min_response_pp`, `pulses_per_liter`, `overrun_ml`, `soil_interval_s`, `ec5_slope`, `ec5_offset`, `ec5_mv_min`, `ec5_mv_max`, `ec5_cal_mv_lo`, `ec5_cal_mv_hi`, `tank_empty_cm`, `tank_full_cm`, `tank_min_pct`, `tank_interval_s`, `win1_en`, `win1_start`, `win1_end`, `win2_en`, `win2_start`, `win2_end`, `midday_start`, `midday_end`, `emergency_en`, `temp_postpone_c`, `hot_temp_c`, `dry_rh_pct`, `telemetry_s`, `tz`, `mode`, `power_enabled`, `auto_saved`. Los límites de cada uno están en [CONFIGURACION_HUMEDAD.md](CONFIGURACION_HUMEDAD.md) y en `main/configuration.c`.

## Estado de verificación
El código MQTT **compila**, pero **no se ha verificado conectado a un broker**: durante el desarrollo la PC estaba en otra red y `raspberrypi.local:1883` no respondía. Ver [PRUEBAS_REALIZADAS.md](PRUEBAS_REALIZADAS.md).
