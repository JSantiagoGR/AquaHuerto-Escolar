"""Componentes del gabinete y del tinaco RECREADOS (forma 3D + textos 3D), sin texturas de fotos:
batería 12 V 9 Ah -> controlador de carga PWM -> sensor PING))) con su caja de acrílico.

Abre AquaHuerto_componentes_reales.blend (sin modificarlo), quita los planos con fotos y guarda
AquaHuerto_componentes_modelados.blend.
Ejecutar: blender -b -P escena_componentes_modelados.py -- <carpeta_modelos_3D> [bateria] [controlador] [ping] [--video]
(sin nombres de piezas = todas)
"""
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
DIR = args[0]
PIEZAS = [a for a in args[1:] if not a.startswith('--')] or ['bateria', 'controlador', 'ping']
VIDEO = '--video' in args
NUEVO = os.path.join(DIR, 'AquaHuerto_componentes_modelados.blend')
REN = os.path.join(DIR, 'renders')
FUENTES = 'C:/Windows/Fonts/'
bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_componentes_reales.blend'))
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
sc = bpy.context.scene
sc.frame_set(1)
col = bpy.data.collections['Gabinete y sensor del tinaco']
GX, GZ, YB = -0.95, 1.45, -3.99


def P(u, v, w):
    return Vector((GX - u, YB + w, GZ + v))


def borrar(*prefijos):
    for o in list(bpy.data.objects):
        if any(o.name == p or o.name.startswith(p + '.') for p in prefijos):
            bpy.data.objects.remove(o, do_unlink=True)


def mat(nombre, color, rough=0.5, metal=0.0, emision=None, spec=0.5):
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Specular'].default_value = spec
    if emision:
        b.inputs['Emission'].default_value = (*emision, 1)
        b.inputs['Emission Strength'].default_value = 2.0
    return m


def ligar(o):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    return o


def caja_w(nombre, centro, dim, m, bisel=0.0):
    """Caja en coordenadas mundo (centro) con dimensiones mundo (dx, dy, dz)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=centro)
    o = bpy.context.object
    o.name = nombre
    o.scale = dim
    bpy.ops.object.transform_apply(scale=True)
    if bisel:
        md = o.modifiers.new('bisel', 'BEVEL')
        md.width, md.segments, md.limit_method = bisel, 3, 'ANGLE'
    o.data.materials.append(m)
    return ligar(o)


def caja(nombre, u, v, w, du, dv, dw, m, bisel=0.0):
    return caja_w(nombre, P(u, v, w), (du, dw, dv), m, bisel)


def cil_w(nombre, p1, p2, r, m, n=24):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=d.length, location=(p1 + p2) / 2)
    o = bpy.context.object
    o.name = nombre
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    o.data.materials.append(m)
    return ligar(o)


def tubo(nombre, puntos, r, m):
    pts = [Vector(p) for p in puntos]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    mu = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        n = max(6, int((p2 - p1).length / 0.003))
        for k in range(n):
            t = k / n
            mu.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                             (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    mu.append(pts[-1])
    cu = bpy.data.curves.new(nombre, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(len(mu) - 1)
    for p, q in zip(sp.points, mu):
        p.co = (q.x, q.y, q.z, 1)
    o = bpy.data.objects.new(nombre, cu)
    o.data.materials.append(m)
    col.objects.link(o)
    return o


def fuente(archivo):
    return bpy.data.fonts.load(FUENTES + archivo, check_existing=True)


ALTO_MAYUS = {'arial.ttf': 0.716, 'arialbd.ttf': 0.716, 'ARIALN.TTF': 0.716, 'ARIALNB.TTF': 0.716, 'seguisym.ttf': 0.75,
              'segoeuib.ttf': 0.70, 'segoeui.ttf': 0.70, 'bahnschrift.ttf': 0.70, 'impact.ttf': 0.79}


def texto(nombre, cuerpo, base, eje_lectura, eje_arriba, alto_mayus, archivo, m, largo=None, alinear='LEFT',
          interlineado=1.0, extrusion=0.0):
    """Texto 3D plano. base = punto del inicio de la línea base (mundo); eje_lectura/eje_arriba = direcciones mundo.
    alto_mayus en metros; si se da 'largo' (m), se ajusta el ancho para que la línea mida eso (como en la foto)."""
    cu = bpy.data.curves.new(nombre, 'FONT')
    cu.body = cuerpo
    cu.font = fuente(archivo)
    cu.size = alto_mayus / ALTO_MAYUS.get(archivo, 0.72)
    cu.align_x = alinear
    cu.space_line = interlineado
    cu.extrude = extrusion
    o = bpy.data.objects.new(nombre, cu)
    o.data.materials.append(m)
    col.objects.link(o)
    x = Vector(eje_lectura).normalized()
    y = Vector(eje_arriba).normalized()
    z = x.cross(y)
    o.matrix_world = Matrix.Translation(Vector(base)) @ Matrix((x, y, z)).transposed().to_4x4()
    if largo:
        bpy.context.view_layer.update()
        if o.dimensions.x > 0:
            o.scale.x = largo / o.dimensions.x
    return o


BLANCO_T = mat('Texto blanco impreso', (0.92, 0.92, 0.9), 0.55)
NEGRO_T = mat('Texto negro impreso', (0.01, 0.01, 0.01), 0.6)
METAL = mat('Metal tornillo real', (0.75, 0.75, 0.78), 0.3, 1.0)
LATON = mat('Laton terminal F2', (0.78, 0.72, 0.55), 0.3, 1.0)
CABLE_N = mat('Cable negro 14 AWG', (0.012, 0.012, 0.012), 0.45)

# quitar los planos con fotos de la versión anterior
borrar('Bateria - etiqueta real (foto)', 'Controlador - frente real (foto)', 'PING))) - tarjeta real (foto)')

# ======================================================================================== BATERÍA 12 V 9 Ah
if 'bateria' in PIEZAS:
    borrar('Bateria 12 V 9 Ah', 'Bateria - terminal F2', 'Bateria + (rojo)', 'Bateria - (negro)', 'Terminal ojo rojo',
           'Terminal ojo azul')
    bu, bv = 0.085, 0.06
    BA, BH, BF = 0.094, 0.151, 0.065           # ancho (u), alto (v), fondo (w)
    W0 = 0.006                                 # fondo del gabinete
    UL, VB, WF = bu - BA / 2, bv - BH / 2, W0 + BF   # borde izquierdo, borde de abajo, cara frontal
    CAJA_B = mat('Bateria ABS negro', (0.018, 0.018, 0.02), 0.42, spec=0.45)
    ETQ_N = mat('Bateria etiqueta negra brillante', (0.008, 0.008, 0.01), 0.38, spec=0.35)
    TAPA = 0.0148                              # la tapa (lado de las terminales) ocupa el lado izquierdo
    caja('Bateria - cuerpo', bu + TAPA / 2, bv, W0 + BF / 2, BA - TAPA, BH, BF, CAJA_B, 0.0018)
    caja('Bateria - tapa (lado de terminales)', UL + TAPA / 2 - 0.0002, bv, W0 + BF / 2, TAPA - 0.0008, BH + 0.0008,
         BF + 0.0008, CAJA_B, 0.0016)
    caja('Bateria - ranura de la tapa', UL + TAPA, bv, W0 + BF / 2, 0.0009, BH - 0.002, BF - 0.002,
         mat('Ranura negra', (0.004, 0.004, 0.004), 0.8))
    caja('Bateria - etiqueta (fondo negro)', bu + TAPA / 2 + 0.0002, bv, WF + 0.00015, BA - TAPA - 0.003, BH - 0.003,
         0.0003, ETQ_N)
    # terminales F2 (6.35 mm) en el lado izquierdo, abajo; + al frente con marca roja, - atrás con marca negra
    VT = VB + 0.0095
    for nombre_t, wt, marca in (('+', W0 + 0.05, mat('Marca roja +', (0.7, 0.03, 0.02), 0.4)),
                                ('-', W0 + 0.015, mat('Marca negra -', (0.03, 0.03, 0.03), 0.5))):
        caja(f'Bateria - base de terminal {nombre_t}', UL - 0.0012, VT, wt, 0.0024, 0.011, 0.011, marca, 0.0008)
        caja(f'Bateria - terminal F2 {nombre_t}', UL - 0.0024 - 0.0035, VT, wt, 0.007, 0.00635, 0.0008, LATON, 0.0002)
        cil_w(f'Bateria - orificio terminal {nombre_t}', P(UL - 0.0055, VT, wt - 0.0006), P(UL - 0.0055, VT, wt + 0.0006),
              0.0011, mat('Hueco', (0.0, 0.0, 0.0), 0.9), 12)
        texto(f'Bateria - simbolo {nombre_t}', '−' if nombre_t == '-' else '+', P(UL - 0.0003, VT + 0.0075, wt - 0.0022),
              (0, 1, 0), (0, 0, 1), 0.0045, 'arialbd.ttf', BLANCO_T)     # sobre la tapa (cara izquierda)
    # conectores hembra de pala aislados (rojo en +, azul en -) y cables negros 14 AWG hacia el controlador
    for nombre_t, wt, color, inicio in (('+', W0 + 0.05, (0.75, 0.04, 0.03), (-0.073, -0.093 + 0.042, 0.036)),
                                        ('-', W0 + 0.015, (0.05, 0.2, 0.75), (-0.06, -0.093 + 0.042, 0.036))):
        ais = mat(f'Aislante pala {nombre_t}', color, 0.35)
        caja(f'Bateria - pala metalica {nombre_t}', UL - 0.0058, VT, wt, 0.0075, 0.0075, 0.0026, METAL, 0.0003)
        cil_w(f'Bateria - aislante de la pala {nombre_t}', P(UL - 0.0093, VT, wt), P(UL - 0.0205, VT, wt), 0.0034, ais, 20)
        cil_w(f'Bateria - cuello del aislante {nombre_t}', P(UL - 0.0205, VT, wt), P(UL - 0.0225, VT, wt), 0.0024, ais, 16)
        tubo(f'Bateria {nombre_t} (cable negro)', [P(*inicio), P(-0.03, -0.035, 0.034), P(0.0, -0.03, wt),
                                                   P(UL - 0.04, VT - 0.012, wt), P(UL - 0.022, VT, wt)], 0.0021, CABLE_N)

    # ---------------- etiqueta: textos medidos sobre la foto (px de la foto enderezada 640 x 1030 = 94 x 151 mm)
    def F(x, y):                 # px -> punto de la cara frontal
        return P(UL + x / 6.809 / 1000, VB + (151 - y / 6.821) / 1000, WF + 0.00035)

    LEER, ARRIBA = (0, 0, 1), (1, 0, 0)       # se lee de abajo hacia arriba; la parte de arriba de las letras va a la izquierda

    def T(nombre, txt, x, y0, y1, cap_px, archivo='arial.ttf', m=BLANCO_T, **kw):
        largo = (y0 - y1) / 6.821 / 1000 if y1 is not None else None
        return texto('Bateria - ' + nombre, txt, F(x, y0) + Vector((0, 0.0005, 0)), LEER, ARRIBA, cap_px / 6.81 / 1000, archivo, m, largo, **kw)

    def R(nombre, x0, y0, x1, y1, m, dz=0.0, bisel=0.0):
        a, b = F(x0, y0), F(x1, y1)
        return caja_w('Bateria - ' + nombre, ((a + b) / 2) + Vector((0, 0.00005 + dz, 0)),
                      (abs(a.x - b.x), 0.0001, abs(a.z - b.z)), m, bisel)

    T('PRECAUTIONS', 'PRECAUTIONS:', 165, 607, 380, 19, 'arialbd.ttf')
    R('subrayado PRECAUTIONS', 167, 607, 170, 380, BLANCO_T)
    for i, (t, yf) in enumerate((('Keep out of reach of children.', 330), ('Read instruction manual carefully.', 272),
                                 ('Replace every 3-5 years.', 372), ('Do not discharge below 10.5V under load.', 198),
                                 ('Limited warranty applies.', 348))):
        T('precaucion %d' % i, '\u2022   ' + t, 191 + i * 22.5, 607, yf, 13)
    T('HAZARDS', 'HAZARDS:', 168, 988, 848, 19, 'arialbd.ttf')
    R('subrayado HAZARDS', 170, 988, 173, 848, BLANCO_T)
    for i, (t, yf) in enumerate((('Do not short circuit.', 822), ('Do not charge in sealed container.', 690),
                                 ('Recharge after use at low voltage.', 700), ('Keep away from sparks or open flames.', 650))):
        T('peligro %d' % i, '\u2022   ' + t, 193 + i * 22.5, 988, yf, 13)
    T('triangulo WARNING', '\u26A0', 314, 996, None, 48, 'seguisym.ttf', mat('Amarillo advertencia', (0.95, 0.75, 0.05), 0.4))
    T('WARNING', 'WARNING:', 309, 958, 842, 16, 'arialbd.ttf')
    T('aviso 1', 'Battery posts, terminals and related accessories contain lead and lead', 309, 835, 165, 13)
    T('aviso 2', 'compounds. This product contains chemicals known to the State of California to cause cancer,', 337, 990, 140, 13)
    T('aviso 3', 'birth defects, or other reproductive harm.', 363, 990, 615, 13)
    T('aviso 4', 'For more information: www.P65Warnings.ca.gov', 395, 990, 595, 12)

    # código de barras (calcomanía blanca)
    R('codigo de barras (fondo)', 226, 30, 326, 137, mat('Etiqueta blanca codigo', (0.93, 0.93, 0.91), 0.5), 0.0, 0.0002)
    random.seed(7)
    y = 42
    while y < 125:
        g = random.choice((1.2, 1.2, 2.2, 3.4))
        R('barra', 236, y, 300, y + g, NEGRO_T, 0.0001)
        y += g + random.choice((1.4, 2.2, 3.0))
    T('digitos codigo', '8   60000   52498   8', 318, 133, 34, 7, 'arial.ttf', NEGRO_T)

    # recuadro DANGER / POISON
    R('recuadro (borde blanco)', 418, 33, 637, 1003, BLANCO_T, 0.0, 0.0006)
    R('recuadro franja negra', 422, 38, 468, 998, ETQ_N, 0.0001)
    R('recuadro celdas blancas', 470, 38, 633, 998, mat('Etiqueta blanca celdas', (0.93, 0.93, 0.9), 0.5), 0.0001)
    T('DANGER / POISON', 'DANGER / POISON', 459, 727, 372, 23, 'arialbd.ttf')
    for y0 in (770, 352):
        T('triangulo DANGER', '\u26A0', 466, y0, None, 60, 'seguisym.ttf')
    cortes = [1000, 835, 700, 535, 395, 215, 38]
    for yc in cortes[1:-1]:
        for k in range(9):
            x0 = 474 + k * 18
            R('linea punteada', x0, yc - 0.8, x0 + 9, yc + 0.8, NEGRO_T, 0.0002)
    celdas = [('\u25C9\u25C9', 'SHIELD EYES.\nEXPLOSIVE GASES\nCAN CAUSE BLINDNESS\nOR INJURY.'),
              ('\u2697', 'SULFURIC ACID\nCAN CAUSE\nBLINDNESS OR\nSEVERE BURNS.'),
              ('\u271A', 'FLUSH EYES\nIMMEDIATELY WITH\nWATER. GET MEDICAL\nHELP FAST.'),
              ('!', 'SKIN, EYE, OR\nRESPIRATORY\nTRACT IRRITANTS'),
              ('\u2738', 'HEALTH HAZARD: CAUSE\nRESPIRATORY IRRITATION,\nREPRODUCTIVE OR\nORGAN TOXICITY.'),
              ('\u2663', 'CHEMICAL IS\nTOXIC TO AQUATIC\nWILDLIFE')]
    for i, (icono, txt) in enumerate(celdas):
        yc = (cortes[i] + cortes[i + 1]) / 2
        T('icono %d' % i, icono, 545, yc, None, 70 if icono != '!' else 50, 'seguisym.ttf' if icono != '!' else 'arialbd.ttf',
          NEGRO_T, alinear='CENTER')
        T('texto celda %d' % i, txt, 588, yc, None, 11, 'ARIALNB.TTF', NEGRO_T, alinear='CENTER', interlineado=0.92)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

# ======================================================================================== CONTROLADOR DE CARGA PWM
if 'controlador' in PIEZAS:
    borrar('Controlador - cuerpo negro', 'Controlador - oreja', 'Controlador - tornillo de borne', 'Controlador - boton',
           'Cable carga 1', 'Cable carga 2', 'Bateria + (cable negro)', 'Bateria - (cable negro)')
    cu_, cv_ = -0.087, -0.093
    CW, CH = 0.130, 0.077                       # medido contra la batería en la foto (130 x 77 mm con orejas)
    W0 = 0.006
    WC = W0 + 0.030                             # frente del cuerpo
    PXU, PXV = 1130 / 130.0, 670 / 77.0         # px por mm de la foto enderezada

    def C(x, y, w):                             # px de la foto -> punto
        return P(cu_ - CW / 2 + x / PXU / 1000, cv_ + CH / 2 - y / PXV / 1000, w)

    def RC(nombre, x0, y0, x1, y1, w0, w1, m, bisel=0.0):
        a, b = C(x0, y0, w0), C(x1, y1, w1)
        return caja_w('Controlador - ' + nombre, (a + b) / 2, (abs(a.x - b.x), abs(a.y - b.y), abs(a.z - b.z)), m, bisel)

    def CIL(nombre, x, y, w0, w1, r_px, m, n=24):
        return cil_w('Controlador - ' + nombre, C(x, y, w0), C(x, y, w1), r_px / PXU / 1000, m, n)

    LEER_C, ARRIBA_C = (1, 0, 0), (0, 0, -1)    # el controlador está montado de cabeza: todo el texto va invertido

    def TC(nombre, txt, x, y_base, cap_px, w, archivo='arial.ttf', m=BLANCO_T, ancho_px=None, alinear='CENTER', **kw):
        largo = ancho_px / PXU / 1000 if ancho_px else None
        return texto('Controlador - ' + nombre, txt, C(x, y_base, w), LEER_C, ARRIBA_C, cap_px / PXV / 1000, archivo, m,
                     largo, alinear, **kw)

    NEG_C = mat('Controlador plastico negro', (0.012, 0.012, 0.013), 0.5, spec=0.4)
    AZUL_C = mat('Controlador panel azul', (0.008, 0.11, 0.52), 0.35)
    CELESTE = mat('Controlador recuadro celeste', (0.2, 0.55, 0.9), 0.4)
    LCD_C = mat('Controlador LCD', (0.33, 0.36, 0.27), 0.15, spec=0.6)
    MARCO_LCD = mat('Controlador marco LCD', (0.05, 0.06, 0.06), 0.4)
    BOTON = mat('Controlador boton negro', (0.01, 0.01, 0.01), 0.3, spec=0.6)
    USB_MET = mat('USB metal', (0.7, 0.7, 0.72), 0.25, 1.0)
    HUECO = mat('Hueco', (0.0, 0.0, 0.0), 0.9)

    # orejas de montaje con tornillos al gabinete
    RC('oreja izquierda', 0, 0, 72, 670, W0, W0 + 0.0035, NEG_C, 0.0008)
    RC('oreja derecha', 1058, 0, 1130, 670, W0, W0 + 0.0035, NEG_C, 0.0008)
    for x, y in ((32, 95), (32, 540), (1100, 85), (1100, 515)):
        CIL('tornillo de la oreja', x, y, W0 + 0.0035, W0 + 0.0058, 22, METAL, 20)
        RC('ranura del tornillo', x - 18, y - 2.5, x + 18, y + 2.5, W0 + 0.0055, W0 + 0.0061, HUECO)
    # cuerpo y cubierta de bornes (parte de arriba)
    RC('cuerpo', 72, 0, 1058, 670, W0, WC, NEG_C, 0.002)
    RC('cubierta de bornes', 100, 30, 1030, 215, WC - 0.002, WC + 0.0045, NEG_C, 0.0025)
    for k, x in enumerate((340, 430, 518, 605, 690, 777)):
        CIL('hueco del borne', x, 130, WC + 0.0035, WC + 0.0047, 27, HUECO, 20)
        CIL('tornillo de borne', x, 130, WC + 0.002, WC + 0.0050, 22, METAL, 20)
        RC('cruz del tornillo', x - 15, 128, x + 15, 132, WC + 0.0049, WC + 0.0052, HUECO)
        RC('cruz del tornillo', x - 2, 115, x + 2, 145, WC + 0.0049, WC + 0.0052, HUECO)
        RC('entrada de cable', x - 16, -2, x + 16, 6, WC - 0.012, WC - 0.004, HUECO)       # orificios en el canto de arriba
    # símbolos de los bornes (carga, batería, panel), de cabeza como en la foto
    for xs, icono in ((385, '☼'), (561, '▭'), (733, '▦')):
        TC('simbolo de borne', icono, xs, 166, 30, WC + 0.0047, 'seguisym.ttf')
        TC('signo -', '−', xs - 45, 170, 18, WC + 0.0047, 'arialbd.ttf')
        TC('signo +', '+', xs + 45, 170, 18, WC + 0.0047, 'arialbd.ttf')
    # panel azul
    RC('panel azul', 140, 215, 965, 642, WC, WC + 0.0006, AZUL_C, 0.0006)
    WP = WC + 0.0006
    for x, y in ((425, 300), (563, 297), (698, 295)):
        CIL('aro del boton', x, y, WP, WP + 0.0006, 40, NEG_C, 28)
        CIL('boton', x, y, WP, WP + 0.003, 34, BOTON, 28)
    for x, icono in ((420, '☼/▲'), (563, '▲'), (690, '⇆')):
        TC('icono del boton', icono, x, 355, 26, WP + 0.0002, 'seguisym.ttf')
    RC('marco de la pantalla', 398, 380, 722, 596, WP, WP + 0.0008, MARCO_LCD, 0.0004)
    RC('pantalla LCD', 410, 390, 712, 588, WP + 0.0008, WP + 0.0011, LCD_C)
    RC('marco USB', 170, 450, 324, 614, WP, WP + 0.0018, NEG_C, 0.0006)
    for y0 in (470, 535):
        RC('puerto USB (lamina)', 190, y0, 305, y0 + 55, WP + 0.0018, WP + 0.0024, USB_MET, 0.0002)
        RC('puerto USB (hueco)', 196, y0 + 6, 299, y0 + 49, WP + 0.0024, WP + 0.0025, HUECO)
        RC('puerto USB (lengüeta)', 200, y0 + 30, 295, y0 + 44, WP + 0.0025, WP + 0.0026, BLANCO_T)
    TC('logo USB', 'USB', 258, 398, 30, WP + 0.0002, 'arialbd.ttf', ancho_px=92)
    TC('logo USB (punta)', '◀', 330, 398, 22, WP + 0.0002, 'seguisym.ttf')
    TC('SOLAR CHARGE CONTROLLER', 'SOLAR CHARGE CONTROLLER', 557, 612, 24, WP + 0.0002, 'arial.ttf', ancho_px=515)
    # recuadros celestes con icono y texto
    for (x0, y0, x1, y1), (linea, icono) in zip(((745, 320, 837, 447), (855, 320, 950, 447), (745, 465, 837, 588), (855, 465, 950, 588)),
                                               (('FULL\nprotect', '\U0001F512'), ('Build-in\ntimer', 'Ⓛ'),
                                                ('SET\nvoltage', '⚙'), ('MCU\ncontrol', '▣'))):
        RC('recuadro celeste', x0, y0, x1, y1, WP, WP + 0.0003, CELESTE, 0.0015)
        xc = (x0 + x1) / 2
        TC('texto del recuadro', linea, xc, y0 + 22, 13, WP + 0.0004, 'arial.ttf', NEGRO_T, interlineado=0.9)
        TC('icono del recuadro', icono, xc, y0 + 55, 75, WP + 0.0004, 'seguisym.ttf', NEGRO_T)

    # cables: azules (salida de carga) a los WAGO y negros (batería) a las palas de la batería
    def boca(x):                 # entrada del cable en el canto de arriba
        return C(x, -2, WC - 0.008)

    CAB_AZ = bpy.data.materials.get('Cable azul') or mat('Cable azul', (0.05, 0.2, 0.75), 0.4)
    for k, x in enumerate((340, 430)):
        b = boca(x)
        tubo(f'Cable carga {k + 1}', [b, b + Vector((0, 0.002, 0.012)), P(-0.1 + k * 0.012, -0.025, 0.03),
                                      P(-0.1 + k * 0.01, 0.0, 0.03), P(-0.07 + k * 0.007, -0.025, 0.02)], 0.0016, CAB_AZ)
    bu, bv = 0.085, 0.06
    UL, VT = bu - 0.047, bv - 0.0755 + 0.0095
    for nombre_t, x, wt in (('-', 518, W0 + 0.015), ('+', 605, W0 + 0.05)):
        b = boca(x)
        tubo(f'Bateria {nombre_t} (cable negro)', [b, b + Vector((0, 0.002, 0.012)), P(-0.03, -0.035, 0.034),
                                                   P(0.0, -0.03, wt), P(UL - 0.04, VT - 0.012, wt), P(UL - 0.022, VT, wt)],
             0.0021, CABLE_N)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

# ======================================================================================== SENSOR PING))) + CAJA DE ACRÍLICO
if 'ping' in PIEZAS:
    borrar('Caja acrilica del sensor', 'Oreja de acrilico', 'Tornillo de la oreja', 'PING))) - tarjeta azul',
           'PING))) - transductor', 'PING))) - malla', 'PING))) - pin', 'PING))) - cable blanco', 'PING))) - cable morado',
           'PING))) - cable azul')
    TY, ZT = -3.75, 1.258
    piv = bpy.data.objects['Tapa del tinaco (pivote)']
    sc.frame_set(1)
    bpy.context.view_layer.update()
    nuevos_ping = []

    def adoptar(o):
        nuevos_ping.append(o)
        return o

    ACR = mat('Acrilico transparente (caja PING)', (0.92, 0.97, 0.98), 0.04)
    _b = ACR.node_tree.nodes['Principled BSDF']
    _b.inputs['Alpha'].default_value = 0.18
    ACR.blend_method = 'BLEND'
    ACR.show_transparent_back = False
    ACR_CANTO = mat('Acrilico canto', (0.85, 0.95, 0.97), 0.05)
    ACR_CANTO.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.45
    ACR_CANTO.blend_method = 'BLEND'
    ZINC = mat('Tornillo zincado', (0.78, 0.72, 0.5), 0.3, 1.0)
    PCB_PING = mat('PING PCB azul', (0.02, 0.09, 0.32), 0.45)
    SERIG = mat('PING serigrafia blanca', (0.88, 0.9, 0.92), 0.5)
    ALU = mat('PING aro de aluminio', (0.82, 0.83, 0.85), 0.22, 1.0)

    # coordenadas de la cara del sensor (vista desde el agua): a -> -X, b -> +Y, la cara mira hacia -Z
    def S(a, b, z):
        return Vector((-a / 1000, TY + b / 1000, z))

    E = 0.003                                   # acrílico de 3 mm
    AX, BY, PZ = 0.078, 0.060, 0.030            # caja: 78 x 60 mm, 30 mm de fondo bajo la tapa
    Z0, Z1 = ZT, ZT - PZ
    # base (la que da al agua) con dos perforaciones para los transductores y 4 paredes
    base = adoptar(caja_w('Caja de acrilico - base (cara al agua)', S(0, 0, Z1 + E / 2), (AX, BY, E), ACR))
    for sx in (-1, 1):
        cil = cil_w('perforacion', S(sx * 14.5, 4.2, Z1 - 0.002), S(sx * 14.5, 4.2, Z1 + E + 0.002), 0.0084, ACR, 40)
        md = base.modifiers.new('perforacion', 'BOOLEAN')
        md.object, md.operation = cil, 'DIFFERENCE'
        bpy.context.view_layer.objects.active = base
        bpy.ops.object.modifier_apply(modifier=md.name)
        bpy.data.objects.remove(cil, do_unlink=True)
    for sy in (-1, 1):
        adoptar(caja_w('Caja de acrilico - pared larga', S(0, sy * (BY / 2 - E / 2) * 1000, (Z0 + Z1) / 2 - E / 2),
                       (AX, E, PZ - E), ACR))
    for sx in (-1, 1):
        adoptar(caja_w('Caja de acrilico - pared corta', S(sx * (AX / 2 - E / 2) * 1000, 0, (Z0 + Z1) / 2 - E / 2),
                       (E, BY - 2 * E, PZ - E), ACR))
    # uniones de dedos (cortes láser): dientes alternados en las 4 aristas verticales y en el borde de la base
    for sx in (-1, 1):
        for sy in (-1, 1):
            n = 5
            for k in range(n):
                if k % 2 == 0:
                    z = Z0 - (k + 0.5) * PZ / n
                    adoptar(caja_w('Caja de acrilico - diente', S(sx * (AX / 2 + 0.0004) * 1000, sy * (BY / 2 - E / 2) * 1000, z),
                                   (0.0008, E, PZ / n * 0.92), ACR_CANTO))
    for sy in (-1, 1):
        for k in range(7):
            if k % 2 == 1:
                a = -AX / 2 + (k + 0.5) * AX / 7
                adoptar(caja_w('Caja de acrilico - diente', S(a * 1000, sy * (BY / 2 + 0.0004) * 1000, Z1 + E / 2),
                               (AX / 7 * 0.92, 0.0008, E), ACR_CANTO))
    # orejas: dos grandes del lado de los pines (-Y) y dos chicas del lado contrario, atornilladas a la tapa
    for a, b0, b1, ancho in ((-22.0, -30.0, -51.0, 13.5), (25.2, -30.0, -51.0, 13.5), (-19.5, 30.0, 35.0, 10.0),
                             (18.5, 30.0, 35.0, 10.0)):
        bm = (b0 + b1) / 2
        adoptar(caja_w('Caja de acrilico - oreja', S(a, bm, Z0 - E / 2), (ancho / 1000, abs(b1 - b0) / 1000, E), ACR))
        bt = b1 + (6.0 if b1 < 0 else -2.5)
        adoptar(cil_w('Tornillo de la oreja (cabeza)', S(a, bt, Z0 - E), S(a, bt, Z0 - E - 0.0022), 0.0034, ZINC, 24))
        for ang in (0, 90):
            ln = Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0)) * 0.0045
            c = S(a, bt, Z0 - E - 0.0023)
            adoptar(caja_w('Tornillo de la oreja (cruz)', c, (abs(ln.x) + 0.0007, abs(ln.y) + 0.0007, 0.0004), mat('Hueco', (0, 0, 0), 0.9)))

    # tarjeta PING))) 45.7 x 21.3 mm: transductores al frente (hacia el agua), a ras de la base
    ZP = Z1 + 0.012                             # cara de componentes de la tarjeta
    adoptar(caja_w('PING))) - tarjeta (PCB)', S(0, 0, ZP + 0.0008), (0.0457, 0.0213, 0.0016), PCB_PING, 0.0003))
    for sx in (-1, 1):
        a = sx * 14.5
        aro = cil_w('PING))) - transductor (aro de aluminio)', S(a, 4.2, ZP), S(a, 4.2, Z1 - 0.0004), 0.0081, ALU, 48)
        hueco = cil_w('h', S(a, 4.2, Z1 + 0.0035), S(a, 4.2, Z1 - 0.003), 0.0068, ALU, 48)
        md = aro.modifiers.new('hueco', 'BOOLEAN')
        md.object, md.operation = hueco, 'DIFFERENCE'
        bpy.context.view_layer.objects.active = aro          # (después de crear el cilindro del hueco)
        bpy.ops.object.modifier_apply(modifier=md.name)
        bpy.data.objects.remove(hueco, do_unlink=True)
        adoptar(aro)
        MALLA = mat('PING malla dorada', (0.42, 0.33, 0.14), 0.55, 0.6)
        if not MALLA.node_tree.nodes.get('Cuadros'):
            nt = MALLA.node_tree
            ch = nt.nodes.new('ShaderNodeTexChecker')
            ch.name = 'Cuadros'
            ch.inputs['Scale'].default_value = 70.0
            ch.inputs['Color1'].default_value = (0.42, 0.33, 0.14, 1)
            ch.inputs['Color2'].default_value = (0.08, 0.06, 0.03, 1)
            tc = nt.nodes.new('ShaderNodeTexCoord')
            nt.links.new(tc.outputs['Generated'], ch.inputs['Vector'])
            nt.links.new(ch.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
        adoptar(cil_w('PING))) - malla del transductor', S(a, 4.2, Z1 + 0.0022), S(a, 4.2, Z1 + 0.0018), 0.0068, MALLA, 48))
        adoptar(cil_w('PING))) - fondo del transductor', S(a, 4.2, Z1 + 0.0045), S(a, 4.2, Z1 + 0.0040), 0.0068,
                      mat('Negro mate', (0.02, 0.02, 0.02), 0.7), 32))
    # serigrafía y piezas de la tarjeta (se lee mirando la cara del sensor; pines abajo)
    ZS = ZP - 0.00012
    LEER_P, ARRIBA_P = (-1, 0, 0), (0, 1, 0)

    def TP(nombre, txt, a, b, cap_mm, archivo='arial.ttf', m=SERIG, ancho=None, alinear='CENTER', leer=LEER_P, arriba=ARRIBA_P):
        return adoptar(texto('PING))) - ' + nombre, txt, S(a, b, ZS), leer, arriba, cap_mm / 1000, archivo, m,
                             ancho / 1000 if ancho else None, alinear))

    TP('www.parallax.com', 'www.parallax.com', 0.3, 7.6, 1.15, 'arialbd.ttf', ancho=13.5)
    TP('PING)))', 'PING)))', -0.6, -2.4, 2.0, 'arialbd.ttf', ancho=7.6)
    TP('TM', 'TM', 3.9, -3.0, 0.5, 'arial.ttf')
    TP('ACT', 'ACT', 0.0, 1.0, 0.9, 'arialbd.ttf')
    for x0, y0, x1, y1 in ((-2.0, 0.5, 2.0, 0.65), (-2.0, 4.6, 2.0, 4.75), (-2.0, 0.5, -1.85, 4.75), (1.85, 0.5, 2.0, 4.75)):
        adoptar(caja_w('PING))) - recuadro ACT', S((x0 + x1) / 2, (y0 + y1) / 2, ZS + 0.00005),
                       (abs(x1 - x0) / 1000, abs(y1 - y0) / 1000, 0.00008), SERIG))
    adoptar(caja_w('PING))) - LED ACT', S(0.0, 3.4, ZP - 0.0003), (0.0016, 0.0008, 0.0006), mat('LED rojo apagado', (0.35, 0.02, 0.02), 0.3)))
    for i, (et, a) in enumerate((('GND', -2.54), ('5V', 0.0), ('SIG', 2.54))):
        TP('etiqueta ' + et, et, a + 0.45, -8.6, 0.85, 'arialbd.ttf', alinear='LEFT', leer=(0, 1, 0), arriba=(1, 0, 0))
        for x0, x1, y0, y1 in ((a - 1.15, a + 1.15, -9.0, -8.85), (a - 1.15, a + 1.15, -4.5, -4.35)):
            adoptar(caja_w('PING))) - recuadro de pin', S((x0 + x1) / 2, (y0 + y1) / 2, ZS + 0.00005),
                           (abs(x1 - x0) / 1000, abs(y1 - y0) / 1000, 0.00008), SERIG))
        adoptar(caja_w('PING))) - linea entre pines', S(a + 1.25, -6.7, ZS + 0.00005), (0.00012, 0.0045, 0.00008), SERIG))
    TP('(c)2010', '©2010', -14.8, -9.6, 1.0, 'arial.ttf', ancho=6.5)
    adoptar(cil_w('PING))) - aro del barreno', S(-21.0, -7.3, ZS + 0.0001), S(-21.0, -7.3, ZS - 0.00002), 0.0017, SERIG, 24))
    adoptar(cil_w('PING))) - barreno', S(-21.0, -7.3, ZS + 0.0002), S(-21.0, -7.3, ZS - 0.00008), 0.0012,
                  mat('Hueco', (0, 0, 0), 0.9), 24))
    for a, b in ((-6.5, 1.2), (6.0, 1.0), (-6.0, -5.5), (6.5, -5.8), (-9.5, -2.0), (9.5, -2.5)):
        adoptar(caja_w('PING))) - componente SMD', S(a, b, ZP - 0.0004), (0.002, 0.0012, 0.0007), mat('Componente SMD', (0.05, 0.05, 0.05), 0.4)))
    # tira de 3 pines en el borde de abajo, paralela a la tarjeta
    adoptar(caja_w('PING))) - base negra de los pines', S(0, -10.3, ZP - 0.0013), (0.0078, 0.0025, 0.0025), mat('Negro mate', (0.02, 0.02, 0.02), 0.7)))
    ORO = mat('Dorado', (0.8, 0.65, 0.3), 0.3, 1.0)
    for i, a in enumerate((-2.54, 0.0, 2.54)):
        adoptar(caja_w('PING))) - pin', S(a, -14.8, ZP - 0.0013), (0.00064, 0.0095, 0.00064), ORO))
    # cables (blanco GND, morado 5V, azul SIG) con su conector, salen por la pared del lado de los pines
    adoptar(caja_w('PING))) - conector hembra 3 pines', S(0, -19.0, ZP - 0.0013), (0.0078, 0.0045, 0.0026),
                   mat('Negro mate', (0.02, 0.02, 0.02), 0.7)))
    for i, (cn, a) in enumerate((('blanco', -2.54), ('morado', 0.0), ('azul', 2.54))):
        m = bpy.data.materials.get('Cable ' + cn) or mat('Cable ' + cn, {'blanco': (0.85, 0.85, 0.85), 'morado': (0.35, 0.08, 0.5),
                                                                          'azul': (0.05, 0.2, 0.75)}[cn], 0.4)
        adoptar(tubo(f'PING))) - cable {cn}', [S(a, -21.0, ZP - 0.0013), S(a * 0.6, -25.5, ZP - 0.0005),
                                               S(-4 + i * 1.6, -BY * 1000 / 2 - 2, Z0 - 0.008), S(-30 + i * 1.6, -46, Z0 - 0.004),
                                               (-0.18, TY - 0.03, ZT - 0.004)], 0.0011, m))
    # todo lo nuevo va pegado a la tapa (se voltea con ella en el video)
    bpy.context.view_layer.update()
    for o in nuevos_ping:
        mw = o.matrix_world.copy()
        o.parent = piv
        o.matrix_parent_inverse = piv.matrix_world.inverted()
        o.matrix_world = mw
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

# ======================================================================================== imágenes de revisión
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.eevee.taa_render_samples = 64
sc.render.image_settings.file_format = 'PNG'
camara_video = sc.camera


def foto(nombre, pos, mira, lente, frame, arriba=None):
    cd = bpy.data.cameras.new(nombre)
    cd.lens, cd.clip_start = lente, 0.003
    c = bpy.data.objects.new(nombre, cd)
    col.objects.link(c)
    c.location = pos
    c.rotation_euler = (Vector(mira) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    sc.frame_set(frame)
    sc.camera = c
    sc.render.filepath = os.path.join(REN, nombre + '.png')
    bpy.ops.render.render(write_still=True)


if 'bateria' in PIEZAS:
    foto('modelado_bateria_frente', tuple(P(0.085, 0.06, 0.36)), tuple(P(0.085, 0.06, 0.07)), 32, 200)
    foto('modelado_bateria_etiqueta', tuple(P(0.11, 0.06, 0.2)), tuple(P(0.11, 0.06, 0.07)), 30, 200)
    foto('modelado_bateria_terminales', tuple(P(-0.03, -0.06, 0.2)), tuple(P(0.045, -0.01, 0.04)), 50, 200)
if 'controlador' in PIEZAS:
    foto('modelado_controlador_frente', tuple(P(-0.087, -0.093, 0.27)), tuple(P(-0.087, -0.093, 0.035)), 40, 200)
    foto('modelado_controlador_angulo', tuple(P(-0.03, -0.17, 0.2)), tuple(P(-0.087, -0.085, 0.035)), 40, 200)
if 'ping' in PIEZAS:
    piv = bpy.data.objects['Tapa del tinaco (pivote)']
    pcb = bpy.data.objects['PING))) - tarjeta (PCB)']
    for nombre, frame, dist, inclin, lente in (('modelado_ping_cara', 330, 0.13, 0.0, 50), ('modelado_ping_caja', 330, 0.2, 0.55, 40)):
        sc.frame_set(frame)
        bpy.context.view_layer.update()
        r = piv.matrix_world.to_3x3().normalized()
        n = (r @ Vector((0, 0, -1))).normalized()          # hacia donde miran los transductores
        arriba = (r @ Vector((0, 1, 0))).normalized()      # lado contrario a los pines
        zc = (n + inclin * (r @ Vector((-1, 0, 0)))).normalized()
        yc = (arriba - arriba.dot(zc) * zc).normalized()
        cd = bpy.data.cameras.new(nombre)
        cd.lens, cd.clip_start = lente, 0.003
        cp = bpy.data.objects.new(nombre, cd)
        col.objects.link(cp)
        cp.matrix_world = Matrix((list(yc.cross(zc)), list(yc), list(zc))).transposed().to_4x4()
        centro = sum((pcb.matrix_world @ Vector(c) for c in pcb.bound_box), Vector()) / 8   # (las mallas tienen el origen en 0)
        cp.location = centro + zc * dist
        sc.camera = cp
        sc.render.filepath = os.path.join(REN, nombre + '.png')
        bpy.ops.render.render(write_still=True)
sc.camera = camara_video
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
print('MODELADOS_OK', PIEZAS)
