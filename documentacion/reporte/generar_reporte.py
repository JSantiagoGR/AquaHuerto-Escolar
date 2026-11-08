"""Genera el reporte técnico de AquaHuerto Escolar en Word (python-docx)."""
import os
from PIL import Image
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor, Inches

D = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(D, 'img')
OUT = os.path.join(D, 'Reporte_AquaHuerto_Equipo2.docx')
VERDE = RGBColor(0x1B, 0x5E, 0x20)
VERDE_HEX = '1B5E20'
GRIS = RGBColor(0x55, 0x55, 0x55)

# EPANET: solo el mapa de la red
ep = os.path.join(IMG, 'epanet_red.png')
Image.open(os.path.join(IMG, 'banda_humedad.png')).crop((0, 0, 1344, 285)).save(os.path.join(IMG, 'banda_recorte.png'))
Image.open(os.path.join(IMG, 'epanet.png')).crop((20, 290, 1412, 640)).save(ep)

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for s in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
    setattr(sec, s, Inches(1))

st = doc.styles['Normal']
st.font.name = 'Calibri'
st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
st.font.size = Pt(11)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.15
for lvl, size in ((1, 16), (2, 13), (3, 11.5)):
    h = doc.styles['Heading %d' % lvl]
    h.font.name = 'Calibri'
    rf = h.element.rPr.find(qn('w:rFonts'))
    if rf is not None:
        for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
            rf.attrib.pop(qn(a), None)
        rf.set(qn('w:ascii'), 'Calibri')
        rf.set(qn('w:hAnsi'), 'Calibri')
    h.font.size = Pt(size)
    h.font.bold = True
    h.font.color.rgb = VERDE if lvl < 3 else RGBColor(0x2E, 0x7D, 0x32)
    h.paragraph_format.space_before = Pt(18 if lvl == 1 else 12)
    h.paragraph_format.space_after = Pt(6)
    h.paragraph_format.keep_with_next = True


def campo(par, instr):
    r = par.add_run()
    for tag, extra in (('begin', None), (None, instr), ('separate', None), (None, None), ('end', None)):
        if tag:
            e = OxmlElement('w:fldChar')
            e.set(qn('w:fldCharType'), tag)
            r._r.append(e)
        elif extra:
            t = OxmlElement('w:instrText')
            t.set(qn('xml:space'), 'preserve')
            t.text = extra
            r._r.append(t)
    return r


def borde_inferior(par, color=VERDE_HEX, size=12):
    pPr = par._p.get_or_add_pPr()
    b = OxmlElement('w:pBdr')
    e = OxmlElement('w:bottom')
    for k, v in (('val', 'single'), ('sz', str(size)), ('space', '4'), ('color', color)):
        e.set(qn('w:' + k), v)
    b.append(e)
    pPr.append(b)


def sombrear(celda, hexcolor):
    tcPr = celda._tc.get_or_add_tcPr()
    sh = OxmlElement('w:shd')
    sh.set(qn('w:val'), 'clear')
    sh.set(qn('w:color'), 'auto')
    sh.set(qn('w:fill'), hexcolor)
    tcPr.append(sh)


def p(texto='', bold=False, italic=False, size=None, align=None, color=None, after=None, style=None):
    par = doc.add_paragraph(style=style)
    if texto:
        partes = texto.split('**')
        for i, t in enumerate(partes):
            if not t:
                continue
            r = par.add_run(t)
            r.bold = bold or (i % 2 == 1)
            r.italic = italic
            if size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = color
    if align is not None:
        par.alignment = align
    if after is not None:
        par.paragraph_format.space_after = Pt(after)
    return par


def J(texto):
    par = p(texto)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return par


def vinetas(items, estilo='List Bullet'):
    for it in items:
        par = p(it, style=estilo)
        par.paragraph_format.space_after = Pt(3)


FIG = [0]
TAB = [0]


def figura(nombre, titulo, ancho=6.0, nota='Elaboración propia.', alto_max=None):
    FIG[0] += 1
    a = p('Figura %d' % FIG[0], bold=True, after=0)
    a.paragraph_format.keep_with_next = True
    b = p(titulo, italic=True, after=4)
    b.paragraph_format.keep_with_next = True
    path = os.path.join(IMG, nombre)
    w, h = Image.open(path).size
    if alto_max and ancho * h / w > alto_max:
        ancho = alto_max * w / h
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.keep_with_next = True
    c.add_run().add_picture(path, width=Inches(ancho))
    n = p('', after=10)
    r = n.add_run('Nota. ')
    r.italic = True
    r.font.size = Pt(9.5)
    r2 = n.add_run(nota)
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = GRIS


def tabla(titulo, encabezado, filas, anchos, nota=None, fuente=9.5):
    TAB[0] += 1
    a = p('Tabla %d' % TAB[0], bold=True, after=0)
    a.paragraph_format.keep_with_next = True
    b = p(titulo, italic=True, after=4)
    b.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(encabezado))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, txt in enumerate(encabezado):
        c = t.rows[0].cells[i]
        c.text = ''
        r = c.paragraphs[0].add_run(txt)
        r.bold = True
        r.font.size = Pt(fuente)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombrear(c, VERDE_HEX)
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement('w:tblHeader')
    th.set(qn('w:val'), 'true')
    trPr.append(th)
    for k, fila in enumerate(filas):
        cells = t.add_row().cells
        for i, txt in enumerate(fila):
            cells[i].text = ''
            par = cells[i].paragraphs[0]
            for j, parte in enumerate(str(txt).split('**')):
                if parte:
                    r = par.add_run(parte)
                    r.bold = j % 2 == 1
                    r.font.size = Pt(fuente)
            if k % 2 == 1:
                sombrear(cells[i], 'EEF5EE')
    for row in t.rows:
        for i, w in enumerate(anchos):
            row.cells[i].width = Inches(w)
            row.cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for par in row.cells[i].paragraphs:
                par.paragraph_format.space_after = Pt(1)
                par.paragraph_format.line_spacing = 1.0
    if nota:
        n = p('', after=10)
        r = n.add_run('Nota. ')
        r.italic = True
        r.font.size = Pt(9.5)
        r2 = n.add_run(nota)
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = GRIS
    else:
        p('', after=4)


def ecuacion(texto):
    par = p(texto, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
    return par


def salto():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ================================================================ PORTADA
p('Tecnológico de Monterrey', bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, color=VERDE, after=0)
p('Campus Chihuahua', size=12, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
p('Escuela de Ingeniería y Ciencias', size=12, align=WD_ALIGN_PARAGRAPH.CENTER, after=18)
p('Automatización industrial · Reto', size=12, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, after=28)
t = p('AquaHuerto Escolar', bold=True, size=30, align=WD_ALIGN_PARAGRAPH.CENTER, color=VERDE, after=4)
s = p('Reporte técnico de implementación de un sistema de riego inteligente con ESP32, '
      'Raspberry Pi, monitoreo IoT y modelo predictivo', size=14, align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
borde_inferior(s, size=16)
p('Equipo 2', bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, after=24)
cov = doc.add_paragraph()
cov.alignment = WD_ALIGN_PARAGRAPH.CENTER
cov.add_run().add_picture(os.path.join(IMG, 'f_cajon.jpg'), height=Cm(4.3))
p('', after=10)
p('Integrantes', bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, color=VERDE, after=4)
INTEGRANTES = [
    ('Jaime Santiago Galaviz Reaza', ''),
    ('Victor Manuel Palicio Torres', ''),
    ('Eyra Cristal Garcia', ''),
]
ti = doc.add_table(rows=0, cols=2)
ti.alignment = WD_TABLE_ALIGNMENT.CENTER
for nombre, mat in INTEGRANTES:
    c = ti.add_row().cells
    for i, (txt, w) in enumerate(((nombre, 3.2), (mat, 1.3))):
        c[i].width = Inches(w)
        c[i].text = ''
        r = c[i].paragraphs[0].add_run(txt)
        r.font.size = Pt(11)
        c[i].paragraphs[0].paragraph_format.space_after = Pt(1)
        c[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.RIGHT
p('', after=6)
p('Chihuahua, Chihuahua, 2 de noviembre de 2026', size=11, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS)

# ================================================================ RESUMEN E ÍNDICE
nueva = doc.add_section(WD_SECTION.NEW_PAGE)
ft = nueva.footer
ft.is_linked_to_previous = False
fp = ft.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
campo(fp, 'PAGE')
hd = nueva.header
hd.is_linked_to_previous = False
hp = hd.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = hp.add_run('AquaHuerto Escolar · Reporte técnico · Equipo 2')
r.font.size = Pt(9)
r.font.color.rgb = GRIS
doc.sections[0].different_first_page_header_footer = True

doc.add_heading('Resumen', 1)
J('AquaHuerto Escolar es un sistema de riego automatizado para un cajón de cultivo de 1 × 1 m instalado en la '
  'Escuela Primaria Federal Belisario Domínguez, en Chihuahua. Un microcontrolador ESP32 mide la humedad volumétrica '
  'del suelo (sensor EC-5), el nivel del tinaco (ultrasónico PING))), la temperatura y la humedad del aire (DHT22) y '
  'el caudal (YF-S201), y controla una bomba de 12 V y una electroválvula normalmente cerrada. Las decisiones de riego '
  'se basan en umbrales agronómicos derivados de FAO-56 y de la capacidad de campo del sustrato, se aplican por dosis '
  'con espera de infiltración y se complementan con un modelo predictivo de mínimos cuadrados recursivos que aprende '
  'la respuesta del suelo al riego y su velocidad de secado. Una Raspberry Pi recibe la información por MQTT, la '
  'almacena en SQLite y la presenta en un dashboard de diez páginas. El sistema opera en producción desde el 21 de '
  'octubre de 2026; las pruebas físicas incluyen riegos por volumen de hasta 2.8 L, un autodiagnóstico en la placa '
  'de 51/51 pruebas y una prueba de campo de 28/28. Este documento describe la arquitectura, la implementación, los '
  'resultados, las mejoras de confiabilidad realizadas tras la puesta en marcha y los pendientes para considerar el '
  'sistema validado.')
p('**Palabras clave:** riego inteligente, ESP32, IoT, MQTT, humedad volumétrica, FAO-56, mínimos cuadrados recursivos.')

doc.add_heading('Índice', 1)
toc = doc.add_paragraph()
campo(toc, 'TOC \\o "1-2" \\h \\z \\u')
salto()

# ================================================================ 1. INTRODUCCIÓN
doc.add_heading('1. Introducción', 1)
J('La agricultura concentra alrededor del 72 % de las extracciones mundiales de agua dulce (FAO, 2021), por lo que '
  'aplicar el agua solo cuando el cultivo la necesita es una medida directa de sostenibilidad. En un huerto escolar el '
  'riego suele depender de horarios fijos o de que una persona esté disponible, lo que provoca exceso o falta de agua, '
  'bombas que operan sin nivel suficiente y poca información para el mantenimiento.')
J('Las revisiones recientes describen sistemas de riego inteligente que combinan sensores de humedad, variables '
  'ambientales, controladores embebidos y comunicación IoT para decidir con base en las condiciones reales del '
  'cultivo (Moustafa et al., 2026), incluso alimentados con energía solar y comunicados por MQTT (Al Mamun et al., '
  '2025). AquaHuerto Escolar aplica ese enfoque a escala de un prototipo escolar: el control es local y sigue '
  'funcionando sin internet, mientras que el servidor y el dashboard agregan registro, supervisión y análisis.')
doc.add_heading('1.1 Objetivo general', 2)
J('Diseñar, construir y poner en operación un sistema de riego automatizado y supervisado para un huerto escolar que '
  'riegue según la humedad medida del suelo, proteja el equipo ante fallas y registre su operación para el análisis y '
  'la mejora continua.')
doc.add_heading('1.2 Objetivos específicos', 2)
vinetas([
    'Medir humedad volumétrica del suelo, nivel del tinaco, temperatura, humedad relativa y caudal.',
    'Implementar tres modos de operación (MANUAL, AUTOMÁTICO e IA) con umbrales por cultivo y etapa.',
    'Proteger la bomba y la instalación con enclavamientos, límites de volumen y un supervisor independiente.',
    'Comunicar el ESP32 con un servidor mediante MQTT con confirmación de cada comando.',
    'Almacenar el historial y presentarlo en un dashboard accesible desde la red local.',
    'Documentar la operación y el mantenimiento mediante manuales de usuario.',
])

# ================================================================ 2. MARCO TEÓRICO
doc.add_heading('2. Marco teórico', 1)
doc.add_heading('2.1 Humedad volumétrica y necesidades hídricas', 2)
J('La humedad volumétrica (θ, %VWC) es el volumen de agua por unidad de volumen de suelo. Entre la capacidad de '
  'campo (FC), el agua que el suelo retiene tras drenar, y el punto de marchitez permanente (WP) se encuentra el agua '
  'útil para la planta. FAO-56 calcula la evapotranspiración del cultivo como ETc = Kc · ET0, donde ET0 es la '
  'evapotranspiración de referencia y Kc el coeficiente del cultivo según su etapa, y define una fracción p de '
  'agotamiento permisible antes de que el cultivo sufra estrés (Allen et al., 1998). Con esos parámetros se obtienen '
  'los umbrales de riego de cada cultivo y etapa.')
doc.add_heading('2.2 Sensores', 2)
J('El EC-5 es un sensor capacitivo que entrega un voltaje proporcional a la permitividad del suelo, la cual depende '
  'del contenido de agua (METER Group, s.f.). El PING))) mide distancia por el tiempo de vuelo de un pulso '
  'ultrasónico (Parallax, s.f.), el DHT22 entrega temperatura y humedad relativa por un bus digital de un hilo '
  '(Aosong Electronics, s.f.) y el YF-S201 genera pulsos con un sensor de efecto Hall proporcionales al caudal.')
doc.add_heading('2.3 Comunicación y estimación en línea', 2)
J('MQTT es un protocolo de publicación y suscripción ligero, adecuado para dispositivos con recursos limitados (OASIS, '
  '2014). Para el modelo predictivo se utilizan mínimos cuadrados recursivos (RLS), que actualizan los coeficientes '
  'de una regresión lineal con cada nueva observación sin almacenar todo el historial (Haykin, 2014).')

# ================================================================ 3. DESCRIPCIÓN GENERAL
doc.add_heading('3. Descripción general del sistema', 1)
J('El sistema se organiza en tres caminos: el agua, que va del tinaco al cajón; la energía, que va del panel solar a '
  'las cargas; y los datos, que van de los sensores al dashboard (Figura 1). El ESP32 es el único elemento que decide '
  'y acciona: si la Raspberry Pi o la red fallan, el riego continúa con las reglas locales.')
figura('diagrama_sistema.png', 'Arquitectura del sistema: los tres caminos del agua, la energía y los datos')
figura('f_cajon.jpg', 'Cajón de cultivo de 1 × 1 m con la mezcla de sustrato instalada', ancho=3.3,
       nota='Fotografía del equipo, 21 de octubre de 2026.')
tabla('Datos generales de la instalación', ['Concepto', 'Valor'], [
    ['Ubicación', 'Escuela Primaria Federal Belisario Domínguez, Chihuahua (28.659830, −106.074051)'],
    ['Cajón de cultivo', '1.00 × 1.00 m, 37.5 cm de sustrato (375 L); 1 punto de %VWC ≈ 3.75 L'],
    ['Sustrato', 'Peat moss, tierra negra y perlita (≈ 74/19/7 % en volumen); FC ≈ 48 %, WP ≈ 16 % (estimados)'],
    ['Cultivo configurado', 'Frijol en establecimiento; óptima 39 %VWC'],
    ['Tinaco', 'Ø ≈ 0.90 m; ≈ 6.3 L por cm; capacidad útil estimada ≈ 650 L'],
    ['Energía', 'Panel de 50 W, controlador PWM y batería SLA de 12 V y 9 Ah'],
    ['En operación', 'Desde el 21 de octubre de 2026, en modo AUTOMÁTICO'],
], [1.8, 4.7])

# ================================================================ 4. HIDRÁULICA
doc.add_heading('4. Sistema hidráulico', 1)
J('El agua sale del tinaco por una salida de ½" con válvula de esfera, pasa por la bomba de diafragma de 12 V, el '
  'caudalímetro y la electroválvula normalmente cerrada, sube por la línea principal de tubo PPR de 20 mm y se reparte '
  'en una cruz hacia tres mangueras con tres microaspersores cada una. La red se modeló en EPANET 2.2 (Rossman et '
  'al., 2020) con un caudal impuesto de 30 L/h por aspersor (4.5 L/min en total); el modelo corrió sin fallas '
  '(71 verificaciones correctas y 3 avisos), aunque sus resultados son preliminares porque la curva de la bomba es '
  'provisional.')
figura('epanet_red.png', 'Modelo hidráulico en EPANET: tinaco, bomba, caudalímetro, electroválvula, subida vertical y '
       'tres laterales con nueve aspersores', nota='Elaboración propia en EPANET 2.2.')
figura('f_tinaco_salida.jpg', 'Salida de ½" del tinaco con la válvula de esfera', ancho=3.0,
       nota='Fotografía del equipo, 13 de octubre de 2026.')
tabla('Caudal medido por el YF-S201 en distintas fechas', ['Fecha', 'Caudal', 'Observación'], [
    ['9 oct', '3.5–4.5 L/min', 'Banco de pruebas, tras ~4 s de cebado'],
    ['12 oct', '≈ 2.3 L/min', 'Primer riego en el huerto (0.773 L en 20.5 s)'],
    ['14 oct', '≈ 1.7 L/min', 'Riegos por meta de 2.80 y 1.40 L'],
    ['21 oct', '≈ 3.0 L/min', 'Prueba final: 2.051 L en 42.8 s'],
], [1.0, 1.4, 4.1], nota='Volúmenes calculados por pulsos (450 pulsos/L); el caudalímetro aún no se calibra con '
                         'recipiente graduado.')

# ================================================================ 5. ELÉCTRICO
doc.add_heading('5. Sistema eléctrico y electrónico', 1)
J('La electrónica se aloja en un gabinete plástico junto a la batería y el controlador solar (Figura 5). El ESP32 '
  'se monta en una placa de expansión y acciona un módulo de dos relevadores optoacoplados: K1 para la bomba y K2 para '
  'la electroválvula, ambos por los contactos COM → NO, de modo que ante una falla de alimentación las cargas quedan '
  'apagadas.')
figura('f_gabinete.jpg', 'Gabinete: ESP32 y relevadores, batería y controlador solar', ancho=3.2,
       nota='Fotografía del equipo, 13 de octubre de 2026.')
tabla('Asignación de pines del ESP32', ['Función', 'GPIO', 'Detalle'], [
    ['Relevador de la bomba (IN1)', '26', 'Activo en bajo'],
    ['Relevador de la electroválvula (IN2)', '27', 'Activo en bajo'],
    ['Caudalímetro YF-S201', '19', 'Contador de pulsos por hardware (PCNT), filtro de 10 µs'],
    ['Ultrasónico PING)))', '18', 'Un solo pin de señal; divisor 1 kΩ / 2 kΩ'],
    ['DHT22', '4', 'Bus digital de un hilo'],
    ['EC-5, excitación', '25', 'Pulso de 10 ms'],
    ['EC-5, señal', '34', 'ADC1, atenuación de 12 dB, 1 MΩ a tierra'],
], [2.6, 0.7, 3.2])
figura('f_reles.jpg', 'Módulo de dos relevadores SRD-05VDC-SL-C utilizado para la bomba y la electroválvula', ancho=2.8,
       nota='Fotografía del equipo durante las pruebas de banco.')
J('El relevador SRD admite 3 A con cargas inductivas a 28 VDC y la bomba consume 6 A nominales, por lo que la etapa de '
  'potencia actual no se considera definitiva. Se observaron reinicios del ESP32 al conmutar la bomba; se mitigaron '
  'por software (separación de 1.5 s entre la apertura de la válvula y el arranque de la bomba) y quedan pendientes '
  'diodos de rueda libre, un capacitor de 470–1000 µF en la alimentación, un relevador automotriz de 30/40 A y fusibles.')

# ================================================================ 6. SENSORES
doc.add_heading('6. Sensores y calibraciones', 1)
doc.add_heading('6.1 Humedad del suelo (EC-5)', 2)
J('La calibración experimental de la Actividad 2.2 relacionó el voltaje con la fracción de agua de mezclas de tierra '
  'y agua (R² = 0.945, válida de 360 a 870 mV):')
ecuacion('s = 0.08146067 · mV − 23.932584')
J('Como esa calibración expresó el agua respecto al volumen de tierra más agua, el firmware convierte el resultado a '
  'humedad volumétrica estándar, que es la que usan FAO-56 y la capacidad de campo:')
ecuacion('θ = s / (1 − s)')
J('El sensor se lee cada 5 minutos (con más frecuencia cuando hace calor o el aire está seco). En campo marcó cerca de '
  '375 mV al aire y entre 515 y 600 mV en el sustrato.')
doc.add_heading('6.2 Nivel del tinaco (PING)))', 2)
J('La distancia se calcula con la velocidad del sonido corregida por temperatura y el nivel se obtiene entre las '
  'referencias de tinaco vacío (117 cm) y lleno (12 cm):')
ecuacion('d = t · (331.3 + 0.606 · T) / 2          Nivel % = (117 − d) / (117 − 12) · 100')
figura('f_ultrasonico.jpg', 'Sensor PING))) en su caja acrílica sobre la tapa del tinaco', ancho=2.8,
       nota='Fotografía del equipo, 13 de octubre de 2026.')
doc.add_heading('6.3 Ambiente y caudal', 2)
J('El DHT22 se usa para el déficit de presión de vapor (VPD), que alimenta el modelo de secado. El YF-S201 convierte '
  'pulsos a litros con un factor provisional de 450 pulsos/L y protege la bomba: sin pulsos durante 45 s con la bomba '
  'encendida (NO_FLOW), caudal mayor a 8 L/min (FLOW_HIGH) o pulsos con todo apagado, que indicarían una fuga o un '
  'contacto pegado.')

# ================================================================ 7. FIRMWARE
doc.add_heading('7. Firmware del ESP32', 1)
J('El firmware riego-2.0.0 está escrito en C sobre ESP-IDF 6.0.2 (Espressif Systems, 2026), con 25 módulos y '
  'alrededor de 7 900 líneas. Usa tareas de FreeRTOS para control, sensores, clima y consola, y una máquina de estados '
  'pura que también se compila y prueba en la computadora. Los parámetros (~75) se validan por rangos y se guardan en '
  'memoria no volátil.')
doc.add_heading('7.1 Modos de operación', 2)
tabla('Modos de operación', ['Modo', 'Quién decide', 'Comportamiento'], [
    ['MANUAL', 'El usuario', 'Riego por litros o hasta una humedad meta; no riega solo. El riego manual solo se acepta en este modo.'],
    ['AUTOMÁTICO', 'Reglas del ESP32', 'Riega si la humedad baja de la óptima menos la histéresis (2 pp), confirmado con dos lecturas, '
                                        'en las ventanas 06:00–09:00 y 18:00–20:00, nunca de 11:00 a 16:00 ni con más de 35 °C. '
                                        'Dosis de 1.5 L con 15 min de infiltración, hasta 5 dosis (7.5 L).'],
    ['IA', 'Modelo predictivo', 'Todo lo anterior, más dosificación según el plan del modelo y aplazamiento por lluvia '
                                'solo si la lluvia prevista cubre el déficit.'],
], [1.1, 1.3, 4.1], nota='En los tres modos: emergencia de 1.5 L a cualquier hora si la humedad cae bajo el umbral '
                         'crítico (máximo una cada 4 h), máximo diario de 30 L y ningún riego al arrancar.')
doc.add_heading('7.2 Protecciones', 2)
vinetas([
    'Arranque seguro: salidas inactivas antes que nada; tras un reinicio se restaura el modo sin regar.',
    'Enclavamiento: nunca bomba con válvula cerrada; 1.5 s entre válvula y bomba al abrir y al cerrar.',
    'Supervisor independiente: tope absoluto de bomba de 5.5 min y corte si la tarea de control deja de responder 3 s.',
    'Límites por ciclo, por evento y por día; bloqueo por humedad máxima.',
    'Comandos MQTT: se rechazan duplicados, mensajes retenidos y órdenes con más de 60 s de antigüedad; STOP siempre se ejecuta.',
])
doc.add_heading('7.3 Filtrado de lecturas', 2)
J('Tras la puesta en marcha se observaron lecturas erróneas aisladas: picos de humedad sin riego, pérdidas de señal '
  'del EC-5 y ecos falsos del ultrasónico. Para que el control y la IA no reaccionen a ellas se agregó un filtro entre '
  'mediciones, además de mejoras dentro de cada medición (Tabla 5).')
tabla('Filtros agregados a las lecturas de los sensores', ['Sensor', 'Dentro de la medición', 'Entre mediciones'], [
    ['EC-5 (humedad)', '9 pulsos de excitación, mediana y dispersión sin extremos',
     'Mediana de 3; un salto > 3 pp se ignora hasta que 2 lecturas seguidas lo confirmen (± 2 pp); '
     'hasta 2 lecturas inválidas conservan el último valor bueno; re-medición en 60 s'],
    ['PING))) (tinaco)', '7 ecos; se promedia el grupo que coincide con la mediana (± 3 cm, mínimo 4); '
                         'se rechazan distancias imposibles',
     'Un salto > 8 cm requiere 3 lecturas que coincidan (± 3 cm); hasta 6 inválidas conservan el valor'],
], [1.3, 2.4, 2.8], nota='Las lecturas retenidas o ignoradas no alimentan a la IA ni a la detección de lluvia; la IA '
                         'además descarta riegos que aparentan bajar la humedad.')
doc.add_heading('7.4 Modelo predictivo', 2)
J('El ESP32 ajusta en línea, mediante RLS, dos regresiones lineales: el modelo A estima cuántos puntos de humedad sube '
  'el suelo por litro y el modelo B estima cuánto se seca por hora a partir del VPD, la ET0 de Open-Meteo (Zippenfenig, '
  '2023), el Kc y la hora del día. El modelo pasa por las fases APRENDIZAJE, VALIDACIÓN y PREDICTIVO_ACTIVO; requiere '
  'al menos 6 riegos y 48 h de secado observados. Como los datos previos a los filtros contenían lecturas erróneas, el '
  'modelo se reinició y volvió a la fase de aprendizaje con datos limpios.')

# ================================================================ 8. SERVIDOR Y DASHBOARD
doc.add_heading('8. Servidor y dashboard', 1)
J('Una Raspberry Pi del laboratorio ejecuta una instancia propia y aislada de Node-RED (OpenJS Foundation, s.f.) en el '
  'puerto 1881 con FlowFuse Dashboard 2.0 (FlowFuse, s.f.) y un broker Mosquitto propio en el puerto 1884, con '
  'usuarios y listas de control de acceso, sin interferir con los servicios del profesor ni de otros equipos. Los datos '
  'se guardan en SQLite (SQLite Consortium, s.f.) en 22 tablas y se respaldan cada día a las 03:00. El dashboard solo es '
  'accesible desde la red local del huerto.')
figura('d_inicio_panel.jpg', 'Página Inicio del dashboard: medidores, actuadores y riego rápido',
       nota='Captura tomada con el simulador del sistema; en la instalación real no aparece la franja amarilla.')
figura('banda_recorte.png', 'Banda de humedad del frijol en establecimiento y acción del sistema en cada zona')
tabla('Páginas del dashboard', ['Página', 'Función'], [
    ['Inicio', 'Estado general, panel de control, balance de agua del día y selección de modo'],
    ['Manual', 'Riego por litros o hasta una humedad, con progreso, caudal y gráficas'],
    ['Automático', 'Decisión actual y su justificación; ajuste de umbrales, horarios y límites'],
    ['IA', 'Fase del modelo, predicción contra realidad, coeficientes y comparación de modelos'],
    ['Cultivos / Crecimiento', '10 cultivos base y personalizados; etapas, grados-día y cosecha estimada'],
    ['Clima', 'Pronóstico de Open-Meteo, ET0, ETc, VPD y lluvia'],
    ['Historial / Alertas', 'Gráficas, exportación CSV y confirmación de la causa de aumentos de humedad'],
    ['Configuración', 'Calibraciones, cama de cultivo, suelo, respaldos y diagnóstico'],
], [1.8, 4.7])
figura('d_manual.jpg', 'Página Manual: riego por cantidad fija, riego hasta una humedad y paro inmediato',
       nota='Captura tomada con el simulador del sistema.')
figura('d_ia.jpg', 'Página IA: fase de aprendizaje, autonomía estimada y predicción del día',
       nota='Captura tomada con el simulador; los coeficientes simulados no se copian al ESP32.')
figura('d_alertas.jpg', 'Página Alertas: resumen por categoría y confirmación de la causa de cada aumento de humedad',
       nota='Captura tomada con el simulador del sistema.')
J('Cada comando del dashboard pide confirmación, se publica en MQTT con un identificador y una marca de tiempo, y solo '
  'se reporta como aplicado cuando el ESP32 responde con su confirmación (ACK); si no llega en 12 s se informa que no '
  'hubo cambios.')

# ================================================================ 9. RESULTADOS
doc.add_heading('9. Pruebas y resultados', 1)
tabla('Resultados de las pruebas', ['Fecha', 'Prueba', 'Resultado'], [
    ['Sep', 'Calibración del EC-5 (4 muestras)', '360/420/630/870 mV; R² = 0.945'],
    ['9 oct', 'Bomba y válvula (4 ciclos de 10 s)', 'La válvula corta el agua; relevadores activos en bajo'],
    ['11 oct', 'Pruebas automáticas de firmware', 'Lógica 47/47; autodiagnóstico en placa 49/49; integración 29/29'],
    ['12 oct', 'Primer riego en el huerto', '0.773 L en 20.5 s'],
    ['13 oct', 'Prueba de campo Pi + ESP32', '28/28 (sin 12 V el sistema cortó por NO_FLOW, como se esperaba)'],
    ['14 oct', 'Riegos por meta de humedad', '2.802 L y 1.404 L'],
    ['21 oct', 'Tinaco con la tapa puesta', '30.4–31.4 cm = 82 %, estable'],
    ['21 oct', 'Prueba final con agua', '2.051 L en 42.8 s; paro inmediato a 0.622 L; sin reinicios; 14 de 15 pasos '
                                         '(1 falso fallo del script)'],
    ['21 oct', 'Integración con el servidor', '30/30'],
    ['Oct', 'Operación nocturna', 'Riegos de emergencia y programados ejecutados; sin lectura válida del EC-5 '
                                   'el riego matutino se omitió por seguridad'],
    ['Oct', 'Filtros de lecturas', 'Autodiagnóstico en la placa 51/51'],
], [0.8, 2.3, 3.4], nota='Ningún volumen se ha medido todavía con recipiente graduado; los litros se calculan por pulsos.')
figura('f_tinaco_medicion.jpg', 'Medición del tinaco para calibrar el nivel', ancho=2.8,
       nota='Fotografía del equipo, 13 de octubre de 2026.')

# ================================================================ 10. DOCUMENTACIÓN Y MONITOREO
doc.add_heading('10. Documentación de operación y monitoreo remoto', 1)
J('Para que cualquier persona pueda operar y mantener el sistema se elaboraron dos manuales: el **Manual del '
  'Dashboard**, que explica cada página, los modos, el riego manual, los avisos y qué hacer ante situaciones comunes, y '
  'el **Manual de Instalación Física**, que cubre la seguridad antes de intervenir, el recorrido del agua, las '
  'conexiones pin por pin, la instalación de los sensores, los pasos para desmontar y rearmar el sistema, la tabla de '
  'fallas y el calendario de mantenimiento.')
J('Como el dashboard solo es accesible en la red del huerto, se preparó un bot de Telegram de solo lectura (Telegram, '
  's.f.) que corre en la Raspberry Pi: responde a /estado, /riegos, /alertas e /ia, avisa de alertas nuevas o de la '
  'falta de datos del ESP32 y envía un resumen diario. Solo realiza conexiones de salida, no abre puertos ni puede '
  'accionar el riego. Su instalación en la Pi queda pendiente.')

# ================================================================ 11. DIFICULTADES
doc.add_heading('11. Dificultades y soluciones', 1)
tabla('Dificultades encontradas y soluciones aplicadas', ['Problema', 'Causa', 'Solución', 'Estado'], [
    ['Reinicios del ESP32 al conmutar la bomba', 'Picos inductivos; relevador inadecuado',
     'Separación de 1.5 s (software); diodos, capacitor y relevador de potencia (hardware)', 'Hardware pendiente'],
    ['Desconexiones de Wi-Fi', 'Señal de −84 a −94 dBm en el gabinete', 'Wi-Fi sin ahorro de energía, keepalive de 30 s',
     'Mejoró'],
    ['EC-5 sin señal o a 3.1 V', 'Pin equivocado y empalmes húmedos', 'Pines 25/34, secado y aislamiento', 'Resuelto'],
    ['Lecturas erróneas aisladas', 'Ruido eléctrico y contactos', 'Filtros entre mediciones y reinicio de la IA', 'Resuelto'],
    ['Ultrasónico inestable', 'Tapa quitada, montaje', 'Sensor centrado y tapa puesta', 'Resuelto'],
    ['NO_FLOW repetido', 'Tinaco bajo y cebado', 'Llenado del tinaco', 'Resuelto'],
    ['Micro-USB del ESP32 original dañado', 'Daño físico', 'ESP32 de reemplazo con la misma configuración', 'Resuelto'],
], [1.6, 1.5, 2.3, 1.1])

# ================================================================ 12. PENDIENTES
doc.add_heading('12. Limitaciones y trabajo futuro', 1)
vinetas([
    'Etapa de potencia definitiva: relevador automotriz o MOSFET, fusibles de 15/10/3 A, diodos y capacitor; medir la corriente de arranque de la bomba.',
    'Calibrar el caudalímetro con recipiente graduado.',
    'Medir la capacidad de campo real del sustrato y validar el EC-5 en esta mezcla.',
    'Completar el aprendizaje de la IA (≥ 6 riegos y 48 h de secado) y evaluar su desempeño.',
    'Mejorar la señal Wi-Fi del gabinete.',
    'Medir el balance energético diario y la autonomía de la batería.',
    'Contrastar el modelo de EPANET con mediciones de presión y uniformidad de riego.',
    'Instalar el bot de monitoreo remoto en la Raspberry Pi.',
])

# ================================================================ 13. CONCLUSIONES
doc.add_heading('13. Conclusiones', 1)
J('AquaHuerto Escolar pasó del diseño a un sistema en operación real que riega un huerto escolar con base en la '
  'humedad medida, con umbrales agronómicos por cultivo, riego por dosis e infiltración, protecciones en varios '
  'niveles y supervisión remota en la red local. La separación entre el control local del ESP32 y el servidor permite '
  'que el riego continúe aunque fallen la red o la Raspberry Pi.')
J('La operación en campo mostró que la confiabilidad de las lecturas es tan importante como la lógica de control: los '
  'filtros agregados evitan riegos y aprendizajes basados en datos erróneos. Los pendientes principales son de '
  'hardware y de validación (etapa de potencia, calibración del caudal y de la capacidad de campo); una vez atendidos, '
  'el sistema podrá considerarse validado y la IA podrá operar en su fase predictiva con datos confiables.')

# ================================================================ REFERENCIAS
salto()
doc.add_heading('Referencias', 1)
REFS = [
    'Al Mamun, M. R., Ahmed, A. K., Upoma, S. M., Haque, M., & Ashik-E-Rabbani, M. (2025). IoT-enabled solar-powered '
    'smart irrigation for precision agriculture. *Smart Agricultural Technology, 10*, 100773. '
    'https://doi.org/10.1016/j.atech.2025.100773',
    'Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop '
    'water requirements* (FAO Irrigation and Drainage Paper No. 56). Food and Agriculture Organization of the United '
    'Nations.',
    'Aosong Electronics. (s.f.). *Digital-output relative humidity & temperature sensor/module AM2302* [Hoja de datos].',
    'Espressif Systems. (2026). *ESP-IDF programming guide* (v6.0). https://docs.espressif.com/projects/esp-idf/',
    'Food and Agriculture Organization of the United Nations. (2021). *The state of the world\'s land and water resources '
    'for food and agriculture: Systems at breaking point* (SOLAW 2021). https://doi.org/10.4060/cb7654en',
    'FlowFuse. (s.f.). *FlowFuse Dashboard 2.0 documentation*. https://dashboard.flowfuse.com',
    'Haykin, S. (2014). *Adaptive filter theory* (5th ed.). Pearson.',
    'METER Group. (s.f.). *EC-5 soil moisture sensor* [Manual de usuario]. https://www.metergroup.com',
    'Moustafa, A., Abdelwahab, O. M. M., Ricci, G. F., & Gentile, F. (2026). Internet of Things-enabled smart irrigation '
    'systems for precision water management: A systematic review. *Agricultural Water Management, 333*, 110615. '
    'https://doi.org/10.1016/j.agwat.2026.110615',
    'OASIS. (2014). *MQTT version 3.1.1* [OASIS Standard]. https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html',
    'OpenJS Foundation. (s.f.). *Node-RED: Low-code programming for event-driven applications*. https://nodered.org',
    'Parallax Inc. (s.f.). *PING))) ultrasonic distance sensor (#28015)* [Hoja de datos]. https://www.parallax.com',
    'Rossman, L. A., Woo, H., Tryby, M., Shang, F., Janke, R., & Haxton, T. (2020). *EPANET 2.2 user manual* '
    '(EPA/600/R-20/133). U.S. Environmental Protection Agency.',
    'SQLite Consortium. (s.f.). *SQLite*. https://www.sqlite.org',
    'Telegram. (s.f.). *Telegram Bot API*. https://core.telegram.org/bots/api',
    'Zippenfenig, P. (2023). *Open-Meteo.com weather API* [Software]. Zenodo. https://doi.org/10.5281/zenodo.7970649',
]
for ref in REFS:
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Inches(0.5)
    par.paragraph_format.first_line_indent = Inches(-0.5)
    par.paragraph_format.line_spacing = 1.5
    par.paragraph_format.space_after = Pt(4)
    for i, parte in enumerate(ref.split('*')):
        if parte:
            r = par.add_run(parte)
            r.italic = i % 2 == 1

doc.core_properties.title = 'AquaHuerto Escolar: reporte técnico'
doc.core_properties.author = 'Equipo 2'
doc.save(OUT)
print(OUT, FIG[0], 'figuras', TAB[0], 'tablas')
