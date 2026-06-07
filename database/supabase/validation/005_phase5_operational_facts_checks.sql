do $$
declare
  v_missing_tables text[];
begin
  select array_agg(expected_table)
    into v_missing_tables
  from (
    select unnest(array[
      'operational_fact_runs',
      'session_slices',
      'idle_windows',
      'application_usage_facts'
    ]) as expected_table
  ) expected
  where not exists (
    select 1
    from information_schema.tables t
    where t.table_schema = 'public'
      and t.table_name = expected.expected_table
  );

  if v_missing_tables is not null then
    raise exception 'missing phase 5 tables: %', array_to_string(v_missing_tables, ', ');
  end if;
end
$$;

select
  (select count(*) from public.operational_fact_runs) as operational_fact_run_count,
  (select count(*) from public.session_slices) as session_slice_count,
  (select count(*) from public.idle_windows) as idle_window_count,
  (select count(*) from public.application_usage_facts) as application_usage_count;

