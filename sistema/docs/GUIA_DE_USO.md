# Guía de uso

## Encender todo

Doble clic o en PowerShell:

```bash
powershell -ExecutionPolicy Bypass -File C:\ESP32_Riego_Automatico\Pruebas_Casa_ESP32_v1\scripts\iniciar_todo.ps1 -Simulador -Abrir
```

## Elegir qué ver

Arriba de cada página, **Dispositivo**:
- `esp32_01 (ESP32 real)`: la placa conectada por USB-C (cuando tenga Wi-Fi).
- `sim_01 (SIMULADOR)`: aparece la franja amarilla **MODO DEMOSTRACIÓN — DATOS SIMULADOS**. Nada de lo que veas ahí viene de sensores reales y sus comandos nunca llegan al ESP32 (el broker lo impide).

## Cambiar de modo

Las pestañas MANUAL / AUTOMÁTICO / IA **no cambian el modo**. Para cambiarlo:
1. Botón **SELECCIONAR MODO** (Inicio) o el de la pestaña.
2. Diálogo "¿Deseas cambiar al modo X?" → **CONFIRMAR**.
3. Espera "CONFIRMADO por el dispositivo". Si dice TIMEOUT o REJECTED, el modo no cambió.

Al reiniciar, el ESP32 de pruebas **siempre arranca en MANUAL**.

## Regar manualmente

Pestaña MANUAL: elige litros → **REGAR** → confirma. Verás progreso, caudal y pulsos. **DETENER TODO** apaga de inmediato (no pide confirmación).
"REGAR HACIA LA ÓPTIMA" hace dosis de hasta `liters_per_cycle` con infiltración y nueva lectura entre dosis.

Con el ESP32 real y las salidas de potencia deshabilitadas, el ESP32 **rechaza** los riegos (protección). Las salidas solo se habilitan por USB con `POWER ON CONFIRMAR` tras verificar la etapa de potencia (ver [SEGURIDAD.md](SEGURIDAD.md)).

## Cultivos y etapas

1. **Configuración → Calibración del suelo:** registra la capacidad de campo y el punto de marchitez **medidos** con tu EC-5. Sin eso, los cultivos se aplican pero conservan los umbrales actuales (PENDIENTE DE CALIBRACIÓN).
2. **Cultivos:** selecciona un cultivo (vista previa) → elige etapa → **GUARDAR COMO CULTIVO ACTIVO** → confirma.
3. **Crecimiento → NUEVA PLANTACIÓN:** fecha de siembra o trasplante. **Una caja = una plantación activa** (por dispositivo): registrar otra cierra la actual, que queda en el historial. Según el modo: MANUAL tú cambias la etapa; AUTOMÁTICO recomienda; IA la actualiza y te avisa (puedes corregirla o BLOQUEAR).

## Alertas de lluvia o agua externa

Si la humedad sube sin que la bomba haya regado, aparece POSIBLE LLUVIA, POSIBLE RIEGO EXTERNO, AUMENTO NO EXPLICADO o POSIBLE ERROR DEL SENSOR. En **Alertas** confirma la causa; queda en la base de datos.

## Historial y CSV

Historial → rango de fechas → APLICAR FILTROS. Botones CSV para lecturas, riegos, alertas, predicciones y lluvia.

## Respaldos

Configuración → **RESPALDAR AHORA** (también automático a las 03:00). Quedan en `backups\db` y `backups\nodered`.

## Simulador (para practicar)

Configuración (con `sim_01` seleccionado) → panel del simulador: velocidad x1/x60/x600, lluvia, riego externo, pronóstico de lluvia, fallas de sensores, tinaco, perder MQTT, hora.
