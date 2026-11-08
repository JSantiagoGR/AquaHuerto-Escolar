# Los 10 cultivos precargados

Catálogo: `database/cultivos_base.json` (generado por `database/generar_cultivos_base.py`, cargado en la tabla `crops`).

## Fuentes consultadas (2026-10-11)

| Clave | Fuente |
|---|---|
| FAO56-T11/T12/T22 | FAO Irrigation and Drainage Paper 56: duración de etapas (Tabla 11), Kc (Tabla 12), profundidad de raíz y fracción de agotamiento p (Tabla 22) — <https://www.fao.org/4/x0490e/x0490e0b.htm>, <https://www.fao.org/4/x0490e/x0490e0e.htm> |
| ACES-1061 | Alabama Cooperative Extension ANR-1061, temperatura del **suelo** para germinación |
| WVU-HT | West Virginia University / SARE, *Temperature Management in High Tunnels* (temperatura del **aire** óptima y máxima) |
| PURDUE-GDD | Purdue Midwestern Regional Climate Center, temperaturas base de grados-día |
| WISC-GDD | University of Wisconsin Extension (umbral GDD común 10 °C; 4.4 °C para clima fresco) |

## Datos por cultivo

| Cultivo | Etapas FAO (días) | Ciclo | Kc ini/mid/end | p | Raíz (m) | Base GDD | Sensibilidad |
|---|---|---|---|---|---|---|---|
| Lechuga | 25/35/30/10 (Arid Region) | 100 | 0.7/1.00/0.95 | 0.30 | 0.3–0.5 | 4.4 °C | Media-alta |
| Espinaca | 20/30/40/10 (Arid Region) | 100 | 0.7/1.00/0.95 | **0.20** | 0.3–0.5 | 4.4 °C* | **Alta** |
| Rábano | 10/10/15/5 (Winter, Arid) | 40 | 0.7/0.90/0.85 | 0.30 | 0.3–0.5 | 4.4 °C* | Media-alta |
| Zanahoria | 20/30/50/20 (Arid climate) | 120 | 0.7/1.05/0.95 | 0.35 | 0.5–1.0 | 4.4 °C* | Media-alta |
| Cebolla (bulbo) | 20/35/110/45 (Arid; Calif.) | 210 | 0.7/1.05/0.75 | 0.30 | 0.3–0.6 | 4.4 °C* | Media-alta |
| Tomate | 30/40/40/25 (Arid Region) | 135 | 0.6/1.15/0.80 | 0.40 | 0.7–1.5 | 10 °C | Media |
| Pimiento | 30/35/40/20 (Europa/Medit.) | 125 | 0.6/1.05/0.90 | 0.30 | 0.5–1.0 | 10 °C* | Media-alta |
| Pepino | 20/30/40/15 (Arid Region) | 105 | 0.6/1.00/0.75 | 0.50 | 0.7–1.2 | 12.8 °C | Media-baja |
| Calabacita | 25/35/25/15 (Medit.; Arid) | 100 | 0.5/0.95/0.75 | 0.50 | 0.6–1.0 | 7.2 °C* | Media-baja |
| Frijol ejotero | 20/30/30/10 (Calif.; Medit.) | 90 | 0.5/1.05/0.90 | 0.45 | 0.5–0.7 | 10 °C | Media |

\* Base no confirmada específicamente para el cultivo: se usó el umbral típico de la fuente indicada y queda marcado "verificar".
Kc de la etapa de desarrollo = promedio entre inicial y media (en FAO-56 varía linealmente). Kc final del tomate: FAO da 0.70–0.90.
Temperaturas del aire: disponibles para hojas (lechuga, espinaca), tomate, pimiento y cucurbitáceas; para rábano, zanahoria, cebolla y frijol quedan **PENDIENTES** (no se encontró tabla de extensión): no se inventaron.

## Humedad volumétrica: NO se inventa

Las fuentes dan la **fracción de agotamiento p** del agua disponible, no %VWC del EC-5. El sistema convierte solo cuando existe la calibración del suelo:

`θ(d) = FC − d·(FC − WP)`, con `p_aj = p + 0.04·(5 − ETc)` limitado a 0.1–0.8 (FAO-56) y `ETc = Kc_etapa · ET0` (Open-Meteo):

| Umbral | Agotamiento d |
|---|---|
| Máxima | 0 (capacidad de campo) |
| Reserva superior | min(0.10, p/4) (así queda siempre entre la óptima y la máxima, también en cultivos con p bajo como la espinaca) |
| Óptima | p_aj / 2 |
| Mínima normal | p_aj (inicio de estrés, RAW = p·TAW) |
| Emergencia | min(p_aj + 0.20, 0.85) |

Sin FC/WP medidos, el perfil se marca **PENDIENTE_DE_CALIBRACION**: al aplicarlo se envían cultivo, etapa, Kc y horarios, pero el ESP32 **conserva** los umbrales actuales. Los umbrales que trae de fábrica (18/25/35/40/45 %VWC) son **de ejemplo** y no son agronómicos.

## Horarios

Todos los cultivos base usan 06:00–09:00 y 18:00–20:00; el mediodía (11:00–16:00) se evita. Editables por cultivo personalizado.
