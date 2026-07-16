import { ChangeDetectionStrategy, Component, OnInit, signal } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';

import { DocumentItem } from '../../core/api.models';
import { ApiService } from '../../core/api.service';
import { RuntimeConfigService } from '../../core/runtime-config.service';

@Component({
  standalone: true,
  imports: [DatePipe, DecimalPipe, MatButtonModule, MatCardModule, MatProgressBarModule, MatTableModule, RouterLink],
  template: `
    <header class="page-header"><div><p class="eyebrow">BIBLIOTECA</p><h1>Documentos</h1><p>Carga, procesa y consulta tus PDF.</p></div></header>
    <mat-card class="dropzone" [class.dragging]="dragging()" (dragover)="drag($event, true)" (dragleave)="drag($event, false)" (drop)="drop($event)">
      <input #fileInput type="file" accept="application/pdf,.pdf" hidden (change)="selectFile($event)" />
      <div class="upload-mark">PDF</div><h2>Arrastra TU archivo aquí</h2><p>PDF de hasta {{ maxSizeMb }} MB. Se procesa en segundo plano.</p>
      <button mat-flat-button color="primary" type="button" (click)="fileInput.click()" [disabled]="uploading()">Seleccionar archivo</button>
      @if (uploading()) { <mat-progress-bar mode="indeterminate" /><p>{{ uploadMessage() }}</p> }
      @if (error()) { <p class="error">{{ error() }}</p> }
    </mat-card>
    <section class="list-header"><h2>Historial</h2><button mat-button type="button" (click)="load()">Actualizar</button></section>
    <div class="table-wrap">
      <table mat-table [dataSource]="documents()">
        <ng-container matColumnDef="name"><th mat-header-cell *matHeaderCellDef>Documento</th><td mat-cell *matCellDef="let doc"><a [routerLink]="['/documents', doc.id]">{{ doc.original_name }}</a><small>{{ doc.size_bytes / 1048576 | number:'1.1-1' }} MB</small></td></ng-container>
        <ng-container matColumnDef="status"><th mat-header-cell *matHeaderCellDef>Estado</th><td mat-cell *matCellDef="let doc"><span class="status" [attr.data-status]="doc.status">{{ statusLabel(doc.status) }}</span></td></ng-container>
        <ng-container matColumnDef="pages"><th mat-header-cell *matHeaderCellDef>Páginas</th><td mat-cell *matCellDef="let doc">{{ doc.page_count ?? 'Pendiente' }}</td></ng-container>
        <ng-container matColumnDef="date"><th mat-header-cell *matHeaderCellDef>Carga</th><td mat-cell *matCellDef="let doc">{{ doc.created_at | date:'medium' }}</td></ng-container>
        <ng-container matColumnDef="action"><th mat-header-cell *matHeaderCellDef></th><td mat-cell *matCellDef="let doc"><a mat-stroked-button [routerLink]="['/documents', doc.id]">Abrir</a></td></ng-container>
        <tr mat-header-row *matHeaderRowDef="columns"></tr><tr mat-row *matRowDef="let row; columns: columns"></tr>
      </table>
      @if (!loading() && documents().length === 0) { <div class="empty">Aún no has cargado documentos.</div> }
    </div>
  `,
  styles: `
    .page-header h1 { margin: 0; color: #14213d; font-size: 3rem; letter-spacing: -.045em; } .page-header p:last-child { color: #64748b; } .eyebrow { color: #4f46e5; font-size: .76rem; font-weight: 800; letter-spacing: .12em; }
    .dropzone { display: grid; place-items: center; padding: 2.5rem; text-align: center; border: 2px dashed #cbd5e1; border-radius: 22px; box-shadow: none; transition: .2s; } .dropzone.dragging { border-color: #4f46e5; background: #eef2ff; } .dropzone h2 { margin: .8rem 0 .2rem; } .dropzone p { color: #64748b; } .dropzone mat-progress-bar { width: min(460px, 100%); margin-top: 1.3rem; }
    .upload-mark { display: grid; place-items: center; width: 56px; height: 56px; border-radius: 16px; background: #ffedd5; color: #c2410c; font-weight: 900; }
    .list-header { display: flex; justify-content: space-between; align-items: center; margin-top: 2rem; } .table-wrap { overflow: auto; background: white; border: 1px solid #e2e8f0; border-radius: 18px; } table { width: 100%; } td a:not([mat-stroked-button]) { display: block; color: #1e3a8a; font-weight: 700; text-decoration: none; } td small { display: block; color: #94a3b8; margin-top: .2rem; }
    .status { display: inline-block; padding: .38rem .65rem; border-radius: 999px; background: #f1f5f9; color: #475569; font-size: .78rem; font-weight: 750; } .status[data-status='completed'] { background: #dcfce7; color: #166534; } .status[data-status='failed'] { background: #fee2e2; color: #991b1b; } .status[data-status='queued'], .status[data-status='extracting'], .status[data-status='indexing'] { background: #e0e7ff; color: #3730a3; }
    .empty { padding: 3rem; text-align: center; color: #64748b; } .error { color: #991b1b !important; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DocumentsComponent implements OnInit {
  readonly columns = ['name', 'status', 'pages', 'date', 'action'];
  readonly documents = signal<DocumentItem[]>([]);
  readonly loading = signal(true);
  readonly uploading = signal(false);
  readonly dragging = signal(false);
  readonly uploadMessage = signal('');
  readonly error = signal('');
  readonly maxSizeMb: number;

  constructor(private readonly api: ApiService, config: RuntimeConfigService) {
    this.maxSizeMb = config.config.maxPdfSizeMb;
  }

  ngOnInit(): void { void this.load(); }

  async load(): Promise<void> {
    this.loading.set(true);
    try { this.documents.set((await this.api.listDocuments()).items); }
    catch (error) { this.error.set(error instanceof Error ? error.message : 'No se cargaron los documentos'); }
    finally { this.loading.set(false); }
  }

  drag(event: DragEvent, active: boolean): void { event.preventDefault(); this.dragging.set(active); }
  drop(event: DragEvent): void { event.preventDefault(); this.dragging.set(false); const file = event.dataTransfer?.files.item(0); if (file) void this.upload(file); }
  selectFile(event: Event): void { const file = (event.target as HTMLInputElement).files?.item(0); if (file) void this.upload(file); }

  async upload(file: File): Promise<void> {
    this.error.set('');
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) { this.error.set('Selecciona un archivo PDF.'); return; }
    if (file.size > this.maxSizeMb * 1024 * 1024) { this.error.set(`El archivo supera ${this.maxSizeMb} MB.`); return; }
    this.uploading.set(true); this.uploadMessage.set('Cargando a almacenamiento seguro...');
    try { await this.api.upload(file); this.uploadMessage.set('Trabajo creado. TU worker local continuará el proceso.'); await this.load(); }
    catch (error) { this.error.set(error instanceof Error ? error.message : 'La carga falló'); }
    finally { this.uploading.set(false); }
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = { awaiting_upload: 'Esperando carga', queued: 'En cola', validating: 'Validando', extracting: 'Extrayendo', chunking: 'Segmentando', indexing: 'Indexando', classifying: 'Resumiendo', completed: 'Completado', failed: 'Fallido' };
    return labels[status] ?? status;
  }
}

