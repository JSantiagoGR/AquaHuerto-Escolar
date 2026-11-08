// Lista los respaldos existentes para la página CONFIGURACIÓN
const fs = global.get('fs'), path = global.get('path');
const dir = path.join(env.get('RIEGO_BACKUPS'), 'db');
let list = [];
try {
    list = fs.readdirSync(dir).filter(f => f.endsWith('.db')).map(f => {
        const st = fs.statSync(path.join(dir, f));
        return { file: f, kb: Math.round(st.size / 1024), ts: Math.floor(st.mtimeMs / 1000) };
    }).sort((a, b) => b.ts - a.ts).slice(0, 30);
    global.set('db_ok', true);
} catch (e) { list = []; }
global.set('backups', list);
const notif = msg._backup ? { payload: 'Respaldo creado: ' + path.basename(msg._backup), ui_update: { color: 'green' } } : null;
return [{ topic: 'refresh' }, notif];
