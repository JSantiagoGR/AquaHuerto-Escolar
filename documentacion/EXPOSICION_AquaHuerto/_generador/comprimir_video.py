"""Re-codifica el video del recorrido a un tamaño para correo (≈ 9 MB) y saca 4 cuadros de muestra.
Ejecutar: blender -b -P comprimir_video.py -- <video_entrada> <video_salida> <carpeta_cuadros>"""
import os
import sys

import bpy

ent, sal, cuadros = sys.argv[sys.argv.index('--') + 1:][:3]
os.makedirs(cuadros, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.sequence_editor_create()
st = sc.sequence_editor.sequences.new_movie('recorrido', ent, channel=1, frame_start=1)
sc.frame_start, sc.frame_end = 1, st.frame_final_duration
sc.render.fps = 30
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = 100
for f in (1, 70, 190, 300):
    sc.frame_set(f)
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.filepath = os.path.join(cuadros, 'cuadro_%03d.jpg' % f)
    bpy.ops.render.render(write_still=True)
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'FFMPEG'
sc.render.ffmpeg.format = 'MPEG4'
sc.render.ffmpeg.codec = 'H264'
sc.render.ffmpeg.constant_rate_factor = 'NONE'
sc.render.ffmpeg.video_bitrate = 5500
sc.render.ffmpeg.maxrate = 7000
sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
sc.render.filepath = sal
bpy.ops.render.render(animation=True)
print('COMPRIMIDO_OK')
