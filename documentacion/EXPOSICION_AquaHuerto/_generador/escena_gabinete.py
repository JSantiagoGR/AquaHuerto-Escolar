"""Gabinete con la electrónica (como en la foto), tapa del tinaco con el sensor ultrasónico y video del recorrido:
gabinete abierto -> sensor del tinaco -> panel solar.

Abre AquaHuerto_cajas_abiertas.blend (sin modificarlo) y guarda AquaHuerto_gabinete_tinaco_panel.blend.
Ejecutar: blender -b -P escena_gabinete.py -- <carpeta_modelos_3D> [--solo-cuadros]
"""
import math
import os
import sys

import bpy
from mathutils import Vector, Matrix

args = sys.argv[sys.argv.index('--') + 1:]
DIR = args[0]
SOLO_CUADROS = '--solo-cuadros' in args
NUEVO = os.path.join(DIR, 'AquaHuerto_gabinete_tinaco_panel.blend')
REN = os.path.join(DIR, 'renders')
bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_cajas_abiertas.blend'))
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
sc = bpy.context.scene

# ------------------------------------------------------------------ cajas del piso cerradas en este video
for o in bpy.data.objects:
    if o.name.endswith('- tapa (parte superior)'):
        o.animation_data_clear()
        o.location, o.rotation_euler = (0, 0, 0), (0, 0, 0)
for n in ('Gabinete (ESP32, bateria, reles)', 'Tapa', 'Caja acrilica del sensor', 'Sensor PING', 'Cable del sensor de nivel'):
    if n in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)

col = bpy.data.collections.new('Gabinete y sensor del tinaco')
sc.collection.children.link(col)


def mat(nombre, color, rough=0.5, metal=0.0, alpha=1.0, emision=None):
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
        b.inputs['Transmission'].default_value = 0.6
        m.blend_method = 'BLEND'
        m.show_transparent_back = False
    if emision:
        b.inputs['Emission'].default_value = (*emision, 1)
        b.inputs['Emission Strength'].default_value = 3
    return m


GAB = mat('Gabinete gris claro', (0.78, 0.79, 0.78), 0.45)
NEG = mat('Negro mate', (0.02, 0.02, 0.02), 0.7)
MORADO = mat('PCB morada', (0.38, 0.06, 0.32), 0.5)
PCB_N = mat('PCB negra ESP32', (0.03, 0.03, 0.035), 0.4)
PCB_A = mat('PCB azul', (0.03, 0.15, 0.45), 0.45)
RELE = mat('Rele azul', (0.08, 0.3, 0.75), 0.35)
METAL = mat('Metal brillante', (0.75, 0.75, 0.78), 0.25, 1.0)
ORO = mat('Dorado', (0.8, 0.65, 0.3), 0.3, 1.0)
AMAR = mat('Header amarillo', (0.9, 0.75, 0.1), 0.4)
BLANCO = mat('Protoboard blanca', (0.93, 0.93, 0.9), 0.5)
NAR = mat('Wago naranja', (0.95, 0.45, 0.05), 0.4)
TRANSP = mat('Plastico transparente', (0.9, 0.95, 0.95), 0.05, 0.0, 0.35)
CTRL_A = mat('Frente azul del controlador', (0.08, 0.45, 0.85), 0.4)
LCD = mat('Pantalla LCD', (0.55, 0.62, 0.55), 0.2)
BAT = mat('Bateria negra', (0.03, 0.03, 0.03), 0.5)
ETIQ_B = mat('Etiqueta blanca bateria', (0.92, 0.92, 0.9), 0.5)
LED_R = mat('LED rojo', (1.0, 0.1, 0.05), 0.3, 0.0, 1.0, (1.0, 0.1, 0.05))
CAB = {'azul': mat('Cable azul', (0.05, 0.2, 0.75), 0.4), 'negro': mat('Cable negro', (0.01, 0.01, 0.01), 0.4),
       'rojo': mat('Cable rojo', (0.75, 0.03, 0.02), 0.4), 'blanco': mat('Cable blanco', (0.92, 0.92, 0.92), 0.4),
       'morado': mat('Cable morado', (0.4, 0.1, 0.6), 0.4), 'verde': mat('Cable verde', (0.03, 0.45, 0.25), 0.4),
       'amarillo': mat('Cable amarillo', (0.85, 0.7, 0.05), 0.4), 'naranja': mat('Cable naranja', (0.95, 0.4, 0.05), 0.4)}


def poner(o, c=None):
    for cc in o.users_collection:
        cc.objects.unlink(o)
    (c or col).objects.link(o)
    return o


def caja(nombre, c, d, m, bisel=0.0, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c)
    o = bpy.context.object
    o.name = nombre
    o.scale = d
    bpy.ops.object.transform_apply(scale=True)
    if rot:
        o.rotation_euler = rot
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


def tubo(nombre, puntos, r, m, zmin=0.0):
    pts = [Vector(p) for p in puntos]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    mu = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        n = max(6, int((p2 - p1).length / 0.004))
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
        p.co = (q.x, q.y, max(q.z, zmin), 1)
    o = bpy.data.objects.new(nombre, cu)
    o.data.materials.append(m)
    col.objects.link(o)
    return o


# ================================================================== GABINETE (en la pared, a la derecha del tinaco)
GX, GZ, YB = -0.95, 1.45, -3.99          # centro (x, z) y cara de la pared
W, H, D, DT = 0.40, 0.40, 0.15, 0.03     # ancho, alto, fondo de la base, fondo de la tapa
E = 0.006


def P(u, v, w):
    """Coordenadas locales del gabinete: u (izq->der), v (abajo->arriba), w (desde el fondo hacia afuera)."""
    return (GX - u, YB + w, GZ + v)      # visto de frente (+Y), u crece hacia la derecha


def bloque(nombre, u, v, w, du, dv, dw, m, bisel=0.0):
    return caja(nombre, P(u, v, w), (du, dw, dv), m, bisel)


partes = [bloque('Gabinete - fondo', 0, 0, E / 2, W, H, E, GAB),
          bloque('p', -W / 2 + E / 2, 0, D / 2, E, H, D, GAB), bloque('p', W / 2 - E / 2, 0, D / 2, E, H, D, GAB),
          bloque('p', 0, -H / 2 + E / 2, D / 2, W - 2 * E, E, D, GAB), bloque('p', 0, H / 2 - E / 2, D / 2, W - 2 * E, E, D, GAB)]
for su in (-1, 1):
    for sv in (-1, 1):
        partes.append(cil('torreta de tornillo', P(su * (W / 2 - 0.02), sv * (H / 2 - 0.02), E),
                          P(su * (W / 2 - 0.02), sv * (H / 2 - 0.02), D), 0.011, GAB, 20))
for su, sv in ((-0.13, 0.16), (0.0, 0.15), (0.13, -0.17), (-0.13, -0.17), (0.17, 0.0), (-0.17, 0.0)):
    partes.append(cil('poste interior', P(su, sv, E), P(su, sv, 0.03), 0.008, GAB, 16))
bpy.ops.object.select_all(action='DESELECT')
for o in partes:
    o.select_set(True)
bpy.context.view_layer.objects.active = partes[0]
bpy.ops.object.join()
base_gab = bpy.context.object
base_gab.name = 'Gabinete - base (pegada a la pared)'
for su in (-1, 1):
    for sv in (-1, 1):
        cil('tornillo de la tapa (inserto)', P(su * (W / 2 - 0.02), sv * (H / 2 - 0.02), D - 0.002),
            P(su * (W / 2 - 0.02), sv * (H / 2 - 0.02), D + 0.001), 0.004, METAL, 12)

# tapa del gabinete (se quita en el video)
tp = [bloque('Gabinete - tapa frente', 0, 0, D + DT - E / 2, W, H, E, GAB),
      bloque('p', -W / 2 + E / 2, 0, D + DT / 2, E, H, DT, GAB), bloque('p', W / 2 - E / 2, 0, D + DT / 2, E, H, DT, GAB),
      bloque('p', 0, -H / 2 + E / 2, D + DT / 2, W - 2 * E, E, DT, GAB), bloque('p', 0, H / 2 - E / 2, D + DT / 2, W - 2 * E, E, DT, GAB)]
for su in (-1, 1):
    for sv in (-1, 1):
        tp.append(cil('tornillo de la tapa', P(su * (W / 2 - 0.02), sv * (H / 2 - 0.02), D + DT),
                      P(su * (W / 2 - 0.02), sv * (H / 2 - 0.02), D + DT + 0.004), 0.006, METAL, 16))
bpy.ops.object.select_all(action='DESELECT')
for o in tp:
    o.select_set(True)
bpy.context.view_layer.objects.active = tp[0]
bpy.ops.object.join()
tapa_gab = bpy.context.object
tapa_gab.name = 'Gabinete - tapa'

# ---- controlador de carga PWM (abajo a la izquierda)
cu_, cv_ = -0.087, -0.093
bloque('Controlador - cuerpo negro', cu_, cv_, 0.022, 0.15, 0.09, 0.032, NEG, 0.004)
bloque('Controlador - frente azul', cu_ + 0.004, cv_ - 0.012, 0.0385, 0.12, 0.05, 0.002, CTRL_A, 0.002)
bloque('Controlador - pantalla LCD', cu_ + 0.002, cv_ - 0.015, 0.0398, 0.042, 0.028, 0.001, LCD)
for k, du in enumerate((-0.02, 0.0, 0.02)):
    cil('Controlador - boton', P(cu_ + du, cv_ + 0.019, 0.038), P(cu_ + du, cv_ + 0.019, 0.041), 0.0045, NEG, 16)
for dv in (-0.006, -0.02):
    bloque('Controlador - USB', cu_ - 0.048, cv_ + dv, 0.039, 0.014, 0.009, 0.004, METAL)
for k in range(6):
    cil('Controlador - borne', P(cu_ - 0.052 + k * 0.021, cv_ + 0.036, 0.038), P(cu_ - 0.052 + k * 0.021, cv_ + 0.036, 0.041),
        0.004, METAL, 12)
for sx in (-1, 1):
    bloque('Controlador - oreja', cu_ + sx * 0.08, cv_, 0.008, 0.014, 0.07, 0.004, NEG)

# ---- batería SLA 12 V 9 Ah (arriba a la derecha)
bu, bv = 0.085, 0.06
bloque('Bateria 12 V 9 Ah', bu, bv, 0.006 + 0.0325, 0.094, 0.151, 0.065, BAT, 0.003)
bloque('Bateria - etiqueta PRECAUTIONS', bu + 0.024, bv, 0.072, 0.04, 0.14, 0.0006, ETIQ_B)
for k in range(8):
    bloque('Bateria - texto', bu - 0.018, bv + 0.05 - k * 0.012, 0.0718, 0.036 - (k % 3) * 0.006, 0.0025, 0.0004, ETIQ_B)
for du in (-0.03, -0.012):
    bloque('Bateria - terminal F2', bu + du, bv - 0.077, 0.03, 0.008, 0.01, 0.0015, METAL)

# ---- placa de expansión morada con ESP32 (arriba a la izquierda)
eu, ev = -0.078, 0.104
bloque('Placa de expansion (morada)', eu, ev, 0.031, 0.083, 0.053, 0.0018, MORADO)
for k in range(2):
    bloque('Headers amarillos', eu, ev + (0.022 if k else -0.022), 0.034, 0.075, 0.004, 0.004, AMAR)
bloque('ESP32 DevKit (PCB negra)', eu - 0.01, ev + 0.003, 0.038, 0.055, 0.028, 0.0016, PCB_N)
bloque('ESP32 - modulo WROOM', eu - 0.028, ev + 0.003, 0.0405, 0.018, 0.016, 0.003, METAL, 0.001)
bloque('ESP32 - antena', eu - 0.034, ev + 0.003, 0.039, 0.006, 0.016, 0.0008, AMAR)
bloque('ESP32 - micro USB', eu + 0.017, ev + 0.003, 0.0405, 0.006, 0.008, 0.003, METAL)
cil('LED rojo encendido', P(eu + 0.012, ev - 0.012, 0.039), P(eu + 0.012, ev - 0.012, 0.041), 0.0015, LED_R, 10)
cil('LED rojo placa', P(eu + 0.03, ev - 0.02, 0.033), P(eu + 0.03, ev - 0.02, 0.035), 0.0015, LED_R, 10)
bloque('Jack DC de la placa', eu + 0.035, ev - 0.01, 0.036, 0.01, 0.012, 0.009, NEG)

# ---- mini protoboard (izquierda, en medio)
pu, pv = -0.123, 0.042
bloque('Mini protoboard', pu, pv, 0.012, 0.035, 0.047, 0.008, BLANCO, 0.001)
for k in range(10):
    bloque('orificios', pu, pv + 0.02 - k * 0.0045, 0.0161, 0.028, 0.0008, 0.0002, mat('Gris orificios', (0.5, 0.5, 0.5)))
for k, (c1, c2) in enumerate((('negro', 'rojo'), ('blanco', 'morado'))):
    cil('Resistencia', P(pu - 0.005 + k * 0.01, pv - 0.01, 0.019), P(pu - 0.005 + k * 0.01, pv + 0.006, 0.019), 0.0015,
        mat('Resistencia azul', (0.3, 0.5, 0.75)), 10)

# ---- módulo de 2 relevadores (centro)
ru, rv = -0.063, 0.038
bloque('Modulo 2 reles (PCB azul)', ru, rv, 0.031, 0.041, 0.05, 0.0016, PCB_A)
for du in (-0.009, 0.009):
    bloque('Rele SRD-05VDC', ru + du, rv - 0.002, 0.04, 0.015, 0.019, 0.016, RELE, 0.001)
bloque('Borneras de los reles', ru, rv - 0.024, 0.036, 0.04, 0.007, 0.009, mat('Bornera azul', (0.1, 0.3, 0.8)))
bloque('Pines de entrada', ru, rv + 0.024, 0.035, 0.016, 0.004, 0.006, NEG)
cil('LED rele', P(ru + 0.015, rv + 0.02, 0.033), P(ru + 0.015, rv + 0.02, 0.035), 0.0015, LED_R, 10)

# ---- conectores WAGO (debajo de los relés)
for k in range(3):
    bloque('Conector WAGO 221 (cuerpo)', -0.07 + k * 0.007, -0.02, 0.012, 0.006, 0.018, 0.012, TRANSP)
    bloque('Conector WAGO 221 (palanca)', -0.07 + k * 0.007, -0.016, 0.019, 0.006, 0.01, 0.003, NAR)

# ---- cables (como en la foto)
Wc = 0.034
def ruta(pts):
    return [P(u, v, w) for u, v, w in pts]

for k, du in enumerate((-0.004, 0.0, 0.004, 0.008)):   # haz azul del ESP32 hacia los relés / WAGO / poliducto
    tubo(f'Cable azul {k + 1}', ruta([(eu + 0.03, ev - 0.02, 0.036), (-0.02 + du, 0.07, Wc), (-0.02 + du, 0.02, Wc),
                                      (-0.035 + du, -0.03, Wc), (-0.06 + du, -0.025, 0.02)]), 0.0016, CAB['azul'])
for k, du in enumerate((-0.006, 0.006)):               # salidas de los relés a los WAGO
    tubo(f'Cable rele-wago {k + 1}', ruta([(ru + du, rv - 0.028, 0.036), (ru + du * 2, rv - 0.045, 0.03),
                                          (-0.07 + k * 0.007, -0.012, 0.02)]), 0.0016, CAB['azul'])
for k, du in enumerate((-0.11, -0.095)):               # del controlador (carga) a los WAGO
    tubo(f'Cable carga {k + 1}', ruta([(du, cv_ + 0.042, 0.036), (du + 0.01, -0.02, 0.03), (-0.1 + k * 0.01, 0.0, 0.03),
                                      (-0.07 + k * 0.007, -0.025, 0.02)]), 0.0017, CAB['azul'])
tubo('Bateria + (rojo)', ruta([(-0.073, cv_ + 0.042, 0.036), (-0.04, -0.03, 0.032), (0.01, -0.0, 0.03), (0.03, -0.015, 0.03),
                               (bu - 0.03, bv - 0.08, 0.03)]), 0.002, CAB['negro'])
tubo('Bateria - (negro)', ruta([(-0.06, cv_ + 0.042, 0.036), (-0.02, -0.04, 0.03), (0.02, -0.02, 0.028),
                                (bu - 0.012, bv - 0.08, 0.03)]), 0.002, CAB['negro'])
cil('Terminal ojo rojo', P(bu - 0.03, bv - 0.083, 0.03), P(bu - 0.03, bv - 0.093, 0.03), 0.0025, CAB['rojo'], 12)
cil('Terminal ojo azul', P(bu - 0.012, bv - 0.083, 0.03), P(bu - 0.012, bv - 0.093, 0.03), 0.0025, CAB['azul'], 12)
tubo('Cable USB blanco (ESP32 a la salida)', ruta([(eu + 0.02, ev + 0.003, 0.042), (0.0, 0.11, 0.045), (0.06, 0.15, 0.05),
                                                  (0.15, 0.13, 0.06), (0.192, 0.08, 0.06)]), 0.0025, CAB['blanco'])
for k, nombre in enumerate(('verde', 'amarillo', 'naranja', 'morado')):   # cables de colores de los sensores (arriba)
    tubo(f'Cable de sensores {nombre}', ruta([(eu - 0.02 + k * 0.004, ev + 0.026, 0.036), (-0.06 + k * 0.004, 0.16, 0.05),
                                              (-0.01 + k * 0.004, 0.185, 0.045), (0.01 + k * 0.004, 0.199, 0.04)]),
         0.0013, CAB[nombre])
for k, (c1, du) in enumerate((('blanco', -0.15), ('morado', -0.145), ('negro', -0.14))):  # a la protoboard
    tubo(f'Cable protoboard {k + 1}', ruta([(eu - 0.03, ev - 0.026, 0.035), (du, 0.075, 0.035), (pu + (k - 1) * 0.008, pv + 0.022, 0.02)]),
         0.0013, CAB[c1])
for k, c1 in enumerate(('rojo', 'negro', 'blanco')):      # bajan al poliducto (fondo del gabinete)
    tubo(f'Cable a poliducto {k + 1}', ruta([(pu + 0.005, pv - 0.022, 0.02), (-0.15 + k * 0.004, -0.05, 0.03),
                                             (-0.16 + k * 0.004, -0.15, 0.03), (-0.04 + k * 0.004, -0.199, 0.03)]), 0.0014, CAB[c1])

# ================================================================== TAPA DEL TINACO CON EL SENSOR ULTRASÓNICO DEBAJO
TY = -3.75
ZT = 1.258
piv = bpy.data.objects.new('Tapa del tinaco (pivote)', None)
col.objects.link(piv)
piv.location = (0.0, TY, ZT)
lid = []
lid.append(cil('Tapa del tinaco', (0, TY, ZT), (0, TY, ZT + 0.03), 0.23, bpy.data.materials['Plastico negro'], 64))
for dx in (-0.12, 0.12):
    lid.append(caja('Ventila de la tapa', (dx, TY, ZT + 0.031), (0.03, 0.12, 0.004), NEG))
    for k in range(3):
        lid.append(caja('rejilla', (dx, TY - 0.04 + k * 0.04, ZT + 0.0335), (0.03, 0.004, 0.002), bpy.data.materials['Plastico negro']))
# caja de acrílico (con orejas y tornillos) y PING))) mirando hacia el agua, por debajo de la tapa
lid.append(caja('Caja acrilica del sensor', (0, TY, ZT - 0.026), (0.09, 0.08, 0.05), TRANSP, 0.002))
for sy in (-1, 1):
    for sx in (-1, 1):
        lid.append(caja('Oreja de acrilico', (sx * 0.03, TY + sy * 0.052, ZT - 0.002), (0.016, 0.026, 0.003), TRANSP))
        lid.append(cil('Tornillo de la oreja', (sx * 0.03, TY + sy * 0.058, ZT - 0.0005), (sx * 0.03, TY + sy * 0.058, ZT - 0.006),
                       0.0035, METAL, 12))
lid.append(caja('PING))) - tarjeta azul', (0, TY, ZT - 0.04), (0.045, 0.02, 0.0016), PCB_A))
for dx in (-0.0125, 0.0125):
    lid.append(cil('PING))) - transductor', (dx, TY, ZT - 0.041), (dx, TY, ZT - 0.054), 0.008, METAL, 24))
    lid.append(cil('PING))) - malla', (dx, TY, ZT - 0.0545), (dx, TY, ZT - 0.0548), 0.0068, mat('Malla dorada', (0.45, 0.4, 0.25), 0.6), 24))
for k in range(3):
    lid.append(cil('PING))) - pin', (-0.003 + k * 0.003, TY - 0.012, ZT - 0.04), (-0.003 + k * 0.003, TY - 0.02, ZT - 0.04), 0.0006, ORO, 8))
for k, c1 in enumerate(('blanco', 'morado', 'azul')):
    lid.append(tubo(f'PING))) - cable {c1}', [(-0.003 + k * 0.003, TY - 0.02, ZT - 0.04), (-0.003 + k * 0.003, TY - 0.034, ZT - 0.03),
                                             (-0.04, TY - 0.05, ZT - 0.012), (-0.18, TY - 0.03, ZT - 0.004)], 0.0012, CAB[c1]))
for o in lid:
    mw = o.matrix_world.copy()
    o.parent = piv
    o.matrix_parent_inverse = piv.matrix_world.inverted()
    o.matrix_world = mw
# cable del sensor: sale por el borde de la tapa y llega al gabinete
tubo('Cable del sensor de nivel', [(-0.2, TY + 0.02, ZT + 0.005), (-0.32, TY + 0.06, 1.3), (-0.55, -3.93, 1.42),
                                   (GX + 0.17, -3.96, GZ + 0.05)], 0.006, bpy.data.materials['Poliducto naranja'])

# luz suave para ver dentro del gabinete y la tapa del tinaco
bpy.ops.object.light_add(type='AREA', location=(-0.95, -3.25, 1.95))
la = bpy.context.object
la.name = 'Luz del gabinete'
la.data.energy = 14
la.data.size = 0.8
la.rotation_euler = (Vector((-0.95, -3.97, 1.45)) - la.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.light_add(type='AREA', location=(0.4, -3.0, 2.4))
lb = bpy.context.object
lb.name = 'Luz de la tapa del tinaco'
lb.data.energy = 10
lb.data.size = 0.6
lb.rotation_euler = (Vector((0.1, -3.5, 1.65)) - lb.location).to_track_quat('-Z', 'Y').to_euler()

# ================================================================== ANIMACIÓN
def suave(o):
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for k in fc.keyframe_points:
                k.interpolation = 'BEZIER'
                k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'


# tapa del gabinete: se aflojan los tornillos, sale hacia afuera y se aparta
tapa_gab.keyframe_insert('location', frame=1)
tapa_gab.keyframe_insert('location', frame=80)
tapa_gab.keyframe_insert('rotation_euler', frame=80)
tapa_gab.location = (0, 0.14, 0)
tapa_gab.keyframe_insert('location', frame=100)
tapa_gab.location = (-0.55, 0.3, -0.05)
tapa_gab.rotation_euler = (0, 0, math.radians(-25))
tapa_gab.keyframe_insert('location', frame=128)
tapa_gab.keyframe_insert('rotation_euler', frame=128)
suave(tapa_gab)
# tapa del tinaco: sube y se voltea para enseñar el sensor
piv.keyframe_insert('location', frame=1)
piv.keyframe_insert('location', frame=250)
piv.keyframe_insert('rotation_euler', frame=250)
piv.location = (0.0, TY, ZT + 0.32)
piv.keyframe_insert('location', frame=272)
piv.location = (0.12, TY + 0.25, ZT + 0.42)
piv.rotation_euler = (math.radians(150), 0, 0)
piv.keyframe_insert('location', frame=298)
piv.keyframe_insert('rotation_euler', frame=298)
suave(piv)

# cámara
obj = bpy.data.objects.new('Objetivo video gabinete', None)
sc.collection.objects.link(obj)
bpy.ops.object.camera_add(location=(4.0, 1.5, 2.8))
cam = bpy.context.object
cam.name = 'Camara video gabinete-tinaco-panel'
tr = cam.constraints.new('TRACK_TO')
tr.target = obj
tr.track_axis = 'TRACK_NEGATIVE_Z'
tr.up_axis = 'UP_Y'
ruta_c = [
    (1, (4.2, 1.6, 2.9), (-0.5, -3.6, 1.2), 24),
    (70, (-0.6, -2.6, 1.6), (-0.95, -3.95, 1.45), 30),          # frente al gabinete cerrado
    (130, (-0.78, -3.25, 1.52), (-0.95, -3.97, 1.46), 32),       # tapa quitada
    (165, (-1.02, -3.4, 1.58), (-1.02, -3.97, 1.53), 40),        # ESP32 y relés
    (200, (-0.9, -3.42, 1.38), (-0.9, -3.97, 1.4), 40),          # controlador
    (225, (-0.72, -3.4, 1.5), (-0.86, -3.97, 1.5), 40),          # batería
    (255, (0.75, -2.95, 1.9), (0.0, -3.75, 1.35), 30),           # al tinaco
    (300, (0.5, -3.0, 2.0), (0.12, -3.45, 1.68), 38),            # sensor ultrasónico
    (345, (0.38, -3.12, 1.95), (0.12, -3.45, 1.68), 48),
    (400, (1.2, -3.4, 3.4), (-0.45, -4.6, 2.9), 30),             # sube al panel solar
    (470, (0.75, -4.0, 3.25), (-0.45, -4.6, 2.92), 32),
    (520, (0.9, -5.2, 3.4), (-0.45, -4.6, 2.92), 32),
]
for f, pc, po, lente in ruta_c:
    cam.location, obj.location = pc, po
    cam.data.lens = lente
    cam.keyframe_insert('location', frame=f)
    obj.keyframe_insert('location', frame=f)
    cam.data.keyframe_insert('lens', frame=f)
suave(cam)
suave(obj)
if cam.data.animation_data:
    for fc in cam.data.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = 'BEZIER'
sc.camera = cam
sc.frame_start, sc.frame_end = 1, 520
sc.render.fps = 30
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

# cuadros de revisión
sc.eevee.taa_render_samples = 48
sc.render.image_settings.file_format = 'PNG'
for f in (60, 165, 200, 320, 470):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(REN, 'gabinete_video_cuadro_%03d.png' % f)
    bpy.ops.render.render(write_still=True)
sc.frame_set(1)
if not SOLO_CUADROS:
    sc.eevee.taa_render_samples = 24
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'NONE'
    sc.render.ffmpeg.video_bitrate = 7000
    sc.render.ffmpeg.maxrate = 9000
    sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
    sc.render.filepath = os.path.join(DIR, 'video', 'AquaHuerto_gabinete_tinaco_panel_')
    bpy.ops.render.render(animation=True)
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
print('GABINETE_OK', NUEVO)
