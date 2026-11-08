# Conexiones eléctricas

Estado: **CONFIRMADO** (probado físicamente) · **PROVISIONAL** (diseño a validar) · **PENDIENTE**.

## 1. Señales al ESP32
| Componente | Terminal | Se conecta a | Voltaje | Estado | Observaciones |
|---|---|---|---|---|---|
| Módulo relevadores | IN1 | GPIO26 | 0 / 3.3 V | CONFIRMADO | Activo en BAJO |
| Módulo relevadores | IN2 | GPIO27 | 0 / 3.3 V | CONFIRMADO | — |
| Módulo relevadores | VCC | Pin **5V** del DevKit | 5 V | CONFIRMADO | Puente JD-VCC↔VCC puesto |
| Módulo relevadores | GND | GND | 0 V | CONFIRMADO | — |
| YF-S201 | Rojo | 5V | 5 V | CONFIRMADO | ~15 mA |
| YF-S201 | Negro | GND | 0 V | CONFIRMADO | — |
| YF-S201 | Amarillo | Cátodo (franja) de diodo 1N5819/1N4148; ánodo → **GPIO19** | 0–5 V → 0–3.3 V | CONFIRMADO | El pull-up interno da el nivel alto |
| PING))) | 5V / GND | 5V / GND | 5 V | CONFIRMADO | 30–35 mA |
| PING))) | SIG | 1 kΩ → **GPIO18**; 2 kΩ de GPIO18 a GND | 0–5 V → ~3.3 V | CONFIRMADO | Disparo y eco por el mismo cable |
| DHT22 (módulo) | + / out / − | **3V3** / **GPIO4** / GND | 3.3 V | CONFIRMADO | Sin adaptación |
| EC-5 | Alimentación (blanco o café) | **GPIO25** | 3.3 V en pulso de 10 ms | PROVISIONAL | Igual que la calibración de la Act. 2.2 |
| EC-5 | Salida analógica (rojo o naranja) | **GPIO34** + 1 MΩ a GND | 0.3–1.6 V | PROVISIONAL | El 1 MΩ permite detectar desconexión |
| EC-5 | Tierra (desnudo) | GND | 0 V | PROVISIONAL | — |
| EC-5 jack 3.5 mm | Punta / anillo / manga | Ver arriba | — | **PENDIENTE** | Identificar por continuidad (cables dupont verde / naranja / azul del adaptador) |

### ¿Se necesita transistor para el EC-5?
**No**, en este diseño:
- Consumo de 10 mA a 2.5–3.6 V durante ≤ 10 ms (hoja de datos). Un GPIO del ESP32 entrega esa corriente con caída de ~0.1–0.2 V; se configura en `GPIO_DRIVE_CAP_3` (máxima).
- La calibración de la Actividad 2.2 se hizo **exactamente así**: GPIO directo a 3.3 V con pulso de 10 ms. Agregar un transistor cambiaría la tensión de excitación e invalidaría la regresión.
- El circuito del dibujo a mano (NPN en el lado alto alimentado de 5 V) **no sirve**: entregaría ~2.6 V variables, por la caída base-emisor del seguidor de emisor (análisis en la Prueba 01, `PINOUT_FUTURO.md`).
- **Nunca conecte el EC-5 a 5 V** (máximo 3.6 V).
- Si en el futuro hiciera falta más corriente o aislamiento: P-MOSFET AO3401 en el lado alto alimentado de 3.3 V (compuerta con 100 kΩ a 3.3 V, GPIO en BAJO = encendido), poner `EC5_POWER_ACTIVE_HIGH 0` en `board.h` **y recalibrar**.

### ¿Se necesita transistor para el DHT22?
No. Su consumo en reposo es de µA y puede quedar alimentado de forma continua.

## 2. Potencia 12 V
```
BATERÍA ML9-12 (+) ─[F1 15 A]─┬──[F2 10 A]──── 30  RELEVADOR AUTOMOTRIZ 12 V 30/40 A
                              │                87 ─────────── BOMBA (+) rojo
                              │                                 │  D3 Schottky ≥5 A (cátodo a +)
                              │                               BOMBA (−) negro ──┐
                              ├──[F3 3 A]─┬─ K1 COM                             │
                              │           │  K1 NO ── 86 (bobina)               │
                              │           │           85 ───────────────────────┤ D1 1N4007 en 86–85
                              │           └─ K2 COM                             │
                              │              K2 NO ── ELECTROVÁLVULA (A)        │ D2 1N4007 en A–B
                              │                       ELECTROVÁLVULA (B) ───────┤
BATERÍA ML9-12 (−) ════════════ barra de retorno (−) ═══════════════════════════┘
Controlador solar: PANEL → PV, BATERÍA → BAT. Corte manual en el (+) de la batería.
```

| Componente | Terminal | Se conecta a | Estado | Observaciones |
|---|---|---|---|---|
| Batería | (+) | F1 15 A a < 20 cm del borne → barra +12 V | PENDIENTE | Fusible principal |
| Relevador automotriz | 30 | +12 V vía F2 10 A | **PENDIENTE (requerido)** | Sustituye al SRD para la bomba |
| Relevador automotriz | 87 | Bomba (+) | PENDIENTE | Cable ≥ 16 AWG |
| Relevador automotriz | 86 / 85 | K1 NO / retorno (−) | PENDIENTE | Bobina de ~0.15 A: dentro de los 3 A del SRD |
| Módulo K2 | COM / NO | +12 V vía F3 / electroválvula | CONFIRMADO (sin fusible) | La válvula sí cabe en el SRD |
| Bomba | (−) | Retorno (−) directo a batería | CONFIRMADO | Nunca por la placa del ESP32 |
| D1, D2, D3 | — | Ver diagrama | PENDIENTE | Cátodo al + |

**Configuración usada en las pruebas físicas (no recomendada para operación):** bomba directo en K1 (COM→NO), negativo al controlador, sin fusible ni diodo confirmados.

## 3. Alimentación del ESP32
| Etapa | Fuente | Estado |
|---|---|---|
| Pruebas | USB de la computadora | CONFIRMADO |
| Final | USB-A del controlador solar con cable USB-A → micro-USB | **PENDIENTE**: medir 4.9–5.25 V en vacío y ≥ 4.75 V con carga de 0.5 A (10 Ω / 5 W), también durante el arranque de la bomba |
| Alternativa | Convertidor buck 12 → 5 V ≥ 3 A, ajustado a 5.0–5.1 V, con fusible de 2 A y capacitor de 470–1000 µF, al pin 5V | Si el USB del controlador no pasa la prueba |

**Nunca dos fuentes a la vez** (USB de la PC + controlador o buck) sin verificar la placa.

## 4. Tierras
- Con el ESP32 alimentado de la batería (buck o USB del controlador), las tierras quedan unidas en la batería: **un solo punto** (estrella) en el borne (−).
- La corriente de la bomba vuelve por su propio cable al (−) de la batería.
- Los cables de la bomba deben ir separados de los de los sensores, sobre todo del YF-S201 y del EC-5.
