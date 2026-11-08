"""Saca cuadros de un video para revisarlo: blender -b -P cuadros_video.py -- <video> <carpeta> <f1,f2,...>"""
import os
import sys

import bpy

ent, sal, lista = sys.argv[sys.argv.index('--') + 1:][:3]
os.makedirs(sal, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.sequence_editor_create()
sc.sequence_editor.sequences.new_movie('v', ent, channel=1, frame_start=1)
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.image_settings.file_format = 'JPEG'
for f in [int(x) for x in lista.split(',')]:
    sc.frame_set(f)
    sc.render.filepath = os.path.join(sal, 'f_%03d.jpg' % f)
    bpy.ops.render.render(write_still=True)
