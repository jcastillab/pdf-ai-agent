begin;

create extension if not exists pgmq;
select pgmq.create('document_jobs')
where not exists (select 1 from pgmq.list_queues() where queue_name = 'document_jobs');
select pgmq.create('document_jobs_dlq')
where not exists (select 1 from pgmq.list_queues() where queue_name = 'document_jobs_dlq');

commit;

-- En Supabase Dashboard abre Integrations > Queues, habilita "Expose Queues via PostgREST"
-- y concede Select, Insert, Update y Delete únicamente al rol service_role.

