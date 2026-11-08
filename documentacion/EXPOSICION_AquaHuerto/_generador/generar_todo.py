"""Arma la carpeta completa de la exposicion: figuras, documentos, cartel, copias, fotos y PDF."""
import glob
import os
import shutil
import sys

from PIL import Image, ImageOps

from rutas import FIG, RAIZ, REP_IMG, MAN, EPANET, RES, UPLOADS, HUERTO
import graficas
import documentos as A
import documentos2 as B
import cartel

TMP = os.path.join(os.environ['TEMP'], 'claude', '39a626b1fcced733', 'eef6cd60-6159-4c5f-a073-f96aebcfdbc1', 'scratchpad')


def cp(src, dst_dir, nombre=None):
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, nombre or os.path.basename(src))
    shutil.copy2(src, dst)
    return dst


def foto(src, dst, lado=1800):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
    im.thumbnail((lado, lado))
    im.save(dst, quality=88)


def preparar_figuras():
    os.makedirs(FIG, exist_ok=True)
    r = graficas.todo()
    integ = os.path.join(TMP, 'img_integrador', 'word', 'media')
    avance = os.path.join(TMP, 'm_Reporte Segundo Avance (Equipo)', 'word', 'media')
    shutil.copy2(os.path.join(integ, 'image9.png'), os.path.join(FIG, 'cad_modelos_integrador.png'))
    shutil.copy2(os.path.join(avance, 'image7.png'), os.path.join(FIG, 'cad_modelos_avance.png'))
    shutil.copy2(os.path.join(integ, 'image6.png'), os.path.join(FIG, 'cad_bosquejo.png'))
    for n in ('image2.png', 'image3.png', 'image7.png', 'image8.png'):
        shutil.copy2(os.path.join(integ, n), os.path.join(FIG, 'diseno_' + n))
    rep = os.path.join(EPANET, 'reporte', 'figuras')
    shutil.copy2(os.path.join(rep, 'fig_planta.png'), os.path.join(FIG, 'epanet_planta.png'))
    shutil.copy2(os.path.join(rep, 'fig_perfil.png'), os.path.join(FIG, 'epanet_perfil.png'))
    shutil.copy2(os.path.join(EPANET, 'capturas_epanet', '00_Modelo_Limpio.png'), os.path.join(FIG, 'epanet_captura.png'))
    img = os.path.join(MAN, 'img')
    shutil.copy2(os.path.join(img, 't_ping_cables_marcada.jpg'), os.path.join(FIG, 'ping_cables.jpg'))
    for a, b in (('p_bomba.jpg', 'comp_bomba.jpg'), ('p_valvula.jpg', 'comp_valvula.jpg'), ('p_medidor.jpg', 'comp_caudal.jpg'),
                 ('t_esp32.jpg', 'comp_esp32.jpg'), ('t_reles.jpg', 'comp_reles.jpg'), ('t_dht22.jpg', 'comp_dht.jpg')):
        shutil.copy2(os.path.join(img, a), os.path.join(FIG, b))
    # collage de componentes para la portada
    ims = [Image.open(os.path.join(FIG, n)).convert('RGB') for n in
           ('comp_bomba.jpg', 'comp_valvula.jpg', 'comp_caudal.jpg', 'comp_esp32.jpg', 'comp_reles.jpg', 'comp_dht.jpg')]
    cw, ch = 600, 450
    col = Image.new('RGB', (cw * 3, ch * 2), 'white')
    for k, im in enumerate(ims):
        im = ImageOps.fit(im, (cw - 10, ch - 10))
        col.paste(im, ((k % 3) * cw + 5, (k // 3) * ch + 5))
    col.save(os.path.join(FIG, 'componentes_collage.jpg'), quality=88)
    return r


def copiar_material():
    D1, D2, D3 = A.D1, A.D2, A.D3
    # 5 memoria: reporte y manuales tecnicos
    m5 = os.path.join(D2, '05_Memoria_tecnica')
    cp(os.path.join(HUERTO, 'reporte', 'Reporte_AquaHuerto_Equipo2.pdf'), m5, 'Anexo_Reporte_tecnico_completo.pdf')
    cp(os.path.join(MAN, 'Manual_Tecnico_Sistema_de_Control_AquaHuerto.pdf'), m5, 'Anexo_Manual_tecnico_sistema_de_control.pdf')
    cp(os.path.join(MAN, 'Manual_Tecnico_Instalacion_AquaHuerto.pdf'), m5, 'Anexo_Manual_tecnico_instalacion.pdf')
    # 6 planos
    p6 = os.path.join(D2, '06_Planos_CAD', 'imagenes')
    for n in ('plano_1_cajon.png', 'plano_2_base_huerto.png', 'plano_3_base_tinaco.png', 'plano_4_soporte_panel.png',
              'cad_modelos_integrador.png', 'cad_modelos_avance.png', 'cad_bosquejo.png'):
        cp(os.path.join(FIG, n), p6)
    # 7 hidraulico
    p7 = os.path.join(D2, '07_Diagramas_hidraulicos', 'imagenes')
    for n in ('fig_diagrama_hidraulico.png', 'epanet_planta.png', 'epanet_perfil.png', 'plano_1_cajon.png'):
        cp(os.path.join(FIG, n), p7)
    # 8 EPANET
    p8 = os.path.join(D2, '08_EPANET')
    for n in ('riego_huerto_v3_final.inp', 'riego_huerto_v3_presentacion.inp', 'resultados_epanet.csv', 'escenarios_sensibilidad.csv',
              'BOM_hidraulico.csv', 'calculos_resultados.md', 'validacion_epanet.txt'):
        cp(os.path.join(EPANET, n), os.path.join(p8, 'modelo_y_resultados'))
    for f in glob.glob(os.path.join(EPANET, 'capturas_epanet', '*.png')):
        cp(f, os.path.join(p8, 'capturas'))
    cp(os.path.join(EPANET, 'reporte', 'Reporte_Riego_Automatizado_v3.pdf'), p8, 'Anexo_Reporte_EPANET_v3.pdf')
    cp(os.path.join(FIG, 'fig_epanet_presiones.png'), os.path.join(p8, 'capturas'))
    # 9-11
    cp(os.path.join(FIG, 'fig_diagrama_electrico.png'), os.path.join(D2, '09_Diagrama_electrico', 'imagenes'))
    cp(os.path.join(FIG, 'ping_cables.jpg'), os.path.join(D2, '09_Diagrama_electrico', 'imagenes'))
    for n in ('fig_arquitectura.png', 'fig_maquina_estados.png', 'fig_flujo_automatico.png', 'fig_flujo_riego_seguro.png',
              'fig_flujo_comando.png', 'fig_flujo_ia.png'):
        cp(os.path.join(FIG, n), os.path.join(D2, '11_Diagramas_flujo_y_arquitectura', 'imagenes'))
    # 13 dashboard
    for f in glob.glob(os.path.join(REP_IMG, 'd_*.jpg')):
        cp(f, os.path.join(D2, '13_Dashboard_MQTT_NodeRED_RaspberryPi', 'capturas_dashboard'))
    cp(os.path.join(MAN, 'Manual_Pantalla_de_Control_AquaHuerto.pdf'), os.path.join(D2, '13_Dashboard_MQTT_NodeRED_RaspberryPi'),
       'Anexo_Manual_de_la_pantalla_de_control.pdf')
    # 15, 16
    for n in ('fig_calibracion_ec5.png', 'fig_calibracion_ping.png', 'fig_calibracion_caudalimetro.png'):
        cp(os.path.join(FIG, n), os.path.join(D2, '15_Calibracion_sensores', 'graficas'))
    for n in ('fig_riegos_reales.png', 'fig_caudal_por_fecha.png', 'fig_serie_riego_2L.png', 'fig_datos_reales_huerto.png',
              'fig_resumen_pruebas.png'):
        cp(os.path.join(FIG, n), os.path.join(D2, '16_Pruebas_fisicas', 'graficas'))
    crudos = os.path.join(D2, '16_Pruebas_fisicas', 'datos_crudos')
    for n in ('riego_2L_20261013_1613.csv', 'riego_1L_red_20261014_1030.csv', 'prueba_final_20261021_1443.txt',
              'campo_pi_20261013_1000.txt', 'integracion_20261021_1521.txt', 'logica_pc_20261011_1751.txt',
              'selftest_esp32_proyecto_20261014.txt', 'esp32_real_20261011_2313.txt'):
        if os.path.exists(os.path.join(RES, n)):
            cp(os.path.join(RES, n), crudos)
    # 19 fotografias (solo del huerto)
    f19 = os.path.join(D2, '19_Fotografias')
    up = lambda s: sorted(glob.glob(os.path.join(UPLOADS, s, '*-image.jpg')))
    b5 = up('b5ae748a-9c12-4d0a-80d7-830ccaed9a5b')
    nombres_b5 = ['pizarron_conexiones', 'cajon_con_sustrato', 'salida_tinaco_medicion', 'gabinete_interior_esp32',
                  'tinaco_medicion_borde', 'letrero_escuela', 'estructura_superior', 'salida_tinaco_cinta',
                  'tinaco_interior_medicion', 'sensor_nivel_caja_acrilica', 'tinaco_interior_cinta', 'tinaco_circunferencia',
                  'tinaco_borde_cinta', 'perlita', 'peat_moss', 'ubicacion_gps', 'gabinete_completo', 'sensor_nivel_caja_acrilica_2']
    destino_b5 = ['1_Diseno_y_conexiones', '1_Construccion_e_instalacion', '3_Mediciones_y_pruebas', '1_Construccion_e_instalacion',
                  '3_Mediciones_y_pruebas', '1_Construccion_e_instalacion', '1_Construccion_e_instalacion', '3_Mediciones_y_pruebas',
                  '3_Mediciones_y_pruebas', '1_Construccion_e_instalacion', '3_Mediciones_y_pruebas', '3_Mediciones_y_pruebas',
                  '3_Mediciones_y_pruebas', '1_Construccion_e_instalacion', '1_Construccion_e_instalacion', '1_Construccion_e_instalacion',
                  '1_Construccion_e_instalacion', '1_Construccion_e_instalacion']
    for i, f in enumerate(b5):
        foto(f, os.path.join(f19, destino_b5[i].replace('1_Diseno_y_conexiones', '1_Construccion_e_instalacion'),
                             f'{i + 1:02d}_{nombres_b5[i]}.jpg'))
    for i, f in enumerate(up('6fd1cd98-3815-4ab4-8a73-4cdb08309467')):
        foto(f, os.path.join(f19, '1_Construccion_e_instalacion', f'cajon_construccion_{i + 1}.jpg'))
    comp = ['bateria_etiqueta', 'reles_y_ultrasonico', 'electrovalvula', 'banco_reles_caudalimetro', 'bomba_caja',
            'electrovalvula_2', 'linea_de_prueba', 'caudalimetro', 'banco_de_pruebas', 'caudalimetro_2', 'esp32_placa',
            'dht22', 'linea_tuboplus_caudalimetro', 'modulo_reles', 'electrovalvula_conector', 'electrovalvula_3']
    for i, f in enumerate(up('72a136ba-68c0-46a8-825c-dab63a7ef406')):
        foto(f, os.path.join(f19, '2_Componentes', f'{i + 1:02d}_{comp[i] if i < len(comp) else "componente"}.jpg'))
    for f in up('6849a377-213c-404d-b6bd-8bf4a7279d78'):
        pass
    cp(os.path.join(FIG, 'ping_cables.jpg'), os.path.join(f19, '2_Componentes'), 'conexion_cables_sensor_nivel.jpg')
    for f in glob.glob(os.path.join(EPANET, 'fotos_reales', '*.jpg')):
        foto(f, os.path.join(f19, '1_Construccion_e_instalacion', 'epanet_' + os.path.basename(f)))
    for f in glob.glob(os.path.join(REP_IMG, 'f_*.jpg')):
        cp(f, os.path.join(f19, '4_Seleccion_para_presentacion'))
    for f in glob.glob(os.path.join(REP_IMG, 'd_*.jpg')):
        cp(f, os.path.join(f19, '5_Capturas_dashboard'))
    # 21 y 23
    g23 = os.path.join(D3, '23_Fotos_graficas_y_videos')
    for f in glob.glob(os.path.join(FIG, 'fig_*.png')) + glob.glob(os.path.join(FIG, 'plano_*.png')):
        cp(f, os.path.join(g23, 'graficas_y_diagramas'))
    for f in glob.glob(os.path.join(REP_IMG, 'f_*.jpg')):
        cp(f, os.path.join(g23, 'fotos'))
    os.makedirs(os.path.join(g23, 'videos'), exist_ok=True)
    with open(os.path.join(g23, 'videos', 'LEEME_videos.txt'), 'w', encoding='utf8') as fh:
        fh.write('Videos sugeridos para grabar y guardar en esta carpeta:\n\n'
                 '1. Riego real en el huerto: abrir válvula, encender bomba, aspersores funcionando (30-60 s).\n'
                 '2. Dashboard en el celular o laptop mostrando el riego en vivo y el botón DETENER.\n'
                 '3. Corte de seguridad: STOP desde el dashboard y la bomba se apaga.\n'
                 '4. Bot de Telegram: /estado, /ia y /modo.\n'
                 '5. Recorrido del huerto: tinaco, gabinete, panel solar, cajón.\n\n'
                 'Guardarlos en MP4 para que se reproduzcan sin Internet.\n')


def exportar_pdf(docx_list, pptx):
    import win32com.client as w
    import pythoncom
    pythoncom.CoInitialize()
    app = w.Dispatch('Word.Application')
    app.Visible = False
    try:
        for p in docx_list:
            doc = app.Documents.Open(p)
            for t in doc.TablesOfContents:
                t.Update()
            doc.Fields.Update()
            doc.SaveAs2(p[:-5] + '.pdf', FileFormat=17)
            doc.Save()
            doc.Close(False)
    finally:
        app.Quit()
    pp = w.Dispatch('PowerPoint.Application')
    try:
        pres = pp.Presentations.Open(pptx, WithWindow=False)
        pres.SaveAs(pptx[:-5] + '.pdf', 32)
        pres.Close()
    finally:
        pp.Quit()


def main():
    r = preparar_figuras()
    docs = [A.anteproyecto(), A.bitacora(), A.bibliografia(), A.memoria(), A.planos(), A.hidraulico(), A.epanet(),
            A.electrico(), A.especificaciones(), B.flujo(), B.firmware(), B.dashboard(), B.ia(), B.calibracion(),
            B.pruebas(r['_filas_riegos']), B.comparacion(), B.riesgos(), B.demostracion(), B.guion(), B.indice_general()]
    cart = cartel.cartel(os.path.join(A.D1, '03_Cartel_cientifico', 'Cartel_AquaHuerto_90x120cm.pptx'))
    copiar_material()
    if '--sin-pdf' not in sys.argv:
        exportar_pdf(docs, cart)
        # copias para la exhibicion
        cp(cart[:-5] + '.pdf', os.path.join(A.D3, '20_Cartel_para_imprimir'))
        cp(cart, os.path.join(A.D3, '20_Cartel_para_imprimir'))
        cp(os.path.join(A.D1, '02_Bitacora_del_proyecto.pdf'), os.path.join(A.D3, '21_Bitacora_para_evaluadores'))
    for p in docs:
        print(p)


if __name__ == '__main__':
    main()
