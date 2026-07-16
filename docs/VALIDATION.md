# Validación de la entrega

Fecha: 14 de julio de 2026.

## Resultado

| Control | Resultado |
| --- | --- |
| Build de Angular 17 | Aprobado, bundle de producción generado |
| Pruebas de FastAPI | 10 aprobadas |
| Cobertura de FastAPI | 71.17%, mínimo CI 70% |
| Pruebas del worker | 13 aprobadas |
| Cobertura del worker | 63.21%, mínimo CI 55% |
| Ruff | Aprobado |
| Mypy | Aprobado en 35 archivos Python |
| OpenAPI | Aprobado, 22 rutas y operaciones principales presentes |
| YAML y JSON de infraestructura | Sintaxis aprobada |
| Assets de Cloudflare Pages | `_redirects` y `assets/config.json` presentes en el build |

## Límite del entorno de validación

La prueba unitaria de Angular usa Chrome Headless. El entorno de construcción no tenía un binario de Chrome. El workflow de GitHub Actions instala Chrome antes de ejecutar `npm test`.

La prueba de integración completa requiere credenciales y recursos externos del propietario: proyecto Supabase, bucket R2, servicio Render, proyecto Cloudflare Pages y Sentry. Tras configurar esos recursos, ejecuta el smoke test de `docs/runbooks/DEPLOYMENT.md`.

Docker no estaba instalado en el entorno de construcción. Se validó la sintaxis de `docker-compose.yml` y de los archivos YAML asociados. Ejecuta `docker compose config` en la máquina de destino antes de iniciar los perfiles locales.
