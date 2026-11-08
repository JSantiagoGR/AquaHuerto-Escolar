-- =====================================================================
-- Base de datos histórica del riego inteligente (SQLite 3)
-- Archivo: database/riego_casa.db (casa) | riego_final.db (Raspberry Pi)
-- Nada se borra automáticamente: el historial se conserva por años.
-- Cada fila guarda 'simulated' (1 = dato simulado) y 'data_version'
-- (versión de calibración/suelo) para no mezclar datos incompatibles.
-- =====================================================================
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('schema_version', '1');
INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('created', strftime('%s','now'));

-- Lecturas periódicas (telemetría del ESP32 o del simulador)
CREATE TABLE IF NOT EXISTS readings (
    id            INTEGER PRIMARY KEY,
    device        TEXT    NOT NULL,
    ts            INTEGER NOT NULL,             -- epoch UTC (s)
    boot          INTEGER,
    seq           INTEGER,
    simulated     INTEGER NOT NULL DEFAULT 0,
    source        TEXT    NOT NULL DEFAULT 'live',   -- live | buffer (enviado tras reconexión)
    vwc           REAL,                         -- %VWC (NULL si el EC-5 no es válido)
    soil_mv       INTEGER,
    soil_status   TEXT,
    temp_c        REAL,
    rh_pct        REAL,
    vpd_kpa       REAL,
    tank_pct      REAL,
    tank_cm       REAL,
    tank_status   TEXT,
    flow_lpm      REAL,
    today_l       REAL,
    total_l       REAL,
    mode          TEXT,
    state         TEXT,
    crop          TEXT,
    stage         TEXT,
    data_version  INTEGER,
    UNIQUE(device, ts, boot, seq)
);
CREATE INDEX IF NOT EXISTS ix_readings_dev_ts ON readings(device, ts);

-- Riegos (uno por ciclo de bomba) con su seguimiento
CREATE TABLE IF NOT EXISTS irrigation_events (
    event_id        TEXT PRIMARY KEY,           -- <device>-<consecutivo>
    device          TEXT NOT NULL,
    ts_start        INTEGER,
    ts_end          INTEGER,
    reason          TEXT,                       -- MANUAL, SCHEDULED, EMERGENCY, MANUAL_TARGET, IA
    mode            TEXT,
    crop            TEXT,
    stage           TEXT,
    vwc_before      REAL,
    goal_vwc        REAL,
    target_l        REAL,
    pulses          INTEGER,
    pulses_per_liter REAL,
    delivered_l     REAL,                       -- calculado por pulsos (no medido con recipiente)
    avg_flow_lpm    REAL,
    duration_s      REAL,
    vwc_after       REAL,                       -- tras la infiltración
    ia_pred_dvwc    REAL,
    ia_obs_dvwc     REAL,
    ia_error        REAL,
    result          TEXT,
    safety          TEXT,
    simulated       INTEGER NOT NULL DEFAULT 0,
    data_version    INTEGER
);
CREATE INDEX IF NOT EXISTS ix_irr_dev_ts ON irrigation_events(device, ts_start);

-- Eventos de fin de evento automático / IA / manual hacia objetivo
CREATE TABLE IF NOT EXISTS event_ends (
    id         INTEGER PRIMARY KEY,
    device     TEXT, ts INTEGER, event_id TEXT, why TEXT, why_text TEXT, cycles INTEGER,
    liters     REAL, vwc_before REAL, vwc_after REAL, goal_vwc REAL, simulated INTEGER DEFAULT 0,
    UNIQUE(device, event_id, ts)
);

-- Decisiones publicadas por el ESP32 (justificación de cada decisión)
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY, device TEXT, ts INTEGER, code TEXT, text TEXT, mode TEXT,
    soil_vwc REAL, in_window INTEGER, rain_expected INTEGER, simulated INTEGER DEFAULT 0,
    UNIQUE(device, ts, code)
);

-- Pronóstico Open-Meteo (consulta del servidor) y resumen del ESP32
CREATE TABLE IF NOT EXISTS weather_fetches (
    id INTEGER PRIMARY KEY, ts_fetch INTEGER NOT NULL, origin TEXT NOT NULL,   -- servidor | esp32:<id>
    lat REAL, lon REAL, ok INTEGER, http INTEGER, error TEXT,
    temp_c REAL, rh_pct REAL, precip_mm REAL, rain_mm REAL, weather_code INTEGER,
    past24h_precip_mm REAL, next24h_precip_mm REAL, next24h_prob_max REAL, et0_today_mm REAL,
    UNIQUE(ts_fetch, origin)
);
CREATE TABLE IF NOT EXISTS forecast_hourly (
    ts_fetch INTEGER NOT NULL, time INTEGER NOT NULL,
    temp_c REAL, rh_pct REAL, precip_prob REAL, precip_mm REAL, vpd_kpa REAL, et0_mm REAL,
    PRIMARY KEY (ts_fetch, time)
);
CREATE TABLE IF NOT EXISTS forecast_daily (
    ts_fetch INTEGER NOT NULL, date TEXT NOT NULL,
    tmax_c REAL, tmin_c REAL, precip_mm REAL, precip_prob_max REAL, et0_mm REAL,
    PRIMARY KEY (ts_fetch, date)
);

-- Aumentos de humedad no explicados (posible lluvia / riego externo / sensor)
CREATE TABLE IF NOT EXISTS rain_events (
    id INTEGER PRIMARY KEY, device TEXT, ts INTEGER, vwc_from REAL, vwc_to REAL, rise_pp REAL,
    classification TEXT, server_classification TEXT, weather_precip_mm REAL,
    confirmed_cause TEXT, confirmed_ts INTEGER, simulated INTEGER DEFAULT 0,
    UNIQUE(device, ts)
);

-- Cultivos: base (10) y personalizados (ilimitados, limitados solo por el disco)
CREATE TABLE IF NOT EXISTS crops (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL CHECK(type IN ('base','custom')),
    data TEXT NOT NULL,                         -- JSON del perfil
    created INTEGER, updated INTEGER, deleted INTEGER NOT NULL DEFAULT 0
);

-- Plantaciones y seguimiento de etapas
CREATE TABLE IF NOT EXISTS plantings (
    id INTEGER PRIMARY KEY, device TEXT, crop_id TEXT NOT NULL, variety TEXT, sow_date TEXT, transplant_date TEXT,   -- una plantación activa por caja (dispositivo)
    stage_index INTEGER NOT NULL DEFAULT 0, stage_start TEXT, stage_locked INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1, notes TEXT, created INTEGER, updated INTEGER
);
CREATE TABLE IF NOT EXISTS stage_changes (
    id INTEGER PRIMARY KEY, planting_id INTEGER, ts INTEGER, from_stage INTEGER, to_stage INTEGER,
    source TEXT,                                -- manual | recomendacion | ia_auto | correccion
    estimated INTEGER NOT NULL DEFAULT 1, confirmed INTEGER NOT NULL DEFAULT 0, note TEXT,
    days_in_stage REAL, gdd_in_stage REAL
);

-- Cambios de configuración enviados al ESP32 (con ID de transacción y ACK)
CREATE TABLE IF NOT EXISTS config_changes (
    id INTEGER PRIMARY KEY, device TEXT, ts INTEGER, txn TEXT UNIQUE, cmd TEXT, version INTEGER,
    status TEXT, message TEXT, params TEXT, ack_ts INTEGER
);

-- Cultivo/etapa activos por dispositivo
CREATE TABLE IF NOT EXISTS crop_changes (
    id INTEGER PRIMARY KEY, device TEXT, ts INTEGER, crop_id TEXT, stage TEXT, version INTEGER, source TEXT
);

-- IA: versiones del modelo, observaciones y predicciones
CREATE TABLE IF NOT EXISTS ia_snapshots (
    id INTEGER PRIMARY KEY, device TEXT, ts INTEGER, model_version INTEGER, status TEXT,
    events INTEGER, drying_hours REAL, mae_response REAL, mae_drying REAL,
    coef_response TEXT, coef_drying TEXT, data_version INTEGER, change_detected INTEGER,
    simulated INTEGER DEFAULT 0,
    UNIQUE(device, model_version, status, data_version, simulated)
);
CREATE TABLE IF NOT EXISTS ia_observations (
    id INTEGER PRIMARY KEY, device TEXT, ts INTEGER, model TEXT, event_id TEXT,
    predicted REAL, observed REAL, error REAL, used TEXT, x1 REAL, x2 REAL,
    model_version INTEGER, status TEXT, simulated INTEGER DEFAULT 0,
    UNIQUE(device, ts, model)
);
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY, device TEXT, ts_made INTEGER, ts_target INTEGER,
    predicted_vwc REAL, actual_vwc REAL, error REAL, model_version INTEGER, ia_status TEXT,
    crop TEXT, stage TEXT, season TEXT, simulated INTEGER DEFAULT 0,
    UNIQUE(device, ts_target)
);

-- Alertas y conectividad
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY, ts INTEGER, device TEXT, code TEXT, severity TEXT, message TEXT,
    active INTEGER NOT NULL DEFAULT 1, acknowledged INTEGER NOT NULL DEFAULT 0, source TEXT,
    simulated INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_alerts_ts ON alerts(ts);
CREATE TABLE IF NOT EXISTS connectivity (
    id INTEGER PRIMARY KEY, ts INTEGER, device TEXT, kind TEXT, detail TEXT
);

-- Versiones de datos (calibración del EC-5, cambio de suelo, etc.)
CREATE TABLE IF NOT EXISTS data_versions (
    version INTEGER PRIMARY KEY, ts INTEGER, description TEXT
);
INSERT OR IGNORE INTO data_versions(version, ts, description)
VALUES (1, strftime('%s','now'), 'Calibracion EC-5 Actividad 2.2 (0.08146067*mV - 23.932584); suelo sin caracterizar');

-- Calibración del suelo (capacidad de campo / marchitez medidas con el EC-5)
CREATE TABLE IF NOT EXISTS soil_calibration (
    id INTEGER PRIMARY KEY, ts INTEGER, data_version INTEGER, fc_vwc REAL, wp_vwc REAL,
    method TEXT, notes TEXT
);

-- Ajustes del servidor (dispositivo seleccionado, ubicación, etc.)
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY, value TEXT, updated INTEGER
);
