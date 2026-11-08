"""Lectura en vivo del ultrasónico del tinaco por la Raspberry Pi (sin USB), para acomodar el sensor.
Uso:  python tests/ver_tinaco_pi.py      Ctrl+C para salir.
"""
import json
import os
import time

import paho.mqtt.client as mqtt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = {}
for line in open(os.path.join(ROOT, 'configs', 'secrets', 'credenciales_final.env'), encoding='utf-8'):
    if '=' in line and not line.startswith('#'):
        k, v = line.strip().split('=', 1)
        env[k] = v

EXPLICA = {'OK': 'lectura válida', 'SIN_ECO': 'no regresó el eco (no ve nada o cable flojo)',
           'INESTABLE': 'las 5 mediciones no coinciden (rebotes o sensor inclinado)',
           'FUERA_DE_RANGO': 'midió más lejos que el fondo del tinaco (no apunta al agua)'}


def on_msg(cl, u, m):
    if m.retain:
        return
    j = json.loads(m.payload)
    if m.topic.endswith('/telemetry'):
        k = j.get('tank', {})
        d, p, st = k.get('distance_cm'), k.get('level_pct'), k.get('status')
        print('%s  %-15s %s%s' % (time.strftime('%H:%M:%S'), st,
              ('distancia %5.1f cm  nivel %3.0f %%   ' % (d, p)) if d is not None and p is not None else '',
              EXPLICA.get(st, '')), flush=True)
    elif m.topic.endswith('/status') and not j.get('online'):
        print(time.strftime('%H:%M:%S'), 'ESP32 DESCONECTADO de la Pi (esperando...)', flush=True)


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='tinaco-pi-%d' % time.time())
c.username_pw_set(env['MQTT_ADMIN_USER'], env['MQTT_ADMIN_PASS'])
c.on_message = on_msg
c.connect('raspberrypi.local', 1884, 30)
c.subscribe('huerto/final/esp32_principal/#', 1)
print('Ultrasónico del tinaco en vivo (por la Pi), una lectura cada 10 s. Ctrl+C para salir.')
print('Con el agua a 25-30 cm del sensor debe decir OK, ~25-30 cm, nivel ~85 %.\n', flush=True)
try:
    c.loop_forever()
except KeyboardInterrupt:
    pass
