"""Figuras de resultados equivalentes a las vistas del mapa de EPANET (Pressure/Flow, Pressure/Velocity,
Demand/Unit Headloss). Son FIGURAS PYTHON con resultados del motor EPANET 2.2 (WNTR) sobre
riego_huerto_v2_presentacion.inp; NO son capturas de la interfaz grafica de EPANET.

Uso: uv run --python 3.12 --with wntr --with epyt --with matplotlib python graficar_resultados.py
"""
import os, shutil, tempfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
import wntr

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "capturas_epanet")
BLUE = LinearSegmentedColormap.from_list("blue", ["#86b6ef", "#3987e5", "#256abf", "#104281", "#0d366b"])
INK, MUTED, SURF = "#1f1f1f", "#6b6b6b", "#ffffff"

src = os.path.join(HERE, "riego_huerto_v2_presentacion.inp")
tmp = os.path.join(tempfile.mkdtemp(), "p.inp"); shutil.copy(src, tmp)
wn = wntr.network.WaterNetworkModel(tmp)
res = wntr.sim.EpanetSimulator(wn).run_sim(file_prefix=os.path.join(tempfile.mkdtemp(), "r"), version=2.2)
P = res.node["pressure"].iloc[0]; Dm = res.node["demand"].iloc[0] * 1000
Q = res.link["flowrate"].iloc[0] * 1000; V = res.link["velocity"].iloc[0]
HL = res.link["headloss"].iloc[0] * 1000      # WNTR: perdida unitaria de tuberias (m/m) -> m/km
xy = {n: wn.get_node(n).coordinates for n in wn.node_name_list}
EM = ["E1", "E2", "E3", "E4"]
NOMBRES = {"R1": "TINACO", "J-PIN": "succion", "J-POUT": "descarga\nbomba", "J-T": "T", **{e: e for e in EM}}


def mapa(ax, node_val, node_lbl, node_fmt, link_val, link_lbl, link_fmt, link_keys, titulo):
    tuberias = [l for l in wn.link_name_list if wn.get_link(l).link_type == "Pipe"]
    vmax = max(abs(link_val[l]) for l in tuberias) or 1       # la bomba no escala el grosor
    for l in wn.link_name_list:
        lk = wn.get_link(l)
        a, b = xy[lk.start_node_name], xy[lk.end_node_name]
        w = 3.0 if l not in tuberias else 1.0 + 5.0 * min(abs(link_val[l]) / vmax, 1.0)
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#4a4a4a" if l not in tuberias else "#8a8a8a", lw=w,
                solid_capstyle="round", zorder=1)
        if l in link_keys:
            vert = abs(a[0] - b[0]) < 1e-6
            ax.annotate(f"{l}: {link_fmt(link_val[l])}", ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2),
                        xytext=(-7, 0) if vert else (0, -14), textcoords="offset points",
                        ha="right" if vert else "center", va="center" if vert else "baseline",
                        fontsize=7.5, color=MUTED, zorder=4)
    nv = [node_val[n] for n in wn.node_name_list if n != "R1"]
    norm = Normalize(min(nv), max(nv) if max(nv) > min(nv) else min(nv) + 1)
    for n in wn.node_name_list:
        c = "#3a3a3a" if n == "R1" else BLUE(norm(node_val[n]))
        ax.scatter(*xy[n], s=70 if n in EM or n == "R1" else 34, color=c, edgecolor=SURF, linewidth=1.5,
                   marker="s" if n == "R1" else "o", zorder=3)
        if n in NOMBRES:
            txt = (f"TINACO\nnivel {wn.get_node('R1').base_head:.2f} m" if n == "R1"
                   else f"{NOMBRES[n]}\n{node_fmt(node_val[n])}")
            off, ha = ((10, 10), "left") if n == "J-T" else ((0, 10), "center")
            ax.annotate(txt, xy[n], xytext=off, textcoords="offset points",
                        ha=ha, va="bottom", fontsize=8, color=INK, zorder=5)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=BLUE)
    cb = plt.colorbar(sm, ax=ax, fraction=0.025, pad=0.01); cb.set_label(node_lbl, color=INK, fontsize=9)
    cb.outline.set_visible(False)
    ax.set_title(titulo, loc="left", fontsize=11, color=INK)
    ax.text(0, -0.06, f"Nodos (color): {node_lbl}.   Enlaces (grosor y rotulos): {link_lbl}.   "
            "Figura Python con resultados del motor EPANET 2.2 (WNTR) - NO es captura de la GUI de EPANET.\n"
            "Presiones PROVISIONALES (curva de bomba no certificada). Perdida unitaria como la reporta EPANET "
            "(friccion + perdidas menores por km de enlace). Bomba en gris oscuro. Caudal de aspersor a >2 bar = EXTRAPOLACION del modelo, no dato Hunter.", transform=ax.transAxes,
            fontsize=7.5, color=MUTED, va="top")
    ax.set_aspect("equal"); ax.axis("off")


def fig(nombre, *args):
    f, ax = plt.subplots(figsize=(15, 5.6))
    f.patch.set_facecolor(SURF)
    mapa(ax, *args)
    f.tight_layout(); f.savefig(os.path.join(OUT, nombre), dpi=130, facecolor=SURF); plt.close(f)
    print("ok", nombre)


claves = ["PU1", "T-F", "BR-L", "L1-B", "L2-B", "RE2", "RE4"]
fig("01_Pressure_Flow_PYTHON.png", P, "Presion (m)", lambda v: f"{v:.2f} m", Q, "Caudal (L/s)", lambda v: f"{v:.4f} L/s", claves,
    "Riego v2 - Presion en nodos y caudal en enlaces (escenario base)")
fig("02_Pressure_Velocity_PYTHON.png", P, "Presion (m)", lambda v: f"{v:.2f} m", V, "Velocidad (m/s)", lambda v: f"{v:.3f} m/s",
    ["T-F", "YF", "BR-L", "L1-B", "RE2"], "Riego v2 - Presion en nodos y velocidad en enlaces")
fig("03_Demand_UnitHeadloss_PYTHON.png", Dm, "Demanda / flujo de emisor (L/s)", lambda v: f"{v:.4f} L/s", HL,
    "Perdida unitaria (m/km)", lambda v: f"{v:.1f} m/km", ["T-F", "YF", "BR-L", "L1-B", "RE2"],
    "Riego v2 - Flujo de emisores y perdida unitaria (friccion + menores)")


# ---------------- 04: cobertura geometrica del cajon ----------------
import sys, numpy as np
sys.path.insert(0, HERE)
import generar_modelo as G
from matplotlib.patches import Circle, Rectangle
cfg = G.CONFIG
pts = [(x, y) for y in cfg["cajon"]["y_laterales"] for x in cfg["cajon"]["x_aspersores"]]
f, axs = plt.subplots(1, 2, figsize=(11, 5.4)); f.patch.set_facecolor(SURF)
for ax, r in zip(axs, (cfg["cobertura"]["radio_deseado_m"], cfg["cobertura"]["radio_objetivo_m"])):
    cv = G.cobertura(r)
    g = np.linspace(0, 1, 401); Xg, Yg = np.meshgrid(g, g)
    d = np.min([np.hypot(Xg - a, Yg - b) for a, b in pts], axis=0)
    ax.imshow((d > r).astype(float), extent=(0, 1, 0, 1), origin="lower", cmap=LinearSegmentedColormap.from_list("u", [SURF, "#e06c5a"]),
              vmin=0, vmax=1, zorder=0)
    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, ec=INK, lw=1.5, zorder=3))
    for a, b in pts:
        ax.add_patch(Circle((a, b), r, fc="#86b6ef", ec="#256abf", alpha=0.35, lw=1.2, zorder=1))
        ax.plot(a, b, "o", color="#104281", ms=7, zorder=4)
    for (x, y) in cv["puntos_dmax"]:
        ax.plot(x, y, "x", color=INK, ms=7, mew=1.5, zorder=5)
    pr = G.presion_para_radio(r)
    exacto = any(abs(2 * r - t[2]) < 1e-9 for t in cfg["aspersor"]["tabla_bar_Lh_diam_m"])
    ptxt = (f"{pr['P_bar']:.2f} bar y {pr['Q_tabla_Lh']:.0f} L/h (punto de la tabla oficial Hunter, max. ajuste)" if exacto else
            f"~{pr['P_bar']:.2f} bar y ~{pr['Q_tabla_Lh']:.0f} L/h (interpolado de la tabla Hunter, max. ajuste)") \
        if pr["dentro_tabla"] else "fuera de tabla"
    ax.set_title(f"Radio {r:.2f} m: cubierto {cv['cubierto'] * 100:.1f} %\n{ptxt}", fontsize=10, color=INK, loc="left")
    ax.set_xlim(-0.05, 1.05); ax.set_ylim(-0.05, 1.05); ax.set_aspect("equal")
    ax.set_xlabel("x en el cajon (m)", color=MUTED); ax.set_ylabel("y (m)", color=MUTED)
f.text(0.01, 0.01, "Rojo = zona fuera del radio de todo aspersor. X = puntos a 0.354 m del aspersor mas cercano (centro, esquinas, "
       "puntos medios de bordes). Presion por interpolacion lineal de la tabla oficial Hunter (diametro de mojado en maximo ajuste); "
       "no es dato publicado. Cobertura geometrica != lamina uniforme.", fontsize=7.5, color=MUTED, wrap=True)
f.tight_layout(rect=(0, 0.06, 1, 1)); f.savefig(os.path.join(OUT, "04_Cobertura_PYTHON.png"), dpi=130, facecolor=SURF); plt.close(f)
print("ok 04_Cobertura_PYTHON.png")
