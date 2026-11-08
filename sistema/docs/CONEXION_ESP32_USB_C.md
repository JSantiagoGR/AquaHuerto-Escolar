# Conexión de la segunda ESP32 por USB-C

Conexión: **USB-C de la laptop → cable USB-C a USB-C → ESP32 de pruebas**. El cable solo alimenta la placa y transporta datos; **nunca** se alimenta una carga de 12 V por USB.

## Detección (verificada el 2026-10-11)

| Dato | Valor | Cómo se obtuvo |
|---|---|---|
| Reconocida por Windows | Sí: `Silicon Labs CP210x USB to UART Bridge (COM8)` | `Get-PnpDevice -PresentOnly` |
| Puerto COM real | **COM8** | (coincide con la placa anterior porque el CP210x de ambas tiene número de serie `0001`) |
| Puente USB | **CP210x** (no CH340, no USB-Serial/JTAG nativo) | VID 10C4 / PID EA60 |
| Chip | **ESP32-D0WD-V3, revisión v3.1**, doble núcleo, 240 MHz, cristal 40 MHz | `python -m esptool --port COM8 flash-id` |
| MAC | `xx:xx:xx:xx:xx:xx` — **distinta** de la placa anterior (`xx:xx:xx:xx:xx:xx`) | esptool |
| Flash | 4 MB (fabricante 0x68, dispositivo 0x4016) | esptool |
| Cable USB-C con datos | Sí (esptool se comunicó y leyó/escribió la flash) | |
| BOOT/RESET manual | **No hace falta**: el auto-reset por DTR/RTS funcionó en todas las operaciones | |
| Baudios fiables | 115200. A 460800 la lectura falló ("Packet content transfer stopped"), igual que con la placa anterior | |

Firmware que traía: el de la **Práctica 4 MQTT** (mensajes `RIEGO: WiFi desconectado -> bomba OFF`, topics `equipo2/...`, bomba en GPIO2).

## Respaldo antes de flashear

Flash completa respaldada en 4 bloques de 1 MB (115200 baudios, reintentos):
`backups\esp32_casa_flash_original\flash_20500d1a0054_4MB.bin` — SHA-256
`E9DE0AF48C1D25FE74A19950B0CB2227415508A874E4076720406DB20A0ACEE5`.

Restaurar el firmware de la Práctica 4 (si algún día se necesita):

```bash
python -m esptool --port COM8 --baud 115200 write-flash 0x0 backups\esp32_casa_flash_original\flash_20500d1a0054_4MB.bin
```

## Flasheo realizado (con autorización del usuario)

```bash
idf.py -p COM8 -b 115200 erase-flash flash      # primera vez (NVS limpia)
idf.py -p COM8 -b 115200 app-flash              # actualizaciones: conserva NVS (Wi-Fi/broker)
```

Verificado: `Hash of data verified`, arranque correcto, **SELFTEST 49/49 PASS en la placa**.

## Monitor serial

`esp_idf_monitor` reinicia la placa en modo descarga; se usa el monitor sin DTR/RTS:

```bash
python -m serial.tools.miniterm COM8 115200 --dtr 0 --rts 0 --eol CRLF --encoding utf-8
```

o la herramienta del proyecto (envía comandos y muestra la respuesta sin reiniciar):

```bash
.venv\Scripts\python.exe firmware\tools\serial_cmd.py COM8 10 "ESTADO" "RED"
```

## Estado de las salidas

La placa solo tiene el cable USB-C (confirmado por el usuario). El firmware arranca en **perfil A (pruebas), modo MANUAL y potencia deshabilitada**: los GPIO de bomba y válvula quedan en nivel inactivo.
