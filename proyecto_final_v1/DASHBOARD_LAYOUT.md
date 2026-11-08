# Distribución del dashboard (propuesta)

Página: **Riego del huerto** (`/dashboard/riego`), cuadrícula de 12 columnas en escritorio, 6 en tableta y 3 en teléfono.

```
┌──────────────────────────── A. PANEL PRINCIPAL (12) ───────────────────────────────┐
│ [Humedad suelo %VWC] [Nivel tinaco %] [Temp °C] [HR aire %] [Caudal L/min]          │
│ Litros hoy | Estado EC-5 | Estado tinaco | Origen de datos (REAL / SIMULACIÓN)      │
│ Bomba: APAGADA | Electroválvula: CERRADA | Estado: MONITORING | MQTT/Wi-Fi | Modo A │
│ ESP32: EN LÍNEA                                                                     │
├─ B. HUMEDAD DEL SUELO (4) ──┬─ C. RIEGO MANUAL (4) ──────┬─ D. RIEGO AUTOMÁTICO (4) ─┤
│ HUMEDAD MÍNIMA     [====]   │ Litros a regar   [==]      │ Riego automático  (o)     │
│ HUMEDAD OBJETIVO   [=====]  │ [ START ]   [ STOP ]       │ Decisión: OUTSIDE_WINDOW  │
│ HUMEDAD MÁXIMA     [======] │ 0.42 / 1 L (42 %) 9 s      │ Próximo horario: 18:00    │
│ Guardado en ESP32: 25/35/45 │ ( progreso % )             │ Ciclos 1 | 1 L | infilt.  │
│                             │                            │ 1 L/ciclo · 15 min · 3    │
│                             │                            │ H1 06:00-09:00 H2 ...     │
├──────────────────────────── E. GRÁFICAS (12) ──────────────────────────────────────┤
│ Humedad suelo vs tiempo │ Nivel tinaco │ Temperatura │ HR aire │ Caudal │ Litros día  │
├─────────────── F. HISTORIAL (8) ──────────────────┬─ G. CONFIGURACIÓN Y ALERTAS (4) ─┤
│ Fecha | Tipo | Resultado | Litros | Duración |    │ Alarmas activas: ...             │
│ Humedad antes | Humedad después                   │ Tinaco: SIN CALIBRAR | mín 20 %  │
│                                                   │ Máximos: 3 L/evento, 10 L/día    │
│                                                   │ [ CLEAR_ALARM (ALL) ]            │
└───────────────────────────────────────────────────┴──────────────────────────────────┘
Notificaciones (esquina superior derecha): confirmaciones de comandos y alarmas.
```

## Colores
| Uso | Color |
|---|---|
| Acción segura / OK / START | Verde `#2e7d32` |
| STOP / alarma crítica | Rojo `#c62828` |
| Advertencia / CLEAR_ALARM | Ámbar `#ef6c00` |
| Información | Azul `#1565c0` |
| Barra superior | Verde oscuro `#1b5e20` |

## Reglas de diseño
1. **STOP siempre visible** y separado de START.
2. Distinguir siempre **humedad del suelo (%VWC)** de **humedad relativa del aire (%HR)**: nombres y unidades distintos.
3. El nivel del tinaco muestra "SIN CALIBRAR" y no un porcentaje mientras `tank.calibrated` sea `false`.
4. "SIMULACIÓN" muy visible cuando `simulation = true`.
5. Toda configuración muestra el **valor guardado en el ESP32** (topic `config`), no el último valor movido en pantalla.
6. Cada acción tiene confirmación (notificación del `ack`).
7. La sección D muestra el **motivo** de la decisión, el próximo horario y por qué se pospone o bloquea un riego.
