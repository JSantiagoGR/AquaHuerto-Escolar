// SEGUIMIENTO DE CRECIMIENTO (estimación por calendario FAO-56 + grados-día)
// Los sensores NO pueden confirmar floración ni fructificación: todo cambio
// automático es una ESTIMACIÓN que el usuario puede corregir.
//  MANUAL     -> solo informa la etapa estimada.
//  AUTOMATICO -> recomienda el cambio y pide confirmación.
//  IA         -> actualiza la etapa (si no está bloqueada), notifica y permite corregir.
// Salidas: 1) escrituras SQLite  2) refrescar  3) alertas  4) solicitud (aplicar perfil)
const plantings = global.get('plantings_cache') || [];
const tdaily = global.get('tdaily', 'file') || {};
const stats = global.get('stage_history') || [];
const devs = global.get('devices') || {};
const sel = global.get('selected_device', 'file') || 'esp32_01';
const mode = ((devs[sel] || {}).state || {}).mode || 'MANUAL';
const now = Math.floor(Date.now() / 1000);
const DAY = 86400;
const today = new Date(Date.now() - 6 * 3600 * 1000).toISOString().slice(0, 10);   // hora de Chihuahua (UTC-6)
const toDays = (a, b) => Math.floor((Date.parse(b) - Date.parse(a)) / (DAY * 1000));
const W = [], A = [], R = [];
const notified = context.get('notified') || {};

// Correcciones del usuario -> duración observada por cultivo/etapa (mejora la estimación)
function observedDays(cropId, idx) {
    const v = stats.filter(s => s.from_stage === idx && s.days_in_stage > 0 &&
        ['manual', 'correccion', 'recomendacion_confirmada'].includes(s.source) &&
        (plantings.find(p => p.id === s.planting_id) || {}).crop_id === cropId).map(s => s.days_in_stage);
    return v.length ? { n: v.length, avg: v.reduce((a, b) => a + b, 0) / v.length } : null;
}

function gddBetween(from, to, base) {
    let g = 0, n = 0, missing = 0;
    for (let t = Date.parse(from); t <= Date.parse(to); t += DAY * 1000) {
        const k = new Date(t).toISOString().slice(0, 10);
        const x = tdaily[k];
        if (x && typeof x.tmax === 'number') { g += Math.max(0, (x.tmax + x.tmin) / 2 - base); n++; } else missing++;
    }
    return { gdd: Math.round(g), days_with_data: n, days_missing: missing };
}

const items = [];
for (const p of plantings.filter(x => x.active)) {
    const pdev = p.device || sel;
    const pmode = ((devs[pdev] || {}).state || {}).mode || 'MANUAL';
    const c = p.crop || {};
    const st = c.etapas || [];
    if (!st.length) continue;
    const ref = p.sow_date || p.transplant_date;
    const elapsed = Math.max(0, toDays(ref, today));
    const est = st.map((s, i) => { const o = observedDays(p.crop_id, i);
        return o ? Math.round((s.dias + o.avg * o.n) / (1 + o.n)) : s.dias; });
    let acc = 0, estIdx = st.length - 1;
    for (let i = 0; i < st.length; i++) { acc += est[i]; if (elapsed < acc) { estIdx = i; break; } }
    const cur = Math.min(p.stage_index || 0, st.length - 1);
    const stageStart = p.stage_start || ref;
    const inStage = Math.max(0, toDays(stageStart, today));
    const remainingStage = Math.max(0, est[cur] - inStage);
    const remainingAfter = est.slice(cur + 1).reduce((a, b) => a + b, 0);
    const harvest = new Date(Date.parse(today) + (remainingStage + remainingAfter) * DAY * 1000).toISOString().slice(0, 10);
    const base = (c.gdd && typeof c.gdd.base_c === 'number') ? c.gdd.base_c : null;
    const g = base !== null ? gddBetween(ref, today, base) : null;
    const gs = base !== null ? gddBetween(stageStart, today, base) : null;
    const total = est.reduce((a, b) => a + b, 0);
    const it = {
        id: p.id, device: pdev, crop_id: p.crop_id, crop_name: c.nombre || p.crop_id, variety: p.variety, sow_date: p.sow_date,
        transplant_date: p.transplant_date, stage_index: cur, stage_name: (st[cur] || {}).nombre, n_stages: st.length,
        stages: st.map((s, i) => ({ nombre: s.nombre, dias_fao: s.dias, dias_estimados: est[i], kc: s.kc })),
        estimated_index: estIdx, estimated_name: (st[estIdx] || {}).nombre, elapsed_days: elapsed,
        days_in_stage: inStage, stage_days: est[cur], remaining_stage_days: remainingStage,
        remaining_weeks: Math.round((remainingStage + remainingAfter) / 7 * 10) / 10,
        next_stage: cur + 1 < st.length ? st[cur + 1].nombre : 'Cosecha / fin del ciclo',
        harvest_date: harvest, progress_pct: Math.min(100, Math.round(elapsed / total * 100)),
        stage_progress_pct: Math.min(100, Math.round(inStage / Math.max(1, est[cur]) * 100)),
        gdd: g, gdd_in_stage: gs ? gs.gdd : null, gdd_base: base, locked: !!p.stage_locked, mode: pmode,
        estimate_note: 'Estimacion por calendario FAO-56' + (est.some((e, i) => e !== st[i].dias) ? ' ajustada con correcciones del usuario' : '') +
            (base !== null ? '; grados-dia con temperatura del aire de Open-Meteo (no es la temperatura de la planta)' : '')
    };
    items.push(it);
    // IA: si nadie cambió la etapa, pasa a la SIGUIENTE solo cuando ya se cumplió el tiempo de la actual
    // (un cambio manual reinicia stage_start, así que se respeta).
    const sig = cur + 1;
    if (pmode === 'IA' && !p.stage_locked && sig < st.length && inStage >= est[cur]) {
        W.push({ topic: 'UPDATE plantings SET stage_index=$1, stage_start=$2, updated=$3 WHERE id=$4', payload: [sig, today, now, p.id] });
        W.push({ topic: 'INSERT INTO stage_changes(planting_id,ts,from_stage,to_stage,source,estimated,confirmed,note,days_in_stage,gdd_in_stage) VALUES($1,$2,$3,$4,$5,1,0,$6,$7,$8)',
            payload: [p.id, now, cur, sig, 'ia_auto', 'Tiempo de la etapa cumplido (modo IA)', inStage, gs ? gs.gdd : null] });
        A.push({ code: 'STAGE_CHANGE', severity: 'INFO', message: (c.nombre || '') + ': se cumplieron ' + inStage + ' dias de "' + st[cur].nombre +
            '"; etapa cambiada a "' + st[sig].nombre + '" (modo IA). Puede corregirla en CRECIMIENTO.' });
        R.push({ topic: 'req', payload: { type: 'apply_crop', crop_id: p.crop_id, stage_index: sig, device: pdev } });
        p.stage_index = sig; p.stage_start = today;
    } else if (estIdx > cur) {
        const key = p.id + ':' + estIdx;
        if (pmode === 'AUTOMATICO' && !notified[key]) {
            notified[key] = now;
            A.push({ code: 'STAGE_RECOMMENDED', severity: 'INFO', message: (c.nombre || '') + ': por calendario la etapa probable es "' +
                st[estIdx].nombre + '". Confirme el cambio en CRECIMIENTO.' });
        }
    }
}
context.set('notified', notified);
global.set('growth', { ts: now, mode, items });
return [W.length ? W : null, { topic: 'refresh' }, A.length ? A.map(a => ({ topic: 'alert', payload: a })) : null, R.length ? R : null];
