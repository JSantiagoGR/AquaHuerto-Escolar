"""Recorrido completo de la instalación (40 s): cajón regando (cascada en cada microaspersor) -> cajas que se abren ->
tubería, filtro y escalón -> tinaco (se abre la tapa: PING))) y agua adentro) -> gabinete (se quita la tapa) -> panel solar.
Además: colores de tubería como en las fotos, madera de pino con veta, sustrato con perlita, agua clara.

Abre AquaHuerto_riego.blend (sin modificarlo) y guarda AquaHuerto_recorrido_completo.blend.
Ejecutar: blender -b -P video_recorrido_completo.py -- <carpeta_modelos_3D> [--cuadros] [--video]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
DIR = args[0]
CUADROS = '--cuadros' in args
VIDEO = '--video' in args
NUEVO = os.path.join(DIR, 'AquaHuerto_recorrido_completo.blend')
REN = os.path.join(DIR, 'renders')
bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_riego.blend'))
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
sc = bpy.context.scene
F_FIN = 1200
F_AGUA = 30
sc.frame_start, sc.frame_end = 1, F_FIN
sc.render.fps = 30
col = bpy.data.collections.get('Riego (gotas)') or sc.collection


def principled(m):
    return next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def srgb(c):
    return tuple(((x / 255) / 12.92) if x / 255 <= 0.04045 else (((x / 255) + 0.055) / 1.055) ** 2.4 for x in c)


# ====================================================================== 1. colores de la tubería (como en las fotos)
for nombre, rgb, rough in (('Tuboplus verde', (52, 128, 96), 0.42),       # PPR verde (tono apagado, como la foto)
                           ('Manguera azul', (24, 74, 112), 0.35)):     # manguera azul petróleo que sube al cajón
    m = bpy.data.materials.get(nombre)
    if m:
        b = principled(m)
        for l in list(b.inputs['Base Color'].links):
            m.node_tree.links.remove(l)
        b.inputs['Base Color'].default_value = (*srgb(rgb), 1)
        b.inputs['Roughness'].default_value = rough
        b.inputs['Specular'].default_value = 0.45

# ====================================================================== 2. madera de pino con veta (según el largo de cada pieza)
def madera(eje):
    m = bpy.data.materials.new(f'Pino con veta ({eje})')
    m.use_nodes = True
    nt = m.node_tree
    b = principled(m)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    esc = {'X': (1.5, 45, 45), 'Y': (45, 1.5, 45), 'Z': (45, 45, 1.5)}[eje]
    mp.inputs['Scale'].default_value = esc
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    veta = nt.nodes.new('ShaderNodeTexNoise')
    veta.inputs['Scale'].default_value = 3.0
    veta.inputs['Detail'].default_value = 10
    veta.inputs['Distortion'].default_value = 1.2
    nt.links.new(mp.outputs['Vector'], veta.inputs['Vector'])
    anillos = nt.nodes.new('ShaderNodeTexWave')
    anillos.wave_type = 'RINGS'
    anillos.inputs['Scale'].default_value = 1.2
    anillos.inputs['Distortion'].default_value = 6
    anillos.inputs['Detail'].default_value = 4
    nt.links.new(mp.outputs['Vector'], anillos.inputs['Vector'])
    mezcla = nt.nodes.new('ShaderNodeMixRGB')
    mezcla.blend_type = 'MULTIPLY'
    mezcla.inputs['Fac'].default_value = 0.55
    nt.links.new(veta.outputs['Fac'], mezcla.inputs['Color1'])
    nt.links.new(anillos.outputs['Fac'], mezcla.inputs['Color2'])
    rampa = nt.nodes.new('ShaderNodeValToRGB')
    e = rampa.color_ramp.elements
    e[0].position, e[0].color = 0.18, (*srgb((178, 128, 62)), 1)
    e[1].position, e[1].color = 0.62, (*srgb((226, 190, 122)), 1)
    nt.links.new(mezcla.outputs['Color'], rampa.inputs['Fac'])
    nt.links.new(rampa.outputs['Color'], b.inputs['Base Color'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.08
    bump.inputs['Distance'].default_value = 0.002
    nt.links.new(mezcla.outputs['Color'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.62
    b.inputs['Specular'].default_value = 0.3
    return m


PINOS = {e: madera(e) for e in 'XYZ'}
madera_vieja = bpy.data.materials.get('Madera pino')
for o in bpy.data.objects:
    if o.type != 'MESH' or not madera_vieja:
        continue
    for i, m in enumerate(o.data.materials):
        if m == madera_vieja:
            d = o.dimensions
            eje = 'XYZ'[max(range(3), key=lambda k: d[k])]
            o.data.materials[i] = PINOS[eje]

# ====================================================================== 3. sustrato con perlita (puntitos blancos como en la foto)
sus = bpy.data.objects.get('Sustrato')
m_sus = sus.data.materials[0] if sus and sus.data.materials else None
if m_sus:
    nt = m_sus.node_tree
    b = principled(m_sus)
    mezcla_moja = next((n for n in nt.nodes if n.type == 'MIX_RGB' and n.blend_type == 'MULTIPLY'), None)
    destino = mezcla_moja.inputs['Color1'] if mezcla_moja else b.inputs['Base Color']
    base = nt.nodes.new('ShaderNodeTexNoise')
    base.inputs['Scale'].default_value = 140
    base.inputs['Detail'].default_value = 8
    r1 = nt.nodes.new('ShaderNodeValToRGB')
    r1.color_ramp.elements[0].color = (*srgb((38, 26, 18)), 1)
    r1.color_ramp.elements[1].color = (*srgb((84, 62, 44)), 1)
    nt.links.new(base.outputs['Fac'], r1.inputs['Fac'])
    perl = nt.nodes.new('ShaderNodeTexVoronoi')
    perl.inputs['Scale'].default_value = 260
    pr = nt.nodes.new('ShaderNodeValToRGB')
    pr.color_ramp.elements[0].position, pr.color_ramp.elements[0].color = 0.0, (1, 1, 1, 1)
    pr.color_ramp.elements[1].position, pr.color_ramp.elements[1].color = 0.09, (0, 0, 0, 1)
    nt.links.new(perl.outputs['Distance'], pr.inputs['Fac'])
    mx = nt.nodes.new('ShaderNodeMixRGB')
    mx.inputs['Color2'].default_value = (0.82, 0.8, 0.76, 1)
    nt.links.new(r1.outputs['Color'], mx.inputs['Color1'])
    nt.links.new(pr.outputs['Color'], mx.inputs['Fac'])
    for l in list(destino.links):
        nt.links.remove(l)
    nt.links.new(mx.outputs['Color'], destino)
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.35
    nt.links.new(base.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    # se moja durante el riego (retiempo de la animación anterior)
    if mezcla_moja:
        c2 = mezcla_moja.inputs['Color2']
        if nt.animation_data:
            nt.animation_data_clear()
        c2.default_value = (1, 1, 1, 1)
        c2.keyframe_insert('default_value', frame=F_AGUA + 20)
        c2.default_value = (0.55, 0.53, 0.52, 1)
        c2.keyframe_insert('default_value', frame=420)
        rr = b.inputs['Roughness']
        rr.default_value = 0.9
        rr.keyframe_insert('default_value', frame=F_AGUA + 20)
        rr.default_value = 0.45
        rr.keyframe_insert('default_value', frame=420)

# ====================================================================== 4. agua clara: gotas alargadas y cascada en cada aspersor
gota = bpy.data.objects['Gota (instancia)']
gota.scale = (5.0, 1.0, 1.0)
ag = gota.data.materials[0]
b = principled(ag)
b.inputs['Base Color'].default_value = (0.75, 0.88, 1.0, 1)
b.inputs['Alpha'].default_value = 0.5
b.inputs['Emission'].default_value = (0.8, 0.92, 1.0, 1)
b.inputs['Emission Strength'].default_value = 0.35
b.inputs['Roughness'].default_value = 0.02
for o in bpy.data.objects:
    if o.name.startswith('Emisor de gotas'):
        st = o.particle_systems[0].settings
        st.frame_start, st.frame_end = F_AGUA, F_FIN
        st.count = 42000
        st.normal_factor = 0.95
        st.factor_random = 0.3


def agua_cascada():
    m = bpy.data.materials.new('Cascada de agua (rociador)')
    m.use_nodes = True
    m.blend_method = 'BLEND'
    m.shadow_method = 'NONE'
    m.show_transparent_back = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
    # ángulo alrededor del cono (para chorros radiales) y altura
    sx = nt.nodes.new('ShaderNodeMath'); sx.operation = 'SUBTRACT'; sx.inputs[1].default_value = 0.5
    sy = nt.nodes.new('ShaderNodeMath'); sy.operation = 'SUBTRACT'; sy.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs['X'], sx.inputs[0]); nt.links.new(sep.outputs['Y'], sy.inputs[0])
    ang = nt.nodes.new('ShaderNodeMath'); ang.operation = 'ARCTAN2'
    nt.links.new(sy.outputs[0], ang.inputs[0]); nt.links.new(sx.outputs[0], ang.inputs[1])
    tiempo = nt.nodes.new('ShaderNodeValue')
    tiempo.outputs[0].default_value = 0.0
    fc = tiempo.outputs[0].driver_add('default_value')
    fc.driver.expression = 'frame*0.09'
    zt = nt.nodes.new('ShaderNodeMath'); zt.operation = 'MULTIPLY_ADD'
    zt.inputs[1].default_value = 3.0
    nt.links.new(sep.outputs['Z'], zt.inputs[0]); nt.links.new(tiempo.outputs[0], zt.inputs[2])
    comb = nt.nodes.new('ShaderNodeCombineXYZ')
    a2 = nt.nodes.new('ShaderNodeMath'); a2.operation = 'MULTIPLY'; a2.inputs[1].default_value = 9.0
    nt.links.new(ang.outputs[0], a2.inputs[0])
    nt.links.new(a2.outputs[0], comb.inputs['X']); nt.links.new(zt.outputs[0], comb.inputs['Y'])
    ruido = nt.nodes.new('ShaderNodeTexNoise')
    ruido.inputs['Scale'].default_value = 2.2
    ruido.inputs['Detail'].default_value = 3
    nt.links.new(comb.outputs['Vector'], ruido.inputs['Vector'])
    chorros = nt.nodes.new('ShaderNodeValToRGB')
    chorros.color_ramp.elements[0].position, chorros.color_ramp.elements[0].color = 0.5, (0, 0, 0, 1)
    chorros.color_ramp.elements[1].position, chorros.color_ramp.elements[1].color = 0.68, (1, 1, 1, 1)
    nt.links.new(ruido.outputs['Fac'], chorros.inputs['Fac'])
    # se desvanece arriba (sale de la boquilla) y abajo (llega a la tierra en gotas)
    arr = nt.nodes.new('ShaderNodeMapRange')
    arr.inputs['From Min'].default_value, arr.inputs['From Max'].default_value = 1.0, 0.82
    nt.links.new(sep.outputs['Z'], arr.inputs['Value'])
    aba = nt.nodes.new('ShaderNodeMapRange')
    aba.inputs['From Min'].default_value, aba.inputs['From Max'].default_value = 0.0, 0.35
    nt.links.new(sep.outputs['Z'], aba.inputs['Value'])
    f1 = nt.nodes.new('ShaderNodeMath'); f1.operation = 'MULTIPLY'
    nt.links.new(arr.outputs[0], f1.inputs[0]); nt.links.new(aba.outputs[0], f1.inputs[1])
    f2 = nt.nodes.new('ShaderNodeMath'); f2.operation = 'MULTIPLY'
    nt.links.new(f1.outputs[0], f2.inputs[0]); nt.links.new(chorros.outputs['Color'], f2.inputs[1])
    f3 = nt.nodes.new('ShaderNodeMath'); f3.operation = 'MULTIPLY'; f3.inputs[1].default_value = 0.0
    nt.links.new(f2.outputs[0], f3.inputs[0])
    m['_fac_socket'] = 1
    # encendido del agua (0 antes de F_AGUA)
    f3.inputs[1].default_value = 0.0
    f3.inputs[1].keyframe_insert('default_value', frame=F_AGUA)
    f3.inputs[1].default_value = 0.55
    f3.inputs[1].keyframe_insert('default_value', frame=F_AGUA + 12)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    gl = nt.nodes.new('ShaderNodeBsdfPrincipled')
    gl.inputs['Base Color'].default_value = (0.8, 0.9, 1.0, 1)
    gl.inputs['Roughness'].default_value = 0.05
    gl.inputs['Specular'].default_value = 0.8
    gl.inputs['Emission'].default_value = (0.85, 0.93, 1.0, 1)
    gl.inputs['Emission Strength'].default_value = 0.45
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(f3.outputs[0], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return m


CASCADA = agua_cascada()
Z_TIERRA = 0.48
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if not o.name.startswith('Boquilla '):
        continue
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    c = sum(pts, Vector()) / 8
    zb = min(p.z for p in pts) - 0.002
    h = zb - Z_TIERRA
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=0.30, radius2=0.012, depth=h, end_fill_type='NOTHING',
                                    location=(c.x, c.y, Z_TIERRA + h / 2))
    cono = bpy.context.object
    cono.name = 'Cascada de agua ' + o.name.replace('Boquilla ', '')
    cono.data.materials.append(CASCADA)
    bpy.ops.object.shade_smooth()
    for cc in list(cono.users_collection):
        cc.objects.unlink(cono)
    col.objects.link(cono)
    # cono un poco "abombado" (sombrilla): el agua se abre rápido abajo de la boquilla y luego cae
    for v in cono.data.vertices:
        t = min(1.0, max(0.0, (v.co.z + h / 2) / h))   # 0 abajo, 1 arriba
        r = math.hypot(v.co.x, v.co.y)
        if r > 1e-6:
            nr = 0.012 + (0.30 - 0.012) * (1 - t) ** 0.55
            v.co.x *= nr / r
            v.co.y *= nr / r

# ====================================================================== 5. tapas que se abren durante el recorrido
def suave(o):
    for fc in o.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = 'BEZIER'
            k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'


for nombre, f0 in (('Caja de la bomba', 335), ('Caja del caudalimetro', 360), ('Caja de la electrovalvula', 385)):
    t = bpy.data.objects.get(f'{nombre} - tapa (parte superior)')
    if not t:
        continue
    t.animation_data_clear()
    t.location, t.rotation_euler = (0, 0, 0), (0, 0, 0)
    t.keyframe_insert('location', frame=1)
    t.keyframe_insert('location', frame=f0)
    t.keyframe_insert('rotation_euler', frame=f0)
    t.location = (0, 0, 0.22)
    t.keyframe_insert('location', frame=f0 + 16)
    t.location = (-0.45, 0, 0.22)               # hacia atrás (lado contrario a la cámara) para no taparla
    t.rotation_euler = (0, 0, math.radians(-8))
    t.keyframe_insert('location', frame=f0 + 32)
    t.keyframe_insert('rotation_euler', frame=f0 + 32)
    t.location = (-0.45, 0, -0.05)
    t.keyframe_insert('location', frame=f0 + 46)
    suave(t)

TY, ZT = -3.45, 1.258 + 0.14
piv = bpy.data.objects['Tapa del tinaco (pivote)']
piv.animation_data_clear()
piv.location, piv.rotation_euler = (0, TY, ZT), (0, 0, 0)
piv.keyframe_insert('location', frame=1)
piv.keyframe_insert('location', frame=585)
piv.keyframe_insert('rotation_euler', frame=585)
piv.location = (0, TY, ZT + 0.32)
piv.keyframe_insert('location', frame=607)
piv.location = (0.12, TY + 0.25, ZT + 0.42)
piv.rotation_euler = (math.radians(150), 0, 0)
piv.keyframe_insert('location', frame=633)
piv.keyframe_insert('rotation_euler', frame=633)
suave(piv)

tg = bpy.data.objects['Gabinete - tapa']
tg.animation_data_clear()
tg.location, tg.rotation_euler = (0, 0, 0), (0, 0, 0)
tg.keyframe_insert('location', frame=1)
tg.keyframe_insert('location', frame=770)
tg.keyframe_insert('rotation_euler', frame=770)
tg.location = (0, 0.14, 0)
tg.keyframe_insert('location', frame=790)
tg.location = (-0.55, 0.3, -0.05)
tg.rotation_euler = (0, 0, math.radians(-25))
tg.keyframe_insert('location', frame=818)
tg.keyframe_insert('rotation_euler', frame=818)
suave(tg)

# ====================================================================== 6. cámara del recorrido
obj = bpy.data.objects.new('Objetivo recorrido completo', None)
sc.collection.objects.link(obj)
cd = bpy.data.cameras.new('Camara recorrido completo')
cam = bpy.data.objects.new('Camara recorrido completo', cd)
sc.collection.objects.link(cam)
cd.clip_start = 0.01
trk = cam.constraints.new('TRACK_TO')
trk.target = obj
trk.track_axis, trk.up_axis = 'TRACK_NEGATIVE_Z', 'UP_Y'
ruta = [
    (1, (4.6, 3.4, 3.1), (0.0, -1.4, 0.6), 24),            # vista general
    (110, (2.5, 1.7, 1.8), (0.0, 0.0, 0.9), 28),            # cajón regando
    (200, (1.05, -0.95, 1.05), (0.0, 0.0, 1.2), 24),        # bajo los aspersores (cascadas)
    (270, (1.2, -1.15, 0.9), (0.05, -1.5, 0.15), 28),       # hacia las cajas
    (340, (0.62, -1.2, 0.55), (0.03, -1.7, 0.06), 30),      # se abren las cajas
    (440, (0.48, -1.95, 0.45), (0.03, -1.55, 0.05), 30),
    (505, (0.75, -2.25, 0.6), (0.05, -2.8, 0.25), 30),      # tubería, filtro Y y escalón
    (565, (1.3, -2.45, 1.3), (0.0, -3.45, 0.85), 28),       # tinaco
    (640, (0.5, -2.7, 2.15), (0.12, -3.15, 1.82), 34),      # tapa abierta: PING))) en su caja de acrílico
    (705, (-0.3, -3.62, 2.1), (0.03, -3.42, 1.2), 28),      # agua dentro del tinaco
    (775, (-0.55, -2.65, 1.7), (-0.95, -3.95, 1.45), 30),   # gabinete (se quita la tapa)
    (870, (-0.88, -3.35, 1.5), (-0.95, -3.97, 1.45), 34),   # electrónica
    (965, (1.25, -2.9, 3.5), (-0.15, -4.3, 2.8), 30),       # panel solar
    (1060, (0.9, -4.95, 3.45), (-0.15, -4.3, 2.82), 30),
    (1130, (1.35, -0.55, 3.7), (0.0, -1.8, 0.8), 26),       # (rodea el árbol de la derecha, no lo atraviesa)
    (1200, (1.6, 5.2, 4.4), (0.0, -1.5, 0.8), 24),          # cierre: vista general entre los árboles
]
for f, pc, po, lente in ruta:
    cam.location, obj.location, cd.lens = pc, po, lente
    cam.keyframe_insert('location', frame=f)
    obj.keyframe_insert('location', frame=f)
    cd.keyframe_insert('lens', frame=f)
suave(cam)
suave(obj)
sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

# ====================================================================== simulación de gotas y render
sc.frame_set(1)
bpy.ops.ptcache.free_bake_all()
bpy.ops.ptcache.bake_all(bake=True)
print('HORNEADO')
sc.render.image_settings.file_format = 'PNG'
if CUADROS:
    sc.eevee.taa_render_samples = 32
    for f in (110, 200, 400, 520, 650, 705, 870, 1000):
        sc.frame_set(f)
        sc.render.filepath = os.path.join(REN, 'recorrido_completo_cuadro_%04d.png' % f)
        bpy.ops.render.render(write_still=True)
if VIDEO:
    sc.eevee.taa_render_samples = 20
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'NONE'
    sc.render.ffmpeg.video_bitrate = 9000
    sc.render.ffmpeg.maxrate = 12000
    sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
    sc.render.filepath = os.path.join(DIR, 'video', 'AquaHuerto_recorrido_completo_v2_')
    bpy.ops.render.render(animation=True)
# la caché horneada pesa mucho: no se guarda en el .blend (se vuelve a simular al abrirlo)
sc.frame_set(1)
bpy.ops.ptcache.free_bake_all()
sc.render.image_settings.file_format = 'PNG'
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
print('RECORRIDO_OK', NUEVO)
