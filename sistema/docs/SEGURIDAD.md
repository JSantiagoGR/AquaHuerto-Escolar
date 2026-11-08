# Seguridad

## Eléctrica (la más importante)

- **El relevador SRD del módulo no se considera apto** para la bomba: está especificado ~3 A con carga inductiva a 28 VDC y la bomba pide ~6 A nominales con una corriente de arranque **desconocida**. Que una prueba haya funcionado no lo valida.
- Antes de cualquier activación real: relevador automotriz 30/40 A o MOSFET adecuado, **fusibles** (15 A batería, 10 A bomba, 3 A válvula y electrónica), **diodos** de rueda libre en bomba y válvula, cableado del calibre correcto e **interruptor de corte manual**. Medir la corriente de arranque de la bomba.
- El USB-C solo alimenta la placa: **nunca** cargas de 12 V.
- La ESP32 de pruebas solo tiene el USB-C conectado.
- Si un contacto se pega, el firmware lo detecta (`FLOW_WHEN_IDLE`) pero **no puede abrirlo**: el corte manual y el fusible son imprescindibles.

## Firmware (siempre activas, también sin red)

| Protección | Detalle |
|---|---|
| Arranque seguro | Salidas inactivas antes que nada; perfil A → modo MANUAL; potencia deshabilitada por defecto |
| Sin riego tras reiniciar | Perfil A siempre MANUAL; perfil B espera el intervalo mínimo y lecturas nuevas. Un reinicio durante un riego no lo reanuda: alarma `REBOOT_DURING_WATERING` |
| Potencia | `POWER ON CONFIRMAR` **solo por USB**; nunca por MQTT |
| Enclavamiento | Nunca bomba con válvula cerrada; válvula 300 ms antes de la bomba y cierre 300 ms después |
| Sin flujo | `NO_FLOW` a los 10 s sin pulsos con bomba encendida |
| Caudal anormal / bomba demasiado tiempo | `FLOW_HIGH`, `PUMP_TIMEOUT` (90 s por ciclo; tope duro del supervisor 330 s) |
| Supervisor independiente | Temporizador de 100 ms: corta si la bomba excede el límite o la tarea de control deja de latir; watchdog de tareas con reinicio |
| Límites | Litros por ciclo, por evento y por día; máximo de ciclos; humedad máxima y reserva superior |
| Tinaco | Bajo el mínimo o sin lectura válida → bloquea (si está calibrado; en perfil B es obligatorio calibrarlo) |
| Suelo sin respuesta | Bloquea el automático tras varios riegos sin aumento de humedad |
| Comandos | Duplicados, retenidos y viejos se rechazan; STOP siempre se ejecuta |
| Configuración | Validación completa y atómica; límites duros que MQTT no puede superar |

## Red

- Broker: sin anónimos, usuario y contraseña por cliente, **ACL** por árbol de topics (el simulador no puede comandar al ESP32 real), firewall solo subred local en red Privada. **No expuesto a internet.**
- Node-RED: editor con usuario y contraseña; dashboard con contraseña desde otros equipos; paleta bloqueada.
- Contraseñas: generadas aleatoriamente en `configs/secrets/credenciales_casa.env` (excluido de exportaciones y del paquete para la Pi; el empaquetador verifica que no se cuele ninguna). El broker guarda solo hashes. El Wi-Fi del ESP32 se escribe oculto y va directo a su NVS: no queda en archivos de la PC ni en registros.
- TLS con verificación de certificados para Open-Meteo (servidor y ESP32).

## Simulador

Usuario MQTT propio, topics `huerto/casa/sim_01/...`, actuadores virtuales, todos los datos marcados `simulated`. `SIM_CONTROL` solo se envía a dispositivos `sim*`.

## Riesgos residuales

Calibraciones provisionales (EC-5, YF-S201, tinaco), etapa de potencia no certificada, red del Tec no verificada, IA del ESP32 real sin datos. Ver [ESTADO_FINAL.md](ESTADO_FINAL.md).
