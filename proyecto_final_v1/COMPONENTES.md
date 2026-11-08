# Componentes

Identificación hecha a partir de las fotografías analizadas en la Prueba 01 (inventario detallado en `C:\TEC\SEMESTRE 5\Automatización industrial\Reto\ESP32\Prueba_01_Bomba_Electrovalvula\COMPONENTES.md`) y confirmada en las pruebas físicas 01–03.

| Componente | Fabricante / modelo | Alimentación | Consumo | Función | Conexión | Estado de identificación | Uso |
|---|---|---|---|---|---|---|---|
| Microcontrolador | Espressif **ESP32-WROOM-32U** (chip ESP32-D0WD-V3 rev 3.1, 4 MB flash) en DevKit 38 pines | 5 V USB / 3.3 V | ~80 mA prom., picos ~0.5 A con Wi-Fi | Control | CP210x, COM8 | CONFIRMADO (esptool) | Ahora |
| Placa de expansión | Genérica morada para DevKit 38 pines | DC 6.5–16 V, micro-USB, USB-C | — | Soporte y distribución | Fila VCC seleccionable 3.3/5 V | PROBABLE (sin marca) | Ahora |
| Antena | 2.4 GHz SMA + pigtail u.FL | — | — | Wi-Fi (el WROOM-32U no tiene antena integrada) | u.FL | CONFIRMADO | Ahora |
| Relevadores | Módulo 2 canales, **Songle SRD-05VDC-SL-C**, optoacoplado | 5 V | ~72 mA por bobina | Válvula (K2) y mando de bomba (K1) | IN1 GPIO26, IN2 GPIO27, activo en BAJO | CONFIRMADO | Ahora |
| Bomba | **GOOD PUMPS** diafragma "Pro Edition", SKU D2-BXSB (modelo de fábrica no impreso) | 12 V (9–14.4 V) | 6 A anunciados, 72 W; arranque **sin medir** | Impulsión | Vía etapa de potencia | CONFIRMADO (etiqueta) | Ahora |
| Electroválvula | **KING SHENG** 12 V DC, NC, pilotada "con presión" | 12 V | **Sin medir** (típico 0.3–0.6 A) | Corte de línea | K2 COM→NO | CONFIRMADO (etiqueta); consumo PENDIENTE | Ahora |
| Caudalímetro | **YF-S201** (1–30 L/min, ≤ 1.75 MPa) | 5–18 V | ~15 mA | Volumen y caudal | GPIO19 vía diodo | CONFIRMADO | Ahora |
| Ultrasónico | **Parallax PING))) #28015 REV B** | 5 V ±10 % | 30–35 mA | Nivel del tinaco | GPIO18 vía divisor 1k/2k | CONFIRMADO | Ahora |
| Humedad del suelo | **METER/Decagon ECH2O EC-5** Rev 04.00 | 2.5–3.6 V, pulso ≤ 10 ms | 10 mA | %VWC | GPIO25 excitación / GPIO34 ADC | CONFIRMADO; pinout del jack PENDIENTE | Ahora |
| Adaptador EC-5 | Jack hembra 3.5 mm con cables dupont verde / naranja / azul | — | — | Conexión del EC-5 | Ver CONEXIONES | Asignación PENDIENTE | Ahora |
| Ambiente | Módulo **DHT22/AM2302** (+ / out / −), carcasa blanca | 3.3–5.5 V | ~1–2.5 mA midiendo | Temperatura y **HR del aire** | GPIO4 a 3.3 V | PROBABLE el modelo exacto; **mide ambas variables** (probado: 21.5 °C, 53.7 %) | Ahora |
| Panel solar | **Firstech FE-50WP** 50 W, Vmp 17.4 V, Imp 2.87 A, Voc 21.6 V, Isc 3.16 A | — | — | Carga | Controlador PV | CONFIRMADO | Final |
| Batería | **Mighty Max ML9-12** 12 V 9 Ah SLA | — | Carga inicial < 2.7 A | Almacenamiento | BAT | CONFIRMADO | Ahora |
| Controlador solar | PWM genérico con LCD y 2 USB-A (marca/modelo **no identificados**) | 12 V | — | Carga y salidas LOAD/USB | PV / BAT / LOAD / USB | Modelo PENDIENTE | Ahora / final |
| Transistor TO-220 | Sin marcado legible | — | — | — | — | PENDIENTE | No se usa |

## Lista de materiales

### 1. YA TENEMOS
ESP32-WROOM-32U DevKit, placa de expansión, antena, módulo 2 relevadores, bomba GOOD PUMPS, electroválvula KING SHENG, YF-S201, PING))) 28015, EC-5 y adaptador de jack, DHT22, panel FE-50WP, batería ML9-12, controlador PWM, tubería PPR, cable 18 AWG, terminales faston, conectores de palanca, cables dupont, diodo y resistencias usados en la Prueba 03 (1 kΩ / 2 kΩ y diodo para el YF-S201).

### 2. NECESARIO PARA LA OPERACIÓN SEGURA (no confirmado en el inventario)
| Pieza | Especificación |
|---|---|
| Relevador automotriz + base | 12 V, 30/40 A, 30/87/85/86 (o módulo MOSFET ≥ 30 A / ≥ 30 V, compuerta 3.3 V) |
| Fusibles + portafusibles | F1 15 A, F2 10 A, F3 3 A (cuchilla ATO/ATC) |
| Diodos de rueda libre | 2 × 1N4007 (válvula, bobina automotriz), 1 × Schottky ≥ 5 A ≥ 40 V (bomba) |
| Corte manual | Interruptor de 15 A en el (+) de la batería |
| Cable de la rama de la bomba | ≥ 16 AWG |
| Resistencia | 1 MΩ de GPIO34 a GND (detección de EC-5 desconectado) |

### 3. NECESARIO DESPUÉS
| Pieza | Para |
|---|---|
| Convertidor buck 12 → 5 V ≥ 3 A + fusible 2 A + capacitor 470–1000 µF | Si el USB del controlador no pasa la medición |
| Divisor 100 kΩ / 22 kΩ + 100 nF a GPIO33 | Medición de batería (futuro) |
| Caja IP65 y prensaestopas | Instalación exterior |
| Recipiente graduado | Calibración del YF-S201 |
