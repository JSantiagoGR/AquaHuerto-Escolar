"""Genera el reporte Word del sistema de riego v3 (escenario A, construido).
Uso (desde la carpeta 3):
    python reporte/generar_figuras.py      # figuras + datos_reporte.json
    python reporte/generar_reporte.py      # Reporte_Riego_Automatizado_v3.docx
Los datos de portada se editan en PORTADA. Los números salen de resultados_calculo.json (generar_modelo.py)."""
import csv, json, os, re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, Inches, RGBColor

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SALIDA = os.path.join(AQUI, "Reporte_Riego_Automatizado_v3.docx")
D = json.load(open(os.path.join(AQUI, "datos_reporte.json"), encoding="utf8"))
DIMS = json.load(open(os.path.join(AQUI, "dims.json"), encoding="utf8"))

# ---------------------------------------------------------------- PORTADA (editar aquí) -----
PORTADA = {
    "institucion": "Instituto Tecnológico y de Estudios Superiores de Monterrey",
    "escuela": "Escuela de Ingeniería y Ciencias",
    "campus": "Campus [CAMPUS]",
    "materia": "[CLAVE] Automatización industrial — Grupo [GRUPO]",
    "titulo": "Diseño, modelado hidráulico en EPANET e implementación de un sistema de riego automatizado por aspersión para un huerto elevado",
    "subtitulo": "Reporte técnico del reto",
    "integrantes": [("[NOMBRE COMPLETO 1]", "[MATRÍCULA]"), ("[NOMBRE COMPLETO 2]", "[MATRÍCULA]"),
                    ("[NOMBRE COMPLETO 3]", "[MATRÍCULA]"), ("[NOMBRE COMPLETO 4]", "[MATRÍCULA]"),
                    ("[NOMBRE COMPLETO 5]", "[MATRÍCULA]")],
    "profesor": "[NOMBRE DEL PROFESOR(A)]",
    "lugar_fecha": "[Ciudad], [día] de [mes] de 2026",
}

FUENTE = "Arial"
AZUL = RGBColor(0x1F, 0x3A, 0x5F)
rows = {r["id"]: r for r in D["rows"]}
res, esc, geo, nodes, links = D["res"], D["esc"], D["geo"], D["nodes"], D["links"]


def f(x, n=3):
    return f"{x:,.{n}f}".replace(",", " ")


# ---------------------------------------------------------------- utilidades XML ------------
def campo(par, instr, texto="Actualice los campos (F9)"):
    r = par.add_run(); e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "begin"); r._r.append(e)
    r = par.add_run(); t = OxmlElement("w:instrText"); t.set(qn("xml:space"), "preserve"); t.text = instr; r._r.append(t)
    r = par.add_run(); e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "separate"); r._r.append(e)
    par.add_run(texto)
    r = par.add_run(); e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r._r.append(e)


def sombrear(celda, color):
    tcPr = celda._tc.get_or_add_tcPr(); s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), color); tcPr.append(s)


def bordes_tabla(tabla, ver=True):
    tblPr = tabla._tbl.tblPr; b = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{lado}")
        if ver:
            e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "808080")
        else:
            e.set(qn("w:val"), "nil")
        b.append(e)
    tblPr.append(b)


def repetir_encabezado(fila):
    trPr = fila._tr.get_or_add_trPr(); e = OxmlElement("w:tblHeader"); e.set(qn("w:val"), "true"); trPr.append(e)


def no_partir(fila):
    trPr = fila._tr.get_or_add_trPr(); e = OxmlElement("w:cantSplit"); e.set(qn("w:val"), "true"); trPr.append(e)


# ---------------------------------------------------------------- documento -------------
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, m, Inches(1))
ANCHO = 6.5

st = doc.styles["Normal"]
st.font.name = FUENTE; st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
st.paragraph_format.space_after = Pt(6); st.paragraph_format.line_spacing = 1.15
for nivel, tam in ((1, 14), (2, 12), (3, 11)):
    h = doc.styles[f"Heading {nivel}"]
    h.font.name = FUENTE; h.font.size = Pt(tam); h.font.bold = True; h.font.color.rgb = AZUL
    h.element.rPr.rFonts.set(qn("w:asciiTheme"), FUENTE) if False else None
    rf = h.element.rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); h.element.rPr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), FUENTE)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    h.paragraph_format.space_before = Pt(14 if nivel == 1 else 10); h.paragraph_format.space_after = Pt(6)
    h.paragraph_format.keep_with_next = True

CONT = {"fig": 0, "tab": 0, "ec": 0, "num": 0}


def runs(par, texto, size=None, color=None):
    """Texto con **negritas**, *cursivas*, x_{sub} y x^{sup}."""
    for trozo in re.split(r"(\*\*.+?\*\*|\*.+?\*|_\{.+?\}|\^\{.+?\})", texto):
        if not trozo:
            continue
        if trozo.startswith("**"):
            r = par.add_run(trozo[2:-2]); r.bold = True
        elif trozo.startswith("*"):
            r = par.add_run(trozo[1:-1]); r.italic = True
        elif trozo.startswith("_{"):
            r = par.add_run(trozo[2:-1]); r.font.subscript = True
        elif trozo.startswith("^{"):
            r = par.add_run(trozo[2:-1]); r.font.superscript = True
        else:
            r = par.add_run(trozo)
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
    return par


def P(texto, al=WD_ALIGN_PARAGRAPH.JUSTIFY, **kw):
    p = doc.add_paragraph(); p.alignment = al; return runs(p, texto, **kw)


def H(texto, nivel=1):
    return doc.add_heading(texto, level=nivel)


def viñeta(texto, estilo="List Bullet"):
    p = doc.add_paragraph(style=estilo); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(2); return runs(p, texto)


def numerada(texto, reiniciar=False):
    if reiniciar:
        CONT["num"] = 0
    CONT["num"] += 1
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT; p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Inches(0.4); p.paragraph_format.first_line_indent = Inches(-0.3)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(0.4))
    p.add_run(f"{CONT['num']}.	"); return runs(p, texto)


def ecuacion(texto, donde=None):
    CONT["ec"] += 1
    p = doc.add_paragraph(); p.paragraph_format.tab_stops.add_tab_stop(Inches(3.25), WD_TAB_ALIGNMENT.CENTER)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT)
    p.add_run("\t"); runs(p, texto); p.add_run(f"\t({CONT['ec']})")
    if donde:
        q = P(donde, size=10); q.paragraph_format.left_indent = Inches(0.4)
    return CONT["ec"]


def figura(ruta, titulo, nota="*Nota.* Elaboración propia.", ancho=6.0, alto_max=6.2):
    CONT["fig"] += 1
    w, h = DIMS.get(ruta.replace(os.sep, "/").split("EPANET/3/")[-1], (4, 3))
    if ancho * h / w > alto_max:
        ancho = alto_max * w / h
    p = doc.add_paragraph(); p.paragraph_format.keep_with_next = True; p.paragraph_format.space_after = Pt(0)
    runs(p, f"**Figura {CONT['fig']}**")
    p = doc.add_paragraph(); p.paragraph_format.keep_with_next = True; runs(p, f"*{titulo}*")
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(os.path.join(RAIZ, ruta), width=Inches(ancho))
    if nota:
        P(nota, al=WD_ALIGN_PARAGRAPH.LEFT, size=9.5)
    return CONT["fig"]


def figuras_lado(rutas, titulo, nota, alto=3.4):
    CONT["fig"] += 1
    p = doc.add_paragraph(); p.paragraph_format.keep_with_next = True; p.paragraph_format.space_after = Pt(0)
    runs(p, f"**Figura {CONT['fig']}**")
    p = doc.add_paragraph(); p.paragraph_format.keep_with_next = True; runs(p, f"*{titulo}*")
    t = doc.add_table(rows=2, cols=len(rutas)); bordes_tabla(t, False); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (ruta, sub) in enumerate(rutas):
        w, h = DIMS[ruta.replace("reporte/img/", "fotos_reales/")]
        c = t.cell(0, i); c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraphs[0].add_run().add_picture(os.path.join(RAIZ, ruta), height=Inches(alto) if w / h < 1.2 else None,
                                               width=None if w / h < 1.2 else Inches(ANCHO / len(rutas) - 0.15))
        c2 = t.cell(1, i); c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER; runs(c2.paragraphs[0], sub, size=9)
    no_partir(t.rows[0])
    P(nota, al=WD_ALIGN_PARAGRAPH.LEFT, size=9.5)
    return CONT["fig"]


def tabla(enc, filas, anchos, titulo, nota=None, tam=9, alinear=None):
    CONT["tab"] += 1
    p = doc.add_paragraph(); p.paragraph_format.keep_with_next = True; p.paragraph_format.space_after = Pt(0)
    runs(p, f"**Tabla {CONT['tab']}**")
    p = doc.add_paragraph(); p.paragraph_format.keep_with_next = True; runs(p, f"*{titulo}*")
    t = doc.add_table(rows=1 + len(filas), cols=len(enc)); bordes_tabla(t); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, e in enumerate(enc):
        c = t.cell(0, i); sombrear(c, "1F3A5F"); c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        pr = c.paragraphs[0]; pr.alignment = WD_ALIGN_PARAGRAPH.CENTER
        runs(pr, f"**{e}**", size=tam, color=RGBColor(255, 255, 255))
    repetir_encabezado(t.rows[0])
    for j, fila in enumerate(filas, 1):
        no_partir(t.rows[j])
        for i, v in enumerate(fila):
            c = t.cell(j, i); c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if j % 2 == 0:
                sombrear(c, "EEF2F7")
            pr = c.paragraphs[0]; pr.paragraph_format.space_after = Pt(0); pr.paragraph_format.line_spacing = 1.0
            pr.alignment = (alinear[i] if alinear else (WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER))
            runs(pr, str(v), size=tam)
    for fila in t.rows:
        for i, w in enumerate(anchos):
            fila.cells[i].width = Inches(w)
    if len(filas) <= 18:
        for fila in t.rows[:-1]:
            for c in fila.cells:
                for pr in c.paragraphs:
                    pr.paragraph_format.keep_with_next = True
    if nota:
        q = P(nota, al=WD_ALIGN_PARAGRAPH.LEFT, size=9.5); q.paragraph_format.space_before = Pt(3)
    else:
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return CONT["tab"]


def salto():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def leer_csv(nombre):
    with open(os.path.join(RAIZ, nombre), encoding="utf8") as fh:
        return list(csv.DictReader(fh))


# ================================================================= PORTADA ==================
for t, tam, neg in ((PORTADA["institucion"], 15, True), (PORTADA["escuela"], 12, False), (PORTADA["campus"], 12, False)):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; r = p.add_run(t); r.font.size = Pt(tam); r.bold = neg
p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(18); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run(PORTADA["materia"]); r.font.size = Pt(12)
p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(40); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run(PORTADA["titulo"]); r.bold = True; r.font.size = Pt(18); r.font.color.rgb = AZUL
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run(PORTADA["subtitulo"]); r.italic = True; r.font.size = Pt(12)
p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(36); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Integrantes del equipo"); r.bold = True
t = doc.add_table(rows=1 + len(PORTADA["integrantes"]), cols=2); bordes_tabla(t); t.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, e in enumerate(("Nombre", "Matrícula")):
    c = t.cell(0, i); sombrear(c, "1F3A5F"); c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    runs(c.paragraphs[0], f"**{e}**", color=RGBColor(255, 255, 255))
for j, (n, m) in enumerate(PORTADA["integrantes"], 1):
    t.cell(j, 0).text = n; t.cell(j, 1).text = m; t.cell(j, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
for fila in t.rows:
    fila.cells[0].width = Inches(3.6); fila.cells[1].width = Inches(1.6)
for t_, neg in ((f"Profesor(a): {PORTADA['profesor']}", False), (PORTADA["lugar_fecha"], False)):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(24); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(t_)

# ================================================================= ÍNDICE ===================
doc.add_section(WD_SECTION.NEW_PAGE)
p = doc.add_paragraph(); r = p.add_run("Índice"); r.bold = True; r.font.size = Pt(14); r.font.color.rgb = AZUL
campo(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(12)
r = p.add_run("Índice de figuras"); r.bold = True; r.font.size = Pt(12); r.font.color.rgb = AZUL
P("Las figuras y tablas se numeran en orden de aparición (formato APA 7.ª ed.).", size=9.5)

# pie de página con número (secciones 2 en adelante)
s2 = doc.sections[1]; s2.footer.is_linked_to_previous = False
fp = s2.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER; campo(fp, "PAGE", "1")
doc.sections[0].footer.is_linked_to_previous = False
salto()

# ================================================================= RESUMEN ==================
Q = res["Q_total_Lmin"]; Pmin, Pmax = res["P_min"], res["P_max"]
H("Resumen", 1)
P(f"Se diseñó, modeló e implementó un sistema de riego automatizado por aspersión para un huerto elevado (cajón de 1 × 1 m). "
  f"El agua sale del tinaco existente, pasa por la instalación previa (válvula de bola, check y bajada de Tuboplus) y es impulsada "
  f"por una bomba de diafragma de 12 V; después atraviesa un caudalímetro YF-S201 y una electroválvula normalmente cerrada, recorre "
  f"la línea principal de Tuboplus de 20 mm, sube verticalmente hasta 1.52 m y se reparte en una cruz hacia **3 líneas paralelas de "
  f"manguera con 3 aspersores cada una (9 aspersores)**. La red se modeló en EPANET 2.2 (unidades LPS, fórmula de Darcy-Weisbach) con "
  f"43 nodos y 43 enlaces, y se verificó con cálculo manual y con otros tres motores (WNTR, EPyT y el servidor MCP de EPANET). Con el "
  f"caudal nominal provisional de 30 L/h por aspersor (Q = {Q:.2f} L/min), la presión en los aspersores resultó de {Pmin:.2f}–{Pmax:.2f} m "
  f"(≈ {Pmin * 0.0981:.2f} bar), con una relación Pmin/Pmax de {res['uniformidad_hidraulica_presion_PminPmax']:.4f}; la velocidad en la "
  f"línea principal fue de {res['V_principal']:.2f} m/s. Las presiones son preliminares porque el fabricante no publica la curva "
  f"carga-caudal de la bomba. El sistema se armó en sitio y funcionó; el control con ESP32 mide el volumen con el YF-S201 (450 pulsos/L) "
  f"y apaga la bomba al completar 5 L por riego. Se listan las mediciones físicas pendientes con las que se actualizará el modelo.")
p = P("**Palabras clave:** EPANET, riego por aspersión, Darcy-Weisbach, bomba de diafragma, ESP32, Tuboplus.")

# ================================================================= 1 INTRODUCCIÓN ===========
H("1. Introducción", 1)
P("El riego manual de un huerto escolar depende de la disponibilidad de las personas y suele aplicar volúmenes irregulares. "
  "Automatizarlo exige resolver dos problemas a la vez: uno hidráulico (llevar el agua desde el tinaco hasta los aspersores con "
  "presión y caudal suficientes) y otro de control (decidir cuándo regar y cuánta agua aplicar). Este reporte documenta ambos para "
  "el huerto elevado del reto.")
P("La parte hidráulica se resolvió con EPANET 2.2, el programa de la Agencia de Protección Ambiental de Estados Unidos (EPA) para "
  "simular redes a presión (Rossman et al., 2020). Aunque EPANET suele usarse en redes municipales, sus ecuaciones son las mismas para "
  "una red pequeña: conservación de masa en los nodos y de energía en los tramos, con pérdidas por fricción y por accesorios. La parte "
  "de control usa un microcontrolador ESP32 que cuenta los pulsos del caudalímetro y gobierna la bomba (Espressif Systems, 2024).")
P("El documento describe el sistema construido, los datos y supuestos del modelo, los cálculos hidráulicos tramo por tramo, los "
  "resultados de EPANET, el análisis de sensibilidad, la lógica de control, la lista de materiales y las mediciones que faltan para "
  "cerrar el modelo con datos reales.")

# ================================================================= 2 OBJETIVOS ==============
H("2. Objetivos", 1)
H("2.1 Objetivo general", 2)
P("Diseñar, modelar en EPANET e implementar un sistema de riego por aspersión automatizado que distribuya agua del tinaco existente "
  "a 9 aspersores sobre un cajón de cultivo de 1 × 1 m, controlando el volumen aplicado con un sensor de flujo y un microcontrolador.")
H("2.2 Objetivos específicos", 2)
for t in ("Definir el trazado físico (diseño principal con subida vertical) y todas las conexiones desde el tinaco hasta los aspersores.",
          "Construir el modelo hidráulico en EPANET 2.2 con datos oficiales de la tubería y de los accesorios.",
          "Calcular a mano velocidades, número de Reynolds, factores de fricción y pérdidas, y compararlos con EPANET.",
          "Evaluar la presión en los 9 aspersores, el punto de operación de la bomba y la sensibilidad a los datos inciertos.",
          "Describir el sistema de control por volumen con ESP32 y caudalímetro YF-S201.",
          "Identificar las mediciones físicas necesarias para validar y actualizar el modelo."):
    viñeta(t)

# ================================================================= 3 MARCO TEÓRICO ===========
H("3. Marco teórico", 1)
H("3.1 Ecuación de la energía", 2)
P("Entre dos puntos 1 y 2 de una tubería con una bomba intermedia, la ecuación de la energía (Bernoulli extendida) es "
  "(Çengel & Cimbala, 2018; Mott & Untener, 2015):")
ecuacion("z_{1} + p_{1}/γ + V_{1}^{2}/2g + h_{B} = z_{2} + p_{2}/γ + V_{2}^{2}/2g + h_{f} + h_{m}",
         "donde z es la elevación (m), p/γ la carga de presión (m), V la velocidad (m/s), h_{B} la carga que aporta la bomba, "
         "h_{f} las pérdidas por fricción y h_{m} las pérdidas menores (accesorios). EPANET trabaja con la carga piezométrica H = z + p/γ.")
H("3.2 Caudal, velocidad y número de Reynolds", 2)
ecuacion("V = Q / A = 4Q / (πD^{2})")
ecuacion("Re = V·D / ν", "con ν = 1.0 × 10^{-6} m²/s (agua a 20 °C). Re < 2000: laminar; 2000–4000: transición; > 4000: turbulento.")
H("3.3 Pérdidas por fricción: Darcy-Weisbach", 2)
ecuacion("h_{f} = f · (L/D) · V^{2}/2g")
P("En régimen laminar f = 64/Re. En régimen turbulento f se obtiene de la ecuación de Colebrook (1939), que EPANET aproxima con la "
  "fórmula explícita de Swamee y Jain (1976):")
ecuacion("1/√f = −2 log_{10}( ε/(3.7D) + 2.51/(Re√f) )",
         "con rugosidad absoluta ε = 0.007 mm para PP-R Tuboplus (Rotoplas, 2017). Como comparación se usó Hazen-Williams con C = 150.")
H("3.4 Pérdidas menores", 2)
ecuacion("h_{m} = K · V^{2}/2g",
         "K se toma de la Tabla 10 del Manual Técnico Tuboplus para codos, conectores y tees (Rotoplas, 2017) y de Crane Co. (2010) "
         "para válvulas. Para la electroválvula se usa el coeficiente de flujo K_{v}: Δp[bar] = (Q[m³/h]/K_{v})^{2} (IEC, 2011).")
H("3.5 Bomba y punto de operación", 2)
P("La bomba entrega una carga h_{B} que disminuye al aumentar el caudal (curva carga-caudal). El punto de operación es el caudal "
  "con el que la carga de la bomba iguala la carga que exige el sistema. En este proyecto los aspersores se modelan con **demanda "
  "fija** (caudal impuesto), así que EPANET calcula qué carga entrega la bomba a ese caudal y con ello la presión en cada aspersor.")
H("3.6 EPANET 2.2", 2)
P("EPANET resuelve simultáneamente la continuidad en nodos y la energía en enlaces con el método del gradiente global (Todini & "
  "Pilati, 1988). Representa tinacos como *reservoirs* o *tanks*, tuberías como *pipes* (con K menor), bombas con su curva, válvulas "
  "check como tuberías CV y consumos como demandas en nodos (Rossman et al., 2020).")
H("3.7 Sensor de flujo YF-S201", 2)
P("El YF-S201 es un caudalímetro de turbina con sensor de efecto Hall. Su frecuencia de salida es F = 7.5·Q (F en Hz, Q en L/min), "
  "equivalente a 450 pulsos por litro, para un rango de 1 a 30 L/min (Handson Technology, s. f.).")

# ================================================================= 4 DESCRIPCIÓN ============
H("4. Descripción del sistema", 1)
H("4.1 Sitio e instalación construida", 2)
P("El sistema se instaló junto al edificio, alimentado por el tinaco negro ubicado a la derecha (Figura 1). El cajón de cultivo de "
  "1 × 1 m tiene un marco de madera que sostiene las líneas a 1.00 m sobre el borde superior del cajón. La subida de Tuboplus llega "
  "a la cruz y de ella salen las 3 mangueras negras con 3 aspersores rojos cada una (Figura 2). Las cajas grises del piso solo "
  "protegen la electrónica. **El sistema ya está armado y se probó en funcionamiento.**")
figura("reporte/img/F01_vista_general_tinaco_cajon.jpg", "Vista general: tinaco de alimentación (derecha), cajón y marco con las líneas de aspersión",
       "*Nota.* Fotografía tomada por el equipo, 2026.", ancho=4.0, alto_max=5.0)
figuras_lado([("reporte/img/F02_cajon_subida_y_cruz.jpg", "a) Subida de Tuboplus, cruz y laterales"),
              ("reporte/img/F03_lineas_y_aspersores.jpg", "b) Tres mangueras con 3 aspersores cada una")],
             "Detalle de la distribución sobre el cajón", "*Nota.* Fotografías tomadas por el equipo, 2026.", alto=3.6)

H("4.2 Componentes", 2)
P("La Tabla 1 resume los componentes. La bomba es de diafragma, autocebante, con presostato que la apaga al cerrarse el flujo "
  "(Figura 3). El dato de 0.9 MPa (130 psi) de la placa es la **presión de corte del presostato**, con caudal prácticamente nulo; "
  "no es la presión a 6 L/min (La Electrónica, s. f.).")
comp = [("Tinaco (existente)", "Agua a +1.19 m; salida 1/2\" a +0.265 m", "Reserva de agua"),
        ("Válvula de bola 1/2\" (existente)", "Paso completo", "Cierre manual"),
        ("Válvula check 1/2\" (existente)", "Columpio", "Evita retorno al tinaco"),
        ("Tubo Tuboplus PP-R clase 16", "20 mm, DI 14.40 mm, SDR 7.4", "Línea principal, subida y brazos"),
        ("Codos 90°, cruz, conectores, uniones mixtas Tuboplus", "20 mm; 20 × 1/2\"", "Cambios de dirección y transiciones"),
        ("Bomba de diafragma GOOD PUMPS", "12 V, 6 A, 72 W, 6 L/min máx., corte 0.9 MPa", "Impulsión"),
        ("Caudalímetro YF-S201", "G1/2, DI 11 mm, 1–30 L/min, 450 pulsos/L", "Medición de volumen"),
        ("Electroválvula NC 12 V DC", "1/2\"", "Apertura/cierre del riego"),
        ("Manguera negra", "DI ≈ 12 mm (por medir), 3 tramos ≈ 0.9 m", "Laterales"),
        ("Aspersores regulables (9)", "≈ 70 L/h máx.; nominal del modelo 30 L/h", "Riego"),
        ("ESP32 + relevador", "GPIO2 (bomba), GPIO4 (pulsos)", "Control por volumen")]
tabla(["Componente", "Especificación", "Función"], comp, [2.4, 2.4, 1.7], "Componentes principales del sistema",
      "*Nota.* Datos de placa, fichas técnicas y Rotoplas (2017). Elaboración propia.")
figuras_lado([("reporte/img/F04_bomba_placa.jpg", "a) Bomba y placa de datos"),
              ("reporte/img/F06_caja_bomba_etiqueta_SKU.jpg", "b) Etiqueta: 130 psi, 6 L/min, 12 V, 72 W"),
              ("reporte/img/F08_manguera_negra.jpg", "c) Manguera negra de los laterales")],
             "Bomba de diafragma y manguera utilizadas", "*Nota.* Fotografías tomadas por el equipo, 2026.", alto=2.6)

H("4.3 Recorrido y conexiones (tinaco → aspersores)", 2)
P("El recorrido completo, en el orden en que circula el agua, es el siguiente (Figuras 4 a 6):")
P("**Instalación existente (no se modificó):**", al=WD_ALIGN_PARAGRAPH.LEFT)
CONT["num"] = 0
for t in ("Tinaco → niple de salida 1/2\".", "Válvula de bola manual 1/2\" (abierta durante el riego).", "Válvula check 1/2\".",
          "Conector y tramo corto de Tuboplus 20 mm → T de Tuboplus.", "Bajada vertical de Tuboplus hasta z ≈ 0.08 m."):
    numerada(t)
P("**Equipos y línea nueva:**", al=WD_ALIGN_PARAGRAPH.LEFT)
for t in ("Codo 90° al pie de la bajada → tramo de Tuboplus → unión mixta 20 × 1/2\".",
          "Adaptación 1/2\" → puerto de la bomba (≈ 3/8\"; tipo de rosca por confirmar).",
          "**Bomba** → adaptación → unión mixta 20 × 1/2\" → niple de Tuboplus.",
          "Conector hembra 20 × 1/2\" → **caudalímetro YF-S201** → conector hembra → niple → conector hembra.",
          "**Electroválvula NC** → conector hembra 20 × 1/2\".",
          "Línea principal de Tuboplus hasta el cajón (≈ 2.74 m).",
          "Codo 90° → **subida vertical** de Tuboplus (0.08 → 1.52 m, ≈ 1.44 m) → codo 90°.",
          "Tramo corto horizontal de Tuboplus → **cruz** Tuboplus (z = 1.52 m)."):
    numerada(t)
P("**Salidas de la cruz (3 líneas):**", al=WD_ALIGN_PARAGRAPH.LEFT)
for t in ("**Línea 2 (centro):** salida recta → tubo → unión (conector hembra 20 × 1/2\") → espiga → manguera.",
          "**Líneas 1 y 3 (lados):** salida lateral → tubo (brazo ≈ 0.33 m) → codo 90° → tubo → unión → espiga → manguera.",
          "En cada manguera: aspersor a ≈ 0.145 m, segundo a 0.33 m, tercero a 0.33 m y tapón final; 3 × 3 = 9 aspersores."):
    viñeta(t)
figura("reporte/figuras/fig_bloques.png", "Diagrama de bloques del recorrido del agua")
figura("reporte/figuras/fig_elevacion.png", "Esquema en elevación del diseño construido (subida vertical)",
       "*Nota.* Elaboración propia. Longitudes estimadas, pendientes de medición (sección 11).")
figura("reporte/figuras/fig_planta.png", "Vista en planta del cajón: 3 líneas × 3 aspersores", ancho=4.2)

# ================================================================= 5 METODOLOGÍA ============
H("5. Metodología y modelo en EPANET", 1)
H("5.1 Procedimiento", 2)
CONT["num"] = 0
for t in ("Levantamiento del sitio y de las piezas (fotografías, placas y fichas técnicas).",
          "Definición del trazado y de las conexiones (sección 4.3).",
          "Generación paramétrica del archivo .inp con Python: todas las longitudes salen de una tabla de mediciones editable.",
          "Simulación en EPANET 2.2 y verificación con runepanet, WNTR (Klise et al., 2020), EPyT (Kyriakou et al., 2023) y el servidor MCP de EPANET.",
          "Cálculo manual tramo por tramo y comparación con EPANET.",
          "Análisis de sensibilidad de los datos inciertos (caudal, curva de bomba, manguera, K, nivel del tinaco)."):
    numerada(t)
H("5.2 Opciones y elementos del modelo", 2)
tabla(["Elemento", "Representación en EPANET"],
      [("Unidades / fórmula", "LPS (L/s, m) / Darcy-Weisbach; viscosidad relativa 1.0; precisión 0.00001"),
       ("Tinaco", "Reservoir R1 con carga 1.19 m (nivel de agua)"),
       ("Tuberías y mangueras", "Pipes con L, D interior, ε = 0.007 mm y K menor sobre la velocidad del tramo"),
       ("Válvula check", "Pipe con estado CV"),
       ("Electroválvula", "Pipe abierto con K = " + f"{D['K_EV']:.2f}" + " (equivalente a K_{v} = 3, estimado)"),
       ("Bomba", "Pump PU1 con curva de 3 puntos PROVISIONAL"),
       ("Aspersores", "9 nodos con demanda fija de 30 L/h (0.00833 L/s) a z = 1.52 m"),
       ("Tamaño", "43 nodos, 43 enlaces (42 tuberías + 1 bomba)")],
      [1.8, 4.7], "Configuración del modelo EPANET")
H("5.3 Coeficientes de pérdidas menores", 2)
tabla(["Accesorio", "K", "Fuente / estado"],
      [("Codo 90° Tuboplus", "2.00", "Rotoplas (2017), Tabla 10 — oficial"),
       ("Conector Tuboplus", "0.40", "Rotoplas (2017), Tabla 10 — oficial"),
       ("Cruz: paso recto / lateral", "1.80 / 2.20", "Equivalente a tee — provisional"),
       ("Entrada del tinaco", "0.50", "Crane Co. (2010) — estimado"),
       ("Válvula de bola paso completo", "0.08", "Crane Co. (2010) — estimado"),
       ("Válvula check", "2.70", "Crane Co. (2010) — estimado"),
       ("YF-S201", "2.00", "Estimado"),
       ("Electroválvula (K_{v} = 3)", f"{D['K_EV']:.2f}", "IEC 60534 — estimado"),
       ("Toma de cada aspersor", "1.00", "Estimado")],
      [2.6, 1.0, 2.9], "Coeficientes K utilizados")
H("5.4 Curva de la bomba", 2)
P("El fabricante no publica la curva carga-caudal. Con los dos datos disponibles (corte del presostato de 0.9 MPa ≈ 91.9 m con "
  "caudal nulo y 6 L/min máximo a descarga libre) se definió una curva **provisional** lineal de tres puntos: (0, 91.91 m), "
  "(0.05 L/s, 45.96 m) y (0.10 L/s, 0 m). Por eso las presiones calculadas son preliminares; la curva real se medirá con "
  "manómetro y probeta (sección 11).")

# ================================================================= 6 CÁLCULOS ===============
H("6. Cálculos hidráulicos", 1)
H("6.1 Caudal de diseño", 2)
ecuacion("Q = 9 × 30 L/h = 270 L/h = 4.5 L/min = 0.075 L/s",
         "Cada línea lleva 3 × 30 = 90 L/h = 0.025 L/s. El caudal está por debajo de los 6 L/min máximos de la bomba (margen 25 %) "
         "y dentro del rango del YF-S201 (1–30 L/min).")
H("6.2 Ejemplo de cálculo: línea principal (tramo N-D)", 2)
r = rows["N-D"]; g = 9.81
A_ = 3.141592653589793 * 0.0144 ** 2 / 4
P(f"Datos: L = {r['L']:.3f} m, D = 14.40 mm, Q = 0.075 L/s, K = {r['K']:.2f} (codo inferior de la subida + conector).")
ecuacion(f"A = π(0.0144)^{{2}}/4 = {A_:.4e} m²")
ecuacion(f"V = 0.075 × 10^{{-3}} / {A_:.4e} = {r['V']:.3f} m/s")
ecuacion(f"Re = ({r['V']:.3f})(0.0144) / 1.0 × 10^{{-6}} = {r['Re']:.0f}   → turbulento")
ecuacion(f"f (Colebrook, ε/D = {0.007 / 14.4:.2e}) = {r['f']:.4f}")
ecuacion(f"h_{{f}} = {r['f']:.4f} × ({r['L']:.3f}/0.0144) × {r['V']:.3f}^{{2}}/(2·9.81) = {r['hf']:.4f} m")
ecuacion(f"h_{{m}} = {r['K']:.2f} × {r['V']:.3f}^{{2}}/(2·9.81) = {r['hm']:.4f} m")
ecuacion(f"h_{{total}} = {r['hf']:.4f} + {r['hm']:.4f} = {r['hf'] + r['hm']:.4f} m   (EPANET: {r['hepanet'] if 'hepanet' in r else links['N-D']['hl']:.4f} m)")
P("La diferencia con EPANET es menor a 2 mm y se debe a que EPANET usa la aproximación explícita de Swamee-Jain y una "
  "interpolación en la zona de transición.")
H("6.3 Cálculo por tramo", 2)
P("La Tabla 4 presenta el cálculo de todos los tramos de la trayectoria principal y de la línea 1; las líneas 2 y 3 son "
  "equivalentes (la línea 2 no tiene brazo ni codo).")
orden = ["P-TK", "BOLA", "CHK", "EX-TB", "EX-BAJ", "N-A", "AD-IN", "AD-OUT", "N-B", "YF", "N-C", "EV", "N-D", "N-E", "N-H",
         "XO1", "ESP1", "HL11", "RA11", "HL12", "HL13", "XO2"]
fil = []
for k in orden:
    r = rows[k]
    fil.append((k, f"{r['L']:.3f}", f"{r['D']:.1f}", f"{r['Q'] * 1000 / 1000:.4f}", f"{r['V']:.3f}", f"{r['Re']:.0f}",
                r["reg"].split(" ")[0], f"{r['f']:.4f}", f"{r['K']:.2f}", f"{r['hf']:.4f}", f"{r['hm']:.4f}",
                f"{links[k]['hl']:.4f}"))
tabla(["Tramo", "L (m)", "D (mm)", "Q (L/s)", "V (m/s)", "Re", "Régimen", "f", "K", "h_{f} (m)", "h_{m} (m)", "EPANET (m)"],
      fil, [0.55, 0.45, 0.45, 0.55, 0.5, 0.5, 0.75, 0.5, 0.4, 0.55, 0.55, 0.6], "Cálculo hidráulico por tramo (Darcy-Weisbach)",
      "*Nota.* AD-IN/AD-OUT: adaptadores de los puertos de la bomba (D ≈ 7 mm); XO1/XO2: salidas de la cruz; ESP: espiga; HL: manguera; "
      "RA: toma del aspersor. Elaboración propia.", tam=7.5)
tot_hf = sum(r["hf"] for r in D["rows"]); tot_hm = sum(r["hm"] for r in D["rows"])
P(f"En toda la red, la pérdida por fricción suma {tot_hf:.3f} m y las pérdidas menores {tot_hm:.3f} m. Los adaptadores de los "
  f"puertos de la bomba concentran la mayor pérdida individual porque su diámetro pequeño (≈ 7 mm) eleva la velocidad a "
  f"{rows['AD-IN']['V']:.2f} m/s (Figura 7).")
figura("reporte/figuras/fig_perdidas.png", "Pérdidas de carga por grupo de componentes en la trayectoria al aspersor A13")
H("6.4 Balance de energía tinaco → aspersor más desfavorable (A13)", 2)
camino = ["P-TK", "BOLA", "CHK", "EX-TB", "EX-BAJ", "N-A", "AD-IN", "AD-OUT", "N-B", "YF", "N-C", "EV", "N-D", "N-E", "N-H",
          "XO1", "ESP1", "HL11", "HL12", "HL13", "RA13"]
perd = sum(links[k]["hl"] for k in camino); hb = res["H_bomba"]; pa = nodes["A13"]["P"]
ecuacion(f"1.19 + {hb:.2f} = 1.52 + p_{{A13}}/γ + {perd:.3f}")
ecuacion(f"p_{{A13}}/γ = 1.19 + {hb:.2f} − 1.52 − {perd:.3f} = {1.19 + hb - 1.52 - perd:.2f} m   (EPANET: {pa:.2f} m)")
P(f"La carga de velocidad en la toma del aspersor es despreciable frente a estos valores. La succión de la bomba queda a "
  f"{res['P_succion']:.2f} m (positiva), lo que confirma que la bomba recibe agua con carga del tinaco.")
figura("reporte/figuras/fig_perfil.png", "Perfil de carga piezométrica desde el tinaco hasta el aspersor A13")
H("6.5 Punto de operación de la bomba", 2)
P(f"Con 30 L/h por aspersor, la bomba opera en Q = {Q:.2f} L/min con una carga de {hb:.2f} m sobre la curva provisional "
  "(Figura 9). Para caudales mayores la carga cae rápidamente: con 40 L/h por aspersor (6 L/min) la bomba ya no aporta carga y "
  "aparecen presiones negativas, por lo que ese escenario no es viable.")
figura("reporte/figuras/fig_bomba.png", "Curva provisional de la bomba y puntos de operación para distintos caudales por aspersor", ancho=5.2)

# ================================================================= 7 RESULTADOS ============
H("7. Resultados de EPANET", 1)
P("El modelo corrió en la interfaz de EPANET 2.2 con el mensaje «Run was successful» y sin advertencias en el escenario nominal. "
  "Las Figuras 10 a 13 son capturas reales del programa.")
for ruta, t in (("capturas_epanet/00_Modelo_Limpio.png", "Modelo en EPANET 2.2: red completa del diseño construido"),
                ("capturas_epanet/01_Pressure_Flow.png", "EPANET 2.2: presión en nodos y caudal en enlaces"),
                ("capturas_epanet/02_Pressure_Velocity.png", "EPANET 2.2: presión en nodos y velocidad en enlaces"),
                ("capturas_epanet/03_Demand_UnitHeadloss.png", "EPANET 2.2: demanda en nodos y pérdida unitaria en enlaces")):
    figura(ruta, t, "*Nota.* Captura de EPANET 2.2 (Rossman et al., 2020). Elaboración propia.")
asp = [(f"A{i}{j}", f"L{i}", f"{nodes[f'A{i}{j}']['P']:.3f}", f"{nodes[f'A{i}{j}']['P'] * 0.0981:.3f}", "30.0")
       for i in (1, 2, 3) for j in (1, 2, 3)]
tabla(["Aspersor", "Línea", "Presión (m)", "Presión (bar)", "Caudal (L/h)"], asp, [1.1, 0.9, 1.3, 1.3, 1.3],
      "Presión en los 9 aspersores (escenario nominal)",
      "*Nota.* Presiones preliminares, dependientes de la curva provisional de la bomba. Elaboración propia.")
tabla(["Indicador", "Valor"],
      [("Caudal total", f"{Q:.2f} L/min ({res['Q_total_Ls']:.3f} L/s)"),
       ("Caudal por línea", "0.025 L/s (90 L/h)"),
       ("Presión en aspersores", f"{Pmin:.3f} – {Pmax:.3f} m"),
       ("Relación Pmin/Pmax", f"{res['uniformidad_hidraulica_presion_PminPmax']:.4f}"),
       ("Carga de la bomba", f"{hb:.2f} m"),
       ("Presión en la succión", f"{res['P_succion']:.2f} m"),
       ("Velocidad en la línea principal", f"{res['V_principal']:.3f} m/s"),
       ("Velocidad máxima en manguera", f"{res['V_manguera_max']:.3f} m/s"),
       ("Frecuencia del YF-S201", f"{res['YF_Hz']:.1f} Hz"),
       ("Margen respecto a 6 L/min", f"{res['margen_bomba_pct']:.0f} %")],
      [3.0, 3.0], "Resumen de resultados del escenario nominal")
P("La relación Pmin/Pmax cercana a 1 indica que **las presiones de los 9 aspersores son prácticamente iguales**, porque las "
  "pérdidas en la distribución son de milímetros. Esto no equivale a la uniformidad de riego, que depende del patrón de mojado, "
  "del radio de alcance y de la presión mínima del aspersor; esa uniformidad se debe medir con recipientes (sección 11).")

# ================================================================= 8 SENSIBILIDAD ===========
H("8. Análisis de sensibilidad", 1)
P("Como varios datos no están medidos, se simularon 20 escenarios en EPANET. La Tabla 7 resume los principales y la Figura 14 "
  "los grafica.")
nom = {"Q20": "20 L/h por aspersor", "Q25": "25 L/h por aspersor", "Q30": "30 L/h (nominal)", "Q35": "35 L/h por aspersor",
       "Q40": "40 L/h por aspersor", "Q70": "70 L/h por aspersor", "DH10": "Manguera DI 10 mm", "DH14": "Manguera DI 14 mm",
       "CURVA_x0.25": "Curva de bomba × 0.25", "CURVA_x0.50": "Curva de bomba × 0.50", "CURVA_x0.75": "Curva de bomba × 0.75",
       "HW150": "Hazen-Williams C = 150", "TINACO_MIN": "Tinaco casi vacío", "K_ALTOS": "K × 2 y K_{v} = 1",
       "K_BAJOS": "K × 0.5 y K_{v} = 6"}
fil = []
for k, t in nom.items():
    e = esc[k]; rr = e["r"]
    if e["ok"] and rr:
        fil.append((t, f"{rr['Q_total_Lmin']:.2f}", f"{rr['P_min']:.2f} – {rr['P_max']:.2f}", f"{rr['H_bomba']:.2f}", "Sí"))
    else:
        fil.append((t, "—", "presiones negativas", "—", "No"))
tabla(["Escenario", "Q (L/min)", "P aspersores (m)", "H bomba (m)", "Viable"], fil, [2.2, 0.9, 1.5, 1.0, 0.9],
      "Escenarios de sensibilidad", "*Nota.* Elaboración propia con EPANET 2.2.")
figura("reporte/figuras/fig_sensibilidad.png", "Sensibilidad de la presión mínima en los aspersores")
P("El parámetro dominante es la curva de la bomba: con la curva escalada a 0.25 la presión baja a ≈ 4.6 m, mientras que el diámetro "
  "de la manguera, los K y el nivel del tinaco cambian la presión en menos de 1.1 m. El caudal por aspersor está acotado por la "
  "bomba: 35 L/h es el máximo viable con la curva provisional; 40 L/h y 70 L/h no son viables (9 × 70 L/h = 10.5 L/min > 6 L/min).")

# ================================================================= 9 CONTROL ===============
H("9. Sistema de control", 1)
H("9.1 Arquitectura", 2)
P("Un ESP32 lee los pulsos del YF-S201 con el periférico contador de pulsos (PCNT) en el GPIO4 y activa la bomba mediante un "
  "relevador conectado al GPIO2 (Espressif Systems, 2024). La electroválvula NC se abre durante el riego y, al cortar, evita que "
  "el agua siga fluyendo por gravedad o por la presión residual. La electrónica se aloja en las cajas grises junto al cajón.")
H("9.2 Lógica de riego por volumen", 2)
P("El programa (Figura 15) espera 10 s, borra el contador, enciende la bomba y cada 100 ms lee los pulsos acumulados. Cuando "
  "se superan 5 L × 450 pulsos/L = 2250 pulsos, apaga la bomba y reporta el total.")
figura("reporte/figuras/fig_control.png", "Diagrama de flujo del programa de control por volumen", ancho=3.3)
H("9.3 Cálculos del control", 2)
ecuacion("N = V · k = 5 L × 450 pulsos/L = 2250 pulsos")
ecuacion(f"F = 7.5 · Q = 7.5 × {Q:.2f} = {7.5 * Q:.2f} Hz")
ecuacion(f"t_{{riego}} = V / Q = 5 L / {Q:.2f} L/min = {5 / Q:.2f} min ≈ {60 * 5 / Q:.0f} s")
ecuacion("lámina = V / A = 5 L / 1 m² = 5 mm por riego (≈ 0.56 L por aspersor)")
P("La frecuencia de 33.8 Hz es baja para el PCNT del ESP32, por lo que no hay riesgo de perder pulsos; el filtro de 1 µs elimina "
  "rebotes. El volumen por riego se ajusta cambiando la constante NUM_LITROS.")
H("9.4 Código implementado", 2)
P("Fragmento principal del programa en ESP-IDF (archivo main.c del proyecto control_riego_por_litro):")
codigo = """#define PCNT_INPUT_SIG_IO   4     // Entrada de pulsos (YF-S201)
#define PUMP_GPIO           2     // Salida a la bomba
#define PULSOS_X_LITRO    450     // 450 pulsos por litro
#define NUM_LITROS          5     // Litros por riego

gpio_set_level(PUMP_GPIO, TURN_ON);            // Encender bomba
while (1) {
    vTaskDelay(100 / portTICK_PERIOD_MS);
    pcnt_unit_get_count(pcnt_unit, &count);    // Leer pulsos
    if (count > (NUM_LITROS * PULSOS_X_LITRO)) fin_riego = 1;
    if (fin_riego) gpio_set_level(PUMP_GPIO, TURN_OFF);   // Apagar
}"""
for linea in codigo.split("\n"):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.left_indent = Inches(0.3); p.paragraph_format.keep_with_next = True
    r = p.add_run(linea if linea else " "); r.font.name = "Consolas"; r.font.size = Pt(8.5)
doc.add_paragraph()
P("En el código revisado solo se gobierna la salida de la bomba (GPIO2); la electroválvula debe energizarse junto con la bomba, "
  "ya sea por el mismo relevador o con una salida adicional. Esta conexión se confirmará al documentar el cableado final.")

# ================================================================= 10 MATERIALES ===========
H("10. Materiales y tubería Tuboplus", 1)
bom = leer_csv("BOM_hidraulico.csv")
fil = [(b["componente"], b["cantidad"], b["medida"], b["categoria"].capitalize()) for b in bom if "filtro" not in b["componente"].lower()]
tabla(["Componente", "Cantidad", "Medida", "Origen"], fil, [2.4, 1.2, 1.9, 1.0], "Lista de materiales hidráulicos",
      "*Nota.* Elaboración propia.", tam=8)
tr = geo["tramos"]
fil = [(t["tramo"], t["descripcion"], f"{t['distancia_m']:.3f}", str(t["cantidad"]), f"{t['corte_neto_m']:.3f}") for t in tr]
fil.append(("", "**Total Tuboplus nuevo (estimado)**", "", "", f"**{geo['nuevo_m']:.3f}**"))
tabla(["Tramo", "Descripción", "Distancia (m)", "Cant.", "Corte neto (m)"], fil, [0.5, 3.3, 1.0, 0.6, 1.1],
      "Cortes de Tuboplus nuevo del diseño construido",
      "*Nota.* Corte neto = distancia − tramo absorbido por las conexiones + inserción de termofusión. Valores estimados hasta "
      "registrar las mediciones de la sección 11. Elaboración propia.", tam=8.5)
P(f"Con las longitudes estimadas, el diseño requiere ≈ {geo['nuevo_m']:.2f} m de Tuboplus nuevo, frente a un presupuesto de compra "
  f"de 4.00 m (un tubo). El valor depende sobre todo de la línea principal (M5) y del tramo hacia la bomba (M1): el diseño cabe en "
  f"un tubo si M1 + M5 ≤ {geo['M1_M5_max_m']:.3f} m. La longitud real instalada se confirmará con las mediciones.")

# ================================================================= 11 PENDIENTES ===========
H("11. Mediciones y validaciones pendientes", 1)
P("El modelo está parametrizado: al registrar cada medición se regeneran el archivo .inp, las tablas, las figuras y este reporte. "
  "Las mediciones pendientes son:")
med = leer_csv("mediciones_fisicas.csv")
fil = [(m["clave_CONFIG"].split("_")[0], m["medicion"], m["valor_actual"], m["como_medir"]) for m in med]
tabla(["Clave", "Medición", "Valor actual", "Cómo medir"], fil, [0.6, 2.6, 0.9, 2.4], "Mediciones físicas pendientes",
      "*Nota.* Todos los valores actuales son estimados. Elaboración propia.", tam=8)
for t in ("**Curva real de la bomba:** manómetro, válvula y probeta a 12 V; al menos 5 puntos hasta el corte del presostato.",
          "**Ciclado del presostato** con los 9 aspersores: registrar presión, corriente y pulsos durante 5–10 min.",
          "**Aspersores:** marca, modelo, presión mínima y relación apertura-caudal.",
          "**Uniformidad de riego:** prueba con recipientes en malla sobre el cajón.",
          "**Rosca de los puertos de la bomba** (NPT o BSP) con galga.",
          "**K**_{v}** de la electroválvula** y pérdidas reales del YF-S201."):
    viñeta(t)

# ================================================================= 12 VALIDACIÓN ===========
H("12. Validación del modelo", 1)
tabla(["Herramienta", "Resultado"],
      [("EPANET 2.2 (interfaz gráfica)", "«Run was successful»; capturas de las Figuras 10–13"),
       ("runepanet.exe 2.2", "Corrida sin advertencias en el escenario nominal"),
       ("WNTR 1.5 y EPyT (OWA-EPANET 2.3)", "Caudales iguales a EPANET (diferencia < 1 × 10^{-5} L/s)"),
       ("Servidor MCP de EPANET", "43 nodos / 43 enlaces; presión mínima 0.86 m (succión)"),
       ("Script validar_modelo.py", "71 comprobaciones correctas, 3 avisos, 0 fallas"),
       ("Cálculo manual (Tabla 4)", "Diferencias con EPANET de milímetros por tramo"),
       ("Prueba física", "Sistema armado y probado: los aspersores funcionaron")],
      [2.5, 4.0], "Validación del modelo")
P("Los tres avisos del script corresponden a datos que solo se resuelven midiendo: la longitud real de Tuboplus, la uniformidad "
  "de riego y la presión requerida por los aspersores.")

# ================================================================= 13 CONCLUSIONES =========
H("13. Conclusiones", 1)
for t in (f"Se diseñó e implementó un sistema de riego automatizado con 3 líneas × 3 aspersores alimentado desde el tinaco existente; "
          f"el sistema se armó en sitio y funcionó.",
          f"El modelo de EPANET 2.2 predice, con el caudal nominal de 30 L/h por aspersor, presiones de ≈ {Pmin:.1f} m (≈ {Pmin * 0.0981:.1f} bar) "
          f"prácticamente iguales en los 9 aspersores; la distribución con cruz y mangueras cortas no introduce desbalance.",
          "Las pérdidas totales son de alrededor de 1 m; la mayor parte se concentra en los adaptadores de la bomba, la electroválvula y "
          "los codos, no en la longitud de la tubería.",
          "La variable que más afecta las presiones es la curva de la bomba, que no está publicada; medirla es la prioridad para cerrar el modelo.",
          "El caudal máximo viable con la curva provisional es de ≈ 35 L/h por aspersor; con 40 L/h o más la bomba no alcanza.",
          "El control por volumen con ESP32 y YF-S201 aplica 5 L (≈ 5 mm de lámina) en ≈ 67 s, y el volumen se ajusta con una constante.",
          "El modelo y este reporte están parametrizados: al registrar las mediciones reales se actualizan automáticamente."):
    viñeta(t)

# ================================================================= REFERENCIAS =============
H("Referencias", 1)
refs = [
    "Çengel, Y. A., & Cimbala, J. M. (2018). *Mecánica de fluidos: Fundamentos y aplicaciones* (4.ª ed.). McGraw-Hill Education.",
    "Colebrook, C. F. (1939). Turbulent flow in pipes, with particular reference to the transition region between the smooth and rough pipe laws. *Journal of the Institution of Civil Engineers, 11*(4), 133–156. https://doi.org/10.1680/ijoti.1939.13150",
    "Crane Co. (2010). *Flow of fluids through valves, fittings, and pipe* (Technical Paper No. 410). Crane Co.",
    "Espressif Systems. (2024). *ESP-IDF programming guide: Pulse counter (PCNT)*. https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/pcnt.html",
    "Handson Technology. (s. f.). *Water flow sensor YF-S201* [Hoja de datos]. https://handsontec.com/dataspecs/sensor/Water%20Flow%20Sensor.pdf",
    "International Electrotechnical Commission. (2011). *Industrial-process control valves — Part 2-1: Flow capacity — Sizing equations for fluid flow under installed conditions* (IEC 60534-2-1:2011). IEC.",
    "Klise, K. A., Hart, D. B., Bynum, M., Hogge, J., Haxton, T., Murray, R., & Burkhardt, J. (2020). *Water Network Tool for Resilience (WNTR) user manual* (EPA/600/R-20/185). U.S. Environmental Protection Agency.",
    "Kyriakou, M. S., Demetriades, M., Vrachimis, S. G., Eliades, D. G., & Polycarpou, M. M. (2023). EPyT: An EPANET-Python toolkit for smart water network simulations. *Journal of Open Source Software, 8*(92), 5947. https://doi.org/10.21105/joss.05947",
    "La Electrónica. (s. f.). *Bomba de diafragma automática de 12V y 6 L/min, recto a rosca 3/8*. https://laelectronica.com.gt/products/bomba-de-diafragma-automatica-de-12v-y-6-lmin-recto-a-rosca-38",
    "Mott, R. L., & Untener, J. A. (2015). *Mecánica de fluidos* (7.ª ed.). Pearson Educación.",
    "Rossman, L. A., Woo, H., Tryby, M., Shang, F., Janke, R., & Haxton, T. (2020). *EPANET 2.2 user manual* (EPA/600/R-20/133). U.S. Environmental Protection Agency.",
    "Rotoplas. (2017). *Manual técnico Tuboplus*. https://ferreambriz.com/wp-content/uploads/2024/08/MANUAL-TUBOPLUS.pdf",
    "Rotoplas. (s. f.). *Tubo clase 16 de 20 mm Tuboplus*. https://rotoplas.com.mx/product/Tubo-clase-16-de-20-mm-Tuboplus/",
    "Swamee, P. K., & Jain, A. K. (1976). Explicit equations for pipe-flow problems. *Journal of the Hydraulics Division, 102*(5), 657–664.",
    "Todini, E., & Pilati, S. (1988). A gradient algorithm for the analysis of pipe networks. En B. Coulbeck & C.-H. Orr (Eds.), *Computer applications in water supply: Vol. 1. Systems analysis and simulation* (pp. 1–20). Research Studies Press.",
]
for t in refs:
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.5); p.paragraph_format.first_line_indent = Inches(-0.5)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT; runs(p, t)

# quitar el subtítulo provisional de "Índice de figuras" (Word no genera la lista sin campos de leyenda)
cuerpo = doc.element.body
for par in list(doc.paragraphs):
    if par.text in ("Índice de figuras", "Las figuras y tablas se numeran en orden de aparición (formato APA 7.ª ed.)."):
        cuerpo.remove(par._p)

doc.save(SALIDA)
print("OK", SALIDA, "figuras:", CONT["fig"], "tablas:", CONT["tab"], "ecuaciones:", CONT["ec"])
