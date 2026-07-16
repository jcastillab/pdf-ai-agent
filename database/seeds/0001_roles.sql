insert into public.roles (code, name, description) values
  ('admin', 'Administrador', 'Gestiona usuarios, modelos y auditoría'),
  ('user', 'Usuario', 'Gestiona sus documentos y consultas'),
  ('reviewer', 'Revisor', 'Revisa extracciones de baja confianza')
on conflict (code) do update set name = excluded.name, description = excluded.description;

insert into public.permissions (code, description) values
  ('documents.read', 'Leer documentos propios'),
  ('documents.write', 'Crear y procesar documentos'),
  ('agent.query', 'Consultar el agente'),
  ('reviews.manage', 'Gestionar revisiones'),
  ('admin.manage', 'Gestionar configuración administrativa')
on conflict (code) do update set description = excluded.description;

insert into public.model_prices (
  provider, model, input_per_million_usd, output_per_million_usd, valid_from, source_url
) values ('ollama', 'local', 0, 0, current_date, 'local-compute')
on conflict (provider, model, valid_from) do nothing;

