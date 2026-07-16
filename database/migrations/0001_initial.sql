begin;

create extension if not exists pgcrypto;
create extension if not exists vector;

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  settings jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  organization_id uuid references public.organizations(id) on delete set null,
  display_name text,
  status text not null default 'active' check (status in ('active','blocked','invited')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.roles (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists public.permissions (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists public.role_permissions (
  role_id uuid not null references public.roles(id) on delete cascade,
  permission_id uuid not null references public.permissions(id) on delete cascade,
  primary key (role_id, permission_id)
);

create table if not exists public.user_roles (
  user_id uuid not null references auth.users(id) on delete cascade,
  role_id uuid not null references public.roles(id) on delete cascade,
  organization_id uuid references public.organizations(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, role_id)
);

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  organization_id uuid references public.organizations(id) on delete cascade,
  original_name varchar(255) not null,
  object_key varchar(1024) not null unique,
  mime_type varchar(100) not null default 'application/pdf',
  size_bytes bigint not null check (size_bytes > 0),
  sha256 varchar(64),
  page_count integer check (page_count is null or page_count > 0),
  status varchar(40) not null default 'awaiting_upload',
  confidence numeric(5,4) check (confidence between 0 and 1),
  summary text,
  metadata jsonb not null default '{}'::jsonb,
  processed_at timestamptz,
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists ix_documents_owner_created on public.documents(owner_id, created_at desc) where deleted_at is null;
create index if not exists ix_documents_org_status on public.documents(organization_id, status) where deleted_at is null;
create index if not exists ix_documents_sha256 on public.documents(sha256) where sha256 is not null;

create table if not exists public.document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  version integer not null,
  object_key text not null,
  sha256 varchar(64) not null,
  processing_config jsonb not null default '{}'::jsonb,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  unique(document_id, version)
);

create table if not exists public.document_pages (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  page_number integer not null check (page_number > 0),
  text text not null default '',
  extraction_method varchar(30) not null,
  confidence numeric(5,4) not null default 1 check (confidence between 0 and 1),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(document_id, page_number)
);

create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  document_version_id uuid references public.document_versions(id) on delete set null,
  page_number integer not null check (page_number > 0),
  section text,
  chunk_index integer not null check (chunk_index >= 0),
  text text not null,
  token_count integer not null check (token_count > 0),
  extraction_method varchar(30) not null,
  confidence numeric(5,4) not null default 1 check (confidence between 0 and 1),
  bounding_box jsonb,
  content_hash varchar(64) not null,
  embedding_model varchar(120) not null,
  embedding vector(768) not null,
  created_at timestamptz not null default now(),
  unique(document_id, chunk_index)
);
create index if not exists ix_document_chunks_document_page on public.document_chunks(document_id, page_number);
create index if not exists ix_document_chunks_embedding_hnsw on public.document_chunks using hnsw (embedding vector_cosine_ops);
create index if not exists ix_document_chunks_fts on public.document_chunks using gin (to_tsvector('spanish', text));

create table if not exists public.processing_jobs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references public.documents(id) on delete cascade,
  owner_id uuid not null references auth.users(id) on delete cascade,
  organization_id uuid references public.organizations(id) on delete cascade,
  task_type varchar(50) not null,
  status varchar(40) not null default 'queued',
  progress integer not null default 0 check (progress between 0 and 100),
  current_step varchar(80),
  payload jsonb not null default '{}'::jsonb,
  result jsonb not null default '{}'::jsonb,
  error_code varchar(80),
  error_message text,
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  cancel_requested boolean not null default false,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists ix_jobs_owner_created on public.processing_jobs(owner_id, created_at desc);
create index if not exists ix_jobs_status on public.processing_jobs(status, created_at);

create table if not exists public.processing_steps (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.processing_jobs(id) on delete cascade,
  step_name text not null,
  status text not null,
  attempt integer not null default 1,
  duration_ms integer,
  input_summary jsonb not null default '{}'::jsonb,
  output_summary jsonb not null default '{}'::jsonb,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists ix_processing_steps_job on public.processing_steps(job_id, created_at);

create table if not exists public.extraction_templates (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references public.organizations(id) on delete cascade,
  name text not null,
  document_type text not null,
  schema_json jsonb not null,
  version integer not null default 1,
  active boolean not null default true,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(organization_id, name, version)
);

create table if not exists public.extraction_results (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  template_id uuid references public.extraction_templates(id) on delete set null,
  agent_run_id uuid,
  status text not null,
  confidence numeric(5,4),
  result_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.extracted_fields (
  id uuid primary key default gen_random_uuid(),
  extraction_result_id uuid not null references public.extraction_results(id) on delete cascade,
  field_name text not null,
  value_json jsonb,
  page_number integer,
  confidence numeric(5,4),
  source_quote text,
  reviewed boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references public.documents(id) on delete cascade,
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  role text not null check (role in ('user','assistant','system')),
  content text not null,
  citations jsonb not null default '[]'::jsonb,
  token_count integer,
  created_at timestamptz not null default now()
);

create table if not exists public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references public.documents(id) on delete set null,
  job_id uuid references public.processing_jobs(id) on delete set null,
  owner_id uuid not null references auth.users(id) on delete cascade,
  run_type varchar(40) not null,
  status varchar(40) not null default 'queued',
  input_json jsonb not null default '{}'::jsonb,
  output_json jsonb not null default '{}'::jsonb,
  trace_id varchar(64),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.extraction_results
  add constraint extraction_results_agent_run_fk foreign key (agent_run_id) references public.agent_runs(id) on delete set null;

create table if not exists public.graph_checkpoints (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.processing_jobs(id) on delete cascade,
  node text not null,
  state jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists ix_graph_checkpoints_job on public.graph_checkpoints(job_id, created_at desc);

create table if not exists public.llm_calls (
  id uuid primary key default gen_random_uuid(),
  agent_run_id uuid references public.agent_runs(id) on delete set null,
  document_id uuid references public.documents(id) on delete set null,
  owner_id uuid references auth.users(id) on delete set null,
  provider varchar(40) not null,
  model varchar(120) not null,
  task_type varchar(50) not null,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  cached_tokens integer not null default 0,
  latency_ms integer not null default 0,
  time_to_first_token_ms integer,
  estimated_cost_usd numeric(14,8) not null default 0,
  success boolean not null default true,
  error_code varchar(80),
  trace_id varchar(64),
  prompt_version_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists ix_llm_calls_owner_created on public.llm_calls(owner_id, created_at desc);
create index if not exists ix_llm_calls_document on public.llm_calls(document_id);

create table if not exists public.tool_calls (
  id uuid primary key default gen_random_uuid(),
  agent_run_id uuid references public.agent_runs(id) on delete cascade,
  tool_name text not null,
  success boolean not null,
  latency_ms integer not null,
  input_summary jsonb not null default '{}'::jsonb,
  output_summary jsonb not null default '{}'::jsonb,
  error_code text,
  created_at timestamptz not null default now()
);

create table if not exists public.token_usage (
  id uuid primary key default gen_random_uuid(),
  llm_call_id uuid not null references public.llm_calls(id) on delete cascade,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  cached_tokens integer not null default 0,
  total_tokens integer generated always as (input_tokens + output_tokens + cached_tokens) stored,
  created_at timestamptz not null default now()
);

create table if not exists public.model_prices (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  model text not null,
  input_per_million_usd numeric(14,6) not null default 0,
  output_per_million_usd numeric(14,6) not null default 0,
  valid_from date not null,
  valid_to date,
  source_url text,
  created_at timestamptz not null default now(),
  unique(provider, model, valid_from)
);

create table if not exists public.feedback (
  id uuid primary key default gen_random_uuid(),
  agent_run_id uuid references public.agent_runs(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,
  rating integer check (rating between 1 and 5),
  correction text,
  created_at timestamptz not null default now()
);

create table if not exists public.human_reviews (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  extraction_result_id uuid references public.extraction_results(id) on delete cascade,
  assigned_to uuid references auth.users(id) on delete set null,
  status text not null default 'pending',
  reason text,
  corrections jsonb not null default '{}'::jsonb,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references auth.users(id) on delete set null,
  action varchar(100) not null,
  resource_type varchar(60) not null,
  resource_id uuid,
  trace_id varchar(64),
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists ix_audit_logs_created on public.audit_logs(created_at desc);
create index if not exists ix_audit_logs_resource on public.audit_logs(resource_type, resource_id);

create table if not exists public.security_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  event_type text not null,
  severity text not null,
  ip_hash text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.error_events (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references public.processing_jobs(id) on delete set null,
  trace_id text,
  error_code text not null,
  message text not null,
  stack_fingerprint text,
  retryable boolean not null default false,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.roi_baselines (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  process_name text not null,
  manual_minutes_per_document numeric(10,2) not null,
  hourly_cost_usd numeric(12,4) not null,
  error_rate numeric(5,4) not null default 0,
  valid_from date not null,
  created_at timestamptz not null default now()
);

create table if not exists public.roi_events (
  id uuid primary key default gen_random_uuid(),
  baseline_id uuid not null references public.roi_baselines(id) on delete cascade,
  document_id uuid references public.documents(id) on delete set null,
  automated_minutes numeric(10,2) not null,
  human_review_minutes numeric(10,2) not null default 0,
  estimated_savings_usd numeric(14,4) not null,
  processing_cost_usd numeric(14,4) not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists public.roi_monthly_summary (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  month date not null,
  documents_processed integer not null,
  hours_saved numeric(14,2) not null,
  gross_savings_usd numeric(14,2) not null,
  operating_cost_usd numeric(14,2) not null,
  net_benefit_usd numeric(14,2) generated always as (gross_savings_usd - operating_cost_usd) stored,
  created_at timestamptz not null default now(),
  unique(organization_id, month)
);

create table if not exists public.prompt_versions (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  version integer not null,
  template text not null,
  input_schema jsonb not null default '{}'::jsonb,
  output_schema jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  unique(name, version)
);
alter table public.llm_calls
  add constraint llm_calls_prompt_version_fk foreign key (prompt_version_id) references public.prompt_versions(id) on delete set null;

create table if not exists public.model_configurations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references public.organizations(id) on delete cascade,
  task_type text not null,
  provider text not null,
  model text not null,
  parameters jsonb not null default '{}'::jsonb,
  fallback_order jsonb not null default '[]'::jsonb,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(organization_id, task_type, provider, model)
);

create or replace function public.match_document_chunks(
  query_embedding vector(768),
  query_text text,
  match_document_id uuid,
  match_count integer default 6
)
returns table (
  id uuid,
  page_number integer,
  chunk_index integer,
  text text,
  similarity double precision
)
language sql stable security definer set search_path = public as $$
  select dc.id, dc.page_number, dc.chunk_index, dc.text,
         (0.8 * (1 - (dc.embedding <=> query_embedding))) +
         (0.2 * ts_rank_cd(to_tsvector('spanish', dc.text), plainto_tsquery('spanish', query_text)))
         as similarity
  from public.document_chunks dc
  where dc.document_id = match_document_id
  order by similarity desc
  limit least(greatest(match_count, 1), 20);
$$;

create or replace function public.document_context(
  target_document_id uuid,
  max_chars integer default 24000
)
returns text language sql stable security definer set search_path = public as $$
  select left(string_agg('[Página ' || page_number || '] ' || text, E'\n\n' order by chunk_index), max_chars)
  from public.document_chunks
  where document_id = target_document_id;
$$;

revoke all on function public.match_document_chunks(vector, text, uuid, integer) from public, anon, authenticated;
revoke all on function public.document_context(uuid, integer) from public, anon, authenticated;
grant execute on function public.match_document_chunks(vector, text, uuid, integer) to service_role;
grant execute on function public.document_context(uuid, integer) to service_role;

do $$
declare table_name text;
begin
  foreach table_name in array array[
    'organizations','profiles','roles','permissions','role_permissions','user_roles',
    'documents','document_versions','document_pages','document_chunks','processing_jobs',
    'processing_steps','extraction_templates','extraction_results','extracted_fields',
    'conversations','messages','agent_runs','graph_checkpoints','llm_calls','tool_calls',
    'token_usage','model_prices','feedback','human_reviews','audit_logs','security_events',
    'error_events','roi_baselines','roi_events','roi_monthly_summary','prompt_versions',
    'model_configurations'
  ] loop
    execute format('alter table public.%I enable row level security', table_name);
  end loop;
end $$;

create policy documents_owner_select on public.documents for select to authenticated
  using (owner_id = auth.uid() and deleted_at is null);
create policy documents_owner_delete on public.documents for delete to authenticated
  using (owner_id = auth.uid());
create policy jobs_owner_select on public.processing_jobs for select to authenticated
  using (owner_id = auth.uid());
create policy agent_runs_owner_select on public.agent_runs for select to authenticated
  using (owner_id = auth.uid());
create policy conversations_owner_all on public.conversations for all to authenticated
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy pages_owner_select on public.document_pages for select to authenticated
  using (exists (select 1 from public.documents d where d.id = document_id and d.owner_id = auth.uid()));
create policy chunks_owner_select on public.document_chunks for select to authenticated
  using (exists (select 1 from public.documents d where d.id = document_id and d.owner_id = auth.uid()));

do $$
declare table_name text;
begin
  foreach table_name in array array[
    'organizations','profiles','documents','document_pages','processing_jobs','extraction_templates',
    'extraction_results','conversations','agent_runs','human_reviews','model_configurations'
  ] loop
    execute format('drop trigger if exists trg_%I_updated_at on public.%I', table_name, table_name);
    execute format('create trigger trg_%I_updated_at before update on public.%I for each row execute function public.set_updated_at()', table_name, table_name);
  end loop;
end $$;

commit;
