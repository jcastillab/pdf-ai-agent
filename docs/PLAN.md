# Plan de producto

## Alcance por etapa

### MVP, incluido en este repositorio

- Autenticación, PDF privado, extracción, OCR, resumen, RAG con citas.
- Trabajo asíncrono, estados, reintentos, cancelación y DLQ.
- Historial, chat, panel inicial, tokens, costo y errores.
- Pruebas, CI/CD y despliegue.

### Piloto empresarial

- Revisión humana, tablas, comparación y clasificación.
- Plantillas por documento y roles por área.
- Evals, alertas, backups, retención y tablero ROI.

### Producción

- Dos o más workers, continuidad, SLO contractual y escalado.
- Ambientes separados, secretos administrados y pruebas de carga.
- Gobierno de modelos, auditoría externa y políticas de privacidad.

## Roadmap de doce semanas

| Semana | Objetivo | Entregable | Criterio | Riesgo |
| --- | --- | --- | --- | --- |
| 1 | Casos y línea base | Mapa de procesos y métricas | Caso prioritario aprobado | Alcance difuso |
| 2 | Arquitectura | ADR, ER y repositorio | Revisión técnica aprobada | Región incorrecta |
| 3 | Identidad | Login, JWT y roles | Usuario A no lee datos de B | RLS incompleta |
| 4 | Carga | R2, validación y trabajos | PDF válido llega a cola | CORS y tamaño |
| 5 | Extracción | Texto nativo y OCR | Dataset documental pasa | OCR deficiente |
| 6 | RAG | Chunks, embeddings y citas | Preguntas conocidas con fuente | Evidencia pobre |
| 7 | LangGraph | Estado, reintento y cancelación | Recuperación tras caída | Duplicados |
| 8 | Frontend | Historial, detalle y chat | Flujo de punta a punta | Estados confusos |
| 9 | Telemetría | Tokens, latencia y Sentry | Trazabilidad por trabajo | PII en logs |
| 10 | ROI y seguridad | Línea base, guardrails y evals | Indicadores calculados | Beneficio no probado |
| 11 | Rendimiento | Carga, estrés y correcciones | SLO piloto medido | Equipo local limitado |
| 12 | Despliegue | CI/CD, rollback y capacitación | Criterios globales aprobados | Operación dependiente |

Responsable de observabilidad, telemetría y ROI: Juan Esteban Castilla Baquero.

## Backlog priorizado

| ID | Épica | Historia o tarea | Prioridad | Estimación | Dependencia | Terminado cuando |
| --- | --- | --- | --- | ---: | --- | --- |
| AUTH-1 | Autenticación | Registro, login y recuperación | P0 | 5 | Supabase | Flujos probados |
| SEC-1 | Seguridad | JWT, RLS y aislamiento | P0 | 8 | AUTH-1 | Prueba A/B pasa |
| DOC-1 | Documentos | URL firmada y R2 privado | P0 | 8 | SEC-1 | Carga y descarga autorizada |
| JOB-1 | Jobs | Cola, worker, retry y DLQ | P0 | 13 | DOC-1 | Caída recuperable |
| PDF-1 | PDF | Validación y texto nativo | P0 | 8 | JOB-1 | Dataset básico pasa |
| OCR-1 | OCR | OCR selectivo Tesseract | P0 | 8 | PDF-1 | Escaneados legibles |
| RAG-1 | RAG | Chunking y pgvector | P0 | 13 | PDF-1 | Índice con página |
| AGT-1 | Agente | Respuesta con rechazo y citas | P0 | 13 | RAG-1 | Citas verificadas |
| UI-1 | Frontend | Historial, estado y detalle | P0 | 8 | DOC-1 | Responsive y accesible |
| UI-2 | Frontend | Chat por trabajo | P0 | 8 | AGT-1 | Pregunta completa |
| OBS-1 | Telemetría | Tokens, latencia y costo | P0 | 8 | JOB-1 | Panel inicial |
| DEV-1 | DevOps | CI, Render y Pages | P0 | 8 | Pruebas | Main despliega |
| REV-1 | Revisión | Bandeja de baja confianza | P1 | 13 | Extracción | Decisión auditada |
| TAB-1 | Tablas | Camelot y fallback | P1 | 13 | PDF-1 | Dataset de tablas pasa |
| CMP-1 | Comparación | Diferencias con citas | P1 | 13 | RAG-1 | Resultado verificable |
| EVAL-1 | QA IA | Dataset de regresión | P1 | 13 | AGT-1 | Umbrales en CI |
| ROI-1 | ROI | Línea base y resumen mensual | P1 | 8 | OBS-1 | Ahorro reproducible |
| ADM-1 | Administración | Usuarios, prompts y modelos | P2 | 13 | RBAC | Cambios auditados |
| INT-1 | Integraciones | Correo y almacenamiento | P2 | 21 | Piloto | Conector aislado |

Estimación en puntos Fibonacci. P0 bloquea piloto, P1 completa piloto, P2 pertenece a evolución.

## Definición de terminado

- Criterios de aceptación automatizados.
- Revisión de seguridad cuando afecta identidad, PDF o secretos.
- Sin advertencias de lint.
- Cobertura acordada.
- Migración compatible y documentada.
- Logs sin PII ni contenido completo.
- Métricas y errores instrumentados.
- README y runbook actualizados.
- Preview desplegado.
- Rollback definido.

## Matriz RACI

Roles: PO, Arquitectura, Frontend, Backend, IA, Datos, QA, DevOps, Seguridad, Observabilidad.

| Frente | Descubrimiento | Diseño | Construcción | Pruebas | Operación |
| --- | --- | --- | --- | --- | --- |
| MCP e integraciones | A/PO | R/Arquitectura | R/Backend | C/QA | C/DevOps |
| Orquestación | C/PO | A/Arquitectura | R/IA | R/QA | C/Observabilidad |
| RAG | C/PO | A/IA | R/IA | R/QA | C/Datos |
| Prompts y skills | A/PO | R/IA | R/IA | R/QA | C/Observabilidad |
| Evals y QA | C/PO | A/QA | R/QA | R/QA | C/IA |
| Economía de tokens | A/PO | R/Observabilidad | C/IA | R/QA | R/Observabilidad |
| Backend e infraestructura | C/PO | A/Arquitectura | R/Backend | C/QA | R/DevOps |
| Angular 17 | C/PO | A/Frontend | R/Frontend | R/QA | C/DevOps |
| Seguridad y gobierno | C/PO | A/Seguridad | R/Seguridad | R/QA | R/Seguridad |
| Resiliencia | C/PO | A/Arquitectura | R/Backend | R/QA | R/DevOps |
| Observabilidad y ROI | A/PO | R/Observabilidad | R/Observabilidad | C/QA | R/Observabilidad |
| Procesos agentizables | A/PO | R/Arquitectura | C/IA | C/QA | C/Observabilidad |

R: ejecuta. A: responde por el resultado. C: aporta criterio. Una persona asume varios roles en el MVP.

## Registro de riesgos

| Riesgo | Prob. | Impacto | Nivel | Responsable | Mitigación | Contingencia |
| --- | --- | --- | --- | --- | --- | --- |
| Angular 17 fuera de soporte | Alta | Alta | Crítico | Frontend | Ruta incremental | Congelar alcance y migrar |
| Equipo local apagado | Alta | Media | Alto | DevOps | Cola durable y alertas | Worker dedicado |
| Costos de IA | Baja | Media | Medio | Observabilidad | Ollama y presupuestos | Modelo menor |
| Latencia Ollama | Media | Alta | Alto | IA | Modelo acorde al hardware | Escalar o servicio remoto |
| Extracción deficiente | Media | Alta | Alto | IA | Dataset y OCR selectivo | Revisión humana |
| OCR incorrecto | Media | Alta | Alto | QA | Confianza por página | Proveedor documental |
| Alucinación | Media | Alta | Alto | IA | Rechazo y citas | Revisión humana |
| Fuga de datos | Baja | Crítico | Crítico | Seguridad | RLS, R2 privado, secretos | Revocar y responder incidente |
| Prompt injection | Alta | Alta | Crítico | Seguridad | Evidencia no confiable | Bloquear resultado |
| Almacenamiento creciente | Media | Media | Medio | Datos | Retención y ciclo de vida | Archivo frío o eliminación |
| Telemetría con PII | Media | Alta | Alto | Observabilidad | Lista permitida de campos | Purga y rotación |
| Base saturada | Baja | Alta | Alto | Datos | Pool, índices y agregados | Subir compute |
| Baja adopción | Media | Alta | Alto | PO | Caso prioritario y UX | Rediseñar flujo |
| ROI no demostrado | Media | Alta | Alto | Observabilidad | Línea base previa | Detener expansión |
| Falta de línea base | Alta | Alta | Crítico | PO | Dos semanas de medición | Estudio retrospectivo |
| Exceso de alcance | Alta | Alta | Crítico | PO | P0, P1 y P2 | Recortar piloto |
| Permisos erróneos | Media | Crítico | Crítico | Seguridad | Pruebas A/B | Desactivar acceso |
| Servicio externo caído | Media | Media | Medio | DevOps | Retries acotados | Operación manual |
| Pruebas insuficientes | Media | Alta | Alto | QA | Gates en CI | Bloquear despliegue |
| Sin revisión humana | Media | Alta | Alto | PO | Umbral de confianza | No automatizar decisión |

## Criterios de aceptación del piloto

- Usuario confirma cuenta e inicia sesión.
- Carga un PDF válido sin exponer credenciales.
- PDF inválido, grande, corrupto o protegido se rechaza.
- Trabajo continúa tras reiniciar el worker.
- Texto nativo y OCR preservan página.
- Pregunta existente devuelve evidencia y cita.
- Pregunta sin evidencia produce rechazo.
- Tokens, modelo, latencia, error y costo quedan registrados.
- Usuario B no accede a recursos de usuario A.
- CI pasa y despliega.
- Backup, rollback y runbooks han sido ensayados.
- Línea base y ROI aparecen en el informe de piloto.

