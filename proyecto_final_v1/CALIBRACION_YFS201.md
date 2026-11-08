# Calibración del caudalímetro YF-S201

## 1. Estado actual: **sin calibración física**
El firmware usa **450 pulsos/L** (`pulses_per_liter`), el mismo valor de la Actividad 2.3 y de las Pruebas 01–03. Es el valor nominal del fabricante (f ≈ 7.5·Q → 450 pulsos/L) y **nunca se ha comparado contra un recipiente graduado**. Los "litros" que reporta el sistema son **litros calculados por pulsos**.

## 2. Análisis de la Actividad 2.3 (Control de Consumo de Agua)
| Volumen programado | Corte del programa | Pulsos registrados | Exceso sobre el corte |
|---|---|---|---|
| 1 L | 450 | 481 | +31 |
| 2 L | 900 | 920 | +20 |
| 3 L | 1350 | 1390 | +40 |
| 4 L | 1800 | 1850 | +50 |
| 5 L | 2250 | 2315 | +65 |

- Los **pulsos** son mediciones del propio sensor.
- Los "litros entregados" del reporte (1.069, 2.044 … L) se calcularon como **pulsos / 450**. El "error %" del reporte compara el sensor **consigo mismo**: mide cuántos pulsos pasaron **después** del corte (sobrepaso), no la exactitud del caudalímetro.
- El sobrepaso se explica por la lectura del contador cada 100 ms, el tiempo de conmutación del relevador y la inercia del agua. En esa práctica **no había electroválvula**, que sí hay en este sistema.
- La foto de evidencia del reporte muestra 451 y 526 pulsos, que **no coinciden** con la tabla (481). No se usan esos datos para calibrar.
- El proyecto MQTT anterior (`Practica4_MQTT`) tenía `PULSOS_X_LITRO 480`. No se encontró una medición física que lo respalde; probablemente viene de los 481 pulsos de la prueba de 1 L, que es una medida de sobrepaso.

### Prueba 03 (este proyecto, 2026-10-09)
Objetivo 450 pulsos; corte a 19.7 s; **455 pulsos** al cerrar la válvula y 458 en reposo → sobrepaso de 5 a 8 pulsos (11–18 mL calculados). Mucho menor que en la 2.3 porque el firmware revisa el contador cada 20 ms y la válvula corta la línea. Tampoco es una calibración física.

## 3. Procedimiento de calibración con recipiente graduado
Material: recipiente graduado de al menos 2 L (o cubeta y báscula: 1 g ≈ 1 mL de agua), tinaco con agua, descarga libre al recipiente.

1. Purgue el aire de la línea con un riego corto (`START 0.5`) y descarte esa agua.
2. Vacíe el recipiente. Consola: `ESTADO` → anote `Pulsos` (P0).
3. Ejecute `START 2` (o el volumen de prueba).
4. Al terminar, espere 10 s a que escurra y mida el volumen real **V_real** (mL) en el recipiente.
5. `ESTADO` → anote `Pulsos` (P1). Pulsos del ensayo: **N = P1 − P0**. Incluye los pulsos posteriores al cierre, porque también son agua entregada.
6. Repita **al menos 5 veces** con 1, 2 y 3 L, al caudal real de trabajo (aspersores instalados).
7. Para cada ensayo calcule `K = N / (V_real / 1000)` [pulsos/L]. Use el **promedio** y revise la dispersión: debería ser < 5 %.
8. Cargue el factor:
   - Consola: `CALFLUJO <N_total> <mL_totales>` (suma de todos los ensayos) o `SET pulses_per_liter <K>`
   - MQTT: `{"cmd":"SET_FLOW_CALIBRATION","pulses":<N>,"measured_ml":<V_real>}` o `{"cmd":"SET_FLOW_CALIBRATION","pulses_per_liter":<K>}`
9. **Sobrepaso:** con el factor nuevo, ejecute `START 1` cinco veces y mida. Si de forma sistemática entrega más del objetivo, configure `SET overrun_ml <exceso_promedio>`: el firmware cortará ese volumen antes.

### Tabla de registro (llenar)
| Ensayo | Objetivo | P0 | P1 | N | V_real (mL) | K = N/(V/1000) |
|---|---|---|---|---|---|---|
| 1 | 1 L | | | | | |
| 2 | 1 L | | | | | |
| 3 | 2 L | | | | | |
| 4 | 2 L | | | | | |
| 5 | 3 L | | | | | |
| **Promedio** | | | | | | |

## 4. Notas
- El YF-S201 es de ±10 % según los distribuidores, y su respuesta cambia con el caudal. Calíbrelo al caudal real, con los 9 aspersores.
- Instálelo con la flecha en el sentido del flujo, en tramo recto y sin aire.
- El factor anterior queda en el historial de configuración de este documento. No sobrescriba los resultados experimentales.
