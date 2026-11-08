# Riego v2 — modelo EPANET de 1 cajón con 4 microaspersores

Sistema: **TINACO → check 1/2" → bajada → BOMBA 12 V → [FILTRO ≥ 100 mesh / 150 µm, PENDIENTE] → YF‑S201 → electroválvula NC → línea principal → subida → T centrada → 2 laterales → 4 microaspersores Hunter SD‑B (PROVISIONALES)**, todo en Tuboplus 20 mm Clase 16 (DI 14.40 mm).

El filtro es la filtración mínima exigida por Hunter; se instala en la descarga de la bomba, antes del YF‑S201. Aún no está en el modelo hidráulico (ver esquema físico en `calculos_hidraulicos.md` §9c).

## Archivos

| Archivo | Contenido |
|---|---|
| `riego_huerto_v2_final.inp` | Modelo EPANET principal (LPS, Darcy‑Weisbach, 4 EMITTERS, check CV, electroválvula OPEN) |
| `riego_huerto_v2_presentacion.inp` | Misma hidráulica, acomodado para leerse en EPANET 2.2 (**abrir este**) |
| `calculos_hidraulicos.md` | Conversiones, emisores, área, V, Re, f, D‑W vs H‑W, pérdidas distribuidas y menores por tramo, altura requerida, sensibilidad |
| `resultados_epanet.csv` | Resultados por nodo y enlace del escenario base |
| `escenarios_sensibilidad.csv` | 21 escenarios (n, demanda fija, H‑W, tinaco, curva de bomba, K check, K YF‑S201, Kv electroválvula, cobertura r 0.36 m); columna `nota_caudal_aspersor` marca las extrapolaciones |
| `tabla_cortes_tuboplus.csv` | Cortes de Tuboplus: **5.722 m ≤ 8.00 m** |
| `BOM_hidraulico.csv` | Lista de materiales con estado CONFIRMADO / PROVISIONAL / PENDIENTE |
| `validacion_epanet.txt` | Evidencia de validación (EPANET 2.2, WNTR, EPyT, MCP) |
| `SOURCES.md` · `DECISIONS.md` · `ASSUMPTIONS_AND_PENDING.md` · `PROJECT_STATE.md` | Fuentes, decisiones, supuestos/pendientes, estado |
| `generar_modelo.py` | Generador **paramétrico** (bloque `CONFIG`) de ambos .inp, CSV y escenarios |
| `validar_modelo.py` | Validación automática (70 comprobaciones, incluye cobertura) |
| `graficar_resultados.py` | Figuras de resultados |
| `capturas_epanet/` | `00_Modelo_Limpio.png` (captura real de EPANET 2.2), `01‑03_*_PYTHON.png` (resultados) y `04_Cobertura_PYTHON.png` (cobertura del cajón); las figuras Python no son capturas de la GUI |
| `resultados_calculo.json` | Datos intermedios para la documentación |
| `.mcp.json` | Configuración del servidor MCP de EPANET (igual a la de la carpeta 1) |

## Cómo regenerar todo (después de cambiar el tinaco, el aspersor o la bomba)

1. Editar el bloque `CONFIG` de `generar_modelo.py` (p. ej. `tinaco`, `aspersor`, `bomba_curva`, `K`).
2. Ejecutar desde esta carpeta:

```bash
uv run --python 3.12 --with wntr --with epyt --with matplotlib python generar_modelo.py
```

```bash
uv run --python 3.12 --with wntr --with epyt --with matplotlib python validar_modelo.py
```

```bash
uv run --python 3.12 --with wntr --with epyt --with matplotlib python graficar_resultados.py
```

(`uv` está en `C:\Users\jaime\AppData\Roaming\Python\Python314\Scripts\uv.exe`.)

## Resultado principal (PRELIMINAR)

- Diseño: 4 × 50 L/h = **200 L/h = 3.333 L/min = 0.05556 L/s** a 1.5 bar → la bomba debe dar **≈ 15.0 m a 3.33 L/min**.
- Con la curva **provisional** de bomba: 0.0733 L/s y **2.41 bar** por aspersor (presión mayor que la de diseño). El caudal de **65.9 L/h es una EXTRAPOLACIÓN del modelo, no un dato de Hunter**: la tabla oficial del Solo‑Drip llega a 2.0 bar (40 / 50 / 60 L/h a 1.0 / 1.5 / 2.0 bar); solo el rango general de funcionamiento llega a 2.5 bar.
- **Cobertura:** con radio 0.30 m se cubre el 95.0 % del cajón (quedan fuera el centro, las 4 esquinas y los 4 puntos medios de borde, a 0.354 m). El escenario de 0.36 m cubre el 100 % y corresponde a ≈ 1.80 bar y ≈ 56 L/h (interpolado de la tabla Hunter) → bomba ≈ 18.2 m a 3.71 L/min.
- **Prueba física pendiente de la bomba de diafragma:** curva Q‑H real y posible ciclado del presostato trabajando con solo 4 microaspersores. **Es la prioridad.**
