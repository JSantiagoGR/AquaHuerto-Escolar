# Firmware del ESP32 (`riego-2.0.0`)

ESP-IDF **v6.0.2** · objetivo `esp32` · flash 4 MB · partición única de 1.5 MB (27 % libre) · componentes `espressif/mqtt` 1.1.0 y `espressif/cjson` 1.7.19.
Archivo principal: **`firmware/main/main.c`**. Una sola base de código para casa y huerto (cambia la configuración, no el código).

## Compilar, flashear y monitorear

En una terminal de ESP-IDF (`. C:\Espressif\tools\Microsoft.v6.0.2.PowerShell_profile.ps1`):

```bash
cd C:\ESP32_Riego_Automatico\Pruebas_Casa_ESP32_v1\firmware
idf.py build
idf.py -p COM8 -b 115200 app-flash
python -m serial.tools.miniterm COM8 115200 --dtr 0 --rts 0 --eol CRLF --encoding utf-8
```

En VS Code (`firmware/.vscode/tasks.json`) hay tareas equivalentes.

## Módulos

| Módulo | Función |
|---|---|
| `main.c` | Arranque seguro: salidas inactivas primero, luego NVS, red, sensores, control |
| `irrigation_logic.c` | Máquina de estados **pura** (MANUAL/AUTO/IA, eventos por dosis, límites) |
| `ia_model.c` | IA ligera: dos modelos RLS, validación, plan predictivo, corrección acotada |
| `config_table.c` / `configuration.c` | 73 parámetros con límites duros, validación global, NVS con CRC |
| `net_config.c` | Redes Wi-Fi (casa/tec/huerto), broker, topic, identidad (NVS) |
| `wifi_manager.c` / `mqtt_manager.c` | Reconexión, cambio de red y de broker con reversión |
| `weather.c` | Open-Meteo por HTTPS con verificación de certificados |
| `irrigation_controller.c` | Tarea de control: comandos, IA, lluvia, búfer sin conexión, publicaciones |
| `commands.c` | Validación de comandos MQTT (id, duplicados, retenidos, antigüedad) |
| `actuators.c` / `safety.c` | Salidas y supervisor independiente (tope duro de bomba, latido) |
| `sensors.c` + drivers | EC-5, PING))), DHT22, YF-S201 (PCNT) |
| `logic_tests.c` / `selftest.c` | 47 escenarios comunes PC/ESP32 + 2 propios del ESP32 |

## Modos de operación

| Modo | Comportamiento |
|---|---|
| MANUAL | Solo riegos pedidos (litros o "hacia la óptima") |
| AUTOMÁTICO | En horario preferido riega si la humedad está bajo (óptima − histéresis), confirmado con 2 lecturas; dosis + infiltración + nueva lectura; evita mediodía, calor y lluvia prevista; emergencia (bajo el umbral crítico) a cualquier hora con un ciclo limitado |
| IA | Igual de protegido. Si el modelo está en PREDICTIVO_ACTIVO, riega solo si predice que no llegará al siguiente horario sobre la mínima y calcula los litros mínimos; si no, usa el automático conservador |

Perfil de instalación (independiente del modo): **A pruebas** (arranca siempre en MANUAL) / **B final** (restaura el modo guardado solo con potencia habilitada y tinaco calibrado; nunca riega al arrancar: espera el intervalo mínimo y lecturas nuevas).

## Seguridad que no se puede desactivar por MQTT

Potencia (`POWER ON CONFIRMAR`), perfil (`PERFIL B CONFIRMAR`), simulación, reinicios: **solo por USB**. Ver [SEGURIDAD.md](SEGURIDAD.md).

## Consola (USB)

`AYUDA` lista todo. Principales: `ESTADO`, `CONFIG`, `IA`, `CLIMA`, `RED`, `MODO MANUAL|AUTO|IA`, `START <L>`, `OBJETIVO`, `STOP`, `SET <param> <valor>`, `SELFTEST`, `SIM ON|OFF|SUELO|TINACO|FLUJO|AMB|HORA|VELOCIDAD|SECADO|LLUVIA`.
