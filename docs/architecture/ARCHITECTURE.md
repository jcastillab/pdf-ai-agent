# Arquitectura

## Vista general

```mermaid
flowchart TB
  U["Usuario"] --> CF["Angular 17<br/>Cloudflare Pages"]
  CF --> AUTH["Supabase Auth"]
  CF --> API["FastAPI<br/>Render"]
  CF -->|"PUT firmado"| R2["Cloudflare R2"]
  API --> DB["Supabase PostgreSQL<br/>pgvector"]
  API --> Q["Supabase Queues<br/>pgmq"]
  W["Worker Python local"] -->|"poll saliente"| Q
  W --> R2
  W --> DB
  W --> O["Ollama local"]
  API --> S["Sentry"]
  W --> S
  API --> OT["OpenTelemetry"]
  W --> OT
```

## Despliegue

```mermaid
flowchart LR
  subgraph Edge["Cloudflare"]
    P["Pages"]
    R["R2 privado"]
    D["DNS y TLS"]
  end
  subgraph Cloud["Servicios administrados"]
    A["Render API"]
    S["Supabase<br/>Auth, DB, Queue"]
    E["Sentry"]
  end
  subgraph Local["Equipo local"]
    W["Worker"]
    O["Ollama"]
    T["Tesseract"]
  end
  P --> A
  P --> R
  A --> S
  W --> S
  W --> R
  W --> O
  W --> T
  A --> E
  W --> E
```

El worker no acepta tráfico entrante. Todas sus conexiones salen hacia servicios HTTPS. Ollama escucha en `localhost`.

## Secuencia de carga y procesamiento

```mermaid
sequenceDiagram
  actor U as Usuario
  participant F as Angular
  participant A as FastAPI
  participant R as R2
  participant Q as Supabase Queue
  participant W as Worker local
  participant O as Ollama
  participant D as PostgreSQL

  U->>F: Selecciona PDF
  F->>A: POST /documents/upload
  A->>D: Crea documento
  A-->>F: URL PUT firmada
  F->>R: PUT PDF
  F->>A: POST /upload-complete
  A->>R: HEAD objeto
  A->>D: Crea trabajo queued
  A->>Q: Envía mensaje
  A-->>F: 202 y job_id
  W->>Q: Lee mensaje
  W->>R: Descarga PDF
  W->>W: Valida, extrae y OCR
  W->>O: Embeddings y resumen
  W->>D: Páginas, chunks y métricas
  W->>Q: Archiva mensaje
  F->>A: GET documento y trabajo
  A-->>F: completed
```

## Secuencia de una pregunta

```mermaid
sequenceDiagram
  actor U as Usuario
  participant F as Angular
  participant A as FastAPI
  participant Q as Queue
  participant W as Worker
  participant V as pgvector
  participant O as Ollama

  U->>F: Escribe pregunta
  F->>A: POST /documents/{id}/ask
  A->>Q: answer_question
  A-->>F: 202, job_id
  W->>Q: Lee trabajo
  W->>O: Embedding de pregunta
  W->>V: Búsqueda híbrida filtrada por documento
  V-->>W: Fragmentos con página
  W->>O: Pregunta más evidencia
  O-->>W: JSON con respuesta y citas
  W->>W: Valida página y cita
  W->>V: Guarda resultado y tokens
  F->>A: GET /jobs/{id}
  A-->>F: Respuesta y citas
```

## Revisión humana, piloto

```mermaid
sequenceDiagram
  participant W as Worker
  participant D as PostgreSQL
  participant F as Angular
  actor R as Revisor

  W->>W: Calcula confianza
  alt Confianza bajo umbral
    W->>D: Crea human_review pending
    D-->>F: Revisión pendiente
    F-->>R: Muestra campos y fuentes
    R->>F: Corrige o aprueba
    F->>D: Guarda decisión auditada
  else Confianza suficiente
    W->>D: Marca resultado aprobado automáticamente
  end
```

## Telemetría

```mermaid
sequenceDiagram
  participant C as Angular o API
  participant A as FastAPI
  participant W as Worker
  participant O as Ollama
  participant D as PostgreSQL
  participant T as OpenTelemetry
  participant S as Sentry

  C->>A: Solicitud con X-Request-ID
  A->>D: Metadatos del trabajo
  A->>T: Span HTTP y DB
  W->>O: Llamada con tarea y modelo
  W->>D: Tokens, latencia y costo
  W->>T: Span de trabajo
  opt Error
    A->>S: Excepción sin PII
    W->>S: Excepción sin texto del PDF
  end
```

## Flujo LangGraph

El grafo ejecutable enruta cuatro clases de trabajo. El procesamiento documental registra checkpoints por etapa. El diseño de evolución conserva todos los nodos solicitados.

```mermaid
flowchart TB
  A["Recepción"] --> B["Validación de seguridad"]
  B --> C["Hash y duplicado"]
  C --> D["Almacenamiento confirmado"]
  D --> E["Extracción nativa"]
  E --> F{"¿OCR necesario?"}
  F -->|Sí| G["OCR selectivo"]
  F -->|No| H["Normalización"]
  G --> H
  H --> I["Tablas y clasificación"]
  I --> J["Segmentación"]
  J --> K["Embeddings"]
  K --> L["Indexación"]
  L --> M["Extracción de campos"]
  M --> N["Reglas y confianza"]
  N --> O{"¿Revisión?"}
  O -->|Sí| P["Interrupción humana"]
  O -->|No| Q["Respuesta o resumen"]
  P --> Q
  Q --> R["Exportación"]
  R --> S["Telemetría"]
  S --> T["Finalización"]
```

### Estado compartido

| Campo | Uso |
| --- | --- |
| `job_id` | Idempotencia, estado, cancelación y trazabilidad |
| `document_id` | Filtro obligatorio de documento |
| `owner_id` | Aislamiento de propietario |
| `task_type` | Ruta del grafo |
| `agent_run_id` | Correlación de preguntas y extracción |
| `payload` | Entrada validada de la tarea |
| `result` | Salida persistida |

### Resiliencia

- Cada nodo relevante actualiza `processing_jobs` y `graph_checkpoints`.
- `cancel_requested` se revisa antes de avanzar.
- El mensaje permanece invisible durante 3.600 segundos.
- Un fallo transitorio deja el mensaje en la cola para reintento.
- El tercer fallo envía una copia a `document_jobs_dlq` y archiva el original.
- Un trabajo `completed` o `cancelled` se archiva sin repetir efectos.
- La reindexación elimina e inserta páginas y chunks bajo el mismo documento.

## Modelo entidad relación

```mermaid
erDiagram
  AUTH_USERS ||--o| PROFILES : tiene
  ORGANIZATIONS ||--o{ PROFILES : agrupa
  AUTH_USERS ||--o{ DOCUMENTS : posee
  ORGANIZATIONS ||--o{ DOCUMENTS : separa
  DOCUMENTS ||--o{ DOCUMENT_VERSIONS : versiona
  DOCUMENTS ||--o{ DOCUMENT_PAGES : contiene
  DOCUMENTS ||--o{ DOCUMENT_CHUNKS : indexa
  DOCUMENTS ||--o{ PROCESSING_JOBS : procesa
  PROCESSING_JOBS ||--o{ PROCESSING_STEPS : detalla
  PROCESSING_JOBS ||--o{ GRAPH_CHECKPOINTS : conserva
  PROCESSING_JOBS ||--o| AGENT_RUNS : ejecuta
  AGENT_RUNS ||--o{ LLM_CALLS : registra
  AGENT_RUNS ||--o{ TOOL_CALLS : registra
  DOCUMENTS ||--o{ CONVERSATIONS : conversa
  CONVERSATIONS ||--o{ MESSAGES : contiene
  DOCUMENTS ||--o{ EXTRACTION_RESULTS : extrae
  EXTRACTION_RESULTS ||--o{ EXTRACTED_FIELDS : desglosa
  EXTRACTION_RESULTS ||--o{ HUMAN_REVIEWS : revisa
  ORGANIZATIONS ||--o{ ROI_BASELINES : mide
  ROI_BASELINES ||--o{ ROI_EVENTS : calcula
```

El archivo `database/migrations/0001_initial.sql` crea 33 tablas, índices HNSW, búsqueda textual, RLS y funciones RPC del RAG.

## Límites del MVP

- Un worker local activo define la capacidad de procesamiento.
- Si el worker permanece apagado, la cola crece sin perder mensajes.
- Ollama y OCR consumen CPU, RAM y VRAM del equipo local.
- La consulta usa polling desde Angular. SSE está expuesto en la API para una evolución.
- El frontend implementa funciones de usuario. Administración y revisión humana quedan para el piloto.

## SLO inicial

| Indicador | Objetivo piloto |
| --- | --- |
| Disponibilidad API | 99,5% mensual |
| Metadatos API p95 | Menos de 700 ms, sin cold start |
| Creación de trabajo p95 | Menos de 1,5 s |
| Inicio de trabajo | Menos de 30 s con worker activo |
| Extracción nativa | Menos de 1 s por página p95 |
| OCR | Menos de 8 s por página p95 |
| Respuesta RAG | Menos de 20 s p95 en hardware local |
| Tasa de trabajos exitosos | Mayor o igual a 98% |

Valida estos valores con PDF reales y la red de Bogotá antes del piloto.

