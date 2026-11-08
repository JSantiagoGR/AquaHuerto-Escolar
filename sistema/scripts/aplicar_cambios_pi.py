"""Aplica los cambios pendientes en la Raspberry Pi y en el ESP32 del proyecto (por la red, sin USB).

1) Sube y despliega el flujo 'final' en la instancia propia (puerto 1881).
2) Envía al ESP32 (esp32_principal) la ubicación de la escuela (lat/lon) para Open-Meteo.
Requiere estar conectado a RouterHuerto1.   Uso:  python scripts/aplicar_cambios_pi.py
"""
import json
import os
import subprocess
import sys
import time

import paho.mqtt.client as mqtt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PI = "raspberrypi.local"
LAT, LON = 28.659830, -106.074051
SSH = ["ssh", "-i", os.path.expanduser("~/.ssh/equipo2_pi"), "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "pi@" + PI]
env = {}
for line in open(os.path.join(ROOT, "configs", "secrets", "credenciales_final.env"), encoding="utf-8"):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1)
        env[k] = v

flow = os.path.join(ROOT, "dashboard", "export", "flows_riego_final.json")
with open(flow, "rb") as f:
    r = subprocess.run(SSH + ["cp ~/equipo2_proyecto/dashboard/export/flows_riego_final.json "
                              "~/equipo2_proyecto/backups/flows_riego_final.antes_%s.json; "
                              "cat > ~/equipo2_proyecto/dashboard/export/flows_riego_final.json" % time.strftime("%Y%m%d_%H%M")],
                       stdin=f, capture_output=True, text=True)
if r.returncode:
    sys.exit("No se pudo llegar a la Pi (¿estás en RouterHuerto1?): " + r.stderr.strip())
r = subprocess.run(SSH + ["cd ~/equipo2_proyecto && python3 nodered/desplegar_flows.py --entorno final "
                          "--url http://127.0.0.1:1881 --env-file configs/secrets/credenciales_final.env"],
                   capture_output=True, text=True)
print("Flujo en la Pi:", (r.stdout or r.stderr).strip().splitlines()[-1])

B = "huerto/final/esp32_principal"
msgs = []
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="aplicar-cambios-%d" % time.time())
c.username_pw_set(env["MQTT_ADMIN_USER"], env["MQTT_ADMIN_PASS"])
c.on_message = lambda cl, u, m: msgs.append((time.time(), m.topic, m.payload.decode("utf-8", "replace")))
c.connect(PI, 1884, 10)
c.subscribe(B + "/#", 1)
c.loop_start()
time.sleep(3)
cfg = [json.loads(p) for _, t, p in msgs if t.endswith("/config")]
ver = ((cfg[-1].get("profile_version") if cfg else None) or 600) + 1
cid = "ubic-%d" % (time.time() * 1000)
t0 = time.time()
c.publish(B + "/command", json.dumps({"cmd": "APPLY_CONFIG", "id": cid, "ts": int(time.time()), "version": ver,
                                      "params": {"lat": LAT, "lon": LON, "pump_max_s": 180, "liters_per_cycle": 1.5,
                                                 "max_cycles": 5, "emergency_liters": 1.5}}), qos=1)
ack = None
while time.time() - t0 < 10 and not ack:
    for t, top, p in list(msgs):
        if t >= t0 and top.endswith("/ack") and json.loads(p).get("id") == cid:
            ack = json.loads(p)
    time.sleep(0.2)
c.loop_stop()
print("Ubicación en el ESP32:", ack.get("status") if ack else "sin respuesta (¿ESP32 encendido?)", "-", (ack or {}).get("message", ""))
