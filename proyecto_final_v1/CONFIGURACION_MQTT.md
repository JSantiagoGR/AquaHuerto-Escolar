# Configuración de Wi-Fi y MQTT

## Credenciales (no versionadas)
Están en `sdkconfig.secrets`, en la raíz del proyecto, que está en `.gitignore`. Se generó copiando los valores del proyecto anterior `Practica4_MQTT` (red `RouterHuerto1`, broker `mqtt://raspberrypi.local:1883`). La contraseña no aparece en ningún documento ni en el log del ESP32.

```
CONFIG_RIEGO_WIFI_SSID="..."
CONFIG_RIEGO_WIFI_PASSWORD="..."
CONFIG_RIEGO_MQTT_URI="mqtt://raspberrypi.local:1883"
CONFIG_RIEGO_MQTT_USERNAME=""
CONFIG_RIEGO_MQTT_PASSWORD=""
CONFIG_RIEGO_CMD_TOKEN=""
```
Plantilla: `sdkconfig.secrets.example`. **Al cambiar el archivo, borre `sdkconfig`** para que se apliquen los valores nuevos, y vuelva a compilar.

Aviso: `sdkconfig` y la carpeta `build/` contienen esos valores después de compilar. Tampoco se versionan.

## Comportamiento
| Aspecto | Implementación |
|---|---|
| Wi-Fi | Estación; reconexión automática con espera creciente de 1 s a 60 s |
| Hora | SNTP (`pool.ntp.org`) al obtener IP; zona `CST6` (Chihuahua, UTC−6 sin horario de verano). Para Cd. Juárez: `SET tz MST7MDT,M3.2.0,M11.1.0` |
| Cliente MQTT | esp-mqtt 1.1.0 (componente `espressif/mqtt`, el mismo del proyecto anterior), MQTT 3.1.1, keepalive 15 s, reconexión cada 5 s |
| Client ID | `riego-XXXXXX` (últimos 3 bytes de la MAC) |
| Sesión | **Limpia**: el broker no acumula comandos viejos |
| LWT | `huerto/esp32/status` = `{"online":false,"reason":"LWT"}`, QoS 1, retenido |
| Al conectar | Publica `status` `{"online":true}`, `config`, `decision` y `state` (retenidos) y se suscribe a `command` (QoS 1) |
| Publicación | En cola (`esp_mqtt_client_enqueue`): no bloquea la tarea de control |
| Sin broker | Todo el control, las protecciones y los límites siguen funcionando en local. Alarma informativa `COMMS` |

## Seguridad recomendada (antes del modo B)
1. **Mosquitto con usuario y contraseña** (`password_file`) y `allow_anonymous false`.
2. **ACL**:
   ```
   user nodered
   topic write huerto/esp32/command
   topic read huerto/esp32/#
   user esp32riego
   topic read huerto/esp32/command
   topic write huerto/esp32/#
   ```
3. Defina `CONFIG_RIEGO_MQTT_USERNAME` y `CONFIG_RIEGO_MQTT_PASSWORD` en `sdkconfig.secrets`.
4. Opcional: `CONFIG_RIEGO_CMD_TOKEN` (los comandos de accionamiento y `SET_*` deben incluir `"token"`).
5. MQTT sin TLS: úselo solo en la red local del huerto.

## Verificación pendiente
Durante el desarrollo **no hubo conexión real a un broker**: la PC estaba en otra red (`raspberrypi.local:1883` no respondía) y el ESP32 no estaba conectado. Cuando esté en `RouterHuerto1`:
1. Consola: `wifi: Conectado, IP ...` y `mqtt: Conectado al broker`.
2. En otra PC: `mosquitto_sub -h raspberrypi.local -t "huerto/esp32/#" -v`.
3. `mosquitto_pub -h raspberrypi.local -t huerto/esp32/command -m "{\"id\":\"t1\",\"cmd\":\"GET_STATUS\"}"` → debe llegar `ack` con `OK`.
4. Repita el mismo `id` → `DUPLICATE`. Publique con `-r` (retenido) → `RETAINED`.
5. Apague el ESP32 → en ~20 s llega `status` `{"online":false}` (LWT).
