"""Despliega el flujo generado en Node-RED por su Admin API (autenticada).

- Agrega las credenciales del broker desde el archivo de secretos (NO están en el JSON).
- Node-RED las guarda cifradas (credentialSecret) en flows_cred.json.
- Despliegue completo ("full"): reemplaza el flujo de ESTA instancia aislada solamente.

Uso: python desplegar_flows.py [--entorno casa] [--url http://127.0.0.1:1880] [--env-file ...]
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_env(path):
    vals = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals


def http(method, url, data=None, headers=None):
    body = None
    h = dict(headers or {})
    if data is not None:
        if isinstance(data, dict) and h.get("Content-Type") == "application/x-www-form-urlencoded":
            body = urllib.parse.urlencode(data).encode()
        else:
            body = json.dumps(data).encode()
            h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        txt = r.read().decode()
        return r.status, (json.loads(txt) if txt else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entorno", default="casa")
    ap.add_argument("--url", default="http://127.0.0.1:1880")
    ap.add_argument("--env-file", default=os.path.join(ROOT, "configs", "secrets", "credenciales_casa.env"))
    a = ap.parse_args()
    sec = read_env(a.env_file)
    flow_path = os.path.join(ROOT, "dashboard", "export", "flows_riego_%s.json" % a.entorno)
    with open(flow_path, encoding="utf-8") as f:
        flow = json.load(f)
    for n in flow:
        if n["type"] == "mqtt-broker":
            n["credentials"] = {"user": sec["MQTT_NODERED_USER"], "password": sec["MQTT_NODERED_PASS"]}
    st, tok = http("POST", a.url + "/auth/token", {
        "client_id": "node-red-admin", "grant_type": "password", "scope": "*",
        "username": sec.get("NODERED_ADMIN_USER", "admin"), "password": sec["NODERED_ADMIN_PASS"]},
        {"Content-Type": "application/x-www-form-urlencoded"})
    auth = {"Authorization": "Bearer " + tok["access_token"], "Node-RED-API-Version": "v2"}
    st, cur = http("GET", a.url + "/flows", headers=auth)
    st, res = http("POST", a.url + "/flows", {"flows": flow, "rev": cur.get("rev")},
                   dict(auth, **{"Node-RED-Deployment-Type": "full"}))
    print("Despliegue OK (HTTP %d): %d nodos, revision %s" % (st, len(flow), (res or {}).get("rev")))
    http("POST", a.url + "/auth/revoke", {"token": tok["access_token"]}, auth)
    return 0


if __name__ == "__main__":
    sys.exit(main())
