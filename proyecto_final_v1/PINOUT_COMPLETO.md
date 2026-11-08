# Pinout completo — ESP32-WROOM-32U (ESP32-D0WD-V3 rev 3.1)

Definido en `main/board.h`. Verificado al arrancar (`board_check_pins`), por consola (`PINES`) y con `tools/validate_project.py`.

| GPIO | Función | Dir. | Nivel | Origen / estado | Notas |
|---|---|---|---|---|---|
| **26** | Relevador bomba (IN1) | Salida | 3.3 V, **activo en BAJO** | **Probado físicamente** (Pruebas 01–03) | Arranque: alta impedancia → relevador apagado |
| **27** | Relevador electroválvula (IN2) | Salida | 3.3 V, activo en BAJO | **Probado físicamente** | — |
| **19** | YF-S201 (PCNT) | Entrada | Pull-up interno 3.3 V + diodo | **Probado físicamente** (Prueba 03) | Flanco de subida, filtro de 10 µs |
| **18** | PING))) SIG | E/S | Divisor 1 kΩ / 2 kΩ | **Probado físicamente** (Prueba 03) | Pull-down interno en reposo |
| **4** | DHT22 datos | E/S (drenador abierto) | 3.3 V | **Probado físicamente** (Prueba 03) | El módulo trae pull-up |
| **25** | Excitación EC-5 | Salida | 3.3 V, pulso ≤ 10 ms, máx. corriente | Esquema Act. 2.2; **pendiente físico** en este proyecto | ~10 mA |
| **34** | Salida EC-5 (ADC1_CH6) | Entrada analógica | 0–3.1 V (atenuación 12 dB) | Esquema Act. 2.2; **pendiente físico** | Recomendado 1 MΩ a GND |
| 1 / 3 | UART0 (USB CP210x) | — | — | Consola y flasheo | No usar |
| 6–11 | Flash SPI | — | — | — | Prohibidos |
| 0, 2, 5, 12, 15 | Pines de arranque | — | — | — | Evitados (GPIO12 en alto cambia el voltaje de la flash) |
| 32, 33, 35, 36, 39 | ADC1 libres | — | — | Reservados | GPIO33: medición de batería futura (divisor 100 k / 22 k) |
| 13, 14, 16, 17, 21, 22, 23 | Libres | — | — | — | 21/22: I²C futuro |

## Reglas aplicadas
- Solo **ADC1** (GPIO32–39) para analógico, porque el Wi-Fi ocupa el ADC2.
- Ninguna salida en GPIO34–39 (solo entrada).
- Ninguna señal de 5 V directa a un GPIO: el PING))) usa divisor y el YF-S201 un diodo.
- Sin pines repetidos (comprobado por software).

## Placa de expansión morada
- Fila amarilla = señal, roja = VCC (seleccionable 3.3 V / 5 V con el puente "JUMP"), negra = GND.
- Para los sensores de 5 V y el módulo de relevadores use el pin **5V** del DevKit; la fila roja puede estar en 3.3 V.
- El DHT22 va a **3V3** (no a 5 V), para que su señal sea de 3.3 V.
