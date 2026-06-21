-- Centralized Vulcan root WhatsApp channel.
-- The root phone number and secrets stay in environment/secret storage.
-- Tenant tables below store only recipient rules, templates, queue state,
-- delivery history and audit-friendly metadata.

alter type public.vulcan_notification_status add value if not exists 'pending';
alter type public.vulcan_notification_status add value if not exists 'sending';
alter type public.vulcan_notification_status add value if not exists 'delivered';
alter type public.vulcan_notification_status add value if not exists 'cancelled';
alter type public.vulcan_notification_status add value if not exists 'skipped';
alter type public.vulcan_notification_status add value if not exists 'retrying';

create table if not exists public.root_whatsapp_templates (
  id text primary key,
  tenant_id uuid references public.tenants (id) on delete cascade,
  template_type text not null,
  title text not null,
  body text not null,
  variables jsonb not null default '[]'::jsonb,
  language text not null default 'pt-BR',
  version integer not null default 1 check (version > 0),
  active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.notification_schedules (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  created_by_membership_id uuid references public.memberships (id) on delete set null,
  name text not null,
  channel public.vulcan_notification_channel not null default 'whatsapp',
  notification_type text not null,
  recurrence text not null check (recurrence in ('imediato', 'diario', 'semanal', 'mensal', 'personalizado')),
  timezone text not null default 'America/Sao_Paulo',
  days_of_week jsonb not null default '[]'::jsonb,
  times jsonb not null default '[]'::jsonb,
  recipient_rules jsonb not null default '{}'::jsonb,
  template_id text references public.root_whatsapp_templates (id) on delete set null,
  enabled boolean not null default true,
  next_run_at timestamptz,
  last_run_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.whatsapp_delivery_queue (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  notification_id uuid references public.notifications (id) on delete set null,
  recipient_membership_id uuid references public.memberships (id) on delete set null,
  schedule_id uuid references public.notification_schedules (id) on delete set null,
  template_id text references public.root_whatsapp_templates (id) on delete set null,
  notification_type text not null,
  root_channel_name text,
  root_channel_number text,
  destination text not null,
  title text not null,
  message text not null,
  priority text not null default 'medio' check (priority in ('informativo', 'baixo', 'medio', 'alto', 'critico')),
  status text not null default 'pending' check (
    status in (
      'pending', 'queued', 'sending', 'sent', 'delivered', 'failed',
      'mocked', 'missing_credentials', 'missing_destination',
      'retrying', 'cancelled', 'skipped', 'unknown_provider', 'disabled'
    )
  ),
  provider text,
  provider_message_id text,
  scheduled_for timestamptz,
  next_attempt_at timestamptz,
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 3 check (max_attempts > 0),
  last_error text,
  payload jsonb not null default '{}'::jsonb,
  sent_at timestamptz,
  delivered_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.whatsapp_delivery_logs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  queue_id uuid references public.whatsapp_delivery_queue (id) on delete cascade,
  notification_id uuid references public.notifications (id) on delete set null,
  recipient_membership_id uuid references public.memberships (id) on delete set null,
  destination text,
  status text not null,
  provider text,
  provider_result text,
  error text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_root_whatsapp_templates_tenant_type
  on public.root_whatsapp_templates (tenant_id, template_type, active);

create index if not exists idx_notification_schedules_tenant_channel
  on public.notification_schedules (tenant_id, channel, enabled, next_run_at);

create index if not exists idx_whatsapp_delivery_queue_tenant_status
  on public.whatsapp_delivery_queue (tenant_id, status, scheduled_for, next_attempt_at);

create index if not exists idx_whatsapp_delivery_queue_recipient
  on public.whatsapp_delivery_queue (tenant_id, recipient_membership_id, created_at desc);

create index if not exists idx_whatsapp_delivery_logs_tenant_created
  on public.whatsapp_delivery_logs (tenant_id, created_at desc);

alter table public.root_whatsapp_templates enable row level security;
alter table public.notification_schedules enable row level security;
alter table public.whatsapp_delivery_queue enable row level security;
alter table public.whatsapp_delivery_logs enable row level security;

drop policy if exists root_whatsapp_templates_read_member on public.root_whatsapp_templates;
create policy root_whatsapp_templates_read_member on public.root_whatsapp_templates
for select using (tenant_id is null or public.vulcan_is_tenant_member(tenant_id));

drop policy if exists notification_schedules_read_tenant_scope on public.notification_schedules;
create policy notification_schedules_read_tenant_scope on public.notification_schedules
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or created_by_membership_id = public.vulcan_current_membership_id(tenant_id)
);

drop policy if exists whatsapp_delivery_queue_read_hierarchy on public.whatsapp_delivery_queue;
create policy whatsapp_delivery_queue_read_hierarchy on public.whatsapp_delivery_queue
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or recipient_membership_id = public.vulcan_current_membership_id(tenant_id)
  or public.vulcan_can_view_membership(tenant_id, recipient_membership_id)
);

drop policy if exists whatsapp_delivery_logs_read_hierarchy on public.whatsapp_delivery_logs;
create policy whatsapp_delivery_logs_read_hierarchy on public.whatsapp_delivery_logs
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or recipient_membership_id = public.vulcan_current_membership_id(tenant_id)
  or public.vulcan_can_view_membership(tenant_id, recipient_membership_id)
);

drop policy if exists service_role_all_root_whatsapp_templates on public.root_whatsapp_templates;
create policy service_role_all_root_whatsapp_templates
on public.root_whatsapp_templates for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists service_role_all_notification_schedules on public.notification_schedules;
create policy service_role_all_notification_schedules
on public.notification_schedules for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists service_role_all_whatsapp_delivery_queue on public.whatsapp_delivery_queue;
create policy service_role_all_whatsapp_delivery_queue
on public.whatsapp_delivery_queue for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists service_role_all_whatsapp_delivery_logs on public.whatsapp_delivery_logs;
create policy service_role_all_whatsapp_delivery_logs
on public.whatsapp_delivery_logs for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

insert into public.root_whatsapp_templates (
  id, tenant_id, template_type, title, body, variables, language, version, active, metadata
)
values
  (
    'root-whatsapp-metrica',
    null,
    'metrica',
    'Métrica operacional Vulcan',
    'Vulcan: {{escopo}} registrou {{metrica}} em {{periodo}}. Valor: {{valor}}. Acesse {{link_dashboard}}',
    '["escopo", "metrica", "periodo", "valor", "link_dashboard"]'::jsonb,
    'pt-BR',
    1,
    true,
    '{"system": true}'::jsonb
  ),
  (
    'root-whatsapp-alerta',
    null,
    'alerta',
    'Alerta operacional Vulcan',
    'Vulcan Alert: {{titulo}}. Impacto: {{impacto}}. Recomendação: {{recomendacao}}',
    '["titulo", "impacto", "recomendacao"]'::jsonb,
    'pt-BR',
    1,
    true,
    '{"system": true}'::jsonb
  ),
  (
    'root-whatsapp-insight',
    null,
    'insight',
    'Insight Vulcan',
    'Vulcan Insight: {{resumo}}. Oportunidade estimada: {{economia_estimada}}. Próximo passo: {{recomendacao}}',
    '["resumo", "economia_estimada", "recomendacao"]'::jsonb,
    'pt-BR',
    1,
    true,
    '{"system": true}'::jsonb
  ),
  (
    'root-whatsapp-relatorio-diario',
    null,
    'relatorio_diario',
    'Resumo diário Vulcan',
    'Resumo diário: {{escopo}} teve {{tempo_ativo}} ativos, {{tempo_ocioso}} ociosos e {{gargalos}} gargalos. Ver dashboard: {{link_dashboard}}',
    '["escopo", "tempo_ativo", "tempo_ocioso", "gargalos", "link_dashboard"]'::jsonb,
    'pt-BR',
    1,
    true,
    '{"system": true}'::jsonb
  ),
  (
    'root-whatsapp-relatorio-semanal',
    null,
    'relatorio_semanal',
    'Resumo semanal Vulcan',
    'Resumo semanal: {{escopo}} gerou {{insights}} insights, {{automacoes}} oportunidades e {{economia_estimada}} de economia potencial.',
    '["escopo", "insights", "automacoes", "economia_estimada"]'::jsonb,
    'pt-BR',
    1,
    true,
    '{"system": true}'::jsonb
  ),
  (
    'root-whatsapp-critico',
    null,
    'critico',
    'Crítico Vulcan',
    'Alerta crítico: {{evento}}. Escopo: {{escopo}}. Ação imediata: {{acao}}',
    '["evento", "escopo", "acao"]'::jsonb,
    'pt-BR',
    1,
    true,
    '{"system": true}'::jsonb
  )
on conflict (id) do update
set title = excluded.title,
    body = excluded.body,
    variables = excluded.variables,
    active = excluded.active,
    updated_at = timezone('utc', now());
