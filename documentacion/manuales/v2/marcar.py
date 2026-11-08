"""Marca con números los botones en las capturas del dashboard (manual v2)."""
from PIL import Image, ImageDraw, ImageFont
F = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 22)
ROJO = (200, 30, 30)


def marcar(src, dst, marcas, cajas=()):
    im = Image.open('imagenes/' + src).convert('RGB')
    d = ImageDraw.Draw(im)
    for c in cajas:
        d.rounded_rectangle(c, 8, outline=ROJO, width=5)
    for n, (x, y) in marcas:
        r = 17
        d.ellipse((x - r, y - r, x + r, y + r), fill=ROJO, outline='white', width=3)
        d.text((x, y), str(n), fill='white', font=F, anchor='mm')
    im.save('v2/img/' + dst, quality=88)


marcar('d_inicio_panel.jpg', 'inicio_marcada.jpg',
       [(1, (17, 175)), (2, (802, 212)), (3, (24, 390)), (4, (845, 330)), (5, (845, 392)), (6, (845, 448))],
       [(122, 160, 432, 192), (720, 162, 884, 190), (865, 368, 1238, 416), (865, 424, 1238, 472)])
marcar('d_manual.jpg', 'manual_marcada.jpg',
       [(1, (17, 248)), (2, (24, 375)), (3, (24, 462)), (4, (440, 345)), (5, (440, 520)), (6, (845, 392))],
       [(40, 438, 198, 486), (450, 500, 680, 542), (862, 368, 1240, 416)])
marcar('d_alertas.jpg', 'alertas_marcada.jpg', [(1, (18, 434))], [(38, 416, 474, 456)])
