// IA (servidor): guarda cada hora la predicción "humedad dentro de 1 h" de cada
// dispositivo y después la compara con la lectura real (error de predicción).
// Así se puede comparar el modelo por versión, estación, cultivo y etapa.
const now = Math.floor(Date.now() / 1000);
const devs = global.get('devices') || {};
const W = [];
const hourKey = Math.floor(now / 3600);
const done = context.get('done') || {};
const season = (m) => (m === 12 || m <= 2) ? 'invierno' : (m <= 5 ? 'primavera' : (m <= 8 ? 'verano' : 'otono'));
const month = new Date(Date.now() - 6 * 3600 * 1000).getUTCMonth() + 1;
for (const [id, d] of Object.entries(devs)) {
    const ia = d.ia || {};
    const plan = ia.plan || {};
    const fresh = d.last_seen && now - d.last_seen < 600;
    if (!fresh || typeof plan.pred_next_hour_vwc !== 'number') continue;
    if (done[id] === hourKey) continue;
    done[id] = hourKey;
    W.push({ topic: 'INSERT OR IGNORE INTO predictions(device,ts_made,ts_target,predicted_vwc,model_version,ia_status,crop,stage,season,simulated) ' +
        'VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)',
        payload: [id, now, now + 3600, plan.pred_next_hour_vwc, ia.model_version || 0, ia.status || null,
            (d.state || {}).crop || null, (d.state || {}).stage || null, season(month), d.simulated ? 1 : 0] });
}
context.set('done', done);
// Completa las predicciones vencidas con la lectura real más cercana (±10 min)
W.push({ topic: 'UPDATE predictions SET actual_vwc = (SELECT r.vwc FROM readings r WHERE r.device = predictions.device ' +
    'AND r.vwc IS NOT NULL AND r.ts BETWEEN predictions.ts_target - 600 AND predictions.ts_target + 600 ' +
    'ORDER BY ABS(r.ts - predictions.ts_target) LIMIT 1) WHERE actual_vwc IS NULL AND ts_target < $1', payload: [now - 600] });
W.push({ topic: 'UPDATE predictions SET error = actual_vwc - predicted_vwc WHERE error IS NULL AND actual_vwc IS NOT NULL', payload: [] });
return [W];
