"""Modelos 3D de AquaHuerto (CadQuery). Exporta STEP y STL por pieza y el ensamble completo.

Unidades: mm. Origen en el piso, esquina de la base del huerto.
Medidas: Reporte Integrador (bases y soporte), mediciones del huerto (cajón, tinaco, sensor a 127 cm) y EPANET v3
(subida a 1.52 m, salida del tinaco a 0.265 m, 3 líneas x 3 aspersores en 0.17/0.50/0.83 m).
"""
import math
import os
import sys

import cadquery as cq
from cadquery import Vector

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modelos_3d')


def tubo(p1, p2, a, b=None, t=3.0):
    """Perfil tubular rectangular (PTR) hueco de p1 a p2."""
    b = b or a
    p1, p2 = Vector(*p1), Vector(*p2)
    v = p2 - p1
    d = v.normalized()
    xd = Vector(0, 0, 1).cross(d) if abs(d.z) < 0.99 else Vector(1, 0, 0)
    pl = cq.Plane(origin=p1, xDir=xd, normal=d)
    return cq.Workplane(pl).rect(a, b).rect(a - 2 * t, b - 2 * t).extrude(v.Length)


def cil(p1, p2, r, ri=0):
    p1, p2 = Vector(*p1), Vector(*p2)
    v = p2 - p1
    d = v.normalized()
    xd = Vector(0, 0, 1).cross(d) if abs(d.z) < 0.99 else Vector(1, 0, 0)
    w = cq.Workplane(cq.Plane(origin=p1, xDir=xd, normal=d)).circle(r)
    if ri:
        w = w.circle(ri)
    return w.extrude(v.Length)


def caja(x0, y0, z0, dx, dy, dz):
    return cq.Workplane('XY').box(dx, dy, dz, centered=False).translate((x0, y0, z0))


def unir(partes):
    r = partes[0]
    for p in partes[1:]:
        r = r.union(p)
    return r


# ------------------------------------------------------------------ base del huerto (PTR 40x40x3, 6 patas)
def base_huerto():
    a, H, L = 40, 120, 1200
    zc = H - a / 2
    p = [tubo((0, a / 2, zc), (L, a / 2, zc), a), tubo((0, L - a / 2, zc), (L, L - a / 2, zc), a),
         tubo((a / 2, a, zc), (a / 2, L - a, zc), a), tubo((L - a / 2, a, zc), (L - a / 2, L - a, zc), a)]
    for x in (300, 600, 900):
        p.append(tubo((x, a, zc), (x, L - a, zc), a))
    for x, y in ((a / 2, a / 2), (L - a / 2, a / 2), (a / 2, L - a / 2), (L - a / 2, L - a / 2), (a / 2, L / 2), (L - a / 2, L / 2)):
        p.append(tubo((x, y, 6), (x, y, H - a), a))
        p.append(caja(x - 50, y - 50, 0, 100, 100, 6))
    return unir(p)


# ------------------------------------------------------------------ base del tinaco (PTR 50x50x3, 5 patas, 8 diagonales, placa 4 mm)
def base_tinaco():
    a, L, H = 50, 1200, 250
    zc = H - 4 - a / 2
    p = [tubo((0, a / 2, zc), (L, a / 2, zc), a), tubo((0, L - a / 2, zc), (L, L - a / 2, zc), a),
         tubo((a / 2, a, zc), (a / 2, L - a, zc), a), tubo((L - a / 2, a, zc), (L - a / 2, L - a, zc), a)]
    for x in (300, 600, 900):
        p.append(tubo((x, a, zc), (x, L - a, zc), a))
    pies = ((a / 2, a / 2), (L - a / 2, a / 2), (a / 2, L - a / 2), (L - a / 2, L - a / 2), (L / 2, L / 2))
    for x, y in pies:
        p.append(tubo((x, y, 6), (x, y, H - 4 - a), a))
        p.append(caja(x - 60, y - 60, 0, 120, 120, 6))
    # 8 diagonales (2 por pata de esquina)
    zb, s = 70, 140
    for x, y in pies[:4]:
        sx = 1 if x < L / 2 else -1
        sy = 1 if y < L / 2 else -1
        p.append(tubo((x, y + sy * a / 2, zb), (x, y + sy * s, zc - a / 2), 30, 30, 2))
        p.append(tubo((x + sx * a / 2, y, zb), (x + sx * s, y, zc - a / 2), 30, 30, 2))
    p.append(caja(0, 0, H - 4, L, L, 4))
    return unir(p)


# ------------------------------------------------------------------ soporte del panel (PTR 25x25x2, 30 grados)
def soporte_panel():
    a, t = 25, 2
    Lp, Wp = 680, 620
    x2 = Lp * math.cos(math.radians(30))
    z2 = Lp * math.sin(math.radians(30))
    p = []
    for y in (a / 2, Wp - a / 2):
        p.append(tubo((0, y, a / 2), (x2, y, a / 2), a, a, t))
        p.append(tubo((x2, y, a), (x2, y, z2), a, a, t))
        p.append(tubo((0, y, a), (x2 - a / 2, y, z2), a, a, t))
    p.append(tubo((x2, a, a / 2), (x2, Wp - a, a / 2), a, a, t))
    p.append(tubo((x2, a, z2 - a / 2), (x2, Wp - a, z2 - a / 2), a, a, t))
    p.append(caja(-40, 0, 0, 40, Wp, 3))
    return unir(p)


def panel_solar():
    Lp, Wp = 680, 620
    pl = caja(0, 0, 0, Lp, Wp, 25)
    return pl.rotate((0, 0, 0), (0, 1, 0), -30).translate((0, 0, 30))


# ------------------------------------------------------------------ cajón, sustrato y postes
def cajon():
    e, L, H = 25, 1000, 400
    ext = caja(0, 0, 0, L, L, H)
    hueco = caja(e, e, e, L - 2 * e, L - 2 * e, H)
    c = ext.cut(hueco)
    for x, y in ((0, 0), (L - 50, 0), (0, L - 50), (L - 50, L - 50)):
        c = c.union(caja(x, y, 0, 50, 50, 1450))
    return c


def sustrato():
    return caja(25, 25, 25, 950, 950, 375)


# ------------------------------------------------------------------ tinaco, sensor, gabinete
def tinaco():
    r, h = 450, 1020
    t = cq.Workplane('XY').circle(r).extrude(h)
    tapa = cq.Workplane('XY').circle(220).extrude(30).translate((0, 0, h))
    return t.union(tapa)


def sensor_nivel():
    return caja(-45, -35, 0, 90, 70, 50)


def gabinete():
    return caja(0, 0, 0, 300, 160, 400)


# ------------------------------------------------------------------ hidráulica
def tuberia(puntos, r=10):
    p = []
    for a, b in zip(puntos[:-1], puntos[1:]):
        p.append(cil(a, b, r, r - 2))
    return unir(p)


def ensamble():
    """Distribución de la instalación real (igual que la escena de Blender): cajón centrado en el origen,
    línea en el piso hacia -Y y tinaco a 3.75 m, junto a la pared."""
    TY = -3750
    piezas = {}
    piezas['base_huerto'] = (base_huerto(), (-600, -600, 0), (0.18, 0.18, 0.2))
    piezas['cajon'] = (cajon(), (-500, -500, 120), (0.62, 0.42, 0.17))
    piezas['sustrato'] = (sustrato(), (-500, -500, 120), (0.17, 0.12, 0.09))
    piezas['base_tinaco'] = (base_tinaco(), (-600, TY - 600, 0), (0.18, 0.18, 0.2))
    piezas['tinaco'] = (tinaco(), (0, TY, 250), (0.05, 0.05, 0.06))
    piezas['sensor_nivel'] = (sensor_nivel(), (0, TY, 250 + 1050), (0.85, 0.9, 0.95))
    piezas['gabinete'] = (gabinete(), (800, TY - 300, 1300), (0.9, 0.9, 0.88))
    piezas['soporte_panel'] = (soporte_panel(), (1300, TY - 1000, 0), (0.75, 0.75, 0.78))
    piezas['panel_solar'] = (panel_solar(), (1300, TY - 1000, 0), (0.05, 0.1, 0.25))
    ZP, ZM, YF = 35, 1475, -540
    lin = [(0, TY + 450, 265), (0, TY + 650, 265), (0, TY + 650, ZP), (0, -850, ZP), (0, -580, 60), (0, -580, ZM - 30),
           (0, YF, ZM)]
    piezas['tuberia'] = (tuberia(lin, 12), (0, 0, 0), (0.03, 0.32, 0.12))
    man = tuberia([(-330, YF, ZM), (330, YF, ZM)], 12)
    lat = [tuberia([(x, YF, ZM), (x, 500, ZM)], 8) for x in (-330, 0, 330)]
    piezas['mangueras'] = (unir([man] + lat), (0, 0, 0), (0.03, 0.03, 0.03))
    asp = [cil((x, y, ZM - 8), (x, y, ZM - 70), 9) for x in (-330, 0, 330) for y in (-330, 0, 330)]
    piezas['microaspersores'] = (unir(asp), (0, 0, 0), (0.85, 0.1, 0.1))
    piezas['caja_valvula'] = (caja(-100, -1410, 10, 200, 280, 130), (0, 0, 0), (0.42, 0.43, 0.43))
    piezas['caja_caudalimetro'] = (caja(-90, -1720, 10, 180, 240, 100), (0, 0, 0), (0.03, 0.03, 0.035))
    piezas['caja_bomba'] = (caja(-150, -2160, 10, 300, 360, 130), (0, 0, 0), (0.42, 0.43, 0.43))
    piezas['valvula_esfera'] = (cil((0, TY + 700, ZP), (0, TY + 790, ZP), 17), (0, 0, 0), (0.1, 0.4, 0.9))
    piezas['filtro_y'] = (cil((0, TY + 1130, ZP), (0, TY + 1250, ZP), 20), (0, 0, 0), (0.45, 0.38, 0.28))
    return piezas


def exportar():
    from cadquery import exporters
    os.makedirs(os.path.join(OUT, 'STEP'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'STL'), exist_ok=True)
    sueltas = {'Base_del_huerto': base_huerto(), 'Base_del_tinaco': base_tinaco(), 'Soporte_del_panel_solar': soporte_panel(),
               'Cajon_de_cultivo': cajon(), 'Tinaco': tinaco()}
    for n, s in sueltas.items():
        exporters.export(s, os.path.join(OUT, 'STEP', n + '.step'))
        exporters.export(s, os.path.join(OUT, 'STL', n + '.stl'), tolerance=0.5, angularTolerance=0.2)
    asm = cq.Assembly(name='AquaHuerto')
    pz = ensamble()
    os.makedirs(os.path.join(OUT, 'STL', 'ensamble'), exist_ok=True)
    for n, (s, pos, col) in pz.items():
        asm.add(s, name=n, loc=cq.Location(Vector(*pos)), color=cq.Color(*col))
        exporters.export(s.translate(pos), os.path.join(OUT, 'STL', 'ensamble', n + '.stl'), tolerance=0.5, angularTolerance=0.2)
    asm.save(os.path.join(OUT, 'STEP', 'Ensamble_AquaHuerto.step'))
    with open(os.path.join(OUT, 'STL', 'ensamble', 'colores.txt'), 'w') as f:
        for n, (_, _, col) in pz.items():
            f.write('%s %.3f %.3f %.3f\n' % (n, *col))
    print('listo', OUT)


if __name__ == '__main__':
    exportar()
