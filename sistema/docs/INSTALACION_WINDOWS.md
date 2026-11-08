# Instalación en Windows (lo que realmente se hizo)

Fecha: 2026-10-11 · Laptop Windows 11 Home · Wi-Fi `RED_DE_CASA_5` (5 GHz) · IP `IP_DE_LA_LAPTOP` (DHCP, puede cambiar).

## 1. Componentes que ya existían (no se reinstalaron)

| Componente | Versión verificada | Comando |
|---|---|---|
| ESP-IDF | v6.0.2 (`C:\esp\v6.0.2\esp-idf`) | `idf.py --version` |
| Node.js / npm | v24.19.0 / 11.17.0 | `node --version`, `npm --version` |
| Python | 3.14.6 | `python --version` |
| Git | 2.55.0 | `git --version` |
| VS Code | instalado (`code`) | `Get-Command code` |

## 2. Componentes instalados en esta sesión

| Componente | Versión | Cómo se instaló | Dónde |
|---|---|---|---|
| Mosquitto | 2.1.2 | `winget install --id EclipseFoundation.Mosquitto --version 2.1.2 --exact` (aceptando UAC) | `C:\Program Files\mosquitto` |
| Node-RED | 5.0.8 | `npm install node-red@5.0.8` **local** (no global) | `nodered\runtime` |
| FlowFuse Dashboard 2.0 | `@flowfuse/node-red-dashboard` 1.33.0 | `npm install` en el userDir aislado | `nodered\userdata` |
| node-red-node-sqlite | 2.0.1 (sqlite3 6.0.1, SQLite 3.52.0) | `npm install` + `npm approve-scripts sqlite3` + `npm rebuild sqlite3` | `nodered\userdata` |
| Entorno Python | venv con paho-mqtt 2.1.0, pyserial 3.5, ziglang 0.16.0, pypdf | `python -m venv .venv` + `pip install ...` | `.venv` |

Notas reales del proceso:
- npm 11 bloquea los scripts de instalación: fue necesario `npm approve-scripts sqlite3` para obtener el binario de SQLite.
- La primera instalación de Mosquitto se canceló en el aviso UAC; se repitió y el usuario la aceptó.
- `ziglang` (compilador de C para la PC) se usa para compilar la lógica del firmware como DLL (pruebas y simulador).
- No se instaló el paquete antiguo `node-red-dashboard`; no se creó ninguna cuenta de FlowFuse Cloud.

## 3. Configuración de administrador (una vez)

`configs\CONFIGURAR_BROKER_Y_FIREWALL.bat` (clic derecho → Ejecutar como administrador). Lo ejecutó el usuario y dejó:
- Reglas de firewall de entrada **solo subred local y perfil Privado**: `Riego Casa - MQTT 1883 (LAN)` y `Riego Casa - Node-RED 1880 (LAN)`.
- La red Wi-Fi de casa marcada como **Privada** (con confirmación del usuario).
- El servicio de Windows "mosquitto" configurado con `include_dir` hacia `mqtt\conf.d`. **Ese servicio no arrancó** con la cuenta del sistema (el archivo de registro que crea queda con permisos restringidos), así que el broker se ejecuta como proceso del usuario desde `iniciar_todo.ps1` con `mqtt\mosquitto_casa.conf`. Si el servicio llegara a arrancar en el futuro, `iniciar_todo.ps1` detecta el puerto ocupado y lo reutiliza (misma configuración, mismos usuarios).
- Para deshacer: `configs\admin_revertir_broker_firewall.ps1` (como administrador).

## 4. Base de datos y flujos

```bash
.venv\Scripts\python.exe database\inicializar_db.py
.venv\Scripts\python.exe dashboard\generar_flows.py --entorno casa
.venv\Scripts\python.exe nodered\desplegar_flows.py --entorno casa
```

`iniciar_todo.ps1 -Desplegar` hace los tres pasos.

## 5. Compilación de la lógica para la PC

```bash
powershell -File tests\host\build_host.ps1
```

Genera `tests\host\build\logic_tests.exe` (47 escenarios) y `riego_core.dll` (simulador).
