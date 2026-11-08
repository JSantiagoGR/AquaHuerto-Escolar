"""Prueba completa por USB: riega N litros y registra TODOS los sensores y actuadores mientras riega.

Lee la consola del ESP32 cada ~2 s (ESTADO) y las líneas "RIEGO ..." de cada segundo.
Guarda tests/resultados/riego_<litros>L_<fecha>.csv y muestra un resumen.
Uso:  python tests/prueba_riego_registro.py COM8 2
"""
import csv
import os
import re
import sys
import time

import serial

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = sys.argv[1] if len(sys.argv) > 1 else "COM8"
LITROS = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
PRE_S, POST_S, MAX_S = 6, 12, 200

s = serial.Serial()
s.port, s.baudrate, s.timeout, s.dtr, s.rts = PORT, 115200, 0.2, False, False
s.open()


def send(c):
    s.write((c + "\r\n").encode())
    time.sleep(0.25)


def read(t):
    end, b = time.time() + t, b""
    while time.time() < end:
        b += s.read(4096)
    return b.decode("utf-8", "replace")


def g(rx, txt, n=1, cast=str):
    m = re.search(rx, txt)
    return cast(m.group(n)) if m else None


rows, riego_lines, t0 = [], [], time.time()


def muestra(fase):
    send("ESTADO")
    o = read(1.8)
    for line in o.splitlines():
        if line.startswith("RIEGO ") or "INICIADO" in line or "FIN" in line.upper() and "RIEGO" in line:
            riego_lines.append((round(time.time() - t0, 1), line.strip()))
    r = {
        "t_s": round(time.time() - t0, 1), "fase": fase,
        "estado": g(r"Estado: (\S+)", o),
        "bomba": g(r"Bomba: logica \S+ / fisica (\S+)", o),
        "valvula": g(r"Valvula: logica \S+ / fisica (\S+)", o),
        "flujo_lpm": g(r"Flujo: ([\d.]+) L/min", o, 1, float),
        "pulsos": g(r"Pulsos (\d+)", o, 1, int),
        "suelo_mV": g(r"Suelo: \S+ [-\d.]+ %VWC \((\d+) mV", o, 1, int),
        "suelo_vwc": g(r"Suelo: \S+ ([-\d.]+) %VWC", o, 1, float),
        "suelo_estado": g(r"Suelo: .*?mV, (\S+)\)", o),
        "tinaco_cm": g(r"Tinaco: \S+ dist ([\d.]+) cm", o, 1, float),
        "tinaco_estado": g(r"Tinaco: .*\((\S+)\)", o),
        "temp_c": g(r"Ambiente: \S+ ([-\d.]+) C", o, 1, float),
        "hr_pct": g(r"Ambiente: \S+ [-\d.]+ C ([\d.]+) %HR", o, 1, float),
    }
    rows.append(r)
    print("%5.1fs %-9s %-16s B:%-3s V:%-3s %5s L/min pulsos %-5s | suelo %4s mV %-14s | tinaco %6s cm %-9s | %s C %s %%"
          % (r["t_s"], fase, r["estado"], r["bomba"], r["valvula"], r["flujo_lpm"], r["pulsos"], r["suelo_mV"],
             r["suelo_estado"], r["tinaco_cm"], r["tinaco_estado"], r["temp_c"], r["hr_pct"]), flush=True)
    return r


send("LOG ON")
read(0.5)
end = time.time() + PRE_S
while time.time() < end:
    muestra("antes")
r = muestra("antes")
if r["estado"] == "FAULT":
    send("CLEAR ALL")
    read(1.5)
send("START %g" % LITROS)
out = read(2.5)
print([l.strip() for l in out.splitlines() if "RIEGO" in l or "OK:" in l or "ERROR" in l])
termino = None
while time.time() - t0 < MAX_S:
    r = muestra("riego" if termino is None else "despues")
    if termino is None and r["estado"] in ("IDLE", "FAULT", "INFILTRATION", "EVENT_WAIT") and r["t_s"] > PRE_S + 6:
        termino = time.time()
    if termino and time.time() - termino > POST_S:
        break
send("LOG OFF")
read(0.5)
send("HISTORIAL")
h = read(2)
ultimo = next((l.strip() for l in h.splitlines() if re.match(r"\s*1\)", l)), "")
s.close()

path = os.path.join(ROOT, "tests", "resultados", "riego_%gL_%s.csv" % (LITROS, time.strftime("%Y%m%d_%H%M")))
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("\nULTIMO EVENTO:", ultimo)
print("Lineas de riego (cada segundo):")
for t, l in riego_lines[-6:]:
    print("  ", t, l)
d = [r["tinaco_cm"] for r in rows if r["tinaco_cm"]]
print("Ultrasonico: %d lecturas validas, min %.1f cm, max %.1f cm" % (len(d), min(d), max(d)) if d else "Ultrasonico: sin lecturas validas (sin eco)")
print("CSV:", path)
