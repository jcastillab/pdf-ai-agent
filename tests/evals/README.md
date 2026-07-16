# Evals

Amplía `packages/evaluation/cases.jsonl` con ejemplos aprobados por negocio.

Métricas mínimas:

- Exact match y F1 para preguntas.
- Precisión y recall por campo.
- Página correcta y cita contenida en evidencia.
- Tasa de rechazo en preguntas sin respuesta.
- JSON válido.
- Tasa de instrucciones maliciosas ignoradas.
- Corrección humana.

Bloquea cambios de modelo o prompt cuando una métrica crítica cae por debajo del umbral acordado.

