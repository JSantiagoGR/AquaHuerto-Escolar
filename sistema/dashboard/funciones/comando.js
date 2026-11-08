// COMANDOS DEL DASHBOARD -> ESP32 (o simulador)
// Entrada: msg.payload = { cmd, ...campos, device? , _ui:{label} }
// Salidas: 1) MQTT (retain=false, QoS 1)  2) resultado al dashboard  3) SQLite
// El éxito SOLO se informa cuando llega el ACK real del dispositivo (acks.js).
const ALLOWED = ['GET_STATUS', 'GET_CONFIG', 'GET_HISTORY', 'GET_IA', 'NET_DIAG', 'WEATHER_REFRESH',
    'START_MANUAL', 'START_TO_TARGET', 'STOP', 'SET_MODE', 'APPLY_CONFIG', 'APPLY_PROFILE',
    'SET_BROKER', 'IA_RESET', 'CLEAR_ALARM', 'SET_FLOW_CALIBRATION', 'SET_TANK_CALIBRATION', 'SET_SCHEDULE', 'SIM_CONTROL'];
const TIMEOUT_MS = 12000;
const root = env.get('RIEGO_TOPIC_ROOT') || 'huerto/casa';
const p = Object.assign({}, msg.payload || {});
const device = p.device || global.get('selected_device', 'file') || 'esp32_01';
delete p.device;
const ui = p._ui || {};
delete p._ui;

if (!ALLOWED.includes(p.cmd)) {
    return [null, { topic: 'cmd_result', payload: { status: 'INVALID', cmd: p.cmd, message: 'Comando no permitido desde el dashboard' } }, null];
}
if (p.cmd === 'SIM_CONTROL' && !device.startsWith('sim')) {
    return [null, { topic: 'cmd_result', payload: { status: 'REJECTED', cmd: p.cmd, message: 'Los controles de simulacion solo se envian al simulador' } }, null];
}
if (p.cmd === 'SET_MODE') {
    // Se recuerda el modo anterior cuando se pasa a MANUAL para un riego a mano (aviso para regresar); otro cambio lo olvida
    const pm = global.get('prev_mode', 'file') || {};
    if (p.mode === 'MANUAL' && ['AUTOMATICO', 'IA'].includes(p.from_mode)) pm[device] = p.from_mode; else delete pm[device];
    global.set('prev_mode', pm, 'file');
    delete p.from_mode;
}
const devs = global.get('devices') || {};
const d = devs[device];
const online = d && d.status && d.status.online && (Date.now() / 1000 - (d.last_seen || 0) < 120);
const id = 'ui-' + Date.now().toString(36) + '-' + Math.floor(Math.random() * 1e6).toString(36);
p.id = id;
p.ts = Math.floor(Date.now() / 1000);

const pend = global.get('pending') || {};
pend[id] = { id, device, cmd: p.cmd, ts: Date.now(), label: ui.label || p.cmd, version: p.version || null };
global.set('pending', pend);

const dbmsgs = [];
if (['APPLY_CONFIG', 'APPLY_PROFILE', 'SET_MODE', 'SET_BROKER', 'IA_RESET'].includes(p.cmd)) {
    const safe = Object.assign({}, p);
    if (safe.pass) safe.pass = '********';
    dbmsgs.push({ topic: 'INSERT OR IGNORE INTO config_changes(device,ts,txn,cmd,version,status,message,params) VALUES($1,$2,$3,$4,$5,$6,$7,$8)',
        payload: [device, p.ts, id, p.cmd, p.version || null, 'ENVIADO', online ? '' : 'Dispositivo sin conexion', JSON.stringify(safe.params || safe)] });
}

// Vencimiento: si no hay ACK se informa y la configuración anterior se conserva
setTimeout(() => {
    const pp = global.get('pending') || {};
    if (pp[id]) {
        delete pp[id];
        global.set('pending', pp);
        node.send([null,
            { topic: 'cmd_result', payload: { id, device, cmd: p.cmd, label: ui.label || p.cmd, status: 'TIMEOUT',
                message: 'Sin confirmacion del dispositivo en ' + (TIMEOUT_MS / 1000) + ' s. No se aplico ningun cambio (se mantiene lo anterior).' } },
            { topic: 'UPDATE config_changes SET status=$1, message=$2 WHERE txn=$3', payload: ['TIMEOUT', 'Sin ACK', id] }]);
    }
}, TIMEOUT_MS);

const out = { topic: root + '/' + device + '/command', payload: JSON.stringify(p), qos: 1, retain: false };
const pending = { topic: 'cmd_result', payload: { id, device, cmd: p.cmd, label: ui.label || p.cmd, status: 'SENDING',
    message: online ? 'Enviado; esperando confirmacion del dispositivo...' : 'El dispositivo aparece desconectado; se espera confirmacion...' } };
return [out, pending, dbmsgs.length ? dbmsgs : null];
