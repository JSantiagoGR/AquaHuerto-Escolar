"""Validacion estructural + simulacion de los modelos EPANET del cajon de riego.

Uso:  python validar_modelo.py riego_huerto_final.inp [--json salida.json]
Requiere: wntr (incluye la libreria EPANET 2.2) y epyt (toolkit OWA-EPANET).
"""
import sys, json, re, os, tempfile

inp = sys.argv[1]
out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
report = {"file": os.path.abspath(inp), "checks": [], "errors": [], "warnings": []}


def check(name, ok, detail=""):
    report["checks"].append({"check": name, "ok": bool(ok), "detail": str(detail)})
    print(("[OK]   " if ok else "[FAIL] ") + name + (f"  -> {detail}" if detail else ""))
    if not ok:
        report["errors"].append(name + " " + str(detail))


# ---------- 1. Parseo de secciones (texto crudo) ----------
sections, cur = {}, None
with open(inp, encoding="utf-8") as fh:
    for raw in fh:
        line = raw.split(";")[0].strip()
        m = re.match(r"^\[(\w+)\]$", line)
        if m:
            cur = m.group(1).upper(); sections.setdefault(cur, []); continue
        if line and cur:
            sections[cur].append(line.split())
check("Archivo legible y con secciones", len(sections) > 0, sorted(sections))
for s in ["TITLE", "JUNCTIONS", "RESERVOIRS", "PIPES", "PUMPS", "VALVES", "CURVES", "OPTIONS", "COORDINATES", "END"]:
    check(f"Seccion [{s}] presente", s in sections)

opts = {r[0].upper(): " ".join(r[1:]) for r in sections.get("OPTIONS", []) if r}
check("Units = LPS", opts.get("UNITS", "").upper() == "LPS", opts.get("UNITS"))
check("Headloss definido", opts.get("HEADLOSS", "").upper() in ("H-W", "D-W", "C-M"), opts.get("HEADLOSS"))

junc = {r[0]: r for r in sections.get("JUNCTIONS", [])}
resv = {r[0]: r for r in sections.get("RESERVOIRS", [])}
tank = {r[0]: r for r in sections.get("TANKS", [])}
nodes = {**junc, **resv, **tank}
pipes = {r[0]: r for r in sections.get("PIPES", [])}
pumps = {r[0]: r for r in sections.get("PUMPS", [])}
valves = {r[0]: r for r in sections.get("VALVES", [])}
links = {**pipes, **pumps, **valves}
curves = {r[0] for r in sections.get("CURVES", [])}
coords = {r[0] for r in sections.get("COORDINATES", [])}

check("IDs de nodos unicos", len(nodes) == len(junc) + len(resv) + len(tank))
check("IDs de enlaces unicos", len(links) == len(pipes) + len(pumps) + len(valves))
orphans = [(l, n) for l, r in links.items() for n in (r[1], r[2]) if n not in nodes]
check("Todos los enlaces tienen nodos existentes", not orphans, orphans or "")
check("Ningun enlace une un nodo consigo mismo", all(r[1] != r[2] for r in links.values()))
used = {n for r in links.values() for n in (r[1], r[2])}
check("Sin nodos aislados", not (set(nodes) - used), sorted(set(nodes) - used) or "")
check("Existe fuente hidraulica (reservoir/tank)", len(resv) + len(tank) > 0, list(resv) + list(tank))
bad_len = [p for p, r in pipes.items() if float(r[3]) <= 0]
bad_d = [p for p, r in pipes.items() if float(r[4]) <= 0] + [v for v, r in valves.items() if float(r[3]) <= 0]
bad_rough = [p for p, r in pipes.items() if float(r[5]) <= 0]
check("Longitudes > 0", not bad_len, bad_len or "")
check("Diametros > 0", not bad_d, bad_d or "")
check("Rugosidad > 0 en todas las tuberias", not bad_rough, bad_rough or "")
for pid, r in pumps.items():
    check(f"Bomba {pid} conectada ({r[1]} -> {r[2]})", r[1] in nodes and r[2] in nodes)
    if "HEAD" in [x.upper() for x in r]:
        cid = r[[x.upper() for x in r].index("HEAD") + 1]
        check(f"Curva de bomba '{cid}' definida en [CURVES]", cid in curves)
        report["pump_curve"] = cid
status = {r[0]: r[1].upper() for r in sections.get("STATUS", [])}
for vid in set(valves) | ({"V1"} & set(links)):
    pipe_st = pipes[vid][7].upper() if vid in pipes and len(pipes[vid]) > 7 else None
    st = status.get(vid, pipe_st)
    check(f"Electrovalvula {vid} ({'Pipe ON/OFF' if vid in pipes else 'Valve'}) OPEN en riego activo", st == "OPEN", st)
missing_xy = sorted(set(nodes) - coords)
check("Coordenadas definidas para todos los nodos", not missing_xy, missing_xy or "")
xy = [tuple(r[1:3]) for r in sections.get("COORDINATES", [])]
check("Sin nodos superpuestos (coordenadas repetidas)", len(xy) == len(set(xy)))
qsum = sum(float(r[2]) for r in junc.values() if len(r) > 2)
report["demand_sum_Ls"] = qsum
check("Suma de demandas ~ 0.0266667 L/s", abs(qsum - 0.0266667) < 1e-6, f"{qsum:.8f} L/s = {qsum*60:.5f} L/min = {qsum*3600:.4f} L/h")

# ---------- 2. Conectividad (grafo) con WNTR ----------
import wntr, networkx as nx
wn = wntr.network.WaterNetworkModel(inp)
check("WNTR parsea el archivo", True, f"{wn.num_nodes} nodos, {wn.num_links} enlaces")
G = wn.to_graph().to_undirected()
check("Red conexa (un solo componente)", nx.number_connected_components(G) == 1)
src = list(wn.reservoir_name_list) + list(wn.tank_name_list)
unreach = [n for n in wn.junction_name_list if not any(nx.has_path(G, s, n) for s in src)]
check("Todos los junctions alcanzables desde la fuente", not unreach, unreach or "")


# ---------- 3. Simulacion con EPANET 2.2 (libreria del toolkit incluida en WNTR) ----------
def run_epanet(path):
    sim = wntr.sim.EpanetSimulator(wntr.network.WaterNetworkModel(path))
    prefix = os.path.join(tempfile.mkdtemp(), "run")
    return sim.run_sim(file_prefix=prefix, version=2.2), prefix


res, prefix = run_epanet(inp)
rpt = open(prefix + ".rpt", encoding="latin-1").read()
warn = [l.strip() for l in rpt.splitlines() if re.search(r"WARNING|Error", l, re.I)]
report["warnings"] += warn
check("Simulacion EPANET 2.2 ejecutada sin errores", not re.search(r"Error \d{3}", rpt), "; ".join(warn) or "sin advertencias")

n = {k: res.node[k].iloc[0] for k in ("head", "pressure", "demand")}
L = {k: res.link[k].iloc[0] for k in ("flowrate", "velocity", "headloss", "status")}
report["nodes"] = {i: {"head_m": n["head"][i], "pressure_m": n["pressure"][i], "demand_Ls": n["demand"][i] * 1000} for i in wn.node_name_list}
report["links"] = {}
for i in wn.link_name_list:
    lk = wn.get_link(i)
    hl = float(L["headloss"][i])
    if lk.link_type == "Pipe":
        hl_total = hl * lk.length          # WNTR entrega headloss de tuberias por unidad de longitud (m/m)
    else:
        hl_total = float(n["head"][lk.start_node_name] - n["head"][lk.end_node_name])
    report["links"][i] = {"type": lk.link_type, "flow_Ls": float(L["flowrate"][i]) * 1000,
                          "velocity_ms": float(L["velocity"][i]), "headloss_m": hl_total,
                          "status": {0: "CLOSED", 1: "OPEN", 2: "ACTIVE"}.get(int(L["status"][i]), str(L["status"][i]))}
for p in wn.pump_name_list:
    lk = wn.get_link(p)
    report["links"][p]["head_gain_m"] = float(n["head"][lk.end_node_name] - n["head"][lk.start_node_name])
Qp = report["links"][wn.pump_name_list[0]]["flow_Ls"]
check("Caudal de bomba = suma de demandas", abs(Qp - qsum) < 1e-8, f"{Qp:.9f} L/s")
serie = [i for i in ("PU1", "P-MAIN", "V1", "P-HEADER") if i in report["links"]]
dq = max(report["links"][i]["flow_Ls"] for i in serie) - min(report["links"][i]["flow_Ls"] for i in serie)
check("Continuidad en serie PU1-P-MAIN-V1-P-HEADER", dq < 1e-8, f"max dif = {dq:.2e} L/s")

# ---------- 4. Contraste con EPyT (OWA-EPANET toolkit) ----------
try:
    from epyt import epanet as ep
    d = ep(inp, display_msg=False, display_warnings=False)
    r2 = d.getComputedHydraulicTimeSeries()
    q2 = dict(zip(d.getLinkNameID(), r2.Flow[0]))
    report["epyt_version"] = str(d.getVersion())
    diff = max(abs(q2[i] - report["links"][i]["flow_Ls"]) for i in q2)
    check("EPyT/OWA-EPANET reproduce los caudales", diff < 1e-6, f"EPANET v{d.getVersion()}, max dif = {diff:.2e} L/s")
    d.unload()
except Exception as e:
    report["warnings"].append(f"EPyT no ejecutado: {e}")

print("\nNODOS:  ID | Head m | Pressure m | Demand L/s")
for i, v in report["nodes"].items():
    print(f"  {i:10s} {v['head_m']:9.4f} {v['pressure_m']:9.4f} {v['demand_Ls']:.8f}")
print("ENLACES: ID | tipo | Flow L/s | V m/s | hf m | status")
for i, v in report["links"].items():
    print(f"  {i:9s} {v['type']:5s} {v['flow_Ls']:.8f} {v['velocity_ms']:.4f} {v['headloss_m']:.6f} {v['status']}"
          + (f"  head gain={v['head_gain_m']:.3f} m" if 'head_gain_m' in v else ""))
report["ok"] = not report["errors"]
print("\nESTADO FINAL:", "OK" if report["ok"] else f"{len(report['errors'])} ERRORES")
if out_json:
    json.dump(report, open(out_json, "w", encoding="utf-8"), indent=1, default=float)
