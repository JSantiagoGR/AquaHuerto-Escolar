"""Muestra en vivo la lectura del ultrasónico del tinaco (por USB, consola del ESP32) para acomodar el sensor.
Espera solo a que se conecte el ESP32 y se reconecta si se desconecta el cable.
Uso:  python tests/ver_tinaco_en_vivo.py [COM8]      Ctrl+C para salir.
"""
import re
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM8'
EXPLICA = {'OK': 'lectura válida', 'SIN_ECO': 'no regresó el eco (no ve nada o cable flojo)',
           'INESTABLE': 'las mediciones no coinciden (rebotes o sensor inclinado)',
           'FUERA_DE_RANGO': 'más lejos que el fondo del tinaco (no apunta al agua)'}

print('Ultrasónico del tinaco en vivo por USB (%s), una lectura cada 10 s. Ctrl+C para salir.' % PORT)
print('Con el agua a 25-30 cm del sensor debe marcar OK, ~25-30 cm y nivel ~85 %.\n', flush=True)
avisado = False
try:
    while True:
        try:
            s = serial.Serial()
            s.port, s.baudrate, s.timeout = PORT, 115200, 0.3
            s.dtr = False
            s.rts = False
            s.open()
        except serial.SerialException:
            if not avisado:
                print(time.strftime('%H:%M:%S'), 'esperando que se conecte el ESP32 por USB...', flush=True)
                avisado = True
            time.sleep(2)
            continue
        print(time.strftime('%H:%M:%S'), 'ESP32 conectado, leyendo...', flush=True)
        avisado, buf = False, b''
        try:
            while True:
                buf += s.read(4096)
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    m = re.search(r'TINACO (\S+) ([0-9.]+) cm', line.decode('utf-8', 'replace'))
                    if m:
                        st, d = m.group(1), float(m.group(2))
                        pct = max(0.0, min(100.0, (117 - d) / 105 * 100))
                        print('%s  %-15s distancia %6.1f cm  nivel %3.0f %%   %s' % (
                            time.strftime('%H:%M:%S'), st, d, pct, EXPLICA.get(st, '')), flush=True)
        except serial.SerialException:
            print(time.strftime('%H:%M:%S'), 'se desconectó el USB', flush=True)
            try:
                s.close()
            except Exception:
                pass
except KeyboardInterrupt:
    pass
