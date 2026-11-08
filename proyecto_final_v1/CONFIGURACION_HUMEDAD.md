# Configuración de humedad del suelo

El sistema no depende de un cultivo. La escuela fija tres umbrales de **humedad volumétrica del suelo (%VWC)** medida por el EC-5. No confundir con la humedad **relativa** del aire (%HR) del DHT22, que es solo informativa.

| Parámetro | Clave | Valor de ejemplo* | Límites duros | Significado |
|---|---|---|---|---|
| HUMEDAD MÍNIMA | `hum_min` | 25 | 5–60 | Bajo este valor el suelo necesita agua |
| HUMEDAD RECOMENDADA / OBJETIVO | `hum_target` | 35 | 5–65 | Humedad que se busca recuperar |
| HUMEDAD MÁXIMA | `hum_max` | 45 | 5–70 | En o sobre este valor no se agrega agua |
| Humedad crítica (emergencia) | `hum_critical` | 18 | 0–55 | Permite un riego limitado fuera de horario |

\* **Valores de demostración. No son recomendaciones agronómicas.** Además, la calibración del EC-5 solo está validada entre 0 y 45 %VWC (ver [CALIBRACION_EC5.md](CALIBRACION_EC5.md)).

## Reglas que valida el firmware
- `MINIMA + 1 ≤ OBJETIVO` y `OBJETIVO + 1 ≤ MAXIMA` (al menos 1 punto entre cada umbral).
- `CRITICA < MINIMA`.
- Cada valor dentro de sus límites duros: ninguna orden remota puede salir de ellos.
- Si un cambio deja la configuración inválida, **se rechaza completo** y se responde el motivo (`ack` con `status: REJECTED`).
- Los valores se guardan en NVS con CRC y sobreviven a reinicios. Si la NVS está corrupta, se cargan los valores por defecto y se activa la alarma `CONFIG_RESET`.

## Histéresis y protección contra activaciones repetidas
| Mecanismo | Parámetro | Por defecto |
|---|---|---|
| Inicia solo bajo la mínima y busca el objetivo (banda entre ambos) | `hum_min` / `hum_target` | 25 / 35 |
| Lecturas seguidas bajo la mínima antes de regar | `dry_confirm` | 2 |
| Intervalo mínimo entre eventos de riego | `min_event_gap_min` | 60 min |
| Espera de infiltración entre ciclos | `infilt_min` | 15 min |
| Máximo de ciclos por evento | `max_cycles` | 3 |
| Respuesta mínima esperada del suelo | `min_response_pp` tras `response_cycles` | 1.0 %VWC tras 2 ciclos |
| Intervalo entre emergencias | `emergency_gap_min` | 240 min |

## Cómo cambiarlos

### Desde el dashboard (futuro)
Sección **CONFIGURACIÓN DE HUMEDAD DEL SUELO**: tres sliders que envían `SET_HUMIDITY_RANGE` (ver [GUIA_DASHBOARD_NODE_RED.md](GUIA_DASHBOARD_NODE_RED.md) §12).

### Por MQTT (`huerto/esp32/command`)
```json
{"id":"cultivo-001","cmd":"SET_HUMIDITY_RANGE","min":25,"target":35,"max":45}
{"id":"cultivo-002","cmd":"SET_HUMIDITY_MIN","value":27}
{"id":"cultivo-003","cmd":"SET_CONFIG","key":"hum_critical","value":18}
```
Al cambiar los tres umbrales, use `SET_HUMIDITY_RANGE`. Con comandos individuales el orden importa: subir primero la máxima, luego el objetivo y al final la mínima.

### Por consola serial
```
HUMEDAD 25 35 45
SET hum_critical 18
CONFIG
```

## Al elegir el cultivo
1. Busque el intervalo recomendado de humedad del suelo **en %VWC** para ese cultivo y tipo de suelo, o el porcentaje de agua disponible convertido a %VWC con la capacidad de campo de la tierra.
2. Mida en el cajón el %VWC a capacidad de campo: riegue a saturación, cubra, espere 24–48 h y anote el %VWC. La máxima no debería superarlo.
3. Fije `hum_max` cerca de la capacidad de campo, `hum_target` algo por debajo y `hum_min` donde la planta empieza a necesitar agua.
4. Ajuste `liters_per_cycle` al volumen del cajón (~1 m² × profundidad de raíces) y al aumento de %VWC que produzca 1 L (mídalo tras la primera semana).
