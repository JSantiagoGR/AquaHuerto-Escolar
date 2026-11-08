"""Documentos 11 a 24 e indice general."""
import os
from docx.enum.text import WD_ALIGN_PARAGRAPH

from doc import Doc, GRIS
from datos import PROBLEMAS
from documentos import D1, D2, D3, F, R
from rutas import FIG


# ============================================================== 11. FLUJO Y ARQUITECTURA
def flujo():
    d = Doc('11', 'Diagramas de flujo y arquitectura del programa', 'Cómo está organizado el software y cómo toma decisiones',
            F('fig_arquitectura.png'))
    d.h1('Arquitectura del sistema')
    d.imagen(F('fig_arquitectura.png'), pie='Arquitectura: sensores, ESP32, servidor, dashboard y bot.')
    d.h1('Tareas del firmware (FreeRTOS)')
    d.tabla(['Tarea', 'Núcleo', 'Qué hace'], [
        ['control', '0 (vigilada por watchdog)', 'Ciclo principal: entradas, comandos, plan de IA, lógica de riego, publicaciones'],
        ['sensors', '1', 'Lee EC-5, PING))), DHT22 y caudalímetro'],
        ['clima', '1', 'Consulta Open-Meteo por HTTPS cada 60 min'],
        ['mqtt_pub', '1', 'Envía los mensajes MQTT desde una cola (agregada el 5-nov para que la red no bloquee el control)'],
        ['console', '0', 'Consola USB: ESTADO, RED, SELFTEST, PINES'],
        ['safety (temporizador)', '—', 'Supervisor independiente: tope de bomba 5.5 min y corte si el control no responde 3 s'],
    ], [1.5, 1.7, 3.5])
    d.h1('Máquina de estados')
    d.imagen(F('fig_maquina_estados.png'), pie='Estados del firmware y transiciones.')
    d.h1('Decisión de riego (AUTOMÁTICO)', nueva=True)
    d.imagen(F('fig_flujo_automatico.png'), ancho=5.2, pie='Diagrama de flujo de la decisión de riego.')
    d.h1('Secuencia segura de riego', nueva=True)
    d.imagen(F('fig_flujo_riego_seguro.png'), pie='Orden de encendido y cortes de seguridad.')
    d.h1('Recorrido de un comando')
    d.imagen(F('fig_flujo_comando.png'), pie='Del botón al ESP32 y de regreso con confirmación.')
    d.h1('Modo IA')
    d.imagen(F('fig_flujo_ia.png'), pie='Aprendizaje y plan del modo IA.')
    return d.guardar(os.path.join(D2, '11_Diagramas_flujo_y_arquitectura', '11_Diagramas_de_flujo_y_arquitectura.docx'))


# ============================================================== 12. FIRMWARE
def firmware():
    d = Doc('12', 'Firmware del ESP32 y sus tres modos', 'Manual, Automático e IA', F('fig_maquina_estados.png'), indice=True)
    d.h1('Datos generales')
    d.tabla(['Dato', 'Valor'], [
        ['Versión', 'riego-2.0.0'], ['Lenguaje y entorno', 'C con ESP-IDF 6.0.2 y FreeRTOS'],
        ['Tamaño', '25 módulos, ≈ 7 900 líneas, binario ≈ 1.1 MB'],
        ['Parámetros', '≈ 75 parámetros con rangos validados, guardados en memoria NVS'],
        ['Pruebas internas', '50 escenarios de lógica y autodiagnóstico en la placa (51/51 el 5-nov)'],
        ['Carga', '`idf.py -p COM8 app-flash` (conserva Wi-Fi, configuración, modo y modelo de IA)'],
    ], [2.0, 4.7])
    d.h1('Módulos')
    d.tabla(['Archivo', 'Función'], [
        ['main.c', 'Arranque; nunca riega al encender'], ['board.c', 'Pines (bomba 26, válvula 27, flujo 19, PING 18, DHT 4, EC-5 25/34)'],
        ['actuators.c', 'Bomba y válvula con enclavamiento: nunca bomba con la válvula cerrada'],
        ['safety.c', 'Supervisor independiente (tope 5.5 min, control sin responder 3 s)'],
        ['sensors.c, soil_sensor.c, tank_level.c, environment_sensor.c, flow_sensor.c', 'Lectura y validación de sensores'],
        ['irrigation_logic.c', 'Máquina de estados pura (se prueba en la PC)'],
        ['irrigation_controller.c', 'Orquesta: MQTT, IA, detección de lluvia, publicaciones'],
        ['ia_model.c', 'Modelos A y B con RLS'], ['weather.c', 'Open-Meteo por HTTPS'],
        ['mqtt_manager.c, wifi_manager.c, net_config.c', 'Red; cola de publicación (5-nov); credenciales en NVS'],
        ['commands.c', 'Comandos JSON con id, hora y ACK'], ['config_table.c, configuration.c', 'Parámetros con rangos'],
        ['storage.c', 'Contadores, modo y modelo en NVS'], ['timekeeping.c', 'Hora por NTP (CST6)'],
        ['wdt_diag.c', 'Guarda qué tarea causó un reinicio por watchdog (5-nov)'],
        ['selftest.c, logic_tests.c, simulation.c', 'Autodiagnóstico, pruebas y simulación interna'],
    ], [2.8, 3.9], size=9)
    d.h1('Modo MANUAL')
    d.bullets(['Riego por litros (0.1 L hasta el máximo por riego) o **hasta una humedad** (por dosis con infiltración).',
               'Solo se acepta en MANUAL; desde el dashboard se cambia y luego ofrece regresar al modo anterior.',
               'Respeta el máximo diario salvo con **PERMITIR RIEGO EXTRA** (válido para un riego).',
               'Rechaza el riego con salidas deshabilitadas, en FALLA o con la tierra en la humedad máxima. STOP siempre gana.'])
    d.h1('Modo AUTOMÁTICO')
    d.bullets(['Umbrales del cultivo y etapa (FAO-56 convertidos a %VWC con FC y WP del sustrato).',
               'Riega si la humedad baja de objetivo − 2 pp en **2 lecturas seguidas**.',
               'Ventanas de riego 06:00–09:00 y 18:00–20:00; **nunca de 11:00 a 16:00**; pospone con más de 35 °C.',
               'Emergencia: 1.5 L a cualquier hora (máximo una cada 240 min).',
               'Riego por dosis de 1.5 L con 15 min de infiltración, hasta 5 dosis o 7.5 L; máximo 30 L por día.'])
    d.h1('Modo IA')
    d.bullets(['Todo lo de AUTOMÁTICO más **lluvia por balance**: pospone solo si 0.8 × lluvia prevista en 6 h × ganancia ≥ déficit.',
               'Mientras el modelo está en APRENDIZAJE o VALIDACIÓN usa la lógica AUTOMÁTICA (modo sombra).',
               'En PREDICTIVO_ACTIVO riega la cantidad mínima que mantiene la humedad hasta el siguiente horario.',
               'La IA **aprende en los tres modos**; cambiar de modo no borra el modelo.'])
    d.h1('Protecciones')
    d.tabla(['Protección', 'Valor'], [
        ['NO_FLOW (sin pulsos)', '45 s'], ['FLOW_HIGH', '> 8 L/min'], ['Flujo con todo apagado (fuga o contacto pegado)', '≥ 20 pulsos'],
        ['Tiempo máximo de bomba', '180 s (configurable) + tope fijo 5.5 min'], ['Máximo por riego / por día', '7.5 L / 30 L'],
        ['Separación válvula ↔ bomba', '1.5 s'], ['Sin hora válida', 'solo emergencias'],
        ['Comandos', 'rechaza duplicados (anillo de 32), retenidos y con más de 60 s de antigüedad'],
    ], [3.2, 3.5])
    d.h1('Mejora del 5 de noviembre: reinicios por watchdog')
    d.p('El ESP32 se reiniciaba entre 15 y 70 veces al día. El diagnóstico mostró que la tarea de control se quedaba esperando '
        'mientras la biblioteca MQTT reconectaba con Wi-Fi débil (−77 a −87 dBm), y el watchdog de 5 s la reiniciaba. Se movió el '
        'envío de mensajes a una **cola con su propia tarea**, se agregó un registro de qué tarea y en qué etapa ocurre un '
        'reinicio (`last_wdt`) y las horas de secado de la IA se guardan cada hora. El autodiagnóstico quedó en 51/51.')
    return d.guardar(os.path.join(D2, '12_Firmware_ESP32', '12_Firmware_ESP32_y_modos.docx'))


# ============================================================== 13. DASHBOARD
def dashboard():
    d = Doc('13', 'Dashboard, MQTT, Node-RED y Raspberry Pi', 'Servidor, comunicación, base de datos y bot de Telegram',
            R('d_inicio_panel.jpg'), indice=True)
    d.h1('Servidor en la Raspberry Pi')
    d.p('La Raspberry Pi del laboratorio (raspberrypi.local, red RouterHuerto1) es compartida con otros equipos. AquaHuerto usa una '
        '**instancia propia y aislada** en `~/equipo2_proyecto`: Node-RED 5.0.8 en el puerto 1881 y Mosquitto en el 1884. No '
        'modifica el Node-RED (1880) ni el Mosquitto (1883) del profesor. Arranca solo al encender la Pi.')
    d.h1('MQTT')
    d.tabla(['Topic (huerto/final/esp32_principal/...)', 'Contenido'], [
        ['status', 'En línea / fuera de línea (mensaje de última voluntad)'], ['telemetry', 'Lecturas cada 10 s'],
        ['state', 'Estado, modo, bomba, válvula'], ['config', 'Configuración activa y su versión'],
        ['decision', 'Por qué riega o no'], ['event', 'Inicio y fin de cada riego'], ['alarm', 'Fallas y avisos'],
        ['ia', 'Estado del modelo de IA'], ['weather', 'Pronóstico vigente'], ['diag', 'Diagnóstico (señal, reinicios, last_wdt)'],
        ['telemetry_buffer', 'Datos guardados mientras no hubo conexión'], ['command / ack', 'Comandos y confirmaciones'],
    ], [3.0, 3.7])
    d.bullets(['Broker con usuarios y lista de control de acceso (ACL); anónimos prohibidos.',
               'Comandos con QoS 1, sin retener, con `id` y `ts`; el ESP32 responde ACK con el mismo `id`.',
               'Sin respuesta en 12 s → TIMEOUT y no cambia nada.'])
    d.h1('Node-RED')
    d.tabla(['Función', 'Qué hace'], [
        ['ingesta.js', 'MQTT → SQLite, estado y alertas'], ['comando.js', 'Lista blanca, id, hora, tiempo de espera'],
        ['acks.js, alertas.js, snapshot.js', 'Confirmaciones, alertas, estado (≤ 1 por segundo)'],
        ['clima_pedir.js / clima_procesar.js', 'Open-Meteo cada 30 min'], ['crecimiento.js', 'Etapas del cultivo y grados-día'],
        ['umbrales.js', 'FAO-56 → %VWC'], ['ia_servidor.js', 'Predicho contra real'], ['respaldo.js, csv_*', 'Respaldo diario y CSV'],
    ], [2.6, 4.1])
    d.p('El flujo (125 nodos) se genera con un script de Python y se despliega por la API de Node-RED.')
    d.h1('Base de datos SQLite')
    d.p('22 tablas: readings, irrigation_events, event_ends, decisions, weather_fetches, forecast_hourly, forecast_daily, '
        'rain_events, crops, plantings, stage_changes, config_changes, crop_changes, ia_snapshots, ia_observations, predictions, '
        'alerts, connectivity, data_versions, soil_calibration, app_settings y schema_meta. Respaldo diario a las 03:00.')
    d.h1('Dashboard (10 páginas)', nueva=True)
    d.tabla(['Página', 'Contenido'], [
        ['Inicio', 'Medidores, bomba y válvula, iniciar/detener, resumen, balance de agua y selección de modo'],
        ['Manual', 'Riego por litros o hasta una humedad, progreso, gráficas en vivo e historial'],
        ['Automático', 'Decisión actual y su justificación; umbrales, horarios y límites'],
        ['IA', 'Estado, plan, predicho contra real, coeficientes'], ['Cultivos', '10 cultivos base y personalizados'],
        ['Crecimiento', 'Etapas, días restantes, grados-día'], ['Clima', 'Open-Meteo, VPD, ET0, lluvia, 48 h y 10 días'],
        ['Historial', 'Gráficas agrupables y CSV'], ['Alertas', '12 categorías'], ['Configuración', 'Red, calibraciones, suelo, respaldos'],
    ], [1.4, 5.3])
    for n, t in (('d_inicio_panel.jpg', 'Página Inicio: panel de control.'), ('d_manual.jpg', 'Página Manual.'),
                 ('d_ia.jpg', 'Página IA.'), ('d_clima.jpg', 'Página Clima.'), ('d_alertas.jpg', 'Página Alertas.')):
        d.imagen(R(n), alto_max=3.0, pie=t + ' (captura con datos de demostración)')
    d.h1('Bot de Telegram')
    d.p('@aquahuerto_equipo2_bot corre en la Pi y responde solo a chats autorizados: /estado, /riegos, /alertas, /ia, /modo y '
        '/ayuda. Avisa alertas, si el ESP32 deja de enviar datos más de 20 min y manda un resumen a las 20:30. Puede cambiar el modo '
        'con confirmación, pero **no riega ni borra fallas**. No se abrió ningún puerto a Internet.')
    return d.guardar(os.path.join(D2, '13_Dashboard_MQTT_NodeRED_RaspberryPi', '13_Dashboard_MQTT_NodeRED_y_Pi.docx'))


# ============================================================== 14. IA
def ia():
    d = Doc('14', 'Modelo de IA predictiva', 'Qué datos usa, cómo aprende y cómo decide', F('fig_flujo_ia.png'))
    d.h1('Idea')
    d.p('En lugar de regar siempre lo mismo, el ESP32 aprende **dos cosas del propio huerto**: cuánto sube la humedad por cada '
        'litro y cuánto se seca por hora. Con eso calcula el agua mínima necesaria hasta el siguiente horario de riego.')
    d.h1('Modelo A: respuesta al riego')
    d.p('Δθ = L · (a0 + a1·u1 + a2·u2 + a3·u3 + a4·u4)', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    d.bullets(['u1 = (θ0 − 25)/10: humedad antes del riego', 'u2 = (T − 20)/10: temperatura', 'u3 = (HR − 50)/50: humedad del aire',
               'u4 = min(horas desde el último riego, 48)/24', 'Aprende después de cada riego ≥ 100 mL, con la primera lectura tras la infiltración.'])
    d.h1('Modelo B: secado')
    d.p('pérdida (pp/h) = b0 + b1·(θ−25)/10 + b2·Kc·VPD + b3·Kc·ET0_h·10 + b4·sin(2πh/24) + b5·cos(2πh/24)', bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER)
    d.bullets(['Limitada a 0–3 pp/h; sin pronóstico usa ET0 ≈ 0.12·VPD.',
               'Aprende con pares de lecturas separados ≥ 1 h **sin agua** (sin riego reciente ni aumentos externos de humedad).'])
    d.h1('Datos que usa')
    d.tabla(['Dato', 'Origen'], [
        ['Humedad volumétrica θ', 'EC-5'], ['Temperatura y HR, VPD', 'DHT22'], ['Litros aplicados', 'YF-S201'],
        ['ET0, lluvia, VPD pronosticados', 'Open-Meteo'], ['Kc del cultivo y etapa', 'Perfil FAO-56 del cultivo'], ['Hora del día', 'NTP'],
    ], [3.0, 3.7])
    d.h1('Aprendizaje')
    d.bullets(['**Mínimos cuadrados recursivos (RLS)** con una ganancia inicial de 0.27 pp/L calculada con la geometría de la cama (Haykin, 2014).',
               'Factor de olvido 0.995 (A, ≈ 200 riegos) y 0.999 (B, ≈ 6 semanas).',
               'Se descartan datos atípicos con residuo > 4σ.',
               '**CUSUM** (k = 0.5, h = 6) detecta cambios del suelo: vuelve a VALIDACIÓN sin borrar el modelo.',
               'El error se mide **antes** de aprender cada dato (validación fuera de muestra).',
               'El modelo ocupa ≈ 0.6 KB y se guarda en la memoria NVS.'])
    d.h1('Estados del modelo')
    d.tabla(['Estado', 'Condición', 'Qué hace el modo IA'], [
        ['APRENDIZAJE', '< 6 riegos o < 48 h de secado', 'Riega como AUTOMÁTICO'],
        ['VALIDACIÓN', 'Errores fuera de tolerancia (A ≤ 2 pp, B ≤ 0.4 pp/h)', 'Riega como AUTOMÁTICO'],
        ['PREDICTIVO_ACTIVO', 'Datos suficientes y errores en tolerancia', 'Riega según el plan'],
    ], [1.7, 2.8, 2.2])
    d.imagen(F('fig_flujo_ia.png'), pie='Aprendizaje y plan.')
    d.h1('Resultados')
    d.tabla(['Prueba', 'Resultado'], [
        ['11 escenarios automáticos', 'Aprende una ganancia de 3.5 ± 0.5 pp/L, descarta atípicos, detecta cambios, plan mínimo y limitado'],
        ['Simulador (14 días simulados)', 'PREDICTIVO_ACTIVO con errores de 0.25 pp y 0.17–0.20 pp/h (datos simulados)'],
        ['Huerto real (5-nov)', 'APRENDIZAJE: 30 riegos aprendidos (meta 6 cumplida) y 9 de 48 h de secado'],
    ], [2.2, 4.5])
    d.p('Como todavía no hay plantas, el sistema se dejó en MANUAL sin regar para que la tierra se seque y el modelo B junte las '
        '48 horas de secado. Las horas se van sumando aunque haya reinicios o se pierda el Wi-Fi.')
    return d.guardar(os.path.join(D2, '14_Modelo_IA', '14_Modelo_de_IA_predictiva.docx'))


# ============================================================== 15. CALIBRACION
def calibracion():
    d = Doc('15', 'Tablas y gráficas de calibración', 'EC-5, ultrasónico PING))) y caudalímetro YF-S201',
            F('fig_calibracion_ec5.png'))
    d.h1('Sensor de humedad EC-5')
    d.tabla(['Agua agregada (mL)', 'Tierra (mL)', 's = V agua / (V tierra + V agua)', 'Lectura (mV)'], [
        ['0', '600', '0 %', '360'], ['105', '600', '14.9 %', '420'], ['257', '600', '30.0 %', '630'], ['490', '600', '45.0 %', '870'],
    ], [1.6, 1.2, 2.4, 1.4], titulo='Muestras de calibración del EC-5 (Actividad 2.2).')
    d.p('Recta: **s = 0.08146067·mV − 23.932584**, R² = 0.94494. Resolución teórica 0.0219 %VWC por cuenta del ADC. '
        'En el firmware se convierte a humedad volumétrica estándar con **θ = s/(1 − s)**; ADC con atenuación de 12 dB; '
        'intervalo calibrado 360–870 mV.')
    d.imagen(F('fig_calibracion_ec5.png'), pie='Calibración del EC-5 y conversión a humedad volumétrica.')
    d.tabla(['Condición (21-oct)', 'Lectura'], [['Sensor al aire', '≈ 375 mV'], ['Sensor en el sustrato', '515–600 mV'],
                                                ['Lectura en la Pi', '25.9 %VWC (546 mV)']], [3.0, 3.0])
    d.h1('Sensor de nivel PING)))', nueva=True)
    d.p('Distancia = t·c/2 con c = 331.3 + 0.606·T (corregida con la temperatura del DHT22). Se toman 5 pulsos separados 60 ms y '
        'se usa la mediana. Nivel % = (117 − d)/(117 − 12)·100. El sensor está a 127 cm del piso; Ø del tinaco ≈ 0.90 m '
        '(circunferencia 2.83 m) → ≈ 6.3 L por cm.')
    d.imagen(F('fig_calibracion_ping.png'), pie='Calibración del sensor de nivel.')
    d.tabla(['Fecha', 'Distancia medida', 'Nivel', 'Comparación'], [
        ['9-oct (banco)', '94.9 cm', '—', 'Prueba de funcionamiento'], ['14-oct', '110.7–112 cm', '5–6 %', 'Tinaco casi vacío'],
        ['21-oct', '30.4–31.4 cm', '82 % (≈ 535 L)', 'Cinta métrica: 25–30 cm'],
    ], [1.4, 1.6, 1.6, 2.1])
    d.h1('Caudalímetro YF-S201', nueva=True)
    d.tabla(['Volumen pedido (L)', 'Pulsos', 'Pulsos por litro'], [
        ['1', '481', '481'], ['2', '920', '460'], ['3', '1390', '463'], ['4', '1850', '463'], ['5', '2315', '463'],
    ], [2.0, 2.0, 2.0], titulo='Pulsos registrados (Actividad 2.3).')
    d.imagen(F('fig_calibracion_caudalimetro.png'), pie='Pulsos contra volumen y factor de fábrica.')
    d.nota('Los pulsos de más respecto a 450 p/L son el sobrepaso después de la orden de apagado: el volumen se calculó, no se '
           'midió con recipiente. El firmware usa 450 p/L. **Pendiente:** calibración con recipiente graduado.', 'FFF3E0')
    return d.guardar(os.path.join(D2, '15_Calibracion_sensores', '15_Calibracion_de_sensores.docx'))


# ============================================================== 16. PRUEBAS FISICAS
def pruebas(filas_riegos):
    d = Doc('16', 'Reporte de pruebas físicas', 'Volúmenes, caudal, humedad, consumo y funcionamiento',
            F('fig_riegos_reales.png'), indice=True)
    d.h1('Resumen')
    d.imagen(F('fig_resumen_pruebas.png'), ancho=5.6, pie='Pruebas automáticas y físicas aprobadas.')
    d.h1('Riegos reales en el huerto')
    d.tabla(['Fecha y hora', 'Pedido (L)', 'Medido (L)', 'Resultado', 'Duración (s)'],
            [[f[0], f'{f[1]:.1f}', f'{f[2]:.3f}', f[3], f'{f[4]:.1f}'] for f in filas_riegos], [1.6, 1.1, 1.1, 1.4, 1.2],
            titulo='Riegos con agua registrados por el sistema.', size=9)
    d.imagen(F('fig_riegos_reales.png'), pie='Litros pedidos contra litros medidos.')
    d.p('Los riegos que llegaron a la meta (TARGET) entregaron entre 0.0 y 2.5 % más de lo pedido (2.002/2.0, 0.502/0.5, '
        '2.802/2.8, 1.404/1.4 y 2.051/2.0 L), medido con el propio caudalímetro. Los NO_FLOW de los días 13 y 14 ocurrieron con '
        'el tinaco casi vacío y el corte de seguridad funcionó en todos.')
    d.h1('Caudal', nueva=True)
    d.imagen(F('fig_caudal_por_fecha.png'), ancho=5.4, pie='Caudal medido en cada prueba.')
    d.imagen(F('fig_serie_riego_2L.png'), pie='Riego de 2 L del 13-oct: caudal y volumen acumulado.')
    d.h1('Humedad del suelo')
    d.imagen(F('fig_datos_reales_huerto.png'), pie='Respuesta del EC-5 a dos riegos reales (14-oct).')
    d.p('Después del riego de 2.8 L la lectura subió de 28.5 a 32.7 %VWC y, tras el de 1.4 L, llegó a 53–54 %VWC al '
        'infiltrarse el agua. Ese día se terminó de cablear el sensor, por lo que estos datos sirven para ver la respuesta, no '
        'como calibración.')
    d.h1('Consumo de agua y energía')
    d.tabla(['Concepto', 'Valor', 'Tipo'], [
        ['Agua por riego automático', '1.5 L por dosis, máximo 7.5 L por riego', 'Configuración'],
        ['Agua máxima por día', '30 L', 'Configuración'],
        ['Autonomía del tinaco (≈ 650 L útiles)', '≥ 3 semanas con el máximo diario; más con riegos normales', 'Calculado'],
        ['Energía de la bomba', '72 W × 43 s ≈ 0.9 Wh por un riego de 2 L', 'Calculado'],
        ['Energía de la bomba con 30 L/día', '≈ 15 min de bombeo ≈ 18 Wh/día', 'Calculado'],
        ['Batería', '12 V × 9 Ah ≈ 108 Wh', 'Dato del fabricante'],
    ], [2.6, 2.9, 1.2])
    d.nota('El consumo eléctrico se calculó con los datos de placa; falta medir el voltaje de la batería con la bomba encendida '
           'y el balance diario del panel.', 'FFF3E0')
    d.h1('Funcionamiento', nueva=True)
    d.tabla(['Prueba', 'Resultado', 'Fecha'], [
        ['Bomba y válvula 10 s × 4 ciclos', 'La válvula corta el agua; relevadores activos en BAJO', '9-oct'],
        ['Primer riego en el huerto', '0.773 L en 20.5 s (STOP)', '12-oct'],
        ['Prueba de campo Pi + ESP32', '28/28 (sin 12 V → NO_FLOW correcto)', '13-oct'],
        ['Reinicio en AUTOMÁTICO', 'Vuelve en AUTOMÁTICO y no riega al arrancar', '14-oct'],
        ['Prueba final con agua', '14/15: válvula→bomba 1.3 s; 2.051 L en 42.8 s; STOP a 0.622 L; sin reinicio', '21-oct'],
        ['Riego manual en AUTOMÁTICO', 'Rechazado (regla nueva)', '21-oct'],
        ['Estabilidad Wi-Fi', '3 min sin desconexión en mesa (−68 a −82 dBm); −84 a −94 dBm en el gabinete', '21-oct'],
        ['Operación automática', 'Riega sola desde el 21-oct; 30 riegos aprendidos por la IA al 5-nov', '21-oct a 5-nov'],
        ['Autodiagnóstico tras el firmware nuevo', '51/51 sin reinicios por watchdog', '5-nov'],
    ], [2.2, 3.4, 1.1])
    d.h1('Archivos de datos')
    d.p('Los datos crudos (CSV y resultados de las pruebas) están en la subcarpeta `datos_crudos`.', size=10, color=GRIS)
    return d.guardar(os.path.join(D2, '16_Pruebas_fisicas', '16_Reporte_de_pruebas_fisicas.docx'))


# ============================================================== 17. COMPARACION
def comparacion():
    d = Doc('17', 'Comparación contra los objetivos de diseño', 'Metas H1–H10 y requisitos R1–R10 contra lo logrado', None,
            horizontal=True)
    d.h1('Metas de ingeniería (QFD)')
    d.tabla(['Código', 'Especificación', 'Meta', 'Resultado obtenido', 'Estado'], [
        ['H1', 'Error de medición de humedad', '≤ 5 pp tras calibración', 'Calibración R² = 0.945 en laboratorio; falta validar en el sustrato', 'Parcial'],
        ['H2', 'Banda de histéresis', '5 a 10 pp', 'Riega bajo objetivo − 2 pp y para en la reserva (39 → 44.8 %): banda ≈ 6 pp', 'Cumplido'],
        ['H3', 'Error de caudal', '≤ 10 %', 'Entregas de 0–2.5 % sobre la meta según el YF-S201; falta recipiente graduado', 'Pendiente'],
        ['H4', 'Error de nivel', '≤ 10 % del volumen útil', 'Sensor 30.4–31.4 cm contra cinta 25–30 cm: ≤ 5 % de 105 cm', 'Cumplido (preliminar)'],
        ['H5', 'Respuesta ante falla', '≤ 5 s', 'STOP y cortes por software inmediatos; NO_FLOW espera 45 s para cebar la bomba', 'Parcial'],
        ['H6', 'Canales de riego', '1 canal', '1 electroválvula, 9 aspersores', 'Cumplido'],
        ['H7', 'Funciones sin Internet', '100 %', 'Decide y riega localmente; guarda 24 h de datos. Falta prueba física sin Internet', 'Parcial'],
        ['H8', 'Margen energético', '≥ 20 %', 'Calculado: bomba ≤ 18 Wh/día; falta medir consumo y generación', 'Pendiente'],
        ['H9', 'Protección del gabinete', 'IP65', 'Gabinete cerrado; no certificado', 'Pendiente'],
        ['H10', 'Sustitución de un componente', '≤ 30 min', 'Se cambió el ESP32 conservando la configuración (21-oct); no cronometrado', 'Parcial'],
    ], [0.6, 1.8, 1.4, 4.3, 1.1], size=9)
    d.h1('Requisitos del cliente', nueva=True)
    d.tabla(['Código', 'Requisito', 'Evidencia', 'Estado'], [
        ['R1', 'Riego automático de un huerto', 'Riega solo desde el 21-oct; 30 riegos aprendidos al 5-nov', 'Cumplido'],
        ['R2', 'Humedad + histéresis', 'Umbrales FAO-56 por cultivo y etapa; 2 lecturas para confirmar', 'Cumplido'],
        ['R3', 'Impedir bombeo sin agua', 'NO_FLOW a los 45 s en 11 eventos reales; el nivel bajo solo avisa (decisión del equipo)', 'Cumplido con cambio'],
        ['R4', 'Verificar flujo', 'Contador de pulsos por hardware; NO_FLOW y FLOW_HIGH', 'Cumplido'],
        ['R5', 'Sin Internet', 'Lógica y protecciones en el ESP32', 'Parcial'],
        ['R6', 'Modo manual con protecciones', 'Riego manual solo en MANUAL, respeta límites', 'Cumplido'],
        ['R7', 'Gabinete exterior protegido', 'Gabinete cerrado; IP65 no certificado', 'Parcial'],
        ['R8', 'Margen energético ≥ 20 %', 'Sin medición', 'Pendiente'],
        ['R9', 'Registrar variables y estado', 'SQLite con 22 tablas, dashboard, CSV y bot', 'Cumplido'],
        ['R10', 'Sustitución ≤ 30 min', 'Arquitectura modular; no cronometrado', 'Parcial'],
    ], [0.6, 2.4, 4.8, 1.4], size=9)
    d.h1('Cambios respecto al diseño original')
    d.tabla(['Diseño original', 'Lo que se construyó', 'Motivo'], [
        ['Dos ESP32 cooperando (concepto B)', 'Un ESP32 en el huerto + Raspberry Pi como servidor', 'Menos cableado y una sola fuente de verdad'],
        ['Huerto de 1.20 × 1.20 m', 'Cajón de 1.00 × 1.00 m (la base metálica sí es de 1.20 m)', 'Medida real del cajón'],
        ['Tinaco de 450 L', '≈ 650 L útiles medidos', 'Medición con cinta'],
        ['Bloqueo por nivel bajo', 'Aviso por nivel bajo + corte NO_FLOW', 'El sensor de nivel daba lecturas inválidas con la tapa quitada'],
        ['Bomba máximo 90 s', '180 s + tope fijo 5.5 min', 'El caudal real es menor que el de diseño'],
        ['Sin IA', 'Modo IA con RLS dentro del ESP32', 'Regar la cantidad mínima con datos del propio huerto'],
    ], [2.6, 3.2, 3.2], size=9)
    return d.guardar(os.path.join(D2, '17_Comparacion_contra_objetivos', '17_Comparacion_contra_objetivos.docx'))


# ============================================================== 18. RIESGOS
def riesgos():
    d = Doc('18', 'Análisis de riesgos y medidas de seguridad', 'Riesgos eléctricos, hidráulicos, de uso, de software y de exhibición',
            None, horizontal=True)
    d.h1('AMEF de diseño (Diseño Mecatrónico)')
    d.tabla(['Modo de falla', 'Efecto', 'S', 'O', 'D', 'NPR', 'Acción tomada en el prototipo'], [
        ['Sensor de humedad con deriva o lectura fija', 'Riego excesivo o insuficiente', '7', '5', '5', '175',
         'Calibración, validación de rango (360–870 mV), estado SIN_SENAL, 2 lecturas para decidir, detección de aumentos sin bomba'],
        ['Sensor de nivel con lectura falsa', 'Bomba en seco o sin riego', '8', '4', '4', '128',
         'Mediana de 5 pulsos, estados INESTABLE/FUERA_DE_RANGO y corte NO_FLOW de 45 s'],
        ['Batería degradada o baja tensión', 'Reinicios y paro del bombeo', '7', '4', '4', '112',
         'Detector de caída de voltaje; nunca riega al reiniciar; pendiente: medición de voltaje'],
        ['Bomba sin flujo', 'No riega; calentamiento', '8', '4', '3', '96', 'NO_FLOW, tiempo máximo y tope fijo de 5.5 min'],
        ['Electroválvula atascada', 'Riego no controlado', '8', '3', '4', '96',
         'Válvula NC (cierra sin energía), detección de flujo con todo apagado (≥ 20 pulsos)'],
        ['Panel con generación insuficiente', 'Menor autonomía', '6', '4', '3', '72', 'Pendiente: medir energía diaria'],
    ], [2.0, 1.6, 0.35, 0.35, 0.35, 0.5, 4.0], size=8.5)
    d.h1('Matriz de riesgos del prototipo', nueva=True)
    d.tabla(['Riesgo', 'Tipo', 'Probabilidad', 'Gravedad', 'Medidas actuales', 'Medidas pendientes'], [
        ['Relevador de 3 A con bomba de 6 A', 'Eléctrico', 'Alta', 'Media', 'Separación de 1.5 s entre arranques', 'Relé automotriz 30/40 A, fusible 10 A'],
        ['Picos inductivos que reinician el ESP32', 'Eléctrico', 'Alta', 'Baja', 'Nunca riega al reiniciar; conserva el modo', 'Diodos 1N4007 y capacitor 470–1000 µF'],
        ['Cortocircuito en el cableado de 12 V', 'Eléctrico', 'Baja', 'Alta', 'Cable 18 AWG, conectores de palanca', 'Fusibles 10 A y 3 A'],
        ['Agua dentro del gabinete', 'Eléctrico', 'Media', 'Alta', 'Gabinete cerrado, separado de la tubería', 'Prensaestopas, IP65 real'],
        ['Fuga o salida de agua sin control', 'Hidráulico', 'Baja', 'Media', 'Válvula NC, detección de flujo con todo apagado, llave azul', '—'],
        ['Bombeo en seco', 'Hidráulico', 'Media', 'Media', 'NO_FLOW 45 s, aviso de tinaco bajo', '—'],
        ['Congelación en invierno', 'Ambiental', 'Media', 'Media', 'Aviso en el manual', 'Vaciar la bomba si hay heladas'],
        ['Alumnos manipulando el equipo', 'Uso', 'Media', 'Media', 'Gabinete cerrado, manual en lenguaje simple', 'Cerradura o candado'],
        ['Comandos falsos o repetidos', 'Software', 'Baja', 'Media', 'Usuarios y ACL en MQTT, id, hora, ACK', '—'],
        ['Pérdida de Internet o Wi-Fi', 'Software', 'Alta', 'Baja', 'Funciona local, buffer de 24 h', 'Mejor señal Wi-Fi'],
        ['Exposición de contraseñas', 'Seguridad', 'Baja', 'Media', 'Credenciales en NVS y archivos protegidos; nada expuesto a Internet', '—'],
    ], [2.3, 0.9, 0.9, 0.8, 2.4, 2.0], size=8.5)
    d.h1('Medidas de seguridad durante la exhibición', nueva=True)
    d.bullets(['No llevar la batería de 12 V conectada a la bomba a la mesa de exposición; usar la demostración segura (documento 22).',
               'Si se lleva agua, usar un recipiente cerrado y mantenerla lejos de la electrónica y de los enchufes.',
               'Cables fijos con cinta, sin cruzar pasillos.',
               'No dejar el equipo sin un integrante presente.',
               'Respetar las restricciones del evento sobre líquidos, baterías y fuentes de energía.'])
    d.h1('Normas y ética')
    d.p('Referencias de diseño: NOM-001-SEDE-2012 (instalaciones eléctricas), NMX-J-529-ANCE-2020 (código IP), ISO 12100:2010 '
        '(evaluación de riesgos) y Código de Ética del IEEE (seguridad, honestidad en las afirmaciones técnicas y privacidad). El '
        'prototipo es académico y no está certificado.')
    return d.guardar(os.path.join(D2, '18_Analisis_de_riesgos', '18_Analisis_de_riesgos_y_seguridad.docx'))


# ============================================================== 22. DEMOSTRACION
def demostracion():
    d = Doc('22', 'Demostración segura del sistema', 'Cómo mostrar AquaHuerto en la exhibición sin riesgos', R('d_inicio_panel.jpg'))
    d.h1('Opciones de demostración')
    d.tabla(['Opción', 'Qué se muestra', 'Qué se necesita', 'Riesgo'], [
        ['A. Dashboard con simulador (recomendada)', 'Dashboard completo con el dispositivo simulado `sim_01`: riego, modos, IA, '
         'gráficas e historial', 'Laptop con el dashboard local; no necesita Internet ni el huerto', 'Ninguno'],
        ['B. Banco de sensores', 'ESP32 con DHT22 y ultrasónico midiendo en vivo; las salidas quedan deshabilitadas', 'ESP32, cable USB, '
         'sensores, laptop', 'Muy bajo (5 V por USB)'],
        ['C. Huerto en vivo', 'Datos reales del huerto con el bot de Telegram (/estado, /ia)', 'Celular con Internet', 'Ninguno'],
        ['D. Videos y fotos', 'Riego real, cortes de seguridad, instalación', 'Pantalla o laptop', 'Ninguno'],
    ], [1.8, 2.5, 1.6, 0.8], size=9)
    d.h1('Preparación de la opción A')
    d.bullets(['Encender la laptop y abrir el dashboard local (http://localhost:1880/dashboard).',
               'Seleccionar el dispositivo `sim_01`: aparece la franja **MODO DEMOSTRACIÓN – DATOS SIMULADOS**.',
               'Mostrar: Inicio → INICIAR RIEGO 1 L → ver litros y caudal → DETENER; cambiar de modo y ver el ACK; página IA; Historial.',
               'Explicar que el dispositivo real del huerto hace exactamente lo mismo con agua.'], numerada=True)
    d.h1('Lista de verificación antes de la exhibición')
    d.tabla(['Revisión', 'Listo'], [
        ['Laptop cargada y cargador', '☐'], ['Dashboard local abre con el simulador', '☐'], ['Cartel impreso', '☐'],
        ['Bitácora impresa', '☐'], ['Videos copiados en la laptop (sin depender de Internet)', '☐'],
        ['Bot de Telegram responde /estado desde el celular', '☐'], ['Sin batería de 12 V ni bomba conectadas en la mesa', '☐'],
        ['Cables fijos y fuera del paso', '☐'], ['Respetadas las reglas del evento sobre agua y baterías', '☐'],
    ], [5.4, 1.0])
    return d.guardar(os.path.join(D3, '22_Demostracion_segura', '22_Demostracion_segura.docx'))


# ============================================================== 24. GUION
def guion():
    d = Doc('24', 'Explicación oral para la evaluación', 'Guion de 15 minutos y preguntas frecuentes', F('fig_arquitectura.png'))
    d.h1('Guion (15 minutos)')
    d.tabla(['Tiempo', 'Sección', 'Qué decir', 'Apoyo'], [
        ['0:00–1:00', 'Presentación', 'Nombre del proyecto, equipo y escuela donde está instalado.', 'Cartel: título'],
        ['1:00–2:30', 'Problema', 'Los huertos escolares se riegan por horario o cuando alguien se acuerda; fines de semana y vacaciones; '
         'la agricultura usa ≈ 72 % del agua dulce.', 'Cartel: introducción'],
        ['2:30–3:30', 'Objetivo', 'Regar solo cuando la humedad medida lo justifique, medir cada litro, protegerse de fallas y funcionar '
         'sin Internet con energía solar.', 'Cartel: objetivos'],
        ['3:30–5:30', 'Diseño', 'QFD, concepto elegido, CAD de las bases, EPANET (9 aspersores, 2.14 bar).', 'Planos y EPANET'],
        ['5:30–8:00', 'Cómo funciona', 'Sensores → ESP32 → bomba y válvula; secuencia segura; tres modos; riego por dosis.', 'Diagramas'],
        ['8:00–9:30', 'IA', 'Dos modelos que aprenden del huerto; estados; por qué no riega igual siempre.', 'Diagrama IA'],
        ['9:30–11:30', 'Demostración', 'Dashboard con simulador: riego, STOP, cambio de modo con ACK; bot de Telegram en vivo.', 'Laptop y celular'],
        ['11:30–13:00', 'Resultados', '2.051 L en 42.8 s; cortes NO_FLOW; pruebas 48/48, 51/51, 30/30, 28/28; riega solo desde el 21-oct.', 'Gráficas'],
        ['13:00–14:00', 'Problemas y soluciones', 'Reinicios por la bomba y el Wi-Fi: cómo se diagnosticaron y corrigieron.', 'Bitácora'],
        ['14:00–15:00', 'Conclusiones', 'Qué se logró, qué falta (etapa de potencia, calibración del caudal, energía) y siguiente paso.', 'Cartel'],
    ], [0.9, 1.2, 3.6, 1.0], size=9)
    d.h1('Preguntas probables y respuestas', nueva=True)
    preguntas = [
        ('¿Por qué no usaron un temporizador?', 'Porque no sabe si la tierra está húmeda. AquaHuerto mide antes de regar y riega por dosis.'),
        ('¿Cómo saben cuánta agua riegan?', 'El caudalímetro da 450 pulsos por litro y el ESP32 los cuenta con un contador por hardware; el riego se corta al llegar a los litros pedidos.'),
        ('¿Qué pasa si se acaba el agua?', 'Si en 45 s no hay pulsos, apaga bomba y válvula y marca FALLA (NO_FLOW). Lo probamos con el tinaco vacío.'),
        ('¿Y si se va el Internet?', 'Sigue regando con sus reglas locales y guarda 24 h de datos para enviarlos después.'),
        ('¿Qué hace la IA exactamente?', 'Aprende cuánto sube la humedad por litro y cuánto se seca por hora con el clima; con eso riega solo lo necesario hasta el siguiente horario.'),
        ('¿Cómo validan la IA?', 'Mide su error antes de aprender cada dato; solo se activa cuando el error está dentro de tolerancia (2 pp y 0.4 pp/h).'),
        ('¿Por qué el caudal real es menor que el de EPANET?', 'EPANET usa una curva de bomba provisional y 30 L/h por aspersor; falta medir la curva real y la apertura de los aspersores.'),
        ('¿Es seguro para niños?', 'La electrónica está en un gabinete cerrado, la válvula es normalmente cerrada y el sistema nunca riega al encender. Falta instalar fusibles y diodos.'),
        ('¿Cuánto cuesta y se puede replicar?', 'Usa componentes comerciales y software libre; el código, los manuales y los planos están documentados.'),
        ('¿Qué mejorarían?', 'Relé automotriz, diodos y capacitor, calibrar el caudalímetro con recipiente, medir la energía y mejorar la señal Wi-Fi.'),
    ]
    d.tabla(['Pregunta', 'Respuesta corta'], [list(p) for p in preguntas], [2.3, 4.4], size=9.5)
    d.h1('Consejos')
    d.bullets(['Hablar con datos medidos y decir claramente qué está pendiente.', 'Señalar el cartel y las gráficas mientras se habla.',
               'Dejar que el evaluador pruebe un botón del dashboard con el simulador.', 'Practicar el guion completo al menos dos veces con cronómetro.'])
    return d.guardar(os.path.join(D3, '24_Explicacion_oral_15_min', '24_Guion_de_exposicion_15_min.docx'))


# ============================================================== 00. INDICE
def indice_general():
    d = Doc('', 'Índice general de la carpeta', 'Dónde está cada documento solicitado', None)
    d.h1('Contenido de la carpeta')
    filas = [
        ['1', 'Anteproyecto de Ingenierías (Anexo 2)', '1_Documentos_principales/01_Anteproyecto_Anexo2'],
        ['2', 'Bitácora del proyecto', '1_Documentos_principales/02_Bitacora_del_proyecto'],
        ['3', 'Cartel científico', '1_Documentos_principales/03_Cartel_cientifico'],
        ['4', 'Bibliografía y referencias', '1_Documentos_principales/04_Bibliografia_y_referencias'],
        ['5', 'Memoria técnica', '2_Documentacion_tecnica/05_Memoria_tecnica (+ reporte y manuales técnicos)'],
        ['6', 'Planos y modelos CAD', '2_Documentacion_tecnica/06_Planos_CAD (+ modelos 3D: SolidWorks, STEP, STL y Blender)'],
        ['7', 'Diagramas hidráulicos', '2_Documentacion_tecnica/07_Diagramas_hidraulicos'],
        ['8', 'Simulaciones de EPANET', '2_Documentacion_tecnica/08_EPANET (+ modelo .inp y resultados)'],
        ['9', 'Diagrama eléctrico y electrónico', '2_Documentacion_tecnica/09_Diagrama_electrico'],
        ['10', 'Especificaciones de componentes', '2_Documentacion_tecnica/10_Especificaciones_componentes'],
        ['11', 'Diagramas de flujo y arquitectura', '2_Documentacion_tecnica/11_Diagramas_flujo_y_arquitectura'],
        ['12', 'Firmware ESP32 y modos', '2_Documentacion_tecnica/12_Firmware_ESP32'],
        ['13', 'Dashboard, MQTT, Node-RED y Raspberry Pi', '2_Documentacion_tecnica/13_Dashboard_MQTT_NodeRED_RaspberryPi'],
        ['14', 'Modelo de IA predictiva', '2_Documentacion_tecnica/14_Modelo_IA'],
        ['15', 'Calibración de sensores', '2_Documentacion_tecnica/15_Calibracion_sensores'],
        ['16', 'Pruebas físicas', '2_Documentacion_tecnica/16_Pruebas_fisicas (+ datos crudos)'],
        ['17', 'Comparación contra objetivos', '2_Documentacion_tecnica/17_Comparacion_contra_objetivos'],
        ['18', 'Riesgos y seguridad', '2_Documentacion_tecnica/18_Analisis_de_riesgos'],
        ['19', 'Fotografías del proceso', '2_Documentacion_tecnica/19_Fotografias'],
        ['20', 'Cartel para imprimir', '3_Exhibicion/20_Cartel_para_imprimir'],
        ['21', 'Bitácora para evaluadores', '3_Exhibicion/21_Bitacora_para_evaluadores'],
        ['22', 'Demostración segura', '3_Exhibicion/22_Demostracion_segura'],
        ['23', 'Fotografías, gráficas y videos', '3_Exhibicion/23_Fotos_graficas_y_videos'],
        ['24', 'Explicación oral de 15 minutos', '3_Exhibicion/24_Explicacion_oral_15_min'],
    ]
    d.tabla(['#', 'Documento', 'Carpeta'], filas, [0.4, 2.6, 3.7], size=9.5)
    d.p('Cada documento está en Word (para editar) y en PDF (para imprimir o entregar).', size=10, color=GRIS)
    d.h1('Lo que deben agregar ustedes')
    d.bullets(['**Videos** del riego real y de la demostración (carpeta 23).',
               'Fotos de la **construcción** que tengan en sus celulares (carpeta 19).',
               'Si la convocatoria da un **formato oficial** del Anexo 2 o medidas del cartel distintas a 90 × 120 cm, pasar el contenido a ese formato.'])
    return d.guardar(os.path.join(os.path.dirname(D1), '00_Indice_general.docx'))
