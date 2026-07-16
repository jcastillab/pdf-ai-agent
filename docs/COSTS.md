# Costos estimados

Consulta: 14 de julio de 2026. Conversión de planeación: `1 USD = 4.000 COP`. Esta tasa es un supuesto presupuestal, no una cotización cambiaria.

## Tarifas de referencia

| Servicio | Referencia usada |
| --- | --- |
| Render Web Service | Free US$0, Starter US$7, Standard US$25 al mes |
| Supabase | Free US$0, Pro desde US$25 al mes |
| Cloudflare R2 Standard | US$0,015 por GB mes, 10 GB mes incluidos |
| R2 operaciones A | US$4,50 por millón, primer millón incluido |
| R2 operaciones B | US$0,36 por millón, primeros 10 millones incluidos |
| R2 egress | Sin costo directo desde R2 |
| Cloudflare Pages | Nivel gratuito suficiente para el MVP |
| Sentry | Developer US$0, Team US$26 al mes anualizado |
| Ollama | Sin tarifa por token, consume TU electricidad y hardware |

Fuentes oficiales:

- [Render Pricing](https://render.com/pricing)
- [Supabase Pricing](https://supabase.com/pricing)
- [Cloudflare R2 Pricing](https://developers.cloudflare.com/r2/pricing/)
- [Sentry Pricing](https://sentry.io/pricing/)

## Escenario 1, desarrollo personal

| Concepto | USD mes | COP mes |
| --- | ---: | ---: |
| Cloudflare Pages | 0 | 0 |
| Render Free | 0 | 0 |
| Supabase Free | 0 | 0 |
| R2, dentro del nivel incluido | 0 | 0 |
| Sentry Developer | 0 | 0 |
| Ollama local | 0 en servicios | 0 en servicios |
| Total servicios | **0** | **0** |

Restricciones: cold start de Render, límites de proyectos, backups y capacidad. Este escenario sirve para desarrollo y demostración.

## Escenario 2, piloto empresarial

| Concepto | USD mes | COP mes |
| --- | ---: | ---: |
| Cloudflare Pages | 0 | 0 |
| Render Starter | 7 | 28.000 |
| Supabase Pro | 25 | 100.000 |
| R2, 50 GB medios | 0,60 después de 10 GB incluidos | 2.400 |
| Sentry Developer | 0 | 0 |
| Dominio, prorrateo estimado | 1,50 | 6.000 |
| Reserva energía y red del worker | 10 | 40.000 |
| Total estimado | **44,10** | **176.400** |

El cálculo de R2 asume 40 GB facturables a US$0,015. Operaciones permanecen dentro de los límites incluidos.

## Escenario 3, producción inicial

| Concepto | USD mes | COP mes |
| --- | ---: | ---: |
| Cloudflare Pages | 0 a 5 | 0 a 20.000 |
| Render Standard | 25 | 100.000 |
| Supabase Pro | 25 | 100.000 |
| R2, 500 GB medios | 7,35 después del nivel incluido | 29.400 |
| Sentry Team | 26 | 104.000 |
| Dominio y correo transaccional | 5 | 20.000 |
| Worker dedicado local | 30 de operación estimada | 120.000 |
| Total estimado | **118,35 a 123,35** | **473.400 a 493.400** |

Producción empresarial exige evaluar otro worker, disponibilidad, soporte, políticas de datos y reemplazo del cómputo local cuando el SLO lo requiera.

## Fórmula R2

\[
Costo\ R2 = GB\ mes\ facturables \times 0,015 + Millones\ A \times 4,50 + Millones\ B \times 0,36
\]

Resta el nivel mensual incluido antes de aplicar la fórmula. Cloudflare redondea al siguiente bloque de facturación.

## Variables que dominan el costo

- Volumen medio almacenado, no el total cargado durante el mes.
- Retención y versiones del PDF.
- Cantidad de lecturas del worker y descargas de usuarios.
- Plan mínimo de Render sin suspensión.
- Supabase Pro para backups y operación del piloto.
- Electricidad, mantenimiento y disponibilidad del equipo local.

Actualiza esta tabla antes de aprobar un piloto. Registra fecha, fuente y tasa COP usada.

