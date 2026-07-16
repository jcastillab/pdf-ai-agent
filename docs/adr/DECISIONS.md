# Registro de decisiones de arquitectura

Fecha de decisiones: 14 de julio de 2026. Estado inicial: aceptado.

## ADR 001, Angular 17

- Contexto: requisito explícito del proyecto, aunque perdió soporte activo.
- Decisión: conservar Angular 17.3 en el MVP.
- Alternativas: Angular vigente, React, Vue.
- Ventaja: cumple el estándar definido y usa componentes standalone.
- Desventaja: riesgo de seguridad y compatibilidad.
- Consecuencia: migración mayor por PR después del piloto.

## ADR 002, FastAPI

- Contexto: procesamiento PDF y pruebas con Pytest viven en Python.
- Decisión: FastAPI con Pydantic y SQLAlchemy.
- Alternativas: NestJS, Django REST Framework.
- Ventaja: OpenAPI, async y ecosistema documental.
- Desventaja: el equipo mantiene TypeScript y Python.
- Consecuencia: esquemas compartidos se derivan de OpenAPI.

## ADR 003, LangGraph

- Contexto: trabajos requieren estado, rutas, reintentos y revisión futura.
- Decisión: LangGraph enruta tareas y cada etapa persiste checkpoint.
- Alternativas: funciones lineales, Celery Canvas.
- Ventaja: evolución hacia interrupciones humanas.
- Desventaja: agrega una abstracción.
- Consecuencia: el estado conserva IDs, no binarios ni texto completo.

## ADR 004, PostgreSQL administrado

- Contexto: metadatos, trabajos, telemetría y ROI son relacionales.
- Decisión: Supabase PostgreSQL.
- Alternativas: Render PostgreSQL, Neon, Azure PostgreSQL.
- Ventaja: Auth, RLS, Queues y pgvector integrados.
- Desventaja: dependencia del proveedor.
- Consecuencia: SQL estándar y S3 compatible conservan portabilidad.

## ADR 005, pgvector

- Contexto: el MVP no justifica otro motor vectorial.
- Decisión: vector de 768 dimensiones e índice HNSW.
- Alternativas: Qdrant, Weaviate, Pinecone.
- Ventaja: filtro transaccional por documento.
- Desventaja: telemetría y vectores comparten recursos.
- Consecuencia: migrar a motor dedicado cuando latencia p95 o volumen incumplan SLO.

## ADR 006, Cloudflare R2

- Contexto: los PDF no pertenecen en tablas operativas.
- Decisión: bucket privado y URLs firmadas.
- Alternativas: Supabase Storage, S3, Azure Blob, MinIO.
- Ventaja: API S3 y egress directo sin tarifa de R2.
- Desventaja: servicio adicional y CORS.
- Consecuencia: claves aleatorias, ciclo de vida y separación por ambiente.

## ADR 007, Supabase Queues

- Contexto: el procesamiento no debe bloquear HTTP.
- Decisión: pgmq con cola principal y DLQ.
- Alternativas: Celery más Redis, RabbitMQ, SQS.
- Ventaja: menos servicios y durabilidad PostgreSQL.
- Desventaja: consumidor por polling y visibilidad fija.
- Consecuencia: migrar a broker dedicado con varios workers y alto volumen.

## ADR 008, Supabase Auth

- Contexto: se necesitan sesiones, correo, recuperación y JWT.
- Decisión: frontend contra Supabase Auth, backend valida JWT.
- Alternativas: Entra ID, Auth0, Keycloak, Cognito.
- Ventaja: integración con RLS.
- Desventaja: SSO empresarial queda pendiente.
- Consecuencia: Entra ID se evalúa cuando el cliente Microsoft lo exija.

## ADR 009, OpenTelemetry

- Contexto: una solicitud cruza frontend, API, cola, worker y modelo.
- Decisión: trazas OTLP con IDs correlacionados.
- Alternativas: instrumentación propietaria.
- Ventaja: formato abierto.
- Desventaja: costo y volumen si no se muestrea.
- Consecuencia: muestreo y retención por ambiente.

## ADR 010, logs estructurados

- Contexto: soporte necesita buscar por trabajo sin guardar el PDF.
- Decisión: JSON con `request_id`, `job_id`, etapa y código.
- Alternativas: texto libre.
- Ventaja: correlación y alertas.
- Desventaja: exige disciplina de campos.
- Consecuencia: texto del PDF, JWT y secretos quedan prohibidos.

## ADR 011, nube distribuida

- Contexto: el usuario definió Cloudflare, Render y Supabase.
- Decisión: conservar esos servicios y acercar regiones.
- Alternativas: Azure, AWS o GCP integrados.
- Ventaja: costo inicial bajo.
- Desventaja: latencia entre proveedores.
- Consecuencia: medir cada enlace antes de producción.

## ADR 012, despliegue desacoplado

- Contexto: frontend estático, API y worker tienen ciclos diferentes.
- Decisión: Pages para Angular, Render para API y proceso local para worker.
- Alternativas: monolito en una VM.
- Ventaja: despliegues y escalado independientes.
- Desventaja: más configuración.
- Consecuencia: contratos versionados bajo `/api/v1`.

## ADR 013, abstracción de modelos

- Contexto: Ollama es inicial, no debe contaminar reglas de negocio.
- Decisión: cliente con `generate`, `embed` y `health_check`.
- Alternativas: llamadas directas en cada nodo.
- Ventaja: reemplazo de proveedor.
- Desventaja: interfaz adicional.
- Consecuencia: agregar OpenAI, Anthropic o vLLM como adaptadores.

## ADR 014, retención

- Contexto: PDF, texto y telemetría crecen a ritmos distintos.
- Decisión: política configurable por organización.
- Alternativas: retención indefinida.
- Ventaja: control de costo y privacidad.
- Desventaja: restauración limitada después de eliminar.
- Consecuencia: borrado auditado y ciclo de vida R2.

## ADR 015, multiempresa

- Contexto: la solución debe crecer a varias organizaciones.
- Decisión: `organization_id` en datos compartidos y `owner_id` obligatorio en MVP.
- Alternativas: una base por cliente.
- Ventaja: operación simple y filtros consistentes.
- Desventaja: RLS requiere pruebas estrictas.
- Consecuencia: organización dedicada cuando regulación o escala lo exija.

## ADR 016, revisión humana

- Contexto: OCR y LLM no garantizan exactitud.
- Decisión: resultados bajo umbral crean `human_reviews`.
- Alternativas: aprobación automática total.
- Ventaja: reduce riesgo empresarial.
- Desventaja: agrega tiempo y costo.
- Consecuencia: el piloto mide correcciones para ajustar umbrales.

