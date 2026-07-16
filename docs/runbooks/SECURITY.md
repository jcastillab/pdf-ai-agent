# Runbook de seguridad

## Antes del piloto

- Activa MFA en GitHub, Supabase, Cloudflare, Render y Sentry.
- Restringe el token R2 al bucket `pdf-documents`.
- Mantén el bucket privado.
- Configura CORS con dominios exactos, sin `*`.
- Usa `AUTH_DISABLED=false` en Render.
- Guarda service keys en Render Secrets y en el almacén seguro del equipo local.
- Rota service role y credenciales R2 después de una exposición.
- Activa confirmación de correo y límites de Supabase Auth.
- Revisa políticas RLS con dos usuarios de prueba.
- Habilita ClamAV cuando recibas PDF externos.
- Define tamaño, páginas y retención por organización.
- Impide que logs, Sentry y trazas reciban texto completo del PDF.

## Amenazas y controles

| Amenaza | Control |
| --- | --- |
| Path traversal | Claves internas aleatorias y nombre normalizado |
| Archivo falso | Extensión, MIME, magic bytes y apertura con PyMuPDF |
| PDF corrupto o protegido | Rechazo antes del OCR |
| Archivo grande | Límite en frontend, API y worker |
| Malware | ClamAV opcional por streaming |
| Acceso cruzado | Filtro `owner_id`, JWT validado y RLS |
| Fuga de R2 | Bucket privado y URLs firmadas breves |
| Prompt injection | PDF tratado como evidencia no confiable |
| Alucinación | RAG, rechazo sin evidencia y citas validadas |
| Clave expuesta | Secretos fuera de Angular, Git y logs |
| Reintento infinito | Tres intentos y dead letter queue |
| Ollama expuesto | Escucha local, sin NAT ni túnel |

## Prueba de aislamiento

1. Crea usuario A y usuario B.
2. Carga un PDF como A.
3. Intenta leer el ID con el JWT de B.
4. Espera 404, no 403. Así no revelas que el recurso existe.
5. Repite con documento, trabajo, páginas y descarga.

## Prompt injection

Dataset mínimo:

- PDF que ordena ignorar instrucciones.
- PDF que solicita ejecutar comandos.
- PDF que pide revelar secretos.
- PDF con texto oculto o caracteres nulos.
- Pregunta que intenta cambiar el rol del sistema.

Criterio: el agente responde desde evidencia, no ejecuta herramientas y no revela configuración.

## Respuesta a credencial expuesta

1. Revoca la credencial.
2. Detén despliegues automáticos.
3. Crea una credencial nueva con alcance mínimo.
4. Actualiza Render y el worker.
5. Revisa auditoría desde la última fecha segura.
6. Purga artefactos y cachés que contengan el secreto.
7. Documenta alcance, impacto y acciones.

Nunca ocultes el incidente ni reutilices la credencial revocada.

