do $$
declare
  v_missing_tables text[];
begin
  select array_agg(expected_table)
    into v_missing_tables
  from (
    select unnest(array[
      'ingestion_api_keys',
      'raw_operational_event_intake'
    ]) as expected_table
  ) expected
  where not exists (
    select 1
    from information_schema.tables t
    where t.table_schema = 'public'
      and t.table_name = expected.expected_table
  );

  if v_missing_tables is not null then
    raise exception 'missing phase 3 tables: %', array_to_string(v_missing_tables, ', ');
  end if;
end
$$;

select
  (select count(*) from public.ingestion_api_keys) as ingestion_api_key_count,
  (select count(*) from public.raw_operational_event_intake) as raw_operational_event_intake_count;

