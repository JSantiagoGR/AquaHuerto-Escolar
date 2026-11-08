# Fuentes — v3

Prioridad: fabricante > manual oficial > literatura técnica > vendedores con ficha técnica > otras. Consultadas entre el 29 de septiembre y el 3 de octubre de 2026.

| # | Fuente | Dato utilizado | Uso | Clase |
|---|---|---|---|---|
| 1 | Rotoplas, *Manual Técnico Tuboplus* 2017 — https://ferreambriz.com/wp-content/uploads/2024/08/MANUAL-TUBOPLUS.pdf | Tubo 200224: d 20, **di 14.40**, e 2.80 mm, Clase 16 SDR 7.4; ε 0.007 mm; Tabla 10 de K (codo 90° 2.00, codo 45° 0.60, conector 0.40, tees 1.8/1.3/4.2/2.2); Tabla 11; dimensiones de codo 90° 200014, **codo 45° 200005 (L 20 / p 15)**, **cruz 200082 (L 54 / p 16)**, conector 200039, tuerca unión mixta 200235; recomendación de fijar abrazaderas sobre el tubo | DI en EPANET, K oficiales, cortes, BOM | OFICIAL |
| 2 | Rotoplas MX, producto 200224 — https://rotoplas.com.mx/product/Tubo-clase-16-de-20-mm-Tuboplus/ | SKU 200224 = tubo Clase 16 de 20 mm | Confirma el producto comercial | OFICIAL |
| 3 | Rotoplas Centroamérica, ficha Tuboplus — https://rotoplascentroamerica.com/tuboplus/rtp-resources/descargas/Final_Ficha_Tecnica_Tuboplus_Impresioon.pdf | 24 kg/cm² a 20 °C; tiempos de termofusión 20 mm | Instalación | OFICIAL |
| 4 | Fotografías del equipo (bomba, caja, etiqueta) — adjuntas en la conversación | Placa: GOOD PUMPS 12 V (9‑14.4 V), 6 A, 72 W, 6 L/min, Pressure Setting 0.9 MPa; caja “Electric Diaphragm Pump — Auto Start Stop / Automatic water absorption”; etiqueta del vendedor “Bomba De Agua Diafragma Portátil 130 Psi 6L/min 12V 72w”, SKU D2‑BXSB, PKAV94551; la caja muestra también otro modelo (SF‑4200: 3.0 A, 4.0 L/min, 0.6 MPa) que **no** es la bomba disponible | Identificación; 130 psi = 0.9 MPa | MEDIDO / FOTO |
| 5 | La Electrónica (GT) — https://laelectronica.com.gt/products/bomba-de-diafragma-automatica-de-12v-y-6-lmin-recto-a-rosca-38 | Misma bomba 12 V/6 L/min: presostato con **corte a 0.9 MPa (≈130 psi) al cerrar el flujo y rearranque al abrir**; caudal 4.0–6.0 L/min; 6 A; **puerto de salida rosca macho 3/8"**, entrada/salida ≈ 10 mm (espiga para manguera 10 mm); succión 1–2 m; 16.5 × 10 × 6 cm | Conexión 3/8", interpretación de 130 psi, ciclado | VENDEDOR con ficha técnica |
| 6 | Dynamic Solutions — https://dynamic.me/water-pump-12-v-6-a-72-w-130-psi-6-l-min-stable-high-pressure-diaphragm-water-pump-pressure-protection | Entrada/salida 10 mm; servicio **intermitente**; presostato de protección; “presión máxima 7 kg” (contradice 130 psi → dato no confiable) | Riesgos de operación | VENDEDOR |
| 7 | MercadoLibre / Amazon / AliExpress (listados de “bomba diafragma 130 psi 6 L/min 12 V 72 W”) | Repiten la placa; variantes “roscada” y “espiga”; **ninguno publica curva Q‑H** | Justifica la curva PROVISIONAL | COMERCIAL |
| 8 | Handson Technology, YF‑S201 — https://handsontec.com/dataspecs/sensor/Water%20Flow%20Sensor.pdf ; ficha YF‑S201 (fabacademy) | DI 11 mm, 1–30 L/min, F = 7.5·Q, 450 pulsos/L, ≤ 1.75–2.0 MPa | Rango y frecuencia del YF‑S201 | DOC. TÉCNICA |
| 9 | Crane Co., *Technical Paper 410* | K check columpio = 100·f_T (≈ 2.7 en 1/2"); K válvula de bola de paso completo = 3·f_T (≈ 0.08); entrada de borde vivo 0.5 | K ESTIMADOS | LITERATURA |
| 10 | IEC 60534 / VDI 2173 (Kv) | Δp = (Q/Kv)² | K de la electroválvula | NORMA |
| 11 | U.S. EPA, *EPANET 2.2 User Manual* (EPA/600/R‑20/133) | LPS, D‑W, Pipe CV, demandas/emisores, mensajes de advertencia | Modelo | OFICIAL |
| 12 | OpenWaterAnalytics EPANET / EPyT; USEPA WNTR; KWR‑Water epanet‑mcp‑server | Motores y validación | Validación | OFICIAL / código abierto |
| 13 | Proyecto v2 (carpeta 2, solo lectura) | Métodos, datos de Tuboplus y de Hunter (Hunter ya no se usa en v3) | Referencia | INTERNO |

**No encontrado (búsqueda exhaustiva):** fabricante, modelo exacto y curva Q‑H de la bomba (los códigos D2‑BXSB y PKAV94551 no aparecen en fuentes públicas); marca y modelo de los aspersores (no se recibió su fotografía).
