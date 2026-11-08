"""Video de los componentes recreados en 3D (~27 s): se quita la tapa del gabinete -> ESP32 con su placa de expansión ->
módulo de relevadores y WAGO -> controlador de carga PWM -> batería (etiqueta y terminales) -> tinaco: se abre la tapa y
se ve el sensor PING))) en su caja de acrílico.

Abre AquaHuerto_recorrido_completo.blend (sin modificarlo) y guarda AquaHuerto_componentes_video.blend.
Ejecutar: blender -b -P video_componentes.py -- <carpeta_modelos_3D> [--cuadros] [--video]
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
DIR = args[0]
CUADROS = '--cuadros' in args
VIDEO = '--video' in args
NUEVO = os.path.join(DIR, 'AquaHuerto_componentes_video.blend')
REN = os.path.join(DIR, 'renders')
bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_recorrido_completo.blend'))
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
sc = bpy.context.scene
F_FIN = 820
sc.frame_start, sc.frame_end = 1, F_FIN
sc.render.fps = 30
GX, GZ, YB = -0.95, 1.45, -3.99
TY, ZT = -3.45, 1.258 + 0.14


def P(u, v, w):
    return Vector((GX - u, YB + w, GZ + v))


def suave(o):
    for fc in o.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = 'BEZIER'
            k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'


# sin riego en este video: fuera gotas y cascadas (además el render es mucho más rápido)
for o in bpy.data.objects:
    for m in o.modifiers:
        if m.type == 'PARTICLE_SYSTEM':
            m.show_render = m.show_viewport = False
    if o.name.startswith('Cascada de agua'):
        o.hide_render = o.hide_viewport = True

# tapas: las cajas quedan cerradas; gabinete se abre al inicio y el tinaco al final
for nombre in ('Caja de la bomba', 'Caja del caudalimetro', 'Caja de la electrovalvula'):
    t = bpy.data.objects.get(f'{nombre} - tapa (parte superior)')
    if t:
        t.animation_data_clear()
        t.location, t.rotation_euler = (0, 0, 0), (0, 0, 0)

tg = bpy.data.objects['Gabinete - tapa']
tg.animation_data_clear()
tg.location, tg.rotation_euler = (0, 0, 0), (0, 0, 0)
tg.keyframe_insert('location', frame=1)
tg.keyframe_insert('location', frame=40)
tg.keyframe_insert('rotation_euler', frame=40)
tg.location = (0, 0.14, 0)
tg.keyframe_insert('location', frame=60)
tg.location = (-0.55, 0.3, -0.05)
tg.rotation_euler = (0, 0, math.radians(-25))
tg.keyframe_insert('location', frame=88)
tg.keyframe_insert('rotation_euler', frame=88)
suave(tg)

F_TAPA = 615
piv = bpy.data.objects['Tapa del tinaco (pivote)']
piv.animation_data_clear()
piv.location, piv.rotation_euler = (0, TY, ZT), (0, 0, 0)
piv.keyframe_insert('location', frame=1)
piv.keyframe_insert('location', frame=F_TAPA)
piv.keyframe_insert('rotation_euler', frame=F_TAPA)
piv.location = (0, TY, ZT + 0.32)
piv.keyframe_insert('location', frame=F_TAPA + 22)
piv.location = (0.12, TY + 0.25, ZT + 0.42)
piv.rotation_euler = (math.radians(150), 0, 0)
piv.keyframe_insert('location', frame=F_TAPA + 48)
piv.keyframe_insert('rotation_euler', frame=F_TAPA + 48)
suave(piv)

# ---------------------------------------------------------------- cámaras para el PING))) (relativas a la tapa abierta)
sc.frame_set(F_TAPA + 60)
bpy.context.view_layer.update()
pcb = bpy.data.objects['PING))) - tarjeta (PCB)']
r = piv.matrix_world.to_3x3().normalized()
n = (r @ Vector((0, 0, -1))).normalized()          # hacia donde miran los transductores
centro = sum((pcb.matrix_world @ Vector(c) for c in pcb.bound_box), Vector()) / 8
z1 = n
z2 = (n + 0.55 * (r @ Vector((-1, 0, 0)))).normalized()
PING_CARA = (tuple(centro + z1 * 0.14), tuple(centro))
PING_CAJA = (tuple(centro + z2 * 0.22), tuple(centro))

# ---------------------------------------------------------------- recorrido de la cámara
obj = bpy.data.objects.new('Objetivo componentes', None)
sc.collection.objects.link(obj)
cd = bpy.data.cameras.new('Camara componentes')
cd.clip_start = 0.003
cam = bpy.data.objects.new('Camara componentes', cd)
sc.collection.objects.link(cam)
trk = cam.constraints.new('TRACK_TO')
trk.target = obj
trk.track_axis, trk.up_axis = 'TRACK_NEGATIVE_Z', 'UP_Y'
E = (-0.084, 0.106)                                    # ESP32 sobre la placa de expansión (u, v)
ruta = [
    (1, P(0.35, 0.05, 1.25), P(0.0, 0.0, 0.08), 32),      # gabinete cerrado en la pared
    (40, P(0.12, 0.02, 0.85), P(0.0, 0.0, 0.06), 34),     # se quita la tapa
    (100, P(0.0, 0.0, 0.64), P(0.0, 0.0, 0.03), 36),      # todo el gabinete
    (150, P(E[0] + 0.01, E[1] - 0.035, 0.17), P(E[0], E[1], 0.035), 50),   # ESP32 + placa de expansión
    (200, P(E[0] - 0.03, E[1] - 0.05, 0.16), P(E[0], E[1], 0.035), 50),
    (245, P(-0.05, 0.0, 0.2), P(-0.064, 0.025, 0.03), 42),                 # relevadores y WAGO
    (290, P(-0.03, -0.01, 0.19), P(-0.064, 0.015, 0.03), 42),
    (340, P(-0.087, -0.093, 0.27), P(-0.087, -0.093, 0.035), 40),          # controlador PWM
    (390, P(-0.03, -0.17, 0.2), P(-0.087, -0.085, 0.035), 40),
    (440, P(0.085, 0.06, 0.36), P(0.085, 0.06, 0.07), 32),                 # batería
    (485, P(0.11, 0.06, 0.2), P(0.11, 0.06, 0.07), 30),                    # etiqueta
    (530, P(-0.03, -0.06, 0.2), P(0.045, -0.01, 0.04), 50),                # terminales
    (570, P(0.0, 0.0, 0.75), P(0.0, 0.0, 0.03), 34),                       # de vuelta al gabinete
    (615, Vector((0.55, -2.65, 2.2)), Vector((0.05, -3.4, 1.55)), 30),     # tinaco
    (665, Vector((0.5, -2.7, 2.15)), Vector((0.12, -3.15, 1.82)), 34),     # tapa abierta
    (720, Vector(PING_CAJA[0]), Vector(PING_CAJA[1]), 40),                 # PING))) en su caja de acrílico
    (770, Vector(PING_CARA[0]), Vector(PING_CARA[1]), 50),                 # transductores de frente
    (820, Vector(PING_CARA[0]), Vector(PING_CARA[1]), 46),
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
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

if CUADROS:
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.resolution_percentage = 50
    sc.eevee.taa_render_samples = 16
    for f in (1, 70, 100, 175, 265, 340, 390, 440, 485, 530, 615, 665, 720, 770):
        sc.frame_set(f)
        sc.render.filepath = os.path.join(REN, 'componentes_video_cuadro_%04d.jpg' % f)
        bpy.ops.render.render(write_still=True)
    sc.render.resolution_percentage = 100
if VIDEO:
    sc.eevee.taa_render_samples = 24
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'NONE'
    sc.render.ffmpeg.video_bitrate = 9000
    sc.render.ffmpeg.maxrate = 12000
    sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
    sc.render.filepath = os.path.join(DIR, 'video', 'AquaHuerto_componentes_')
    bpy.ops.render.render(animation=True)
sc.frame_set(1)
sc.render.image_settings.file_format = 'PNG'
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
print('COMPONENTES_VIDEO_OK', NUEVO)
