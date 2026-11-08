"""Genera database/cultivos_base.json: los 10 cultivos precargados.

Fuentes (consultadas el 2026-10-11):
 [FAO56-T11] FAO Irrigation and Drainage Paper 56, Tabla 11 (duración de etapas)
             https://www.fao.org/4/x0490e/x0490e0b.htm
 [FAO56-T12] FAO-56 Tabla 12 (Kc ini/mid/end y altura máxima). Kc ini por grupo
             (hortalizas pequeñas 0.7, solanáceas 0.6, cucurbitáceas 0.5, leguminosas 0.4)
 [FAO56-T22] FAO-56 Tabla 22 (profundidad de raíz Zr y fracción de agotamiento p)
             https://www.fao.org/4/x0490e/x0490e0e.htm  ;  p_aj = p + 0.04(5 - ETc), 0.1<=p<=0.8
 [ACES-1061] Alabama Cooperative Extension, ANR-1061 "Soil Temperature Conditions for
             Vegetable Seed Germination" (temperatura de SUELO para germinación)
 [WVU-HT]    West Virginia Univ. / SARE, "Temperature Management in High Tunnels"
             (temperatura del AIRE: óptima y máxima por grupo de cultivo)
 [PURDUE-GDD] Purdue Midwestern Regional Climate Center, tabla de temperatura base GDD
 [WISC-GDD]  Univ. of Wisconsin Extension: umbral más común 10 °C (50 °F); hortalizas de
             clima fresco ~4.4 °C (40 °F)

IMPORTANTE: aquí NO hay humedades volumétricas (%VWC). Los umbrales del EC-5 se
calculan en el servidor solo cuando el usuario registra la capacidad de campo y el
punto de marchitez MEDIDOS en su propio suelo con su sensor; mientras tanto el
perfil aparece como "PENDIENTE DE CALIBRACIÓN".
"""
import json
import os


def f2c(f):
    return round((f - 32) * 5 / 9, 1)


def soil_germ(mn, lo, hi, mx):
    return {"min_c": f2c(mn), "opt_min_c": f2c(lo), "opt_max_c": f2c(hi), "max_c": f2c(mx), "fuente": "ACES-1061"}


LEAFY = {"opt_min_c": f2c(60), "opt_max_c": f2c(65), "max_c": f2c(75), "fuente": "WVU-HT (hortalizas de hoja)"}
CUCURB = {"opt_min_c": f2c(70), "opt_max_c": f2c(85), "max_c": f2c(90), "fuente": "WVU-HT (cucurbitáceas)"}
TOMATO = {"opt_min_c": f2c(70), "opt_max_c": f2c(75), "max_c": f2c(85), "fuente": "WVU-HT (tomate, floración a cosecha)"}
PEPPER = {"opt_min_c": f2c(70), "opt_max_c": f2c(80), "max_c": f2c(88), "fuente": "WVU-HT (chile/pimiento: máx. 85-90 °F)"}
PENDIENTE = {"opt_min_c": None, "opt_max_c": None, "max_c": None,
             "fuente": "PENDIENTE: no se encontró una tabla de extensión con temperatura del aire para este cultivo"}

LEAF_STAGES = ["Establecimiento", "Desarrollo vegetativo", "Crecimiento máximo", "Cosecha"]
ROOT_STAGES = ["Establecimiento", "Desarrollo de hojas", "Engrosamiento de raíz", "Maduración y cosecha"]
FRUIT_STAGES = ["Establecimiento", "Desarrollo vegetativo", "Floración y fructificación", "Maduración y cosecha"]
FAO_STAGE_KEYS = ["inicial", "desarrollo", "media", "final"]


def stages(names, days, kc_ini, kc_mid, kc_end):
    kcs = [kc_ini, round((kc_ini + kc_mid) / 2, 2), kc_mid, kc_end]
    return [{"clave": k, "nombre": n, "dias": d, "kc": kc, "kc_nota": ("promedio ini-mid (Kc varía linealmente en desarrollo)" if k == "desarrollo" else
             ("Kc al final del ciclo" if k == "final" else "FAO-56 Tabla 12"))}
            for k, n, d, kc in zip(FAO_STAGE_KEYS, names, days, kcs)]


def crop(cid, nombre, cientifico, familia, temporada, st_names, days, fao_row, kc, p, zr, germ, aire, gdd, sensib, notas):
    return {
        "id": cid, "nombre": nombre, "cientifico": cientifico, "familia": familia, "temporada": temporada,
        "tipo": "base",
        "etapas": stages(st_names, days, *kc),
        "ciclo_total_dias": sum(days),
        "fila_fao_t11": fao_row,
        "kc": {"ini": kc[0], "mid": kc[1], "end": kc[2], "fuente": "FAO56-T12"},
        "p_agotamiento": p, "p_fuente": "FAO56-T22 (para ETc ~5 mm/d; se ajusta con p + 0.04(5-ETc))",
        "raiz_m": zr, "raiz_fuente": "FAO56-T22",
        "temp_germinacion_suelo": germ,
        "temp_aire_crecimiento": aire,
        "gdd": gdd,
        "sensibilidad_deficit": sensib,
        "humedad_vwc": {"estado": "PENDIENTE_DE_CALIBRACION",
                        "nota": "Se calcula con capacidad de campo y punto de marchitez medidos con el EC-5 en el suelo real"},
        "horarios": {"win1": ["06:00", "09:00"], "win2": ["18:00", "20:00"]},
        "notas": notas,
        "fuentes": ["FAO56-T11", "FAO56-T12", "FAO56-T22", germ["fuente"], aire["fuente"], gdd["fuente"]],
    }


def sens(p):
    if p <= 0.25:
        return {"nivel": "ALTA", "texto": f"p = {p}: tolera poco agotamiento del agua disponible antes de estresarse"}
    if p <= 0.35:
        return {"nivel": "MEDIA-ALTA", "texto": f"p = {p}: conviene riegos frecuentes y ligeros"}
    if p <= 0.45:
        return {"nivel": "MEDIA", "texto": f"p = {p}: tolera agotamiento moderado"}
    return {"nivel": "MEDIA-BAJA", "texto": f"p = {p}: raíz más profunda, tolera más agotamiento (sensible en floración/fructificación)"}


COOL_GDD = {"base_c": 4.4, "fuente": "WISC-GDD (base típica de hortalizas de clima fresco; verificar para el cultivo)"}

CROPS = [
    crop("lechuga", "Lechuga", "Lactuca sativa", "Asteraceae", "fresca", LEAF_STAGES, [25, 35, 30, 10],
         "25/35/30/10 = 100 d, Oct/Nov, Arid Region", (0.7, 1.00, 0.95), 0.30, [0.3, 0.5],
         soil_germ(35, 40, 80, 85), LEAFY, {"base_c": 4.4, "fuente": "PURDUE-GDD (lettuce 40 °F)"}, sens(0.30),
         "Raíz superficial: riego frecuente. El calor excesivo favorece la floración prematura."),
    crop("espinaca", "Espinaca", "Spinacia oleracea", "Amaranthaceae", "fresca", LEAF_STAGES, [20, 30, 40, 10],
         "20/30/40/10 = 100 d, November, Arid Region", (0.7, 1.00, 0.95), 0.20, [0.3, 0.5],
         soil_germ(35, 45, 75, 85), LEAFY, COOL_GDD, sens(0.20),
         "La más sensible al déficit hídrico de la lista (p = 0.20)."),
    crop("rabano", "Rábano", "Raphanus sativus", "Brassicaceae", "fresca", ROOT_STAGES, [10, 10, 15, 5],
         "10/10/15/5 = 40 d, Winter, Arid Region", (0.7, 0.90, 0.85), 0.30, [0.3, 0.5],
         soil_germ(40, 45, 90, 95), PENDIENTE, COOL_GDD, sens(0.30),
         "Ciclo muy corto; la humedad irregular puede agrietar la raíz."),
    crop("zanahoria", "Zanahoria", "Daucus carota", "Apiaceae", "fresca", ROOT_STAGES, [20, 30, 50, 20],
         "20/30/50/20 = 120 d, Oct/Jan, Arid climate (FAO da 50/30 d en etapa media)", (0.7, 1.05, 0.95), 0.35,
         [0.5, 1.0], soil_germ(40, 45, 85, 95), PENDIENTE, COOL_GDD, sens(0.35),
         "La germinación requiere superficie húmeda constante."),
    crop("cebolla", "Cebolla (bulbo)", "Allium cepa", "Amaryllidaceae", "fresca", ["Establecimiento", "Desarrollo de hojas", "Formación de bulbo", "Maduración y cosecha"],
         [20, 35, 110, 45], "20/35/110/45 = 210 d, Oct; Jan, Arid Region; Calif.", (0.7, 1.05, 0.75), 0.30,
         [0.3, 0.6], soil_germ(35, 50, 95, 95), PENDIENTE, COOL_GDD, sens(0.30),
         "Reducir el riego al madurar el bulbo (Kc final 0.75)."),
    crop("tomate", "Tomate", "Solanum lycopersicum", "Solanaceae", "cálida", FRUIT_STAGES, [30, 40, 40, 25],
         "30/40/40/25 = 135 d, January, Arid Region", (0.6, 1.15, 0.80), 0.40, [0.7, 1.5],
         soil_germ(50, 70, 95, 95), TOMATO, {"base_c": 10.0, "fuente": "PURDUE-GDD (tomato 50 °F)"}, sens(0.40),
         "Riego irregular en fructificación favorece pudrición apical y rajado. Kc final 0.70-0.90 (FAO)."),
    crop("pimiento", "Pimiento / chile morrón", "Capsicum annuum", "Solanaceae", "cálida", FRUIT_STAGES,
         [30, 35, 40, 20], "25-30/35/40/20 = 125 d, April/June, Europe and Medit.", (0.6, 1.05, 0.90), 0.30,
         [0.5, 1.0], soil_germ(60, 65, 95, 95), PEPPER,
         {"base_c": 10.0, "fuente": "WISC-GDD (umbral común 50 °F para cultivos de clima cálido; verificar)"}, sens(0.30),
         "Sensible al déficit en floración: caída de flores."),
    crop("pepino", "Pepino", "Cucumis sativus", "Cucurbitaceae", "cálida", FRUIT_STAGES, [20, 30, 40, 15],
         "20/30/40/15 = 105 d, June/Aug, Arid Region", (0.6, 1.00, 0.75), 0.50, [0.7, 1.2],
         soil_germ(60, 60, 95, 105), CUCURB, {"base_c": 12.8, "fuente": "PURDUE-GDD (cucumber 55 °F)"}, sens(0.50),
         "Kc ini 0.6 (mercado fresco, FAO). Fruto con alto contenido de agua: evitar déficit en fructificación."),
    crop("calabacita", "Calabacita", "Cucurbita pepo", "Cucurbitaceae", "cálida", FRUIT_STAGES, [25, 35, 25, 15],
         "25/35/25/15 = 100 d, Apr; Dec, Medit.; Arid Reg.", (0.5, 0.95, 0.75), 0.50, [0.6, 1.0],
         soil_germ(60, 70, 95, 100), CUCURB, {"base_c": 7.2, "fuente": "PURDUE-GDD (squash 45 °F; fuente única, verificar)"},
         sens(0.50), "Cosecha escalonada desde la etapa media."),
    crop("frijol_ejotero", "Frijol ejotero", "Phaseolus vulgaris", "Fabaceae", "cálida", FRUIT_STAGES, [20, 30, 30, 10],
         "20/30/30/10 = 90 d, Feb/Mar, Calif., Mediterranean", (0.5, 1.05, 0.90), 0.45, [0.5, 0.7],
         soil_germ(60, 65, 85, 95), PENDIENTE, {"base_c": 10.0, "fuente": "PURDUE-GDD (snap bean 50 °F)"}, sens(0.45),
         "Kc ini 0.5 (FAO, ejote). Sensible al déficit en floración y llenado de vaina."),
]

SOURCES = {
    "FAO56-T11": "FAO Riego y Drenaje 56, Tabla 11 - https://www.fao.org/4/x0490e/x0490e0b.htm",
    "FAO56-T12": "FAO Riego y Drenaje 56, Tabla 12 - https://www.fao.org/4/x0490e/x0490e0b.htm",
    "FAO56-T22": "FAO Riego y Drenaje 56, Tabla 22 y Ec. 82-83 - https://www.fao.org/4/x0490e/x0490e0e.htm",
    "ACES-1061": "Alabama Cooperative Extension System ANR-1061 - https://www.aces.edu/wp-content/uploads/2023/03/ANR-1061_SoilTemperatureConditionsforVegetableSeedGermination_030623bL-G.pdf",
    "WVU-HT": "West Virginia University / SARE, Temperature Management in High Tunnels - https://sare.org/wp-content/uploads/Temperature-Management-in-High-Tunnels.pdf",
    "PURDUE-GDD": "Purdue MRCC, Growing Degree Day description - https://mrcc.purdue.edu/resources/growing-degree-day-description",
    "WISC-GDD": "University of Wisconsin Extension (hort.extension.wisc.edu) - umbral GDD comun 50 F; clima fresco 40 F",
}

if __name__ == "__main__":
    out = {"version": 1, "generado": "2026-10-11", "fuentes": SOURCES,
           "metodo_umbrales_vwc": {
               "formula": "theta(d) = thetaFC - d*(thetaFC - thetaWP); d = fraccion de agotamiento del agua disponible (TAW)",
               "maxima": "d = 0 (capacidad de campo)",
               "reserva": "d = min(0.10, p/4)",
               "objetivo": "d = p_aj/2",
               "minima": "d = p_aj (inicio de estres, RAW = p*TAW)",
               "emergencia": "d = min(p_aj + 0.20, 0.85)",
               "p_aj": "p + 0.04*(5 - ETc), ETc = Kc_etapa * ET0 (Open-Meteo), limitado a 0.1-0.8",
               "requisito": "thetaFC y thetaWP medidos con el EC-5 en el suelo real; sin ellos: PENDIENTE_DE_CALIBRACION"},
           "cultivos": CROPS}
    path = os.path.join(os.path.dirname(__file__), "cultivos_base.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("Escrito", path, len(CROPS), "cultivos")
