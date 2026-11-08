// SOLICITUDES DEL DASHBOARD (no son comandos al ESP32)
// Entrada: { topic:'req', payload:{ type, ... } }
// Salidas: 1) consultas SQLite (link call)  2) escrituras SQLite  3) refrescar estado
//          4) comandos al dispositivo  5) actualizar clima  6) respaldo  7) respuesta directa
const r = msg.payload || {};
const now = Math.floor(Date.now() / 1000);
const reqid = 'r' + Date.now().toString(36) + Math.floor(Math.random() * 1000);
const Q = [], W = [];
let refresh = null, cmd = null, wx = null, bk = null, resp = null;
// _client: la respuesta de las consultas va solo al navegador que la pidió (no a todos)
const q = (sql, params, part, total, extra) => Q.push({ topic: sql, payload: params || [], _client: msg._client,
    _req: Object.assign({ type: r.type, reqid, part, total: total || 1, args: r }, extra || {}) });
const w = (sql, params) => W.push({ topic: sql, payload: params || [] });
const dev = global.get('selected_device', 'file') || 'esp32_01';
const slug = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 20) || 'cultivo';
const CROPS_SQL = "SELECT id,name,type,data,updated FROM crops WHERE deleted=0 ORDER BY type, name";
const PLANT_SQL = "SELECT p.*, c.name AS crop_name, c.data AS crop_data FROM plantings p LEFT JOIN crops c ON c.id=p.crop_id ORDER BY p.active DESC, p.id DESC LIMIT 50";
const STAGES_SQL = "SELECT * FROM stage_changes ORDER BY ts DESC LIMIT 100";

function validCrop(c) {
    if (!c || !c.nombre || String(c.nombre).trim().length < 2) return 'El cultivo necesita nombre';
    if (!Array.isArray(c.etapas) || c.etapas.length < 1 || c.etapas.length > 8) return 'Defina de 1 a 8 etapas';
    for (const e of c.etapas) {
        if (!e.nombre || !(e.dias > 0 && e.dias <= 400)) return 'Cada etapa necesita nombre y duracion (1-400 dias)';
        if (e.umbrales) {
            const u = e.umbrales;
            const ks = ['hum_critical', 'hum_min', 'hum_target', 'hum_reserve', 'hum_max'];
            const some = ks.some(k => typeof u[k] === 'number');
            if (some) {
                if (!ks.every(k => typeof u[k] === 'number')) return 'Etapa ' + e.nombre + ': complete los 5 umbrales o deje todos vacios';
                if (!(u.hum_critical + 1 <= u.hum_min && u.hum_min + 1 <= u.hum_target && u.hum_target + 0.5 <= u.hum_reserve && u.hum_reserve <= u.hum_max && u.hum_max <= 70))
                    return 'Etapa ' + e.nombre + ': debe cumplirse emergencia < minima < optima < reserva <= maxima (<= 70)';
            }
        }
    }
    return null;
}

switch (r.type) {
case 'select_device':
    if (r.device && /^[a-z0-9_]{2,24}$/.test(r.device)) global.set('selected_device', r.device, 'file');
    refresh = { topic: 'refresh' };
    break;
case 'prev_mode_clear': {
    const pm = global.get('prev_mode', 'file') || {};
    delete pm[dev];
    global.set('prev_mode', pm, 'file');
    resp = { topic: 'config_result', payload: { ok: true, message: 'Se queda en MANUAL: solo regará cuando lo pidas' } };
    refresh = { topic: 'refresh' };
    break;
}
case 'crops_list':
    q(CROPS_SQL, [], 1, 1);
    break;
case 'crop_save': {
    const c = r.crop || {};
    const err = validCrop(c);
    if (err) { resp = { topic: 'crop_result', payload: { ok: false, message: err } }; break; }
    let id = c.id;
    if (!id || r.is_new) id = 'custom_' + slug(c.nombre) + '_' + now.toString(36);
    if (/^(lechuga|espinaca|rabano|zanahoria|cebolla|tomate|pimiento|pepino|calabacita|frijol_ejotero)$/.test(id)) {
        resp = { topic: 'crop_result', payload: { ok: false, message: 'Los cultivos base no se editan: use DUPLICAR' } }; break;
    }
    c.id = id; c.tipo = 'custom';
    c.ciclo_total_dias = c.etapas.reduce((a, e) => a + Number(e.dias || 0), 0);
    w('INSERT INTO crops(id,name,type,data,created,updated,deleted) VALUES($1,$2,$3,$4,$5,$6,0) ' +
      'ON CONFLICT(id) DO UPDATE SET name=excluded.name, data=excluded.data, updated=excluded.updated, deleted=0',
      [id, c.nombre, 'custom', JSON.stringify(c), now, now]);
    q(CROPS_SQL, [], 1, 1, { saved: id, message: 'Cultivo "' + c.nombre + '" guardado' });
    break;
}
case 'crop_delete':
    if (!String(r.id || '').startsWith('custom_')) { resp = { topic: 'crop_result', payload: { ok: false, message: 'Solo se eliminan cultivos personalizados' } }; break; }
    // Borrado lógico: el historial que lo usa se conserva
    w('UPDATE crops SET deleted=1, updated=$1 WHERE id=$2 AND type=$3', [now, r.id, 'custom']);
    q(CROPS_SQL, [], 1, 1, { message: 'Cultivo eliminado (el historial se conserva)' });
    break;
case 'plantings_list':
    q(PLANT_SQL, [], 1, 2);
    q(STAGES_SQL, [], 2, 2);
    break;
case 'planting_save': {
    const p = r.planting || {};
    if (!p.crop_id || !(p.sow_date || p.transplant_date)) { resp = { topic: 'growth_result', payload: { ok: false, message: 'Seleccione cultivo y fecha de siembra o trasplante' } }; break; }
    if (p.id) {
        w('UPDATE plantings SET crop_id=$1, variety=$2, sow_date=$3, transplant_date=$4, notes=$5, updated=$6 WHERE id=$7',
          [p.crop_id, p.variety || '', p.sow_date || null, p.transplant_date || null, p.notes || '', now, p.id]);
        w('INSERT INTO stage_changes(planting_id,ts,from_stage,to_stage,source,estimated,confirmed,note) VALUES($1,$2,$3,$4,$5,0,1,$6)',
          [p.id, now, null, null, 'correccion', 'Fechas corregidas por el usuario']);
    } else {
        // Una sola caja = una sola plantación activa: la anterior se cierra (queda en el historial)
        const pdev = r.device || dev;
        w('UPDATE plantings SET active=0, updated=$1 WHERE active=1 AND (device=$2 OR device IS NULL)', [now, pdev]);
        w('INSERT INTO plantings(device,crop_id,variety,sow_date,transplant_date,stage_index,stage_start,stage_locked,active,notes,created,updated) ' +
          'VALUES($1,$2,$3,$4,$5,0,$6,0,1,$7,$8,$9)',
          [pdev, p.crop_id, p.variety || '', p.sow_date || null, p.transplant_date || null, p.sow_date || p.transplant_date, p.notes || '', now, now]);
        // El cultivo de la plantación nueva pasa a ser el perfil activo de esa caja (primera etapa)
        q("SELECT id,name,type,data FROM crops WHERE id=$1", [p.crop_id], 1, 1, { type: 'apply_crop', stage_index: 0, device: pdev });
    }
    q(PLANT_SQL, [], 1, 2, { message: 'Plantacion guardada' });
    q(STAGES_SQL, [], 2, 2);
    break;
}
case 'planting_stage': {
    // action: advance | back | confirm | lock | unlock | set (to)
    const g = (global.get('growth') || { items: [] }).items.find(x => x.id === r.id);
    if (!g) { resp = { topic: 'growth_result', payload: { ok: false, message: 'Plantacion no encontrada' } }; break; }
    const nst = g.n_stages || 4;
    let to = g.stage_index;
    if (r.action === 'advance') to = Math.min(nst - 1, g.stage_index + 1);
    else if (r.action === 'back') to = Math.max(0, g.stage_index - 1);
    else if (r.action === 'confirm') to = (typeof g.estimated_index === 'number') ? g.estimated_index : g.stage_index;
    else if (r.action === 'set') to = Math.max(0, Math.min(nst - 1, Number(r.to) || 0));
    if (r.action === 'lock' || r.action === 'unlock') {
        w('UPDATE plantings SET stage_locked=$1, updated=$2 WHERE id=$3', [r.action === 'lock' ? 1 : 0, now, r.id]);
    } else if (to !== g.stage_index) {
        const today = new Date().toISOString().slice(0, 10);
        w('UPDATE plantings SET stage_index=$1, stage_start=$2, updated=$3 WHERE id=$4', [to, today, now, r.id]);
        w('INSERT INTO stage_changes(planting_id,ts,from_stage,to_stage,source,estimated,confirmed,note,days_in_stage,gdd_in_stage) ' +
          'VALUES($1,$2,$3,$4,$5,0,1,$6,$7,$8)',
          [r.id, now, g.stage_index, to, r.action === 'confirm' ? 'recomendacion_confirmada' : (r.action === 'set' ? 'correccion' : 'manual'),
           r.note || '', g.days_in_stage || null, g.gdd_in_stage || null]);
        if (r.apply !== false) q("SELECT id,name,type,data FROM crops WHERE id=$1", [g.crop_id], 1, 1,
            { type: 'apply_crop', stage_index: to, planting_id: r.id, silent: false, device: g.device || dev });
    }
    q(PLANT_SQL, [], 1, 2, { type: 'plantings_list', message: 'Etapa actualizada' });
    q(STAGES_SQL, [], 2, 2, { type: 'plantings_list' });
    break;
}
case 'apply_crop':
    // Aplica el perfil del cultivo/etapa al ESP32 (requiere confirmación en el dashboard)
    q("SELECT id,name,type,data FROM crops WHERE id=$1", [r.crop_id], 1, 1, { stage_index: r.stage_index || 0 });
    break;
case 'history': {
    const from = Math.floor(Number(r.from) || now - 7 * 86400), to = Math.floor(Number(r.to) || now);
    const span = to - from;
    // Intervalo elegido por el usuario (10 min, hora, 6 h, día, semana, mes de 30 días) o automático
    const PERMITIDOS = [600, 3600, 21600, 86400, 604800, 2592000];
    const elegido = Number(r.bucket);
    const bucket = PERMITIDOS.includes(elegido) ? elegido : (span <= 2 * 86400 ? 600 : (span <= 14 * 86400 ? 3600 : 21600));
    const d = r.device || dev;
    const crop = r.crop || '';
    const cf = crop ? ' AND crop=$4' : '';
    const prm = crop ? [d, from, to, crop] : [d, from, to];
    q('SELECT ((ts - 21600)/' + bucket + ')*' + bucket + ' + 21600 AS t, AVG(vwc) vwc, AVG(temp_c) temp, AVG(rh_pct) rh, AVG(tank_pct) tank, ' +
      'MAX(today_l) today, MAX(simulated) sim FROM readings WHERE device=$1 AND ts BETWEEN $2 AND $3' + cf + ' GROUP BY t ORDER BY t', prm, 1, 4, { bucket });
    q("SELECT date(ts_start,'unixepoch','-6 hours') AS day, SUM(COALESCE(delivered_l,0)) liters, COUNT(*) n FROM irrigation_events " +
      'WHERE device=$1 AND ts_start BETWEEN $2 AND $3' + cf + ' GROUP BY day ORDER BY day', prm, 2, 4, { bucket });
    q('SELECT * FROM irrigation_events WHERE device=$1 AND ts_start BETWEEN $2 AND $3' + cf + ' ORDER BY ts_start DESC LIMIT 200', prm, 3, 4, { bucket });
    q('SELECT * FROM rain_events WHERE device=$1 AND ts BETWEEN $2 AND $3 ORDER BY ts DESC LIMIT 100', [d, from, to], 4, 4, { bucket });
    break;
}
case 'compare_history': {
    // Comparaciones históricas por mes/estación, cultivo y etapa
    const d = r.device || dev;
    q("SELECT strftime('%Y-%m', ts,'unixepoch','-6 hours') AS mes, crop, stage, ROUND(AVG(vwc),1) vwc, ROUND(AVG(temp_c),1) temp, " +
      'ROUND(AVG(vpd_kpa),2) vpd, COUNT(*) n, MAX(simulated) sim FROM readings WHERE device=$1 GROUP BY mes, crop, stage ORDER BY mes DESC LIMIT 60', [d], 1, 2);
    q("SELECT strftime('%Y-%m', ts_start,'unixepoch','-6 hours') AS mes, crop, mode, ROUND(SUM(COALESCE(delivered_l,0)),2) liters, COUNT(*) n " +
      'FROM irrigation_events WHERE device=$1 GROUP BY mes, crop, mode ORDER BY mes DESC LIMIT 60', [d], 2, 2);
    break;
}
case 'alerts_list':
    q('SELECT * FROM alerts ORDER BY ts DESC LIMIT $1', [Math.min(500, r.limit || 150)], 1, 2);
    q('SELECT * FROM rain_events ORDER BY ts DESC LIMIT 50', [], 2, 2);
    break;
case 'alert_ack':
    w('UPDATE alerts SET acknowledged=1, active=0 WHERE id=$1', [r.id]);
    q('SELECT * FROM alerts ORDER BY ts DESC LIMIT $1', [150], 1, 2, { type: 'alerts_list' });
    q('SELECT * FROM rain_events ORDER BY ts DESC LIMIT 50', [], 2, 2, { type: 'alerts_list' });
    break;
case 'rain_confirm':
    if (['LLUVIA', 'RIEGO_EXTERNO', 'ERROR_SENSOR', 'OTRO'].includes(r.cause)) {
        w('UPDATE rain_events SET confirmed_cause=$1, confirmed_ts=$2 WHERE id=$3', [r.cause, now, r.id]);
    }
    q('SELECT * FROM alerts ORDER BY ts DESC LIMIT $1', [150], 1, 2, { type: 'alerts_list', message: 'Causa registrada' });
    q('SELECT * FROM rain_events ORDER BY ts DESC LIMIT 50', [], 2, 2, { type: 'alerts_list' });
    break;
case 'ia_compare': {
    const d = r.device || dev;
    q('SELECT ts_target t, predicted_vwc p, actual_vwc a FROM predictions WHERE device=$1 AND ts_target > $2 ORDER BY ts_target', [d, now - 7 * 86400], 1, 5);
    q('SELECT model_version, ia_status, COUNT(actual_vwc) n, ROUND(AVG(ABS(error)),3) mae FROM predictions WHERE device=$1 AND actual_vwc IS NOT NULL ' +
      'GROUP BY model_version, ia_status ORDER BY model_version DESC LIMIT 20', [d], 2, 5);
    q('SELECT season, crop, stage, COUNT(actual_vwc) n, ROUND(AVG(ABS(error)),3) mae FROM predictions WHERE device=$1 AND actual_vwc IS NOT NULL ' +
      'GROUP BY season, crop, stage ORDER BY season', [d], 3, 5);
    q('SELECT * FROM ia_snapshots WHERE device=$1 ORDER BY ts DESC LIMIT 30', [d], 4, 5);
    q('SELECT * FROM ia_observations WHERE device=$1 ORDER BY ts DESC LIMIT 60', [d], 5, 5);
    break;
}
case 'bed_save': {
    const a = Number(r.area_m2), dcm = Number(r.depth_cm);
    if (!(a >= 0.05 && a <= 20 && dcm >= 5 && dcm <= 100)) {
        resp = { topic: 'config_result', payload: { ok: false, message: 'Valores invalidos: area 0.05-20 m2 y profundidad de sustrato 5-100 cm' } }; break;
    }
    const bed = { area_m2: a, depth_cm: dcm, drainage: r.drainage === 'restringido' ? 'restringido' : 'libre',
        mix: String(r.mix || '').slice(0, 120), ts: now };
    global.set('bed', bed, 'file');
    resp = { topic: 'config_result', payload: { ok: true, message: 'Cama guardada: ' + Math.round(a * dcm * 10) + ' L de sustrato, 1 punto de %VWC = ' +
        (a * dcm / 10).toFixed(2) + ' L. Vuelve a aplicar el cultivo para enviar los litros al ESP32.' } };
    refresh = { topic: 'refresh' };
    break;
}
case 'soil_cal_save': {
    const fc = Number(r.fc_vwc), wp = Number(r.wp_vwc);
    if (!(fc > 5 && fc <= 70 && wp >= 0 && wp < fc - 5)) {
        resp = { topic: 'config_result', payload: { ok: false, message: 'Valores invalidos: se requiere 0 <= marchitez < capacidad de campo - 5 <= 70 %VWC' } }; break;
    }
    const cal = { fc_vwc: fc, wp_vwc: wp, method: r.method || '', notes: r.notes || '', ts: now, data_version: r.data_version || 1 };
    global.set('soil_cal', cal, 'file');
    w('INSERT INTO soil_calibration(ts,data_version,fc_vwc,wp_vwc,method,notes) VALUES($1,$2,$3,$4,$5,$6)',
      [now, cal.data_version, fc, wp, cal.method, cal.notes]);
    resp = { topic: 'config_result', payload: { ok: true, message: 'Calibracion del suelo guardada en el servidor (FC ' + fc + ', WP ' + wp + ' %VWC)' } };
    refresh = { topic: 'refresh' };
    break;
}
case 'location_save': {
    const lat = Number(r.lat), lon = Number(r.lon);
    if (!(lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) || (lat === 0 && lon === 0)) {
        resp = { topic: 'config_result', payload: { ok: false, message: 'Coordenadas invalidas' } }; break;
    }
    global.set('location', { lat, lon, label: String(r.label || '').slice(0, 60) || 'Huerto', ts: now }, 'file');
    wx = { topic: 'weather_refresh' };
    resp = { topic: 'config_result', payload: { ok: true, message: 'Ubicacion guardada; se consulta Open-Meteo de nuevo' } };
    refresh = { topic: 'refresh' };
    break;
}
case 'data_version_new':
    q('SELECT COALESCE(MAX(version),0)+1 AS v FROM data_versions', [], 1, 1, { description: String(r.description || 'Nueva calibracion').slice(0, 200) });
    break;
case 'weather_refresh':
    wx = { topic: 'weather_refresh' };
    break;
case 'backup_now':
    bk = { topic: 'backup' };
    break;
case 'boot_hist':
    q('SELECT device, ts, vwc, temp_c AS temp, rh_pct AS rh, tank_pct AS tank FROM readings WHERE ts > $1 ORDER BY ts', [now - 86400], 1, 1);
    break;
case 'db_stats':
    q("SELECT (SELECT COUNT(*) FROM readings) readings, (SELECT COUNT(*) FROM irrigation_events) events, " +
      "(SELECT COUNT(*) FROM alerts) alerts, (SELECT COUNT(*) FROM predictions) predictions, (SELECT MIN(ts) FROM readings) first_ts", [], 1, 1);
    break;
default:
    resp = { topic: 'error', payload: { message: 'Solicitud desconocida: ' + r.type } };
}
// Las consultas que leen lo recién escrito se envían un poco después
if (W.length && Q.length) {
    setTimeout(() => node.send([Q, null, null, null, null, null, null]), 300);
    return [null, W, refresh, cmd, wx, bk, resp];
}
return [Q.length ? Q : null, W.length ? W : null, refresh, cmd, wx, bk, resp];
