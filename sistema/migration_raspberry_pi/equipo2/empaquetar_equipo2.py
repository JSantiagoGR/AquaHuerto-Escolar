"""Arma el paquete de migración de "Equipo 2 Proyecto" para la Raspberry Pi.

Exporta lo que ya funciona en la laptop (sin reconstruir nada):
  - flujo y dashboard generados para el entorno final (mismo código que localhost:1880)
  - base SQLite completa (copia consistente) -> database/riego_final.db
  - contexto persistente (cama, suelo, versión de perfil, clima diario)
  - settings.js, package.json, ACL del broker, scripts sin sudo
El archivo de credenciales NO entra al zip: se copia aparte.

Uso:  python migration_raspberry_pi/equipo2/empaquetar_equipo2.py
"""
import json
import os
import shutil
import sqlite3
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
MIG = os.path.dirname(HERE)
R = os.path.dirname(MIG)
TS = time.strftime('%Y%m%d_%H%M')
OUT = os.path.join(R, 'backups', 'paquete_equipo2_proyecto')
SECRETS = os.path.join(R, 'configs', 'secrets', 'credenciales_final.env')


def cp(src, rel):
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def lf(src, rel):
    """Copia un script de texto con fin de línea LF (Linux)."""
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    data = open(src, 'rb').read().replace(b'\r\n', b'\n')
    open(dst, 'wb').write(data)


if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

# Node-RED
lf(os.path.join(MIG, 'nodered', 'settings.js'), 'nodered/userdata/settings.js')
lf(os.path.join(MIG, 'nodered', 'package.json'), 'nodered/userdata/package.json')
lf(os.path.join(R, 'nodered', 'desplegar_flows.py'), 'nodered/desplegar_flows.py')
cp(os.path.join(R, 'dashboard', 'export', 'flows_riego_final.json'), 'dashboard/export/flows_riego_final.json')

# Contexto persistente: mismo contenido, con el ESP32 del proyecto seleccionado
ctx = json.load(open(os.path.join(R, 'nodered', 'userdata', 'context', 'global', 'global.json'), encoding='utf-8'))
ctx['selected_device'] = 'esp32_principal'
dst = os.path.join(OUT, 'nodered', 'userdata', 'context', 'global', 'global.json')
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump(ctx, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# Base de datos: copia consistente de la base de la laptop
os.makedirs(os.path.join(OUT, 'database'), exist_ok=True)
src = sqlite3.connect(os.path.join(R, 'database', 'riego_casa.db'))
dstdb = sqlite3.connect(os.path.join(OUT, 'database', 'riego_final.db'))
src.backup(dstdb)
dstdb.close()
src.close()
for f in ('schema.sql', 'inicializar_db.py', 'cultivos_base.json', 'generar_cultivos_base.py'):
    lf(os.path.join(R, 'database', f), 'database/' + f)

# Broker propio (la configuración con rutas se genera en la Pi) y scripts
lf(os.path.join(MIG, 'mqtt', 'acl_final.conf'), 'mqtt/acl_final.conf')
for f in sorted(os.listdir(os.path.join(HERE, 'scripts'))):
    lf(os.path.join(HERE, 'scripts', f), 'scripts/' + f)
lf(os.path.join(HERE, 'LEEME.md'), 'LEEME.md')
os.makedirs(os.path.join(OUT, 'configs', 'secrets'), exist_ok=True)
open(os.path.join(OUT, 'configs', 'secrets', 'COPIAR_AQUI_credenciales_final.env.txt'), 'w', encoding='utf-8').write(
    'El archivo credenciales_final.env se copia aparte (no viaja en el zip).\n')

# Verificación: ninguna contraseña del archivo de credenciales dentro del paquete
secret_vals = []
for line in open(SECRETS, encoding='utf-8'):
    if '=' in line and not line.startswith('#'):
        k, v = line.strip().split('=', 1)
        if any(t in k for t in ('PASS', 'SECRET')) and len(v) >= 8:
            secret_vals.append(v.encode())
leaks = []
for root, _, files in os.walk(OUT):
    for f in files:
        data = open(os.path.join(root, f), 'rb').read()
        if any(s in data for s in secret_vals):
            leaks.append(os.path.relpath(os.path.join(root, f), OUT))
if leaks:
    print('ERROR: contraseñas dentro del paquete:', leaks)
    sys.exit(1)

zpath = os.path.join(R, 'backups', 'paquete_equipo2_proyecto_%s.zip' % TS)
n = 0
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(OUT):
        for f in files:
            full = os.path.join(root, f)
            z.write(full, os.path.join('equipo2_proyecto', os.path.relpath(full, OUT)))
            n += 1
db = sqlite3.connect(os.path.join(OUT, 'database', 'riego_final.db'))
tables = db.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
crops = db.execute("SELECT count(*) FROM crops").fetchone()[0]
reads = db.execute("SELECT count(*) FROM readings").fetchone()[0]
db.close()
print('Paquete: %s (%d archivos, %.1f MB) · carpeta %s' % (zpath, n, os.path.getsize(zpath) / 1e6, OUT))
print('Base migrada: %d tablas, %d cultivos, %d lecturas · contraseñas en el paquete: 0' % (tables, crops, reads))
