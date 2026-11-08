// ACK del dispositivo -> resultado real en el dashboard + registro en SQLite
const a = msg.payload || {};
const pend = global.get('pending') || {};
const p = pend[a.id];
if (!p) return null;                         // ACK de otro cliente o ya vencido
if (a.status === 'PENDING') {                 // p. ej. SET_BROKER: confirmación posterior
    return [{ topic: 'cmd_result', payload: { id: a.id, device: msg.device, cmd: a.cmd, label: p.label, status: 'PENDING', message: a.message } }, null];
}
delete pend[a.id];
global.set('pending', pend);
const res = { id: a.id, device: msg.device, cmd: a.cmd, label: p.label, status: a.status, message: a.message,
    mode_applied: a.mode_applied, version_applied: a.version_applied, txn: a.txn, ms: Date.now() - p.ts };
const db = { topic: 'UPDATE config_changes SET status=$1, message=$2, ack_ts=$3 WHERE txn=$4',
    payload: [a.status, a.message || '', Math.floor(Date.now() / 1000), a.id] };
const extra = [];
if (a.status === 'OK' && (a.cmd === 'APPLY_PROFILE' || a.cmd === 'APPLY_CONFIG') && p.version) {
    extra.push({ topic: 'INSERT INTO crop_changes(device,ts,crop_id,stage,version,source) VALUES($1,$2,$3,$4,$5,$6)',
        payload: [msg.device, Math.floor(Date.now() / 1000), (global.get('last_profile') || {}).crop_id || null,
            (global.get('last_profile') || {}).stage || null, p.version, a.cmd] });
}
return [{ topic: 'cmd_result', payload: res }, [db].concat(extra)];
