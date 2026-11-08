# Modelo predictivo (modo IA)

Implementación real y ligera **dentro del ESP32** (`firmware/main/ia_model.c`, C puro, ~400 líneas, ~0.6 KB de NVS). No es PID ni PWM: la bomba sigue siendo ON/OFF y la IA solo decide **cuántos litros** y **si** regar.

## Modelo A — respuesta al riego

Predice cuánto sube la humedad tras la infiltración:

`Δ%VWC = L · (a0 + a1·u1 + a2·u2 + a3·u3 + a4·u4)`, con
`u1 = (θ0 − 25)/10` (humedad inicial), `u2 = (T − 20)/10`, `u3 = (HR − 50)/50`, `u4 = min(h desde el riego anterior, 48)/24`.

Cultivo y etapa se registran con cada observación en SQLite para el análisis por cultivo/etapa (ver comparaciones).

## Modelo B — pérdida de humedad

`pérdida pp/h = b0 + b1·(θ−25)/10 + b2·Kc·VPD + b3·Kc·ET0_h·10 + b4·sin(2πh/24) + b5·cos(2πh/24)`

Usa VPD (calculado del sensor o del pronóstico), ET0 horaria de Open-Meteo (si está vigente; si no, aproximación 0.12·VPD), Kc de la etapa y la hora del día.

## Aprendizaje

- **RLS** (mínimos cuadrados recursivos) con **previa bayesiana** (regularización hacia un supuesto inicial: ganancia `ia_gain_prior`, marcada "NO calibrada"; con la cama registrada vale 1 / (litros por punto) = 0.27 pp/L para 1 m² × 37.5 cm, antes 2 pp/L por defecto) y factor de olvido cercano a 1 (A: 0.995 ≈ 200 riegos; B: 0.999 ≈ 6 semanas de horas): aprende en verano e invierno sin que pocos datos recientes borren lo aprendido.
- Tope de covarianza (evita "wind-up"), **rechazo de atípicos** aislados (residuo > 4σ) y **detección de cambios** (CUSUM o 3 atípicos seguidos): si el suelo/sensor cambia de verdad, vuelve a VALIDACIÓN y se adapta más rápido **sin borrar** el modelo.
- **Cuándo aprende A:** tras cada riego ≥ 0.1 L, con la primera lectura nueva después de la infiltración.
- **Cuándo aprende B:** con pares de lecturas separados ≥ 1 h **sin agua** (sin riego en las últimas `infilt + 30` min y sin aumentos no explicados): los periodos sin riego también enseñan.
- El error de validación se registra **antes** de aprender (fuera de muestra).
- Una nueva **versión de datos** (calibración/suelo) reinicia el modelo; el historial completo se conserva en SQLite.

## Estados

| Estado | Condición | Qué hace el modo IA |
|---|---|---|
| APRENDIZAJE | < `ia_min_events` (6) riegos o < `ia_min_hours` (48) h de secado | Usa el **automático conservador**; el plan solo se registra (modo sombra) |
| VALIDACION | Datos suficientes pero error medio > tolerancia (A ≤ 2 pp, B ≤ 0.4 pp/h) o cambio detectado | Igual: automático conservador |
| PREDICTIVO_ACTIVO | Datos suficientes y errores dentro de tolerancia | Dosifica por modelo |

No se llama "modelo entrenado" sin datos: el ESP32 de pruebas está en **APRENDIZAJE** (no tiene sensores conectados).

## Plan de riego

En el horario preferido calcula el horizonte hasta el **siguiente** horario (p. ej. 06:00 → 18:00 = 12 h, o al día siguiente si no hay ventana vespertina) y simula la humedad hora a hora:
- Si al final sigue sobre `mínima + margen` → **no riega** (no sube la humedad innecesariamente).
- Si no: meta = `mínima + margen + pérdida prevista` (la **menor** que mantiene la banda), litros = (meta − actual) / ganancia prevista.
- Si la meta supera la **reserva superior** → riega solo hasta la reserva e informa **IA_LIMITED** ("no alcanzable sin exceder límites").
- Tras cada dosis e infiltración, **corrección proporcional acotada**: `L = Kp·error/ganancia`, `Kp = 0.8`, máximo `liters_per_cycle`; termina dentro de ±tolerancia/2.
- **Emergencia** (bajo el umbral crítico): riega aunque sea fuera de horario, un ciclo limitado; se registra el error de predicción.

Meta inicial de precisión: ±2 pp tras la infiltración **si las mediciones y la calibración lo permiten. No es garantía de exactitud física.**

## Servidor

- Guarda cada hora la predicción "humedad en 1 h" y la compara con la lectura real (`predictions`): comparación por versión de modelo, estación, cultivo y etapa.
- Guarda observaciones (predicho vs real, usado/atípico) y versiones del modelo (`ia_observations`, `ia_snapshots`).
- El ahorro de agua **solo** se mostrará con una comparación válida; hoy se muestran consumos medidos por pulsos.

## Pruebas

- 11 escenarios de IA en `logic_tests.c` (PC y ESP32): aprende la ganancia real (3.5 pp/L ± 0.5), descarta atípicos, detecta cambios, plan mínimo/limitado, corrección acotada, emergencia.
- Simulador: 14 días simulados → PREDICTIVO_ACTIVO con error 0.25 pp (respuesta) y 0.17–0.20 pp/h (secado). **Es un modelo de DATOS SIMULADOS**: no describe el suelo real y no se copia al ESP32.
