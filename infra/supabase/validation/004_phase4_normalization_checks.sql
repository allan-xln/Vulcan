do $$
declare
  v_missing_tables text[];
begin
  select array_agg(expected_table)
    into v_missing_tables
  from (
    select unnest(array[
      'normalization_runs',
      'normalized_operational_events'
    ]) as expected_table
  ) expected
  where not exists (
    select 1
    from information_schema.tables t
    where t.table_schema = 'public'
      and t.table_name = expected.expected_table
  );

  if v_missing_tables is not null then
    raise exception 'missing phase 4 tables: %', array_to_string(v_missing_tables, ', ');
  end if;
end
$$;

select
  (select count(*) from public.normalization_runs) as normalization_run_count,
  (select count(*) from public.normalized_operational_events) as normalized_event_count;

