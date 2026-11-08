# Seguridad

> **El software no reemplaza fusibles, protecciones ni dispositivos de conmutación correctamente dimensionados.**
> Las protecciones del firmware reducen riesgos; no los eliminan.

## 1. Riesgo principal pendiente: la etapa de potencia de la bomba
- El módulo usa relevadores **Songle SRD-05VDC-SL-C (forma C)**. Su hoja de datos indica **3 A a 28 VDC con carga inductiva**. El "10 A" impreso en la carcasa es para carga **resistiva**.
- La bomba GOOD PUMPS anuncia **6 A nominales**, con una corriente de arranque **desconocida** (sin medir) y un presostato que la arranca y para por su cuenta.
- En las Pruebas 01–03 la bomba se conectó directo al contacto NO del relevador K1 y funcionó en pocos ciclos. **Eso no certifica el relevador para uso repetitivo**: el arco de cada arranque desgasta el contacto y puede **soldarlo**.
- **Contacto pegado = la bomba sigue encendida aunque el firmware la apague.** El firmware lo detecta como `FLOW_WHEN_IDLE` (pulsos con todo apagado) y pasa a FAULT, pero **no puede abrir un contacto soldado**.

**Antes del modo B (obligatorio):**
1. Bomba conmutada por un **relevador automotriz 12 V de 30/40 A** (bornes 30/87/85/86) accionado por el canal K1, o por un **módulo MOSFET** de ≥ 30 A / ≥ 30 V con compuerta compatible con 3.3 V. Ver [CONEXIONES_ELECTRICAS.md](CONEXIONES_ELECTRICAS.md).
2. **Fusible** de 10 A en el positivo de la bomba y fusible principal de 15 A junto a la batería.
3. **Diodo de rueda libre** en la bomba (Schottky ≥ 5 A, cátodo al +), en la electroválvula (1N4007) y en la bobina del relevador automotriz.
4. **Medio de corte manual** accesible: interruptor o desconectador en el positivo de la batería, rotulado "CORTE BOMBA".

## 2. Protecciones implementadas en el firmware
| Protección | Cómo |
|---|---|
| Arranque seguro | `actuators_init()` es la primera instrucción: nivel inactivo **antes** de configurar el pin como salida |
| Versión segura por defecto | `power_enabled = 0`: los GPIO de potencia no se activan hasta `POWER ON CONFIRMAR` por consola serial |
| Modo A al encender | Riego automático **siempre deshabilitado** al arrancar en modo A |
| Enclavamiento | La bomba no se energiza si la válvula no está energizada (en la lógica y en `actuators`) |
| Secuencia | Válvula → 300 ms → bomba; al terminar, bomba OFF → 300 ms → válvula OFF (probada físicamente) |
| STOP prioritario | Apaga los GPIO en la propia tarea que recibe la orden (consola o MQTT) **antes** de encolarla; queda un *latch* que impide reactivar hasta que el control procese el STOP |
| Volumen | Corte por pulsos del YF-S201, no por tiempo |
| Sin flujo | `no_flow_s` (10 s) sin pulsos con bomba encendida → `NO_FLOW` (FAULT) |
| Caudal anormal | > `flow_max_lpm` (8 L/min) en 3 ventanas de 1 s → `FLOW_HIGH` (FAULT) |
| Tiempo de bomba | `pump_max_s` (90 s) por ciclo → `PUMP_TIMEOUT` (FAULT) |
| Supervisor independiente | `esp_timer` cada 100 ms: corta si la bomba física supera `pump_max_s + 10 s` (tope absoluto 330 s) o si la tarea de control deja de dar señales 3 s con alguna salida activa → `SAFETY_TRIP` |
| Watchdog de tareas | La tarea de control está suscrita al TWDT (5 s, pánico → reinicio → salidas seguras) |
| Flujo con todo apagado | ≥ 20 pulsos en 1 min con bomba y válvula apagadas → `FLOW_WHEN_IDLE` (posible contacto pegado o fuga) |
| Volumen por evento / diario | `max_liters_event` (3 L, tope 10), `max_liters_daily` (10 L, tope 50) |
| Ciclos | `max_cycles` (3, tope 6) e intervalo mínimo entre eventos |
| Suelo sin respuesta | Sin aumento ≥ `min_response_pp` tras `response_cycles` ciclos → `SOIL_NO_RESPONSE` (bloquea el automático) |
| Tinaco | Calibrado: bloqueo bajo `tank_min_pct` y corte del riego si baja durante el bombeo. Sin calibrar: el automático no riega; en modo B tampoco el manual |
| Sensores inválidos | EC-5 inválido → no hay riego automático. Sensor de nivel sin datos (calibrado) → bloqueo |
| Reinicio durante un riego | Se detecta al arrancar (marca en NVS), **no se reanuda** y se activa `REBOOT_DURING_WATERING` |
| Parámetros | Límites duros por parámetro, validación de relaciones y CRC en NVS |
| MQTT | `id` obligatorio, rechazo de duplicados, retenidos y antiguos; token opcional; potencia, modo y simulación **no** se controlan por MQTT |
| Red | El riego y sus límites funcionan sin Wi-Fi ni MQTT. La red nunca reinicia el sistema |
| Brownout | Detector activado: ante una caída de tensión el ESP32 se reinicia con salidas seguras |

## 3. Limitaciones que debe cubrir el hardware
1. **Reinicio:** entre el reset y `app_main` (~0.3 s) los GPIO quedan en alta impedancia. Con el módulo activo en BAJO, una entrada flotante **no** activa el relevador, porque no hay camino a GND para el LED del optoacoplador. Si se cambia por un módulo activo en ALTO, agregar 10 kΩ de *pull-down* en IN1/IN2.
2. **Pérdida de alimentación del ESP32:** usar contactos **NO** y válvula **NC**. Sin energía, todo queda apagado.
3. **Realimentación:** el VCC del módulo de relevadores debe salir del mismo 5 V que el ESP32.
4. **Contacto pegado:** solo se corrige con la etapa de potencia adecuada y el corte manual.
5. **Presostato de la bomba:** arranca y para el motor por su cuenta mientras el relevador está cerrado.
6. **Presión:** el presostato corta a 0.9 MPa (~130 psi). Verifique que la electroválvula, las mangueras y las uniones lo soporten. El firmware nunca enciende la bomba con la válvula cerrada, pero una obstrucción aguas abajo sí puede ocurrir.

## 4. Acciones restringidas a la consola serial (presencia física)
| Acción | Comando | Motivo |
|---|---|---|
| Habilitar potencia | `POWER ON CONFIRMAR` | Primera energización tras revisar el hardware |
| Modo B | `MODO B CONFIRMAR` (requiere potencia y tinaco calibrado) | Riego sin supervisión |
| Simulación | `SIM ON` / `SIM OFF` | Cambia el origen de los datos |
| Fábrica | `FABRICA CONFIRMAR` | Borra la configuración (vuelve a potencia OFF y modo A) |

## 5. Red MQTT
- Usar un broker con **usuario y contraseña** y una ACL: solo Node-RED publica en `huerto/esp32/command`; el ESP32 publica en el resto.
- Configurar `CONFIG_RIEGO_CMD_TOKEN` si la red es compartida.
- Las credenciales están en `sdkconfig.secrets` (no versionado). No las copie en documentos ni capturas.
- MQTT sin TLS envía todo en texto plano: úselo solo en la red local del huerto.

## 6. Antes de energizar (lista corta)
- [ ] Etapa de potencia de la bomba adecuada (relevador automotriz o MOSFET).
- [ ] Fusibles F1 15 A, F2 10 A y F3 3 A colocados.
- [ ] Diodos de rueda libre con la polaridad correcta (cátodo al +).
- [ ] Corte manual accesible.
- [ ] Sin cortos: resistencia +12 V a (−) con todo apagado.
- [ ] Succión con agua y descarga libre.
- [ ] `SELFTEST` con 33 PASS en la placa real.
