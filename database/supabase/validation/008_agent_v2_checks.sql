begin;

do $$
declare
  v_user_id uuid;
begin
  select membership.user_id
    into v_user_id
  from public.memberships membership
  where membership.status = 'active'
  order by membership.created_at
  limit 1;

  if v_user_id is null then
    raise exception 'agent v2 validation requires one active membership';
  end if;

  perform set_config('request.jwt.claim.sub', v_user_id::text, true);
  perform set_config('request.jwt.claim.role', 'authenticated', true);
end
$$;

set local role authenticated;

do $$
declare
  v_visible bigint;
  v_table text;
begin
  foreach v_table in array array[
    'agent_enrollment_tokens',
    'agent_identities',
    'agent_policies',
    'agent_request_nonces',
    'agent_commands',
    'agent_releases'
  ]
  loop
    begin
      execute format('select count(*) from public.%I', v_table) into v_visible;
    exception
      when insufficient_privilege then
        v_visible := 0;
    end;
    if v_visible <> 0 then
      raise exception 'RLS leak: authenticated role directly saw % row(s) in %', v_visible, v_table;
    end if;
  end loop;
end
$$;

reset role;

do $$
declare
  v_missing_rls integer;
begin
  select count(*)
    into v_missing_rls
  from pg_tables
  where schemaname = 'public'
    and tablename = any(array[
      'agent_enrollment_tokens',
      'agent_identities',
      'agent_policies',
      'agent_request_nonces',
      'agent_commands',
      'agent_releases'
    ])
    and not rowsecurity;

  if v_missing_rls <> 0 then
    raise exception 'agent v2 RLS disabled on % table(s)', v_missing_rls;
  end if;

  if exists (
    select 1
    from public.agent_enrollment_tokens
    where token_hash !~ '^[0-9a-f]{64}$'
       or length(token_prefix) > 24
  ) then
    raise exception 'agent enrollment token storage is not hash/prefix-only';
  end if;

  if not exists (
    select 1
    from pg_indexes
    where schemaname = 'public'
      and indexname = 'uq_agent_identities_active_device_fingerprint'
      and indexdef ilike '%where%revoked%retired%'
  ) then
    raise exception 'active agent identity uniqueness index is missing';
  end if;

  if not exists (
    select 1
    from pg_trigger trigger_row
    where trigger_row.tgrelid = 'public.activity_events'::regclass
      and trigger_row.tgname = 'trg_activity_events_unified_mirror'
      and pg_get_triggerdef(trigger_row.oid) ilike '%vulcan-agent-v2%'
  ) then
    raise exception 'agent v2 activity mirror guard is missing';
  end if;

  if exists (
    select 1
    from public.unified_events
    where extensions ->> 'compatibilityMirrorSuperseded' = 'true'
      and source = 'vulcan-agent-v2'
      and data_origin <> coalesce(context ->> 'dataOrigin', data_origin)
  ) then
    raise exception 'superseded agent v2 mirror has inconsistent data origin';
  end if;
end
$$;

rollback;
