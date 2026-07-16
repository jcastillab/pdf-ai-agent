# Runbook de despliegue

## Orden inicial

1. Supabase y migraciones.
2. Colas y permisos `service_role`.
3. Bucket R2, CORS y credenciales.
4. Render API.
5. Sentry.
6. Cloudflare Pages.
7. DNS.
8. Worker local y Ollama.
9. Smoke test completo.

## Smoke test

1. `GET /api/v1/health` devuelve 200.
2. Registra y confirma un usuario.
3. Carga un PDF digital de dos páginas.
4. Confirma que R2 contiene el objeto privado.
5. Confirma mensaje en `document_jobs`.
6. Inicia worker.
7. Espera estado `completed`.
8. Verifica páginas, resumen y chunks.
9. Pregunta un dato existente y valida cita.
10. Pregunta un dato inexistente y espera rechazo por falta de evidencia.
11. Revisa `llm_calls`, Sentry y trazas.

## DNS recomendado

| Subdominio | Destino |
| --- | --- |
| `app.dominio.com` | Cloudflare Pages |
| `api.dominio.com` | Render custom domain |
| `status.dominio.com` | Página de estado futura |
| `docs.dominio.com` | Documentación futura |

Configura TLS administrado, redirección HTTPS, MFA, CAA, bloqueo de transferencia y renovación automática.

## Producción

- Protege `main`.
- Exige PR, revisión y CI exitoso.
- Ejecuta migraciones compatibles antes del código que las necesita.
- Mantén columnas anteriores durante una versión.
- Ejecuta smoke test después de cada despliegue.
- Conserva la versión anterior de Render para rollback.
- Separa proyectos Supabase, buckets R2 y dominios por ambiente.

## Actualizar Angular

1. Crea rama `chore/angular-18`.
2. Ejecuta `ng update @angular/core@18 @angular/cli@18`.
3. Corrige Material y TypeScript.
4. Ejecuta build y pruebas.
5. Despliega preview de Cloudflare.
6. Repite una versión mayor por PR.

No combines una actualización mayor con cambios de negocio.

