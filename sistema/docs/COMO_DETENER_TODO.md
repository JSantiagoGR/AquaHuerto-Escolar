# Cómo detener todo

```bash
powershell -ExecutionPolicy Bypass -File C:\ESP32_Riego_Automatico\Pruebas_Casa_ESP32_v1\scripts\detener_todo.ps1
```

- Detiene **solo** lo que inició `iniciar_todo.ps1` (simulador, Node-RED, Mosquitto de usuario), usando los PID de `run\`.
- No toca otras instancias de Node-RED ni el servicio de Windows de Mosquitto.
- Los datos quedan en `database\riego_casa.db`; flujos y ajustes persisten para el siguiente inicio.
- El ESP32 sigue funcionando solo con sus protecciones locales (sin MQTT guarda muestras en RAM y las envía al volver).

Para apagar la ESP32: desconecte el USB-C (las salidas quedan inactivas al no tener alimentación).
