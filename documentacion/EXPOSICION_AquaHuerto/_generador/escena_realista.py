"""Versión realista de la escena (texturas, cielo, sol, árboles, pasto) y video de recorrido.

No modifica AquaHuerto_instalacion.blend: lo abre y guarda una COPIA como AquaHuerto_instalacion_realista.blend.
Ejecutar: blender -b -P escena_realista.py -- <carpeta_modelos_3D> [--sin-video]
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
DIR = args[0]
VIDEO = '--sin-video' not in args
ORIG = os.path.join(DIR, 'AquaHuerto_instalacion.blend')
NUEVO = os.path.join(DIR, 'AquaHuerto_instalacion_realista.blend')
OUTV = os.path.join(DIR, 'video')
os.makedirs(OUTV, exist_ok=True)
REN = os.path.join(DIR, 'renders')

bpy.ops.wm.open_mainfile(filepath=ORIG)
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)      # desde aquí todo se guarda en la copia
sc = bpy.context.scene
random.seed(7)
piso = bpy.data.objects['Piso de tierra']
piso.scale = (5, 5, 1)
bpy.ops.object.select_all(action='DESELECT')
piso.select_set(True)
bpy.context.view_layer.objects.active = piso
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.data.objects['Pasto'].scale = (6, 5, 1)


# ------------------------------------------------------------------ utilidades de nodos
def nodos(m):
    m.use_nodes = True
    nt = m.node_tree
    return nt, nt.nodes, nt.links, nt.nodes['Principled BSDF']


def coord(nt, escala=1.0):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (escala, escala, escala)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    return mp.outputs['Vector']


def rampa(nt, fac, colores):
    cr = nt.nodes.new('ShaderNodeValToRGB')
    el = cr.color_ramp.elements
    el[0].position, el[0].color = colores[0][0], (*colores[0][1], 1)
    el[1].position, el[1].color = colores[-1][0], (*colores[-1][1], 1)
    for pos, c in colores[1:-1]:
        e = el.new(pos)
        e.color = (*c, 1)
    nt.links.new(fac, cr.inputs['Fac'])
    return cr.outputs['Color']


def ruido(nt, v, escala, detalle=6, rug=0.55):
    n = nt.nodes.new('ShaderNodeTexNoise')
    n.inputs['Scale'].default_value = escala
    n.inputs['Detail'].default_value = detalle
    n.inputs['Roughness'].default_value = rug
    nt.links.new(v, n.inputs['Vector'])
    return n.outputs['Fac']


def relieve(nt, bsdf, altura, fuerza=0.3, dist=0.01):
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = fuerza
    b.inputs['Distance'].default_value = dist
    nt.links.new(altura, b.inputs['Height'])
    nt.links.new(b.outputs['Normal'], bsdf.inputs['Normal'])


def M(nombre):
    return bpy.data.materials.get(nombre)


def mezclar(nt, a, b, fac):
    mx = nt.nodes.new('ShaderNodeMixRGB')
    nt.links.new(fac, mx.inputs['Fac'])
    nt.links.new(a, mx.inputs['Color1'])
    nt.links.new(b, mx.inputs['Color2'])
    return mx.outputs['Color']


# ------------------------------------------------------------------ texturas procedurales
def madera(m):
    nt, n, l, bs = nodos(m)
    v = coord(nt, 6)
    w = n.new('ShaderNodeTexWave')
    w.wave_type = 'BANDS'
    w.bands_direction = 'Z'
    w.inputs['Scale'].default_value = 3.0
    w.inputs['Distortion'].default_value = 6.0
    w.inputs['Detail'].default_value = 3
    l.new(v, w.inputs['Vector'])
    f = mezclar(nt, w.outputs['Fac'], n.new('ShaderNodeTexNoise').outputs['Fac'], ruido(nt, v, 2))
    col = rampa(nt, w.outputs['Fac'], [(0.0, (0.38, 0.22, 0.07)), (0.5, (0.55, 0.36, 0.13)), (1.0, (0.45, 0.28, 0.09))])
    l.new(col, bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.65
    relieve(nt, bs, w.outputs['Fac'], 0.08, 0.002)


def tierra(m, c1, c2, escala=4, fuerza=0.6):
    nt, n, l, bs = nodos(m)
    v = coord(nt, escala)
    f1 = ruido(nt, v, 3, 8, 0.6)
    f2 = ruido(nt, v, 40, 4, 0.7)
    col = rampa(nt, f1, [(0.3, c1), (0.7, c2)])
    l.new(col, bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.95
    relieve(nt, bs, f2, fuerza, 0.02)


def concreto(m):
    nt, n, l, bs = nodos(m)
    v = coord(nt, 2)
    f = ruido(nt, v, 25, 8, 0.6)
    l.new(rampa(nt, f, [(0.35, (0.5, 0.49, 0.46)), (0.65, (0.66, 0.65, 0.61))]), bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.9
    relieve(nt, bs, f, 0.25, 0.01)


def blocks(m, c_block, c_junta, pintado=False):
    nt, n, l, bs = nodos(m)
    tc = n.new('ShaderNodeTexCoord')
    br = n.new('ShaderNodeTexBrick')
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Brick Width'].default_value = 0.4
    br.inputs['Row Height'].default_value = 0.2
    br.inputs['Mortar Size'].default_value = 0.012
    br.offset = 0.5
    sep = n.new('ShaderNodeSeparateXYZ')
    cmb = n.new('ShaderNodeCombineXYZ')
    l.new(tc.outputs['Object'], sep.inputs['Vector'])
    l.new(sep.outputs['X'], cmb.inputs['X'])
    l.new(sep.outputs['Z'], cmb.inputs['Y'])
    l.new(cmb.outputs['Vector'], br.inputs['Vector'])
    br.inputs['Color1'].default_value = (*c_block, 1)
    br.inputs['Color2'].default_value = (*[c * 0.93 for c in c_block], 1)
    br.inputs['Mortar'].default_value = (*c_junta, 1)
    suc = ruido(nt, tc.outputs['Object'], 6, 6, 0.6)
    col = mezclar(nt, br.outputs['Color'], (lambda: (rampa(nt, suc, [(0.4, tuple(c * 0.8 for c in c_block)),
                                                                    (0.8, c_block)])))(), suc)
    l.new(col, bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.85
    relieve(nt, bs, br.outputs['Fac'], -0.4, 0.01)


def plastico(m, color, rugo=0.45, manchas=False):
    nt, n, l, bs = nodos(m)
    v = coord(nt, 3)
    f = ruido(nt, v, 5, 6, 0.6)
    if manchas:
        l.new(rampa(nt, f, [(0.4, color), (0.8, tuple(min(1, c * 1.8 + 0.02) for c in color))]), bs.inputs['Base Color'])
    else:
        bs.inputs['Base Color'].default_value = (*color, 1)
    r = rampa(nt, f, [(0.3, (rugo - 0.1,) * 3), (0.7, (rugo + 0.15,) * 3)])
    l.new(r, bs.inputs['Roughness'])


def metal(m, color, rugo=0.4):
    nt, n, l, bs = nodos(m)
    v = coord(nt, 4)
    f = ruido(nt, v, 30, 8, 0.6)
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = 0.85
    l.new(rampa(nt, f, [(0.3, (rugo - 0.15,) * 3), (0.7, (rugo + 0.2,) * 3)]), bs.inputs['Roughness'])
    relieve(nt, bs, f, 0.05, 0.002)


def malla(m):
    nt, n, l, bs = nodos(m)
    v = coord(nt, 1)
    ck = n.new('ShaderNodeTexChecker')
    ck.inputs['Scale'].default_value = 400
    l.new(v, ck.inputs['Vector'])
    bs.inputs['Base Color'].default_value = (0.03, 0.03, 0.03, 1)
    bs.inputs['Roughness'].default_value = 0.8
    relieve(nt, bs, ck.outputs['Fac'], 0.3, 0.002)


def panel_solar(m):
    nt, n, l, bs = nodos(m)
    v = coord(nt, 1)
    br = n.new('ShaderNodeTexBrick')
    br.inputs['Scale'].default_value = 9
    br.offset = 0.0
    br.inputs['Brick Width'].default_value = 1.0
    br.inputs['Row Height'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = 0.03
    br.inputs['Color1'].default_value = (0.02, 0.05, 0.16, 1)
    br.inputs['Color2'].default_value = (0.03, 0.07, 0.2, 1)
    br.inputs['Mortar'].default_value = (0.7, 0.72, 0.75, 1)
    l.new(v, br.inputs['Vector'])
    l.new(br.outputs['Color'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.08
    bs.inputs['Specular'].default_value = 0.8


madera(M('Madera pino'))
tierra(M('Tierra'), (0.22, 0.15, 0.09), (0.36, 0.26, 0.17), 2, 0.8)
tierra(M('Sustrato'), (0.06, 0.04, 0.03), (0.16, 0.11, 0.08), 6, 1.0)
tierra(M('Pasto'), (0.06, 0.14, 0.03), (0.2, 0.32, 0.08), 3, 0.4)
concreto(M('Concreto'))
concreto(M('Losa'))
blocks(M('Pared blanca'), (0.74, 0.73, 0.68), (0.55, 0.54, 0.5))
blocks(M('Pared azul'), (0.04, 0.24, 0.38), (0.03, 0.18, 0.28))
plastico(M('Plastico negro'), (0.025, 0.025, 0.03), 0.4, manchas=True)
plastico(M('Caja gris'), (0.45, 0.46, 0.46), 0.5)
plastico(M('Gabinete blanco'), (0.85, 0.85, 0.82), 0.4)
plastico(M('Poliducto naranja'), (0.85, 0.16, 0.02), 0.5)
plastico(M('Tuboplus verde'), (0.03, 0.3, 0.12), 0.3)
plastico(M('Manguera azul'), (0.02, 0.12, 0.6), 0.3)
metal(M('Acero PTR'), (0.12, 0.11, 0.1), 0.5)
metal(M('Aluminio'), (0.8, 0.8, 0.82), 0.3)
malla(M('Malla antimaleza'))
panel_solar(M('Celdas solares'))

# ------------------------------------------------------------------ pasto con pelo, árboles y cielo
pasto = bpy.data.objects['Pasto']
ps = pasto.modifiers.new('pasto', 'PARTICLE_SYSTEM').particle_system
st = ps.settings
st.type = 'HAIR'
st.count = 60000
st.hair_length = 0.07
st.use_advanced_hair = True
st.factor_random = 0.04
st.brownian_factor = 0.01
st.child_type = 'NONE'
st.display_step = 2
st.render_step = 2
mg = bpy.data.materials.new('Hojas de pasto')
mg.use_nodes = True
mg.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.09, 0.22, 0.04, 1)
pasto.data.materials.append(mg)
st.material = len(pasto.data.materials)

col_arb = bpy.data.collections.new('Arboles')
sc.collection.children.link(col_arb)
mt = bpy.data.materials.new('Tronco')
plastico(mt, (0.42, 0.4, 0.36), 0.8, manchas=True)
mh = bpy.data.materials.new('Follaje')
tierra(mh, (0.05, 0.16, 0.03), (0.22, 0.38, 0.08), 8, 0.8)


def arbol(x, y, h):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.14, depth=h, location=(x, y, h / 2), vertices=16)
    t = bpy.context.object
    t.data.materials.append(mt)
    for o in [t]:
        for c in o.users_collection:
            c.objects.unlink(o)
        col_arb.objects.link(o)
    for k in range(5):
        r = random.uniform(0.9, 1.4)
        bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=3,
                                              location=(x + random.uniform(-0.8, 0.8), y + random.uniform(-0.8, 0.8),
                                                        h + random.uniform(-0.2, 0.9)))
        f = bpy.context.object
        d = f.modifiers.new('irregular', 'DISPLACE')
        tx = bpy.data.textures.new('ruido_hojas', 'CLOUDS')
        tx.noise_scale = 0.4
        d.texture = tx
        d.strength = 0.45
        f.data.materials.append(mh)
        bpy.ops.object.shade_smooth()
        for c in f.users_collection:
            c.objects.unlink(f)
        col_arb.objects.link(f)


arbol(-5.2, 3.6, 3.4)
arbol(3.9, -2.3, 3.8)
arbol(-4.8, -2.0, 3.0)

# cielo físico y sol
w = sc.world
nt = w.node_tree
for nd in list(nt.nodes):
    if nd.type == 'TEX_SKY':
        nt.nodes.remove(nd)
sky = nt.nodes.new('ShaderNodeTexSky')
sky.sky_type = 'NISHITA'
sky.sun_elevation = math.radians(38)
sky.sun_rotation = math.radians(25)        # sol del lado +X, hacia donde mira el panel
sky.altitude = 1400
sky.air_density = 1.2
sky.dust_density = 1.5
nt.links.new(sky.outputs['Color'], nt.nodes['Background'].inputs['Color'])
nt.nodes['Background'].inputs['Strength'].default_value = 0.12
sol = [o for o in bpy.data.objects if o.type == 'LIGHT'][0]
sol.data.energy = 3.6
sol.data.angle = math.radians(1.5)
sol.data.color = (1.0, 0.96, 0.9)
dirv = Vector((math.cos(math.radians(38)) * math.cos(math.radians(25)),
               math.cos(math.radians(38)) * math.sin(math.radians(25)), math.sin(math.radians(38))))
sol.rotation_euler = (-dirv).to_track_quat('-Z', 'Y').to_euler()

# ------------------------------------------------------------------ render EEVEE con más calidad
sc.render.engine = 'BLENDER_EEVEE'
ee = sc.eevee
ee.use_soft_shadows = True
ee.shadow_cube_size = '2048'
ee.shadow_cascade_size = '4096'
ee.use_gtao = True
ee.gtao_distance = 0.6
ee.use_ssr = True
ee.use_ssr_refraction = False
ee.use_bloom = True
ee.bloom_intensity = 0.03
ee.taa_render_samples = 64
sc.view_settings.view_transform = 'Filmic'
sc.view_settings.look = 'Medium High Contrast'
sc.view_settings.exposure = -0.6

# ------------------------------------------------------------------ cámara del recorrido
objetivo = bpy.data.objects.new('Objetivo del recorrido', None)
sc.collection.objects.link(objetivo)
bpy.ops.object.camera_add(location=(6, 4, 3.5))
cam = bpy.context.object
cam.name = 'Camara recorrido'
cam.data.lens = 24
cam.data.dof.use_dof = False
tr = cam.constraints.new('TRACK_TO')
tr.target = objetivo
tr.track_axis = 'TRACK_NEGATIVE_Z'
tr.up_axis = 'UP_Y'
ruta = [  # cuadro, posición de la cámara, punto que mira
    (1, (6.5, 4.5, 3.6), (0.0, -1.7, 0.8)),
    (70, (3.0, 0.6, 1.9), (0.0, -0.1, 0.9)),
    (130, (-1.7, 0.9, 2.1), (0.0, 0.0, 1.0)),
    (190, (-1.3, -1.6, 0.9), (0.0, -2.2, 0.15)),
    (250, (1.1, -1.4, 1.5), (-0.3, -3.9, 1.4)),
    (300, (0.6, -0.7, 2.3), (-0.4, -4.2, 2.6)),
    (360, (5.5, 3.0, 4.2), (0.0, -1.9, 0.8)),
]
for f, pc, po in ruta:
    cam.location = pc
    objetivo.location = po
    cam.keyframe_insert('location', frame=f)
    objetivo.keyframe_insert('location', frame=f)
for o in (cam, objetivo):
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
sc.camera = cam
sc.frame_start, sc.frame_end = 1, 360
sc.render.fps = 30
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = 100
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

# imágenes fijas realistas
for nombre, f in (('realista_general', 1), ('realista_cajon', 70), ('realista_linea', 190), ('realista_tinaco_panel', 300)):
    sc.frame_set(f)
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = os.path.join(REN, nombre + '.png')
    bpy.ops.render.render(write_still=True)
sc.frame_set(1)

if VIDEO:
    ee.taa_render_samples = 24
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
    sc.render.filepath = os.path.join(OUTV, 'AquaHuerto_recorrido_')
    bpy.ops.render.render(animation=True)
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
print('REALISTA_OK', NUEVO)
