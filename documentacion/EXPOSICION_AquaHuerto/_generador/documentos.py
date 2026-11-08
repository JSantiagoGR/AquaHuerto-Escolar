"""Genera los documentos Word de la carpeta de exposicion."""
import os
from docx.enum.text import WD_ALIGN_PARAGRAPH

from doc import Doc, GRIS
from datos import REFERENCIAS, COMPONENTES, BITACORA, PROBLEMAS
from rutas import RAIZ, FIG, REP_IMG

D1 = os.path.join(RAIZ, '1_Documentos_principales')
D2 = os.path.join(RAIZ, '2_Documentacion_tecnica')
D3 = os.path.join(RAIZ, '3_Exhibicion')
F = lambda n: os.path.join(FIG, n)
R = lambda n: os.path.join(REP_IMG, n)
CAD = os.path.join(FIG, 'cad_modelos_integrador.png')


# ============================================================== 1. ANTEPROYECTO
def anteproyecto():
    d = Doc('1', 'Anteproyecto de Ingenierías (Anexo 2)', 'Problema, justificación, objetivos, metodología y resultados',
            R('diagrama_sistema.png'), indice=True)
    d.h1('Datos generales')
    d.tabla(['Campo', 'Información'], [
        ['Título del proyecto', '**AquaHuerto Escolar: sistema mecatrónico de riego inteligente para huertos escolares**'],
        ['Área', 'Ingenierías (mecatrónica, electrónica, software y riego)'],
        ['Institución', 'Tecnológico de Monterrey, Campus Chihuahua'],
        ['Lugar de implementación', 'Escuela Primaria Federal Belisario Domínguez, Chihuahua, Chih. (28.659830, −106.074051)'],
        ['Equipo', 'Equipo 2: ' + ', '.join(n for n, _ in __import__('doc').INTEGRANTES)],
        
        ['Periodo', 'Agosto a noviembre de 2026'],
    ], [1.9, 4.8])
    d.h1('Resumen')
    d.p('AquaHuerto Escolar es un sistema de riego automatizado para un cajón de cultivo de 1 m² en una primaria pública. '
        'Un ESP32 programado en C mide la humedad volumétrica del suelo (EC-5), el nivel del tinaco (ultrasónico PING))), '
        'la temperatura y humedad del aire (DHT22) y los litros que pasan por la tubería (caudalímetro YF-S201). Con esos '
        'datos decide cuándo y cuánto regar en tres modos: **MANUAL**, **AUTOMÁTICO** (umbrales agronómicos FAO-56 por cultivo y '
        'etapa) e **IA** (dos modelos que aprenden en línea cómo responde y cómo se seca el suelo). Una Raspberry Pi guarda el '
        'historial en SQLite y muestra un dashboard de 10 páginas; un bot de Telegram permite consultar el estado y cambiar el '
        'modo desde fuera de la escuela. El sistema se alimenta con un panel solar de 50 W y una batería de 12 V.')
    d.p('Entre el 12 y el 21 de octubre de 2026 se hicieron riegos reales medidos por volumen (por ejemplo, 2.051 L en 42.8 s), '
        'se comprobaron los cortes de seguridad y se aprobaron 48/48 pruebas de lógica, 51/51 de autodiagnóstico en la placa, '
        '30/30 de integración y 28/28 de campo. Desde el 21 de octubre el sistema riega solo en el huerto.')
    d.h1('Planteamiento del problema')
    d.p('En los huertos escolares el riego suele depender de un horario fijo o de que alguien revise la tierra. Ese esquema '
        'falla en fines de semana, vacaciones y días de calor: el exceso de agua se desperdicia y puede dañar las raíces, y la '
        'falta de agua estresa a las plantas. Además, nadie sabe cuánta agua se usa realmente.')
    d.nota('**Pregunta de investigación:** ¿Es posible construir, con componentes comerciales y energía solar, un sistema que '
           'riegue un huerto escolar solo cuando la humedad medida lo justifique, que mida el agua que entrega, que se proteja '
           'solo ante fallas y que siga funcionando sin Internet?')
    d.h1('Justificación')
    d.bullets([
        'La agricultura concentra cerca del **72 %** de las extracciones de agua dulce del mundo (FAO, 2021). En Chihuahua la '
        'tecnificación del riego es una prioridad para producir con menos agua (CONAGUA, 2025).',
        'En el ciclo 2024-2025 Chihuahua tuvo **6,013 escuelas de educación básica** (SEP, 2025); muchas tienen o pueden tener un '
        'huerto que depende del cuidado del personal.',
        'Los temporizadores son baratos pero no saben si la tierra está húmeda; los sistemas comerciales con sensores e IoT son '
        'costosos y dependen de la nube (Vallejo-Gómez et al., 2023; Sharma et al., 2025).',
        'El proyecto se alinea con los ODS 2 (agricultura sostenible), 4 (educación), 6 (agua), 7 (energía renovable) y 12 '
        '(consumo responsable).',
        'El huerto se vuelve un recurso educativo: los alumnos ven qué se mide, por qué se riega y cuánta agua se usa.',
    ])
    d.h1('Objetivos')
    d.h2('Objetivo general')
    d.p('Diseñar, construir y probar un sistema mecatrónico de riego para un huerto escolar que decida con mediciones reales de '
        'humedad, nivel y caudal, que entregue volúmenes medidos, que se proteja ante fallas y que funcione con energía solar y '
        'sin depender de Internet.')
    d.h2('Objetivos específicos')
    d.bullets([
        'Medir la humedad volumétrica del suelo con un sensor calibrado (meta H1: error ≤ 5 puntos porcentuales).',
        'Regar por volumen medido con un caudalímetro (meta H3: error ≤ 10 %) y con dosis separadas por tiempo de infiltración.',
        'Detectar y responder a fallas: falta de flujo, flujo excesivo, tiempo máximo de bomba y límites diarios (meta H5).',
        'Mantener todas las funciones esenciales sin Internet (meta H7) y nunca regar al encender.',
        'Ofrecer tres modos (MANUAL, AUTOMÁTICO e IA) con umbrales agronómicos por cultivo y etapa.',
        'Desarrollar un modelo predictivo que aprenda en el propio ESP32 la respuesta del suelo al riego y su secado.',
        'Registrar humedad, nivel, caudal, estado y fallas en una base de datos y mostrarlos en un dashboard (meta R9).',
        'Simular la red hidráulica en EPANET para dimensionar la distribución en 9 microaspersores.',
    ], numerada=True)
    d.h2('Hipótesis')
    d.p('Si el riego se decide con la humedad medida del suelo, se dosifica por volumen y se ajusta con el pronóstico y con un '
        'modelo que aprende del propio huerto, entonces el sistema puede mantener la humedad dentro del rango del cultivo sin '
        'supervisión diaria y registrando cada litro aplicado.')
    d.h1('Metodología')
    d.p('Se siguió el proceso de diseño mecatrónico (Ulrich & Eppinger, 2013; Ullman, 2003) en cinco etapas:')
    d.tabla(['Etapa', 'Qué se hizo', 'Herramientas y evidencia'], [
        ['1. Definición', 'Problema, usuarios, mercado, ética, requisitos R1–R10 y metas H1–H10', 'Evidencia 1; QFD'],
        ['2. Diseño conceptual', 'Árbol de funciones, caja negra, matriz morfológica, selección del concepto B (4.65)', 'Actividad 3; Reporte Integrador'],
        ['3. Diseño de detalle', 'CAD de estructuras, AMEF, EPANET v3, PCB de potencia, diagrama eléctrico', 'SolidWorks, EPANET 2.2, Proteus'],
        ['4. Construcción e integración', 'Cajón, tinaco, tubería, gabinete, firmware en C, servidor en la Pi, dashboard, bot', 'ESP-IDF 6.0.2, Node-RED, SQLite'],
        ['5. Pruebas y validación', 'Calibraciones, pruebas automáticas, de campo y con agua; operación real desde el 21-oct', 'Scripts de prueba, base de datos'],
    ], [1.5, 3.3, 1.9])
    d.h2('Variables medidas')
    d.tabla(['Variable', 'Sensor', 'Frecuencia', 'Unidad'], [
        ['Humedad volumétrica del suelo', 'EC-5', 'Cada 5 min (más seguido con calor)', '%VWC'],
        ['Nivel del tinaco', 'PING)))', 'Cada 10 s', 'cm, %, L'],
        ['Temperatura y humedad del aire', 'DHT22', 'Cada 10 s', '°C, %HR, kPa (VPD)'],
        ['Volumen y caudal', 'YF-S201 (PCNT)', 'Continuo durante el riego', 'L, L/min'],
        ['ET0, lluvia, VPD pronosticados', 'Open-Meteo', 'Cada 60 min (ESP32) y 30 min (servidor)', 'mm, mm/h'],
    ], [2.2, 1.4, 2.0, 1.1])
    d.h1('Resultados')
    d.tabla(['Resultado', 'Valor obtenido'], [
        ['Calibración del EC-5', 'R² = 0.945 (4 muestras, 360–870 mV)'],
        ['Riego por volumen (prueba final, 21-oct)', '2.051 L pedidos 2.0 L, 42.8 s, 923 pulsos, ≈ 3.0 L/min'],
        ['Corte por STOP', '0.622 L entregados y bomba y válvula apagadas'],
        ['Corte por falta de agua (NO_FLOW)', 'Correcto a los 45 s en 11 eventos reales con el tinaco vacío'],
        ['Pruebas automáticas', 'Lógica 48/48 · autodiagnóstico 51/51 · integración 30/30 · ESP32 por red 15/15'],
        ['Prueba de campo Pi + ESP32', '28/28'],
        ['Operación real', 'Riega solo desde el 21-oct; la IA llevaba 30 riegos aprendidos al 5-nov'],
        ['Simulación EPANET', '9 × 30 L/h = 4.5 L/min, ≈ 2.14 bar en aspersores, uniformidad de presión 0.9998'],
    ], [2.6, 4.1])
    d.imagen(F('fig_resumen_pruebas.png'), ancho=5.8, pie='Resumen de pruebas aprobadas.')
    d.h1('Conclusiones preliminares')
    d.p('El prototipo cumple el objetivo principal: decide el riego con la humedad medida, entrega volúmenes medidos, se '
        'protege ante falta de agua y conserva su modo tras un reinicio. Quedan pendientes la etapa de potencia definitiva de la '
        'bomba (relé automotriz, diodos y capacitor), la calibración del caudalímetro con recipiente graduado, la medición del '
        'balance de energía y la validación del modelo de IA con datos reales.')
    d.h1('Referencias', nueva=True)
    d.refs(REFERENCIAS)
    return d.guardar(os.path.join(D1, '01_Anteproyecto_Anexo2.docx'))


# ============================================================== 2. BITACORA
def bitacora():
    d = Doc('2', 'Bitácora del proyecto', 'Registro cronológico del diseño, construcción, programación y pruebas',
            R('f_cajon.jpg'), horizontal=True)
    d.h1('Cómo leer esta bitácora')
    d.p('Cada renglón es una etapa del proyecto con su fecha, lo que se hizo, los problemas o decisiones y dónde está la '
        'evidencia (archivo, foto o resultado). Las fechas salen de los archivos del proyecto, de los resultados de las pruebas '
        'y de la base de datos del sistema.')
    d.h1('Registro cronológico')
    d.tabla(['Fecha', 'Etapa', 'Actividad', 'Problemas, resultados y decisiones', 'Evidencia'],
            [list(b) for b in BITACORA], [1.0, 1.0, 3.2, 3.0, 1.0], size=8.5)
    d.h1('Problemas encontrados y soluciones', nueva=True)
    d.tabla(['Problema', 'Causa', 'Solución', 'Estado'], [list(p) for p in PROBLEMAS], [2.2, 2.6, 3.0, 1.2], size=9)
    d.h1('Evidencias fotográficas', nueva=True)
    for a, b, pa, pb in (('f_banco.jpg', 'f_reles.jpg', 'Banco de pruebas (30-sep)', 'Módulo de relevadores'),
                         ('f_tinaco_medicion.jpg', 'f_ultrasonico.jpg', 'Medición del tinaco (13-oct)', 'Sensor de nivel en caja acrílica'),
                         ('f_gabinete.jpg', 'f_cajon.jpg', 'Gabinete con la electrónica', 'Cajón con sustrato (21-oct)')):
        d.imagen(R(a), alto_max=2.6, pie=pa)
        d.imagen(R(b), alto_max=2.6, pie=pb)
    d.h1('Registro para llenar a mano durante la exposición', nueva=True)
    d.tabla(['Fecha', 'Actividad u observación', 'Responsable', 'Firma'], [['', '', '', '']] * 12, [1.2, 5.0, 1.8, 1.2], size=10)
    return d.guardar(os.path.join(D1, '02_Bitacora_del_proyecto.docx'))


# ============================================================== 4. BIBLIOGRAFIA
def bibliografia():
    d = Doc('4', 'Bibliografía y referencias', 'Fuentes científicas, técnicas y normativas usadas en el proyecto (APA 7)', None)
    grupos = {
        'Artículos científicos y libros': ['Al Mamun', 'Allen', 'Colizzi', 'Dutta', 'Haykin', 'Moustafa', 'Sharma', 'Ulrich',
                                           'Ullman', 'Vallejo', 'Food and Agriculture Organization of the United Nations. (2021)'],
        'Hojas de datos y documentación técnica': ['Aosong', 'Espressif', 'FlowFuse', 'METER', 'OASIS', 'OpenJS', 'Parallax',
                                                   'Rossman', 'SQLite', 'Telegram', 'Zippenfenig'],
        'Normas, ética y propiedad intelectual': ['ASME', 'Bancroft', 'IEEE', 'International Organization', 'Secretaría de Economía'],
        'Contexto: agua, educación y desarrollo sostenible': ['Comisión Nacional', 'Food and Agriculture Organization of the United Nations. (s.f.)',
                                                              'Organización de las Naciones', 'Secretaría de Educación', 'UN-Water'],
    }
    usadas = set()
    for g, claves in grupos.items():
        d.h1(g)
        lista = [r for r in REFERENCIAS if any(r.startswith(k) for k in claves) and r not in usadas]
        usadas.update(lista)
        d.refs(lista)
    resto = [r for r in REFERENCIAS if r not in usadas]
    if resto:
        d.h1('Otras')
        d.refs(resto)
    return d.guardar(os.path.join(D1, '04_Bibliografia_y_referencias.docx'))


# ============================================================== 5. MEMORIA TECNICA
def memoria():
    d = Doc('5', 'Memoria técnica', 'Descripción completa de cómo funciona AquaHuerto', F('fig_arquitectura.png'), indice=True)
    d.h1('1. Qué es AquaHuerto')
    d.p('Es un sistema de riego automatizado para **un cajón de cultivo de 1.00 × 1.00 m** con 37.5 cm de sustrato, instalado '
        'en la Escuela Primaria Federal Belisario Domínguez. Riega con agua de un tinaco, mide todo lo que hace y se alimenta '
        'con energía solar.')
    d.imagen(F('fig_arquitectura.png'), pie='Arquitectura general del sistema.')
    d.h1('2. Subsistemas')
    d.tabla(['Subsistema', 'Qué lo forma', 'Qué hace'], [
        ['Hidráulico', 'Tinaco (≈ 650 L útiles), válvula de esfera, bomba de diafragma 12 V, YF-S201, electroválvula NC, Tuboplus ½", '
         'cruz, 3 mangueras y 9 microaspersores', 'Lleva el agua del tinaco al cajón solo cuando la válvula abre y la bomba enciende'],
        ['Eléctrico', 'Panel FE-50WP 50 W, controlador PWM, batería ML9-12 (12 V, 9 Ah), módulo de 2 relevadores',
         'Genera, almacena y conmuta la energía de bomba y válvula'],
        ['Sensado', 'EC-5, PING))), DHT22, YF-S201', 'Humedad del suelo, nivel del tinaco, aire y litros'],
        ['Control', 'ESP32 con firmware riego-2.0.0 (C, ESP-IDF 6.0.2, ≈ 7 900 líneas, 25 módulos, FreeRTOS)',
         'Decide y actúa en tiempo real, con supervisor de seguridad independiente'],
        ['Servidor', 'Raspberry Pi: Mosquitto 1884, Node-RED 1881, SQLite (22 tablas), bot de Telegram',
         'Guarda el historial, muestra el dashboard y avisa por el celular'],
        ['Estructura', 'Cajón de madera, base del tinaco, gabinete, soporte del panel', 'Sostiene y protege todo'],
    ], [1.3, 3.0, 2.4])
    d.h1('3. Cómo se decide un riego')
    d.p('Cada 5 minutos el ESP32 lee la humedad del suelo. Los umbrales salen de la FAO-56: con la capacidad de campo (FC ≈ 48 %) '
        'y el punto de marchitez (WP ≈ 16 %) del sustrato real se calcula θ = FC − d·(FC − WP) para cada cultivo y etapa. Para el '
        'frijol en establecimiento: emergencia 23.6, mínima 30, **óptima 39**, reserva 44.8 y máxima 48 %VWC.')
    d.imagen(F('fig_flujo_automatico.png'), ancho=5.0, pie='Decisión de riego en modo AUTOMÁTICO.')
    d.p('El riego se hace **por dosis**: 1.5 L, espera de 15 minutos para que el agua se infiltre, nueva medición y, si hace '
        'falta, otra dosis (hasta 5 dosis o 7.5 L por riego y 30 L por día). Así no se riega de más.')
    d.imagen(F('fig_flujo_riego_seguro.png'), pie='Secuencia segura de cada riego y cortes de seguridad.')
    d.h1('4. Los tres modos')
    d.tabla(['Modo', 'Cómo funciona', 'Cuándo usarlo'], [
        ['MANUAL', 'Riega solo cuando el usuario lo pide (por litros o hasta una humedad). Respeta el máximo diario salvo autorización.',
         'Pruebas, mantenimiento, cuando no hay plantas'],
        ['AUTOMÁTICO', 'Umbrales del cultivo y su etapa, histéresis de 2 pp, ventanas 06–09 y 18–20 h, nunca de 11 a 16 h, emergencias.',
         'Uso diario'],
        ['IA', 'Igual que AUTOMÁTICO más lluvia por balance; cuando el modelo está listo riega la cantidad mínima que mantiene la humedad '
         'hasta el siguiente horario.', 'Cuando la IA ya aprendió (≥ 6 riegos y ≥ 48 h de secado)'],
    ], [1.1, 4.0, 1.6])
    d.h1('5. Seguridad')
    d.bullets([
        'Nunca bomba con la válvula cerrada: válvula → 1.5 s → bomba; al terminar, bomba → 1.5 s → válvula.',
        'NO_FLOW: si en 45 s no hay pulsos, apaga todo (bombeo en seco). FLOW_HIGH: más de 8 L/min.',
        'Tiempo máximo de bomba 180 s y **tope fijo de 5.5 min** en un supervisor independiente.',
        'Si la tarea de control deja de responder 3 s, el supervisor apaga las salidas.',
        'Comandos con identificador, hora y confirmación (ACK); rechaza duplicados, retenidos y antiguos.',
        'Tras un reinicio restaura el modo guardado y **nunca riega al arrancar**.',
    ])
    d.h1('6. Comunicación y servidor')
    d.p('El ESP32 publica telemetría cada 10 s en MQTT (`huerto/final/esp32_principal/...`). Node-RED la guarda en SQLite, '
        'calcula alertas y muestra un dashboard de 10 páginas: Inicio, Manual, Automático, IA, Cultivos, Crecimiento, Clima, '
        'Historial, Alertas y Configuración. Sin MQTT el ESP32 guarda 24 h de datos y los envía al reconectar; sin Internet '
        'sigue regando con sus reglas locales.')
    d.h1('7. Inteligencia artificial')
    d.p('Dos regresiones lineales que aprenden en línea con mínimos cuadrados recursivos (RLS): el **modelo A** predice cuánto '
        'sube la humedad por litro y el **modelo B** cuánto se seca el suelo por hora con VPD, ET0, Kc y la hora del día. '
        'Detalle en el documento 14.')
    d.imagen(F('fig_flujo_ia.png'), pie='Cómo aprende y decide el modo IA.')
    d.h1('8. Documentos de apoyo')
    d.p('En esta misma carpeta están el reporte técnico completo (con imágenes y referencias APA) y los dos manuales técnicos '
        '(sistema de control e instalación y mantenimiento).')
    return d.guardar(os.path.join(D2, '05_Memoria_tecnica', '05_Memoria_tecnica.docx'))


# ============================================================== 6. PLANOS
def planos():
    d = Doc('6', 'Planos y modelos CAD', 'Cajón, bases metálicas, tinaco y soporte solar', CAD)
    d.h1('Modelos CAD')
    d.p('Los modelos 3D se hicieron en SolidWorks durante Diseño Mecatrónico. Las imágenes vienen del Reporte Integrador Final y '
        'del Segundo Avance del equipo.')
    d.imagen(CAD, pie='Modelos CAD del subsistema estructural: base del huerto, base del tinaco y soporte del panel.')
    d.imagen(F('cad_modelos_avance.png'), pie='Modelos CAD (Segundo Avance).')
    d.imagen(F('cad_bosquejo.png'), alto_max=3.2, pie='Bosquejo conceptual del conjunto.')
    M3 = os.path.join(D2, '06_Planos_CAD', 'modelos_3D')
    RD = lambda n: os.path.join(M3, 'renders', n)
    d.h1('Modelo 3D de la instalación real', nueva=True)
    d.p('Se modeló en 3D toda la instalación tal como está en la escuela, a partir de las fotos y de las medidas del huerto: '
        'cajón sobre la base metálica, marco de madera con las 3 líneas y 9 microaspersores, subida de manguera azul, línea '
        'verde en el piso con las cajas de la válvula, el caudalímetro y la bomba, filtro Y, válvula de esfera, tinaco junto a '
        'la pared, gabinete, poliductos naranjas y panel solar en el techo. La escena está en Blender '
        '(`modelos_3D/AquaHuerto_instalacion.blend`).')
    d.imagen(RD('blender_Camara_general.png'), pie='Vista general de la instalación (Blender).')
    d.imagen(RD('blender_Camara_cajon.png'), alto_max=3.6, pie='Cajón, marco y distribución en la parte alta.')
    d.imagen(RD('blender_Camara_linea.png'), alto_max=3.6, pie='Línea en el piso: cajas de válvula, caudalímetro y bomba.')
    d.imagen(RD('blender_Camara_tinaco_y_pared.png'), alto_max=3.6, pie='Tinaco, gabinete y poliductos en la pared.')
    d.h1('Piezas en 3D (SolidWorks, STEP y STL)', nueva=True)
    d.p('Cada pieza estructural se modeló con sus medidas y se guardó en formato nativo de SolidWorks (.SLDPRT / .SLDASM), '
        'en STEP (para cualquier programa CAD) y en STL (para impresión 3D o visualización).')
    for n, t in (('render_Base_del_huerto.png', 'Base del huerto: PTR 40 × 40 × 3 mm, 1200 × 1200 mm, 6 patas.'),
                 ('render_Base_del_tinaco.png', 'Base del tinaco: PTR 50 × 50 × 3 mm, 5 patas, 8 diagonales, placa de 4 mm.'),
                 ('render_Soporte_del_panel_solar.png', 'Soporte del panel: PTR 25 × 25 × 2 mm a 30°.'),
                 ('render_Cajon_de_cultivo.png', 'Cajón de cultivo 1.00 × 1.00 × 0.40 m con postes.'),
                 ('render_Ensamble_AquaHuerto.png', 'Ensamble completo (CAD).')):
        d.imagen(RD(n), alto_max=2.9, pie=t)
    d.tabla(['Archivo', 'Contenido'], [
        ['SolidWorks/*.SLDPRT, *.SLDASM', 'Piezas y ensamble para abrir y editar en SolidWorks'],
        ['STEP/*.step', 'Mismos modelos en formato estándar'], ['STL/*.stl', 'Mallas para impresión 3D'],
        ['AquaHuerto_instalacion.blend', 'Escena completa en Blender con materiales y 4 cámaras'],
        ['renders/*.png', 'Imágenes de alta resolución'],
    ], [2.6, 4.1])
    d.nota('Las alturas de las patas de las bases no estaban documentadas: la base del huerto se tomó de 120 mm (cajón a 0.12 m, '
           'como en EPANET) y la del tinaco de 250 mm (salida del tinaco a 0.265 m). Las cajas de la línea, el gabinete y los '
           'poliductos se dimensionaron a partir de las fotos.', 'FFF3E0')
    d.h1('Datos de las estructuras', nueva=True)
    d.tabla(['Conjunto', 'Geometría y material', 'Verificación preliminar'], [
        ['Base del huerto', '1200 × 1200 mm; PTR 40 × 40 × 3 mm; 6 patas; carga de diseño 1500 kg',
         'Esfuerzo ≈ 94 MPa; deflexión ≈ 3.1 mm; 8.60 m de PTR'],
        ['Base del tinaco', '1200 × 1200 mm; PTR 50 × 50 × 3 mm; 5 patas; 8 diagonales; placa de 4 mm; carga 850 kg',
         'Travesaño ≈ 32 MPa / 0.8 mm; larguero ≈ 75 MPa / 2.3 mm; placa ≈ 24 MPa / 0.6 mm'],
        ['Soporte del panel', 'Panel 680 × 620 × 25 mm; 30°; PTR 25 × 25 × 2 mm; 4 anclajes',
         'Viento 1.5 kPa → 0.632 kN; esfuerzo ≈ 20.6 MPa; deflexión ≈ 0.40 mm'],
        ['Cajón de cultivo (construido)', '1.00 × 1.00 m; 40 cm de alto; 37.5 cm de sustrato', '1 punto de %VWC = 3.75 L de agua'],
    ], [1.5, 2.9, 2.3])
    d.nota('Los cálculos son verificaciones preliminares de diseño y no sustituyen una revisión de soldaduras, anclajes, suelo y viento.',
           'FFF3E0')
    d.h1('Planos acotados', nueva=True)
    for n, t in (('plano_1_cajon.png', 'Plano 1. Cajón y distribución de los 9 microaspersores.'),
                 ('plano_2_base_huerto.png', 'Plano 2. Base metálica del huerto.'),
                 ('plano_3_base_tinaco.png', 'Plano 3. Base metálica del tinaco.'),
                 ('plano_4_soporte_panel.png', 'Plano 4. Soporte del panel solar.')):
        d.imagen(F(n), alto_max=4.2, pie=t)
    return d.guardar(os.path.join(D2, '06_Planos_CAD', '06_Planos_y_modelos_CAD.docx'))


# ============================================================== 7. HIDRAULICO
def hidraulico():
    d = Doc('7', 'Diagramas hidráulicos', 'Bomba, electroválvula, tuberías, caudalímetro y microaspersores',
            F('fig_diagrama_hidraulico.png'))
    d.h1('Recorrido del agua')
    d.imagen(F('fig_diagrama_hidraulico.png'), pie='Diagrama hidráulico (diseño EPANET v3, escenario A).')
    d.bullets([
        'Tinaco → salida existente de ½" con **válvula de esfera azul**, check y T.',
        'Codo → **bomba** de diafragma 12 V (6 L/min máx., presostato 0.9 MPa).',
        '**Caudalímetro YF-S201** (450 pulsos por litro) → **electroválvula NC** de 12 V (pilotada, necesita presión).',
        'Subida vertical en Tuboplus ½" hasta 1.52 m → **cruz** → 3 mangueras negras con 3 microaspersores cada una '
        '(posiciones 0.17, 0.50 y 0.83 m).',
    ], numerada=True)
    d.h1('Distribución en el cajón')
    d.imagen(F('plano_1_cajon.png'), pie='Distribución de las 3 líneas y los 9 microaspersores.')
    d.imagen(os.path.join(FIG, 'epanet_planta.png'), alto_max=3.5, pie='Planta del modelo EPANET.')
    d.imagen(os.path.join(FIG, 'epanet_perfil.png'), alto_max=3.5, pie='Perfil de alturas del modelo EPANET.')
    d.h1('Datos de diseño')
    d.tabla(['Magnitud', 'Valor', 'Fuente'], [
        ['Caudal de diseño', '9 × 30 L/h = 4.5 L/min', 'EPANET v3'],
        ['Presión en aspersores', '≈ 21.8 m (2.14 bar), curva de bomba provisional', 'EPANET v3'],
        ['Velocidad en la línea principal', '0.461 m/s', 'EPANET v3'],
        ['Pérdidas', '0.29 m por fricción + 0.81 m por accesorios', 'EPANET v3'],
        ['Caudal real medido', '1.7 a 3.0 L/min', 'YF-S201, pruebas 12–21 oct'],
        ['Volumen útil del tinaco', '≈ 650 L (≈ 6.3 L por cm)', 'Medición con cinta'],
    ], [2.2, 2.8, 1.7])
    d.imagen(F('fig_caudal_por_fecha.png'), ancho=5.4, pie='Caudal real de la bomba en cada prueba.')
    return d.guardar(os.path.join(D2, '07_Diagramas_hidraulicos', '07_Diagramas_hidraulicos.docx'))


# ============================================================== 8. EPANET
def epanet():
    d = Doc('8', 'Simulaciones y resultados de EPANET', 'Modelo hidráulico v3 de la red de riego', F('fig_epanet_presiones.png'))
    d.h1('Modelo')
    d.p('Se modeló la red completa en EPANET 2.2 (Rossman et al., 2020): 43 nodos y 43 enlaces (42 tuberías y 1 bomba). '
        'Se usó la ecuación de Darcy-Weisbach y se comparó con Hazen-Williams (C = 150). El modelo se validó con EPANET 2.2 GUI, '
        'runepanet, WNTR y EPyT: **71 verificaciones OK, 3 avisos y 0 fallas**.')
    d.imagen(os.path.join(FIG, 'epanet_captura.png'), alto_max=3.6, pie='Captura del modelo en EPANET 2.2.')
    d.h1('Resultados del escenario principal')
    d.imagen(F('fig_epanet_presiones.png'), pie='Presión en los 9 aspersores y sensibilidad al caudal por aspersor.')
    d.tabla(['Aspersor', 'Presión (m)', 'Presión (bar)', 'Caudal (L/h)'], [
        ['A11', '21.818', '2.136', '30'], ['A12', '21.817', '2.136', '30'], ['A13', '21.816', '2.136', '30'],
        ['A21', '21.821', '2.137', '30'], ['A22', '21.820', '2.137', '30'], ['A23', '21.820', '2.137', '30'],
        ['A31', '21.818', '2.136', '30'], ['A32', '21.817', '2.136', '30'], ['A33', '21.816', '2.136', '30'],
    ], [1.4, 1.6, 1.6, 1.6], titulo='Presión en cada microaspersor (escenario A).')
    d.h1('Sensibilidad')
    d.tabla(['Escenario', 'Caudal total', 'Presión mínima', '¿Viable?'], [
        ['20 L/h por aspersor', '3.00 L/min', '4.43 bar', 'Sí'], ['25 L/h', '3.75 L/min', '3.29 bar', 'Sí'],
        ['30 L/h (diseño)', '4.50 L/min', '2.14 bar', 'Sí'], ['35 L/h', '5.25 L/min', '0.98 bar', 'Sí'],
        ['40 L/h', '6.00 L/min', 'negativa', 'No'], ['70 L/h', '10.5 L/min', 'excede la bomba', 'No'],
        ['Tinaco casi vacío', '4.50 L/min', '2.05 bar', 'Sí'], ['Trazado B a 45°', '4.50 L/min', '2.14 bar', 'Sí'],
    ], [2.0, 1.6, 1.6, 1.0])
    d.h1('Conclusiones de la simulación')
    d.bullets([
        'Con 30 L/h por aspersor la presión es casi igual en los 9 (uniformidad de presión 0.9998).',
        'Aspersores de 40 o 70 L/h no son viables con esta bomba (9 × 70 L/h supera 6 L/min).',
        'El caudal real medido (1.7–3.0 L/min) es menor que el de diseño: la curva real de la bomba y la apertura de los '
        'aspersores aún deben medirse para validar el modelo.',
    ])
    d.p('Los archivos del modelo (.inp), resultados (.csv) y el reporte completo de EPANET están en esta misma carpeta.', size=10,
        color=GRIS)
    return d.guardar(os.path.join(D2, '08_EPANET', '08_EPANET_simulaciones_y_resultados.docx'))


# ============================================================== 9. ELECTRICO
def electrico():
    d = Doc('9', 'Diagrama eléctrico y electrónico', 'Energía solar, ESP32, relevadores, sensores y cargas',
            F('fig_diagrama_electrico.png'))
    d.h1('Diagrama')
    d.imagen(F('fig_diagrama_electrico.png'), pie='Diagrama eléctrico y electrónico. Lo punteado son protecciones recomendadas.')
    d.h1('Conexiones del ESP32')
    d.tabla(['Señal', 'GPIO', 'Detalle'], [
        ['Bomba (relé K1, IN1)', '26', 'Salida, activa en BAJO'],
        ['Electroválvula (relé K2, IN2)', '27', 'Salida, activa en BAJO'],
        ['Caudalímetro YF-S201', '19', 'Contador de pulsos por hardware (PCNT), pull-up, filtro 10 µs'],
        ['Ultrasónico PING))) (SIG)', '18', 'Divisor 1 kΩ / 2 kΩ hacia 3.3 V; alimentado a 5 V'],
        ['DHT22', '4', 'Bus de un hilo, 3.3 V'],
        ['EC-5 excitación', '25', 'Pulso de 10 ms (cable blanco)'],
        ['EC-5 señal', '34 (ADC1_CH6)', 'Atenuación 12 dB (cable rojo); sin forro a GND'],
        ['Alimentación', 'VIN (jack)', '12 V de la batería, 6.5–16 V'],
    ], [2.3, 1.2, 3.2])
    d.h2('Cables del sensor del tinaco')
    d.imagen(F('ping_cables.jpg'), ancho=4.6, pie='Blanco → GND, morado → 5V, azul → SIG.')
    d.h1('Energía')
    d.tabla(['Elemento', 'Dato'], [
        ['Panel', 'Firstech FE-50WP: 50 W, Vmp 17.4 V, Imp 2.87 A, Voc 21.6 V, Isc 3.16 A'],
        ['Batería', 'Mighty Max ML9-12: 12 V, 9 Ah (≈ 108 Wh), corriente de carga < 2.7 A, no bajar de 10.5 V'],
        ['Bomba', '12 V, 6 A (72 W): un riego de 45 s consume ≈ 0.9 Wh'],
        ['Controlador', 'PWM con LCD y 2 USB'],
        ['Cable', '18 AWG (0.824 mm²) y conectores de palanca WAGO 221'],
    ], [1.5, 5.2])
    d.h1('Mejoras eléctricas recomendadas')
    d.bullets([
        '**Relé automotriz de 30/40 A** (o MOSFET) para la bomba: el SRD soporta 3 A inductivos y la bomba pide 6 A.',
        '**Diodos 1N4007** (o 1N5819) en paralelo con la bomba y la electroválvula para absorber los picos al apagar.',
        '**Capacitor de 470–1000 µF** en la entrada VIN del ESP32.',
        '**Fusibles**: 10 A para la bomba, 3 A para la electrónica.',
    ])
    return d.guardar(os.path.join(D2, '09_Diagrama_electrico', '09_Diagrama_electrico_y_electronico.docx'))


# ============================================================== 10. ESPECIFICACIONES
def especificaciones():
    d = Doc('10', 'Especificaciones de componentes', 'ESP32, bomba, sensores, panel solar, batería y controlador',
            os.path.join(FIG, 'componentes_collage.jpg'), horizontal=True)
    d.h1('Lista de componentes')
    d.tabla(['Sistema', 'Componente', 'Marca y modelo', 'Especificaciones', 'Función', 'Cant.'],
            [list(c) for c in COMPONENTES], [0.9, 1.4, 2.1, 2.4, 1.9, 0.6], size=8.5)
    d.h1('Fotografías de los componentes', nueva=True)
    for n, t in (('comp_bomba.jpg', 'Bomba de diafragma (caja)'), ('comp_valvula.jpg', 'Electroválvula NC 12 V'),
                 ('comp_caudal.jpg', 'Caudalímetro YF-S201'), ('comp_esp32.jpg', 'ESP32 en placa de expansión'),
                 ('comp_reles.jpg', 'Módulo de 2 relevadores'), ('comp_dht.jpg', 'DHT22')):
        if os.path.exists(os.path.join(FIG, n)):
            d.imagen(os.path.join(FIG, n), alto_max=1.9, pie=t)
    return d.guardar(os.path.join(D2, '10_Especificaciones_componentes', '10_Especificaciones_de_componentes.docx'))
