"""Componentes eléctricos realistas en el gabinete y en el tinaco:
- ESP32 DevKit + placa de expansión morada armados con modelos 3D OFICIALES de KiCad (módulo ESP32-WROOM-32, tiras de pines,
  zócalos, micro USB, regulador SOT-223, CP2102 QFN-28, botones, LEDs, jack DC), convertidos de STEP a .glb con step_a_gltf.py.
- Batería 12 V 9 Ah, controlador de carga PWM y tarjeta del PING))) con texturas sacadas de las fotos reales (texturas_fotos.py).
- Módulo de 2 relés real de Soldered (ya venía de escena_gabinete_real.py).

Abre AquaHuerto_gabinete_real.blend (sin modificarlo) y guarda AquaHuerto_componentes_reales.blend.
Ejecutar: blender -b -P escena_componentes_reales.py -- <carpeta_modelos_3D> [--video]
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
DIR = args[0]
VIDEO = '--video' in args
NUEVO = os.path.join(DIR, 'AquaHuerto_componentes_reales.blend')
REN = os.path.join(DIR, 'renders')
KI = os.path.join(DIR, 'descargas', 'kicad_oficial')
TEX = os.path.join(DIR, 'texturas')
bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_gabinete_real.blend'))
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
sc = bpy.context.scene
sc.frame_set(1)
col = bpy.data.collections['Gabinete y sensor del tinaco']
# acrílico: en EEVEE la "transmisión" tapaba lo que hay dentro (se veía el cielo borroso); se deja transparente simple
if 'Plastico transparente' in bpy.data.materials:
    _b = bpy.data.materials['Plastico transparente'].node_tree.nodes['Principled BSDF']
    _b.inputs['Transmission'].default_value = 0.0
    _b.inputs['Alpha'].default_value = 0.22

GX, GZ, YB = -0.95, 1.45, -3.99


def P(u, v, w):
    return Vector((GX - u, YB + w, GZ + v))


def borrar(*prefijos):
    for o in list(bpy.data.objects):
        if any(o.name == p or o.name.startswith(p + '.') for p in prefijos):
            bpy.data.objects.remove(o, do_unlink=True)


def mat(nombre, color, rough=0.5, metal=0.0, emision=None):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emision:
        b.inputs['Emission'].default_value = (*emision, 1)
        b.inputs['Emission Strength'].default_value = 3.0
    return m


def mat_foto(nombre, archivo, rough=0.45):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    im = nt.nodes.new('ShaderNodeTexImage')
    im.image = bpy.data.images.load(os.path.join(TEX, archivo))
    im.image.pack()
    nt.links.new(im.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    return m


def caja(nombre, u, v, w, du, dv, dw, m, bisel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=P(u, v, w))
    o = bpy.context.object
    o.name = nombre
    o.scale = (du, dw, dv)
    bpy.ops.object.transform_apply(scale=True)
    if bisel:
        md = o.modifiers.new('bisel', 'BEVEL')
        md.width, md.segments = bisel, 2
    o.data.materials.append(m)
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    return o


def cil_w(nombre, u, v, w0, w1, r, m, n=24):
    """Cilindro perpendicular a la pared (eje en w)."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=abs(w1 - w0), location=P(u, v, (w0 + w1) / 2),
                                        rotation=(math.radians(90), 0, 0))
    o = bpy.context.object
    o.name = nombre
    o.data.materials.append(m)
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    return o


def foto_frente(nombre, u, v, w, ancho, alto, m):
    """Plano con textura de foto, mirando hacia afuera del gabinete (+Y), con la imagen derecha (arriba = arriba)."""
    bpy.ops.mesh.primitive_plane_add(size=1, location=P(u, v, w), rotation=(math.radians(90), 0, math.radians(180)))
    o = bpy.context.object
    o.name = nombre
    o.scale = (ancho, alto, 1)
    o.data.materials.append(m)
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    return o


GIRO_BASE = Matrix.Rotation(math.pi, 4, 'Z')     # KiCad X -> u (derecha), KiCad Y -> v (arriba), KiCad Z -> hacia afuera


def pieza(archivo, nombre, u, v, w, giro=0.0, colores=None):
    """Importa una pieza de KiCad (.glb) y la pone con su origen (superficie de la placa) en w, centrada en (u, v)."""
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(KI, archivo))
    nuevos = [o for o in bpy.data.objects if o not in antes]
    raiz = [o for o in nuevos if o.parent is None][0]
    raiz.name = nombre
    for o in nuevos:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
        o.select_set(False)
    raiz.matrix_world = Matrix.Translation(P(0, 0, w)) @ GIRO_BASE @ Matrix.Rotation(math.radians(giro), 4, 'Y')
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in nuevos if o.type == 'MESH' for c in o.bound_box]
    cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2
    cz = (min(p.z for p in pts) + max(p.z for p in pts)) / 2
    objetivo = P(u, v, w)
    raiz.location = raiz.location + Vector((objetivo.x - cx, 0, objetivo.z - cz))
    if colores:
        for o in nuevos:
            if o.type != 'MESH':
                continue
            for i, m in enumerate(o.data.materials):
                if not (m and m.use_nodes and 'Principled BSDF' in m.node_tree.nodes):
                    continue
                c = m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value
                es_plastico = max(c[0], c[1], c[2]) < 0.3
                if es_plastico and 'plastico' in colores:
                    o.data.materials[i] = colores['plastico']
    return raiz


NEGRO_PCB = mat('PCB negra ESP32 real', (0.012, 0.012, 0.015), 0.7)
NEGRO_PCB.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.2
MAGENTA = mat('PCB placa de expansion magenta', (0.33, 0.015, 0.17), 0.45)
SERIG = mat('Serigrafia blanca', (0.85, 0.85, 0.85), 0.5)
AMARILLO = mat('Plastico amarillo pines', (0.85, 0.65, 0.05), 0.4)
ROJO = mat('Plastico rojo pines', (0.65, 0.04, 0.03), 0.4)
NEGRO = mat('Plastico negro pines', (0.02, 0.02, 0.02), 0.45)
LED_ROJO = mat('LED rojo encendido real', (1.0, 0.1, 0.05), 0.3, 0.0, (1.0, 0.08, 0.03))
METAL = mat('Metal tornillo real', (0.75, 0.75, 0.78), 0.3, 1.0)
GOMA = mat('Boton negro controlador', (0.03, 0.03, 0.03), 0.6)

# ================================================================== ESP32 DevKit + placa de expansión (arriba a la izquierda)
borrar('Placa de expansion (morada)', 'Headers amarillos', 'ESP32 DevKit (PCB negra)', 'ESP32 - modulo WROOM', 'ESP32 - antena',
       'ESP32 - micro USB', 'LED rojo encendido', 'LED rojo placa', 'Jack DC de la placa')
eu, ev = -0.078, 0.104
W_EXP = 0.0318                       # superficie de la placa de expansión
caja('Placa de expansion ESP32 (magenta)', eu, ev, 0.031, 0.083, 0.055, 0.0016, MAGENTA, 0.0008)
du_, dv_ = eu - 0.006, ev + 0.002    # centro del DevKit
for s in (-1, 1):
    pieza('PinSocket_1x15_P2.54mm_Vertical.glb', 'Zocalo hembra 1x15 (DevKit)', du_, dv_ + s * 0.0127, W_EXP, 90)
    for k, (dv, c) in enumerate(((0.0185, NEGRO), (0.021, ROJO), (0.0235, AMARILLO))):    # filas G / V / S
        pieza('PinHeader_1x15_P2.54mm_Vertical.glb', 'Tira de pines G-V-S', du_, dv_ + s * dv + (0.0 if s > 0 else 0.0), W_EXP,
              90, {'plastico': c})
W_DK = W_EXP + 0.0085                # el DevKit va montado sobre los zócalos
caja('ESP32 DevKit - PCB negra', du_, dv_, W_DK + 0.0008, 0.052, 0.0285, 0.0016, NEGRO_PCB, 0.0005)
WS = W_DK + 0.0016
pieza('ESP32-WROOM-32.glb', 'ESP32-WROOM-32 (modulo real)', du_ - 0.0165, dv_ + 0.0005, WS, 90)
pieza('USB_Micro-B_Molex_47346-0001.glb', 'DevKit - micro USB', du_ + 0.0235, dv_, WS, 90)
pieza('QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm.glb', 'DevKit - CP2102 (USB-serial)', du_ + 0.009, dv_ - 0.003, WS)
pieza('SOT-223.glb', 'DevKit - regulador AMS1117', du_ + 0.002, dv_ + 0.007, WS)
for s in (-1, 1):
    pieza('SW_SPST_TL3342.glb', 'DevKit - boton EN/BOOT', du_ + 0.017, dv_ + s * 0.0095, WS)
pieza('LED_0805_2012Metric.glb', 'DevKit - LED rojo', du_ + 0.003, dv_ - 0.009, WS)
cil_w('DevKit - luz del LED', du_ + 0.003, dv_ - 0.009, WS, WS + 0.0009, 0.0007, LED_ROJO, 10)
# accesorios de la placa de expansión (lado derecho, como en la foto)
pieza('BarrelJack_Horizontal.glb', 'Placa de expansion - jack DC 6.5-16 V', eu + 0.031, ev + 0.012, W_EXP, 0)
pieza('SOT-223.glb', 'Placa de expansion - regulador', eu + 0.033, ev - 0.006, W_EXP)
pieza('PinHeader_1x03_P2.54mm_Vertical.glb', 'Placa de expansion - selector 5V/3V3', eu + 0.024, ev - 0.02, W_EXP, 0)
pieza('LED_0805_2012Metric.glb', 'Placa de expansion - LED PWR', eu + 0.036, ev - 0.022, W_EXP)
cil_w('Placa de expansion - luz PWR', eu + 0.036, ev - 0.022, W_EXP, W_EXP + 0.0009, 0.0007, LED_ROJO, 10)
for su in (-1, 1):
    for sv in (-1, 1):
        cil_w('Placa de expansion - tornillo', eu + su * 0.0375, ev + sv * 0.0235, W_EXP, W_EXP + 0.0015, 0.0022, METAL, 12)

# ================================================================== batería 12 V 9 Ah (etiqueta de la foto)
borrar('Bateria - etiqueta PRECAUTIONS', 'Bateria - texto')
bu, bv = 0.085, 0.06
foto_frente('Bateria - etiqueta real (foto)', bu, bv, 0.0712, 0.094, 0.151, mat_foto('Bateria etiqueta (foto)', 'tex_bateria_frente.png', 0.5))

# ================================================================== controlador de carga PWM (frente de la foto)
borrar('Controlador - frente azul', 'Controlador - pantalla LCD', 'Controlador - boton', 'Controlador - USB', 'Controlador - borne')
cu_, cv_ = -0.087, -0.093
AC, HC = 0.172, 0.09
foto_frente('Controlador - frente real (foto)', cu_, cv_, 0.0382, AC, HC, mat_foto('Controlador frente (foto)', 'tex_controlador_frente.png', 0.35))


def en_textura(rx, ry):          # posición relativa en la foto (0..1, desde arriba-izquierda) -> (u, v)
    return cu_ - AC / 2 + rx * AC, cv_ + HC / 2 - ry * HC


for rx in (0.30, 0.38, 0.46, 0.53, 0.60, 0.69):
    u, v = en_textura(rx, 0.19)
    cil_w('Controlador - tornillo de borne', u, v, 0.0382, 0.0397, 0.0028, METAL, 16)
for rx in (0.37, 0.495, 0.615):
    u, v = en_textura(rx, 0.45)
    cil_w('Controlador - boton', u, v, 0.0382, 0.0405, 0.0042, GOMA, 20)

# ================================================================== PING))) (tarjeta con la foto, bajo la tapa del tinaco)
TY, ZT = -3.75, 1.258
piv = bpy.data.objects['Tapa del tinaco (pivote)']
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, TY, ZT - 0.0409), rotation=(math.pi, 0, math.pi))   # pines abajo, como en la foto
pl = bpy.context.object
pl.name = 'PING))) - tarjeta real (foto)'
pl.scale = (0.046, 0.0212, 1)
pl.data.materials.append(mat_foto('PING tarjeta (foto)', 'tex_ping_tarjeta.png', 0.4))
for c in list(pl.users_collection):
    c.objects.unlink(pl)
col.objects.link(pl)
bpy.context.view_layer.update()            # sin esto matrix_world todavía no trae la escala y la tarjeta queda de 1 m
mw = pl.matrix_world.copy()
pl.parent = piv
pl.matrix_parent_inverse = piv.matrix_world.inverted()
pl.matrix_world = mw
bpy.ops.object.select_all(action='DESELECT')
# malla de los transductores: más oscura (en la foto se ve la malla dorada hundida dentro del aro plateado)
if 'Malla dorada' in bpy.data.materials:
    _m = bpy.data.materials['Malla dorada'].node_tree.nodes['Principled BSDF']
    _m.inputs['Base Color'].default_value = (0.16, 0.13, 0.06, 1)
    _m.inputs['Roughness'].default_value = 0.85
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

# ================================================================== imágenes de revisión
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.eevee.taa_render_samples = 64
sc.render.image_settings.file_format = 'PNG'
camara_video = sc.camera


def foto(nombre, pos, mira, lente, frame):
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


foto('componentes_reales_gabinete', tuple(P(0.0, 0.0, 0.62)), tuple(P(0.0, 0.0, 0.03)), 38, 200)
foto('componentes_reales_esp32', tuple(P(eu + 0.01, ev - 0.035, 0.17)), tuple(P(eu, ev, 0.035)), 50, 200)
foto('componentes_reales_controlador_bateria', tuple(P(0.02, -0.02, 0.36)), tuple(P(0.0, -0.01, 0.04)), 40, 200)
sc.frame_set(330)
bpy.context.view_layer.update()
m3 = pl.matrix_world.to_3x3()
n = (m3 @ Vector((0, 0, 1))).normalized()
arriba = (m3 @ Vector((0, 1, 0))).normalized()
centro = pl.matrix_world.translation
cd = bpy.data.cameras.new('componentes_reales_ping')
cd.lens, cd.clip_start = 60, 0.003
cp = bpy.data.objects.new('componentes_reales_ping', cd)
col.objects.link(cp)
zc = (n + 0.35 * arriba.cross(n)).normalized()
yc = (arriba - arriba.dot(zc) * zc).normalized()
cp.matrix_world = Matrix((list(yc.cross(zc)), list(yc), list(zc))).transposed().to_4x4()
cp.location = centro + zc * 0.16
sc.camera = cp
sc.render.filepath = os.path.join(REN, 'componentes_reales_ping.png')
bpy.ops.render.render(write_still=True)
sc.camera = camara_video
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

if VIDEO:
    sc.eevee.taa_render_samples = 24
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'NONE'
    sc.render.ffmpeg.video_bitrate = 7000
    sc.render.ffmpeg.maxrate = 9000
    sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
    sc.render.filepath = os.path.join(DIR, 'video', 'AquaHuerto_componentes_reales_')
    bpy.ops.render.render(animation=True)
print('COMPONENTES_OK', NUEVO)
