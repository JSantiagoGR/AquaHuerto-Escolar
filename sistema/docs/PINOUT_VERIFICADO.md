# Pinout verificado

Fuente: `firmware/main/board.h`, heredado **del firmware que funcionó físicamente** en las Pruebas 01–03 (riego de ~1 L con bomba, válvula y YF-S201; lecturas del PING))) y del DHT22), **no** de la Práctica 4.

| Función | GPIO | Detalle | ¿Probado físicamente? |
|---|---|---|---|
| Bomba (relevador IN1) | **26** | Activo en BAJO (módulo SRD probado) | Sí, Pruebas 01–03 (placa anterior) |
| Electroválvula NC (IN2) | **27** | Activo en BAJO | Sí, Pruebas 01–03 |
| YF-S201 (pulsos) | **19** | PCNT, flanco de subida, filtro 10 µs, pull-up | Sí, Prueba 02/03 |
| PING))) Parallax #28015 (SIG) | **18** | Bidireccional con divisor 1 kΩ/2 kΩ hacia 3.3 V | Sí, Prueba 03 (94.9 cm) |
| DHT22 / AM2302 | **4** | Bit-bang | Sí, Prueba 03 (21.5 °C / 53.7 %HR) |
| EC-5 excitación | **25** | Pulso de 10 ms desde el GPIO | **No** (sensor nunca conectado en estos proyectos) |
| EC-5 salida | **34** | ADC1_CH6 (válido con Wi-Fi), 12 dB, + 1 MΩ a GND | **No** |

`PINES` en la consola revisa duplicados y pines prohibidos (arranque, flash, UART0, solo entrada).

## Diferencias con otras prácticas (no copiar a ciegas)

| Proyecto | Bomba | Caudalímetro |
|---|---|---|
| Práctica 4 MQTT (`my_mqtt_client`) | GPIO2 | GPIO4 (+ GPIO5 control) |
| Pruebas 01–03 / este proyecto | GPIO26 (+ válvula GPIO27) | GPIO19 |

La PDF de la Actividad 2.2 se contradice (GPIO25/34 vs GPIO2/32): se eligió 25/34 porque GPIO2 es pin de arranque.

## Sobre la segunda ESP32

Es el mismo modelo de chip (ESP32-D0WD-V3 rev 3.1), pero **sus conexiones no se han verificado físicamente**: solo tiene el USB-C. Antes de conectar sensores o relevadores, revise el módulo y su serigrafía (algunas placas no exponen todos los GPIO) y ejecute `PINES`.

## Modelos de sensores

| Sensor | Modelo usado en el código | Notas |
|---|---|---|
| Humedad del suelo | METER (Decagon) ECH2O **EC-5** | Salida en mV → %VWC con la regresión de la Act. 2.2 |
| Ambiente | **DHT22/AM2302** | T y humedad **relativa del aire** (no es humedad del suelo) |
| Nivel | Parallax **PING)))** #28015 | Distancia; % solo con referencias de lleno/vacío |
| Caudal | **YF-S201** | Pulsos; 450 p/L provisional |
| Actuadores | Bomba 12 V ~6 A, electroválvula NC 12 V | Por etapa de potencia (ver SEGURIDAD) |

## ESP32 del proyecto (MAC xx:xx:xx:xx:xx:xx) — verificado el 2026-10-12

Su firmware anterior (Prueba 03) imprimió al arrancar: `RELE BOMBA: GPIO26 | RELE ELECTROVALVULA: GPIO27 | POLARIDAD: ACTIVO EN BAJO`, `CAUDALIMETRO YF-S201: GPIO19 | 450 PULSOS/L`, `PING))) GPIO18 | DHT22 GPIO4`. Coincide con `board.h`; con `riego-2.0.0` el DHT22 lee 25–26 °C / ~50 %HR (físico). PING))) sin eco con ambos firmwares (problema de cableado o alimentación, no de código).
