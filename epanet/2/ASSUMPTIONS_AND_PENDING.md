# Supuestos, clasificación de datos y pendientes

## 1. Clasificación de cada dato del modelo

| Dato | Valor en el modelo | Clase | Dónde se cambia |
|---|---|---|---|
| DI Tuboplus 20 mm C16 | 14.40 mm | **OFICIAL** | `CONFIG["tubo"]` |
| Rugosidad Tuboplus | 0.007 mm | **OFICIAL** | `CONFIG["tubo"]["rug_mm"]` |
| K codo / tee / tee rosca / conector / reducción | 2.00 / 2.20 / 0.80 / 0.40 / 0.55‑0.85 | **OFICIAL** (Tuboplus Tabla 10) | `CONFIG["K"]` |
| Dimensiones de conexiones Tuboplus | L, p del catálogo | **OFICIAL** | `CONFIG["fit"]` |
| Tabla P‑Q‑Ø del Hunter SD‑B | 1.0/1.5/2.0 bar → 40/50/60 L/h, Ø 0.5/0.6/0.8 m (**la tabla termina en 2.0 bar**; rango general de funcionamiento 0.5–2.5 bar) | **OFICIAL** | `CONFIG["aspersor"]` |
| Caudal del SD‑B fuera de 1.0–2.0 bar (p. ej. 65.9 L/h a 2.41 bar) | resultado de Q = C·Pⁿ | **EXTRAPOLACIÓN DEL MODELO** (no es dato Hunter) | — |
| Presión/caudal para radio 0.36 m | ≈ 1.80 bar, ≈ 56 L/h | **CALCULADO** (interpolación lineal de la tabla oficial) | `CONFIG["cobertura"]` |
| Exponente del emisor n | 0.5827 | **CALCULADO** (de datos oficiales) | se recalcula solo |
| Coeficiente del emisor C | 2.8318×10⁻³ (L/s)/mⁿ | **CALCULADO** | se recalcula solo |
| n = 0.5 (escenario S1) | 0.5 | **SUPUESTO** (orificio; Hunter no lo especifica) | `CONFIG["aspersor"]["n_supuesto_orificio"]` |
| DI del YF‑S201 | 11 mm | Doc. técnica de distribuidor | `CONFIG["D_yfs201_mm"]` |
| Nivel de agua del tinaco | +1.19 m | **MEDIDO aprox. / PROVISIONAL** | `CONFIG["tinaco"]["z_agua_max"]` |
| Salida del tinaco | +0.265 m | **MEDIDO aprox. / PROVISIONAL** | `CONFIG["tinaco"]["z_salida"]` |
| Bomba | +0.08 m | **MEDIDO aprox.** | `CONFIG["z_bomba"]` |
| Nivel de riego | +0.52 m | **MEDIDO aprox.** | `CONFIG["z_riego"]` |
| Eje del lateral / boquilla | +0.53 / +0.56 m | **CALCULADO / ESTIMADO** | `CONFIG["z_lateral"]`, `["z_boquilla"]` |
| Curva Q‑H de la bomba | lineal 91.91 m → 0 m (0 → 0.1 L/s) | **PROVISIONAL** | `CONFIG["bomba_curva"]` |
| K de la check | 2.7 | **ESTIMADO** (Crane, columpio) | `CONFIG["K"]["check"]` |
| K del YF‑S201 | 2.0 | **ESTIMADO** | `CONFIG["K"]["yfs201"]` |
| Kv de la electroválvula | 3 m³/h (K = 7.65) | **ESTIMADO** | `CONFIG["Kv_electrovalvula"]` |
| K entrada del tinaco | 0.5 | **ESTIMADO** (literatura) | `CONFIG["K"]["entrada_tinaco"]` |
| Rama del aspersor | D 4 mm, L 30 mm, K 1.0 | **ESTIMADO** | `CONFIG["D_rama_aspersor_mm"]`, `["K"]["rama_aspersor"]` |
| Longitudes de check, bomba, YF, electroválvula, adaptadores | 55 / 160 / 62 / 85 / 35 mm | **ESTIMADO** (YF 62 mm: doc. técnica) | `CONFIG["L_*"]` |
| Distancia tinaco → subida | 3.95 m (cajón en 4.00 m) | **ESTIMADO** a partir de “~4 m” | `CONFIG["X_subida"]` |
| Propiedades del agua | 20 °C | **ESTIMADO** | `CONFIG` |
| Estándar de rosca de la bomba | OD 16‑17 mm | **MEDIDO / PENDIENTE** (no se asume NPT ni BSP) | BOM |

## 2. Pendientes para la validación física (ordenados por impacto)

| # | Pendiente | Por qué importa | Cómo obtenerlo | Dónde se usa |
|---|---|---|---|---|
| P1 | **Prueba física de la bomba de diafragma: curva Q‑H real** | Determina TODA la presión: con la curva provisional los SD‑B quedan a 2.41 bar (caudal extrapolado); con ×0.25 a 1.19 bar | Montar bomba → manómetro (0‑6 bar) → válvula de bola → probeta. A 12 V medidos, cerrar la válvula por pasos (0, 0.5, 1, 1.5, 2, 3, 4 bar hasta el corte del presostato); en cada paso medir volumen en 30 s. H = P/(ρg) + Δz manómetro. ≥ 5 puntos | `CONFIG["bomba_curva"]` → regenerar |
| P1b | **Prueba física de la bomba: posible ciclado del presostato con solo 4 microaspersores** | La bomba (6 L/min máx.) trabajaría con 3.3–4.4 L/min. Si la presión alcanza el ajuste del presostato, la bomba se apaga y enciende (ciclado): presión pulsante, riego irregular, desgaste de bomba y relé y lecturas intermitentes del YF‑S201 (el ESP32 podría interpretarlas como “sin flujo”). El modelo EPANET (régimen permanente) **no** representa el presostato | Con los 4 SD‑B instalados y abiertos, 12 V medidos: registrar 5–10 min manómetro en la T del cajón, corriente de la bomba y pulsos del YF‑S201; contar arranques/paradas por minuto. Repetir con tapas a medio ajuste. Si hay ciclado: regulador de presión / bypass a tinaco / reducir voltaje (PWM) según el resultado | Decisión de montaje; lógica del ESP32 (alarma de “sin flujo”) |
| P2 | **Tinaco definitivo**: nivel de agua máx./mín., cota y rosca de la salida | Cambia la altura de succión y la presión (sensibilidad: −0.34 m de presión del tinaco lleno al casi vacío) | Medir cotas respecto a la tierra del huerto (z = 0) | `CONFIG["tinaco"]` |
| P3 | **Microaspersor definitivo** (o confirmar SD‑B) y su ajuste de tapa | El SD‑B es PROVISIONAL; su C depende del ajuste | Ficha oficial (tabla P‑Q‑radio) o aforo de 2–3 presiones | `CONFIG["aspersor"]` |
| P4 | Presión de trabajo real en los aspersores vs radio deseado (30 cm) | A 2.41 bar se está fuera de la tabla Hunter (≤ 2.0 bar): el caudal de 65.9 L/h es **extrapolación del modelo** y el radio real es desconocido (a 2.0 bar ya llega a Ø 0.8 m) | Probar con manómetro en la T del cajón; medir radio y aforar; ajustar tapa o instalar regulador | Escenario de diseño |
| P4b | **Cobertura del cajón** | Con r = 0.30 m solo se cubre el 95.0 %: quedan sin agua el centro, las 4 esquinas y los 4 puntos medios de borde (todos a 0.354 m). Se requiere r ≥ 0.354 m; el escenario r ≈ 0.36 m (≈ 1.80 bar y ≈ 56 L/h interpolados de la tabla) cubre el 100 % geométricamente | Prueba de campo con recipientes en esos 9 puntos (y en una malla) a 1.5 y 1.8 bar; medir el radio real | Escenarios S9/S10; elección del aspersor definitivo |
| P5 | Estándar de rosca de los puertos de la bomba (OD 16‑17 mm) | Define los adaptadores (posible 3/8") | Galga de roscas / comparar con niple 3/8" NPT y BSP | BOM |
| P6 | Kv / Cv de la electroválvula y **presión diferencial mínima de apertura** | Pérdida localizada; si es de piloto puede requerir ≈ 0.2–0.5 bar para abrir | Ficha técnica del modelo exacto o ensayo con 2 manómetros | `CONFIG["Kv_electrovalvula"]` |
| P7 | Pérdida de carga del YF‑S201 | Sin dato confiable (sensibilidad: ≤ 0.2 m) | Manómetro diferencial a 3–4 L/min; K = 2gΔh/V² | `CONFIG["K"]["yfs201"]` |
| P8 | Modelo exacto de la check (columpio o resorte) y presión de apertura | K 2.7 vs 16 (sensibilidad ≤ 0.06 m), y una de resorte puede dificultar el cebado | Ficha / prueba | `CONFIG["K"]["check"]` |
| P9 | Adaptador 1/2" → espiga 6 mm (existencia comercial y paso interior) | Es la mayor pérdida menor individual del modelo | Comprar/medir el paso | `CONFIG["D_rama_aspersor_mm"]` |
| P10 | **Filtro de malla ≥ 100 mesh / ≤ 150 µm** (filtración mínima OFICIAL de Hunter) y su K | Sin filtro, los SD‑B (y el rotor del YF‑S201) pueden obstruirse; no está en el modelo base | Elegir el filtro de 1/2" y tomar su K/ΔP de la ficha | Agregar un enlace con su K entre la bomba y el YF‑S201; alargar el corte D |
| P11 | Longitudes físicas reales de check, bomba, YF‑S201 y electroválvula | Ajustan cortes y posiciones (no el resultado hidráulico) | Medir con flexómetro | `CONFIG["L_*"]` y `["cortes"]` |
| P12 | Comprobación en campo del caudal (YF‑S201) y de la uniformidad de los 4 aspersores | Validación final del modelo | Registro ESP32 (F/7.5 = L/min) + aforo volumétrico por aspersor | Comparación con `resultados_epanet.csv` |

## 3. Pendientes de montaje

| # | Pendiente | Detalle |
|---|---|---|
| M1 | **Instalar filtro de malla 1/2" ≥ 100 mesh / ≤ 150 µm** | Requisito oficial de Hunter. Posición recomendada: descarga de la bomba, antes del YF‑S201 (ver esquema en `calculos_hidraulicos.md` §9c). Debe quedar accesible para su limpieza. Tras elegirlo: agregar su K al modelo, alargar el corte D en la tabla de cortes y regenerar |
| M2 | Probar la bomba antes de fijarla | Curva Q‑H y ciclado del presostato con los 4 SD‑B (P1, P1b) |
| M3 | Confirmar roscas | Puertos de la bomba (OD 16‑17 mm), salida del tinaco, check, electroválvula, YF‑S201 (G1/2 BSPP) frente a conexiones Tuboplus NPT |
| M4 | Adaptador 1/2" → espiga 6 mm para cada SD‑B | Conseguir y medir el paso interior |
| M5 | Prueba de fugas y de cobertura | Termofusión según tiempos Tuboplus; luego aforo en los 9 puntos críticos de cobertura (P4b) |

## 4. Supuestos de modelado

- Régimen permanente (riego activo), electroválvula **OPEN**, bomba **ON**, tinaco lleno.
- Agua limpia a 20 °C.
- El aspersor se supone en máximo ajuste (su C a 1.5 bar = 50 L/h).
- La pérdida de cada conexión se aplica con la velocidad del tubo de 14.4 mm (YF‑S201 con la de 11 mm).
- No se modela la cavitación de la bomba ni el comportamiento del presostato (corte a 0.9 MPa); con la curva provisional la bomba opera a 0.25 MPa. El posible **ciclado** del presostato con solo 4 aspersores debe comprobarse físicamente (P1b).
- No se incluye el filtro ≥ 100 mesh en el modelo base (pendiente M1/P10).
- Las presiones del escenario base son **resultado preliminar dependiente de la curva provisional de bomba**; **no** son presiones validadas.
