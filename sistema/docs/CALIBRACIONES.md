# Calibraciones

Ninguna de estas calibraciones se ha contrastado físicamente en este proyecto. Todo lo que dependa de ellas está marcado como **provisional** o **pendiente**.

## EC-5 → humedad volumétrica (%VWC)

- Regresión experimental de la **Actividad 2.2**: `%VWC = 0.08146067 · mV − 23.932584` (R² 0.945), válida entre **360 y 870 mV**. Fuera de ese intervalo la lectura se marca `OK_FUERA_DE_CALIBRACION`.
- Es **%VWC** (m³ de agua por m³ de suelo × 100), no un "porcentaje de humedad" arbitrario ni la humedad relativa del aire.
- Defecto conocido: a 360 mV da 5.4 % (no 0 %). Con otro suelo la recta cambia.
- Incertidumbre: con R² 0.945 y pocos puntos, considere al menos ±2–3 pp hasta recalibrar en el suelo real (gravimétrico: pesar muestra húmeda, secar a 105 °C, densidad aparente).
- Parámetros editables (Configuración): `ec5_slope`, `ec5_offset`, `ec5_cal_mv_lo/hi`.
- **Versión de datos** (`data_version`): al cambiar la calibración o el suelo cree una versión nueva (Configuración → NUEVA VERSIÓN). La IA reinicia su modelo y la base de datos guarda cada lectura con su versión para no mezclar datos incompatibles.

### Escala: agua/(tierra+agua) → %VWC estándar (corrección del 2026-10-12)

La Actividad 2.2 mezcló **600 mL de tierra seca** con 0 / 105 / 257 / 490 mL de agua y calculó `agua / (tierra + agua)`: 105/705 = 15 %, 257/857 = 30 %, 490/1090 = 45 %. Al mojar la tierra el agua ocupa los poros y el volumen casi no cambia, así que el **%VWC estándar** (agua / volumen de suelo, el de FAO-56 y el de la capacidad de campo) de esas muestras era 0 / **17.5** / **42.8** / **81.7** % (la última era lodo saturado).

El firmware (`ec5_scale = 1`, por defecto desde `CONFIG_VERSION 3`) aplica la recta tal cual y luego convierte: `theta = s / (1 − s)`.

| mV | Recta (agua/(tierra+agua)) | %VWC estándar |
|---|---|---|
| 360 | 5.4 | 5.7 |
| 463 | 13.8 | **16.0** (punto de marchitez estimado de la cama) |
| 630 | 27.4 | 37.7 |
| 645 | 28.6 | **40.0** (capacidad de campo estimada de la cama) |
| 700 | 33.1 | 49.5 |
| 785 | 40.0 | 66.7 |
| 870 | 46.9 | 88.5 → `IMPOSIBLE` (saturado) |

Sin esta conversión, un umbral FAO de "40 %" se habría comparado con la recta y equivaldría a 785 mV ≈ 67 % de agua: la cama encharcada. Si se recalibra directamente en %VWC estándar, poner `ec5_scale = 0` (Configuración → EC-5). Verificado: SELFTEST 49/49 en la placa (`tests/resultados/selftest_esp32_COM8_20261012_escala_ec5.txt`) y prueba de ida y vuelta mV → %VWC → mV en la PC.

## Cama de cultivo

| Dato | Valor |
|---|---|
| Medidas | 1 m × 1 m, cajón de 40 cm, sustrato ≈ **37.5 cm** (dejar 2–5 cm libres) |
| Volumen de sustrato | **375 L** |
| **1 punto de %VWC** | **3.75 L** (área × profundidad / 10) |
| Agua útil (FC 40 − WP 16) | ≈ 90 L |
| Fondo | Tablas separadas; **drenaje libre**: malla antimaleza (geotextil) o lona **perforada**. Lona sin perforar = fondo encharcado (no usar) |

Se registra en Configuración → Cama de cultivo y el servidor la usa en los tres modos (`umbrales.js → paramsCama`), enviándola con cada perfil de cultivo:

| Parámetro | Fórmula | Valor en esta cama |
|---|---|---|
| `liters_per_cycle` | 0.67 × L/punto (cabe en `pump_max_s` = 90 s con ≥ 1.7 L/min) | 2.5 L |
| `max_liters_event` | 3 dosis, máx. 10 | 7.5 L (≈ 2 puntos = histéresis) |
| `max_liters_daily` | 4 × L/punto | 15 L (ETc del frijol 3–6 L/día) |
| `emergency_liters` | 0.5 × L/punto, máx. 2 | 1.9 L |
| `ia_gain_prior` | 1 / L/punto | 0.27 %/L (promedio físico; la IA aprende la del sensor) |
| `min_response_pp` | fija | 0.5 |

El dashboard muestra en Inicio, Manual y Automático cuántos puntos sube un volumen y cuántos litros faltan para la óptima.

## Suelo: capacidad de campo (FC) y punto de marchitez (WP)

Necesarios para traducir los perfiles FAO-56 a %VWC del EC-5 (ver [CULTIVOS.md](CULTIVOS.md)).
- **FC**: saturar el suelo, cubrir para evitar evaporación, dejar drenar 24–48 h y registrar la lectura estable del EC-5.
- **WP**: no se inventa. Use un valor de laboratorio o de tabla para su textura de suelo, documentando la fuente.
- Se registran en Configuración → Calibración del suelo (tabla `soil_calibration`).

**Estado: ESTIMADO, no medido (2026-10-12): FC 40 / WP 16 %VWC.** Mezcla 50 % tierra negra, 30 % peat moss y 20 % lombricomposta, promediada por componente (tierra negra ≈ 28–36 / 12–20; peat moss ≈ 55–70 / 10–20; lombricomposta ≈ 45–60 / 15–25; valores generales de sustratos, no de una tabla oficial). En una cama de 37.5 cm el agua drena mejor que en maceta, por eso FC se tomó en la parte baja. Incertidumbre ±5 puntos. **Pendiente:** medir FC en la cama (regar a fondo, tapar, 48 h) y verificar el EC-5 en esta mezcla (los sustratos orgánicos suelen leer distinto).

## YF-S201 → litros

- Valor provisional **450 pulsos/L** (el que se usó en la práctica; la Práctica 4 usaba 480; las fotos tenían 451/526).
- **No** se ha medido con un recipiente graduado. Los litros del dashboard dicen "calculados por pulsos".
- Procedimiento: regar 1–2 L a un recipiente medido, anotar pulsos (`pulses` del evento) y mL reales → consola `CALFLUJO <pulsos> <mL>` o MQTT `SET_FLOW_CALIBRATION`. Repetir 3 veces a caudal de trabajo.
- `overrun_ml` compensa el agua que pasa tras cortar la bomba (medir después de calibrar).

## Tinaco (PING)))

- El % solo existe con dos referencias: distancia sensor→agua con tinaco **vacío** y **lleno** (`TINACO <vacío_cm> <lleno_cm>` o Configuración).
- Sin calibrar: se publica la distancia y el nivel aparece como "Sin calibrar"; en perfil B no se riega.
- Lecturas inválidas (sin eco, inestables, fuera de rango) bloquean el riego si el tinaco está calibrado.
- Nivel mínimo para regar: `tank_min_pct` (20 % por defecto, con histéresis de 3 %).

## Hora

NTP (`pool.ntp.org`), zona POSIX `CST6` (Chihuahua, UTC−6 sin horario de verano). Sin hora válida no hay riegos por horario (solo emergencias).
