# Configuración Wi-Fi del ESP32 (sin recompilar)

Las redes se guardan en la NVS del ESP32 (espacio `net`, con CRC). Hay tres ranuras:

| Ranura | Uso |
|---|---|
| `casa` | Wi-Fi de la casa (pruebas) |
| `tec` | Red del Tec (ver limitaciones) |
| `huerto` | `RouterHuerto1` (Raspberry Pi) |

El ESP32 intenta la red **preferida**; tras 4 fallos seguidos prueba la siguiente habilitada. Reconecta con espera creciente de 1 a 30 s. **El riego nunca depende del Wi-Fi**: todas las protecciones son locales.

## Forma recomendada (la contraseña no queda en ningún archivo)

Doble clic en `configs\CONFIGURAR_WIFI_ESP32.bat` (ESP32 conectada por USB):
1. Pide el nombre de la red (Enter = `RED_DE_CASA_2.4`).
2. Pide la contraseña **sin mostrarla** (getpass).
3. La envía al ESP32 por USB en hexadecimal (admite espacios y símbolos), junto con el broker (IP actual de esta PC), el usuario MQTT del archivo de secretos y el topic.
4. Muestra `RESULTADO: Wi-Fi ... | MQTT ...`.

Equivalente en terminal:

```bash
.venv\Scripts\python.exe firmware\tools\provisionar_red.py --port COM8 --red casa --ssid RED_DE_CASA_2.4
```

**Importante:** el ESP32 solo usa **2.4 GHz**. La laptop está en `RED_DE_CASA_5` (5 GHz); el ESP32 debe usar `RED_DE_CASA_2.4` (visible, canal 1, WPA2-Personal). Ambas son del mismo módem.

## Comandos de consola (USB)

| Comando | Efecto |
|---|---|
| `RED` | Muestra redes, broker y estado **sin contraseñas** |
| `RED DIAG` | Publica el diagnóstico por MQTT (`.../diag`) |
| `WIFI SCAN` | Lista redes visibles (marca las empresariales 802.1X) |
| `WIFI <casa\|tec\|huerto> <ssid> <contraseña>` | Guarda una red (sin espacios) |
| `WIFIHEX <red> <ssid_hex> <contraseña_hex>` | Igual, admite cualquier carácter |
| `WIFI PREF <red>` / `WIFI OFF <red>` | Red preferida / deshabilitar |
| `RED APLICAR` | Reconecta Wi-Fi y MQTT con lo guardado (sin reiniciar) |

La consola solo repite la primera palabra del comando; la contraseña no se imprime. `RED`, `diag` y el dashboard muestran "guardada" o "(vacía)", nunca el valor.

## Red del Tec — limitación identificada (no verificada)

- Si la red usa **WPA2-Enterprise / 802.1X** (usuario y contraseña institucionales), el firmware actual **no** la soporta: solo WPA2-Personal o red abierta. `WIFI SCAN` la marca como "EMPRESARIAL 802.1X (no soportada)".
- Las redes institucionales suelen **aislar clientes**: aunque el ESP32 se conecte, puede no alcanzar al broker de la laptop.
- No se promete compatibilidad hasta probarla en sitio.

**Escaneo real del ESP32 en el Tec (2026-10-12, `WIFI SCAN`):**

| Red | Seguridad | Uso con el ESP32 |
|---|---|---|
| `Tec` | EMPRESARIAL 802.1X | **No soportada** (confirmado) |
| `Tec-Visitantes` | Abierta | Probablemente con portal de acceso y aislamiento de clientes: no recomendada |
| `Tec-IoT` | WPA/WPA2/WPA3 personal | Posible, pero requiere la contraseña y la autorización de TI |
| `RouterHuerto1` | WPA/WPA2/WPA3 personal | Red del huerto (Raspberry Pi), −55 dBm |

Alternativa probada en sitio: hotspot del celular en 2.4 GHz (iPhone: "Maximizar compatibilidad"), con `configs\CONFIGURAR_WIFI_HOTSPOT_ESP32.bat` (ranura `tec`).

## Estado al cierre

**Conectado y verificado (2026-10-11 23:11):** red `casa` = `RED_DE_CASA_2.4`, IP del ESP32 `IP_DEL_ESP32`, −50 dBm; broker `mqtt://IP_DE_LA_LAPTOP:1883` con el usuario `esp32_casa_01`; topic `huerto/casa/esp32_01`. Tras un reinicio conecta Wi-Fi en 2.2 s y MQTT en 2.6 s.

Lección del proceso: la primera vez se escribió "s" en la pregunta del nombre de la red y luego se presionó Enter sin contraseña; el diagnóstico (`RED`) mostró "red no encontrada" y "contraseña (vacía)". El `.bat` ahora solo pide la contraseña.

## Si cambia la IP de la laptop

La IP es por DHCP. Si cambia, vuelva a ejecutar `provisionar_red.py --solo-mqtt`, o use CONFIGURACIÓN → "Cambiar broker" en el dashboard (con reversión automática si no conecta en 90 s). Lo ideal es reservar la IP de la laptop en el módem.
