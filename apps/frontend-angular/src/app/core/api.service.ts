import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import {
  AgentAccepted,
  DocumentItem,
  DocumentList,
  Job,
  Page,
  TelemetryOverview,
  UploadTicket,
} from './api.models';
import { RuntimeConfigService } from './runtime-config.service';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl: string;

  constructor(private readonly http: HttpClient, config: RuntimeConfigService) {
    this.baseUrl = `${config.config.apiUrl.replace(/\/$/, '')}/api/v1`;
  }

  listDocuments(): Promise<DocumentList> {
    return firstValueFrom(this.http.get<DocumentList>(`${this.baseUrl}/documents`));
  }

  getDocument(id: string): Promise<DocumentItem> {
    return firstValueFrom(this.http.get<DocumentItem>(`${this.baseUrl}/documents/${id}`));
  }

  getPages(id: string): Promise<Page[]> {
    return firstValueFrom(this.http.get<Page[]>(`${this.baseUrl}/documents/${id}/pages`));
  }

  async upload(file: File): Promise<{ document: DocumentItem; job_id: string }> {
    const ticket = await firstValueFrom(
      this.http.post<UploadTicket>(`${this.baseUrl}/documents/upload`, {
        filename: file.name,
        content_type: file.type || 'application/pdf',
        size_bytes: file.size,
      }),
    );
    const upload = await fetch(ticket.upload_url, {
      method: ticket.method,
      headers: ticket.headers,
      body: file,
    });
    if (!upload.ok) throw new Error(`R2 rechazó la carga con HTTP ${upload.status}`);
    return firstValueFrom(
      this.http.post<{ document: DocumentItem; job_id: string }>(
        `${this.baseUrl}/documents/${ticket.document_id}/upload-complete`,
        {},
      ),
    );
  }

  deleteDocument(id: string): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`${this.baseUrl}/documents/${id}`));
  }

  ask(documentId: string, question: string): Promise<AgentAccepted> {
    return firstValueFrom(
      this.http.post<AgentAccepted>(`${this.baseUrl}/documents/${documentId}/ask`, { question }),
    );
  }

  getJob(id: string): Promise<Job> {
    return firstValueFrom(this.http.get<Job>(`${this.baseUrl}/jobs/${id}`));
  }

  overview(): Promise<TelemetryOverview> {
    return firstValueFrom(
      this.http.get<TelemetryOverview>(`${this.baseUrl}/telemetry/overview`),
    );
  }
}

