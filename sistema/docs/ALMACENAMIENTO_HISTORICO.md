# Almacenamiento histórico

## Tres niveles

| Nivel | Dónde | Qué |
|---|---|---|
| **Historial completo en la computadora** | SQLite `database/riego_casa.db` (WAL) | Todo, por años; nada se borra automáticamente |
| **Modelo compacto en el ESP32** | NVS (`ia`, ~0.6 KB) | Coeficientes y estadísticas de la IA; contadores; últimos 16 riegos |
| **Búfer limitado sin conexión** | RAM del ESP32 | 144 muestras (una cada 10 min = 24 h) que se envían al reconectar (`source='buffer'`) |

No se escriben muestras continuamente en NVS: solo al iniciar/terminar riegos, al cambiar de día, al aprender un riego y cada 6 h de secado aprendido.

## Tablas (esquema `database/schema.sql`)

`readings` (fecha, humedad, mV, estado del sensor, T, HR, VPD, tinaco, caudal, litros día/total, modo, estado, cultivo, etapa, versión de datos, simulado, origen), `irrigation_events` (ID de evento, inicio/fin, humedad inicial, meta, volumen programado, pulsos, p/L, litros calculados, caudal, humedad tras infiltración, predicción IA, error, motivo, resultado, seguridad), `event_ends`, `decisions`, `weather_fetches`, `forecast_hourly`, `forecast_daily`, `rain_events` (con causa confirmada), `crops`, `plantings`, `stage_changes`, `config_changes` (txn, versión, estado del ACK), `crop_changes`, `ia_snapshots` (versiones del modelo), `ia_observations`, `predictions`, `alerts`, `connectivity`, `data_versions`, `soil_calibration`, `app_settings`, `schema_meta`.

## Control de duplicados

`UNIQUE` en las claves naturales (`device, ts, boot, seq` en lecturas; `event_id`; `ts_fetch, origin`...) + `INSERT OR IGNORE`: reenvíos MQTT o del búfer no duplican.

## Datos simulados y versiones

- Cada fila lleva `simulated` (1 = simulador). Las gráficas y tablas lo marcan "[sim]".
- `data_version` identifica la calibración/suelo vigente: al cambiarla, los análisis pueden separar datos incompatibles.

## Respaldo, recuperación y exportación

- **Respaldo**: `VACUUM INTO` (copia consistente en caliente) diario a las 03:00 y con RESPALDAR AHORA → `backups/db/riego_<fecha>.db`; flujos y contexto → `backups/nodered/`. Los respaldos no se borran solos. Verificado: `riego_20261011_175436.db`.
- **Recuperación**: detener Node-RED, copiar el respaldo como `database/riego_casa.db`, iniciar (en la Pi: `restaurar_pi.sh`, que primero renombra la base actual).
- **Exportación CSV**: `/riego/export.csv?tipo=lecturas|riegos|alertas|predicciones|lluvia&desde=AAAA-MM-DD&hasta=AAAA-MM-DD&device=...` (UTF-8 con BOM para Excel). Botones en Historial.
- **Errores de almacenamiento**: cualquier error de SQLite genera la alerta "Problema de almacenamiento" (verificado con un error real corregido durante las pruebas).

## Capacidad

Una lectura cada 10 s ≈ 8 640 filas/día ≈ 3 millones/año ≈ 400–600 MB/año. Para años de datos conviene subir `telemetry_s` (por ejemplo 60 s) en el entorno final; el disco es el único límite.
