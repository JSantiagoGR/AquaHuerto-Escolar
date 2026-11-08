# Riego v3 (corregido) — cruz + 3 laterales de manguera × 3 aspersores = 9

**Diseño principal (Escenario A, deseado):** TINACO → [existente: salida → válvula de bola → check → T → bajada] → codo 90° → BOMBA → YF‑S201 → ELECTROVÁLVULA NC → línea principal → codo 90° → **SUBIDA VERTICAL** hasta z 1.52 m (1.00 m sobre el cajón) → codo 90° → tramo corto → **CRUZ** → 3 salidas (las laterales con brazo de Tuboplus y codo 90°) → 3 mangueras negras paralelas → 3 aspersores por línea → tapón. **Sin filtro.**

**Escenario B (subida a 45°):** solo **alternativa de contingencia**, si las mediciones demuestran que A no cabe en 4.00 m de Tuboplus nuevo.

## Archivos

| Archivo | Contenido |
|---|---|
| `riego_huerto_v3_final.inp` | Modelo EPANET del escenario A (LPS, D‑W, 9 aspersores de demanda fija) |
| `riego_huerto_v3_presentacion.inp` | Misma hidráulica, acomodado para EPANET 2.2 (**abrir este**) |
| `generar_modelo.py` | Generador paramétrico: `CONFIG["medidas"]` (mediciones), `geometrias` A/A2/B/B2, caudales, bomba, K |
| `validar_modelo.py` | Validación automática |
| `tabla_cortes_tuboplus.csv` | Tuboplus por escenario: tramos medidos/estimados, componentes (no Tuboplus), neto, total, margen, veredicto, condición |
| `mediciones_fisicas.csv` | Lista de mediciones pendientes con valor estimado y cómo medir |
| `alternativas_trazado.csv` | A / A2 / B / B2 |
| `calculos_hidraulicos.md` · `calculos_resultados.md` | Cálculo explicado · tablas numéricas generadas |
| `resultados_epanet.csv` · `escenarios_sensibilidad.csv` | Resultados (presiones PRELIMINARES) y 20 escenarios |
| `BOM_hidraulico.csv` | YA INSTALADO / YA DISPONIBLE / COMPRAR / PENDIENTE DE CONFIRMAR |
| `validacion_epanet.txt` | Evidencia (GUI de EPANET 2.2, runepanet, WNTR, EPyT, MCP) |
| `SOURCES.md` · `DECISIONS.md` · `ASSUMPTIONS_AND_PENDING.md` · `PROJECT_STATE.md` | Fuentes, decisiones, mediciones/pendientes, estado |
| `capturas_epanet/` | Capturas **reales** de EPANET 2.2 con la subida vertical (00–03) |

## Después de medir

Editar `CONFIG["medidas"]` (valor + `estado: "MEDIDO"`) y ejecutar:

```bash
uv run --python 3.12 --with wntr --with epyt --with matplotlib python generar_modelo.py
```

```bash
uv run --python 3.12 --with wntr --with epyt --with matplotlib python validar_modelo.py
```

## Resultado actual (ESTIMADO / PRELIMINAR)

- **Tuboplus del diseño A:** ≈ 5.148 m frente al límite de 4.00 m. Es una estimación: cabe si M1 + M5 ≤ 1.662 m. **No se puede confirmar hasta medir.**
- **Caudal:** 30 L/h × 9 = 4.5 L/min (nominal provisional).
- **Aspersores:** 21.82 m (≈ 2.14 bar), presión **preliminar dependiente de la curva provisional de la bomba**.
- **Uniformidad hidráulica de presión** Pmin/Pmax = 0.9998. **No es uniformidad de riego**, que queda pendiente de validación experimental.
