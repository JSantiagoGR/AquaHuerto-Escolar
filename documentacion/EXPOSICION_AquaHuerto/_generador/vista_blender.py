"""Al abrir el .blend: vista con materiales desde la cámara general (para la captura)."""
import bpy


def ajustar():
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.scene.camera = bpy.data.objects['Camara general']
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
