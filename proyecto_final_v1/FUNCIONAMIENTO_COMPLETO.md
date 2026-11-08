# Funcionamiento completo

## 1. Arranque
1. Bomba y válvula al nivel inactivo (primera instrucción).
2. Verificación de pines, NVS (configuración y contadores con CRC).
3. Si el arranque anterior se cortó durante un riego: **no se reanuda**, se registra en el historial y se activa `REBOOT_DURING_WATERING`.
4. Sensores (núcleo 1), supervisor de seguridad, tarea de control, consola.
5. Wi-Fi → SNTP → MQTT (opcional: sin red todo sigue funcionando).
6. **Modo A:** automático deshabilitado siempre. **Modo B:** se restaura el automático guardado, pero no se riega antes de `min_event_gap_min`.
7. Por defecto `power_enabled = 0`: aunque se pida riego, los GPIO de potencia no se activan.

## 2. Riego manual por volumen
`START_MANUAL` (MQTT) o `START <litros> [FORCE]` (consola).

**Validaciones, en este orden:**
1. Volumen entre 0.10 L y `max_liters_event` (tope 10 L).
2. Sin otro riego en curso; sin evento automático en espera de infiltración (conflicto → STOP primero).
3. Sin falla (FAULT).
4. Potencia habilitada (o simulación).
5. Cabe en lo que queda del máximo diario.
6. Tinaco calibrado: lectura válida y ≥ `tank_min_pct`. Sin calibrar: en modo A se permite con advertencia; en modo B se rechaza.
7. Suelo en o sobre `hum_max`: rechazado salvo `force`.

**Secuencia** (probada físicamente en las Pruebas 01–03):
1. Abre la electroválvula.
2. Espera 300 ms (`valve_lead_ms`).
3. Enciende la bomba.
4. Cuenta pulsos (PCNT). Volumen = pulsos × 1000 / `pulses_per_liter`.
5. Al llegar a `objetivo − overrun_ml`: apaga la bomba.
6. Espera 300 ms (`valve_lag_ms`) y cierra la electroválvula.
7. Publica `WATERING_END` con litros calculados, pulsos, duración y humedad antes/después, y guarda el historial.

**Cortes durante el bombeo:**

| Condición | Resultado |
|---|---|
| Sin pulsos `no_flow_s` | `NO_FLOW` (FAULT) |
| Caudal > `flow_max_lpm` en 3 s | `FLOW_HIGH` (FAULT) |
| Bomba > `pump_max_s` | `PUMP_TIMEOUT` (FAULT) |
| Se alcanza el máximo diario | `DAILY_LIMIT` |
| Se alcanza el máximo por evento | `EVENT_LIMIT` |
| Tinaco bajo `tank_min_pct` − 2 % | `TANK_LOW` |

`STOP` apaga todo de inmediato, sin esperas.

## 3. Riego automático por humedad
Requiere `ENABLE_AUTO` (o modo B con automático guardado). Se evalúa con cada lectura nueva del EC-5 y al menos una vez por minuto. **Decisión, en este orden** (cada una se publica en `decision`):

| # | Condición | Decisión |
|---|---|---|
| 1 | Potencia deshabilitada | `OUTPUTS_DISABLED` |
| 2 | EC-5 inválido | `SOIL_INVALID` (no riega) |
| 3 | Humedad ≥ máxima | `TOO_WET` |
| 4 | Humedad ≥ mínima | `HUMIDITY_OK` |
| 5 | Menos de `dry_confirm` lecturas seguidas bajo la mínima | `CONFIRMING_DRY` |
| 6 | `SOIL_NO_RESPONSE` activa | `AUTO_LOCKED` |
| 7 | Tinaco sin calibrar / sin dato / bajo el mínimo | `TANK_UNCALIBRATED` / `TANK_INVALID` / `TANK_LOW` |
| 8 | Máximo diario alcanzado | `DAILY_LIMIT` |
| 9 | No pasó `min_event_gap_min` desde el último riego | `MIN_GAP` |
| 10 | **Humedad < crítica** y emergencias habilitadas y pasó `emergency_gap_min` | **`START_EMERGENCY`**: `emergency_liters`, un solo ciclo, en cualquier horario y aun sin hora |
| 11 | Hora no válida | `TIME_INVALID` |
| 12 | Dentro del bloqueo de mediodía | `MIDDAY` |
| 13 | Fuera de los horarios | `OUTSIDE_WINDOW` (+ próximo horario) |
| 14 | Temperatura > `temp_postpone_c` | `HOT` |
| 15 | Todo correcto | **`START_SCHEDULED`**: `liters_per_cycle` |

Si la emergencia estaba bloqueada por su intervalo, la decisión publicada es `EMERGENCY_GAP`.

**Ciclo de un evento:**
1. Riego del ciclo (misma secuencia y protecciones que el manual).
2. `INFILTRATION_WAIT` durante `infilt_min`, con todo apagado.
3. Lectura **nueva** del EC-5.
4. Evaluación:

| Condición | Resultado |
|---|---|
| EC-5 inválido | Fin (`SOIL_INVALID`) |
| Humedad ≥ objetivo | Fin (`TARGET_REACHED`) |
| Emergencia | Fin tras un ciclo (`EMERGENCY_DONE`) |
| Tras `response_cycles` ciclos la humedad subió menos de `min_response_pp` | `SOIL_NO_RESPONSE`, bloquea el automático (`NO_RESPONSE`) |
| `max_cycles` alcanzado | Fin (`MAX_CYCLES`) |
| Se agotan los litros del evento o del día | Fin (`MAX_EVENT_LITERS` / `DAILY_LIMIT`) |
| Tinaco no apto | Fin |
| Terminó el horario o empezó el mediodía | Fin (`WINDOW_ENDED`) |
| Temperatura alta | Fin (`HOT`) |
| Si no, otro ciclo | `CONTINUE_CYCLE` |

5. Fin del evento: `AUTO_EVENT_END` con ciclos, litros y humedad antes y después de la infiltración. Corre de nuevo el intervalo mínimo.

**No riega indefinidamente:** por el máximo de ciclos, los litros por evento y por día, el tiempo de bomba y la respuesta exigida al suelo.

## 4. Horarios y ambiente (riego inteligente)
| Parámetro | Defecto | Uso |
|---|---|---|
| `win1_*` | 06:00–09:00, ON | Horario preferido 1 |
| `win2_*` | 18:00–20:00, ON | Horario preferido 2 (opcional) |
| `midday_*` | 11:00–16:00 | Nunca riego rutinario, aunque un horario lo cubra |
| `temp_postpone_c` | 35 °C | Pospone el riego rutinario |
| `hot_temp_c` / `dry_rh_pct` | 30 °C / 30 % | Acortan a la mitad el intervalo de lectura del EC-5 (mín. 60 s) |
| `tz` | `CST6` | Hora local de Chihuahua (UTC−6) |

La temperatura y la HR del aire **no cambian** la humedad objetivo: solo deciden cuándo medir más seguido y cuándo posponer.

## 5. Nivel del tinaco
- Distancia = eco × velocidad del sonido (corregida con la temperatura del DHT22) / 2. Mediana de 5 ecos; inválida si la dispersión es > 5 cm o hay menos de 3 ecos.
- **Sin calibrar** (`tank_empty_cm`/`tank_full_cm` = 0): se publica la distancia y `level_pct = null`; el automático no riega (`TANK_UNCALIBRATED`).
- Calibrado: % = (vacío − distancia) / (vacío − lleno) × 100. Alarma `TANK_LOW` con 3 % de histéresis.

## 6. Contadores
- Litros del día: se reinician a medianoche local. Sin hora válida, cada 24 h de funcionamiento. Al pasar de "sin hora" a "con hora" no se pierde lo contado.
- Litros totales: acumulados en NVS.
- Historial: últimos 16 riegos en NVS (incluye reinicios a mitad de riego).

## 7. Alarmas
Ver la tabla en [MQTT_TOPICS.md](MQTT_TOPICS.md#alarm). Las **enclavadas** requieren `CLEAR_ALARM`, que solo se acepta si la causa está resuelta. Las **de condición** se activan y desactivan solas.

## 8. Modos y simulación
- **A (pruebas):** activo por defecto. **B (instalación):** ver [GUIA_INSTALACION_FINAL.md](GUIA_INSTALACION_FINAL.md).
- **Simulación (`SIM ON`):** los sensores, el flujo y la hora son simulados, y las salidas físicas quedan **forzadas a inactivas**. Con `SIM VELOCIDAD n` el tiempo corre n veces más rápido; útil para ver infiltraciones, pero exagera el sobrepaso de volumen, porque se suman muchos pulsos por ciclo de control.
