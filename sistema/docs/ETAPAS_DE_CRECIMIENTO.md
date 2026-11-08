# Etapas de crecimiento

Página **Crecimiento**. Función de servidor `dashboard/funciones/crecimiento.js` (cada 10 min y tras cada cambio).

## Una caja, una plantación

Cada plantación está ligada a su caja (dispositivo, columna `plantings.device`). Solo hay **una plantación activa por caja**: registrar una nueva cierra la anterior (queda en el historial). Los cambios de etapa y el perfil que se envía usan el modo y el ESP32 de esa caja, aunque en el selector esté otro dispositivo.

## Qué se muestra por plantación

Cultivo, variedad, fechas de siembra y trasplante, etapa actual, tiempo en la etapa, duración estimada, días y semanas restantes, próxima etapa probable, cosecha estimada, barras de progreso (ciclo y etapa), grados-día acumulados y el historial de cambios.

## Cómo se estima

1. **Calendario FAO-56** (Tabla 11) desde la fecha de siembra (o trasplante si no hay siembra).
2. **Correcciones del usuario**: cuando confirmas, adelantas o corriges una etapa se guarda cuántos días duró realmente. La siguiente estimación de esa etapa para ese cultivo es el promedio ponderado `(FAO + Σ observados)/(1 + n)`. Verificado: tras confirmar a los 31 días, el "Establecimiento" de lechuga pasó de 25 a 28 días estimados.
3. **Grados-día** (método del promedio): `max(0, (Tmáx + Tmín)/2 − base)` con la temperatura del aire diaria de Open-Meteo, guardada día a día.

**Limitaciones (documentadas):** la temperatura de Open-Meteo es la del aire a 2 m de un modelo, no la de la planta ni la del suelo; los días anteriores a la instalación no tienen dato (se muestra cuántos faltan). Los sensores **no pueden confirmar** floración ni frutos: todo cambio automático es una **estimación**.

## Según el modo activo del dispositivo

| Modo | Comportamiento |
|---|---|
| MANUAL | Solo informa la etapa estimada; tú la cambias |
| AUTOMÁTICO | Genera la alerta "Cambio de etapa recomendado" y espera tu confirmación |
| IA | Actualiza la etapa estimada (si no está bloqueada), registra `ia_auto` como **estimado**, notifica y envía el perfil de la nueva etapa al ESP32. Puedes corregirla |

Botones: ADELANTAR, RETRASAR, CONFIRMAR ETAPA ESTIMADA, BLOQUEAR CAMBIOS AUTOMÁTICOS, CORREGIR FECHAS. Cada cambio de etapa envía `APPLY_PROFILE` (Kc y umbrales de la etapa) con confirmación del ESP32.

Tablas: `plantings`, `stage_changes` (origen: manual, recomendación confirmada, ia_auto, corrección; estimado/confirmado; días y GDD en la etapa).
