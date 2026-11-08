# Node-RED (instancia aislada)

| | |
|---|---|
| Versión | Node-RED 5.0.8 sobre Node.js 24.19.0 |
| Ejecutable | `nodered\runtime\node_modules\node-red\red.js` (instalación local, no global) |
| Directorio de usuario | `nodered\userdata` (propio: no comparte nada con otras prácticas) |
| Archivo de flujo | `nodered\userdata\flows_riego.json` (credenciales cifradas en `flows_riego_cred.json`) |
| Puerto | 1880 (estaba libre; escucha en 0.0.0.0, el firewall limita a la red local) |
| Editor | Protegido con usuario y contraseña (`adminAuth`); verificado: la API responde 401 sin token |
| Dashboard | FlowFuse Dashboard 2.0 (1.33.0) en `/dashboard` |
| Paleta | Bloqueada (no se instalan nodos desde el editor) |
| Diagnóstico y telemetría de Node-RED | Deshabilitados |

## Seguridad del dashboard

- Desde **esta computadora** (127.0.0.1) se entra sin contraseña.
- Desde **otro equipo de la red** (celular) pide usuario `huerto` y la contraseña `DASHBOARD_PASS` del archivo de secretos (Basic). Aplica a las páginas, al canal socket.io del dashboard y a `/riego/export.csv`. Verificado: 401 sin credenciales y 200 con ellas desde la IP de la red.

## Secretos

`settings.js` lee `configs\secrets\credenciales_casa.env` (o el archivo que indique `RIEGO_ENV_FILE`) y pasa los valores como variables de entorno. **Los flujos exportados no contienen contraseñas**: las credenciales del broker se agregan al desplegar (`nodered\desplegar_flows.py`) y Node-RED las guarda cifradas con `credentialSecret`. Verificado con búsqueda de texto.

## Persistencia

- Flujos y credenciales: archivos del userDir.
- Contexto persistente (`file`): dispositivo seleccionado, calibración del suelo, ubicación, versión de perfil, temperaturas diarias para grados-día. Verificado tras reiniciar Node-RED (el dispositivo seleccionado se conservó).
- Datos históricos: SQLite (`database\riego_casa.db`).

## Flujos

Se generan con `dashboard\generar_flows.py` (125 nodos, 3 pestañas):

1. **Riego - Datos y comandos:** ingesta MQTT → SQLite, ACK de comandos, alertas, estado para el dashboard.
2. **Riego - Servicios:** SQLite (escritura y consulta), Open-Meteo (cada 30 min), crecimiento (cada 10 min), IA del servidor (cada 5 min), vigilancia (cada minuto), respaldos (03:00), exportación CSV.
3. **Riego - Dashboard:** 10 páginas (plantillas Vue) y notificaciones.

El código de cada función está en `dashboard\funciones\*.js` y cada página en `dashboard\plantillas\*.vue`.

## Comandos

```bash
.venv\Scripts\python.exe dashboard\generar_flows.py --entorno casa
.venv\Scripts\python.exe nodered\desplegar_flows.py --entorno casa
```

Registro: `nodered\logs\nodered.log`.
