// RESPALDO: copia consistente de SQLite (VACUUM INTO) + copia de flujos y ajustes.
// Los respaldos se conservan (no se borran automáticamente).
const fs = global.get('fs'), path = global.get('path');
const dir = env.get('RIEGO_BACKUPS');
const stamp = new Date(Date.now() - 6 * 3600 * 1000).toISOString().replace(/[-:]/g, '').replace('T', '_').slice(0, 15);
const dbDir = path.join(dir, 'db');
const flowDir = path.join(dir, 'nodered');
try {
    fs.mkdirSync(dbDir, { recursive: true });
    fs.mkdirSync(flowDir, { recursive: true });
    const userDir = path.join(env.get('RIEGO_PROJECT'), 'nodered', 'userdata');
    for (const f of ['flows_riego.json', 'package.json']) {
        const src = path.join(userDir, f);
        if (fs.existsSync(src)) fs.copyFileSync(src, path.join(flowDir, stamp + '_' + f));
    }
    // Contexto persistente (cultivo seleccionado, calibración del suelo, ubicación)
    const ctx = path.join(userDir, 'context', 'global', 'global.json');
    if (fs.existsSync(ctx)) fs.copyFileSync(ctx, path.join(flowDir, stamp + '_context_global.json'));
} catch (e) {
    node.error('Respaldo de flujos: ' + e.message);
}
const target = path.join(dbDir, 'riego_' + stamp + '.db').replace(/\\/g, '/').replace(/'/g, "''");
global.set('backup_last', { ts: Math.floor(Date.now() / 1000), file: target });
// VACUUM INTO no admite parámetros: la ruta la arma el servidor (sin datos del usuario)
return { topic: "VACUUM INTO '" + target + "'", payload: [], _backup: target };
