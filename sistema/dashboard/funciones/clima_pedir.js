// OPEN-METEO (servidor): arma la consulta HTTPS con la ubicación configurada.
// Respeta el uso gratuito no comercial: una consulta cada 30 min (más las manuales,
// limitadas a 1 por minuto). TLS con verificación normal de certificados.
const loc = global.get('location', 'file') || { lat: 28.659830, lon: -106.074051 };
const last = context.get('last') || 0;
if (msg.topic === 'weather_refresh' && Date.now() - last < 60000) return null;
context.set('last', Date.now());
const url = 'https://api.open-meteo.com/v1/forecast?latitude=' + loc.lat.toFixed(4) + '&longitude=' + loc.lon.toFixed(4) +
    '&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code' +
    '&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,vapour_pressure_deficit,et0_fao_evapotranspiration' +
    '&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,et0_fao_evapotranspiration' +
    '&past_days=7&forecast_days=3&timeformat=unixtime&timezone=auto';
return { url, loc, ts_request: Math.floor(Date.now() / 1000) };
