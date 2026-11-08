# Riego automatizado inteligente — Proyecto Final v1

Firmware ESP-IDF 6.0.2 (C) para un ESP32-WROOM-32U que riega un huerto de ~1 × 1 m:
- **Bomba 12 V y electroválvula NC** en ON/OFF (sin PWM, sin PI/PID).
- **Dosificación por litros** contando pulsos del caudalímetro **YF-S201**.
- **Decisión por humedad volumétrica del suelo** (EC-5, calibración de la Actividad 2.2), con **horarios** (hora NTP de Chihuahua), **nivel del tinaco** (PING))) y **condiciones ambientales** (DHT22).
- **MQTT / Node-RED** para supervisión y control, con todas las protecciones funcionando en local.

> **Estado:** firmware completo a nivel de software, compilado sin warnings y probado en el emulador QEMU (SELFTEST 33/33 e integración). **No** se ha flasheado en la placa (no estaba conectada) ni se ha probado conectado al broker. La etapa de potencia de la bomba sigue pendiente de certificar. Ver [PROJECT_STATE.md](PROJECT_STATE.md).

## Inicio rápido
```powershell
. "C:\Espressif\tools\Microsoft.v6.0.2.PowerShell_profile.ps1"
cd C:\ESP32_Riego_Automatico\Proyecto_Final_v1
idf.py build
idf.py -p COM8 -b 115200 flash
python -m serial.tools.miniterm COM8 115200 --dtr 0 --rts 0 --eol CRLF --encoding utf-8
```
En la consola: `AYUDA`, `ESTADO`, `SELFTEST`.

**Versión segura por defecto:** modo A, salidas de potencia **deshabilitadas** y riego automático apagado. Para regar de verdad: `POWER ON CONFIRMAR` (solo por consola), después de revisar [SEGURIDAD.md](SEGURIDAD.md).

## Pines (sin cambios respecto a lo probado)
| GPIO | Uso |
|---|---|
| 26 / 27 | Relevador bomba / electroválvula (activo en BAJO) |
| 19 | YF-S201 (PCNT) |
| 18 | PING))) SIG (divisor 1k/2k) |
| 4 | DHT22 |
| 25 / 34 | EC-5 excitación / ADC1_CH6 |

## Documentación
| Tema | Archivo |
|---|---|
| Estado del proyecto | [PROJECT_STATE.md](PROJECT_STATE.md) |
| Arquitectura y módulos | [ARQUITECTURA.md](ARQUITECTURA.md) |
| Cómo funciona todo | [FUNCIONAMIENTO_COMPLETO.md](FUNCIONAMIENTO_COMPLETO.md) |
| Pines | [PINOUT_COMPLETO.md](PINOUT_COMPLETO.md) |
| Conexiones eléctricas | [CONEXIONES_ELECTRICAS.md](CONEXIONES_ELECTRICAS.md) |
| Componentes y materiales | [COMPONENTES.md](COMPONENTES.md) |
| Fuentes | [DATASHEETS_Y_FUENTES.md](DATASHEETS_Y_FUENTES.md) |
| Calibración EC-5 | [CALIBRACION_EC5.md](CALIBRACION_EC5.md) |
| Calibración YF-S201 | [CALIBRACION_YFS201.md](CALIBRACION_YFS201.md) |
| Humedad mínima / objetivo / máxima | [CONFIGURACION_HUMEDAD.md](CONFIGURACION_HUMEDAD.md) |
| Wi-Fi y MQTT | [CONFIGURACION_MQTT.md](CONFIGURACION_MQTT.md) |
| Topics y JSON | [MQTT_TOPICS.md](MQTT_TOPICS.md), [EJEMPLOS_MQTT.json](EJEMPLOS_MQTT.json) |
| Dashboard Node-RED (guía) | [GUIA_DASHBOARD_NODE_RED.md](GUIA_DASHBOARD_NODE_RED.md), [DASHBOARD_LAYOUT.md](DASHBOARD_LAYOUT.md), [node-red/flow_dashboard_riego.json](node-red/flow_dashboard_riego.json) |
| Pruebas | [PRUEBAS_REALIZADAS.md](PRUEBAS_REALIZADAS.md) |
| Pendientes de hardware | [PENDIENTES_HARDWARE.md](PENDIENTES_HARDWARE.md) |
| Seguridad | [SEGURIDAD.md](SEGURIDAD.md) |
| Modo A → modo B | [GUIA_INSTALACION_FINAL.md](GUIA_INSTALACION_FINAL.md) |
| Compilar, flashear, emulador | [COMO_COMPILAR_Y_FLASHEAR.md](COMO_COMPILAR_Y_FLASHEAR.md) |

## Estructura
```
Proyecto_Final_v1/
├── main/                 Código fuente (21 módulos .c/.h)
├── tools/                validate_project.py, run_selftest.py, qemu_test.py, generar_flow_node_red.py
├── node-red/             Flow de ejemplo (NO importado ni desplegado)
├── sdkconfig.defaults    Configuración base (TWDT, brownout, 4 MB, consola)
├── sdkconfig.qemu        Solo para la compilación de prueba en QEMU (sin Wi-Fi)
├── sdkconfig.secrets     Credenciales locales (NO versionar; plantilla: .example)
└── *.md                  Documentación
```

## Proyectos anteriores
No se modificaron: la Prueba 01 (`C:\TEC\SEMESTRE 5\Automatización industrial\Reto\ESP32\Prueba_01_Bomba_Electrovalvula`), `Practica4_MQTT` ni los proyectos EPANET. Solo se consultaron.
