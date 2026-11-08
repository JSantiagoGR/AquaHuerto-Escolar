# AquaHuerto Escolar

Sistema de **riego inteligente** para un huerto escolar de 1 × 1 m con:
- un ESP32 con sensores de humedad del suelo (EC-5), nivel del tinaco (PING))), clima (DHT22) y caudal (YF-S201);
- bomba, electroválvula y energía solar (panel de 50 W, controlador PWM y batería de 12 V);
- una Raspberry Pi con MQTT y Node-RED, un dashboard para celular y un bot de Telegram;
- un modo de **IA** que aprende cuánto sube la humedad por cada litro de agua y qué tan rápido se seca la tierra.

Incluye todo lo necesario para **revisarlo o recrearlo**:
- firmware;
- dashboard;
- simulador;
- modelo hidráulico en EPANET;
- modelos CAD/3D;
- escenas y videos de Blender;
- manuales, reporte y documentos de la exposición.

## Autores

| | |
|---|---|
| **Jaime Santiago Galaviz Reaza** | Autor principal · [LinkedIn](https://www.linkedin.com/in/santiagogalaviz) · [GitHub](https://github.com/JSantiagoGR) |
| Eyra Cristal Garcia | Coautora |
| Victor Manuel Palicio Torres | Coautor |

Equipo 2 · Tecnológico de Monterrey, Campus Chihuahua · 2026.

Si usas este proyecto, por favor da crédito (ver [Licencia](#licencia) y `CITATION.cff`).

## Videos del modelo 3D

| Video | Contenido |
|---|---|
| `.../modelos_3D/video/AquaHuerto_recorrido_completo_v2_0001-1200.mp4` | Recorrido completo (40 s): riego, cajas, tinaco, gabinete y panel |
| `.../modelos_3D/video/AquaHuerto_componentes_0001-0820.mp4` | Componentes recreados: ESP32, relevadores, controlador, batería y PING))) |
| `.../modelos_3D/video/AquaHuerto_riego_0001-0330.mp4` | Riego con los 9 microaspersores |
| `.../modelos_3D/video/AquaHuerto_cajas_por_dentro_0001-0420.mp4` | Bomba, caudalímetro y electroválvula dentro de sus cajas |

(`...` = `documentacion/EXPOSICION_AquaHuerto/2_Documentacion_tecnica/06_Planos_CAD`)

## Estructura

| Carpeta | Contenido |
|---|---|
| `sistema/firmware/` | Firmware del ESP32 (ESP-IDF): sensores, riego, MQTT, supervisor de seguridad, protección anti-reinicios |
| `sistema/dashboard/` | Generador del dashboard de Node-RED (plantillas Vue, funciones, exportaciones) |
| `sistema/nodered/`, `sistema/mqtt/` | Flujos de Node-RED y configuración del broker Mosquitto |
| `sistema/telegram/` | Bot de Telegram (`/estado`, `/ia`, `/modo`); solo consulta, no riega |
| `sistema/simulation/` | Núcleo de decisión de riego y simulador del huerto (modo IA) para probar sin hardware |
| `sistema/migration_raspberry_pi/` | Instalación en una Raspberry Pi (instancia aislada, puertos 1881/1884) |
| `sistema/docs/` | Documentación técnica: instalación, pinout verificado, calibraciones, seguridad, pruebas |
| `sistema/tests/` | Pruebas automáticas y de campo |
| `proyecto_final_v1/` | Primera versión del proyecto (arquitectura, pinout, calibraciones) |
| `epanet/` | Modelos hidráulicos en EPANET (`.inp`/`.net`), cálculos y validaciones |
| `documentacion/manuales/` | Manuales de uso y técnicos (Word y PDF) con sus scripts generadores |
| `documentacion/reporte/` | Reporte técnico del proyecto (APA) |
| `documentacion/EXPOSICION_AquaHuerto/` | Anteproyecto, bitácora, cartel, documentos técnicos 05–24, planos CAD, modelos 3D (STEP/STL/SolidWorks/Blender), renders, videos y los scripts que los generan (`_generador/`) |

## Cómo recrearlo

1. **Hardware:** lista de componentes y conexiones en `sistema/docs/PINOUT_VERIFICADO.md`,
   `documentacion/manuales/v2/Manual_Tecnico_Instalacion_AquaHuerto.pdf` y
   `documentacion/EXPOSICION_AquaHuerto/2_Documentacion_tecnica/09_Diagrama_electrico/`.
2. **Hidráulica:** abre `epanet/3/` en EPANET 2.2 (tinaco → bomba → filtro → caudalímetro → electroválvula → 9 microaspersores).
3. **Firmware (ESP-IDF 6.x):**
   1. Compila y carga desde `sistema/firmware/` (`idf.py build flash monitor`).
   2. Configura la red Wi-Fi y el broker MQTT después de cargar el firmware, con `sistema/firmware/tools/provisionar_red.py` o por la consola serial (`WIFI`). Se guardan en la memoria del ESP32, no en el código.
   3. La versión anterior (`proyecto_final_v1/`) usa `sdkconfig.secrets.example`: cópialo a `sdkconfig.secrets` y llena los valores.
4. **Servidor (Raspberry Pi o PC):** sigue `sistema/migration_raspberry_pi/README.md` para instalar Mosquitto, Node-RED y el dashboard
   (`sistema/scripts/desplegar_dashboard_pi.py`). En los scripts, `raspberrypi.local` es la dirección de tu Pi: cámbiala si usas otra.
5. **Sin hardware:** `sistema/simulation/` simula el huerto completo (sensores, riego e IA) y publica por MQTT igual que el ESP32.
6. **Modelos 3D y videos:** Blender 3.4. Cada escena se genera con su script de `documentacion/EXPOSICION_AquaHuerto/_generador/`
   (`blender -b -P <script>.py -- <carpeta modelos_3D> [--video]`). Cada script abre la escena anterior y guarda una nueva.

### Lo que NO está en el repositorio (a propósito)

Contraseñas, token del bot, credenciales de MQTT y Wi-Fi, bases de datos con mediciones, respaldos de la memoria del ESP32,
direcciones de la red local, entornos virtuales y `node_modules`. Donde hacían falta hay marcadores
(`raspberrypi.local`, `IP_DEL_ESP32`, `RED_DE_CASA`, `xx:xx:xx:xx:xx:xx`) o plantillas `.example`.

## Seguridad del diseño

- Nunca riega al arrancar y no ejecuta órdenes MQTT retenidas.
- Tiene un supervisor independiente que corta la bomba por tiempo máximo, falta de flujo o falla de sensores.
- La potencia solo se habilita por consola, nunca por la red.
- El bot de Telegram solo consulta: no riega ni borra fallas.

## Licencia

- **Código:** [MIT](LICENSE).
- **Documentos, imágenes, videos y modelos 3D:** [CC BY 4.0](LICENSE-DOCS.md). Puedes usarlos y adaptarlos dando crédito a los autores.
- **Modelos de terceros** (KiCad, Soldered Electronics): conservan su licencia (ver `LICENSE-DOCS.md`).
