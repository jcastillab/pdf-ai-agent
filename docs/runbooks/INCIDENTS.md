# Incidentes, recuperación y rollback

## API sin servicio

1. Revisa `/health`, eventos de Render y Sentry.
2. Confirma variables obligatorias.
3. Valida conexión al pooler de Supabase.
4. Revierte al despliegue anterior si el fallo comenzó tras una versión.
5. Mantén el worker detenido cuando una migración incompatible esté activa.

## Worker detenido

1. Revisa Ollama con `ollama list`.
2. Revisa red hacia Supabase y R2.
3. Reinicia el worker.
4. Confirma que trabajos `queued` empiezan a avanzar.
5. Revisa dead letter queue antes de reintentar.

Los mensajes permanecen durables. No recrees trabajos hasta confirmar el estado original.

## Trabajo atascado

1. Compara `updated_at` con la hora actual.
2. Revisa `graph_checkpoints`.
3. Confirma tiempo de visibilidad de la cola.
4. Solicita cancelación.
5. Espera la liberación del mensaje.
6. Reintenta desde la API cuando el trabajo esté `failed`.

## Rollback de código

- Frontend: promueve el despliegue anterior en Cloudflare Pages.
- API: usa Instant Rollback de Render.
- Worker: detén el proceso, cambia al tag anterior y reinicia.
- Base de datos: evita downgrades destructivos. Restaura backup en un proyecto aislado y valida antes de conmutar.

## Recuperación de R2

- Activa versionado o una política de retención cuando el negocio lo exija.
- Prueba restauración trimestral.
- Mantén `object_key` y hash en PostgreSQL.
- Registra eliminaciones en auditoría.

## Severidad

| Nivel | Ejemplo | Tiempo de respuesta |
| --- | --- | --- |
| SEV1 | Fuga de datos o credencial | Inmediato |
| SEV2 | API o cola fuera de servicio | 30 minutos |
| SEV3 | Parte del OCR o chat falla | 4 horas |
| SEV4 | Error visual o métrica menor | Siguiente ciclo |

