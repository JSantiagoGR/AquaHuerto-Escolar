"""Recorta y endereza (perspectiva) partes de las fotos reales para usarlas como texturas en Blender.
Ejecutar: py texturas_fotos.py <foto_gabinete.jpg> <foto_ping.jpg> <carpeta_salida>"""
import os
import sys

import numpy as np
from PIL import Image, ImageEnhance


def coeficientes(dst, src):
    """Coeficientes de Image.PERSPECTIVE que llevan el rectángulo dst al cuadrilátero src."""
    a = []
    for (x, y), (u, v) in zip(dst, src):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    b = np.array(src).reshape(8)
    return np.linalg.solve(np.array(a, float), b)


def enderezar(im, quad, ancho, alto, escala, brillo=1.0):
    quad = [(x * escala, y * escala) for x, y in quad]
    dst = [(0, 0), (ancho, 0), (ancho, alto), (0, alto)]
    out = im.transform((ancho, alto), Image.PERSPECTIVE, coeficientes(dst, quad), Image.BICUBIC)
    return ImageEnhance.Brightness(out).enhance(brillo)


gab, ping, sal = sys.argv[1:4]
os.makedirs(sal, exist_ok=True)
g = Image.open(gab).convert('RGB')
k = g.size[0] / 1659.0                    # las coordenadas se tomaron sobre la vista de 1659 px de ancho
# batería (cara grande con la etiqueta), esquinas: arriba-izq, arriba-der, abajo-der, abajo-izq
enderezar(g, [(992, 628), (1386, 652), (1398, 1293), (935, 1284)], 640, 1030, k, 1.05).save(
    os.path.join(sal, 'tex_bateria_frente.png'))
# frente del controlador de carga (marco negro con bornes, panel azul, pantalla, USB)
enderezar(g, [(226, 1428), (790, 1426), (788, 1762), (220, 1760)], 1130, 670, k, 1.05).save(
    os.path.join(sal, 'tex_controlador_frente.png'))
# placa de expansión morada (para el color y la serigrafía alrededor del ESP32)
enderezar(g, [(378, 642), (690, 655), (686, 890), (376, 878)], 940, 700, k, 1.1).save(
    os.path.join(sal, 'tex_placa_expansion.png'))
p = Image.open(ping).convert('RGB')
kp = p.size[0] / 1512.0
# tarjeta azul del PING))) (de frente, con el texto parallax / PING))) / GND 5V SIG)
enderezar(p, [(492, 888), (962, 888), (962, 1105), (492, 1105)], 940, 434, kp, 1.15).save(
    os.path.join(sal, 'tex_ping_tarjeta.png'))
print('TEXTURAS_OK')
