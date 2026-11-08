# Estado del proyecto v3 — 2026-10-03 (resumen completo y autocontenido)

Carpeta de trabajo: `C:\TEC\SEMESTRE 5\Automatización industrial\Reto\EPANET\3`.
Carpetas 1 y 2: **solo referencia, no se modifican**. Al cierre de la corrección v3 estaban intactas (32 y 24 entradas con el mismo hash).

## 1. Diseño físico

**ESCENARIO A — DISEÑO PRINCIPAL / DESEADO (modelo final y presentación):**
TINACO → [EXISTENTE, no cuenta en el presupuesto: salida 1/2" → válvula de bola manual → check → conector + Tuboplus → T existente → bajada vertical Tuboplus hasta z ≈ 0.08 m] → **codo 90° nuevo** → Tuboplus → unión mixta → adaptación a la bomba → **BOMBA** → adaptación → unión mixta → niple → **YF‑S201** → niple → **ELECTROVÁLVULA NC (OPEN en riego)** → **línea principal** → **codo 90°** → **SUBIDA VERTICAL** (0.08 → 1.52 m) → **codo 90°** → tramo horizontal corto → **CRUZ** (Tuboplus 200082, z 1.52 m) → salida recta = línea 2; salidas laterales = brazo de Tuboplus + **codo 90°** → líneas 1 y 3 → conector hembra 20 × 1/2" → espiga → **3 mangueras negras paralelas** → **3 aspersores por línea** → tapón.

- **Configuración: 3 líneas × 3 aspersores = 9 aspersores**, cuadrícula 3 × 3 sobre el cajón de 1 × 1 m: líneas a 0.17 / 0.50 / 0.83 m a lo ancho y aspersores a 0.17 / 0.50 / 0.83 m a lo largo.
- **z de la cruz y las líneas = 0.12 (base) + 0.40 (cajón) + 1.00 = 1.52 m.**
- **Codos nuevos en A: 5 × 90°** (pie de la bajada, base y cima de la subida, 2 brazos).
- **Sin filtro** (indicación del equipo; queda solo como recomendación).
- La **manguera negra se usa solo en los 3 laterales**, nunca en la bomba.
- **Hunter SD‑B ya no se usa** en v3; los aspersores son los reales que entregaron.

**ESCENARIO B — subida a 45° (2 codos 45°): solo ALTERNATIVA DE CONTINGENCIA**, si las mediciones demuestran que A no cabe. Variantes calculadas: A2 (vertical + desvío exterior con manguera) y B2 (45° + desvío con manguera).

## 2. Límite de 4.00 m de Tuboplus nuevo

- **4.00 m es un límite de COMPRA** (máximo 1 tubo de 4 m), no una medida cerrada. La instalación existente no cuenta.
- Solo cuenta tubo real: bomba, YF‑S201, electroválvula, adaptadores, cruz, codos y mangueras **no** cuentan.
- **Estimaciones actuales (todas ESTIMADAS):**

| Escenario | Tuboplus nuevo | Margen |
|---|---|---|
| A | **5.148 m** | −1.148 m |
| A2 | 4.534 m | — |
| B | 4.332 m | — |
| B2 | 3.718 m | +0.282 m |

- **Condición automática:** A cumple si **M1 + M5 ≤ 1.662 m**; la estimación actual es 2.810 m.
- **Hoy no se puede confirmar ni descartar que A quepa:** depende de las mediciones de la sección 4.
- Fuente de cálculo: `tabla_cortes_tuboplus.csv`, que se regenera desde `CONFIG["medidas"]`. Distingue tramos medidos y estimados, longitud de componentes, longitud neta, total, margen, veredicto y condición.

## 3. Hidráulica (escenario A, nominal PROVISIONAL)

| Magnitud | Valor |
|---|---|
| Caudal por aspersor | **30 L/h impuesto (nominal provisional)**; escenarios 20/25/30/35/40/70 L/h. **No se conoce la relación apertura‑caudal ni se supone lineal** |
| Caudal total | 9 × 30 = 270 L/h = **4.50 L/min = 0.075 L/s**; 0.025 L/s por línea |
| Presión en los 9 aspersores | **21.816–21.821 m (≈ 2.14 bar): PRELIMINAR, DEPENDIENTE DE LA CURVA PROVISIONAL DE BOMBA** (sensibilidad de la curva: 4.6–16.1 m) |
| Uniformidad hidráulica de presión Pmin/Pmax | **0.9998**. **No es uniformidad de riego**: esa queda pendiente de validación experimental |
| Bomba | 22.98 m a 0.075 L/s (curva provisional); margen 25 % frente a 6 L/min |
| Succión de la bomba | +0.88 m |
| YF‑S201 | 4.5 L/min → 33.8 Hz (rango 1–30 L/min) |
| Velocidad principal | 0.461 m/s |
| Pérdidas (red) | distribuida 0.292 m; menores 0.814 m |
| 40 L/h y 70 L/h por aspersor | **No viables** (presiones negativas; 9 × 70 L/h = 10.5 L/min > 6 L/min) |

**Bomba:** GOOD PUMPS de diafragma autocebante, 12 V (9–14.4 V), 6 A, 72 W, 6 L/min máximo anunciado (a descarga libre). **0.9 MPa = 130 psi = corte del presostato, no punto de operación.** Curva Q‑H **PROVISIONAL** (no publicada; SKU del vendedor D2‑BXSB / PKAV94551). Puertos: **hipótesis fuerte ~3/8" compatibles con manguera de ~10 mm; NPT/BSP SIN CONFIRMAR**; el adaptador no se compra hasta verificarlo.

**Manguera negra:** DI **12 mm PROVISIONAL, NO MEDIDO** (estimación visual), sensibilidad 10/12/14 mm; DE ≈ 16 mm no medido. Longitud calculada ≈ 0.905 m por línea.

## 4. Mediciones físicas pendientes (`CONFIG["medidas"]` / `mediciones_fisicas.csv`)

| Clave | Medición | Estimado hoy |
|---|---|---|
| M0 | Altura de la línea principal / pie de la bajada | 0.08 m |
| M1 | Horizontal: final de la bajada existente → zona de la bomba | 0.07 m |
| M2 | Longitud ocupada por bomba + adaptadores + uniones | 0.295 m |
| M3 | Longitud ocupada por YF‑S201 + adaptadores | 0.136 m |
| M4 / M4b | Longitud ocupada por electroválvula + adaptadores / niples entre conjuntos | 0.159 m / 0.06 m |
| M5 | Horizontal: conjunto (salida EV) → inicio de la subida | 2.74 m |
| M6 | Altura del piso a la parte superior del cajón | 0.52 m |
| M7 | Altura adicional hasta la cruz | 1.00 m |
| M8 | Horizontal superior: eje de la subida → eje de la cruz | 0.083 m |
| M9 / M9b | DI / DE de la manguera negra (vernier) | 12 / 16 mm |
| M10 | Diámetro, paso y tipo de rosca de la bomba (galga) | ~3/8", NPT/BSP ? |
| M11 / M11b | Posición exacta de las 3 líneas y de los aspersores | 0.17/0.50/0.83 m |
| M12 | Longitud real de cada línea de manguera | 0.905 m c/u |
| — | Distancia tinaco → cajón; tramos existentes | 4.00 m; 0.04/0.06/0.055/0.15 m |

Otros pendientes físicos:
- curva Q‑H real y **ciclado del presostato** con 9 aspersores parcialmente abiertos;
- marca, modelo, curva P‑Q y relación apertura‑caudal de los aspersores (no hubo foto);
- **uniformidad de riego** con recipientes;
- Kv de la electroválvula y pérdidas del YF‑S201 y de los adaptadores;
- tinaco definitivo;
- soportes de la subida vertical y de las líneas a 1.52 m;
- fotos de la instalación existente (no se recibieron).

## 5. Validación y archivos

- `validar_modelo.py`: modelo final **71 OK, 3 avisos, 0 fallas**; presentación 69 OK, 3 avisos, 0 fallas. Los avisos son: Tuboplus estimado > 4 m pendiente de medir, uniformidad de riego pendiente y presión requerida por el aspersor desconocida.
- EPANET 2.2 GUI: “Run was successful”. runepanet.exe, WNTR, EPyT/OWA y MCP EPANET (con directorio temporal): OK.
- **Capturas reales** de EPANET 2.2 con la subida vertical: `capturas_epanet/00_Modelo_Limpio.png`, `01_Pressure_Flow.png`, `02_Pressure_Velocity.png`, `03_Demand_UnitHeadloss.png`.
- **Proyecto EPANET guardado:** `riego_huerto_v3_presentacion.net`, con las leyendas de las capturas. Los `.inp` generados no se modificaron desde la GUI. Todas las ventanas de EPANET quedaron cerradas; la ventana obsoleta con la versión a 45° se cerró **sin guardar**.
- Archivos principales: `riego_huerto_v3_final.inp`, `riego_huerto_v3_presentacion.inp`, `generar_modelo.py`, `validar_modelo.py`, `calculos_hidraulicos.md`, `calculos_resultados.md`, `tabla_cortes_tuboplus.csv`, `alternativas_trazado.csv`, `mediciones_fisicas.csv`, `resultados_epanet.csv`, `escenarios_sensibilidad.csv` (20 escenarios), `BOM_hidraulico.csv`, `validacion_epanet.txt`, `SOURCES.md`, `DECISIONS.md`, `ASSUMPTIONS_AND_PENDING.md`, `README.md`, `.mcp.json`.

## 6. Cómo continuar (tras medir)

1. Editar `CONFIG["medidas"]` en `generar_modelo.py` (`valor` + `estado: "MEDIDO"`). Si cambia la curva de la bomba, editar `CONFIG["bomba_curva"]`.
2. Ejecutar desde la carpeta 3 (`uv` está en `C:\Users\jaime\AppData\Roaming\Python\Python314\Scripts\uv.exe`):

```bash
uv run --python 3.12 --with wntr --with epyt --with matplotlib python generar_modelo.py
```

```bash
uv run --python 3.12 --with wntr --with epyt --with matplotlib python validar_modelo.py
```

3. Si A excede con medidas reales → evaluar B (`CONFIG["geometria_principal"] = "B"`) o B2. Si cabe → mantener A.
4. Si cambia la red visualmente, actualizar las capturas 00–03 en la GUI de EPANET 2.2.

## 7. Reporte Word (2026-11-02)

- `reporte/Reporte_Riego_Automatizado_v3.docx` (+ PDF de revisión): portada con espacios para llenar, índice, 13 secciones, 15 figuras, 11 tablas, 20 ecuaciones y referencias APA 7. Solo escenario A (el construido). Incluye sección de control (ESP32 + YF-S201, riego por volumen de 5 L, del `control_riego_por_litro.zip`).
- El sistema **ya está armado y funcionó** (dato del equipo). Tinaco de alimentación: el negro de la derecha (F01). Las cajas grises solo protegen la electrónica.
- Conexión arriba confirmada: subida → codo 90° → tubo → **CRUZ**; centro: tubo → unión → espiga → manguera; lados: tubo → codo 90° → tubo → unión → espiga → manguera; 3 aspersores por manguera.
- Fotos reales en `fotos_reales/` (F01–F08); copias reducidas en `reporte/img/`.
- Regenerar tras medir: `generar_modelo.py` → `python reporte/generar_figuras.py` → `python reporte/generar_reporte.py` → `reporte/render_word.ps1` (actualiza índice y exporta PDF). Datos de portada en `PORTADA` de `generar_reporte.py`.
