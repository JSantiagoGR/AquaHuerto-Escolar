"""Quita la caché de partículas (gotas de agua) guardada dentro de un .blend para que pese poco.
La simulación se vuelve a calcular sola al reproducir la animación en Blender.
Ejecutar: blender -b <archivo.blend> -P limpiar_cache_particulas.py"""
import bpy

sc = bpy.context.scene
sc.frame_set(sc.frame_start)
bpy.ops.ptcache.free_bake_all()
for o in bpy.data.objects:
    for ps in getattr(o, 'particle_systems', []):
        ps.point_cache.use_disk_cache = False
        st = ps.settings
        st.count = st.count            # cualquier cambio en los ajustes invalida la caché en memoria
        ps.seed = ps.seed
bpy.context.view_layer.update()
bpy.context.preferences.filepaths.use_file_compression = True
bpy.ops.wm.save_mainfile(compress=True)
print('LIMPIO', bpy.data.filepath)
