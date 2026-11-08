"""Diagnóstico completo del ESP32 del proyecto (esp32_principal) por la Raspberry Pi, sin USB.
Escucha 45 s y resume conexión, sensores, hora, pronóstico, IA, potencia y modo.
Uso:  python tests/diagnostico_pi.py
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
B = 'huerto/final/esp32_principal'
last, tel, offl = {}, [], []


def on(cl, u, m):
    j = json.loads(m.payload)
    k = m.topic.rsplit('/', 1)[1]
    if k == 'telemetry' and not m.retain:
        tel.append(j)
    if k == 'status' and not m.retain and not j.get('online'):
        offl.append(time.strftime('%H:%M:%S'))
    if not m.retain or k not in last:
        last[k] = j


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='diag-%d' % time.time())
c.username_pw_set(env['MQTT_ADMIN_USER'], env['MQTT_ADMIN_PASS'])
c.on_message = on
c.connect('raspberrypi.local', 1884, 10)
c.subscribe(B + '/#', 1)
c.loop_start()
time.sleep(45)
c.loop_stop()

st, cfg, ia, wx = last.get('state', {}), last.get('config', {}).get('params', {}), last.get('ia', {}), last.get('weather', {})
print('CONEXION  online=%s  uptime=%s s  rssi=%s dBm  telemetrias=%d en 45 s  desconexiones=%s' % (
    last.get('status', {}).get('online'), st.get('uptime_s'), st.get('rssi'), len(tel), offl or 'ninguna'))
print('ESTADO    modo=%s  estado=%s  potencia=%s  hora_valida=%s  alarmas=%s  fw=%s' % (
    st.get('mode'), st.get('state'), st.get('power_outputs'), st.get('time_valid'), st.get('alarms'), st.get('fw')))
if tel:
    x = tel[-1]
    s, k, e, f = x.get('soil', {}), x.get('tank', {}), x.get('env', {}), x.get('flow', {})
    print('SUELO     %s %%VWC  %s mV  %s' % (s.get('vwc_pct'), s.get('mv'), s.get('status')))
    print('TINACO    %s cm  %s %%  %s' % (k.get('distance_cm'), k.get('level_pct'), k.get('status')))
    print('AMBIENTE  %s C  %s %%HR  VPD %s kPa  %s' % (e.get('temp_c'), e.get('rh_pct'), e.get('vpd_kpa'), e.get('status')))
    print('FLUJO     %s L/min  hoy %s L  total %s L' % (f.get('lpm'), f.get('today_l'), f.get('total_l')))
print('PRONOSTICO fresco=%s  edad=%s s  temp=%s  lluvia6h=%s mm  prob=%s %%  ET0_24h=%s mm  fuente=%s' % (
    wx.get('fresh'), wx.get('age_s'), wx.get('temp_c', wx.get('cur_temp')), wx.get('next6_precip', wx.get('rain_6h_mm')),
    wx.get('next6_pprob_max', wx.get('rain_prob_max')), wx.get('et0_24h', wx.get('et0_24h_mm')), (wx.get('source') or '')[:30]))
print('IA        estado=%s  riegos=%s  horas_secado=%s' % (ia.get('status'), ia.get('events_learned'), ia.get('drying_hours_learned')))
print('CONFIG    v%s  objetivo=%s min=%s emerg=%s max=%s  dosis=%s L x %s  max_dia=%s L  valvula->bomba=%s ms' % (
    last.get('config', {}).get('profile_version'), cfg.get('hum_target'), cfg.get('hum_min'), cfg.get('hum_critical'),
    cfg.get('hum_max'), cfg.get('liters_per_cycle'), cfg.get('max_cycles'), cfg.get('max_liters_daily'), cfg.get('valve_lead_ms')))
print('CLAVES pronostico:', sorted(wx.keys())[:25])
