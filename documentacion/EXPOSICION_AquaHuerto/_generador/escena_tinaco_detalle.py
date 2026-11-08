"""Tinaco como en las fotos:
- tinaco hueco (pared de 6 mm) con boca abierta bajo la tapa y AGUA adentro (se ve al abrir la tapa);
- base de ángulo de fierro (café/oxidado) con patas, sobre la LOSA de concreto del patio;
- escalón: la losa termina después del tinaco y baja a la tierra donde están las cajas;
- salida del tinaco: adaptador blanco -> niple negro -> llave de esfera (manija azul) -> tubo verde -> filtro Y -> tubo verde
  -> codo que baja a la caja de la bomba.

Abre AquaHuerto_componentes_modelados.blend (sin modificarlo) y guarda AquaHuerto_tinaco_detalle.blend.
Ejecutar: blender -b -P escena_tinaco_detalle.py -- <carpeta_modelos_3D> [--video]
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
DIR = args[0]
VIDEO = '--video' in args
NUEVO = os.path.join(DIR, 'AquaHuerto_tinaco_detalle.blend')
REN = os.path.join(DIR, 'renders')
bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'AquaHuerto_componentes_modelados.blend'))
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)
sc = bpy.context.scene
sc.frame_set(1)

TY0 = -3.75                     # donde estaba el tinaco (atravesaba la pared en y=-3.99)
TY, R = -3.45, 0.45             # adelantado: la base queda junto a la pared sin atravesarla
DY = TY - TY0
LOSA = 0.10                     # alto de la losa de concreto del patio
Y_ESCALON = -2.55               # borde de la losa (después del tinaco baja a la tierra)
PATAS = 0.10                    # alto de la base de ángulo
ZB = LOSA + PATAS               # fondo del tinaco
DZ = ZB - 0.06                  # cuánto sube todo el tinaco respecto a la escena anterior
ZT_ANT = 1.258                  # boca anterior (donde asentaba la tapa)
ZBOCA = ZT_ANT + DZ
col_t = bpy.data.collections.get('Tinaco') or sc.collection


def borrar(*prefijos):
    for o in list(bpy.data.objects):
        if any(o.name == p or o.name.startswith(p + '.') for p in prefijos):
            bpy.data.objects.remove(o, do_unlink=True)


def mat(nombre, color, rough=0.5, metal=0.0):
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


def ligar(o, c=None):
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    (c or col_t).objects.link(o)
    return o


def caja(nombre, centro, dim, m, bisel=0.0, c=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centro)
    o = bpy.context.object
    o.name = nombre
    o.scale = dim
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bisel:
        md = o.modifiers.new('bisel', 'BEVEL')
        md.width, md.segments = bisel, 2
    o.data.materials.append(m)
    return ligar(o, c)


def cil(nombre, p1, p2, r, m, n=32, c=None):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=d.length, location=(p1 + p2) / 2)
    o = bpy.context.object
    o.name = nombre
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return ligar(o, c)


def esfera(nombre, p, r, m, c=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=p, segments=24, ring_count=12)
    o = bpy.context.object
    o.name = nombre
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return ligar(o, c)


NEGRO_T = bpy.data.materials.get('Plastico negro') or mat('Plastico negro', (0.02, 0.02, 0.02), 0.5)
CONCRETO = bpy.data.materials.get('Concreto') or mat('Concreto', (0.6, 0.58, 0.55), 0.9)
VERDE = bpy.data.materials.get('Tuboplus verde') or mat('Tuboplus verde', (0.1, 0.45, 0.25), 0.4)
BRONCE = bpy.data.materials.get('Bronce') or mat('Bronce', (0.4, 0.3, 0.15), 0.4, 1.0)
METAL = bpy.data.materials.get('Metal brillante') or mat('Metal brillante', (0.75, 0.75, 0.78), 0.25, 1.0)
AZUL = mat('Manija azul de la llave', (0.03, 0.12, 0.7), 0.35)
BLANCO = mat('PVC blanco', (0.85, 0.85, 0.82), 0.45)
FILTRO_N = mat('Filtro Y hierro negro', (0.06, 0.06, 0.065), 0.5, 0.6)

# ------------------------------------------------------------------ óxido para la base de ángulo
OXIDO = bpy.data.materials.new('Angulo de fierro oxidado')
OXIDO.use_nodes = True
nt = OXIDO.node_tree
b = nt.nodes['Principled BSDF']
ruido = nt.nodes.new('ShaderNodeTexNoise')
ruido.inputs['Scale'].default_value = 60
ruido.inputs['Detail'].default_value = 8
rampa = nt.nodes.new('ShaderNodeValToRGB')
rampa.color_ramp.elements[0].color = (0.05, 0.022, 0.012, 1)
rampa.color_ramp.elements[1].color = (0.16, 0.07, 0.03, 1)
nt.links.new(ruido.outputs['Fac'], rampa.inputs['Fac'])
nt.links.new(rampa.outputs['Color'], b.inputs['Base Color'])
b.inputs['Roughness'].default_value = 0.75
b.inputs['Metallic'].default_value = 0.4

# ================================================================== LOSA DE CONCRETO Y ESCALÓN
borrar('Banqueta')
y0 = -4.1
caja('Losa de concreto del patio', (0.5, (y0 + Y_ESCALON) / 2, LOSA / 2), (7.0, Y_ESCALON - y0, LOSA), CONCRETO, 0.008,
     bpy.data.collections.get('Entorno'))
# borde del escalón un poco desgastado (franja más oscura) como en la foto
caja('Escalon - canto', (0.5, Y_ESCALON + 0.001, LOSA / 2), (7.0, 0.004, LOSA - 0.01),
     mat('Concreto canto', (0.42, 0.4, 0.37), 0.95), 0.0, bpy.data.collections.get('Entorno'))

# ================================================================== TINACO HUECO CON BOCA
borrar('Tinaco', 'Tapa del tinaco (domo)', 'Marco del tinaco +1', 'Marco del tinaco -1', 'Travesano del tinaco +1',
       'Travesano del tinaco -1')
perfil = [(0.0, ZB), (R - 0.03, ZB), (R - 0.008, ZB + 0.006), (R, ZB + 0.03)]
z_hombro = 1.16 + DZ
for k in range(1, 9):                      # costillas suaves del tinaco
    z = ZB + 0.03 + (z_hombro - ZB - 0.03) * k / 9
    perfil.append((R, z - 0.012))
    perfil.append((R + 0.006, z))
    perfil.append((R, z + 0.012))
perfil.append((R, z_hombro))
for k in range(1, 11):                     # hombro redondeado hasta la boca
    t = k / 10 * math.pi / 2
    perfil.append((0.235 + (R - 0.235) * math.cos(t), z_hombro + (ZBOCA - 0.012 - z_hombro) * math.sin(t)))
perfil += [(0.222, ZBOCA - 0.006), (0.215, ZBOCA)]   # cuello de la boca (ahí asienta la tapa)
me = bpy.data.meshes.new('Tinaco (perfil)')
me.from_pydata([(r, 0, z) for r, z in perfil], [(i, i + 1) for i in range(len(perfil) - 1)], [])
tin = bpy.data.objects.new('Tinaco (hueco, con boca)', me)
ligar(tin)
tin.location = (0, TY, 0)
sc_ = tin.modifiers.new('girar', 'SCREW')
sc_.steps = sc_.render_steps = 72
sc_.use_merge_vertices = True
sc_.use_normal_calculate = True
so = tin.modifiers.new('pared', 'SOLIDIFY')
so.thickness = 0.006
so.offset = 1.0
tin.data.materials.append(NEGRO_T)
bpy.context.view_layer.objects.active = tin
for md in list(tin.modifiers):
    bpy.ops.object.modifier_apply(modifier=md.name)
bpy.ops.object.shade_smooth()
tin.data.use_auto_smooth = True
tin.data.auto_smooth_angle = math.radians(40)
# interior más oscuro (sin luz directa) usando el mismo material: se deja; el agua da el contraste

# agua adentro (tinaco casi lleno) con pequeñas ondas
AGUA = bpy.data.materials.new('Agua del tinaco')
AGUA.use_nodes = True
nt = AGUA.node_tree
b = nt.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (0.02, 0.07, 0.08, 1)
b.inputs['Roughness'].default_value = 0.04
b.inputs['Specular'].default_value = 0.7
b.inputs['IOR'].default_value = 1.33
ond = nt.nodes.new('ShaderNodeTexNoise')
ond.inputs['Scale'].default_value = 18
ond.inputs['Detail'].default_value = 4
bump = nt.nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = 0.12
bump.inputs['Distance'].default_value = 0.02
nt.links.new(ond.outputs['Fac'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
Z_AGUA = ZB + 0.95
bpy.ops.mesh.primitive_circle_add(vertices=72, radius=R - 0.0005, fill_type='NGON', location=(0, TY, Z_AGUA))
ag = bpy.context.object
ag.name = 'Agua dentro del tinaco'
ag.data.materials.append(AGUA)
ligar(ag)
# el agua se ve un poco por la pared del hombro: recortarla al radio interior a esa altura
r_int = R - 0.006
ag.scale = (r_int / (R - 0.0005), r_int / (R - 0.0005), 1)

# luz suave dentro del tinaco (la que entra por la boca abierta) para que se vea el agua y la pared interior
bpy.ops.object.light_add(type='POINT', location=(0.0, TY, ZBOCA - 0.08))
li = bpy.context.object
li.name = 'Luz dentro del tinaco'
li.data.energy = 3
li.data.shadow_soft_size = 0.35
li.data.color = (0.85, 0.95, 1.0)
ligar(li)
# subir la tapa (y todo lo que cuelga de ella: caja de acrílico y PING))) ) a la nueva boca
piv = bpy.data.objects['Tapa del tinaco (pivote)']
for fc in piv.animation_data.action.fcurves:
    if fc.data_path == 'location' and fc.array_index in (1, 2):
        dd = DZ if fc.array_index == 2 else DY
        for k in fc.keyframe_points:
            k.co[1] += dd
            k.handle_left[1] += dd
            k.handle_right[1] += dd
# cable del sensor de nivel: los puntos cerca del tinaco suben con él
cab = bpy.data.objects.get('Cable del sensor de nivel')
if cab:
    for s in cab.data.splines:
        for p in s.points:
            d = math.hypot(p.co[0], p.co[1] - TY0)
            w = max(0.0, min(1.0, (0.62 - d) / 0.25))
            p.co[2] += DZ * w
            p.co[1] += DY * w
            d = math.hypot(p.co[0], p.co[1] - TY)
            if d < 0.26:                 # que el poliducto termine sobre el hombro, afuera de la boca (no colgando adentro)
                k = 0.26 / max(d, 1e-6)
                p.co[0], p.co[1] = p.co[0] * k, TY + (p.co[1] - TY) * k
                p.co[2] = ZBOCA - 0.012 + cab.data.bevel_depth
# cámara del video gabinete -> tinaco: mirar a la nueva altura de la tapa
for n in ('Camara video gabinete-tinaco-panel', 'Objetivo video gabinete'):
    o = bpy.data.objects.get(n)
    if o and o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            if fc.data_path == 'location' and fc.array_index in (1, 2):
                dd = DZ if fc.array_index == 2 else DY
                for k in fc.keyframe_points:
                    if 250 <= k.co[0] <= 345:
                        k.co[1] += dd
                        k.handle_left[1] += dd
                        k.handle_right[1] += dd

# ================================================================== BASE DE ÁNGULO DE FIERRO (con patas) SOBRE LA LOSA
A, T = 0.038, 0.004                     # ángulo de 1 1/2" x 1/8"
L = 1.0
zt = ZB                                 # el tinaco asienta sobre el marco


def angulo(nombre, p1, p2, ala_abajo=True):
    """Ángulo L entre p1 y p2 (horizontal o vertical)."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    c = (p1 + p2) / 2
    if abs(d.z) > 1e-6:                 # pata vertical
        caja(nombre + ' (ala 1)', c + Vector((0, A / 2 - T / 2, 0)) * 0, (A, T, abs(d.z)), OXIDO)
        caja(nombre + ' (ala 2)', c + Vector((-A / 2 + T / 2, A / 2, 0)) * 0 + Vector((A / 2 - T / 2, 0, 0)) * 0,
             (T, A, abs(d.z)), OXIDO)
        return
    horiz_x = abs(d.x) > abs(d.y)
    largo = d.length
    if horiz_x:
        caja(nombre + ' (ala horizontal)', c + Vector((0, 0, -T / 2)), (largo, A, T), OXIDO)
        caja(nombre + ' (ala vertical)', c + Vector((0, A / 2 - T / 2, -A / 2)), (largo, T, A), OXIDO)
    else:
        caja(nombre + ' (ala horizontal)', c + Vector((0, 0, -T / 2)), (A, largo, T), OXIDO)
        caja(nombre + ' (ala vertical)', c + Vector((A / 2 - T / 2, 0, -A / 2)), (T, largo, A), OXIDO)


for sx in (-1, 1):
    angulo(f'Base del tinaco - larguero {sx:+d}', (sx * L / 2, TY - L / 2, zt), (sx * L / 2, TY + L / 2, zt))
for sy in (-1, 1):
    angulo(f'Base del tinaco - travesano {sy:+d}', (-L / 2, TY + sy * L / 2, zt), (L / 2, TY + sy * L / 2, zt))
for xx in (-0.17, 0.17):               # soportes bajo el tinaco
    angulo('Base del tinaco - soporte', (xx, TY - L / 2, zt), (xx, TY + L / 2, zt))
for sx in (-1, 1):
    for sy in (-1, 1):
        p = Vector((sx * (L / 2 - A / 2), TY + sy * (L / 2 - A / 2), 0))
        caja('Base del tinaco - pata', Vector((p.x, p.y, LOSA + PATAS / 2 - A / 2)), (A, A, PATAS - A), OXIDO)
        caja('Base del tinaco - placa de la pata', Vector((p.x, p.y, LOSA + 0.002)), (0.06, 0.06, 0.004), OXIDO)

# ================================================================== SALIDA DEL TINACO Y LÍNEA HASTA LA CAJA DE LA BOMBA
borrar('Niple al tinaco', 'Valvula de esfera', 'Manija azul', 'Tubo a valvula', 'Filtro Y (bronce)', 'Filtro Y (canastilla)',
       'Tubo a filtro')
X = 0.05
Y_SAL = TY + math.sqrt(R * R - X * X)
ZS = ZB + 0.06                          # altura de la salida (abajo, en el costado del tinaco)
ZP = 0.035                              # entrada de la caja de la bomba
Y_CODO = -2.33
hid = bpy.data.collections.get('Hidraulica') or col_t


def tramo(nombre, ya, yb, r, m, z=ZS):
    return cil(nombre, (X, ya, z), (X, yb, z), r, m, 32, hid)


tramo('Salida del tinaco - adaptador blanco', Y_SAL - 0.01, Y_SAL + 0.02, 0.025, BLANCO)
cil('Salida del tinaco - tuerca blanca', (X, Y_SAL - 0.004, ZS), (X, Y_SAL + 0.004, ZS), 0.032, BLANCO, 6, hid)
tramo('Niple negro', Y_SAL + 0.02, Y_SAL + 0.06, 0.015, NEGRO_T)
yv = Y_SAL + 0.085
tramo('Llave de esfera - cuerpo', yv - 0.028, yv + 0.028, 0.019, METAL)
for s in (-1, 1):
    cil('Llave de esfera - hexagono', (X, yv + s * 0.022, ZS), (X, yv + s * 0.032, ZS), 0.021, METAL, 6, hid)
cil('Llave de esfera - vastago', (X, yv, ZS + 0.018), (X, yv, ZS + 0.03), 0.005, METAL, 16, hid)
caja('Llave de esfera - manija azul', (X + 0.04, yv, ZS + 0.033), (0.085, 0.014, 0.006), AZUL, 0.002, hid)
tramo('Cople verde 1', yv + 0.03, yv + 0.07, 0.019, VERDE)
yf = Y_ESCALON - 0.06                   # filtro Y justo antes del escalón
tramo('Tubo verde 1', yv + 0.07, yf - 0.05, 0.0125, VERDE)
tramo('Cople verde 2', yf - 0.05, yf - 0.03, 0.018, VERDE)
tramo('Filtro Y - cuerpo', yf - 0.035, yf + 0.035, 0.017, FILTRO_N)
for s in (-1, 1):
    cil('Filtro Y - hexagono', (X, yf + s * 0.03, ZS), (X, yf + s * 0.042, ZS), 0.02, FILTRO_N, 6, hid)
pierna = Vector((0, 0.03, -0.03)).normalized()
p0 = Vector((X, yf, ZS))
cil('Filtro Y - pierna de la canastilla', p0, p0 + pierna * 0.05, 0.012, FILTRO_N, 24, hid)
cil('Filtro Y - tapon', p0 + pierna * 0.05, p0 + pierna * 0.058, 0.014, FILTRO_N, 6, hid)
tramo('Cople verde 3', yf + 0.04, yf + 0.06, 0.018, VERDE)
tramo('Tubo verde 2 (pasa el escalon)', yf + 0.06, Y_CODO, 0.0125, VERDE)
esfera('Codo verde (arriba)', (X, Y_CODO, ZS), 0.018, VERDE, hid)
cil('Tubo verde 3 (baja a la caja)', (X, Y_CODO, ZS), (X, Y_CODO, ZP), 0.0125, VERDE, 32, hid)
esfera('Codo verde (abajo)', (X, Y_CODO, ZP), 0.018, VERDE, hid)
tramo('Tubo verde 4 (entra a la caja)', Y_CODO, -2.24, 0.0125, VERDE, ZP)

# ================================================================== poliductos y cables sobre la losa (nunca dentro del concreto)
for o in bpy.data.objects:
    if o.type != 'CURVE' or o.parent is not None:
        continue
    r = o.data.bevel_depth
    cambio = False
    for s in o.data.splines:
        for p in s.points:
            if p.co[1] < Y_ESCALON + 0.004 and p.co[2] < LOSA + r:
                p.co[2] = LOSA + r + 0.001
                cambio = True
    if cambio:
        print('SUBIDO A LA LOSA:', o.name)

bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=NUEVO)

# ================================================================== imágenes de revisión
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.eevee.taa_render_samples = 64
sc.render.image_settings.file_format = 'PNG'
cam_video = sc.camera


def foto(nombre, pos, mira, lente, frame):
    cd = bpy.data.cameras.new(nombre)
    cd.lens, cd.clip_start = lente, 0.01
    c = bpy.data.objects.new(nombre, cd)
    sc.collection.objects.link(c)
    c.location = pos
    c.rotation_euler = (Vector(mira) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    sc.frame_set(frame)
    sc.camera = c
    sc.render.filepath = os.path.join(REN, nombre + '.png')
    bpy.ops.render.render(write_still=True)


foto('tinaco_abierto_por_dentro', (-0.32, -3.68, ZBOCA + 0.62), (0.03, -3.38, Z_AGUA), 26, 330)
foto('tinaco_base_y_escalon', (1.75, -1.55, 0.8), (0.05, -3.2, 0.3), 30, 1)
foto('tinaco_contra_la_pared', (1.6, -3.3, 1.2), (0.0, -3.75, 0.6), 30, 1)
foto('tinaco_salida_y_filtro', (0.55, -2.25, 0.55), (0.05, -2.75, 0.2), 30, 1)
sc.camera = cam_video
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
    sc.render.filepath = os.path.join(DIR, 'video', 'AquaHuerto_gabinete_tinaco_panel_v2_')
    bpy.ops.render.render(animation=True)
print('TINACO_OK', NUEVO)
