# Diccionario del modelo de datos

La migración SQL define campos, tipos, claves, restricciones e índices. Esta tabla añade finalidad, sensibilidad, retención y particionamiento.

| Tabla | Finalidad | Claves e índices principales | Sensibilidad | Retención inicial | Partición al escalar |
| --- | --- | --- | --- | --- | --- |
| `organizations` | Tenant y configuración | PK `id`, UQ `slug` | Configuración | Vida del cliente + 90 días | No |
| `profiles` | Perfil de `auth.users` | PK/FK `id`, FK organización | PII | Cuenta + 90 días | No |
| `roles` | Catálogo RBAC | PK, UQ `code` | Baja | Indefinida | No |
| `permissions` | Permisos | PK, UQ `code` | Baja | Indefinida | No |
| `role_permissions` | Relación rol permiso | PK compuesta | Baja | Indefinida | No |
| `user_roles` | Roles del usuario | PK compuesta, FK usuario | Identidad | Cuenta + 90 días | No |
| `documents` | Metadatos del PDF | Owner y fecha, hash, estado | Alta | Política del tenant | Organización si supera 50 M |
| `document_versions` | Historial de objetos | UQ documento y versión | Alta | Igual al documento | Documento |
| `document_pages` | Texto por página | UQ documento y página | Alta | Igual al documento | Hash de documento |
| `document_chunks` | Fragmentos y embeddings | UQ chunk, HNSW, GIN FTS | Alta | Igual al documento | Hash de documento |
| `processing_jobs` | Estado asíncrono | Owner y fecha, estado | Media | 12 meses | Mes por `created_at` |
| `processing_steps` | Duración y error por nodo | Job y fecha | Media | 6 meses | Mes |
| `extraction_templates` | Esquemas de campos | Organización, nombre y versión | Media | Indefinida versionada | No |
| `extraction_results` | Salida estructurada | Documento y template | Alta | Igual al documento | Mes si alto volumen |
| `extracted_fields` | Campo, fuente y confianza | Resultado | Alta | Igual al resultado | Resultado |
| `conversations` | Sesión de chat | Owner y documento | Alta | 12 meses o política | Mes |
| `messages` | Mensajes y citas | Conversación y fecha | Alta | 12 meses o política | Mes |
| `agent_runs` | Ejecución del agente | Owner, trabajo, documento, traza | Media | 12 meses | Mes |
| `graph_checkpoints` | Recuperación del grafo | Job y fecha | Media | 30 días | Mes |
| `llm_calls` | Modelo, tokens, costo y latencia | Owner y fecha, documento | Media | 13 meses | Mes |
| `tool_calls` | Uso de herramientas | Agent run y fecha | Media | 13 meses | Mes |
| `token_usage` | Desglose de tokens | FK llamada LLM | Baja | 13 meses | Mes |
| `model_prices` | Tarifas históricas | Proveedor, modelo y fecha | Pública | Indefinida | Año |
| `feedback` | Calidad y corrección | Run y usuario | Alta | 13 meses | Mes |
| `human_reviews` | Decisiones humanas | Documento, resultado, revisor | Alta | 24 meses | Mes |
| `audit_logs` | Acciones auditables | Fecha, recurso, actor, traza | Alta | 24 meses | Mes |
| `security_events` | Eventos de acceso y seguridad | Tipo, severidad y fecha | Alta | 24 meses | Mes |
| `error_events` | Errores técnicos | Job, código, huella y fecha | Media | 6 meses | Mes |
| `roi_baselines` | Línea base del proceso | Organización y vigencia | Comercial | 36 meses | Año |
| `roi_events` | Ahorro por documento | Baseline, documento y fecha | Comercial | 36 meses | Mes |
| `roi_monthly_summary` | Agregado mensual | UQ organización y mes | Comercial | Indefinida | Año |
| `prompt_versions` | Plantillas versionadas | UQ nombre y versión | Propiedad intelectual | Indefinida | No |
| `model_configurations` | Enrutamiento de modelos | Organización y tarea | Configuración | Indefinida versionada | No |

## Datos que no se guardan

- PDF binario en PostgreSQL.
- JWT o refresh tokens.
- Credenciales de R2, Supabase u Ollama.
- Prompt completo y respuesta completa dentro de logs técnicos.
- Stack traces enviados al navegador.

## Índices

- HNSW con distancia coseno para `document_chunks.embedding`.
- GIN sobre `to_tsvector('spanish', text)` para recuperación textual.
- Índices compuestos por propietario, estado y fecha.
- Hash SHA 256 para detección de duplicados futura.

## RLS

El frontend no escribe documentos ni trabajos directo en PostgREST. Las políticas de lectura garantizan propietario. La API repite el filtro, aunque RLS exista. El worker usa `service_role` y recibe IDs desde una cola privada.

Antes del piloto añade políticas específicas para administración, revisores y organización. No uses una política global basada en datos enviados por el frontend.

