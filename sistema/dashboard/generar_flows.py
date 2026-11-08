"""Genera el flujo completo de Node-RED + FlowFuse Dashboard 2.0 del riego inteligente.

Uso:
  python generar_flows.py --entorno casa   -> nodered/userdata/flows_riego.json y dashboard/export/flows_riego_casa.json
  python generar_flows.py --entorno final  -> dashboard/export/flows_riego_final.json (para la Raspberry Pi)

Las funciones están en dashboard/funciones/*.js y las páginas en dashboard/plantillas/*.vue.
El flujo NO contiene contraseñas: las credenciales del broker se agregan al desplegar
(tools/desplegar_flows.py) y Node-RED las guarda cifradas en flows_cred.json.
"""
import argparse
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FN = os.path.join(HERE, "funciones")
TPL = os.path.join(HERE, "plantillas")

ENVS = {
    "casa": {"topic_root": "huerto/casa", "client": "nodered-riego-casa", "label": "Casa (pruebas)", "title": "Equipo 2 Proyecto"},
    "final": {"topic_root": "huerto/final", "client": "nodered-riego-final", "label": "Huerto (definitivo)", "title": "Equipo 2 Proyecto"},
}

nodes = []


def nid(name):
    return hashlib.sha1(name.encode()).hexdigest()[:16]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def fn(name, tab, x, y, file, outputs, wires, prepend=None, label=None):
    code = read(os.path.join(FN, file))
    if prepend:
        code = read(os.path.join(FN, prepend)) + "\n" + code
    nodes.append({"id": nid(name), "type": "function", "z": tab, "name": label or name, "func": code,
                  "outputs": outputs, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
                  "x": x, "y": y, "wires": wires})
    return nid(name)


def node(name, ntype, tab, x, y, wires=None, **props):
    n = {"id": nid(name), "type": ntype, "x": x, "y": y, "name": props.pop("label", name)}
    if tab:
        n["z"] = tab
    if wires is not None:
        n["wires"] = wires
    n.update(props)
    nodes.append(n)
    return nid(name)


def ids(*names):
    return [nid(n) for n in names]


def wrap_script(fmt):
    """Dashboard 2.0 exige que el <script> empiece con 'export default':
    el código común y las constantes se encierran en una función."""
    a = fmt.index("<script>") + len("<script>")
    b = fmt.index("</script>")
    script = fmt[a:b]
    k = script.index("export default")
    prefix, body = script[:k], script[k + len("export default"):].strip()
    body = body.rstrip().rstrip(";")
    nl = chr(10)
    new = nl + "export default (function () {" + nl + prefix + nl + "return " + body + ";" + nl + "})();" + nl
    return fmt[:a] + new + fmt[b:]


def build(env):
    E = ENVS[env]
    nodes.clear()
    T1, T2, T3 = nid("tab_datos"), nid("tab_servicios"), nid("tab_dashboard")
    nodes.append({"id": T1, "type": "tab", "label": "Riego - Datos y comandos", "disabled": False,
                  "info": "Ingesta MQTT, comandos con ACK, alertas y estado del dashboard. Entorno: " + E["label"]})
    nodes.append({"id": T2, "type": "tab", "label": "Riego - Servicios", "disabled": False,
                  "info": "SQLite, Open-Meteo, crecimiento, IA (servidor), vigilancia, respaldos y CSV."})
    nodes.append({"id": T3, "type": "tab", "label": "Riego - Dashboard", "disabled": False,
                  "info": "Páginas de FlowFuse Dashboard 2.0 (plantillas Vue en dashboard/plantillas)."})

    # ----------------------------- Configuración ------------------------------
    BROKER = nid("broker")
    nodes.append({"id": BROKER, "type": "mqtt-broker", "name": "Mosquitto " + env, "broker": "${MQTT_HOST}",
                  "port": "${MQTT_PORT}", "clientid": E["client"], "autoConnect": True, "usetls": False,
                  "protocolVersion": "4", "keepalive": "30", "cleansession": True, "autoUnsubscribe": True,
                  "birthTopic": "", "birthQos": "0", "birthRetain": "false", "birthPayload": "", "birthMsg": {},
                  "closeTopic": "", "closeQos": "0", "closeRetain": "false", "closePayload": "", "closeMsg": {},
                  "willTopic": "", "willQos": "0", "willRetain": "false", "willPayload": "", "willMsg": {},
                  "userProps": "", "sessionExpiry": ""})
    DB = nid("sqlitedb")
    nodes.append({"id": DB, "type": "sqlitedb", "db": "${RIEGO_DB}", "mode": "RWC"})
    UI = nid("ui_base")
    nodes.append({"id": UI, "type": "ui-base", "name": E["title"], "path": "/dashboard", "appIcon": "",
                  "includeClientData": True, "acceptsClientConfig": ["ui-notification", "ui-control", "ui-template"],
                  "showPathInSidebar": False, "headerContent": "page", "navigationStyle": "default",
                  "titleBarStyle": "default", "showReconnectNotification": True, "notificationDisplayTime": 1,
                  "showDisconnectNotification": True, "allowInstall": True})
    THEME = nid("ui_theme")
    nodes.append({"id": THEME, "type": "ui-theme", "name": "Huerto",
                  "colors": {"surface": "#1b4332", "primary": "#2e7d32", "bgPage": "#f1f5f2",
                             "groupBg": "#ffffff", "groupOutline": "#d7e3da"},
                  "sizes": {"density": "default", "pagePadding": "12px", "groupGap": "12px",
                            "groupBorderRadius": "8px", "widgetGap": "12px"}})

    # ------------------------------ Páginas -----------------------------------
    common_js = read(os.path.join(TPL, "_comun.js"))
    cj_data = common_js.split("//@@DATA")[1].split("//@@COMPUTED")[0]
    cj_comp = common_js.split("//@@COMPUTED")[1].split("//@@METHODS")[0]
    cj_meth = common_js.split("//@@METHODS")[1]
    head = read(os.path.join(TPL, "_cabecera.html"))
    dialogs = read(os.path.join(TPL, "_dialogos.html"))
    css = read(os.path.join(TPL, "_estilos.css"))
    umbrales = read(os.path.join(FN, "umbrales.js"))
    umbrales_fn = umbrales[umbrales.index("function calcUmbrales("):].replace("function calcUmbrales(", "function (", 1).strip()
    pages = [("inicio", "Inicio", "home"), ("manual", "Manual", "hand-water"), ("automatico", "Automático", "robot"),
             ("ia", "IA", "brain"), ("cultivos", "Cultivos", "sprout"), ("crecimiento", "Crecimiento", "chart-timeline-variant"),
             ("clima", "Clima", "weather-partly-cloudy"), ("historial", "Historial", "history"),
             ("alertas", "Alertas", "bell-alert"), ("configuracion", "Configuración", "cog")]
    tpl_ids = []
    for i, (key, title, icon) in enumerate(pages):
        page = nid("page_" + key)
        nodes.append({"id": page, "type": "ui-page", "name": title, "ui": UI, "path": "/" + key, "icon": icon,
                      "layout": "grid", "theme": THEME, "breakpoints": [
                          {"name": "Default", "px": 0, "cols": 3}, {"name": "Tablet", "px": 576, "cols": 6},
                          {"name": "Small Desktop", "px": 768, "cols": 9}, {"name": "Desktop", "px": 1024, "cols": 12}],
                      "order": i + 1, "className": "", "visible": "true", "disabled": "false"})
        grp = nid("group_" + key)
        nodes.append({"id": grp, "type": "ui-group", "name": title, "page": page, "width": "12", "height": "1",
                      "order": 1, "showTitle": False, "className": "", "visible": "true", "disabled": "false",
                      "groupType": "default"})
        fmt = read(os.path.join(TPL, key + ".vue"))
        fmt = (fmt.replace("@@CABECERA@@", head).replace("@@DIALOGOS@@", dialogs)
               .replace("    mixins: [@@COMUNJS@@]," + chr(10), "").replace("@@ESTILOS@@", css).replace("@@UMBRALES_FN@@", umbrales_fn))
        fmt = fmt.replace("data () { return {}; }", "data () { return ({ }); }")
        i = fmt.index("data () {")
        j = fmt.index("{", fmt.index("return", i)) + 1
        fmt = fmt[:j] + cj_data + fmt[j:]
        k = fmt.index("computed: {") + len("computed: {")
        fmt = fmt[:k] + cj_comp + fmt[k:]
        k = fmt.index("methods: {") + len("methods: {")
        fmt = fmt[:k] + cj_meth + fmt[k:]
        assert "@@" not in fmt, key
        tid = nid("tpl_" + key)
        nodes.append({"id": tid, "type": "ui-template", "z": T3, "group": grp, "page": "", "ui": "",
                      "name": "Página " + title, "order": 1, "width": "0", "height": "0", "head": "",
                      "format": fmt, "storeOutMessages": True, "passthru": False, "resendOnRefresh": True,
                      "templateScope": "local", "className": "", "x": 180, "y": 60 + i * 50,
                      "wires": [[nid("router")]]})
        tpl_ids.append(tid)
    node("Notificaciones", "ui-notification", T3, 600, 560, [[]], ui=UI, position="top right", colorDefault=True,
         color="", displayTime="8", showCountdown=True, outputs=1, allowDismiss=True, dismissText="Cerrar",
         allowConfirm=False, confirmText="Confirmar", raw=False, className="")
    node("link_in_ui", "link in", T3, 60, 300, [tpl_ids], links=[], label="a páginas")
    node("router", "switch", T3, 470, 300, [[nid("link_out_cmd")], [nid("link_out_req")]], property="topic",
         propertyType="msg", rules=[{"t": "eq", "v": "cmd", "vt": "str"}, {"t": "eq", "v": "req", "vt": "str"}],
         checkall="true", repair=False, outputs=2, label="comando o solicitud")
    node("link_out_cmd", "link out", T3, 650, 280, links=[nid("link_in_cmd")], mode="link", label="-> comando")
    node("link_out_req", "link out", T3, 650, 320, links=[nid("link_in_req")], mode="link", label="-> solicitud")
    node("link_in_notif", "link in", T3, 400, 560, [[nid("Notificaciones")]], links=[], label="notificaciones")

    # --------------------------- Datos y comandos -----------------------------
    node("mqtt_in", "mqtt in", T1, 120, 80, [[nid("ingesta")]], topic=E["topic_root"] + "/+/+", qos="1",
         datatype="auto-detect", broker=BROKER, nl=False, rap=True, rh=0, inputs=0, label="dispositivos " + env)
    fn("ingesta", T1, 330, 80, "ingesta.js", 6,
       [ids("lo_dbw_1"), ids("lo_snap_1"), ids("acks"), ids("alertas"), [], ids("mqtt_out")], label="ingesta MQTT")
    fn("acks", T1, 560, 140, "acks.js", 2, [ids("lo_ui_1"), ids("lo_dbw_2")], label="ACK -> resultado")
    fn("alertas", T1, 560, 220, "alertas.js", 3, [ids("lo_dbw_3"), ids("lo_notif_1"), ids("lo_snap_2")])
    node("st_mqtt", "status", T1, 120, 300, [[nid("broker_estado")]], scope=[nid("mqtt_in")], label="estado MQTT")
    fn("broker_estado", T1, 330, 300, "broker_estado.js", 2, [ids("lo_snap_3"), ids("alertas")], label="estado del broker")
    node("link_in_snap", "link in", T1, 120, 380, [[nid("snapshot")]], links=[], label="refrescar")
    fn("snapshot", T1, 330, 380, "snapshot.js", 1, [ids("lo_ui_2")], label="estado para el dashboard")
    node("link_in_cmd", "link in", T1, 120, 460, [[nid("comando")]], links=[nid("link_out_cmd")], label="comando")
    fn("comando", T1, 330, 460, "comando.js", 3, [ids("mqtt_out"), ids("lo_ui_3"), ids("lo_dbw_4")],
       label="comando -> ESP32")
    node("mqtt_out", "mqtt out", T1, 560, 440, None, topic="", qos="", retain="", respTopic="", contentType="",
         userProps="", correl="", expiry="", broker=BROKER, label="publicar comando")
    nodes[-1]["wires"] = []
    node("link_in_req", "link in", T1, 120, 540, [[nid("solicitudes")]], links=[nid("link_out_req")], label="solicitud")
    fn("solicitudes", T1, 330, 540, "solicitudes.js", 7,
       [ids("call_dbq"), ids("lo_dbw_5"), ids("lo_snap_4"), ids("comando"), ids("lo_clima"), ids("lo_bk"), ids("lo_ui_4")])
    node("call_dbq", "link call", T1, 560, 540, [[nid("respuesta")]], links=[nid("link_in_dbq")], linkType="static",
         timeout="30", label="consultar SQLite")
    fn("respuesta", T1, 760, 540, "respuesta.js", 4, [ids("lo_ui_5"), ids("comando"), ids("lo_crec"), ids("lo_dbw_6")],
       prepend="umbrales.js", label="respuesta SQLite")

    ui_outs = ["lo_ui_%d" % i for i in range(1, 6)]
    for i, name in enumerate(ui_outs):
        node(name, "link out", T1, 980, 80 + i * 60, links=[nid("link_in_ui")], mode="link", label="-> páginas")
    dbw_outs = ["lo_dbw_%d" % i for i in range(1, 7)]
    snap_outs = ["lo_snap_%d" % i for i in range(1, 5)]
    for i, name in enumerate(dbw_outs):
        node(name, "link out", T1, 980, 420 + i * 40, links=[nid("link_in_dbw")], mode="link", label="-> SQLite")
    for i, name in enumerate(snap_outs):
        node(name, "link out", T1, 1160, 80 + i * 40, links=[nid("link_in_snap")], mode="link", label="-> refrescar")
    node("lo_notif_1", "link out", T1, 980, 680, links=[nid("link_in_notif")], mode="link", label="-> notificación")
    node("lo_clima", "link out", T1, 560, 620, links=[nid("link_in_clima")], mode="link", label="-> clima")
    node("lo_bk", "link out", T1, 560, 660, links=[nid("link_in_bk")], mode="link", label="-> respaldo")
    node("lo_crec", "link out", T1, 980, 720, links=[nid("link_in_crec")], mode="link", label="-> crecimiento")

    # ------------------------------- Servicios --------------------------------
    node("link_in_dbw", "link in", T2, 100, 60, [[nid("sqlite_w")]], links=ids(*dbw_outs, "lo_dbw_s1", "lo_dbw_s2", "lo_dbw_s3", "lo_dbw_s4", "lo_dbw_s5"),
         label="escritura SQLite")
    node("sqlite_w", "sqlite", T2, 300, 60, [[]], mydb=DB, sqlquery="msg.topic", sql="", label="SQLite escritura")
    node("link_in_dbq", "link in", T2, 100, 120, [[nid("sqlite_q")]], links=[], label="consulta SQLite")
    node("sqlite_q", "sqlite", T2, 300, 120, [[nid("ret_dbq")]], mydb=DB, sqlquery="msg.topic", sql="", label="SQLite consulta")
    node("ret_dbq", "link out", T2, 480, 120, mode="return", links=[], label="respuesta")
    node("catch_db", "catch", T2, 100, 180, [[nid("f_catch")]], scope=ids("sqlite_w", "sqlite_q", "sqlite_bk", "sqlite_csv"),
         uncaught=False, label="errores SQLite")
    nodes.append({"id": nid("f_catch"), "type": "function", "z": T2, "name": "problema de almacenamiento",
                  "func": "global.set('db_ok', false);\nreturn { topic: 'alert', device: 'servidor', payload: { code: 'STORAGE_ERROR', severity: 'CRITICAL', "
                          "message: 'Error de SQLite: ' + ((msg.error || {}).message || '') + ' | ' + String(msg.topic || '').slice(0, 80) } };",
                  "outputs": 1, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [], "x": 300, "y": 180,
                  "wires": [[nid("lo_alert_s")]]})
    node("lo_alert_s", "link out", T2, 500, 180, links=[nid("link_in_alert")], mode="link", label="-> alertas")
    node("link_in_alert", "link in", T1, 330, 220, [[nid("alertas")]], links=ids("lo_alert_s", "lo_alert_s2", "lo_alert_s3", "lo_alert_s4"),
         label="alertas")

    # Open-Meteo
    node("inj_clima", "inject", T2, 120, 260, [[nid("clima_pedir")]], props=[{"p": "topic", "vt": "str"}],
         repeat="1800", crontab="", once=True, onceDelay="5", topic="periodic", label="cada 30 min")
    node("link_in_clima", "link in", T2, 120, 300, [[nid("clima_pedir")]], links=[nid("lo_clima")], label="actualizar clima")
    fn("clima_pedir", T2, 330, 280, "clima_pedir.js", 1, [ids("http_om")], label="consulta Open-Meteo")
    node("http_om", "http request", T2, 530, 280, [[nid("clima_procesar")]], method="GET", ret="obj", paytoqs="ignore",
         url="", tls="", persist=False, proxy="", insecureHTTPParser=False, authType="", senderr=False, headers=[],
         label="HTTPS api.open-meteo.com")
    fn("clima_procesar", T2, 740, 280, "clima_procesar.js", 3, [ids("lo_dbw_s1"), ids("lo_snap_s1"), ids("lo_alert_s2")],
       label="procesar pronóstico")

    # Crecimiento
    node("inj_crec", "inject", T2, 120, 380, [[nid("crecimiento")]], props=[{"p": "topic", "vt": "str"}],
         repeat="600", crontab="", once=True, onceDelay="12", topic="tick", label="cada 10 min")
    node("link_in_crec", "link in", T2, 120, 420, [[nid("crecimiento")]], links=[nid("lo_crec")], label="recalcular")
    fn("crecimiento", T2, 330, 400, "crecimiento.js", 4, [ids("lo_dbw_s2"), ids("lo_snap_s2"), ids("lo_alert_s3"), ids("lo_req_s1")],
       label="etapas de crecimiento")

    # Arranque: cargar caches
    nodes.append({"id": nid("inj_boot"), "type": "inject", "z": T2, "name": "al iniciar", "props": [{"p": "payload"}],
                  "repeat": "", "crontab": "", "once": True, "onceDelay": "2", "topic": "", "payload": "", "payloadType": "date",
                  "x": 120, "y": 480, "wires": [[nid("boot_reqs")]]})
    nodes.append({"id": nid("boot_reqs"), "type": "function", "z": T2, "name": "solicitudes de arranque",
                  "func": "return [[{topic:'req',payload:{type:'plantings_list'}},{topic:'req',payload:{type:'crops_list'}},"
                          "{topic:'req',payload:{type:'boot_hist'}},{topic:'req',payload:{type:'db_stats'}}]];",
                  "outputs": 1, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [], "x": 330, "y": 480,
                  "wires": [[nid("lo_req_s1")]]})
    node("lo_req_s1", "link out", T2, 560, 440, links=[nid("link_in_req")], mode="link", label="-> solicitud")
    # El link in de solicitudes también recibe del servicio
    for n in nodes:
        if n["id"] == nid("link_in_req"):
            n["links"].append(nid("lo_req_s1"))

    # IA servidor
    node("inj_ia", "inject", T2, 120, 560, [[nid("ia_servidor")]], props=[{"p": "topic", "vt": "str"}],
         repeat="300", crontab="", once=True, onceDelay="20", topic="tick", label="cada 5 min")
    fn("ia_servidor", T2, 330, 560, "ia_servidor.js", 1, [ids("lo_dbw_s3")], label="predicciones vs real")

    # Vigilancia
    node("inj_vig", "inject", T2, 120, 620, [[nid("vigilancia")]], props=[{"p": "topic", "vt": "str"}],
         repeat="60", crontab="", once=True, onceDelay="30", topic="tick", label="cada minuto")
    fn("vigilancia", T2, 330, 620, "vigilancia.js", 2, [ids("lo_alert_s4"), ids("lo_snap_s3")], label="vigilancia")

    # Respaldos
    node("inj_bk", "inject", T2, 120, 700, [[nid("respaldo")]], props=[{"p": "topic", "vt": "str"}],
         repeat="", crontab="00 03 * * *", once=False, onceDelay="", topic="diario", label="diario 03:00")
    node("link_in_bk", "link in", T2, 120, 740, [[nid("respaldo")]], links=[nid("lo_bk")], label="respaldar ahora")
    fn("respaldo", T2, 330, 720, "respaldo.js", 1, [ids("sqlite_bk")], label="respaldo SQLite + flujos")
    node("sqlite_bk", "sqlite", T2, 530, 720, [[nid("respaldo_listar")]], mydb=DB, sqlquery="msg.topic", sql="", label="VACUUM INTO")
    nodes.append({"id": nid("inj_bklist"), "type": "inject", "z": T2, "name": "listar al iniciar", "props": [{"p": "payload"}],
                  "repeat": "3600", "crontab": "", "once": True, "onceDelay": "4", "topic": "", "payload": "", "payloadType": "date",
                  "x": 330, "y": 780, "wires": [[nid("respaldo_listar")]]})
    fn("respaldo_listar", T2, 740, 740, "respaldo_listar.js", 2, [ids("lo_snap_s4"), ids("lo_notif_s")], label="listar respaldos")
    node("lo_notif_s", "link out", T2, 940, 760, links=[nid("link_in_notif")], mode="link", label="-> notificación")

    # CSV
    node("http_csv", "http in", T2, 130, 840, [[nid("csv_consulta")]], url="/riego/export.csv", method="get",
         upload=False, swaggerDoc="", label="GET /riego/export.csv")
    fn("csv_consulta", T2, 330, 840, "csv_consulta.js", 1, [ids("sqlite_csv")], label="consulta CSV")
    node("sqlite_csv", "sqlite", T2, 530, 840, [[nid("csv_formato")]], mydb=DB, sqlquery="msg.topic", sql="", label="SQLite CSV")
    fn("csv_formato", T2, 730, 840, "csv_formato.js", 1, [ids("http_resp")], label="formato CSV")
    node("http_resp", "http response", T2, 920, 840, None, statusCode="", headers={}, label="descarga")
    nodes[-1]["wires"] = []

    for i in range(1, 6):
        node("lo_dbw_s%d" % i, "link out", T2, 980, 40 + i * 40, links=[nid("link_in_dbw")], mode="link", label="-> SQLite")
    for i in range(1, 5):
        node("lo_snap_s%d" % i, "link out", T2, 1160, 40 + i * 40, links=[nid("link_in_snap")], mode="link", label="-> refrescar")
    for name in ("lo_alert_s2", "lo_alert_s3", "lo_alert_s4"):
        node(name, "link out", T2, 980, 300 + len(name), links=[nid("link_in_alert")], mode="link", label="-> alertas")

    # Enlaces de vuelta (link in de refrescar/ui/notificaciones/dbq)
    back = {"link_in_snap": snap_outs + ["lo_snap_s%d" % i for i in range(1, 5)],
            "link_in_ui": ui_outs, "link_in_notif": ["lo_notif_1", "lo_notif_s"]}
    for n in nodes:
        for k, v in back.items():
            if n["id"] == nid(k):
                n["links"] = ids(*v)
    # alertas desde broker/ingesta van directo; desde servicios por link
    return nodes


def check(flow):
    byid = {n["id"]: n for n in flow}
    problems = []
    for n in flow:
        for out in n.get("wires", []):
            for t in out:
                if t not in byid:
                    problems.append("%s (%s) -> %s inexistente" % (n.get("name"), n["type"], t))
        for t in n.get("links", []):
            if t not in byid:
                problems.append("link %s -> %s inexistente" % (n.get("name"), t))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entorno", default="casa", choices=list(ENVS))
    a = ap.parse_args()
    flow = build(a.entorno)
    probs = check(flow)
    if probs:
        raise SystemExit("ERRORES:\n" + "\n".join(probs))
    out_dir = os.path.join(HERE, "export")
    os.makedirs(out_dir, exist_ok=True)
    data = json.dumps(flow, ensure_ascii=False, indent=1)
    path = os.path.join(out_dir, "flows_riego_%s.json" % a.entorno)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
    print("Flujo generado:", path, "(%d nodos)" % len(flow))


if __name__ == "__main__":
    main()
