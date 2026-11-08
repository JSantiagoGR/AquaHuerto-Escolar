"""Ejecuta el autodiagnóstico SELFTEST en el ESP32 conectado y guarda el resultado.

No reinicia el ESP32 (DTR/RTS inactivos) y no activa salidas: SELFTEST trabaja
sobre una copia de la lógica con entradas y reloj virtuales.

Uso:
    python tools/run_selftest.py [COM8] [archivo_salida.txt]
"""
import sys
import time

import serial

port = sys.argv[1] if len(sys.argv) > 1 else "COM8"
out_path = sys.argv[2] if len(sys.argv) > 2 else "resultado_selftest.txt"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

s = serial.Serial()
s.port = port
s.baudrate = 115200
s.timeout = 0.05
s.dtr = False
s.rts = False
s.open()
time.sleep(0.3)
s.reset_input_buffer()
s.write(b"SELFTEST\r\n")

buf = b""
t_end = time.monotonic() + 60
while time.monotonic() < t_end:
    buf += s.read(s.in_waiting or 1)
    if b"SELFTEST FIN" in buf:
        time.sleep(0.2)
        buf += s.read(s.in_waiting or 1)
        break
s.close()

lines = [l for l in buf.decode("utf-8", "replace").splitlines() if "SELFTEST" in l]
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
fails = [l for l in lines if " FAIL" in l and "FIN" not in l]
print(f"\nResultado guardado en {out_path}")
sys.exit(1 if fails or not any("SELFTEST FIN" in l for l in lines) else 0)
