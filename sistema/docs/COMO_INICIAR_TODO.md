# Cómo iniciar todo

Un solo comando (no requiere administrador):

```bash
powershell -ExecutionPolicy Bypass -File C:\ESP32_Riego_Automatico\Pruebas_Casa_ESP32_v1\scripts\iniciar_todo.ps1 -Simulador -Abrir
```

| Opción | Efecto |
|---|---|
| (ninguna) | Broker + base de datos + Node-RED |
| `-Simulador` | Inicia también el simulador `sim_01` (datos SIMULADOS) |
| `-Abrir` | Abre <http://localhost:1880/dashboard> |
| `-Desplegar` | Regenera y vuelve a desplegar el flujo |

Pasos que hace:
1. **Mosquitto** en 1883 con `mqtt\mosquitto_casa.conf` (si ya hay un broker escuchando, lo reutiliza).
2. **SQLite**: crea o actualiza las tablas sin borrar nada y carga los 10 cultivos.
3. **Node-RED** aislado en 1880 (espera a que responda, hasta 60 s).
4. **Simulador** (opcional).
5. Muestra las direcciones (incluida la del celular).

Los procesos quedan en segundo plano; sus PID se guardan en `run\*.pid`.

## ESP32

Conectada por USB-C, arranca sola (modo MANUAL, potencia deshabilitada). Cuando tenga Wi-Fi se conecta sola al broker. Para ver su consola:

```bash
python -m serial.tools.miniterm COM8 115200 --dtr 0 --rts 0 --eol CRLF --encoding utf-8
```

## Registros

`nodered\logs\nodered.log`, `mqtt\log\broker_usuario.log`, `simulation\simulador.log`.
