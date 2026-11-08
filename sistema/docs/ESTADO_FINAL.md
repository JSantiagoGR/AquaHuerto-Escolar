# Estado final verificable (2026-10-11)

## Datos clave

| | |
|---|---|
| Ruta del proyecto | `C:\ESP32_Riego_Automatico\Pruebas_Casa_ESP32_v1` |
| Puerto COM | **COM8** (CP210x, cable USB-C a USB-C con datos) |
| Chip | **ESP32-D0WD-V3 rev 3.1**, 4 MB, MAC `xx:xx:xx:xx:xx:xx` (distinta de la placa anterior) |
| ESP-IDF | **v6.0.2** |
| Firmware | `riego-2.0.0` compilado (0 errores, 0 advertencias, 27 % libre) y **flasheado** (hash verificado); firmware anterior (Práctica 4) respaldado |
| IP de la laptop | `IP_DE_LA_LAPTOP` (Wi-Fi `RED_DE_CASA_5`, DHCP) |
| IP del ESP32 | `IP_DEL_ESP32` (Wi-Fi `RED_DE_CASA_2.4`, −50 dBm) |
| Broker | Mosquitto 2.1.2 `mqtt://IP_DE_LA_LAPTOP:1883` (usuarios + ACL, solo red local) |
| Node-RED | 5.0.8, instancia aislada: <http://localhost:1880> (editor protegido) |
| Dashboard | **<http://localhost:1880/dashboard>** · celular: `http://IP_DE_LA_LAPTOP:1880/dashboard` (usuario y contraseña) |
| Base de datos | SQLite 3.52 `database\riego_casa.db` (22 tablas, 10 cultivos, respaldos en `backups\db`) |

## Estado por componente

| Componente | Estado |
|---|---|
| MQTT | **Funcionando**: ESP32 real, Node-RED y simulador conectados; bidireccional con ACK verificado (15/15 con la placa real, 29/29 con el simulador) |
| Open-Meteo | **Funcionando con datos reales**: servidor (cada 30 min) y ESP32 (cada 60 min), ambos por HTTPS con certificados |
| Base de datos | **Funcionando**: lecturas reales (`simulated=0`) y simuladas separadas; respaldo, CSV y alertas de almacenamiento probados |
| IA | ESP32 real: **APRENDIZAJE** (sin sensores no hay datos; usa el automático conservador). Simulador: PREDICTIVO_ACTIVO con un modelo de **datos simulados** |
| Dashboard | **10 páginas** desplegadas y probadas (ver PRUEBAS) |

## Qué funciona con datos reales

Detección y flasheo del ESP32; Wi-Fi, MQTT, NTP y diagnóstico del ESP32; telemetría real (que hoy dice honestamente "sin señal" porque **no hay sensores conectados**); modos y validaciones del ESP32 desde el dashboard; reconexión tras caída del broker y tras reinicio; Open-Meteo (servidor y ESP32); SQLite; respaldos; exportación CSV; seguridad del broker y de Node-RED.

## Qué funciona con simulación

Riegos (manual, hacia la óptima, matutino automático, emergencia), lluvia y riego externo, fallas de sensores, pérdida de MQTT, tinaco, IA aprendiendo y activa, cultivos aplicados y etapas de crecimiento. Todo marcado **MODO DEMOSTRACIÓN — DATOS SIMULADOS** y separado en la base de datos.

## Botones y flujos probados

SELECCIONAR MODO (simulador y ESP32 real) con confirmación y ACK; REGAR 1 L y progreso en vivo; STOP (por MQTT); GUARDAR COMO CULTIVO ACTIVO (perfil v1 confirmado); NUEVA PLANTACIÓN y CONFIRMAR ETAPA ESTIMADA (perfil v503 confirmado, la estimación aprende de la corrección); RESPALDAR AHORA; filtros e historial; selector de dispositivo; cambio de modo en el ESP32 real. Por MQTT automatizado: configuración atómica, duplicados, retenidos, antiguos, lluvia, fallas, LWT, CSV y autenticación.

## Copias de seguridad

- Flash original de la ESP32: `backups\esp32_casa_flash_original\flash_20500d1a0054_4MB.bin` (SHA-256 `E9DE0AF4…EE5`).
- Base de datos: `backups\db\riego_<fecha>.db` (automático 03:00 y botón).
- Flujos y contexto: `backups\nodered\`.
- Paquete para la Raspberry Pi (sin secretos): `backups\paquete_raspberry_pi_<fecha>.zip`.

## Cama y suelo (2026-10-12)

- Cama 1 m² × 37.5 cm de sustrato (375 L): 1 punto de %VWC ≈ 3.75 L; drenaje libre (geotextil o lona perforada).
- Suelo **estimado** (no medido): FC 40 / WP 16 %VWC (50 % tierra negra, 30 % peat moss, 20 % lombricomposta).
- Firmware: el EC-5 convierte la recta de la Act. 2.2 (agua/(tierra+agua)) a %VWC estándar (`ec5_scale`, `CONFIG_VERSION 3`); flasheado, SELFTEST 49/49.
- ESP32: **Frijol ejotero / Establecimiento, perfil v509** confirmado: 22.4 / 27.2 / 33.6 / 37.6 / 40 %VWC, 2.5 L por dosis, 7.5 L por evento, 15 L por día, IA con 0.27 %/L inicial. Tras el flasheo arrancó en MANUAL.
- Los 10 cultivos dan umbrales válidos con este suelo (se corrigió la reserva: `d = min(0.10, p/4)`; antes la espinaca quedaba sin rango).

## Falta del hardware físico

1. **Etapa de potencia apta** para la bomba de ~6 A (el relevador SRD no se considera apto), fusibles, diodos, corte manual; medir la corriente de arranque.
2. Conectar y verificar sensores en la ESP32 nueva (`PINES`): EC-5 (GPIO25/34 + 1 MΩ), YF-S201 (19), PING))) (18), DHT22 (4), relevadores (26/27).
3. Calibrar: EC-5 en el suelo real (y FC/WP), YF-S201 con recipiente, tinaco (vacío/lleno).
4. Riego con agua con el firmware nuevo (solo con autorización y tras el punto 1).
5. Coordenadas reales del huerto (hoy: centro de Chihuahua aproximado).
6. Red del Tec: no verificada (probablemente 802.1X o con aislamiento).
7. Acceso desde el celular (configurado y probado desde la IP de la red, falta probar en un teléfono).

## Después, en la Raspberry Pi

Instalación **independiente** (Node-RED en 1881 con Dashboard 2.0, listener MQTT autenticado en 1884, base `riego_final.db`, topics `huerto/final/esp32_principal`) con `migration_raspberry_pi/scripts/instalar_pi.sh`, sin tocar el flujo "Equipo 2" ni su `/ui`. Respaldar y flashear el ESP32 original, configurar `RouterHuerto1` y seguir el checklist de [MIGRACION_RASPBERRY_PI.md](MIGRACION_RASPBERRY_PI.md).

## Instalado en la Raspberry Pi (2026-10-12)

| | Dirección |
|---|---|
| **Dashboard Equipo 2 Proyecto** (sin contraseña, red RouterHuerto1) | http://raspberrypi.local:1881/dashboard |
| Editor de esa instancia (protegido, `NODERED_ADMIN_*`) | http://raspberrypi.local:1881 |
| Broker propio (usuarios + ACL) | mqtt://raspberrypi.local:1884 |
| Dashboard anterior de los equipos (sin cambios) | http://raspberrypi.local:1880/ui |

- Carpeta `~/equipo2_proyecto` (usuario `pi`), Node-RED 5.0.8 propio, Dashboard 2.0, SQLite migrada (3846 lecturas, 10 cultivos, cama y suelo).
- Sin `sudo`. Cambios fuera de la carpeta: una línea en `~/.ssh/authorized_keys` (llave de la laptop) y una línea `@reboot` en el crontab de `pi`.
- Verificado: `~/.node-red/flows.json`, `settings.js` y `/etc/mosquitto/mosquitto.conf` con el **mismo SHA-256** antes y después; el Node-RED del profesor (PID 732) y el Mosquitto del sistema (PID 1599) nunca se reiniciaron.
- Acceso: dashboard 200 sin contraseña; editor y API 401/403 sin la contraseña de administrador; broker 1884 rechaza conexiones sin usuario.
- Respaldos previos: `backups/raspberry_pi_antes_20261012_1050/` (incluye `.node-red` y `/etc/mosquitto`).
- Errores encontrados y corregidos al instalar: el script de detener no reconocía el Node-RED propio (Node-RED renombra su proceso) ni el broker (`grep -q` + `pipefail`); ahora identifica los procesos por `/proc/<pid>/cmdline|environ` y el ciclo detener/iniciar quedó probado.
- **ESP32 conectada a la Pi (2026-10-12 13:57):** la placa de casa (COM8) ahora es `esp32_principal`: Wi-Fi `RouterHuerto1` (IP IP_DEL_ESP32, −55 dBm), broker propio `mqtt://raspberrypi.local:1884`, topic `huerto/final/esp32_principal`; la red de casa queda guardada como respaldo. Dashboard de la Pi: "ESP32 en línea", MANUAL, salidas deshabilitadas, Frijol / Establecimiento v509.
- **ESP32 del proyecto (la que tiene el cableado) ahora es `esp32_principal` (2026-10-12 15:50):** MAC `xx:xx:xx:xx:xx:xx`, COM3. Firmware anterior (Prueba 03, solo serie) respaldado completo en `backups/esp32_proyecto_flash_original/` (SHA-256 `B0C0FE4E…BBB4`). Pines leídos de su propio arranque y **idénticos** a `board.h` (26/27 activo en bajo, 19, 18, 4). Firmware `riego-2.0.0` con borrado completo, SELFTEST 49/49, `PINES` sin conflictos. Wi-Fi RouterHuerto1 (IP_DEL_ESP32), broker 1884. Perfil Frijol / Establecimiento **v515** confirmado. **DHT22 real: 25.1 °C / 51 %HR** en el dashboard de la Pi. PING))) responde SIN_ECO (igual que con el firmware anterior: revisar 5 V, SIG y divisor). EC-5 sin conectar. La ESP32 de casa sigue configurada como `esp32_principal`: regresarla a casa antes de volver a encenderla en el huerto.

## Cambios del 2026-10-14 (compilados y probados; pendientes de cargar en la ESP32 y la Pi)

- **Modo persistente:** la ESP32 guarda el último modo (MANUAL/AUTOMATICO/IA) y lo restaura tras un reinicio o apagón si la potencia está habilitada. Al arrancar nunca riega de inmediato.
- **Tinaco:** en el mínimo o sin lectura **riega y avisa** (alarma TANK_LOW "casi sin agua"); el corte por falta de flujo protege la bomba. Antes el AUTOMATICO/IA no regaban sin tinaco calibrado.
- **Lluvia pronosticada:** solo la usa el **modo IA**; la IA conserva todas las reglas del AUTOMATICO.
- **Manual "regar hasta X %"** elegido por el usuario: por dosis con pausa de infiltración y nueva lectura (no riega sin parar).
- **Etapas en IA:** si nadie la cambió, pasa a la siguiente cuando se cumple el tiempo de la etapa actual.
- **Dosis según el caudal real (~1.3 L/min):** 1.5 L por dosis, hasta 5 dosis (7.5 L), emergencia 1.5 L, `pump_max_s` 180 s.
- **Ubicación:** Escuela Primaria Federal Belisario Domínguez (28.659830, −106.074051).
- **Recuperación de riegos:** al reconectarse la ESP32, el servidor pide su historial y completa los riegos que quedaron sin final.
- Pruebas: lógica 47/47, integración 29/29 (una corrida previa dio 26/29 por estado residual del simulador; la siguiente 29/29).
- **Aplicado el 2026-10-14 10:00:** firmware cargado en la ESP32 del proyecto (SELFTEST 49/49), flujo desplegado en la Pi, configuración v518 confirmada (ubicación, dosis 1.5 L × 5, emergencia 1.5 L, bomba 180 s). **Prueba de reinicio física:** en AUTOMATICO → REINICIAR → volvió en AUTOMATICO con potencia habilitada y sin regar al arrancar. **EC-5 leyendo:** 395 mV = 9.0 %VWC (válida) tras corregir las conexiones del jack.

## 2026-10-14 (tarde)
- Sensores físicos en la Pi: EC-5 válido (27–33 %VWC en la mezcla de prueba; tras 1.4 L: 28.8 → 32.1 %), ultrasónico 110.7–112 cm (calibrado: vacío 117 cm, lleno 12 cm, mínimo 5 %), DHT22 OK.
- Riegos reales: 2.802 L (TARGET) y 1.404 L (TARGET) a ~1.7 L/min; cuatro intentos previos sin flujo (tinaco bajo / cebado) con corte NO_FLOW y FALLA.
- **Pendiente de hardware:** la ESP32 se reinició (watchdog, motivo 7) al apagarse la bomba en un riego: diodos de rueda libre en bomba y válvula + capacitor de 470–1000 µF en 5 V.
- Dashboard: aviso SISTEMA EN FALLA con botón LIMPIAR FALLA; Historial con "Agrupar por" (10 min, hora, día, semana, mes) y respuestas solo al navegador que pide; Manual con gráficas de humedad y riego en vivo e historial.
- Firmware corregido (compilado, **pendiente de cargar por USB**): los litros del día ya no se reinician al arrancar sin hora (antes el límite diario se perdía en cada apagón).

## Laptop igual que la Pi (2026-10-14)
- Node-RED de la laptop (http://localhost:1880/dashboard) con el mismo flujo que la Pi (todas las páginas y cambios); dashboard abierto en la red local (`DASHBOARD_PUBLIC=1`), editor con usuario.
- Broker de la laptop (1883): misma configuración que el de la Pi (1884), espacio `huerto/casa/`.
- `scripts/espejo_pi.py` (o `iniciar_todo.ps1 -EspejoPi`): copia en vivo y en **solo lectura** `huerto/final/esp32_principal/#` (Pi) → `huerto/casa/esp32_principal/#` (laptop). Los comandos de la laptop no llegan al ESP32; solo la Pi lo controla.
- `scripts/copiar_historial_pi.py`: copia el historial de esp32_principal de la base de la Pi (abierta en solo lectura) a `database/riego_casa.db`; respalda la base local antes.
- Pruebas de integración en la laptop: 29/29.

## Lluvia por balance y balance de agua (2026-10-19)
- Firmware: en modo IA el pronóstico de lluvia solo pospone si la lluvia efectiva cubre lo que falta:
  `0.8 × mm_previstos_6h × ia_gain_prior >= hum_target − humedad` (cama de 1 m²: 1 mm = 1 L). Las emergencias nunca se posponen; AUTOMÁTICO sigue sin usar lluvia.
  Pruebas de lógica 47/47 (prueba 35: 2 mm no pospone, 50 mm sí). Cargado el 2026-10-20 por adaptador CH340G (micro-USB del ESP32 dañado), solo la app en 0x10000 (conserva NVS); hash verificado y SELFTEST 49/49 en el ESP32.
- Dashboard: tarjeta "Balance de agua de hoy" en Inicio y Clima (Kc × ET0 en litros, regado hoy, lluvia prevista). Solo informativa.
  Desplegado en la laptop y en la Pi 1881 el 2026-10-20 (solo el flujo, sin otros cambios). Integración 29/29.

## ESP32 de reemplazo y puesta en marcha final (2026-10-21)
- **ESP32 nuevo (MAC xx:xx:xx:xx:xx:xx)** reemplaza al principal (micro-USB dañado; el viejo …xx:xx:xx debe quedar APAGADO, comparten identidad).
  Respaldo de su firmware de fábrica (AT): `backups/esp32_d0ef7613f30c_flash_original/`. Firmware completo cargado; red configurada con la clave guardada en Windows (sin mostrarla).
  Configuración copiada del principal (74 parámetros, EC-5 exacto por consola). Potencia habilitada por USB (`POWER ON CONFIRMAR`).
- **Firmware:** Wi-Fi sin ahorro de energía (`esp_wifi_set_ps(WIFI_PS_NONE)`), MQTT keepalive 30 s y timeout 10 s. `valve_lead_ms`/`valve_lag_ms` = 1500.
- **Suelo real:** ~74 % peat moss Premier (107 L comprimido), ~19 % tierra negra (40 kg), ~7 % perlita (20 L) → FC 48 / WP 16 %VWC (estimado).
  Frijol/establecimiento: emergencia 23.6 · mínima 30 · óptima 39 · reserva 44.8 · máxima 48. Perfil v525; máximo diario 30 L (v526) para recuperar humedad.
- **EC-5:** blanco → GPIO25, rojo → GPIO34, sin forro → GND. Falla previa: empalmes húmedos y cable en pin equivocado. Al aire ~375 mV, en tierra ~520–600 mV.
- **Ultrasónico:** estable con la tapa puesta (30.5 cm, 82 %).
- **Prueba final (tests/prueba_final_riego.py):** válvula→bomba 1.3 s, 2.05 L en TARGET a 3.0 L/min, STOP a 0.62 L, sin reinicios, registro en la Pi, Open-Meteo vigente. Modo AUTOMÁTICO activo.
- Herramientas nuevas: `tests/diagnostico_pi.py`, `tests/ver_tinaco_pi.py`, `tests/ver_tinaco_en_vivo.py`, `tests/ver_senal_wifi.py`, `tests/ver_ec5_en_vivo.py`, `tests/ec5_multimetro.py`.
- Pendiente de hardware: diodos (bomba y válvula), capacitor 470–1000 µF en VIN, mejor señal Wi-Fi (−78 a −94 dBm en la placa de expansión).

## Riego manual solo en MANUAL y riego extra autorizado (2026-10-21)
- **Firmware:** `START_MANUAL` y `START_TO_TARGET` se rechazan fuera de MANUAL ("Modo X activo: cambie a MANUAL"). El máximo diario
  aplica también a los riegos manuales; con `"over_daily": true` (botón PERMITIR RIEGO EXTRA) se permite pasarlo en ESE riego
  (las demás protecciones siguen). Prueba de lógica 50; host 48/48. Cargado el 2026-10-21 (hash verificado, SELFTEST 50/50); en el ESP32 real START_MANUAL/START_TO_TARGET en AUTOMATICO -> REJECTED.
- **Dashboard:** si se pide un riego manual desde AUTOMÁTICO/IA, avisa, cambia a MANUAL y riega. Al terminar muestra
  "EL SISTEMA QUEDÓ EN MANUAL" con REGRESAR A <modo anterior> / QUEDARSE EN MANUAL (si no se elige, se queda en MANUAL).
  Si el riego se rechaza por el máximo diario aparece "MÁXIMO DIARIO ALCANZADO" con PERMITIR RIEGO EXTRA (con confirmación).
  El perfil de la cama ahora manda máximo diario de 30 L (8 puntos). Probado en la laptop con el simulador; integración 30/30.
  Desplegado en la Pi 1881 el 2026-10-21 15:35 tras reiniciar la Pi (respaldo en ~/equipo2_proyecto/backups/).
