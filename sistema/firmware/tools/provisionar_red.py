"""Configura la red del ESP32 por USB (consola serial) SIN recompilar.

- Wi-Fi: pide la contraseña de forma oculta (getpass); no se guarda en ningún
  archivo de la computadora ni se imprime. Se envía en hexadecimal para
  admitir espacios y símbolos.
- MQTT: toma usuario/contraseña del archivo local de credenciales
  (configs/secrets/credenciales_casa.env), que no se exporta.
- Broker: por defecto usa la IP actual de esta computadora en la red local.

Ejemplos:
  python provisionar_red.py --port COM8 --red casa --ssid "RED_DE_CASA_2.4"
  python provisionar_red.py --port COM8 --solo-mqtt
  python provisionar_red.py --port COM8 --red huerto --ssid RouterHuerto1 --broker raspberrypi.local \
         --topic huerto/final/esp32_principal --device esp32_principal --entorno final --env-file <otro.env>
"""
import argparse
import getpass
import os
import re
import socket
import sys
import time

import serial

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_ENV = os.path.join(ROOT, "configs", "secrets", "credenciales_casa.env")
SECRET_PATTERNS = []


def local_ip():
    """IP de esta computadora en la red local (sin enviar datos)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.1.254", 9))
        return s.getsockname()[0]
    finally:
        s.close()


def read_env(path):
    vals = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals


def hexs(text):
    return text.encode("utf-8").hex()


def mask(line):
    for sec in SECRET_PATTERNS:
        if sec and sec in line:
            line = line.replace(sec, "********")
    return line


def send(port, lines, wait):
    s = serial.Serial()
    s.port, s.baudrate, s.timeout, s.dtr, s.rts = port, 115200, 0.1, False, False
    s.open()
    out = bytearray()
    for ln in lines:
        s.write((ln + "\r\n").encode())
        t = time.time() + 0.8
        while time.time() < t:
            out += s.read(4096)
    t = time.time() + wait
    while time.time() < t:
        out += s.read(4096)
        txt = out.decode("utf-8", "replace")
        if "Conectado al broker" in txt:
            t = min(t, time.time() + 3)
    s.close()
    return out.decode("utf-8", "replace")


def main():
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--red", default="casa", choices=["casa", "tec", "huerto"])
    ap.add_argument("--ssid")
    ap.add_argument("--broker", help="IP o URI del broker (por defecto: IP de esta PC)")
    ap.add_argument("--topic", default="huerto/casa/esp32_01")
    ap.add_argument("--device", default="esp32_01")
    ap.add_argument("--entorno", default="casa", choices=["casa", "final"])
    ap.add_argument("--env-file", default=DEFAULT_ENV)
    ap.add_argument("--solo-mqtt", action="store_true", help="No cambia el Wi-Fi")
    ap.add_argument("--espera", type=float, default=40)
    a = ap.parse_args()

    cmds = []
    if not a.solo_mqtt:
        ssid = a.ssid or input("SSID de la red Wi-Fi de 2.4 GHz: ").strip()
        pwd = getpass.getpass("Contrasena Wi-Fi (no se muestra): ")
        if pwd and not (8 <= len(pwd) <= 63):
            sys.exit("La contrasena WPA2 debe tener entre 8 y 63 caracteres")
        SECRET_PATTERNS.append(pwd)
        cmds.append(f"WIFIHEX {a.red} {hexs(ssid)} {hexs(pwd) if pwd else ''}".strip())
        cmds.append(f"WIFI PREF {a.red}")

    env = read_env(a.env_file)
    user, pw = env["MQTT_ESP32_USER"], env["MQTT_ESP32_PASS"]
    SECRET_PATTERNS.append(pw)
    broker = a.broker or local_ip()
    uri = broker if broker.startswith("mqtt") else f"mqtt://{broker}:1883"
    cmds += [
        f"MQTT URI {uri}",
        f"MQTTHEX {hexs(user)} {hexs(pw)}",
        f"MQTT TOPIC {a.topic}",
        f"DEVICE {a.device} {a.entorno}",
        "RED APLICAR",
    ]
    print(f"Configurando {a.port}: broker {uri}, usuario {user}, topic {a.topic}, dispositivo {a.device}")
    out = send(a.port, cmds, a.espera)
    keep = re.compile(r"OK:|ERROR|wifi:|mqtt:|Conectado|Intentando|desconect|Sin exito|rechazo|Broker", re.I)
    for line in out.splitlines():
        if keep.search(line):
            print(mask(line))
    ok_wifi = "Conectado, IP" in out
    ok_mqtt = "Conectado al broker" in out
    print("\nRESULTADO: Wi-Fi %s | MQTT %s" % ("CONECTADO" if ok_wifi else "sin conexion todavia",
                                             "CONECTADO" if ok_mqtt else "sin conexion todavia"))
    return 0 if (ok_mqtt or a.solo_mqtt) else 1


if __name__ == "__main__":
    sys.exit(main())
