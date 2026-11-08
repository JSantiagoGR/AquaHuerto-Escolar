"""Copia el historial del ESP32 del proyecto (esp32_principal) de la base de la Raspberry Pi
(~/equipo2_proyecto/database/riego_final.db, abierta en SOLO LECTURA) a la base de la laptop
(database/riego_casa.db), para que las gráficas de localhost muestren lo mismo que la Pi.

Reemplaza en la laptop solo las filas de esp32_principal (las demás, como sim_01, no se tocan).
Se puede repetir cuando quieras: la Pi es la fuente. Hace un respaldo de la base local antes.
Uso:  python scripts/copiar_historial_pi.py
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PI = "raspberrypi.local"
DEV = "esp32_principal"
SSH = ["ssh", "-i", os.path.expanduser("~/.ssh/equipo2_pi"), "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "pi@" + PI]
LOCAL_DB = os.path.join(ROOT, "database", "riego_casa.db")

REMOTO = r'''
import json, os, sqlite3
c = sqlite3.connect("file:" + os.path.expanduser("~/equipo2_proyecto/database/riego_final.db") + "?mode=ro", uri=True)
out = {}
for (t,) in c.execute("select name from sqlite_master where type='table'"):
    cols = [r[1] for r in c.execute("pragma table_info(%s)" % t)]
    if "device" in cols:
        out[t] = {"cols": cols, "rows": c.execute("select * from %s where device=?" % t, ("DEV",)).fetchall()}
print(json.dumps(out))
'''.replace("DEV", DEV)

r = subprocess.run(SSH + ["python3 -"], input=REMOTO.encode(), capture_output=True)
if r.returncode:
    sys.exit("No se pudo leer la base de la Pi (¿estás en la red del router?): " + r.stderr.decode("utf-8", "replace").strip())
pi = json.loads(r.stdout)

bk = os.path.join(ROOT, "backups", "riego_casa.antes_copia_pi_%s.db" % time.strftime("%Y%m%d_%H%M"))
src = sqlite3.connect(LOCAL_DB)
dst = sqlite3.connect(bk)
src.backup(dst)
dst.close()

db = sqlite3.connect(LOCAL_DB, timeout=30)
with db:
    for t, d in pi.items():
        loc = [r[1] for r in db.execute("pragma table_info(%s)" % t)]
        if not loc:
            continue
        pk_auto = [r[1] for r in db.execute("pragma table_info(%s)" % t) if r[5] and r[2].upper() == "INTEGER"]
        cols = [c for c in d["cols"] if c in loc and c not in pk_auto]
        idx = [d["cols"].index(c) for c in cols]
        db.execute("DELETE FROM %s WHERE device=?" % t, (DEV,))
        db.executemany("INSERT OR REPLACE INTO %s (%s) VALUES (%s)" % (t, ",".join(cols), ",".join("?" * len(cols))),
                       [[row[i] for i in idx] for row in d["rows"]])
        print("%-18s %6d filas" % (t, len(d["rows"])))
db.close()
print("Listo. Respaldo previo de la base local:", os.path.relpath(bk, ROOT))
