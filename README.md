# DocuMind, agente web para procesamiento de PDF

MVP web con Angular 17, FastAPI, Supabase, Cloudflare R2 y un worker Python local que usa Ollama. El sistema carga PDF, valida su integridad, extrae texto, aplica OCR en páginas escaneadas, crea embeddings, genera un resumen y responde preguntas con citas por página.

## Estado de la entrega

Implementado:

- Registro, login, recuperación y cierre de sesión con Supabase Auth.
- Carga directa del navegador a un bucket privado de R2 mediante URL firmada.
- API FastAPI desplegable en Render.
- Cola durable con Supabase Queues y dead letter queue.
- Worker local sin puertos públicos ni túneles hacia TU computador.
- Validación por extensión, MIME, magic bytes, tamaño, páginas y estructura del PDF.
- Antivirus ClamAV opcional.
- Extracción con PyMuPDF y OCR selectivo con Tesseract.
- Segmentación con trazabilidad por página.
- Embeddings de Ollama y RAG híbrido sobre pgvector más búsqueda textual.
- Respuestas con citas validadas contra los fragmentos recuperados.
- Resumen y extracción estructurada mediante trabajos asíncronos.
- Estados, cancelación, reintentos, checkpoints y dead letter queue.
- Registro de tokens, latencia, proveedor, modelo y costo estimado.
- Panel Angular de documentos, telemetría y chat.
- Sentry, logs JSON y OpenTelemetry.
- Pruebas de API, validadores y procesamiento documental.
- GitHub Actions, Render Blueprint y despliegue de Cloudflare Pages.

Preparado en esquema y documentación, pendiente de interfaz completa:

- Revisión humana, comparación, administración de usuarios, modelos y prompts.
- Tablero ROI avanzado, auditoría y alertas.
- Evals de IA, pruebas de carga y conectores empresariales.

## Arquitectura seleccionada

| Capa | Tecnología | Responsabilidad |
| --- | --- | --- |
| Frontend | Angular 17, Material, RxJS | Login, carga, historial, estados, chat y panel |
| Hosting web | Cloudflare Pages | Sitio estático, TLS y despliegues de preview |
| API | FastAPI en Render | Autorización, metadatos, URLs firmadas, trabajos y telemetría |
| Identidad | Supabase Auth | Usuarios, sesiones, recuperación y JWT |
| Datos | Supabase PostgreSQL | Estado transaccional, auditoría, telemetría y ROI |
| Vectores | pgvector | Embeddings y recuperación semántica |
| Cola | Supabase Queues, pgmq | Entrega durable, visibilidad, reintentos y archivo |
| Objetos | Cloudflare R2 | PDF privados fuera de PostgreSQL |
| Procesamiento | Worker Python local | Extracción, OCR, embeddings, RAG y LangGraph |
| IA | Ollama local | Chat y embeddings sin enviar el PDF a un proveedor externo |
| Monitoreo | Sentry y OpenTelemetry | Errores, trazas, latencias y correlación |

Render nunca llama a Ollama. El worker inicia conexiones salientes hacia Supabase y R2. No abras el puerto 11434 en Internet.

## Flujo principal

1. Angular obtiene una URL `PUT` firmada desde FastAPI.
2. El navegador carga el PDF directo a R2.
3. FastAPI verifica el objeto con `HEAD`, crea un trabajo y lo envía a Supabase Queues.
4. El worker local lee el mensaje con un tiempo de visibilidad.
5. El worker descarga el PDF, valida, extrae, aplica OCR, segmenta e indexa.
6. Ollama genera el resumen. El worker guarda resultados y telemetría.
7. Angular consulta el estado en FastAPI.
8. Una pregunta crea otro trabajo. El worker recupera evidencia, consulta Ollama y guarda respuesta con citas.

Los diagramas completos están en [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md).

## Requisitos

- Node.js 20 LTS para Angular 17.
- Python 3.12.
- Git y Docker Desktop.
- Ollama.
- Tesseract con paquetes `spa` y `eng`.
- Cuentas en Supabase, Cloudflare, Render, GitHub y Sentry.

En Windows instala Tesseract y agrega su carpeta al `PATH`. Confirma con:

```powershell
tesseract --version
ollama --version
```

Descarga los modelos:

```powershell
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

`nomic-embed-text` genera 768 dimensiones. Si cambias el modelo, ajusta `EMBEDDING_DIMENSIONS` y la columna `vector(768)` mediante una migración.

## 1. Configurar Supabase

1. Crea un proyecto.
2. En SQL Editor ejecuta, en orden:
   - `database/migrations/0001_initial.sql`
   - `database/migrations/0002_queues.sql`
   - `database/seeds/0001_roles.sql`
3. Abre `Integrations > Queues`.
4. Confirma las colas `document_jobs` y `document_jobs_dlq`.
5. Activa `Expose Queues via PostgREST`.
6. Concede `Select`, `Insert`, `Update` y `Delete` al rol `service_role` en ambas colas.
7. No concedas acceso de colas a `anon` ni `authenticated`.
8. En Authentication activa correo y define las URL permitidas:
   - `http://localhost:4200`
   - `https://app.TU_DOMINIO.com`
9. Copia Project URL, anon key, service role key y la URL del pooler de PostgreSQL.

La anon key es pública y pertenece al frontend. La service role key es secreta y pertenece a Render y al worker.

## 2. Configurar Cloudflare R2

1. Crea el bucket privado `pdf-documents`.
2. Crea credenciales S3 limitadas a ese bucket.
3. Aplica la política CORS de `infrastructure/cloudflare/r2-cors.json`.
4. Reemplaza `https://app.TU_DOMINIO.com` por TU dominio real.
5. Mantén desactivado el acceso público.
6. Define una regla de ciclo de vida según TU política de retención.

La API firma cada operación sobre una clave aleatoria. La URL vence en 15 minutos para cargas y 5 minutos para descargas.

## 3. Variables de entorno

Copia `.env.example` como `.env`. Completa valores reales. Nunca confirmes `.env` en Git.

Variables secretas:

- `DATABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `SENTRY_DSN`

Variables públicas del frontend:

- `FRONTEND_API_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

Genera `assets/config.json`:

```bash
node scripts/configure-frontend.mjs
```

## Inicio rápido local en Windows

Antes de iniciar, confirma que Docker Desktop y Ollama estén funcionando y que los archivos de configuración local ya existan:

- `apps/backend-api/.env`
- `apps/worker/.env`
- `apps/frontend-angular/src/assets/config.json`

Desde la raíz del repositorio ejecuta:

```powershell
.\scripts\start-local.ps1

El script valida las dependencias y abre terminales independientes para:

- FastAPI en http://127.0.0.1:8000
- Angular en http://localhost:4200
- Worker Python local
- Ollama en http://127.0.0.1:11434

También abre automáticamente la aplicación y la documentación de la API.

Para evitar abrir el navegador:
```powershell
.\scripts\start-local.ps1 -SkipBrowser

Para comprobar el estado de los cuatro servicios:
```powershell
.\scripts\status-local.ps1
## 4. Ejecutar el frontend

```bash
cd apps/frontend-angular
npm ci
npm start
```

Abre `http://localhost:4200`.

## 5. Ejecutar la API

```bash
cd apps/backend-api
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Linux o macOS:

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Revisa:

- API: `http://localhost:8000/api/v1/health`
- OpenAPI: `http://localhost:8000/docs`

`AUTH_DISABLED=true` está restringido por código a `development` y `test`. No lo actives en Render.

## 6. Ejecutar el worker local

Mantén `ollama serve` activo. Luego ejecuta:

```powershell
.\scripts\start-worker.ps1
```

Alternativa manual:

```powershell
cd apps\worker
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m worker.main
```

El worker necesita estas variables:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- Credenciales R2
- Modelos Ollama

Cuando el equipo se apaga, los trabajos permanecen en cola. Al encenderlo y ejecutar el worker, el procesamiento continúa.

## Infraestructura auxiliar con Docker

MinIO local:

```bash
docker compose up -d minio minio-setup
```

Ollama en contenedor:

```bash
docker compose --profile local-ai up -d ollama
```

Observabilidad:

```bash
docker compose --profile observability up -d
```

Abre Grafana en `http://localhost:3000`, usuario `admin`, contraseña `admin`. Cambia la contraseña fuera de desarrollo.

El perfil `standalone-db` ofrece PostgreSQL con pgvector para pruebas aisladas. El flujo completo de autenticación y cola requiere Supabase administrado o Supabase CLI.

## Despliegue

### Backend en Render

1. Conecta el repositorio.
2. Crea el servicio desde `render.yaml`.
3. Carga las variables secretas.
4. Usa plan Starter para evitar suspensión del piloto.
5. Confirma `/api/v1/health`.
6. Define `CORS_ORIGINS` con el dominio exacto de Cloudflare Pages.

### Frontend en Cloudflare Pages

GitHub Actions despliega `apps/frontend-angular/dist/frontend-angular/browser`. Configura:

Secrets:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `SUPABASE_ANON_KEY`
- `RENDER_DEPLOY_HOOK_URL`

Variables:

- `FRONTEND_API_URL`
- `SUPABASE_URL`
- `API_HEALTH_URL`

La regla `_redirects` permite abrir rutas Angular directamente.

## Pruebas

Frontend:

```bash
cd apps/frontend-angular
npm run build
npm test
```

Backend y worker:

```bash
python -m pip install -r apps/backend-api/requirements-dev.txt -r apps/worker/requirements.txt
PYTHONPATH=apps/backend-api pytest apps/backend-api/tests
PYTHONPATH=apps/worker pytest apps/worker/tests
ruff check apps/backend-api apps/worker
```

## Seguridad aplicada

- El frontend jamás recibe service keys ni credenciales R2.
- Los binarios quedan fuera de PostgreSQL.
- Cada consulta filtra por `owner_id` y las tablas sensibles tienen RLS.
- El nombre del objeto no usa la ruta aportada por el usuario.
- El worker trata el texto del PDF como datos no confiables.
- Las citas se aceptan cuando la página y el fragmento existen en la evidencia recuperada.
- El modelo recibe fragmentos controlados, no el PDF completo.
- Los logs evitan texto completo, tokens y secretos.
- Las URLs firmadas son credenciales temporales.
- Los trabajos tienen límite de reintentos y dead letter queue.

Consulta [docs/runbooks/SECURITY.md](docs/runbooks/SECURITY.md) antes de un piloto con datos reales.

## Estructura

```text
pdf-ai-agent/
├── apps/
│   ├── frontend-angular/
│   ├── backend-api/
│   └── worker/
├── database/
│   ├── migrations/
│   └── seeds/
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── api/
│   ├── roi/
│   └── runbooks/
├── infrastructure/
├── packages/
├── scripts/
├── tests/
├── .github/workflows/
├── docker-compose.yml
├── render.yaml
└── .env.example
```

## Documentación

- [Arquitectura y diagramas](docs/architecture/ARCHITECTURE.md)
- [Catálogo de endpoints](docs/api/ENDPOINTS.md)
- [Despliegue](docs/runbooks/DEPLOYMENT.md)
- [Seguridad](docs/runbooks/SECURITY.md)
- [Incidentes y rollback](docs/runbooks/INCIDENTS.md)
- [ROI](docs/roi/METHOD.md)
- [Costos](docs/COSTS.md)
- [Validación de la entrega](docs/VALIDATION.md)
- [Roadmap, backlog, RACI y riesgos](docs/PLAN.md)
- [Decisiones ADR](docs/adr/DECISIONS.md)

## Versiones y soporte

Angular 17 se mantiene por requisito. Está fuera de soporte activo. La ruta definida es actualizar primero a Angular 18, ejecutar pruebas, luego avanzar una versión mayor por pull request hasta una versión LTS vigente. No mezcles la migración de Angular con cambios funcionales.

## Referencias técnicas verificadas el 14 de julio de 2026

- [Supabase Queues](https://supabase.com/docs/guides/queues)
- [API de Supabase Queues](https://supabase.com/docs/guides/queues/api)
- [URLs firmadas de Cloudflare R2](https://developers.cloudflare.com/r2/api/s3/presigned-urls/)
- [Angular en Cloudflare Pages](https://developers.cloudflare.com/pages/framework-guides/deploy-an-angular-site/)
- [FastAPI en Render](https://render.com/docs/deploy-fastapi)
