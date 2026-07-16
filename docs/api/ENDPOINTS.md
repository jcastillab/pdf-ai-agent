# Catálogo de API

Base: `/api/v1`. Todos los endpoints, excepto operación, requieren `Authorization: Bearer <Supabase access token>`.

## Operación

| Método | Ruta | Respuesta | Autenticación |
| --- | --- | --- | --- |
| GET | `/health` | Estado y hora UTC | No |
| GET | `/live` | Proceso activo | No |
| GET | `/ready` | API lista | No |
| GET | `/version` | Versión | No |

## Autenticación

El frontend ejecuta registro, login, refresh, logout y recuperación directamente contra Supabase Auth. FastAPI valida cada JWT y expone:

| Método | Ruta | Respuesta |
| --- | --- | --- |
| GET | `/auth/me` | `id`, `email`, `role`, `organization_id` |

## Documentos

| Método | Ruta | Estado | Permiso | Idempotencia |
| --- | --- | --- | --- | --- |
| POST | `/documents/upload` | 201 | Usuario autenticado | Nuevo documento por solicitud |
| POST | `/documents/{id}/upload-complete` | 202 | Propietario | Segunda confirmación devuelve 409 |
| GET | `/documents` | 200 | Propietario | Sí |
| GET | `/documents/{id}` | 200 | Propietario | Sí |
| GET | `/documents/{id}/status` | 200 | Propietario | Sí |
| GET | `/documents/{id}/pages` | 200 | Propietario | Sí |
| GET | `/documents/{id}/download` | 200 | Propietario | Genera URL temporal |
| POST | `/documents/{id}/process` | 202 | Propietario | Crea trabajo nuevo |
| DELETE | `/documents/{id}` | 204 | Propietario | Segundo intento devuelve 404 |

### Crear carga

```json
{
  "filename": "contrato.pdf",
  "content_type": "application/pdf",
  "size_bytes": 845321
}
```

Respuesta:

```json
{
  "document_id": "08a8cacc-17f4-4703-bbf7-1c604042765e",
  "upload_url": "https://ACCOUNT.r2.cloudflarestorage.com/...",
  "method": "PUT",
  "headers": {"Content-Type": "application/pdf"},
  "expires_in": 900
}
```

El navegador ejecuta `PUT` con el PDF y luego confirma la carga. R2 no admite `POST` multipart con URL firmada en este flujo.

### Listar documentos

Parámetros:

- `limit`, entre 1 y 100, valor inicial 20.
- `offset`, entero mayor o igual a 0.

Respuesta:

```json
{
  "items": [
    {
      "id": "08a8cacc-17f4-4703-bbf7-1c604042765e",
      "original_name": "contrato.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 845321,
      "page_count": 12,
      "status": "completed",
      "confidence": 0.94,
      "summary": "...",
      "created_at": "2026-07-14T18:00:00Z",
      "processed_at": "2026-07-14T18:02:12Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

## Agente

| Método | Ruta | Estado | Resultado |
| --- | --- | --- | --- |
| POST | `/documents/{id}/ask` | 202 | Trabajo de pregunta |
| POST | `/documents/{id}/summarize` | 202 | Trabajo de resumen |
| POST | `/documents/{id}/extract` | 202 | Trabajo de extracción |

Pregunta:

```json
{
  "question": "¿Cuál es la fecha de vencimiento?",
  "conversation_id": null
}
```

Respuesta inicial:

```json
{
  "run_id": "f28c1c44-80c4-4eaa-a5b5-ccaaed365d7f",
  "job_id": "6280ead7-6d14-491b-95b0-b289a52f4fe5",
  "status": "queued"
}
```

Resultado final en `job.result`:

```json
{
  "answer": "La fecha de vencimiento es el 30 de septiembre de 2026.",
  "citations": [
    {"page": 4, "quote": "Fecha de vencimiento: 30 de septiembre de 2026"}
  ]
}
```

Extracción:

```json
{
  "fields": ["numero_factura", "fecha", "total", "nit_proveedor"]
}
```

## Trabajos

| Método | Ruta | Estado | Regla |
| --- | --- | --- | --- |
| GET | `/jobs` | 200 | Últimos trabajos del usuario |
| GET | `/jobs/{id}` | 200 | Propietario |
| POST | `/jobs/{id}/cancel` | 200 | No aplica a trabajos terminados |
| POST | `/jobs/{id}/retry` | 202 | Aplica a estado `failed` |
| GET | `/jobs/{id}/events` | 200 SSE | Flujo de progreso por 5 minutos |

Estados:

`queued`, `validating`, `extracting`, `ocr`, `classifying`, `chunking`, `indexing`, `extracting_fields`, `validating_results`, `waiting_human_review`, `generating`, `completed`, `failed`, `cancelled`.

## Telemetría

| Método | Ruta | Métricas |
| --- | --- | --- |
| GET | `/telemetry/overview` | Documentos, trabajos, tokens, costo y latencia media |

## Errores

| Código | Significado |
| --- | --- |
| 400 | Solicitud inválida |
| 401 | JWT ausente, inválido o vencido |
| 403 | Permiso insuficiente |
| 404 | Recurso inexistente o ajeno |
| 409 | Estado incompatible o carga repetida |
| 413 | PDF supera el tamaño configurado |
| 422 | Cuerpo no cumple el esquema |
| 429 | Límite de solicitudes |
| 500 | Error interno registrado |
| 503 | Cola o dependencia no disponible |

No devuelvas detalles de credenciales, SQL, rutas internas ni trazas al cliente.

## Evolución de endpoints

Pendientes para piloto:

- `/documents/compare`
- `/reviews/*`
- `/admin/*`
- Series detalladas de `/telemetry/*`
- Exportación CSV y JSON persistida
- Conversaciones persistentes

FastAPI publica el contrato OpenAPI en `/openapi.json`. Usa ese archivo para generar clientes y pruebas de contrato.

