// ALERTAS: registra en SQLite, mantiene la lista reciente y notifica las importantes
const a = msg.payload || {};
const now = Math.floor(Date.now() / 1000);
const recent = global.get('alerts_recent') || [];
const device = msg.device || a.device || 'servidor';
const NAMES = {
    NO_FLOW: 'Ausencia de flujo', FLOW_HIGH: 'Caudal anormal', PUMP_TIMEOUT: 'Bomba demasiado tiempo encendida',
    SAFETY_TRIP: 'Corte del supervisor de seguridad', FLOW_WHEN_IDLE: 'Flujo con todo apagado',
    SOIL_NO_RESPONSE: 'El suelo no responde al riego', REBOOT_DURING_WATERING: 'Reinicio durante un riego',
    CONFIG_RESET: 'Configuracion restaurada', SOIL_SENSOR: 'Fallo del sensor de humedad (EC-5)',
    TANK_SENSOR: 'Fallo del sensor de nivel', TANK_LOW: 'Nivel bajo del tinaco', ENV_SENSOR: 'Fallo del sensor ambiental',
    TIME_INVALID: 'Hora no sincronizada', DAILY_LIMIT: 'Limite diario de litros', COMMS: 'Sin Wi-Fi/MQTT en el ESP32',
    DEVICE_OFFLINE: 'Perdida de conexion MQTT', HUM_CRITICAL: 'Humedad critica', HUM_EXCESS: 'Humedad excesiva',
    WEATHER_STALE: 'Pronostico vencido', POSIBLE_LLUVIA: 'Posible lluvia', POSIBLE_RIEGO_EXTERNO: 'Posible riego externo',
    AUMENTO_NO_EXPLICADO: 'Aumento de humedad no explicado', POSIBLE_ERROR_SENSOR: 'Posible error del sensor',
    IA_PREDICTION_ERROR: 'Error del modelo IA', IA_CHANGE_DETECTED: 'Cambio detectado por la IA',
    STAGE_CHANGE: 'Cambio de etapa', STAGE_RECOMMENDED: 'Cambio de etapa recomendado', STORAGE_ERROR: 'Problema de almacenamiento',
    BROKER_DOWN: 'Broker MQTT no disponible', OFFLINE_BUFFER: 'Datos recuperados del bufer'
};
// Resolución de una alerta previa (p. ej. dispositivo de nuevo en línea)
if (a.resolve || a.active === false) {
    const code = a.resolve || a.code;
    let changed = false;
    for (const r of recent) if (r.code === code && r.device === device && r.active) { r.active = false; changed = true; }
    global.set('alerts_recent', recent);
    if (a.severity === 'INFO' && !a.fromDevice) return [ { topic: 'UPDATE alerts SET active=0 WHERE code=$1 AND device=$2 AND active=1', payload: [code, device] }, null, { topic: 'refresh' }];
    return [{ topic: 'UPDATE alerts SET active=0 WHERE code=$1 AND device=$2 AND active=1', payload: [code, device] }, null, changed ? { topic: 'refresh' } : null];
}
// Evita repetir la misma alerta activa
const dup = recent.find(r => r.code === a.code && r.device === device && r.active && now - r.ts < 600);
if (dup) return null;
const item = { ts: now, device, code: a.code, name: NAMES[a.code] || a.code, severity: a.severity || 'INFO',
    message: a.message || '', active: true, simulated: !!msg.simulated };
recent.unshift(item);
if (recent.length > 200) recent.length = 200;
global.set('alerts_recent', recent);
const db = { topic: 'INSERT INTO alerts(ts,device,code,severity,message,active,source,simulated) VALUES($1,$2,$3,$4,$5,1,$6,$7)',
    payload: [now, device, a.code, item.severity, item.message, a.fromDevice ? 'dispositivo' : 'servidor', item.simulated ? 1 : 0] };
let notif = null;
if (item.severity !== 'INFO' || ['STAGE_CHANGE', 'STAGE_RECOMMENDED'].includes(a.code)) {
    notif = { payload: (item.simulated ? '[SIMULADO] ' : '') + item.name + ': ' + item.message,
        ui_update: { color: item.severity === 'CRITICAL' ? 'red' : (item.severity === 'WARNING' ? 'orange' : 'blue'), displayTime: 8 } };
}
return [db, notif, { topic: 'refresh' }];
