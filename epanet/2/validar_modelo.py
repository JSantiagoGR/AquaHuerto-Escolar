"""Validacion automatica del modelo EPANET v2 (riego, 2 laterales, 4 microaspersores).

Uso (desde la carpeta 2):
    uv run --python 3.12 --with wntr --with epyt --with matplotlib python validar_modelo.py
Opcional: python validar_modelo.py <archivo.inp> [--json salida.json]

Comprueba formato, simulacion (EPANET 2.2 runepanet.exe, WNTR/EPANET 2.2, EPyT/OWA-EPANET),
continuidad, topologia, check, electrovalvula, diametros, longitudes, elevaciones, caudales,
velocidades, presiones, perdidas, limite de Tuboplus y concordancia con el calculo manual.
"""
import sys, os, re, json, csv, math, shutil, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generar_modelo as G  # CONFIG, red, calculos

INP = os.path.join(HERE, sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.path.join(HERE, "riego_huerto_v2_final.inp")
OUTJ = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
RUNEPANET = r"C:\Program Files (x86)\EPANET 2.2\runepanet.exe"
C = G.CONFIG
R = {"archivo": INP, "checks": [], "fallos": [], "advertencias": []}


def chk(nombre, ok, detalle="", aviso=False):
    est = "OK" if ok else ("AVISO" if aviso else "FALLA")
    R["checks"].append({"check": nombre, "estado": est, "detalle": str(detalle)})
    print(f"[{est:5s}] {nombre}" + (f"  -> {detalle}" if detalle != "" else ""))
    if not ok:
        (R["advertencias"] if aviso else R["fallos"]).append(f"{nombre}: {detalle}")


def ascii_copy(path):
    t = os.path.join(tempfile.mkdtemp(), "m.inp"); shutil.copy(path, t); return t


# ---------------- 1. parseo de texto ----------------
sec, cur = {}, None
for raw in open(INP, encoding="utf-8"):
    line = raw.split(";")[0].strip()
    m = re.match(r"^\[(\w+)\]$", line)
    if m:
        cur = m.group(1).upper(); sec.setdefault(cur, []); continue
    if line and cur:
        sec[cur].append(line.split())
for s in ["TITLE", "JUNCTIONS", "RESERVOIRS", "PIPES", "PUMPS", "CURVES", "EMITTERS", "OPTIONS", "COORDINATES", "STATUS", "END"]:
    chk(f"Seccion [{s}]", s in sec)
opts = {r[0].upper(): " ".join(r[1:]) for r in sec["OPTIONS"]}
chk("Unidades LPS", opts.get("UNITS", "").upper() == "LPS", opts.get("UNITS"))
chk("Formula de perdidas Darcy-Weisbach (referencia principal)", opts.get("HEADLOSS", "").upper() == "D-W", opts.get("HEADLOSS"))
J = {r[0]: r for r in sec["JUNCTIONS"]}; RS = {r[0]: r for r in sec["RESERVOIRS"]}
P = {r[0]: r for r in sec["PIPES"]}; PU = {r[0]: r for r in sec["PUMPS"]}
EMI = {r[0]: float(r[1]) for r in sec.get("EMITTERS", [])}
nodes = {**J, **RS}; links = {**P, **PU}
orf = [(l, n) for l, r in links.items() for n in (r[1], r[2]) if n not in nodes]
chk("Enlaces con nodos existentes", not orf, orf or "")
usados = {n for r in links.values() for n in (r[1], r[2])}
chk("Sin nodos aislados", not (set(nodes) - usados), sorted(set(nodes) - usados) or "")
chk("Coordenadas para todos los nodos", not (set(nodes) - {r[0] for r in sec["COORDINATES"]}))
chk("Fuente hidraulica R1 (tinaco) presente", "R1" in RS, RS.get("R1"))

# ---------------- 2. topologia ----------------
lat = sorted({re.match(r"(L\d)-", l).group(1) for l in P if re.match(r"L\d-", l)})
chk("Exactamente 2 laterales", lat == ["L1", "L2"], lat)
chk("Exactamente 4 emisores en [EMITTERS]", sorted(EMI) == ["E1", "E2", "E3", "E4"], sorted(EMI))
dem_em = {e: float(J[e][2]) for e in ("E1", "E2", "E3", "E4")}
chk("Aspersores modelados individualmente como EMITTERS (sin demanda equivalente)", all(v == 0 for v in dem_em.values()) and len(set(EMI.values())) == 1, dem_em)
chk("Ningun otro nodo con demanda", all(float(r[2]) == 0 for k, r in J.items()))
chk("Bomba PU1 entre J-PIN y J-POUT", PU.get("PU1", [None, ""])[1:3] == ["J-PIN", "J-POUT"])
chk("Check CHK con Status CV", P["CHK"][7].upper() == "CV", P["CHK"][7])
chk("Sentido del check: tinaco -> bomba (Node1=J-TK aguas arriba de la bomba)", P["CHK"][1] == "J-TK" and P["CHK"][2] == "J-CHK" and P["P-TK"][1] == "R1")
st = {r[0]: r[1].upper() for r in sec["STATUS"]}
chk("Electrovalvula EV abierta (riego)", st.get("EV") == "OPEN" and P["EV"][7].upper() == "OPEN")
orden = ["P-TK", "CHK", "T-A", "T-B", "T-C", "PU1", "T-D", "YF", "T-E", "EV", "T-F", "T-G", "T-H"]
cadena = all(links[orden[i]][2] == links[orden[i + 1]][1] for i in range(len(orden) - 1))
chk("Cadena TINACO-CHECK-BOMBA-YF-S201-ELECTROVALVULA-PRINCIPAL-SUBIDA-T en orden", cadena)
chk("T distribuye a 2 brazos", P["BR-L"][1] == "J-T" and P["BR-R"][1] == "J-T")

# ---------------- 3. geometria ----------------
tub = [l for l, r in P.items() if l.startswith(("T-", "BR-", "L1-", "L2-"))]
chk("Diametro interior Tuboplus 14.40 mm (no 12.7)", all(abs(float(P[l][4]) - 14.40) < 1e-6 for l in tub))
chk("YF-S201 con D interior 11 mm", abs(float(P["YF"][4]) - 11.0) < 1e-6)
chk("Longitudes > 0", all(float(r[3]) > 0 for r in P.values()))
chk("Diametros > 0", all(float(r[4]) > 0 for r in P.values()))
chk("Rugosidad Tuboplus 0.007 mm", all(abs(float(P[l][5]) - 0.007) < 1e-9 for l in tub))
z = {k: float(r[1]) for k, r in J.items()}
chk("Elevaciones: bomba +0.08, salida tinaco +0.265, laterales +0.53, boquillas +0.56",
    abs(z["J-PIN"] - C["z_bomba"]) < 1e-6 and abs(z["J-TK"] - C["tinaco"]["z_salida"]) < 1e-6 and
    abs(z["T-E1"] - C["z_lateral"]) < 1e-6 and abs(z["E1"] - C["z_boquilla"]) < 1e-6, z)
chk("Nivel de agua del tinaco = 1.19 m (PROVISIONAL)", abs(float(RS["R1"][1]) - C["tinaco"]["z_agua_max"]) < 1e-6, RS["R1"][1])
dz = C["tinaco"]["z_agua_max"] - C["z_riego"]
chk("Desnivel agua -> nivel de riego = 0.67 m", abs(dz - 0.67) < 1e-9, f"{dz:.3f} m")
cortes = list(csv.reader(open(os.path.join(HERE, "tabla_cortes_tuboplus.csv"), encoding="utf-8")))
tot = float(next(r for r in cortes if r and r[0] == "TOTAL")[4])
chk("Tuboplus utilizado <= 8.00 m", tot <= 8.0, f"{tot:.3f} m")
chk("Tuboplus utilizado <= 7.50 m (objetivo con margen)", tot <= 7.5, f"{tot:.3f} m (margen {8 - tot:.3f} m)")
LKsum = sum(float(P[l][3]) for l in tub)
chk("Cortes vs. longitudes EPANET coherentes (cortes < c-c por las tomas de conexiones)", tot < LKsum, f"cortes {tot:.3f} m < c-c {LKsum:.3f} m")

# ---------------- 4. simulaciones ----------------
rep = os.path.join(tempfile.mkdtemp(), "r")
a = ascii_copy(INP)
p = subprocess.run([RUNEPANET, a, rep + ".rpt", rep + ".out"], capture_output=True, text=True)
rpt = open(rep + ".rpt", encoding="latin-1").read()
ok22 = "ran successfully" in p.stdout and not re.search(r"Error \d+", rpt)
chk("EPANET 2.2 (runepanet.exe) ejecuta sin errores", ok22, p.stdout.strip().splitlines()[-1] if p.stdout else rpt[:200])
warn = [l.strip() for l in rpt.splitlines() if "WARNING" in l.upper()]
chk("Sin WARNINGS de EPANET 2.2", not warn, "; ".join(warn), aviso=True)
import wntr, networkx as nx
wn = wntr.network.WaterNetworkModel(a)
chk("WNTR parsea el archivo", True, f"{wn.num_nodes} nodos, {wn.num_links} enlaces")
chk("Red conexa", nx.number_connected_components(wn.to_graph().to_undirected()) == 1)
res22 = wntr.sim.EpanetSimulator(wn).run_sim(file_prefix=os.path.join(tempfile.mkdtemp(), "w"), version=2.2)
r = G.simular(INP)   # EPyT / OWA-EPANET (doble precision)
q22 = res22.link["flowrate"].iloc[0] * 1000
dq = max(abs(q22[l] - r["links"][l]["Q"]) for l in r["links"])
chk("EPANET 2.2 (WNTR) y OWA-EPANET (EPyT) coinciden en caudales", dq < 1e-5, f"version EPyT {r['version']}, max dif {dq:.2e} L/s")
N, L = r["nodes"], r["links"]

# ---------------- 5. continuidad / masa ----------------
qem = {e: L["RE" + e[1]]["Q"] for e in ("E1", "E2", "E3", "E4")}
qR = -N["R1"]["D"]; qsum = sum(qem.values()); qdem = sum(N[e]["D"] for e in qem)
chk("Masa: salida del tinaco = suma de 4 emisores", abs(qR - qsum) < 1e-6, f"{qR:.6f} vs {qsum:.6f} L/s")
chk("Masa: flujo de rama = flujo del emisor en cada nodo", abs(qsum - qdem) < 1e-6)
serie = ["P-TK", "CHK", "T-A", "T-B", "T-C", "PU1", "T-D", "YF", "T-E", "EV", "T-F", "T-G", "T-H"]
ds = max(L[l]["Q"] for l in serie) - min(L[l]["Q"] for l in serie)
chk("Continuidad en la cadena en serie", ds < 1e-6, f"max dif {ds:.2e} L/s")
chk("Continuidad en la T: T-H = BR-L + BR-R", abs(L["T-H"]["Q"] - L["BR-L"]["Q"] - L["BR-R"]["Q"]) < 1e-6)
chk("Lateral 1 = E1 + E2 ; Lateral 2 = E3 + E4", abs(L["BR-L"]["Q"] - qem["E1"] - qem["E2"]) < 1e-6 and abs(L["BR-R"]["Q"] - qem["E3"] - qem["E4"]) < 1e-6,
    f"L1 {L['BR-L']['Q']:.5f} L/s, L2 {L['BR-R']['Q']:.5f} L/s")
chk("Tapones sin flujo", abs(L["L1-T"]["Q"]) < 1e-8 and abs(L["L2-T"]["Q"]) < 1e-8)
chk("Check con flujo positivo (abierto, tinaco->bomba)", L["CHK"]["Q"] > 0 and L["CHK"]["st"] == 1, f"{L['CHK']['Q']:.5f} L/s")
chk("Electrovalvula con flujo (abierta)", L["EV"]["Q"] > 0 and L["EV"]["st"] == 1)

# ---------------- 6. caudales, velocidades, presiones ----------------
Qt = L["T-F"]["Q"]
chk("Caudal total dentro del rango util del YF-S201 (1-30 L/min)", 1 <= Qt * 60 <= 30, f"{Qt:.5f} L/s = {Qt * 60:.3f} L/min -> {7.5 * Qt * 60:.1f} Hz")
chk("Reparto equitativo entre laterales (<2 %)", abs(L["BR-L"]["Q"] - L["BR-R"]["Q"]) / Qt < 0.02)
qe = list(qem.values())
chk("Uniformidad entre emisores (<1 %)", (max(qe) - min(qe)) / max(qe) < 0.01, ", ".join(f"{v * 3600:.2f}" for v in qe) + " L/h")
vmax = max(abs(L[l]["V"]) for l in tub)
chk("Velocidad en Tuboplus < 1.5 m/s", vmax < 1.5, f"max {vmax:.3f} m/s; principal {L['T-F']['V']:.3f} m/s")
chk("Presion positiva en la succion de la bomba", N["J-PIN"]["P"] > 0, f"{N['J-PIN']['P']:.3f} m")
chk("Sin presiones negativas", min(v["P"] for k, v in N.items() if k != "R1") >= 0)
bar = lambda m: m * C["rho"] * C["g"] / 1e5
pe = [bar(N[e]["P"]) for e in qem]
lo, hi = C["aspersor"]["rango_bar"]
chk(f"Presion de emisores dentro del rango Hunter {lo}-{hi} bar", all(lo <= x <= hi for x in pe), ", ".join(f"{x:.2f}" for x in pe) + " bar")
chk("Presion de emisores dentro de la tabla oficial Hunter (1.0-2.0 bar: 40/50/60 L/h)", all(1.0 <= x <= 2.0 for x in pe),
    f"{max(pe):.2f} bar > 2.0 bar: el caudal {max(qe) * 3600:.1f} L/h es una EXTRAPOLACION DEL MODELO (Q=C*P^n), "
    "NO un dato oficial de Hunter; depende de la curva PROVISIONAL de bomba", aviso=True)
# ---------------- cobertura geometrica (analisis, no cambia la red) ----------------
cv = G.cobertura(C["cobertura"]["radio_deseado_m"]); co = G.cobertura(C["cobertura"]["radio_objetivo_m"])
chk("Distancia maxima al aspersor mas cercano = 0.354 m (centro, esquinas y puntos medios de bordes)",
    abs(cv["dmax"] - math.hypot(0.25, 0.25)) < 1e-6, f"{cv['dmax']:.4f} m en {len(cv['puntos_dmax'])} puntos")
chk(f"Cobertura con radio {cv['r']:.2f} m completa", cv["cubierto"] >= 0.9999,
    f"{cv['cubierto'] * 100:.1f} % del cajon; sin cubrir centro, 4 esquinas y 4 puntos medios de borde", aviso=True)
chk(f"Escenario de cobertura radio {co['r']:.2f} m cubre 100 %", co["cubierto"] >= 0.9999, f"{co['cubierto'] * 100:.1f} %")
pr = G.presion_para_radio(C["cobertura"]["radio_objetivo_m"])
chk("Presion para radio objetivo dentro de la tabla oficial (interpolacion, no extrapolacion)", pr["dentro_tabla"],
    f"{pr['P_bar']:.2f} bar, ~{pr['Q_tabla_Lh']:.0f} L/h (interpolado de la tabla Hunter; CALCULADO, no dato del fabricante)")

# ---------------- 7. perdidas y calculo manual ----------------
rows = G.calculos_por_tramo(r)
hf = sum(x["hf"] for x in rows); hm = sum(x["hm"] for x in rows)
R["perdidas"] = {"distribuida_m": hf, "menores_m": hm}
chk("Perdidas: distribuida y menores calculadas", hf > 0 and hm > 0, f"distribuida {hf:.4f} m, menores {hm:.4f} m")
mx = 0; mxl = ""
for x in rows:
    if x["Q"] > 0 and not x["reg"].startswith("transicion"):
        e = abs(x["ht"] - x["epanet"]) / x["epanet"]
        if e > mx: mx, mxl = e, x["id"]
chk("Calculo manual D-W vs EPANET (tramos laminares/turbulentos) < 2 %", mx < 0.02, f"max {mx * 100:.2f} % en {mxl}")
tr = [x for x in rows if x["reg"].startswith("transicion")]
et = max((abs(x["ht"] - x["epanet"]) / x["epanet"] for x in tr), default=0)
chk("Tramos en transicion: diferencia manual (Colebrook) vs EPANET (interpolacion) < 10 %", et < 0.10, f"max {et * 100:.1f} %")
# Tuboplus Tabla 11 (OFICIAL): Q = 0.05 L/s, DN20 -> j = 0.013 mca/m, v = 0.31 m/s
Q = 0.05e-3; D = C["tubo"]["di_mm"] / 1000; V = Q / (math.pi * D**2 / 4); Re = V * D / 1.02e-6
f, _ = G.f_dw(Re, D, C["tubo"]["rug_mm"] / 1000); j = f / D * V**2 / 19.62
chk("Contraste con Tabla 11 oficial Tuboplus (0.05 L/s: j=0.013 m/m, v=0.31 m/s)", abs(j - 0.013) / 0.013 < 0.08 and abs(V - 0.31) < 0.01, f"j={j:.4f} m/m, v={V:.3f} m/s")
Hb = N["J-POUT"]["H"] - N["J-PIN"]["H"]
bal = C["tinaco"]["z_agua_max"] + Hb - sum(abs(L[l]["hl"]) for l in L if l not in ("PU1",) and abs(L[l]["Q"]) > 0 and l in serie + ["BR-L", "L1-A", "RE1"]) - N["E1"]["H"]
chk("Balance de energia tinaco -> E1 (Bernoulli) cierra", abs(bal) < 1e-3, f"residuo {bal:.2e} m")

# ---------------- 8. presentacion = final ----------------
if os.path.basename(INP) == "riego_huerto_v2_final.inp":
    pres = os.path.join(HERE, "riego_huerto_v2_presentacion.inp")
    strip = lambda t: re.sub(r"\[(TITLE|COORDINATES|VERTICES|LABELS|BACKDROP)\]\n.*?\n\n(?=\[)", "", t, flags=re.S)
    same = strip(open(INP, encoding="utf-8").read()) == strip(open(pres, encoding="utf-8").read())
    chk("Presentacion: secciones hidraulicas identicas al final", same)
    rp = G.simular(pres)
    d = max(abs(rp["links"][l]["Q"] - L[l]["Q"]) for l in L) + max(abs(rp["nodes"][n]["P"] - N[n]["P"]) for n in N)
    chk("Presentacion: resultados identicos al final", d == 0, f"dif {d:.2e}")

R["resultados"] = {"Q_total_Ls": Qt, "Q_L1_Ls": L["BR-L"]["Q"], "Q_L2_Ls": L["BR-R"]["Q"],
                   "Q_emisores_Lh": {e: v * 3600 for e, v in qem.items()}, "P_emisores_m": {e: N[e]["P"] for e in qem},
                   "P_emisores_bar": dict(zip(qem, pe)), "V_principal": L["T-F"]["V"], "H_bomba": Hb, "tuboplus_m": tot}
R["ok"] = not R["fallos"]
print(f"\nRESULTADO: {len([c for c in R['checks'] if c['estado'] == 'OK'])} OK, {len(R['advertencias'])} AVISOS, {len(R['fallos'])} FALLAS")
print("ESTADO FINAL:", "OK" if R["ok"] else "CON FALLAS")
if OUTJ:
    json.dump(R, open(OUTJ, "w", encoding="utf-8"), indent=1, default=float)
sys.exit(0 if R["ok"] else 1)
