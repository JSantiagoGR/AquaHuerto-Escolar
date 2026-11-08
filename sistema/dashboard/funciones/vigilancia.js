// VIGILANCIA PERIÓDICA (cada minuto): dispositivo sin datos, pronóstico vencido,
// humedad crítica o excesiva respecto a los umbrales vigentes del ESP32.
const now = Math.floor(Date.now() / 1000);
const devs = global.get('devices') || {};
const A = [];
const flags = context.get('flags') || {};
const raise = (key, a, on) => {
    if (on && !flags[key]) { flags[key] = true; A.push(a); }
    else if (!on && flags[key]) { flags[key] = false; A.push(Object.assign({}, a, { resolve: a.payload.code, payload: Object.assign({}, a.payload, { resolve: a.payload.code, severity: 'INFO' }) })); }
};
for (const [id, d] of Object.entries(devs)) {
    const age = now - (d.last_seen || 0);
    raise(id + ':silent', { topic: 'alert', device: id, simulated: d.simulated ? 1 : 0, payload: { code: 'DEVICE_OFFLINE', severity: 'CRITICAL',
        message: id + ' no envia datos desde hace ' + Math.round(age / 60) + ' min' } }, d.last_seen && age > 180);
    const t = d.telemetry || {}, c = (d.config || {}).params || {};
    const v = t.soil && t.soil.valid ? t.soil.vwc_pct : null;
    if (typeof v === 'number' && typeof c.hum_critical === 'number') {
        raise(id + ':crit', { topic: 'alert', device: id, simulated: d.simulated ? 1 : 0, payload: { code: 'HUM_CRITICAL', severity: 'CRITICAL',
            message: 'Humedad ' + v.toFixed(1) + ' %VWC bajo el umbral de emergencia (' + c.hum_critical + ')' } }, v < c.hum_critical);
        raise(id + ':wet', { topic: 'alert', device: id, simulated: d.simulated ? 1 : 0, payload: { code: 'HUM_EXCESS', severity: 'WARNING',
            message: 'Humedad ' + v.toFixed(1) + ' %VWC sobre la maxima (' + c.hum_max + ')' } }, v >= c.hum_max);
    }
}
const sw = global.get('server_weather');
if (sw && sw.ts_fetch) {
    sw.fresh = now - sw.ts_fetch < 3 * 3600;
    raise('wx:stale', { topic: 'alert', device: 'servidor', payload: { code: 'WEATHER_STALE', severity: 'WARNING',
        message: 'El pronostico tiene mas de 3 h: no se usa para decidir hasta actualizarlo' } }, !sw.fresh);
}
context.set('flags', flags);
return [A.length ? A : null, { topic: 'refresh' }];
