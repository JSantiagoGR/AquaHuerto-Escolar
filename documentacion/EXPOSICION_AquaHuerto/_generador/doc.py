"""Estilo comun de los documentos de la exposicion (python-docx)."""
import os
from PIL import Image
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, RGBColor

VERDE = RGBColor(0x1B, 0x5E, 0x20)
VERDE_HEX = '1B5E20'
GRIS = RGBColor(0x55, 0x55, 0x55)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
INTEGRANTES = [
    ('Jaime Santiago Galaviz Reaza', ''),
    ('Victor Manuel Palicio Torres', ''),
    ('Eyra Cristal Garcia', ''),
]
FECHA = 'Noviembre de 2026'
ASESOR = ''
LOGO_TEC = None


def shd(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement('w:shd')
    s.set(qn('w:val'), 'clear')
    s.set(qn('w:color'), 'auto')
    s.set(qn('w:fill'), fill)
    tcPr.append(s)


def campo(par, instr):
    r = par.add_run()
    for tag, txt in (('begin', None), (None, instr), ('separate', None), ('end', None)):
        if tag:
            e = OxmlElement('w:fldChar')
            e.set(qn('w:fldCharType'), tag)
            r._r.append(e)
        else:
            t = OxmlElement('w:instrText')
            t.set(qn('xml:space'), 'preserve')
            t.text = txt
            r._r.append(t)


class Doc:
    def __init__(self, numero, titulo, subtitulo, portada_img=None, indice=False, horizontal=False):
        self.d = Document()
        s = self.d.sections[0]
        if horizontal:
            s.page_width, s.page_height = Inches(11), Inches(8.5)
        else:
            s.page_width, s.page_height = Inches(8.5), Inches(11)
        for m in ('left_margin', 'right_margin'):
            setattr(s, m, Inches(0.9))
        s.top_margin = s.bottom_margin = Inches(0.8)
        self.ancho = (s.page_width - s.left_margin - s.right_margin) / 914400
        st = self.d.styles['Normal']
        st.font.name = 'Calibri'
        st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
        st.font.size = Pt(11)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.line_spacing = 1.15
        for lvl, size in ((1, 16), (2, 13), (3, 11.5)):
            h = self.d.styles['Heading %d' % lvl]
            rf = h.element.rPr.find(qn('w:rFonts'))
            if rf is not None:
                for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
                    rf.attrib.pop(qn(a), None)
                rf.set(qn('w:ascii'), 'Calibri')
                rf.set(qn('w:hAnsi'), 'Calibri')
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.color.rgb = VERDE
            h.paragraph_format.space_before = Pt(14 if lvl == 1 else 10)
            h.paragraph_format.space_after = Pt(5)
            h.paragraph_format.keep_with_next = True
        self.titulo = titulo
        self.fig = 0
        self.tab = 0
        self.horizontal = horizontal
        self.portada(numero, titulo, subtitulo, portada_img)
        self.pie()
        if indice:
            self.indice()

    # ------------------------------------------------------------ portada
    def portada(self, numero, titulo, subtitulo, img):
        t = self.d.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        c = t.rows[0].cells[0]
        shd(c, VERDE_HEX)
        p = c.paragraphs[0]
        r = p.add_run('AQUAHUERTO ESCOLAR' + (f'  ·  DOCUMENTO {numero}' if numero else ''))
        r.bold = True
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor(0xC8, 0xE6, 0xC9)
        p = c.add_paragraph()
        r = p.add_run(titulo)
        r.bold = True
        r.font.size = Pt(28)
        r.font.color.rgb = BLANCO
        p = c.add_paragraph()
        r = p.add_run(subtitulo)
        r.font.size = Pt(13)
        r.font.color.rgb = BLANCO
        p.paragraph_format.space_after = Pt(8)
        self.p('', after=8)
        if img:
            self.imagen(img, ancho=self.ancho, alto_max=1.5 if self.horizontal else 3.3, numerar=False)
        self.p('Sistema mecatrónico de riego inteligente para huertos escolares', size=12, bold=True,
               align=WD_ALIGN_PARAGRAPH.CENTER, color=VERDE, after=2)
        self.p('Escuela Primaria Federal Belisario Domínguez · Chihuahua, Chihuahua', size=11,
               align=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, after=12)
        self.p('Equipo 2 · Tecnológico de Monterrey, Campus Chihuahua', size=11, bold=True,
               align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
        for n, m in INTEGRANTES:
            self.p(f'{n}  ·  {m}', size=11, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
        self.p('', after=6)
        if ASESOR: self.p('Asesor: ' + ASESOR, size=11, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
        self.p(FECHA, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, after=0)
        self.salto()

    def pie(self):
        sec = self.d.sections[0]
        sec.different_first_page_header_footer = True
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run(f'AquaHuerto · {self.titulo} · Página ')
        r.font.size = Pt(9)
        r.font.color.rgb = GRIS
        campo(fp, 'PAGE')

    def indice(self):
        self.p('Contenido', size=16, bold=True, color=VERDE, after=6)
        campo(self.d.add_paragraph(), r'TOC \o "1-2" \h \z \u')
        self.salto()

    # ------------------------------------------------------------ bloques
    def runs(self, par, texto, size=None, color=None, bold=False, italic=False):
        partes = texto.split('**')
        for i, parte in enumerate(partes):
            if not parte:
                continue
            r = par.add_run(parte)
            r.bold = bold or (i % 2 == 1)
            r.italic = italic
            if size:
                r.font.size = Pt(size)
            if color is not None:
                r.font.color.rgb = color
        return par

    def p(self, texto='', size=None, align=None, color=None, bold=False, italic=False, after=None):
        par = self.d.add_paragraph()
        self.runs(par, texto, size, color, bold, italic)
        if align is not None:
            par.alignment = align
        if after is not None:
            par.paragraph_format.space_after = Pt(after)
        return par

    def h1(self, t, nueva=False):
        h = self.d.add_heading(t, 1)
        if nueva:
            h.paragraph_format.page_break_before = True
        return h

    def h2(self, t):
        return self.d.add_heading(t, 2)

    def h3(self, t):
        return self.d.add_heading(t, 3)

    def bullets(self, items, numerada=False):
        for it in items:
            par = self.d.add_paragraph(style='List Number' if numerada else 'List Bullet')
            self.runs(par, it)
            par.paragraph_format.space_after = Pt(2)

    def nota(self, texto, fondo='E8F5E9'):
        t = self.d.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        c = t.rows[0].cells[0]
        shd(c, fondo)
        self.runs(c.paragraphs[0], texto, size=10.5)
        self.p('', after=2)

    def tabla(self, enc, filas, anchos=None, size=9.5, titulo=None):
        if titulo:
            self.tab += 1
            q = self.p(f'Tabla {self.tab}. {titulo}', size=10, bold=True, color=VERDE, after=2)
            q.paragraph_format.keep_with_next = True
        t = self.d.add_table(rows=1, cols=len(enc))
        t.style = 'Table Grid'
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, e in enumerate(enc):
            c = t.rows[0].cells[i]
            shd(c, VERDE_HEX)
            c.paragraphs[0].text = ''
            r = c.paragraphs[0].add_run(e)
            r.bold = True
            r.font.size = Pt(size)
            r.font.color.rgb = BLANCO
        tr = t.rows[0]._tr
        trPr = tr.get_or_add_trPr()
        h = OxmlElement('w:tblHeader')
        h.set(qn('w:val'), 'true')
        trPr.append(h)
        for k, f in enumerate(filas):
            cells = t.add_row().cells
            for i, v in enumerate(f):
                cells[i].paragraphs[0].text = ''
                self.runs(cells[i].paragraphs[0], str(v), size=size)
                cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
                if k % 2 == 1:
                    shd(cells[i], 'F1F8E9')
        if anchos:
            for row in t.rows:
                for i, w in enumerate(anchos):
                    row.cells[i].width = Inches(w)
        self.p('', after=4)
        return t

    def imagen(self, path, ancho=None, pie=None, alto_max=None, numerar=True):
        ancho = ancho or self.ancho
        with Image.open(path) as im:
            w, h = im.size
        if alto_max and ancho * h / w > alto_max:
            ancho = alto_max * w / h
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = bool(pie)
        par.add_run().add_picture(path, width=Inches(ancho))
        if pie:
            if numerar:
                self.fig += 1
                pie = f'Figura {self.fig}. {pie}'
            self.p(pie, size=9.5, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, after=8)

    def salto(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def refs(self, lista):
        for ref in lista:
            par = self.d.add_paragraph()
            par.paragraph_format.left_indent = Inches(0.5)
            par.paragraph_format.first_line_indent = Inches(-0.5)
            par.paragraph_format.space_after = Pt(4)
            for i, parte in enumerate(ref.split('*')):
                if parte:
                    r = par.add_run(parte)
                    r.italic = i % 2 == 1

    def guardar(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.d.core_properties.title = self.titulo
        self.d.core_properties.author = 'Equipo 2 AquaHuerto'
        self.d.save(path)
        return path
