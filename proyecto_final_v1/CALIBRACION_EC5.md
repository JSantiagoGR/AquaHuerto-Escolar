# Calibración del sensor de humedad del suelo EC-5

## 1. Origen: Actividad 2.2 (Sistema de Adquisición de Datos)

**Condiciones de la medición (del reporte):**
- ESP32 con el EC-5 **excitado directamente desde un GPIO a 3.3 V** con pulsos de **10 ms**: código `gpio_set_level(OUTPUT_PIN, 1); vTaskDelay(10 ms); adc_oneshot_read(...)`.
- Lectura con `adc_oneshot` de ADC1 y `adc_cali_raw_to_voltage` (calibración de ESP-IDF).
- Muestras: 600 mL de tierra seca con 0, 105, 257 y 490 mL de agua. Se definió %VWC = V_agua / (V_tierra + V_agua) × 100.

| %VWC preparado | mV medidos |
|---|---|
| 0 | 360 |
| 15 | 420 |
| 30 | 630 |
| 45 | 870 |

Los valores ADC (1340, 1564, 2346, 3239) de la tabla del reporte son **teóricos** (calculados con 1.1 V de fondo de escala); **no** son lecturas. Lo medido son los mV.

**Regresión lineal:**
- Fracción: `VWC = 0.0008146067 · mV − 0.2393258427`
- Porcentaje (la que usa el firmware): **`%VWC = 0.08146067 · mV − 23.932584`**
- R² ≈ 0.94494

## 2. Diferencias detectadas en el PDF (revisadas antes de elegir pines)
| Fuente en el PDF | Excitación | Salida |
|---|---|---|
| Esquemático (figura 1) | GPIO25 "SENSOR_POWER" (dibujado con un ESP32-S3) | GPIO34 / ADC1_CH6 |
| Diagrama de conexiones (figura 2) | D2 / GPIO2 | D32 / GPIO32 (ADC1_CH4) |
| Código | `OUTPUT_PIN` (sin valor en el texto) | `ADC1_CHANNEL_VAR1` (sin valor) |

**Decisión:** GPIO25 para excitación y **GPIO34 (ADC1_CH6)** para la salida.
- GPIO2 es pin de arranque (strapping): no conviene manejarlo en el arranque.
- GPIO34 es ADC1, que funciona con Wi-Fi activo (ADC2 no).
- La placa del proyecto es un ESP32-D0WD-V3 (no un S3); GPIO25 y GPIO34 existen y están libres.

## 3. Limitaciones de esta calibración
1. **Solo 4 puntos y R² = 0.945.** La recta no pasa por los puntos: a 360 mV da **5.4 %**, no 0 %, y a 420 mV da 10.3 % en lugar de 15 %. Error típico de varios puntos de %VWC.
2. **Intervalo validado: 360–870 mV ≈ 0–45 %VWC.** Fuera de él la recta es extrapolación. El firmware marca `in_cal_range = false` y `status = OK_FUERA_DE_CALIBRACION` si la lectura sale de 360–870 mV (±5 %).
3. **Una sola tierra** (la de la práctica). Otro sustrato o una mezcla con composta puede cambiar la respuesta.
4. **Definición de %VWC usada** (V_agua / (V_tierra + V_agua)): es una aproximación; el %VWC estricto es V_agua / V_total de la muestra compactada.
5. **Excitación a 3.3 V desde GPIO.** La ecuación del fabricante (θ = 1.19×10⁻³·mV − 0.401) **solo vale a 2.5 V**; por eso no se usa: la regresión propia se hizo en las mismas condiciones que el firmware (GPIO a 3.3 V, pulso de 10 ms).
6. **Atenuación del ADC:** el firmware usa 12 dB (rango ~0–3.1 V) para detectar lecturas imposibles. El reporte mencionaba un rango de 1.1 V. Como `adc_cali` convierte a mV, la diferencia esperada es pequeña, pero hay que **verificarla con una lectura comparativa** (pendiente físico).

**Conclusión:** es un punto de partida real, no una calibración definitiva.

## 4. Cómo la usa el firmware
- Excitación: GPIO25 en alto ~9.6 ms (`EC5_POWER_ACTIVE_HIGH=1`, máxima corriente del pin). El EC-5 nunca queda alimentado de forma continua.
- 5 pulsos separados 200 ms; en cada uno se promedian 4 lecturas ADC al final del pulso.
- Se usa la **mediana** de los 5 pulsos (filtra picos sin ocultar cambios reales; cada lectura es independiente).
- Validez:
  | Condición | Estado |
  |---|---|
  | mV < `ec5_mv_min` (200) | `SIN_SENAL` (desconectado, cable roto, sin excitación) |
  | mV > `ec5_mv_max` (1500) | `FUERA_DE_RANGO` |
  | Dispersión entre pulsos > 150 mV | `INESTABLE` |
  | %VWC < −10 o > 70 | `IMPOSIBLE` |
  | Sin calibración ADC | `ADC_ERROR` |
- Intervalo base: `soil_interval_s` = 300 s. Se reduce a la mitad (mínimo 60 s) si la temperatura ≥ `hot_temp_c` o la HR ≤ `dry_rh_pct`. Tras cada infiltración se toma una lectura nueva.
- Parámetros editables sin recompilar: `ec5_slope`, `ec5_offset`, `ec5_mv_min`, `ec5_mv_max`, `ec5_cal_mv_lo`, `ec5_cal_mv_hi`.

### Detección de sensor desconectado
GPIO34 no tiene resistencia interna. Con el sensor desconectado la entrada queda flotando y puede leer cualquier valor. **Recomendado:** resistencia de **1 MΩ de GPIO34 a GND**. No afecta la medición: la salida del EC-5 es de baja impedancia comparada con 1 MΩ. Con ella, el sensor desconectado lee ~0 mV y se detecta como `SIN_SENAL`.

## 5. Recalibración en la tierra del cajón (recomendada)
1. Tome 5 a 6 muestras de la **misma tierra del huerto**, secada (horno a 105 °C, 24 h, o al sol varios días).
2. Prepare contenidos de agua conocidos: por ejemplo 0, 10, 20, 30, 40 y 50 % en volumen, con probeta y la misma compactación.
3. Inserte el EC-5 completo (las dos varillas) en cada muestra. Por consola: `SIM OFF` y `ESTADO`; anote los **mV** (el `%VWC` mostrado aún usa la ecuación vieja). Repita 3 veces por muestra.
4. Calcule la regresión `%VWC = a·mV + b` (Excel / Python). Revise R² y los residuos.
5. Cargue los coeficientes:
   - Consola: `SET ec5_slope <a>`, `SET ec5_offset <b>`, `SET ec5_cal_mv_lo <mV mín>`, `SET ec5_cal_mv_hi <mV máx>`
   - MQTT: `{"cmd":"SET_CONFIG","key":"ec5_slope","value":<a>}` (idem `ec5_offset`)
6. Registre la nueva tabla en este archivo. **No borre la de la Actividad 2.2.**

## 6. Instalación en el cajón
- Varillas completamente enterradas, en vertical u horizontal, en la zona de raíces y a media distancia entre aspersores.
- Sin piedras ni huecos de aire junto a las varillas. Compactar ligeramente al cerrar.
- El cable con una curva de goteo para que el agua no escurra hacia el conector.
- Conector de 3.5 mm y adaptador protegidos de la humedad.
