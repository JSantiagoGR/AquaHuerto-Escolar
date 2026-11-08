"""Video: la cámara se acerca a las cajas, se abren una por una y se ve el interior.
No modifica AquaHuerto_cajas_abiertas.blend: guarda la versión del video como AquaHuerto_cajas_video.blend.
Ejecutar: blender -b -P video_cajas.py -- <carpeta_modelos_3D>"""
import math
import os
import sys

import bpy
from mathutils import Vector

DIR = sys.argv[sys.argv.index('--') + 1:][0]
bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_cajas_abiertas.blend'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_cajas_video.blend'))
sc = bpy.context.scene


def suave(o):
    for fc in o.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = 'BEZIER'
            k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'


# ------------------------------------------------------------------ tapas: se abren cuando la cámara llega a cada caja
orden = ['Caja de la bomba', 'Caja del caudalimetro', 'Caja de la electrovalvula']
inicios = [112, 188, 258]
for nombre, f0 in zip(orden, inicios):
    t = bpy.data.objects[f'{nombre} - tapa (parte superior)']
    t.animation_data_clear()
    t.location, t.rotation_euler = (0, 0, 0), (0, 0, 0)
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
    suave(t)

# ------------------------------------------------------------------ cámara del recorrido
obj = bpy.data.objects.new('Objetivo video cajas', None)
sc.collection.objects.link(obj)
bpy.ops.object.camera_add(location=(6.5, 4.5, 3.6))
cam = bpy.context.object
cam.name = 'Camara video cajas'
cam.data.lens = 26
tr = cam.constraints.new('TRACK_TO')
tr.target = obj
tr.track_axis = 'TRACK_NEGATIVE_Z'
tr.up_axis = 'UP_Y'
ruta = [
    (1, (6.5, 4.5, 3.6), (0.0, -1.7, 0.8)),
    (60, (2.2, 0.4, 1.7), (0.0, -1.6, 0.15)),
    (95, (0.8, -1.0, 0.75), (0.0, -1.68, 0.05)),
    (110, (0.36, -1.74, 0.38), (0.03, -1.98, 0.06)),       # bomba
    (172, (0.3, -1.8, 0.3), (0.03, -1.98, 0.055)),
    (186, (0.2, -1.45, 0.31), (0.0, -1.6, 0.04)),           # caudalímetro
    (246, (0.15, -1.48, 0.27), (0.0, -1.6, 0.04)),
    (258, (0.15, -1.12, 0.33), (0.0, -1.27, 0.06)),         # electroválvula
    (318, (0.12, -1.16, 0.3), (0.0, -1.27, 0.06)),
    (360, (0.85, -0.95, 0.72), (0.0, -1.68, 0.04)),         # las tres abiertas
    (420, (3.4, 1.2, 2.2), (0.0, -1.9, 0.35)),
]
for f, pc, po in ruta:
    cam.location, obj.location = pc, po
    cam.keyframe_insert('location', frame=f)
    obj.keyframe_insert('location', frame=f)
suave(cam)
suave(obj)
cam.data.lens = 26
cam.data.keyframe_insert('lens', frame=95)
cam.data.lens = 32
cam.data.keyframe_insert('lens', frame=110)
cam.data.keyframe_insert('lens', frame=318)
cam.data.lens = 26
cam.data.keyframe_insert('lens', frame=360)

sc.camera = cam
sc.frame_start, sc.frame_end = 1, 420
sc.render.fps = 30
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.eevee.taa_render_samples = 24
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_cajas_video.blend'))

os.makedirs(os.path.join(DIR, 'video'), exist_ok=True)
sc.render.image_settings.file_format = 'FFMPEG'
sc.render.ffmpeg.format = 'MPEG4'
sc.render.ffmpeg.codec = 'H264'
sc.render.ffmpeg.constant_rate_factor = 'NONE'
sc.render.ffmpeg.video_bitrate = 7000
sc.render.ffmpeg.maxrate = 9000
sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
sc.render.filepath = os.path.join(DIR, 'video', 'AquaHuerto_cajas_por_dentro_')
bpy.ops.render.render(animation=True)
print('VIDEO_CAJAS_OK')
