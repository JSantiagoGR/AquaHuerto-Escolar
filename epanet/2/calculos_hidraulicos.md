# Cálculos hidráulicos — Riego v2 (1 cajón, 2 laterales, 4 microaspersores)

Unidades SI. EPANET en **LPS**. Modelo: `riego_huerto_v2_final.inp`. Todo es regenerable con `generar_modelo.py`.
Clasificación de datos: **OFICIAL · MEDIDO · CALCULADO · ESTIMADO · PROVISIONAL · PENDIENTE** (ver `ASSUMPTIONS_AND_PENDING.md`).

> **Estado:** caudales, velocidades y pérdidas quedan bien determinados. Las **presiones finales son PROVISIONALES** porque dependen de la curva Q‑H de la bomba (no certificada) y del tinaco original (que se va a cambiar).

---

## 1. Datos de partida

| Dato | Valor | Tipo | Fuente |
|---|---|---|---|
| Tubo Tuboplus 20 mm (1/2") Clase 16, código 200224 | DE 20.0 mm, e = 2.80 mm, **DI = 14.40 mm**, A = 1.63 cm² | OFICIAL | Manual Técnico Tuboplus 2017 (catálogo, p. 102‑103); SDR 7.4 (p. 24‑25) |
| Rugosidad Tuboplus | ε = 0.007 mm | OFICIAL | Manual Tuboplus, Tabla 11 |
| Coeficientes K de conexiones | codo 90° 2.00; tee normal (8, entra por derivación) 2.20; tee rosca central 0.80; conector 0.40; reducción 0.55/0.85 | OFICIAL | Manual Tuboplus, Tabla 10 (p. 71) |
| Microaspersor (PROVISIONAL) Hunter Solo‑Drip SD‑B | Tabla de desempeño (**solo hasta 2.0 bar**): 1.0 bar 0–40 L/h Ø0–0.5 m · **1.5 bar 0–50 L/h Ø0–0.6 m** · 2.0 bar 0–60 L/h Ø0–0.8 m. **Rango general de funcionamiento 0.5–2.5 bar** (sin datos de caudal/radio publicados entre 2.0 y 2.5 bar). Espiga 6 mm; filtración mínima 100 mesh / 150 µm | OFICIAL | Hunter, ficha métrica Micro Sprays y tabla de desempeño |
| YF‑S201 | DI 11 mm, 1–30 L/min, F = 7.5·Q, 450 pulsos/L, ≤1.75 MPa (prueba) / 2.0 MPa | DOC. TÉCNICA (distribuidor) | Handsontec; ficha técnica de distribuidor |
| Bomba GOOD PUMPS 12 V, 6 A, 72 W, “largest flow 6 L/min”, “pressure setting 0.9 MPa” | curva Q‑H **no publicada** | PROVISIONAL | placa (fotografía) + anuncios comerciales |
| Tinaco original | banqueta +0.07, base +0.12, fondo +0.19, agua máx. **+1.19**, salida **+0.265** | MEDIDO aprox. / PROVISIONAL | equipo |
| Bomba | z = +0.08 m | MEDIDO aprox. | equipo |
| Cajón | 1.0 × 1.0 m, base 0.12, alto 0.40 → nivel de riego **+0.52** | MEDIDO aprox. | equipo |
| Agua 20 °C | ρ = 998.2 kg/m³, μ = 1.002×10⁻³ Pa·s, g = 9.81 m/s² | ESTIMADO (propiedades asumidas) | — |

**Verificación del desnivel:** Δz = 1.19 − 0.52 = **0.67 m** ✔ (agua del tinaco lleno sobre el nivel de riego).
Elevaciones del modelo: eje del lateral +0.53 (0.52 + radio exterior 0.01, CALCULADO), boquilla SD‑B +0.56 (ESTIMADO, ~3 cm de tee + adaptador + cuerpo).

---

## 2. Caudal de diseño y conversiones

Hunter confirma **50 L/h a 1.5 bar** (máximo ajuste) → escenario de diseño:

- Q emisor = 50 L/h ÷ 3600 s/h = **0.0138889 L/s** = 0.8333 L/min
- Q lateral = 2 × 50 = **100 L/h** = 0.0277778 L/s = 1.6667 L/min
- Q total = 4 × 50 = **200 L/h** ÷ 60 = **3.3333 L/min** ÷ 60 = **0.0555556 L/s** ✔ (= 5.5556×10⁻⁵ m³/s)
- 1.5 bar = 1.5×10⁵ Pa ÷ (998.2 × 9.81) = **15.318 m** de columna de agua.
- YF‑S201 a 3.333 L/min: F = 7.5 × 3.333 = **25.0 Hz** → dentro del rango 1–30 L/min ✔ (en operación con la curva provisional: 4.40 L/min → 33.0 Hz ✔).

---

## 3. Emisores (EMITTERS de EPANET): Q = C·Pⁿ

Hunter da tres puntos de **máximo ajuste**: (10.21 m; 40 L/h), (15.32 m; 50 L/h), (20.42 m; 60 L/h). Hunter **no publica el exponente n**.

- Exponentes entre puntos: ln(50/40)/ln(1.5) = 0.550; ln(60/50)/ln(4/3) = 0.634; ln(60/40)/ln(2) = 0.585.
- Regresión log‑log de los 3 puntos: **n = 0.5827 (CALCULADO a partir de datos OFICIALES)**.
- C anclado exactamente al punto de diseño: C = 0.0138889 / 15.318^0.5827 = **2.8318×10⁻³ (L/s)/mⁿ**. Verificación: a 10.21 m da 39.5 L/h (tabla 40) y a 20.42 m da 59.1 L/h (tabla 60) ✔.
- Escenario alterno **n = 0.5 (SUPUESTO de orificio, no especificado por Hunter)**: C = 0.0138889/15.318^0.5 = 3.5487×10⁻³.

Limitación: el SD‑B es ajustable (≈20 clics); C corresponde al **máximo ajuste**. Si se cierra la tapa, C baja (y el radio también).

**Validez del ajuste:** Q = C·Pⁿ solo está respaldado por datos oficiales entre **1.0 y 2.0 bar** (10.2–20.4 m). Todo caudal calculado por encima de 2.0 bar (o por debajo de 1.0 bar) es una **EXTRAPOLACIÓN DEL MODELO**, no un dato de Hunter. Los CSV lo marcan en la columna `nota` / `nota_caudal_aspersor`.

---

## 4. Área, velocidad, Reynolds, fricción (ejemplo con la línea principal T‑F, L = 2.796 m)

**Área:** A = π·D²/4 = π·(0.0144 m)²/4 = **1.6286×10⁻⁴ m²** (oficial: 1.63 cm² ✔).

**Punto de diseño (Q = 5.5556×10⁻⁵ m³/s):**
- V = Q/A = 5.5556×10⁻⁵ / 1.6286×10⁻⁴ = **0.341 m/s**
- Re = ρVD/μ = 998.2 × 0.3412 × 0.0144 / 1.002×10⁻³ = **4894 → turbulento (bajo)**
- ε/D = 0.007×10⁻³ / 0.0144 = **4.86×10⁻⁴**
- Swamee‑Jain: f = 0.25/[log₁₀(ε/3.7D + 5.74/Re^0.9)]² = 0.25/[log₁₀(1.314×10⁻⁴ + 2.743×10⁻³)]² = 0.25/(−2.5415)² = **0.0387**; Colebrook iterado: **0.0382**
- V²/2g = 0.3412²/19.62 = 5.932×10⁻³ m; L/D = 194.17
- **hf (D‑W) = 0.0382 × 194.17 × 5.932×10⁻³ = 0.0440 m**
- H‑W (C = 150): hf = 10.67·L·Q^1.852/(C^1.852·D^4.87) = 10.67 × 2.796 × 1.3161×10⁻⁸ / (10718.2 × 1.0745×10⁻⁹) = **0.0341 m** (−22 % vs D‑W)
- Pérdida menor (conector 0.40 + codo 2.00): hm = 2.40 × 5.932×10⁻³ = **0.0142 m**

**Contraste con la Tabla 11 oficial de Tuboplus** (Q = 0.05 L/s, DN20): oficial j = 0.013 m/m, v = 0.31 m/s; calculado j = 0.0132 m/m, v = 0.307 m/s ✔ (confirma DI = 14.4 mm y ε = 0.007 mm).

**Moody (verificación cualitativa):** Re ≈ 4900–6500 con ε/D ≈ 5×10⁻⁴ cae justo después de la zona crítica, cerca de la curva de tubo liso, f ≈ 0.035–0.039 ✔. Los brazos y el primer tramo de lateral (Re ≈ 3200) están en **transición**: no hay f único; se usa Colebrook como cota y EPANET interpola. El tramo entre aspersores (Re ≈ 1600) es **laminar**: f = 64/Re.

---

## 5. Tabla por tramo — escenario BASE (emisores, curva PROVISIONAL, tinaco lleno)

K referidos a la velocidad del propio enlace. “EPANET” = pérdida total reportada por EPANET (fricción + menor). La última columna usa H‑W C = 150 para la fricción + la misma pérdida menor.

| Tramo | Material | L (m) | D int (mm) | A (m²) | Q (L/s) | V (m/s) | Re | Régimen | f | K | hf D-W (m) | hm (m) | h total (m) | EPANET (m) | H-W C=150 + hm (m) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P-TK | niple | 0.040 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 0.50 | 0.00101 | 0.00516 | 0.00617 | 0.00618 | 0.00597 |
| CHK | check | 0.055 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 2.70 | 0.00139 | 0.02784 | 0.02924 | 0.02924 | 0.02896 |
| T-A | tuboplus | 0.139 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 2.40 | 0.00352 | 0.02475 | 0.02827 | 0.02831 | 0.02758 |
| T-B | tuboplus | 0.185 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 2.00 | 0.00469 | 0.02062 | 0.02531 | 0.02537 | 0.02439 |
| T-C | tuboplus | 0.317 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 0.95 | 0.00803 | 0.00980 | 0.01783 | 0.01795 | 0.01625 |
| T-D | tuboplus | 0.162 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 1.65 | 0.00411 | 0.01702 | 0.02112 | 0.02117 | 0.02031 |
| YF | yfs201 | 0.062 | 11.0 | 9.503e-05 | 0.07326 | 0.771 | 8447 | turbulento (Colebrook) | 0.0332 | 2.00 | 0.00567 | 0.06057 | 0.06624 | 0.06627 | 0.06526 |
| T-E | tuboplus | 0.134 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 0.80 | 0.00340 | 0.00825 | 0.01165 | 0.01169 | 0.01098 |
| EV | electrovalvula | 0.085 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 7.65 | 0.00215 | 0.07892 | 0.08107 | 0.08106 | 0.08065 |
| T-F | tuboplus | 2.796 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 2.40 | 0.07087 | 0.02475 | 0.09562 | 0.09667 | 0.08164 |
| T-G | tuboplus | 0.450 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 2.00 | 0.01141 | 0.02062 | 0.03203 | 0.03219 | 0.02978 |
| T-H | tuboplus | 0.083 | 14.4 | 1.629e-04 | 0.07326 | 0.450 | 6453 | turbulento (Colebrook) | 0.0354 | 2.20 | 0.00210 | 0.02269 | 0.02479 | 0.02481 | 0.02438 |
| BR-L | tuboplus | 0.250 | 14.4 | 1.629e-04 | 0.03663 | 0.225 | 3226 | transición (Colebrook, cota) | 0.0430 | 2.00 | 0.00193 | 0.00516 | 0.00708 | 0.00674 | 0.00657 |
| BR-R | tuboplus | 0.250 | 14.4 | 1.629e-04 | 0.03663 | 0.225 | 3226 | transición (Colebrook, cota) | 0.0430 | 2.00 | 0.00193 | 0.00516 | 0.00708 | 0.00674 | 0.00657 |
| L1-A | tuboplus | 0.217 | 14.4 | 1.629e-04 | 0.03663 | 0.225 | 3226 | transición (Colebrook, cota) | 0.0430 | 0.80 | 0.00167 | 0.00206 | 0.00373 | 0.00343 | 0.00329 |
| L1-B | tuboplus | 0.500 | 14.4 | 1.629e-04 | 0.01831 | 0.112 | 1613 | laminar (64/Re) | 0.0397 | 0.80 | 0.00089 | 0.00052 | 0.00140 | 0.00142 | 0.00130 |
| L1-T | tuboplus | 0.023 | 14.4 | 1.629e-04 | 0 | 0 | — | sin flujo (tapón) | — | — | 0 | 0 | 0 | 0 | 0 |
| L2-A | tuboplus | 0.217 | 14.4 | 1.629e-04 | 0.03663 | 0.225 | 3226 | transición (Colebrook, cota) | 0.0430 | 0.80 | 0.00167 | 0.00206 | 0.00373 | 0.00343 | 0.00329 |
| L2-B | tuboplus | 0.500 | 14.4 | 1.629e-04 | 0.01831 | 0.112 | 1613 | laminar (64/Re) | 0.0397 | 0.80 | 0.00089 | 0.00052 | 0.00140 | 0.00142 | 0.00130 |
| L2-T | tuboplus | 0.023 | 14.4 | 1.629e-04 | 0 | 0 | — | sin flujo (tapón) | — | — | 0 | 0 | 0 | 0 | 0 |
| RE1 | adaptador | 0.030 | 4.0 | 1.257e-05 | 0.01831 | 1.457 | 5808 | turbulento (Colebrook) | 0.0379 | 1.00 | 0.03074 | 0.10826 | 0.13900 | 0.13956 | 0.13224 |
| RE2 | adaptador | 0.030 | 4.0 | 1.257e-05 | 0.01831 | 1.457 | 5807 | turbulento (Colebrook) | 0.0379 | 1.00 | 0.03074 | 0.10825 | 0.13899 | 0.13955 | 0.13223 |
| RE3 | adaptador | 0.030 | 4.0 | 1.257e-05 | 0.01831 | 1.457 | 5808 | turbulento (Colebrook) | 0.0379 | 1.00 | 0.03074 | 0.10826 | 0.13900 | 0.13956 | 0.13224 |
| RE4 | adaptador | 0.030 | 4.0 | 1.257e-05 | 0.01831 | 1.457 | 5807 | turbulento (Colebrook) | 0.0379 | 1.00 | 0.03074 | 0.10825 | 0.13899 | 0.13955 | 0.13223 |

**Totales (escenario base):**
- Toda la red: pérdida distribuida **0.250 m**, pérdidas menores **0.770 m** (incluye las 4 ramas de aspersor).
- Ruta crítica tinaco → E2: distribuida **0.153 m**, menores **0.437 m**, total **0.591 m**.
- Solo Tuboplus: distribuida 0.117 m, menores 0.164 m.
- Mayores contribuciones: rama de aspersor (espiga de 6 mm, 0.139 m c/u), electroválvula (0.081 m), línea principal (0.097 m), YF‑S201 (0.066 m), check (0.029 m).
- Concordancia manual vs EPANET: < 1.1 % en tramos turbulentos/laminares; < 9 % en transición (EPANET interpola Moody).

**Darcy‑Weisbach vs Hazen‑Williams:** H‑W subestima la fricción en la línea principal ≈ 20 % porque es empírica para flujo turbulento pleno en diámetros mayores, no depende de Re y no aplica a régimen laminar/transición. **Se usa Darcy‑Weisbach como referencia principal** (`Headloss D‑W` en EPANET). En presión final la diferencia es mínima (24.623 vs 24.635 m) porque la fricción es pequeña frente a la altura de la bomba.

---

## 6. Resultados EPANET — escenario BASE (`riego_huerto_v2_final.inp`)

**Resultado preliminar dependiente de la curva PROVISIONAL de la bomba y del tinaco original.**

| Nodo | z (m) | Head (m) | Presión (m) |
|---|---|---|---|
| R1 tinaco (nivel) | 1.190 | 1.190 | — |
| J‑TK salida tinaco | 0.265 | 1.184 | 0.919 |
| J‑PIN succión bomba | 0.080 | 1.083 | **1.003** (positiva ✔) |
| J‑POUT descarga bomba | 0.080 | 25.666 | 25.586 |
| J‑FLOW entrada YF‑S201 | 0.080 | 25.645 | 25.565 |
| J‑EV2 salida electroválvula | 0.080 | 25.486 | 25.406 |
| J‑T (T del cajón) | 0.530 | 25.333 | 24.803 |
| **E1 / E2 / E3 / E4** | 0.560 | 25.183 / 25.181 / 25.183 / 25.181 | **24.62 / 24.62 / 24.62 / 24.62 (2.41 bar, preliminar; fuera de la tabla Hunter)** |

- Caudal total **0.07326 L/s = 4.40 L/min = 263.7 L/h**; cada lateral **0.03663 L/s**; cada aspersor **65.9 L/h (EXTRAPOLACIÓN DEL MODELO, no dato Hunter)**.

> ⚠ **Los 65.9 L/h a 2.41 bar NO son un dato oficial de Hunter.** La tabla oficial del Solo‑Drip termina en 2.0 bar (40 L/h a 1.0 bar, 50 L/h a 1.5 bar, 60 L/h a 2.0 bar). El valor de 65.9 L/h sale de extrapolar el ajuste Q = C·Pⁿ fuera de esa tabla. Hunter solo indica que el rango general de funcionamiento llega a 2.5 bar; no publica caudal ni radio entre 2.0 y 2.5 bar.
- Bomba: Q = 0.07326 L/s, altura **24.58 m**. Velocidad en la línea principal **0.450 m/s**.
- Conservación de masa: salida del tinaco = Σ4 emisores (0.073256 L/s) ✔.

**Interpretación:** con la curva provisional la bomba entrega **más presión que la de diseño**; los SD‑B quedan a 2.41 bar, dentro del rango general de funcionamiento (0.5–2.5 bar) pero **fuera de la tabla de desempeño (≤ 2.0 bar)**. Por eso el caudal de 65.9 L/h es una **extrapolación del modelo**, y el radio a 2.41 bar es **desconocido** (la tabla solo dice Ø0–0.8 m a 2.0 bar). Ambos son resultados preliminares que dependen de la curva provisional de la bomba.

---

## 7. Punto de diseño y altura requerida de la bomba

Con demanda fija de 50 L/h por aspersor (escenario S2) se obtienen las pérdidas en el caudal de diseño 0.05556 L/s:

H_req = (z_boquilla + P_diseño) − z_agua + pérdidas_succión + pérdidas_descarga
= (0.56 + 15.318) − 1.19 + 0.062 + 0.285 = **15.04 m a 0.0556 L/s (3.33 L/min)**.

→ **Requisito para la bomba real: ≈ 15 m (≈1.5 bar) a 3.33 L/min**, con el tinaco lleno. La curva provisional da 40.9 m a ese caudal (sobra presión); en la sensibilidad, la curva escalada ×0.40 produce 1.57 bar y 51.4 L/h por aspersor.

---

## 8. Sensibilidad (EPANET, `escenarios_sensibilidad.csv`)

| Escenario | Descripción | Q total (L/s) | Q total (L/min) | Q por aspersor (L/h) | P aspersores (m) | P aspersores (bar) | H bomba (m) | Clase del caudal por aspersor |
|---|---|---|---|---|---|---|---|---|
| S0_base | BASE: emisores n ajustado, D-W, tinaco lleno, curva provisional | 0.0733 | 4.39 | 65.93 | 24.623 | 2.411 | 24.583 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S1_n05 | Emisores con n=0.5 (SUPUESTO orificio) | 0.0720 | 4.32 | 64.84 | 25.759 | 2.522 | 25.700 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S2_demanda_fija | Demanda FIJA 50 L/h por aspersor (diseno), sin emisores | 0.0556 | 3.33 | 50.00 | 41.137 | 4.028 | 40.854 | DEMANDA FIJA (impuesta; la presión resultante no es operable con SD‑B si > 2.5 bar) |
| S3_HW150 | Hazen-Williams C=150 (comparacion) | 0.0733 | 4.40 | 65.95 | 24.635 | 2.412 | 24.564 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S4_tinaco_min | Tinaco casi vacio (agua en +0.30 m) | 0.0727 | 4.36 | 65.40 | 24.284 | 2.378 | 25.125 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S5_curva_x0.25 | Curva provisional con alturas x0.25 | 0.0486 | 2.92 | 43.74 | 12.175 | 1.192 | 11.812 | dentro de la tabla Hunter (interpolado) |
| S5_curva_x0.40 | Curva provisional con alturas x0.40 | 0.0571 | 3.42 | 51.37 | 16.046 | 1.571 | 15.781 | dentro de la tabla Hunter (interpolado) |
| S5_curva_x0.50 | Curva provisional con alturas x0.50 | 0.0612 | 3.67 | 55.04 | 18.064 | 1.769 | 17.851 | dentro de la tabla Hunter (interpolado) |
| S5_curva_x0.75 | Curva provisional con alturas x0.75 | 0.0684 | 4.10 | 61.57 | 21.893 | 2.144 | 21.780 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S6_check_K1.5 | Check K=1.5 | 0.0733 | 4.40 | 65.94 | 24.627 | 2.412 | 24.576 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S6_check_K8.0 | Check K=8.0 | 0.0732 | 4.39 | 65.90 | 24.602 | 2.409 | 24.617 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S6_check_K16.2 | Check K=16.2 | 0.0732 | 4.39 | 65.85 | 24.570 | 2.406 | 24.668 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S7_yfs201_K0.0 | YF-S201 K=0.0 | 0.0733 | 4.40 | 65.97 | 24.646 | 2.413 | 24.547 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S7_yfs201_K5.0 | YF-S201 K=5.0 | 0.0732 | 4.39 | 65.88 | 24.588 | 2.408 | 24.639 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S7_yfs201_K10.0 | YF-S201 K=10.0 | 0.0731 | 4.39 | 65.79 | 24.531 | 2.402 | 24.730 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S7_yfs201_K20.0 | YF-S201 K=20.0 | 0.0729 | 4.37 | 65.61 | 24.417 | 2.391 | 24.912 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S8_EV_Kv1.0 | Electrovalvula Kv=1.0 m3/h (K=68.9) | 0.0728 | 4.37 | 65.56 | 24.385 | 2.388 | 24.963 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S8_EV_Kv2.0 | Electrovalvula Kv=2.0 m3/h (K=17.2) | 0.0732 | 4.39 | 65.87 | 24.585 | 2.407 | 24.643 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S8_EV_Kv6.0 | Electrovalvula Kv=6.0 m3/h (K=1.9) | 0.0733 | 4.40 | 65.97 | 24.645 | 2.413 | 24.547 | **EXTRAPOLACIÓN del modelo** (> 2.0 bar; no es dato Hunter) |
| S9_cobertura_r036_fija | COBERTURA r=0.36 m: demanda fija 55.6 L/h por aspersor (P interpolada 1.80 bar) | 0.0618 | 3.71 | 55.60 | 35.335 | 3.460 | 35.130 | DEMANDA FIJA (impuesta; la presión resultante no es operable con SD‑B si > 2.5 bar) |
| S10_cobertura_r036_curva | COBERTURA r=0.36 m: curva provisional x0.517 (emisores a ~1.80 bar) | 0.0618 | 3.71 | 55.61 | 18.383 | 1.800 | 18.178 | dentro de la tabla Hunter (interpolado) |

**Conclusión de sensibilidad:** la variable dominante es **la curva de la bomba** (de 1.19 a 2.41 bar según la curva; todo resultado > 2.0 bar es extrapolación del modelo en el caudal del aspersor). K del check, YF‑S201 y electroválvula, n del emisor, H‑W vs D‑W y el nivel del tinaco cambian la presión en los aspersores < 0.25 m. Por eso **medir la curva Q‑H real es la prioridad #1**.

Conversión Kv → K usada: Δp[bar] = (Q[m³/h]/Kv)², h = Δp·10⁵/(ρg), K = 2g·h/V² (independiente de Q). Kv = 3 → K = 7.65 (ESTIMADO).

---

## 9. Geometría y Tuboplus

Ver `tabla_cortes_tuboplus.csv`. Tomas oficiales (centro de la conexión → extremo del tubo insertado): codo 90° 12 mm (L 27 − p 15), tee 11 mm (27 − 16), tee rosca central 11 mm, conector/union mixta 37/30 mm al inicio de la rosca, tapón 4 mm más allá del tubo.

- Recorrido: salida del tinaco X = 0 → check → bajada (0.185 m) → bomba (X 0.55–0.71) → YF‑S201 (0.87–0.94) → electroválvula (1.07–1.15) → línea principal → subida en X = 3.95 (0.45 m) → T en X = 4.03 (3 cm dentro del cajón) → brazos ±0.25 m → laterales en y = 0.25 y 0.75 → aspersores en x = 0.25 y 0.75 del cajón → tapones en X ≈ 4.77 (< 5 m) ✔.
- **Tuboplus cortado = 5.722 m** (tubo 1: 3.844 m; tubo 2: 1.878 m) **≤ 7.50 m ≤ 8.00 m**, margen 2.278 m ✔.
- Los componentes no Tuboplus (check, bomba, YF‑S201, electroválvula, adaptadores) **no** se cuentan como tubo; tienen su propia longitud física ESTIMADA.

---

## 9b. Cobertura geométrica del cajón (1 × 1 m, aspersores en 0.25/0.75 m)

Aspersores en (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75) m. La distancia máxima de cualquier punto del cajón al aspersor más cercano es

d_max = √(0.25² + 0.25²) = **0.3536 m**,

y se alcanza en **9 puntos**: el centro (0.5, 0.5), las **4 esquinas** y también los **4 puntos medios de los bordes** (0.5, 0), (0, 0.5), (1, 0.5), (0.5, 1).

| Radio de mojado | Área del cajón cubierta (malla 1001×1001) | Área con traslape de ≥ 2 aspersores | Presión en máximo ajuste según la tabla Hunter | Caudal por aspersor |
|---|---|---|---|---|
| **0.30 m** (deseado; Ø 0.6 m) | **95.0 %** (sin cubrir: centro, 4 esquinas y 4 puntos medios de borde) | 9.0 % | 1.5 bar (punto de la tabla oficial) | 50 L/h (oficial) |
| 0.3536 m (mínimo geométrico) | 100 % (justo, sin margen) | 28.5 % | ≈ 1.77 bar (interpolado) | — |
| **0.36 m** (escenario de cobertura; Ø 0.72 m) | **100 %** | 31.1 % | **≈ 1.80 bar** (interpolado) | **≈ 56 L/h** (interpolado de la tabla) / 55.6 L/h (ajuste Q = C·Pⁿ) |

**Cómo se obtuvo la presión para r ≈ 0.36 m (sin inventar datos):** interpolación lineal **dentro** de la tabla oficial de diámetro de mojado en máximo ajuste: Ø 0.6 m @ 1.5 bar y Ø 0.8 m @ 2.0 bar → Ø 0.72 m ⇒ P = 1.5 + (0.72 − 0.6)/(0.8 − 0.6) × 0.5 = **1.80 bar** (18.38 m); Q = 50 + (1.80 − 1.5)/0.5 × 10 = **56 L/h**. Es un valor **CALCULADO** (interpolado), no publicado por Hunter: la relación radio‑presión entre los puntos de la tabla no se conoce, y con la tapa parcialmente cerrada el radio sería menor.

**Escenarios EPANET de cobertura (no cambian la red ni la distribución):**
- **S9** (demanda fija 55.6 L/h por aspersor, 0.0618 L/s = 3.71 L/min = 222 L/h): la bomba debería entregar **≈ 18.2 m a 0.0618 L/s** con el tinaco lleno (frente a 15.0 m a 0.0556 L/s del diseño de 1.5 bar).
- **S10** (emisores con la curva provisional escalada ×0.517): los aspersores quedan en 1.80 bar y 55.6 L/h. Indica la forma de curva que daría ese punto, **no** es la curva real.

**Limitaciones:** la cobertura geométrica (todo punto dentro de algún radio) **no** equivale a una lámina uniforme; en el borde de alcance cae poca agua. Un criterio habitual de uniformidad (alcance ≈ separación, aquí 0.5 m) pediría Ø ≈ 1.0 m, fuera de la tabla del SD‑B (máx. Ø 0.8 m a 2.0 bar). **No se cambió la distribución**; queda como decisión de campo (aforo con recipientes) o como criterio para elegir el aspersor definitivo. Figura: `capturas_epanet/04_Cobertura_PYTHON.png`.

## 9c. Esquema físico de montaje (incluye filtro)

```
TINACO (salida 1/2", z +0.265)
  → niple/adaptador → VÁLVULA CHECK 1/2" → conector macho Tuboplus → codo 90° → BAJADA 0.185 m → codo 90°
  → tuerca unión mixta → adaptador → BOMBA 12 V (z +0.08) → adaptador → tuerca unión mixta
  → FILTRO DE MALLA 1/2" ≥ 100 mesh / ≤ 150 µm  (requisito Hunter; PENDIENTE: modelo, K y longitud)
  → YF‑S201 → ELECTROVÁLVULA NC → LÍNEA PRINCIPAL 2.75 m → codo → SUBIDA 0.45 m → codo
  → T centrada → brazo izq./der. 0.25 m → codo → LATERAL → T rosca central + adaptador espiga 6 mm + SD‑B (A)
  → tramo 0.5 m → T rosca central + SD‑B (B) → niple → TAPÓN
```

- **Posición recomendada del filtro:** en la descarga de la bomba, **antes del YF‑S201**: protege el rotor del caudalímetro, la electroválvula y los SD‑B, sin añadir pérdida en la succión de la bomba de diafragma.
- **Estado:** el filtro **no** está en el modelo hidráulico base ni en la tabla de cortes. Al definirlo hay que (1) agregar un enlace con su K (de la ficha; un filtro sucio aumenta la pérdida), (2) alargar el corte D (bomba → YF‑S201) según la longitud del filtro (hay 2.12 m de Tuboplus sobrante en el tubo 2) y (3) volver a ejecutar `generar_modelo.py`. Ver `ASSUMPTIONS_AND_PENDING.md` (montaje).

## 10. Fórmulas usadas

- Continuidad: Q = V·A; A = πD²/4
- Reynolds: Re = ρVD/μ; laminar < 2000 (EPANET) / < 2300 (clase); transición hasta 4000
- Darcy‑Weisbach: hf = f·(L/D)·V²/2g; laminar f = 64/Re; turbulento Colebrook‑White 1/√f = −2 log₁₀(ε/3.7D + 2.51/(Re√f)); Swamee‑Jain como valor inicial
- Hazen‑Williams SI: hf = 10.67·L·Q^1.852/(C^1.852·D^4.87)
- Pérdidas menores: hm = ΣK·V²/2g (Tuboplus: PCC = Σr·V²·γ/2g)
- Emisor: Q = C·Pⁿ
- Presión ↔ altura: H = P/(ρg)
