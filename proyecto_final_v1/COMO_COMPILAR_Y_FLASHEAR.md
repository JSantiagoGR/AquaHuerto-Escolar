# Cómo compilar, flashear y probar

Proyecto: `C:\ESP32_Riego_Automatico\Proyecto_Final_v1` (ruta ASCII: sin los problemas de la ruta con "ó" de la Prueba 01).
ESP-IDF **v6.0.2** (`C:\esp\v6.0.2\esp-idf`), objetivo `esp32`, puerto habitual **COM8** (CP210x).

## 1. Activar ESP-IDF (PowerShell)
```powershell
. "C:\Espressif\tools\Microsoft.v6.0.2.PowerShell_profile.ps1"
cd C:\ESP32_Riego_Automatico\Proyecto_Final_v1
```

## 2. Compilar
```powershell
idf.py build
```
- La primera vez descarga `espressif/mqtt` y `espressif/cjson` (requiere internet).
- Resultado esperado: `riego_proyecto_final_v1.bin binary size 0xf7…` (~1.0 MB, 34 % libre en la partición de 1.5 MB).
- Sin warnings: ESP-IDF compila con `-Wall -Wextra -Werror`.

## 3. Flashear (a 115200 baudios: a 460800 falló con esta placa)
```powershell
idf.py -p COM8 -b 115200 flash
```
El firmware arranca **siempre** en la versión segura: modo A, salidas de potencia deshabilitadas y automático apagado.

## 4. Monitor serial
`esp_idf_monitor` reinició la placa en modo descarga en la Prueba 01. Use miniterm:
```powershell
python -m serial.tools.miniterm COM8 115200 --dtr 0 --rts 0 --eol CRLF --encoding utf-8
```
Salir: `Ctrl+]`. Escriba `AYUDA`.

## 5. Pruebas
| Prueba | Comando | Requiere |
|---|---|---|
| Autodiagnóstico de la lógica en la placa | `python tools\run_selftest.py COM8` | ESP32 conectado |
| Firmware completo en emulador | ver §6 | Nada (QEMU) |
| Validación estática | `python tools\validate_project.py` | Nada |
| Regenerar flow de Node-RED | `python tools\generar_flow_node_red.py` | Nada |

## 6. Emulador QEMU (sin placa)
QEMU no emula Wi-Fi ni el ADC: se usa una compilación aparte, sin red, en `build_qemu`.
```powershell
idf.py -B build_qemu -D SDKCONFIG=build_qemu/sdkconfig -D "SDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.qemu" build
cd build_qemu
python -m esptool --chip esp32 merge-bin --fill-flash-size 4MB -o qemu_flash.bin "@flash_args"
cd ..
python tools\qemu_test.py
```
QEMU se instaló con `python %IDF_PATH%\tools\idf_tools.py install qemu-xtensa` (desde el archivo ya descargado en `C:\Espressif\dist`).

## 7. VS Code
Abra la carpeta `C:\ESP32_Riego_Automatico\Proyecto_Final_v1`. El archivo `.vscode/settings.json` apunta a ESP-IDF v6.0.2 y COM8, y hay tareas en `.vscode/tasks.json` (Terminal → Run Task):
- *Compilar*, *Flashear COM8 (115200)*, *Monitor miniterm*, *SELFTEST en placa*, *Validar proyecto*.
