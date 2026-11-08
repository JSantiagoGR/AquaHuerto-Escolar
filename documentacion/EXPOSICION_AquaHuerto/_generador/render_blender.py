"""Render de los modelos 3D con Blender (ejecutar: blender -b -P render_blender.py -- <carpeta_STL> <carpeta_salida>)."""
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
STL, OUT = args[0], args[1]
os.makedirs(OUT, exist_ok=True)


def limpiar():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def material(nombre, col, metal=0.0, rough=0.5):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    m.diffuse_color = (*col, 1)
    return m


def importar(path, col, metal=0.0):
    bpy.ops.import_mesh.stl(filepath=path, global_scale=0.001)
    o = bpy.context.selected_objects[0]
    o.data.materials.append(material(os.path.basename(path), col, metal))
    bpy.ops.object.shade_flat()
    return o


def escena(objs, nombre, dist=1.0, elev=28, azim=-50, res=(1800, 1200)):
    mn = Vector((min(v[0] for o in objs for v in o.bound_box), min(v[1] for o in objs for v in o.bound_box),
                 min(v[2] for o in objs for v in o.bound_box)))
    mx = Vector((max(v[0] for o in objs for v in o.bound_box), max(v[1] for o in objs for v in o.bound_box),
                 max(v[2] for o in objs for v in o.bound_box)))
    c = (mn + mx) / 2
    r = (mx - mn).length
    bpy.ops.mesh.primitive_plane_add(size=r * 6, location=(c.x, c.y, mn.z - 0.001))
    piso = bpy.context.object
    piso.data.materials.append(material('piso', (0.93, 0.94, 0.93), 0, 0.9))
    e, a = math.radians(elev), math.radians(azim)
    d = r * 1.25 * dist
    pos = c + Vector((d * math.cos(e) * math.cos(a), d * math.cos(e) * math.sin(a), d * math.sin(e)))
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.rotation_euler = (c - pos).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 40
    bpy.context.scene.camera = cam
    bpy.ops.object.light_add(type='SUN', location=(c.x, c.y, c.z + 5))
    sun = bpy.context.object
    sun.rotation_euler = (math.radians(40), math.radians(10), math.radians(-30))
    sun.data.energy = 3.5
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.eevee.use_soft_shadows = True
    sc.eevee.use_gtao = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    w = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.95, 0.97, 1.0, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
    sc.view_settings.view_transform = 'Standard'
    sc.render.filepath = os.path.join(OUT, nombre + '.png')
    bpy.ops.render.render(write_still=True)


ACERO = (0.62, 0.64, 0.68)
piezas = [('Base_del_huerto', ACERO, 0.6, 1.0, 30, -50), ('Base_del_tinaco', ACERO, 0.6, 1.0, 30, -50),
          ('Soporte_del_panel_solar', ACERO, 0.6, 1.0, 25, -60), ('Cajon_de_cultivo', (0.76, 0.6, 0.42), 0, 1.0, 30, -50),
          ('Tinaco', (0.12, 0.12, 0.13), 0, 1.1, 20, -50)]
for n, col, met, dist, el, az in piezas:
    limpiar()
    o = importar(os.path.join(STL, n + '.stl'), col, met)
    escena([o], 'render_' + n, dist, el, az)

limpiar()
objs = []
with open(os.path.join(STL, 'ensamble', 'colores.txt')) as f:
    for line in f:
        n, r, g, b = line.split()
        met = 0.6 if n.startswith(('base', 'soporte')) else 0.0
        objs.append(importar(os.path.join(STL, 'ensamble', n + '.stl'), (float(r), float(g), float(b)), met))
escena(objs, 'render_Ensamble_AquaHuerto', 0.85, 28, -55, (2400, 1500))
escena(objs, 'render_Ensamble_AquaHuerto_vista2', 0.85, 35, 35, (2400, 1500))
