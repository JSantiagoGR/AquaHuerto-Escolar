"""Prueba de integración del firmware COMPLETO en el emulador QEMU de Espressif.

Arranca build/qemu_flash.bin en qemu-system-xtensa (ESP32), conecta la consola
serie emulada por TCP y ejecuta un guion de comandos verificando las
respuestas. En QEMU no hay sensores, Wi-Fi ni salidas reales: el guion usa el
modo SIMULACION del firmware. NO valida hardware.

Uso:
    python tools/qemu_test.py [ruta_qemu] [archivo_resultado]
Requisitos: haber compilado y generado build/qemu_flash.bin:
    python -m esptool --chip esp32 merge-bin --fill-flash-size 4MB -o qemu_flash.bin @flash_args
"""
import os
import re
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QEMU = sys.argv[1] if len(sys.argv) > 1 else (
    r"C:\Espressif\tools\tools\qemu-xtensa\esp_develop_9.2.2_20250817\qemu\bin\qemu-system-xtensa.exe")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "resultado_qemu.txt")
PORT = 5555
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = []
results = []


def emit(line):
    log.append(line)
    print(line, flush=True)


class Console:
    def __init__(self, sock):
        self.s = sock
        self.s.settimeout(0.05)
        self.buf = ""

    def pump(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                data = self.s.recv(4096)
                if not data:
                    break
                text = data.decode("utf-8", "replace")
                self.buf += text
                for ln in text.replace("\r", "").splitlines():
                    if ln.strip():
                        emit("   | " + ln)
            except socket.timeout:
                pass

    def quiet(self, idle=1.5, limit=60):
        """Espera a que la consola emulada deje de transmitir (UART de QEMU lenta)."""
        end = time.monotonic() + limit
        last_len, last_change = len(self.buf), time.monotonic()
        while time.monotonic() < end:
            self.pump(0.2)
            if len(self.buf) != last_len:
                last_len, last_change = len(self.buf), time.monotonic()
            elif time.monotonic() - last_change >= idle:
                return

    def send(self, cmd):
        self.quiet()
        emit(f">>> {cmd}")
        self.buf = ""
        self.s.sendall((cmd + "\r\n").encode())

    def wait_for(self, pattern, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if re.search(pattern, self.buf):
                return True
            self.pump(0.2)
        return bool(re.search(pattern, self.buf))


def check(name, ok, detail=""):
    results.append((name, ok))
    emit(f"[{'PASS' if ok else 'FAIL'}] {name}{'' if ok else ' -> ' + detail}")


IMG = os.path.join(ROOT, "build_qemu", "qemu_flash.bin")


def start_qemu():
    """Arranca el ESP32 emulado (la flash persiste en IMG entre arranques)."""
    args = [QEMU, "-machine", "esp32", "-display", "none",
            "-drive", f"file={IMG},if=mtd,format=raw",
            "-global", "driver=timer.esp32.timg,property=wdt_disable,value=true",
            "-serial", f"tcp:127.0.0.1:{PORT},server,nowait", "-monitor", "none"]
    emit("QEMU: " + " ".join(os.path.basename(a) if a == QEMU else a for a in args))
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sock = None
    for _ in range(50):
        try:
            sock = socket.create_connection(("127.0.0.1", PORT), timeout=1)
            break
        except OSError:
            time.sleep(0.2)
    return proc, sock


def main():
    proc, sock = start_qemu()
    if sock is None:
        emit("No se pudo conectar a la consola de QEMU")
        proc.kill()
        return 2
    c = Console(sock)
    try:
        ok = c.wait_for(r"Escriba AYUDA", 60)
        check("Arranque completo del firmware", ok, "no aparecio el mensaje final de arranque")
        check("Arranque en modo A con potencia deshabilitada",
              "A (PRUEBAS)" in c.buf and "DESHABILITADAS" in c.buf, "banner inesperado")
        c.pump(3)
        c.send("LOG OFF")           # Sin línea periódica: la UART emulada es lenta
        c.pump(1)

        c.send("ESTADO")
        ok = c.wait_for(r"Automatico: NO", 60)
        check("Automatico deshabilitado al encender (modo A)", ok and "Estado: IDLE" in c.buf,
              "estado inicial inesperado")

        c.send("START 1")
        check("START rechazado sin potencia habilitada",
              c.wait_for(r"REJECTED: Salidas de potencia deshabilitadas", 60), "no fue rechazado")
        c.send("AUTO ON")
        check("AUTO ON rechazado sin potencia", c.wait_for(r"REJECTED: No se habilita", 60), "no fue rechazado")

        c.send("SET hum_min 40")
        check("Parametro invalido rechazado (MIN > OBJETIVO)",
              c.wait_for(r"REJECTED: Debe cumplirse MINIMA < OBJETIVO < MAXIMA", 60), "aceptado")
        c.send("HUMEDAD 28 36 46")
        check("Rango de humedad valido guardado", c.wait_for(r"OK: Humedad: minima 28.0", 60), "rechazado")
        c.send("SET pump_max_s 900")
        check("Limite duro de bomba no se puede superar", c.wait_for(r"REJECTED: pump_max_s fuera de limites", 60),
              "aceptado")

        c.send("SELFTEST")
        ok = c.wait_for(r"SELFTEST FIN: (\d+) PASS, (\d+) FAIL", 120)
        m = re.search(r"SELFTEST FIN: (\d+) PASS, (\d+) FAIL", c.buf)
        check(f"SELFTEST de la logica ({m.group(1) if m else '?'} PASS)",
              ok and m and m.group(2) == "0", m.group(0) if m else "sin resultado")

        c.send("SIM ON")
        check("Simulacion activada", c.wait_for(r"SIMULACION ACTIVA", 60), "no se activo")
        c.send("SET min_event_gap_min 0")
        c.wait_for(r"OK:", 60)
        c.pump(2)

        # Riego manual a velocidad real (x1): 1 L a 4 L/min = 15 s
        c.send("SIM VELOCIDAD 1")
        c.send("SIM FLUJO 4")
        c.send("START 1")
        ok = c.wait_for(r"RIEGO TERMINADO \(TARGET\)", 90)
        m = re.search(r"RIEGO TERMINADO \(TARGET\): ([\d.]+) L calculados \((\d+) pulsos\)", c.buf)
        check("Riego manual simulado de 1 L termina por volumen",
              ok and m and 1.0 <= float(m.group(1)) <= 1.02, m.group(0) if m else "sin fin por TARGET")

        c.send("START 1")
        c.wait_for(r"RIEGO MANUAL INICIADO", 60)
        c.send("STOP")
        check("STOP inmediato durante riego", c.wait_for(r"RIEGO TERMINADO \(STOP_CMD\)", 60), "sin STOP_CMD")

        # Procesador de comandos MQTT (mismo código que un mensaje del broker)
        c.send('JSON {"id":"q1","cmd":"GET_STATUS"}')
        check("MQTT: comando valido -> ack OK", c.wait_for(r"MQTT GET_STATUS \(q1\): OK", 60), "sin OK")
        c.send('JSON {"id":"q1","cmd":"GET_STATUS"}')
        check("MQTT: id repetido -> DUPLICATE", c.wait_for(r"\(q1\): DUPLICATE", 60), "no detecto duplicado")
        c.send('JSONRET {"id":"q2","cmd":"START_MANUAL","liters":1}')
        check("MQTT: START retenido -> RETAINED (no riega)",
              c.wait_for(r"\(q2\): RETAINED", 60) and "RIEGO MANUAL INICIADO" not in c.buf, "se ejecuto")
        c.send('JSON {"cmd":"GET_STATUS"}')
        check("MQTT: sin id -> INVALID", c.wait_for(r"INVALID - Falta 'id'", 60), "aceptado sin id")
        c.send('JSON {esto no es json')
        check("MQTT: JSON invalido -> INVALID", c.wait_for(r"INVALID - JSON invalido", 60), "aceptado")
        c.send('JSON {"id":"q3","cmd":"SET_HUMIDITY_RANGE","min":40,"target":35,"max":45}')
        check("MQTT: rango de humedad invalido -> REJECTED",
              c.wait_for(r"\(q3\): REJECTED - Debe cumplirse", 60), "aceptado")
        c.send('JSON {"id":"q4","cmd":"START_MANUAL","liters":50}')
        check("MQTT: volumen fuera de limite -> INVALID", c.wait_for(r"\(q4\): INVALID - Volumen invalido", 60),
              "aceptado")
        c.send('JSON {"id":"q5","cmd":"START_MANUAL","liters":0.5}')
        ok5 = c.wait_for(r"\(q5\): OK", 60)
        c.send('JSON {"id":"q6","cmd":"STOP"}')
        check("MQTT: START_MANUAL y STOP por JSON",
              ok5 and c.wait_for(r"RIEGO TERMINADO \((STOP_CMD|TARGET)\)", 60), "sin inicio/fin")

        c.send("SIM FLUJO 0")
        c.pump(0.5)
        c.send("START 1")
        ok = c.wait_for(r"ALARMA NO_FLOW ACTIVA", 30)
        check("Sin flujo -> alarma NO_FLOW y FAULT", ok and c.wait_for(r"ESTADO -> FAULT", 60), "sin falla")
        c.send("START 1")
        check("START rechazado en FALLA", c.wait_for(r"REJECTED: Sistema en FALLA", 60), "no rechazado")
        c.send("SIM FLUJO 4")
        c.pump(0.5)
        c.send("CLEAR ALL")
        check("CLEAR_ALARM recupera el sistema", c.wait_for(r"OK: Alarmas borradas; estado IDLE", 60), "no recupero")

        # Riego automático con tiempo acelerado x60 (infiltración de 15 min = 15 s)
        c.send("SIM VELOCIDAD 60")
        c.send("SIM SUELO 20")
        c.pump(0.5)
        c.send("SIM HORA 07:00")
        c.pump(0.5)
        c.send("AUTO ON")
        check("AUTO ON aceptado en simulacion", c.wait_for(r"OK: Riego automatico habilitado", 60), "rechazado")
        ok = c.wait_for(r"RIEGO SCHEDULED INICIADO", 40)
        check("Riego automatico por humedad baja en horario", ok, "no inicio")
        ok = c.wait_for(r"DECISION: INFILTRATING", 40)
        check("Espera de infiltracion tras el ciclo", ok, "no entro a infiltracion")
        c.send("SIM SUELO 37")
        ok = c.wait_for(r"EVENTO AUTOMATICO TERMINADO: TARGET_REACHED", 60)
        check("Fin del evento al alcanzar humedad objetivo", ok, "no termino por objetivo")

        c.send("SIM SUELO 20")
        c.pump(0.3)
        c.send("SIM HORA 13:00")
        ok = c.wait_for(r"DECISION: MIDDAY", 40)
        check("Mediodia: riego pospuesto", ok, "sin decision MIDDAY")
        c.send("SIM HORA INVALIDA")
        ok = c.wait_for(r"DECISION: TIME_INVALID", 40)
        check("Sin hora valida: no se riega por horario", ok, "sin decision TIME_INVALID")
        c.send("AUTO OFF")
        c.wait_for(r"OK: Riego automatico deshabilitado", 60)

        c.send("SIM VELOCIDAD 1")
        c.pump(0.3)
        c.send("SIM FLUJO 0.3")
        c.pump(0.3)
        c.send("START 2")
        c.wait_for(r"RIEGO MANUAL INICIADO", 60)
        c.pump(2.0)
        # Corte de energía durante el riego: se mata el emulador y se vuelve a
        # arrancar con la MISMA flash (NVS conservada). (esp_restart dentro de
        # QEMU falla por una limitación del emulador; en la placa funciona.)
        emit("=== CORTE DE ENERGIA SIMULADO (se detiene QEMU durante el riego) ===")
        sock.close()
        proc.kill()
        proc.wait(timeout=10)
        time.sleep(1)
        proc, sock = start_qemu()
        c = Console(sock)
        ok = c.wait_for(r"ALARMA REBOOT_DURING_WATERING ACTIVA", 90)
        check("Reinicio durante riego: no reanuda y alarma", ok, "sin alarma tras reinicio")
        check("Tras reinicio: simulacion desactivada, modo A y potencia deshabilitada",
              "A (PRUEBAS)" in c.buf and "DESHABILITADAS" in c.buf and "RIEGO MANUAL INICIADO" not in c.buf,
              "banner inesperado o riego reanudado")
        c.wait_for(r"Escriba AYUDA", 60)
        c.send("LOG OFF")
        c.send("HISTORIAL")
        check("Historial guardado en NVS (incluye REBOOT)", c.wait_for(r"MANUAL\s+REBOOT", 60), "sin registro")
    finally:
        sock.close()
        proc.kill()

    passed = sum(1 for _, ok in results if ok)
    emit(f"\nQEMU RESULTADO: {passed} PASS, {len(results) - passed} FAIL")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
