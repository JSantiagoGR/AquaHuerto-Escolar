# Open-Meteo

API: <https://open-meteo.com/en/docs> (uso gratuito no comercial, sin clave). Datos de **modelo meteorológico**: no son mediciones del huerto. El sistema distingue siempre sensor local, modelo (pasado reciente) y pronóstico.

## Variables verificadas (consulta real del 2026-10-11, HTTP 200)

| Grupo | Variables |
|---|---|
| current | `temperature_2m`, `relative_humidity_2m`, `precipitation`, `rain`, `weather_code` |
| hourly | `temperature_2m`, `relative_humidity_2m`, `precipitation_probability`, `precipitation`, `vapour_pressure_deficit`, `et0_fao_evapotranspiration` |
| daily | `temperature_2m_max/min`, `precipitation_sum`, `precipitation_probability_max`, `et0_fao_evapotranspiration` |

Ubicación del huerto: **Escuela Primaria Federal Belisario Domínguez, Chihuahua (28.659830, −106.074051)** → Configuración → Ubicación para poner las coordenadas reales del huerto (se aplican al servidor y al ESP32). Zona horaria `timezone=auto` (America/Chihuahua, UTC−6).

## Servidor (Node-RED)

- Cada **30 min** y al pulsar ACTUALIZAR (máximo una consulta manual por minuto): `past_days=7&forecast_days=3`.
- HTTPS con verificación normal de certificados del nodo `http request` (no se desactivó TLS).
- Guarda cada consulta con su fecha en `weather_fetches`, `forecast_hourly` y `forecast_daily`.
- Calcula lluvia 24 h pasada y próxima, probabilidad máxima, ET0 del día y horas recomendadas (horarios preferidos con menor VPD y sin lluvia probable).
- Pronóstico de más de 3 h → **VENCIDO**: alerta "Pronóstico vencido" y no se usa para decidir.
- Si falla internet: alerta, se conserva el último pronóstico solo mientras siga vigente y el riego continúa con los sensores locales.

## ESP32

- `weather.c`: HTTPS con `esp_crt_bundle` (certificados validados), cada `weather_min` (60 min, 30–180), consulta compacta (`past_hours=6&forecast_hours=24&timeformat=unixtime`, ~2 KB).
- Con pronóstico vigente: pospone el riego **rutinario** si la probabilidad máxima de las próximas 6 h ≥ `rain_prob_pct` (70 %) **y** la lluvia prevista ≥ `rain_mm` (2 mm). Las emergencias no se posponen.
- La IA usa VPD y ET0 horarios del pronóstico.
- Sin internet o con pronóstico vencido (> 3 h): no se usa.

Estado verificado: servidor consultando con éxito (30.9 °C, ET0 4.84 mm) y **ESP32 consultando por HTTPS** con certificados validados (25.3 °C, lluvia 6 h 0.0 mm, ET0 24 h 5.6 mm, a los 8 s de arrancar).
