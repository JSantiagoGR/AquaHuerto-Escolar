# Supuestos y pendientes — v3 (corregido)

**Contexto:**
- **Diseño principal:** Escenario A con **SUBIDA VERTICAL**, cruz a z 1.52 m y **3 líneas × 3 aspersores = 9**.
- **Límite de compra:** **4.00 m de Tuboplus nuevo**. El diseño A se estima hoy en 5.148 m y cumple si M1 + M5 ≤ 1.662 m.
- **Escenario B (45°):** solo contingencia.
- **Bomba:** 12 V, 6 A, 72 W, 6 L/min máximo anunciado. **0.9 MPa = 130 psi es el corte del presostato.** Curva Q‑H PROVISIONAL.
- **Sin filtro.**

## 1. MEDICIONES FÍSICAS NECESARIAS

Todas editables en `CONFIG["medidas"]` de `generar_modelo.py` (también listadas en `mediciones_fisicas.csv`). Al medir: cambiar `valor`, poner `estado: "MEDIDO"` y regenerar. El veredicto de 4.00 m se recalcula solo.

| # | Clave | Medición | Valor estimado hoy | Cómo medir |
|---|---|---|---|---|
| 1 | M1_d_bajada_a_bomba | Distancia horizontal del final de la bajada existente (eje) a la zona de la bomba (cara de la unión de succión) | 0.07 m | Presentar el codo y el conjunto de la bomba; flexómetro |
| 2 | M2_L_conjunto_bomba | Longitud ocupada por bomba + adaptadores + uniones | 0.295 m | Armar en banco y medir de cara a cara |
| 3 | M3_L_conjunto_yf | Longitud ocupada por YF‑S201 + adaptadores | 0.136 m | Armar y medir |
| 4 | M4_L_conjunto_ev (+ M4b niples) | Longitud ocupada por electroválvula + adaptadores (y niples entre conjuntos) | 0.159 m (+ 2 × 0.06 m) | Armar y medir |
| 5 | M5_d_conjunto_a_subida | Distancia horizontal del conjunto (salida EV) al inicio de la subida | 2.74 m | Flexómetro en línea recta hacia el cajón |
| 6 | M6_z_superior_cajon | Altura del piso a la parte superior del cajón | 0.52 m | Flexómetro |
| 7 | M7_h_cruz_sobre_cajon | Altura adicional hasta la cruz | 1.00 m | Definir y medir |
| 8 | M8_d_superior_a_cruz | Distancia horizontal superior (eje de la subida → eje de la cruz) | 0.083 m | Flexómetro |
| 9 | M9 / M9b | Diámetro interior / exterior de la manguera negra | 12 / 16 mm **NO MEDIDO** | Vernier |
| 10 | M10_rosca_bomba | Diámetro, paso y tipo de rosca de los puertos de la bomba | ~3/8" (NPT o BSP sin confirmar) | Galga de roscas (NPT 18 hilos/in, BSP 19 hilos/in) |
| 11 | M11 / M11b | Posición exacta de las 3 líneas y de los aspersores | 0.17 / 0.50 / 0.83 m | Medir sobre el cajón |
| 12 | M12_L_lineas | Longitud real de cada línea de manguera | 0.905 m c/u (calculada) | Medir cada manguera cortada |
| 13 | M0_z_linea_principal | Altura de la línea principal / pie de la bajada | 0.08 m | Flexómetro |
| — | X_borde_cajon, L_existente | Distancia tinaco → cajón y tramos existentes | 4.00 m; 0.04/0.06/0.055/0.15 m | Flexómetro |

**Veredicto actual (estimado):** el escenario A requiere ≈ 5.148 m (excede 1.148 m). A cumple si **M1 + M5 ≤ 1.662 m** con el resto de medidas como hoy. **No se puede confirmar ni descartar hasta medir.**

## 2. Otros pendientes de validación física

| # | Pendiente | Por qué importa | Cómo |
|---|---|---|---|
| P1 | **Curva Q‑H real de la bomba** | Define todas las presiones (hoy son preliminares) | Manómetro + válvula + probeta a 12 V: ≥ 5 puntos hasta el corte |
| P2 | **Ciclado del presostato** con 9 aspersores parcialmente abiertos | Arranques y paradas, presión pulsante, falsa alarma de “sin flujo” en el ESP32 | Registrar presión, corriente y pulsos del YF durante 5–10 min |
| P3 | Marca, modelo, curva P‑Q y **relación apertura‑caudal** de los aspersores | Presión mínima requerida; no se supone linealidad | Etiqueta/foto; aforo a distintas aperturas y presiones |
| P4 | **Uniformidad de RIEGO** (no hidráulica) | La relación Pmin/Pmax = 0.9998 no la garantiza: faltan patrón de mojado, radio, presión mínima y el efecto de la altura de 1 m | Prueba con recipientes en malla sobre el cajón |
| P5 | Rosca de la bomba (ver M10) | Compra del adaptador | Galga |
| P6 | Kv de la electroválvula; pérdidas del YF‑S201 y de los adaptadores | Sensibilidad ≤ 1.1 m | Ficha o manómetros |
| P7 | Tinaco definitivo | Nivel y cota de salida | Medir |
| P8 | Soportes de la subida vertical (1.44 m) y de la cruz y los laterales a 1.52 m | Seguridad mecánica | Diseño |
| P9 | Recomendación no incluida en v3: filtro | Algunos aspersores lo requieren | Revisar al identificar el aspersor |

## 3. Supuestos

- Régimen permanente de riego (bola abierta, check CV, EV OPEN, bomba ON).
- Aspersores con caudal impuesto e iguales entre sí, a la cota del lateral (z 1.52 m).
- Presostato no modelado (EPANET es estacionario).
- Agua a 20 °C; K estimados según `CONFIG["K"]`.
