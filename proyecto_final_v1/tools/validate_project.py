"""Validaciones estáticas del proyecto (sin hardware).

1. Conflictos de GPIO en main/board.h (repetidos, strapping, flash, UART0, solo entrada).
2. JSON válido en EJEMPLOS_MQTT.json y node-red/*.json.
3. Que los comandos de EJEMPLOS_MQTT.json existan en el firmware (commands.c).
4. Que ninguna documentación contenga la contraseña Wi-Fi de sdkconfig.secrets.

Uso: python tools/validate_project.py
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = []
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1) Pines
board = open(os.path.join(ROOT, "main", "board.h"), encoding="utf-8").read()
pins = {}
for name, num in re.findall(r"#define\s+(PIN_\w+)\s+GPIO_NUM_(\d+)", board):
    pins[name] = int(num)
outputs = {"PIN_PUMP", "PIN_VALVE", "PIN_PING", "PIN_DHT22", "PIN_EC5_POWER"}
forbidden = {0: "strapping", 2: "strapping", 5: "strapping", 12: "strapping", 15: "strapping",
             1: "UART0", 3: "UART0", **{g: "flash" for g in range(6, 12)}}
seen = {}
for name, gpio in pins.items():
    if gpio in seen:
        errors.append(f"GPIO{gpio} repetido: {seen[gpio]} y {name}")
    seen[gpio] = name
    if gpio in forbidden:
        errors.append(f"{name} usa GPIO{gpio} ({forbidden[gpio]})")
    if name in outputs and gpio >= 34:
        errors.append(f"{name} es salida en GPIO{gpio} (solo entrada)")
adc = re.search(r"EC5_ADC_CHANNEL\s+ADC_CHANNEL_(\d+)", board)
if pins.get("PIN_EC5_ADC") != 34 or not adc or adc.group(1) != "6":
    errors.append("EC-5: GPIO34 debe corresponder a ADC1_CH6")
print("PINES:", ", ".join(f"{k}=GPIO{v}" for k, v in pins.items()))

# 2) JSON
json_files = [os.path.join(ROOT, "EJEMPLOS_MQTT.json")] + glob.glob(os.path.join(ROOT, "node-red", "*.json"))
for jf in json_files:
    try:
        json.load(open(jf, encoding="utf-8"))
        print("JSON OK:", os.path.relpath(jf, ROOT))
    except Exception as e:  # noqa: BLE001
        errors.append(f"JSON invalido {jf}: {e}")

# 3) Comandos de ejemplo existentes en el firmware
cmds_src = open(os.path.join(ROOT, "main", "commands.c"), encoding="utf-8").read()
known = set(re.findall(r'\{"([A-Z_]+)",\s+C_', cmds_src))
try:
    ex = json.load(open(os.path.join(ROOT, "EJEMPLOS_MQTT.json"), encoding="utf-8"))
    for item in ex.get("comandos", []):
        c = item["payload"].get("cmd")
        if c not in known:
            errors.append(f"Comando de ejemplo no implementado: {c}")
    print(f"COMANDOS: {len(ex.get('comandos', []))} ejemplos verificados contra {len(known)} comandos del firmware")
except Exception as e:  # noqa: BLE001
    errors.append(f"No se pudieron verificar los ejemplos: {e}")

# 4) Secretos fuera de la documentación
secrets = os.path.join(ROOT, "sdkconfig.secrets")
if os.path.exists(secrets):
    m = re.search(r'CONFIG_RIEGO_WIFI_PASSWORD="([^"]*)"', open(secrets, encoding="utf-8").read())
    pw = m.group(1) if m else ""
    if pw:
        for f in glob.glob(os.path.join(ROOT, "**", "*.*"), recursive=True):
            rel = os.path.relpath(f, ROOT)
            if rel.startswith(("build", "managed_components")) or rel in ("sdkconfig", "sdkconfig.secrets", "sdkconfig.old"):
                continue
            if f.endswith((".md", ".json", ".c", ".h", ".py", ".txt", ".yml", ".csv")):
                if pw in open(f, encoding="utf-8", errors="ignore").read():
                    errors.append(f"La contrasena Wi-Fi aparece en {rel}")
    print("SECRETOS: revisados (la contrasena no se imprime)")

print()
if errors:
    print("ERRORES:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("VALIDACION OK: sin conflictos de GPIO, JSON validos, comandos existentes, sin secretos expuestos")
