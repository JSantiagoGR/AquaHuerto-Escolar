"""Escena completa de AquaHuerto en Blender, basada en las fotos de la instalación real.

Ejecutar: blender -b -P escena_blender.py -- <carpeta_modelos_3D>
Guarda AquaHuerto_instalacion.blend y renders en <carpeta>/renders.
Unidades: metros. El cajón está en el origen; el tinaco y la pared quedan hacia -Y.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
DIR = args[0]
REN = os.path.join(DIR, 'renders')
os.makedirs(REN, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
MATS = {}


def mat(nombre, col, rough=0.6, metal=0.0, alpha=1.0):
    if nombre in MATS:
        return MATS[nombre]
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
        m.blend_method = 'BLEND'
    m.diffuse_color = (*col, alpha)
    MATS[nombre] = m
    return m


def coleccion(nombre):
    c = bpy.data.collections.new(nombre)
    sc.collection.children.link(c)
    return c


def mover(o, col):
    for c in o.users_collection:
        c.objects.unlink(o)
    col.objects.link(o)
    return o


def caja(nombre, centro, dims, m, col, bisel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centro)
    o = bpy.context.object
    o.name = nombre
    o.scale = dims
    bpy.ops.object.transform_apply(scale=True)
    if bisel:
        md = o.modifiers.new('bisel', 'BEVEL')
        md.width = bisel
        md.segments = 2
    o.data.materials.append(m)
    return mover(o, col)


def cil(nombre, p1, p2, r, m, col, verts=24):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, vertices=verts, location=(p1 + p2) / 2)
    o = bpy.context.object
    o.name = nombre
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return mover(o, col)


def tubo(nombre, puntos, r, m, col, suave=True):
    cu = bpy.data.curves.new(nombre, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    if suave:
        # curva suave (Catmull-Rom) muestreada; nunca baja del piso: el tubo queda apoyado encima
        piso = 0.02 + r
        pts = [Vector(p) for p in puntos]
        ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
        muestras = []
        for i in range(1, len(ext) - 2):
            p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
            n = max(4, int((p2 - p1).length / 0.03))
            for k in range(n):
                t = k / n
                q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                           (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)
                muestras.append(q)
        muestras.append(pts[-1])
        sp = cu.splines.new('POLY')
        sp.points.add(len(muestras) - 1)
        for pt, q in zip(sp.points, muestras):
            pt.co = (q.x, q.y, max(q.z, piso), 1)
    else:
        sp = cu.splines.new('POLY')
        sp.points.add(len(puntos) - 1)
        for pt, p in zip(sp.points, puntos):
            pt.co = (*p, 1)
    o = bpy.data.objects.new(nombre, cu)
    o.data.materials.append(m)
    col.objects.link(o)
    return o


def importar_stl(path, nombre, m, col, loc):
    bpy.ops.import_mesh.stl(filepath=path, global_scale=0.001)
    o = bpy.context.selected_objects[0]
    o.name = nombre
    o.location = loc
    o.data.materials.append(m)
    return mover(o, col)


# ------------------------------------------------------------------ materiales
MADERA = mat('Madera pino', (0.62, 0.42, 0.17), 0.7)
ACERO = mat('Acero PTR', (0.18, 0.18, 0.2), 0.45, 0.7)
SUELO = mat('Tierra', (0.25, 0.17, 0.11), 0.95)
PASTO = mat('Pasto', (0.16, 0.3, 0.08), 0.95)
SUSTRATO = mat('Sustrato', (0.17, 0.12, 0.09), 1.0)
MALLA = mat('Malla antimaleza', (0.05, 0.05, 0.05), 0.9)
VERDE = mat('Tuboplus verde', (0.03, 0.32, 0.12), 0.35)
AZUL = mat('Manguera azul', (0.02, 0.15, 0.7), 0.35)
NEGRO = mat('Plastico negro', (0.03, 0.03, 0.035), 0.4)
NARANJA = mat('Poliducto naranja', (0.9, 0.18, 0.02), 0.5)
GRIS = mat('Caja gris', (0.42, 0.43, 0.43), 0.5)
BLANCO = mat('Gabinete blanco', (0.9, 0.9, 0.88), 0.4)
ROJO = mat('Aspersor rojo', (0.85, 0.1, 0.1), 0.4)
BRONCE = mat('Bronce', (0.45, 0.38, 0.28), 0.4, 0.8)
METAL = mat('Metal brillante', (0.75, 0.75, 0.78), 0.25, 1.0)
PARED_B = mat('Pared blanca', (0.7, 0.69, 0.64), 0.9)
PARED_A = mat('Pared azul', (0.04, 0.22, 0.35), 0.85)
TECHO = mat('Losa', (0.78, 0.77, 0.73), 0.9)
PANEL = mat('Celdas solares', (0.05, 0.1, 0.25), 0.15, 0.3)
MARCO = mat('Aluminio', (0.8, 0.8, 0.82), 0.3, 1.0)
ACRILICO = mat('Acrilico', (0.85, 0.92, 0.95), 0.05, 0.0, 0.45)
TRIPLAY = mat('Triplay', (0.75, 0.6, 0.38), 0.8)
PING = mat('Tarjeta PING', (0.05, 0.2, 0.55), 0.4)

C_ENT = coleccion('Entorno')
C_CAJ = coleccion('Cajon y estructura')
C_HID = coleccion('Hidraulica')
C_ELE = coleccion('Electrica y control')
C_TIN = coleccion('Tinaco')

# ------------------------------------------------------------------ entorno
bpy.ops.mesh.primitive_plane_add(size=16, location=(0.5, -1.5, 0))
mover(bpy.context.object, C_ENT).data.materials.append(SUELO)
bpy.context.object.name = 'Piso de tierra'
bpy.ops.mesh.primitive_plane_add(size=1, location=(1.8, 1.5, 0.002))
g = bpy.context.object
g.scale = (6, 5, 1)
g.name = 'Pasto'
g.data.materials.append(PASTO)
mover(g, C_ENT)
caja('Banqueta', (0.5, -2.95, 0.009), (7.0, 0.6, 0.018), mat('Concreto', (0.6, 0.58, 0.55), 0.9), C_ENT)
# pared y techo del edificio
caja('Pared (parte azul)', (0.5, -4.1, 0.45), (7.0, 0.22, 0.9), PARED_A, C_ENT)
caja('Pared (block)', (0.5, -4.1, 1.75), (7.0, 0.22, 1.7), PARED_B, C_ENT)
caja('Losa del techo', (0.5, -4.6, 2.67), (7.4, 1.4, 0.14), TECHO, C_ENT)

# ------------------------------------------------------------------ cajón sobre base metálica
base = importar_stl(os.path.join(DIR, 'STL', 'Base_del_huerto.stl'), 'Base metalica del huerto', ACERO, C_CAJ, (-0.6, -0.6, 0))
L, e = 1.10, 0.04
for i, z in enumerate((0.22, 0.42)):
    caja(f'Tabla frente {i + 1}', (0, -L / 2 + e / 2, z), (L, e, 0.195), MADERA, C_CAJ, 0.004)
    caja(f'Tabla atras {i + 1}', (0, L / 2 - e / 2, z), (L, e, 0.195), MADERA, C_CAJ, 0.004)
    caja(f'Tabla izquierda {i + 1}', (-L / 2 + e / 2, 0, z), (e, L - 2 * e, 0.195), MADERA, C_CAJ, 0.004)
    caja(f'Tabla derecha {i + 1}', (L / 2 - e / 2, 0, z), (e, L - 2 * e, 0.195), MADERA, C_CAJ, 0.004)
caja('Fondo del cajon', (0, 0, 0.13), (L, L, 0.02), MADERA, C_CAJ)
caja('Sustrato', (0, 0, 0.3), (L - 2 * e, L - 2 * e, 0.34), SUSTRATO, C_CAJ)
# postes y marco superior (madera 2x2")
P, H = 0.48, 1.55
for sx in (-1, 1):
    for sy in (-1, 1):
        caja(f'Poste {sx:+d}{sy:+d}', (sx * P, sy * P, (0.15 + H) / 2), (0.045, 0.045, H - 0.15), MADERA, C_CAJ, 0.003)
for sy in (-1, 1):
    caja(f'Larguero superior {"frente" if sy < 0 else "atras"}', (0, sy * P, H - 0.02), (2 * P + 0.045, 0.045, 0.045), MADERA, C_CAJ, 0.003)
for sx in (-1, 1):
    caja(f'Larguero lateral {sx:+d}', (sx * P, 0, H + 0.025), (0.045, 2 * P + 0.045, 0.045), MADERA, C_CAJ, 0.003)
caja('Larguero central', (0, 0, H + 0.025), (0.045, 2 * P + 0.045, 0.045), MADERA, C_CAJ, 0.003)

# ------------------------------------------------------------------ distribución en la parte alta
ZM = H - 0.075
cil('Tuboplus frente (cruz a laterales)', (-0.33, -P - 0.04, ZM), (0.33, -P - 0.04, ZM), 0.0125, VERDE, C_HID)
caja('T de Tuboplus', (0, -P - 0.04, ZM), (0.05, 0.05, 0.05), VERDE, C_HID, 0.01)
for x in (-0.33, 0.0, 0.33):
    cil(f'Codo a lateral {x:+.2f}', (x, -P - 0.04, ZM), (x, -P + 0.02, ZM), 0.0135, VERDE, C_HID)
    tubo(f'Manguera lateral {x:+.2f}', [(x, -P + 0.02, ZM), (x, P - 0.02, ZM)], 0.008, NEGRO, C_HID, suave=False)
    for y in (-0.33, 0.0, 0.33):
        cil(f'Microaspersor {x:+.2f} {y:+.2f}', (x, y, ZM - 0.008), (x, y, ZM - 0.06), 0.008, ROJO, C_HID, 12)
        cil(f'Boquilla {x:+.2f} {y:+.2f}', (x, y, ZM - 0.06), (x, y, ZM - 0.075), 0.013, ROJO, C_HID, 12)

# subida: manguera azul por el frente del cajón hasta la T
Y0 = -L / 2 - 0.03
tubo('Subida (manguera azul)', [(0, -0.85, 0.03), (0, Y0 - 0.06, 0.06), (0, Y0, 0.25), (0, Y0, 0.55), (0, -P - 0.06, 1.0),
                                (0, -P - 0.04, ZM - 0.03)], 0.011, AZUL, C_HID)

# ------------------------------------------------------------------ línea en el piso: tinaco -> filtro -> cajas -> cajón
TY = -3.75            # centro del tinaco
R = 0.45
YT = TY + R            # frente del tinaco
ZP = 0.035
caja('Malla antimaleza', (0, -1.55, 0.004), (0.85, 1.75, 0.006), MALLA, C_HID)
caja('Triplay bajo la bomba', (0.05, -2.3, 0.01), (0.55, 0.28, 0.015), TRIPLAY, C_HID)
cil('Tubo verde al cajon', (0, -0.85, ZP), (0, -1.12, ZP), 0.0125, VERDE, C_HID)
caja('Caja gris pequena (valvula)', (0, -1.27, 0.075), (0.2, 0.28, 0.13), GRIS, C_HID, 0.006)
for dy in (-0.11, 0.11):
    caja('Soporte', (0, -1.27 + dy, 0.02), (0.27, 0.035, 0.03), GRIS, C_HID)
caja('Caja negra (caudalimetro)', (0, -1.6, 0.06), (0.18, 0.24, 0.1), NEGRO, C_HID, 0.004)
for dy in (-0.1, 0.1):
    caja('Soporte negro', (0, -1.6 + dy, 0.015), (0.25, 0.03, 0.025), NEGRO, C_HID)
caja('Caja gris grande (bomba)', (0, -1.98, 0.075), (0.3, 0.36, 0.13), GRIS, C_HID, 0.006)
cil('Tubo entre cajas 1', (0, -1.41, ZP), (0, -1.48, ZP), 0.0125, VERDE, C_HID)
cil('Tubo entre cajas 2', (0, -1.72, ZP), (0, -1.8, ZP), 0.0125, VERDE, C_HID)
cil('Codo salida bomba', (0.05, -2.16, ZP), (0.05, -2.24, ZP), 0.015, VERDE, C_HID)
cil('Tubo a filtro', (0.05, -2.24, ZP), (0.05, -2.48, ZP), 0.0125, VERDE, C_HID)
cil('Union verde', (0.05, -2.3, ZP), (0.05, -2.38, ZP), 0.019, VERDE, C_HID)
cil('Filtro Y (bronce)', (0.05, -2.5, ZP), (0.05, -2.62, ZP), 0.02, BRONCE, C_HID)
cil('Filtro Y (canastilla)', (0.05, -2.56, ZP), (0.05, -2.53, ZP - 0.05), 0.014, BRONCE, C_HID)
cil('Tubo a valvula', (0.05, -2.62, ZP), (0.05, -2.95, ZP), 0.0125, VERDE, C_HID)
cil('Valvula de esfera', (0.05, -2.98, ZP), (0.05, -3.07, ZP), 0.017, METAL, C_HID)
caja('Manija azul', (0.08, -3.02, ZP + 0.03), (0.07, 0.02, 0.01), AZUL, C_HID)
cil('Niple al tinaco', (0.05, -3.07, ZP), (0.05, YT + 0.02, 0.06), 0.016, NEGRO, C_HID)

# ------------------------------------------------------------------ tinaco
cil('Tinaco', (0, TY, 0.06), (0, TY, 1.16), R, NEGRO, C_TIN, 48)
bpy.ops.mesh.primitive_uv_sphere_add(radius=R, location=(0, TY, 1.16), segments=48, ring_count=24)
dom = bpy.context.object
dom.name = 'Tapa del tinaco (domo)'
dom.scale = (1, 1, 0.22)
dom.data.materials.append(NEGRO)
bpy.ops.object.shade_smooth()
mover(dom, C_TIN)
cil('Tapa', (0, TY, 1.24), (0, TY, 1.27), 0.2, NEGRO, C_TIN, 40)
caja('Caja acrilica del sensor', (0, TY, 1.31), (0.1, 0.08, 0.06), ACRILICO, C_TIN)
caja('Sensor PING', (0, TY, 1.29), (0.045, 0.02, 0.012), PING, C_TIN)
for sx in (-1, 1):
    caja(f'Marco del tinaco {sx:+d}', (sx * 0.5, TY, 0.03), (0.04, 1.05, 0.04), ACERO, C_TIN)
for sy in (-1, 1):
    caja(f'Travesano del tinaco {sy:+d}', (0, TY + sy * 0.5, 0.03), (1.04, 0.04, 0.04), ACERO, C_TIN)

# ------------------------------------------------------------------ eléctrico: gabinete, poliductos y panel
GX, GZ = -0.95, 1.45          # gabinete a la derecha del tinaco (visto desde el huerto), como en la foto
caja('Gabinete (ESP32, bateria, reles)', (GX, -3.95, GZ), (0.32, 0.12, 0.3), BLANCO, C_ELE, 0.008)
# 3 poliductos: bajan por la pared, siguen junto al costado derecho del tinaco y van por el lado izquierdo de la tubería
for i, dx in enumerate((-0.04, 0.0, 0.04)):
    tubo(f'Poliducto a cajas y cajon {i + 1}', [(GX + dx, -3.97, GZ - 0.16), (GX + dx, -3.97, 0.95), (-0.72 + dx, -3.93, 0.45),
                                                 (-0.64 + dx, -3.6, 0.03), (-0.6 + dx, -3.1, 0.03), (-0.32 + dx, -2.45, 0.03),
                                                 (-0.24 + dx, -1.5, 0.02)],
         0.011, NARANJA, C_ELE)
tubo('Poliducto a la caja grande', [(-0.2, -1.5, 0.02), (-0.2, -1.85, 0.05), (-0.15, -1.98, 0.08)], 0.009, NARANJA, C_ELE)
tubo('Poliducto al cajon (EC-5)', [(-0.26, -1.5, 0.02), (-0.12, -0.9, 0.03), (-0.06, -0.64, 0.06), (-0.05, Y0, 0.3), (-0.06, -0.5, 0.52),
                                   (-0.15, -0.3, 0.5)], 0.009, NARANJA, C_ELE)
# panel solar en el techo, encima del tinaco, inclinado 30 grados hacia +X (hacia el sol, como en la foto)
PX, PY, PZ = -0.15, -4.3, 2.74
tubo('Poliducto al panel solar', [(GX + 0.08, -3.97, GZ + 0.15), (GX + 0.25, -3.97, 1.9), (-0.45, -3.97, 2.45), (-0.4, -3.95, 2.62),
                                  (-0.42, -4.05, 2.77), (-0.45, -4.4, 2.78)], 0.01, NARANJA, C_ELE)
tubo('Cable del sensor de nivel', [(-0.05, TY, 1.31), (-0.3, -3.9, 1.32), (-0.6, -3.94, 1.42), (GX + 0.16, -3.96, GZ + 0.05)],
     0.006, NARANJA, C_ELE)
sop = importar_stl(os.path.join(DIR, 'STL', 'Soporte_del_panel_solar.stl'), 'Soporte del panel solar', MARCO, C_ELE, (0, 0, 0))
sop.rotation_euler = (0, 0, math.radians(180))      # lado alto hacia -X, el panel mira hacia +X
sop.location = (PX, PY, PZ)
L1 = 0.68 * math.cos(math.radians(30))
caja('Panel solar FE-50WP', (0, 0, 0), (0.68, 0.62, 0.03), PANEL, C_ELE)
pan = bpy.context.object
pan.rotation_euler = (0, math.radians(30), 0)
pan.location = (PX - L1 / 2, PY - 0.31, PZ + 0.68 * math.sin(math.radians(30)) / 2 + 0.035)
caja('Marco del panel', (0, 0, 0), (0.7, 0.64, 0.025), MARCO, C_ELE)
mf = bpy.context.object
mf.rotation_euler = pan.rotation_euler
mf.location = pan.location - Vector((0, 0, 0.014))

# ------------------------------------------------------------------ luces, cámara y render
bpy.ops.object.light_add(type='SUN', location=(3, 3, 6))
sun = bpy.context.object
sun.data.energy = 3.2
sun.data.angle = math.radians(3)
sun.rotation_euler = (math.radians(50), math.radians(8), math.radians(150))
w = bpy.data.worlds.new('Cielo')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.55, 0.72, 0.95, 1)
bg.inputs['Strength'].default_value = 0.6
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.use_soft_shadows = True
sc.eevee.use_gtao = True
sc.eevee.gtao_distance = 0.5
sc.eevee.shadow_cascade_size = '4096'
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x, sc.render.resolution_y = 2000, 1300


def camara(nombre, pos, mira, lente=30):
    bpy.ops.object.camera_add(location=pos)
    c = bpy.context.object
    c.name = nombre
    c.rotation_euler = (Vector(mira) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    c.data.lens = lente
    return c


vistas = [
    camara('Camara general', (4.2, 2.3, 3.4), (0.2, -2.0, 0.9), 22),
    camara('Camara cajon', (1.7, -1.8, 1.9), (0.0, 0.0, 0.85), 28),
    camara('Camara linea', (1.25, -1.1, 1.35), (0.0, -2.2, 0.15), 30),
    camara('Camara tinaco y pared', (0.6, -0.6, 1.9), (-0.4, -3.9, 1.6), 24),
]
sc.camera = vistas[0]
blend = os.path.join(DIR, 'AquaHuerto_instalacion.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend)
for c in vistas:
    sc.camera = c
    sc.render.filepath = os.path.join(REN, 'blender_' + c.name.replace(' ', '_') + '.png')
    bpy.ops.render.render(write_still=True)
sc.camera = vistas[0]
bpy.ops.wm.save_as_mainfile(filepath=blend)
print('ESCENA_OK', blend)
