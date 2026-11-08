"""Cajas de protección de dos partes (base y tapa) con la bomba, el caudalímetro y la electroválvula adentro.

Abre AquaHuerto_instalacion_realista.blend (sin modificarlo) y guarda una copia nueva AquaHuerto_cajas_abiertas.blend.
Las tapas están animadas: cerradas al inicio, se levantan y se apartan para ver el interior.
Ejecutar: blender -b -P escena_cajas.py -- <carpeta_modelos_3D>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

DIR = sys.argv[sys.argv.index('--') + 1:][0]
ORIG = os.path.join(DIR, 'AquaHuerto_instalacion_realista.blend')
NUEVO = os.path.join(DIR, 'AquaHuerto_cajas_abiertas.blend')
REN = os.path.join(DIR, 'renders')
bpy.ops.wm.open_mainfile(filepath=ORIG)
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
sc = bpy.context.scene

col = bpy.data.collections.new('Cajas y componentes internos')
sc.collection.children.link(col)

# ------------------------------------------------------------------ quitar las cajas macizas y los tramos de tubo que cambian
for o in list(bpy.data.objects):
    if o.name.startswith(('Caja gris pequena', 'Caja negra (caudalimetro)', 'Caja gris grande', 'Soporte negro',
                          'Tubo entre cajas', 'Codo salida bomba', 'Tubo verde al cajon', 'Poliducto a cajas y cajon',
                          'Poliducto a la caja grande', 'Poliducto al cajon')) or \
            (o.name.startswith('Soporte') and not o.name.startswith('Soporte del panel')):
        bpy.data.objects.remove(o, do_unlink=True)


def M(n):
    return bpy.data.materials[n]


def mat(nombre, color, rough=0.5, metal=0.0):
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


GRIS, NEGRO, VERDE, METAL = M('Caja gris'), M('Plastico negro'), M('Tuboplus verde'), M('Metal brillante')
BLANCO = mat('Plastico blanco valvula', (0.9, 0.9, 0.88), 0.35)
NEGRO_MATE = mat('Negro mate', (0.02, 0.02, 0.02), 0.7)
MOTOR = mat('Motor plateado', (0.6, 0.62, 0.65), 0.3, 0.9)
NARANJA_B = mat('Cuerpo bomba', (0.85, 0.82, 0.78), 0.4)
CABLE_R = mat('Cable rojo', (0.75, 0.03, 0.02), 0.4)
CABLE_N = mat('Cable negro', (0.01, 0.01, 0.01), 0.4)
CABLE_A = mat('Cable amarillo', (0.85, 0.7, 0.05), 0.4)
LATON = mat('Laton', (0.75, 0.6, 0.25), 0.3, 1.0)
MANG = mat('Manguera cristal', (0.75, 0.85, 0.9), 0.1)
ETIQ = mat('Etiqueta', (0.95, 0.85, 0.2), 0.5)


def poner(o):
    for c in o.users_collection:
        c.objects.unlink(o)
    col.objects.link(o)
    return o


def caja(nombre, c, d, m, bisel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c)
    o = bpy.context.object
    o.name = nombre
    o.scale = d
    bpy.ops.object.transform_apply(scale=True)
    if bisel:
        b = o.modifiers.new('bisel', 'BEVEL')
        b.width = bisel
        b.segments = 2
    o.data.materials.append(m)
    return poner(o)


def cil(nombre, p1, p2, r, m, v=24):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, vertices=v, location=(p1 + p2) / 2)
    o = bpy.context.object
    o.name = nombre
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return poner(o)


def tubo(nombre, puntos, r, m):
    pts = [Vector(p) for p in puntos]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    mu = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        n = max(6, int((p2 - p1).length / 0.005))
        for k in range(n):
            t = k / n
            mu.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                             (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    mu.append(pts[-1])
    cu = bpy.data.curves.new(nombre, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(len(mu) - 1)
    for p, q in zip(sp.points, mu):
        p.co = (q.x, q.y, max(q.z, 0.015 + r), 1)
    o = bpy.data.objects.new(nombre, cu)
    o.data.materials.append(m)
    col.objects.link(o)
    return o


def unir(objs, nombre):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = nombre
    return o


Z0, HB, HT, T = 0.01, 0.08, 0.07, 0.005     # piso de la caja, alto de base, alto de tapa, espesor de pared


def caja_dos_partes(nombre, cx, cy, dx, dy, m):
    """Base abierta arriba + tapa abierta abajo. Devuelve (base, tapa)."""
    b = [caja(f'{nombre} base piso', (cx, cy, Z0 + T / 2), (dx, dy, T), m),
         caja('p', (cx - dx / 2 + T / 2, cy, Z0 + HB / 2), (T, dy, HB), m),
         caja('p', (cx + dx / 2 - T / 2, cy, Z0 + HB / 2), (T, dy, HB), m),
         caja('p', (cx, cy - dy / 2 + T / 2, Z0 + HB / 2), (dx - 2 * T, T, HB), m),
         caja('p', (cx, cy + dy / 2 - T / 2, Z0 + HB / 2), (dx - 2 * T, T, HB), m)]
    for sy in (-1, 1):  # orejas de fijación al piso
        b.append(caja('oreja', (cx, cy + sy * (dy / 2 + 0.012), Z0 + 0.004), (dx * 0.7, 0.024, 0.008), m))
    base = unir(b, f'{nombre} - base (parte inferior)')
    z1 = Z0 + HB
    t = [caja(f'{nombre} tapa techo', (cx, cy, z1 + HT - T / 2), (dx, dy, T), m),
         caja('p', (cx - dx / 2 + T / 2, cy, z1 + HT / 2), (T, dy, HT), m),
         caja('p', (cx + dx / 2 - T / 2, cy, z1 + HT / 2), (T, dy, HT), m),
         caja('p', (cx, cy - dy / 2 + T / 2, z1 + HT / 2), (dx - 2 * T, T, HT), m),
         caja('p', (cx, cy + dy / 2 - T / 2, z1 + HT / 2), (dx - 2 * T, T, HT), m)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            t.append(cil('tornillo', (cx + sx * (dx / 2 - 0.015), cy + sy * (dy / 2 - 0.015), z1 + HT),
                         (cx + sx * (dx / 2 - 0.015), cy + sy * (dy / 2 - 0.015), z1 + HT + 0.003), 0.005, METAL, 12))
    tapa = unir(t, f'{nombre} - tapa (parte superior)')
    for o in (base, tapa):
        bv = o.modifiers.new('bisel', 'BEVEL')
        bv.width = 0.0015
        bv.segments = 2
    return base, tapa


ZP = 0.035
# ------------------------------------------------------------------ caja 1 (cerca del tinaco): BOMBA
b1, t1 = caja_dos_partes('Caja de la bomba', 0.0, -1.98, 0.30, 0.36, GRIS)
cy = -1.98
caja('Placa de montaje de la bomba', (0.0, cy, Z0 + T + 0.003), (0.17, 0.12, 0.006), METAL)
# Bomba GOOD PUMPS 12 V en línea con la tubería (como en la foto): el agua entra por un costado del cabezal y sale por el
# otro; el motor queda de lado (perpendicular al tubo) y al frente del cabezal está el bloque del presostato.
ZA = 0.058
XB = 0.05                                    # eje de la tubería dentro de la caja
NEG = mat('Plastico negro bomba', (0.025, 0.025, 0.028), 0.45)
ETB = mat('Etiqueta blanca GOOD PUMPS', (0.92, 0.92, 0.9), 0.5)
cil('Bomba - motor 12 V', (XB - 0.03, cy, ZA), (XB - 0.115, cy, ZA), 0.027, NEG, 40)
cil('Bomba - tapa trasera del motor', (XB - 0.115, cy, ZA), (XB - 0.122, cy, ZA), 0.022, NEG, 40)
et = cil('Bomba - etiqueta GOOD PUMPS', (XB - 0.04, cy, ZA), (XB - 0.105, cy, ZA), 0.0274, ETB, 48)
corte = caja('corte etiqueta', (XB - 0.072, cy, ZA - 0.022), (0.08, 0.07, 0.04), ETB)
bo = et.modifiers.new('mitad superior', 'BOOLEAN')
bo.operation = 'DIFFERENCE'
bo.object = corte
bpy.context.view_layer.objects.active = et
bpy.ops.object.modifier_apply(modifier=bo.name)
bpy.data.objects.remove(corte, do_unlink=True)
caja('Bomba - logo PUMPS', (XB - 0.06, cy, ZA + 0.0276), (0.016, 0.006, 0.0006), NEG)
for k in range(4):
    caja('Bomba - texto de la etiqueta', (XB - 0.075 - k * 0.008, cy, ZA + 0.0276), (0.004, 0.014, 0.0006), NEG)
caja('Bomba - brida motor-cabezal', (XB - 0.026, cy, ZA), (0.012, 0.058, 0.058), NEG, 0.006)
caja('Bomba - cabezal', (XB, cy, ZA - 0.002), (0.042, 0.066, 0.062), NEG, 0.012)
caja('Bomba - tapa superior del cabezal', (XB, cy, ZA + 0.031), (0.038, 0.05, 0.006), NEG, 0.004)
for sx, sy in ((-0.013, -0.019), (-0.013, 0.019), (0.013, -0.019), (0.013, 0.019)):
    cil('Bomba - tornillo superior', (XB + sx, cy + sy, ZA + 0.034), (XB + sx, cy + sy, ZA + 0.037), 0.0026, METAL, 12)
caja('Bomba - bloque del presostato', (XB + 0.033, cy, ZA - 0.004), (0.026, 0.044, 0.04), NEG, 0.004)
for sz in (0.012, -0.018):
    cil('Bomba - tornillo del presostato', (XB + 0.046, cy - 0.008, ZA + sz), (XB + 0.049, cy - 0.008, ZA + sz), 0.0026, METAL, 12)
cil('Bomba - orificio del presostato', (XB + 0.0455, cy + 0.009, ZA - 0.004), (XB + 0.0465, cy + 0.009, ZA - 0.004), 0.004,
    NEGRO_MATE, 16)
cil('Bomba - marca verde', (XB + 0.012, cy + 0.0335, ZA - 0.012), (XB + 0.012, cy + 0.0345, ZA - 0.012), 0.004,
    mat('Punto verde', (0.1, 0.6, 0.2), 0.4), 12)
# puertos a los costados, rosca de metal y tuerca unión verde (entrada hacia el tinaco, salida hacia el caudalímetro)
for sgn, nombre in ((-1, 'entrada'), (1, 'salida')):
    y0 = cy + sgn * 0.033
    cil(f'Bomba - puerto de {nombre}', (XB, y0, ZA), (XB, y0 + sgn * 0.016, ZA), 0.009, NEG, 20)
    cil(f'Bomba - rosca de metal {nombre}', (XB, y0 + sgn * 0.016, ZA), (XB, y0 + sgn * 0.038, ZA), 0.0095, METAL, 20)
    for k in range(4):
        cil('rosca', (XB, y0 + sgn * (0.018 + k * 0.005), ZA), (XB, y0 + sgn * (0.0205 + k * 0.005), ZA), 0.0105, METAL, 20)
    cil(f'Tuerca union verde {nombre}', (XB, y0 + sgn * 0.036, ZA), (XB, y0 + sgn * 0.066, ZA), 0.017, VERDE, 12)
    cil(f'Union verde {nombre}', (XB, y0 + sgn * 0.066, ZA), (XB, y0 + sgn * 0.08, ZA), 0.014, VERDE, 24)
# 4 orejas de hule bajo el motor y el cabezal
for sx in (XB - 0.005, XB - 0.105):
    for sy in (-1, 1):
        caja('Bomba - oreja de hule', (sx, cy + sy * 0.04, Z0 + T + 0.009), (0.02, 0.022, 0.006), NEG, 0.003)
        caja('Bomba - soporte de oreja', (sx, cy + sy * 0.026, Z0 + T + 0.02), (0.014, 0.012, 0.024), NEG, 0.002)
# tubería de entrada (del filtro) y de salida (al caudalímetro), sube del piso al eje de la bomba con codos
cil('Tubo de llegada (del filtro)', (XB, -2.24, ZP), (XB, -2.135, ZP), 0.0125, VERDE)
caja('Codo de entrada', (XB, -2.24, ZP), (0.032, 0.032, 0.032), VERDE, 0.006)
caja('Codo de subida a la bomba', (XB, -2.12, ZP + 0.006), (0.03, 0.03, 0.04), VERDE, 0.006)
cil('Tubo a la bomba', (XB, -2.12, ZA), (XB, cy - 0.113, ZA), 0.0125, VERDE)
caja('Codo de entrada a la bomba', (XB, -2.12, ZA), (0.03, 0.03, 0.03), VERDE, 0.006)
cil('Tubo de salida de la bomba', (XB, cy + 0.113, ZA), (XB, -1.85, ZA), 0.0125, VERDE)
caja('Codo de salida 1', (XB, -1.85, ZA), (0.03, 0.03, 0.03), VERDE, 0.006)
cil('Tubo de salida (bajada)', (XB, -1.85, ZA), (XB, -1.85, ZP), 0.0125, VERDE)
caja('Codo de salida 2', (XB, -1.85, ZP), (0.03, 0.03, 0.03), VERDE, 0.006)
cil('Tubo de salida (lateral)', (XB, -1.85, ZP), (0.0, -1.85, ZP), 0.0125, VERDE)
caja('Codo de salida 3', (0.0, -1.85, ZP), (0.03, 0.03, 0.03), VERDE, 0.006)
cil('Tubo de salida (a la pared)', (0.0, -1.85, ZP), (0.0, -1.805, ZP), 0.0125, VERDE)
CABLE_V = mat('Cable verde', (0.03, 0.45, 0.25), 0.4)
tubo('Bomba - cable rojo', [(XB + 0.04, cy + 0.02, ZA - 0.02), (XB + 0.02, cy + 0.06, 0.04), (-0.05, cy + 0.06, 0.05),
                            (-0.149, cy + 0.006, 0.08)], 0.0022, CABLE_R)
tubo('Bomba - cable verde', [(XB - 0.02, cy - 0.02, ZA + 0.03), (-0.02, cy - 0.05, ZA + 0.03), (-0.1, cy - 0.04, 0.075),
                             (-0.149, cy - 0.004, 0.078)], 0.0022, CABLE_V)

# ------------------------------------------------------------------ caja 2 (en medio): CAUDALÍMETRO YF-S201
b2, t2 = caja_dos_partes('Caja del caudalimetro', 0.0, -1.60, 0.18, 0.24, NEGRO)
cy = -1.60
ZC = 0.04                                         # eje de la tubería dentro de estas cajas
NEGP = mat('Plastico negro YF', (0.02, 0.02, 0.022), 0.5)
BLANCA = mat('Etiqueta blanca', (0.95, 0.95, 0.93), 0.5)
ARO = mat('Aro rojo etiqueta', (0.75, 0.05, 0.25), 0.5)
TEFLON = mat('Cinta teflon', (0.95, 0.95, 0.95), 0.6)
PLAT = mat('Soporte plateado', (0.78, 0.79, 0.8), 0.25, 1.0)


def union_verde(nombre, y0, y1):
    """Tuerca unión verde (dentada) + cuerpo de la unión, entre y0 y y1 sobre el eje de la tubería."""
    ym = y0 + (y1 - y0) * 0.55
    cil(f'{nombre} - tuerca', (0.0, y0, ZC), (0.0, ym, ZC), 0.0175, VERDE, 12)
    for k in range(12):
        a = k * math.pi / 6
        caja('estria', (0.018 * math.cos(a), (y0 + ym) / 2, ZC + 0.018 * math.sin(a)), (0.003, abs(ym - y0) * 0.9, 0.003), VERDE)
    cil(f'{nombre} - cuerpo', (0.0, ym, ZC), (0.0, y1, ZC), 0.0145, VERDE, 24)


def bajar(nombre, y_union, y_pared):
    """Del eje de la caja (ZC) a la altura de la tubería del piso (ZP) en la pared."""
    cil(nombre, (0.0, y_union, ZC), (0.0, y_pared, ZP + (ZC - ZP) * 0.0), 0.0125, VERDE)


# ------------------------------------------------------------------ caudalímetro YF-S201 (como en la foto)
cy = -1.60
cil('Tubo verde bomba-caudalimetro', (0.0, -1.80, ZP), (0.0, -1.72, ZC), 0.0125, VERDE)
union_verde('Union entrada caudalimetro', -1.72, -1.672)
union_verde('Union salida caudalimetro', -1.48, -1.528)
for s in (-1, 1):
    cil('YF-S201 - rosca', (0.0, cy + s * 0.072, ZC), (0.0, cy + s * 0.03, ZC), 0.0115, NEGP, 24)
    cil('YF-S201 - cinta teflon', (0.0, cy + s * 0.071, ZC), (0.0, cy + s * 0.064, ZC), 0.0122, TEFLON, 24)
cil('YF-S201 - cuerpo del tubo', (0.0, cy - 0.032, ZC), (0.0, cy + 0.032, ZC), 0.013, NEGP, 32)
cil('YF-S201 - carcasa redonda', (-0.013, cy, ZC), (0.011, cy, ZC), 0.023, NEGP, 48)
caja('YF-S201 - brida con 4 tornillos', (0.0135, cy, ZC), (0.006, 0.05, 0.05), NEGP, 0.012)
cil('YF-S201 - aro rojo', (0.0165, cy, ZC), (0.0172, cy, ZC), 0.0158, ARO, 48)
cil('YF-S201 - etiqueta Water Flow Sensor', (0.0168, cy, ZC), (0.0176, cy, ZC), 0.0150, BLANCA, 48)
for k in range(4):
    caja('YF-S201 - texto', (0.0177, cy, ZC + 0.007 - k * 0.0035), (0.0004, 0.016 - (k == 0) * 0.003, 0.0012), NEGP)
cil('YF-S201 - logo PASS QC', (0.0176, cy, ZC - 0.009), (0.0178, cy, ZC - 0.009), 0.0035, NEGP, 24)
for sy in (-0.019, 0.019):
    for sz in (-0.019, 0.019):
        cil('YF-S201 - tornillo', (0.0165, cy + sy, ZC + sz), (0.0195, cy + sy, ZC + sz), 0.0032, METAL, 16)
for k in range(6):   # rayos de la tapa trasera
    a = k * math.pi / 3
    caja('YF-S201 - rayo trasero', (-0.0135, cy + 0.011 * math.cos(a), ZC + 0.011 * math.sin(a)), (0.0015, 0.0025, 0.022), NEGP).rotation_euler = (a, 0, 0)
cil('YF-S201 - centro trasero', (-0.0145, cy, ZC), (-0.0135, cy, ZC), 0.004, NEGP, 24)
caja('YF-S201 - conector', (-0.004, cy + 0.012, ZC - 0.024), (0.01, 0.012, 0.01), NEGP, 0.002)
for i, (m, dy_) in enumerate(((CABLE_R, -0.003), (CABLE_N, 0.0), (CABLE_A, 0.003))):
    tubo(f'YF-S201 - cable {i + 1}', [(-0.004, cy + 0.012 + dy_, ZC - 0.029), (-0.03, cy + 0.03 + dy_, 0.03),
                                     (-0.065, cy + 0.01 + dy_, 0.05), (-0.087, cy + dy_, 0.072)], 0.0018, m)
cil('Tubo verde caudalimetro-valvula', (0.0, -1.48, ZC), (0.0, -1.41, ZC), 0.0125, VERDE)

# ------------------------------------------------------------------ caja 3 (cerca del cajón): ELECTROVÁLVULA KING SHENG NC 12 V
b3, t3 = caja_dos_partes('Caja de la electrovalvula', 0.0, -1.27, 0.20, 0.28, GRIS)
cy = -1.27
cil('Tubo verde a la valvula', (0.0, -1.41, ZC), (0.0, -1.385, ZC), 0.0125, VERDE)
union_verde('Union entrada valvula', -1.385, -1.333)
union_verde('Union salida valvula', -1.155, -1.207)
for s in (-1, 1):
    cil('Electrovalvula - rosca blanca 1/2"', (0.0, cy + s * 0.063, ZC), (0.0, cy + s * 0.028, ZC), 0.0125, BLANCO, 24)
    for k in range(4):
        cil('rosca', (0.0, cy + s * (0.03 + k * 0.006), ZC), (0.0, cy + s * (0.0325 + k * 0.006), ZC), 0.0138, BLANCO, 24)
cil('Electrovalvula - cuerpo blanco', (0.0, cy - 0.028, ZC), (0.0, cy + 0.028, ZC), 0.018, BLANCO, 32)
# bobina hacia arriba (perpendicular al tubo) con el soporte plateado y la etiqueta al frente, terminales hacia un lado
caja('Electrovalvula - base de la bobina', (0.0, cy, ZC + 0.02), (0.036, 0.044, 0.018), BLANCO, 0.005)
cil('Electrovalvula - bobina negra', (0.0, cy, ZC + 0.029), (0.0, cy, ZC + 0.066), 0.0165, NEGRO_MATE, 40)
caja('Electrovalvula - soporte metalico (abajo)', (0.0, cy, ZC + 0.029), (0.044, 0.05, 0.002), PLAT, 0.001)
caja('Electrovalvula - soporte metalico (arriba)', (0.0, cy, ZC + 0.067), (0.044, 0.046, 0.002), PLAT, 0.004)
for sx in (-1, 1):
    caja('Electrovalvula - soporte metalico (costado)', (sx * 0.021, cy, ZC + 0.048), (0.002, 0.04, 0.038), PLAT, 0.001)
for sy in (-1, 1):
    cil('Electrovalvula - tornillo del soporte', (sy * 0.016, cy - 0.023, ZC + 0.03), (sy * 0.016, cy - 0.023, ZC + 0.033), 0.0028,
        METAL, 12)
caja('Electrovalvula - etiqueta KING SHENG DC12V', (0.0, cy - 0.002, ZC + 0.0683), (0.034, 0.03, 0.0006), BLANCA)
for k in range(4):
    caja('Electrovalvula - texto', (0.0, cy + 0.009 - k * 0.0055, ZC + 0.0688), (0.026 - k * 0.004, 0.0015, 0.0004), NEGP)
caja('Electrovalvula - bloque de terminales', (0.0, cy + 0.027, ZC + 0.05), (0.03, 0.01, 0.028), NEGRO_MATE, 0.002)
for dx in (-0.008, 0.008):
    caja('Electrovalvula - terminal de pala', (dx, cy + 0.038, ZC + 0.056), (0.0065, 0.013, 0.0012), LATON)
tubo('Electrovalvula - cable rojo', [(-0.008, cy + 0.045, ZC + 0.056), (-0.02, cy + 0.06, ZC + 0.05), (-0.07, cy + 0.04, 0.085),
                                     (-0.097, cy - 0.01, 0.08)], 0.0022, CABLE_R)
tubo('Electrovalvula - cable negro', [(0.008, cy + 0.045, ZC + 0.056), (0.0, cy + 0.07, ZC + 0.045), (-0.07, cy + 0.06, 0.08),
                                      (-0.097, cy, 0.078)], 0.0022, CABLE_N)
cil('Tubo verde salida de la valvula', (0.0, -1.155, ZC), (0.0, -1.13, ZP), 0.0125, VERDE)
cil('Tubo verde al cajon', (0.0, -1.13, ZP), (0.0, -0.85, ZP), 0.0125, VERDE)


# ------------------------------------------------------------------ poliductos: uno entra a cada caja (cables) y otro sigue al cajón (EC-5)
NAR = M('Poliducto naranja')
GX, GZ, R = -0.95, 1.45, 0.011
inicio = lambda dx: [(GX + dx, -3.97, GZ - 0.16), (GX + dx, -3.97, 0.95), (-0.72 + dx, -3.93, 0.45), (-0.64 + dx, -3.6, 0.03),
                     (-0.6 + dx, -3.1, 0.03), (-0.34 + dx, -2.45, 0.03)]
tubo('Poliducto a la caja de la bomba', inicio(-0.04) + [(-0.3, -2.15, 0.03), (-0.21, -2.0, 0.05), (-0.165, -1.98, 0.075),
                                                          (-0.148, -1.98, 0.08)], R, NAR)
tubo('Poliducto a la caja del caudalimetro', inicio(0.0) + [(-0.3, -2.1, 0.03), (-0.24, -1.75, 0.03), (-0.14, -1.62, 0.06),
                                                             (-0.088, -1.6, 0.072)], R, NAR)
tubo('Poliducto a la caja de la electrovalvula', inicio(0.04) + [(-0.27, -2.1, 0.03), (-0.25, -1.6, 0.03), (-0.17, -1.32, 0.05),
                                                                  (-0.098, -1.27, 0.08)], R, NAR)
tubo('Poliducto al cajon (EC-5)', [(-0.05, -1.13, 0.075), (-0.06, -1.05, 0.04), (-0.07, -0.9, 0.03), (-0.06, -0.64, 0.06),
                                   (-0.05, -0.58, 0.3), (-0.06, -0.5, 0.52), (-0.15, -0.3, 0.5)], 0.009, NAR)
tubo('Cables EC-5 dentro de la caja', [(-0.097, -1.25, 0.075), (-0.07, -1.18, 0.07), (-0.05, -1.14, 0.075)], 0.003, CABLE_N)

# ------------------------------------------------------------------ animación de las tapas
tapas = [t1, t2, t3]
for i, t in enumerate(tapas):
    f0 = 20 + i * 25
    t.location = (0, 0, 0)
    t.rotation_euler = (0, 0, 0)
    t.keyframe_insert('location', frame=1)
    t.keyframe_insert('location', frame=f0)
    t.keyframe_insert('rotation_euler', frame=f0)
    t.location = (0, 0, 0.22)
    t.keyframe_insert('location', frame=f0 + 18)
    t.location = (0.42, 0, 0.22)
    t.rotation_euler = (0, 0, math.radians(8))
    t.keyframe_insert('location', frame=f0 + 36)
    t.keyframe_insert('rotation_euler', frame=f0 + 36)
    t.location = (0.42, 0, -0.08)
    t.keyframe_insert('location', frame=f0 + 52)
    for fc in t.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = 'BEZIER'
            k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'

# ------------------------------------------------------------------ cámara para ver las cajas abiertas
bpy.ops.object.camera_add(location=(0.62, -0.95, 0.62))
cam = bpy.context.object
cam.name = 'Camara cajas abiertas'
cam.data.lens = 30
cam.rotation_euler = (Vector((0.0, -1.68, 0.03)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam
sc.frame_set(140)
sc.render.image_settings.file_format = 'PNG'
sc.eevee.taa_render_samples = 64
for nombre, f, c in (('cajas_cerradas', 1, cam), ('cajas_abiertas', 140, cam)):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(REN, nombre + '.png')
    bpy.ops.render.render(write_still=True)
bpy.ops.object.camera_add(location=(0.32, -1.62, 0.36))
cam2 = bpy.context.object
cam2.name = 'Camara interior de cerca'
cam2.data.lens = 35
cam2.rotation_euler = (Vector((0.0, -1.75, 0.04)) - cam2.location).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam2
sc.frame_set(140)
sc.render.filepath = os.path.join(REN, 'cajas_interior_cerca.png')
bpy.ops.render.render(write_still=True)
bpy.ops.object.camera_add(location=(0.3, -1.84, 0.22))
cam3 = bpy.context.object
cam3.name = 'Camara bomba de cerca'
cam3.data.lens = 40
cam3.rotation_euler = (Vector((0.02, -1.98, 0.05)) - cam3.location).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam3
sc.frame_set(140)
sc.render.filepath = os.path.join(REN, 'bomba_de_cerca.png')
bpy.ops.render.render(write_still=True)
for nombre, pos, mira in (('Camara caudalimetro de cerca', (0.13, -1.47, 0.27), (0.0, -1.6, 0.035)),
                          ('Camara electrovalvula de cerca', (0.12, -1.16, 0.3), (0.0, -1.27, 0.06))):
    bpy.ops.object.camera_add(location=pos)
    cx = bpy.context.object
    cx.name = nombre
    cx.data.lens = 40
    cx.rotation_euler = (Vector(mira) - cx.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cx
    sc.frame_set(140)
    sc.render.filepath = os.path.join(REN, nombre.replace('Camara ', '').replace(' ', '_') + '.png')
    bpy.ops.render.render(write_still=True)
sc.camera = cam
sc.frame_set(140)
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
print('CAJAS_OK', NUEVO)
