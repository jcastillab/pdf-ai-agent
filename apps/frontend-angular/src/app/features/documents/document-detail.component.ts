import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { Citation, DocumentItem, Page } from '../../core/api.models';
import { ApiService } from '../../core/api.service';

interface ChatMessage { role: 'user' | 'assistant'; content: string; citations?: Citation[]; }

@Component({
  standalone: true,
  imports: [DatePipe, ReactiveFormsModule, RouterLink, MatButtonModule, MatCardModule, MatExpansionModule, MatFormFieldModule, MatInputModule, MatProgressBarModule],
  template: `
    <a class="back" routerLink="/documents">← Volver a documentos</a>
    @if (document(); as doc) {
      <header class="page-header"><div><p class="eyebrow">DOCUMENTO</p><h1>{{ doc.original_name }}</h1><p>{{ doc.page_count ?? '...' }} páginas · {{ doc.created_at | date:'medium' }}</p></div><span class="status" [attr.data-status]="doc.status">{{ doc.status }}</span></header>
      @if (doc.status !== 'completed' && doc.status !== 'failed') { <mat-card class="processing"><div><strong>Procesamiento en curso</strong><span>{{ doc.status }}</span></div><mat-progress-bar mode="indeterminate" /></mat-card> }
      @if (doc.status === 'failed') { <mat-card class="failed">El trabajo falló. Revisa que el worker local, Ollama y Tesseract estén activos.</mat-card> }
      <section class="workspace">
        <div class="document-column">
          <mat-card class="summary"><p class="eyebrow">RESUMEN</p><h2>Contenido principal</h2><p>{{ doc.summary || 'El resumen aparecerá cuando termine el procesamiento.' }}</p></mat-card>
          @if (pages().length) { <h2 class="section-title">Texto extraído</h2><mat-accordion>@for (page of pages(); track page.page_number) { <mat-expansion-panel><mat-expansion-panel-header><mat-panel-title>Página {{ page.page_number }}</mat-panel-title><mat-panel-description>{{ page.extraction_method }} · {{ (page.confidence * 100).toFixed(0) }}%</mat-panel-description></mat-expansion-panel-header><p class="page-text">{{ page.text }}</p></mat-expansion-panel> }</mat-accordion> }
        </div>
        <mat-card class="chat">
          <div class="chat-header"><p class="eyebrow">CONSULTA CON CITAS</p><h2>Pregunta al documento</h2></div>
          <div class="messages" aria-live="polite">
            @if (!messages().length) { <div class="chat-empty"><strong>Empieza con una pregunta concreta.</strong><span>Ejemplo: ¿Cuáles son las obligaciones y fechas clave?</span></div> }
            @for (message of messages(); track $index) { <article [class.user]="message.role === 'user'"><span>{{ message.role === 'user' ? 'TÚ' : 'IA' }}</span><p>{{ message.content }}</p>@if (message.citations?.length) { <div class="citations">@for (citation of message.citations; track $index) { <button type="button" (click)="openPage(citation.page)">Página {{ citation.page }}</button> }</div> }</article> }
            @if (asking()) { <article><span>IA</span><p>Buscando evidencia y generando la respuesta...</p><mat-progress-bar mode="indeterminate" /></article> }
          </div>
          <form [formGroup]="questionForm" (ngSubmit)="ask()"><mat-form-field appearance="outline"><mat-label>Escribe TU pregunta</mat-label><textarea matInput rows="3" formControlName="question"></textarea></mat-form-field><button mat-flat-button color="primary" type="submit" [disabled]="questionForm.invalid || asking() || doc.status !== 'completed'">Preguntar</button></form>
        </mat-card>
      </section>
    } @else { <p>{{ error() || 'Cargando documento...' }}</p> }
  `,
  styles: `
    .back { display: inline-block; margin-bottom: 1.2rem; color: #4f46e5; text-decoration: none; font-weight: 700; } .page-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.4rem; } h1 { margin: 0; color: #14213d; font-size: clamp(2rem, 4vw, 3rem); letter-spacing: -.045em; overflow-wrap: anywhere; } .page-header p:last-child { color: #64748b; } .eyebrow { color: #4f46e5; font-size: .74rem; font-weight: 800; letter-spacing: .12em; }
    .status { padding: .5rem .8rem; border-radius: 999px; background: #e0e7ff; color: #3730a3; font-weight: 750; } .status[data-status='completed'] { background: #dcfce7; color: #166534; } .status[data-status='failed'] { background: #fee2e2; color: #991b1b; }
    .processing { display: grid; gap: .8rem; padding: 1rem; margin-bottom: 1rem; } .processing div { display: flex; justify-content: space-between; } .failed { padding: 1rem; margin-bottom: 1rem; color: #991b1b; background: #fef2f2; }
    .workspace { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(330px, .85fr); gap: 1rem; align-items: start; } .summary, .chat { padding: 1.4rem; border-radius: 18px; } .summary h2, .chat h2 { margin: .25rem 0 1rem; } .summary > p:last-child { white-space: pre-line; line-height: 1.7; color: #334155; }
    .section-title { margin: 2rem 0 1rem; } .page-text { white-space: pre-line; line-height: 1.65; color: #334155; } mat-expansion-panel { margin-bottom: .6rem; }
    .chat { position: sticky; top: 86px; display: grid; grid-template-rows: auto minmax(320px, 52vh) auto; } .messages { overflow: auto; padding: .8rem 0; border-block: 1px solid #e2e8f0; } .chat-empty { display: grid; place-items: center; min-height: 250px; text-align: center; color: #64748b; } .chat-empty strong { color: #334155; }
    article { margin: .8rem 0; padding: .9rem; background: #f8fafc; border-radius: 14px 14px 14px 4px; } article.user { margin-left: 2rem; background: #eef2ff; border-radius: 14px 14px 4px 14px; } article > span { color: #4f46e5; font-size: .68rem; font-weight: 900; } article p { margin: .35rem 0; white-space: pre-line; line-height: 1.55; } .citations { display: flex; flex-wrap: wrap; gap: .4rem; } .citations button { border: 0; padding: .35rem .55rem; color: #1d4ed8; background: #dbeafe; border-radius: 999px; cursor: pointer; }
    form { display: grid; grid-template-columns: 1fr auto; align-items: end; gap: .7rem; padding-top: 1rem; } mat-form-field { width: 100%; }
    @media (max-width: 900px) { .workspace { grid-template-columns: 1fr; } .chat { position: static; } } @media (max-width: 560px) { .page-header { align-items: start; flex-direction: column; } form { grid-template-columns: 1fr; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DocumentDetailComponent implements OnInit, OnDestroy {
  readonly document = signal<DocumentItem | null>(null);
  readonly pages = signal<Page[]>([]);
  readonly messages = signal<ChatMessage[]>([]);
  readonly asking = signal(false);
  readonly error = signal('');
  readonly questionForm = this.formBuilder.nonNullable.group({ question: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(2000)]] });
  private readonly id = this.route.snapshot.paramMap.get('id')!;
  private refreshTimer?: ReturnType<typeof setTimeout>;

  constructor(private readonly route: ActivatedRoute, private readonly router: Router, private readonly formBuilder: FormBuilder, private readonly api: ApiService) {}
  ngOnInit(): void { void this.load(); }
  ngOnDestroy(): void { if (this.refreshTimer) clearTimeout(this.refreshTimer); }

  private async load(): Promise<void> {
    try {
      const doc = await this.api.getDocument(this.id); this.document.set(doc);
      if (doc.status === 'completed') this.pages.set(await this.api.getPages(this.id));
      else if (doc.status !== 'failed') this.refreshTimer = setTimeout(() => void this.load(), 2500);
    } catch (error) { this.error.set(error instanceof Error ? error.message : 'No se cargó el documento'); }
  }

  async ask(): Promise<void> {
    if (this.questionForm.invalid) return;
    const question = this.questionForm.controls.question.value.trim();
    this.messages.update((items) => [...items, { role: 'user', content: question }]); this.questionForm.reset(); this.asking.set(true);
    try {
      const accepted = await this.api.ask(this.id, question);
      const result = await this.waitForJob(accepted.job_id);
      this.messages.update((items) => [...items, { role: 'assistant', content: String(result['answer'] ?? 'Sin respuesta'), citations: (result['citations'] ?? []) as Citation[] }]);
    } catch (error) { this.messages.update((items) => [...items, { role: 'assistant', content: error instanceof Error ? error.message : 'La consulta falló' }]); }
    finally { this.asking.set(false); }
  }

  private async waitForJob(jobId: string): Promise<Record<string, unknown>> {
    for (let attempt = 0; attempt < 180; attempt += 1) {
      const job = await this.api.getJob(jobId);
      if (job.status === 'completed') return job.result;
      if (job.status === 'failed' || job.status === 'cancelled') throw new Error(job.error_message || `El trabajo terminó como ${job.status}`);
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    throw new Error('La consulta superó el tiempo de espera');
  }

  openPage(page: number): void { const panel = document.querySelectorAll('mat-expansion-panel')[page - 1]; panel?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
}

