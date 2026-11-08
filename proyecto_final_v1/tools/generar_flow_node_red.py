"""Genera node-red/flow_dashboard_riego.json (Node-RED + Dashboard 2.0).

El archivo es un EJEMPLO para importar más adelante (Menú > Importar). Este
script NO se conecta a Node-RED ni despliega nada.

Requiere en Node-RED: paleta @flowfuse/node-red-dashboard (Dashboard 2.0).
Uso: python tools/generar_flow_node_red.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "node-red", "flow_dashboard_riego.json")
BASE = "huerto/esp32"
TAB = "tab_riego"

nodes = []
_y = {}


def nid(name):
    return name.replace(" ", "_").lower()


def pos(col, row):
    return 180 + col * 260, 60 + row * 50


def add(node):
    nodes.append(node)
    return node["id"]


# ---------------------------------------------------------------- config
add({"id": TAB, "type": "tab", "label": "Riego Huerto", "disabled": False,
     "info": "Dashboard del riego automatizado (Proyecto_Final_v1). Topics en MQTT_TOPICS.md."})
add({"id": "broker_huerto", "type": "mqtt-broker", "name": "Broker huerto", "broker": "raspberrypi.local",
     "port": "1883", "clientid": "nodered-huerto", "autoConnect": True, "usetls": False,
     "protocolVersion": "4", "keepalive": "60", "cleansession": True, "autoUnsubscribe": True,
     "birthTopic": "", "birthQos": "0", "birthRetain": "false", "birthPayload": "", "birthMsg": {},
     "closeTopic": "", "closeQos": "0", "closeRetain": "false", "closePayload": "", "closeMsg": {},
     "willTopic": "", "willQos": "0", "willRetain": "false", "willPayload": "", "willMsg": {},
     "userProps": "", "sessionExpiry": ""})
add({"id": "ui_base_huerto", "type": "ui-base", "name": "Huerto", "path": "/dashboard",
     "includeClientData": True, "acceptsClientConfig": ["ui-notification", "ui-control"],
     "showPathInSidebar": False, "navigationStyle": "default", "titleBarStyle": "default"})
add({"id": "ui_theme_huerto", "type": "ui-theme", "name": "Tema huerto",
     "colors": {"surface": "#1b5e20", "primary": "#2e7d32", "bgPage": "#eef2ee",
                "groupBg": "#ffffff", "groupOutline": "#c8d6c8"},
     "sizes": {"density": "default", "pagePadding": "12px", "groupGap": "12px",
               "groupBorderRadius": "8px", "widgetGap": "10px"}})
add({"id": "ui_page_riego", "type": "ui-page", "name": "Riego del huerto", "ui": "ui_base_huerto",
     "path": "/riego", "icon": "water", "layout": "grid", "theme": "ui_theme_huerto",
     "breakpoints": [{"name": "Default", "px": "0", "cols": "3"}, {"name": "Tablet", "px": "576", "cols": "6"},
                     {"name": "Desktop", "px": "1024", "cols": "12"}],
     "order": 1, "className": "", "visible": "true", "disabled": "false"})

GROUPS = [
    ("g_principal", "A. Panel principal", 12),
    ("g_humedad", "B. Configuración de humedad del suelo", 4),
    ("g_manual", "C. Riego manual", 4),
    ("g_auto", "D. Riego automático", 4),
    ("g_graficas", "E. Gráficas", 12),
    ("g_historial", "F. Historial", 8),
    ("g_alertas", "G. Configuración y alertas", 4),
]
for i, (gid, name, w) in enumerate(GROUPS):
    add({"id": gid, "type": "ui-group", "name": name, "page": "ui_page_riego", "width": str(w),
         "height": "1", "order": i + 1, "showTitle": True, "className": "", "visible": "true",
         "disabled": "false", "groupType": "default"})


# --------------------------------------------------------------- helpers
def mqtt_in(id_, topic, col, row, wires, qos="1"):
    x, y = pos(col, row)
    return add({"id": id_, "type": "mqtt in", "z": TAB, "name": topic.split("/")[-1], "topic": topic,
                "qos": qos, "datatype": "json", "broker": "broker_huerto", "nl": False, "rap": True,
                "rh": 0, "inputs": 0, "x": x, "y": y, "wires": [wires]})


def mqtt_out(id_, col, row):
    x, y = pos(col, row)
    return add({"id": id_, "type": "mqtt out", "z": TAB, "name": "Comando al ESP32",
                "topic": BASE + "/command", "qos": "1", "retain": "false", "respTopic": "",
                "contentType": "", "userProps": "", "correl": "", "expiry": "",
                "broker": "broker_huerto", "x": x, "y": y, "wires": []})


def func(id_, name, code, outputs, col, row, wires):
    x, y = pos(col, row)
    return add({"id": id_, "type": "function", "z": TAB, "name": name, "func": code, "outputs": outputs,
                "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
                "x": x, "y": y, "wires": wires})


def text(id_, group, order, label, col, row, fmt="{{msg.payload}}", width=3):
    x, y = pos(col, row)
    return add({"id": id_, "type": "ui-text", "z": TAB, "group": group, "order": order, "width": str(width),
                "height": "1", "name": label, "label": label, "format": fmt, "layout": "row-spread",
                "style": False, "font": "", "fontSize": 16, "color": "#1b1b1b", "wrapText": False,
                "className": "", "x": x, "y": y, "wires": []})


def gauge(id_, group, order, title, units, mn, mx, segments, col, row, width=3):
    x, y = pos(col, row)
    return add({"id": id_, "type": "ui-gauge", "z": TAB, "name": title, "group": group, "order": order,
                "width": str(width), "height": "3", "gtype": "gauge-half", "gstyle": "Rounded",
                "title": title, "units": units, "icon": "", "prefix": "", "suffix": "",
                "segments": [{"from": str(f), "color": c} for f, c in segments],
                "min": mn, "max": mx, "sizeThickness": 16, "sizeGap": 4, "sizeKeyThickness": 8,
                "styleRounded": True, "styleGlow": False, "className": "", "x": x, "y": y, "wires": []})


def slider(id_, group, order, label, mn, mx, step, col, row, wires):
    x, y = pos(col, row)
    return add({"id": id_, "type": "ui-slider", "z": TAB, "group": group, "name": label, "label": label,
                "tooltip": "", "order": order, "width": "4", "height": "1", "passthru": False,
                "outs": "end", "topic": "topic", "topicType": "msg", "thumbLabel": "always",
                "showTicks": "always", "min": str(mn), "max": str(mx), "step": str(step), "className": "",
                "iconPrepend": "", "iconAppend": "", "color": "", "colorTrack": "", "colorThumb": "",
                "showTextField": True, "x": x, "y": y, "wires": [wires]})


def button(id_, group, order, label, payload, color, col, row, wires, width=2):
    x, y = pos(col, row)
    return add({"id": id_, "type": "ui-button", "z": TAB, "group": group, "name": label, "label": label,
                "order": order, "width": str(width), "height": "1", "emulateClick": False, "tooltip": "",
                "color": "#ffffff", "bgcolor": color, "className": "", "icon": "", "iconPosition": "left",
                "payload": payload, "payloadType": "str", "topic": "topic", "topicType": "msg",
                "buttonColor": color, "textColor": "#ffffff", "iconColor": "", "enableClick": True,
                "enablePointerdown": False, "pointerdownPayload": "", "pointerdownPayloadType": "str",
                "enablePointerup": False, "pointerupPayload": "", "pointerupPayloadType": "str",
                "x": x, "y": y, "wires": [wires]})


def chart(id_, group, order, label, ymin, ymax, col, row, width=6):
    x, y = pos(col, row)
    return add({"id": id_, "type": "ui-chart", "z": TAB, "group": group, "name": label, "label": label,
                "order": order, "chartType": "line", "category": "topic", "categoryType": "msg",
                "xAxisLabel": "", "xAxisProperty": "", "xAxisPropertyType": "timestamp", "xAxisType": "time",
                "xAxisFormat": "", "xAxisFormatType": "auto", "yAxisLabel": "", "yAxisProperty": "payload",
                "yAxisPropertyType": "msg", "ymin": str(ymin), "ymax": str(ymax), "bins": 10,
                "action": "append", "stackSeries": False, "pointShape": "circle", "pointRadius": 2,
                "showLegend": True, "removeOlder": 1, "removeOlderUnit": "86400", "removeOlderPoints": "1000",
                "colors": ["#2e7d32", "#1565c0", "#ef6c00", "#6a1b9a", "#c62828", "#00838f",
                           "#5d4037", "#9e9d24", "#455a64"],
                "textColor": ["#666666"], "textColorDefault": True, "gridColor": ["#e5e5e5"],
                "gridColorDefault": True, "width": str(width), "height": "4", "className": "",
                "interpolation": "linear", "x": x, "y": y, "wires": [[]]})


def table(id_, group, order, label, col, row, width=8):
    x, y = pos(col, row)
    return add({"id": id_, "type": "ui-table", "z": TAB, "group": group, "name": label, "label": label,
                "order": order, "width": str(width), "height": "6", "maxrows": 12, "passthru": False,
                "autocols": True, "showSearch": True, "deselect": True, "selectionType": "none",
                "columns": [], "mobileBreakpoint": "sm", "mobileBreakpointType": "defaults",
                "action": "replace", "x": x, "y": y, "wires": [[]]})


# Generador de comandos: añade id único y ts (segundos Unix)
CMD_JS = ("const now = Date.now();\n"
          "msg.payload = Object.assign({ id: 'nr-' + now + '-' + Math.floor(Math.random()*1000),"
          " ts: Math.floor(now/1000) }, msg.payload);\nreturn msg;")

mqtt_out("out_cmd", 6, 14)
func("f_cmd", "Añadir id y ts", CMD_JS, 1, 5, 14, [["out_cmd"]])

# ------------------------------------------------------------ A. principal
TEL_JS = """const t = msg.payload;
const ts = Date.now();
function m(v, topic) { return (v === null || v === undefined) ? null : { payload: v, topic: topic, timestamp: ts }; }
return [
  m(t.soil && t.soil.valid ? t.soil.vwc_pct : null, 'Humedad suelo %VWC'),
  m(t.tank && t.tank.level_pct !== null ? t.tank.level_pct : null, 'Tinaco %'),
  m(t.env && t.env.valid ? t.env.temp_c : null, 'Temperatura C'),
  m(t.env && t.env.valid ? t.env.rh_pct : null, 'HR ambiente %'),
  m(t.flow ? t.flow.lpm : null, 'Caudal L/min'),
  m(t.flow ? t.flow.today_l : null, 'Litros hoy'),
  { payload: (t.soil ? t.soil.status : '-') + ' | ' + (t.soil ? t.soil.mv + ' mV' : '') },
  { payload: (t.tank ? t.tank.status : '-') + ' | ' + (t.tank && t.tank.distance_cm !== null ? t.tank.distance_cm + ' cm' : 'sin eco') },
  { payload: t.simulation ? 'SIMULACIÓN (salidas inactivas)' : 'Sensores reales' }
];"""
mqtt_in("in_tel", BASE + "/telemetry", 0, 0, ["f_tel"], qos="0")
func("f_tel", "Separar telemetría", TEL_JS, 9, 1, 0,
     [["g_soil", "c_soil"], ["g_tank", "c_tank"], ["g_temp", "c_temp"], ["g_rh", "c_rh"],
      ["g_flow", "c_flow"], ["t_today", "c_today"], ["t_soilst"], ["t_tankst"], ["t_sim"]])
gauge("g_soil", "g_principal", 1, "Humedad del suelo", "%VWC", 0, 60,
      [(0, "#c62828"), (25, "#f9a825"), (35, "#2e7d32"), (45, "#1565c0")], 2, 0)
gauge("g_tank", "g_principal", 2, "Nivel del tinaco", "%", 0, 100,
      [(0, "#c62828"), (20, "#f9a825"), (40, "#2e7d32")], 2, 1)
gauge("g_temp", "g_principal", 3, "Temperatura ambiente", "°C", -5, 50,
      [(-5, "#1565c0"), (15, "#2e7d32"), (30, "#f9a825"), (35, "#c62828")], 2, 2)
gauge("g_rh", "g_principal", 4, "Humedad relativa del aire", "%HR", 0, 100,
      [(0, "#f9a825"), (30, "#2e7d32"), (80, "#1565c0")], 2, 3)
gauge("g_flow", "g_principal", 5, "Caudal", "L/min", 0, 8,
      [(0, "#9e9e9e"), (1, "#2e7d32"), (6, "#c62828")], 2, 4)
text("t_today", "g_principal", 6, "Litros hoy", 2, 5, "{{msg.payload}} L")
text("t_soilst", "g_principal", 7, "Estado EC-5", 2, 6)
text("t_tankst", "g_principal", 8, "Estado tinaco", 2, 7)
text("t_sim", "g_principal", 9, "Origen de datos", 2, 8)

STATE_JS = """const s = msg.payload;
const w = s.watering || {}; const e = s.event || {};
flow.set('state', s);
return [
  { payload: s.pump ? 'ENCENDIDA' : 'APAGADA' },
  { payload: s.valve ? 'ABIERTA' : 'CERRADA' },
  { payload: s.state + (s.phase && s.phase !== 'NONE' ? ' / ' + s.phase : '') },
  { payload: (s.mqtt ? 'MQTT OK' : 'MQTT —') + ' | Wi-Fi ' + (s.wifi ? 'OK' : '—') + ' | RSSI ' + s.rssi },
  { payload: w.active ? (w.delivered_l + ' / ' + w.target_l + ' L (' + w.progress_pct + ' %) ' + w.elapsed_s + ' s') : 'Sin riego' },
  { payload: w.active ? w.progress_pct : 0 },
  { payload: s.auto_enabled },
  { payload: s.decision ? s.decision.code + ': ' + s.decision.text : '-' },
  { payload: 'Próximo horario: ' + s.next_window + (s.time_valid ? '' : ' (SIN HORA)') },
  { payload: 'Ciclos: ' + e.cycles + ' | ' + e.liters + ' L' + (e.infiltration_remaining_s ? ' | infiltración ' + e.infiltration_remaining_s + ' s' : '') },
  { payload: (s.alarms && s.alarms.length) ? s.alarms.join(', ') : 'Sin alarmas' },
  { payload: 'Modo ' + s.mode + ' | Potencia ' + (s.power_outputs ? 'HABILITADA' : 'DESHABILITADA') + (s.simulation ? ' | SIMULACIÓN' : '') }
];"""
mqtt_in("in_state", BASE + "/state", 0, 10, ["f_state"])
func("f_state", "Separar estado", STATE_JS, 12, 1, 10,
     [["t_pump"], ["t_valve"], ["t_state"], ["t_comms"], ["t_progress"], ["g_progress"], ["sw_auto"],
      ["t_decision"], ["t_next"], ["t_cycles"], ["t_alarms"], ["t_mode"]])
text("t_pump", "g_principal", 10, "Bomba", 2, 9)
text("t_valve", "g_principal", 11, "Electroválvula", 2, 10)
text("t_state", "g_principal", 12, "Estado del riego", 2, 11)
text("t_comms", "g_principal", 13, "Comunicación", 2, 12)
text("t_mode", "g_principal", 14, "Modo", 2, 13)

STATUS_JS = "msg.payload = msg.payload.online ? 'ESP32 EN LÍNEA' : 'ESP32 DESCONECTADO (LWT)';\nreturn msg;"
mqtt_in("in_status", BASE + "/status", 0, 14, ["f_status"])
func("f_status", "Online / offline", STATUS_JS, 1, 1, 14, [["t_online"]])
text("t_online", "g_principal", 15, "ESP32", 2, 14)

# ------------------------------------------------- B. humedad del suelo
CFG_JS = """const p = msg.payload.params || {};
flow.set('cfg', p);
return [
  { payload: p.hum_min }, { payload: p.hum_target }, { payload: p.hum_max },
  { payload: 'Guardado en ESP32: mín ' + p.hum_min + ' / obj ' + p.hum_target + ' / máx ' + p.hum_max + ' %VWC' },
  { payload: p.liters_per_cycle + ' L por ciclo | infiltración ' + p.infilt_min + ' min | máx ' + p.max_cycles + ' ciclos' },
  { payload: 'Horario 1: ' + (p.win1_en ? p.win1_start + '-' + p.win1_end : 'OFF') + ' | Horario 2: ' + (p.win2_en ? p.win2_start + '-' + p.win2_end : 'OFF') },
  { payload: 'Tinaco: ' + (msg.payload.tank_calibrated ? 'calibrado' : 'SIN CALIBRAR') + ' | mínimo ' + p.tank_min_pct + ' %' },
  { payload: 'Máximos: ' + p.max_liters_event + ' L/evento, ' + p.max_liters_daily + ' L/día | ' + p.pulses_per_liter + ' pulsos/L' }
];"""
mqtt_in("in_cfg", BASE + "/config", 0, 16, ["f_cfg"])
func("f_cfg", "Separar configuración", CFG_JS, 8, 1, 16,
     [["s_min"], ["s_target"], ["s_max"], ["t_hum_saved"], ["t_auto_cfg"], ["t_sched"], ["t_tankcfg"], ["t_limits"]])
HUM_JS = """// Guarda el valor del slider y envía SET_HUMIDITY_RANGE con los tres valores
const p = flow.get('cfg') || {};
const h = flow.get('hum') || { min: p.hum_min, target: p.hum_target, max: p.hum_max };
h[msg.topic] = Number(msg.payload);
flow.set('hum', h);
if (!(h.min < h.target && h.target < h.max)) {
  node.warn('No se envía: debe cumplirse MÍNIMA < OBJETIVO < MÁXIMA');
  return [null, { payload: 'Revise: MÍNIMA < OBJETIVO < MÁXIMA' }];
}
return [{ payload: { cmd: 'SET_HUMIDITY_RANGE', min: h.min, target: h.target, max: h.max } }, null];"""
slider("s_min", "g_humedad", 1, "HUMEDAD MÍNIMA (%VWC)", 5, 60, 0.5, 2, 16, ["ch_min"])
slider("s_target", "g_humedad", 2, "HUMEDAD RECOMENDADA / OBJETIVO (%VWC)", 5, 65, 0.5, 2, 17, ["ch_target"])
slider("s_max", "g_humedad", 3, "HUMEDAD MÁXIMA (%VWC)", 5, 70, 0.5, 2, 18, ["ch_max"])
for cid, key, row in (("ch_min", "min", 16), ("ch_target", "target", 17), ("ch_max", "max", 18)):
    x, y = pos(3, row)
    add({"id": cid, "type": "change", "z": TAB, "name": "topic=" + key,
         "rules": [{"t": "set", "p": "topic", "pt": "msg", "to": key, "tot": "str"}],
         "action": "", "property": "", "from": "", "to": "", "reg": False, "x": x, "y": y, "wires": [["f_hum"]]})
func("f_hum", "Rango de humedad", HUM_JS, 2, 4, 17, [["f_cmd"], ["t_hum_saved"]])
text("t_hum_saved", "g_humedad", 4, "Confirmación", 2, 19, width=4)

# ------------------------------------------------------- C. riego manual
slider("s_liters", "g_manual", 1, "Litros a regar", 0.1, 3, 0.1, 2, 21, ["ch_liters"])
x, y = pos(3, 21)
add({"id": "ch_liters", "type": "change", "z": TAB, "name": "Guardar litros",
     "rules": [{"t": "set", "p": "liters", "pt": "flow", "to": "payload", "tot": "msg"}],
     "action": "", "property": "", "from": "", "to": "", "reg": False, "x": x, "y": y, "wires": [[]]})
START_JS = """const l = Number(flow.get('liters') || 1.0);
msg.payload = { cmd: 'START_MANUAL', liters: Math.round(l * 100) / 100 };
return msg;"""
button("b_start", "g_manual", 2, "START", "start", "#2e7d32", 2, 22, ["f_start"])
func("f_start", "START_MANUAL", START_JS, 1, 3, 22, [["f_cmd"]])
button("b_stop", "g_manual", 3, "STOP", "stop", "#c62828", 2, 23, ["f_stop"])
func("f_stop", "STOP", "msg.payload = { cmd: 'STOP' };\nreturn msg;", 1, 3, 23, [["f_cmd"]])
text("t_progress", "g_manual", 4, "Progreso", 2, 24, width=4)
gauge("g_progress", "g_manual", 5, "Progreso del riego", "%", 0, 100, [(0, "#1565c0"), (100, "#2e7d32")], 2, 25, width=4)

# --------------------------------------------------- D. riego automático
x, y = pos(2, 27)
add({"id": "sw_auto", "type": "ui-switch", "z": TAB, "name": "Riego automático", "label": "Riego automático",
     "group": "g_auto", "order": 1, "width": "4", "height": "1", "passthru": False, "decouple": True,
     "topic": "topic", "topicType": "msg", "style": "", "className": "", "layout": "row-spread",
     "clickableArea": "switch", "onvalue": "true", "onvalueType": "bool", "onicon": "", "oncolor": "",
     "offvalue": "false", "offvalueType": "bool", "officon": "", "offcolor": "", "x": x, "y": y,
     "wires": [["f_auto"]]})
func("f_auto", "ENABLE/DISABLE_AUTO", "msg.payload = { cmd: msg.payload ? 'ENABLE_AUTO' : 'DISABLE_AUTO' };\nreturn msg;",
     1, 3, 27, [["f_cmd"]])
text("t_decision", "g_auto", 2, "Decisión", 2, 28, width=4)
text("t_next", "g_auto", 3, "Horario", 2, 29, width=4)
text("t_cycles", "g_auto", 4, "Evento", 2, 30, width=4)
text("t_auto_cfg", "g_auto", 5, "Parámetros", 2, 31, width=4)
text("t_sched", "g_auto", 6, "Horarios", 2, 32, width=4)

# ------------------------------------------------------------ E. gráficas
chart("c_soil", "g_graficas", 1, "Humedad del suelo (%VWC)", 0, 60, 3, 0)
chart("c_tank", "g_graficas", 2, "Nivel del tinaco (%)", 0, 100, 3, 1)
chart("c_temp", "g_graficas", 3, "Temperatura (°C)", "", "", 3, 2)
chart("c_rh", "g_graficas", 4, "Humedad relativa del aire (%)", 0, 100, 3, 3)
chart("c_flow", "g_graficas", 5, "Caudal (L/min)", 0, 8, 3, 4)
chart("c_today", "g_graficas", 6, "Litros del día", 0, "", 3, 5)

# ----------------------------------------------------------- F. historial
EV_JS = """// Historial local (contexto de flujo; ver la guía para guardarlo en disco)
const e = msg.payload;
if (e.type !== 'WATERING_END' && e.type !== 'AUTO_EVENT_END') return null;
const h = flow.get('historial') || [];
const fecha = e.ts ? new Date(e.ts * 1000).toLocaleString('es-MX') : 'sin hora';
h.unshift({
  Fecha: fecha,
  Tipo: e.type === 'WATERING_END' ? 'Riego ' + e.reason : 'Evento automático',
  Resultado: e.result || e.why,
  Litros: e.delivered_l !== undefined ? e.delivered_l : e.liters,
  'Duración s': e.duration_s,
  'Humedad antes': e.vwc_before,
  'Humedad después': e.vwc_after
});
flow.set('historial', h.slice(0, 50));
msg.payload = h.slice(0, 50);
return msg;"""
mqtt_in("in_event", BASE + "/event", 0, 34, ["f_event"])
func("f_event", "Agregar al historial", EV_JS, 1, 1, 34, [["tb_hist"]])
table("tb_hist", "g_historial", 1, "Riegos", 2, 34)

# ------------------------------------------------ G. configuración/alertas
text("t_alarms", "g_alertas", 1, "Alarmas activas", 2, 36, width=4)
text("t_tankcfg", "g_alertas", 2, "Tinaco", 2, 37, width=4)
text("t_limits", "g_alertas", 3, "Límites", 2, 38, width=4)
button("b_clear", "g_alertas", 4, "CLEAR_ALARM (ALL)", "clear", "#ef6c00", 2, 39, ["f_clear"], width=4)
func("f_clear", "CLEAR_ALARM", "msg.payload = { cmd: 'CLEAR_ALARM', alarm: 'ALL' };\nreturn msg;", 1, 3, 39, [["f_cmd"]])

x, y = pos(3, 41)
add({"id": "notif", "type": "ui-notification", "z": TAB, "ui": "ui_base_huerto", "position": "top right",
     "colorDefault": False, "color": "#2e7d32", "displayTime": "6", "showCountdown": True, "outputs": 0,
     "allowDismiss": True, "dismissText": "Cerrar", "raw": False, "className": "", "name": "Avisos",
     "x": x, "y": y, "wires": []})
ACK_JS = """const a = msg.payload;
msg.payload = a.cmd + ': ' + a.status + ' — ' + a.message;
msg.ui_update = { color: a.status === 'OK' ? '#2e7d32' : '#c62828' };
return msg;"""
mqtt_in("in_ack", BASE + "/ack", 0, 41, ["f_ack"])
func("f_ack", "Confirmación de comando", ACK_JS, 1, 1, 41, [["notif"]])
ALM_JS = """const a = msg.payload;
msg.payload = 'ALARMA ' + a.code + (a.active ? ' ACTIVA: ' : ' resuelta: ') + a.message;
msg.ui_update = { color: a.severity === 'CRITICAL' ? '#c62828' : (a.severity === 'WARNING' ? '#ef6c00' : '#1565c0') };
return msg;"""
mqtt_in("in_alarm", BASE + "/alarm", 0, 42, ["f_alarm"])
func("f_alarm", "Aviso de alarma", ALM_JS, 1, 1, 42, [["notif"]])

x, y = pos(0, 44)
add({"id": "inj_status", "type": "inject", "z": TAB, "name": "Al iniciar: GET_STATUS + GET_CONFIG",
     "props": [{"p": "payload"}], "repeat": "", "crontab": "", "once": True, "onceDelay": "3",
     "topic": "", "payload": "", "payloadType": "date", "x": x, "y": y, "wires": [["f_init"]]})
func("f_init", "Pedir estado y config",
     "return [[{ payload: { cmd: 'GET_STATUS' } }, { payload: { cmd: 'GET_CONFIG' } }]];", 1, 1, 44, [["f_cmd"]])

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nodes, f, ensure_ascii=False, indent=2)

# Comprobación: todos los cables apuntan a nodos existentes
ids = {n["id"] for n in nodes}
missing = [(n["id"], w) for n in nodes for out in n.get("wires", []) for w in out if w not in ids]
print(f"{len(nodes)} nodos escritos en {os.path.relpath(OUT, ROOT)}")
print("Cables huérfanos:", missing if missing else "ninguno")
