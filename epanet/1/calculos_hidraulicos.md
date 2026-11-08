# Cálculos hidráulicos — Riego por goteo automatizado, 1 cajón

Modelo EPANET principal: `riego_huerto_final.inp` (simplificado, 4 demandas terminales).
Modelo opcional: `riego_huerto_24_goteros.inp` (24 demandas fijas).
Fecha: 2026-09-28.

> **Estado:** resultados **PRELIMINARES**. Los caudales y las pérdidas por fricción quedan bien definidos con los datos del diseño; las **presiones** dependen de una curva de bomba **provisional** y de elevaciones de **datum (0 m)**, por lo que **no son presiones físicas validadas**.

---

## 1. Fuentes de datos revisadas

| Fuente | Contenido usado |
|---|---|
| `riego_1_cajon.docx` (Descargas) | Cajón 1.20 × 0.80 m; 4 líneas × 6 goteros; 4 L/h; 96 L/h = 1.6 L/min; cadena tinaco → bomba 12 V → YF‑S201 → electroválvula NC 1/2 in → cabezal PE 16 mm (0.8 m) → 4 laterales 16 mm (1.2 m); manguera principal ~1.5 m de 1/2 in; C = 140 (supuesto preliminar); tabla de IDs EPANET (R1, PU1, J‑FLOW, V1, J‑H, L1–L4); lógica de control con histéresis; figuras 1–6 (diseño físico, vista superior, cadena hidráulica, lógica de control, modelo simplificado, modelo de 24 nodos). |
| `Epanet 2.pptx` (Descargas) | Hazen‑Williams SI `hf = 10.67·L·Q^1.852/(C^1.852·D^4.87)`; Darcy‑Weisbach `hf = f(L/D)(V²/2g)`; `Re = ρVD/μ`; laminar `f = 64/Re`; límites 2300/4000; tabla de materiales (PVC: C_H = 150, ε = 0.0015 mm); diagrama de Moody; EPANET 2.2 → Flow units = **LPS**; fotografía de placa de la bomba. |
| Fotografía de la bomba (pptx, imagen 4) | GOOD PUMPS · 12 V (9–14.4 V) · 6 A · 72 W · “The largest flow: 6 L/MIN” · “Pressure Setting: 0.9 MPa” · CE/RoHS. Bomba de diafragma con interruptor de presión (tipo de carcasa visible). |

**Discrepancia de unidades detectada:** el docx (tabla 6.3) proponía `LPM` y demandas de 0.40 L/min. Se sigue la indicación del curso (pptx diapositiva 5) y de la actividad: **Flow Units = LPS**. Por tanto la demanda por lateral es **0.00666667 L/s**, no 0.40 (0.40 es L/min; usarlo en LPS multiplicaría la demanda ×60).

---

## 2. Continuidad y conversiones

Factores: 1 h = 3600 s = 60 min; 1 m³ = 1000 L.

**Gotero**

- Q = 4 L/h
- 4 L/h ÷ 60 min/h = **0.0666667 L/min** ✔
- 4 L/h ÷ 3600 s/h = **0.00111111 L/s** ✔
- 0.00111111 L/s ÷ 1000 L/m³ = **1.11111 × 10⁻⁶ m³/s**

**Lateral (6 goteros)**

- Q = 6 × 4 L/h = **24 L/h** ✔
- 24 ÷ 60 = **0.40 L/min** ✔
- 24 ÷ 3600 = **0.00666667 L/s** ✔ → 6.66667 × 10⁻⁶ m³/s

**Sistema (4 laterales = 24 goteros)**

- Q = 4 × 24 L/h = **96 L/h** ✔
- 96 ÷ 60 = **1.60 L/min** ✔
- 1.60 L/min ÷ 60 s/min = **0.0266667 L/s** ✔ → 2.66667 × 10⁻⁵ m³/s
- Volumen en 10 min: V = 1.60 L/min × 10 min = **16 L** ✔ (suponiendo que todos los goteros entregan su caudal nominal)

**Suma de demandas en el .INP:** 4 × 0.00666667 = 0.02666668 L/s (redondeo; nominal exacto 0.0266667 L/s).
En el modelo de 24 goteros: 24 × 0.001111111 = 0.02666666 L/s.
EPANET reporta caudal de bomba = 0.02666668 L/s (modelo principal): **continuidad cerrada**.

---

## 3. Propiedades asumidas y geometría

**PROPIEDADES ASUMIDAS (no medidas):** agua a ≈20 °C

- ρ = 998.2 kg/m³
- μ = 1.002 × 10⁻³ Pa·s
- g = 9.81 m/s²

**Rugosidad (material de clase, PVC):** ε = 0.0015 mm = 0.0015 × 10⁻³ m = **1.5 × 10⁻⁶ m**.
(El cabezal y los laterales son de PE; se usa el valor de PVC del material de clase como referencia de tubería plástica lisa.)

**Diámetros — APROXIMACIÓN PROVISIONAL (nominales, NO interiores medidos):**

| Tramo | Diámetro usado | Conversión |
|---|---|---|
| Principal (1/2 in) | 12.7 mm | 1/2 in × 25.4 mm/in = 12.7 mm = 0.0127 m |
| Cabezal PE | 16 mm | 16 mm ÷ 1000 = 0.016 m |
| Laterales | 16 mm | 0.016 m |

> El diámetro **interior** real de una manguera “de 16 mm” (nominal = exterior) suele ser menor; como hf ∝ D^‑4.87, un D interior menor aumenta bastante la pérdida. Este dato está pendiente.

---

## 4. Área, velocidad y Reynolds

### 4.1 Área — `A = π D² / 4` (preliminar, con D nominal)

- Principal: A = π (0.0127 m)² / 4 = π × 1.6129 × 10⁻⁴ / 4 = **1.2668 × 10⁻⁴ m²**
- Cabezal: A = π (0.016 m)² / 4 = π × 2.56 × 10⁻⁴ / 4 = **2.0106 × 10⁻⁴ m²**
- Lateral: igual que cabezal = **2.0106 × 10⁻⁴ m²**

### 4.2 Velocidad — `V = Q / A`

- Principal: V = 2.66667 × 10⁻⁵ m³/s ÷ 1.2668 × 10⁻⁴ m² = **0.2105 m/s**
- Cabezal (entrada, Q total): V = 2.66667 × 10⁻⁵ ÷ 2.0106 × 10⁻⁴ = **0.1326 m/s**
- Lateral (entrada): V = 6.66667 × 10⁻⁶ ÷ 2.0106 × 10⁻⁴ = **0.0332 m/s**

El caudal del cabezal **disminuye después de cada derivación** (laterales separados 0.2 m a lo ancho de 0.80 m):

| Segmento cabezal | Longitud | Q (L/s) | V (m/s) |
|---|---|---|---|
| Entrada → lateral 1 | 0.1 m | 0.0266667 (4/4) | 0.1326 |
| Lateral 1 → 2 | 0.2 m | 0.0200000 (3/4) | 0.0995 |
| Lateral 2 → 3 | 0.2 m | 0.0133333 (2/4) | 0.0663 |
| Lateral 3 → 4 | 0.2 m | 0.0066667 (1/4) | 0.0332 |
| Lateral 4 → tapón | 0.1 m | 0 | 0 |

Igualmente, dentro de cada lateral el caudal baja 0.00111111 L/s en cada gotero (6/6 … 1/6). Este reparto se modela en `riego_huerto_24_goteros.inp`.

### 4.3 Reynolds — `Re = ρ V D / μ`

- Principal: Re = 998.2 × 0.2105 × 0.0127 / 1.002 × 10⁻³ = 2.6687 / 1.002 × 10⁻³ = **2663** → **2300 < Re < 4000: TRANSICIÓN**
- Cabezal (Q total): Re = 998.2 × 0.1326 × 0.016 / 1.002 × 10⁻³ = **2114** → **laminar** (cerca del límite)
- Lateral: Re = 998.2 × 0.0332 × 0.016 / 1.002 × 10⁻³ = **528** → **laminar**
- Segmentos del cabezal: 2114, 1586, 1057, 528 → laminar.

---

## 5. Rugosidad relativa y factor de fricción

### 5.1 Rugosidad relativa `ε/D`

- Principal: 1.5 × 10⁻⁶ m / 0.0127 m = **1.18 × 10⁻⁴**
- Cabezal y lateral: 1.5 × 10⁻⁶ / 0.016 = **9.38 × 10⁻⁵**

Son valores muy pequeños: en Moody corresponden a curvas prácticamente de **tubería lisa** (entre las curvas 0.0001 y 0.00005).

### 5.2 Factor de fricción

**Laminar (cabezal y laterales):** `f = 64/Re` (independiente de ε/D).

- Cabezal: f = 64 / 2114 = **0.0303**
- Lateral: f = 64 / 528.5 = **0.1211**

**Principal (transición, Re = 2663):** no existe un f único y fiable en esta zona. Se reportan las dos cotas:

- Cota laminar extrapolada: f = 64 / 2663 = **0.0240**
- Cota turbulenta, **Swamee‑Jain** (aproximación explícita de Colebrook):

  `f = 0.25 / [ log₁₀( ε/(3.7D) + 5.74/Re^0.9 ) ]²`

  ε/(3.7D) = 1.5 × 10⁻⁶ / (3.7 × 0.0127) = 3.19 × 10⁻⁵
  5.74 / 2663^0.9 = 4.74 × 10⁻³
  log₁₀(3.19 × 10⁻⁵ + 4.74 × 10⁻³) = −2.3211
  f = 0.25 / (−2.3211)² = **0.0464**

- Comprobación numérica con **Colebrook‑White** iterado: `1/√f = −2 log₁₀( ε/(3.7D) + 2.51/(Re √f) )` → **f = 0.0453** (Swamee‑Jain difiere 2.6 %, aceptable).

> Swamee‑Jain/Colebrook son válidos para flujo turbulento (Re > 4000); a Re = 2663 se usan solo como **cota superior**. El valor real está entre 0.024 y 0.046 y depende de perturbaciones de entrada, accesorios, etc. **No se pretende mayor precisión.**

### 5.3 Verificación cualitativa con el diagrama de Moody

- Laterales (Re ≈ 530) y cabezal (Re ≈ 2100): caen sobre la **recta laminar f = 64/Re**, a la izquierda de la zona gris de transición. En esa recta la rugosidad no influye → coherente con f = 0.121 y 0.030.
- Principal (Re ≈ 2660): cae **dentro de la franja gris de transición** del diagrama (≈ 2000–4000), donde Moody no define una curva; el diagrama muestra f entre ≈ 0.025 (prolongación laminar) y ≈ 0.045–0.05 (inicio de las curvas turbulentas lisas). Coherente con el rango 0.024–0.046 calculado.
- ε/D ≈ 10⁻⁴ está en las curvas inferiores (casi lisa); a estos Re bajos las curvas de ε/D ≤ 0.0001 se confunden con la de tubería lisa. ✔

---

## 6. Darcy‑Weisbach — `hf = f (L/D) (V²/2g)`

**Principal** (L = 1.5 m, D = 0.0127 m, L/D = 118.11, V²/2g = 0.2105² / 19.62 = 2.2586 × 10⁻³ m):

- Cota laminar: hf = 0.0240 × 118.11 × 2.2586 × 10⁻³ = **0.00641 m**
- Cota turbulenta (Colebrook): hf = 0.0453 × 118.11 × 2.2586 × 10⁻³ = **0.01207 m** (Swamee‑Jain: 0.01238 m)
- EPANET D‑W (interpolación de Moody en transición, ε = 0.0015 mm): **0.00791 m**

**Cabezal, Q total** (L = 0.8 m, L/D = 50, V²/2g = 8.966 × 10⁻⁴ m):
hf = 0.0303 × 50 × 8.966 × 10⁻⁴ = **0.00136 m**

**Lateral, Q total al extremo** (L = 1.2 m, L/D = 75, V²/2g = 5.603 × 10⁻⁵ m):
hf = 0.1211 × 75 × 5.603 × 10⁻⁵ = **5.09 × 10⁻⁴ m**

---

## 7. Hazen‑Williams SI — `hf = 10.67 L Q^1.852 / (C^1.852 D^4.87)`

Unidades: hf [m], L [m], Q [m³/s], D [m], C [adimensional].
Conversiones: Q (L/s) ÷ 1000 → m³/s; D (mm) ÷ 1000 → m.
Potencias: 140^1.852 = 9432.6; 150^1.852 = 10718.2; 0.0127^4.87 = 5.828 × 10⁻¹⁰; 0.016^4.87 = 1.795 × 10⁻⁹;
(2.66667 × 10⁻⁵)^1.852 = 3.3798 × 10⁻⁹; (6.66667 × 10⁻⁶)^1.852 = 2.5935 × 10⁻¹⁰.

**Principal**

- C = 140: hf = 10.67 × 1.5 × 3.3798 × 10⁻⁹ / (9432.6 × 5.828 × 10⁻¹⁰) = 5.4094 × 10⁻⁸ / 5.4973 × 10⁻⁶ = **0.00984 m**
- C = 150: hf = 5.4094 × 10⁻⁸ / (10718.2 × 5.828 × 10⁻¹⁰) = **0.00866 m**

**Cabezal (Q total)**

- C = 140: hf = 10.67 × 0.8 × 3.3798 × 10⁻⁹ / (9432.6 × 1.795 × 10⁻⁹) = 2.8850 × 10⁻⁸ / 1.6932 × 10⁻⁵ = **0.00170 m**
- C = 150: **0.00150 m**

**Cada lateral (PL1 = PL2 = PL3 = PL4, Q total al extremo)**

- C = 140: hf = 10.67 × 1.2 × 2.5935 × 10⁻¹⁰ / (9432.6 × 1.795 × 10⁻⁹) = 3.3207 × 10⁻⁹ / 1.6932 × 10⁻⁵ = **1.96 × 10⁻⁴ m**
- C = 150: **1.73 × 10⁻⁴ m**

---

## 8. Tabla comparativa

D nominal (provisional). hf en metros. f del principal = rango de transición.

| Tramo | L (m) | D (mm) | Q (L/s) | V (m/s) | Re | Régimen | f | hf D‑W (m) | hf H‑W C=140 (m) | hf H‑W C=150 (m) |
|---|---|---|---|---|---|---|---|---|---|---|
| P‑MAIN | 1.5 | 12.7 | 0.0266667 | 0.2105 | 2663 | Transición | 0.024 – 0.045 | 0.0064 – 0.0121 (EPANET: 0.0079) | 0.00984 | 0.00866 |
| V1 (enlace ON/OFF) | 0.01 | 12.7 | 0.0266667 | 0.2105 | 2663 | Transición | 0.024 – 0.045 | 4.3e‑5 – 8.0e‑5 | 6.6e‑5 | 5.8e‑5 |
| P‑HEADER (Q total) | 0.8 | 16 | 0.0266667 | 0.1326 | 2114 | Laminar | 0.0303 | 0.00136 | 0.00170 | 0.00150 |
| PL1…PL4 (c/u, Q total) | 1.2 | 16 | 0.00666667 | 0.0332 | 528 | Laminar | 0.1211 | 5.09e‑4 | 1.96e‑4 | 1.73e‑4 |
| Cabezal seg. 1 | 0.1 | 16 | 0.0266667 | 0.1326 | 2114 | Laminar | 0.0303 | 1.70e‑4 | 2.13e‑4 | 1.87e‑4 |
| Cabezal seg. 2 | 0.2 | 16 | 0.0200000 | 0.0995 | 1586 | Laminar | 0.0404 | 2.55e‑4 | 2.50e‑4 | 2.20e‑4 |
| Cabezal seg. 3 | 0.2 | 16 | 0.0133333 | 0.0663 | 1057 | Laminar | 0.0606 | 1.70e‑4 | 1.18e‑4 | 1.04e‑4 |
| Cabezal seg. 4 | 0.2 | 16 | 0.0066667 | 0.0332 | 528 | Laminar | 0.1211 | 8.5e‑5 | 3.3e‑5 | 2.9e‑5 |

**Pérdida total por fricción bomba → final del lateral (modelo simplificado):**
H‑W C=140: 0.0119 m · H‑W C=150: 0.0104 m · D‑W (EPANET): 0.0099 m.
Es decir, **≈ 1 cm de columna de agua**: la fricción en tuberías es despreciable frente a las incógnitas pendientes (desnivel tinaco‑cajón, pérdidas del YF‑S201, electroválvula y accesorios, curva de la bomba).

**Modelo base vs. material de clase:**
- **C = 140** → modelo EPANET **base** (supuesto preliminar del documento de diseño).
- **C = 150** → referencia del **material de clase** (tabla PVC). Reduce las pérdidas ≈ 12 % (factor (140/150)^1.852 = 0.880). No cambia caudales ni conclusiones.

### ¿Por qué Hazen‑Williams y Darcy‑Weisbach no coinciden?

1. **Hazen‑Williams es empírico** y se ajustó para agua en **flujo turbulento** en tuberías de diámetro mayor (típ. > 50 mm, V ≈ 1 m/s). Su exponente fijo 1.852 y C constante no representan el flujo laminar.
2. **Darcy‑Weisbach es físicamente fundamentado**: f depende de Re y ε/D. En régimen laminar hf ∝ Q¹ (f = 64/Re), mientras H‑W supone hf ∝ Q^1.852.
3. Por eso, a Re ≈ 500 (laterales) H‑W **subestima** la pérdida ≈ 2.6 veces (1.96e‑4 vs 5.09e‑4 m); en el cabezal (Re ≈ 2100) coinciden mejor, y en el principal (transición) H‑W queda dentro del rango D‑W.
4. Para este sistema de microirrigación (Re < 4000 en todos los tramos) **Darcy‑Weisbach es el método más apropiado**. Se mantiene H‑W C=140 como modelo EPANET base por indicación del diseño; en cualquier caso la diferencia absoluta es < 1 cm.

---

## 9. Bomba: altura de referencia y curva PROVISIONAL

### 9.1 Búsqueda de la curva real

Se buscó la bomba por marca/placa (GOOD PUMPS, 12 V, 6 A, 72 W, 6 L/min, 0.9 MPa). Solo se encontraron **anuncios comerciales** (eBay, Amazon, AliExpress, tiendas electrónicas) que repiten los datos de placa; **ninguna hoja técnica del fabricante ni curva Q‑H verificable**. No se usa la curva de ninguna otra bomba “parecida”.
→ **Curva Q‑H real: PENDIENTE.**

### 9.2 Altura equivalente a 0.9 MPa

`H = P / (ρ g)` = 0.9 × 10⁶ Pa / (998.2 kg/m³ × 9.81 m/s²) = 0.9 × 10⁶ (kg·m⁻¹·s⁻²) / 9792.3 (kg·m⁻²·s⁻²) = **91.91 m**
(con ρ = 1000: 91.74 m).

“Pressure Setting” = presión de ajuste del **interruptor de presión** de la bomba de diafragma (la bomba se apaga al alcanzarla). **No es una presión garantizada a ningún caudal**, y en particular **no significa 6 L/min a 0.9 MPa**.

### 9.3 PUMP_CURVE_PROVISIONAL

**Esta curva no corresponde necesariamente a la curva certificada del fabricante. Se utiliza únicamente para comprobar topología, continuidad y funcionamiento computacional del modelo.**

Hipótesis de construcción: los dos datos de placa se interpretan como extremos — Q = 6 L/min = 0.1 L/s a H ≈ 0 (“largest flow”) y H = 91.91 m a Q ≈ 0 (corte del presostato) — con interpolación lineal (simplificación habitual de bombas de diafragma):

| Q (L/s) | H (m) |
|---|---|
| 0.000 | 91.91 |
| 0.050 | 45.96 |
| 0.100 | 0.00 |

Punto de operación calculado: H = 91.91 × (1 − 0.0266667/0.1) = **67.40 m** (EPANET: 67.406 m). Potencia hidráulica ρgQH ≈ 17.6 W (< 72 W eléctricos).

**La simulación hidráulica definitiva requiere la curva Q‑H real.** No se concluye que la bomba cumpla.

**Observación de ingeniería:** con demandas fijas (DDA) el caudal lo imponen las demandas; la bomba solo fija el nivel de altura. Por eso **caudales y pérdidas son independientes de la curva** (verificado: con una curva 20 % más baja, las pérdidas no cambian y todas las presiones bajan 13.48 m). Una bomba de diafragma con presostato que trabaja a ~27 % de su caudal máximo tenderá a presiones altas; en la realidad los goteros (no compensados) entregarían **más** de 4 L/h a presiones altas, o la bomba ciclaría por el presostato. Esto debe verificarse con la curva real, la presión admisible del gotero/manguera y, si procede, un regulador de presión (a decidir cuando existan esos datos).

---

## 10. Resultados EPANET — escenario RIEGO ACTIVO (`riego_huerto_final.inp`)

Motor: EPANET 2.2 (librería del toolkit incluida en WNTR 1.5.0), contrastado con OWA‑EPANET 2.3.5 vía EPyT y con el servidor **MCP EPANET** (mismos resultados). Unidades: LPS, m.

**Resultado preliminar dependiente de la curva provisional de bomba y del datum de elevación 0 m.**

### Nodos

| Nodo | Head (m) | Pressure (m) | Demand (L/s) |
|---|---|---|---|
| R1 (tinaco, datum) | 0.0000 | 0.0000 | −0.02666668 (suministro) |
| J‑PUMP | 67.4057 | 67.4057 | 0 |
| J‑FLOW (YF‑S201) | 67.3959 | 67.3959 | 0 |
| J‑HEAD‑IN | 67.3958 | 67.3958 | 0 |
| J‑H | 67.3941 | 67.3941 | 0 |
| L1 | 67.3939 | 67.3939 | 0.00666667 |
| L2 | 67.3939 | 67.3939 | 0.00666667 |
| L3 | 67.3939 | 67.3939 | 0.00666667 |
| L4 | 67.3939 | 67.3939 | 0.00666667 |

### Enlaces

| Enlace | Tipo | Flow (L/s) | Velocity (m/s) | Headloss (m) | Status |
|---|---|---|---|---|---|
| PU1 | Pump | 0.02666668 | — | Head gain = **67.406** | OPEN (ON) |
| P‑MAIN | Pipe | 0.02666668 | 0.2105 | 0.00988 | OPEN |
| V1 (electroválvula) | Pipe ON/OFF | 0.02666668 | 0.2105 | 0.00007 | **OPEN** (riego) |
| P‑HEADER | Pipe | 0.02666668 | 0.1326 | 0.00171 | OPEN |
| PL1 / PL2 / PL3 / PL4 | Pipe | 0.00666667 c/u | 0.0332 | 0.00020 c/u | OPEN |

✔ Caudal total 0.0266667 L/s = 1.60 L/min = 96 L/h. ✔ Cada lateral 0.00666667 L/s. ✔ Pérdidas EPANET = cálculo manual H‑W (diferencias < 0.5 %, por redondeo).

### Sensibilidad en EPANET

| Escenario | Head bomba (m) | hf P‑MAIN (m) | hf P‑HEADER (m) | hf PL (m) | P en L1 (m) |
|---|---|---|---|---|---|
| H‑W C = 140 (**base**) | 67.406 | 0.00988 | 0.00171 | 1.97e‑4 | 67.394 |
| H‑W C = 150 (material de clase) | 67.406 | 0.00870 | 0.00151 | 1.73e‑4 | 67.395 |
| D‑W ε = 0.0015 mm | 67.406 | 0.00791 | 0.00139 | 5.18e‑4 | 67.396 |
| H‑W C=140, curva −20 % | 53.927 | 0.00988 | 0.00171 | 1.97e‑4 | 53.915 |

### Modelo detallado de 24 goteros (`riego_huerto_24_goteros.inp`)

- Cada gotero = **DEMANDA FIJA** 0.001111111 L/s. **Demanda fija no equivale a emisor dependiente de presión**: no puede mostrar variación de caudal entre goteros, solo de presión.
- Caudal total 0.02666666 L/s; cabezal 0.0267 → 0.0200 → 0.0133 → 0.0067 L/s; cada lateral 0.00667 → 0.00111 L/s.
- Pérdida por lateral (distribuida): 7.0e‑5 m (H‑W 140) frente a 1.97e‑4 m del modelo simplificado (que concentra todo el caudal al extremo, conservador; factor ≈ 0.35).
- Diferencia de presión entre el gotero más favorecido (E11) y el más alejado (E46): **0.46 mm** (H‑W 140) / 0.73 mm (D‑W). Con estos supuestos la uniformidad hidráulica por fricción es prácticamente perfecta; la no‑uniformidad real vendrá de desniveles del terreno, tolerancias del gotero y obstrucciones.

---

## 11. Supuestos (todos provisionales)

1. Tinaco = Reservoir R1, Head = 0 m. **ESTO NO SIGNIFICA QUE EL NIVEL REAL DEL TINACO SEA 0 m**; es un datum.
2. Elevación de todos los junctions = 0 m: datum común, **no elevaciones medidas**.
3. Diámetros nominales usados como interiores (12.7 mm y 16 mm).
4. C = 140 (base), C = 150 (sensibilidad), ε = 0.0015 mm (PVC, material de clase).
5. Agua a 20 °C (ρ = 998.2 kg/m³, μ = 1.002 × 10⁻³ Pa·s).
6. Curva de bomba **PUMP_CURVE_PROVISIONAL** (sección 9.3).
7. YF‑S201: junction J‑FLOW sin pérdida propia (**pérdida adicional = 0, falta caracterizar**).
8. Electroválvula V1: enlace ON/OFF (Pipe 0.01 m, D 12.7 mm, K = 0) con estado **OPEN** en riego activo. Se probó primero una válvula TCV con K = 0; EPANET la trata como resistencia nula y produjo un desbalance numérico de continuidad (~6 × 10⁻⁷ L/s entre enlaces en serie), por lo que se sustituyó. **K/Cv/Kv real pendiente**; cuando exista podrá usarse TCV con Setting = K real.
9. Sin pérdidas menores en accesorios (tee, adaptador 1/2 in → 16 mm, conectores de arranque).
10. Laterales del modelo simplificado: todo el caudal concentrado al extremo (conservador).
11. Escenario estático (Duration 0): riego activo en régimen permanente.

## 12. Datos pendientes

Ver `datos_pendientes_validacion_final.md`. Principales: curva Q‑H real de la bomba (y modelo exacto), nivel y altura del tinaco, elevación del cajón, desnivel tinaco‑cajón, diámetros interiores reales, pérdida del YF‑S201, Cv/Kv de la electroválvula, curva presión‑caudal / emitter coefficient de los goteros, presión máxima admisible de goteros y manguera.

---

## 13. FUENTES CONSULTADAS

- U.S. EPA. *EPANET 2.2 User Manual*, EPA/600/R‑20/133 (2020). https://www.epa.gov/system/files/documents/2021-07/epanet_users_manual_2.2.0-1.pdf — unidades, formato .INP, bombas (curvas de 1 y 3 puntos), válvulas, emisores, D‑W con interpolación en transición.
- U.S. EPA. EPANET. https://www.epa.gov/water-research/epanet
- OpenWaterAnalytics, EPANET (toolkit OWA). https://github.com/OpenWaterAnalytics/EPANET
- USEPA/Sandia, WNTR 1.5.0 (Python; incluye librería EPANET 2.2). https://github.com/USEPA/WNTR
- EPyT — EPANET Python Toolkit (OWA‑EPANET 2.3.5). https://github.com/OpenWaterAnalytics/EPyT
- KWR‑Water, *epanet-mcp-server* (paquete `mcp-server-epanet` 1.30.0). https://github.com/KWR-Water/epanet-mcp-server
- Material de clase `Epanet 2.pptx` (fórmulas, tabla de materiales, diagrama de Moody) y documento `riego_1_cajon.docx`.
- Búsqueda de la bomba (solo anuncios comerciales, **no usados como curva**): p. ej. https://www.ebay.com/itm/296626432825 , https://www.aliexpress.com/item/1005005564374311.html
- Swamee, P. K. & Jain, A. K. (1976). Explicit equations for pipe‑flow problems. *J. Hydraulics Div. ASCE*, 102(5), 657‑664.
