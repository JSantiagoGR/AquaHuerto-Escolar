# Cálculos hidráulicos — Riego v3 (corregido): cruz + 3 laterales de manguera × 3 aspersores = 9

EPANET en **LPS**, documentación en SI. Modelo: `riego_huerto_v3_final.inp` = **ESCENARIO GEOMÉTRICO A (DISEÑO PRINCIPAL / DESEADO): subida VERTICAL**.
Lo genera `generar_modelo.py` a partir del bloque `CONFIG`, que incluye la tabla `CONFIG["medidas"]`. Las tablas numéricas completas se regeneran en `calculos_resultados.md`.

> **Estado:**
> - Caudales, velocidades y pérdidas están determinados para la geometría ESTIMADA.
> - **Las presiones son preliminares y dependen de la curva PROVISIONAL de la bomba.**
> - **La longitud de Tuboplus es ESTIMADA** hasta medir en sitio.
> - **La uniformidad de riego no está validada.**

---

## 1. Datos y clasificación

| Dato | Valor usado | Clase |
|---|---|---|
| Tuboplus 20 mm C16, código 200224 | DE 20.0, e 2.80, **DI 14.40 mm**, ε 0.007 mm | OFICIAL |
| K Tuboplus: codo 90° / codo 45° / conector / tee (8) / tee (5) | 2.00 / 0.60 / 0.40 / 2.20 / 1.80 | OFICIAL (Tabla 10) |
| Cruz Tuboplus 200082 | toma 11 mm; **K no publicado** → recto 1.80, lateral 2.20 (proxies de tee) | OFICIAL (dimensiones) / PROVISIONAL (K) |
| Bomba GOOD PUMPS 12 V, 6 A, 72 W; 6 L/min máx. anunciado; 0.9 MPa = 130 psi (corte del presostato) | curva Q‑H **no publicada** | PROVISIONAL |
| Puertos de bomba | ~3/8" macho con punta para manguera de ~10 mm (OD medido 16‑17 mm) | HIPÓTESIS FUERTE; **NPT/BSP SIN CONFIRMAR** |
| YF‑S201 | DI 11 mm, 1–30 L/min, F = 7.5·Q | DOC. TÉCNICA |
| Tinaco | agua +1.19, salida +0.265 | MEDIDO aprox. / PROVISIONAL |
| Línea principal / pie de la bajada | z 0.08 m (`M0`) | ESTIMADO |
| Cruz y laterales | z = 0.12 + 0.40 + 1.00 = **1.52 m** (`M6` + `M7`) | ESTIMADO (dato del equipo) |
| Manguera negra | **DI 12 mm** (sensibilidad 10/12/14 mm) | **ESTIMADO VISUAL — NO MEDIDO** |
| Aspersores | Q máx ≈ 70 L/h (verbal); marca, modelo y curva P‑Q desconocidos | PROVISIONAL |

---

## 2. Caudales (impuestos por escenario) y conversiones

**No se conoce qué apertura física corresponde a cada caudal; no se supone relación lineal entre apertura y caudal.** Cada escenario impone el caudal; no representa una apertura.

| q por aspersor (L/h) | Q total (L/h) | Q total (L/min) | Q total (L/s) | Q por lateral (L/s) | YF‑S201 (Hz) |
|---|---|---|---|---|---|
| 20 | 180 | 3.00 | 0.0500 | 0.01667 | 22.5 |
| 25 | 225 | 3.75 | 0.0625 | 0.02083 | 28.1 |
| **30 (nominal PROVISIONAL)** | 270 | **4.50** | **0.0750** | **0.02500** | 33.8 |
| 35 | 315 | 5.25 | 0.0875 | 0.02917 | 39.4 |
| 40 | 360 | 6.00 | 0.1000 | 0.03333 | 45.0 |
| 70 (máx.) | 630 | 10.50 | 0.1750 | 0.05833 | 78.8 |

---

## 3. Ejemplo de cálculo — línea principal N‑D (L = 2.777 m estimada, D = 14.4 mm, Q = 0.075 L/s)

- A = π·0.0144²/4 = **1.6286×10⁻⁴ m²**; V = 7.5×10⁻⁵ / 1.6286×10⁻⁴ = **0.461 m/s**
- Re = 998.2 × 0.4605 × 0.0144 / 1.002×10⁻³ = **6606 → turbulento bajo**; ε/D = 4.86×10⁻⁴; Colebrook: **f = 0.0352**
- V²/2g = 0.01081 m → hf (D‑W) = f·(L/D)·V²/2g = 0.0352 × 192.8 × 0.01081 = **0.0733 m**; hm (conector 0.40 + codo 90° 2.00) = 2.40 × 0.01081 = **0.0259 m**; H‑W (C 150) ≈ 20 % menor en fricción.

Regímenes: Tuboplus principal turbulento bajo; salidas de la cruz y primer tramo de manguera en transición; manguera entre aspersores laminar (f = 64/Re); puertos de bomba de 7 mm turbulentos (V ≈ 1.95 m/s). **Darcy‑Weisbach es la referencia física principal.** Concordancia con EPANET: < 2 % en tramos laminares/turbulentos y < 5 mm absolutos en transición.

---

## 4. Resultados — escenario A, nominal provisional 30 L/h

**PRESIÓN PRELIMINAR DEPENDIENTE DE CURVA PROVISIONAL DE BOMBA** (no es la presión real definitiva).

| Punto | z (m) | Presión (m) |
|---|---|---|
| Succión bomba | 0.08 | 0.88 (positiva) |
| Descarga bomba | 0.08 | 23.86 |
| Base de la subida vertical | 0.08 | 23.36 |
| Cruz | 1.52 | 21.86 |
| **9 aspersores A11…A33** | 1.52 | **21.816 – 21.821 m (≈ 2.14 bar), PRELIMINAR** |

- Q total 0.0750 L/s = 4.50 L/min; 0.0250 L/s por lateral; 30 L/h por aspersor (impuesto).
- Bomba: 22.98 m a 0.075 L/s con la curva provisional, frente a un corte de 0.9 MPa (≈ 91.9 m). Margen del 25 % respecto a 6 L/min.
- Velocidades: principal **0.461 m/s**; manguera ≤ 0.22 m/s.
- **Pérdidas (red): distribuida 0.292 m; menores 0.814 m.** Ruta crítica tinaco → A13: 0.218 + 0.619 m.

### Uniformidad hidráulica de presión (relación Pmin/Pmax) = **0.9998**

Este valor **solo** indica que las presiones calculadas en los 9 aspersores son casi iguales (≈ 5 mm de diferencia). **No es uniformidad de riego.** Presiones similares **no garantizan** una distribución uniforme del agua, porque aún no se conocen:
- el patrón de mojado;
- el radio real;
- la presión mínima requerida por el aspersor;
- la relación apertura‑caudal (y cada aspersor puede quedar con una apertura distinta);
- el efecto de tener los aspersores **1 m por encima del cajón** (viento, deriva, ángulo de caída).

**La uniformidad de riego real queda PENDIENTE DE VALIDACIÓN EXPERIMENTAL**, por ejemplo con recipientes en una malla sobre el cajón.

---

## 5. Escenarios (todos con presión preliminar)

| q (L/h) | Q (L/min) | P aspersores (m) | H bomba (m) | Margen vs 6 L/min | EPANET | Viabilidad hidráulica |
|---|---|---|---|---|---|---|
| 20 | 3.00 | 45.3 | 46.0 | 50 % | OK | Sí |
| 25 | 3.75 | 33.6 | 34.5 | 38 % | OK | Sí |
| **30** | **4.50** | **21.8** | **23.0** | **25 %** | OK | **Sí (nominal provisional)** |
| 35 | 5.25 | 10.0 | 11.5 | 13 % | OK | Sí, margen bajo |
| 40 | 6.00 | −1.8 | 0.0 | 0 % | WARNING: Negative pressures | **No** |
| 70 | 10.50 | — | — | < 0 | WARNING: Negative pressures | **No** |

Sensibilidad a 30 L/h:
- **Curva de bomba:** ×0.25 → 4.6 m; ×0.5 → 10.3 m; ×0.75 → 16.1 m. Es la variable dominante.
- **Manguera DI 10/12/14 mm:** 21.80 / 21.82 / 21.82 m.
- **K de accesorios:** K ×2 → 20.75 m; K ×0.5 → 22.08 m.
- **Tinaco casi vacío:** 20.93 m.
- **Geometrías A2, B y B2:** 21.8–21.9 m; la geometría casi no cambia la hidráulica.

---

## 6. Bomba

- **0.9 MPa = 130 psi = presión de corte del presostato** (Q ≈ 0). **No** es la presión de operación a 6 L/min; 6 L/min es el caudal anunciado a descarga libre.
- **Curva Q‑H PROVISIONAL** (lineal entre esos dos extremos), con sensibilidad ×0.25…×0.75.
- **Ciclado:** en régimen permanente a 4.5 L/min la bomba trabaja lejos del corte. El riesgo aparece cuando el caudal tiende a cero: aspersores casi cerrados u obstruidos, o la electroválvula cerrándose con la bomba encendida. Hay que **probarlo físicamente**.
- **Conexión:** hipótesis fuerte de puertos de ~3/8" compatibles con manguera de ~10 mm. **El tipo de rosca (NPT o BSP) está PENDIENTE de confirmar**; no se compra el adaptador hasta verificarlo con galga. Opciones: (a) roscada 3/8" ↔ 1/2" con tuerca unión mixta Tuboplus; (b) manguera corta de 10 mm DI con espiga 10 mm × rosca 1/2" (nunca la manguera negra).

---

## 7. Tuboplus nuevo — ESTIMACIÓN paramétrica (no es una medida cerrada)

El límite de **4.00 m** es un **límite de compra**. La longitud real depende de mediciones que aún no se hacen. La tabla `tabla_cortes_tuboplus.csv` separa tramos medidos y estimados, la longitud ocupada por componentes (que no es Tuboplus), la longitud neta de Tuboplus, el total y el margen. Se recalcula sola al cambiar `CONFIG["medidas"]`.

| Escenario | Rol | Tuboplus nuevo ESTIMADO | Margen | Cumple (estimado) |
|---|---|---|---|---|
| **A — subida VERTICAL, codos 90°, cruz arriba, brazos Tuboplus (5 codos 90°)** | **DISEÑO PRINCIPAL / DESEADO** | **5.148 m** | −1.148 m | No (estimado) |
| A2 — vertical, desvío exterior con manguera | variante | 4.534 m | −0.534 m | No (estimado) |
| B — subida a 45° (2 codos 45°) + brazos Tuboplus | **ALTERNATIVA DE CONTINGENCIA** | 4.332 m | −0.332 m | No (estimado) |
| B2 — 45° + desvío con manguera | contingencia extrema | 3.718 m | +0.282 m | Sí (estimado) |

Desglose de A (estimado):
- A, bajada → bomba: 0.074 m
- B y C, niples: 0.060 + 0.060 m
- D, línea principal: 2.744 m
- E, subida vertical: 1.416 m
- H, tramo a la cruz: 0.060 m
- I, brazos: 0.614 m
- N, niples a conectores: 0.120 m

**Condición automática:** manteniendo las demás medidas, A cumple si **M1 + M5 ≤ 1.662 m**; el valor estimado actual es 2.810 m. Es decir, A solo cabe si la distancia horizontal real de Tuboplus entre la bajada y la subida es unos 1.15 m menor que la estimada, o si cambian otras medidas (altura de la cruz, distancia superior, separación de las líneas).

**Hoy no se puede confirmar si el diseño principal cabe en 4.00 m.** La estimación indica que no cabría, pero se apoya en distancias no medidas (M1, M5, M6, M7, M8, M11). La subida a 45° (B) **no** se adopta todavía: solo se usará si las mediciones confirman que A excede el límite. Incluso B necesita combinarse con el desvío por manguera (B2) para caber con las estimaciones actuales.

---

## 8. Mediciones físicas necesarias (`mediciones_fisicas.csv`, `CONFIG["medidas"]`)

1. **M1** — distancia horizontal del final de la bajada existente a la zona de la bomba.
2. **M2** — longitud ocupada por bomba + adaptadores + uniones.
3. **M3** — longitud ocupada por YF‑S201 + adaptadores.
4. **M4** — longitud ocupada por electroválvula + adaptadores (y **M4b**, niples entre conjuntos).
5. **M5** — distancia horizontal de ese conjunto al inicio de la subida.
6. **M6** — altura del piso a la parte superior del cajón.
7. **M7** — altura adicional hasta la cruz.
8. **M8** — distancia horizontal superior hasta la cruz.
9. **M9 / M9b** — diámetro interior y exterior de la manguera negra.
10. **M10** — diámetro, paso y tipo de rosca de la bomba.
11. **M11 / M11b** — posición exacta de las 3 líneas y de los aspersores sobre el cajón.
12. **M12** — longitud real de cada línea de manguera (estimada hoy en 0.905 m cada una).
13. **M0** — altura real de la línea principal / pie de la bajada.

Al medir: cambiar `valor` y poner `estado: "MEDIDO"` en `CONFIG["medidas"]`, ejecutar `generar_modelo.py` y `validar_modelo.py`.

---

## 9. Fórmulas

Q = V·A; A = πD²/4; Re = ρVD/μ; D‑W hf = f(L/D)V²/2g (laminar f = 64/Re; Colebrook en turbulento); H‑W hf = 10.67·L·Q^1.852/(C^1.852·D^4.87); hm = ΣK·V²/2g; Kv → K: Δp[bar] = (Q[m³/h]/Kv)², K = 2g·Δh/V²; H = P/(ρg); corte de Tuboplus = distancia − tomas de conexiones + inserciones.
