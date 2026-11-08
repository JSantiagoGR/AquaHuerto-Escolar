# Resultados numericos (generado por generar_modelo.py - no editar a mano)

Geometria principal: **A - DISENO PRINCIPAL / DESEADO** (Subida VERTICAL (codos 90) + cruz + brazos Tuboplus con codos 90). Caudal 30 L/h por aspersor (PROVISIONAL), manguera DI 12.0 mm (NO MEDIDO), curva de bomba PROVISIONAL. z cruz/laterales = 1.52 m.

## Tuboplus nuevo por escenario geometrico (ESTIMADO hasta medir)

| Escenario | Rol | Descripcion | Tuboplus nuevo (m) | Margen vs 4.00 m | Cumple (estimado) | Estado | Codos 90 | Codos 45 |
|---|---|---|---|---|---|---|---|---|
| A | DISENO PRINCIPAL / DESEADO | Subida VERTICAL (codos 90) + cruz + brazos Tuboplus con codos 90 | 5.148 | -1.148 | NO | ESTIMADO | 5 | 0 |
| A2 | variante | Subida vertical + desvio de laterales exteriores con la manguera | 4.534 | -0.534 | NO | ESTIMADO | 3 | 0 |
| B | ALTERNATIVA DE CONTINGENCIA | Subida a 45 deg (2 codos 45) + brazos Tuboplus con codos 90 | 4.332 | -0.332 | NO | ESTIMADO | 3 | 2 |
| B2 | contingencia extrema | Subida a 45 deg + desvio exterior con la manguera | 3.718 | 0.282 | SI | ESTIMADO | 1 | 2 |

Condicion para cumplir 4.00 m manteniendo las demas medidas: A: M1 + M5 <= 1.662 m; A2: M1 + M5 <= 2.276 m; B: M1 + M5 <= 2.478 m; B2: M1 + M5 <= 3.092 m (estimado actual M1 + M5 = 2.810 m).

Longitud de manguera por linea (calculada): L1 = 0.91 m, L2 = 0.91 m, L3 = 0.91 m

## Tabla por tramo (escenario base)

| Tramo | Material | L (m) | D (mm) | Q (L/s) | V (m/s) | Re | Regimen | f | K | hf D-W (m) | hm (m) | h total (m) | EPANET (m) | H-W C150 + hm (m) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P-TK | existente | 0.040 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 0.50 | 0.00106 | 0.00540 | 0.00646 | 0.00647 | 0.00625 |
| BOLA | existente | 0.060 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 0.08 | 0.00158 | 0.00086 | 0.00245 | 0.00247 | 0.00214 |
| CHK | existente | 0.055 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 2.70 | 0.00145 | 0.02918 | 0.03064 | 0.03064 | 0.03035 |
| EX-TB | existente | 0.187 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 2.20 | 0.00494 | 0.02378 | 0.02872 | 0.02878 | 0.02775 |
| EX-BAJ | existente | 0.185 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 0.00 | 0.00488 | 0.00000 | 0.00488 | 0.00496 | 0.00393 |
| N-A | tuboplus | 0.100 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 2.40 | 0.00264 | 0.02594 | 0.02858 | 0.02861 | 0.02807 |
| AD-IN | adaptador | 0.035 | 7.0 | 0.07500 | 1.949 | 13590 | turbulento (Colebrook) | 0.0302 | 0.50 | 0.02927 | 0.09679 | 0.12605 | 0.12631 | 0.12174 |
| AD-OUT | adaptador | 0.035 | 7.0 | 0.07500 | 1.949 | 13590 | turbulento (Colebrook) | 0.0302 | 1.00 | 0.02927 | 0.19358 | 0.22284 | 0.22304 | 0.21853 |
| N-B | tuboplus | 0.127 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 0.80 | 0.00335 | 0.00865 | 0.01200 | 0.01204 | 0.01135 |
| YF | yfs201 | 0.062 | 11.0 | 0.07500 | 0.789 | 8648 | turbulento (Colebrook) | 0.0330 | 2.00 | 0.00591 | 0.06349 | 0.06940 | 0.06943 | 0.06838 |
| N-C | tuboplus | 0.134 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 0.80 | 0.00354 | 0.00865 | 0.01219 | 0.01223 | 0.01150 |
| EV | electrovalvula | 0.085 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 7.65 | 0.00224 | 0.08272 | 0.08496 | 0.08495 | 0.08452 |
| N-D | tuboplus | 2.777 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 2.40 | 0.07332 | 0.02594 | 0.09926 | 0.10032 | 0.08496 |
| N-E | tuboplus | 1.440 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 2.00 | 0.03802 | 0.02162 | 0.05964 | 0.06018 | 0.05222 |
| N-H | tuboplus | 0.083 | 14.4 | 0.07500 | 0.461 | 6606 | turbulento (Colebrook) | 0.0352 | 0.00 | 0.00219 | 0.00000 | 0.00219 | 0.00222 | 0.00176 |
| XO1 | tuboplus | 0.434 | 14.4 | 0.02500 | 0.154 | 2202 | transicion (Colebrook, cota) | 0.0483 | 4.60 | 0.00175 | 0.00552 | 0.00727 | 0.00661 | 0.00673 |
| ESP1 | adaptador | 0.040 | 9.0 | 0.02500 | 0.393 | 3523 | transicion (Colebrook, cota) | 0.0422 | 0.50 | 0.00148 | 0.00394 | 0.00541 | 0.00530 | 0.00503 |
| HL11 | manguera | 0.145 | 12.0 | 0.02500 | 0.221 | 2643 | transicion (Colebrook, cota) | 0.0458 | 0.00 | 0.00138 | 0.00000 | 0.00138 | 0.00089 | 0.00098 |
| RA11 | conexion_aspersor | 0.030 | 4.0 | 0.00833 | 0.663 | 2643 | transicion (Colebrook, cota) | 0.0467 | 1.00 | 0.00786 | 0.02241 | 0.03027 | 0.02743 | 0.02799 |
| HL12 | manguera | 0.330 | 12.0 | 0.01667 | 0.147 | 1762 | laminar (64/Re) | 0.0363 | 0.00 | 0.00111 | 0.00000 | 0.00111 | 0.00113 | 0.00105 |
| RA12 | conexion_aspersor | 0.030 | 4.0 | 0.00833 | 0.663 | 2643 | transicion (Colebrook, cota) | 0.0467 | 1.00 | 0.00786 | 0.02241 | 0.03027 | 0.02743 | 0.02799 |
| HL13 | manguera | 0.330 | 12.0 | 0.00833 | 0.074 | 881 | laminar (64/Re) | 0.0727 | 0.00 | 0.00055 | 0.00000 | 0.00055 | 0.00056 | 0.00029 |
| RA13 | conexion_aspersor | 0.030 | 4.0 | 0.00833 | 0.663 | 2643 | transicion (Colebrook, cota) | 0.0467 | 1.00 | 0.00786 | 0.02241 | 0.03027 | 0.02743 | 0.02799 |
| HT1 | manguera | 0.100 | 12.0 | 0 | 0 | - | sin flujo | - | - | 0 | 0 | 0 | 0 | 0 |
| XO2 | tuboplus | 0.104 | 14.4 | 0.02500 | 0.154 | 2202 | transicion (Colebrook, cota) | 0.0483 | 2.20 | 0.00042 | 0.00264 | 0.00306 | 0.00290 | 0.00293 |
| ESP2 | adaptador | 0.040 | 9.0 | 0.02500 | 0.393 | 3523 | transicion (Colebrook, cota) | 0.0422 | 0.50 | 0.00148 | 0.00394 | 0.00541 | 0.00530 | 0.00503 |
| HL21 | manguera | 0.145 | 12.0 | 0.02500 | 0.221 | 2643 | transicion (Colebrook, cota) | 0.0458 | 0.00 | 0.00138 | 0.00000 | 0.00138 | 0.00089 | 0.00098 |
| RA21 | conexion_aspersor | 0.030 | 4.0 | 0.00833 | 0.663 | 2643 | transicion (Colebrook, cota) | 0.0467 | 1.00 | 0.00786 | 0.02241 | 0.03027 | 0.02743 | 0.02799 |
| HL22 | manguera | 0.330 | 12.0 | 0.01667 | 0.147 | 1762 | laminar (64/Re) | 0.0363 | 0.00 | 0.00111 | 0.00000 | 0.00111 | 0.00113 | 0.00105 |
| RA22 | conexion_aspersor | 0.030 | 4.0 | 0.00833 | 0.663 | 2643 | transicion (Colebrook, cota) | 0.0467 | 1.00 | 0.00786 | 0.02241 | 0.03027 | 0.02743 | 0.02799 |
| HL23 | manguera | 0.330 | 12.0 | 0.00833 | 0.074 | 881 | laminar (64/Re) | 0.0727 | 0.00 | 0.00055 | 0.00000 | 0.00055 | 0.00056 | 0.00029 |
| RA23 | conexion_aspersor | 0.030 | 4.0 | 0.00833 | 0.663 | 2643 | transicion (Colebrook, cota) | 0.0467 | 1.00 | 0.00786 | 0.02241 | 0.03027 | 0.02743 | 0.02799 |
| HT2 | manguera | 0.100 | 12.0 | 0 | 0 | - | sin flujo | - | - | 0 | 0 | 0 | 0 | 0 |
| XO3 | tuboplus | 0.434 | 14.4 | 0.02500 | 0.154 | 2202 | transicion (Colebrook, cota) | 0.0483 | 4.60 | 0.00175 | 0.00552 | 0.00727 | 0.00661 | 0.00673 |
| ESP3 | adaptador | 0.040 | 9.0 | 0.02500 | 0.393 | 3523 | transicion (Colebrook, cota) | 0.0422 | 0.50 | 0.00148 | 0.00394 | 0.00541 | 0.00530 | 0.00503 |
| HL31 | manguera | 0.145 | 12.0 | 0.02500 | 0.221 | 2643 | transicion (Colebrook, cota) | 0.0458 | 0.00 | 0.00138 | 0.00000 | 0.00138 | 0.00089 | 0.00098 |
| RA31 | conexion_aspersor | 0.030 | 4.0 | 0.00833 | 0.663 | 2643 | transicion (Colebrook, cota) | 0.0467 | 1.00 | 0.00786 | 0.02241 | 0.03027 | 0.02743 | 0.02799 |
| HL32 | manguera | 0.330 | 12.0 | 0.01667 | 0.147 | 1762 | laminar (64/Re) | 0.0363 | 0.00 | 0.00111 | 0.00000 | 0.00111 | 0.00113 | 0.00105 |
| RA32 | conexion_aspersor | 0.030 | 4.0 | 0.00833 | 0.663 | 2643 | transicion (Colebrook, cota) | 0.0467 | 1.00 | 0.00786 | 0.02241 | 0.03027 | 0.02743 | 0.02799 |
| HL33 | manguera | 0.330 | 12.0 | 0.00833 | 0.074 | 881 | laminar (64/Re) | 0.0727 | 0.00 | 0.00055 | 0.00000 | 0.00055 | 0.00056 | 0.00029 |
| RA33 | conexion_aspersor | 0.030 | 4.0 | 0.00833 | 0.663 | 2643 | transicion (Colebrook, cota) | 0.0467 | 1.00 | 0.00786 | 0.02241 | 0.03027 | 0.02743 | 0.02799 |
| HT3 | manguera | 0.100 | 12.0 | 0 | 0 | - | sin flujo | - | - | 0 | 0 | 0 | 0 | 0 |

Totales red: perdida distribuida 0.2918 m, perdidas menores 0.8138 m.

## Aspersores (escenario base) - PRESION PRELIMINAR DEPENDIENTE DE CURVA PROVISIONAL DE BOMBA

| Aspersor | Presion (m) | Presion (bar) | Caudal impuesto (L/h) |
|---|---|---|---|
| A11 | 21.818 | 2.136 | 30.00 |
| A12 | 21.817 | 2.136 | 30.00 |
| A13 | 21.816 | 2.136 | 30.00 |
| A21 | 21.821 | 2.137 | 30.00 |
| A22 | 21.820 | 2.137 | 30.00 |
| A23 | 21.820 | 2.137 | 30.00 |
| A31 | 21.818 | 2.136 | 30.00 |
| A32 | 21.817 | 2.136 | 30.00 |
| A33 | 21.816 | 2.136 | 30.00 |

**Uniformidad hidraulica de presion (relacion Pmin/Pmax) = 0.9998.** Solo indica que las presiones de los 9 aspersores son casi iguales; NO es uniformidad de riego (patron de mojado, radio, presion minima requerida, relacion apertura-caudal y efecto de la altura de 1 m sobre el cajon son desconocidos). La uniformidad de riego real queda PENDIENTE DE VALIDACION EXPERIMENTAL.

## Escenarios

| Escenario | Descripcion | EPANET 2.2 | Q total (L/min) | P min-max (m, prelim.) | Pmin/Pmax | H bomba (m) | V principal (m/s) | YF (Hz) | Margen vs 6 L/min | Viable |
|---|---|---|---|---|---|---|---|---|---|---|
| Q20 | 20 L/h por aspersor impuesto (x9 = 3.00 L/min); apertura fisica desconocida | OK | 3.000 | 45.25-45.25 | 0.9999 | 45.96 | 0.307 | 22.5 | 50 % | SI |
| Q25 | 25 L/h por aspersor impuesto (x9 = 3.75 L/min); apertura fisica desconocida | OK | 3.750 | 33.55-33.56 | 0.9999 | 34.47 | 0.384 | 28.1 | 38 % | SI |
| Q30 | 30 L/h por aspersor impuesto (x9 = 4.50 L/min); apertura fisica desconocida | OK | 4.500 | 21.82-21.82 | 0.9998 | 22.98 | 0.461 | 33.7 | 25 % | SI |
| Q35 | 35 L/h por aspersor impuesto (x9 = 5.25 L/min); apertura fisica desconocida | OK | 5.250 | 10.03-10.04 | 0.9993 | 11.49 | 0.537 | 39.4 | 13 % | SI |
| Q40 | 40 L/h por aspersor impuesto (x9 = 6.00 L/min); apertura fisica desconocida | ERROR / WARNING: Negative pressures at 0:00:00 hrs. | 6.000 | -1.79--1.78 | 0.0000 | 0.00 | 0.614 | 45.0 | 0 % | NO |
| Q70 | 70 L/h por aspersor impuesto (x9 = 10.50 L/min); apertura fisica desconocida | ERROR: WARNING: Negative pressures at 0:00:00 hrs.; WARNING: Pump PU1 open but exceeds maximum flow at 0:00:00 hrs.; EPyT: list | - | - | - | - | - | - | - | NO |
| DH10 | Manguera DI 10 mm (NO medido) | OK | 4.500 | 21.80-21.81 | 0.9997 | 22.98 | 0.461 | 33.7 | 25 % | SI |
| DH12 | Manguera DI 12 mm (NO medido) | OK | 4.500 | 21.82-21.82 | 0.9998 | 22.98 | 0.461 | 33.7 | 25 % | SI |
| DH14 | Manguera DI 14 mm (NO medido) | OK | 4.500 | 21.82-21.83 | 0.9998 | 22.98 | 0.461 | 33.7 | 25 % | SI |
| CURVA_x0.25 | Curva provisional con alturas x0.25 | OK | 4.500 | 4.58-4.59 | 0.9988 | 5.75 | 0.461 | 33.7 | 25 % | SI |
| CURVA_x0.40 | Curva provisional con alturas x0.40 | OK | 4.500 | 8.03-8.03 | 0.9993 | 9.19 | 0.461 | 33.7 | 25 % | SI |
| CURVA_x0.50 | Curva provisional con alturas x0.50 | OK | 4.500 | 10.33-10.33 | 0.9995 | 11.49 | 0.461 | 33.7 | 25 % | SI |
| CURVA_x0.75 | Curva provisional con alturas x0.75 | OK | 4.500 | 16.07-16.08 | 0.9997 | 17.24 | 0.461 | 33.7 | 25 % | SI |
| HW150 | Hazen-Williams C=150 (comparacion) | OK | 4.500 | 21.85-21.86 | 0.9998 | 22.98 | 0.461 | 33.8 | 25 % | SI |
| TINACO_MIN | Tinaco casi vacio (agua +0.30 m) | OK | 4.500 | 20.93-20.93 | 0.9997 | 22.98 | 0.461 | 33.7 | 25 % | SI |
| K_ALTOS | K estimados x2 y Kv EV = 1 | OK | 4.500 | 20.75-20.75 | 0.9997 | 22.98 | 0.461 | 33.7 | 25 % | SI |
| K_BAJOS | K estimados x0.5 y Kv EV = 6 | OK | 4.500 | 22.08-22.09 | 0.9998 | 22.98 | 0.461 | 33.7 | 25 % | SI |
| GEO_A2 | Geometria A2 (variante): Subida vertical + desvio de laterales exteriores con la manguera | OK | 4.500 | 21.82-21.82 | 0.9998 | 22.98 | 0.461 | 33.7 | 25 % | SI |
| GEO_B | Geometria B (ALTERNATIVA DE CONTINGENCIA): Subida a 45 deg (2 codos 45) + brazos Tuboplus con codos 90 | OK | 4.500 | 21.87-21.87 | 0.9998 | 22.98 | 0.461 | 33.7 | 25 % | SI |
| GEO_B2 | Geometria B2 (contingencia extrema): Subida a 45 deg + desvio exterior con la manguera | OK | 4.500 | 21.87-21.87 | 0.9998 | 22.98 | 0.461 | 33.7 | 25 % | SI |
