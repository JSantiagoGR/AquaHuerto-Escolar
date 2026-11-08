# Reporte de pruebas (2026-10-11)

Categorías: **FÍSICO** (con el hardware real), **SIMULACIÓN** (simulador `sim_01` o modo SIM), **AUTOMÁTICO** (pruebas programadas), **PENDIENTE** (falta hardware, red o calibración).
Resultados en `tests/resultados/`.

## Resumen

| Conjunto | Resultado | Tipo |
|---|---|---|
| Lógica pura en la PC (`tests/host/build/logic_tests.exe`) | **47/47 PASS** | AUTOMÁTICO |
| SELFTEST en la ESP32 real (COM8) | **49/49 PASS** (dos veces: tras el primer flasheo y tras la actualización) | AUTOMÁTICO en hardware real |
| Integración broker + Node-RED + SQLite + simulador (`tests/test_integracion.py`) | **29/29 PASS** | SIMULACIÓN + AUTOMÁTICO |
| ESP32 real por red (`tests/test_esp32_real.py`) | **15/15 PASS** | FÍSICO + AUTOMÁTICO |
| Recuperación con el ESP32 real (broker caído, reinicio) | **3/3 PASS** | FÍSICO |
| Dashboard en el navegador integrado | Ver tabla de páginas | SIMULACIÓN (manual) |

Primeras ejecuciones de integración: 20/29 y 28/29. Los fallos eran reales y se corrigieron: detección de lluvia gradual (referencia = mínimo de 3 h, en firmware y simulador), autenticación del dashboard desde la red (Dashboard 2.0 usa su propio middleware), y dos pruebas mal planteadas (comando retenido y orden hora/pronóstico).

## Detalle

| Prueba | Estado | Tipo / evidencia |
|---|---|---|
| Compilación ESP-IDF 6.0.2 | OK, 0 errores y 0 advertencias, 1.1 MB (27 % libre) | AUTOMÁTICO |
| Detección del ESP32 (COM8, CP210x, ESP32-D0WD-V3 rev 3.1, 4 MB) | OK | FÍSICO |
| Respaldo de la flash original (4 MB, SHA-256 registrado) | OK | FÍSICO |
| Flasheo seguro (erase + flash, luego app-flash) | OK, hash verificado | FÍSICO |
| Monitor serial y consola (ESTADO, RED, SELFTEST) | OK | FÍSICO |
| Salidas inactivas al arrancar (modo MANUAL, potencia deshabilitada) | OK (estado reportado por la consola) | FÍSICO (sin cargas conectadas) |
| Sensores reales en la ESP32 nueva | Sin sensores conectados: EC-5 "SIN_SENAL", PING "SIN_ECO", DHT "SIN_LECTURA" (lecturas reales de ausencia) | FÍSICO |
| Wi-Fi del ESP32 (`RED_DE_CASA_2.4`, IP IP_DEL_ESP32, −50 dBm) | OK | FÍSICO |
| MQTT ESP32 ↔ broker (bidireccional) | **15/15 PASS** (`tests/test_esp32_real.py`): estado, telemetría real con NTP, sensores ausentes reportados como inválidos, ACK, START rechazado sin potencia, modos, APPLY inválido rechazado, DUPLICATE, STALE, diagnóstico sin contraseñas, IA en APRENDIZAJE, guardado en SQLite con `simulated=0` | FÍSICO + AUTOMÁTICO |
| Open-Meteo desde el ESP32 (HTTPS con certificados) | OK (25.3 °C, ET0 24 h 5.6 mm) | FÍSICO |
| Reconexión tras caída del broker (8 s) | OK: ESP32, Node-RED y simulador reconectaron solos | FÍSICO |
| Reinicio del ESP32 | OK: MANUAL + potencia deshabilitada; Wi-Fi 2.2 s, MQTT 2.6 s, clima 8 s | FÍSICO |
| Cambio de modo desde el dashboard con el ESP32 real | OK: "CONFIRMADO por el dispositivo" (solo decide; salidas deshabilitadas); se regresó a MANUAL | FÍSICO |
| Broker: anónimos rechazados, ACL, usuarios | OK | AUTOMÁTICO |
| MQTT bidireccional, ACK, duplicados, retenidos, antiguos | OK | SIMULACIÓN + AUTOMÁTICO |
| Configuración atómica (inválida rechazada, válida con versión) | OK | SIMULACIÓN + AUTOMÁTICO |
| Riego manual por volumen, STOP | OK | SIMULACIÓN |
| Riego matutino automático, emergencia a mediodía, pronóstico de lluvia | OK | SIMULACIÓN |
| Posible lluvia / riego externo → evento y SQLite | OK | SIMULACIÓN |
| Fallo de sensor → alarma y SQLite | OK | SIMULACIÓN |
| Pérdida de MQTT → LWT, reconexión, registro | OK | SIMULACIÓN |
| IA sin datos (ESP32 real) | APRENDIZAJE, usa el automático (también escenario 37 de la lógica) | FÍSICO (estado) + AUTOMÁTICO |
| IA aprendiendo / con modelo simulado | 14 días simulados → PREDICTIVO_ACTIVO (error 0.25 pp / 0.17 pp/h); escenarios 44–47 | SIMULACIÓN + AUTOMÁTICO |
| Open-Meteo real (servidor) | OK, HTTPS 200, 240 horas + 10 días guardados | FÍSICO (internet real) |
| Fecha y hora | Servidor OK; ESP32 sincronizado por NTP (verificado con el rechazo STALE) | FÍSICO |
| SQLite: escritura, lectura de historial, duplicados | OK | AUTOMÁTICO |
| Exportación CSV | OK (local); 401 desde la red sin credenciales | AUTOMÁTICO |
| Respaldo SQLite (botón) | OK: `backups/db/riego_20261011_175436.db` | SIMULACIÓN (manual) |
| Reinicio de Node-RED | OK: flujos, credenciales cifradas y dispositivo seleccionado persisten | AUTOMÁTICO |
| Reinicio del ESP32 | OK tras flasheo: arranca en MANUAL con potencia deshabilitada; recuperación de reinicio durante riego en escenario 21 | FÍSICO + AUTOMÁTICO |
| Pérdida de internet | Escenario de alerta y conservación del pronóstico vigente implementado; no se cortó internet físicamente | PENDIENTE (prueba física) |
| Límites de seguridad | Escenarios 8–31 | AUTOMÁTICO |

## Dashboard (navegador integrado, con el simulador)

| Página | Verificado |
|---|---|
| Inicio | Datos en vivo, franja de demostración, SELECCIONAR MODO → diálogo → ACK "CONFIRMADO" |
| Manual | REGAR 1 L con confirmación; progreso 34 % → fin; 3.99 L/min; pulsos |
| Automático | Carga de parámetros activos al borrador |
| IA | Estado, plan, explicación, coeficientes, comparaciones |
| Cultivos | Lista de 10, vista previa de Tomate con PENDIENTE_DE_CALIBRACION, aplicado → "Configuración v1 aplicada (8 parámetros)" |
| Inicio · panel de control (2026-10-11 23:45) | Simulador: INICIAR RIEGO 1000 mL → CONFIRMADO, medidores y focos en vivo, DETENER BOMBA → STOP confirmado, el medidor conserva 418 mL. ESP32 real: panel con datos reales (EC-5 sin sensor en gris y "no válida"); **no** se le envió riego (pendiente que lo pruebe el usuario: debe responder RECHAZADO por salidas deshabilitadas) |
| Plantación nueva y cambio de etapa → perfil (2026-10-12 01:15) | Simulador: NUEVA PLANTACIÓN Tomate → v510 Establecimiento (23.6/28.4/34.2 aprox.); ADELANTAR → v511 Desarrollo (25.8/30.6/35.3/37.6/40); ADELANTAR → v512 **RECHAZADO**: "Floración y fructificación" ocupa 28 bytes y el ESP32 guarda 23 (afectaba a tomate, pimiento, pepino, calabacita y **frijol**). Corregido ("Floración y fructif.", recorte por bytes) → v514 Floración (27.3/32.1/36.0/38.0/40). El simulador ahora publica el estado al aplicar (antes tardaba hasta 30 s). Plantación de prueba borrada | SIMULACIÓN |
| Crecimiento · una plantación por caja (2026-10-11 23:52) | Primer intento: quedaban **dos activas** (parámetros SQL `$2` antes de `$1`, SQLite los asigna por orden de aparición); corregido y revisadas todas las consultas. Segundo intento: Lechuga → Tomate deja solo Tomate activa; fecha de siembra local (antes salía en UTC). Plantaciones de prueba borradas |
| **Prueba de campo Pi + ESP32 del proyecto (2026-10-13 10:00)** | **28/28 PASS** (`tests/test_campo_pi.py`, `tests/resultados/campo_pi_20261013_1000.txt`) con la batería de 12 V desconectada: servicios 1880/1881/1883/1884, configuración del profesor intacta, autoarranque, 10 páginas, editor protegido, estado y telemetría reales (DHT22), DUPLICATE/STALE/REJECTED, modos, **relevadores conmutan y el riego se corta solo por NO_FLOW**, alarma y CLEAR_ALARM, STOP_CMD y registro en la base de la Pi. SELFTEST en la placa 49/49 | FÍSICO + AUTOMÁTICO |
| Integración 2026-10-13 | 29/29 PASS (la prueba de emergencia ahora compara con `emergency_liters` del dispositivo: 1.9 L con la cama de 375 L, antes 0.5 L fijo) | SIMULACIÓN + AUTOMÁTICO |
| Primer riego real en el huerto (2026-10-12 15:58) | 1 L pedido desde el dashboard de la Pi: válvula y bomba encendieron, 0.773 L medidos en 20.5 s (≈ 2.3 L/min), terminado con STOP; guardado en la base de la Pi | FÍSICO |
| Integración tras los cambios de cama y escala (2026-10-12 00:58) | **29/29 PASS** (`tests/resultados/integracion_20261012_0058.txt`); se borraron 45 filas **simuladas** con fecha futura que dejan las pruebas al adelantar el reloj del simulador | SIMULACIÓN + AUTOMÁTICO |
| Escala del EC-5 (2026-10-12) | PC: ida y vuelta mV → %VWC → mV (360–870 mV) sin error > 0.5 mV; 47/47 lógica. Placa: SELFTEST **49/49** con el firmware nuevo; Wi-Fi y MQTT reconectaron solos tras el flasheo | AUTOMÁTICO + FÍSICO |
| Cama y perfil del frijol (2026-10-12) | Configuración: cama y suelo guardados en el servidor. Cultivos: Frijol / Establecimiento → ESP32 **v509 confirmado (19 parámetros)**, con umbrales y litros de la cama visibles en Automático | FÍSICO (configuración; sin riego) |
| Crecimiento | Nueva plantación, etapa estimada, GDD, confirmar etapa → perfil v503 confirmado; aprendizaje de la corrección (25 → 28 días) |
| Clima | Open-Meteo real: vigente, 10 días, ET0, horas recomendadas |
| Historial | Eventos de riego del simulador; error de SQL encontrado y corregido |
| Alertas | Contadores por categoría, eventos para confirmar causa, registro |
| Configuración | RESPALDAR AHORA, lista de respaldos, panel del simulador |

Se borraron de la base: la plantación de prueba y 218 filas **simuladas** con fecha futura (creadas al acelerar el reloj del simulador en las pruebas).

## Pendiente de validar físicamente

EC-5 conectado y calibrado en el suelo real; YF-S201 contra recipiente; tinaco (vacío/lleno); etapa de potencia certificada; riego con agua con el firmware nuevo; red del Tec; corte de internet real; acceso desde el celular.
