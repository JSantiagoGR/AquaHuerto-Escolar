# Hojas de datos y fuentes

| # | Fuente | Usada para |
|---|---|---|
| 1 | Espressif, *ESP32-WROOM-32D & ESP32-WROOM-32U Datasheet* — https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32d_esp32-wroom-32u_datasheet_en.pdf | Alimentación, pines de arranque, flash, GPIO de solo entrada |
| 2 | Espressif, *ESP-IDF v6.0 Programming Guide* (PCNT, ADC oneshot y calibración, NVS, esp_timer, Task WDT, SNTP, Wi-Fi) — https://docs.espressif.com/projects/esp-idf/en/latest/esp32/ | Drivers usados |
| 3 | Espressif, *ESP-MQTT* (componente `espressif/mqtt` 1.1.0) — https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/protocols/mqtt.html | LWT, QoS, enqueue |
| 4 | Ningbo Songle, *SRD Relay datasheet* — https://www.circuitbasics.com/wp-content/uploads/2015/11/SRD-05VDC-SL-C-Datasheet.pdf | Forma C: 7 A/28 VDC resistiva, **3 A/28 VDC inductiva**; bobina 0.36 W / 71.4 mA |
| 5 | METER Group, *EC-5 User Manual* — https://publications.metergroup.com/Manuals/20431_EC-5_Manual_Web.pdf | 2.5–3.6 V, 10 mA, ≤ 10 ms, salida 10–50 % de la excitación, colores de cable |
| 6 | Parallax, *PING))) #28015 datasheet v2.0* — https://www.digikey.cn/htmldatasheets/production/1253021/0/0/1/28015.pdf | 5 V ±10 %, 30/35 mA, 2 cm–3 m, pulsos de 2–5 µs y eco de 115 µs a 18.5 ms |
| 7 | Aosong, *DHT22 / AM2302* (copia SparkFun) — https://cdn.sparkfun.com/assets/f/7/d/9/c/DHT22.pdf | 3.3–6 V, protocolo, lectura cada ≥ 2 s |
| 8 | *YF-S201 datasheets* (Fondyes / Phipps) — https://www.phippselectronics.com/wp-content/uploads/2024/04/YF-S201-Datasheet.pdf | 5–18 V, f ≈ 7.5·Q → ~450 pulsos/L, ±10 % |
| 9 | Etiquetas fotografiadas (Prueba 01): bomba GOOD PUMPS, caja SKU D2-BXSB, KING SHENG, YF-S201, ML9-12, FE-50WP | Datos confirmados por foto |
| 10 | **Actividad 2.2** — Sistema de Adquisición de Datos (EC-5), reporte del equipo | Calibración 360/420/630/870 mV ↔ 0/15/30/45 %VWC, regresión y R² |
| 11 | **Actividad 2.3** — Control de Consumo de Agua (YF-S201), reporte del equipo | 450 pulsos/L; conteos 481…2315 (sobrepaso, no calibración) |
| 12 | Proyecto `Practica4_MQTT/my_mqtt_client` (solo lectura) | Broker `raspberrypi.local:1883`, componente `espressif/mqtt`, red Wi-Fi |
| 13 | Pruebas físicas 01–03 de esta conversación | GPIO26/27 activo en bajo, secuencia de 300 ms, 1 L ≈ 19.7 s, 455 pulsos, PING))) 94.9 cm, DHT22 21.5 °C / 53.7 % |
| 14 | Gobierno de México — cambio de horario 2022; zona America/Chihuahua UTC−6 sin horario de verano (Cd. Juárez: America/Ciudad_Juarez) | Zona horaria `CST6` |

Datos **sin documentación del fabricante** (quedan como mediciones pendientes): corriente de arranque y ciclo de trabajo de la bomba, consumo y presiones de la electroválvula, modelo del controlador solar, regulador de la placa de expansión.
