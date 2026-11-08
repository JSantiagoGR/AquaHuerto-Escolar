# Bot de Telegram (ver el huerto desde cualquier red)

Bot de **solo lectura** que corre en la Raspberry Pi, dentro de `~/equipo2_proyecto`. Solo hace conexiones de salida
a `api.telegram.org`: no abre puertos, no expone Node-RED ni MQTT y **no puede regar ni cambiar nada**.

| Qué hace | Detalle |
|---|---|
| `/estado` | Humedad, tinaco, aire, litros de hoy, modo, cultivo, IA y alertas activas |
| `/riegos` | Últimos 5 riegos |
| `/alertas` | Alertas activas |
| `/ia` | Fase de la IA y cuánto le falta |
| Avisos | Alertas nuevas CRITICAL/WARNING (cada código máximo 1 vez por hora); ESP32 sin datos > 20 min y su regreso |
| Resumen diario | 20:30 |

Solo responde a los chats autorizados; los demás se ignoran. Si la Pi entera se apaga, el bot también (deja de
contestar a `/estado`): eso mismo indica que la Pi está caída.

## Instalar (una vez, en la red RouterHuerto1)

1. En Telegram, habla con **@BotFather** → `/newbot` → ponle nombre → copia el token.
2. En la laptop: `python scripts/instalar_bot_telegram_pi.py` → pega el token (no se muestra).
3. Manda `/start` al bot cuando lo pida y confirma tu nombre.

El instalador verifica el token, copia `telegram/` a la Pi, guarda el token en `configs/secrets/telegram.env`
(permisos 600, excluido del repositorio), prueba la lectura de la base, agrega una línea a
`scripts/iniciar_equipo2.sh` (respaldo en `backups/`) para que arranque solo con la Pi, y lo inicia.

- Otra persona o un grupo: `python scripts/instalar_bot_telegram_pi.py --agregar`
- Cambiar el token: `... --token` · Quitarlo: `... --desinstalar`
- Registro en la Pi: `~/equipo2_proyecto/logs/telegram.log`
- Probar sin Telegram: `python telegram/bot_huerto.py --prueba`
