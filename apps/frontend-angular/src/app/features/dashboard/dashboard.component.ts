import { ChangeDetectionStrategy, Component, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { TelemetryOverview } from '../../core/api.models';
import { ApiService } from '../../core/api.service';

@Component({
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatProgressSpinnerModule, RouterLink],
  template: `
    <header class="page-header">
      <div><p class="eyebrow">OPERACIÓN</p><h1>Panel documental</h1><p>Estado del MVP y consumo de TU agente.</p></div>
      <a mat-flat-button color="primary" routerLink="/documents">Cargar un PDF</a>
    </header>
    @if (loading()) { <div class="loading"><mat-spinner diameter="42" /></div> }
    @else {
      @if (data(); as overview) {
      <section class="kpis">
        <mat-card><span>Documentos</span><strong>{{ overview.documents.total }}</strong><small>{{ overview.documents.completed }} procesados</small></mat-card>
        <mat-card><span>Trabajos</span><strong>{{ overview.jobs.total }}</strong><small>{{ overview.jobs.failed }} fallidos</small></mat-card>
        <mat-card><span>Tokens</span><strong>{{ overview.llm.input_tokens + overview.llm.output_tokens }}</strong><small>Entrada y salida</small></mat-card>
        <mat-card><span>Costo LLM</span><strong>US$ {{ overview.llm.estimated_cost_usd.toFixed(4) }}</strong><small>Ollama local registra US$ 0</small></mat-card>
      </section>
      <section class="status-grid">
        <mat-card class="architecture">
          <p class="eyebrow">RUTA ACTIVA</p><h2>Procesamiento local seguro</h2>
          <ol><li><span>1</span>Angular carga el archivo a R2.</li><li><span>2</span>Render crea el trabajo en Supabase.</li><li><span>3</span>TU worker local consume la cola.</li><li><span>4</span>Ollama genera respuestas con citas.</li></ol>
        </mat-card>
        <mat-card class="metric"><p>Latencia promedio LLM</p><strong>{{ overview.llm.average_latency_ms.toFixed(0) }} ms</strong><div class="bar"><i [style.width.%]="latencyBar(overview)"></i></div><small>SLO inicial: menor a 10 s</small></mat-card>
      </section>
      } @else { <p class="error">{{ error() }}</p> }
    }
  `,
  styles: `
    .page-header { display: flex; justify-content: space-between; align-items: end; gap: 1rem; margin-bottom: 2rem; } h1 { margin: 0; color: #14213d; font-size: clamp(2rem, 4vw, 3.4rem); letter-spacing: -.045em; } .page-header p:last-child { color: #64748b; }
    .eyebrow { color: #4f46e5; font-size: .76rem; font-weight: 800; letter-spacing: .12em; }
    .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
    .kpis mat-card { padding: 1.25rem; border-radius: 18px; } .kpis span, .kpis small { color: #64748b; } .kpis strong { display: block; margin: .45rem 0; color: #14213d; font-size: 2rem; letter-spacing: -.04em; }
    .status-grid { display: grid; grid-template-columns: 1.35fr .65fr; gap: 1rem; margin-top: 1rem; } .status-grid mat-card { padding: 1.5rem; border-radius: 18px; }
    .architecture h2 { margin: .3rem 0 1rem; } ol { display: grid; gap: .9rem; padding: 0; list-style: none; } li { display: flex; align-items: center; gap: .8rem; color: #334155; } li span { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 9px; background: #eef2ff; color: #4338ca; font-weight: 800; }
    .metric { display: flex; flex-direction: column; justify-content: center; background: #14213d; color: white; } .metric p, .metric small { color: #cbd5e1; } .metric strong { font-size: 2.2rem; } .bar { height: 8px; margin: 1rem 0; overflow: hidden; background: #334155; border-radius: 9px; } .bar i { display: block; height: 100%; background: #fb923c; }
    .loading { display: grid; place-items: center; min-height: 300px; } .error { color: #991b1b; }
    @media (max-width: 900px) { .kpis { grid-template-columns: repeat(2, 1fr); } .status-grid { grid-template-columns: 1fr; } } @media (max-width: 560px) { .page-header { align-items: start; flex-direction: column; } .kpis { grid-template-columns: 1fr; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardComponent implements OnInit {
  readonly data = signal<TelemetryOverview | null>(null);
  readonly loading = signal(true);
  readonly error = signal('');

  constructor(private readonly api: ApiService) {}

  async ngOnInit(): Promise<void> {
    try {
      this.data.set(await this.api.overview());
    } catch (error) {
      this.error.set(error instanceof Error ? error.message : 'No se cargó la telemetría');
    } finally {
      this.loading.set(false);
    }
  }

  latencyBar(overview: TelemetryOverview): number {
    return Math.min(100, (overview.llm.average_latency_ms / 10000) * 100);
  }
}
