# Prompts

Los prompts ejecutables viven en `apps/worker/worker/services/prompts.py` para el MVP. Antes del piloto, muévelos a `prompt_versions` y exige:

- Nombre, versión y propietario.
- Esquema de entrada y salida.
- Dataset de evaluación asociado.
- Métrica anterior y nueva.
- Aprobación antes de activar.
- Rollback a la versión previa.

El system prompt siempre declara el PDF como dato no confiable y prohíbe obedecer instrucciones incluidas en el documento.

