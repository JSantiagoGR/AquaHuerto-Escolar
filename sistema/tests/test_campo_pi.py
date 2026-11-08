"""PRUEBA DE CAMPO: Raspberry Pi (Equipo 2 Proyecto, 1881/1884) + ESP32 del proyecto (esp32_principal).

Pensada para correr con la BATERÍA DE 12 V DESCONECTADA: los relevadores conmutan pero no sale agua,
así que el riego de prueba debe terminar solo por falta de flujo (NO_FLOW). También comprueba
STOP, modos, protecciones de comandos, base de datos en la Pi, páginas del dashboard y que el
Node-RED del profesor (1880) y el Mosquitto del sistema sigan intactos.

Uso:  python tests/test_campo_pi.py            -> tests/resultados/campo_pi_<fecha>.txt
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import paho.mqtt.client as mqtt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PI = "raspberrypi.local"
BASE = "huerto/final/esp32_principal"
SSH = ["ssh", "-i", os.path.expanduser("~/.ssh/equipo2_pi"), "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "pi@" + PI]
RES = []


def env():
    vals = {}
    for line in open(os.path.join(ROOT, "configs", "secrets", "credenciales_final.env"), encoding="utf-8"):
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            vals[k] = v
    return vals


SEC = env()


def check(name, ok, detail=""):
    RES.append((bool(ok), name, detail))
    print(("[PASS] " if ok else "[FAIL] ") + name + ("" if ok else " -> " + str(detail)[:300]), flush=True)


def ssh(cmd):
    r = subprocess.run(SSH + [cmd], capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def http(url):
    try:
        return urllib.request.urlopen(url, timeout=10).status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return "sin conexión: %s" % e


class Bus:
    def __init__(self):
        self.msgs = []
        self.c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="prueba-campo-%d" % time.time())
        self.c.username_pw_set(SEC["MQTT_ADMIN_USER"], SEC["MQTT_ADMIN_PASS"])
        self.c.on_message = lambda c, u, m: self.msgs.append((time.time(), m.topic, m.payload.decode("utf-8", "replace")))
        self.c.connect(PI, 1884, 30)
        self.c.subscribe(BASE + "/#", 1)
        self.c.loop_start()
        time.sleep(1.5)

    def cmd(self, d, wait=8.0):
        d = dict(d)
        d.setdefault("id", "campo-%d-%d" % (time.time() * 1000, len(self.msgs)))
        d.setdefault("ts", int(time.time()))
        t0 = time.time()
        self.c.publish(BASE + "/command", json.dumps(d), qos=1, retain=False)
        return self.wait_for("/ack", lambda j: j.get("id") == d["id"], t0, wait), d

    def wait_for(self, end_topic, pred, t0, wait):
        end = time.time() + wait
        while time.time() < end:
            for t, top, p in list(self.msgs):
                if t >= t0 and top.endswith(end_topic):
                    try:
                        j = json.loads(p)
                    except ValueError:
                        continue
                    if pred(j):
                        return j
            time.sleep(0.1)
        return None


def main():
    # --- Servicios en la Pi y lo existente intacto -------------------------------------------
    hashes_antes = open(sorted(
        os.path.join(ROOT, "backups", d, "pi_hashes_antes.txt") for d in os.listdir(os.path.join(ROOT, "backups"))
        if d.startswith("raspberry_pi_antes_") and os.path.exists(os.path.join(ROOT, "backups", d, "pi_hashes_antes.txt")))[-1]).read()
    ahora = ssh("sha256sum ~/.node-red/settings.js /etc/mosquitto/mosquitto.conf")
    check("Configuración del Node-RED del profesor y del Mosquitto del sistema sin cambios",
          all(line.split()[0] in hashes_antes for line in ahora.splitlines()), ahora)
    check("Node-RED de los equipos (1880/ui) responde", http("http://%s:1880/ui/" % PI) == 200)
    est = ssh("bash ~/equipo2_proyecto/scripts/estado_equipo2.sh | head -7")
    check("Instancia propia: Node-RED 1881 y broker 1884 escuchando",
          "1881: escuchando" in est and "1884: escuchando" in est, est)
    cron = ssh("crontab -l 2>/dev/null")
    check("Arranque automático configurado (@reboot)", "iniciar_equipo2.sh" in cron, cron)
    pages = ["inicio", "manual", "automatico", "ia", "cultivos", "crecimiento", "clima", "historial", "alertas", "configuracion"]
    codes = {p: http("http://%s:1881/dashboard/%s" % (PI, p)) for p in pages}
    check("Las 10 páginas del dashboard responden sin contraseña (200)", all(c == 200 for c in codes.values()), codes)
    check("Editor/API protegidos (401 sin usuario)", http("http://%s:1881/flows" % PI) == 401)

    # --- ESP32 del proyecto --------------------------------------------------------------------
    b = Bus()
    st = b.wait_for("/state", lambda j: True, 0, 5)
    check("ESP32 publica estado con firmware riego-2.0.0", st and st.get("fw") == "riego-2.0.0", str(st)[:150])
    check("Modo MANUAL y potencia habilitada (autorizada por el equipo)",
          st and st.get("mode") == "MANUAL" and st.get("power_outputs") is True, str(st)[:200])
    t0 = time.time()
    tel = b.wait_for("/telemetry", lambda j: True, t0, 20)
    check("Telemetría real cada 10 s con hora NTP", tel and tel.get("ts", 0) > 1.7e9, str(tel)[:150])
    envr = (tel or {}).get("env") or {}
    check("DHT22 real válido (temperatura y HR plausibles)",
          envr.get("valid") and 0 < envr.get("temp_c", -99) < 50 and 5 < envr.get("rh_pct", -1) <= 100, envr)
    check("EC-5 sin conectar se reporta inválido (no se inventa)", tel and not tel["soil"]["valid"], (tel or {}).get("soil"))

    a, d = b.cmd({"cmd": "GET_STATUS"})
    check("GET_STATUS -> ACK OK", a and a["status"] == "OK", a)
    b.c.publish(BASE + "/command", json.dumps(d), qos=1)
    a2 = b.wait_for("/ack", lambda j: j.get("id") == d["id"] and j.get("status") == "DUPLICATE", time.time() - 0.5, 8)
    check("Comando repetido -> DUPLICATE", a2 is not None, a2)
    a, _ = b.cmd({"cmd": "START_MANUAL", "liters": 0.3, "ts": int(time.time()) - 600})
    check("Comando viejo (10 min) -> STALE (no riega)", a and a["status"] == "STALE", a)
    a, _ = b.cmd({"cmd": "APPLY_CONFIG", "version": 9001, "params": {"hum_min": 40, "hum_target": 35}})
    check("Configuración inválida -> REJECTED", a and a["status"] == "REJECTED", a)
    a, _ = b.cmd({"cmd": "SET_MODE", "mode": "AUTOMATICO"})
    check("SET_MODE AUTOMATICO -> OK", a and a["status"] == "OK" and a.get("mode_applied") == "AUTOMATICO", a)
    a, _ = b.cmd({"cmd": "SET_MODE", "mode": "MANUAL"})
    check("SET_MODE MANUAL -> OK", a and a["status"] == "OK", a)

    # --- Riego con la batería desconectada: relevadores sí, agua no -> corte por falta de flujo -
    t0 = time.time()
    a, _ = b.cmd({"cmd": "START_MANUAL", "liters": 0.3})
    check("START_MANUAL 0.3 L -> ACK OK (potencia habilitada)", a and a["status"] == "OK", a)
    on = b.wait_for("/state", lambda j: j.get("pump") is True and j.get("valve") is True, t0, 8)
    check("Válvula y bomba se activan (relevadores conmutan)", on is not None)
    end = b.wait_for("/event", lambda j: j.get("type") == "WATERING_END", t0, 40)
    check("Sin agua (batería desconectada) -> se corta solo por NO_FLOW",
          end and end.get("result") == "NO_FLOW", end)
    off = b.wait_for("/state", lambda j: j.get("pump") is False and j.get("valve") is False, t0, 10)
    check("Bomba y válvula quedan apagadas", off is not None)
    al = b.wait_for("/alarm", lambda j: j.get("code") == "NO_FLOW" and j.get("active"), t0, 10)
    check("Alarma NO_FLOW publicada", al is not None, al)
    a, _ = b.cmd({"cmd": "CLEAR_ALARM", "alarm": "NO_FLOW"})
    check("CLEAR_ALARM NO_FLOW -> OK", a and a["status"] == "OK", a)

    time.sleep(3)
    t0 = time.time()
    a, _ = b.cmd({"cmd": "START_MANUAL", "liters": 0.3})
    check("Segundo riego de prueba -> ACK OK", a and a["status"] == "OK", a)
    time.sleep(3)
    a, _ = b.cmd({"cmd": "STOP"})
    end = b.wait_for("/event", lambda j: j.get("type") == "WATERING_END", t0, 15)
    check("STOP durante el riego -> STOP_CMD", end and end.get("result") == "STOP_CMD", end)

    # --- Registro en la base de datos de la Pi ------------------------------------------------
    time.sleep(5)
    out = ssh("python3 -c \"import sqlite3,time;c=sqlite3.connect('/home/pi/equipo2_proyecto/database/riego_final.db');"
              "t=int(time.time())-600;print(c.execute(\\\"select count(*) from irrigation_events where device='esp32_principal' and ts_start>?\\\",(t,)).fetchone()[0],"
              "c.execute(\\\"select count(*) from readings where device='esp32_principal' and simulated=0 and ts>?\\\",(t,)).fetchone()[0],"
              "c.execute(\\\"select count(*) from alerts where code='NO_FLOW' and ts>?\\\",(t,)).fetchone()[0])\"")
    try:
        ev, rd, alc = (int(x) for x in out.split())
    except ValueError:
        ev = rd = alc = -1
    check("La Pi guarda los riegos de prueba en SQLite", ev >= 2, out)
    check("La Pi guarda telemetría REAL (simulated=0)", rd > 0, out)
    check("La alerta NO_FLOW queda registrada en la Pi", alc >= 1, out)
    b.c.loop_stop()

    ok = sum(1 for r in RES if r[0])
    path = os.path.join(ROOT, "tests", "resultados", "campo_pi_%s.txt" % time.strftime("%Y%m%d_%H%M"))
    with open(path, "w", encoding="utf-8") as f:
        f.write("PRUEBA DE CAMPO (Pi + esp32_principal, batería de 12 V desconectada) %s\n" % time.strftime("%Y-%m-%d %H:%M"))
        for r in RES:
            f.write(("[PASS] " if r[0] else "[FAIL] ") + r[1] + ("" if r[0] else " -> " + str(r[2])[:300]) + "\n")
        f.write("RESULTADO: %d PASS, %d FAIL\n" % (ok, len(RES) - ok))
    print("RESULTADO: %d PASS, %d FAIL -> %s" % (ok, len(RES) - ok, path))
    return 0 if ok == len(RES) else 1


if __name__ == "__main__":
    sys.exit(main())
