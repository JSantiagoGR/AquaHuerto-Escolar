"""Manuales TÉCNICOS de AquaHuerto (persona responsable y técnico): sistema de control e instalación física."""
import os

from manual_base import Manual, IMG, OLD, REP, GRIS, AZUL_HEX, ROJO_HEX, NARANJA_HEX

T = 'MANUAL TÉCNICO'

# ================================================================== SISTEMA DE CONTROL
c = Manual('Manual técnico del sistema de control',
           'Pantalla de control, ESP32, Raspberry Pi, comunicación y diagnóstico',
           os.path.join(REP, 'diagrama_sistema.png'), etiqueta=T)
c.indice()

c.h1('1. Alcance')
c.p('Este manual es para la **persona responsable** del sistema y para quien le dé mantenimiento. Explica cómo está '
    'construido el software, qué hace cada página y botón de la pantalla de control, cómo decide el sistema cuándo '
    'regar, qué significa cada alarma y cómo se administran el ESP32 y la Raspberry Pi.')
c.p('El personal de la escuela usa el **Manual de la pantalla de control**, que es la versión corta.')
c.tabla(['Requisito', 'Para qué'], [
    ['Estar en la red **RouterHuerto1**', 'Abrir la pantalla de control y conectarse a la Raspberry Pi.'],
    ['Laptop del equipo con la llave SSH (`~/.ssh/equipo2_pi`)', 'Administrar la Raspberry Pi y desplegar cambios.'],
    ['Cable USB de datos y puerto **COM8**', 'Cargar firmware, configurar el Wi-Fi y habilitar la potencia del ESP32.'],
], [3.0, 3.7])
c.caja('Reglas de seguridad', [
    'La Raspberry Pi es **compartida**: el Node-RED 1880 y el Mosquitto 1883 son del profesor y de otros equipos. '
    'Todo lo de este proyecto vive en `~/equipo2_proyecto` (puertos 1881 y 1884).',
    'Las contraseñas nunca se escriben en documentos, fotos, chats ni registros. El Wi-Fi del ESP32 se configura solo por USB.',
    'MQTT y Node-RED **no** se exponen a internet. Para ver el sistema desde fuera se usa el bot de Telegram.',
], color=ROJO_HEX, fondo='FBEBEB')

c.h1('2. Arquitectura')
c.imagen(os.path.join(REP, 'diagrama_sistema.png'), ancho=4.2, pie='Los tres caminos del sistema: agua, energía y datos.')
c.tabla(['Elemento', 'Qué es', 'Dónde'], [
    ['**ESP32**', 'Firmware propio `riego-2.0.0` (ESP-IDF 6.0.2). Lee sensores, decide y acciona bomba y válvula. '
                  'Funciona aunque no haya red.', 'Gabinete del huerto'],
    ['**Broker MQTT**', 'Mosquitto propio con usuarios y listas de acceso.', 'Raspberry Pi, puerto **1884**'],
    ['**Node-RED + pantalla**', 'FlowFuse Dashboard 2.0, 10 páginas. Recibe datos, guarda y envía órdenes.',
     'Raspberry Pi, puerto **1881**'],
    ['**Base de datos**', 'SQLite `riego_final.db` con todo el historial. Respaldo diario a las 03:00.',
     '`~/equipo2_proyecto/database/`'],
    ['**Open-Meteo**', 'Pronóstico del clima (lluvia, ET0). Lo consultan el ESP32 (cada 60 min) y el servidor (cada 30 min).',
     'Internet (HTTPS)'],
    ['**Bot de Telegram**', 'Consulta y cambio de modo desde cualquier red (no puede regar).', 'Raspberry Pi'],
], [1.5, 3.6, 1.6], size=10.5)
c.h2('Qué pasa si algo falla')
c.tabla(['Falla', 'Qué sigue funcionando'], [
    ['Se cae la Raspberry Pi o el Wi-Fi', 'El ESP32 sigue regando con sus reglas. Guarda 144 muestras (24 h, una cada 10 min) '
                                          'y las envía al reconectar.'],
    ['No hay internet', 'Riega igual; sin hora válida solo permite riegos de emergencia.'],
    ['El ESP32 se reinicia', 'Recupera su modo guardado y **nunca riega al arrancar**. Un riego interrumpido no se '
                             'reanuda (alarma REBOOT_DURING_WATERING).'],
], [2.3, 4.4])

c.h1('3. Comunicación MQTT')
c.p('Todos los mensajes van en JSON bajo la base **huerto/final/esp32_principal/**.')
c.tabla(['Subtopic', 'Sentido', 'Contenido'], [
    ['status', 'ESP32 → Pi', 'En línea / fuera de línea (mensaje de última voluntad, retenido)'],
    ['telemetry', 'ESP32 → Pi', 'Cada 10 s: suelo, tinaco, ambiente, flujo, modo, estado, cultivo'],
    ['state', 'ESP32 → Pi', 'Máquina de estados, bomba y válvula, riego en curso, alarmas'],
    ['config', 'ESP32 → Pi', 'Todos los parámetros y su versión'],
    ['decision', 'ESP32 → Pi', 'Código y explicación de la última decisión'],
    ['event', 'ESP32 → Pi', 'Inicio y fin de riego, observaciones de la IA, aumentos de humedad sin riego'],
    ['alarm', 'ESP32 → Pi', 'Alarmas activadas y resueltas'],
    ['ia', 'ESP32 → Pi', 'Fase del modelo, plan y coeficientes'],
    ['weather / diag', 'ESP32 → Pi', 'Pronóstico usado y diagnóstico de red (sin contraseñas)'],
    ['telemetry_buffer', 'ESP32 → Pi', 'Muestras guardadas mientras no hubo conexión'],
    ['command', 'Pi → ESP32', 'Órdenes (QoS 1, nunca retenidas)'],
    ['ack', 'ESP32 → Pi', 'Respuesta a cada orden: OK o motivo del rechazo'],
], [1.5, 1.2, 4.0], size=10.5)
c.h2('Recorrido de una orden')
c.pasos([
    'El usuario presiona un botón y confirma en el diálogo.',
    'Node-RED valida la orden contra una lista permitida, le asigna un identificador y la hora, y la publica en **command**.',
    'El ESP32 rechaza órdenes repetidas (**DUPLICATE**), retenidas (**RETAINED**) o con más de 60 s de antigüedad (**STALE**).',
    'La lógica valida todo junto y responde en **ack** con OK o con el motivo.',
    'La pantalla muestra **CONFIRMADO por el dispositivo**. Si no hay respuesta en 12 s muestra **TIMEOUT** y no cambia nada.',
])

c.h1('4. Modos y lógica de riego')
c.tabla(['Modo', 'Comportamiento'], [
    ['**MANUAL**', 'Solo riega por orden del usuario: por litros (0.1 L hasta el máximo por riego) o hasta una humedad meta '
                   '(por dosis con infiltración). El riego manual **solo se acepta en este modo**.'],
    ['**AUTOMÁTICO**', 'Reglas fijas por humedad, horario y límites (orden de decisión abajo). No usa el pronóstico de lluvia.'],
    ['**IA**', 'Todo lo de AUTOMÁTICO; además dosifica según el modelo predictivo cuando está en PREDICTIVO_ACTIVO y '
               'pospone solo si la lluvia prevista cubre el déficit. Las emergencias nunca se posponen.'],
], [1.4, 5.3])
c.h2('Orden de decisión del modo AUTOMÁTICO')
c.pasos([
    'Salidas deshabilitadas o lectura del EC-5 inválida: **no riega**.',
    'Humedad en la máxima o sobre la reserva: **no riega**.',
    'Sin emergencia y humedad no menor que (óptima − histéresis): **no riega**.',
    'Confirma la sequedad con **2 lecturas** seguidas.',
    'Máximo diario alcanzado o menos de 60 min desde el último riego: espera.',
    '**Emergencia** (bajo el umbral crítico): 1.5 L a cualquier hora, como máximo una cada 240 min.',
    'Sin hora válida: no hay riegos por horario.',
    'De 11:00 a 16:00 no riega. Solo riega de **06:00 a 09:00** y de **18:00 a 20:00**. Con más de 35 °C pospone.',
    'Si todo se cumple: dosis de 1.5 L, 15 min de infiltración, nueva lectura; hasta 5 dosis (7.5 L) o hasta la óptima.',
])
c.h2('Parámetros en producción')
c.tabla(['Parámetro', 'Valor', 'Nota'], [
    ['Cultivo y etapa', 'Frijol, establecimiento', 'Sustrato: FC ≈ 48 %, WP ≈ 16 % (estimados)'],
    ['Emergencia / mínima / óptima', '23.6 / 30 / 39 %VWC', 'Se recalculan al cambiar cultivo o etapa'],
    ['Reserva / máxima', '44.8 / 48 %VWC', ''],
    ['Histéresis', '2 puntos', 'Riega bajo ≈ 37 %VWC'],
    ['Dosis / máximo por evento', '1.5 L / 7.5 L', '5 dosis como máximo'],
    ['Máximo diario', '30 L', 'Se puede exceder una vez con PERMITIR RIEGO EXTRA'],
    ['Infiltración', '15 min', 'Entre dosis'],
    ['Sin flujo (NO_FLOW)', '45 s', 'Corte si la bomba no produce pulsos'],
    ['Tiempo máximo de bomba', '180 s por ciclo', 'Tope duro del supervisor: 5.5 min'],
    ['Tinaco mínimo', '20 %', 'Solo avisa (TANK_LOW); no bloquea'],
    ['Cama de cultivo', '1 × 1 m, 37.5 cm', '1 punto de %VWC ≈ 3.75 L'],
], [2.3, 1.9, 2.5], size=10.5)
c.h2('Fases de la IA')
c.tabla(['Fase', 'Significado'], [
    ['APRENDIZAJE', 'Junta datos. Requiere al menos 6 riegos y 48 h de secado observado.'],
    ['VALIDACIÓN', 'Compara predicciones con la realidad antes de usarlas.'],
    ['PREDICTIVO_ACTIVO', 'En modo IA decide la cantidad mínima que mantiene la humedad hasta el siguiente horario.'],
], [1.9, 4.8])
c.p('El modelo A estima cuántos puntos sube la humedad por litro y el modelo B cuánto se seca por hora (VPD, ET0, Kc y '
    'hora del día). Ambos se ajustan por mínimos cuadrados recursivos. La IA aprende en los tres modos y cambiar de modo '
    'no la borra. **REINICIAR MODELO** solo se usa si cambia el sensor, el sustrato o la calibración.')

c.h1('5. La pantalla de control, página por página')
c.p('Dirección: **http://raspberrypi.local:1881/dashboard** (solo desde RouterHuerto1). Toda acción que cambia algo pide '
    'confirmación y espera el ACK del ESP32.')
c.imagen(os.path.join(OLD, 'd_inicio_panel.jpg'), ancho=6.2, pie='Inicio (captura del simulador).')
c.tabla(['Página', 'Muestra', 'Controles', 'Precaución'], [
    ['**Inicio**', 'Medidores, bomba y válvula, resumen, balance de agua, banda de humedad, alertas recientes',
     'INICIAR RIEGO, DETENER BOMBA, SELECCIONAR MODO', 'Riego rápido en mL'],
    ['**Manual**', 'Progreso, caudal, pulsos, gráficas en vivo e historial', 'REGAR X L, REGAR HASTA X %, DETENER TODO',
     'Solo en modo MANUAL'],
    ['**Automático**', 'Decisión actual y justificación, historial de decisiones',
     'Borrador de umbrales, horarios, límites, lluvia; GUARDAR / CANCELAR', 'Cambia cómo riega'],
    ['**IA**', 'Fase, plan, autonomía, predicho contra real, coeficientes', 'SELECCIONAR MODO IA, REINICIAR MODELO',
     'Reiniciar borra lo aprendido'],
    ['**Cultivos**', '10 cultivos base y personalizados, etapas, Kc, umbrales calculados',
     'AGREGAR, EDITAR, DUPLICAR, ELIMINAR, GUARDAR COMO CULTIVO ACTIVO', 'Cambia los umbrales'],
    ['**Crecimiento**', 'Plantación, etapa, días restantes, cosecha estimada, grados-día',
     'NUEVA PLANTACIÓN, ADELANTAR/RETRASAR ETAPA, CONFIRMAR, CORREGIR FECHAS', 'Una plantación activa'],
    ['**Clima**', 'Open-Meteo, ET0, ETc, VPD, lluvia, 48 h y 10 días', 'ACTUALIZAR', ''],
    ['**Historial**', 'Gráficas agrupables, eventos de riego y de lluvia', 'Filtros, APLICAR FILTROS, CSV', ''],
    ['**Alertas**', '12 categorías y registro', 'FUE LLUVIA, RIEGO EXTERNO, ERROR DEL SENSOR, OTRA CAUSA, MARCAR REVISADA',
     'Confirmar la causa mejora la IA'],
    ['**Configuración**', 'Dispositivos, red (sin contraseñas), calibraciones, cama, suelo, respaldos',
     'DIAGNÓSTICO, PEDIR ESTADO, CAMBIAR BROKER, GUARDAR…, NUEVA VERSIÓN, RESPALDAR AHORA', 'Solo el responsable'],
], [1.1, 2.1, 2.2, 1.3], size=9.5)
c.h2('Avisos de la cabecera')
c.tabla(['Aviso', 'Causa', 'Acción'], [
    ['SISTEMA EN FALLA', 'Alarma crítica (NO_FLOW, FLOW_HIGH, PUMP_TIMEOUT, SAFETY_TRIP, FLOW_WHEN_IDLE)',
     'Corregir la causa y LIMPIAR FALLA. Si se repite, revisar el hardware.'],
    ['EL SISTEMA QUEDÓ EN MANUAL', 'Se cambió a MANUAL para regar a mano', 'REGRESAR A AUTOMÁTICO o QUEDARSE EN MANUAL'],
    ['MÁXIMO DIARIO ALCANZADO', 'Se llegó a 30 L', 'PERMITIR RIEGO EXTRA autoriza un solo riego adicional'],
], [2.0, 2.6, 2.1], size=10.5)
c.h2('Borrador y configuración activa')
c.p('Las páginas Automático, Cultivos y Configuración editan un **borrador** ("Hay cambios SIN GUARDAR"). GUARDAR muestra '
    'la lista de cambios (antes → después); el ESP32 valida todo junto y responde con la versión aplicada. Si rechaza o '
    'vence el tiempo, se conserva la configuración anterior. Salir de la página descarta el borrador.')
c.imagen(os.path.join(OLD, 'd_automatico.jpg'), ancho=6.2, pie='Automático: decisión actual y parámetros (captura del simulador).')

c.h1('6. Códigos de decisión y alarmas')
c.h2('Decisiones más comunes')
c.tabla(['Código', 'Significado'], [
    ['HUMIDITY_OK', 'Humedad en rango: no hace falta regar'],
    ['CONFIRMING_DRY', 'Humedad bajo el objetivo: confirmando con más lecturas'],
    ['BELOW_MIN_WAIT', 'Bajo la mínima pero sobre la emergencia: espera el horario'],
    ['OUTSIDE_WINDOW / MIDDAY', 'Pospuesto hasta el próximo horario / por el mediodía'],
    ['START_SCHEDULED / START_EMERGENCY', 'Inicio de riego programado / de emergencia'],
    ['INFILTRATING / CONTINUE_CYCLE', 'Esperando infiltración / nueva dosis'],
    ['TARGET_REACHED', 'Humedad objetivo alcanzada: fin del riego'],
    ['MAX_CYCLES / MAX_EVENT_LITERS / WINDOW_ENDED', 'Fin del riego por límite o por fin del horario'],
    ['DAILY_LIMIT / MIN_GAP / EMERGENCY_GAP', 'Límite diario / intervalo mínimo entre riegos o emergencias'],
    ['SOIL_INVALID', 'Lectura del EC-5 inválida: no se riega'],
    ['TOO_WET / ABOVE_RESERVE', 'Humedad en la máxima o sobre la reserva'],
    ['NO_RESPONSE / AUTO_LOCKED', 'El suelo no respondió a riegos previos: automático bloqueado'],
    ['TIME_INVALID', 'Hora no sincronizada: no hay riegos por horario'],
    ['MODE_MANUAL / OUTPUTS_DISABLED / FAULT', 'Modo manual / salidas deshabilitadas / sistema en falla'],
], [2.9, 3.8], size=10)
c.h2('Alarmas')
c.tabla(['Alarma', 'Nivel', 'Significado', 'Qué revisar'], [
    ['NO_FLOW', 'Crítica', 'Bomba encendida sin pulsos del caudalímetro', 'Tinaco, llave azul, cebado, mangueras, sensor'],
    ['FLOW_HIGH', 'Crítica', 'Caudal fuera de límites o pulsos erráticos', 'Fuga o manguera suelta; cable del caudalímetro'],
    ['PUMP_TIMEOUT', 'Crítica', 'La bomba superó el tiempo máximo', 'Caudal bajo, aspersores tapados'],
    ['SAFETY_TRIP', 'Crítica', 'El supervisor independiente cortó las salidas', 'Ruido eléctrico, reinicios, tarea bloqueada'],
    ['FLOW_WHEN_IDLE', 'Crítica', 'Flujo con la bomba apagada', 'Relé pegado, válvula abierta o fuga'],
    ['SOIL_NO_RESPONSE', 'Aviso', 'La humedad no subió tras varios riegos', 'Aspersores, posición del EC-5'],
    ['REBOOT_DURING_WATERING', 'Aviso', 'Reinicio durante un riego', 'Diodos, capacitor, alimentación'],
    ['CONFIG_RESET', 'Aviso', 'Configuración corrupta: valores por defecto', 'Volver a aplicar el cultivo y calibraciones'],
    ['SOIL_SENSOR', 'Aviso', 'EC-5 sin lectura válida', 'Jack, cables, empalmes secos'],
    ['TANK_SENSOR', 'Aviso', 'Ultrasónico sin lectura válida', 'Tapa puesta, sensor centrado, cable SIG'],
    ['TANK_LOW', 'Aviso', 'Tinaco en el mínimo (el riego sigue)', 'Llenar el tinaco'],
    ['ENV_SENSOR', 'Info', 'DHT22 sin lectura válida', 'Cable del DHT22'],
    ['TIME_INVALID', 'Info', 'Hora no sincronizada por NTP', 'Internet del router'],
    ['DAILY_LIMIT', 'Info', 'Máximo diario de litros alcanzado', 'Normal'],
    ['COMMS', 'Info', 'Sin Wi-Fi o MQTT', 'Señal Wi-Fi, Raspberry Pi'],
], [1.8, 0.7, 2.2, 2.0], size=9.5)
c.p('Resultados de un riego: TARGET, STOP_CMD, NO_FLOW, FLOW_HIGH, PUMP_TIMEOUT, DAILY_LIMIT, EVENT_LIMIT, TANK_LOW, '
    'SAFETY, REBOOT.', size=10.5, color=GRIS)

c.h1('7. Lecturas, filtros y calibración')
c.tabla(['Sensor', 'Conversión', 'Filtro'], [
    ['EC-5 (cada 5 min)', 's = 0.08146067 · mV − 23.932584;  θ = s / (1 − s). Rango calibrado 360–870 mV.',
     '9 pulsos, mediana; salto > 3 pp requiere 2 lecturas que coincidan; hasta 2 lecturas inválidas conservan el valor (RETENIDA)'],
    ['PING))) (cada 10 s)', 'd = t · (331.3 + 0.606·T) / 2;  nivel = (117 − d) / (117 − 12) · 100',
     '7 ecos, grupo coincidente ±3 cm; salto > 8 cm requiere 3 lecturas; distancias imposibles se rechazan'],
    ['YF-S201', 'litros = pulsos / 450 (sin calibrar con recipiente)', 'NO_FLOW 45 s, FLOW_HIGH > 8 L/min'],
    ['DHT22', 'T y HR directas; VPD calculado', 'Lectura cada ≥ 2 s'],
], [1.4, 2.8, 2.5], size=10)
c.p('Las lecturas retenidas o ignoradas no alimentan a la IA ni a la detección de lluvia; la IA descarta riegos que '
    'aparentan bajar la humedad.')
c.h2('Calibraciones')
c.tabla(['Qué', 'Cómo'], [
    ['Tinaco', 'Consola: **TINACO <vacío_cm> <lleno_cm>** (hoy 117 y 12), o Configuración.'],
    ['Caudalímetro', 'Regar 1–2 L a un recipiente medido, anotar pulsos y mL reales: **CALFLUJO <pulsos> <mL>**. Repetir 3 veces.'],
    ['Suelo (FC y WP)', 'Configuración → Calibración del suelo. FC: saturar, tapar y leer a las 24–48 h.'],
    ['Cambio de sensor o sustrato', 'Configuración → **NUEVA VERSIÓN** de datos; la IA reinicia y el historial no se mezcla.'],
], [1.8, 4.9])

c.h1('8. Administración de la Raspberry Pi')
c.tabla(['Tarea', 'Comando o lugar'], [
    ['Entrar por SSH (desde la laptop)', '`ssh -i ~/.ssh/equipo2_pi pi@raspberrypi.local`'],
    ['Ver estado', '`bash ~/equipo2_proyecto/scripts/estado_equipo2.sh`'],
    ['Iniciar / detener', '`bash ~/equipo2_proyecto/scripts/iniciar_equipo2.sh`  ·  `detener_equipo2.sh`'],
    ['Respaldar a mano', '`bash ~/equipo2_proyecto/scripts/respaldar_equipo2.sh` (o RESPALDAR AHORA en la pantalla)'],
    ['Arranque automático', 'Una línea @reboot en el crontab del usuario ejecuta iniciar_equipo2.sh'],
    ['Registros', '`~/equipo2_proyecto/logs/` (nodered.log, mosquitto, telegram.log)'],
    ['Base de datos', '`~/equipo2_proyecto/database/riego_final.db`'],
    ['Diagnóstico desde la laptop', '`python tests/diagnostico_pi.py`'],
    ['Desplegar cambios del dashboard', '`python scripts/desplegar_dashboard_pi.py` (respalda el flujo anterior)'],
], [2.4, 4.3], size=10.5)
c.h2('Tablas principales de la base de datos')
c.tabla(['Tabla', 'Contenido'], [
    ['readings', 'Lecturas cada 10 s: humedad, mV, tinaco, temperatura, HR, VPD, flujo, litros del día, modo, estado'],
    ['irrigation_events / event_ends', 'Cada riego: motivo, litros, pulsos, caudal, humedad antes y después, resultado'],
    ['decisions', 'Decisiones y su justificación'],
    ['alerts', 'Alertas con severidad, estado y confirmación'],
    ['ia_snapshots / ia_observations / predictions', 'Evolución y datos del modelo predictivo'],
    ['weather_fetches / forecast_hourly / forecast_daily / rain_events', 'Clima y eventos de lluvia'],
    ['crops / plantings / stage_changes', 'Cultivos, plantaciones y etapas'],
    ['config_changes / soil_calibration / data_versions', 'Historial de configuración y calibraciones'],
], [2.6, 4.1], size=10)

c.h1('9. Administración del ESP32')
c.tabla(['Tarea', 'Cómo'], [
    ['Identificación', 'ESP32 en servicio: MAC termina en **xx:xx:xx**, identidad `esp32_principal`. El ESP32 viejo (…xx:xx:xx) debe estar apagado.'],
    ['Cargar firmware', 'USB a la laptop → `configs\\CARGAR_FIRMWARE_ESP32.bat COM8` (conserva Wi-Fi y configuración)'],
    ['Consola serial', '`python -m serial.tools.miniterm COM8 115200 --dtr 0 --rts 0 --eol CRLF --encoding utf-8`'],
    ['Configurar Wi-Fi', '`configs\\CONFIGURAR_WIFI_ESP32.bat` o consola **WIFI**. La contraseña se escribe oculta y va directo a la memoria del ESP32.'],
    ['Habilitar potencia', 'Solo por consola: **POWER ON CONFIRMAR** (nunca por MQTT)'],
    ['Prueba interna', '**SELFTEST**: 51/51 pruebas en la última carga'],
], [1.7, 5.0], size=10.5)
c.h2('Comandos de consola más usados')
c.tabla(['Comando', 'Para qué'], [
    ['ESTADO | CONFIG | PINES | AYUDA', 'Estado, parámetros, revisión de pines, lista completa'],
    ['STOP', 'Detiene todo de inmediato'],
    ['MODO MANUAL | MODO AUTO | MODO IA', 'Cambia el modo'],
    ['START <litros>  |  OBJETIVO [%VWC]', 'Riego manual por volumen / hasta una humedad'],
    ['SET <parámetro> <valor>', 'Cambia un parámetro (con validación)'],
    ['TINACO <vacío> <lleno>  |  CALFLUJO <pulsos> <mL>', 'Calibraciones'],
    ['EC5 PRUEBA [s]', 'Excita el EC-5 y muestra los mV'],
    ['CLEAR [ALARMA|ALL]', 'Borra alarmas resueltas'],
    ['IA  |  IA BORRAR CONFIRMAR', 'Estado / reinicio del modelo'],
    ['RED | RED DIAG | WIFI SCAN | RED APLICAR', 'Diagnóstico y reconexión de red'],
    ['REINICIAR', 'Reinicia el ESP32 (no riega al arrancar)'],
], [2.9, 3.8], size=10.5)
c.h2('Protección contra reinicios (firmware del 5 de noviembre de 2026)')
c.p('Con señal Wi-Fi débil (−81 a −87 dBm) el ESP32 se reiniciaba varias veces al día: la tarea de control se quedaba '
    'esperando a que el envío MQTT terminara mientras la conexión se recuperaba, y el vigilante (watchdog) de 5 s la '
    'reiniciaba. El firmware actual corrige esto:')
c.tabla(['Cambio', 'Qué logra'], [
    ['Cola de envío + tarea **mqtt_pub**', 'La tarea de control ya no espera a la red: deja el mensaje en una cola y sigue '
                                          'midiendo y regando. Si la red tarda, solo se retrasa el envío.'],
    ['Registro del vigilante (**wdt_diag**)', 'Antes de un reinicio por vigilante guarda qué tarea y en qué etapa se quedó; '
                                              'al arrancar lo publica como **last_wdt** en el diagnóstico.'],
    ['Horas de secado de la IA cada hora', 'Se guardan en la memoria del ESP32 cada hora (antes cada 6 h), así un reinicio '
                                           'casi no borra lo aprendido.'],
    ['SELFTEST', 'Las 51 pruebas internas pasan con el firmware nuevo (51/51).'],
], [2.3, 4.4], size=10.5)
c.p('Para revisarlo: comando **NET_DIAG** (consola o pantalla de control) y el campo **last_wdt**; en la base de datos, '
    'los reinicios del día son la diferencia entre el valor más alto y el más bajo de **readings.boot**. '
    'Si los reinicios ocurren justo al encender la bomba, la causa es eléctrica: ver diodos, capacitor y relevador en el '
    'manual técnico de instalación.')

c.h1('10. Monitoreo remoto (bot de Telegram)')
c.p('Bot @aquahuerto_equipo2_bot que corre en la Raspberry Pi. Solo hace conexiones de salida y no abre puertos. '
    'Responde a /estado, /riegos, /alertas e /ia; avisa alertas críticas, ESP32 sin datos más de 20 min y envía un '
    'resumen diario a las 20:30. Solo atiende a los chats autorizados.')
c.h2('Cambiar el modo desde Telegram')
c.p('**/modo** muestra el modo actual con un botón por modo; **/modo automatico**, **/modo manual** o **/modo ia** van '
    'directo a la confirmación. El bot pide **Sí, cambiar / Cancelar** (la confirmación vence a los 2 minutos), publica '
    'el mismo SET_MODE que la pantalla en el broker local (127.0.0.1:1884, usuario de administración del proyecto) y '
    'solo informa **CONFIRMADO** cuando llega el ACK del ESP32; sin ACK en 15 s no cambia nada. El bot **no puede '
    'regar** ni limpiar fallas. Cada cambio queda en `logs/telegram.log`.')
c.h2('Instalación')
c.pasos([
    'Conectar la laptop a RouterHuerto1.',
    'Ejecutar `python scripts/instalar_bot_telegram_pi.py` y pegar el token de @BotFather cuando lo pida (no se muestra).',
    'Mandar /start al bot y confirmar el nombre. Con `--agregar` se autorizan más personas o un grupo.',
])

c.h1('11. Solución de problemas')
c.tabla(['Síntoma', 'Diagnóstico', 'Acción'], [
    ['Pantalla no abre', '¿Está en RouterHuerto1? ¿Responde raspberrypi.local:1881?', 'estado_equipo2.sh; reiniciar con iniciar_equipo2.sh'],
    ['ESP32 sin conexión', 'Señal Wi-Fi (−78 a −94 dBm en el gabinete), alimentación', 'Consola RED DIAG; acercar router o reubicar antena'],
    ['TIMEOUT en órdenes', 'MQTT caído o ESP32 fuera de línea', 'Chips de cabecera; revisar broker 1884'],
    ['REJECTED', 'Orden inválida en ese estado', 'Leer el motivo (p. ej. riego manual fuera de MANUAL)'],
    ['No riega en automático', 'Ver la decisión en la página Automático', 'Actuar según el código (sección 6)'],
    ['SAFETY_TRIP o reinicios al conmutar', 'Picos de la bomba', 'Diodos, capacitor y relevador de potencia (manual técnico del equipo)'],
    ['Humedad RETENIDA por horas', 'EC-5 intermitente', 'EC5 PRUEBA; revisar jack y empalmes'],
    ['Tinaco SIN_ECO / INESTABLE', 'Montaje del ultrasónico', 'Tapa puesta, sensor centrado; recalibrar si se movió'],
], [1.8, 2.5, 2.4], size=10)
c.guardar('Manual_Tecnico_Sistema_de_Control_AquaHuerto.docx')


# ================================================================== INSTALACIÓN FÍSICA
e = Manual('Manual técnico de instalación y mantenimiento',
           'Hidráulica, electricidad, sensores, montaje, pruebas y fallas',
           os.path.join(IMG, 'p_linea_marcada.jpg'), etiqueta=T)
e.indice()

e.h1('1. Alcance y seguridad')
e.p('Este manual es para quien **instale, repare, mueva o mantenga** el equipo físico. Describe cada componente, las '
    'conexiones exactas, las calibraciones y los procedimientos de montaje, prueba y diagnóstico.')
e.caja('Seguridad eléctrica', [
    'La batería es de 12 V y la bomba consume 6 A. Un corto puede quemar cables, derretir plástico o dañar el ESP32.',
    'Los pines del ESP32 son de **3.3 V**. Nunca conectar 5 V o 12 V a un pin de señal, ni cargas al puerto USB.',
    'Antes de intervenir: **DETENER TODO** y modo **MANUAL** en la pantalla, desconectar el panel y después la batería '
    '(negativo primero), y cerrar la llave azul.',
    'Ningún diodo, capacitor o fusible se coloca al revés: un diodo invertido hace corto al encender la carga.',
], color=ROJO_HEX, fondo='FBEBEB')

e.h1('2. Componentes')
e.tabla(['Sistema', 'Componente', 'Especificación', 'Función'], [
    ['Control', 'ESP32-D0WD-V3 en placa de expansión', '240 MHz, 4 MB; puente CP210x (COM8); jack 6.5–16 V', 'Control, sensores, red'],
    ['Potencia', 'Módulo 2 relés Songle SRD-05VDC-SL-C', 'Bobina 5 V; contactos 10 A resistivos, **3 A inductivos** a 28 VDC', 'K1 bomba, K2 válvula'],
    ['Hidráulica', 'Bomba de diafragma GOOD PUMPS', '12 V, 6 A, 72 W, 6 L/min máx., presostato', 'Impulsar el agua'],
    ['Hidráulica', 'Electroválvula KING SHENG', '12 VDC, normalmente cerrada, pilotada (requiere presión), ½"', 'Abrir y cerrar la línea'],
    ['Medición', 'Caudalímetro YF-S201', '1–30 L/min, ≤ 1.75 MPa, Hall, 5–18 V', 'Pulsos → litros'],
    ['Sensor', 'METER EC-5', '2.5–3.6 V, salida analógica', 'Humedad volumétrica del suelo'],
    ['Sensor', 'Parallax PING))) #28015', '5 V, 2 cm – 3 m, un pin de señal', 'Nivel del tinaco'],
    ['Sensor', 'DHT22 / AM2302', '3.3 V, bus de un hilo', 'Temperatura y humedad del aire'],
    ['Energía', 'Panel Firstech FE-50WP', '50 W, Vmp 17.4 V, Imp 2.87 A', 'Generación'],
    ['Energía', 'Batería Mighty Max ML9-12', '12 V, 9 Ah, SLA; no bajar de 10.5 V; reemplazo cada 3–5 años', 'Almacenamiento'],
    ['Energía', 'Controlador solar PWM con pantalla', 'Corriente nominal no identificada', 'Carga y protección'],
], [0.9, 1.9, 2.5, 1.4], size=9.5)
e.fotos([(os.path.join(IMG, 't_esp32.jpg'), 'ESP32 en placa de expansión'),
         (os.path.join(IMG, 't_reles.jpg'), 'Módulo de 2 relés'),
         (os.path.join(IMG, 't_dht22.jpg'), 'DHT22')], alto=1.9)
e.fotos([(os.path.join(IMG, 't_ping.jpg'), 'Ultrasónico PING)))'),
         (os.path.join(IMG, 't_medidor.jpg'), 'Caudalímetro YF-S201'),
         (os.path.join(IMG, 'p_valvula.jpg'), 'Electroválvula')], alto=1.7)
e.fotos([(os.path.join(IMG, 'p_bomba.jpg'), 'Bomba (caja del fabricante)'),
         (os.path.join(IMG, 't_bateria.jpg'), 'Batería ML9-12 (advertencias)')], alto=1.7)

e.h1('3. Sistema hidráulico')
e.p('Recorrido: tinaco → salida de ½" con válvula de esfera (llave azul) → bomba → caudalímetro → electroválvula NC → '
    'tubo PPR verde de 20 mm → cruz → 3 mangueras con 3 microaspersores cada una (9) y tapón al final.')
e.imagen(os.path.join(IMG, 'p_linea_marcada.jpg'), ancho=6.0,
         pie='Tubería de prueba armada en el banco. El agua corre de derecha a izquierda.')
e.imagen(os.path.join(REP, 'epanet_red.png'), ancho=6.2, pie='Modelo hidráulico en EPANET 2.2 (diseño, escenario de subida vertical).')
e.tabla(['Dato', 'Valor'], [
    ['Tinaco', 'Ø ≈ 0.90 m; ≈ 6.3 L por cm; capacidad útil estimada ≈ 650 L'],
    ['Sensor del tinaco', 'A 127 cm del piso; vacío = 117 cm, lleno = 12 cm (distancia sensor → agua)'],
    ['Caudal medido', '1.7 a 3.0 L/min según la fecha (por pulsos)'],
    ['Diseño EPANET', '30 L/h por aspersor (4.5 L/min); ~2.1 bar en aspersores con curva de bomba provisional'],
], [1.8, 4.9], size=10.5)
e.h2('Buenas prácticas')
e.doc.paragraphs[-1].paragraph_format.page_break_before = True
e.checklist([
    'Bomba, caudalímetro y electroválvula tienen **flecha de sentido**: verificar antes de apretar.',
    'Cinta teflón en roscas; apretar a mano más un cuarto de vuelta (plástico).',
    'La electroválvula tiene un **filtro de malla** en la entrada: limpiarlo si baja el caudal.',
    'Tras vaciar el tinaco o abrir la línea, purgar con un riego manual corto de 0.5 L.',
    'Antes de heladas, vaciar bomba, caudalímetro y válvula.',
])
e.fotos([(os.path.join(IMG, 't_valvula_filtro.jpg'), 'Filtro de malla en la entrada de la electroválvula')], alto=1.8)

e.h1('4. Sistema eléctrico')
e.h2('Conexiones de control (ESP32)')
e.tabla(['Función', 'GPIO', 'Conecta a', 'Nota'], [
    ['Relé de la bomba', '26', 'IN1 del módulo', 'Activo en BAJO'],
    ['Relé de la válvula', '27', 'IN2 del módulo', 'Activo en BAJO'],
    ['Alimentación del módulo', '5V / GND', 'VCC / GND del módulo', 'Puente JD-VCC ↔ VCC puesto'],
    ['Caudalímetro', '19', 'Cable amarillo', 'Contador por hardware (PCNT), pull-up, filtro 10 µs'],
    ['Ultrasónico', '18', 'SIG', 'Divisor 1 kΩ / 2 kΩ hacia 3.3 V; alimentación 5 V'],
    ['DHT22', '4', 'out', 'Alimentación 3.3 V'],
    ['EC-5 excitación', '25', 'Cable blanco (punta del jack)', 'Pulso de 10 ms'],
    ['EC-5 señal', '34', 'Cable rojo (anillo del jack)', 'ADC1, 12 dB, 1 MΩ a GND'],
    ['EC-5 tierra', 'GND', 'Cable sin forro (manga del jack)', ''],
], [1.7, 0.8, 2.1, 2.1], size=10)
e.h2('Conexiones de potencia (estado actual)')
e.tabla(['Carga', 'Conexión'], [
    ['Bomba', 'Relé K1, bornes COM → NO'],
    ['Electroválvula', 'Relé K2, bornes COM → NO'],
    ['ESP32', 'Jack de la placa de expansión (6.5–16 V)'],
    ['Bornes NC', 'Sin conectar: sin alimentación, todo queda apagado'],
], [1.8, 4.9])
e.caja('Identificar COM, NO y NC', ['Con el módulo sin energía y el multímetro en continuidad, el par que suena es COM–NC. '
                                    'Al activar el relé (clic), el par que suena es COM–NO. El borne común es COM.'],
       color=AZUL_HEX, fondo='E7F1FB')
e.h2('Mejora recomendada de la etapa de potencia')
e.doc.paragraphs[-1].paragraph_format.page_break_before = True
e.p('El relé del módulo soporta 3 A inductivos y la bomba consume 6 A con una corriente de arranque desconocida. Se '
    'observaron reinicios del ESP32 al conmutar la bomba. Se recomienda:')
e.tabla(['Elemento', 'Ubicación', 'Detalle'], [
    ['Relé automotriz 12 V, 30/40 A', 'K1 acciona su bobina (86–85); el contacto 30 → 87 alimenta la bomba', 'El SRD solo maneja la bobina'],
    ['Fusible F1 15 A', 'Positivo de la batería, a menos de 20 cm', 'Protege el cableado'],
    ['Fusible F2 10 A', 'Rama de la bomba', 'Cable ≥ 16 AWG'],
    ['Fusible F3 3 A', 'Rama de mando y válvula', ''],
    ['Diodo D1 1N4007', 'En la bobina del relé automotriz', 'Franja (cátodo) al positivo'],
    ['Diodo D2 1N4007', 'En la electroválvula', 'Franja al positivo'],
    ['Diodo D3 Schottky ≥ 5 A (p. ej. SB560)', 'En la bomba', 'Franja al positivo'],
    ['Capacitor 470–1000 µF', 'Entrada de alimentación del ESP32', 'Respetar polaridad'],
    ['Interruptor de corte manual', 'Línea de la bomba', 'Corte aunque un relé se pegue'],
], [2.0, 2.6, 2.1], size=10)
e.p('Con un módulo MOSFET en lugar de relé, la lógica pasa a activo en ALTO y hay que ajustar el firmware.', size=10.5, color=GRIS)

e.h1('5. Sensores: instalación y calibración')
e.tabla(['Sensor', 'Instalación', 'Verificación y calibración'], [
    ['EC-5', 'Vertical, toda la parte plana bajo tierra y sin huecos de aire. Empalmes secos y aislados. '
             'Sacarlo jalando del cuerpo.',
     'Consola **EC5 PRUEBA**: ≈ 375 mV al aire, 515–600 mV en el sustrato. Cambio permanente de lugar → NUEVA VERSIÓN de datos.'],
    ['PING)))', 'En su caja acrílica sobre la tapa, a 127 cm del piso, centrado y apuntando hacia abajo. Tapa siempre puesta.',
     'Si cambia la altura o el tinaco: medir vacío y lleno y ejecutar **TINACO <vacío> <lleno>**.'],
    ['YF-S201', 'Entre la bomba y la electroválvula, flecha hacia el cajón.',
     '450 p/L provisional. Calibrar: 1–2 L a recipiente medido, **CALFLUJO <pulsos> <mL>**, 3 repeticiones.'],
    ['DHT22', 'A la sombra y ventilado; mide el aire, no el suelo.', 'Comparar con la temperatura de Open-Meteo en la página Clima.'],
], [1.0, 2.9, 2.8], size=10)

e.h1('6. Montaje, desmontaje y puesta en marcha')
e.h2('Desmontaje')
e.checklist([
    'Pantalla: DETENER TODO y modo MANUAL.',
    'Fotos de todas las conexiones y etiquetas en cada cable (por ejemplo "GPIO 26 → IN1").',
    'Desconectar el panel del controlador y después la batería (negativo primero).',
    'Cerrar la llave azul; desconectar mangueras y vaciar bomba, caudalímetro y válvula.',
    'Retirar el EC-5 por el cuerpo; guardar sensores y ESP32 secos.',
    'Si se mueve el tinaco, vaciarlo antes (lleno pesa más de 600 kg).',
])
e.h2('Montaje y puesta en marcha')
e.checklist([
    'Tubería: flechas hacia el cajón, teflón en roscas, sin fugas al llenar.',
    'Cableado según las tablas de la sección 4; ningún 12 V cerca de pines del ESP32.',
    'Conectar la batería al controlador (positivo y luego negativo) y después el panel.',
    'EC-5 enterrado, ultrasónico centrado, tapa puesta, tinaco lleno, llave azul abierta.',
    'Pantalla: ESP32 en línea y MQTT conectado; humedad y tinaco con valores lógicos.',
    'Consola: **SELFTEST** sin fallas y **POWER ON CONFIRMAR** si las salidas aparecen deshabilitadas.',
    'Riego manual de 0.5 L: sale agua, aparece el caudal, no hay fugas ni reinicios.',
    'Recalibrar el tinaco si cambió la altura; regresar a AUTOMÁTICO.',
])

e.h1('7. Diagnóstico de fallas')
e.tabla(['Síntoma o alarma', 'Causa probable', 'Acción'], [
    ['NO_FLOW', 'Tinaco vacío, llave cerrada, aire, manguera doblada, válvula sin presión', 'Llenar, abrir, purgar; revisar filtro de la válvula'],
    ['FLOW_WHEN_IDLE / agua sin parar', 'Relé pegado o válvula atorada', 'Cerrar llave azul; limpiar válvula o cambiar relé'],
    ['FLOW_HIGH', 'Manguera suelta o pulsos erráticos', 'Revisar uniones y cable amarillo'],
    ['PUMP_TIMEOUT', 'Caudal bajo', 'Aspersores tapados, filtro sucio, voltaje bajo'],
    ['SAFETY_TRIP / REBOOT_DURING_WATERING', 'Picos inductivos o caída de voltaje', 'Instalar diodos, capacitor y relé de potencia; revisar batería'],
    ['LED del relé enciende y la bomba no', 'No llegan 12 V', 'Bornes COM/NO, fusible, batería (< 10.5 V)'],
    ['LED del relé no enciende', 'Señal o 5 V del módulo', 'GPIO 26/27, VCC y GND del módulo'],
    ['Relés con clics rápidos', 'EC-5 en corto o húmedo (señal a 3.1 V)', 'Secar y aislar empalmes del EC-5'],
    ['SOIL_SENSOR', 'Jack mal insertado o cable roto', 'EC5 PRUEBA; revisar blanco, rojo y sin forro'],
    ['TANK_SENSOR / SIN_ECO', 'Tapa quitada, sensor chueco, cable SIG', 'Centrar, tapar, revisar divisor 1 k / 2 k'],
    ['ENV_SENSOR', 'Cable del DHT22', 'Revisar +, out y −'],
    ['COMMS frecuente', 'Señal −84 a −94 dBm en el gabinete', 'Antena fuera de metal y lo más alta posible; acercar router'],
], [1.9, 2.3, 2.5], size=10)

e.h1('8. Mantenimiento preventivo')
e.tabla(['Frecuencia', 'Actividad'], [
    ['Semanal', 'Nivel del tinaco (llenar bajo 20 % o bajo la mitad), fugas, aspersores, gabinete seco, pantalla sin fallas'],
    ['Mensual', 'Limpiar panel solar; revisar bornes y conectores (óxido); voltaje de batería en el controlador; empalmes del EC-5'],
    ['Cada 3 meses', 'Limpiar filtro de la electroválvula y aspersores; revisar presión y caudal (comparar con 1.7–3 L/min)'],
    ['Cada temporada', 'Calibrar el caudalímetro; limpiar el tinaco; vaciar la línea antes de heladas'],
    ['Cada 3–5 años', 'Reemplazar la batería (indicado por el fabricante)'],
], [1.4, 5.3])
e.guardar('Manual_Tecnico_Instalacion_AquaHuerto.docx')
