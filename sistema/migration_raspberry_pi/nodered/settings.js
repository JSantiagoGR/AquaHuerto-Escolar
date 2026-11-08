/**
 * Node-RED - Riego inteligente (instancia AISLADA del entorno CASA)
 *
 * - Directorio de usuario propio: nodered/userdata (no toca otras prácticas).
 * - Editor protegido con usuario/contraseña (adminAuth).
 * - Dashboard 2.0 en /dashboard protegido con autenticación básica (httpNodeAuth).
 * - Las credenciales se leen de configs/secrets/<archivo>.env y se pasan como
 *   variables de entorno: los flujos exportados NO contienen contraseñas.
 * - El mismo archivo sirve en la Raspberry Pi cambiando RIEGO_ENV_FILE.
 */
const fs = require("fs");
const path = require("path");

const PROJECT = path.resolve(__dirname, "..", "..");
const ENV_FILE = process.env.RIEGO_ENV_FILE ||
    path.join(PROJECT, "configs", "secrets", "credenciales_casa.env");

function loadEnv(file) {
    const vals = {};
    try {
        for (const raw of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
            const line = raw.trim();
            if (!line || line.startsWith("#") || !line.includes("=")) continue;
            const i = line.indexOf("=");
            vals[line.slice(0, i).trim()] = line.slice(i + 1).trim();
        }
    } catch (e) {
        console.error("[riego] No se pudo leer el archivo de credenciales:", file);
    }
    return vals;
}

const secrets = loadEnv(ENV_FILE);
for (const [k, v] of Object.entries(secrets)) {
    if (process.env[k] === undefined) process.env[k] = v;
}
// Rutas y parámetros del entorno (no secretos)
process.env.RIEGO_PROJECT = process.env.RIEGO_PROJECT || PROJECT;
process.env.RIEGO_ENV = process.env.RIEGO_ENV || "casa";
process.env.RIEGO_DB = process.env.RIEGO_DB || path.join(PROJECT, "database", "riego_" + process.env.RIEGO_ENV + ".db");
process.env.RIEGO_BACKUPS = process.env.RIEGO_BACKUPS || path.join(PROJECT, "backups");
process.env.RIEGO_TOPIC_ROOT = process.env.RIEGO_TOPIC_ROOT || ("huerto/" + process.env.RIEGO_ENV);
process.env.MQTT_HOST = process.env.MQTT_HOST || "127.0.0.1";
process.env.MQTT_PORT = process.env.MQTT_PORT || "1883";

// bcryptjs viene con Node-RED (runtime local)
let bcrypt;
try {
    bcrypt = require(path.join(PROJECT, "nodered", "runtime", "node_modules", "bcryptjs"));
} catch (e) {
    bcrypt = require("bcryptjs");
}
const hash = (p) => bcrypt.hashSync(String(p || ""), 10);

// ¿Petición desde esta computadora o con usuario/contraseña del dashboard?
const crypto = require("crypto");
function sameText(a, b) {
    const x = Buffer.from(String(a)), y = Buffer.from(String(b));
    return x.length === y.length && crypto.timingSafeEqual(x, y);
}
function allowed(req) {
    // DASHBOARD_PUBLIC=1: dashboard abierto para cualquiera en la red local (el editor sigue protegido con adminAuth)
    if (process.env.DASHBOARD_PUBLIC === "1") return true;
    const ip = String((req.socket && req.socket.remoteAddress) || "");
    if (ip === "127.0.0.1" || ip === "::1" || ip === "::ffff:127.0.0.1") return true;
    const h = String((req.headers && req.headers.authorization) || "");
    if (!h.startsWith("Basic ")) return false;
    const [u, ...rest] = Buffer.from(h.slice(6), "base64").toString("utf8").split(":");
    return sameText(u, process.env.DASHBOARD_USER || "huerto") &&
           !!process.env.DASHBOARD_PASS && sameText(rest.join(":"), process.env.DASHBOARD_PASS);
}
function httpAuth(req, res, next) {
    if (allowed(req)) return next();
    res.set("WWW-Authenticate", 'Basic realm="Riego inteligente"');
    res.status(401).send("Autenticacion requerida");
}

module.exports = {
    uiPort: parseInt(process.env.PORT || "1880", 10),
    uiHost: "0.0.0.0",              // Alcanzable en la red local (firewall: solo subred local)

    flowFile: "flows_riego.json",
    flowFilePretty: true,
    credentialSecret: process.env.NODERED_CREDENTIAL_SECRET || false,
    userDir: __dirname,

    adminAuth: {
        type: "credentials",
        users: [{
            username: process.env.NODERED_ADMIN_USER || "admin",
            password: hash(process.env.NODERED_ADMIN_PASS),
            permissions: "*",
        }],
    },
    // Dashboard, socket.io del dashboard y /riego/export.csv: sin contraseña desde ESTA
    // computadora (127.0.0.1); desde otros equipos de la red (celular) se pide usuario
    // y contraseña (Basic). Node-RED aplica httpNodeMiddleware a los nodos http-in;
    // Dashboard 2.0 usa dashboard.middleware (HTTP) y dashboard.ioMiddleware (socket.io).
    httpNodeMiddleware: httpAuth,
    dashboard: {
        middleware: httpAuth,
        ioMiddleware: function (socket, next) {
            const req = socket.request;
            // Igual que el middleware por defecto del Dashboard: sin websocket directo ni otro dominio
            if (String(socket.client.conn.request.url || "").indexOf("transport=websocket") !== -1) {
                return next(new Error("rechazado"));
            }
            if (socket.handshake.xdomain !== false) return next(new Error("rechazado"));
            return allowed(req) ? next() : next(new Error("Autenticacion requerida"));
        },
    },

    diagnostics: { enabled: false, ui: false },
    runtimeState: { enabled: false, ui: false },
    telemetry: { enabled: false, updateNotification: false },

    logging: {
        console: { level: "info", metrics: false, audit: false },
    },

    contextStorage: {
        default: { module: "memory" },
        file: { module: "localfilesystem", config: { flushInterval: 30 } },
    },

    exportGlobalContextKeys: false,
    externalModules: { autoInstall: false, palette: { allowInstall: false } },
    functionExternalModules: false,
    functionGlobalContext: {
        fs: require("fs"),
        path: require("path"),
        crypto: require("crypto"),
    },
    functionTimeout: 0,
    debugMaxLength: 2000,
    mqttReconnectTime: 5000,
    serialReconnectTime: 15000,

    editorTheme: {
        page: { title: "Riego inteligente - Node-RED (" + process.env.RIEGO_ENV + ")" },
        header: { title: "Riego inteligente - entorno " + process.env.RIEGO_ENV },
        projects: { enabled: false },
        tours: false,
        palette: { editable: false },
        codeEditor: { lib: "monaco" },
    },
};
