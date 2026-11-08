"""Lectura en vivo del EC-5 en GPIO34 (por USB) para probar el sensor alimentado directo a 3.3 V.
Usa el diagnóstico EC5 PRUEBA del firmware y convierte los mV con la misma fórmula (Actividad 2.2, escala theta).
Uso:  python tests/ver_ec5_en_vivo.py [COM8]      Ctrl+C para salir.
"""
import re
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM8'
SLOPE, OFFSET = 0.08146067, -23.932584


def vwc(mv):
    s = SLOPE * mv + OFFSET
    if s <= 0:
        return 0.0
    f = s / 100.0
    return None if f >= 0.95 else 100.0 * f / (1.0 - f)


def lectura(mv):
    if mv < 200:
        return 'SIN SEÑAL (no llega nada a GPIO34)'
    if mv < 420:
        return 'al aire / tierra muy seca'
    if mv < 1300:
        return 'en tierra (lectura normal)'
    return 'DEMASIADO ALTO (¿5 V o señal mal conectada?)'


s = serial.Serial()
s.port, s.baudrate, s.timeout = PORT, 115200, 0.2
s.dtr = False
s.rts = False
s.open()
print('EC-5 en vivo (GPIO34, %s). Ctrl+C para salir.' % PORT)
print('Esperado: al aire ~250-400 mV; en tierra húmeda 500-900 mV.\n', flush=True)
try:
    while True:
        s.reset_input_buffer()
        s.write(b'EC5 PRUEBA\r\n')
        t0, buf = time.time(), b''
        while time.time() - t0 < 9 and b'EC5 PRUEBA: fin' not in buf:
            buf += s.read(4096)
        vals = [int(v) for v in re.findall(rb'GPIO34=\s*(\d+) mV', buf)]
        if vals:
            mv = sum(vals) / len(vals)
            v = vwc(mv)
            print('%s  GPIO34 = %5.0f mV (min %d, max %d)  ->  %s %%VWC   %s' % (
                time.strftime('%H:%M:%S'), mv, min(vals), max(vals), '%.1f' % v if v is not None else '>100', lectura(mv)), flush=True)
        else:
            print(time.strftime('%H:%M:%S'), 'sin respuesta del ESP32', flush=True)
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    s.close()
