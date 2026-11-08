# Pendientes de hardware (mediciones y conexiones)

## Críticos (antes de operación repetitiva o del modo B)
| # | Pendiente | Cómo | Por qué |
|---|---|---|---|
| 1 | Etapa de potencia de la bomba | Relevador automotriz 30/40 A accionado por K1, o MOSFET ≥ 30 A | El SRD-05VDC-SL-C admite 3 A inductivos y la bomba anuncia 6 A |
| 2 | Corriente real y de arranque de la bomba | Pinza DC con función *inrush*, u osciloscopio + shunt | Dimensionar relevador y fusible |
| 3 | Fusibles F1 15 A / F2 10 A / F3 3 A | Portafusibles en línea | Protección contra cortocircuito |
| 4 | Diodos de rueda libre | 1N4007 en la válvula y en la bobina automotriz; Schottky ≥ 5 A en la bomba (cátodo al +) | Arco en contactos, picos |
| 5 | Corte manual | Interruptor en el (+) de la batería | Contacto pegado |
| 6 | Presión máxima de la electroválvula y de las uniones | Hoja del fabricante o prueba | El presostato corta a 0.9 MPa |

## Sensores
| # | Pendiente | Cómo |
|---|---|---|
| 7 | Pinout del jack del EC-5 | Continuidad entre punta, anillo y manga y los cables dupont verde / naranja / azul; identificar excitación, salida y tierra (manual METER) |
| 8 | Primera lectura del EC-5 en este proyecto | Conectar a GPIO25/GPIO34 + 1 MΩ a GND; `ESTADO`: debe dar ~360 mV en tierra seca |
| 9 | Comparación de atenuación del ADC (12 dB vs. la de la Act. 2.2) | Misma muestra con ambas configuraciones o con multímetro |
| 10 | Recalibración del EC-5 con la tierra del cajón | [CALIBRACION_EC5.md](CALIBRACION_EC5.md) §5 |
| 11 | Calibración del YF-S201 con recipiente | [CALIBRACION_YFS201.md](CALIBRACION_YFS201.md) §3 |
| 12 | Medidas del tinaco (distancia vacío / lleno) | Ver [GUIA_INSTALACION_FINAL.md](GUIA_INSTALACION_FINAL.md) Etapa 3 |
| 13 | Montaje del PING))) sobre el tinaco | Centrado, perpendicular, a ≥ 2 cm del nivel máximo, protegido de la condensación |
| 14 | Confirmar el modelo exacto del sensor ambiental | Marcado al reverso del sensor (DHT22 / AM2302) |

## Energía
| # | Pendiente | Cómo |
|---|---|---|
| 15 | Modelo y capacidad del controlador solar (10/20/30 A, salida LOAD) | Foto de la etiqueta lateral o trasera |
| 16 | Salida USB del controlador | 4.9–5.25 V en vacío; ≥ 4.75 V con 10 Ω / 5 W; registrar el mínimo durante el arranque de la bomba |
| 17 | Si el USB no pasa: convertidor buck 12 → 5 V ≥ 3 A | Ajustar a 5.0–5.1 V **antes** de conectar; fusible de 2 A |
| 18 | Balance energético real | Medir los litros y el tiempo de bomba diarios; un riego de 1 L ≈ 20 s × 6 A ≈ 0.03 Ah |

## Verificaciones de firmware que requieren la placa
| # | Verificación | Comando |
|---|---|---|
| 19 | Flashear el Proyecto Final v1 (versión segura) | `idf.py -p COM8 -b 115200 flash` |
| 20 | SELFTEST en la placa real | `python tools\run_selftest.py COM8` → 33 PASS |
| 21 | Conexión real a Wi-Fi `RouterHuerto1`, NTP y broker | [CONFIGURACION_MQTT.md](CONFIGURACION_MQTT.md) "Verificación pendiente" |
| 22 | Reinicio durante un riego en la placa | `SIM ON`, `START 2`, `REINICIAR DURO` → alarma `REBOOT_DURING_WATERING` |
| 23 | Pruebas físicas con agua del firmware nuevo | [GUIA_INSTALACION_FINAL.md](GUIA_INSTALACION_FINAL.md) Etapa 4 (requiere autorización) |
