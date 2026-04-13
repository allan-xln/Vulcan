begin;

set local role authenticated;
set local "request.jwt.claim.sub" = '11111111-1111-1111-1111-111111111111';

do $$
declare
  v_visible_tenants integer;
  v_visible_audit_logs integer;
begin
  select count(*) into v_visible_tenants
  from public.tenants;

  if v_visible_tenants <> 1 then
    raise exception 'expected authenticated seeded user to see 1 tenant, saw %', v_visible_tenants;
  end if;

  select count(*) into v_visible_audit_logs
  from public.audit_logs;

  if v_visible_audit_logs < 1 then
    raise exception 'expected at least 1 audit log row for seeded tenant';
  end if;
end
$$;

rollback;

