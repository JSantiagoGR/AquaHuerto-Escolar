"""Estilo y bloques comunes de los manuales de AquaHuerto (uso y técnicos)."""
import os
from PIL import Image
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, RGBColor

D = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(D, 'img')
OLD = os.path.join(os.path.dirname(D), 'imagenes')
REP = os.path.join(os.path.dirname(os.path.dirname(D)), 'reporte', 'img')
AUTOR = 'Jaime Santiago Galaviz Reaza'
FECHA = 'Noviembre de 2026'
EQUIPO = ['Victor Manuel Palicio Torres', 'Eyra Cristal Garcia']

VERDE, VERDE_HEX = RGBColor(0x1B, 0x5E, 0x20), '1B5E20'
VERDE_CLARO = 'E8F3E8'
ROJO_HEX, AZUL_HEX, NARANJA_HEX, GRIS_HEX = 'C62828', '1565C0', 'E65100', '616161'
GRIS = RGBColor(0x55, 0x55, 0x55)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)


# ------------------------------------------------------------------ utilidades de formato
def shd(el, fill):
    s = OxmlElement('w:shd')
    s.set(qn('w:val'), 'clear')
    s.set(qn('w:color'), 'auto')
    s.set(qn('w:fill'), fill)
    el.append(s)


def borde_celda(celda, lados, color, size):
    tcPr = celda._tc.get_or_add_tcPr()
    b = OxmlElement('w:tcBorders')
    for lado in ('top', 'left', 'bottom', 'right'):
        e = OxmlElement('w:' + lado)
        if lado in lados:
            e.set(qn('w:val'), 'single')
            e.set(qn('w:sz'), str(size))
            e.set(qn('w:color'), color)
        else:
            e.set(qn('w:val'), 'nil')
        b.append(e)
    tcPr.append(b)


def margen_celda(celda, pts=6):
    tcPr = celda._tc.get_or_add_tcPr()
    m = OxmlElement('w:tcMar')
    for lado in ('top', 'left', 'bottom', 'right'):
        e = OxmlElement('w:' + lado)
        e.set(qn('w:w'), str(pts * 20))
        e.set(qn('w:type'), 'dxa')
        m.append(e)
    tcPr.append(m)


def campo(par, instr):
    r = par.add_run()
    for tag in ('begin', 'instr', 'separate', 'end'):
        if tag == 'instr':
            t = OxmlElement('w:instrText')
            t.set(qn('xml:space'), 'preserve')
            t.text = instr
            r._r.append(t)
        else:
            e = OxmlElement('w:fldChar')
            e.set(qn('w:fldCharType'), tag)
            r._r.append(e)


class Manual:
    def __init__(self, titulo, subtitulo, portada_img, etiqueta='MANUAL DE USO', equipo=False):
        self.doc = Document()
        s = self.doc.sections[0]
        s.page_width, s.page_height = Inches(8.5), Inches(11)
        s.left_margin = s.right_margin = Inches(0.9)
        s.top_margin = s.bottom_margin = Inches(0.8)
        st = self.doc.styles['Normal']
        st.font.name = 'Calibri'
        st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
        st.font.size = Pt(12)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.line_spacing = 1.15
        for lvl, size in ((1, 20), (2, 14)):
            h = self.doc.styles['Heading %d' % lvl]
            rf = h.element.rPr.find(qn('w:rFonts'))
            for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
                rf.attrib.pop(qn(a), None)
            rf.set(qn('w:ascii'), 'Calibri')
            rf.set(qn('w:hAnsi'), 'Calibri')
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.color.rgb = VERDE
            h.paragraph_format.space_before = Pt(6 if lvl == 1 else 12)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True
        self.titulo = titulo
        self.etiqueta = etiqueta
        self.equipo = equipo
        self.portada(titulo, subtitulo, portada_img)

    # -------------------------------------------------------------- bloques
    def p(self, texto='', size=None, align=None, color=None, bold=False, italic=False, after=None):
        """Párrafo con **negritas** y [[BOTONES]] en línea."""
        par = self.doc.add_paragraph()
        self.runs(par, texto, size, color, bold, italic)
        if align is not None:
            par.alignment = align
        if after is not None:
            par.paragraph_format.space_after = Pt(after)
        return par

    def runs(self, par, texto, size=None, color=None, bold=False, italic=False):
        import re
        for tok in re.split(r'(\[\[[^\]]+\]\]|\*\*[^*]+\*\*|`[^`]+`)', texto):
            if not tok:
                continue
            if tok.startswith('[['):
                self.boton(par, tok[2:-2], size)
                continue
            if tok.startswith('`'):
                r = par.add_run(tok[1:-1])
                r.font.name = 'Consolas'
                r.font.size = Pt((size or 12) - 1.5)
                shd(r._r.get_or_add_rPr(), 'EFEFEF')
                continue
            neg = tok.startswith('**')
            r = par.add_run(tok[2:-2] if neg else tok)
            r.bold = bold or neg
            r.italic = italic
            if size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = color

    def boton(self, par, texto, size=None):
        """Nombre de un botón como etiqueta de color, igual que en la pantalla."""
        if '|' in texto:
            texto, color = texto.split('|')
        else:
            color = ROJO_HEX if any(w in texto for w in ('DETENER', 'LIMPIAR', 'PERMITIR')) else VERDE_HEX
        r = par.add_run(' ' + texto + ' ')
        r.bold = True
        r.font.size = Pt((size or 12) - 1.5)
        r.font.color.rgb = BLANCO
        shd(r._r.get_or_add_rPr(), color)

    def h1(self, texto, nueva_pagina=True):
        h = self.doc.add_heading(texto, 1)
        h.paragraph_format.page_break_before = nueva_pagina
        pPr = h._p.get_or_add_pPr()
        b = OxmlElement('w:pBdr')
        e = OxmlElement('w:bottom')
        for k, v in (('val', 'single'), ('sz', '12'), ('space', '4'), ('color', VERDE_HEX)):
            e.set(qn('w:' + k), v)
        b.append(e)
        pPr.append(b)

    def h2(self, texto):
        self.doc.add_heading(texto, 2)

    def indice(self):
        """Tabla de contenido (Word la llena al abrir o al exportar)."""
        self.h1('Contenido')
        par = self.doc.add_paragraph()
        campo(par, r'TOC \o "1-2" \h \z \u')

    def salto(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def caja(self, titulo, lineas, color=VERDE_HEX, fondo=VERDE_CLARO):
        """Recuadro destacado con barra de color a la izquierda."""
        t = self.doc.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        c = t.rows[0].cells[0]
        c.width = Inches(6.7)
        shd(c._tc.get_or_add_tcPr(), fondo)
        borde_celda(c, ('left',), color, 36)
        margen_celda(c, 8)
        par = c.paragraphs[0]
        r = par.add_run(titulo)
        r.bold = True
        r.font.color.rgb = RGBColor.from_string(color)
        for ln in lineas:
            q = c.add_paragraph()
            q.paragraph_format.space_after = Pt(2)
            self.runs(q, ln)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def pasos(self, lista):
        """Pasos numerados con un número grande en un recuadro verde."""
        t = self.doc.add_table(rows=0, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, texto in enumerate(lista, 1):
            a, b = t.add_row().cells
            a.width, b.width = Inches(0.55), Inches(6.15)
            shd(a._tc.get_or_add_tcPr(), VERDE_HEX)
            a.vertical_alignment = b.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pa = a.paragraphs[0]
            pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
            ra = pa.add_run(str(i))
            ra.bold = True
            ra.font.size = Pt(16)
            ra.font.color.rgb = BLANCO
            margen_celda(b, 6)
            borde_celda(b, ('bottom',), 'D0D0D0', 4)
            pb = b.paragraphs[0]
            pb.paragraph_format.space_after = Pt(0)
            self.runs(pb, texto)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def tabla(self, encabezado, filas, anchos, size=11, numerada=False):
        t = self.doc.add_table(rows=1, cols=len(encabezado))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.style = 'Table Grid'
        for i, txt in enumerate(encabezado):
            c = t.rows[0].cells[i]
            shd(c._tc.get_or_add_tcPr(), VERDE_HEX)
            r = c.paragraphs[0].add_run(txt)
            r.bold = True
            r.font.size = Pt(size)
            r.font.color.rgb = BLANCO
        for k, fila in enumerate(filas):
            cells = t.add_row().cells
            for i, txt in enumerate(fila):
                if numerada and i == 0:
                    shd(cells[i]._tc.get_or_add_tcPr(), ROJO_HEX)
                    pa = cells[i].paragraphs[0]
                    pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r = pa.add_run(str(txt))
                    r.bold = True
                    r.font.color.rgb = BLANCO
                    r.font.size = Pt(size + 1)
                    continue
                self.runs(cells[i].paragraphs[0], str(txt), size)
                if k % 2:
                    shd(cells[i]._tc.get_or_add_tcPr(), 'F3F8F3')
        for row in t.rows:
            for i, w in enumerate(anchos):
                row.cells[i].width = Inches(w)
                row.cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                margen_celda(row.cells[i], 4)
                for par in row.cells[i].paragraphs:
                    par.paragraph_format.space_after = Pt(0)
                    par.paragraph_format.line_spacing = 1.05
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def imagen(self, path, ancho=6.7, pie=None, alto_max=None):
        w, h = Image.open(path).size
        if alto_max and ancho * h / w > alto_max:
            ancho = alto_max * w / h
        par = self.doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = bool(pie)
        par.add_run().add_picture(path, width=Inches(ancho))
        if pie:
            self.p(pie, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, italic=True, after=10)

    def fotos(self, items, alto=2.1):
        """Fila de fotos con su nombre debajo."""
        t = self.doc.add_table(rows=2, cols=len(items))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, (path, nombre) in enumerate(items):
            c = t.rows[0].cells[i]
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraphs[0].add_run().add_picture(path, height=Inches(alto))
            n = t.rows[1].cells[i]
            n.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            self.runs(n.paragraphs[0], nombre, 11, bold=True)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def checklist(self, items):
        t = self.doc.add_table(rows=0, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for it in items:
            a, b = t.add_row().cells
            a.width, b.width = Inches(0.45), Inches(6.25)
            pa = a.paragraphs[0]
            pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
            ra = pa.add_run('☐')
            ra.font.size = Pt(18)
            ra.font.color.rgb = VERDE
            a.vertical_alignment = b.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            borde_celda(b, ('bottom',), 'D0D0D0', 4)
            pb = b.paragraphs[0]
            pb.paragraph_format.space_after = Pt(2)
            self.runs(pb, it)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # -------------------------------------------------------------- portada y pie
    def portada(self, titulo, subtitulo, img):
        t = self.doc.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        c = t.rows[0].cells[0]
        c.width = Inches(6.7)
        shd(c._tc.get_or_add_tcPr(), VERDE_HEX)
        margen_celda(c, 18)
        a = c.paragraphs[0]
        r = a.add_run('AQUAHUERTO ESCOLAR  ·  ' + self.etiqueta)
        r.bold = True
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor(0xC8, 0xE6, 0xC9)
        b = c.add_paragraph()
        r = b.add_run(titulo)
        r.bold = True
        r.font.size = Pt(32)
        r.font.color.rgb = BLANCO
        s = c.add_paragraph()
        r = s.add_run(subtitulo)
        r.font.size = Pt(14)
        r.font.color.rgb = BLANCO
        self.p('', after=10 if self.equipo else 14)
        self.imagen(img, ancho=6.7, alto_max=2.7 if self.equipo else 4.3)
        self.p('Escuela Primaria Federal Belisario Domínguez · Chihuahua, Chihuahua', size=12,
               align=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, after=10 if self.equipo else 18)
        self.p('Elaborado por', size=11, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, after=2)
        if self.equipo:
            for nombre in [AUTOR] + EQUIPO:
                self.p(nombre, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
            self.p('', after=2)
        else:
            self.p(AUTOR, size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=VERDE, after=0)
        self.p('Equipo 2 · Tecnológico de Monterrey, Campus Chihuahua', size=11,
               align=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, after=0)
        self.p(FECHA, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, after=18)

    def contacto(self):
        t = self.doc.add_table(rows=2, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, txt in enumerate(('Persona responsable del sistema:', 'Teléfono:')):
            a, b = t.rows[i].cells
            a.width, b.width = Inches(2.6), Inches(3.4)
            r = a.paragraphs[0].add_run(txt)
            r.bold = True
            r.font.size = Pt(11)
            borde_celda(b, ('bottom',), '888888', 6)

    def pie(self):
        sec = self.doc.sections[0]
        sec.different_first_page_header_footer = True
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run('AquaHuerto · %s · Página ' % self.titulo)
        r.font.size = Pt(9)
        r.font.color.rgb = GRIS
        campo(fp, 'PAGE')

    def guardar(self, nombre):
        self.pie()
        self.doc.core_properties.author = AUTOR
        self.doc.core_properties.title = 'AquaHuerto · ' + self.titulo
        out = os.path.join(D, nombre)
        self.doc.save(out)
        print(out)


