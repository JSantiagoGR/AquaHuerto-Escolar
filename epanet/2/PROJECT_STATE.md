# Estado del proyecto — 2026-09-30

## Terminado ✔

1. `riego_huerto_v2_final.inp` funcional (EPANET 2.2 “ran successfully”, sin WARNINGS).
2. `riego_huerto_v2_presentacion.inp` con hidráulica idéntica (diferencia de resultados = 0) y etiquetas sin solapes.
3. Simulación ejecutada con EPANET 2.2 (runepanet.exe), WNTR, EPyT y el servidor MCP de EPANET.
4. Exactamente **2 laterales** y **4 microaspersores** SD‑B provisionales, como EMITTERS individuales.
5. Cálculos hidráulicos por tramo (A, V, Re, régimen, f, hf, hm, h total) con D‑W y comparación H‑W.
6. Pérdidas distribuidas y menores con K oficiales de Tuboplus y K estimados documentados.
7. Validación automática: **68 OK, 2 avisos (caudal extrapolado; cobertura 95 % con r 0.30 m), 0 fallas**.
8. BOM con estados. 9. Tabla de cortes: **5.722 m ≤ 8.00 m**. 10. Fuentes. 11. Resultados y 21 escenarios (incluye cobertura r 0.36 m).
12. Pendientes separados (`ASSUMPTIONS_AND_PENDING.md`). 13. Carpeta 1 intacta (verificada por hash).
14. Captura real de EPANET 2.2 (`00_Modelo_Limpio.png`) + figuras Python de resultados.

## Resultado actual (PRELIMINAR)

| Magnitud | Valor |
|---|---|
| Caudal total | 0.07326 L/s (4.40 L/min) con curva provisional; diseño 0.05556 L/s (3.33 L/min) |
| Caudal por lateral | 0.03663 L/s (diseño 0.02778 L/s) |
| Aspersores E1–E4 | 24.62 m = 2.41 bar; 65.9 L/h c/u = **extrapolación del modelo** (la tabla Hunter llega a 2.0 bar / 60 L/h) |
| Cobertura del cajón | r 0.30 m → 95.0 % (faltan centro, esquinas y puntos medios de borde); r 0.36 m → 100 % con ≈ 1.80 bar / ≈ 56 L/h (interpolado) |
| Bomba requerida para r 0.36 m | ≈ 18.2 m a 0.0618 L/s (3.71 L/min) |
| Velocidad principal | 0.450 m/s (diseño 0.341 m/s) |
| Altura de bomba requerida (diseño) | 15.04 m a 0.0556 L/s |
| Tuboplus | 5.722 m (margen 2.278 m) |

## Bloqueado por datos físicos (no detiene el modelo)

- **Prueba física de la bomba de diafragma**: curva Q‑H real (define las presiones finales) y posible **ciclado del presostato** al trabajar con solo 4 microaspersores.
- **Filtro ≥ 100 mesh / 150 µm** (mínimo Hunter): elegirlo, instalarlo en la descarga de la bomba antes del YF‑S201 y agregar su K al modelo.
- Cobertura real del cajón (aforo en centro, esquinas y puntos medios de borde).
- Tinaco definitivo → nivel y cota de salida.
- Aspersor definitivo (SD‑B provisional), Kv de la electroválvula, ΔP del YF‑S201, modelo de check, rosca de la bomba, adaptador a espiga 6 mm, filtro ≥ 100 mesh.

## Siguiente paso recomendado

Medir la curva Q‑H de la bomba (procedimiento en `ASSUMPTIONS_AND_PENDING.md`, P1), cargarla en `CONFIG["bomba_curva"]`, regenerar y validar. Si la presión en los aspersores supera ~2 bar, ajustar las tapas del SD‑B o agregar un regulador de presión.
