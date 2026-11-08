"""Figuras y datos del reporte v3. Lee resultados_calculo.json (generado por generar_modelo.py).
Uso (desde la carpeta 3):  python reporte/generar_figuras.py
Al actualizar mediciones: correr generar_modelo.py, luego este script y luego generar_reporte.js."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
FIG = os.path.join(AQUI, "figuras")
os.makedirs(FIG, exist_ok=True)
R = json.load(open(os.path.join(RAIZ, "resultados_calculo.json"), encoding="utf8"))
B, G, ESC, RES = R["base"], R["GEOS"]["A"], R["esc"], R["resumen_base"]
plt.rcParams.update({"font.family": "Arial", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
AZUL, VERDE, GRIS, ROJO, NAR = "#1f5fa8", "#2e8b57", "#6b6b6b", "#c0392b", "#d68910"


def guardar(nombre):
    plt.savefig(os.path.join(FIG, nombre), dpi=200, bbox_inches="tight")
    plt.close()


# 1. Diagrama de bloques del recorrido -------------------------------------------------------
def bloques():
    pasos = [("Tinaco", "existente"), ("Válvula de bola\n1/2\"", "existente"), ("Check 1/2\"", "existente"),
             ("T + bajada\nTuboplus", "existente"), ("Codo 90°", "nuevo"), ("Unión mixta\n20×1/2\"", "nuevo"),
             ("BOMBA 12 V\n72 W", "equipo"), ("Unión mixta\n20×1/2\"", "nuevo"), ("YF-S201", "equipo"),
             ("Electroválvula\nNC 12 V", "equipo"), ("Línea principal\nTuboplus", "nuevo"), ("Codo 90°", "nuevo"),
             ("Subida vertical\n0.08→1.52 m", "nuevo"), ("Codo 90°", "nuevo"), ("Tramo corto", "nuevo"),
             ("CRUZ\nTuboplus", "nuevo")]
    col = {"existente": "#d5d8dc", "nuevo": "#cfe8d6", "equipo": "#d6e4f5"}
    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.set_xlim(0, 8.2); ax.set_ylim(-0.6, 5.2); ax.axis("off")
    pos = []
    for i, (t, k) in enumerate(pasos):
        fila, c = divmod(i, 8)
        x = c if fila % 2 == 0 else 7 - c
        y = 4.4 - fila * 1.5
        pos.append((x + 0.5, y))
        ax.add_patch(FancyBboxPatch((x + 0.08, y - 0.38), 0.84, 0.76, boxstyle="round,pad=0.02", fc=col[k], ec="#333", lw=0.8))
        ax.text(x + 0.5, y, t, ha="center", va="center", fontsize=7.6)
    for (x1, y1), (x2, y2) in zip(pos[:-1], pos[1:]):
        if y1 == y2:
            d = 0.42 if x2 > x1 else -0.42
            ax.annotate("", (x2 - d, y2), (x1 + d, y1), arrowprops=dict(arrowstyle="->", lw=1))
        else:
            ax.annotate("", (x2, y2 + 0.4), (x1, y1 - 0.4), arrowprops=dict(arrowstyle="->", lw=1))
    xc, yc = pos[-1]
    sal = [("Línea 1: brazo + codo 90° +\ntubo + unión + espiga", 0.6), ("Línea 2 (centro): tubo +\nunión + espiga", 3.1),
           ("Línea 3: brazo + codo 90° +\ntubo + unión + espiga", 5.6)]
    for t, x in sal:
        ax.add_patch(FancyBboxPatch((x, -0.45), 2.2, 0.8, boxstyle="round,pad=0.02", fc="#fdebd0", ec="#333", lw=0.8))
        ax.text(x + 1.1, -0.05, t + "\n→ manguera → 3 aspersores → tapón", ha="center", va="center", fontsize=7)
        ax.annotate("", (x + 1.1, 0.37), (xc, yc - 0.4), arrowprops=dict(arrowstyle="->", lw=0.9, color=NAR))
    for k, (lab, c) in enumerate([("Instalación existente", col["existente"]), ("Tuboplus y conexiones nuevas", col["nuevo"]),
                                  ("Equipos", col["equipo"]), ("Laterales de manguera", "#fdebd0")]):
        ax.add_patch(Rectangle((0.1 + k * 2.05, 5.0), 0.25, 0.18, fc=c, ec="#333", lw=0.6))
        ax.text(0.42 + k * 2.05, 5.09, lab, va="center", fontsize=8)
    guardar("fig_bloques.png")


# 2. Esquema en elevación (escenario A) ------------------------------------------------------
def elevacion():
    X = G["X"]; zt = 0.265; zl = 0.08; zc = 1.52
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.add_patch(Rectangle((-0.75, 0.12), 0.6, 1.25, fc="#2b2b2b", ec="k", alpha=0.85))
    ax.text(-0.45, 0.75, "Tinaco", color="w", ha="center", fontsize=9)
    ax.plot([-0.75, -0.15], [1.19, 1.19], color="#5dade2", lw=2)
    ax.text(-0.13, 1.21, "agua +1.19 m", fontsize=7, color="#2471a3")
    ax.plot([-0.15, X["T_existente"]], [zt, zt], color=GRIS, lw=4)
    ax.plot([X["T_existente"]] * 2, [zt, zl], color=GRIS, lw=4)
    ax.plot([X["T_existente"], X["subida"]], [zl, zl], color=VERDE, lw=4)
    ax.plot([X["subida"]] * 2, [zl, zc], color=VERDE, lw=4)
    ax.plot([X["subida"], X["cruz"]], [zc, zc], color=VERDE, lw=4)
    for xa, xb, t, c in [(X["bomba_in"], X["bomba_out"], "Bomba", AZUL), (X["yf_in"], X["yf_out"], "YF", AZUL),
                         (X["ev_in"], X["ev_out"], "EV", AZUL)]:
        ax.add_patch(Rectangle((xa, zl - 0.06), xb - xa, 0.12, fc=c, ec="k"))
        ax.text((xa + xb) / 2, zl + 0.1, t, ha="center", fontsize=7.5)
    ax.text(0.03, zt + 0.05, "bola + check", fontsize=7)
    ax.add_patch(Rectangle((X["subida"] + 0.05, 0.12), 1.0, 0.40, fc="#e8c48a", ec="#8a6d3b"))
    ax.text(X["subida"] + 0.55, 0.3, "Cajón 1×1 m", ha="center", fontsize=8)
    ax.add_patch(Rectangle((X["subida"] + 0.05, 0.0), 1.0, 0.12, fc="#555", ec="k"))
    ax.plot([X["cruz"], X["subida"] + 1.0], [zc, zc], color="k", lw=2.5)
    for xa in (0.17, 0.50, 0.83):
        xx = X["subida"] + 0.05 + xa
        ax.plot([xx, xx], [zc, zc - 0.05], color=ROJO, lw=2)
        ax.add_patch(Circle((xx, zc - 0.07), 0.025, color=ROJO))
    ax.plot(X["cruz"], zc, "s", ms=9, color=NAR)
    ax.text(X["cruz"] - 0.05, zc + 0.09, "Cruz z = 1.52 m", fontsize=8, ha="right")
    ax.annotate("", (X["subida"] - 0.12, zc), (X["subida"] - 0.12, zl), arrowprops=dict(arrowstyle="<->", color=GRIS))
    ax.text(X["subida"] - 0.15, 0.8, "subida vertical\n1.44 m", ha="right", fontsize=8)
    ax.annotate("", (X["subida"], -0.12), (X["ev_out"], -0.12), arrowprops=dict(arrowstyle="<->", color=GRIS))
    ax.text((X["subida"] + X["ev_out"]) / 2, -0.2, "línea principal ≈ 2.74 m (estimado, M5)", ha="center", fontsize=8)
    ax.set_xlim(-0.9, X["subida"] + 1.2); ax.set_ylim(-0.3, 1.75)
    ax.set_xlabel("Distancia horizontal desde la salida del tinaco (m)"); ax.set_ylabel("Elevación (m)")
    ax.plot([], [], color=GRIS, lw=4, label="Existente"); ax.plot([], [], color=VERDE, lw=4, label="Tuboplus nuevo")
    ax.plot([], [], color="k", lw=2.5, label="Manguera lateral"); ax.legend(loc="upper left", fontsize=8, frameon=False)
    guardar("fig_elevacion.png")


# 3. Planta del cajón -------------------------------------------------------------------------
def planta():
    fig, ax = plt.subplots(figsize=(5.6, 5.0))
    ax.add_patch(Rectangle((0, 0), 1, 1, fc="#f6e7c8", ec="#8a6d3b", lw=2))
    yc = 0.5; xc = -0.083
    for i, y in enumerate((0.83, 0.50, 0.17), 1):
        ax.plot([-0.0, 1.0], [y, y], color="k", lw=3)
        if y != 0.5:
            ax.plot([xc, xc], [yc, y], color=VERDE, lw=4); ax.plot([xc, 0.0], [y, y], color=VERDE, lw=4)
            ax.plot(xc, y, "o", color=VERDE, ms=8)
        else:
            ax.plot([xc, 0.0], [y, y], color=VERDE, lw=4)
        for j, x in enumerate((0.17, 0.50, 0.83), 1):
            ax.add_patch(Circle((x, y), 0.03, color=ROJO)); ax.text(x, y + 0.045, f"A{i}{j}", ha="center", fontsize=8)
        ax.plot(1.0, y, "s", color="#444", ms=6)
        ax.text(1.03, y, f"L{i}", va="center", fontsize=9)
    ax.plot(xc, yc, "s", color=NAR, ms=11); ax.text(xc - 0.03, yc, "Cruz", ha="right", va="center", fontsize=9)
    ax.set_xlim(-0.35, 1.15); ax.set_ylim(-0.08, 1.08); ax.set_aspect("equal")
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    ax.plot([], [], color=VERDE, lw=4, label="Tuboplus + codo 90°"); ax.plot([], [], color="k", lw=3, label="Manguera negra")
    ax.plot([], [], "o", color=ROJO, label="Aspersor (9)"); ax.plot([], [], "s", color="#444", label="Tapón")
    ax.legend(loc="lower center", bbox_to_anchor=(0.45, -0.32), ncol=2, fontsize=8, frameon=False)
    guardar("fig_planta.png")


# 4. Curva de bomba y puntos de operación --------------------------------------------------
def bomba():
    fig, ax = plt.subplots(figsize=(7, 4))
    q = [0, 1, 2, 3, 4, 5, 6]
    ax.plot(q, [91.91 * (1 - x / 6) for x in q], color=AZUL, lw=2, label="Curva PROVISIONAL (lineal 0.9 MPa → 6 L/min)")
    for k, c in [("Q20", "#7fb3d5"), ("Q25", "#5499c7"), ("Q30", ROJO), ("Q35", "#1a5276")]:
        r = ESC[k]["resumen"]
        ax.plot(r["Q_total_Lmin"], r["H_bomba"], "o", color=c, ms=8)
        ax.annotate(f"{r['q_asp_Lh'][0]:.0f} L/h c/u\nH = {r['H_bomba']:.1f} m", (r["Q_total_Lmin"], r["H_bomba"]),
                    (-95, -8) if k == "Q35" else (8, 6), textcoords="offset points", fontsize=8)
    ax.axvline(6, color=GRIS, ls="--"); ax.text(5.85, 70, "6 L/min máx.\nanunciado", ha="right", fontsize=8)
    ax.set_xlabel("Caudal total Q (L/min)"); ax.set_ylabel("Carga de la bomba H (m)")
    ax.set_xlim(0, 7); ax.set_ylim(0, 100); ax.legend(fontsize=8, frameon=False); ax.grid(alpha=0.3)
    guardar("fig_bomba.png")


# 5. Perfil de carga piezométrica ---------------------------------------------------------
CAMINO = ["P-TK", "BOLA", "CHK", "EX-TB", "EX-BAJ", "N-A", "AD-IN", "PU1", "AD-OUT", "N-B", "YF", "N-C", "EV",
          "N-D", "N-E", "N-H", "XO1", "ESP1", "HL11", "HL12", "HL13", "RA13"]
NODOS = ["R1", "J-TK", "J-BOL", "J-CHK", "J-TEX", "J-B", "J-PIN1", "J-PIN", "J-POUT", "J-POUT2", "J-FLOW", "J-FLOW2",
         "J-EV1", "J-EV2", "J-R1", "J-R2", "J-X", "J-H1", "M1", "S11", "S12", "S13", "A13"]


def perfil():
    L = {r["id"]: r["L"] for r in R["rows"]}; L["PU1"] = 0.165
    s = [0.0]
    for e in CAMINO:
        s.append(s[-1] + L[e])
    N = B["nodes"]
    H = [1.19] + [N[n]["H"] for n in NODOS[1:]]
    z = [1.19] + [N[n]["z"] for n in NODOS[1:]]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(s, H, "-o", ms=3, color=AZUL, label="Carga piezométrica H (EPANET)")
    ax.plot(s, z, "-", color="#8d6e63", label="Elevación z")
    ax.fill_between(s, z, H, color=AZUL, alpha=0.08)
    i = NODOS.index("J-PIN"); ax.annotate("Bomba +22.98 m", (s[i + 1], H[i + 1]), (15, -25), textcoords="offset points",
                                           arrowprops=dict(arrowstyle="->"), fontsize=8)
    ax.annotate(f"A13 (mínima): P = {N['A13']['P']:.2f} m", (s[-1], H[-1]), (-160, -30), textcoords="offset points",
                arrowprops=dict(arrowstyle="->"), fontsize=8)
    ax.set_xlabel("Distancia a lo largo de la tubería (m)"); ax.set_ylabel("m.c.a."); ax.grid(alpha=0.3)
    ax.legend(fontsize=8, frameon=False, loc="center left")
    guardar("fig_perfil.png")


# 6. Pérdidas por componente --------------------------------------------------------------
def perdidas():
    grupos = {"Instalación existente": ["P-TK", "BOLA", "CHK", "EX-TB", "EX-BAJ"],
              "Adaptadores de bomba (3/8\")": ["AD-IN", "AD-OUT"], "Uniones, niples y codo inicial": ["N-A", "N-B", "N-C"],
              "YF-S201": ["YF"], "Electroválvula": ["EV"], "Línea principal + codo": ["N-D"], "Subida vertical + codo": ["N-E", "N-H"],
              "Cruz, brazo y espiga (L1)": ["XO1", "ESP1"], "Manguera L1": ["HL11", "HL12", "HL13"], "Toma aspersor A13": ["RA13"]}
    rr = {r["id"]: r for r in R["rows"]}
    nom = list(grupos); hf = [sum(rr[e]["hf"] for e in grupos[g]) for g in nom]; hm = [sum(rr[e]["hm"] for e in grupos[g]) for g in nom]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = range(len(nom))
    ax.barh(y, hf, color=AZUL, label="Distribuida (Darcy-Weisbach)")
    ax.barh(y, hm, left=hf, color=NAR, label="Menores (K·V²/2g)")
    for k in y:
        ax.text(hf[k] + hm[k] + 0.003, k, f"{(hf[k] + hm[k]) * 100:.1f} cm", va="center", fontsize=8)
    ax.set_yticks(list(y)); ax.set_yticklabels(nom, fontsize=8.5); ax.invert_yaxis()
    ax.set_xlabel("Pérdida de carga (m)"); ax.legend(fontsize=8, frameon=False, loc="lower right")
    guardar("fig_perdidas.png")


# 7. Sensibilidad -------------------------------------------------------------------------
def sensibilidad():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8))
    ks = ["Q20", "Q25", "Q30", "Q35"]
    a1.plot([ESC[k]["resumen"]["q_asp_Lh"][0] for k in ks], [ESC[k]["resumen"]["P_min"] for k in ks], "-o", color=AZUL)
    a1.plot([40], [-1.79], "x", color=ROJO, ms=10); a1.text(39, 3, "40 L/h:\nno viable", ha="right", fontsize=8, color=ROJO)
    a1.axhline(0, color=GRIS, lw=0.8)
    a1.set_xlabel("Caudal impuesto por aspersor (L/h)"); a1.set_ylabel("Presión mínima en aspersores (m)"); a1.grid(alpha=0.3)
    a1.set_title("a) Caudal por aspersor", fontsize=10)
    et = [("CURVA_x0.25", "Curva ×0.25"), ("CURVA_x0.50", "Curva ×0.50"), ("CURVA_x0.75", "Curva ×0.75"),
          ("TINACO_MIN", "Tinaco casi vacío"), ("K_ALTOS", "K altos"), ("K_BAJOS", "K bajos"), ("DH10", "Manguera 10 mm"),
          ("DH14", "Manguera 14 mm"), ("HW150", "Hazen-Williams"), ("Q30", "Base (30 L/h)")]
    v = [ESC[k]["resumen"]["P_min"] for k, _ in et]
    a2.barh(range(len(et)), v, color=[ROJO if k == "Q30" else "#7fb3d5" for k, _ in et])
    a2.set_yticks(range(len(et))); a2.set_yticklabels([t for _, t in et], fontsize=8); a2.invert_yaxis()
    for i, x in enumerate(v):
        a2.text(x + 0.3, i, f"{x:.1f}", va="center", fontsize=7.5)
    a2.set_xlabel("Presión mínima (m)"); a2.set_title("b) Otros parámetros (30 L/h)", fontsize=10)
    plt.tight_layout(); guardar("fig_sensibilidad.png")


# 8. Diagrama de flujo del control ------------------------------------------------------
def control():
    fig, ax = plt.subplots(figsize=(5.2, 7.2)); ax.axis("off"); ax.set_xlim(0, 10.2); ax.set_ylim(0, 14)
    cajas = [(12.8, "Inicio: configurar GPIO2 (bomba)\ny contador de pulsos PCNT (GPIO4)", "r"),
             (11.1, "Esperar 10 s; borrar contador", "r"),
             (9.4, "Encender bomba (GPIO2 = 1)", "r"),
             (7.7, "Cada 100 ms: leer pulsos\ndel YF-S201", "r"),
             (5.6, "¿pulsos > 5 L × 450\n= 2250?", "d"),
             (3.4, "Apagar bomba (GPIO2 = 0)\n\"Fin de riego\"", "r"),
             (1.5, "Esperar; reportar\npulsos totales", "r")]
    for y, t, f in cajas:
        if f == "d":
            ax.add_patch(plt.Polygon([(5, y + 1.0), (8.4, y), (5, y - 1.0), (1.6, y)], fc="#fdebd0", ec="k"))
        else:
            ax.add_patch(FancyBboxPatch((1.2, y - 0.55), 7.6, 1.1, boxstyle="round,pad=0.05", fc="#d6e4f5", ec="k"))
        ax.text(5, y, t, ha="center", va="center", fontsize=8.5)
    for (y1, _, f1), (y2, _, _) in zip(cajas[:-1], cajas[1:]):
        ax.annotate("", (5, y2 + (1.0 if y2 == 5.6 else 0.6)), (5, y1 - (1.0 if f1 == "d" else 0.6)), arrowprops=dict(arrowstyle="->"))
    ax.text(5.2, 4.35, "Sí", fontsize=8)
    ax.plot([8.4, 9.4, 9.4], [5.6, 5.6, 7.7], color="k", lw=1)
    ax.annotate("", (8.85, 7.7), (9.4, 7.7), arrowprops=dict(arrowstyle="->"))
    ax.text(9.5, 6.6, "No", fontsize=8)
    guardar("fig_control.png")


for f in (bloques, elevacion, planta, bomba, perfil, perdidas, sensibilidad, control):
    f()

# Datos para el documento ----------------------------------------------------------------
json.dump({"rows": R["rows"], "res": RES, "esc": {k: {"desc": v["desc"], "ok": v["ok22"], "msgs": v["msgs"], "r": v.get("resumen")}
          for k, v in ESC.items()}, "geo": {k: v for k, v in G.items()}, "nodes": B["nodes"], "links": B["links"],
           "K_EV": R["K_EV"], "L_lineas": R["L_lineas"],
           "geos": {k: {"nuevo_m": v["nuevo_m"], "margen_m": v["margen_m"], "desc": v["desc"], "rol": v["rol"],
                        "M1_M5_max_m": v["M1_M5_max_m"]} for k, v in R["GEOS"].items()}},
          open(os.path.join(AQUI, "datos_reporte.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
print("OK figuras:", sorted(os.listdir(FIG)))
