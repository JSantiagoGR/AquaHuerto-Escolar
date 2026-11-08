"""Validacion automatica del modelo EPANET v3 (cruz + 3 laterales de manguera + 9 aspersores).

Uso (desde la carpeta 3):
    uv run --python 3.12 --with wntr --with epyt --with matplotlib python validar_modelo.py [archivo.inp] [--json salida.json]
"""
import sys, os, re, json, csv, math, shutil, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generar_modelo as G

INP = os.path.join(HERE, sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.path.join(HERE, "riego_huerto_v3_final.inp")
OUTJ = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
C = G.CONFIG
R = {"archivo": INP, "checks": [], "fallos": [], "avisos": []}


def chk(n, ok, det="", aviso=False):
    e = "OK" if ok else ("AVISO" if aviso else "FALLA")
    R["checks"].append({"check": n, "estado": e, "detalle": str(det)})
    print(f"[{e:5s}] {n}" + (f"  -> {det}" if det != "" else ""))
    if not ok:
        (R["avisos"] if aviso else R["fallos"]).append(f"{n}: {det}")


# ---------- 1. texto ----------
sec, cur = {}, None
for raw in open(INP, encoding="utf-8"):
    line = raw.split(";")[0].strip(); m = re.match(r"^\[(\w+)\]$", line)
    if m: cur = m.group(1).upper(); sec.setdefault(cur, []); continue
    if line and cur: sec[cur].append(line.split())
for s in ["TITLE", "JUNCTIONS", "RESERVOIRS", "PIPES", "PUMPS", "CURVES", "OPTIONS", "COORDINATES", "STATUS", "END"]:
    chk(f"Seccion [{s}]", s in sec)
opts = {r[0].upper(): " ".join(r[1:]) for r in sec["OPTIONS"]}
chk("Unidades LPS", opts.get("UNITS", "").upper() == "LPS", opts.get("UNITS"))
chk("Darcy-Weisbach", opts.get("HEADLOSS", "").upper() == "D-W")
J = {r[0]: r for r in sec["JUNCTIONS"]}; P = {r[0]: r for r in sec["PIPES"]}; PU = {r[0]: r for r in sec["PUMPS"]}
RS = {r[0]: r for r in sec["RESERVOIRS"]}; nodes = {**J, **RS}; links = {**P, **PU}
chk("Enlaces con nodos existentes", all(r[1] in nodes and r[2] in nodes for r in links.values()))
chk("Sin nodos aislados", not (set(nodes) - {n for r in links.values() for n in (r[1], r[2])}))
chk("Coordenadas completas", not (set(nodes) - {r[0] for r in sec["COORDINATES"]}))
chk("Sin filtro en el modelo", not any("FILTR" in (l.upper()) for l in P), "")

# ---------- 2. topologia ----------
asp = sorted(n for n in J if re.fullmatch(r"A\d\d", n))
lat = sorted({n[1] for n in asp})
chk("Exactamente 3 laterales", lat == ["1", "2", "3"], lat)
chk("Exactamente 9 aspersores individuales", len(asp) == 9, asp)
chk("3 aspersores por lateral", all(sum(1 for a in asp if a[1] == l) == 3 for l in lat))
dem = {a: float(J[a][2]) for a in asp}
chk("Demanda solo en los 9 aspersores", all(float(r[2]) == 0 for k, r in J.items() if k not in asp))
chk("Sin demanda equivalente unica", len(asp) == 9 and all(v > 0 for v in dem.values()))
cruz = [l for l, r in links.items() if "J-X" in (r[1], r[2])]
chk("Cruz J-X con 4 conexiones (1 entrada + 3 salidas)", len(cruz) == 4 and sum(1 for l in cruz if links[l][2] == "J-X") == 1, cruz)
chk("Check CHK con status CV y sentido tinaco->bomba", P["CHK"][7].upper() == "CV" and P["CHK"][1] == "J-BOL")
st = {r[0]: r[1].upper() for r in sec["STATUS"]}
chk("Electrovalvula EV OPEN", st.get("EV") == "OPEN")
chk("Valvula de bola existente OPEN", st.get("BOLA") == "OPEN")
orden = ["P-TK", "BOLA", "CHK", "EX-TB", "EX-BAJ", "N-A", "AD-IN", "PU1", "AD-OUT", "N-B", "YF", "N-C", "EV", "N-D", "N-E", "N-H"]
chk("Cadena TINACO-BOLA-CHECK-T-BAJADA-BOMBA-YF-EV-PRINCIPAL-SUBIDA-CRUZ en orden",
    all(links[orden[i]][2] == links[orden[i + 1]][1] for i in range(len(orden) - 1)))

# ---------- 3. geometria ----------
tub = [l for l in P if l.startswith(("N-", "XO", "EX-"))]
chk("Tuboplus DI 14.40 mm", all(abs(float(P[l][4]) - 14.40) < 1e-6 for l in tub))
hose = [l for l in P if l.startswith(("HL", "HT"))]
chk("Manguera de laterales con DI de CONFIG (NO MEDIDO)", all(abs(float(P[l][4]) - G.M["M9_manguera_DI_mm"]) < 1e-6 for l in hose),
    f"{G.M['M9_manguera_DI_mm']} mm (NO MEDIDO)")
chk("Longitudes y diametros > 0", all(float(r[3]) > 0 and float(r[4]) > 0 for r in P.values()))
z = {k: float(r[1]) for k, r in J.items()}
chk("Cruz y laterales a z = 0.12 + 0.40 + 1.00 = 1.52 m", abs(z["J-X"] - 1.52) < 1e-9 and all(abs(z[a] - 1.52) < 1e-9 for a in asp))
chk("Bomba a z 0.08 m y salida del tinaco a 0.265 m", abs(z["J-PIN"] - 0.08) < 1e-9 and abs(z["J-TK"] - 0.265) < 1e-9)
chk("Nivel de agua del tinaco 1.19 m (PROVISIONAL)", abs(float(RS["R1"][1]) - 1.19) < 1e-9)
cortes = list(csv.reader(open(os.path.join(HERE, "tabla_cortes_tuboplus.csv"), encoding="utf-8")))
tot = {r[2].split()[-1]: float(r[8]) for r in cortes if r and r[0] == "TOTAL"}
gp = C["geometria_principal"]; nuevo = tot[gp]
chk("Geometria principal = A (subida VERTICAL, DISENO DESEADO)", gp == "A" and C["geometrias"]["A"]["subida"] == "vertical")
chk("Subida vertical en el modelo: N-E de longitud = desnivel (z 0.08 -> 1.52)", abs(float(P["N-E"][3]) - (1.52 - 0.08)) < 1e-6,
    f"{float(P['N-E'][3]):.3f} m")
chk("Escenario A usa 5 codos de 90 deg nuevos (bajada, subida x2, brazos x2)", G.GEOS["A"]["codos"] == {"codo90": 5, "codo45": 0})
chk("Escenario B (45 deg) calculado solo como alternativa", "B" in tot and C["geometrias"]["B"]["rol"].startswith("ALTERNATIVA"))
chk("Tabla de Tuboplus = geometria del generador", abs(nuevo - G.GEO["nuevo_m"]) < 1e-6 and abs(tot["B"] - G.GEOS["B"]["nuevo_m"]) < 1e-6)
estado = G.GEO["estado_total"]
chk("Tuboplus NUEVO del diseno principal <= 4.00 m", nuevo <= C["tubo"]["limite_nuevo_m"],
    f"{nuevo:.3f} m ({estado}); margen {C['tubo']['limite_nuevo_m'] - nuevo:.3f} m; para cumplir M1+M5 <= {G.GEO['M1_M5_max_m']:.3f} m "
    "-> NO se puede confirmar hasta medir en sitio", aviso=(estado != "MEDIDO"))
chk("Mediciones fisicas pendientes listadas (mediciones_fisicas.csv)", os.path.exists(os.path.join(HERE, "mediciones_fisicas.csv")) and
    sum(1 for _ in open(os.path.join(HERE, "mediciones_fisicas.csv"), encoding="utf-8")) >= 13)

# ---------- 4. simulacion ----------
ok22, msgs = G.runepanet(INP)
chk("EPANET 2.2 runepanet.exe sin errores", bool(ok22), "ran successfully" if ok22 else msgs)
chk("Sin WARNINGS de EPANET 2.2", not msgs, msgs or "")
import wntr, networkx as nx
tmp = os.path.join(tempfile.mkdtemp(), "m.inp"); shutil.copy(INP, tmp)
wn = wntr.network.WaterNetworkModel(tmp)
chk("WNTR parsea", True, f"{wn.num_nodes} nodos, {wn.num_links} enlaces")
chk("Red conexa", nx.number_connected_components(wn.to_graph().to_undirected()) == 1)
r22 = wntr.sim.EpanetSimulator(wn).run_sim(file_prefix=os.path.join(tempfile.mkdtemp(), "w"), version=2.2)
r = G.simular(INP); N, L = r["nodes"], r["links"]
dq = max(abs(r22.link["flowrate"].iloc[0][l] * 1000 - L[l]["Q"]) for l in L)
chk("EPANET 2.2 (WNTR) = OWA-EPANET (EPyT)", dq < 1e-5, f"max dif {dq:.2e} L/s")

# ---------- 5. masa y continuidad ----------
qa = {a: N[a]["D"] for a in asp}; qR = -N["R1"]["D"]
chk("Masa: salida del tinaco = suma de 9 aspersores", abs(qR - sum(qa.values())) < 1e-6, f"{qR:.6f} L/s")
serie = ["P-TK", "BOLA", "CHK", "EX-TB", "EX-BAJ", "N-A", "AD-IN", "PU1", "AD-OUT", "N-B", "YF", "N-C", "EV", "N-D", "N-E", "N-H"]
chk("Continuidad en serie", max(L[l]["Q"] for l in serie) - min(L[l]["Q"] for l in serie) < 1e-6)
chk("Cruz: entrada = suma de 3 salidas", abs(L["N-H"]["Q"] - sum(L[f"XO{i}"]["Q"] for i in (1, 2, 3))) < 1e-6)
for i in (1, 2, 3):
    chk(f"Lateral {i} = suma de sus 3 aspersores", abs(L[f"XO{i}"]["Q"] - sum(qa[f"A{i}{j}"] for j in (1, 2, 3))) < 1e-6,
        f"{L[f'XO{i}']['Q']:.5f} L/s")
chk("Tapones sin flujo", all(abs(L[f"HT{i}"]["Q"]) < 1e-9 for i in (1, 2, 3)))
chk("Check y electrovalvula con flujo positivo", L["CHK"]["Q"] > 0 and L["EV"]["Q"] > 0)

# ---------- 6. caudales, presiones, velocidades ----------
Qt = L["N-D"]["Q"]; qn = C["aspersor"]["Q_nominal_Lh"]
chk("Caudal total = 9 x caudal por aspersor", abs(Qt - 9 * qn / 3600) < 1e-6, f"{Qt:.5f} L/s = {Qt * 60:.3f} L/min")
chk("Caudal por lateral = 3 x aspersor", all(abs(L[f"XO{i}"]["Q"] - 3 * qn / 3600) < 1e-6 for i in (1, 2, 3)))
chk("YF-S201 dentro de 1-30 L/min", 1 <= Qt * 60 <= 30, f"{Qt * 60:.2f} L/min -> {7.5 * Qt * 60:.1f} Hz")
chk("Caudal por debajo de 6 L/min (maximo anunciado de la bomba)", Qt * 60 < C["bomba_Qmax_Lmin"], f"margen {(1 - Qt * 60 / 6) * 100:.0f} %")
Pa = [N[a]["P"] for a in asp]
chk("Presion positiva en los 9 aspersores", min(Pa) > 0, ", ".join(f"{p:.2f}" for p in Pa) + " m")
chk("Uniformidad HIDRAULICA de presion Pmin/Pmax >= 0.95 (NO es uniformidad de riego)", min(Pa) / max(Pa) >= 0.95, f"{min(Pa) / max(Pa):.4f}")
chk("Uniformidad de RIEGO", False, "PENDIENTE DE VALIDACION EXPERIMENTAL (patron de mojado, radio, presion minima y apertura-caudal desconocidos)", aviso=True)
chk("Succion de la bomba con presion positiva", N["J-PIN"]["P"] > 0, f"{N['J-PIN']['P']:.3f} m")
vt = max(abs(L[l]["V"]) for l in L if l.startswith(("N-", "XO")))
chk("Velocidad en Tuboplus < 1.5 m/s", vt < 1.5, f"max {vt:.3f} m/s; principal {L['N-D']['V']:.3f} m/s")
chk("Velocidad en manguera < 1.5 m/s", max(abs(L[l]["V"]) for l in L if l.startswith("HL")) < 1.5)
Hb = N["J-POUT"]["H"] - N["J-PIN"]["H"]
chk("Bomba opera por debajo del corte del presostato (0.9 MPa)", Hb < 0.9e6 / (C["rho"] * C["g"]),
    f"altura {Hb:.2f} m vs corte 91.9 m (curva PROVISIONAL)")
chk("Requisito de presion del aspersor real", False, "DESCONOCIDO; presion = PRELIMINAR DEPENDIENTE DE CURVA PROVISIONAL DE BOMBA", aviso=True)

# ---------- 7. perdidas y calculo manual ----------
rows = G.calculos(r, G.red()[1])
hf = sum(x["hf"] for x in rows); hm = sum(x["hm"] for x in rows)
R["perdidas"] = {"distribuida_m": hf, "menores_m": hm}
chk("Perdidas distribuidas y menores calculadas", hf > 0 and hm > 0, f"distribuida {hf:.4f} m, menores {hm:.4f} m")
e1 = max((abs(x["ht"] - x["epanet"]) / x["epanet"], x["id"]) for x in rows if x["Q"] > 0 and not x["reg"].startswith("transicion"))
chk("Manual D-W vs EPANET (laminar/turbulento) < 2 %", e1[0] < 0.02, f"max {e1[0] * 100:.2f} % en {e1[1]}")
e2 = max(abs(x["ht"] - x["epanet"]) for x in rows if x["reg"].startswith("transicion"))
chk("Tramos en transicion: diferencia absoluta manual vs EPANET < 5 mm", e2 < 0.005, f"max {e2 * 1000:.2f} mm (EPANET interpola Moody)")
path = ["P-TK", "BOLA", "CHK", "EX-TB", "EX-BAJ", "N-A", "AD-IN", "AD-OUT", "N-B", "YF", "N-C", "EV", "N-D", "N-E", "N-H", "XO1", "ESP1", "HL11", "RA11"]
bal = C["tinaco"]["z_agua_max"] + Hb - sum(L[l]["hl"] for l in path) - N["A11"]["H"]
chk("Balance de energia tinaco -> A11", abs(bal) < 1e-3, f"residuo {bal:.2e} m")

# ---------- 8. escenarios ----------
esc = list(csv.DictReader(open(os.path.join(HERE, "escenarios_sensibilidad.csv"), encoding="utf-8")))
ids = {e["escenario"] for e in esc}
chk("Escenarios de caudal 20/25/30/35/40/70 L/h presentes", {"Q20", "Q25", "Q30", "Q35", "Q40", "Q70"} <= ids)
chk("Sensibilidad de manguera con 3 diametros", sum(1 for e in esc if e["escenario"].startswith("DH")) >= 3)
q70 = next(e for e in esc if e["escenario"] == "Q70")
chk("70 L/h x 9 detectado como NO viable", q70["viable_hidraulicamente"] == "NO", q70["mensajes_epanet"][:120])
chk("Escenarios geometricos A2/B/B2 simulados", {"GEO_A2", "GEO_B", "GEO_B2"} <= ids)

# ---------- 9. presentacion ----------
if os.path.basename(INP) == "riego_huerto_v3_final.inp":
    pres = os.path.join(HERE, "riego_huerto_v3_presentacion.inp")
    strip = lambda t: re.sub(r"\[(TITLE|COORDINATES|VERTICES|LABELS|BACKDROP)\]\n.*?\n\n(?=\[)", "", t, flags=re.S)
    chk("Presentacion con hidraulica identica", strip(open(INP, encoding="utf-8").read()) == strip(open(pres, encoding="utf-8").read()))
    rp = G.simular(pres)
    d = max(abs(rp["links"][l]["Q"] - L[l]["Q"]) for l in L) + max(abs(rp["nodes"][n]["P"] - N[n]["P"]) for n in N)
    chk("Presentacion con resultados identicos", d == 0, f"dif {d:.1e}")

R["resultados"] = {"Q_total_Ls": Qt, "P_asp_m": dict(zip(asp, Pa)), "H_bomba": Hb, "V_principal": L["N-D"]["V"], "tuboplus_nuevo_m": nuevo}
R["ok"] = not R["fallos"]
print(f"\nRESULTADO: {sum(1 for c in R['checks'] if c['estado'] == 'OK')} OK, {len(R['avisos'])} AVISOS, {len(R['fallos'])} FALLAS")
print("ESTADO FINAL:", "OK" if R["ok"] else "CON FALLAS")
if OUTJ:
    json.dump(R, open(OUTJ, "w", encoding="utf-8"), indent=1, default=float)
sys.exit(0 if R["ok"] else 1)
