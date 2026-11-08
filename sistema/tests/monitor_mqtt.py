"""Monitor en vivo del ESP32 del proyecto por la red (a través del broker de la Pi). No necesita USB.
Muestra telemetría, estado del riego, eventos, alarmas y respuestas a comandos. Ctrl+C para salir.
Uso:  python tests/monitor_mqtt.py
"""
import json
import os
import time

import paho.mqtt.client as mqtt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = {}
for line in open(os.path.join(ROOT, "configs", "secrets", "credenciales_final.env"), encoding="utf-8"):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1)
        env[k] = v
B = "huerto/final/esp32_principal"


def hora():
    return time.strftime("%H:%M:%S")


def on_msg(cl, u, m):
    sub = m.topic[len(B) + 1:]
    try:
        j = json.loads(m.payload.decode("utf-8", "replace"))
    except ValueError:
        return
    if sub == "telemetry":
        s, k, e, f = j.get("soil", {}), j.get("tank", {}), j.get("env", {}), j.get("flow", {})
        print("[%s] SUELO %s mV = %s %%VWC (%s) | TINACO %s cm = %s %% (%s) | AMB %s C %s %%HR | FLUJO %s L/min, hoy %s L | %s %s"
              % (hora(), s.get("mv"), s.get("vwc_pct"), s.get("status"), k.get("distance_cm"), k.get("level_pct"),
                 k.get("status"), e.get("temp_c"), e.get("rh_pct"), f.get("lpm"), f.get("today_l"), j.get("mode"), j.get("state")),
              flush=True)
    elif sub == "state":
        w = j.get("watering", {})
        if w.get("active"):
            print("[%s]   RIEGO %s: %s / %s L | %s L/min | bomba %s valvula %s"
                  % (hora(), w.get("type"), w.get("delivered_l"), w.get("target_l"), w.get("flow_lpm"),
                     "ON" if j.get("pump") else "OFF", "ON" if j.get("valve") else "OFF"), flush=True)
    elif sub == "event":
        print("[%s] EVENTO %s %s" % (hora(), j.get("type"), {k: j.get(k) for k in ("reason", "result", "delivered_l", "duration_s", "pulses", "target_l") if j.get(k) is not None}), flush=True)
    elif sub == "alarm":
        print("[%s] ALARMA %s %s - %s" % (hora(), j.get("code"), "ACTIVA" if j.get("active") else "resuelta", j.get("message", "")), flush=True)
    elif sub == "ack":
        print("[%s] RESPUESTA %s: %s - %s" % (hora(), j.get("cmd"), j.get("status"), j.get("message")), flush=True)
    elif sub == "status":
        print("[%s] CONEXION ESP32: %s" % (hora(), "EN LINEA" if j.get("online") else "DESCONECTADA"), flush=True)


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="monitor-%d" % time.time())
c.username_pw_set(env["MQTT_ADMIN_USER"], env["MQTT_ADMIN_PASS"])
c.on_message = on_msg
c.connect("raspberrypi.local", 1884, 30)
c.subscribe(B + "/#", 1)
print("Monitor del ESP32 del proyecto (esp32_principal) via Raspberry Pi - Ctrl+C para salir", flush=True)
c.loop_forever()
