# Metodología de ROI

Responsable funcional: Juan Esteban Castilla Baquero.

## Línea base

Mide durante dos semanas, antes de automatizar:

- Documentos por mes.
- Minutos manuales por documento.
- Costo laboral por hora con cargas.
- Porcentaje de documentos con corrección.
- Costo medio de cada error.
- Tiempo de espera hasta respuesta.

Guarda una línea por proceso en `roi_baselines`.

## Cálculos

Para cada documento:

\[
Horas\ ahorradas = \frac{Minutos\ manuales - Minutos\ automatizados - Minutos\ de\ revisión}{60}
\]

\[
Ahorro\ laboral = Horas\ ahorradas \times Costo\ laboral\ por\ hora
\]

\[
Beneficio\ neto = Ahorro\ laboral + Errores\ evitados - Costo\ operativo
\]

\[
ROI\ \% = \frac{Beneficio\ neto - Inversión\ inicial}{Inversión\ inicial} \times 100
\]

\[
Payback\ en\ meses = \frac{Inversión\ inicial}{Beneficio\ neto\ mensual}
\]

## Ejemplo

Supuestos:

- 1.000 PDF al mes.
- 12 minutos manuales por PDF.
- 2 minutos entre automatización y revisión.
- Costo laboral de US$8 por hora.
- Infraestructura de US$40 al mes.
- Implementación inicial de US$3.000.

Resultado:

- Horas ahorradas: `1.000 × 10 / 60 = 166,67`.
- Ahorro laboral: `166,67 × 8 = US$1.333,36`.
- Beneficio neto mensual: `1.333,36 - 40 = US$1.293,36`.
- Payback: `3.000 / 1.293,36 = 2,32 meses`.

Este ejemplo no representa una promesa. Reemplaza cada valor con TU línea base.

## Instrumentación

| Evento | Fuente | Campos mínimos |
| --- | --- | --- |
| Documento recibido | API | proceso, usuario seudonimizado, fecha |
| Trabajo completado | Worker | duración, páginas, OCR, resultado |
| Llamada LLM | Worker | modelo, tokens, latencia, costo |
| Revisión humana | Frontend | minutos, correcciones, confianza |
| Error evitado | Revisor | tipo, costo estimado, evidencia |
| Feedback | Frontend | calificación, corrección |

## Indicadores del piloto

- Adopción semanal.
- Documentos por usuario.
- Tasa de finalización.
- Minutos ahorrados por documento.
- Porcentaje enviado a revisión.
- Porcentaje corregido.
- Costo por documento.
- Ahorro mensual.
- ROI acumulado.
- Payback proyectado.

No uses tokens como medida de valor. Relaciona el consumo con documentos procesados, calidad y tiempo ahorrado.

