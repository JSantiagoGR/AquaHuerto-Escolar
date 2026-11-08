"""Muestra en vivo la señal Wi-Fi del ESP32 (por USB) para encontrar la mejor posición de la placa.
Uso:  python tests/ver_senal_wifi.py [COM8]      Ctrl+C para salir.
"""
import re
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM8'
s = serial.Serial()
s.port, s.baudrate, s.timeout = PORT, 115200, 0.2
s.dtr = False
s.rts = False
s.open()
print('Señal Wi-Fi del ESP32 (%s). Mueve o gira la placa y observa. Ctrl+C para salir.' % PORT)
print('Meta: -70 dBm o mejor (más cerca de 0 es mejor).\n', flush=True)


def nota(r):
    return 5 if r >= -60 else 4 if r >= -65 else 3 if r >= -70 else 2 if r >= -75 else 1


try:
    while True:
        s.reset_input_buffer()
        s.write(b'RED\r\n')
        t0, buf, m = time.time(), b'', None
        while time.time() - t0 < 2.5 and not m:
            buf += s.read(4096)
            m = re.search(rb'Estado: Wi-Fi (\S+) \(\S+ (\S+), (-?\d+) dBm.*?MQTT (\S+)', buf)
        if m:
            r = int(m.group(3))
            print('%s  señal %4d dBm  [%s]  %d/5   Wi-Fi %-12s MQTT %s' % (time.strftime('%H:%M:%S'), r, '#' * nota(r) + '.' * (5 - nota(r)),
                  nota(r), m.group(1).decode(), m.group(4).decode()), flush=True)
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    s.close()
