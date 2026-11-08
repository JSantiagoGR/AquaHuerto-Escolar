# Dashboard completo (FlowFuse Dashboard 2.0)

URL: <http://localhost:1880/dashboard> · desde el celular en la misma red: `http://<IP de la laptop>:1880/dashboard` (pide usuario y contraseña).

Diseño en español, tema verde "Huerto", iconos Material Design, responsive (menú lateral plegable en celular), selectores nativos (fiables en móvil).

## Elementos comunes (todas las páginas)

- **Selector de dispositivo**: `esp32_01 (ESP32 real)` o `sim_01 (SIMULADOR)`. Se guarda y sobrevive reinicios.
- Franja **"MODO DEMOSTRACIÓN — DATOS SIMULADOS"** cuando el dispositivo es el simulador.
- Chips: dispositivo en línea/sin conexión, MQTT, **modo activo**, salidas de potencia deshabilitadas.
- Barra de **resultado de comandos**: "Enviando..." → "CONFIRMADO por el dispositivo" solo con el ACK real; si no llega en 12 s → TIMEOUT y "no se aplicó ningún cambio".
- Diálogos de confirmación (CONFIRMAR / CANCELAR) para toda acción que cambia algo.

## Páginas (10)

| Página | Contenido | Controles |
|---|---|---|
| **Inicio** | **Panel de control**: medidores de humedad del suelo y voltaje del EC-5, focos de bomba / electroválvula / salidas de potencia, VOLUMEN OBJETIVO (mL), INICIAR RIEGO (con confirmación), DETENER BOMBA, agua entregada (conserva el último riego) e historial de agua y humedad de 24 h. Debajo, el resumen: humedad actual y recomendada, T, HR, VPD, tinaco, litros hoy, cultivo/etapa, próximo riego, lluvia (Open-Meteo), bomba/válvula, IA, conexión, banda de humedad, alertas recientes | SELECCIONAR MODO (diálogo "¿Deseas cambiar al modo X?") |
| **Manual** | Ejecución en vivo: progreso, caudal, pulsos, volumen calculado, temperatura, tinaco, humedad; recomendaciones del cultivo | Litros (control deslizante y número), REGAR, REGAR HACIA LA ÓPTIMA, DETENER TODO, SELECCIONAR MODO MANUAL |
| **Automático** | Decisión actual y justificación, historial de decisiones, explicación de la lógica | Borrador de umbrales (emergencia, mínima, óptima, reserva, máxima, histéresis), horarios, límites, infiltración, emergencia, lluvia; GUARDAR (con confirmación) / CANCELAR; SELECCIONAR MODO AUTOMÁTICO |
| **IA** | Aprendizaje, validación, control predictivo, humedad actual y meta, litros, autonomía y hora del límite inferior, gráfica predicha vs real, explicación, coeficientes, comparación de modelos (por versión, estación, cultivo, etapa), observaciones | SELECCIONAR MODO IA, ACTUALIZAR COMPARACIONES, REINICIAR MODELO (confirmación) |
| **Cultivos** | Configuración activa del ESP32, estado de calibración del suelo, 10 cultivos + personalizados, **vista previa (borrador)** con etapas, Kc, umbrales calculados o "PENDIENTE DE CALIBRACIÓN", fuentes | AGREGAR, EDITAR, DUPLICAR, ELIMINAR, GUARDAR / CANCELAR, GUARDAR COMO CULTIVO ACTIVO (confirmación + ACK con versión) |
| **Crecimiento** | Plantaciones: etapa actual, tiempo en etapa, días/semanas restantes, próxima etapa, cosecha estimada, barras de progreso, grados-día, etapa estimada, historial | NUEVA PLANTACIÓN, ADELANTAR, RETRASAR, CONFIRMAR ETAPA ESTIMADA, BLOQUEAR CAMBIOS AUTOMÁTICOS, CORREGIR FECHAS |
| **Clima** | Estado de Open-Meteo y fecha de actualización, clima actual (modelo vs sensor local), VPD, ET0 y ETc, lluvia 24 h pasada/próxima, horas recomendadas, gráfica horaria 48 h, tabla de 10 días | ACTUALIZAR |
| **Historial** | Gráficas de humedad, T/HR, tinaco (con valor al pasar el cursor), litros diarios y acumulados, eventos de riego, eventos de lluvia/agua externa, comparaciones por mes/cultivo/etapa/modo | Filtros de fecha y cultivo, 24 h/7 d/30 d/1 año, exportación CSV (lecturas, riegos, alertas, predicciones, lluvia) |
| **Alertas** | 12 categorías (humedad crítica/excesiva, tinaco, flujo, sensores, MQTT, pronóstico vencido, posible lluvia, riego externo, IA, etapa, almacenamiento) y registro completo | Confirmar causa de aumentos de humedad (lluvia, riego externo, error del sensor, otra), marcar revisada, filtros |
| **Configuración** | Dispositivos reales vs simulados, estado del ESP32, redes Wi-Fi guardadas (sin contraseñas), broker, calibraciones, seguridad, hora/zona, ubicación, **cama de cultivo** (área, profundidad, drenaje, mezcla → litros por punto), calibración del suelo, escala del EC-5, respaldos, datos de conexión; panel del SIMULADOR | DIAGNÓSTICO, PEDIR ESTADO/CONFIGURACIÓN, CAMBIAR BROKER, GUARDAR calibraciones, NUEVA VERSIÓN de datos, GUARDAR UBICACIÓN, GUARDAR CAMA, GUARDAR CALIBRACIÓN DEL SUELO, RESPALDAR AHORA, controles del simulador |

## Borrador vs configuración activa

- `config_activa` = lo que el dispositivo reporta en `config` (retenido).
- `config_borrador` = lo que el usuario edita en la página. Se muestra el aviso **"Hay cambios SIN GUARDAR"**.
- GUARDAR muestra "¿Confirmas aplicar esta configuración?" con la lista de cambios (antes → después).
- El ESP32 valida todo junto y responde con el `id` de transacción y la versión aplicada. Si rechaza, se pierde la conexión o vence el tiempo, se conserva la configuración anterior y se muestra el motivo.
- Cancelar o salir de la página descarta el borrador.

## Arquitectura

```
Plantilla Vue --(cmd)--> comando.js --MQTT--> ESP32 --ack--> acks.js --> páginas
              --(req)--> solicitudes.js --SQLite--> respuesta.js --> páginas
MQTT in --> ingesta.js --> SQLite + alertas.js + snapshot.js --> páginas (≤1/s)
```

Probado en el navegador integrado: navegación por las 10 páginas, selección de dispositivo, cambio de modo con confirmación y ACK, riego manual en vivo, aplicación de perfil de cultivo, creación de plantación y confirmación de etapa, respaldo, historial y alertas (ver [PRUEBAS.md](PRUEBAS.md)).
