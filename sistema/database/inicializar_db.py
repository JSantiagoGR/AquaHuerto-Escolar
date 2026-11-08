"""Crea (o actualiza sin borrar) la base de datos SQLite y carga los 10 cultivos base.

Uso: python inicializar_db.py [ruta.db]      (por defecto database/riego_casa.db)
Es idempotente: CREATE TABLE IF NOT EXISTS / INSERT OR IGNORE. Nunca borra datos.
"""
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "riego_casa.db")
    con = sqlite3.connect(db)
    with open(os.path.join(HERE, "schema.sql"), encoding="utf-8") as f:
        con.executescript(f.read())
    # Migración: bases creadas antes de ligar la plantación a la caja
    cols = [r[1] for r in con.execute("PRAGMA table_info(plantings)")]
    if "device" not in cols:
        con.execute("ALTER TABLE plantings ADD COLUMN device TEXT")
    with open(os.path.join(HERE, "cultivos_base.json"), encoding="utf-8") as f:
        base = json.load(f)
    now = int(time.time())
    n = 0
    for c in base["cultivos"]:
        cur = con.execute("SELECT data FROM crops WHERE id=?", (c["id"],))
        row = cur.fetchone()
        data = json.dumps(c, ensure_ascii=False)
        if row is None:
            con.execute("INSERT INTO crops(id,name,type,data,created,updated) VALUES(?,?,?,?,?,?)",
                        (c["id"], c["nombre"], "base", data, now, now))
            n += 1
        elif row[0] != data:
            # Los cultivos base se actualizan con el catálogo; los personalizados nunca se tocan
            con.execute("UPDATE crops SET data=?, name=?, updated=? WHERE id=? AND type='base'",
                        (data, c["nombre"], now, c["id"]))
    con.execute("INSERT OR IGNORE INTO app_settings(key,value,updated) VALUES('fuentes_cultivos',?,?)",
                (json.dumps(base["fuentes"], ensure_ascii=False), now))
    con.execute("INSERT OR IGNORE INTO app_settings(key,value,updated) VALUES('metodo_umbrales',?,?)",
                (json.dumps(base["metodo_umbrales_vwc"], ensure_ascii=False), now))
    con.commit()
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    crops = con.execute("SELECT COUNT(*) FROM crops WHERE type='base'").fetchone()[0]
    print(f"Base de datos: {db}")
    print(f"Tablas ({len(tables)}): {', '.join(tables)}")
    print(f"Cultivos base: {crops} (nuevos: {n})")
    con.close()


if __name__ == "__main__":
    main()
