# Migración a la Raspberry Pi (entorno definitivo)

**No se ha tocado la Raspberry Pi.** Este documento y `migration_raspberry_pi/` dejan todo listo.

Datos anteriores de referencia (**verificar al migrar**, pueden haber cambiado): Pi `raspberrypi.local`, MQTT 1883, Node-RED 1880, dashboard antiguo `/ui`, flujo "Equipo 2", topics `equipo2/agua|estado|control|nivel`, red `RouterHuerto1`.

## Principios

- **Instalación independiente**: segunda instancia de Node-RED en el puerto **1881** con su propio userDir y su propio Dashboard 2.0 en `/dashboard`. El Node-RED de "Equipo 2" (1880, `/ui`, paquete antiguo `node-red-dashboard`) **no se modifica ni se sobrescribe**.
- **Broker**: el sistema nuevo usa un **listener adicional autenticado en 1884** (archivo aparte en `/etc/mosquitto/conf.d/`). El 1883 de Equipo 2 queda igual. Se respalda `mosquitto.conf` antes y, si Mosquitto no arranca, el instalador retira el archivo nuevo.
- **Topics separados**: `huerto/final/esp32_principal/...` (nunca `huerto/casa/...` ni `equipo2/...`).
- **Credenciales nuevas**: no se copian las de casa (la plantilla obliga a cambiarlas).
- Misma base de código: firmware, funciones y páginas idénticos; solo cambia la configuración.

## Contenido de `migration_raspberry_pi/`

| Archivo | Uso |
|---|---|
| `flows/flows_riego_final.json` | Flujo completo + dashboard (10 páginas) para el entorno final, sin contraseñas |
| `flows/flows_riego_casa_referencia.json` | El flujo de casa, de referencia |
| `nodered/settings.js`, `package.json`, `package_runtime.json` | Ajustes y dependencias exactas |
| `database/schema.sql`, `inicializar_db.py`, `cultivos_base.json` | Esquema y carga inicial |
| `mqtt/mosquitto_riego_final.conf`, `acl_final.conf` | Listener 1884 y ACL |
| `configs/credenciales_final.env.ejemplo` | Plantilla de credenciales (cambiar TODO) |
| `scripts/instalar_pi.sh` | Instalación (`--broker`, `--servicio`) |
| `scripts/iniciar_detener_pi.sh` | iniciar / detener / estado / logs |
| `scripts/respaldar_pi.sh`, `restaurar_pi.sh` | Respaldo verificado y restauración segura |
| `scripts/desplegar_flows.py` | Despliegue por la Admin API |
| `firmware/provisionar_red.py` | Red del ESP32 original |
| `simulation/compilar_core_linux.sh` | Lógica del firmware para Linux (simulador y pruebas) |

## Versiones de referencia (casa)

Node.js 24.19.0 · Node-RED 5.0.8 · @flowfuse/node-red-dashboard 1.33.0 · node-red-node-sqlite 2.0.1 (sqlite3 6.0.1) · Mosquitto 2.1.2 · ESP-IDF 6.0.2 · espressif/mqtt 1.1.0 · espressif/cjson 1.7.19 · Python 3.14 · paho-mqtt 2.1.0.
En la Pi: Node-RED 5 requiere **Node ≥ 22.9**. Si la Pi tiene Node 18/20 (lo usa Equipo 2), el instalador usa la última **Node-RED 4.x** en lugar de actualizar Node.js (para no romper Equipo 2).

## Nodos necesarios

`@flowfuse/node-red-dashboard` (Dashboard 2.0) y `node-red-node-sqlite`; el resto son nodos básicos (mqtt in/out, function, link, http request, http in/response, inject, status, catch, switch).

## Pasos

1. **En la laptop:** `scripts\empaquetar_para_pi.ps1` → `backups\paquete_raspberry_pi_<fecha>.zip` (sin secretos, bases ni node_modules; verifica que no haya contraseñas).
2. Copiar el zip a la Pi y descomprimir, por ejemplo en `~/riego_final`.
3. `cp migration_raspberry_pi/configs/credenciales_final.env.ejemplo configs/secrets/credenciales_final.env` y poner contraseñas nuevas (`openssl rand -base64 18`).
4. Revisar la configuración actual de Mosquitto: `cat /etc/mosquitto/mosquitto.conf; ls /etc/mosquitto/conf.d`. Si ya usa `per_listener_settings` o define listeners de forma incompatible, ajuste `mosquitto_riego_final.conf` antes de seguir.
5. `bash migration_raspberry_pi/scripts/instalar_pi.sh --broker --servicio`
6. Dashboard: `http://<IP de la Pi>:1881/dashboard` (el `/ui` de Equipo 2 en 1880 sigue igual).
7. Firewall (si `ufw` está activo): `sudo ufw allow from 192.168.0.0/24 to any port 1881,1884 proto tcp` (ajuste la subred real).
8. Cron de respaldo: `crontab -e` → `0 3 * * * bash ~/riego_final/migration_raspberry_pi/scripts/respaldar_pi.sh`.

## Firmware del ESP32 original

1. **Respaldar su flash primero** (igual que se hizo con la de casa):
   `python -m esptool --port COMx --baud 115200 read-flash 0 0x400000 respaldo_esp32_original.bin`
2. Compilar y flashear el mismo firmware: `idf.py -p COMx -b 115200 erase-flash flash`.
3. Red, broker y topic del entorno final (la contraseña Wi-Fi se pide oculta):
   ```bash
   python firmware/tools/provisionar_red.py --port COMx --red huerto --ssid RouterHuerto1 --broker mqtt://<IP de la Pi>:1884 --topic huerto/final/esp32_principal --device esp32_principal --entorno final --env-file configs/secrets/credenciales_final.env
   ```
4. Por USB: `SELFTEST` (49/49), `PINES`, calibrar tinaco (`TINACO <vacío> <lleno>`), YF-S201 (`CALFLUJO`), EC-5 y suelo.
5. Solo tras el checklist eléctrico: `POWER ON CONFIRMAR` y `PERFIL B CONFIRMAR`.

## Checklist de validación física

- [ ] Etapa de potencia apta para ~6 A + arranque (relevador automotriz o MOSFET), fusibles 15/10/3 A, diodos, corte manual.
- [ ] Corriente de arranque de la bomba medida.
- [ ] Polaridad de relevadores confirmada (activo en bajo) con la bomba desconectada.
- [ ] Secuencia válvula → bomba → corte → cierre verificada sin agua y luego con agua.
- [ ] `NO_FLOW` comprobado con la succión fuera del agua.
- [ ] YF-S201 calibrado con recipiente (3 repeticiones).
- [ ] Tinaco calibrado (vacío y lleno) y nivel mínimo probado.
- [ ] EC-5 conectado (GPIO25/34 + 1 MΩ), lecturas estables, FC/WP del suelo registrados.
- [ ] DHT22 y PING))) leyendo.
- [ ] Wi-Fi `RouterHuerto1`, MQTT 1884, NTP y Open-Meteo verificados.
- [ ] STOP desde el dashboard y por consola.
- [ ] Corte de energía durante un riego: no se reanuda y queda la alarma.
- [ ] 1 semana en modo AUTOMÁTICO observado antes de usar IA.
- [ ] Flujo Equipo 2 y su `/ui` siguen funcionando igual.
