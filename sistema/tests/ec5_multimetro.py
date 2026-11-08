"""Ayuda para medir el EC-5 con multímetro: deja la excitación (GPIO25) ENCENDIDA 30 s, la apaga unos segundos y repite.
Muestra en vivo cuándo está encendida y cuánto lee el GPIO34.
Uso:  python tests/ec5_multimetro.py [COM8]      Ctrl+C para salir.
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
print('Medición con multímetro (%s). Ctrl+C para salir.' % PORT)
print('Mientras diga ENCENDIDO: blanco-GND debe dar ~3.3 V; rojo-GND 0.25-1 V si el sensor está bien.\n', flush=True)
try:
    while True:
        s.reset_input_buffer()
        s.write(b'EC5 PRUEBA 30\r\n')
        t0, buf, fin = time.time(), b'', False
        while time.time() - t0 < 36 and not fin:
            buf += s.read(4096)
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                if b'ENCENDIDA' in line:
                    print('\n>>> GPIO25 ENCENDIDO 30 s: MIDE AHORA', flush=True)
                elif b'excitacion APAGADA' in line:
                    print('>>> GPIO25 APAGADO', flush=True)
                elif b'EC5 PRUEBA: fin' in line:
                    fin = True
                m = re.search(rb'(\d+\.\d) s\s+GPIO34=\s*(\d+) mV', line)
                if m and float(m.group(1)) % 2 == 0:
                    print('    %s  GPIO34 = %s mV' % (time.strftime('%H:%M:%S'), m.group(2).decode()), flush=True)
        print('--- pausa 3 s ---', flush=True)
        time.sleep(3)
except KeyboardInterrupt:
    pass
finally:
    s.close()
