// INGESTA MQTT: huerto/<entorno>/<dispositivo>/<subtopic>
// Salidas: 1) escrituras SQLite  2) refrescar dashboard  3) ACK de comandos
//          4) alertas  5) eventos para IA/crecimiento  6) comando GET_HISTORY al reconectarse
const parts = String(msg.topic || '').split('/');
if (parts.length < 4) return null;
const device = parts[2];
const sub = parts.slice(3).join('/');
let p = msg.payload;
if (typeof p === 'string') {
    try { p = JSON.parse(p); } catch (e) { node.warn('JSON invalido en ' + msg.topic); return null; }
}
if (p === null || typeof p !== 'object') return null;

const devs = global.get('devices') || {};
const d = devs[device] || (devs[device] = { id: device });
const now = Math.floor(Date.now() / 1000);
d.last_seen = now;
d[sub] = p;
d.simulated = !!p.simulated || device.startsWith('sim');
global.set('devices', devs);

const db = [];
const sim = d.simulated ? 1 : 0;
const ts = (p.ts && p.ts > 1600000000) ? p.ts : now;
const num = (v) => (typeof v === 'number' && isFinite(v)) ? v : null;
const q = (sql, params) => db.push({ topic: sql, payload: params });
let alerts = [];
let evt = null;
let pedirHistorial = false;

switch (sub) {
case 'status':
    q('INSERT INTO connectivity(ts,device,kind,detail) VALUES($1,$2,$3,$4)',
      [now, device, p.online ? 'mqtt_online' : 'mqtt_offline', p.reason || '']);
    if (!p.online) alerts.push({ code: 'DEVICE_OFFLINE', severity: 'CRITICAL',
        message: 'El dispositivo ' + device + ' perdio la conexion MQTT (mensaje de ultima voluntad)' });
    else {
        alerts.push({ code: 'DEVICE_ONLINE', severity: 'INFO', message: device + ' conectado', resolve: 'DEVICE_OFFLINE' });
        pedirHistorial = true;     // completar riegos cuyo final se perdió durante la desconexión
    }
    break;
case 'telemetry': {
    const s = p.soil || {}, e = p.env || {}, t = p.tank || {}, f = p.flow || {};
    q('INSERT OR IGNORE INTO readings(device,ts,boot,seq,simulated,source,vwc,soil_mv,soil_status,temp_c,rh_pct,vpd_kpa,' +
      'tank_pct,tank_cm,tank_status,flow_lpm,today_l,total_l,mode,state,crop,stage,data_version) ' +
      'VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23)',
      [device, ts, p.boot || 0, p.seq || 0, sim, 'live', s.valid ? num(s.vwc_pct) : null, num(s.mv), s.status || null,
       num(e.temp_c), num(e.rh_pct), num(e.vpd_kpa), num(t.level_pct), num(t.distance_cm), t.status || null,
       num(f.lpm), num(f.today_l), num(f.total_l), p.mode || null, p.state || null, p.crop || null, p.stage || null,
       p.data_version || null]);
    // Historial corto en memoria para gráficas rápidas (24 h)
    const h = d.hist || (d.hist = []);
    h.push({ ts, vwc: s.valid ? num(s.vwc_pct) : null, temp: num(e.temp_c), rh: num(e.rh_pct), tank: num(t.level_pct), mv: num(s.mv), water: num(f.today_l) });
    while (h.length && h[0].ts < now - 86400) h.shift();
    if (h.length > 3000) h.splice(0, h.length - 3000);
    global.set('devices', devs);
    break;
}
case 'telemetry_buffer':
    for (const smp of (p.samples || [])) {
        if (!smp.ts) continue;
        q('INSERT OR IGNORE INTO readings(device,ts,boot,seq,simulated,source,vwc,temp_c,rh_pct,tank_pct,today_l,mode,state) ' +
          'VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)',
          [device, smp.ts, -1, smp.ts, sim, 'buffer', num(smp.vwc_pct), num(smp.temp_c), num(smp.rh_pct),
           num(smp.tank_pct), num(smp.today_l), smp.mode || null, smp.state || null]);
    }
    alerts.push({ code: 'OFFLINE_BUFFER', severity: 'INFO',
        message: device + ' envio ' + (p.samples || []).length + ' muestras guardadas mientras no habia conexion' });
    break;
case 'decision':
    q('INSERT OR IGNORE INTO decisions(device,ts,code,text,mode,soil_vwc,in_window,rain_expected,simulated) ' +
      'VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)',
      [device, ts, p.code, p.text, p.mode || null, num(p.soil_vwc), p.in_window ? 1 : 0, p.rain_expected ? 1 : 0, sim]);
    {
        const dh = d.dec_hist || (d.dec_hist = []);
        if (!dh.length || dh[0].code !== p.code || dh[0].ts !== ts) dh.unshift({ ts, code: p.code, text: p.text, vwc: num(p.soil_vwc), mode: p.mode });
        if (dh.length > 30) dh.length = 30;
        global.set('devices', devs);
    }
    break;
case 'event': {
    evt = p;
    if (p.type === 'WATERING_START') {
        q('INSERT OR IGNORE INTO irrigation_events(event_id,device,ts_start,reason,mode,crop,stage,vwc_before,goal_vwc,' +
          'target_l,ia_pred_dvwc,simulated) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)',
          [p.event_id, device, ts, p.reason, p.mode, p.crop, p.stage, num(p.vwc_before), num(p.goal_vwc),
           num(p.target_l), num(p.ia_pred_dvwc), sim]);
    } else if (p.type === 'WATERING_END') {
        q('INSERT OR IGNORE INTO irrigation_events(event_id,device,simulated) VALUES($1,$2,$3)', [p.event_id, device, sim]);
        q('UPDATE irrigation_events SET ts_end=$1,result=$2,pulses=$3,pulses_per_liter=$4,delivered_l=$5,avg_flow_lpm=$6,' +
          'duration_s=$7,safety=$8,target_l=COALESCE(target_l,$9),vwc_before=COALESCE(vwc_before,$10) WHERE event_id=$11',
          [ts, p.result, p.pulses || 0, num(p.pulses_per_liter), num(p.delivered_l), num(p.avg_flow_lpm),
           num(p.duration_s), p.safety || null, num(p.target_l), num(p.vwc_before), p.event_id]);
        if (p.result && !['TARGET', 'STOP_CMD'].includes(p.result))
            alerts.push({ code: 'WATERING_' + p.result, severity: 'CRITICAL',
                message: 'Riego ' + p.event_id + ' termino por ' + p.result });
    } else if (p.type === 'EVENT_END') {
        q('INSERT OR IGNORE INTO event_ends(device,ts,event_id,why,why_text,cycles,liters,vwc_before,vwc_after,goal_vwc,simulated) ' +
          'VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)',
          [device, ts, p.event_id, p.why, p.why_text, p.cycles, num(p.liters), num(p.vwc_before),
           num(p.vwc_after_infiltration), num(p.goal_vwc), sim]);
        q('UPDATE irrigation_events SET vwc_after=$1 WHERE event_id=$2', [num(p.vwc_after_infiltration), p.event_id]);
    } else if (p.type === 'IA_OBSERVATION') {
        q('INSERT OR IGNORE INTO ia_observations(device,ts,model,event_id,predicted,observed,error,used,x1,x2,model_version,status,simulated) ' +
          'VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)',
          [device, ts, p.model, p.event_id || null, num(p.predicted), num(p.observed), num(p.error), p.used,
           num(p.x1), num(p.x2), p.model_version || 0, p.status || null, sim]);
        if (p.model === 'RESPUESTA_RIEGO' && p.event_id) {
            q('UPDATE irrigation_events SET ia_obs_dvwc=$1, ia_error=$2 WHERE event_id=$3',
              [num(p.observed), num(p.error), p.event_id]);
            if (typeof p.error === 'number' && Math.abs(p.error) > 4)
                alerts.push({ code: 'IA_PREDICTION_ERROR', severity: 'WARNING',
                    message: 'Error de prediccion IA de ' + p.error.toFixed(1) + ' pp en ' + p.event_id + ' (se usa para mejorar el modelo)' });
        }
    } else if (p.type === 'UNEXPLAINED_RISE') {
        const sw = global.get('server_weather') || {};
        const pr = (typeof sw.past24h_precip_mm === 'number') ? sw.past24h_precip_mm : null;
        let srv = p.classification;
        if (pr !== null && pr >= 1 && srv !== 'POSIBLE_ERROR_SENSOR') srv = 'POSIBLE_LLUVIA';
        q('INSERT OR IGNORE INTO rain_events(device,ts,vwc_from,vwc_to,rise_pp,classification,server_classification,' +
          'weather_precip_mm,simulated) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)',
          [device, ts, num(p.vwc_from), num(p.vwc_to), num(p.rise_pp), p.classification, srv, pr, sim]);
        const names = { POSIBLE_LLUVIA: 'POSIBLE LLUVIA', POSIBLE_RIEGO_EXTERNO: 'POSIBLE RIEGO EXTERNO',
            AUMENTO_NO_EXPLICADO: 'AUMENTO DE HUMEDAD NO EXPLICADO', POSIBLE_ERROR_SENSOR: 'POSIBLE ERROR DEL SENSOR' };
        alerts.push({ code: srv, severity: 'WARNING', message: (names[srv] || srv) + ': humedad ' +
            (p.vwc_from || 0).toFixed(1) + ' -> ' + (p.vwc_to || 0).toFixed(1) + ' %VWC sin riego de la bomba. Confirme la causa en ALERTAS.' });
    }
    break;
}
case 'alarm':
    alerts.push({ code: p.code, severity: p.severity, message: p.message, active: p.active, fromDevice: true });
    break;
case 'ia': {
    const key = [p.model_version, p.status, p.data_version, sim].join('|');
    if (d._ia_key !== key) {
        d._ia_key = key;
        q('INSERT OR IGNORE INTO ia_snapshots(device,ts,model_version,status,events,drying_hours,mae_response,mae_drying,' +
          'coef_response,coef_drying,data_version,change_detected,simulated) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)',
          [device, ts, p.model_version, p.status, p.events_learned, num(p.drying_hours_learned), num(p.mae_response_pp),
           num(p.mae_drying_pph), JSON.stringify(p.coef_response || []), JSON.stringify(p.coef_drying || []),
           p.data_version || null, p.change_detected ? 1 : 0, sim]);
        if (p.change_detected) alerts.push({ code: 'IA_CHANGE_DETECTED', severity: 'WARNING',
            message: 'La IA detecto un cambio sostenido en la respuesta del suelo: vuelve a VALIDACION' });
    }
    break;
}
case 'weather':
    if (p.fetch_ts) {
        q('INSERT OR IGNORE INTO weather_fetches(ts_fetch,origin,lat,lon,ok,temp_c,rh_pct,precip_mm,past24h_precip_mm,' +
          'next24h_precip_mm,next24h_prob_max,et0_today_mm) VALUES($1,$2,$3,$4,1,$5,$6,$7,$8,$9,$10,$11)',
          [p.fetch_ts, 'esp32:' + device, num(p.lat), num(p.lon), num(p.temp_c), num(p.rh_pct), num(p.precip_mm),
           num(p.past6h_precip_mm), num(p.next6h_precip_mm), num(p.next6h_prob_max_pct), num(p.et0_24h_mm)]);
    }
    break;
case 'history':
    // Historial guardado en el ESP32 (ts = FIN del riego; inicio = ts - duración). Completa los riegos que quedaron sin final
    // en la base (p. ej. el WATERING_END se publicó mientras el MQTT estaba caído) y agrega los que faltan.
    for (const e of (p.entries || [])) {
        if (!e || !(e.ts > 1600000000) || !e.result || e.result === 'NONE') continue;
        const dur = num(e.duration_s), lit = num(e.liters);
        const t0 = e.ts - Math.round(dur || 0);
        const ini = t0 - 3, fin = t0 + 3;
        q('UPDATE irrigation_events SET ts_end=COALESCE(ts_end,$1),result=COALESCE(result,$2),delivered_l=COALESCE(delivered_l,$3),' +
          'duration_s=COALESCE(duration_s,$4),pulses=COALESCE(NULLIF(pulses,0),$5),vwc_after=COALESCE(vwc_after,$6) ' +
          'WHERE device=$7 AND result IS NULL AND ts_start BETWEEN $8 AND $9',
          [e.ts, e.result, lit, dur, e.pulses || 0, num(e.vwc_after), device, ini, fin]);
        q('INSERT INTO irrigation_events(event_id,device,ts_start,ts_end,reason,result,delivered_l,duration_s,pulses,vwc_before,vwc_after,simulated) ' +
          'SELECT $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12 WHERE NOT EXISTS (SELECT 1 FROM irrigation_events WHERE device=$13 AND ts_start BETWEEN $14 AND $15)',
          [device + '-h' + t0, device, t0, e.ts, e.reason || null, e.result, lit, dur, e.pulses || 0,
           num(e.vwc_before), num(e.vwc_after), sim, device, ini, fin]);
    }
    break;
case 'ack':
    break;
default:
    break;
}

const out1 = db.length ? db : null;
const out2 = { topic: 'refresh', device, sub };
const out3 = sub === 'ack' ? { topic: 'ack', device, payload: p } : null;
const out4 = alerts.length ? alerts.map(a => ({ topic: 'alert', device, simulated: sim, payload: a })) : null;
const out5 = evt ? { topic: 'event', device, simulated: sim, payload: evt } : null;
if (pedirHistorial) {
    // Se pide unos segundos después, cuando el ESP32 ya está suscrito a sus comandos
    const root = env.get('RIEGO_TOPIC_ROOT') || 'huerto/casa';
    setTimeout(() => node.send([null, null, null, null, null, { topic: root + '/' + device + '/command', qos: 1, retain: false,
        payload: JSON.stringify({ cmd: 'GET_HISTORY', id: 'srv-hist-' + Date.now().toString(36), ts: Math.floor(Date.now() / 1000) }) }]), 4000);
}
return [out1, out2, out3, out4, out5, null];
