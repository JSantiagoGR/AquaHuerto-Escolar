# Mis cultivos personalizados

Página **Cultivos → MIS CULTIVOS PERSONALIZADOS**.

## Qué se puede hacer

| Acción | Detalle |
|---|---|
| AGREGAR | Cultivo nuevo con plantilla de 4 etapas |
| EDITAR | Nombre, p, base GDD, temperaturas óptimas/máxima, horarios, etapas (1–8: nombre, días, Kc) y **umbrales por etapa** (emergencia, mínima, óptima, reserva, máxima %VWC; opcionales) |
| DUPLICAR | Copia cualquier cultivo (también los 10 base, que no se editan directamente) |
| ELIMINAR | Borrado **lógico** (`deleted=1`): el historial que lo usó se conserva |
| GUARDAR / CANCELAR | Con confirmación; "Cambios sin guardar" mientras se edita |

Si la etapa no tiene sus 5 umbrales, se calculan con la calibración del suelo (FAO-56); si tampoco hay calibración, queda PENDIENTE.

Validaciones (servidor y ESP32): nombre ≥ 2 caracteres, 1–8 etapas, días 1–400, y `emergencia + 1 ≤ mínima`, `mínima + 1 ≤ óptima`, `óptima + 0.5 ≤ reserva ≤ máxima ≤ 70`.

## Borrador vs activo

- Crear o editar un cultivo **no** cambia el cultivo activo del ESP32.
- Seleccionar un cultivo muestra su **VISTA PREVIA (borrador)**.
- Solo **GUARDAR COMO CULTIVO ACTIVO** + confirmación envía `APPLY_PROFILE`; el cultivo cambia cuando el ESP32 responde con la versión aplicada.
- Cancelar, cerrar el editor o cambiar de página descarta el borrador.

## Almacenamiento y capacidad

- Los perfiles viven en SQLite (tabla `crops`, JSON por cultivo): ilimitados en la práctica (solo los limita el disco; cada perfil ocupa ~2–4 KB).
- El ESP32 guarda **solo el perfil activo** (identificador, nombre, etapa, Kc, umbrales y horarios) en su configuración NVS: no se llena con perfiles.
