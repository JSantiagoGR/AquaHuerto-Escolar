"""Instala el bot de Telegram de SOLO LECTURA en la Raspberry Pi (dentro de ~/equipo2_proyecto).

Antes: crea el bot en Telegram con @BotFather (/newbot) y copia el token.
Uso (en la red RouterHuerto1):
    python scripts/instalar_bot_telegram_pi.py               instalar o actualizar
    python scripts/instalar_bot_telegram_pi.py --agregar     autorizar otro chat (otra persona o un grupo)
    python scripts/instalar_bot_telegram_pi.py --desinstalar detener el bot y quitarlo del arranque

Qué toca en la Pi: solo ~/equipo2_proyecto (telegram/, configs/secrets/telegram.env, una línea en
scripts/iniciar_equipo2.sh para que arranque con lo demás). No abre puertos ni toca el 1880/1883.
El token se escribe sin mostrarse y nunca se imprime.
"""
import getpass
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_ENV = os.path.join(ROOT, 'configs', 'secrets', 'telegram.env')
SSH = ['ssh', '-i', os.path.expanduser('~/.ssh/equipo2_pi'), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
       'pi@raspberrypi.local']
REMOTO = '~/equipo2_proyecto'
GANCHO = '[ -f "$P/telegram/iniciar_bot.sh" ] && bash "$P/telegram/iniciar_bot.sh"   # Bot de Telegram (solo lectura)'


def pi(cmd, entrada=None, revisar=True):
    r = subprocess.run(SSH + [cmd], input=entrada, capture_output=True)
    if revisar and r.returncode:
        sys.exit('Falló en la Pi: ' + (r.stderr or r.stdout).decode('utf-8', 'replace').strip())
    return r.stdout.decode('utf-8', 'replace')


def tg(token, metodo, params=None):
    url = 'https://api.telegram.org/bot%s/%s' % (token, metodo)
    try:
        with urllib.request.urlopen(url, data=urllib.parse.urlencode(params or {}).encode(), timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:         # Sin la URL: contiene el token
        sys.exit('Telegram respondió HTTP %d en %s (¿token correcto?)' % (e.code, metodo))
    except urllib.error.URLError as e:
        sys.exit('Sin internet para hablar con Telegram (%s)' % e.reason)


def leer_env():
    env = {}
    if os.path.exists(LOCAL_ENV):
        for line in open(LOCAL_ENV, encoding='utf-8'):
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k] = v
    return env


def guardar_env(env):
    texto = '# Bot de Telegram del huerto (NO compartir este archivo)\n' + \
            ''.join('%s=%s\n' % (k, env[k]) for k in ('TELEGRAM_TOKEN', 'TELEGRAM_CHATS'))
    with open(LOCAL_ENV, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto)
    return texto


def esperar_chats(token, usuario):
    print('\nAbre Telegram y manda /start a @%s (o agrégalo a un grupo y escribe /start ahí).' % usuario)
    print('Esperando hasta 3 minutos...')
    tg(token, 'deleteWebhook')
    fin, vistos, offset = time.time() + 180, {}, 0
    while time.time() < fin and not vistos:
        for u in tg(token, 'getUpdates', {'offset': offset, 'timeout': 20}).get('result', []):
            offset = u['update_id'] + 1
            c = (u.get('message') or {}).get('chat') or {}
            if c.get('id'):
                vistos[str(c['id'])] = c.get('title') or ' '.join(filter(None, [c.get('first_name'), c.get('last_name')]))
    tg(token, 'getUpdates', {'offset': offset, 'timeout': 0})    # Marca esos mensajes como leídos
    if not vistos:
        sys.exit('No llegó ningún /start. Vuelve a correr el instalador.')
    elegidos = []
    for cid, nombre in vistos.items():
        if input('¿Autorizar a "%s"? [s/n] ' % nombre).strip().lower().startswith('s'):
            elegidos.append(cid)
    if not elegidos:
        sys.exit('No se autorizó ningún chat.')
    return elegidos


def main():
    if pi('echo ok', revisar=False).strip() != 'ok':
        sys.exit('No se pudo llegar a la Pi: conecta la laptop a RouterHuerto1 y vuelve a intentar.')

    if '--desinstalar' in sys.argv:
        print(pi('cd %s && bash telegram/detener_bot.sh 2>/dev/null; '
                 'sed -i "\\#telegram/iniciar_bot.sh#d" scripts/iniciar_equipo2.sh; echo "Quitado del arranque"' % REMOTO))
        return

    env = leer_env()
    token = env.get('TELEGRAM_TOKEN')
    if not token or '--token' in sys.argv:
        token = getpass.getpass('Pega el token de @BotFather (no se mostrará): ').strip()
    me = tg(token, 'getMe').get('result', {})
    print('Token válido: bot @%s' % me.get('username'))

    pi('cd %s && bash telegram/detener_bot.sh >/dev/null 2>&1; true' % REMOTO, revisar=False)  # Libera getUpdates
    chats = [c for c in env.get('TELEGRAM_CHATS', '').split(',') if c]
    if not chats or '--agregar' in sys.argv:
        chats = list(dict.fromkeys(chats + esperar_chats(token, me.get('username'))))
    texto_env = guardar_env({'TELEGRAM_TOKEN': token, 'TELEGRAM_CHATS': ','.join(chats)})

    print('Copiando el bot a la Pi...')
    pi('mkdir -p %s/telegram %s/configs/secrets' % (REMOTO, REMOTO))
    for f in ('bot_huerto.py', 'iniciar_bot.sh', 'detener_bot.sh'):
        with open(os.path.join(ROOT, 'telegram', f), 'rb') as h:
            pi('cat > %s/telegram/%s' % (REMOTO, f), h.read().replace(b'\r\n', b'\n'))
    pi('umask 077 && cat > %s/configs/secrets/telegram.env' % REMOTO, texto_env.encode())

    print('Probando la lectura de la base en la Pi...')
    salida = pi('cd %s && python3 telegram/bot_huerto.py --prueba' % REMOTO)
    print('\n'.join(salida.splitlines()[:12]))

    if 'telegram/iniciar_bot.sh' not in pi('cat %s/scripts/iniciar_equipo2.sh' % REMOTO):
        pi("cp %s/scripts/iniciar_equipo2.sh %s/backups/iniciar_equipo2.antes_telegram.sh && "
           "printf '\\n%%s\\n' '%s' >> %s/scripts/iniciar_equipo2.sh" % (REMOTO, REMOTO, GANCHO, REMOTO))
        print('Agregado al arranque automático (scripts/iniciar_equipo2.sh)')

    print(pi('cd %s && bash telegram/iniciar_bot.sh' % REMOTO).strip())
    for c in chats:
        tg(token, 'sendMessage', {'chat_id': c, 'text': '✅ Bot del AquaHuerto instalado. Manda /estado para ver cómo va.'})
    print('Listo. Manda /estado al bot desde cualquier red.')


if __name__ == '__main__':
    main()
