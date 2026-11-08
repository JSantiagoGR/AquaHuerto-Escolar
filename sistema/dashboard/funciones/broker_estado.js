// Estado de la conexión de Node-RED con el broker (nodo "status" del MQTT in).
// Solo alerta si la desconexión dura más de 30 s (evita falsas alarmas al redesplegar).
const st = msg.status || {};
const txt = String(st.text || '');
const connected = /connected/i.test(txt) && !/disconnected|connecting/i.test(txt);
const prev = global.get('broker_status') || {};
const now = Math.floor(Date.now() / 1000);
global.set('broker_status', { connected, text: txt, ts: now, since: connected === prev.connected ? (prev.since || now) : now });
const t = context.get('timer');
if (t) { clearTimeout(t); context.set('timer', null); }
if (!connected) {
    context.set('timer', setTimeout(() => {
        const b = global.get('broker_status') || {};
        if (!b.connected) {
            context.set('alerted', true);
            node.send([null, { topic: 'alert', device: 'servidor', payload: { code: 'BROKER_DOWN', severity: 'CRITICAL',
                message: 'Node-RED no tiene conexion con el broker MQTT desde hace mas de 30 s (' + b.text + '). Los ESP32 siguen operando con sus protecciones locales.' } }]);
        }
    }, 30000));
    return [{ topic: 'refresh' }, null];
}
if (context.get('alerted')) {
    context.set('alerted', false);
    return [{ topic: 'refresh' }, { topic: 'alert', device: 'servidor', payload: { code: 'BROKER_DOWN', resolve: 'BROKER_DOWN', severity: 'INFO' } }];
}
return [{ topic: 'refresh' }, null];
