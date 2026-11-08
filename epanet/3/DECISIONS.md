# Decisiones — v3 (corregido)

| # | Decisión | Motivo |
|---|---|---|
| D1 | **Diseño principal = ESCENARIO A: subida VERTICAL** con codos de 90°, tramo horizontal corto arriba, cruz a z 1.52 m, brazos de Tuboplus con codos de 90° y 3 mangueras paralelas | Es el diseño físico deseado por el equipo. El límite de 4.00 m de Tuboplus nuevo es un **límite de compra**, no una razón para cambiar la geometría antes de medir |
| D2 | **Escenario B (subida a 45°) solo como ALTERNATIVA DE CONTINGENCIA** | Se adoptará únicamente si las mediciones demuestran que A no cabe. Con las estimaciones actuales, B también requiere el desvío por manguera (B2) para caber |
| D3 | Longitudes de Tuboplus calculadas desde la tabla editable `CONFIG["medidas"]` (estado ESTIMADO/MEDIDO por medida), con veredicto automático y la condición M1 + M5 ≤ máximo | Ninguna longitud se presenta como cerrada; 5.148 m (A) es una **estimación** |
| D4 | La tabla de Tuboplus separa tramos medidos y estimados, longitud ocupada por componentes (no Tuboplus), longitud neta, total y margen | Requisito de presupuesto; bomba, YF‑S201, electroválvula, adaptadores, cruz, codos y mangueras **no** cuentan como tubo |
| D5 | “Uniformidad” renombrada a **UNIFORMIDAD HIDRÁULICA DE PRESIÓN (Pmin/Pmax)** | Presiones iguales no garantizan riego uniforme; la uniformidad de riego queda pendiente de validación experimental |
| D6 | Presiones reportadas como **PRELIMINARES, DEPENDIENTES DE LA CURVA PROVISIONAL DE BOMBA** | No existe curva Q‑H publicada |
| D7 | Caudales de aspersor como escenarios **impuestos** (20–70 L/h); 30 L/h es **nominal provisional** | No se conoce la relación apertura‑caudal ni la curva P‑Q de los aspersores reales; no se supone linealidad |
| D8 | Puertos de bomba: hipótesis fuerte de ~3/8" y manguera de ~10 mm; **NPT/BSP sin confirmar**; el adaptador queda PENDIENTE en la BOM | Evitar comprar una rosca incompatible |
| D9 | Manguera negra DI 12 mm **NO MEDIDO**, con sensibilidad 10/12/14 mm; se edita en `M9_manguera_DI_mm` | Estimación visual |
| D10 | Cruz Tuboplus 200082 con K PROVISIONALES (proxies de tee) | Tuboplus no publica K de cruz |
| D11 | Instalación existente modelada pero fuera del presupuesto de Tuboplus | Indicación del equipo |
| D12 | Sin filtro en el modelo y en la BOM | Indicación del equipo (queda como recomendación) |
| D13 | Darcy‑Weisbach como fórmula principal; H‑W como comparación | Coexisten régimen laminar, de transición y turbulento bajo |
| D14 | MCP de EPANET con directorio de trabajo temporal; capturas reales de la GUI de EPANET 2.2 actualizadas para la subida vertical (solo se ajustaron leyendas; no se guardó desde la GUI) | No modificar las carpetas 1, 2 y 3 con archivos del servidor |
| D15 | Fotos de la instalación del tinaco y de los aspersores no recibidas | Las longitudes existentes y los aspersores siguen siendo ESTIMADOS/PROVISIONALES |
| D16 | Configuración **3 líneas × 3 aspersores = 9** (cuadrícula 0.17 / 0.50 / 0.83 m), cada aspersor modelado individualmente (A11…A33) | Distribución uniforme sobre el cajón de 1 × 1 m; nunca una demanda equivalente única |
| D17 | **Hunter SD‑B descartado** en v3; se usan los aspersores reales (≈ 70 L/h máximo, sin marca identificada) | Indicación del equipo |
| D18 | Bomba: **0.9 MPa = 130 psi** interpretado como **corte del presostato** (Q ≈ 0), no como presión a 6 L/min | Placa + documentación de vendedores; no existe curva Q‑H publicada |
| D19 | Proyecto de la GUI guardado como **`riego_huerto_v3_presentacion.net`** (formato propio de EPANET, con las leyendas de las capturas); los `.inp` generados por script no se sobrescriben. Ventana obsoleta con la versión a 45° cerrada **sin guardar** | Evitar que la GUI pise el modelo corregido o reformatee los `.inp` |
