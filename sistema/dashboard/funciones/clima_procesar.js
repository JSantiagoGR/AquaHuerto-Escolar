// OPEN-METEO (servidor): procesa la respuesta, la guarda en SQLite y calcula
// lluvia reciente/prevista, ET0 del día y horas recomendadas para regar.
// Son datos de MODELO meteorológico (no mediciones locales).
const now = Math.floor(Date.now() / 1000);
const W = [];
const prev = global.get('server_weather') || {};
const fail = (err) => {
    const sw = Object.assign({}, prev, { ok: false, last_error: err, last_try: now, fail_count: (prev.fail_count || 0) + 1 });
    sw.fresh = !!(sw.ts_fetch && now - sw.ts_fetch < 3 * 3600);
    global.set('server_weather', sw);
    W.push({ topic: 'INSERT OR IGNORE INTO weather_fetches(ts_fetch,origin,lat,lon,ok,http,error) VALUES($1,$2,$3,$4,0,$5,$6)',
        payload: [now, 'servidor', msg.loc.lat, msg.loc.lon, msg.statusCode || 0, String(err).slice(0, 200)] });
    return [W, { topic: 'refresh' }, { topic: 'alert', payload: { code: 'WEATHER_ERROR', severity: 'WARNING',
        message: 'No se pudo consultar Open-Meteo (' + err + '). Se mantiene la operacion local; ' +
        (sw.fresh ? 'el pronostico anterior sigue vigente.' : 'NO hay pronostico vigente.') } }];
};
if (msg.statusCode !== 200) return fail('HTTP ' + (msg.statusCode || 'sin respuesta') + (msg.error ? ' ' + msg.error : ''));
let d = msg.payload;
if (typeof d === 'string') { try { d = JSON.parse(d); } catch (e) { return fail('JSON invalido'); } }
if (!d || !d.hourly || !d.current) return fail('respuesta inesperada');

const H = d.hourly, D = d.daily || {};
const hourly = H.time.map((t, i) => ({ t, temp: H.temperature_2m[i], rh: H.relative_humidity_2m[i],
    pprob: H.precipitation_probability[i], precip: H.precipitation[i], vpd: H.vapour_pressure_deficit[i],
    et0: H.et0_fao_evapotranspiration[i] }));
const daily = (D.time || []).map((t, i) => ({ t, date: new Date((t + d.utc_offset_seconds) * 1000).toISOString().slice(0, 10),
    tmax: D.temperature_2m_max[i], tmin: D.temperature_2m_min[i], precip: D.precipitation_sum[i],
    pprob: D.precipitation_probability_max[i], et0: D.et0_fao_evapotranspiration[i] }));
const sum = (arr) => arr.reduce((a, x) => a + (typeof x === 'number' ? x : 0), 0);
const past24 = hourly.filter(h => h.t <= now && h.t > now - 86400);
const next24 = hourly.filter(h => h.t > now && h.t <= now + 86400);
const todayLocal = new Date((now + d.utc_offset_seconds) * 1000).toISOString().slice(0, 10);
const today = daily.find(x => x.date === todayLocal) || {};
// Horas recomendadas: en los horarios preferidos (06-09 y 18-20) con menor VPD y sin lluvia probable
const hourLocal = (t) => new Date((t + d.utc_offset_seconds) * 1000).getUTCHours();
const cand = next24.filter(h => { const hh = hourLocal(h.t); return (hh >= 6 && hh < 9) || (hh >= 18 && hh < 20); })
    .filter(h => (h.pprob || 0) < 50).sort((a, b) => (a.vpd || 9) - (b.vpd || 9)).slice(0, 3)
    .map(h => ({ t: h.t, hour: hourLocal(h.t), vpd: h.vpd, temp: h.temp }));
const sw = {
    ok: true, fresh: true, ts_fetch: now, last_try: now, source: 'Open-Meteo (modelo meteorologico)',
    lat: d.latitude, lon: d.longitude, elevation: d.elevation, timezone: d.timezone, utc_offset: d.utc_offset_seconds,
    current: { t: d.current.time, temp: d.current.temperature_2m, rh: d.current.relative_humidity_2m,
        precip: d.current.precipitation, rain: d.current.rain, code: d.current.weather_code },
    hourly: hourly.filter(h => h.t > now - 6 * 3600 && h.t <= now + 48 * 3600),
    daily,
    past24h_precip_mm: Math.round(sum(past24.map(h => h.precip)) * 10) / 10,
    next24h_precip_mm: Math.round(sum(next24.map(h => h.precip)) * 10) / 10,
    next24h_prob_max: Math.max(0, ...next24.map(h => h.pprob || 0)),
    et0_today_mm: today.et0, recommended: cand, fail_count: prev.fail_count || 0, ok_count: (prev.ok_count || 0) + 1
};
global.set('server_weather', sw);
// Temperatura media diaria para grados-día (modelo, no medición local)
const tdaily = global.get('tdaily', 'file') || {};
for (const x of daily) if (x.date <= todayLocal && typeof x.tmax === 'number') tdaily[x.date] = { tmax: x.tmax, tmin: x.tmin, src: 'open-meteo' };
global.set('tdaily', tdaily, 'file');

W.push({ topic: 'INSERT OR IGNORE INTO weather_fetches(ts_fetch,origin,lat,lon,ok,http,temp_c,rh_pct,precip_mm,rain_mm,weather_code,' +
    'past24h_precip_mm,next24h_precip_mm,next24h_prob_max,et0_today_mm) VALUES($1,$2,$3,$4,1,200,$5,$6,$7,$8,$9,$10,$11,$12,$13)',
    payload: [now, 'servidor', sw.lat, sw.lon, sw.current.temp, sw.current.rh, sw.current.precip, sw.current.rain, sw.current.code,
        sw.past24h_precip_mm, sw.next24h_precip_mm, sw.next24h_prob_max, sw.et0_today_mm ?? null] });
for (const h of hourly) W.push({ topic: 'INSERT OR IGNORE INTO forecast_hourly(ts_fetch,time,temp_c,rh_pct,precip_prob,precip_mm,vpd_kpa,et0_mm) VALUES($1,$2,$3,$4,$5,$6,$7,$8)',
    payload: [now, h.t, h.temp, h.rh, h.pprob, h.precip, h.vpd, h.et0] });
for (const x of daily) W.push({ topic: 'INSERT OR IGNORE INTO forecast_daily(ts_fetch,date,tmax_c,tmin_c,precip_mm,precip_prob_max,et0_mm) VALUES($1,$2,$3,$4,$5,$6,$7)',
    payload: [now, x.date, x.tmax, x.tmin, x.precip, x.pprob, x.et0] });
return [W, { topic: 'refresh' }, { topic: 'alert', payload: { code: 'WEATHER_STALE', resolve: 'WEATHER_STALE', severity: 'INFO' } }];
