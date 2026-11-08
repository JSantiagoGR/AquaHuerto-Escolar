# Pruebas realizadas

Leyenda: **FÍSICA** = con hardware real · **EMULADOR** = firmware completo en QEMU (sin sensores, Wi-Fi ni salidas reales) · **LÓGICA** = SELFTEST sobre la máquina de estados pura · **ESTÁTICA** = sin ejecutar.

> Una prueba simulada o emulada **no valida el hardware**.

## 1. Compilación (ESTÁTICA) — 2026-10-11
| Variante | Resultado | Tamaño |
|---|---|---|
| Placa (`build/`) | **OK**, 0 warnings (21 archivos de `main` recompilados con `-Wall -Wextra -Werror`) | 1 013 188 B; app 0xF7640 de 0x177000 (34 % libre); IRAM 70 %, DRAM 23 % |
| Emulador (`build_qemu/`, sin Wi-Fi) | **OK**, 0 warnings | 0x49280 B |

## 2. Validación estática (`tools/validate_project.py`) — **OK**
- GPIO: 26, 27, 19, 18, 4, 25, 34, sin repetidos ni pines prohibidos. GPIO34 = ADC1_CH6.
- `EJEMPLOS_MQTT.json` y `node-red/flow_dashboard_riego.json` válidos.
- Los 26 comandos de ejemplo existen en el firmware.
- La contraseña Wi-Fi no aparece en ningún archivo del proyecto (fuera de `sdkconfig*` y `build`).
- El flow de Node-RED (81 nodos) no tiene cables a nodos inexistentes.

## 3. SELFTEST de la lógica (LÓGICA, ejecutado dentro del firmware en QEMU) — **33/33 PASS**
| # | Escenario | Resultado |
|---|---|---|
| 1 | Tierra seca inicia riego automático | PASS |
| 2 | Tierra húmeda no riega | PASS |
| 3 | Tierra sobre el máximo bloquea agua (manual solo con force) | PASS |
| 4 | Tinaco lleno permite riego | PASS |
| 5 | Tinaco vacío bloquea riego | PASS |
| 6 | Sensor de tinaco sin datos bloquea | PASS |
| 7 | EC-5 inválido no riega | PASS |
| 8 | Caudal normal entrega 1 L por pulsos (1000–1025 mL) | PASS |
| 9 | Sin flujo → falla NO_FLOW y todo apagado | PASS |
| 10 | Pulsos erráticos → falla FLOW_HIGH | PASS |
| 11 | Manual 1 L: válvula, 300 ms, bomba … bomba OFF, 300 ms, válvula OFF | PASS |
| 12 | Automático por humedad baja completa ciclo | PASS |
| 13 | Espera de infiltración (15 min) con salidas apagadas | PASS |
| 14 | Segundo ciclo si continúa seco | PASS |
| 15 | Fin del evento al alcanzar objetivo | PASS |
| 16 | Máximo de ciclos por evento | PASS |
| 17 | Máximo de litros diarios | PASS |
| 18 | STOP inmediato durante riego | PASS |
| 19 | Sin MQTT el riego termina con límites locales | PASS |
| 20 | Comandos MQTT duplicados se descartan | PASS |
| 21 | Parámetros inválidos rechazados | PASS |
| 22 | Reinicio durante riego: no reanuda y alarma | PASS |
| 23 | Falla del DHT22: alarma, pero no bloquea | PASS |
| 24 | Recuperación tras CLEAR_ALARM | PASS |
| 25 | Sin hora: no hay riego por horario; emergencia limitada | PASS |
| 26 | Mediodía y fuera de horario posponen | PASS |
| 27 | Temperatura alta pospone riego rutinario | PASS |
| 28 | Suelo sin respuesta bloquea el automático (manual sigue) | PASS |
| 29 | Emergencia: un ciclo y espera entre emergencias | PASS |
| 30 | Flujo con todo apagado (contacto pegado) → falla | PASS |
| 31 | Manual rechazado durante evento automático | PASS |
| 32 | Sin potencia no se puede regar | PASS |
| 33 | Conversiones EC-5 (Act. 2.2) y nivel del tinaco | PASS |

En cada paso se comprueba además la invariante "nunca bomba con válvula cerrada".

Correcciones hechas durante estas pruebas: los fallos iniciales de los escenarios 11, 14 y 29 eran errores del propio banco de pruebas (registro del instante de apertura, momento de la verificación y número de lecturas de confirmación), no de la lógica.

## 4. Integración del firmware completo (EMULADOR QEMU, `tools/qemu_test.py`) — **32/32 PASS**
Resultado completo: `resultado_qemu.txt`.

| Grupo | Pruebas |
|---|---|
| Arranque | Arranque completo; modo A con potencia deshabilitada; automático apagado al encender |
| Seguridad | START y AUTO ON rechazados sin potencia; parámetro inválido rechazado; límite duro de bomba no superable; rango de humedad válido guardado en NVS |
| SELFTEST | 33/33 dentro del firmware |
| Riego manual (simulación, tiempo real ×1) | 1 L termina por volumen (1.00–1.02 L calculados); STOP inmediato |
| Comandos MQTT por el procesador real (`JSON …`) | OK; DUPLICATE; START retenido → RETAINED (no riega); sin `id` → INVALID; JSON inválido → INVALID; rango inválido → REJECTED; volumen fuera de límite → INVALID; START_MANUAL + STOP por JSON |
| Fallas | Sin flujo → NO_FLOW + FAULT; START rechazado en FAULT; CLEAR_ALARM recupera |
| Automático (simulación ×60) | Riego por humedad baja en horario; espera de infiltración; fin del evento al alcanzar el objetivo; mediodía pospone; sin hora no riega |
| Corte de energía | Se mató el emulador a mitad de un riego y se rearrancó con la misma flash: no reanuda, alarma `REBOOT_DURING_WATERING`, modo A, potencia deshabilitada, historial NVS con `REBOOT` |

### Problemas encontrados y resueltos durante la integración
1. **Pánico al iniciar el Wi-Fi en QEMU** (`assert esp_phy_enable`): QEMU no emula la radio. Se creó la variante `build_qemu` sin Wi-Fi (`CONFIG_RIEGO_SIN_RED`, solo para el emulador). Además, una falla de inicio de red o del PCNT ya no reinicia el ESP32: se registra y el sistema sigue en local.
2. **Bloqueo total al guardar en NVS** (diagnosticado con GDB): el núcleo 1 esperaba una conversión ADC que QEMU nunca completa, con interrupciones bloqueadas, y la escritura en flash del núcleo 0 esperaba al núcleo 1. Corrección: sin calibración ADC disponible no se lee el ADC (`ADC_ERROR`). En la placa real la calibración existe y la conversión dura microsegundos.
3. **`esp_restart()` en QEMU** termina en `InstrFetchProhibited`: es una limitación del emulador. La prueba de reinicio se hace con un corte del emulador, que equivale a un corte de energía.
4. La UART emulada es muy lenta: se ajustaron los tiempos de espera del guion; no es un problema del firmware.

## 5. Pruebas físicas previas (FÍSICA, firmware de las Pruebas 01–03, 2026-10-09)
| Prueba | Resultado |
|---|---|
| Polaridad del módulo de relevadores | Activo en BAJO, confirmado |
| Bomba 10 s con secuencia de válvula | 10 009 ms; el agua se corta al cerrar |
| Riego de 1 L con el YF-S201 | 450 pulsos objetivo en 19.7 s; 455 al cerrar (~1011 mL calculados); 3.5–4.5 L/min |
| Sin agua en la succión | Ciclos de 60 s con 0 pulsos (revelaron la necesidad de cortar por falta de flujo, que el firmware nuevo implementa) |
| PING))) | 94.9 cm / 232 cm según la orientación; responde a obstáculos |
| DHT22 | 21.5 °C, 53.7 %HR |

Ninguno de esos volúmenes se midió con recipiente.

## 6. NO realizadas (requieren hardware o red)
| Prueba | Motivo |
|---|---|
| Flashear el Proyecto Final v1 y SELFTEST en la placa | ESP32 no conectado |
| EC-5 en GPIO25/34 | Sin conexión física en este proyecto |
| Wi-Fi, NTP y broker MQTT reales | La PC estaba en otra red; QEMU no emula Wi-Fi |
| Riego con agua usando el firmware nuevo | Requiere autorización y la etapa de potencia certificada |
| Calibración del YF-S201 y del tinaco | Requiere recipiente y medidas del tinaco |
