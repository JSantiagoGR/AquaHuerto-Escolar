"""Espejo de SOLO LECTURA: Raspberry Pi (broker propio, puerto 1884) -> broker de la laptop (1883).

Hace que el ESP32 del proyecto (esp32_principal) aparezca en vivo en el dashboard de la laptop
(http://localhost:1880/dashboard) igual que en la Pi:
    huerto/final/esp32_principal/...  (Pi)  ->  huerto/casa/esp32_principal/...  (laptop)
Solo se suscribe en la Pi y solo publica en la laptop: los comandos que se den desde la laptop NO llegan
al ESP32 (la Pi sigue siendo el único servidor que lo controla). Usa las credenciales que ya existen en
configs/secrets (no crea usuarios ni guarda contraseñas nuevas, y no las imprime).
Requiere estar en la red del router de la Pi; si no la encuentra, reintenta solo.
Uso:  python scripts/espejo_pi.py      (lo inicia también  iniciar_todo.ps1 -EspejoPi)
"""
import os
import time

import paho.mqtt.client as mqtt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PI = "raspberrypi.local"
REMOTO, LOCAL = "huerto/final/", "huerto/casa/"
DISPOSITIVO = "esp32_principal"


def leer_env(nombre):
    env = {}
    for line in open(os.path.join(ROOT, "configs", "secrets", nombre), encoding="utf-8"):
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            env[k] = v
    return env


fin, casa = leer_env("credenciales_final.env"), leer_env("credenciales_casa.env")
n = [0]


def log(txt):
    print("[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), txt), flush=True)


local = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="espejo-pi-local")
local.username_pw_set(casa["MQTT_ADMIN_USER"], casa["MQTT_ADMIN_PASS"])
local.reconnect_delay_set(2, 30)
local.on_connect = lambda cl, u, f, rc, p=None: log("broker laptop 1883: %s" % rc)
local.connect_async("127.0.0.1", 1883, 60)
local.loop_start()

remoto = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="espejo-laptop-%d" % time.time())
remoto.username_pw_set(fin["MQTT_ADMIN_USER"], fin["MQTT_ADMIN_PASS"])
remoto.reconnect_delay_set(5, 60)


def al_conectar(cl, u, flags, rc, props=None):
    log("broker Pi %s:1884: %s" % (PI, rc))
    if not rc.is_failure:
        cl.subscribe(REMOTO + DISPOSITIVO + "/#", 1)


def al_recibir(cl, u, m):
    if m.topic.endswith("/command"):
        return  # nunca reenviar comandos
    local.publish(LOCAL + m.topic[len(REMOTO):], m.payload, qos=1, retain=m.retain)
    n[0] += 1
    if n[0] % 500 == 1:
        log("mensajes copiados: %d" % n[0])


remoto.on_connect = al_conectar
remoto.on_disconnect = lambda cl, u, f, rc, p=None: log("Pi desconectada (%s), reintentando..." % rc)
remoto.on_message = al_recibir
log("Espejo de solo lectura Pi -> laptop para %s" % DISPOSITIVO)
while True:
    try:
        remoto.connect(PI, 1884, 30)
        remoto.loop_forever(retry_first_connection=True)
    except OSError as e:
        log("Pi no disponible (%s), reintentando en 30 s" % e)
        time.sleep(30)
