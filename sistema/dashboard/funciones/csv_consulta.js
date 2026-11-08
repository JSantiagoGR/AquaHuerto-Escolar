// EXPORTACIÓN CSV (GET /riego/export.csv?tipo=lecturas|riegos|alertas&desde=AAAA-MM-DD&hasta=AAAA-MM-DD&device=esp32_01)
// Protegida con la misma autenticación del dashboard.
const qy = msg.req.query || {};
const toTs = (s, end) => { const t = Date.parse(String(s || '') + (end ? 'T23:59:59-06:00' : 'T00:00:00-06:00')); return isFinite(t) ? Math.floor(t / 1000) : null; };
const now = Math.floor(Date.now() / 1000);
const from = toTs(qy.desde, false) || now - 30 * 86400;
const to = toTs(qy.hasta, true) || now;
const dev = /^[a-z0-9_]{2,24}$/.test(qy.device || '') ? qy.device : (global.get('selected_device', 'file') || 'esp32_01');
const tipo = ['lecturas', 'riegos', 'alertas', 'predicciones', 'lluvia'].includes(qy.tipo) ? qy.tipo : 'lecturas';
const SQL = {
    lecturas: 'SELECT datetime(ts,\'unixepoch\',\'-6 hours\') AS fecha_local, * FROM readings WHERE device=$1 AND ts BETWEEN $2 AND $3 ORDER BY ts',
    riegos: 'SELECT datetime(ts_start,\'unixepoch\',\'-6 hours\') AS inicio_local, * FROM irrigation_events WHERE device=$1 AND ts_start BETWEEN $2 AND $3 ORDER BY ts_start',
    alertas: 'SELECT datetime(ts,\'unixepoch\',\'-6 hours\') AS fecha_local, * FROM alerts WHERE (device=$1 OR device=\'servidor\') AND ts BETWEEN $2 AND $3 ORDER BY ts',
    predicciones: 'SELECT datetime(ts_target,\'unixepoch\',\'-6 hours\') AS objetivo_local, * FROM predictions WHERE device=$1 AND ts_made BETWEEN $2 AND $3 ORDER BY ts_made',
    lluvia: 'SELECT datetime(ts,\'unixepoch\',\'-6 hours\') AS fecha_local, * FROM rain_events WHERE device=$1 AND ts BETWEEN $2 AND $3 ORDER BY ts'
};
msg.topic = SQL[tipo];
msg.payload = [dev, from, to];
msg.filename = 'riego_' + tipo + '_' + dev + '_' + new Date(from * 1000).toISOString().slice(0, 10) + '_' + new Date(to * 1000).toISOString().slice(0, 10) + '.csv';
return msg;
