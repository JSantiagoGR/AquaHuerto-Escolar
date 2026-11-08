# AquaHuerto Escolar — Reporte técnico verificado para la exposición (2026-10-22)

Leyenda de estado: **DISEÑADO** · **IMPLEMENTADO** · **PROBADO (SIM)** · **PROBADO (FÍSICO)** · **VALIDADO** · **PENDIENTE** · **NO VERIFICADO**.
Ningún secreto se reproduce aquí. Fuentes con ruta en la sección S. No se modificó firmware, Pi, ESP32, flujos ni dashboards durante esta revisión.

**Límite de esta revisión:** el 2026-10-22 la laptop estaba en la red `RED_DE_CASA_5`, sin acceso a la Raspberry Pi. Por eso los datos de producción llegan hasta la última lectura directa de la Pi, el **2026-10-21 ~15:50**. Lo que pasó la noche del 21 al 22 (primer riego automático de 18:00–20:00) es **NO VERIFICADO**.

---

## A. RESUMEN EJECUTIVO

**Qué es.** AquaHuerto Escolar es un sistema de riego automatizado para **un solo cajón de cultivo**. Está instalado en la Escuela Primaria Federal Belisario Domínguez, en Chihuahua (28.659830, −106.074051; coordenadas configuradas en el firmware y en el servidor).

**Ruta del agua.** Tinaco → bomba de diafragma de 12 V → caudalímetro YF‑S201 → **una** electroválvula NC de 12 V → línea de distribución → **3 líneas × 3 microaspersores** (EPANET v3).

**Energía.** Batería SLA de 12 V (Mighty Max ML9‑12, 9 Ah), cargada por un panel **Firstech FE‑50WP** de 50 W a través de un controlador PWM genérico con LCD y USB.

**Qué construimos y está funcionando (probado físicamente, 12–21 oct 2026):**

- **Firmware propio en C (ESP‑IDF 6.0.2)**, `riego-2.0.0`.
  - 25 módulos y ~7 900 líneas de C.
  - Corre en un ESP32 que controla bomba y válvula con un módulo de 2 relevadores.
  - Mide los litros con el contador de pulsos por hardware (PCNT).
  - Lee el EC‑5 (humedad volumétrica del suelo), el ultrasónico Parallax PING))) (nivel del tinaco) y el DHT22 (temperatura y humedad relativa del aire).
  - Consulta Open‑Meteo por HTTPS.
  - Decide en tres modos: MANUAL, AUTOMÁTICO e IA.
- **Raspberry Pi del laboratorio (raspberrypi.local).** Corre una **instancia propia aislada**:
  - Node‑RED 5.0.8 en el puerto **1881**, con **FlowFuse Dashboard 2.0** de 10 páginas.
  - Broker Mosquitto propio en el puerto **1884**, con usuarios y ACL.
  - Base de datos **SQLite** (`riego_final.db`) con el historial completo.
  - No toca el Node‑RED (1880) ni el Mosquitto (1883) del profesor ni de los demás equipos.
- **Comunicación por MQTT** con JSON, confirmación (ACK) de cada comando, rechazo de comandos duplicados, retenidos o antiguos, y mensaje de última voluntad (LWT).

**Qué lo hace inteligente:**

1. **Umbrales agronómicos.** Salen de FAO‑56 (Kc, fracción p) y de la capacidad de campo y el punto de marchitez del sustrato real. Cambian por cultivo y etapa (10 cultivos base más personalizados).
2. **Riego por dosis con infiltración.** Riega 1.5 L, espera 15 min, vuelve a medir y repite, en lugar de regar sin parar.
3. **Modelo predictivo dentro del ESP32.** Dos regresiones lineales que aprenden en línea con mínimos cuadrados recursivos (RLS):
   - **Modelo A:** cuánto sube la humedad por litro.
   - **Modelo B:** cuánto se seca el suelo por hora, usando VPD, ET0 de Open‑Meteo, Kc y la hora del día.

   El modo IA las usa para regar la cantidad mínima que mantiene la humedad hasta el siguiente horario. También pospone por lluvia **solo si la lluvia prevista cubre lo que le falta a la tierra**.
4. **Detección de aumentos de humedad sin bomba**, clasificados como lluvia, riego externo o error del sensor.
5. **Balance de agua diario** (ETc = Kc × ET0) en el dashboard.

**Probado físicamente:**

- **Riegos reales** por volumen: 2.05 L en TARGET a ~3 L/min el 21‑oct, y STOP inmediato a 0.62 L.
- **Lecturas reales:**
  - Suelo: 21–34 %VWC.
  - Tinaco: 30.4 cm, 82 %.
  - Aire: 25–28 °C.
- **Autodiagnóstico en placa: 50/50.**
- **Pruebas de integración: 30/30** (simulador).
- **Prueba de campo: 28/28** (con la bomba sin 12 V).
- **Reconexiones sin intervención.** El modo se conserva tras un reinicio y nunca riega al arrancar.

**Qué falta (lo más importante):**

- **Etapa de potencia.** La bomba de 6 A está en un relevador SRD de 3 A inductivos. Faltan los diodos, los fusibles y el capacitor. Hubo reinicios al conmutar la bomba.
- **Caudalímetro sin calibrar** con recipiente: usa 450 p/L de fábrica.
- **Señal Wi‑Fi débil** en el gabinete: −78 a −94 dBm.
- **La IA sigue en APRENDIZAJE**: 1 riego aprendido. Necesita ≥ 6 riegos y 48 h de secado.
- **Capacidad de campo y punto de marchitez estimados**, no medidos.
- **Validación agronómica** del EC‑5 en este sustrato.
- **Energía:** no hay mediciones de autonomía, consumo ni panel en operación.
- **EPANET** es un modelo con supuestos, no está validado contra mediciones.

---

## B. INVENTARIO REAL DE COMPONENTES

| Sistema | Componente | Marca | Modelo | Especificaciones | Función | Cant. | Estado | Fuente |
|---|---|---|---|---|---|---|---|---|
| Control | ESP32 en servicio (desde 21‑oct) | Espressif | ESP32‑D0WD‑V3 rev 3.1, 4 MB; MAC xx:xx:xx:xx:xx:xx. **Módulo y antena NO VERIFICADOS** | 240 MHz, puente CP210x (COM8) | Control, sensores, MQTT, IA | 1 | PROBADO (FÍSICO) | sesión 21‑oct; `backups/esp32_d0ef7613f30c_flash_original/` |
| Control | ESP32 original (fuera de servicio) | Espressif | **ESP32‑WROOM‑32U** (antena externa u.FL→SMA), D0WD‑V3 rev 3.1; MAC xx:xx:xx:xx:xx:xx | DevKit 38 pines tipo DevKitC | Era el principal; micro‑USB dañado; debe estar APAGADO | 1 | Retirado | Prueba_01 `COMPONENTES.md` |
| Control | ESP32 de pruebas en casa | Espressif | `esp32_01` (MAC NO VERIFICADA aquí) | — | Desarrollo con broker de la laptop | 1 | Banco de pruebas | `docs/PRUEBAS.md` |
| Control | Placa de expansión | Genérica (morada) | 38 pines | Jack DC 6.5–16 V, filas S/V/G | Soporte y alimentación | 1 | IMPLEMENTADO | `COMPONENTES.md` §1.2 |
| Control | Adaptador USB‑serie | Genérico | CH340G | — | Carga de firmware cuando el micro‑USB falló (20‑oct) | 1 | PROBADO | sesión 20‑oct |
| Potencia | Módulo de 2 relevadores | Genérico, relevadores Songle | SRD‑05VDC‑SL‑C, optoacoplado | Bobina 5 V/71 mA; contactos 10 A/125 VAC, **inductiva 3 A/28 VDC** | IN1 = bomba (GPIO26), IN2 = válvula (GPIO27), activo en BAJO | 1 | PROBADO (FÍSICO); **no apto para la bomba** | `COMPONENTES.md` §1.4 |
| Hidráulica | Bomba | GOOD PUMPS "Pro Edition" | **Modelo de fábrica no impreso**; SKU D2‑BXSB / tienda PKAV94551 | 12 V (9–14.4), 6 A, 72 W, 6 L/min máx, presostato 0.9 MPa (corte) | Impulsar el agua | 1 | PROBADO (FÍSICO) | `COMPONENTES.md` §1.5; EPANET 3 |
| Hidráulica | Electroválvula NC | KING SHENG | Sin modelo; "DC12V 有压力常闭型" (pilotada, requiere presión) | 12 VDC, rosca ½", corriente NO medida | Abrir/cerrar la línea | 1 | PROBADO (FÍSICO) | `COMPONENTES.md` §1.6 |
| Medición | Caudalímetro | — | YF‑S201 | 1–30 L/min, ≤ 1.75 MPa, Hall, 5–18 V | Pulsos → litros (GPIO19, PCNT) | 1 | PROBADO; **sin calibración física** | firmware `flow_sensor.c` |
| Sensor | Humedad del suelo | Decagon / METER | ECH2O **EC‑5** Rev 04.00 | 2.5–3.6 V, 10 mA, salida analógica | %VWC (excitación GPIO25, señal GPIO34) | 1 | PROBADO (FÍSICO) | sesión 21‑oct |
| Sensor | Nivel del tinaco | Parallax | **PING))) #28015 REV B** | 5 V, 2 cm–3 m, un solo pin SIG | Distancia → % (GPIO18, divisor 1 k/2 k) | 1 | PROBADO (FÍSICO) | fotos 13‑oct; `tank_level.c` |
| Sensor | Ambiente | Aosong (PROBABLE) | DHT22 / AM2302 | 3.3 V, bit‑bang | T y HR del aire (GPIO4) | 1 | PROBADO (FÍSICO) | `COMPONENTES.md` §1.11 |
| Energía | Panel solar | Firstech Energy | **FE‑50WP** (rotulado "Equipo Galaviz") | 50 W, Vmp 17.4 V, Imp 2.87 A, Voc 21.6 V, Isc 3.16 A, 620×680×25 mm, 5 kg | Generación | 1 | Identificado; **instalación en techo NO VERIFICADA** | `COMPONENTES.md` §1.15 |
| Energía | Batería | Mighty Max | **ML9‑12** (en la foto del gabinete del 13‑oct la etiqueta visible no muestra el modelo) | 12 V 9 Ah SLA; carga < 2.7 A; no bajar de 10.5 V | Almacenamiento | 1 | En uso | `COMPONENTES.md` §1.14; foto `ef5b9ed0` |
| Energía | Controlador de carga | Genérico | "Solar Charge Controller" PWM con LCD, 2 USB | Corriente nominal NO identificada | Panel → batería → carga | 1 | En uso | foto `ef5b9ed0` |
| Gabinete | Caja de plástico blanca con tapa | NO VERIFICADO | — | **IP65 = meta de diseño, no certificada** | Electrónica | 1 | IMPLEMENTADO | foto `ef5b9ed0` |
| Servidor | Raspberry Pi del laboratorio | Raspberry Pi | NO VERIFICADO (Debian 13 aarch64, Node 22) | raspberrypi.local, Wi‑Fi `RouterHuerto1` | Node‑RED 1881 + Mosquitto 1884 + SQLite | 1 | En producción | `migration_raspberry_pi/` |
| Hidráulica | Tubería | — | Tuboplus/PPR verde 20 mm (½") | Cruz Tuboplus 200082 | Línea principal | — | Ver G | EPANET 3 `BOM_hidraulico.csv` |
| Hidráulica | Microaspersores | **NO VERIFICADO** (sin foto ni marca) | — | Apertura regulable; caudal real desconocido | Distribución | 9 (diseño) | DISEÑADO / NO VERIFICADO instalado | EPANET 3 |
| Sustrato | Mezcla del cajón | Premier, Eco Sustrato | Peat Moss 107 L comprimido; Perlita 10 L × 2; tierra negra 40 kg genérica | ~74/19/7 % en volumen | Medio de cultivo | — | Instalado (21‑oct) | fotos 21‑oct |
| PCB | Placa de potencia en Proteus | — | `RIEGO_ESP32_PCB.pdsprj` (10 × 10 cm, Q1–Q3, D1–D3) | Diseño para 1 bomba + 2 válvulas | Etapa de potencia | — | **DISEÑADO; no se ve instalada** (el gabinete usa el módulo de relevadores) | `C:\TEC\SEMESTRE 5\ceci\RIEGO_ESP32_PCB\` |

---

## C. CRONOLOGÍA (con evidencia)

| Fecha | Hito | Evidencia |
|---|---|---|
| Ago–sep 2026 (NO VERIFICADO exacto) | Diseño Mecatrónico: definición, QFD, árbol de funciones, AMEF, avances y reporte integrador (bases PTR, arquitectura B 4.65, IP65 meta) | `C:\TEC\SEMESTRE 5\Diseño mecatrónico\*.docx/pdf` |
| 20–23 sep | PCB de potencia en Proteus (versiones 01–09, la "07_SCHEMATIC_FINAL" y "09B_PLACEMENT") | `ceci\RIEGO_ESP32_PCB\BACKUPS\` |
| Sep (NO VERIFICADO exacto) | Act. 2.2: calibración del EC‑5 (360/420/630/870 mV, R² 0.94494). Act. 2.3: YF‑S201 (1–5 L, 450 p/L) | `Automatización industrial\asesor\Actividad 2.2/2.3` |
| 30 sep | Fotos de relevadores, ESP32 y YF‑S201 en banco | uploads `fa99f59b` |
| 3 oct | EPANET v3: cruz + 3 × 3 aspersores, subida vertical | `Reto\EPANET\3\PROJECT_STATE.md` |
| 9 oct | **Prueba 01 física**: bomba 10 s (4 ciclos), la válvula corta el agua, relevadores activos en BAJO. Prueba 02: 1 L en 19.7 s, 455 pulsos (~1011 mL **calculados**). Prueba 03: PING))) 94.9 cm, DHT22 21.5 °C / 53.7 %HR | `Reto\ESP32\Prueba_01_Bomba_Electrovalvula\` |
| 11 oct | Práctica 4 MQTT (topics `equipo2/*`, dashboard `/ui`). `Proyecto_Final_v1` (21 módulos, QEMU 33/33). `Pruebas_Casa_ESP32_v1`: firmware riego‑2.0.0, Dashboard 2.0, lógica 47/47, SELFTEST 49/49, integración 29/29, ESP32 real por red 15/15 | `Downloads\Practica4_MQTT\`; `Proyecto_Final_v1\PRUEBAS_REALIZADAS.md`; `docs\PRUEBAS.md` |
| 12 oct | Migración a la Raspberry Pi: instancia propia 1881/1884. **Primer riego real en el huerto**: 0.773 L en 20.5 s (~2.3 L/min, terminado con STOP). Cama 1 m² × 37.5 cm y perfil del frijol | `docs\PRUEBAS.md`; `docs\ESTADO_FINAL.md` |
| 13 oct | Prueba de campo Pi + ESP32 **28/28** (12 V desconectado → corte por NO_FLOW). Fotos del tinaco, el gabinete y el PING))) montado | `tests\resultados\campo_pi_20261013_1000.txt`; uploads `b5ae748a` |
| 14 oct | EC‑5 leyendo tras recablear el jack; ultrasónico instalado; riegos TARGET de 2.80 y 1.40 L (~1.7 L/min); persistencia del modo; aviso de FALLA; gráficas de Manual e Historial; corrección del contador diario | `docs\ESTADO_FINAL.md` |
| 19–20 oct | Lluvia por balance (firmware) y tarjeta "Balance de agua" (dashboard). Carga de firmware con adaptador CH340G | `docs\ESTADO_FINAL.md` §2026‑10‑19 |
| 21 oct | **ESP32 de reemplazo** (…xx:xx:xx) con la configuración del original. Wi‑Fi sin ahorro de energía; separación válvula↔bomba de 1.5 s; mezcla real → FC 48 / WP 16; **prueba final con agua 14/15** (1 falso fallo del script); riego manual solo en MANUAL y riego extra autorizado; SELFTEST 50/50; queda en **AUTOMÁTICO** | `tests\resultados\prueba_final_20261021_1443.txt`; `docs\ESTADO_FINAL.md` |

---

## D. INFORMACIÓN NUEVA (no estaba en el contexto)

1. **Firmware real:** `C:\ESP32_Riego_Automatico\Pruebas_Casa_ESP32_v1\firmware\main\`.
   - `riego-2.0.0`, ESP‑IDF **6.0.2**, 25 archivos `.c`, ~7 916 líneas.
   - Tareas FreeRTOS:
     - `control` (núcleo 0, con watchdog);
     - `sensors` (núcleo 1);
     - `clima` (núcleo 1);
     - `console` (núcleo 0).
   - **Supervisor de seguridad independiente** (`safety.c`):
     - temporizador con tope absoluto de bomba de **5.5 min**, no configurable;
     - corte si la tarea de control deja de responder **3 s**.
   - Estados: INIT, IDLE, MONITORING, MANUAL_WATERING, AUTO_WATERING, INFILTRATION_WAIT, FAULT.
2. **Hay dos ESP32 en la historia del huerto, pero solo uno a la vez.**
   - El original (WROOM‑32U, …xx:xx:xx) quedó fuera por el micro‑USB dañado.
   - El de reemplazo (…xx:xx:xx) opera desde el 21‑oct con la misma identidad `esp32_principal`.
   - Un tercer ESP32 (`esp32_01`) es solo de pruebas en casa.
   - **No existe arquitectura de dos ESP32 cooperando.**
3. **La Pi es compartida.** El trabajo vive solo en `~/equipo2_proyecto`:
   - Node‑RED 5.0.8 en 1881 y Mosquitto en 1884.
   - Arranque automático con `@reboot`.
   - Dashboard sin contraseña en la red local; el editor sí está protegido.
   - `riego_final.db` en SQLite, con respaldo diario `VACUUM INTO` a las 03:00.
4. **Topics definitivos:** `huerto/final/esp32_principal/{status, telemetry, state, config, decision, event, alarm, ia, weather, diag, telemetry_buffer, ack, command}`. Los `equipo2/*` eran de la Práctica 4.
5. **Tinaco medido** (fotos del 13‑oct y calibración):
   - Circunferencia 2.83 m (Ø ≈ 0.90 m); ~6.2–6.4 L por cm.
   - Sensor a 127 cm del piso; vacío = 117 cm y lleno = 12 cm del sensor.
   - **Capacidad útil estimada ≈ 650 L.** No cuadra con los 450 L nominales del diseño, y el modelo del tinaco es **NO VERIFICADO**.
   - El 21‑oct: 30.4 cm → 82 % ≈ 535 L.
6. **Cajón real 1.00 × 1.00 m, 37.5 cm de sustrato.** Lo midió el equipo y es el que usan EPANET v3 y el firmware: 1 punto de %VWC = 3.75 L. Los 1.20 × 1.20 m corresponden a la **base metálica de diseño**, no al interior del cajón (ver E).
7. **Sustrato real:**
   - Peat moss Premier (paca de 107 L comprimida, ~215 L suelta), 40 kg de tierra negra (~55 L) y 2 × 10 L de perlita.
   - Proporción ≈ 74/19/7 % en volumen.
   - **FC ≈ 48 %, WP ≈ 16 %** (estimados por mezcla).
   - Umbrales del frijol en establecimiento: emergencia 23.6, mínima 30, **óptima 39**, reserva 44.8, máxima 48 %VWC.
8. **La conversión del EC‑5 en el firmware no es la recta directa.**
   - Usa la recta de la Act. 2.2 para obtener `s` (en %).
   - Luego la convierte a humedad volumétrica estándar con **θ = s/(1−s)** (`ec5_scale = 1`), porque la práctica definió %VWC = V_agua/(V_tierra + V_agua).
   - El ADC usa **atenuación de 12 dB** (no 6 dB).
   - Intervalo calibrado 360–870 mV; fuera de él la lectura sale "OK_FUERA_DE_CALIBRACION".
9. **Cableado final del EC‑5**, verificado el 21‑oct con mediciones (detalle en I):
   - Blanco → GPIO25, rojo → GPIO34, sin forro → GND.
   - En el jack: punta → 25, anillo → 34, manga → GND.
10. **Protecciones vigentes** (configuración v526 del 21‑oct): ver Q/§33. Han cambiado varias respecto al contexto.
11. **Regla nueva (21‑oct):** el riego manual solo se ejecuta en MANUAL.
    - Desde el dashboard se cambia automáticamente y luego se ofrece regresar al modo anterior.
    - El máximo diario también aplica al manual, salvo autorización con el botón **PERMITIR RIEGO EXTRA**, válida para un solo riego.
12. **Lluvia por balance (modo IA):** pospone solo si `0.8 × mm_previstos_6h × ganancia ≥ (objetivo − humedad)`. Las emergencias nunca se posponen y AUTOMÁTICO no usa la lluvia.
13. **Hallazgo de seguridad:** `Downloads\Practica4_MQTT\README.md` contiene **en texto plano** la contraseña del Wi‑Fi `RouterHuerto1`. Se recomienda borrarla antes de compartir esa carpeta. No se modificó.

---

## E. INFORMACIÓN CORREGIDA O DESACTUALIZADA

| Dato anterior | Dato actual | Evidencia | Explicación |
|---|---|---|---|
| Cajón 1.20 × 1.20 m | **Cajón 1.00 × 1.00 m × 0.40 m** (37.5 cm de sustrato); 1.20 × 1.20 = base metálica de diseño | EPANET 3 `PROJECT_STATE.md` ("cajón de 1 × 1 m", base 0.12 + cajón 0.40); firmware/dashboard (cama 1 m² × 37.5 cm) | Lo mide el equipo; el diseño estructural usaba otra referencia |
| Tinaco ~450 L | **Útil ≈ 650 L estimado** por medidas (Ø 0.90 m, 105 cm útiles); modelo NO VERIFICADO | Fotos y calibración (117/12 cm) | 450 L era un supuesto de diseño |
| 2–5 L → 920/1390/1850/2315 pulsos sugieren 460–463 p/L | **No sirven para calibrar.** Los volúmenes se **calcularon** con V = N/450 y el programa cortaba al llegar a N×450; los pulsos extra son **sobrepaso** tras la orden de apagado. Error calculado promedio 3.55 % (6.89 % en 1 L). **No hubo recipiente graduado** | Act. 2.3 (texto) | El factor real sigue sin medirse; el firmware usa **450 p/L** (`flow_calibrated = false`) |
| "1000 mL → ~980 mL" | **NO VERIFICADO** en archivos | La tabla de resultados de la Práctica 4 no se pudo extraer con números; `prueba02_1litro` registra 455 pulsos → 1011 mL **calculados** | No presentarlo como medición |
| EC‑5 a 6 dB | **12 dB** en el firmware final | `soil_sensor.c` | — |
| Bomba máx. 90 s | **pump_max_s = 180 s** (+ tope duro 5.5 min) | config v521/v526; `safety.c` | Se subió porque el caudal real era menor |
| 15 L por día | **30 L por día** desde el 21‑oct (el perfil de la cama ahora envía 8 puntos/día) | v526; `umbrales.js` | Recuperar la humedad del sustrato seco |
| 7.5 L por riego | **Sigue vigente** (1.5 L × 5 dosis) | v526 | — |
| Tinaco bajo bloquea el riego | **Ya no bloquea: solo avisa** (TANK_LOW). La protección contra funcionamiento en seco es **NO_FLOW = 45 s sin pulsos** + tope de bomba | `irrigation_logic.c` (decisión del equipo, 14‑oct) | ⚠️ Esto contradice la recomendación del AMEF de "bloqueo por nivel": decisión consciente del equipo, mencionarla así |
| Lluvia en AUTOMÁTICO | **Solo en modo IA** y por balance | `irrigation_logic.c` | — |
| Válvula → bomba 300 ms | **1.5 s** (y bomba OFF → válvula 1.5 s) | v526, sesión 21‑oct | Separar los arranques inductivos |
| Arquitectura de dos ESP32 (concepto B 4.65) | **Un ESP32 en el huerto + Raspberry Pi** como servidor; el concepto de 2 nodos quedó solo como diseño | Firmware y despliegue | — |
| Dashboard `/ui` (Práctica 4) | **FlowFuse Dashboard 2.0** en `http://raspberrypi.local:1881/dashboard`, 10 páginas; el `/ui` de la práctica era una pestaña en el Node‑RED del profesor | `generar_flows.py`; Pi | — |
| Topics `equipo2/*`, broker 1883 | `huerto/final/esp32_principal/*`, broker propio **1884** con usuarios y ACL | `CONFIGURACION_MQTT.md` | — |
| GPIO de prácticas (flujo GPIO4, bomba GPIO2) | **Bomba 26, válvula 27, flujo 19, PING 18, DHT 4, EC‑5 25/34** | `board.h` | Las prácticas usaban otro cableado |
| Pulsos/litro 480 (Práctica 4) | **450** | `config v526` | — |
| EPANET v3 "66 OK, 1 aviso, 43 enlaces" | **71 OK, 3 avisos, 0 fallas** (presentación 69/3/0); **43 nodos (uniones), 43 enlaces (42 tuberías + 1 bomba)** | `EPANET\3\PROJECT_STATE.md`, conteo del `.inp` | Las cifras del contexto eran de una versión intermedia |
| Ruta a 45° con 3.691 m de Tuboplus | El diseño **principal es la subida VERTICAL (escenario A, 5.148 m estimados)**; la de 45° (B: 4.332 m; B2 con desvío por manguera: **3.718 m**) es **solo contingencia** | `EPANET\3\PROJECT_STATE.md` | Ninguna se confirmó con mediciones; la construida es NO VERIFICADA |
| Microaspersores 70 L/h | El modelo usa **30 L/h impuesto**; 40 y 70 L/h salen **no viables** (presión negativa; 9 × 70 L/h > 6 L/min) | EPANET 3 | — |
| Panel a 30° | Dato reciente 28° al sur: **NO VERIFICADO** en archivos (no hay foto de la instalación en el techo) | — | Mantener como dato del equipo |

---

## F. CONSTRUCCIÓN Y SISTEMA FÍSICO

- **Bases metálicas (Diseño Mecatrónico, solo DISEÑO/cálculo simplificado):**
  - **Cajón:** 1200 × 1200 mm, PTR 40×40×3, 6 patas, 1500 kg de diseño, ~94 MPa y ~3.1 mm de deflexión.
  - **Tinaco:** 1200 × 1200 mm, PTR 50×50×3, 5 patas, 8 diagonales, placa de 4 mm, 850 kg. Resultados: travesaño ~32 MPa / 0.8 mm; larguero ~75 MPa / 2.3 mm; placa ~24 MPa / 0.6 mm.
  - **Soporte del panel:** 30°, PTR 25×25×2.
  - Fuente: `Reporte Integrador Final (Equipo).docx`.
  - **No se encontraron archivos de SolidWorks** (.SLDPRT/.SLDASM/.SLDDRW) en la computadora, ni fotos de fabricación o soldadura, ni pruebas de carga. Son cálculos, no certificaciones.
- **Evidencia física (fotos 13‑oct y 21‑oct):**
  - Cajón de madera con malla antimaleza y postes.
  - Tinaco negro sobre base metálica, con salida de ½" y válvula de esfera azul.
  - PING))) en caja acrílica sobre la tapa del tinaco.
  - Gabinete plástico blanco con ESP32 en placa de expansión, mini protoboard, módulo de 2 relevadores, controlador PWM, conectores WAGO 221 y batería SLA.
  - Se ve una estructura metálica superior (foto `8bbd4925`); su función es NO VERIFICADA.
- **Anticorrosión, puesta a tierra y aislamiento del gabinete:** NO VERIFICADO.
- **IP65:** meta de diseño, no certificada.

---

## G. SISTEMA HIDRÁULICO

**Recorrido de diseño (EPANET v3, escenario A):**

1. Tinaco → salida existente de ½": válvula de esfera, check y T, más una bajada.
2. Codo 90° → bomba → YF‑S201 → electroválvula NC.
3. Línea principal → subida **vertical** hasta z = 1.52 m (1.00 m sobre el cajón).
4. **Cruz** Tuboplus → 3 mangueras negras paralelas, con **3 aspersores por línea (9)** en cuadrícula 0.17/0.50/0.83 m, y un tapón al final.
5. Sin filtro.

**Resultados EPANET (SIMULACIÓN, preliminares):**

| Magnitud | Valor |
|---|---|
| Caudal impuesto | 30 L/h × 9 = **4.5 L/min** |
| Presión en los aspersores | ~21.8 m (~2.14 bar), con una **curva de bomba provisional** (sensibilidad 4.6–16.1 m) |
| Uniformidad de presión | 0.9998. **No es uniformidad de riego.** |
| Velocidad principal | 0.461 m/s |
| Pérdidas | 0.29 m por fricción + 0.81 m por accesorios |
| Viabilidad | 40 y 70 L/h por aspersor **no son viables** |

- **Validación del modelo:** 71 OK, 3 avisos, 0 fallas. "Run was successful" en EPANET 2.2 GUI, runepanet, WNTR, EPyT y MCP.
- **Versiones anteriores:**
  - v1: 8 nodos; variante de 24 goteros con 31 nodos.
  - v2: 25 nodos y 4 emisores.
- **Pendientes de medir:**
  - M0–M12 (todas ESTIMADAS);
  - la rosca de la bomba (~3/8", NPT o BSP sin confirmar);
  - el diámetro interior de la manguera (12 mm estimado);
  - la curva Q‑H real;
  - el ciclado del presostato;
  - la marca y la curva de los aspersores;
  - la uniformidad con recipientes.

**Caudal REAL medido por el YF‑S201** (no por recipiente):

| Fecha | Caudal |
|---|---|
| 9‑oct | 3.5–4.5 L/min tras ~4 s de cebado |
| 12‑oct | ~2.3 L/min |
| 14‑oct | ~1.7 L/min |
| 21‑oct | 1.84–1.98 L/min por la mañana; **~2.9–3.0 L/min** en la prueba final |

La variación no tiene causa demostrada: puede ser el voltaje de la batería, la apertura de los aspersores o el nivel del tinaco. **No hay mediciones eléctricas** que la expliquen (la observación de 2.0 → 1.2 L/min queda sin comprobar).

**Lo construido (escenario A, B o B2):** NO VERIFICADO. No hay registro de medidas finales.

---

## H. SISTEMA ELÉCTRICO Y FOTOVOLTAICO

**Topología:** Panel FE‑50WP → controlador PWM → batería ML9‑12 → cargas.

**Cómo está conectado hoy:**

- **Bomba:** se conecta con el contacto COM→NO del relevador K1 del módulo SRD (configuración de la Prueba 01). En la foto del gabinete no se ve un relevador automotriz.
- **Electroválvula:** en K2.
- **ESP32:** alimentado por la placa de expansión (jack de 6.5–16 V). Antes se alimentó por USB.
- **Cables y conectores:** cable de 18 AWG (ARGOS 0.824 mm²) y conectores de palanca.

**Riesgos identificados (NO resueltos):**

1. **El SRD soporta 3 A inductivos y la bomba consume 6 A.** La corriente de arranque es desconocida, y no se encontró relevador automotriz, MOSFET ni la PCB instalada.
2. **Diodos de rueda libre y fusibles:** no instalados según el equipo (21‑oct).
3. **Reinicios del ESP32 al conmutar la bomba:**
   - Hubo un evento REBOOT en un riego a las 13:55 del 21‑oct.
   - En el ESP32 anterior, reset por watchdog al detener la bomba.
   - Mitigación por software: separación de 1.5 s entre válvula y bomba y detector de caída de voltaje en el nivel más bajo.
   - **Corrección pendiente de hardware:** diodos (1N4007 o 1N5819), capacitor de 470–1000 µF en VIN y, recomendado, relevador automotriz de 30/40 A con fusible de 10 A.
4. **Autonomía, consumo, radiación y margen energético ≥ 20 % (H8):** sin cálculos ni mediciones encontradas en los archivos. NO VERIFICADO.

**PCB en Proteus:** RIEGO_ESP32_PCB (Q1 bomba, Q2/Q3 para 2 válvulas, D1–D3), con respaldos del 20 al 23 de septiembre. Es **diseño de la etapa con 2 válvulas**. No hay evidencia de fabricación o instalación.

---

## I. SENSORES Y CALIBRACIONES

**Pinout final** (`firmware/main/board.h`):

| Señal | GPIO |
|---|---|
| Bomba | 26 |
| Válvula | 27 |
| YF‑S201 | 19 (PCNT, pull‑up, filtro 10 µs) |
| PING))) | 18 (divisor 1 kΩ/2 kΩ hacia 3.3 V) |
| DHT22 | 4 |
| EC‑5 excitación | 25 |
| EC‑5 señal | 34 (ADC1_CH6) |

**EC‑5:**

- **Calibración** (Act. 2.2): 600 mL de tierra con 0/105/257/490 mL de agua → 360/420/630/870 mV.
  - Recta: %VWC_s = 0.08146067·mV − 23.932584.
  - R² = **0.94494**.
  - Resolución teórica de 0.0219 %VWC por cuenta (rango de 1.1 V).
- **En el firmware:** θ = s/(1−s). La excitación es un pulso de 10 ms desde GPIO25 y la lectura se toma cada 300 s (5 min). Se acorta con calor (> 30 °C) o aire seco (< 30 %HR).
- **Resultados (21‑oct, con el monitor de diagnóstico):**
  - Al aire: ~375 mV.
  - En el sustrato: 515–600 mV.
  - En la Pi: 25.9 %VWC (546 mV), estado OK.
- **Fallas resueltas:**
  - Señal en un pin equivocado y GPIO25 desconectado.
  - Empalmes húmedos que pasaban la alimentación a la señal (3.1 V).
  - Jack mal insertado.

  Al conectarlo a 3V3 directo, la señal se iba a 3.1 V, el ESP32 se reiniciaba y los relevadores prendían y apagaban rápido.
- **Pendiente:** validación agronómica en este sustrato (peat moss alto).

**PING))):**

- Distancia = t·c/2, con c = 331.3 + 0.606·T (corregida por temperatura).
- Se toman 5 pulsos separados 60 ms y se usa la mediana:
  - si la dispersión es > 5 cm → INESTABLE;
  - si mide más que vacío + 10 cm → FUERA_DE_RANGO.
- Nivel % = (117 − d)/(117 − 12)·100.
- **Resultados:**
  - 94.9 cm (9‑oct, banco).
  - 110.7–112 cm (14‑oct, tinaco casi vacío).
  - **30.4–31.4 cm, 82 %**, estable con la tapa puesta (21‑oct).
  - Antes, con la tapa quitada: lecturas inválidas de 127–160 cm.

**DHT22:** lectura cada ≥ 2 s. Valores: 21.5 °C / 53.7 % (9‑oct) y 25–28 °C / 45–55 % (21‑oct). Se usa para el VPD de la IA y se compara con el modelo de Open‑Meteo en la página Clima.

**YF‑S201:** litros = pulsos / 450. Caudal por ventanas de tiempo. Protecciones:

| Protección | Valor |
|---|---|
| NO_FLOW (sin pulsos) | 45 s |
| FLOW_HIGH | > 8 L/min |
| Flujo con todo apagado (fuga o contacto pegado) | ≥ 20 pulsos |

**Calibración con recipiente: PENDIENTE.**

---

## J. ARQUITECTURA REAL DEL SOFTWARE

**ESP32** (`firmware/main/`):

| Archivo(s) | Función |
|---|---|
| `main.c` | Arranque |
| `board.c` | Pines |
| `actuators.c` | Bomba y válvula, con enclavamiento: nunca bomba con válvula cerrada |
| `safety.c` | Supervisor independiente |
| `sensors.c`, `soil_sensor.c`, `tank_level.c`, `environment_sensor.c`, `flow_sensor.c` | Lectura de sensores |
| `irrigation_logic.c` | Máquina de estados **pura**, compilable en la PC |
| `irrigation_controller.c` | Orquestación, MQTT, IA y detección de lluvia |
| `ia_model.c` | Modelo RLS |
| `weather.c` | Open‑Meteo |
| `mqtt_manager.c`, `wifi_manager.c`, `net_config.c` | Red; credenciales en NVS |
| `commands.c` | Comandos JSON |
| `config_table.c`, `configuration.c` | ~75 parámetros validados con rangos, guardados en NVS |
| `storage.c` | Contadores, modo y modelo en NVS |
| `timekeeping.c` | NTP y zona CST6 |
| `console.c` | Consola USB |
| `selftest.c`, `logic_tests.c` | 50 pruebas internas |
| `simulation.c` | Simulación interna |

Intervalos principales:

- **Telemetría:** cada 10 s.
- **Suelo:** cada 300 s.
- **Tinaco:** cada 10 s.
- **Clima en el ESP32:** cada 60 min.
- **Clima en el servidor:** cada 30 min.

**Sin Internet:** sigue regando con sus reglas locales. Sin hora válida solo permite emergencias. Sin MQTT guarda 144 muestras (24 h, una cada 10 min) en RAM y las envía al reconectar.

**Servidor (Raspberry Pi):** Node‑RED 1881. Funciones en `dashboard/funciones/`:

- `ingesta.js`: MQTT → SQLite, estado y alertas.
- `comando.js`: lista blanca, id, ts, timeout de 12 s.
- `acks.js`, `alertas.js`, `snapshot.js` (estado ≤ 1 por s).
- `solicitudes.js` / `respuesta.js`: consultas SQLite.
- `clima_pedir.js` / `clima_procesar.js`: Open‑Meteo.
- `crecimiento.js`: etapas y grados‑día.
- `umbrales.js`: FAO‑56 → %VWC.
- `ia_servidor.js`: predicho vs real.
- `respaldo.js`, `csv_*`.

El flujo se genera con `dashboard/generar_flows.py` (125 nodos) y se despliega por la API de administración. Broker propio en el puerto 1884, con anónimos prohibidos y ACL por usuario.

**Base de datos (SQLite, 22 tablas):** readings, irrigation_events, event_ends, decisions, weather_fetches, forecast_hourly, forecast_daily, rain_events, crops, plantings, stage_changes, config_changes, crop_changes, ia_snapshots, ia_observations, predictions, alerts, connectivity, data_versions, soil_calibration, app_settings y schema_meta.

- Crecimiento estimado: ~8 640 lecturas por día, unos 400–600 MB por año.
- Respaldo diario a las 03:00.
- Exportación CSV.

**Laptop:** copia idéntica del dashboard (1880/1883), un simulador `sim_01` y un **espejo de solo lectura** de la Pi.

---

## K. DASHBOARD COMPLETO (FlowFuse Dashboard 2.0)

- **URL:** `http://raspberrypi.local:1881/dashboard`. Funciona solo dentro de la red RouterHuerto1, sin contraseña.
- **Título:** "Equipo 2 Proyecto".
- **Elementos comunes en todas las páginas:**
  - Selector de dispositivo.
  - Chips de conexión, MQTT y modo.
  - Franja "DATOS SIMULADOS" cuando se ve el simulador.
  - Barra con el resultado del comando.
  - **Avisos:** SISTEMA EN FALLA (con LIMPIAR FALLA), EL SISTEMA QUEDÓ EN MANUAL (con REGRESAR o QUEDARSE) y MÁXIMO DIARIO ALCANZADO (con PERMITIR RIEGO EXTRA).

| Página | Contenido | Estado |
|---|---|---|
| Inicio | Panel de control: medidores, indicadores de bomba y válvula, volumen objetivo, INICIAR/DETENER, resumen (suelo, tinaco, ambiente, litros, cultivo, IA, conexión), **Balance de agua de hoy** (Kc·ET0 en litros) y selección de modo | Funcional con datos reales |
| Manual | Riego por litros, **regar hasta X %** (por dosis), STOP, progreso, caudal y pulsos; **gráficas de humedad y riego en vivo (30 min) y de historial** (24 h / 7 d / 30 d / 1 año) | Funcional (real) |
| Automático | Decisión actual y justificación; borrador de umbrales, horarios, límites y lluvia con GUARDAR confirmado | Funcional |
| IA | Estado, plan, autonomía, predicho vs real, coeficientes, comparación, REINICIAR MODELO | Funcional; el modelo real está en APRENDIZAJE |
| Cultivos | 10 cultivos base + personalizados (agregar, editar, duplicar, eliminar), vista previa, aplicar con ACK | Funcional |
| Crecimiento | Plantaciones, etapa, días restantes, cosecha estimada, grados‑día, adelantar, retrasar, confirmar, bloquear | Funcional; las etapas se estiman por calendario, no por sensores |
| Clima | Open‑Meteo actual y modelo vs sensor, VPD, ET0, ETc, lluvia, horas recomendadas, 48 h y 10 días, balance | Funcional (real) |
| Historial | Gráficas con **"Agrupar por"** (10 min, hora, día, semana, mes), eventos, CSV | Funcional |
| Alertas | 12 categorías y confirmación de la causa de aumentos de humedad | Funcional |
| Configuración | Dispositivos, red, calibraciones, ubicación, cama, suelo (FC/WP), escala del EC‑5, respaldos, panel del simulador | Funcional |

**Recorrido de un comando:**

1. Botón → diálogo de confirmación.
2. `cmd()` de la página → `comando.js`, que valida la lista blanca, asigna `id` y `ts`, lo registra como pendiente y lo publica en MQTT QoS 1 sin retener en `huerto/final/esp32_principal/command`.
3. ESP32 `commands.c`:
   - JSON válido;
   - `id` repetido (anillo de 32) → DUPLICATE;
   - mensaje retenido → RETAINED;
   - `ts` con más de 60 s de diferencia → STALE.
4. Cola → `irrigation_logic`, que valida todo junto.
5. Respuesta en el topic `ack`, con `id`, estado, mensaje y versión → `acks.js` → la página muestra "CONFIRMADO por el dispositivo".
6. Si no llega el ACK en 12 s aparece **TIMEOUT**, y la configuración anterior se conserva.

---

## L. MODOS (comportamiento verificado en `irrigation_logic.c`)

**MANUAL:**

- `START_MANUAL` (0.1 L hasta el máximo por riego) o `START_TO_TARGET` (por dosis hasta la meta, con espera de infiltración).
- **Solo se acepta en MANUAL.**
- Respeta el máximo diario salvo con `over_daily` (riego extra autorizado).
- Rechaza el riego con salidas deshabilitadas, en FALLA o con la tierra en la humedad máxima (salvo `force`).
- STOP siempre tiene prioridad.

**AUTOMÁTICO** (orden de decisión):

1. Si las salidas están deshabilitadas o el suelo es inválido → no riega.
2. Si la humedad está en la máxima o sobre la reserva → no riega.
3. Si no hay emergencia y la humedad no está por debajo de objetivo − histéresis (2 pp) → no riega.
4. Confirma la sequedad con **2 lecturas**.
5. No riega si alcanzó el máximo diario o si pasaron menos de 60 min desde el último riego.
6. **Emergencia** (por debajo de la crítica): 1.5 L a cualquier hora, como máximo una cada 240 min.
7. Requiere hora válida.
8. **No riega de 11:00 a 16:00.**
9. Solo riega en las ventanas **06:00–09:00 y 18:00–20:00**.
10. Pospone con más de 35 °C.
11. Si todo se cumple → evento de dosis de 1.5 L con 15 min de infiltración, hasta 5 dosis o 7.5 L, buscando el objetivo.

El tinaco bajo **no** bloquea el riego: solo avisa.

**IA:** todo lo de AUTOMÁTICO, más:

- La lluvia por balance.
- Con el modelo en PREDICTIVO_ACTIVO, dosifica según el plan.
- Mientras está en APRENDIZAJE o VALIDACIÓN usa la lógica de AUTOMÁTICO en modo sombra.

**Comunes a los tres modos:**

- La IA **aprende en todos los modos**.
- Cambiar de modo no borra el modelo.
- Tras un reinicio se restaura el modo guardado, **sin regar al arrancar**.

---

## M. INTELIGENCIA ARTIFICIAL (`ia_model.c`)

**Modelo A — respuesta al riego:**

`Δθ = L·(a0 + a1·u1 + a2·u2 + a3·u3 + a4·u4)`, donde:

- `u1 = (θ0 − 25)/10`
- `u2 = (T − 20)/10`
- `u3 = (HR − 50)/50`
- `u4 = min(horas desde el último riego, 48)/24`

**Modelo B — secado:**

`pérdida pp/h = b0 + b1·(θ−25)/10 + b2·Kc·VPD + b3·Kc·ET0_h·10 + b4·sin(2πh/24) + b5·cos(2πh/24)`

- La pérdida se limita a 0–3 pp/h.
- Sin pronóstico vigente usa ET0 ≈ 0.12·VPD.

**Aprendizaje:**

- **RLS** con previa bayesiana: la ganancia inicial es 0.27 pp/L, de la geometría de la cama.
- Factor de olvido: **0.995** en A (~200 riegos) y **0.999** en B (~6 semanas).
- Atípicos: se descartan si el residuo es > **4σ**.
- **CUSUM** (k = 0.5, h = 6) para detectar cambios: vuelve a VALIDACIÓN **sin borrar** el modelo.
- **Cuándo aprende A:** tras cada riego **≥ 100 mL** (`irrigation_controller.c`), con la primera lectura nueva después de la infiltración.
- **Cuándo aprende B:** con pares de lecturas separados **≥ 1 h sin agua** (sin riego en los últimos infiltración + 30 min y sin aumentos externos).
- El error se registra **antes** de aprender (fuera de muestra).

**Estados:**

| Estado | Condición |
|---|---|
| APRENDIZAJE | Menos de 6 riegos o menos de 48 h de secado |
| VALIDACIÓN | Errores sobre la tolerancia (A ≤ 2 pp, B ≤ 0.4 pp/h) |
| PREDICTIVO_ACTIVO | Datos suficientes y errores dentro de tolerancia |

**Plan:**

1. Simula hora por hora hasta el siguiente horario.
2. Si la humedad se mantiene sobre mínima + 1 pp → **no riega**.
3. Si no:
   - meta = mínima + margen + pérdida prevista;
   - litros = (meta − actual)/ganancia;
   - nunca más que la reserva (IA_LIMITED).
4. Corrección acotada después de cada dosis: `L = 0.8·error/ganancia`, con un máximo de 1.5 L.

**Persistencia:** el modelo se guarda en NVS (~0.6 KB). En el servidor quedan `ia_snapshots`, `ia_observations` y `predictions` (predicción a 1 h comparada con la lectura real). Se reinicia solo con el botón (IA_RESET) o con una nueva versión de datos (`data_version`).

**Lo que se ha probado:**

- **11 escenarios automáticos:** aprende una ganancia real de 3.5 ± 0.5 pp/L, descarta atípicos, detecta cambios, plan mínimo y limitado.
- **Simulador:** con 14 días → PREDICTIVO_ACTIVO, con errores de 0.25 pp y 0.17–0.20 pp/h. **Son DATOS SIMULADOS.**
- **Huerto real (21‑oct):** APRENDIZAJE con 1 riego aprendido y 0 h de secado. **No hay métricas de exactitud reales todavía.**

---

## N. CLIMA, CULTIVOS Y CRECIMIENTO

**Open‑Meteo** (`https://api.open-meteo.com/v1/forecast`, sin clave): las consultas las hacen **el ESP32 y el servidor, de forma independiente**.

| | ESP32 (`weather.c`) | Servidor |
|---|---|---|
| Frecuencia | Cada 60 min | Cada 30 min |
| Datos | Ventana compacta: `past_hours=6&forecast_hours=24`; T, HR, precipitación, probabilidad, VPD y ET0 horaria | 7 días pasados + 3 de pronóstico; horario y diario, con ET0 |
| Otros | HTTPS con certificados validados (`esp_crt_bundle`); pronóstico vencido = no se usa | Se guarda en SQLite |

- **Variables adicionales disponibles** (verificadas el 19‑oct, no integradas): radiación de onda corta, horas de sol, nubosidad y viento.
- **Datos reales:**
  - ET0 de 4.1–4.6 mm/día en octubre.
  - Ejemplo del 19‑oct: 9.8 h de sol y 20.1 MJ/m².

**Cultivos:** 10 cultivos base con fuentes FAO‑56 (Tablas 11, 12 y 22: duración de etapas, Kc y fracción p) y referencias de grados‑día (Purdue, Wisconsin).

- **La FAO no da %VWC.** Los umbrales se calculan con `θ = FC − d·(FC − WP)` y la fracción p ajustada por ETc. Sin FC y WP medidos el perfil se marca PENDIENTE_DE_CALIBRACIÓN.
- Se pueden crear, editar, duplicar y eliminar cultivos personalizados, con vista previa y confirmación.
- Cultivo actual: **frijol ejotero, etapa Establecimiento, Kc 0.50.**

**Etapas:**

- Calendario FAO desde la siembra, ajustado con las correcciones del usuario (promedio ponderado).
- Grados‑día con la temperatura diaria.
- En modo IA la etapa avanza sola al cumplirse su duración (salvo bloqueo). En AUTOMÁTICO solo se recomienda.
- **Los sensores no detectan flores ni frutos.**

**Detección de lluvia o riego externo:**

- Se dispara con un aumento de **≥ 3 pp** respecto al mínimo de las últimas 3 h, sin riego reciente y confirmado con 2 lecturas.
- Clasificación:

| Clase | Condición |
|---|---|
| POSIBLE_ERROR_SENSOR | Aumento > 15 pp o sensor no OK |
| POSIBLE_LLUVIA | Lluvia en el pronóstico de las últimas 6 h |
| POSIBLE_RIEGO_EXTERNO | Sin lluvia en el pronóstico |

- Esos periodos **no se usan** para aprender el secado.
- El dashboard permite confirmar la causa.

---

## O. RESULTADOS EXPERIMENTALES (solo cifras con evidencia)

| Fecha | Prueba | Tipo | Resultado | Evidencia |
|---|---|---|---|---|
| Sep | Calibración EC‑5 (4 muestras) | FÍSICA (laboratorio) | 360/420/630/870 mV; R² 0.94494 | Act. 2.2 |
| Sep | YF‑S201 1–5 L | FÍSICA, volumen **calculado** | 481/920/1390/1850/2315 pulsos; error calculado promedio 3.55 % | Act. 2.3 |
| 9‑oct | Bomba + válvula 10 s (×4) | FÍSICA | 10 009 ms; la válvula corta el agua; activo en BAJO | `SEGURIDAD_Y_PRUEBAS.md` |
| 9‑oct | Riego de 1 L | FÍSICA (calculado) | 19.7 s, 455 pulsos ≈ 1011 mL; 3.5–4.5 L/min | `Proyecto_Final_v1\PROJECT_STATE.md` |
| 9‑oct | PING))) / DHT22 | FÍSICA | 94.9 cm; 21.5 °C / 53.7 % | ídem |
| 11‑oct | Firmware | AUTOMÁTICA | Lógica 47/47; SELFTEST en placa 49/49; ESP32 real por red 15/15; recuperación 3/3; integración 29/29 | `docs\PRUEBAS.md` |
| 12‑oct | Primer riego en el huerto | FÍSICA | 0.773 L / 20.5 s (~2.3 L/min) | `docs\PRUEBAS.md` |
| 13‑oct | Prueba de campo Pi + ESP32 | FÍSICA + AUTOMÁTICA | **28/28** (sin 12 V → NO_FLOW correcto) | `campo_pi_20261013_1000.txt` |
| 14‑oct | Riegos TARGET | FÍSICA | 2.802 L y 1.404 L, ~1.7 L/min | `docs\ESTADO_FINAL.md` |
| 14‑oct | Tinaco | FÍSICA | 110.7–112 cm (≈ 5–6 %) | ídem |
| 21‑oct | EC‑5 al aire / en sustrato | FÍSICA | ~375 mV / 515–600 mV; Pi: 25.9 %VWC | sesión 21‑oct |
| 21‑oct | Tinaco con la tapa puesta | FÍSICA | 30.4–31.4 cm = 82 % (cinta: 25–30 cm) | sesión 21‑oct |
| 21‑oct | **Prueba final con agua** | FÍSICA + AUTOMÁTICA | Válvula → bomba 1.3 s; **2.051 L TARGET en 42.8 s (923 pulsos)**, ~3.0 L/min; STOP a 0.622 L; sin reinicio; la Pi registró los riegos; Open‑Meteo vigente; 14 PASS / 1 FAIL del script | `prueba_final_20261021_1443.txt` |
| 21‑oct | Estabilidad Wi‑Fi | FÍSICA | 3 min sin desconexión con −68 a −82 dBm (en mesa); en el gabinete −84 a −94 dBm | sesión 21‑oct |
| 21‑oct | Regla nueva (manual solo en MANUAL) | FÍSICA (sin regar) | START_MANUAL en AUTOMÁTICO → REJECTED; SELFTEST 50/50 | sesión 21‑oct |
| 21‑oct | Integración | AUTOMÁTICA | **30/30** | `integracion_20261021_1521.txt` |
| 3‑oct | EPANET v3 | SIMULACIÓN | 71 OK / 3 avisos / 0 fallas | EPANET 3 |

Ningún volumen se ha medido con recipiente graduado.

---

## P. DIFICULTADES Y SOLUCIONES

| Problema | Causa | Solución | Estado |
|---|---|---|---|
| Reinicios del ESP32 al conmutar la bomba | Picos inductivos o caída de voltaje; relevador inadecuado | Separación de 1.5 s y detector de caída de voltaje en el nivel más bajo (software); **diodos, capacitor y relevador de potencia (hardware)** | Hardware PENDIENTE |
| Desconexiones de Wi‑Fi y MQTT | Señal de −84 a −94 dBm en el gabinete; ahorro de energía del radio | Wi‑Fi sin ahorro de energía, keepalive de 30 s, reconexión automática | Mejoró; falta reubicar la antena o el router |
| Contraseña Wi‑Fi "incorrecta" | Error al teclearla | Se tomó de Windows sin mostrarla | Resuelto |
| EC‑5 sin señal o a 3.1 V; relevadores prendiendo y apagando rápido | Pin equivocado, empalmes húmedos, alimentación directa | Pines 25/34, secado y aislamiento | Resuelto |
| Ultrasónico INESTABLE o FUERA_DE_RANGO | Tapa quitada, montaje | Centrado, tapa puesta | Resuelto (82 % estable) |
| NO_FLOW repetido | Tinaco bajo, cebado | Llenado del tinaco | Resuelto |
| Micro‑USB del ESP32 original dañado | Físico | Adaptador CH340G y luego ESP32 de reemplazo | Resuelto |
| Cable USB que solo cargaba | Cable | Cambio de cable | Resuelto |
| Contador diario borrado al reiniciar sin hora | Firmware | Corregido (prueba 5) | Resuelto |
| "Floración y fructificación" demasiado largo para el ESP32 | 28 > 23 bytes | Recorte por bytes | Resuelto |
| Raspberry Pi colgada (21‑oct) | NO VERIFICADO | Reinicio de la Pi; todo arrancó solo | Resuelto |

---

## Q. PENDIENTES Y LIMITACIONES (para considerarlo validado)

1. **Etapa de potencia de la bomba:** relevador de 30/40 A o MOSFET, fusibles de 15/10/3 A, diodos, capacitor y medición de la corriente de arranque.
2. **Calibración del YF‑S201** con recipiente graduado (meta H3 ≤ 10 %).
3. **Capacidad de campo real** (saturar, tapar y leer a las 24–48 h). La validación del EC‑5 en el sustrato es meta H1.
4. **IA con datos reales:** ≥ 6 riegos y 48 h de secado.
5. **Señal Wi‑Fi del gabinete:** −94 dBm.
6. **Energía:** balance diario, autonomía, voltaje de batería con la bomba encendida y margen ≥ 20 % (H8).
7. **EPANET contra la realidad:** medidas M0–M12, curva de la bomba y uniformidad de riego.
8. **Gabinete:** IP65 real, prensaestopas, tierra física.
9. **Prueba física sin Internet** (H7).
10. **Tiempo de respuesta ante falla ≤ 5 s** (H5): no medido formalmente. Los cortes por software son inmediatos, pero NO_FLOW espera 45 s.
11. **Bloqueo por nivel bajo:** desactivado por decisión del equipo. El riesgo de funcionamiento en seco lo cubre NO_FLOW de 45 s.

**Estado de las metas de diseño (QFD/AMEF):** H1–H10 y los NPR (175, 128, 112, …) son **metas y evaluaciones de diseño**. Se encontraron en los documentos de Diseño Mecatrónico, pero los códigos H1–H10 no se localizaron textualmente. De los NPR solo se localizaron textualmente 175, 128 y 112; los valores 96 (bomba y electroválvula) y 72 (panel) quedan NO VERIFICADOS en los archivos. Ninguna meta está validada formalmente, salvo H6 (un canal de riego: cumplido).

---

## R. EVIDENCIAS VISUALES

| Qué | Dónde |
|---|---|
| Fotos compartidas en las sesiones de Claude | `C:\Users\jaime\.claude\uploads\<sesión>\*.jpg` |
| Banco: relevadores, ESP32, YF‑S201 | `fa99f59b-…\` (30‑sep) |
| Tinaco (medidas), PING))) en caja acrílica, salida del tinaco, gabinete completo (`ef5b9ed0`), interior con ESP32 (`36dfe813`), estructura (`8bbd4925`) | `b5ae748a-…\` (13‑oct) |
| Cajón con el sustrato y bolsas de peat moss y perlita | `b5ae748a-…\` (21‑oct) |
| Coordenadas y letrero de la escuela | `b5ae748a-…\dea4d2c1`, `75d4b11e` (14‑oct) |
| Capturas de EPANET | `C:\TEC\SEMESTRE 5\Automatización industrial\Reto\EPANET\3\capturas_epanet\` (00–03) |
| Dashboard de la Práctica 4 | `C:\Users\jaime\Downloads\Practica4_MQTT\reporte_assets\` (`dashboard_final.jpg`, `dashboard_ciclo_252mL.jpg`, `montaje.jpg`) |
| Capturas del Dashboard 2.0 | **No hay capturas guardadas**; se pueden tomar en `http://raspberrypi.local:1881/dashboard` |
| Panel, bomba, válvula, batería (etiquetas) | Analizadas en `Prueba_01\COMPONENTES.md` ("47 imágenes"); las fotos originales no están en la computadora: NO VERIFICADO dónde están |

**No hay fotos de:** panel instalado en el techo, microaspersores, tubería final instalada, fabricación de las bases.

---

## S. ÍNDICE DE ARCHIVOS CLAVE

| Ruta | Contenido |
|---|---|
| `C:\ESP32_Riego_Automatico\Pruebas_Casa_ESP32_v1\` | **Proyecto final**: firmware, dashboard, simulador, pruebas y documentación |
| `…\firmware\main\` | Firmware riego‑2.0.0 (C) |
| `…\dashboard\generar_flows.py`, `funciones\`, `plantillas\` | Dashboard 2.0 (generador, lógica del servidor, páginas Vue) |
| `…\database\schema.sql` | Esquema SQLite |
| `…\docs\ESTADO_FINAL.md` | Bitácora de cambios hasta el 21‑oct |
| `…\docs\PRUEBAS.md`, `…\tests\resultados\` | Pruebas y resultados |
| `…\docs\MODELO_PREDICTIVO_IA.md`, `CULTIVOS.md`, `ETAPAS_DE_CRECIMIENTO.md`, `OPEN_METEO.md`, `CONFIGURACION_MQTT.md`, `DASHBOARD_COMPLETO.md`, `ALMACENAMIENTO_HISTORICO.md`, `PINOUT_VERIFICADO.md`, `SEGURIDAD.md` | Documentación técnica (DASHBOARD_COMPLETO no incluye los cambios del 14 al 21 de octubre) |
| `…\migration_raspberry_pi\` | Paquete de instalación en la Pi |
| `…\run\config_esp32_principal_20261021.json` | Configuración del ESP32 del huerto (v521, antes de los cambios del 21‑oct) |
| `C:\ESP32_Riego_Automatico\Proyecto_Final_v1\` | Versión intermedia (QEMU 33/33), sustituida |
| `C:\TEC\SEMESTRE 5\Automatización industrial\Reto\ESP32\Prueba_01_Bomba_Electrovalvula\` | Primeras pruebas físicas e **inventario con etiquetas** (`COMPONENTES.md`, `CONEXIONES.md`, `SEGURIDAD_Y_PRUEBAS.md`) |
| `C:\TEC\SEMESTRE 5\Automatización industrial\Reto\EPANET\1`, `2`, `3` | Modelos hidráulicos (usar el 3) |
| `C:\TEC\SEMESTRE 5\Automatización industrial\asesor\Actividad 2.2 / 2.3 *.docx` | Calibración del EC‑5 y del YF‑S201 |
| `C:\TEC\SEMESTRE 5\Diseño mecatrónico\*.docx/pdf` | Diseño: QFD, AMEF, estructuras, arquitectura |
| `C:\TEC\SEMESTRE 5\ceci\RIEGO_ESP32_PCB\` | PCB en Proteus (con 2 válvulas) |
| `C:\Users\jaime\Downloads\Practica4_MQTT\` | Práctica 4 (MQTT básico, `/ui`). ⚠️ El README contiene la contraseña del Wi‑Fi en texto plano |
| Raspberry Pi `~/equipo2_proyecto/` | Producción: Node‑RED 1881, Mosquitto 1884, `database/riego_final.db`, `backups/` |

---

## T. LO MÁS IMPORTANTE PARA LOS PROFESORES (19 hechos)

1. Un cajón de 1 m², una ruta hidráulica, **una** electroválvula NC y una bomba de diafragma de 12 V / 6 A.
2. Control con un ESP32 programado en **C con ESP‑IDF 6.0.2**: firmware propio de ~7 900 líneas y 25 módulos, con tareas FreeRTOS y watchdog.
3. Dosificación **por volumen**: los pulsos del YF‑S201 se cuentan con el **PCNT** por hardware y el riego se corta al llegar a los litros pedidos. Ejemplo: 2.05 L en 43 s.
4. Secuencia segura: válvula → 1.5 s → bomba … bomba OFF → 1.5 s → válvula. Nunca bomba con la válvula cerrada.
5. Supervisor de seguridad independiente: corte por falta de flujo (45 s), tiempo máximo de bomba (180 s más un tope duro de 5.5 min), límites por riego (7.5 L) y por día (30 L).
6. Sensores reales: EC‑5 (humedad volumétrica), PING))) (nivel del tinaco, 82 % medido) y DHT22.
7. Calibración propia del EC‑5 (R² = 0.945) y conversión a humedad volumétrica estándar.
8. **MQTT con confirmación (ACK)** de cada comando y protección contra comandos duplicados, retenidos o antiguos. El broker tiene usuarios y ACL.
9. Servidor en la Raspberry Pi: Node‑RED + Mosquitto + **SQLite** con historial completo, respaldo diario y exportación CSV. Es una instancia aislada que no afecta a otros equipos.
10. **Dashboard FlowFuse 2.0 de 10 páginas**: control en vivo, gráficas, historial agrupable, alertas, cultivos y configuración.
11. Tres modos. **AUTOMÁTICO**: umbrales del cultivo y su etapa, histéresis, ventanas de 06–09 y 18–20 h, sin riego a mediodía, emergencias.
12. **Riego por dosis con infiltración** (1.5 L, 15 min, medir, repetir) en lugar de regar sin parar.
13. **Umbrales agronómicos** de FAO‑56 (Kc, p) convertidos a %VWC con FC/WP del sustrato real (74 % peat moss).
14. **Modo IA**: dos modelos lineales con **RLS**, atípicos, CUSUM y validación fuera de muestra. Riega la cantidad mínima que mantiene la humedad hasta el siguiente horario.
15. **Open‑Meteo** (ESP32 y servidor): ET0, VPD y lluvia. **Lluvia por balance**: pospone solo si la lluvia cubre el déficit.
16. Detección de lluvia o riego externo (aumento de humedad sin bomba), excluida del aprendizaje.
17. **Funciona sin Internet** con sus límites locales; reconecta solo; guarda el modo y nunca riega al reiniciar.
18. Pruebas: autodiagnóstico 50/50 en la placa, integración 30/30, prueba de campo 28/28 y prueba final con agua 14/15 (el fallo fue del script).
19. Honestidad técnica: faltan la etapa de potencia (relevador de 3 A inductivos para una bomba de 6 A), la calibración del caudalímetro, la validación del suelo y del modelo con datos reales, y la energía.

---

## U. PREGUNTAS QUE LOS ARCHIVOS NO RESPONDEN

1. ¿Qué trazado hidráulico se construyó (A vertical, B a 45° o B2), con qué medidas reales y cuántos metros de Tuboplus?
2. ¿Marca y modelo de los microaspersores? ¿Están instalados los 9?
3. ¿El panel está instalado en el techo, a 28° hacia el sur? ¿Hay fotos? ¿Qué cable y qué protección lleva?
4. ¿Corriente nominal del controlador PWM y del regulador de la placa de expansión?
5. ¿Capacidad nominal y modelo del tinaco instalado? Las medidas sugieren unos 650 L útiles, no 450.
6. ¿Se fabricaron las bases metálicas con las medidas del diseño (PTR, patas, placa)? ¿Qué acabado anticorrosivo tienen?
7. ¿Existen los archivos de SolidWorks? No están en esta computadora.
8. ¿Se cambió el relevador de la bomba por uno automotriz o un MOSFET? ¿Se pusieron fusibles?
9. ¿Qué módulo (antena integrada o externa) tiene el ESP32 de reemplazo …xx:xx:xx?
10. ¿Resultados del riego automático del 21‑oct (18:00–20:00) y de la mañana del 22? Requiere conectarse a RouterHuerto1 para consultarlos.
11. ¿Volumen real entregado con recipiente graduado? ¿Cuál es el factor real de pulsos por litro?
12. ¿Voltaje de la batería durante el bombeo? Explicaría la variación de caudal entre 1.7 y 3 L/min.
