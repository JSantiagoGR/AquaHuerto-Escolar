"""PRUEBA FINAL con agua real (esp32_principal por la Raspberry Pi, sin USB).
1) Asegura el máximo diario de 30 L.  2) Riego MANUAL de 2 L hasta el final (orden válvula -> bomba, caudal, litros).
3) Riego de 1 L detenido con STOP a los ~10 s.  4) Revisa reinicios, registro en la Pi e IA.  5) Deja el modo AUTOMATICO.
Uso:  python tests/prueba_final_riego.py   -> tests/resultados/prueba_final_<fecha>.txt
"""
import json
import os
import subprocess
import time

import paho.mqtt.client as mqtt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = {}
for line in open(os.path.join(ROOT, 'configs', 'secrets', 'credenciales_final.env'), encoding='utf-8'):
    if '=' in line and not line.startswith('#'):
        k, v = line.strip().split('=', 1)
        env[k] = v
B = 'huerto/final/esp32_principal'
SSH = ['ssh', '-i', os.path.expanduser('~/.ssh/equipo2_pi'), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', 'pi@raspberrypi.local']
OUT = os.path.join(ROOT, 'tests', 'resultados', 'prueba_final_%s.txt' % time.strftime('%Y%m%d_%H%M'))
msgs, RES = [], []


def log(t):
    line = '[%s] %s' % (time.strftime('%H:%M:%S'), t)
    print(line, flush=True)
    RES.append(line)


def check(name, ok, detail=''):
    log('%s %s %s' % ('[PASS]' if ok else '[FAIL]', name, ('-> ' + str(detail)) if detail else ''))
    return ok


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='prueba-final-%d' % time.time())
c.username_pw_set(env['MQTT_ADMIN_USER'], env['MQTT_ADMIN_PASS'])
c.on_message = lambda cl, u, m: msgs.append((time.time(), m.topic.rsplit('/', 1)[1], m.retain, json.loads(m.payload)))
c.connect('raspberrypi.local', 1884, 10)
c.subscribe(B + '/#', 1)
c.loop_start()
time.sleep(4)


def latest(kind, since=0):
    v = [j for t, k, r, j in msgs if k == kind and t >= since and not r]
    return v[-1] if v else None


def cmd(body, wait=20):
    cid = 'final-%d' % (time.time() * 1000)
    body = dict(body, id=cid, ts=int(time.time()))
    t0 = time.time()
    c.publish(B + '/command', json.dumps(body), qos=1)
    while time.time() - t0 < wait:
        for t, k, r, j in list(msgs):
            if t >= t0 and k == 'ack' and j.get('id') == cid:
                return j
        time.sleep(0.2)
    return None


def version():
    cfg = [j for t, k, r, j in msgs if k == 'config']
    return (cfg[-1].get('profile_version') or 525) if cfg else 525


def watch(seconds, stop_at=None):
    """Sigue el riego: orden de válvula/bomba, caudal, fin y reinicios."""
    t0, first_valve, first_pump, flows, end, stopped = time.time(), None, None, [], None, False
    up0 = (latest('state') or {}).get('uptime_s') or 0
    while time.time() - t0 < seconds:
        for t, k, r, j in list(msgs):
            if t < t0 or r:
                continue
            if k == 'state':
                if j.get('valve') and first_valve is None:
                    first_valve = t
                if j.get('pump') and first_pump is None:
                    first_pump = t
                w = j.get('watering') or {}
                if w.get('active') and (w.get('flow_lpm') or 0) > 0:
                    flows.append(w.get('flow_lpm'))
            if k == 'event' and j.get('type') == 'WATERING_END' and end is None:
                end = j
        if stop_at and not stopped and time.time() - t0 >= stop_at:
            a = cmd({'cmd': 'STOP'})
            log('STOP enviado -> %s' % ((a or {}).get('status')))
            stopped = True
        if end:
            break
        time.sleep(0.5)
    st = latest('state', t0) or {}
    return first_valve, first_pump, flows, end, st, up0


log('=== PRUEBA FINAL esp32_principal ===')
s0 = latest('state') or {}
check('ESP32 en línea y respondiendo', bool(s0), 'uptime %s s, rssi %s' % (s0.get('uptime_s'), s0.get('rssi')))
a = cmd({'cmd': 'APPLY_CONFIG', 'version': version() + 1, 'params': {'max_liters_daily': 30}})
check('Máximo diario 30 L', a and a.get('status') == 'OK', (a or {}).get('message'))
a = cmd({'cmd': 'SET_MODE', 'mode': 'MANUAL'})
check('Modo MANUAL', a and a.get('status') == 'OK', (a or {}).get('message'))
tel0 = latest('telemetry') or {}
vwc0 = (tel0.get('soil') or {}).get('vwc_pct')
today0 = (tel0.get('flow') or {}).get('today_l') or 0
log('Antes: suelo %s %%VWC, hoy %s L, tinaco %s %%' % (vwc0, today0, (tel0.get('tank') or {}).get('level_pct')))

# --- Riego completo de 2 L ---
a = cmd({'cmd': 'START_MANUAL', 'liters': 2.0})
check('START_MANUAL 2 L aceptado', a and a.get('status') == 'OK', (a or {}).get('message'))
fv, fp, flows, end, st, up0 = watch(150)
check('Abre primero la válvula y luego la bomba (separación ~1.5 s)', fv and fp and fp - fv >= 0.8,
      'válvula->bomba %.1f s' % ((fp - fv) if fv and fp else -1))
check('Pasa agua (caudal medido)', len(flows) > 0 and max(flows) > 0.5, 'caudal %s L/min' % (round(sum(flows) / len(flows), 2) if flows else 0))
check('Riego termina en TARGET con ~2 L', end and end.get('result') == 'TARGET' and abs((end.get('delivered_l') or 0) - 2.0) < 0.25,
      {k: (end or {}).get(k) for k in ('result', 'delivered_l', 'duration_s', 'pulses')})
time.sleep(5)
st2 = latest('state') or {}
check('Sin reinicio durante el riego', (st2.get('uptime_s') or 0) > up0, 'uptime %s -> %s s' % (up0, st2.get('uptime_s')))
check('Bomba y válvula apagadas al terminar', not st2.get('pump') and not st2.get('valve'), 'B=%s V=%s' % (st2.get('pump'), st2.get('valve')))

# --- Riego interrumpido con STOP ---
time.sleep(5)
a = cmd({'cmd': 'START_MANUAL', 'liters': 1.0})
check('START_MANUAL 1 L aceptado', a and a.get('status') == 'OK', (a or {}).get('message'))
fv, fp, flows, end, st, up0 = watch(60, stop_at=10)
check('STOP detiene el riego (STOP_CMD)', end and end.get('result') == 'STOP_CMD',
      {k: (end or {}).get(k) for k in ('result', 'delivered_l', 'duration_s')})
time.sleep(5)
st3 = latest('state') or {}
check('Tras STOP: bomba y válvula apagadas, sin reinicio', not st3.get('pump') and not st3.get('valve') and (st3.get('uptime_s') or 0) > up0,
      'B=%s V=%s uptime %s' % (st3.get('pump'), st3.get('valve'), st3.get('uptime_s')))

# --- Registro en la Pi, pronóstico e IA ---
time.sleep(8)
r = subprocess.run(SSH + ["cd ~/equipo2_proyecto && python3 -c \"import sqlite3,time;c=sqlite3.connect('file:database/riego_final.db?mode=ro',uri=True);"
                          "print(c.execute(\\\"select count(*) from irrigation_events where device='esp32_principal' and ts_start>?\\\",(int(time.time())-900,)).fetchone()[0]);"
                          "print(c.execute(\\\"select ok,http from weather_fetches where origin='servidor' order by ts_fetch desc limit 1\\\").fetchone())\""],
                   capture_output=True, text=True)
lines = r.stdout.split()
check('La Pi guardó los 2 riegos en su base de datos', lines and int(lines[0]) >= 2, r.stdout.strip().replace('\n', ' | '))
wx = latest('weather') or [j for t, k, rr, j in msgs if k == 'weather'][-1]
check('Pronóstico Open-Meteo vigente en el ESP32', wx.get('fresh'), 'ET0 24h %s mm, lluvia 6h %s mm' % (wx.get('et0_24h_mm'), wx.get('next6h_precip_mm')))
ia = ([j for t, k, rr, j in msgs if k == 'ia'] or [{}])[-1]
log('IA: %s, %s riegos aprendidos, %s h de secado' % (ia.get('status'), ia.get('events_learned'), ia.get('drying_hours_learned')))
tel1 = latest('telemetry') or {}
log('Después: suelo %s %%VWC (antes %s), hoy %s L' % ((tel1.get('soil') or {}).get('vwc_pct'), vwc0, (tel1.get('flow') or {}).get('today_l')))

# --- Producto final: modo AUTOMATICO ---
a = cmd({'cmd': 'SET_MODE', 'mode': 'AUTOMATICO'})
check('Modo AUTOMATICO activado (recolecta datos para la IA)', a and a.get('status') == 'OK', (a or {}).get('message'))
c.loop_stop()
n_ok = sum('[PASS]' in x for x in RES)
n_bad = sum('[FAIL]' in x for x in RES)
log('RESULTADO: %d PASS, %d FAIL' % (n_ok, n_bad))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write('\n'.join(RES) + '\n')
print('Guardado en', OUT)
