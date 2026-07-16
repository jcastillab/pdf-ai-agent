export interface DocumentItem {
  id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  page_count: number | null;
  status: string;
  confidence: number | null;
  summary: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface DocumentList {
  items: DocumentItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface UploadTicket {
  document_id: string;
  upload_url: string;
  method: 'PUT';
  headers: Record<string, string>;
  expires_in: number;
}

export interface Job {
  id: string;
  document_id: string | null;
  task_type: string;
  status: string;
  progress: number;
  current_step: string | null;
  result: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
  attempts: number;
  cancel_requested: boolean;
  created_at: string;
  updated_at: string;
}

export interface Page {
  page_number: number;
  text: string;
  extraction_method: string;
  confidence: number;
}

export interface TelemetryOverview {
  documents: { total: number; completed: number };
  jobs: { total: number; failed: number };
  llm: {
    input_tokens: number;
    output_tokens: number;
    estimated_cost_usd: number;
    average_latency_ms: number;
  };
}

export interface AgentAccepted {
  run_id: string;
  job_id: string;
  status: string;
}

export interface Citation {
  page: number;
  quote: string;
}

