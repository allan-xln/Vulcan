-- Harden hierarchy RLS for unassigned operational rows.
--
-- Earlier MVP policies allowed rows with null owner_membership_id/membership_id
-- without first proving the authenticated user belonged to that row tenant. That
-- is unacceptable for SaaS isolation because unassigned agent data can exist
-- during enrollment. Tenant membership is now mandatory before any unassigned
-- row can be read.

drop policy if exists devices_read_hierarchy on public.devices;
create policy devices_read_hierarchy on public.devices
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or (public.vulcan_is_tenant_member(tenant_id) and owner_membership_id is null)
  or public.vulcan_can_view_membership(tenant_id, owner_membership_id)
);

drop policy if exists activity_events_read_hierarchy on public.activity_events;
create policy activity_events_read_hierarchy on public.activity_events
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or (public.vulcan_is_tenant_member(tenant_id) and membership_id is null)
  or public.vulcan_can_view_membership(tenant_id, membership_id)
);

drop policy if exists metrics_read_hierarchy on public.operational_metrics;
create policy metrics_read_hierarchy on public.operational_metrics
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or (public.vulcan_is_tenant_member(tenant_id) and membership_id is null)
  or public.vulcan_can_view_membership(tenant_id, membership_id)
);

drop policy if exists insights_read_hierarchy on public.ai_insights;
create policy insights_read_hierarchy on public.ai_insights
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or (public.vulcan_is_tenant_member(tenant_id) and membership_id is null)
  or public.vulcan_can_view_membership(tenant_id, membership_id)
);
