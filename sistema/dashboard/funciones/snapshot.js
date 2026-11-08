// ESTADO PARA EL DASHBOARD: arma una "foto" del dispositivo seleccionado y la
// envía a todas las páginas (máximo ~1 vez por segundo).
function build() {

const now = Math.floor(Date.now() / 1000);
const devs = global.get('devices') || {};
let sel = global.get('selected_device', 'file') || 'esp32_01';
const d = devs[sel] || { id: sel };
const list = Object.keys(devs).sort().map(k => ({
    id: k, simulated: !!devs[k].simulated || k.startsWith('sim'),
    online: !!(devs[k].status && devs[k].status.online) && (now - (devs[k].last_seen || 0) < 120),
    last_seen: devs[k].last_seen || null }));
if (!list.find(x => x.id === sel)) list.push({ id: sel, simulated: sel.startsWith('sim'), online: false, last_seen: null });

// Historial de 24 h reducido a ~300 puntos
const h = d.hist || [];
const step = Math.max(1, Math.ceil(h.length / 300));
const hist = h.filter((_, i) => i % step === 0 || i === h.length - 1);

const online = !!(d.status && d.status.online) && (now - (d.last_seen || 0) < 120);
const snap = {
    server_time: now,
    env: env.get('RIEGO_ENV') || 'casa',
    device: sel,
    devices: list,
    prev_mode: (global.get('prev_mode', 'file') || {})[sel] || null,
    simulated: !!d.simulated || sel.startsWith('sim'),
    online,
    last_seen: d.last_seen || null,
    broker: global.get('broker_status') || { connected: false },
    status: d.status || null,
    telemetry: d.telemetry || null,
    state: d.state || null,
    config: (d.config && d.config.params) ? d.config.params : null,
    profile_version: d.config ? d.config.profile_version : null,
    decision: d.decision || null,
    decisions: d.dec_hist || [],
    ia: d.ia || null,
    weather_dev: d.weather || null,
    diag: d.diag || null,
    weather: global.get('server_weather') || null,
    alerts: (global.get('alerts_recent') || []).filter(a => a.device === sel || a.device === 'servidor').slice(0, 30),
    growth: global.get('growth') || null,
    soil_cal: global.get('soil_cal', 'file') || null,
    bed: global.get('bed', 'file') || null,
    location: global.get('location', 'file') || { lat: 28.659830, lon: -106.074051, label: 'Esc. Prim. Fed. Belisario Domínguez (huerto)' },
    hist24: hist,
    last_cmd: global.get('last_cmd_result') || null,
    backups: global.get('backups') || [],
    db_ok: global.get('db_ok') !== false,
    db_stats: global.get('db_stats') || null
};
return { topic: 'snapshot', payload: snap };
}

const MIN_MS = 800;
const last = context.get('last') || 0;
const nowMs = Date.now();
if (nowMs - last < MIN_MS) {
    if (!context.get('scheduled')) {
        context.set('scheduled', true);
        setTimeout(() => { context.set('scheduled', false); context.set('last', Date.now()); node.send(build()); }, MIN_MS);
    }
    return null;
}
context.set('last', nowMs);
return build();
