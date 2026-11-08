"""Animación del riego: los 9 microaspersores rojos rocían gotas (en forma de sombrilla, con gravedad) sobre el sustrato
del cajón, que se va oscureciendo al mojarse. Cámara que rodea el cajón y se acerca a los aspersores.

Abre AquaHuerto_tinaco_detalle.blend (sin modificarlo) y guarda AquaHuerto_riego.blend.
Ejecutar: blender -b -P escena_riego.py -- <carpeta_modelos_3D> [--video]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
DIR = args[0]
VIDEO = '--video' in args
NUEVO = os.path.join(DIR, 'AquaHuerto_riego.blend')
REN = os.path.join(DIR, 'renders')
bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_tinaco_detalle.blend'))
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
sc = bpy.context.scene
F0, F_INI, F_FIN = 1, 25, 330           # el riego arranca en el cuadro 25
sc.frame_start, sc.frame_end = F0, F_FIN
sc.render.fps = 30
col = bpy.data.collections.new('Riego (gotas)')
sc.collection.children.link(col)

# en este video la tapa del tinaco y la del gabinete quedan cerradas (sin sus animaciones)
for n in ('Tapa del tinaco (pivote)', 'Gabinete - tapa'):
    o = bpy.data.objects.get(n)
    if o and o.animation_data:
        o.animation_data.action = None
        if n.startswith('Tapa del tinaco'):
            o.location = (0.0, -3.45, 1.258 + 0.14)
        else:
            o.location = (0, 0, 0)
        o.rotation_euler = (0, 0, 0)

# ------------------------------------------------------------------ gota de agua (alargada en X: se orienta con la velocidad)
AGUA = bpy.data.materials.new('Gota de agua')
AGUA.use_nodes = True
b = AGUA.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (0.85, 0.93, 1.0, 1)
b.inputs['Roughness'].default_value = 0.05
b.inputs['Specular'].default_value = 0.9
b.inputs['Emission'].default_value = (0.9, 0.95, 1.0, 1)
b.inputs['Emission Strength'].default_value = 0.6
b.inputs['Alpha'].default_value = 0.75
AGUA.blend_method = 'BLEND'
AGUA.shadow_method = 'NONE'
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.0021, location=(0, 0, -5))
gota = bpy.context.object
gota.name = 'Gota (instancia)'
gota.scale = (3.6, 1.0, 1.0)
gota.data.materials.append(AGUA)
bpy.ops.object.shade_smooth()
for c in list(gota.users_collection):
    c.objects.unlink(gota)
col.objects.link(gota)
gota.hide_render = False

# ------------------------------------------------------------------ las gotas mueren al tocar el sustrato (y el fondo del cajón)
for n in ('Sustrato', 'Fondo del cajon', 'Piso de tierra'):
    o = bpy.data.objects.get(n)
    if o:
        o.modifiers.new('choque de gotas', 'COLLISION')
        o.collision.use_particle_kill = True

# ------------------------------------------------------------------ emisores: media esfera bajo cada boquilla
emisores = []
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if not o.name.startswith('Boquilla '):
        continue
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    centro = sum(pts, Vector()) / 8
    zb = min(p.z for p in pts)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.012, location=(centro.x, centro.y, zb - 0.002))
    em = bpy.context.object
    em.name = 'Emisor de gotas ' + o.name.replace('Boquilla ', '')
    # quedarse con la mitad de abajo (las gotas salen hacia los lados y hacia abajo, como sombrilla)
    me = em.data
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > -0.003], context='VERTS')
    bm.to_mesh(me)
    bm.free()
    for c in list(em.users_collection):
        c.objects.unlink(em)
    col.objects.link(em)
    ps = em.modifiers.new('rocio', 'PARTICLE_SYSTEM').particle_system
    st = ps.settings
    st.name = 'Rocio del microaspersor'
    st.count = 9000
    st.frame_start, st.frame_end = F_INI, F_FIN
    st.lifetime = 40
    st.lifetime_random = 0.3
    st.emit_from = 'FACE'
    st.normal_factor = 1.05               # m/s hacia afuera (sombrilla)
    st.factor_random = 0.35
    st.tangent_factor = 0.15
    st.physics_type = 'NEWTON'
    st.mass = 0.001
    st.use_die_on_collision = True
    st.render_type = 'OBJECT'
    st.instance_object = gota
    st.particle_size = 1.0
    st.size_random = 0.5
    st.use_rotations = True
    st.rotation_mode = 'VEL'
    st.use_dynamic_rotation = False
    st.display_method = 'DOT'
    em.show_instancer_for_render = False         # la media esfera no se ve, solo sus gotas (hide_render ocultaría también las gotas)
    ps.seed = len(emisores) * 17 + 3
    emisores.append(em)
print('EMISORES', len(emisores))

# ------------------------------------------------------------------ el sustrato se oscurece al mojarse
sus = bpy.data.objects.get('Sustrato')
if sus and sus.data.materials:
    m = sus.data.materials[0].copy()
    m.name = 'Sustrato (se moja)'
    sus.data.materials[0] = m
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    entrada = bsdf.inputs['Base Color']
    mezcla = nt.nodes.new('ShaderNodeMixRGB')
    mezcla.blend_type = 'MULTIPLY'
    mezcla.inputs['Fac'].default_value = 1.0
    if entrada.is_linked:
        nt.links.new(entrada.links[0].from_socket, mezcla.inputs['Color1'])
    else:
        mezcla.inputs['Color1'].default_value = entrada.default_value
    nt.links.new(mezcla.outputs['Color'], entrada)
    c2 = mezcla.inputs['Color2']
    c2.default_value = (1, 1, 1, 1)
    c2.keyframe_insert('default_value', frame=F_INI + 15)
    c2.default_value = (0.5, 0.48, 0.47, 1)
    c2.keyframe_insert('default_value', frame=F_FIN - 40)
    rough = bsdf.inputs['Roughness']
    r0 = rough.default_value
    rough.keyframe_insert('default_value', frame=F_INI + 15)
    rough.default_value = max(0.35, r0 - 0.35)
    rough.keyframe_insert('default_value', frame=F_FIN - 40)

# ------------------------------------------------------------------ cámara
obj = bpy.data.objects.new('Objetivo video riego', None)
col.objects.link(obj)
cd = bpy.data.cameras.new('Camara video riego')
cam = bpy.data.objects.new('Camara video riego', cd)
col.objects.link(cam)
cd.clip_start = 0.01
tr = cam.constraints.new('TRACK_TO')
tr.target = obj
tr.track_axis, tr.up_axis = 'TRACK_NEGATIVE_Z', 'UP_Y'
ruta = [
    (1, (2.3, -2.4, 1.55), (0.0, 0.0, 0.85), 28),
    (90, (1.55, -1.6, 1.3), (0.0, 0.0, 0.9), 30),
    (170, (0.8, -0.95, 1.05), (0.05, 0.0, 1.25), 26),      # mirando los aspersores desde abajo-afuera
    (240, (-0.9, -1.1, 1.0), (0.0, 0.05, 1.0), 26),
    (330, (-2.0, 0.9, 1.5), (0.0, 0.0, 0.8), 28),
]
for f, pc, po, lente in ruta:
    cam.location, obj.location, cd.lens = pc, po, lente
    cam.keyframe_insert('location', frame=f)
    obj.keyframe_insert('location', frame=f)
    cd.keyframe_insert('lens', frame=f)
for o in (cam, obj):
    for fc in o.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = 'BEZIER'
            k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'
sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

# ------------------------------------------------------------------ simular las gotas cuadro por cuadro (llena la caché)
sc.frame_set(F0)
bpy.ops.ptcache.bake_all(bake=True)      # el render usa la caché horneada (si no, cada cuadro vuelve a empezar)
print('SIMULADO (horneado)')

# cuadros de revisión
sc.eevee.taa_render_samples = 48
sc.render.image_settings.file_format = 'PNG'
for f in (60, 170, 260):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(REN, 'riego_cuadro_%03d.png' % f)
    bpy.ops.render.render(write_still=True)
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

if VIDEO:
    sc.eevee.taa_render_samples = 24
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'NONE'
    sc.render.ffmpeg.video_bitrate = 9000
    sc.render.ffmpeg.maxrate = 12000
    sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
    sc.render.filepath = os.path.join(DIR, 'video', 'AquaHuerto_riego_')
    bpy.ops.render.render(animation=True)
print('RIEGO_OK', NUEVO)
