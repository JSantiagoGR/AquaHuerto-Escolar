"""Cambia el módulo de 2 relevadores hecho a mano por el modelo 3D real descargado (Soldered Electronics, relés SONGLE
SRD-05VDC-SL-C, archivo STEP convertido a .glb con step_a_gltf.py).

Abre AquaHuerto_gabinete_tinaco_panel.blend (sin modificarlo) y guarda AquaHuerto_gabinete_real.blend.
Ejecutar: blender -b -P escena_gabinete_real.py -- <carpeta_modelos_3D> [--video]
"""
import os
import sys

import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
DIR = args[0]
VIDEO = '--video' in args
NUEVO = os.path.join(DIR, 'AquaHuerto_gabinete_real.blend')
REN = os.path.join(DIR, 'renders')
GLB = os.path.join(DIR, 'descargas', 'rele_soldered', 'rele_2canales.glb')
bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_gabinete_tinaco_panel.blend'))
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
sc = bpy.context.scene

# ------------------------------------------------------------------ quitar el módulo de relés simplificado
for o in list(bpy.data.objects):
    if o.name.split('.')[0] in ('Modulo 2 reles (PCB azul)', 'Rele SRD-05VDC', 'Borneras de los reles', 'Pines de entrada',
                                'LED rele'):
        bpy.data.objects.remove(o, do_unlink=True)

# ------------------------------------------------------------------ importar el modelo real
col = bpy.data.collections['Gabinete y sensor del tinaco']
antes = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
nuevos = [o for o in bpy.data.objects if o not in antes]
raiz = [o for o in nuevos if o.parent is None][0]
raiz.name = 'Modulo 2 reles SONGLE (modelo real Soldered)'
for o in nuevos:
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)

# El modelo trae la placa en el plano XZ con los componentes hacia -Y (lado largo de 54 mm en X).
# En el gabinete: lado largo vertical (borneras abajo, pines de entrada arriba) y componentes hacia afuera (+Y).
GX, GZ, YB = -0.95, 1.45, -3.99
ru, rv = -0.063, 0.038


def P(u, v, w):
    return Vector((GX - u, YB + w, GZ + v))


R = Matrix(((0, 0, 1), (0, -1, 0), (1, 0, 0))).to_4x4()         # columnas: X->Z, Y->-Y, Z->X
centro_local = Vector((0.027, 0.0, 0.019))
T = P(ru, rv, 0.03) - (R.to_3x3() @ centro_local)
raiz.matrix_world = Matrix.Translation(T) @ R

# placa azul como la del módulo que usan; relés con un poco de brillo de plástico
for o in nuevos:
    if o.type != 'MESH':
        continue
    for m in o.data.materials:
        if not (m and m.use_nodes and 'Principled BSDF' in m.node_tree.nodes):
            continue
        b = m.node_tree.nodes['Principled BSDF']
        if m.name == 'mat_16':
            m.name = 'Rele real - PCB azul'
            b.inputs['Base Color'].default_value = (0.03, 0.15, 0.45, 1)
            b.inputs['Roughness'].default_value = 0.4
        elif m.name == 'mat_9':
            m.name = 'Rele real - plastico azul SONGLE'
            b.inputs['Base Color'].default_value = (0.02, 0.1, 0.75, 1)
            b.inputs['Roughness'].default_value = 0.3
        elif m.name == 'mat_14':
            m.name = 'Rele real - bornera'
            b.inputs['Base Color'].default_value = (0.05, 0.2, 0.7, 1)
            b.inputs['Roughness'].default_value = 0.45
for o in nuevos:
    o.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

# ------------------------------------------------------------------ acercamiento y cuadros de revisión
sc.eevee.taa_render_samples = 48
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.image_settings.file_format = 'PNG'
cam_d = bpy.data.cameras.new('Camara reles reales')
cam = bpy.data.objects.new('Camara acercamiento reles reales', cam_d)
col.objects.link(cam)
cam_d.lens = 50
cam_d.clip_start = 0.005
objetivo = P(ru - 0.005, rv + 0.005, 0.04)
cam.location = objetivo + Vector((0.12, 0.26, 0.09))
cam.rotation_euler = (objetivo - cam.location).to_track_quat('-Z', 'Y').to_euler()
camara_video = sc.camera
sc.frame_set(200)               # tapa del gabinete ya quitada
sc.camera = cam
sc.render.filepath = os.path.join(REN, 'gabinete_reles_reales_acercamiento.png')
bpy.ops.render.render(write_still=True)
sc.camera = camara_video
for f in (165, 200):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(REN, 'gabinete_real_cuadro_%03d.png' % f)
    bpy.ops.render.render(write_still=True)
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
    sc.render.filepath = os.path.join(DIR, 'video', 'AquaHuerto_gabinete_reles_reales_')
    bpy.ops.render.render(animation=True)
print('GABINETE_REAL_OK', NUEVO)
