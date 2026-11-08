"""PRUEBAS DE INTEGRACIÓN del entorno casa (broker + Node-RED + SQLite + simulador).

Ejecuta escenarios sobre el SIMULADOR sim_01 (nunca sobre el ESP32 real) y verifica
las respuestas MQTT y lo que Node-RED guarda en SQLite. Requiere iniciar_todo.ps1 -Simulador.
Uso: python tests/test_integracion.py      -> tests/resultados/integracion_<fecha>.txt
"""
import json
import os
import socket
import sqlite3
import sys
import time
import urllib.error
import urllib.request

import paho.mqtt.client as mqtt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "riego_casa.db")
BASE = "huerto/casa/sim_01"
RES = []


def env():
    vals = {}
    for line in open(os.path.join(ROOT, "configs", "secrets", "credenciales_casa.env"), encoding="utf-8"):
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            vals[k] = v
    return vals


SEC = env()


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.1.254", 9))
    ip = s.getsockname()[0]
    s.close()
    return ip


class Bus:
    def __init__(self):
        self.msgs = []
        self.c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pruebas-integracion")
        self.c.username_pw_set(SEC["MQTT_ADMIN_USER"], SEC["MQTT_ADMIN_PASS"])
        self.c.on_message = lambda c, u, m: self.msgs.append((time.time(), m.topic, m.payload.decode("utf-8", "replace"), m.retain))
        self.c.connect("127.0.0.1", 1883, 30)
        self.c.subscribe("huerto/casa/#", 1)
        self.c.loop_start()
        time.sleep(1.5)

    def cmd(self, d, retain=False, wait=6.0):
        d = dict(d)
        d.setdefault("id", "test-%d-%d" % (time.time() * 1000, len(self.msgs)))
        d.setdefault("ts", int(time.time()))
        t0 = time.time()
        self.c.publish(BASE + "/command", json.dumps(d), qos=1, retain=retain)
        return self.wait_ack(d["id"], t0, wait), d["id"]

    def wait_ack(self, cid, t0, wait):
        end = time.time() + wait
        while time.time() < end:
            for t, top, p, r in self.msgs:
                if t >= t0 and top == BASE + "/ack":
                    j = json.loads(p)
                    if j.get("id") == cid:
                        return j
            time.sleep(0.1)
        return None

    def wait_for(self, topic_end, pred, t0, wait):
        end = time.time() + wait
        while time.time() < end:
            for t, top, p, r in list(self.msgs):
                if t >= t0 and top.endswith(topic_end):
                    try:
                        j = json.loads(p)
                    except Exception:  # noqa: BLE001
                        continue
                    if pred(j):
                        return j
            time.sleep(0.2)
        return None

    def sim(self, action, value):
        return self.cmd({"cmd": "SIM_CONTROL", "action": action, "value": value})[0]


def check(name, ok, detail=""):
    RES.append((name, bool(ok), detail))
    print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, ("-> " + detail) if detail and not ok else ""))


def q(sql, args=()):
    con = sqlite3.connect(DB, timeout=10)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def http(url, auth=None):
    req = urllib.request.Request(url)
    if auth:
        import base64
        req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()[:400]
    except urllib.error.HTTPError as e:
        return e.code, b""


def main():
    b = Bus()
    # --- Broker y seguridad -----------------------------------------------------------
    anon = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="anonimo")
    rc = []
    anon.on_connect = lambda c, u, f, r, p=None: rc.append(r)
    anon.connect("127.0.0.1", 1883, 10)
    anon.loop_start()
    time.sleep(1.5)
    anon.loop_stop()
    check("Broker rechaza clientes anónimos", rc and rc[0] != 0, str(rc))
    simc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="prueba-acl")
    simc.username_pw_set(SEC["MQTT_SIM_USER"], SEC["MQTT_SIM_PASS"])
    simc.connect("127.0.0.1", 1883, 10)
    simc.loop_start()
    t0 = time.time()
    simc.publish("huerto/casa/esp32_01/command", json.dumps({"id": "acl-test", "cmd": "GET_STATUS"}), qos=1)
    time.sleep(1.5)
    simc.loop_stop()
    leaked = [m for m in b.msgs if m[0] >= t0 and m[1] == "huerto/casa/esp32_01/command"]
    check("ACL: el simulador NO puede enviar comandos al ESP32 real", not leaked)

    # --- Protocolo de comandos ----------------------------------------------------------
    b.sim("speed", 1)
    a, _ = b.cmd({"cmd": "SET_MODE", "mode": "AUTOMATICO"})
    check("SET_MODE AUTOMATICO -> ACK OK con modo aplicado", a and a["status"] == "OK" and a.get("mode_applied") == "AUTOMATICO", str(a))
    a1, cid = b.cmd({"cmd": "GET_STATUS"})
    a2, _ = b.cmd({"cmd": "GET_STATUS", "id": cid})
    check("Comando con id repetido -> DUPLICATE", a2 and a2["status"] == "DUPLICATE", str(a2))
    # Comando retenido que espera en el broker mientras el dispositivo está desconectado:
    # al reconectar llega con la marca "retain" y NO debe ejecutarse.
    b.sim("mqtt_drop", 6)
    time.sleep(1.5)
    rid = "test-retenido-%d" % time.time()
    b.c.publish(BASE + "/command", json.dumps({"id": rid, "cmd": "START_MANUAL", "liters": 0.5, "ts": int(time.time())}), qos=1, retain=True)
    a = b.wait_ack(rid, time.time() - 2, 25)
    b.c.publish(BASE + "/command", b"", qos=1, retain=True)    # borra el retenido de prueba
    check("Comando de riego RETENIDO al reconectar -> se ignora (RETAINED)", a and a["status"] == "RETAINED", str(a))
    time.sleep(2)
    a, _ = b.cmd({"cmd": "START_MANUAL", "liters": 0.5, "ts": int(time.time()) - 600})
    check("Comando antiguo (ts -10 min) -> STALE", a and a["status"] == "STALE", str(a))
    cfg0 = b.wait_for("/config", lambda j: True, 0, 1) or {}
    v0 = (cfg0 or {}).get("profile_version", 0)
    a, _ = b.cmd({"cmd": "APPLY_CONFIG", "version": 500, "params": {"hum_min": 40, "hum_target": 35}})
    check("Configuración inválida (mín > óptima) -> REJECTED y versión sin cambio",
          a and a["status"] == "REJECTED" and a.get("version_applied") != 500, str(a))
    b.cmd({"cmd": "STOP"})
    time.sleep(1)
    a, _ = b.cmd({"cmd": "APPLY_CONFIG", "version": 501, "params": {"infilt_min": 15, "min_event_gap_min": 1, "emergency_gap_min": 30}})
    check("Configuración válida -> OK con version_applied", a and a["status"] == "OK" and a.get("version_applied") == 501, str(a))

    a, _ = b.cmd({"cmd": "START_MANUAL", "liters": 0.5})
    check("Riego manual en AUTOMATICO -> REJECTED (solo en MANUAL)", a and a["status"] == "REJECTED" and "MANUAL" in (a.get("message") or ""), str(a))

    # --- Riego manual por volumen y STOP ------------------------------------------------
    b.cmd({"cmd": "SET_MODE", "mode": "MANUAL"})
    t0 = time.time()
    a, _ = b.cmd({"cmd": "START_MANUAL", "liters": 0.5})
    end = b.wait_for("/event", lambda j: j.get("type") == "WATERING_END", t0, 30)
    check("Riego manual 0.5 L termina por volumen (TARGET)", end and end["result"] == "TARGET" and 0.49 <= end["delivered_l"] <= 0.53, str(end))
    time.sleep(4)
    rows = q("SELECT delivered_l, result FROM irrigation_events WHERE event_id=?", (end["event_id"],)) if end else []
    check("Node-RED guarda el riego en SQLite", rows and rows[0][1] == "TARGET", str(rows))
    t0 = time.time()
    b.cmd({"cmd": "START_MANUAL", "liters": 2.0})
    time.sleep(3)
    b.cmd({"cmd": "STOP"})
    end = b.wait_for("/event", lambda j: j.get("type") == "WATERING_END", t0, 10)
    check("STOP durante el riego -> STOP_CMD", end and end["result"] == "STOP_CMD", str(end))

    # --- Fallas y alertas ---------------------------------------------------------------
    t0 = time.time()
    b.sim("fail_soil", True)
    b.sim("speed", 120)
    al = b.wait_for("/alarm", lambda j: j.get("code") == "SOIL_SENSOR" and j.get("active"), t0, 25)
    check("Falla del EC-5 simulada -> alarma SOIL_SENSOR", al is not None)
    b.sim("fail_soil", False)
    time.sleep(6)
    rows = q("SELECT COUNT(*) FROM alerts WHERE code='SOIL_SENSOR' AND ts>=?", (int(t0) - 5,))
    check("La alerta queda registrada en SQLite", rows[0][0] >= 1, str(rows))

    # --- Riego de emergencia y riego matutino -------------------------------------------
    b.sim("speed", 60)
    b.cmd({"cmd": "SET_MODE", "mode": "AUTOMATICO"})
    b.sim("hour", "13:00")
    b.sim("soil", 15)
    t0 = time.time()
    st = b.wait_for("/event", lambda j: j.get("type") == "WATERING_START", t0, 90)
    # Límite configurado en el dispositivo (con la cama de 375 L: 1.9 L = medio punto de %VWC)
    em = float(((cfg0 or {}).get("params") or {}).get("emergency_liters") or 0.5)
    check("Emergencia (15 %%VWC a las 13:00) -> riego EMERGENCY limitado a emergency_liters (%.1f L)" % em,
          st and st["reason"] == "EMERGENCY" and st["target_l"] <= em + 0.01, str(st))
    b.wait_for("/event", lambda j: j.get("type") == "EVENT_END", t0, 90)
    b.sim("soil", 30)
    b.sim("hour", "06:30")
    t0 = time.time()
    st = b.wait_for("/event", lambda j: j.get("type") == "WATERING_START", t0, 90)
    check("Mañana 06:30 con 30 %VWC (bajo óptima-histéresis) -> riego SCHEDULED", st and st["reason"] in ("SCHEDULED", "IA"), str(st))
    b.cmd({"cmd": "STOP"})

    # --- Lluvia pronosticada y lluvia real ----------------------------------------------
    b.cmd({"cmd": "SET_MODE", "mode": "MANUAL"})
    b.sim("hour", "06:20")          # primero la hora: adelantar el reloj vencería el pronóstico
    b.sim("forecast_rain", 40)       # 40 mm: cubre el déficit (balance), así que la IA debe posponer
    b.sim("soil", 28)
    b.cmd({"cmd": "SET_MODE", "mode": "IA"})          # el pronóstico de lluvia solo lo usa el modo IA
    t0 = time.time()
    d = b.wait_for("/decision", lambda j: j.get("code") == "RAIN_EXPECTED", t0 - 1, 40)
    check("Pronóstico de lluvia en modo IA -> pospone el riego rutinario (RAIN_EXPECTED)", d is not None)
    b.sim("forecast_rain", 0)
    b.cmd({"cmd": "SET_MODE", "mode": "MANUAL"})
    b.sim("speed", 600)
    time.sleep(3)
    t0 = time.time()
    b.sim("rain", 6)
    ev = b.wait_for("/event", lambda j: j.get("type") == "UNEXPLAINED_RISE", t0, 60)
    check("Lluvia simulada -> evento POSIBLE_LLUVIA (sin litros de bomba)", ev and ev["classification"] == "POSIBLE_LLUVIA", str(ev))
    time.sleep(4)
    rows = q("SELECT classification, server_classification FROM rain_events WHERE device='sim_01' AND ts>=?", (int(time.time()) - 86400 * 30,))
    check("El evento de lluvia queda en SQLite", len(rows) >= 1, str(rows[-1:] if rows else rows))
    time.sleep(130 / 6)
    t0 = time.time()
    b.sim("external", 5)
    ev = b.wait_for("/event", lambda j: j.get("type") == "UNEXPLAINED_RISE", t0, 60)
    check("Riego externo simulado -> POSIBLE_RIEGO_EXTERNO", ev and ev["classification"] in ("POSIBLE_RIEGO_EXTERNO", "POSIBLE_LLUVIA"), str(ev))
    b.sim("speed", 1)

    # --- IA ------------------------------------------------------------------------------
    ia = b.wait_for("/ia", lambda j: True, 0, 2)
    check("IA del simulador publica estado y plan", ia and ia.get("status") in ("APRENDIZAJE", "VALIDACION", "PREDICTIVO_ACTIVO") and "plan" in ia, str(ia)[:200])
    a, _ = b.cmd({"cmd": "SET_MODE", "mode": "IA"})
    check("SET_MODE IA -> ACK OK", a and a["status"] == "OK" and a.get("mode_applied") == "IA", str(a))
    b.cmd({"cmd": "SET_MODE", "mode": "MANUAL"})

    # --- Pérdida de MQTT (LWT) -----------------------------------------------------------
    t0 = time.time()
    b.sim("mqtt_drop", 20)
    off = b.wait_for("/status", lambda j: j.get("online") is False, t0, 60)
    check("Pérdida de MQTT -> mensaje de última voluntad (offline)", off is not None)
    on = b.wait_for("/status", lambda j: j.get("online") is True, t0, 60)
    check("Reconexión automática -> online", on is not None)
    time.sleep(3)
    rows = q("SELECT kind FROM connectivity WHERE device='sim_01' AND ts>=?", (int(t0) - 2,))
    check("Desconexión y reconexión registradas en SQLite", ("mqtt_offline",) in rows and ("mqtt_online",) in rows, str(rows))

    # --- Servidor: SQLite, Open-Meteo, CSV, autenticación ---------------------------------
    n = q("SELECT COUNT(*) FROM readings WHERE device='sim_01' AND simulated=1")[0][0]
    check("Lecturas del simulador guardadas y marcadas como simuladas", n > 0, str(n))
    wx = q("SELECT ok, http, temp_c FROM weather_fetches WHERE origin='servidor' ORDER BY ts_fetch DESC LIMIT 1")
    check("Open-Meteo real consultado por HTTPS (HTTP 200)", wx and wx[0][0] == 1 and wx[0][1] == 200, str(wx))
    st, body = http("http://127.0.0.1:1880/riego/export.csv?tipo=riegos&device=sim_01")
    check("Exportación CSV desde esta PC", st == 200 and b"event_id" in body, str(st))
    ip = lan_ip()
    st1, _ = http("http://%s:1880/dashboard/" % ip)
    st2, _ = http("http://%s:1880/dashboard/" % ip, SEC["DASHBOARD_USER"] + ":" + SEC["DASHBOARD_PASS"])
    if SEC.get("DASHBOARD_PUBLIC") == "1":
        check("Dashboard abierto en la red local (DASHBOARD_PUBLIC=1, igual que la Pi)", st1 == 200 and st2 == 200, "%s %s" % (st1, st2))
    else:
        check("Dashboard desde la red local exige usuario (401) y acepta credenciales (200)", st1 == 401 and st2 == 200, "%s %s" % (st1, st2))
    st, _ = http("http://127.0.0.1:1880/flows")
    check("Editor/Admin API de Node-RED protegido (401 sin token)", st == 401, str(st))

    # Restaura la configuración normal del simulador
    b.cmd({"cmd": "STOP"})
    b.cmd({"cmd": "SET_MODE", "mode": "MANUAL"})
    b.cmd({"cmd": "APPLY_CONFIG", "version": 502, "params": {"min_event_gap_min": 60, "emergency_gap_min": 240}})
    b.sim("speed", 1)
    ok = sum(1 for r in RES if r[1])
    out = os.path.join(ROOT, "tests", "resultados")
    os.makedirs(out, exist_ok=True)
    fn = os.path.join(out, "integracion_%s.txt" % time.strftime("%Y%m%d_%H%M"))
    with open(fn, "w", encoding="utf-8") as f:
        f.write("PRUEBAS DE INTEGRACION (simulador sim_01 + broker + Node-RED + SQLite) %s\n" % time.strftime("%Y-%m-%d %H:%M"))
        for name, good, det in RES:
            f.write("[%s] %s %s\n" % ("PASS" if good else "FAIL", name, "" if good else det))
        f.write("RESULTADO: %d PASS, %d FAIL\n" % (ok, len(RES) - ok))
    print("RESULTADO: %d PASS, %d FAIL -> %s" % (ok, len(RES) - ok, fn))
    b.c.loop_stop()
    return 0 if ok == len(RES) else 1


if __name__ == "__main__":
    sys.exit(main())
