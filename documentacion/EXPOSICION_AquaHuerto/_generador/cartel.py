"""Cartel cientifico 90 x 120 cm (vertical) en PowerPoint editable."""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Cm, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from doc import INTEGRANTES
from rutas import FIG, REP_IMG

VERDE = RGBColor(0x1B, 0x5E, 0x20)
VERDE_CL = RGBColor(0xE8, 0xF5, 0xE9)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
GRIS = RGBColor(0x45, 0x45, 0x45)
W, H = 90, 120


def caja(s, x, y, w, h, fill=None, line=None):
    r = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(x), Cm(y), Cm(w), Cm(h))
    r.adjustments[0] = 0.03
    if fill:
        r.fill.solid()
        r.fill.fore_color.rgb = fill
    else:
        r.fill.background()
    if line:
        r.line.color.rgb = line
        r.line.width = Pt(2)
    else:
        r.line.fill.background()
    r.shadow.inherit = False
    return r


def texto(s, x, y, w, h, parrafos, size=24, color=GRIS, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(Cm(x), Cm(y), Cm(w), Cm(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, par in enumerate(parrafos):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(size * 0.35)
        partes = par.split('**')
        for k, t in enumerate(partes):
            if not t:
                continue
            r = p.add_run()
            r.text = t
            r.font.size = Pt(size)
            r.font.bold = bold or k % 2 == 1
            r.font.color.rgb = color
            r.font.name = 'Calibri'
    return tb


def seccion(s, x, y, w, titulo):
    b = caja(s, x, y, w, 2.6, fill=VERDE)
    texto(s, x + 0.6, y + 0.2, w - 1, 2.3, [titulo], size=40, color=BLANCO, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    return y + 3.2


def imagen(s, path, x, y, w=None, h=None):
    with Image.open(path) as im:
        iw, ih = im.size
    if w and h:
        if iw / ih > w / h:
            h2 = w * ih / iw
            y += (h - h2) / 2
            h = h2
        else:
            w2 = h * iw / ih
            x += (w - w2) / 2
            w = w2
    elif w:
        h = w * ih / iw
    s.shapes.add_picture(path, Cm(x), Cm(y), Cm(w), Cm(h))
    return y + h


def alto(parrafos, size, w):
    import math
    cm_pt = 0.03528
    cpl = max(10, int(w / (size * cm_pt * 0.47)))
    lineas = sum(max(1, math.ceil(len(p.replace('**', '')) / cpl)) for p in parrafos)
    return lineas * size * cm_pt * 1.22 + len(parrafos) * size * cm_pt * 0.35 + 0.6


def bloque(s, x, y, w, parrafos, size=30):
    h = alto(parrafos, size, w)
    texto(s, x, y, w, h, parrafos, size=size)
    return y + h + 0.6


def cartel(salida):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Cm(W), Cm(H)
    s = prs.slides.add_slide(prs.slide_layouts[6])
    caja(s, 0, 0, W, 17, fill=VERDE)
    texto(s, 2, 1.2, W - 4, 6, ['AquaHuerto Escolar'], size=110, color=BLANCO, bold=True)
    texto(s, 2, 7.0, W - 4, 3, ['Sistema mecatrónico de riego inteligente con IA y energía solar para huertos escolares'],
          size=40, color=RGBColor(0xC8, 0xE6, 0xC9))
    texto(s, 2, 10.6, W - 4, 3.6, ['   ·   '.join(n for n, _ in INTEGRANTES[:4]), '   ·   '.join(n for n, _ in INTEGRANTES[4:])],
          size=26, color=BLANCO)
    texto(s, 2, 14.3, W - 4, 2, ['Equipo 2 · Tecnológico de Monterrey, Campus Chihuahua · Escuela Primaria Federal Belisario Domínguez'],
          size=22, color=RGBColor(0xC8, 0xE6, 0xC9))
    M, G = 2, 2
    CW = (W - 2 * M - G) / 2
    X1, X2 = M, M + CW + G
    BS = 30
    # ---------------- columna 1
    y = 19
    y = seccion(s, X1, y, CW, 'Introducción')
    y = bloque(s, X1, y, CW, ['La agricultura usa cerca del **72 %** del agua dulce del mundo. En las escuelas, el huerto se riega por '
                              'horario o cuando alguien se acuerda: se desperdicia agua y las plantas sufren en fines de semana y vacaciones.',
                              '**Pregunta:** ¿se puede regar un huerto escolar solo cuando la tierra lo necesita, midiendo cada litro, '
                              'sin depender de Internet y con energía solar?'], BS)
    y = seccion(s, X1, y, CW, 'Objetivos')
    y = bloque(s, X1, y, CW, ['**General:** diseñar, construir y probar un sistema de riego que decida con mediciones reales de humedad, '
                              'nivel y caudal, entregue volúmenes medidos y se proteja ante fallas.',
                              '• Medir la humedad volumétrica del suelo con un sensor calibrado.',
                              '• Regar por volumen y por dosis con tiempo de infiltración.',
                              '• Detectar falta de agua, flujo excesivo y tiempos máximos.',
                              '• Tres modos: MANUAL, AUTOMÁTICO e IA que aprende del huerto.'], BS)
    y = seccion(s, X1, y, CW, 'Metodología')
    y = bloque(s, X1, y, CW, ['Diseño mecatrónico: QFD → concepto → CAD y AMEF → EPANET → construcción → firmware en C (ESP-IDF) → '
                              'servidor en Raspberry Pi → pruebas automáticas, de campo y con agua.'], BS)
    y = imagen(s, os.path.join(FIG, 'fig_arquitectura.png'), X1, y, w=CW) + 0.8
    y = imagen(s, os.path.join(FIG, 'fig_diagrama_hidraulico.png'), X1, y, w=CW) + 0.3
    y = bloque(s, X1, y, CW, ['**EPANET:** 9 microaspersores × 30 L/h, 2.14 bar, uniformidad de presión 0.9998.'], 26)
    y1 = y
    # ---------------- columna 2
    y = 19
    y = seccion(s, X2, y, CW, 'Cómo funciona')
    y = bloque(s, X2, y, CW, ['• **Sensores:** EC-5 (humedad del suelo), PING))) (nivel del tinaco), DHT22 (aire), YF-S201 (litros).',
                              '• **ESP32:** decide cada 5 min con umbrales FAO-56 del cultivo; riega por dosis de 1.5 L con 15 min de infiltración.',
                              '• **Seguridad:** válvula → 1.5 s → bomba; corte sin flujo (45 s); tope de bomba 5.5 min; nunca riega al encender.',
                              '• **IA:** dos modelos que aprenden en línea (RLS) cuánto sube la humedad por litro y cuánto se seca por hora.'], BS)
    y = imagen(s, os.path.join(FIG, 'fig_flujo_ia.png'), X2 + 11, y, w=CW - 22) + 0.6
    y = seccion(s, X2, y, CW, 'Resultados')
    y = imagen(s, os.path.join(FIG, 'fig_riegos_reales.png'), X2, y, w=CW) + 0.4
    y = imagen(s, os.path.join(FIG, 'fig_resumen_pruebas.png'), X2 + 3, y, w=CW - 6) + 0.4
    y = bloque(s, X2, y, CW, ['• Riego real de **2.051 L en 42.8 s** (meta 2.0 L) y STOP inmediato.',
                              '• Corte por falta de agua correcto en **11 eventos reales**.',
                              '• Calibración del EC-5: **R² = 0.945**.',
                              '• Riega solo en el huerto desde el **21 de octubre de 2026**.'], BS)
    y = seccion(s, X2, y, CW, 'Conclusiones')
    y = bloque(s, X2, y, CW, ['AquaHuerto riega solo cuando la tierra lo necesita, mide cada litro y se protege ante fallas, aun sin '
                              'Internet. Siguiente paso: relé automotriz, diodos y capacitor; calibrar el caudalímetro con recipiente; '
                              'medir la energía y validar la IA con plantas.'], BS)
    y2 = y
    # ---------------- fotos y referencias
    fy = max(y1, y2) + 0.5
    fotos = ['f_cajon.jpg', 'f_tinaco_salida.jpg', 'f_ultrasonico.jpg', 'f_gabinete_esp32.jpg', 'd_inicio_panel.jpg']
    fw = (W - 2 * M - 4 * 1.0) / 5
    fh = min(10, H - fy - 6.5)
    for i, f in enumerate(fotos):
        imagen(s, os.path.join(REP_IMG, f), M + i * (fw + 1.0), fy, w=fw, h=fh)
    texto(s, M, fy + fh + 0.6, W - 2 * M, 5, [
        '**Referencias:** Allen et al. (1998), FAO-56 · FAO (2021), SOLAW · Haykin (2014), Adaptive filter theory · '
        'Rossman et al. (2020), EPANET 2.2 · Espressif (2026), ESP-IDF · Vallejo-Gómez et al. (2023), Agronomy 13(2) · '
        'Moustafa et al. (2026), Agric. Water Manag. 333 · METER Group, EC-5. Lista completa en la bibliografía del proyecto.'],
          size=18)
    print('cartel: columna 1 termina en', round(y1, 1), 'cm; columna 2 en', round(y2, 1), 'cm; fotos en', round(fy, 1), 'alto', round(fh, 1))
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    prs.save(salida)
    return salida
