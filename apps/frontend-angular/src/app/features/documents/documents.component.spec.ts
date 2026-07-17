import { fakeAsync, flushMicrotasks, tick } from '@angular/core/testing';

import { DocumentItem, DocumentList } from '../../core/api.models';
import { ApiService } from '../../core/api.service';
import { RuntimeConfigService } from '../../core/runtime-config.service';
import { DocumentsComponent } from './documents.component';

describe('DocumentsComponent', () => {
  const document = (status: string): DocumentItem => ({
    id: 'document-1',
    original_name: 'document.pdf',
    mime_type: 'application/pdf',
    size_bytes: 1024,
    page_count: status === 'completed' ? 1 : null,
    status,
    confidence: null,
    summary: null,
    created_at: '2026-07-16T00:00:00Z',
    processed_at: status === 'completed' ? '2026-07-16T00:01:00Z' : null,
  });

  const list = (status: string): DocumentList => ({
    items: [document(status)],
    total: 1,
    limit: 20,
    offset: 0,
  });

  const createComponent = (responses: DocumentList[]) => {
    const api = jasmine.createSpyObj<ApiService>('ApiService', ['listDocuments']);
    api.listDocuments.and.returnValues(...responses.map((response) => Promise.resolve(response)));
    const config = { config: { maxPdfSizeMb: 25 } } as RuntimeConfigService;
    return { component: new DocumentsComponent(api, config), api };
  };

  it('refreshes pending documents until they reach a terminal status', fakeAsync(() => {
    const { component, api } = createComponent([list('queued'), list('completed')]);

    component.ngOnInit();
    flushMicrotasks();
    expect(api.listDocuments).toHaveBeenCalledTimes(1);
    expect(component.documents()[0].status).toBe('queued');

    tick(2500);
    flushMicrotasks();
    expect(api.listDocuments).toHaveBeenCalledTimes(2);
    expect(component.documents()[0].status).toBe('completed');

    tick(3000);
    expect(api.listDocuments).toHaveBeenCalledTimes(2);
    component.ngOnDestroy();
  }));

  it('cancels the pending refresh when the component is destroyed', fakeAsync(() => {
    const { component, api } = createComponent([list('indexing')]);

    component.ngOnInit();
    flushMicrotasks();
    component.ngOnDestroy();
    tick(2500);

    expect(api.listDocuments).toHaveBeenCalledTimes(1);
  }));
});
