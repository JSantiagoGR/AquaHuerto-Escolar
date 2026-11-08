"""Generador PARAMETRICO del modelo EPANET v2 (riego con 4 microaspersores) + calculos + escenarios.

Uso (desde la carpeta 2):
    uv run --python 3.12 --with wntr --with epyt --with matplotlib python generar_modelo.py

Para cambiar el tinaco, el aspersor, la bomba, los K o la geometria: edite SOLO el bloque CONFIG
y vuelva a ejecutar. Se regeneran: riego_huerto_v2_final.inp, riego_huerto_v2_presentacion.inp,
tabla_cortes_tuboplus.csv, resultados_epanet.csv, escenarios_sensibilidad.csv,
calculos_resultados.md (tablas numericas) y figuras en capturas_epanet/.

Clasificacion de datos: OFICIAL, MEDIDO, CALCULADO, ESTIMADO, PROVISIONAL, PENDIENTE.
"""
import math, os, csv, json, re, tempfile, copy

HERE = os.path.dirname(os.path.abspath(__file__))

# =====================================================================================
# CONFIG  (todas las longitudes en m, diametros en mm, elevaciones z en m sobre tierra del huerto)
# =====================================================================================
CONFIG = {
    # --- Agua (20 C) -------------------------------------------------------------- ESTIMADO
    "rho": 998.2, "mu": 1.002e-3, "nu": 1.004e-6, "g": 9.81,

    # --- Tuberia Tuboplus 20 mm (1/2") Clase 16, SDR 7.4, codigo 200224 ----------- OFICIAL
    "tubo": {"de_mm": 20.0, "e_mm": 2.80, "di_mm": 14.40, "rug_mm": 0.007, "C_HW": 150,
             "largo_tramo_m": 4.0, "n_tramos": 2, "max_m": 8.00, "objetivo_m": 7.50},

    # --- Tinaco ORIGINAL ---------------------------------------------------------- PROVISIONAL (medido aprox.)
    "tinaco": {"z_banqueta": 0.07, "z_base": 0.12, "z_fondo": 0.19, "z_agua_max": 1.19,
               "z_salida": 0.265, "z_agua_min": 0.30},   # z_agua_min: escenario de sensibilidad (ESTIMADO)

    # --- Elevaciones del sistema --------------------------------------------------- MEDIDO aprox. / ESTIMADO
    "z_bomba": 0.08, "z_riego": 0.52,
    "z_lateral": 0.53,          # eje del tubo sobre el suelo del cajon: 0.52 + 0.01 (radio ext.)  CALCULADO
    "z_boquilla": 0.56,         # tee + adaptador + SD-B sobre el eje del lateral (~3 cm)        ESTIMADO

    # --- Microaspersor PROVISIONAL: Hunter Solo-Drip SD-B (SKU SDB) ---------------- OFICIAL (ficha metrica)
    "aspersor": {"modelo": "Hunter Solo-Drip SD-B (SKU SDB) 360 deg, espiga 6 mm",
                 "tabla_bar_Lh_diam_m": [(1.0, 40, 0.5), (1.5, 50, 0.6), (2.0, 60, 0.8)],  # maximo ajuste
                 "rango_bar": (0.5, 2.5), "filtracion": "100 mesh / 150 micras",
                 "P_diseno_bar": 1.5, "Q_diseno_Lh": 50.0, "n_supuesto_orificio": 0.5},

    # --- Bomba GOOD PUMPS 12 V 72 W -------------------------------------------------- PROVISIONAL
    # Curva NO certificada: extremos de placa interpretados como Q=6 L/min a H~0 y 0.9 MPa a Q~0 (lineal).
    "bomba_curva": [(0.000, 91.91), (0.050, 45.96), (0.100, 0.00)],

    # --- K de perdidas menores (referidos a la velocidad del enlace donde se aplican) -----------
    "K": {
        "codo90": 2.00,            # OFICIAL Tuboplus Tabla 10 (No.3)
        "tee_division": 2.20,      # OFICIAL Tuboplus Tabla 10 (No.8: entra por derivacion, sale por ambos lados)
        "tee_rosca_central": 0.80, # OFICIAL Tuboplus Tabla 10 (No.9: tee con rosca central metalica)
        "conector": 0.40,          # OFICIAL Tuboplus Tabla 10 (No.10: conector macho/hembra)
        "reduccion": 0.55,         # OFICIAL Tuboplus Tabla 10 (No.2)  (1/2" -> puerto de bomba)
        "ampliacion": 0.85,        # OFICIAL Tuboplus Tabla 10 (No.2a) (puerto de bomba -> 1/2")  interpretacion
        "entrada_tinaco": 0.50,    # ESTIMADO literatura (entrada de borde vivo; Crane TP-410 / Idelchik)
        "check": 2.70,             # ESTIMADO Crane TP-410 check de columpio K=100 fT, fT(1/2")=0.027
        "yfs201": 2.00,            # ESTIMADO (sin dato de fabricante), referido a la velocidad en D=11 mm
        "rama_aspersor": 1.00,     # ESTIMADO adaptador 1/2" -> espiga 6 mm (contraccion + adaptador)
    },
    "Kv_electrovalvula": 3.0,      # ESTIMADO (m3/h) -> se convierte a K; sensibilidad 1..6
    "D_yfs201_mm": 11.0,           # Handsontec YF-S201 (diametro interior 11 mm)          DOC. TECNICA
    "D_rama_aspersor_mm": 4.0,     # ESTIMADO paso interior de la espiga de 6 mm

    # --- Longitudes fisicas de componentes NO Tuboplus (m) ----------------------------- ESTIMADO
    "L_niple_tinaco": 0.040, "L_check": 0.055, "L_bomba_puertos": 0.160, "L_adaptador_bomba": 0.035,
    "L_yfs201": 0.062, "L_electrovalvula": 0.085, "L_rama_aspersor": 0.030,

    # --- Dimensiones OFICIALES de conexiones Tuboplus 20 mm (catalogo Manual Tecnico 2017) -----
    # toma (take-off) = distancia del centro/cara de la conexion al extremo del tubo insertado
    "fit": {"codo90": {"codigo": "200014", "L": 27, "p": 15},          # toma = 12 mm
            "tee": {"codigo": "200178", "L1": 27, "p": 16},            # toma = 11 mm
            "tee_rc": {"codigo": "2000166", "Lmedio": 27, "L1": 33, "p": 16},  # tee rosca central hembra
            "conector": {"codigo": "200039/200051", "L": 53, "p": 16},  # 37 mm del tubo a la rosca
            "union_mixta": {"codigo": "200235", "L": 46, "p": 16},      # 30 mm
            "tapon": {"codigo": "200155", "L": 20, "p": 16}},

    # --- Cortes de Tuboplus elegidos (m, longitud real a cortar, incluye insercion p en cada socket) ---
    "cortes": {
        "A_salida_check_codo":   0.090,
        "B_bajada_vertical":     None,   # se calcula: (z_salida - z_bomba) - 2 tomas de codo
        "C_codo_a_bomba":        0.240,
        "D_bomba_a_yfs201":      0.060,
        "E_yfs201_a_valvula":    0.060,
        "F_linea_principal":     None,   # se calcula para que el subida quede a X_subida
        "G_subida_vertical":     None,   # se calcula: (z_lateral - z_bomba) - 2 tomas de codo
        "H_codo_a_T":            0.060,
        "I_brazo":               None,   # se calcula: separacion lateral/2 - tomas
        "J_codo_a_aspersor_A":   None,   # se calcula: posicion aspersor A - tomas
        "K_aspersor_A_a_B":      None,   # se calcula: separacion A-B - tomas
        "L_niple_tapon":         0.040,
    },
    "X_subida": 3.95,            # distancia horizontal tinaco -> eje de la subida (borde del cajon en 4.00)  ESTIMADO
    "X_borde_cajon": 4.00,
    "cajon": {"largo": 1.0, "ancho": 1.0, "y_laterales": (0.25, 0.75), "x_aspersores": (0.25, 0.75)},
    # --- Escenario de cobertura (analisis geometrico; NO cambia la distribucion) --------- CALCULADO
    "cobertura": {"radio_deseado_m": 0.30, "radio_objetivo_m": 0.36},
}

# =====================================================================================
# utilidades
# =====================================================================================
C = CONFIG
DI = C["tubo"]["di_mm"] / 1000
A_TUBO = math.pi * DI**2 / 4
Q_E = C["aspersor"]["Q_diseno_Lh"] / 3600            # L/s por emisor
Q_TOT = 4 * Q_E


def toma(f):
    d = C["fit"][f]
    return ({"codo90": d.get("L", 0) - d["p"], "tee": d.get("L1", 0) - d["p"],
             "conector": d.get("L", 0) - d["p"], "union_mixta": d.get("L", 0) - d["p"]}[f]) / 1000


def tee_rc_run():
    return (C["fit"]["tee_rc"]["Lmedio"] - C["fit"]["tee_rc"]["p"]) / 1000


def kv_to_K(Kv, Q_Ls, D_m):
    """Kv [m3/h a dp=1 bar]: dp_bar=(Q/Kv)^2 -> h = dp*1e5/(rho g); K = 2 g h / V^2"""
    Qh = Q_Ls * 3.6
    dp_bar = (Qh / Kv) ** 2
    h = dp_bar * 1e5 / (C["rho"] * C["g"])
    V = Q_Ls / 1000 / (math.pi * D_m**2 / 4)
    return 2 * C["g"] * h / V**2


def ajuste_emisor():
    """Ajuste Q = Cd * P^n con los puntos OFICIALES de maximo ajuste (Q L/s, P m)."""
    pts = [(b * 1e5 / (C["rho"] * C["g"]), q / 3600) for b, q, _ in C["aspersor"]["tabla_bar_Lh_diam_m"]]
    xs = [math.log(p) for p, _ in pts]; ys = [math.log(q) for _, q in pts]
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    a = math.exp(my - b * mx)
    Pd = C["aspersor"]["P_diseno_bar"] * 1e5 / (C["rho"] * C["g"])
    Cd_fit_ancla = Q_E / Pd**b                # ancla exacta en el punto de diseno (1.5 bar, 50 L/h)
    Cd_05 = Q_E / Pd**0.5
    return {"n_fit": b, "C_fit_regresion": a, "C_fit": Cd_fit_ancla, "C_05": Cd_05, "P_diseno_m": Pd, "pts": pts}


EM = ajuste_emisor()
K_EV = kv_to_K(C["Kv_electrovalvula"], Q_TOT, DI)

# =====================================================================================
# GEOMETRIA: cortes, posiciones y longitudes de enlaces
# =====================================================================================
def geometria():
    t = C["tinaco"]; f = C["fit"]; cut = dict(C["cortes"])
    tc, tt = toma("codo90"), toma("tee")
    trc = tee_rc_run()
    tcon, tun = toma("conector"), toma("union_mixta")
    tap_extra = (f["tapon"]["L"] - f["tapon"]["p"]) / 1000
    cut["B_bajada_vertical"] = round((t["z_salida"] - C["z_bomba"]) - 2 * tc, 3)
    cut["G_subida_vertical"] = round((C["z_lateral"] - C["z_bomba"]) - 2 * tc, 3)
    yl = C["cajon"]["y_laterales"]; xa = C["cajon"]["x_aspersores"]
    brazo_cc = (yl[1] - yl[0]) / 2
    cut["I_brazo"] = round(brazo_cc - tt - tc, 3)
    # posiciones a lo largo del recorrido (X horizontal desde la cara de salida del tinaco)
    X = {}
    X["salida"] = 0.0
    X["check_out"] = C["L_niple_tinaco"] + C["L_check"]
    X["C1"] = X["check_out"] + tcon + cut["A_salida_check_codo"] + tc
    X["bomba_in"] = X["C1"] + tc + cut["C_codo_a_bomba"] + tun + C["L_adaptador_bomba"]
    X["bomba_out"] = X["bomba_in"] + C["L_bomba_puertos"]
    X["yf_in"] = X["bomba_out"] + C["L_adaptador_bomba"] + tun + cut["D_bomba_a_yfs201"] + tcon
    X["yf_out"] = X["yf_in"] + C["L_yfs201"]
    X["ev_in"] = X["yf_out"] + tcon + cut["E_yfs201_a_valvula"] + tcon
    X["ev_out"] = X["ev_in"] + C["L_electrovalvula"]
    X["R"] = C["X_subida"]
    cut["F_linea_principal"] = round(X["R"] - X["ev_out"] - tcon - tc, 3)
    X["T"] = X["R"] + tc + cut["H_codo_a_T"] + tt
    x0 = C["X_borde_cajon"]
    X["E_A"] = x0 + xa[0]; X["E_B"] = x0 + xa[1]
    cut["J_codo_a_aspersor_A"] = round((X["E_A"] - X["T"]) - tc - trc, 3)
    cut["K_aspersor_A_a_B"] = round((xa[1] - xa[0]) - 2 * trc, 3)
    X["tapon_fin"] = X["E_B"] + trc + (cut["L_niple_tapon"] - 2 * 0.016) + tap_extra
    # longitudes centro-a-centro de los enlaces EPANET (m)
    Lk = {
        "P-TK": C["L_niple_tinaco"], "CHK": C["L_check"],
        "T-A": tcon + cut["A_salida_check_codo"] + tc,
        "T-B": t["z_salida"] - C["z_bomba"],
        "T-C": tc + cut["C_codo_a_bomba"] + tun + C["L_adaptador_bomba"],
        "T-D": C["L_adaptador_bomba"] + tun + cut["D_bomba_a_yfs201"] + tcon,
        "YF": C["L_yfs201"],
        "T-E": tcon + cut["E_yfs201_a_valvula"] + tcon,
        "EV": C["L_electrovalvula"],
        "T-F": tcon + cut["F_linea_principal"] + tc,
        "T-G": C["z_lateral"] - C["z_bomba"],
        "T-H": tc + cut["H_codo_a_T"] + tt,
        "BRAZO": brazo_cc,
        "LAT-A": tc + cut["J_codo_a_aspersor_A"] + trc,
        "LAT-B": xa[1] - xa[0],
        "TAPON": trc + cut["L_niple_tapon"] - 2 * 0.016 + tap_extra,
        "RAMA": C["L_rama_aspersor"],
    }
    return cut, X, Lk


CUT, X, LK = geometria()

# =====================================================================================
# RED EPANET
# =====================================================================================
def red():
    """Devuelve nodos y enlaces (elevaciones, longitudes, D, K, status, tipo, etiqueta fisica)."""
    t = C["tinaco"]; K = C["K"]; zb = C["z_bomba"]; zl = C["z_lateral"]; ze = C["z_boquilla"]
    nodes = {  # id: (elev, descripcion)
        "J-TK": (t["z_salida"], "Salida del tinaco (rosca 1/2\")"),
        "J-CHK": (t["z_salida"], "Salida de la valvula check"),
        "J-C1": (t["z_salida"], "Codo 90 superior (baja)"),
        "J-C2": (zb, "Codo 90 inferior (a bomba)"),
        "J-PIN": (zb, "Succion de la bomba"),
        "J-POUT": (zb, "Descarga de la bomba"),
        "J-FLOW": (zb, "Entrada YF-S201"),
        "J-FLOW2": (zb, "Salida YF-S201"),
        "J-EV1": (zb, "Entrada electrovalvula"),
        "J-EV2": (zb, "Salida electrovalvula"),
        "J-R1": (zb, "Codo inferior de la subida"),
        "J-R2": (zl, "Codo superior de la subida"),
        "J-T": (zl, "T centrada de distribucion"),
        "J-CL": (zl, "Codo lateral 1"), "J-CR": (zl, "Codo lateral 2"),
        "T-E1": (zl, "Tee aspersor 1 (L1, A)"), "T-E2": (zl, "Tee aspersor 2 (L1, B)"),
        "T-E3": (zl, "Tee aspersor 3 (L2, A)"), "T-E4": (zl, "Tee aspersor 4 (L2, B)"),
        "E1": (ze, "Microaspersor 1 SD-B (L1, A)"), "E2": (ze, "Microaspersor 2 SD-B (L1, B)"),
        "E3": (ze, "Microaspersor 3 SD-B (L2, A)"), "E4": (ze, "Microaspersor 4 SD-B (L2, B)"),
        "TAP1": (zl, "Tapon final lateral 1"), "TAP2": (zl, "Tapon final lateral 2"),
    }
    d = C["tubo"]["di_mm"]; dyf = C["D_yfs201_mm"]; dr = C["D_rama_aspersor_mm"]
    # id: (n1, n2, L, D, K, status, material, descripcion)
    links = [
        ("P-TK", "R1", "J-TK", LK["P-TK"], d, K["entrada_tinaco"], "Open", "niple", "Salida/niple del tinaco"),
        ("CHK", "J-TK", "J-CHK", LK["CHK"], d, K["check"], "CV", "check", "VALVULA CHECK 1/2\" (solo tinaco->bomba)"),
        ("T-A", "J-CHK", "J-C1", LK["T-A"], d, K["conector"] + K["codo90"], "Open", "tuboplus", "Tubo corto + codo 90"),
        ("T-B", "J-C1", "J-C2", LK["T-B"], d, K["codo90"], "Open", "tuboplus", "Bajada vertical + codo 90"),
        ("T-C", "J-C2", "J-PIN", LK["T-C"], d, K["conector"] + K["reduccion"], "Open", "tuboplus", "Tubo a bomba + union mixta + adaptador"),
        ("T-D", "J-POUT", "J-FLOW", LK["T-D"], d, K["ampliacion"] + 2 * K["conector"], "Open", "tuboplus", "Adaptador + union mixta + tubo + conector"),
        ("YF", "J-FLOW", "J-FLOW2", LK["YF"], dyf, K["yfs201"], "Open", "yfs201", "CAUDALIMETRO YF-S201 (D int 11 mm)"),
        ("T-E", "J-FLOW2", "J-EV1", LK["T-E"], d, 2 * K["conector"], "Open", "tuboplus", "Conectores + tubo"),
        ("EV", "J-EV1", "J-EV2", LK["EV"], d, K_EV, "Open", "electrovalvula", "ELECTROVALVULA NC 12 V (OPEN en riego)"),
        ("T-F", "J-EV2", "J-R1", LK["T-F"], d, K["conector"] + K["codo90"], "Open", "tuboplus", "LINEA PRINCIPAL + codo 90"),
        ("T-G", "J-R1", "J-R2", LK["T-G"], d, K["codo90"], "Open", "tuboplus", "SUBIDA al cajon + codo 90"),
        ("T-H", "J-R2", "J-T", LK["T-H"], d, K["tee_division"], "Open", "tuboplus", "Tramo a T + T division"),
        ("BR-L", "J-T", "J-CL", LK["BRAZO"], d, K["codo90"], "Open", "tuboplus", "Brazo izquierdo + codo"),
        ("BR-R", "J-T", "J-CR", LK["BRAZO"], d, K["codo90"], "Open", "tuboplus", "Brazo derecho + codo"),
        ("L1-A", "J-CL", "T-E1", LK["LAT-A"], d, K["tee_rosca_central"], "Open", "tuboplus", "LATERAL 1 tramo a aspersor 1"),
        ("L1-B", "T-E1", "T-E2", LK["LAT-B"], d, K["tee_rosca_central"], "Open", "tuboplus", "LATERAL 1 tramo a aspersor 2"),
        ("L1-T", "T-E2", "TAP1", LK["TAPON"], d, 0.0, "Open", "tuboplus", "Niple + tapon L1 (sin flujo)"),
        ("L2-A", "J-CR", "T-E3", LK["LAT-A"], d, K["tee_rosca_central"], "Open", "tuboplus", "LATERAL 2 tramo a aspersor 3"),
        ("L2-B", "T-E3", "T-E4", LK["LAT-B"], d, K["tee_rosca_central"], "Open", "tuboplus", "LATERAL 2 tramo a aspersor 4"),
        ("L2-T", "T-E4", "TAP2", LK["TAPON"], d, 0.0, "Open", "tuboplus", "Niple + tapon L2 (sin flujo)"),
        ("RE1", "T-E1", "E1", LK["RAMA"], dr, K["rama_aspersor"], "Open", "adaptador", "Adaptador 1/2\"->espiga 6 mm"),
        ("RE2", "T-E2", "E2", LK["RAMA"], dr, K["rama_aspersor"], "Open", "adaptador", "Adaptador 1/2\"->espiga 6 mm"),
        ("RE3", "T-E3", "E3", LK["RAMA"], dr, K["rama_aspersor"], "Open", "adaptador", "Adaptador 1/2\"->espiga 6 mm"),
        ("RE4", "T-E4", "E4", LK["RAMA"], dr, K["rama_aspersor"], "Open", "adaptador", "Adaptador 1/2\"->espiga 6 mm"),
    ]
    return nodes, links


NODES, LINKS = red()
EMISORES = ["E1", "E2", "E3", "E4"]


def coords_final():
    """Esquema geometrico: X = recorrido real (m x 1000); Y = elevacion exagerada x2 en el tramo
    tinaco-subida; en el cajon, vista en planta (Y = posicion transversal)."""
    s = 1000; zc = lambda z: z * 2 * s
    xs = {"J-TK": X["salida"], "J-CHK": X["check_out"], "J-C1": X["C1"], "J-C2": X["C1"],
          "J-PIN": X["bomba_in"], "J-POUT": X["bomba_out"], "J-FLOW": X["yf_in"], "J-FLOW2": X["yf_out"],
          "J-EV1": X["ev_in"], "J-EV2": X["ev_out"], "J-R1": X["R"], "J-R2": X["R"]}
    xy = {k: (v * s, zc(NODES[k][0])) for k, v in xs.items()}
    xy["R1"] = (-0.45 * s, zc(C["tinaco"]["z_agua_max"]))
    yT = zc(C["z_lateral"]); yl = C["cajon"]["y_laterales"]
    xy["J-T"] = (X["T"] * s, yT)
    dy = lambda y: yT + (0.5 - y) * 2 * s           # planta: lateral 1 arriba, lateral 2 abajo
    xy["J-CL"] = (X["T"] * s, dy(yl[0])); xy["J-CR"] = (X["T"] * s, dy(yl[1]))
    for i, (lat, yy) in enumerate([("1", yl[0]), ("2", yl[1])]):
        a, b = ("T-E1", "T-E2") if lat == "1" else ("T-E3", "T-E4")
        ea, eb = ("E1", "E2") if lat == "1" else ("E3", "E4")
        xy[a] = (X["E_A"] * s, dy(yy)); xy[b] = (X["E_B"] * s, dy(yy))
        xy[ea] = (X["E_A"] * s, dy(yy) + 150); xy[eb] = (X["E_B"] * s, dy(yy) + 150)
        xy["TAP" + lat] = (X["tapon_fin"] * s + 120, dy(yy))
    return xy, {}


def coords_presentacion():
    """Vista esquematica legible: cadena principal horizontal y cajon a la derecha."""
    xy = {"R1": (0, 0), "J-TK": (1600, 0), "J-CHK": (3800, 0), "J-C1": (5200, 0), "J-C2": (5200, -2000),
          "J-PIN": (6800, -2000), "J-POUT": (9400, -2000), "J-FLOW": (11000, -2000), "J-FLOW2": (13000, -2000),
          "J-EV1": (14400, -2000), "J-EV2": (16400, -2000), "J-R1": (21600, -2000), "J-R2": (21600, 0),
          "J-T": (24200, 0), "J-CL": (24200, 3000), "J-CR": (24200, -3000),
          "T-E1": (26200, 3000), "T-E2": (31200, 3000), "TAP1": (33200, 3000),
          "T-E3": (26200, -3000), "T-E4": (31200, -3000), "TAP2": (33200, -3000),
          "E1": (26200, 4200), "E2": (31200, 4200), "E3": (26200, -1800), "E4": (31200, -1800)}
    return xy, {}


LABELS_PRES = [  # (x, y, texto)  ancla = esquina superior izquierda (EPANET)
    (-1300, 1500, "TINACO (R1)"),
    (2200, 1500, "CHECK 1/2in (CHK)"),
    (5600, -700, "BAJADA"),
    (6600, -2600, "BOMBA 12 V (PU1)"),
    (10600, -1100, "YF-S201 (YF)"),
    (13600, -2600, "ELECTROVALVULA NC (EV)"),
    (16600, -1100, "LINEA PRINCIPAL"),
    (21900, -800, "SUBIDA"),
    (19600, 1400, "CAJON - T (J-T)"),
    (26900, 3750, "LATERAL 1 (L1)"),
    (26900, -2250, "LATERAL 2 (L2)"),
    (25500, 5200, "SD-B E1"), (30500, 5200, "SD-B E2"),
    (25500, -3500, "SD-B E3"), (30500, -3500, "SD-B E4"),
    (24400, 6600, "4 MICROASPERSORES SD-B (PROVISIONAL)"),
]


def cobertura(r, n=1001):
    """Fraccion del cajon (planta) a distancia <= r de algun aspersor; distancia maxima al mas cercano."""
    import numpy as np
    yl = C["cajon"]["y_laterales"]; xa = C["cajon"]["x_aspersores"]
    pts = [(x, y) for y in yl for x in xa]
    g = np.linspace(0, C["cajon"]["largo"], n); Xg, Yg = np.meshgrid(g, np.linspace(0, C["cajon"]["ancho"], n))
    d = np.min([np.hypot(Xg - a, Yg - b) for a, b in pts], axis=0)
    dmax = float(d.max())
    peores = sorted({(round(float(Xg.flat[i]), 3), round(float(Yg.flat[i]), 3)) for i in np.where(d.ravel() > dmax - 1e-9)[0]})
    return {"r": r, "cubierto": float((d <= r).mean()), "dmax": dmax, "puntos_dmax": peores,
            "traslape2": float((sum((np.hypot(Xg - a, Yg - b) <= r).astype(int) for a, b in pts) >= 2).mean())}


def nota_tabla_hunter(p_bar, emisores=True):
    """Clasifica el caudal de un aspersor segun la tabla OFICIAL Hunter (1.0-2.0 bar)."""
    if not emisores:
        return "DEMANDA FIJA (caudal impuesto, no emisor)"
    lo, hi = min(t[0] for t in C["aspersor"]["tabla_bar_Lh_diam_m"]), max(t[0] for t in C["aspersor"]["tabla_bar_Lh_diam_m"])
    if p_bar > hi + 1e-9:
        return f"EXTRAPOLACION DEL MODELO (P > {hi} bar: fuera de la tabla oficial Hunter; NO es dato Hunter)"
    if p_bar < lo - 1e-9:
        return f"EXTRAPOLACION DEL MODELO (P < {lo} bar: fuera de la tabla oficial Hunter)"
    return "dentro de la tabla oficial Hunter (interpolado por el ajuste Q=C*P^n)"


def presion_para_radio(r):
    """Interpolacion LINEAL de la tabla OFICIAL Hunter (diametro de mojado en maximo ajuste vs presion).
    No es un dato del fabricante: es un valor CALCULADO dentro del rango de la tabla (si r esta dentro)."""
    tab = sorted(C["aspersor"]["tabla_bar_Lh_diam_m"], key=lambda t: t[2])
    D = 2 * r
    for (p0, q0, d0), (p1, q1, d1) in zip(tab, tab[1:]):
        if d0 <= D <= d1:
            p = p0 + (D - d0) / (d1 - d0) * (p1 - p0)
            return {"P_bar": p, "Q_tabla_Lh": q0 + (p - p0) / (p1 - p0) * (q1 - q0), "dentro_tabla": True}
    return {"P_bar": None, "Q_tabla_Lh": None, "dentro_tabla": False}


def escribir_inp(path, xy, labels, titulo_extra, emisores="fit", demanda_fija=False, headloss="D-W",
                 curva=None, overrides=None, backdrop=None, q_emisor=None):
    """emisores: 'fit' (n ajustado), '05' (n=0.5) o None (sin emisores). q_emisor: demanda fija por aspersor (L/s)."""
    ov = overrides or {}
    K = dict(C["K"]); K.update(ov.get("K", {}))
    T = "\t"
    rough = (lambda m: C["tubo"]["rug_mm"]) if headloss == "D-W" else (lambda m: C["tubo"]["C_HW"])
    L = []
    w = L.append
    w("[TITLE]")
    w("Riego huerto v2 - 1 cajon 1x1 m - 2 laterales - 4 microaspersores Hunter SD-B (PROVISIONAL)")
    w("Tuboplus 20 mm C16 DI 14.40 mm (OFICIAL). Curva de bomba PROVISIONAL. Tinaco ORIGINAL PROVISIONAL.")
    w(titulo_extra)
    w("")
    w("[JUNCTIONS]")
    w(";ID              \tElev (m)\tDemand (L/s)\tPattern")
    for n, (z, desc) in NODES.items():
        dem = (q_emisor or Q_E) if (demanda_fija and n in EMISORES) else 0.0
        w(f" {n:<16s}{T}{z:.3f}{T}{dem:.8f}{T}{T};{desc}")
    w("")
    w("[RESERVOIRS]")
    w(";ID              \tHead (m)\tPattern")
    zr = ov.get("z_agua", C["tinaco"]["z_agua_max"])
    w(f" R1              {T}{zr:.3f}{T}{T};TINACO ORIGINAL PROVISIONAL - nivel de agua (z sobre tierra del huerto)")
    w("")
    w("[TANKS]")
    w("")
    w("[PIPES]")
    w(";ID              \tNode1           \tNode2           \tLength (m)\tDiam (mm)\tRoughness\tMinorLoss\tStatus")
    for lid, a, b, Lm, D, k, st, mat, desc in LINKS:
        k = ov.get("Klink", {}).get(lid, k)
        if lid == "CHK": k = K["check"]
        if lid == "YF": k = K["yfs201"]
        if lid == "EV": k = ov.get("K_EV", K_EV)
        w(f" {lid:<16s}{T}{a:<16s}{T}{b:<16s}{T}{Lm:.4f}{T}{D:.2f}{T}{rough(mat)}{T}{k:.4f}{T}{st}{T};{desc}")
    w("")
    w("[PUMPS]")
    w(";ID              \tNode1           \tNode2           \tParameters")
    w(f" PU1             {T}J-PIN           {T}J-POUT          {T}HEAD PUMP_CURVE_PROVISIONAL{T};BOMBA GOOD PUMPS 12 V (curva NO certificada)")
    w("")
    w("[VALVES]")
    w("; Sin valvulas de control: la check es una Pipe con Status CV (CHK) y la electrovalvula una Pipe ON/OFF (EV)")
    w("")
    w("[TAGS]")
    w(" LINK \tCHK\tVALVULA_CHECK\n LINK \tPU1\tBOMBA_12V\n LINK \tYF\tYF-S201\n LINK \tEV\tELECTROVALVULA_NC")
    for e in EMISORES:
        w(f" NODE \t{e}\tHUNTER_SD-B_PROVISIONAL")
    w("")
    w("[DEMANDS]")
    w("")
    w("[STATUS]")
    w(" EV              \tOPEN\t;Electrovalvula ABIERTA - escenario RIEGO")
    w(" PU1             \tOPEN\t;Bomba ENCENDIDA - escenario RIEGO")
    w("")
    w("[PATTERNS]")
    w("")
    w("[CURVES]")
    w(";ID              \tX-Value (L/s)\tY-Value (m)")
    w(";PUMP: PUMP_CURVE_PROVISIONAL - NO ES LA CURVA CERTIFICADA DEL FABRICANTE (ver DECISIONS.md)")
    for q, h in (curva or C["bomba_curva"]):
        w(f" PUMP_CURVE_PROVISIONAL\t{q:.4f}\t{h:.3f}")
    w("")
    w("[CONTROLS]\n\n[RULES]\n")
    w("[ENERGY]\n Global Efficiency  \t75\n Global Price       \t0\n Demand Charge      \t0\n")
    w("[EMITTERS]")
    w(";Junction        \tCoefficient (L/s / m^n)")
    n_exp = 0.5
    if emisores and not demanda_fija:
        cval = EM["C_fit"] if emisores == "fit" else EM["C_05"]
        n_exp = EM["n_fit"] if emisores == "fit" else 0.5
        for e in EMISORES:
            w(f" {e:<16s}{T}{cval:.8f}\t;SD-B PROVISIONAL maximo ajuste: 50 L/h a 1.5 bar (Hunter), n={n_exp:.4f}")
    w("")
    w("[QUALITY]\n\n[SOURCES]\n\n[REACTIONS]\n Order Bulk 1\n Order Tank 1\n Order Wall 1\n Global Bulk 0\n Global Wall 0\n")
    w("[MIXING]\n")
    w("[TIMES]\n Duration           \t0:00\n Hydraulic Timestep \t1:00\n Report Timestep    \t1:00\n Statistic          \tNONE\n")
    w("[REPORT]\n Status             \tYes\n Summary            \tNo\n Nodes              \tAll\n Links              \tAll\n")
    w("[OPTIONS]")
    w(" Units              \tLPS")
    w(f" Headloss           \t{headloss}")
    w(" Specific Gravity   \t1.0")
    w(" Viscosity          \t1.0")
    w(" Trials             \t100")
    w(" Accuracy           \t0.00001")
    w(" Unbalanced         \tStop")
    w(" Pattern            \t1")
    w(" Demand Multiplier  \t1.0")
    w(f" Emitter Exponent   \t{n_exp:.4f}")
    w(" Quality            \tNone mg/L")
    w(" Demand Model       \tDDA")
    w("")
    w("[COORDINATES]")
    w(";Node            \tX-Coord         \tY-Coord")
    for n, (x, y) in xy.items():
        w(f" {n:<16s}\t{x:.2f}\t{y:.2f}")
    w("")
    w("[VERTICES]")
    w("")
    w("[LABELS]")
    for x, y, t in labels:
        w(f" {x:.2f}\t{y:.2f}\t\"{t}\"")
    w("")
    w("[BACKDROP]")
    if backdrop:
        w(f" DIMENSIONS\t{backdrop[0]:.2f}\t{backdrop[1]:.2f}\t{backdrop[2]:.2f}\t{backdrop[3]:.2f}")
    w(" UNITS\tNone\n OFFSET\t0.00\t0.00\n")
    w("[END]")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return path


# =====================================================================================
# SIMULACION (EPyT / OWA-EPANET, doble precision)
# =====================================================================================
def simular(path):
    from epyt import epanet as ep
    import shutil
    # la libreria de EPyT no abre rutas con caracteres no ASCII ("Automatización"): se copia a temp
    tmp = os.path.join(tempfile.mkdtemp(), "modelo.inp"); shutil.copy(path, tmp)
    d = ep(tmp, display_msg=False, display_warnings=False)
    r = d.getComputedHydraulicTimeSeries()
    nid = d.getNodeNameID(); lid = d.getLinkNameID()
    out = {"nodes": {n: {"H": float(r.Head[0][i]), "P": float(r.Pressure[0][i]), "D": float(r.Demand[0][i]),
                         "z": float(d.getNodeElevations()[i])} for i, n in enumerate(nid)},
           "links": {l: {"Q": float(r.Flow[0][i]), "V": float(r.Velocity[0][i]), "hl": float(r.HeadLoss[0][i]),
                         "st": float(r.Status[0][i])} for i, l in enumerate(lid)},
           "version": str(d.getVersion())}
    d.unload()
    return out


def tmp_inp(**kw):
    p = os.path.join(tempfile.mkdtemp(), "esc.inp")
    xy, _ = coords_final()
    escribir_inp(p, xy, [], "ESCENARIO", **kw)
    return p


# =====================================================================================
# CALCULOS MANUALES (Darcy-Weisbach / Hazen-Williams) por tramo
# =====================================================================================
def f_dw(Re, D, eps):
    if Re < 2000:
        return 64 / Re, "laminar (64/Re)"
    fs = 0.25 / math.log10(eps / (3.7 * D) + 5.74 / Re**0.9) ** 2
    f = fs
    for _ in range(60):
        f = (-2 * math.log10(eps / (3.7 * D) + 2.51 / (Re * math.sqrt(f)))) ** -2
    if Re < 4000:
        return f, "transicion (Colebrook, cota)"
    return f, "turbulento (Colebrook)"


def hw(L, Q, D, Cc):
    return 10.67 * L * Q**1.852 / (Cc**1.852 * D**4.87)


def calculos_por_tramo(res):
    """Usa los caudales EPANET del escenario final para el calculo manual independiente."""
    rows = []
    eps = C["tubo"]["rug_mm"] / 1000
    for lid, a, b, Lm, Dmm, k, st, mat, desc in LINKS:
        Q = abs(res["links"][lid]["Q"]) / 1000
        D = Dmm / 1000; A = math.pi * D**2 / 4; V = Q / A if A else 0
        Re = C["rho"] * V * D / C["mu"]
        if Q <= 0:
            rows.append(dict(id=lid, desc=desc, mat=mat, L=Lm, D=Dmm, A=A, Q=0, V=0, Re=0, reg="sin flujo", f=0,
                             hf=0, hm=0, ht=0, hw150=0, K=k, epanet=res["links"][lid]["hl"]))
            continue
        f, reg = f_dw(Re, D, eps)
        hv = V**2 / (2 * C["g"])
        hf = f * Lm / D * hv
        kk = {"CHK": C["K"]["check"], "YF": C["K"]["yfs201"], "EV": K_EV}.get(lid, k)
        hm = kk * hv
        rows.append(dict(id=lid, desc=desc, mat=mat, L=Lm, D=Dmm, A=A, Q=Q * 1000, V=V, Re=Re, reg=reg, f=f,
                         hf=hf, hm=hm, ht=hf + hm, hw150=hw(Lm, Q, D, C["tubo"]["C_HW"]) + hm, K=kk,
                         epanet=res["links"][lid]["hl"]))
    return rows


# =====================================================================================
# MAIN
# =====================================================================================
def main():
    os.makedirs(os.path.join(HERE, "capturas_epanet"), exist_ok=True)
    xy, _ = coords_final()
    f_final = escribir_inp(os.path.join(HERE, "riego_huerto_v2_final.inp"), xy, [],
                           "ESCENARIO BASE: emisores (n ajustado a Hunter), Darcy-Weisbach eps=0.007 mm, tinaco lleno")
    xyp, _ = coords_presentacion()
    f_pres = escribir_inp(os.path.join(HERE, "riego_huerto_v2_presentacion.inp"), xyp, LABELS_PRES,
                          "PRESENTACION: misma hidraulica que riego_huerto_v2_final.inp (solo cambian coordenadas y etiquetas)",
                          backdrop=(-2500, -4800, 36000, 7400))
    base = simular(f_final)

    # ---------- escenarios ----------
    esc = {}
    def run(name, desc, **kw):
        r = simular(tmp_inp(**kw)); esc[name] = (desc, r); return r
    esc["S0_base"] = ("BASE: emisores n ajustado, D-W, tinaco lleno, curva provisional", base)
    run("S1_n05", "Emisores con n=0.5 (SUPUESTO orificio)", emisores="05")
    fija = run("S2_demanda_fija", "Demanda FIJA 50 L/h por aspersor (diseno), sin emisores", emisores=None, demanda_fija=True)
    run("S3_HW150", "Hazen-Williams C=150 (comparacion)", headloss="H-W")
    run("S4_tinaco_min", "Tinaco casi vacio (agua en +0.30 m)", overrides={"z_agua": C["tinaco"]["z_agua_min"]})
    for fac in (0.25, 0.40, 0.50, 0.75):
        run(f"S5_curva_x{fac:.2f}", f"Curva provisional con alturas x{fac:.2f}",
            curva=[(q, h * fac) for q, h in C["bomba_curva"]])
    for kc in (1.5, 8.0, 16.2):
        run(f"S6_check_K{kc}", f"Check K={kc}", overrides={"K": {"check": kc}})
    for ky in (0.0, 5.0, 10.0, 20.0):
        run(f"S7_yfs201_K{ky}", f"YF-S201 K={ky}", overrides={"K": {"yfs201": ky}})
    for kv in (1.0, 2.0, 6.0):
        run(f"S8_EV_Kv{kv}", f"Electrovalvula Kv={kv} m3/h (K={kv_to_K(kv, Q_TOT, DI):.1f})",
            overrides={"K_EV": kv_to_K(kv, Q_TOT, DI)})

    # ---------- altura requerida de bomba en el punto de diseno (de la corrida con demanda fija) ----------
    Pd = EM["P_diseno_m"]
    H_pin = fija["nodes"]["J-PIN"]["H"]; H_pout = fija["nodes"]["J-POUT"]["H"]
    per_up = C["tinaco"]["z_agua_max"] - H_pin
    crit = min(EMISORES, key=lambda e: fija["nodes"][e]["H"])
    per_down = H_pout - fija["nodes"][crit]["H"]
    H_req = (NODES[crit][0] + Pd) - C["tinaco"]["z_agua_max"] + per_up + per_down
    req = {"Q_Ls": Q_TOT, "H_req_m": H_req, "per_succion": per_up, "per_descarga": per_down, "critico": crit,
           "dz": NODES[crit][0] - C["tinaco"]["z_agua_max"], "Pd_m": Pd}

    # ---------- escenario de COBERTURA (radio objetivo ~0.36 m) ----------
    to_m = lambda bar: bar * 1e5 / (C["rho"] * C["g"])
    r_obj = C["cobertura"]["radio_objetivo_m"]
    pc = presion_para_radio(r_obj)
    cov = {"r_deseado": cobertura(C["cobertura"]["radio_deseado_m"]), "r_objetivo": cobertura(r_obj),
           "interp": pc}
    if pc["dentro_tabla"]:
        Pm = to_m(pc["P_bar"]); q_cov = EM["C_fit"] * Pm ** EM["n_fit"]          # L/s por aspersor (ajuste)
        fc = run("S9_cobertura_r036_fija", f"COBERTURA r={r_obj} m: demanda fija {q_cov * 3600:.1f} L/h por aspersor "
                 f"(P interpolada {pc['P_bar']:.2f} bar)", emisores=None, demanda_fija=True, q_emisor=q_cov)
        crit_c = min(EMISORES, key=lambda e: fc["nodes"][e]["H"])
        H_req_c = (NODES[crit_c][0] + Pm) - C["tinaco"]["z_agua_max"] + (C["tinaco"]["z_agua_max"] - fc["nodes"]["J-PIN"]["H"]) \
            + (fc["nodes"]["J-POUT"]["H"] - fc["nodes"][crit_c]["H"])
        lo, hi = 0.25, 1.0                                                            # escala de la curva provisional
        for _ in range(40):
            mid = (lo + hi) / 2
            r_ = simular(tmp_inp(curva=[(q, h * mid) for q, h in C["bomba_curva"]]))
            if min(r_["nodes"][e]["P"] for e in EMISORES) < Pm: lo = mid
            else: hi = mid
        run("S10_cobertura_r036_curva", f"COBERTURA r={r_obj} m: curva provisional x{hi:.3f} (emisores a ~{pc['P_bar']:.2f} bar)",
            curva=[(q, h * hi) for q, h in C["bomba_curva"]])
        cov.update({"P_m": Pm, "q_emisor_Lh_ajuste": q_cov * 3600, "Q_total_Ls": 4 * q_cov, "H_req_m": H_req_c,
                    "escala_curva": hi})

    # ---------- salidas ----------
    rows = calculos_por_tramo(base)
    with open(os.path.join(HERE, "resultados_epanet.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["tipo", "id", "descripcion", "elev_m", "head_m", "presion_m", "presion_bar", "demanda_o_emisor_Ls",
                     "caudal_Ls", "caudal_Lh", "velocidad_ms", "headloss_m", "estado", "nota"])
        for n, v in base["nodes"].items():
            desc = NODES.get(n, (0, "TINACO R1"))[1]
            wr.writerow(["nodo", n, desc, f"{v['z']:.3f}", f"{v['H']:.4f}", f"{v['P']:.4f}",
                         f"{v['P'] * C['rho'] * C['g'] / 1e5:.4f}", f"{v['D']:.6f}", "", f"{v['D'] * 3600:.2f}" if n in EMISORES else "", "", "", "",
                         nota_tabla_hunter(v['P'] * C['rho'] * C['g'] / 1e5) if n in EMISORES else ""])
        for l, v in base["links"].items():
            desc = next((x[8] for x in LINKS if x[0] == l), "BOMBA PU1 (curva provisional)")
            wr.writerow(["enlace", l, desc, "", "", "", "", "", f"{v['Q']:.6f}", f"{v['Q'] * 3600:.2f}",
                         f"{v['V']:.4f}", f"{v['hl']:.5f}", {0: "CERRADO", 1: "ABIERTO"}.get(int(v['st']), str(v['st'])), ""])
    with open(os.path.join(HERE, "escenarios_sensibilidad.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["escenario", "descripcion", "Q_total_Ls", "Q_total_Lmin", "Q_L1_Ls", "Q_L2_Ls"] +
                    [f"Q_{e}_Lh" for e in EMISORES] + [f"P_{e}_m" for e in EMISORES] + [f"P_{e}_bar" for e in EMISORES] +
                    ["H_bomba_m", "P_succion_m", "V_principal_ms", "nota_caudal_aspersor"])
        for k, (desc, r) in esc.items():
            Ld = r["links"]; N = r["nodes"]
            wr.writerow([k, desc, f"{Ld['T-F']['Q']:.5f}", f"{Ld['T-F']['Q'] * 60:.3f}", f"{Ld['BR-L']['Q']:.5f}", f"{Ld['BR-R']['Q']:.5f}"] +
                        [f"{Ld['RE' + e[1]]['Q'] * 3600:.2f}" for e in EMISORES] +
                        [f"{N[e]['P']:.3f}" for e in EMISORES] +
                        [f"{N[e]['P'] * C['rho'] * C['g'] / 1e5:.3f}" for e in EMISORES] +
                        [f"{N['J-POUT']['H'] - N['J-PIN']['H']:.3f}", f"{N['J-PIN']['P']:.3f}", f"{Ld['T-F']['V']:.4f}",
                         nota_tabla_hunter(max(N[e]['P'] for e in EMISORES) * C['rho'] * C['g'] / 1e5,
                                           emisores=not k.startswith(("S2_", "S9_")))])
    # tabla de cortes
    tub = sum(v for k, v in CUT.items())
    with open(os.path.join(HERE, "tabla_cortes_tuboplus.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["corte", "descripcion", "cantidad", "longitud_corte_m", "subtotal_m", "tubo_4m_asignado", "enlace_EPANET", "longitud_EPANET_cc_m", "nota"])
        plan = [("A_salida_check_codo", "Conector macho (rosca a check) -> codo 90 sup.", 1, 1, "T-A"),
                ("B_bajada_vertical", "Bajada vertical codo-codo", 1, 1, "T-B"),
                ("C_codo_a_bomba", "Codo inferior -> union mixta de succion", 1, 1, "T-C"),
                ("D_bomba_a_yfs201", "Union mixta descarga -> conector hembra YF-S201", 1, 1, "T-D"),
                ("E_yfs201_a_valvula", "Conector YF-S201 -> conector electrovalvula", 1, 1, "T-E"),
                ("F_linea_principal", "Conector electrovalvula -> codo de subida", 1, 1, "T-F"),
                ("G_subida_vertical", "Subida vertical codo-codo", 1, 1, "T-G"),
                ("H_codo_a_T", "Codo superior -> T centrada (derivacion)", 1, 1, "T-H"),
                ("I_brazo", "Brazo T -> codo (izq. y der.)", 2, 2, "BR-L/BR-R"),
                ("J_codo_a_aspersor_A", "Codo -> tee aspersor A (L1 y L2)", 2, 2, "L1-A/L2-A"),
                ("K_aspersor_A_a_B", "Tee aspersor A -> tee aspersor B (L1 y L2)", 2, 2, "L1-B/L2-B"),
                ("L_niple_tapon", "Niple tee aspersor B -> tapon (L1 y L2)", 2, 2, "L1-T/L2-T")]
        total = 0
        for key, desc, n, tubo, lk in plan:
            sub = CUT[key] * n; total += sub
            lcc = {"T-A": LK["T-A"], "T-B": LK["T-B"], "T-C": LK["T-C"], "T-D": LK["T-D"], "T-E": LK["T-E"], "T-F": LK["T-F"],
                   "T-G": LK["T-G"], "T-H": LK["T-H"], "BR-L/BR-R": LK["BRAZO"], "L1-A/L2-A": LK["LAT-A"],
                   "L1-B/L2-B": LK["LAT-B"], "L1-T/L2-T": LK["TAPON"]}[lk]
            wr.writerow([key, desc, n, f"{CUT[key]:.3f}", f"{sub:.3f}", f"Tubo {tubo}", lk, f"{lcc:.4f}",
                         "corte incluye 2 x insercion (p=15-16 mm) en sockets"])
        t1 = sum(CUT[k] for k, _, n, tb, _ in plan if tb == 1); t2 = sum(CUT[k] * n for k, _, n, tb, _ in plan if tb == 2)
        wr.writerow([]); wr.writerow(["TOTAL", "Tuboplus 20 mm C16 utilizado", "", "", f"{total:.3f}", "", "", "", ""])
        wr.writerow(["Tubo 1", "4.00 m", "", "", f"{t1:.3f}", f"sobrante {4 - t1:.3f} m", "", "", ""])
        wr.writerow(["Tubo 2", "4.00 m", "", "", f"{t2:.3f}", f"sobrante {4 - t2:.3f} m", "", "", ""])
        wr.writerow(["LIMITE", "maximo 8.00 m / objetivo 7.50 m", "", "", f"margen {8 - total:.3f} m", "OK" if total <= 7.5 else "REVISAR", "", "", ""])
    corte_total = sum(CUT[k] * n for k, _, n, _, _ in plan)

    # tablas para calculos
    json.dump({"EM": {k: v for k, v in EM.items()}, "K_EV": K_EV, "CUT": CUT, "X": X, "LK": LK, "req": req, "cobertura": cov,
               "rows": rows, "tuboplus_total": corte_total, "base": base,
               "esc": {k: {"desc": d, "links": {l: r["links"][l] for l in ("T-F", "BR-L", "BR-R", "RE1", "RE2", "RE3", "RE4", "PU1")},
                           "nodes": {n: r["nodes"][n] for n in ("J-PIN", "J-POUT", "E1", "E2", "E3", "E4", "J-T")}}
                       for k, (d, r) in esc.items()}},
              open(os.path.join(HERE, "resultados_calculo.json"), "w"), indent=1, default=float)
    return base, esc, rows, req, corte_total


if __name__ == "__main__":
    base, esc, rows, req, tot = main()
    print(f"Tuboplus total = {tot:.3f} m | n_fit={EM['n_fit']:.4f} C_fit={EM['C_fit']:.6e} | K_EV={K_EV:.2f}")
    print(f"H requerida (diseno 1.5 bar, 200 L/h) = {req['H_req_m']:.3f} m")
    for k, (d, r) in esc.items():
        print(f"{k:22s} Q={r['links']['T-F']['Q']:.5f} L/s  P(E1..E4)=" +
              ", ".join(f"{r['nodes'][e]['P']:.2f}" for e in EMISORES) +
              "  Q(E) L/h=" + ", ".join(f"{r['links']['RE' + e[1]]['Q'] * 3600:.1f}" for e in EMISORES))
