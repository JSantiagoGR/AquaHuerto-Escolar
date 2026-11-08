# Guía para construir el dashboard de Node-RED

> **Estado:** solo preparación. **No** se ha modificado el servidor Node-RED, **no** se importó ningún flow y **no** se desplegó nada.
> Esta guía y el flow de ejemplo ([node-red/flow_dashboard_riego.json](node-red/flow_dashboard_riego.json)) son para hacerlo después.
> Topics y JSON exactos: [MQTT_TOPICS.md](MQTT_TOPICS.md). Distribución visual: [DASHBOARD_LAYOUT.md](DASHBOARD_LAYOUT.md).

Contenido:
0. Antes de empezar (respaldo)
1. Entrar al servidor Node-RED
2. Dirección del servidor y cómo verificarla
3. Paquete de dashboard
4. Conexión MQTT
5. Topics a suscribir
6. Topics a publicar
7. Nodos que se agregan
8. Cómo conectarlos
9. Qué poner en cada campo
10. JSON que se envía
11. Indicadores
12. Botones y sliders
13. Guardar configuraciones
14. Gráficas
15. Historial
16. Alarmas
17. Probar sin activar la bomba
18. Conectar el ESP32 real
19. Habilitar el modo de instalación final
20. Opción rápida: importar el flow de ejemplo

---

## 0. Antes de empezar: respaldo
1. En Node-RED: **Menú (☰) → Exportar → Todos los flujos → Descargar**. Guarde el archivo `flows_respaldo_AAAA-MM-DD.json`.
2. No borre flujos existentes. Todo lo de esta guía va en una **pestaña nueva** llamada `Riego Huerto`.

## 1. Entrar al servidor Node-RED
1. La computadora debe estar en la **misma red** que el broker (en las prácticas: `RouterHuerto1`).
2. Abra un navegador y entre a `http://<IP_DEL_SERVIDOR>:1880` (puerto por defecto de Node-RED).
3. Si pide usuario y contraseña, use los del servidor (configurados en `settings.js` → `adminAuth`). No los guarde en este proyecto.

## 2. Dirección del servidor y cómo verificarla
En las prácticas el broker MQTT estaba en **raspberrypi.local:1883**. Es probable que Node-RED esté en la misma máquina, pero **verifíquelo**:

| Verificación | Cómo |
|---|---|
| IP del servidor | En la máquina del servidor: `ipconfig` (Windows) o `hostname -I` (Linux / Raspberry Pi) |
| Node-RED responde | Desde otra PC: `Test-NetConnection raspberrypi.local -Port 1880` → `TcpTestSucceeded : True` |
| Broker responde | `Test-NetConnection raspberrypi.local -Port 1883` |
| Node-RED corriendo | En el servidor: `node-red` en la terminal, o `sudo systemctl status nodered` en Raspberry Pi |

Si la IP cambia, conviene reservarla en el router (DHCP estático).

## 3. Paquete de dashboard
1. **Menú → Administrar paleta → pestaña Nodos**. Busque:
   - `@flowfuse/node-red-dashboard` → **Dashboard 2.0** (recomendado; nodos `ui-…` en la paleta, sección *dashboard 2*).
   - `node-red-dashboard` → dashboard clásico (nodos `ui_…`, ya sin mantenimiento).
2. Si no está Dashboard 2.0: pestaña **Instalar** → busque `@flowfuse/node-red-dashboard` → **Instalar**.
3. Esta guía y el flow de ejemplo usan **Dashboard 2.0**. Con el clásico los nombres de nodos cambian (`ui_gauge` en lugar de `ui-gauge`), pero la lógica y los topics son los mismos.
4. La página queda en `http://<IP>:1880/dashboard/riego`.

## 4. Conexión MQTT
Arrastre un nodo **mqtt in**, doble clic → lápiz junto a *Server* → **Add new mqtt-broker**:

| Pestaña / campo | Valor |
|---|---|
| Name | `Broker huerto` |
| Server | `raspberrypi.local` (o la IP verificada) |
| Port | `1883` |
| Connect automatically | ✔ |
| Protocol | MQTT V3.1.1 |
| Client ID | `nodered-huerto` (no repetirlo en otro cliente) |
| Keep Alive | `60` |
| Use clean session | ✔ (evita recibir comandos viejos acumulados) |
| Security | Usuario y contraseña del broker si los tiene. Si el broker no tiene autenticación, configúrela antes de usar el modo B (ver §19 y [CONFIGURACION_MQTT.md](CONFIGURACION_MQTT.md)) |
| Messages (Birth/Close/Will) | Vacíos |

## 5. Topics a suscribir (nodos *mqtt in*)
Todos con **Server** = `Broker huerto` y **Output** = `a parsed JSON object`.

| Nodo | Topic | QoS | Uso |
|---|---|---|---|
| `telemetry` | `huerto/esp32/telemetry` | 0 | Sensores, caudal y litros |
| `state` | `huerto/esp32/state` | 1 | Bomba, válvula, estado, progreso, alarmas activas |
| `status` | `huerto/esp32/status` | 1 | En línea / desconectado (LWT) |
| `config` | `huerto/esp32/config` | 1 | Valores guardados en el ESP32 (sliders) |
| `decision` | `huerto/esp32/decision` | 1 | Motivo de cada decisión y próximo horario |
| `event` | `huerto/esp32/event` | 1 | Inicio y fin de riegos (historial) |
| `alarm` | `huerto/esp32/alarm` | 1 | Avisos de alarma |
| `ack` | `huerto/esp32/ack` | 1 | Confirmación de cada comando |
| `history` | `huerto/esp32/history` | 1 | Historial guardado en el ESP32 (respuesta a `GET_HISTORY`) |

## 6. Topics a publicar (nodo *mqtt out*)
Un solo nodo **mqtt out**:

| Campo | Valor |
|---|---|
| Server | `Broker huerto` |
| Topic | `huerto/esp32/command` |
| QoS | `1` |
| Retain | **false** (obligatorio: el ESP32 rechaza comandos retenidos) |
| Name | `Comando al ESP32` |

Antes de ese nodo va un nodo **function** llamado `Añadir id y ts`, por el que pasan **todos** los comandos:

```javascript
const now = Date.now();
msg.payload = Object.assign({
  id: 'nr-' + now + '-' + Math.floor(Math.random() * 1000),
  ts: Math.floor(now / 1000)
}, msg.payload);
return msg;
```
- `id` único: el ESP32 descarta repetidos (`DUPLICATE`). Así un doble clic o una reconexión no riegan dos veces.
- `ts`: el ESP32 rechaza comandos con más de 60 s de diferencia (`STALE`). Requiere que el servidor tenga la hora correcta (NTP).
- Si configuró `CONFIG_RIEGO_CMD_TOKEN`, agregue `token: 'su_token'` dentro de `Object.assign`. No lo publique en capturas de pantalla.

## 7. Nodos que se agregan

| Sección | Nodos Dashboard 2.0 |
|---|---|
| Configuración | 1 `ui-base` (Huerto, `/dashboard`), 1 `ui-theme`, 1 `ui-page` (`Riego del huerto`, `/riego`), 7 `ui-group` (A–G) |
| A. Panel principal | 5 `ui-gauge`, 9 `ui-text` |
| B. Humedad del suelo | 3 `ui-slider`, 3 `change`, 1 `function`, 1 `ui-text` |
| C. Riego manual | 1 `ui-slider`, 1 `change`, 2 `ui-button`, 2 `function`, 1 `ui-text`, 1 `ui-gauge` |
| D. Riego automático | 1 `ui-switch`, 1 `function`, 5 `ui-text` |
| E. Gráficas | 6 `ui-chart` |
| F. Historial | 1 `function`, 1 `ui-table` |
| G. Configuración y alertas | 3 `ui-text`, 1 `ui-button`, 1 `function`, 1 `ui-notification`, 2 `function` |
| MQTT | 9 `mqtt in`, 1 `mqtt out`, 1 `inject` de arranque |

### Grupos (`ui-group`)
| Nombre | Página | Ancho (columnas de 12) |
|---|---|---|
| A. Panel principal | Riego del huerto | 12 |
| B. Configuración de humedad del suelo | Riego del huerto | 4 |
| C. Riego manual | Riego del huerto | 4 |
| D. Riego automático | Riego del huerto | 4 |
| E. Gráficas | Riego del huerto | 12 |
| F. Historial | Riego del huerto | 8 |
| G. Configuración y alertas | Riego del huerto | 4 |

## 8. Cómo conectarlos
```
[mqtt in telemetry] → [function Separar telemetría] ─┬→ gauges A (suelo, tinaco, temp, HR, caudal)
                                                     ├→ charts E
                                                     └→ textos A (litros hoy, estado EC-5, estado tinaco, origen)
[mqtt in state] → [function Separar estado] → textos A, progreso C, switch D (decisión, horario, evento), alarmas G
[mqtt in status] → [function Online/offline] → texto "ESP32"
[mqtt in config] → [function Separar configuración] → 3 sliders B, textos B/D/G
[slider MÍN] → [change topic=min] ┐
[slider OBJ] → [change topic=target] ├→ [function Rango de humedad] → [Añadir id y ts] → [mqtt out]
[slider MÁX] → [change topic=max] ┘
[slider Litros] → [change flow.liters]
[botón START] → [function START_MANUAL] → [Añadir id y ts] → [mqtt out]
[botón STOP]  → [function STOP] → [Añadir id y ts] → [mqtt out]
[switch Automático] → [function ENABLE/DISABLE_AUTO] → [Añadir id y ts] → [mqtt out]
[botón CLEAR] → [function CLEAR_ALARM] → [Añadir id y ts] → [mqtt out]
[mqtt in event] → [function Agregar al historial] → [ui-table]
[mqtt in ack] → [function Confirmación] → [ui-notification]
[mqtt in alarm] → [function Aviso de alarma] → [ui-notification]
[inject al iniciar] → [function Pedir estado y config] → [Añadir id y ts] → [mqtt out]
```

## 9. Qué poner en cada campo

### `function` "Separar telemetría" (9 salidas)
**Outputs: 9.** Código:
```javascript
const t = msg.payload;
const ts = Date.now();
function m(v, topic) { return (v === null || v === undefined) ? null : { payload: v, topic: topic, timestamp: ts }; }
return [
  m(t.soil && t.soil.valid ? t.soil.vwc_pct : null, 'Humedad suelo %VWC'),
  m(t.tank && t.tank.level_pct !== null ? t.tank.level_pct : null, 'Tinaco %'),
  m(t.env && t.env.valid ? t.env.temp_c : null, 'Temperatura C'),
  m(t.env && t.env.valid ? t.env.rh_pct : null, 'HR ambiente %'),
  m(t.flow ? t.flow.lpm : null, 'Caudal L/min'),
  m(t.flow ? t.flow.today_l : null, 'Litros hoy'),
  { payload: (t.soil ? t.soil.status : '-') + ' | ' + (t.soil ? t.soil.mv + ' mV' : '') },
  { payload: (t.tank ? t.tank.status : '-') + ' | ' + (t.tank && t.tank.distance_cm !== null ? t.tank.distance_cm + ' cm' : 'sin eco') },
  { payload: t.simulation ? 'SIMULACIÓN (salidas inactivas)' : 'Sensores reales' }
];
```
Salidas 1–6 a los gauges **y** a las gráficas; salidas 7–9 a textos.
Importante: `tank.level_pct` es `null` mientras el tinaco no esté calibrado. El gauge no se mueve y es correcto: **no se inventa un porcentaje**.

### `function` "Separar estado" (12 salidas)
Ver el código en el flow de ejemplo (`Separar estado`). Salidas: Bomba, Electroválvula, Estado del riego, Comunicación, Progreso (texto), Progreso (%), switch Automático, Decisión, Próximo horario, Evento, Alarmas, Modo.

### `ui-gauge`
| Gauge | Grupo | Tipo | Mín–Máx | Unidades | Segmentos (desde → color) |
|---|---|---|---|---|---|
| Humedad del suelo | A | Half gauge, Rounded | 0–60 | %VWC | 0 rojo `#c62828`, 25 ámbar `#f9a825`, 35 verde `#2e7d32`, 45 azul `#1565c0` |
| Nivel del tinaco | A | Half gauge | 0–100 | % | 0 rojo, 20 ámbar, 40 verde |
| Temperatura ambiente | A | Half gauge | -5–50 | °C | -5 azul, 15 verde, 30 ámbar, 35 rojo |
| Humedad relativa del aire | A | Half gauge | 0–100 | %HR | 0 ámbar, 30 verde, 80 azul |
| Caudal | A | Half gauge | 0–8 | L/min | 0 gris, 1 verde, 6 rojo |
| Progreso del riego | C | Half gauge | 0–100 | % | 0 azul, 100 verde |

Ajuste los segmentos del suelo a los umbrales que elija la escuela; no son recomendaciones agronómicas.

### `ui-text`
Campo **Label** con el nombre de la tabla de §7, **Format** `{{msg.payload}}` (en *Litros hoy*: `{{msg.payload}} L`), **Layout** `row-spread`.

## 10. JSON que se envía

| Acción del dashboard | `msg.payload` antes de "Añadir id y ts" |
|---|---|
| Cambiar humedad | `{ "cmd": "SET_HUMIDITY_RANGE", "min": 25, "target": 35, "max": 45 }` |
| START | `{ "cmd": "START_MANUAL", "liters": 1.0 }` |
| STOP | `{ "cmd": "STOP" }` |
| Automático ON/OFF | `{ "cmd": "ENABLE_AUTO" }` / `{ "cmd": "DISABLE_AUTO" }` |
| Borrar alarmas | `{ "cmd": "CLEAR_ALARM", "alarm": "ALL" }` |
| Al abrir | `{ "cmd": "GET_STATUS" }` y `{ "cmd": "GET_CONFIG" }` |
| Litros por ciclo | `{ "cmd": "SET_LITERS_PER_CYCLE", "value": 1.0 }` |
| Infiltración | `{ "cmd": "SET_INFILT_WAIT", "value": 15 }` |
| Horario | `{ "cmd": "SET_SCHEDULE", "window": 1, "enabled": true, "start": "06:00", "end": "09:00" }` |
| Temperatura límite | `{ "cmd": "SET_CONFIG", "key": "temp_postpone_c", "value": 35 }` |
| Emergencia | `{ "cmd": "SET_CONFIG", "key": "hum_critical", "value": 18 }` |

Todos los ejemplos: [EJEMPLOS_MQTT.json](EJEMPLOS_MQTT.json).

## 11. Cómo diseñar los indicadores
- **Bomba / Electroválvula:** `ui-text` con el texto ENCENDIDA/APAGADA. Para color, use un `ui-template` con `<v-chip :color="msg.payload==='ENCENDIDA'?'green':'grey'">{{msg.payload}}</v-chip>`.
- **Estado MQTT:** combine `status` (LWT: `online:false` = ESP32 desconectado) con `state.mqtt`. Si no llega `state` en más de 60 s, muestre "SIN DATOS" con un nodo `trigger` (enviar "SIN DATOS" tras 60 s, reiniciar con cada mensaje).
- **Decisión del automático:** texto `decision.code: decision.text`; es la explicación de **por qué** riega, pospone o bloquea.
- **Origen de datos:** si `simulation` es `true`, se ve "SIMULACIÓN". Así nadie confunde una prueba con datos reales.

## 12. Botones y sliders

### Sección B — CONFIGURACIÓN DE HUMEDAD DEL SUELO
Tres `ui-slider`:

| Label | Min | Max | Step | Passthru | Output |
|---|---|---|---|---|---|
| HUMEDAD MÍNIMA (%VWC) | 5 | 60 | 0.5 | **no** | Only on release |
| HUMEDAD RECOMENDADA / OBJETIVO (%VWC) | 5 | 65 | 0.5 | **no** | Only on release |
| HUMEDAD MÁXIMA (%VWC) | 5 | 70 | 0.5 | **no** | Only on release |

- Cada slider va a un nodo `change` que pone `msg.topic` = `min`, `target` o `max`.
- Los tres van a la function **Rango de humedad**, que comprueba `MÍN < OBJ < MÁX` y envía `SET_HUMIDITY_RANGE` con los tres valores. Si no se cumple, no envía nada y muestra "Revise: MÍNIMA < OBJETIVO < MÁXIMA".
- El ESP32 valida otra vez: mínimo 1 punto entre valores, límites duros 5–70 %VWC, y `hum_critical < hum_min`.
- **Mostrar el valor guardado:** cuando el ESP32 acepta, publica `config` (retenido) y la function *Separar configuración* reposiciona los sliders. El texto "Guardado en ESP32: mín / obj / máx" confirma lo que quedó **en el ESP32**, no lo que se movió en pantalla.
- La confirmación de recepción llega como notificación (`ack` con `status: OK` o el motivo del rechazo).

### Sección C — RIEGO MANUAL
| Nodo | Configuración |
|---|---|
| `ui-slider` Litros a regar | Min 0.1, Max 3, Step 0.1 (el ESP32 limita a `max_liters_event`) |
| `change` Guardar litros | `flow.liters` = `msg.payload` |
| `ui-button` START | Color verde `#2e7d32`; → function `START_MANUAL` |
| `ui-button` STOP | Color rojo `#c62828`; → function `STOP`. Siempre visible |
| Progreso | Texto `0.42 / 1 L (42 %) 9 s` + gauge 0–100 % |

Para evitar un riego accidental, puede agregar un diálogo de confirmación: Dashboard 2.0 no lo trae en `ui-button`; use un `ui-template` con un `v-dialog`, o dos botones ("ARMAR" y "CONFIRMAR START") con una ventana de 10 s.

### Sección D — RIEGO AUTOMÁTICO
- `ui-switch` **Riego automático** con **Decouple** activado (`decouple: true`): el switch solo cambia cuando el ESP32 confirma por `state.auto_enabled`. Si el ESP32 rechaza (por ejemplo, potencia deshabilitada), el switch vuelve solo.
- Textos: Decisión, Próximo horario, Evento (ciclos, litros, infiltración restante), Parámetros (L por ciclo, infiltración, ciclos máx.), Horarios.

## 13. Cómo guardar configuraciones
- La configuración **vive en el ESP32** (NVS) y sobrevive a reinicios. El dashboard solo la muestra y la cambia.
- Al conectar, el ESP32 publica `config` **retenido**: el dashboard siempre arranca con los valores reales.
- No guarde copias de los umbrales en Node-RED como fuente de verdad. Si quiere un respaldo, guarde el último `config` recibido en un archivo con un nodo `file` (`/home/<usuario>/riego/config_respaldo.json`, acción *overwrite*).

## 14. Gráficas (`ui-chart`)
| Gráfica | Origen | Eje Y | Ventana |
|---|---|---|---|
| Humedad del suelo (%VWC) | telemetry salida 1 | 0–60 | 24 h (`removeOlder` 1 día, 1000 puntos) |
| Nivel del tinaco (%) | salida 2 | 0–100 | 24 h |
| Temperatura (°C) | salida 3 | auto | 24 h |
| Humedad relativa del aire (%) | salida 4 | 0–100 | 24 h |
| Caudal (L/min) | salida 5 | 0–8 | 24 h |
| Litros del día | salida 6 | auto | 24 h |

Configuración común: *Type* Line, *X-axis* timestamp/time, *Series* `msg.topic`, *Action* append.
Con telemetría cada 10 s, 24 h son 8640 puntos por serie: para el navegador conviene limitar a 1000 puntos o subir `telemetry_s` a 60 (`SET_CONFIG telemetry_s 60`).

**Consumo diario histórico:** guarde `flow.today_l` del último mensaje antes de medianoche (nodo `inject` con *crontab* a las 23:59 que lee `flow.ultimo_today_l`) y grafíquelo como barras (`chartType: bar`).

## 15. Historial
Hay dos fuentes:
1. **Node-RED (eventos):** la function *Agregar al historial* guarda los últimos 50 riegos en `flow.historial` y los muestra en `ui-table`. Columnas: Fecha, Tipo, Resultado, Litros, Duración, Humedad antes, Humedad después.
2. **ESP32 (NVS):** `GET_HISTORY` devuelve los últimos 16 riegos guardados en el propio ESP32, incluidos los registros `REBOOT`.

Para que `flow.historial` sobreviva a reinicios de Node-RED, en `settings.js`:
```javascript
contextStorage: {
    default: { module: "localfilesystem" }
},
```
Reinicie Node-RED. Para un historial largo, use un nodo `file` que agregue cada evento como línea CSV en `/home/<usuario>/riego/historial.csv`, o una base de datos (SQLite / InfluxDB).

## 16. Alarmas
- `mqtt in alarm` → function *Aviso de alarma* → `ui-notification`, en rojo si es CRITICAL, ámbar si es WARNING y azul si es INFO.
- Lista de alarmas activas: `state.alarms` (texto en el grupo G).
- Botón **CLEAR_ALARM (ALL)**: el ESP32 solo borra lo que ya se resolvió. Las alarmas de condición (tinaco bajo, sensor sin dato) se borran solas.
- Falla de comunicación: el LWT `{"online":false}` en `status` indica que el ESP32 se desconectó del broker.
- Alarmas críticas que exigen revisar el equipo antes de borrar: `NO_FLOW`, `FLOW_HIGH`, `PUMP_TIMEOUT`, `SAFETY_TRIP` y `FLOW_WHEN_IDLE` (posible contacto pegado).

## 17. Probar sin activar la bomba
1. En el ESP32, por consola serial: `SIM ON`. Los sensores pasan a ser simulados y **las salidas físicas permanecen inactivas**, aunque la potencia esté habilitada.
2. Con la simulación activa, el dashboard muestra "SIMULACIÓN" y `power_outputs` sigue en lo que esté configurado.
3. Simule condiciones por consola: `SIM SUELO 20`, `SIM TINACO 15`, `SIM FLUJO 0`, `SIM HORA 07:00`, `SIM AMB 38 20`, `SIM VELOCIDAD 60` (1 s = 1 min).
4. Desde el dashboard: START 1 L → progreso, caudal y fin; STOP; automático ON → decisión, ciclo, infiltración y fin del evento.
5. Sin ESP32 se puede probar el dashboard publicando a mano los JSON de [EJEMPLOS_MQTT.json](EJEMPLOS_MQTT.json) con un nodo `inject` (JSON) → `mqtt out` al topic correspondiente (`telemetry`, `state`…). **Nunca publique en `command` con retain.**

## 18. Conectar el ESP32 real
1. El ESP32 debe estar en la misma red: `CONFIG_RIEGO_WIFI_SSID` y la contraseña en `sdkconfig.secrets` (ver [CONFIGURACION_MQTT.md](CONFIGURACION_MQTT.md)).
2. Al conectar, en la consola serial aparece `wifi: Conectado, IP ...` y `mqtt: Conectado al broker`.
3. En el dashboard, "ESP32 EN LÍNEA" y los sliders toman los valores guardados.
4. Envíe `GET_STATUS` (se envía solo al abrir el flow) y revise la notificación `GET_STATUS: OK`.

## 19. Habilitar el modo de instalación final (B)
El cambio de modo **no** se hace desde el dashboard; es intencional. Se hace por consola serial con la lista de [GUIA_INSTALACION_FINAL.md](GUIA_INSTALACION_FINAL.md):
`POWER ON CONFIRMAR` → calibrar tinaco → pruebas físicas → `MODO B CONFIRMAR` → `AUTO ON`.
En el dashboard se verá `Modo B`. Antes de usar el modo B en una red compartida: autenticación en el broker, ACL que solo permita a Node-RED publicar en `huerto/esp32/command` y, opcionalmente, `CONFIG_RIEGO_CMD_TOKEN`.

### Controles del riego inteligente (horario y ambiente)
Puede agregarlos en el grupo G (sliders/inputs que envían `SET_CONFIG` o `SET_SCHEDULE`):

| Control | Comando | Rango |
|---|---|---|
| Horario 1 inicio / fin / habilitado | `SET_SCHEDULE` window 1 | HH:MM |
| Horario 2 inicio / fin / habilitado | `SET_SCHEDULE` window 2 | HH:MM |
| Inicio / fin de bloqueo de mediodía | `SET_CONFIG midday_start` / `midday_end` | HH:MM |
| Temperatura para posponer | `SET_CONFIG temp_postpone_c` | 20–50 °C |
| Temperatura y HR que aceleran la lectura | `hot_temp_c`, `dry_rh_pct` | 15–50 °C / 5–80 % |
| Emergencias habilitadas | `SET_CONFIG emergency_en` true/false | — |
| Humedad crítica | `SET_CONFIG hum_critical` | < humedad mínima |
| Litros de emergencia | `SET_CONFIG emergency_liters` | 0.1–2 L |
| Espera entre emergencias | `SET_CONFIG emergency_gap_min` | 30–1440 min |
| Intervalo mínimo entre eventos | `SET_CONFIG min_event_gap_min` | 0–1440 min |
| Máximo de ciclos | `SET_CONFIG max_cycles` | 1–6 |
| Máximo diario | `SET_MAX_LITERS daily` | 0.5–50 L |

Muestre siempre `decision.text` y `next_window`: allí el ESP32 explica por qué pospone (`OUTSIDE_WINDOW`, `MIDDAY`, `HOT`, `TIME_INVALID`) o bloquea (`TANK_LOW`, `TANK_UNCALIBRATED`, `SOIL_INVALID`, `AUTO_LOCKED`).

## 20. Opción rápida: importar el flow de ejemplo
1. **Menú → Importar → seleccionar archivo** → `node-red/flow_dashboard_riego.json` → *Importar a: nueva pestaña*.
2. Doble clic en cualquier `mqtt in` → revise el **Server** `Broker huerto` (IP, puerto, credenciales).
3. **Deploy** solo cuando el broker y la red estén verificados.
4. Abra `http://<IP>:1880/dashboard/riego`.
5. El flow es un punto de partida generado con `tools/generar_flow_node_red.py`. Si cambia el script, regenérelo; no edite el JSON a mano.
