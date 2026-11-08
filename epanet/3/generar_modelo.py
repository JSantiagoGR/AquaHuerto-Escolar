"""Generador PARAMETRICO del modelo EPANET v3 (correccion): cruz + 3 laterales de manguera x 3 aspersores = 9.

ESCENARIO GEOMETRICO A (DISENO PRINCIPAL / DESEADO): subida VERTICAL con codos de 90 deg, cruz arriba (z 1.52 m),
    brazos exteriores de Tuboplus con codos 90 deg, 3 lineas paralelas.
ESCENARIO GEOMETRICO B (ALTERNATIVA DE CONTINGENCIA): subida a 45 deg; solo si las MEDICIONES demuestran que A no
    cabe en el limite de compra de 4.00 m de Tuboplus nuevo.

La geometria se calcula desde la tabla CONFIG["medidas"]. Cada medida tiene un "estado" (ESTIMADO / MEDIDO).
Cuando se midan en sitio: cambiar "valor" y poner estado "MEDIDO", y ejecutar de nuevo:
    uv run --python 3.12 --with wntr --with epyt --with matplotlib python generar_modelo.py

Regenera: riego_huerto_v3_final.inp, riego_huerto_v3_presentacion.inp, tabla_cortes_tuboplus.csv,
alternativas_trazado.csv, mediciones_fisicas.csv, resultados_epanet.csv, escenarios_sensibilidad.csv,
calculos_resultados.md, resultados_calculo.json.
"""
import math, os, csv, json, re, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))

# =====================================================================================
# CONFIG
# =====================================================================================
CONFIG = {
    "rho": 998.2, "mu": 1.002e-3, "g": 9.81,                                    # agua 20 C   ESTIMADO

    # --- Tuboplus 20 mm (1/2") Clase 16, codigo 200224 ------------------------------ OFICIAL
    "tubo": {"di_mm": 14.40, "de_mm": 20.0, "e_mm": 2.80, "rug_mm": 0.007, "C_HW": 150, "limite_nuevo_m": 4.00},

    # --- Tinaco PROVISIONAL (cotas sobre la tierra del huerto, z = 0) ----------------- MEDIDO aprox.
    "tinaco": {"z_banqueta": 0.07, "z_base": 0.12, "z_fondo": 0.19, "z_agua_max": 1.19, "z_salida": 0.265, "z_agua_min": 0.30},

    # --- Escenario geometrico activo para el modelo final y la presentacion -------------
    "geometria_principal": "A",
    "geometrias": {
        "A":  {"subida": "vertical", "brazos": "tuboplus", "rol": "DISENO PRINCIPAL / DESEADO",
               "desc": "Subida VERTICAL (codos 90) + cruz + brazos Tuboplus con codos 90"},
        "A2": {"subida": "vertical", "brazos": "manguera", "rol": "variante",
               "desc": "Subida vertical + desvio de laterales exteriores con la manguera"},
        "B":  {"subida": "45", "brazos": "tuboplus", "rol": "ALTERNATIVA DE CONTINGENCIA",
               "desc": "Subida a 45 deg (2 codos 45) + brazos Tuboplus con codos 90"},
        "B2": {"subida": "45", "brazos": "manguera", "rol": "contingencia extrema",
               "desc": "Subida a 45 deg + desvio exterior con la manguera"},
    },

    # --- MEDICIONES FISICAS (editar 'valor' y poner estado 'MEDIDO' cuando se midan) ------------------
    # Convenciones: distancias horizontales en m; 'cara' = cara exterior de la conexion por donde entra el tubo.
    "medidas": {
        "M0_z_linea_principal": {"valor": 0.08, "estado": "ESTIMADO", "desc": "Altura del eje de la linea principal / pie de la bajada existente sobre la tierra",
                                 "como": "Flexometro desde la tierra del huerto al eje del tubo"},
        "M1_d_bajada_a_bomba": {"valor": 0.07, "estado": "ESTIMADO", "desc": "Horizontal: eje de la bajada existente (centro del codo nuevo) -> cara de la tuerca union de succion",
                                "como": "Presentar codo y conjunto bomba; medir del eje de la bajada a la cara de la union"},
        "M2_L_conjunto_bomba": {"valor": 0.295, "estado": "ESTIMADO", "desc": "Largo ocupado por bomba + 2 adaptadores + 2 uniones (cara union succion -> cara union descarga)",
                                "como": "Armar el conjunto en banco y medir"},
        "M3_L_conjunto_yf": {"valor": 0.136, "estado": "ESTIMADO", "desc": "Largo ocupado por YF-S201 + 2 conectores (cara a cara)", "como": "Armar y medir"},
        "M4_L_conjunto_ev": {"valor": 0.159, "estado": "ESTIMADO", "desc": "Largo ocupado por electrovalvula + 2 conectores (cara a cara)", "como": "Armar y medir"},
        "M4b_niples_entre_conjuntos": {"valor": 0.06, "estado": "ESTIMADO", "desc": "Corte de cada niple Tuboplus bomba->YF y YF->EV (2 niples)",
                                       "como": "Hueco visible deseado + 2 x 16 mm de insercion"},
        "M5_d_conjunto_a_subida": {"valor": 2.74, "estado": "ESTIMADO", "desc": "Horizontal: cara de salida del conjunto electrovalvula -> eje de la subida (centro del codo inferior)",
                                   "como": "Flexometro sobre el piso, en linea recta hacia el cajon"},
        "M6_z_superior_cajon": {"valor": 0.52, "estado": "ESTIMADO", "desc": "Altura del piso a la parte superior del cajon (base 0.12 + cajon 0.40)",
                                "como": "Flexometro"},
        "M7_h_cruz_sobre_cajon": {"valor": 1.00, "estado": "ESTIMADO", "desc": "Altura adicional del borde superior del cajon al eje de la cruz", "como": "Definir y medir"},
        "M8_d_superior_a_cruz": {"valor": 0.083, "estado": "ESTIMADO", "desc": "Horizontal arriba: eje de la subida -> eje de la cruz", "como": "Flexometro"},
        "M9_manguera_DI_mm": {"valor": 12.0, "estado": "ESTIMADO (NO MEDIDO)", "desc": "Diametro INTERIOR de la manguera negra", "como": "Vernier (puntas interiores)"},
        "M9b_manguera_DE_mm": {"valor": 16.0, "estado": "ESTIMADO (NO MEDIDO)", "desc": "Diametro EXTERIOR de la manguera negra", "como": "Vernier"},
        "M10_rosca_bomba": {"valor": "3/8\" (NPT o BSP sin confirmar); OD 16-17 mm medido", "estado": "PENDIENTE",
                            "desc": "Diametro, paso y tipo de rosca de los puertos de la bomba", "como": "Galga de roscas / hilos por pulgada (NPT 18, BSP 19)"},
        "M11_y_lineas": {"valor": (0.17, 0.50, 0.83), "estado": "ESTIMADO", "desc": "Posicion de las 3 lineas a lo ancho del cajon (m)", "como": "Medir sobre el cajon"},
        "M11b_x_aspersores": {"valor": (0.17, 0.50, 0.83), "estado": "ESTIMADO", "desc": "Posicion de los 3 aspersores a lo largo de cada linea (m)", "como": "Medir"},
        "M12_L_lineas": {"valor": None, "estado": "ESTIMADO (calculada)", "desc": "Longitud real de cada linea de manguera (None = calculada)", "como": "Medir cada manguera cortada"},
        "X_borde_cajon": {"valor": 4.00, "estado": "ESTIMADO", "desc": "Distancia horizontal salida del tinaco -> borde del cajon (referencia)", "como": "Flexometro"},
    },
    "x_tapon_tras_ultimo": 0.10,

    # --- Manguera negra (laterales) ------------------------------------------------------- PROVISIONAL
    "manguera": {"id_sensibilidad_mm": (10.0, 12.0, 14.0), "rug_mm": 0.007, "radio_curva_m": 0.12, "K_curva": 0.30,
                 "espiga_menos_id_mm": 3.0},

    # --- Aspersores reales (marca/modelo NO identificados) ---------------------------------- PROVISIONAL
    # NO se conoce la relacion apertura (%) - caudal; los escenarios son caudales impuestos, no aperturas.
    "aspersor": {"Q_max_Lh": 70.0, "Q_nominal_Lh": 30.0, "Q_escenarios_Lh": (20.0, 25.0, 30.0, 35.0, 40.0, 70.0),
                 "D_conexion_mm": 4.0, "L_conexion_m": 0.03, "K_conexion": 1.0, "z_sobre_lateral": 0.0},

    # --- Bomba GOOD PUMPS 12 V 72 W ---------------------------------------------------------- PROVISIONAL
    "bomba_curva": [(0.000, 91.91), (0.050, 45.96), (0.100, 0.00)],    # NO publicada: 6 L/min a H~0 y corte 0.9 MPa a Q~0
    "bomba_corte_MPa": 0.9, "bomba_Qmax_Lmin": 6.0, "D_puerto_bomba_mm": 7.0, "L_adaptador_bomba": 0.035,
    "L_bomba_puertos": 0.165, "L_yfs201": 0.062, "L_electrovalvula": 0.085,

    # --- K (sobre la velocidad del enlace) ----------------------------------------------------
    "K": {"codo90": 2.00, "codo45": 0.60, "conector": 0.40,                                  # OFICIAL Tuboplus Tabla 10
          "cruz_recto": 1.80, "cruz_lateral": 2.20, "T_existente": 1.80,                    # PROVISIONAL (proxies de tee)
          "entrada_tinaco": 0.50, "bola": 0.08, "check": 2.70,                              # ESTIMADO (Crane TP-410)
          "yfs201": 2.00, "adapt_bomba_in": 0.50, "adapt_bomba_out": 1.00, "espiga": 0.50}, # ESTIMADO
    "Kv_electrovalvula": 3.0, "D_yfs201_mm": 11.0,

    # --- Instalacion existente (no cuenta en el limite) ------------------------------------------ ESTIMADO
    "L_existente": {"niple": 0.04, "bola": 0.06, "check": 0.055, "tubo_a_T": 0.15},

    # --- Conexiones Tuboplus 20 mm (catalogo oficial): (L, p) en mm ------------------------------ OFICIAL
    "fit": {"codo90": (27, 15), "codo45": (20, 15), "cruz": (27, 16), "conector": (53, 16), "union_mixta": (46, 16)},
    "niple_cruz_conector": 0.04,                                                               # ESTIMADO
}
C = CONFIG
M = {k: v["valor"] for k, v in C["medidas"].items()}
DI = C["tubo"]["di_mm"] / 1000
Z_LINEA = M["M0_z_linea_principal"]
Z_LAT = M["M6_z_superior_cajon"] + M["M7_h_cruz_sobre_cajon"]                # 1.52 m
Z_ASP = Z_LAT + C["aspersor"]["z_sobre_lateral"]
Y_LAT, X_ASP = M["M11_y_lineas"], M["M11b_x_aspersores"]
NLAT, NASP = len(Y_LAT), len(X_ASP)
ASP = [f"A{i + 1}{j + 1}" for i in range(NLAT) for j in range(NASP)]


def toma(f):
    L, p = C["fit"][f]; return (L - p) / 1000


def pins(f):
    return C["fit"][f][1] / 1000


def kv_to_K(Kv, D_m):
    A = math.pi * D_m**2 / 4
    return 2 * C["g"] * (3.6 / Kv) ** 2 * 1e5 / (C["rho"] * C["g"]) * (A * 1000) ** 2


K_EV = kv_to_K(C["Kv_electrovalvula"], DI)


# =====================================================================================
# GEOMETRIA desde MEDIDAS
# =====================================================================================
def geometria(gid):
    g = C["geometrias"][gid]; vert = g["subida"] == "vertical"; brazos_tp = g["brazos"] == "tuboplus"
    E = C["L_existente"]; me = C["medidas"]
    dz = Z_LAT - Z_LINEA
    sep = Y_LAT[1] - Y_LAT[0]
    tc, t45, tx, tcon = toma("codo90"), toma("codo45"), toma("cruz"), toma("conector")
    codo_sub = "codo90" if vert else "codo45"; ts = toma(codo_sub)
    X = {}
    X["T_existente"] = E["niple"] + E["bola"] + E["check"] + tcon + E["tubo_a_T"]   # eje de la bajada existente
    X["union_suc"] = X["T_existente"] + M["M1_d_bajada_a_bomba"]
    X["bomba_in"] = X["union_suc"] + (toma("union_mixta") + C["L_adaptador_bomba"])
    X["bomba_out"] = X["bomba_in"] + C["L_bomba_puertos"]
    X["union_des"] = X["union_suc"] + M["M2_L_conjunto_bomba"]
    X["yf_in"] = X["union_des"] + M["M4b_niples_entre_conjuntos"] - 2 * 0.016
    X["yf_out"] = X["yf_in"] + M["M3_L_conjunto_yf"]
    X["ev_in"] = X["yf_out"] + M["M4b_niples_entre_conjuntos"] - 2 * 0.016
    X["ev_out"] = X["ev_in"] + M["M4_L_conjunto_ev"]
    X["subida"] = X["ev_out"] + M["M5_d_conjunto_a_subida"]            # eje de la subida (vertical) / fin de subida (45)
    X["cruz"] = X["subida"] + M["M8_d_superior_a_cruz"]
    X["sube_ini"] = X["subida"] if vert else X["subida"] - dz
    # --- tramos de Tuboplus: (clave, descripcion, distancia de referencia, estado de la medida, restas, sumas, corte)
    T = []
    def tramo(k, d, dist, est, resta, suma, n=1):
        corte = (dist - resta + suma) * n
        T.append({"tramo": k, "descripcion": d, "distancia_m": dist, "estado": est, "resta_conexiones_m": resta,
                  "suma_inserciones_m": suma, "cantidad": n, "corte_neto_m": round(corte, 4)})
    tramo("A", "Eje bajada (codo nuevo 90) -> union mixta succion", M["M1_d_bajada_a_bomba"], me["M1_d_bajada_a_bomba"]["estado"],
          tc, pins("union_mixta"))
    tramo("B", "Niple bomba -> YF-S201", M["M4b_niples_entre_conjuntos"], me["M4b_niples_entre_conjuntos"]["estado"], 0, 0)
    tramo("C", "Niple YF-S201 -> electrovalvula", M["M4b_niples_entre_conjuntos"], me["M4b_niples_entre_conjuntos"]["estado"], 0, 0)
    if vert:
        tramo("D", "Linea principal: conector EV -> codo 90 inferior de la subida", M["M5_d_conjunto_a_subida"],
              me["M5_d_conjunto_a_subida"]["estado"], tc, pins("conector"))
        tramo("E", f"Subida VERTICAL {Z_LINEA:.2f} -> {Z_LAT:.2f} m (codo 90 - codo 90)", dz,
              f"{me['M6_z_superior_cajon']['estado']} + {me['M7_h_cruz_sobre_cajon']['estado']}", 2 * tc, 0)
    else:
        tramo("D", "Linea principal: conector EV -> codo 45 inferior", M["M5_d_conjunto_a_subida"] - dz,
              me["M5_d_conjunto_a_subida"]["estado"], t45, pins("conector"))
        tramo("E", f"Subida a 45 deg {Z_LINEA:.2f} -> {Z_LAT:.2f} m", dz * math.sqrt(2),
              f"{me['M6_z_superior_cajon']['estado']} + {me['M7_h_cruz_sobre_cajon']['estado']}", 2 * t45, 0)
    tramo("H", "Codo superior -> cruz", M["M8_d_superior_a_cruz"], me["M8_d_superior_a_cruz"]["estado"], ts + tx, 0)
    if brazos_tp:
        tramo("I", "Brazos cruz -> codo 90 (laterales exteriores)", sep, me["M11_y_lineas"]["estado"], tx + tc, 0, n=2)
    tramo("N", "Niples cruz/codo -> conector hembra (1 por linea)", C["niple_cruz_conector"], "ESTIMADO", 0, 0, n=3)
    total = round(sum(t["corte_neto_m"] for t in T), 3)
    medido = all("MEDIDO" == C["medidas"][k]["estado"] for k in ("M1_d_bajada_a_bomba", "M4b_niples_entre_conjuntos",
                                                                 "M5_d_conjunto_a_subida", "M6_z_superior_cajon",
                                                                 "M7_h_cruz_sobre_cajon", "M8_d_superior_a_cruz", "M11_y_lineas"))
    codos = {"codo90": 1 + (2 if vert else 0) + (2 if brazos_tp else 0), "codo45": 0 if vert else 2}
    LK = {"A": M["M1_d_bajada_a_bomba"] + toma("union_mixta"), "B": toma("union_mixta") + M["M4b_niples_entre_conjuntos"] + tcon,
          "C": 2 * tcon + M["M4b_niples_entre_conjuntos"],
          "D": (X["sube_ini"] - X["ev_out"]) + tcon, "E": dz if vert else dz * math.sqrt(2), "H": M["M8_d_superior_a_cruz"],
          "K_D": C["K"]["conector"] + C["K"][codo_sub], "K_E": C["K"][codo_sub]}
    return {"id": gid, **g, "X": X, "tramos": T, "nuevo_m": total, "estado_total": "MEDIDO" if medido else "ESTIMADO",
            "cumple": total <= C["tubo"]["limite_nuevo_m"], "margen_m": round(C["tubo"]["limite_nuevo_m"] - total, 3),
            "codos": codos, "LK": LK, "dz": dz, "sep": sep, "brazos_tp": brazos_tp, "vertical": vert,
            # maximo de (M1 + M5) que permitiria cumplir el limite manteniendo el resto de medidas
            "M1_M5_max_m": round(M["M1_d_bajada_a_bomba"] + M["M5_d_conjunto_a_subida"] + (C["tubo"]["limite_nuevo_m"] - total), 3)}


GEOS = {k: geometria(k) for k in C["geometrias"]}
GEO = GEOS[C["geometria_principal"]]


# =====================================================================================
# RED
# =====================================================================================
def red(q_asp_Lh=None, D_hose_mm=None, Kov=None, gid=None):
    geo = GEOS[gid or C["geometria_principal"]]
    K = dict(C["K"]); K.update(Kov or {})
    q = (q_asp_Lh if q_asp_Lh is not None else C["aspersor"]["Q_nominal_Lh"]) / 3600
    Dh = D_hose_mm or M["M9_manguera_DI_mm"]; Desp = Dh - C["manguera"]["espiga_menos_id_mm"]
    t = C["tinaco"]; zb = Z_LINEA; d = C["tubo"]["di_mm"]; E = C["L_existente"]; LK = geo["LK"]
    N = {}; L = []
    def nd(i, z, dem, desc): N[i] = (z, dem, desc)
    def lk(i, a, b, Lm, D, k, mat, desc, st="Open"): L.append((i, a, b, Lm, D, k, st, mat, desc))
    nd("J-TK", t["z_salida"], 0, "Salida del tinaco (EXISTENTE)"); nd("J-BOL", t["z_salida"], 0, "Salida valvula de bola (EXISTENTE)")
    nd("J-CHK", t["z_salida"], 0, "Salida check (EXISTENTE)"); nd("J-TEX", t["z_salida"], 0, "T existente (EXISTENTE)")
    nd("J-B", zb, 0, "Pie de la bajada existente / codo nuevo C1")
    nd("J-PIN1", zb, 0, "Union mixta succion"); nd("J-PIN", zb, 0, "Puerto de succion de la bomba")
    nd("J-POUT", zb, 0, "Puerto de descarga de la bomba"); nd("J-POUT2", zb, 0, "Union mixta descarga")
    nd("J-FLOW", zb, 0, "Entrada YF-S201"); nd("J-FLOW2", zb, 0, "Salida YF-S201")
    nd("J-EV1", zb, 0, "Entrada electrovalvula"); nd("J-EV2", zb, 0, "Salida electrovalvula")
    nd("J-R1", zb, 0, "Codo inferior de la subida"); nd("J-R2", Z_LAT, 0, "Codo superior de la subida")
    nd("J-X", Z_LAT, 0, "CRUZ de distribucion (4 conexiones)")
    lk("P-TK", "R1", "J-TK", E["niple"], d, K["entrada_tinaco"], "existente", "Salida/niple del tinaco (EXISTENTE)")
    lk("BOLA", "J-TK", "J-BOL", E["bola"], d, K["bola"], "existente", "VALVULA DE BOLA manual (EXISTENTE, abierta)")
    lk("CHK", "J-BOL", "J-CHK", E["check"], d, K["check"], "existente", "VALVULA CHECK (EXISTENTE)", st="CV")
    lk("EX-TB", "J-CHK", "J-TEX", toma("conector") + E["tubo_a_T"], d, K["conector"] + K["T_existente"], "existente",
       "Conector + Tuboplus + T (EXISTENTES)")
    lk("EX-BAJ", "J-TEX", "J-B", t["z_salida"] - zb, d, 0.0, "existente", "BAJADA vertical Tuboplus (EXISTENTE)")
    lk("N-A", "J-B", "J-PIN1", LK["A"], d, K["codo90"] + K["conector"], "tuboplus", "Codo nuevo C1 + Tuboplus + union mixta")
    lk("AD-IN", "J-PIN1", "J-PIN", C["L_adaptador_bomba"], C["D_puerto_bomba_mm"], K["adapt_bomba_in"], "adaptador",
       "Adaptacion 1/2\" -> puerto 3/8\" (rosca PENDIENTE)")
    lk("AD-OUT", "J-POUT", "J-POUT2", C["L_adaptador_bomba"], C["D_puerto_bomba_mm"], K["adapt_bomba_out"], "adaptador",
       "Puerto 3/8\" -> adaptacion -> 1/2\" (rosca PENDIENTE)")
    lk("N-B", "J-POUT2", "J-FLOW", LK["B"], d, 2 * K["conector"], "tuboplus", "Union mixta + niple Tuboplus + conector")
    lk("YF", "J-FLOW", "J-FLOW2", C["L_yfs201"], C["D_yfs201_mm"], K["yfs201"], "yfs201", "CAUDALIMETRO YF-S201")
    lk("N-C", "J-FLOW2", "J-EV1", LK["C"], d, 2 * K["conector"], "tuboplus", "Conectores + niple Tuboplus")
    lk("EV", "J-EV1", "J-EV2", C["L_electrovalvula"], d, (Kov or {}).get("K_EV", K_EV), "electrovalvula", "ELECTROVALVULA NC (OPEN en riego)")
    lk("N-D", "J-EV2", "J-R1", LK["D"], d, LK["K_D"], "tuboplus", "LINEA PRINCIPAL + codo inferior de subida")
    lk("N-E", "J-R1", "J-R2", LK["E"], d, LK["K_E"], "tuboplus",
       f"SUBIDA {'VERTICAL' if geo['vertical'] else 'a 45 deg'} a z {Z_LAT:.2f} m + codo superior")
    lk("N-H", "J-R2", "J-X", LK["H"], d, 0.0, "tuboplus", "Tramo superior a la CRUZ")
    x0 = M["X_borde_cajon"]; xc = geo["X"]["cruz"]
    for i in range(NLAT):
        n = i + 1; lado = i != NLAT // 2; dy = abs(Y_LAT[i] - Y_LAT[NLAT // 2])
        nd(f"J-H{n}", Z_LAT, 0, f"Conector Tuboplus -> espiga lateral {n}"); nd(f"M{n}", Z_LAT, 0, f"Inicio manguera lateral {n}")
        if lado and geo["brazos_tp"]:
            Lxo = toma("cruz") + dy + C["niple_cruz_conector"] + 0.053
            kxo = K["cruz_lateral"] + K["codo90"] + K["conector"]; desc = f"Salida lateral de cruz + brazo Tuboplus + codo 90 + conector (L{n})"
        else:
            Lxo = toma("cruz") + C["niple_cruz_conector"] + 0.053
            kxo = (K["cruz_lateral"] if lado else K["cruz_recto"]) + K["conector"]
            desc = f"Salida {'lateral' if lado else 'recta'} de cruz + niple + conector (L{n})"
        lk(f"XO{n}", "J-X", f"J-H{n}", Lxo, d, kxo, "tuboplus", desc)
        lk(f"ESP{n}", f"J-H{n}", f"M{n}", 0.04, Desp, K["espiga"], "adaptador", f"Adaptador rosca 1/2\" -> espiga (L{n})")
        x_ini = xc + toma("cruz") + C["niple_cruz_conector"] + 0.053 + 0.04
        prev = f"M{n}"
        for j in range(NASP):
            s = f"S{n}{j + 1}"; a = f"A{n}{j + 1}"
            nd(s, Z_LAT, 0, f"Toma del aspersor {j + 1} en lateral {n}")
            nd(a, Z_ASP, q, f"ASPERSOR A{n}{j + 1} (lateral {n}, posicion {j + 1}) PROVISIONAL")
            if j == 0:
                r = C["manguera"]["radio_curva_m"]
                curva = lado and not geo["brazos_tp"]
                Lseg = (x0 + X_ASP[0] - x_ini) + (dy - (2 - math.pi / 2) * r if curva else 0)
                kk = C["manguera"]["K_curva"] if curva else 0.0
            else:
                Lseg = X_ASP[j] - X_ASP[j - 1]; kk = 0.0
            lk(f"HL{n}{j + 1}", prev, s, Lseg, Dh, kk, "manguera", f"Manguera lateral {n} tramo {j + 1}")
            lk(f"RA{n}{j + 1}", s, a, C["aspersor"]["L_conexion_m"], C["aspersor"]["D_conexion_mm"],
               C["aspersor"]["K_conexion"], "conexion_aspersor", f"Conexion del aspersor A{n}{j + 1}")
            prev = s
        nd(f"TAP{n}", Z_LAT, 0, f"Tapon final lateral {n}")
        lk(f"HT{n}", prev, f"TAP{n}", C["x_tapon_tras_ultimo"], Dh, 0.0, "manguera", f"Manguera hasta tapon L{n} (sin flujo)")
    return N, L, geo


def longitudes_lineas(Ls):
    out = {}
    for n in range(1, NLAT + 1):
        out[f"L{n}"] = round(sum(x[3] for x in Ls if x[0].startswith((f"HL{n}", f"HT{n}"))), 3)
    if M["M12_L_lineas"]:
        out = {f"L{i + 1}": v for i, v in enumerate(M["M12_L_lineas"])}
    return out


# =====================================================================================
# COORDENADAS
# =====================================================================================
def coords_final(N, geo):
    X = geo["X"]; s = 1000; zc = lambda z: z * 1500
    xy = {"R1": (-450, zc(C["tinaco"]["z_agua_max"])), "J-TK": (0, zc(N["J-TK"][0])),
          "J-BOL": ((C["L_existente"]["niple"] + C["L_existente"]["bola"]) * s, zc(N["J-TK"][0])),
          "J-CHK": ((C["L_existente"]["niple"] + C["L_existente"]["bola"] + C["L_existente"]["check"]) * s, zc(N["J-TK"][0])),
          "J-TEX": (X["T_existente"] * s, zc(N["J-TK"][0])), "J-B": (X["T_existente"] * s, zc(Z_LINEA))}
    for nid, key in [("J-PIN1", "union_suc"), ("J-PIN", "bomba_in"), ("J-POUT", "bomba_out"), ("J-POUT2", "union_des"),
                     ("J-FLOW", "yf_in"), ("J-FLOW2", "yf_out"), ("J-EV1", "ev_in"), ("J-EV2", "ev_out"), ("J-R1", "sube_ini")]:
        xy[nid] = (X[key] * s, zc(Z_LINEA))
    xy["J-R2"] = (X["subida"] * s, zc(Z_LAT)); xy["J-X"] = (X["cruz"] * s, zc(Z_LAT))
    x0 = M["X_borde_cajon"]
    for i in range(NLAT):
        n = i + 1; yy = zc(Z_LAT) + (0.5 - Y_LAT[i]) * 2400
        xy[f"J-H{n}"] = (X["cruz"] * s + 90, yy); xy[f"M{n}"] = (X["cruz"] * s + 180, yy)
        for j in range(NASP):
            xs = (x0 + X_ASP[j]) * s; xy[f"S{n}{j + 1}"] = (xs, yy); xy[f"A{n}{j + 1}"] = (xs, yy - 110)
        xy[f"TAP{n}"] = ((x0 + X_ASP[-1] + C["x_tapon_tras_ultimo"]) * s, yy)
    vert = {f"XO{n}": [(X["cruz"] * s, zc(Z_LAT) + (0.5 - Y_LAT[n - 1]) * 2400)] for n in (1, NLAT)}
    return xy, vert


def coords_presentacion(geo):
    xy = {"R1": (0, 0), "J-TK": (1500, 0), "J-BOL": (3000, 0), "J-CHK": (4500, 0), "J-TEX": (6000, 0),
          "J-B": (6000, -2500), "J-PIN1": (7400, -2500), "J-PIN": (8400, -2500), "J-POUT": (10600, -2500),
          "J-POUT2": (11600, -2500), "J-FLOW": (13000, -2500), "J-FLOW2": (15000, -2500), "J-EV1": (16400, -2500),
          "J-EV2": (18400, -2500)}
    if geo["vertical"]:
        xy.update({"J-R1": (24400, -2500), "J-R2": (24400, 1200), "J-X": (26000, 1200)})
    else:
        xy.update({"J-R1": (22400, -2500), "J-R2": (25400, 1200), "J-X": (26000, 1200)})
    vert = {}
    for i in range(NLAT):
        n = i + 1; yy = 1200 + (1 - i) * 3600
        xy[f"J-H{n}"] = (27900, yy); xy[f"M{n}"] = (28800, yy)
        if n != NLAT // 2 + 1:
            vert[f"XO{n}"] = [(26000, yy)]
        for j in range(NASP):
            xy[f"S{n}{j + 1}"] = (30600 + j * 3300, yy); xy[f"A{n}{j + 1}"] = (30600 + j * 3300, yy - 1000)
        xy[f"TAP{n}"] = (30600 + NASP * 3300 - 1300, yy)
    return xy, vert


LABELS_PRES = [
    (-1300, 1500, "TINACO (R1)"),
    (2400, 1500, "EXISTENTE: BOLA + CHECK + T"),
    (6400, -900, "BAJADA (exist.)"),
    (7600, -3100, "BOMBA 12 V (PU1)"),
    (12600, -1600, "YF-S201 (YF)"),
    (14600, -3100, "ELECTROVALVULA NC (EV)"),
    (18000, -1600, "LINEA PRINCIPAL"),
    (19100, 1000, "SUBIDA VERTICAL"),
    (19100, 300, "a 1.52 m"),
    (22800, 2700, "CRUZ (J-X)"),
    (31200, 5550, "LATERAL 1 (manguera)"),
    (31200, 1950, "LATERAL 2 (manguera)"),
    (31200, -1650, "LATERAL 3 (manguera)"),
    (29000, -4100, "9 ASPERSORES (3 por lateral)"),
]


# =====================================================================================
# .INP
# =====================================================================================
def escribir_inp(path, xy=None, vert=None, labels=(), titulo="", q_asp_Lh=None, D_hose_mm=None, Kov=None, curva=None,
                 z_agua=None, headloss="D-W", backdrop=None, gid=None):
    N, Ls, geo = red(q_asp_Lh, D_hose_mm, Kov, gid)
    if xy is None:
        xy, vert = coords_final(N, geo)
    vert = vert or {}
    T = "\t"; w = []; a = w.append
    rough = lambda mat: (C["manguera"]["rug_mm"] if mat == "manguera" else C["tubo"]["rug_mm"]) if headloss == "D-W" else C["tubo"]["C_HW"]
    a("[TITLE]")
    a(f"Riego huerto v3 - GEOMETRIA {geo['id']} ({geo['rol']}): {geo['desc']}")
    a("Cruz + 3 laterales de manguera x 3 aspersores = 9 (DEMANDA FIJA). Tuboplus DI 14.40 mm (OFICIAL).")
    a("Curva de bomba PROVISIONAL; manguera NO medida; aspersores PROVISIONALES; geometria ESTIMADA hasta medir. " + titulo)
    a(""); a("[JUNCTIONS]"); a(";ID              \tElev (m)\tDemand (L/s)\tPattern")
    for n, (z, dem, desc) in N.items():
        a(f" {n:<16s}{T}{z:.3f}{T}{dem:.8f}{T}{T};{desc}")
    a(""); a("[RESERVOIRS]")
    a(f" R1              {T}{(z_agua if z_agua is not None else C['tinaco']['z_agua_max']):.3f}{T}{T};TINACO PROVISIONAL (nivel de agua)")
    a(""); a("[TANKS]"); a(""); a("[PIPES]")
    a(";ID              \tNode1           \tNode2           \tLength (m)\tDiam (mm)\tRoughness\tMinorLoss\tStatus")
    for i, n1, n2, Lm, D, k, st, mat, desc in Ls:
        a(f" {i:<16s}{T}{n1:<16s}{T}{n2:<16s}{T}{Lm:.4f}{T}{D:.2f}{T}{rough(mat)}{T}{k:.4f}{T}{st}{T};{desc}")
    a(""); a("[PUMPS]")
    a(f" PU1             {T}J-PIN           {T}J-POUT          {T}HEAD PUMP_CURVE_PROVISIONAL{T};BOMBA GOOD PUMPS 12 V 72 W (curva NO publicada)")
    a(""); a("[VALVES]"); a("; Check = Pipe CV (CHK). Electrovalvula = Pipe ON/OFF (EV). Valvula de bola = Pipe con K (BOLA)."); a("")
    a("[TAGS]"); a(" LINK \tCHK\tCHECK_EXISTENTE\n LINK \tBOLA\tVALVULA_BOLA_EXISTENTE\n LINK \tPU1\tBOMBA\n LINK \tYF\tYF-S201\n LINK \tEV\tELECTROVALVULA_NC\n NODE \tJ-X\tCRUZ")
    a(""); a("[DEMANDS]"); a(""); a("[STATUS]")
    a(" EV              \tOPEN\t;riego activo"); a(" PU1             \tOPEN\t;bomba encendida"); a(" BOLA            \tOPEN\t;valvula manual abierta")
    a(""); a("[PATTERNS]"); a(""); a("[CURVES]")
    a(";PUMP: PUMP_CURVE_PROVISIONAL - NO es la curva del fabricante (ver DECISIONS.md)")
    for q, h in (curva or C["bomba_curva"]):
        a(f" PUMP_CURVE_PROVISIONAL\t{q:.4f}\t{h:.3f}")
    a(""); a("[CONTROLS]\n\n[RULES]\n"); a("[ENERGY]\n Global Efficiency  \t75\n Global Price       \t0\n Demand Charge      \t0\n")
    a("[EMITTERS]"); a("; Sin emisores: la curva presion-caudal de los aspersores reales NO se conoce (demanda fija)."); a("")
    a("[QUALITY]\n\n[SOURCES]\n\n[REACTIONS]\n Global Bulk 0\n Global Wall 0\n\n[MIXING]\n")
    a("[TIMES]\n Duration           \t0:00\n Hydraulic Timestep \t1:00\n Report Timestep    \t1:00\n Statistic          \tNONE\n")
    a("[REPORT]\n Status             \tYes\n Summary            \tNo\n Nodes              \tAll\n Links              \tAll\n")
    a("[OPTIONS]\n Units              \tLPS\n Headloss           \t" + headloss +
      "\n Specific Gravity   \t1.0\n Viscosity          \t1.0\n Trials             \t100\n Accuracy           \t0.00001\n Unbalanced         \tContinue 10\n Pattern            \t1\n Demand Multiplier  \t1.0\n Emitter Exponent   \t0.5\n Quality            \tNone mg/L\n Demand Model       \tDDA\n")
    a("[COORDINATES]")
    for n, (x, y) in xy.items():
        a(f" {n:<16s}\t{x:.2f}\t{y:.2f}")
    a(""); a("[VERTICES]")
    for l, pts in vert.items():
        for x, y in pts:
            a(f" {l:<16s}\t{x:.2f}\t{y:.2f}")
    a(""); a("[LABELS]")
    for x, y, t in labels:
        a(f" {x:.2f}\t{y:.2f}\t\"{t}\"")
    a(""); a("[BACKDROP]")
    if backdrop:
        a(f" DIMENSIONS\t{backdrop[0]:.2f}\t{backdrop[1]:.2f}\t{backdrop[2]:.2f}\t{backdrop[3]:.2f}")
    a(" UNITS\tNone\n OFFSET\t0.00\t0.00\n"); a("[END]")
    open(path, "w", encoding="utf-8").write("\n".join(w) + "\n")
    return path, N, Ls


# =====================================================================================
# SIMULACION
# =====================================================================================
def simular(path):
    """EPyT/OWA-EPANET (doble precision). Copia a ruta ASCII (EPyT no abre rutas con acentos)."""
    from epyt import epanet as ep
    tmp = os.path.join(tempfile.mkdtemp(), "m.inp"); shutil.copy(path, tmp)
    d = ep(tmp, display_msg=False, display_warnings=False)
    r = d.getComputedHydraulicTimeSeries()
    nid = d.getNodeNameID(); lid = d.getLinkNameID(); el = d.getNodeElevations()
    out = {"nodes": {n: {"H": float(r.Head[0][i]), "P": float(r.Pressure[0][i]), "D": float(r.Demand[0][i]), "z": float(el[i])}
                     for i, n in enumerate(nid)},
           "links": {l: {"Q": float(r.Flow[0][i]), "V": float(r.Velocity[0][i]), "hl": float(r.HeadLoss[0][i]),
                         "st": float(r.Status[0][i])} for i, l in enumerate(lid)}}
    d.unload()
    return out


def runepanet(path):
    import subprocess
    exe = r"C:\Program Files (x86)\EPANET 2.2\runepanet.exe"
    if not os.path.exists(exe):
        return None, ["runepanet.exe no encontrado"]
    tmp = os.path.join(tempfile.mkdtemp(), "m.inp"); shutil.copy(path, tmp)
    p = subprocess.run([exe, tmp, tmp[:-4] + ".rpt"], capture_output=True, text=True)
    rpt = open(tmp[:-4] + ".rpt", encoding="latin-1").read()
    msgs = [l.strip() for l in rpt.splitlines() if re.search(r"WARNING|Error|cannot deliver|disconnected|negative", l, re.I)]
    return ("ran successfully" in p.stdout and not re.search(r"Error \d{3}", rpt)), msgs


def tmp_inp(**kw):
    p = os.path.join(tempfile.mkdtemp(), "e.inp"); escribir_inp(p, titulo="ESCENARIO", **kw); return p


# =====================================================================================
# CALCULO MANUAL
# =====================================================================================
def f_dw(Re, D, eps):
    if Re < 2000:
        return 64 / Re, "laminar (64/Re)"
    f = 0.25 / math.log10(eps / (3.7 * D) + 5.74 / Re**0.9) ** 2
    for _ in range(60):
        f = (-2 * math.log10(eps / (3.7 * D) + 2.51 / (Re * math.sqrt(f)))) ** -2
    return f, ("transicion (Colebrook, cota)" if Re < 4000 else "turbulento (Colebrook)")


def calculos(res, Ls):
    rows = []
    for i, n1, n2, Lm, Dmm, k, st, mat, desc in Ls:
        Q = abs(res["links"][i]["Q"]) / 1000; D = Dmm / 1000; A = math.pi * D**2 / 4; V = Q / A
        eps = (C["manguera"]["rug_mm"] if mat == "manguera" else C["tubo"]["rug_mm"]) / 1000
        if Q <= 1e-12:
            rows.append(dict(id=i, mat=mat, desc=desc, L=Lm, D=Dmm, A=A, Q=0, V=0, Re=0, reg="sin flujo", f=0, K=k, hf=0, hm=0, ht=0,
                             hw=0, epanet=res["links"][i]["hl"])); continue
        Re = C["rho"] * V * D / C["mu"]; f, reg = f_dw(Re, D, eps); hv = V**2 / (2 * C["g"])
        hf = f * Lm / D * hv; hm = k * hv
        hw = 10.67 * Lm * Q**1.852 / (C["tubo"]["C_HW"]**1.852 * D**4.87)
        rows.append(dict(id=i, mat=mat, desc=desc, L=Lm, D=Dmm, A=A, Q=Q * 1000, V=V, Re=Re, reg=reg, f=f, K=k, hf=hf, hm=hm,
                         ht=hf + hm, hw=hw + hm, epanet=res["links"][i]["hl"]))
    return rows


def resumen(r):
    N, L = r["nodes"], r["links"]
    P = [N[a]["P"] for a in ASP]; q = [N[a]["D"] for a in ASP]; Qt = L["N-D"]["Q"]
    return {"Q_total_Ls": Qt, "Q_total_Lmin": Qt * 60, "Q_lat_Ls": [L[f"XO{i + 1}"]["Q"] for i in range(NLAT)],
            "P_asp_m": P, "P_min": min(P), "P_max": max(P), "P_media": sum(P) / len(P),
            "uniformidad_hidraulica_presion_PminPmax": min(P) / max(P) if max(P) > 0 else 0,
            "q_asp_Lh": [x * 3600 for x in q], "H_bomba": N["J-POUT"]["H"] - N["J-PIN"]["H"],
            "P_succion": N["J-PIN"]["P"], "V_principal": L["N-D"]["V"],
            "V_manguera_max": max(abs(L[x]["V"]) for x in L if x.startswith("HL")), "YF_Hz": 7.5 * Qt * 60,
            "margen_bomba_pct": (1 - Qt * 60 / C["bomba_Qmax_Lmin"]) * 100}


# =====================================================================================
# MAIN
# =====================================================================================
def main():
    os.makedirs(os.path.join(HERE, "capturas_epanet"), exist_ok=True)
    gp = C["geometria_principal"]
    f_final, N, Ls = escribir_inp(os.path.join(HERE, "riego_huerto_v3_final.inp"),
                                  titulo=f"BASE: {C['aspersor']['Q_nominal_Lh']:.0f} L/h por aspersor (PROVISIONAL), D-W, tinaco lleno")
    xyp, vp = coords_presentacion(GEO)
    escribir_inp(os.path.join(HERE, "riego_huerto_v3_presentacion.inp"), xy=xyp, vert=vp, labels=LABELS_PRES,
                 titulo="PRESENTACION: misma hidraulica que riego_huerto_v3_final.inp", backdrop=(-2500, -5000, 41000, 7200))
    base = simular(f_final); ok22, msg22 = runepanet(f_final)

    esc = {}
    def run(nombre, desc, **kw):
        p = tmp_inp(**kw); ok, msgs = runepanet(p)
        try:
            r = simular(p)
        except Exception as e:
            r = None; msgs = msgs + [f"EPyT: {e}"]
        esc[nombre] = {"desc": desc, "ok22": ok, "msgs": msgs, "res": r}
    for qh in C["aspersor"]["Q_escenarios_Lh"]:
        run(f"Q{qh:.0f}", f"{qh:.0f} L/h por aspersor impuesto (x9 = {9 * qh / 60:.2f} L/min); apertura fisica desconocida", q_asp_Lh=qh)
    for dh in C["manguera"]["id_sensibilidad_mm"]:
        run(f"DH{dh:.0f}", f"Manguera DI {dh:.0f} mm (NO medido)", D_hose_mm=dh)
    for fac in (0.25, 0.40, 0.50, 0.75):
        run(f"CURVA_x{fac:.2f}", f"Curva provisional con alturas x{fac:.2f}", curva=[(q, h * fac) for q, h in C["bomba_curva"]])
    run("HW150", "Hazen-Williams C=150 (comparacion)", headloss="H-W")
    run("TINACO_MIN", "Tinaco casi vacio (agua +0.30 m)", z_agua=C["tinaco"]["z_agua_min"])
    run("K_ALTOS", "K estimados x2 y Kv EV = 1",
        Kov={"cruz_recto": 3.6, "cruz_lateral": 4.4, "T_existente": 3.6, "check": 5.4, "yfs201": 4.0, "espiga": 1.0,
             "adapt_bomba_in": 1.0, "adapt_bomba_out": 2.0, "K_EV": kv_to_K(1.0, DI)})
    run("K_BAJOS", "K estimados x0.5 y Kv EV = 6",
        Kov={"cruz_recto": 0.9, "cruz_lateral": 1.1, "T_existente": 0.9, "check": 1.35, "yfs201": 1.0, "espiga": 0.25,
             "adapt_bomba_in": 0.25, "adapt_bomba_out": 0.5, "K_EV": kv_to_K(6.0, DI)})
    for g in C["geometrias"]:
        if g != gp:
            run(f"GEO_{g}", f"Geometria {g} ({C['geometrias'][g]['rol']}): {C['geometrias'][g]['desc']}", gid=g)

    rows = calculos(base, Ls); Llin = longitudes_lineas(Ls)
    # ---------- CSV resultados ----------
    with open(os.path.join(HERE, "resultados_epanet.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["tipo", "id", "descripcion", "elev_m", "head_m", "presion_m_PRELIMINAR", "presion_bar_PRELIMINAR", "demanda_Ls",
                     "demanda_Lh", "caudal_Ls", "caudal_Lmin", "velocidad_ms", "headloss_m", "estado"])
        for n, v in base["nodes"].items():
            wr.writerow(["nodo", n, N.get(n, (0, 0, "TINACO R1"))[2], f"{v['z']:.3f}", f"{v['H']:.4f}", f"{v['P']:.4f}",
                         f"{v['P'] * C['rho'] * C['g'] / 1e5:.4f}", f"{v['D']:.6f}", f"{v['D'] * 3600:.2f}", "", "", "", "", ""])
        for l, v in base["links"].items():
            desc = next((x[8] for x in Ls if x[0] == l), "BOMBA PU1 (curva PROVISIONAL)")
            wr.writerow(["enlace", l, desc, "", "", "", "", "", "", f"{v['Q']:.6f}", f"{v['Q'] * 60:.4f}", f"{v['V']:.4f}",
                         f"{v['hl']:.5f}", {0: "CERRADO", 1: "ABIERTO"}.get(int(v['st']), str(v['st']))])
    with open(os.path.join(HERE, "escenarios_sensibilidad.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["escenario", "descripcion", "epanet22_ok", "mensajes_epanet", "Q_total_Ls", "Q_total_Lmin", "Q_L1_Ls", "Q_L2_Ls",
                     "Q_L3_Ls", "P_min_m_PRELIM", "P_max_m_PRELIM", "P_min_bar_PRELIM", "P_max_bar_PRELIM",
                     "uniformidad_hidraulica_presion_PminPmax", "H_bomba_m", "P_succion_m", "V_principal_ms", "V_manguera_max_ms",
                     "YF_Hz", "margen_vs_6Lmin_pct", "viable_hidraulicamente"])
        for k, e in esc.items():
            r = e["res"]
            if r is None:
                wr.writerow([k, e["desc"], e["ok22"], " | ".join(e["msgs"])] + [""] * 16 + ["NO"]); continue
            s = resumen(r)
            viable = bool(e["ok22"]) and not e["msgs"] and s["P_min"] > 0 and s["margen_bomba_pct"] > 0
            e["resumen"] = s; e["viable"] = viable
            wr.writerow([k, e["desc"], e["ok22"], " | ".join(e["msgs"]), f"{s['Q_total_Ls']:.5f}", f"{s['Q_total_Lmin']:.3f}"] +
                        [f"{x:.5f}" for x in s["Q_lat_Ls"]] +
                        [f"{s['P_min']:.3f}", f"{s['P_max']:.3f}", f"{s['P_min'] * C['rho'] * C['g'] / 1e5:.3f}",
                         f"{s['P_max'] * C['rho'] * C['g'] / 1e5:.3f}", f"{s['uniformidad_hidraulica_presion_PminPmax']:.4f}",
                         f"{s['H_bomba']:.3f}", f"{s['P_succion']:.3f}", f"{s['V_principal']:.4f}", f"{s['V_manguera_max']:.4f}",
                         f"{s['YF_Hz']:.1f}", f"{s['margen_bomba_pct']:.1f}", "SI" if viable else "NO"])
    # ---------- tabla de Tuboplus (paramétrica) ----------
    with open(os.path.join(HERE, "tabla_cortes_tuboplus.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        for gid in ("A", "B"):
            g = GEOS[gid]
            wr.writerow([f"ESCENARIO {gid}", g["rol"], g["desc"]])
            wr.writerow(["seccion", "tramo", "descripcion", "estado_medida", "distancia_referencia_m", "resta_conexiones_m",
                         "suma_inserciones_m", "cantidad", "longitud_neta_tuboplus_m"])
            for estado_sec in ("TRAMOS MEDIDOS", "TRAMOS ESTIMADOS"):
                for t in g["tramos"]:
                    es_med = t["estado"].startswith("MEDIDO") and "ESTIMADO" not in t["estado"]
                    if (estado_sec == "TRAMOS MEDIDOS") == es_med:
                        wr.writerow([estado_sec, t["tramo"], t["descripcion"], t["estado"], f"{t['distancia_m']:.3f}",
                                     f"{t['resta_conexiones_m']:.3f}", f"{t['suma_inserciones_m']:.3f}", t["cantidad"], f"{t['corte_neto_m']:.3f}"])
            wr.writerow(["LONGITUD OCUPADA POR COMPONENTES (NO es Tuboplus)", "", "Conjunto bomba (bomba + adaptadores + uniones)",
                         C["medidas"]["M2_L_conjunto_bomba"]["estado"], f"{M['M2_L_conjunto_bomba']:.3f}", "", "", "", "0"])
            wr.writerow(["LONGITUD OCUPADA POR COMPONENTES (NO es Tuboplus)", "", "Conjunto YF-S201 + conectores",
                         C["medidas"]["M3_L_conjunto_yf"]["estado"], f"{M['M3_L_conjunto_yf']:.3f}", "", "", "", "0"])
            wr.writerow(["LONGITUD OCUPADA POR COMPONENTES (NO es Tuboplus)", "", "Conjunto electrovalvula + conectores",
                         C["medidas"]["M4_L_conjunto_ev"]["estado"], f"{M['M4_L_conjunto_ev']:.3f}", "", "", "", "0"])
            wr.writerow(["LONGITUD OCUPADA POR COMPONENTES (NO es Tuboplus)", "", f"Codos ({g['codos']['codo90']} x 90, {g['codos']['codo45']} x 45), cruz, conectores (tomas oficiales)",
                         "OFICIAL", "", "", "", "", "0"])
            wr.writerow(["LONGITUD OCUPADA POR COMPONENTES (NO es Tuboplus)", "", "Mangueras negras (laterales)", "ESTIMADO", "", "", "", "", "0"])
            wr.writerow(["TOTAL", "", f"Tuboplus NUEVO escenario {gid}", g["estado_total"], "", "", "", "", f"{g['nuevo_m']:.3f}"])
            wr.writerow(["LIMITE", "", "Limite de compra", "", "", "", "", "", f"{C['tubo']['limite_nuevo_m']:.3f}"])
            wr.writerow(["MARGEN", "", "Limite - total (negativo = excede)", g["estado_total"], "", "", "", "", f"{g['margen_m']:.3f}"])
            wr.writerow(["VEREDICTO", "", ("CUMPLE" if g["cumple"] else "EXCEDE") + (" (ESTIMADO: confirmar con mediciones)" if g["estado_total"] != "MEDIDO" else ""),
                         "", "", "", "", "", ""])
            wr.writerow(["CONDICION", "", f"Para cumplir con las demas medidas fijas: M1 + M5 <= {g['M1_M5_max_m']:.3f} m "
                         f"(actual estimado {M['M1_d_bajada_a_bomba'] + M['M5_d_conjunto_a_subida']:.3f} m)", "", "", "", "", "", ""])
            wr.writerow([])
        wr.writerow(["NO_CUENTA", "", "Instalacion existente (niple, bola, check, conector, Tuboplus, T, bajada)", "", "", "", "", "", "0"])
    with open(os.path.join(HERE, "alternativas_trazado.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["escenario", "rol", "descripcion", "subida", "brazos", "tuboplus_nuevo_estimado_m", "margen_m", "cumple_estimado",
                     "estado", "codos90", "codos45"])
        for gid, g in GEOS.items():
            wr.writerow([gid, g["rol"], g["desc"], g["subida"], g["brazos"], f"{g['nuevo_m']:.3f}", f"{g['margen_m']:.3f}",
                         "SI" if g["cumple"] else "NO", g["estado_total"], g["codos"]["codo90"], g["codos"]["codo45"]])
    with open(os.path.join(HERE, "mediciones_fisicas.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["clave_CONFIG", "medicion", "valor_actual", "estado", "como_medir"])
        for k, v in C["medidas"].items():
            wr.writerow([k, v["desc"], v["valor"], v["estado"], v["como"]])
    json.dump({"GEOS": GEOS, "K_EV": K_EV, "Z_LAT": Z_LAT, "base": base, "base_ok22": ok22, "base_msgs": msg22, "rows": rows,
               "L_lineas": Llin, "esc": {k: {kk: vv for kk, vv in e.items() if kk != "res"} for k, e in esc.items()},
               "resumen_base": resumen(base)}, open(os.path.join(HERE, "resultados_calculo.json"), "w"), indent=1, default=float)
    escribir_md(base, rows, esc, Llin)
    return base, esc, rows, ok22, msg22


def escribir_md(base, rows, esc, Llin):
    s = resumen(base); bar = lambda m: m * C["rho"] * C["g"] / 1e5
    L = ["# Resultados numericos (generado por generar_modelo.py - no editar a mano)", "",
         f"Geometria principal: **{GEO['id']} - {GEO['rol']}** ({GEO['desc']}). Caudal {C['aspersor']['Q_nominal_Lh']:.0f} L/h por aspersor "
         f"(PROVISIONAL), manguera DI {M['M9_manguera_DI_mm']:.1f} mm (NO MEDIDO), curva de bomba PROVISIONAL. z cruz/laterales = {Z_LAT:.2f} m.", "",
         "## Tuboplus nuevo por escenario geometrico (ESTIMADO hasta medir)", "",
         "| Escenario | Rol | Descripcion | Tuboplus nuevo (m) | Margen vs 4.00 m | Cumple (estimado) | Estado | Codos 90 | Codos 45 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for gid, g in GEOS.items():
        L.append(f"| {gid} | {g['rol']} | {g['desc']} | {g['nuevo_m']:.3f} | {g['margen_m']:.3f} | {'SI' if g['cumple'] else 'NO'} | {g['estado_total']} | {g['codos']['codo90']} | {g['codos']['codo45']} |")
    L += ["", "Condicion para cumplir 4.00 m manteniendo las demas medidas: " + "; ".join(
        f"{gid}: M1 + M5 <= {g['M1_M5_max_m']:.3f} m" for gid, g in GEOS.items()) +
          f" (estimado actual M1 + M5 = {M['M1_d_bajada_a_bomba'] + M['M5_d_conjunto_a_subida']:.3f} m)."]
    L += ["", f"Longitud de manguera por linea (calculada): " + ", ".join(f"{k} = {v:.2f} m" for k, v in Llin.items()), "",
          "## Tabla por tramo (escenario base)", "",
          "| Tramo | Material | L (m) | D (mm) | Q (L/s) | V (m/s) | Re | Regimen | f | K | hf D-W (m) | hm (m) | h total (m) | EPANET (m) | H-W C150 + hm (m) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["Q"] == 0:
            L.append(f"| {r['id']} | {r['mat']} | {r['L']:.3f} | {r['D']:.1f} | 0 | 0 | - | sin flujo | - | - | 0 | 0 | 0 | 0 | 0 |"); continue
        L.append(f"| {r['id']} | {r['mat']} | {r['L']:.3f} | {r['D']:.1f} | {r['Q']:.5f} | {r['V']:.3f} | {r['Re']:.0f} | {r['reg']} | {r['f']:.4f} | {r['K']:.2f} | {r['hf']:.5f} | {r['hm']:.5f} | {r['ht']:.5f} | {r['epanet']:.5f} | {r['hw']:.5f} |")
    hf = sum(r["hf"] for r in rows); hm = sum(r["hm"] for r in rows)
    L += ["", f"Totales red: perdida distribuida {hf:.4f} m, perdidas menores {hm:.4f} m.", "",
          "## Aspersores (escenario base) - PRESION PRELIMINAR DEPENDIENTE DE CURVA PROVISIONAL DE BOMBA", "",
          "| Aspersor | Presion (m) | Presion (bar) | Caudal impuesto (L/h) |", "|---|---|---|---|"]
    for a in ASP:
        v = base["nodes"][a]; L.append(f"| {a} | {v['P']:.3f} | {bar(v['P']):.3f} | {v['D'] * 3600:.2f} |")
    L += ["", f"**Uniformidad hidraulica de presion (relacion Pmin/Pmax) = {s['uniformidad_hidraulica_presion_PminPmax']:.4f}.** "
              "Solo indica que las presiones de los 9 aspersores son casi iguales; NO es uniformidad de riego "
              "(patron de mojado, radio, presion minima requerida, relacion apertura-caudal y efecto de la altura de 1 m sobre el cajon "
              "son desconocidos). La uniformidad de riego real queda PENDIENTE DE VALIDACION EXPERIMENTAL.", "",
          "## Escenarios", "",
          "| Escenario | Descripcion | EPANET 2.2 | Q total (L/min) | P min-max (m, prelim.) | Pmin/Pmax | H bomba (m) | V principal (m/s) | YF (Hz) | Margen vs 6 L/min | Viable |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, e in esc.items():
        if "resumen" not in e:
            L.append(f"| {k} | {e['desc']} | {'OK' if e['ok22'] else 'ERROR'}: {'; '.join(e['msgs'])[:120]} | - | - | - | - | - | - | - | NO |"); continue
        r = e["resumen"]
        L.append(f"| {k} | {e['desc']} | {'OK' if e['ok22'] else 'ERROR'}{(' / ' + '; '.join(e['msgs'])[:100]) if e['msgs'] else ''} | {r['Q_total_Lmin']:.3f} | "
                 f"{r['P_min']:.2f}-{r['P_max']:.2f} | {r['uniformidad_hidraulica_presion_PminPmax']:.4f} | {r['H_bomba']:.2f} | {r['V_principal']:.3f} | "
                 f"{r['YF_Hz']:.1f} | {r['margen_bomba_pct']:.0f} % | {'SI' if e.get('viable') else 'NO'} |")
    open(os.path.join(HERE, "calculos_resultados.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    base, esc, rows, ok22, msg22 = main()
    s = resumen(base)
    for gid, g in GEOS.items():
        print(f"GEO {gid:2s} {g['rol']:28s} Tuboplus={g['nuevo_m']:.3f} m margen={g['margen_m']:.3f} cumple={g['cumple']} ({g['estado_total']}) codos={g['codos']}")
    print(f"EPANET 2.2 base ok={ok22} msgs={msg22}")
    print(f"BASE (GEO {GEO['id']}): Q={s['Q_total_Lmin']:.3f} L/min H={s['H_bomba']:.2f} m P {s['P_min']:.3f}-{s['P_max']:.3f} m "
          f"Pmin/Pmax={s['uniformidad_hidraulica_presion_PminPmax']:.4f} V={s['V_principal']:.3f}")
    for k, e in esc.items():
        r = e.get("resumen")
        print(f" {k:12s} ok22={e['ok22']} msgs={e['msgs'][:1]} " + (f"Q={r['Q_total_Lmin']:.2f} P={r['P_min']:.2f}-{r['P_max']:.2f} H={r['H_bomba']:.2f} viable={e.get('viable')}" if r else "SIN RESULTADO"))
