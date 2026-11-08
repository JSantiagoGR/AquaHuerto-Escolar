"""Manuales de USO de AquaHuerto (personal de la escuela, sin tecnicismos ni emojis)."""
import os

from docx.enum.text import WD_ALIGN_PARAGRAPH

from manual_base import Manual, IMG, OLD, REP, GRIS, AZUL_HEX, ROJO_HEX, NARANJA_HEX

# ================================================================== MANUAL DEL DASHBOARD
m = Manual('Manual de la pantalla de control',
           'Cómo revisar el huerto y regar desde la computadora o el celular',
           os.path.join(OLD, 'd_inicio_panel.jpg'), equipo=True)

m.h1('Antes de empezar')
m.p('El huerto tiene un sistema que **riega solo**. Mide qué tan mojada está la tierra y, cuando hace falta, '
    'enciende la bomba y riega la cantidad justa.')
m.p('La **pantalla de control** sirve para ver cómo está el huerto y, si alguna vez es necesario, regar a mano. '
    'En el día a día **no tiene que hacer nada**: solo revisar de vez en cuando.')
m.caja('Tres reglas fáciles', [
    '1.  Deje el sistema en modo **AUTOMÁTICO**. Así riega solo.',
    '2.  Si algo se ve mal, presione [[DETENER TODO]]. Apaga el agua al instante y no hace daño.',
    '3.  No cambie nada en la página **Configuración**. Si tiene dudas, llame a la persona responsable.',
])
m.h2('Cómo entrar a la pantalla')
m.pasos([
    'Conecte su celular o computadora a la red Wi-Fi **RouterHuerto1**. La contraseña se la da la persona responsable.',
    'Abra el navegador (Chrome, Edge o Safari).',
    'En la barra de dirección escriba: **raspberrypi.local:1881/dashboard** y presione Entrar.',
    'Guarde la página en favoritos para no tener que escribirla otra vez.',
])
m.caja('Importante', ['La pantalla solo abre si está conectado a la red **RouterHuerto1**. Desde otra red no funciona: '
                      'es así por seguridad.'], color=AZUL_HEX, fondo='E7F1FB')
m.p('A la izquierda hay un menú con varias páginas. Usted solo necesita tres: **Inicio**, **Manual** y **Alertas**.')

m.h1('La página Inicio')
m.p('Es la primera página. Aquí ve de un vistazo si el huerto está bien y puede regar rápidamente.')
m.imagen(os.path.join(IMG, 'inicio_marcada.jpg'), pie='Página Inicio. Los números rojos se explican en la tabla.')
m.tabla(['', 'Qué es', 'Para qué sirve'], [
    [1, 'Dispositivo', 'Debe decir **esp32_principal**. Si dice otra cosa, elíjalo en la lista.'],
    [2, 'Modo activo', 'Dice si el sistema riega solo (**AUTOMÁTICO**) o solo cuando usted lo pide (**MANUAL**).'],
    [3, 'Humedad del suelo', 'Qué tan mojada está la tierra. Vea los colores en la página siguiente.'],
    [4, 'Volumen objetivo', 'Barra para elegir cuánta agua regar (en mililitros; 1000 mL = 1 litro).'],
    [5, 'INICIAR RIEGO', 'Riega la cantidad elegida en la barra. Le pedirá confirmar.'],
    [6, 'DETENER BOMBA', 'Apaga el agua al instante. No pide confirmación.'],
], [0.45, 1.7, 4.55], numerada=True)
m.caja('Los cuadros de colores de arriba', [
    '**Verde** = todo bien.   **Rojo** = algo no está conectado; si sigue así más de una hora, avise a la persona responsable.',
    'Más abajo en la página hay un resumen con la humedad, el agua del tinaco y los litros regados hoy.',
])

m.h1('¿Cómo está la tierra?')
m.p('En la página Inicio hay una **barra de colores**. Una rayita negra marca la humedad de la tierra en este momento.')
m.imagen(os.path.join(REP, 'banda_recorte.png'), pie='Barra de humedad de la tierra.')
m.tabla(['Color', 'Qué significa', 'Qué hacer'], [
    ['**Rojo**', 'La tierra está muy seca.', 'Nada: el sistema riega solo enseguida. Si sigue en rojo varias horas, avise.'],
    ['**Naranja**', 'La tierra está algo seca.', 'Nada: riega en el siguiente horario.'],
    ['**Verde**', 'La tierra está bien.', 'Nada. Así debe estar casi siempre.'],
    ['**Azul**', 'La tierra está húmeda.', 'Nada: el sistema no riega.'],
    ['**Morado**', 'La tierra tiene demasiada agua.', 'No riegue a mano. Si no llovió, avise a la persona responsable.'],
], [1.2, 2.4, 3.1])
m.h2('¿Cuándo riega solo?')
m.p('En modo AUTOMÁTICO riega **por la mañana (6:00 a 9:00)** y **por la tarde (18:00 a 20:00)**, nunca al mediodía. '
    'Riega poco a poco, en tragos de 1.5 litros, y espera a que el agua baje antes de volver a medir. '
    'Si la tierra se seca demasiado, riega a cualquier hora.')

m.h1('El agua del tinaco')
m.p('El sistema riega con el agua del tinaco, así que **hay que llenarlo de vez en cuando**. Un sensor sobre la tapa '
    'mide cuánta agua queda y la pantalla lo muestra.')
m.h2('Dónde ver cuánta agua queda')
m.p('En la página **Inicio**, baje al **Resumen** y busque el cuadro **Nivel del tinaco**. Dice el porcentaje de agua: '
    '100 % es lleno y 0 % es vacío.')
m.tabla(['Si la pantalla dice...', 'Qué significa', 'Qué hacer'], [
    ['**Más de 50 %**', 'Hay agua suficiente.', 'Nada.'],
    ['**Entre 20 y 50 %**', 'El agua se está acabando.', 'Planee llenarlo esta semana.'],
    ['**Menos de 20 %**', 'Queda muy poca agua. Aparece el aviso **Nivel bajo del tinaco**.', '**Llénelo hoy.**'],
    ['**Sin lectura** o un número que no cambia', 'El sensor no puede medir (por ejemplo, la tapa está quitada).',
     'Abra el tinaco y vea el agua con sus propios ojos.'],
], [1.9, 2.5, 2.3])
m.caja('Cada cuánto llenarlo', [
    'Depende del clima y de cuánto riegue: con calor se usa más agua. El sistema riega como máximo 30 litros al día, '
    'así que un tinaco lleno dura **por lo menos unas 3 semanas**.',
    'Revise el nivel **una vez por semana**. Si no puede ver la pantalla, abra la tapa y mire el agua.',
])
m.caja('Si el tinaco se vacía', ['El sistema se detiene solo para cuidar la bomba y aparece **SISTEMA EN FALLA**. Llene '
                                 'el tinaco y después presione [[LIMPIAR FALLA]].'], color=NARANJA_HEX, fondo='FDF0E6')
m.p('Los pasos para llenarlo están en el **Manual del equipo**, sección **Llenar el tinaco**.')

m.h1('Regar a mano')
m.p('Use la página **Manual** solo si la persona responsable se lo pide o si quiere regar algo extra.')
m.imagen(os.path.join(IMG, 'manual_marcada.jpg'), pie='Página Manual.')
m.tabla(['', 'Qué es', 'Para qué sirve'], [
    [1, 'MODO MANUAL ACTIVO', 'Indica que el sistema está en manual. Para regar a mano debe estar así.'],
    [2, 'Litros', 'Escriba cuántos litros quiere regar (por ejemplo 1).'],
    [3, 'REGAR', 'Riega los litros escritos. Le pedirá confirmar.'],
    [4, 'Humedad deseada', 'Opcional: escriba hasta qué número quiere mojar la tierra.'],
    [5, 'REGAR HASTA', 'Riega poco a poco hasta llegar a ese número.'],
    [6, 'DETENER TODO', 'Apaga el agua al instante. Úselo ante cualquier duda.'],
], [0.45, 1.9, 4.35], numerada=True)
m.h2('Paso a paso')
m.doc.paragraphs[-1].paragraph_format.page_break_before = True
m.pasos([
    'Abra la página **Manual** en el menú de la izquierda.',
    'Escriba los litros (casilla 2) y presione [[REGAR]].',
    'Si el sistema estaba en automático, le preguntará si quiere cambiar a manual: presione [[CONFIRMAR]].',
    'Confirme el riego con [[CONFIRMAR]]. Verá cómo avanza el riego en la misma página.',
    'Al terminar aparece el aviso **EL SISTEMA QUEDÓ EN MANUAL**. Presione [[REGRESAR A AUTOMÁTICO]].',
])
m.caja('No olvide el paso 5', ['Si deja el sistema en MANUAL, **el huerto ya no se riega solo**. Siempre regrese a '
                               'AUTOMÁTICO al terminar.'], color=ROJO_HEX, fondo='FBEBEB')

m.h1('Avisos que pueden aparecer')
m.p('A veces aparece un recuadro de color arriba de la página. Esto es lo que significa cada uno:')
m.tabla(['Aviso', 'Qué significa', 'Qué hacer'], [
    ['**SISTEMA EN FALLA**', 'El sistema se detuvo para protegerse (por ejemplo, el tinaco se quedó sin agua).',
     'Revise que el tinaco tenga agua y presione [[LIMPIAR FALLA]]. Si el aviso vuelve a salir, llame a la persona responsable.'],
    ['**EL SISTEMA QUEDÓ EN MANUAL**', 'Se regó a mano y el sistema ya no riega solo.',
     'Presione [[REGRESAR A AUTOMÁTICO]].'],
    ['**MÁXIMO DIARIO ALCANZADO**', 'Hoy ya se regaron 30 litros, que es el límite del día.',
     'Normalmente nada. Solo si la persona responsable lo indica, presione [[PERMITIR RIEGO EXTRA]].'],
    ['**CONFIRMADO por el dispositivo**', 'La orden se cumplió.', 'Nada.'],
    ['**TIMEOUT** o **REJECTED**', 'La orden no se cumplió.', 'Espere un minuto e intente otra vez. Si se repite, avise.'],
], [2.0, 2.3, 2.4], size=10.5)
m.h2('Cambiar el modo')
m.p('En la página Inicio, presione [[SELECCIONAR MODO]], elija el modo y presione [[CONFIRMAR]]. '
    'Espere el mensaje **CONFIRMADO por el dispositivo**.')
m.tabla(['Modo', 'Qué hace', '¿Cuándo usarlo?'], [
    ['**AUTOMÁTICO**', 'Riega solo, según la humedad de la tierra.', 'Siempre. Es el modo normal.'],
    ['**MANUAL**', 'Solo riega cuando usted lo pide.', 'Solo mientras riega a mano o hay mantenimiento.'],
    ['**IA**', 'Riega solo y aprende de los riegos anteriores.', 'Solo si la persona responsable lo indica.'],
], [1.4, 2.8, 2.5])

m.h1('La página Alertas')
m.p('Si la tierra se moja sin que el sistema haya regado (por lluvia o porque alguien regó con manguera), la '
    'pantalla pregunta qué pasó. Contestar ayuda a que el sistema aprenda bien.')
m.imagen(os.path.join(IMG, 'alertas_marcada.jpg'), pie='Página Alertas. En el recuadro 1 se elige qué pasó.')
m.pasos([
    'Abra la página **Alertas** en el menú.',
    'Busque los avisos **POSIBLE LLUVIA** o **POSIBLE RIEGO EXTERNO**.',
    'Presione lo que pasó: [[FUE LLUVIA|1565C0]], [[RIEGO EXTERNO|1565C0]], [[ERROR DEL SENSOR|1565C0]] u [[OTRA CAUSA|1565C0]].',
])

m.h1('Botones que no debe usar')
m.p('Estos botones cambian cómo funciona el sistema. **Solo la persona responsable** debe usarlos:')
m.tabla(['Dónde está', 'Botón', 'Por qué no usarlo'], [
    ['Página Configuración', 'Todos', 'Cambian calibraciones y ajustes del sistema.'],
    ['Página IA', '[[REINICIAR MODELO|616161]]', 'Borra todo lo que el sistema ha aprendido.'],
    ['Página Automático', '[[GUARDAR|616161]]', 'Cambia los horarios y las cantidades de riego.'],
    ['Página Cultivos', '[[GUARDAR COMO CULTIVO ACTIVO|616161]]', 'Cambia la planta para la que se riega.'],
], [1.8, 2.5, 2.4], size=11)
m.caja('Si presionó algo por error', ['Casi todos los botones piden confirmar. Si aparece una ventana que no esperaba, '
                                      'presione [[CANCELAR|616161]] y no se cambia nada.'], color=AZUL_HEX, fondo='E7F1FB')
m.p('La persona responsable encontrará cómo usar estos botones en el **Manual técnico del sistema de control**.')

m.h1('Resumen en una hoja')
m.tabla(['Si quiere...', 'Haga esto'], [
    ['Ver si el huerto está bien', 'Abra **Inicio** y vea la barra de colores: verde es bien.'],
    ['Regar a mano', '**Manual**, escriba los litros, [[REGAR]], [[CONFIRMAR]] y al final [[REGRESAR A AUTOMÁTICO]].'],
    ['Apagar el agua de inmediato', '[[DETENER TODO]] (o [[DETENER BOMBA]] en Inicio).'],
    ['Quitar un aviso de falla', 'Revise el tinaco y presione [[LIMPIAR FALLA]]. Si vuelve, llame al responsable.'],
    ['Avisar que llovió', '**Alertas** y presione [[FUE LLUVIA|1565C0]].'],
    ['Saber si hay que llenar el tinaco', '**Inicio**, cuadro **Nivel del tinaco**: con menos de 20 % llénelo hoy.'],
    ['Que el sistema riegue solo', 'Debe decir **Modo activo: AUTOMÁTICO**.'],
], [2.4, 4.3])
m.guardar('Manual_Pantalla_de_Control_AquaHuerto.docx')


# ================================================================== MANUAL DE INSTALACIÓN
f = Manual('Manual del equipo',
           'Qué es cada parte, cómo revisarla y qué hacer si algo falla',
           os.path.join(REP, 'diagrama_sistema.png'), equipo=True)

f.h1('Antes de empezar')
f.p('Este manual explica **qué es cada parte** del sistema de riego, **cómo revisarlo** cada semana y **qué hacer** '
    'si algo falla. No hace falta saber de electrónica.')
f.caja('Por seguridad', [
    'No abra el gabinete blanco ni desconecte cables. Eso lo hace la persona responsable.',
    'No moje el gabinete ni lo abra cuando llueve.',
    'No deje que la bomba funcione sin agua en el tinaco.',
    'Si ve humo, chispas o un cable dañado, siga los pasos de **Apagar en una emergencia**.',
], color=ROJO_HEX, fondo='FBEBEB')
f.h2('Cómo funciona, en pocas palabras')
f.pasos([
    'Un **sensor enterrado** en el cajón mide qué tan mojada está la tierra.',
    'Una pequeña computadora dentro del **gabinete blanco** decide si hace falta regar.',
    'Si hace falta, abre la **válvula eléctrica** y enciende la **bomba**, que saca agua del **tinaco** y la lleva a los **aspersores** del cajón.',
    'Un **panel solar** carga la batería que da energía a todo.',
])

f.h1('Las partes del sistema')
f.fotos([(os.path.join(OLD, 'f_cajon.jpg'), 'Cajón de cultivo'),
         (os.path.join(OLD, 'f_tinaco_salida.jpg'), 'Salida del tinaco y llave azul'),
         (os.path.join(OLD, 'f_ultrasonico.jpg'), 'Sensor del tinaco'),
         (os.path.join(OLD, 'f_gabinete.jpg'), 'Gabinete blanco')], alto=1.4)
f.fotos([(os.path.join(IMG, 'p_bomba.jpg'), 'Bomba (foto de su caja)'),
         (os.path.join(IMG, 'p_medidor.jpg'), 'Medidor de agua'),
         (os.path.join(IMG, 'p_valvula.jpg'), 'Válvula eléctrica')], alto=1.4)
f.tabla(['Parte', 'Para qué sirve', 'Cuidado'], [
    ['**Tinaco**', 'Guarda el agua para regar.', 'Debe tener agua y la **tapa puesta**.'],
    ['**Llave azul**', 'Abre o cierra la salida del tinaco.', 'Normalmente **abierta**. Ciérrela solo en una emergencia o reparación.'],
    ['**Sensor del tinaco**', 'Mide cuánta agua queda (caja transparente sobre la tapa).', 'No lo mueva ni lo tape.'],
    ['**Bomba, válvula y medidor de agua**', 'Empujan el agua, la dejan pasar solo al regar y cuentan los litros.',
     'Vea la página **Bomba, válvula y medidor de agua**.'],
    ['**Aspersores**', 'Riegan el cajón (9 en total, en 3 mangueras).', 'Que no estén tapados con tierra.'],
    ['**Sensor de humedad**', 'Enterrado en el cajón; mide la humedad de la tierra.', 'No lo saque ni lo pise. Al trabajar la tierra, rodéelo.'],
    ['**Gabinete blanco**', 'Tiene la computadora, la batería y el cargador solar.', 'Siempre cerrado y seco.'],
    ['**Panel solar**', 'Carga la batería con el sol.', 'Limpio y sin sombra.'],
], [1.6, 2.6, 2.5], size=11)

f.h1('Bomba, válvula y medidor de agua')
f.p('Estas tres piezas están en la tubería, entre el tinaco y el cajón. Trabajan juntas cada vez que el sistema riega.')
f.h2('El camino del agua')
f.p('El agua sale del **tinaco** por la **llave azul**, la **bomba** la empuja, el **medidor de agua** cuenta los litros, '
    'la **válvula eléctrica** se abre para dejarla pasar y llega a los **aspersores** del cajón.')
f.imagen(os.path.join(IMG, 'p_linea_marcada.jpg'), ancho=5.6,
         pie='Las tres piezas en la tubería de prueba, antes de instalarla. El agua corre de derecha a izquierda.')
f.tabla(['Pieza', 'Qué hace', 'Cómo saber que funciona', 'Cuidado'], [
    ['**Bomba**', 'Empuja el agua del tinaco hacia el cajón. Funciona con 12 voltios.',
     'Se escucha un zumbido mientras riega. En la pantalla dice **Bomba ENCENDIDA**.',
     'Nunca debe funcionar sin agua: se daña. Si suena pero no sale agua, presione [[DETENER TODO]].'],
    ['**Válvula eléctrica**', 'Es una compuerta: se abre solo mientras se riega y el resto del tiempo está **cerrada**.',
     'Hace un pequeño "clic" al abrir y al cerrar. En la pantalla dice **Electroválvula ABIERTA**.',
     'Si sale agua con el sistema apagado, puede estar atorada: cierre la **llave azul** y avise.'],
    ['**Medidor de agua**', 'Tiene una pequeña rueda que gira con el agua; así el sistema sabe cuántos litros regó.',
     'Mientras riega, la pantalla muestra el **caudal** (litros por minuto) y los litros entregados.',
     'Tiene una **flecha**: debe apuntar hacia donde va el agua. No lo golpee.'],
], [1.2, 1.8, 1.9, 1.8], size=10.5)
f.caja('Si el sistema se detiene solo', ['Si la bomba enciende pero el medidor no cuenta agua, el sistema la apaga a los '
                                         '45 segundos para protegerla y aparece **SISTEMA EN FALLA**. Casi siempre es '
                                         'porque el tinaco está vacío o la llave azul está cerrada.'],
       color=NARANJA_HEX, fondo='FDF0E6')

f.h1('Revisión de cada semana')
f.p('Toma cinco minutos. Marque cada casilla:')
f.checklist([
    'El tinaco tiene **más de la mitad** de agua (si no, vea **Llenar el tinaco**) y la **tapa está puesta**.',
    'La **llave azul** está abierta.',
    'No hay **fugas** ni charcos cerca de la bomba o de las mangueras.',
    'Los **aspersores** mojan el cajón de forma pareja.',
    'El **gabinete blanco** está cerrado, sin agua adentro.',
    'El **panel solar** está limpio y sin sombra.',
    'En la pantalla de control la barra de humedad está en **verde** y no hay avisos rojos.',
    'El sensor de humedad sigue **enterrado** en su lugar.',
])
f.h2('Cada mes')
f.checklist([
    'Limpiar el panel solar con un trapo húmedo (sin jabón).',
    'Limpiar la tierra de los aspersores.',
    'Avisar a la persona responsable si el tinaco se vacía muy rápido.',
])
f.caja('En invierno', ['Si se anuncian **heladas** (temperaturas bajo cero), avise a la persona responsable: el agua '
                       'dentro de la bomba puede congelarse y romperla.'], color=AZUL_HEX, fondo='E7F1FB')

f.h1('Llenar el tinaco')
f.p('El tinaco es el que da el agua para regar. **Hay que llenarlo cada cierto tiempo**, según lo que diga la pantalla '
    'o lo que se vea al abrirlo.')
f.h2('Cuándo llenarlo')
f.tabla(['Cómo saberlo', 'Llénelo cuando...'], [
    ['En la pantalla de control (Inicio, cuadro **Nivel del tinaco**)', 'Marque **menos de 20 %**, o aparezca el aviso '
     '**Nivel bajo del tinaco**. Con menos de 50 %, planee llenarlo esa semana.'],
    ['Abriendo la tapa y mirando', 'El agua esté por debajo de **la mitad** del tinaco.'],
], [3.0, 3.7])
f.p('Un tinaco lleno dura **por lo menos unas 3 semanas**; con calor se gasta más rápido. Revíselo **cada semana**.')
f.fotos([(os.path.join(OLD, 'f_ultrasonico.jpg'), 'Sensor sobre la tapa'),
         (os.path.join(OLD, 'f_tinaco_medicion.jpg'), 'Interior del tinaco')], alto=2.6)
f.h2('Pasos para llenarlo')
f.doc.paragraphs[-1].paragraph_format.page_break_before = True
f.pasos([
    'Quite la tapa con cuidado: **el sensor del nivel va pegado a la tapa** (la caja transparente). No lo golpee ni lo moje.',
    'Llene el tinaco con la manguera o la toma de agua de la escuela.',
    'Deje de llenar cuando el agua esté a **unos 15 cm del borde**. No lo llene hasta arriba: el sensor necesita ese espacio.',
    'Vuelva a poner la tapa **igual que estaba**, con el sensor centrado y mirando hacia el agua.',
    'Revise que la **llave azul** de la salida esté abierta.',
    'En la pantalla, revise que el **Nivel del tinaco** haya subido. Si aparece **SISTEMA EN FALLA**, presione [[LIMPIAR FALLA]].',
])
f.caja('Importante', [
    'Mientras la tapa está quitada, la pantalla puede mostrar un nivel raro. Es normal: se corrige al poner la tapa.',
    'Use agua limpia. Si el tinaco tiene lodo o algas en el fondo, avise a la persona responsable para limpiarlo.',
])

f.h1('Si se desconectan los cables del sensor del tinaco')
f.p('El sensor del tinaco (la caja transparente sobre la tapa) tiene **tres cables de colores**. Si al quitar la tapa '
    'o al limpiar se suelta alguno, la pantalla deja de mostrar el nivel del tinaco. Así van conectados:')
f.imagen(os.path.join(IMG, 't_ping_cables_marcada.jpg'), ancho=5.6,
         pie='Conexión correcta del sensor del tinaco. Cada color va en su letrero.')
f.tabla(['Color del cable', 'Va en el pin que dice', 'Para qué es'], [
    ['**Blanco**', '**GND**', 'Tierra (negativo)'],
    ['**Morado**', '**5V**', 'Energía'],
    ['**Azul**', '**SIG**', 'Señal de la medición'],
], [2.0, 2.2, 2.5])
f.pasos([
    'Antes de conectar, presione [[DETENER TODO]] en la pantalla de control.',
    'Busque los letreros **GND, 5V y SIG** impresos en la tarjeta azul del sensor.',
    'Conecte cada cable en su pin, como en la foto: **blanco arriba, morado en medio, azul abajo**.',
    'Empuje el conector hasta que entre completo y no quede flojo.',
    'Vuelva a poner la tapa con el sensor centrado y revise en la pantalla que el **Nivel del tinaco** aparezca otra vez.',
])
f.caja('Cuidado', ['Si los cables quedan en otro orden, el sensor no mide y puede dañarse. Revise los colores dos veces '
                   'antes de poner la tapa.'], color=NARANJA_HEX, fondo='FDF0E6')

f.h1('Apagar en una emergencia')
f.p('Use estos pasos si hay una **fuga grande**, **sale agua sin parar**, ve **humo o chispas**, o un cable está dañado.')
f.pasos([
    'En la pantalla de control presione [[DETENER TODO]] (o [[DETENER BOMBA]] en Inicio).',
    'Cierre la **llave azul** de la salida del tinaco.',
    'Si hay humo o chispas, aléjese y no toque el gabinete con las manos mojadas.',
    'Llame a la persona responsable y dígale qué vio.',
])
f.caja('Importante', ['El sistema **nunca riega solo al encenderse**. Cuando la persona responsable lo vuelva a encender, '
                      'no se mojará nada de inmediato.'])

f.h1('Qué hacer si...')
f.tabla(['Si pasa esto...', 'Puede ser...', 'Qué hacer'], [
    ['No sale agua al regar', 'Tinaco vacío o llave azul cerrada.', 'Llene el tinaco y abra la llave. Luego, en la pantalla, presione [[LIMPIAR FALLA]].'],
    ['Sale agua sin parar', 'Una pieza se atoró.', 'Cierre la **llave azul** y avise de inmediato.'],
    ['La tierra está seca pero no riega', 'El sistema está en MANUAL o es mediodía.', 'Revise que diga **Modo activo: AUTOMÁTICO**. Al mediodía no riega a propósito.'],
    ['La pantalla dice **sin conexión**', 'El sistema perdió el Wi-Fi.', 'El huerto se sigue regando solo. Si dura más de una hora, avise.'],
    ['La pantalla no abre', 'No está en la red RouterHuerto1.', 'Conéctese a RouterHuerto1 e intente de nuevo.'],
    ['La humedad no cambia en días', 'El sensor se salió de la tierra.', 'Avise a la persona responsable. No lo vuelva a enterrar usted.'],
    ['El nivel del tinaco marca raro', 'La tapa está quitada o el sensor se movió.', 'Ponga la tapa. Si sigue raro, avise.'],
    ['Un aspersor no moja', 'Está tapado con tierra.', 'Límpielo con agua.'],
], [1.9, 1.9, 2.9], size=11)

f.h1('Si hay que mover el sistema')
f.p('Mover el tinaco, la bomba o el gabinete **lo debe hacer la persona responsable**. Usted puede ayudar así:')
f.pasos([
    'Antes: en la pantalla presione [[DETENER TODO]] y cambie a modo **MANUAL** para que no riegue.',
    'Cierre la **llave azul**.',
    'Tome **fotos** de cómo está todo conectado.',
    'Si se mueve el tinaco, hay que **vaciarlo primero**: lleno pesa más de 600 kg.',
    'Después de moverlo, la persona responsable revisa todo y regresa el sistema a **AUTOMÁTICO**.',
])

f.h1('Datos para el técnico')
f.p('Esta página es para la persona que repare el equipo.', italic=True, color=GRIS)
f.tabla(['Conexión', 'Pin del ESP32', 'Nota'], [
    ['Relevador de la bomba (IN1)', 'GPIO 26', 'Activo en bajo; bomba por COM → NO'],
    ['Relevador de la válvula (IN2)', 'GPIO 27', 'Activo en bajo; válvula por COM → NO'],
    ['Medidor de agua YF-S201 (amarillo)', 'GPIO 19', '450 pulsos por litro (sin calibrar)'],
    ['Sensor del tinaco PING))) (SIG)', 'GPIO 18', 'Divisor 1 kΩ / 2 kΩ; vacío 117 cm, lleno 12 cm'],
    ['Temperatura DHT22 (out)', 'GPIO 4', '3.3 V'],
    ['Sensor de humedad EC-5 (blanco)', 'GPIO 25', 'Excitación; punta del jack'],
    ['Sensor de humedad EC-5 (rojo)', 'GPIO 34', 'Señal; anillo del jack; 1 MΩ a GND'],
    ['Sensor de humedad EC-5 (sin forro)', 'GND', 'Manga del jack'],
], [2.6, 1.2, 2.9], size=10.5)
f.tabla(['Dato', 'Valor'], [
    ['Batería', '12 V, 9 Ah; no bajar de 10.5 V'],
    ['Bomba', '12 V, 6 A; nunca en seco'],
    ['Raspberry Pi', 'raspberrypi.local (red RouterHuerto1); pantalla en el puerto 1881'],
], [2.0, 4.7], size=10.5)
f.p('El detalle completo está en el **Manual técnico de instalación y mantenimiento**.', size=10.5, color=GRIS)
f.guardar('Manual_del_Equipo_AquaHuerto.docx')
