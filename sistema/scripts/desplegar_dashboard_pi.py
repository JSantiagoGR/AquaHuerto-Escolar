"""Despliega SOLO el flujo 'final' (dashboard Equipo 2 Proyecto) en la instancia propia de la Raspberry Pi (1881).
Respalda el flujo anterior en ~/equipo2_proyecto/backups/ y no toca el Node-RED del profesor (1880), Mosquitto
ni la configuración del ESP32.   Uso:  python scripts/desplegar_dashboard_pi.py   (en la red RouterHuerto1)
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSH = ['ssh', '-i', os.path.expanduser('~/.ssh/equipo2_pi'), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'pi@raspberrypi.local']
flow = os.path.join(ROOT, 'dashboard', 'export', 'flows_riego_final.json')
stamp = time.strftime('%Y%m%d_%H%M')
with open(flow, 'rb') as f:
    r = subprocess.run(SSH + ['cp ~/equipo2_proyecto/dashboard/export/flows_riego_final.json '
                              '~/equipo2_proyecto/backups/flows_riego_final.antes_%s.json && '
                              'cat > ~/equipo2_proyecto/dashboard/export/flows_riego_final.json' % stamp], stdin=f, capture_output=True)
if r.returncode:
    sys.exit('No se pudo llegar a la Pi (¿estás en RouterHuerto1?): ' + r.stderr.decode('utf-8', 'replace').strip())
r = subprocess.run(SSH + ['cd ~/equipo2_proyecto && python3 nodered/desplegar_flows.py --entorno final '
                          '--url http://127.0.0.1:1881 --env-file configs/secrets/credenciales_final.env'],
                   capture_output=True, text=True)
print('Dashboard en la Pi:', ((r.stdout or r.stderr).strip().splitlines() or ['sin respuesta'])[-1])
print('Respaldo anterior: ~/equipo2_proyecto/backups/flows_riego_final.antes_%s.json' % stamp)
