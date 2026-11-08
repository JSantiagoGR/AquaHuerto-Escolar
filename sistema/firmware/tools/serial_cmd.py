"""Envia comandos a la consola del ESP32 y muestra la salida, sin reiniciar la placa.

Uso:  python serial_cmd.py COM8 [segundos] ["COMANDO 1" "COMANDO 2" ...]
DTR/RTS quedan en 0 para no provocar un reinicio ni el modo de descarga.
"""
import sys
import time

import serial


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    port = sys.argv[1]
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    cmds = sys.argv[3:]
    s = serial.Serial()
    s.port = port
    s.baudrate = 115200
    s.timeout = 0.1
    s.dtr = False
    s.rts = False
    s.open()
    out = bytearray()
    t0 = time.time()
    for c in cmds:
        s.write((c + "\r\n").encode())
        t_end = time.time() + max(1.0, secs / max(1, len(cmds)))
        while time.time() < t_end:
            out += s.read(4096)
    while time.time() - t0 < secs:
        out += s.read(4096)
    s.close()
    sys.stdout.write(out.decode("utf-8", "replace"))


if __name__ == "__main__":
    main()
