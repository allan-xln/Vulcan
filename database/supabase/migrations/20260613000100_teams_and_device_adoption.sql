create table if not exists public.teams (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  name text not null,
  description text,
  color text not null default '#f97316',
  status text not null default 'active' check (status in ('active', 'archived')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, name)
);

create table if not exists public.team_members (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  team_id uuid not null references public.teams (id) on delete cascade,
  membership_id uuid not null references public.memberships (id) on delete cascade,
  role_in_team text not null default 'membro',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, team_id, membership_id)
);

create index if not exists idx_teams_tenant_status on public.teams (tenant_id, status);
create index if not exists idx_team_members_membership on public.team_members (tenant_id, membership_id);

alter table public.teams enable row level security;
alter table public.team_members enable row level security;

drop policy if exists teams_read_tenant on public.teams;
create policy teams_read_tenant on public.teams
for select using (
  auth.role() = 'service_role'
  or exists (
    select 1
    from public.memberships m
    where m.tenant_id = teams.tenant_id
      and m.user_id = auth.uid()
      and m.status = 'active'
  )
);

drop policy if exists team_members_read_tenant on public.team_members;
create policy team_members_read_tenant on public.team_members
for select using (
  auth.role() = 'service_role'
  or exists (
    select 1
    from public.memberships m
    where m.tenant_id = team_members.tenant_id
      and m.user_id = auth.uid()
      and m.status = 'active'
  )
);

drop policy if exists service_role_all_teams on public.teams;
create policy service_role_all_teams on public.teams for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

drop policy if exists service_role_all_team_members on public.team_members;
create policy service_role_all_team_members on public.team_members for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
