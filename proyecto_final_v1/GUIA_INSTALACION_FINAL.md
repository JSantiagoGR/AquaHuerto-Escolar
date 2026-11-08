# Guía de instalación final: paso del MODO A (pruebas) al MODO B (instalación)

| | MODO A — Pruebas (activo) | MODO B — Instalación final |
|---|---|---|
| Al encender | Sensores, red y publicación; **automático deshabilitado siempre** | Inicializa y **restaura el automático** si estaba habilitado |
| Riego manual | Permitido con potencia habilitada; tinaco sin calibrar = advertencia | Exige tinaco calibrado y válido |
| Riego automático | Solo tras `AUTO ON` explícito | Arranca solo; espera `min_event_gap_min` tras el arranque |
| Cambiar a este modo | `MODO A` (consola) | `MODO B CONFIRMAR` (consola; exige potencia y tinaco calibrado) |
| Protecciones | Todas | Todas |

El modo y la potencia **no se pueden cambiar por MQTT**.

## Etapa 1 — Hardware (ver [PENDIENTES_HARDWARE.md](PENDIENTES_HARDWARE.md))
- [ ] Bomba conmutada por relevador automotriz 30/40 A o MOSFET adecuado.
- [ ] Fusibles F1 15 A, F2 10 A, F3 3 A; diodos de rueda libre; corte manual.
- [ ] EC-5 enterrado, cable protegido, 1 MΩ de GPIO34 a GND.
- [ ] PING))) sobre el tinaco, centrado, perpendicular al agua, protegido de la lluvia.
- [ ] DHT22 a la sombra, ventilado, lejos de superficies calientes.
- [ ] YF-S201 con la flecha en sentido del flujo.
- [ ] Alimentación del ESP32 verificada (USB del controlador o buck).
- [ ] Caja de la electrónica protegida del agua.

## Etapa 2 — Verificación sin potencia (modo A)
1. Conecte el USB y abra la consola.
2. `SELFTEST` → **33 PASS, 0 FAIL**.
3. `PINES` → "SIN CONFLICTOS".
4. `ESTADO` → revise que el EC-5, el tinaco y el DHT22 den lecturas válidas.
5. Verifique la hora: `ESTADO` muestra la fecha y hora de Chihuahua (requiere Wi-Fi y NTP).

## Etapa 3 — Calibraciones
1. **Tinaco:**
   - Mida la distancia del sensor a la superficie con el tinaco **lleno** (`ESTADO`, "dist") y con el nivel **vacío útil** (la altura de la toma de la bomba). Si no puede vaciarlo, mida con cinta la profundidad del tinaco y réstela a la lectura lleno.
   - `TINACO <vacio_cm> <lleno_cm>`. Ejemplo: `TINACO 120 20`.
   - `SET tank_min_pct 20` (o el mínimo elegido; deje margen sobre la toma para no aspirar aire).
2. **Caudalímetro:** procedimiento de [CALIBRACION_YFS201.md](CALIBRACION_YFS201.md).
3. **EC-5:** recomendable recalibrar con la tierra del cajón ([CALIBRACION_EC5.md](CALIBRACION_EC5.md)).
4. **Humedad del cultivo:** `HUMEDAD <min> <obj> <max>` ([CONFIGURACION_HUMEDAD.md](CONFIGURACION_HUMEDAD.md)).

## Etapa 4 — Pruebas físicas con agua (modo A)
1. `POWER ON CONFIRMAR`.
2. `START 0.5` → verifique la secuencia (clic de válvula, bomba), el corte por volumen y que **no haya goteo** tras cerrar.
3. `START 1` × 3 → compare con el recipiente graduado.
4. **Prueba de STOP:** `START 2` y a los 5 s `STOP`.
5. **Prueba de falta de agua:** saque la succión del agua, `START 1` → debe cortar a los `no_flow_s` (10 s) con `NO_FLOW`. Vuelva a sumergirla y ejecute `CLEAR ALL`.
6. **Prueba de corte manual:** con la bomba encendida, el corte manual debe apagarla.
7. Ciclo automático supervisado: `AUTO ON` en horario y observe decisión, ciclo, infiltración y siguiente lectura. Supervise al menos 2 eventos completos.

## Etapa 5 — Pasar a modo B
```
MODO B CONFIRMAR
AUTO ON
ESTADO
```
Requisitos que el firmware exige: `power_enabled = 1` y tinaco calibrado. El estado del automático queda guardado (`auto_saved`) y se restaura al encender.

Prueba de rearranque: desconecte la alimentación del ESP32 10 s y vuelva a conectar. Debe arrancar en modo B, con el automático habilitado, sin regar de inmediato (espera `min_event_gap_min`) y con la bomba apagada.

## Volver a modo A (mantenimiento)
`MODO A` → el automático se deshabilita. `POWER OFF` si va a manipular el hardware.

## Dashboard
Con el modo B activo, el dashboard muestra "Modo B". Antes de dejar el sistema sin supervisión: autenticación en el broker y ACL ([CONFIGURACION_MQTT.md](CONFIGURACION_MQTT.md)).
