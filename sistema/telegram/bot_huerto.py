"""Bot de Telegram para ver el huerto desde cualquier red y cambiar el modo de operación.

Corre en la Raspberry Pi dentro de ~/equipo2_proyecto. Solo hace conexiones de SALIDA (HTTPS a
api.telegram.org): no abre puertos ni expone Node-RED o MQTT. Lee la base SQLite en modo solo lectura.
La única acción permitida es cambiar el modo (MANUAL / AUTOMÁTICO / IA), con confirmación, publicando el
mismo SET_MODE que el dashboard en el broker local (127.0.0.1) y esperando el ACK del ESP32. No puede regar.

  - Comandos: /estado, /riegos, /alertas, /ia, /modo, /ayuda (solo los chats autorizados reciben respuesta).
  - Avisos: alertas nuevas del ESP32, ESP32 sin datos y su regreso.
  - Resumen diario a las 20:30.

Configuración: configs/secrets/telegram.env (TELEGRAM_TOKEN, TELEGRAM_CHATS) y, para /modo, el usuario
MQTT de administración de configs/secrets/credenciales_final.env. Nada de eso se imprime.
Uso:  python3 telegram/bot_huerto.py            (servicio)
      python3 telegram/bot_huerto.py --prueba   (imprime los mensajes con la base local, sin Telegram)
"""
import json
import os
import secrets
import socket
import sqlite3
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT, 'configs', 'secrets', 'telegram.env')
MQTT_ENV_FILE = os.path.join(ROOT, 'configs', 'secrets', 'credenciales_final.env')
CONFIRMAR_S = 120           # una confirmación de /modo vence a los 2 minutos
ACK_S = 15                  # tiempo máximo para la confirmación del ESP32
STATE_FILE = os.path.join(ROOT, 'run', 'telegram_estado.json')
DEVICE = 'esp32_principal'
RESUMEN_HORA = (20, 30)
SIN_DATOS_MIN = 20          # minutos sin lecturas para avisar que el ESP32 no reporta
ALERTA_REPETIR_S = 3600     # el mismo código de alerta se avisa como máximo una vez por hora

os.environ['TZ'] = 'CST6'   # Chihuahua, UTC-6 sin horario de verano (igual que el ESP32)
if hasattr(time, 'tzset'):  # No existe en Windows (solo se usa ahí con --prueba)
    time.tzset()


def leer_env(path):
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def ruta_db():
    for p in (os.path.join(ROOT, 'database', 'riego_final.db'), os.path.join(ROOT, 'database', 'riego_casa.db')):
        if os.path.exists(p):
            return p
    sys.exit('No se encontró la base de datos en database/')


def consulta(sql, args=()):
    con = sqlite3.connect('file:%s?mode=ro' % ruta_db(), uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def esc(v):
    """Texto que viene del ESP32 o de la base: sin caracteres especiales de Markdown."""
    s = '—' if v is None else str(v)
    for ch in ('_', '*', '`', '['):
        s = s.replace(ch, '\\' + ch)
    return s


def n(v, d=1, suf=''):
    return '—' if v is None else ('%.*f%s' % (d, v, suf))


def hora(ts):
    return time.strftime('%d/%m %H:%M', time.localtime(ts)) if ts else '—'


def hace(ts):
    if not ts:
        return 'nunca'
    m = int((time.time() - ts) // 60)
    return 'hace %d min' % m if m < 120 else 'hace %.1f h' % (m / 60)


MODOS = {'MANUAL': 'MANUAL ✋', 'AUTOMATICO': 'AUTOMÁTICO ⚙️', 'IA': 'IA 🤖'}


def ultima_lectura():
    r = consulta('SELECT * FROM readings WHERE device=? AND simulated=0 ORDER BY ts DESC LIMIT 1', (DEVICE,))
    return r[0] if r else None


def texto_estado():
    r = ultima_lectura()
    if not r:
        return '⚠️ Todavía no hay lecturas del ESP32 en la base de datos.'
    viejo = time.time() - r['ts'] > SIN_DATOS_MIN * 60
    ia = ia_vivo()
    act = consulta('SELECT COUNT(*) c FROM alerts WHERE device=? AND active=1 AND simulated=0', (DEVICE,))[0]['c']
    lineas = [
        '🌱 *AquaHuerto* — %s' % hora(r['ts']),
        ('🔴 *ESP32 sin datos* (última lectura %s)' % hace(r['ts'])) if viejo else ('🟢 ESP32 en línea (%s)' % hace(r['ts'])),
        '',
        '💧 Humedad del suelo: *%s %%VWC* (%s)' % (n(r['vwc']), esc(r['soil_status'])),
        '🪣 Tinaco: *%s* (%s)' % (n(r['tank_pct'], 0, ' %'), esc(r['tank_status'])),
        '🌡️ Aire: %s · %s HR' % (n(r['temp_c'], 1, ' °C'), n(r['rh_pct'], 0, ' %')),
        '🚿 Regado hoy: *%s*' % n(r['today_l'], 2, ' L'),
        '🕹️ Modo: %s · estado %s' % (MODOS.get(r['mode'], esc(r['mode'])), esc(r['state'])),
    ]
    if r['crop']:
        lineas.append('🌿 Cultivo: %s · %s' % (esc(r['crop']), esc(r['stage'] or '')))
    if ia:
        lineas.append('🤖 IA: %s (%s de %d riegos, %s de %d h de secado)' % (
            FASES_IA.get(ia['status'], esc(ia['status'])), n(ia['eventos'], 0), int(ia['min_eventos']),
            n(ia['horas'], 0), int(ia['min_horas'])))
    rh = reinicios_hoy()
    if rh is not None:
        lineas.append('🔄 Reinicios del ESP32 hoy: %d' % rh)
    lineas.append('🔔 Alertas activas: %d' % act)
    if r['mode'] == 'MANUAL':
        lineas.append('\n⚠️ Está en MANUAL: *no riega solo*.')
    return '\n'.join(lineas)


def texto_riegos(limite=5):
    rows = consulta('SELECT ts_start, reason, delivered_l, vwc_before, vwc_after, result FROM irrigation_events '
                    'WHERE device=? AND simulated=0 ORDER BY ts_start DESC LIMIT ?', (DEVICE, limite))
    if not rows:
        return 'No hay riegos registrados.'
    out = ['🚿 *Últimos riegos*']
    for e in rows:
        out.append('• %s — %s, %s (%s → %s %%) %s' % (
            hora(e['ts_start']), esc(e['reason']), n(e['delivered_l'], 2, ' L'),
            n(e['vwc_before']), n(e['vwc_after']), esc(e['result'] or '')))
    return '\n'.join(out)


def texto_alertas():
    rows = consulta('SELECT ts, severity, code, message FROM alerts WHERE device=? AND active=1 AND simulated=0 '
                    'ORDER BY ts DESC LIMIT 10', (DEVICE,))
    if not rows:
        return '✅ Sin alertas activas.'
    return '\n'.join(['🔔 *Alertas activas*'] + ['• %s %s *%s*: %s' % (
        hora(a['ts']), icono(a['severity']), esc(a['code']), esc(a['message'] or '')) for a in rows])


FASES_IA = {'APRENDIZAJE': 'APRENDIZAJE 📘', 'VALIDACION': 'VALIDACIÓN 🧪', 'PREDICTIVO_ACTIVO': 'PREDICTIVO ACTIVO 🚀'}


def ia_vivo():
    """Estado de la IA: en vivo del topic retenido 'ia' (lo mismo que ve el dashboard); si no, de la base."""
    d = leer_retenido('ia')
    if d and 'status' in d:
        return {'fuente': 'en vivo', 'ts': d.get('ts'), 'status': d.get('status'),
                'eventos': d.get('events_learned'), 'horas': d.get('drying_hours_learned'),
                'min_eventos': d.get('min_events') or 6, 'min_horas': d.get('min_hours') or 48,
                'mae_a': d.get('mae_response_pp'), 'mae_b': d.get('mae_drying_pph'), 'tol': d.get('tolerance_pp'),
                'cambio': d.get('change_detected'), 'modo_ia': d.get('mode_ia_selected'),
                'controla': d.get('controls_watering')}
    rows = consulta('SELECT ts, status, events, drying_hours, mae_response, mae_drying FROM ia_snapshots '
                    'WHERE device=? AND simulated=0 ORDER BY ts DESC LIMIT 1', (DEVICE,))
    if not rows:
        return None
    i = rows[0]
    return {'fuente': 'base de datos', 'ts': i['ts'], 'status': i['status'], 'eventos': i['events'],
            'horas': i['drying_hours'], 'min_eventos': 6, 'min_horas': 48, 'mae_a': i['mae_response'],
            'mae_b': i['mae_drying'], 'tol': None, 'cambio': None, 'modo_ia': None, 'controla': None}


def reinicios_hoy():
    ini = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
    r = consulta('SELECT MIN(boot) a, MAX(boot) b FROM readings WHERE device=? AND simulated=0 AND ts>=? '
                 'AND boot IS NOT NULL', (DEVICE, ini))[0]
    return (r['b'] - r['a']) if r['a'] is not None else None


def texto_ia():
    i = ia_vivo()
    if not i:
        return '🤖 La IA todavía no ha reportado.'
    ev, hs = i['eventos'] or 0, i['horas'] or 0
    me, mh = int(i['min_eventos']), int(i['min_horas'])
    lineas = [
        '🤖 *IA*: %s' % FASES_IA.get(i['status'], esc(i['status'])),
        '📘 Riegos aprendidos: *%s de %d* %s' % (n(ev, 0), me, '✅' if ev >= me else ''),
        '☀️ Horas de secado: *%s de %d* %s' % (n(hs, 0), mh, '✅' if hs >= mh else ''),
        'Error al predecir el riego: %s pp%s' % (n(i['mae_a'], 2), (' (meta ±%s)' % n(i['tol'], 1)) if i['tol'] else ''),
    ]
    if i['status'] == 'APRENDIZAJE':
        falta = []
        if ev < me:
            falta.append('%d riegos' % (me - ev))
        if hs < mh:
            falta.append('%.0f h de secado' % (mh - hs))
        lineas.append('Le falta: ' + ', '.join(falta) + '.')
    elif i['status'] == 'VALIDACION':
        lineas.append('Ya juntó los datos: ahora comprueba sus predicciones con algunos riegos más.')
    else:
        lineas.append('Lista: en modo IA calcula los litros justos.')
    if i['modo_ia'] is not None:
        if i['modo_ia'] and not i['controla']:
            lineas.append('\nModo IA seleccionado: mientras aprende, riega igual que AUTOMÁTICO (sin riesgo).')
        elif i['modo_ia']:
            lineas.append('\nModo IA seleccionado y *controlando el riego*.')
        else:
            lineas.append('\nModo IA no seleccionado (la IA aprende igual en cualquier modo). Cámbialo con /modo ia')
    if i['cambio']:
        lineas.append('Detectó un cambio en el suelo: se está revalidando (no borra lo aprendido).')
    rh = reinicios_hoy()
    if rh is not None:
        lineas.append('🔄 Reinicios del ESP32 hoy: %d' % rh)
    lineas.append('(dato %s)' % i['fuente'])
    return '\n'.join(lineas)


def texto_resumen_dia():
    ini = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
    ev = consulta('SELECT COUNT(*) c, SUM(delivered_l) l FROM irrigation_events WHERE device=? AND simulated=0 '
                  'AND ts_start>=?', (DEVICE, ini))[0]
    hum = consulta('SELECT MIN(vwc) mn, MAX(vwc) mx FROM readings WHERE device=? AND simulated=0 AND ts>=? '
                   'AND vwc IS NOT NULL', (DEVICE, ini))[0]
    al = consulta('SELECT COUNT(*) c FROM alerts WHERE device=? AND simulated=0 AND ts>=?', (DEVICE, ini))[0]
    return '\n'.join([
        '📅 *Resumen del día*',
        'Riegos: %d · %s' % (ev['c'] or 0, n(ev['l'] or 0, 2, ' L')),
        'Humedad mín / máx: %s / %s %%VWC' % (n(hum['mn']), n(hum['mx'])),
        'Alertas nuevas hoy: %d' % (al['c'] or 0),
        '',
        texto_estado(),
    ])


AYUDA = ('🌱 *Bot del AquaHuerto*\n'
         '/estado — cómo está todo ahora\n'
         '/riegos — últimos riegos\n'
         '/alertas — alertas activas\n'
         '/ia — avance de la IA\n'
         '/modo — cambiar entre MANUAL, AUTOMÁTICO e IA (pide confirmación)\n'
         '/ayuda — esta lista\n\n'
         'Te aviso solo si hay alertas o si el ESP32 deja de reportar, y mando un resumen a las 20:30.\n'
         'Para regar a mano usa el dashboard en la red del huerto.')

MODOS_CMD = {'manual': 'MANUAL', 'automatico': 'AUTOMATICO', 'automático': 'AUTOMATICO', 'auto': 'AUTOMATICO',
             'ia': 'IA'}
EFECTO_MODO = {
    'AUTOMATICO': 'El sistema riega solo según la humedad y los horarios.',
    'MANUAL': '⚠️ El sistema *dejará de regar solo*: solo regará cuando alguien lo pida desde el dashboard.',
    'IA': 'Riega solo como en automático y además considera la lluvia; usa el modelo predictivo cuando esté listo.',
}


# ---------------------------------------------------------------- MQTT mínimo (3.1.1, solo biblioteca estándar)
def _mq_str(s):
    b = s.encode()
    return struct.pack('!H', len(b)) + b


def _mq_paquete(tipo, cuerpo):
    n, largo = len(cuerpo), b''
    while True:
        byte, n = n % 128, n // 128
        largo += bytes([byte | (0x80 if n else 0)])
        if not n:
            return bytes([tipo]) + largo + cuerpo


def _mq_leer(sock):
    def exacto(k):
        b = b''
        while len(b) < k:
            parte = sock.recv(k - len(b))
            if not parte:
                raise OSError('el broker cerró la conexión')
            b += parte
        return b
    tipo = exacto(1)[0]
    mult, n = 1, 0
    while True:
        byte = exacto(1)[0]
        n += (byte & 127) * mult
        mult *= 128
        if not byte & 128:
            return tipo, exacto(n)


def _mq_conectar(cid, timeout):
    """Conecta al broker local con el usuario de administración. Devuelve (socket, base) o (None, error)."""
    env = leer_env(MQTT_ENV_FILE)
    user, pw = env.get('MQTT_ADMIN_USER'), env.get('MQTT_ADMIN_PASS')
    if not user or not pw:
        return None, 'No se encontró el usuario MQTT de administración en la Raspberry Pi.'
    host = env.get('MQTT_HOST') or '127.0.0.1'
    port = int(env.get('MQTT_PORT') or 1884)
    base = '%s/%s/' % (env.get('RIEGO_TOPIC_ROOT') or 'huerto/final', DEVICE)
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as e:
        return None, 'No se pudo conectar al broker MQTT (%s).' % e
    try:
        sock.settimeout(timeout)
        sock.sendall(_mq_paquete(0x10, _mq_str('MQTT') + bytes([4, 0xC2]) + struct.pack('!H', 30) +
                                 _mq_str(cid) + _mq_str(user) + _mq_str(pw)))
        tipo, cuerpo = _mq_leer(sock)
    except (OSError, IndexError) as e:
        sock.close()
        return None, 'El broker MQTT no respondió (%s).' % e
    if tipo != 0x20 or len(cuerpo) < 2 or cuerpo[1] != 0:
        sock.close()
        return None, 'El broker MQTT rechazó la conexión del bot.'
    return sock, base


def _mq_cerrar(sock):
    try:
        sock.sendall(b'\xe0\x00')
    except OSError:
        pass
    sock.close()


def _mq_payload(tipo, cuerpo):
    lt = struct.unpack('!H', cuerpo[:2])[0]
    return cuerpo[2 + lt + (2 if tipo & 0x06 else 0):]


def leer_retenido(sub, timeout=4):
    """Último mensaje retenido de un topic del ESP32 (p. ej. 'ia'), o None si no se pudo leer."""
    sock, base = _mq_conectar('tg-r-' + secrets.token_hex(4), timeout)
    if sock is None:
        return None
    try:
        sock.sendall(_mq_paquete(0x82, struct.pack('!H', 1) + _mq_str(base + sub) + b'\x00'))
        limite = time.time() + timeout
        while time.time() < limite:
            sock.settimeout(max(0.5, limite - time.time()))
            tipo, cuerpo = _mq_leer(sock)
            if tipo & 0xF0 == 0x30:
                return json.loads(_mq_payload(tipo, cuerpo).decode())
    except (OSError, IndexError, ValueError):
        return None
    finally:
        _mq_cerrar(sock)
    return None


def enviar_modo(modo):
    """Publica SET_MODE en el broker local y espera el ACK del ESP32. Devuelve (estado, mensaje)."""
    cid = 'tg-' + secrets.token_hex(6)
    orden = {'cmd': 'SET_MODE', 'mode': modo, 'id': cid, 'ts': int(time.time())}
    sock, base = _mq_conectar(cid, ACK_S)
    if sock is None:
        return 'ERROR', base
    try:
        sock.sendall(_mq_paquete(0x82, struct.pack('!H', 1) + _mq_str(base + 'ack') + b'\x00'))
        sock.sendall(_mq_paquete(0x32, _mq_str(base + 'command') + struct.pack('!H', 2) + json.dumps(orden).encode()))
        limite = time.time() + ACK_S
        while time.time() < limite:
            sock.settimeout(max(0.5, limite - time.time()))
            tipo, cuerpo = _mq_leer(sock)
            if tipo & 0xF0 != 0x30:                     # SUBACK, PUBACK, etc.
                continue
            try:
                ack = json.loads(_mq_payload(tipo, cuerpo).decode())
            except ValueError:
                continue
            if ack.get('id') == cid and ack.get('status') != 'PENDING':
                return ack.get('status', '?'), ack.get('message', '')
        return 'TIMEOUT', 'El ESP32 no confirmó en %d s. No se cambió nada.' % ACK_S
    except (OSError, IndexError) as e:
        return 'TIMEOUT', 'Sin confirmación del ESP32 (%s). No se cambió nada.' % e
    finally:
        _mq_cerrar(sock)


def modo_actual():
    r = ultima_lectura()
    return r['mode'] if r else None

COMANDOS = {'/estado': texto_estado, '/riegos': texto_riegos, '/alertas': texto_alertas,
            '/ia': texto_ia, '/ayuda': lambda: AYUDA, '/start': lambda: AYUDA}


def icono(sev):
    return {'CRITICAL': '🔴', 'WARNING': '🟠'}.get(sev, '🔵')


# ---------------------------------------------------------------- Telegram
class Telegram:
    def __init__(self, token):
        self._base = 'https://api.telegram.org/bot%s/' % token

    def llamar(self, metodo, params, timeout=70):
        data = urllib.parse.urlencode(params).encode()
        try:
            with urllib.request.urlopen(self._base + metodo, data=data, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:      # Nunca se registra la URL: contiene el token
            raise RuntimeError('Telegram %s respondió HTTP %d' % (metodo, e.code)) from None
        except (urllib.error.URLError, OSError) as e:
            raise RuntimeError('Sin conexión con Telegram (%s)' % getattr(e, 'reason', e)) from None

    def enviar(self, chat, texto, botones=None):
        extra = {'reply_markup': json.dumps({'inline_keyboard': botones})} if botones else {}
        try:
            self.llamar('sendMessage', dict({'chat_id': chat, 'text': texto, 'parse_mode': 'Markdown'}, **extra), 20)
        except RuntimeError:                       # Markdown roto por un mensaje del ESP32: se manda plano
            self.llamar('sendMessage', dict({'chat_id': chat, 'text': texto.replace('*', '').replace('\\', '')},
                                            **extra), 20)

    def editar(self, chat, msg_id, texto):
        """Reemplaza el mensaje de los botones (los quita) para que no se puedan presionar otra vez."""
        try:
            self.llamar('editMessageText', {'chat_id': chat, 'message_id': msg_id, 'text': texto,
                                            'parse_mode': 'Markdown'}, 20)
        except RuntimeError:
            self.enviar(chat, texto)

    def responder_boton(self, callback_id, texto=''):
        try:
            self.llamar('answerCallbackQuery', {'callback_query_id': callback_id, 'text': texto}, 20)
        except RuntimeError:
            pass


NOMBRE_MODO = {'MANUAL': 'MANUAL', 'AUTOMATICO': 'AUTOMÁTICO', 'IA': 'IA'}


def pedir_modo(tg, chat, arg, pendientes):
    """/modo sin argumento: botones con los tres modos. /modo <nombre>: va directo a la confirmación."""
    actual = modo_actual()
    if arg:
        modo = MODOS_CMD.get(arg.lower())
        if not modo:
            tg.enviar(chat, 'Modos válidos: manual, automatico, ia. Ejemplo: /modo automatico')
            return
        confirmar_modo(tg, chat, modo, actual, pendientes)
        return
    botones = [[{'text': NOMBRE_MODO[m] + ('  (actual)' if m == actual else ''), 'callback_data': 'modo:' + m}]
               for m in ('AUTOMATICO', 'MANUAL', 'IA')]
    tg.enviar(chat, '🕹️ Modo actual: *%s*\n¿A cuál quieres cambiar?' % NOMBRE_MODO.get(actual, actual or '—'), botones)


def confirmar_modo(tg, chat, modo, actual, pendientes):
    if modo == actual:
        tg.enviar(chat, 'El sistema ya está en modo *%s*. No hay nada que cambiar.' % NOMBRE_MODO[modo])
        return
    clave = secrets.token_hex(4)
    pendientes[clave] = (modo, time.time(), chat)
    tg.enviar(chat, '¿Cambiar de *%s* a *%s*?\n%s' % (NOMBRE_MODO.get(actual, actual or '—'), NOMBRE_MODO[modo],
                                                     EFECTO_MODO[modo]),
              [[{'text': 'Sí, cambiar', 'callback_data': 'si:' + clave},
                {'text': 'Cancelar', 'callback_data': 'no:' + clave}]])


def atender_boton(tg, cb, chats, pendientes):
    chat = str(((cb.get('message') or {}).get('chat') or {}).get('id', ''))
    msg_id = (cb.get('message') or {}).get('message_id')
    if chat not in chats:                                  # Botón de un chat no autorizado: se ignora
        tg.responder_boton(cb['id'])
        return
    accion, _, valor = (cb.get('data') or '').partition(':')
    if accion == 'modo' and valor in NOMBRE_MODO:
        tg.responder_boton(cb['id'])
        tg.editar(chat, msg_id, 'Elegiste *%s*.' % NOMBRE_MODO[valor])
        confirmar_modo(tg, chat, valor, modo_actual(), pendientes)
        return
    p = pendientes.pop(valor, None)
    if not p or p[2] != chat or time.time() - p[1] > CONFIRMAR_S:
        tg.responder_boton(cb['id'], 'Esta confirmación ya venció. Usa /modo otra vez.')
        tg.editar(chat, msg_id, 'Confirmación vencida: no se cambió nada.')
        return
    if accion != 'si':
        tg.responder_boton(cb['id'], 'Cancelado')
        tg.editar(chat, msg_id, 'Cancelado: no se cambió nada.')
        return
    modo = p[0]
    tg.responder_boton(cb['id'], 'Enviando al ESP32...')
    tg.editar(chat, msg_id, '⏳ Enviando el cambio a *%s* al ESP32...' % NOMBRE_MODO[modo])
    estado, mensaje = enviar_modo(modo)
    log('Cambio de modo a %s desde Telegram: %s %s' % (modo, estado, mensaje))
    if estado == 'OK':
        tg.enviar(chat, '✅ *CONFIRMADO por el ESP32:* modo *%s*.\n%s' % (NOMBRE_MODO[modo], EFECTO_MODO[modo]))
    else:
        tg.enviar(chat, '❌ *No se cambió el modo* (%s).\n%s' % (esc(estado), esc(mensaje)))


def cargar_estado():
    try:
        return json.load(open(STATE_FILE, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def guardar_estado(st):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + '.tmp'
    json.dump(st, open(tmp, 'w', encoding='utf-8'))
    os.replace(tmp, STATE_FILE)


def log(msg):
    print(time.strftime('[%Y-%m-%d %H:%M:%S] ') + msg, flush=True)


def revisar_avisos(tg, chats, st):
    """Alertas nuevas, ESP32 sin datos / de regreso y resumen diario."""
    if 'ultima_alerta' not in st:              # Primer arranque: no reenviar el historial
        r = consulta('SELECT MAX(id) m FROM alerts')[0]['m']
        st['ultima_alerta'] = r or 0
    nuevas = consulta('SELECT id, ts, severity, code, message FROM alerts WHERE id>? AND device=? AND simulated=0 '
                      'ORDER BY id', (st['ultima_alerta'], DEVICE))
    vistos = st.setdefault('codigos', {})
    for a in nuevas:
        st['ultima_alerta'] = a['id']
        if a['severity'] not in ('CRITICAL', 'WARNING') or a['code'] == 'DEVICE_OFFLINE':
            continue                           # DEVICE_OFFLINE lo cubre el aviso propio de "sin datos"
        if time.time() - vistos.get(a['code'], 0) < ALERTA_REPETIR_S:
            continue
        vistos[a['code']] = time.time()
        for c in chats:
            tg.enviar(c, '%s *Alerta: %s*\n%s\n%s' % (icono(a['severity']), esc(a['code']), esc(a['message'] or ''), hora(a['ts'])))

    r = ultima_lectura()
    sin_datos = (r is None) or (time.time() - r['ts'] > SIN_DATOS_MIN * 60)
    if sin_datos and not st.get('sin_datos'):
        st['sin_datos'] = True
        for c in chats:
            tg.enviar(c, '🔴 *El ESP32 no ha reportado* desde %s.\nSi la Pi o el Wi-Fi se cayeron, el huerto '
                         'sigue regando solo; si dura mucho, revisa batería y señal.' % (hace(r['ts']) if r else 'nunca'))
    elif not sin_datos and st.get('sin_datos'):
        st['sin_datos'] = False
        for c in chats:
            tg.enviar(c, '🟢 El ESP32 volvió a reportar.')

    hoy = time.strftime('%Y-%m-%d')
    lt = time.localtime()
    if (lt.tm_hour, lt.tm_min) >= RESUMEN_HORA and st.get('resumen') != hoy:
        st['resumen'] = hoy
        for c in chats:
            tg.enviar(c, texto_resumen_dia())


def main():
    if '--prueba' in sys.argv:
        for f in (texto_estado, texto_riegos, texto_alertas, texto_ia, texto_resumen_dia):
            print(f(), '\n' + '-' * 40)
        return
    env = leer_env(ENV_FILE)
    token = env.get('TELEGRAM_TOKEN', '')
    chats = [c.strip() for c in env.get('TELEGRAM_CHATS', '').split(',') if c.strip()]
    if not token or not chats:
        sys.exit('Falta TELEGRAM_TOKEN o TELEGRAM_CHATS en configs/secrets/telegram.env')
    tg = Telegram(token)
    st = cargar_estado()
    offset = st.get('offset', 0)
    log('Bot iniciado (consulta y cambio de modo), %d chat(s) autorizado(s)' % len(chats))
    ultimo_revisar = 0
    pendientes = {}                                # confirmaciones de /modo en curso
    while True:
        try:
            if time.time() - ultimo_revisar >= 60:
                revisar_avisos(tg, chats, st)
                ultimo_revisar = time.time()
                guardar_estado(st)
            res = tg.llamar('getUpdates', {'offset': offset, 'timeout': 50,
                                           'allowed_updates': '["message","callback_query"]'})
            for u in res.get('result', []):
                offset = u['update_id'] + 1
                if u.get('callback_query'):
                    atender_boton(tg, u['callback_query'], chats, pendientes)
                    continue
                m = u.get('message') or {}
                chat = str((m.get('chat') or {}).get('id', ''))
                partes = (m.get('text') or '').split()
                cmd = partes[0].split('@')[0].lower() if partes else ''
                if chat not in chats:              # Chats desconocidos: se ignoran en silencio
                    continue
                if cmd == '/modo':
                    pedir_modo(tg, chat, partes[1] if len(partes) > 1 else '', pendientes)
                    continue
                f = COMANDOS.get(cmd)
                tg.enviar(chat, f() if f else 'No conozco ese comando.\n\n' + AYUDA)
            st['offset'] = offset
            guardar_estado(st)
        except RuntimeError as e:
            log(str(e))
            time.sleep(30)
        except sqlite3.Error as e:
            log('Base de datos: %s' % e)
            time.sleep(30)


if __name__ == '__main__':
    main()
