// RESPUESTAS DE SQLITE -> DASHBOARD (combina consultas de varias partes)
// (umbrales.js se antepone a este código al generar el flujo)
// Salidas: 1) dashboard  2) comando al dispositivo  3) refrescar estado  4) escrituras SQLite
const rq = msg._req || {};
if (!rq.type) return null;
const parts = context.get('parts') || {};
let rows = msg.payload;
if (rq.total > 1) {
    const e = parts[rq.reqid] || (parts[rq.reqid] = { t: Date.now(), r: {} });
    e.r[rq.part] = rows;
    // Limpieza de solicitudes viejas incompletas
    for (const k of Object.keys(parts)) if (Date.now() - parts[k].t > 30000) delete parts[k];
    if (Object.keys(e.r).length < rq.total) { context.set('parts', parts); return null; }
    rows = e.r;
    delete parts[rq.reqid];
}
context.set('parts', parts);
const ui = (topic, payload) => [{ topic, payload }, null, null, null];
// Consultas de solo lectura: la respuesta va solo al navegador que la pidió
const uiPriv = (topic, payload) => [{ topic, payload, _client: msg._client }, null, null, null];
// Versión siguiente: mayor entre la del servidor y la que reporta el dispositivo
const nextVersion = (device) => {
    const devs = global.get('devices') || {};
    const d = devs[device || global.get('selected_device', 'file') || 'esp32_01'] || {};
    const v = Math.max(global.get('profile_version', 'file') || 0, (d.config && d.config.profile_version) || 0) + 1;
    global.set('profile_version', v, 'file');
    return v;
};
const parseCrop = (row) => { try { const c = JSON.parse(row.data); c.tipo = row.type; c.updated = row.updated; return c; } catch (e) { return null; } };

switch (rq.type) {
case 'crops_list':
case 'crop_save':
case 'crop_delete': {
    const list = (rows || []).map(parseCrop).filter(Boolean);
    global.set('crops_cache', list);
    const out = ui('crops', { list, saved: rq.saved || null, message: rq.message || null });
    return out;
}
case 'plantings_list':
case 'planting_save':
case 'planting_stage': {
    const pl = (rows[1] || []).map(p => { const c = (() => { try { return JSON.parse(p.crop_data); } catch (e) { return null; } })();
        delete p.crop_data; p.crop = c; return p; });
    global.set('plantings_cache', pl);
    global.set('stage_history', rows[2] || []);
    return [{ topic: 'plantings', payload: { list: pl, history: rows[2] || [], message: rq.message || null } }, null, { topic: 'growth_recalc' }, null];
}
case 'apply_crop': {
    const row = (rows || [])[0];
    const c = row ? parseCrop(row) : null;
    if (!c) return ui('crop_result', { ok: false, message: 'Cultivo no encontrado' });
    const si = Math.max(0, Math.min((c.etapas || []).length - 1, Number(rq.stage_index) || 0));
    const soil = global.get('soil_cal', 'file');
    const sw = global.get('server_weather') || {};
    const u = calcUmbrales(c, si, soil, sw.et0_today_mm);
    const st = c.etapas[si] || {};
    // El ESP32 guarda textos en bytes UTF-8 (crop_id/stage 23, crop_name 31): una "ó" ocupa 2
    const nbytes = (t) => encodeURIComponent(t).replace(/%[0-9A-F]{2}/gi, 'x').length;
    const cutB = (t, max) => { t = String(t); while (nbytes(t) > max) t = t.slice(0, -1); return t.trim(); };
    const stageName = String(st.nombre || ('etapa ' + (si + 1))).replace('fructificación', 'fructif.');
    const params = { crop_id: cutB(c.id, 23), crop_name: cutB(c.nombre, 31),
        stage: cutB(stageName, 23), kc: Math.round((st.kc || u.kc || 1) * 100) / 100 };
    if (u.ok) Object.assign(params, { hum_critical: u.hum_critical, hum_min: u.hum_min, hum_target: u.hum_target,
        hum_reserve: u.hum_reserve, hum_max: u.hum_max });
    const bed = global.get('bed', 'file');
    Object.assign(params, paramsCama(bed));
    if (c.horarios && c.horarios.win1) { params.win1_start = c.horarios.win1[0]; params.win1_end = c.horarios.win1[1]; }
    if (c.horarios && c.horarios.win2) { params.win2_start = c.horarios.win2[0]; params.win2_end = c.horarios.win2[1]; }
    const tdev = rq.device || (rq.args || {}).device || null;
    const version = nextVersion(tdev);
    global.set('last_profile', { crop_id: c.id, stage: params.stage, version, umbrales: u });
    const cmd = { payload: { cmd: 'APPLY_PROFILE', version, params,
        _ui: { label: 'Perfil ' + c.nombre + ' / ' + params.stage + (u.ok ? '' : ' (humedad PENDIENTE DE CALIBRACION: se conservan los umbrales actuales)') } } };
    if (tdev) cmd.payload.device = tdev;
    return [{ topic: 'crop_result', payload: { ok: true, sending: true, umbrales: u, params,
        message: 'Enviando perfil al ESP32 (v' + version + ')...' } }, cmd, null, null];
}
case 'history': {
    const series = rows[1] || [];
    return uiPriv('history', { bucket: rq.bucket, series, daily: rows[2] || [], events: rows[3] || [], rain: rows[4] || [], args: rq.args });
}
case 'compare_history':
    return uiPriv('compare', { readings: rows[1] || [], irrigation: rows[2] || [] });
case 'alerts_list':
case 'alert_ack':
case 'rain_confirm':
    return ui('alerts_list', { alerts: rows[1] || [], rain: rows[2] || [], message: rq.message || null });
case 'ia_compare':
    return ui('ia_compare', { pred: rows[1] || [], by_version: rows[2] || [], by_season: rows[3] || [], snapshots: rows[4] || [], observations: rows[5] || [] });
case 'data_version_new': {
    const v = (rows && rows[0] && rows[0].v) || 2;
    const db = { topic: 'INSERT INTO data_versions(version,ts,description) VALUES($1,$2,$3)', payload: [v, Math.floor(Date.now() / 1000), rq.description] };
    const cmd = { payload: { cmd: 'APPLY_CONFIG', version: nextVersion(), params: { data_version: v },
        _ui: { label: 'Nueva version de datos ' + v } } };
    return [{ topic: 'config_result', payload: { ok: true, message: 'Version de datos ' + v + ' creada; enviando al ESP32 (la IA reinicia su modelo, el historial se conserva)' } }, cmd, null, db];
}
case 'boot_hist': {
    // Recupera las gráficas de 24 h tras reiniciar Node-RED
    const devs = global.get('devices') || {};
    for (const x of (rows || [])) {
        const d = devs[x.device] || (devs[x.device] = { id: x.device });
        (d.hist || (d.hist = [])).push({ ts: x.ts, vwc: x.vwc, temp: x.temp, rh: x.rh, tank: x.tank });
    }
    global.set('devices', devs);
    return [null, null, { topic: 'refresh' }, null];
}
case 'db_stats':
    global.set('db_stats', rows[0] || null);
    return [null, null, { topic: 'refresh' }, null];
default:
    return null;
}
