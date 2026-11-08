"""Al abrir AquaHuerto_cajas_abiertas.blend: cámara de las cajas, tapas abiertas y vista con materiales."""
import bpy


def ajustar():
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    sc = bpy.context.scene
    sc.camera = bpy.data.objects['Camara cajas abiertas']
    sc.frame_set(140)
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                for sp in area.spaces:
                    if sp.type == 'VIEW_3D':
                        sp.shading.type = 'MATERIAL'
                        sp.overlay.show_floor = False
                        sp.overlay.show_axis_x = False
                        sp.overlay.show_axis_y = False
                        sp.overlay.show_extras = False
                        sp.overlay.show_cursor = False
                        sp.region_3d.view_perspective = 'CAMERA'
                        sp.region_3d.view_camera_zoom = 18
                        sp.region_3d.view_camera_offset = (0, 0)
    return None


bpy.app.timers.register(ajustar, first_interval=2.0)
