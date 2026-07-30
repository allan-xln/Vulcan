from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings, get_settings
from app.platform_schemas import IntegrationSyncResult
from app.repository import VulcanRepository


PROXMOX_NODE_ADDRESSES = {
    "PVE01": "192.168.200.20",
    "PVE02": "192.168.200.23",
    "PVE03": "192.168.200.22",
    "PVE04": "192.168.200.24",
}


class InfrastructureSyncService:
    """Read-only collectors that reconcile external inventory into tenant assets."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.repository = VulcanRepository(self.settings)

    @property
    def enabled(self) -> bool:
        return self.repository.enabled

    def _network_scope(self, conn, tenant_id: UUID, address: str | None) -> tuple[UUID | None, UUID | None]:
        if not address:
            return None, None
        row = conn.execute(
            """
            select site_id, id
            from public.infrastructure_networks
            where tenant_id = %s and %s::inet << network_cidr
            order by masklen(network_cidr) desc
            limit 1
            """,
            (tenant_id, address),
        ).fetchone()
        return (row["site_id"], row["id"]) if row else (None, None)

    def _default_site(self, conn, tenant_id: UUID, code: str = "SJP") -> UUID | None:
        row = conn.execute(
            "select id from public.sites where tenant_id = %s and code = %s",
            (tenant_id, code),
        ).fetchone()
        return row["id"] if row else None

    def _upsert_asset(
        self,
        conn,
        *,
        tenant_id: UUID,
        source: str,
        source_key: str,
        asset_type: str,
        name: str,
        status: str,
        observed_at: datetime,
        address: str | None = None,
        site_id: UUID | None = None,
        hostname: str | None = None,
        manufacturer: str | None = None,
        model: str | None = None,
        serial_number: str | None = None,
        mac_address: str | None = None,
        criticality: str = "high",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[UUID, bool]:
        network_id = None
        network_site_id, network_id = self._network_scope(conn, tenant_id, address)
        site_id = network_site_id or site_id
        existing = conn.execute(
            """
            select id, status
            from public.infrastructure_assets
            where tenant_id = %s and source = %s and source_key = %s
            for update
            """,
            (tenant_id, source, source_key),
        ).fetchone()
        payload = Jsonb(metadata or {})
        if existing:
            conn.execute(
                """
                update public.infrastructure_assets
                set site_id = coalesce(%s, site_id), network_id = coalesce(%s, network_id),
                    asset_type = %s, name = %s, hostname = %s, manufacturer = %s,
                    model = %s, serial_number = %s, ip_address = %s::inet,
                    mac_address = %s, status = %s, criticality = %s,
                    lifecycle_state = 'managed', last_seen_at = %s, tags = %s,
                    metadata = metadata || %s
                where id = %s
                """,
                (
                    site_id,
                    network_id,
                    asset_type,
                    name,
                    hostname,
                    manufacturer,
                    model,
                    serial_number,
                    address,
                    mac_address,
                    status,
                    criticality,
                    observed_at,
                    tags or [],
                    payload,
                    existing["id"],
                ),
            )
            return existing["id"], existing["status"] != status
        asset_id = conn.execute(
            """
            insert into public.infrastructure_assets (
              tenant_id, site_id, network_id, asset_type, name, hostname, manufacturer,
              model, serial_number, ip_address, mac_address, status, criticality,
              lifecycle_state, tags, source, source_key, confidence, discovered_at,
              last_seen_at, metadata
            )
            values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::inet, %s, %s, %s,
              'managed', %s, %s, %s, 1, %s, %s, %s
            )
            returning id
            """,
            (
                tenant_id,
                site_id,
                network_id,
                asset_type,
                name,
                hostname,
                manufacturer,
                model,
                serial_number,
                address,
                mac_address,
                status,
                criticality,
                tags or [],
                source,
                source_key,
                observed_at,
                observed_at,
                payload,
            ),
        ).fetchone()["id"]
        return asset_id, True

    def _relationship(
        self,
        conn,
        tenant_id: UUID,
        source_asset_id: UUID,
        target_asset_id: UUID,
        relationship_type: str,
        source: str,
        observed_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            """
            insert into public.asset_relationships (
              tenant_id, source_asset_id, target_asset_id, relationship_type,
              source, confidence, status, observed_at, metadata
            )
            values (%s, %s, %s, %s, %s, 1, 'active', %s, %s)
            on conflict (tenant_id, source_asset_id, target_asset_id, relationship_type)
            do update set status = 'active', observed_at = excluded.observed_at,
                          metadata = public.asset_relationships.metadata || excluded.metadata
            """,
            (
                tenant_id,
                source_asset_id,
                target_asset_id,
                relationship_type,
                source,
                observed_at,
                Jsonb(metadata or {}),
            ),
        )

    def _status_event(
        self,
        conn,
        *,
        tenant_id: UUID,
        asset_id: UUID,
        source: str,
        source_key: str,
        name: str,
        status: str,
        observed_at: datetime,
    ) -> None:
        source_event_id = f"{source_key}:{status}:{observed_at.strftime('%Y%m%dT%H%M')}"
        fingerprint = hashlib.sha256(f"{tenant_id}:{source}:{source_event_id}".encode()).hexdigest()
        severity = "warning" if status in {"offline", "degraded"} else "info"
        message = (
            f"{name} está {status} na última coleta somente leitura."
            if status != "online"
            else f"{name} voltou a responder na coleta de infraestrutura."
        )
        conn.execute(
            """
            insert into public.unified_events (
              id, tenant_id, asset_id, source, source_type, source_event_id,
              event_type, category, severity, occurred_at, device_occurred_at,
              received_at, actor, device, context, metrics, message, fingerprint,
              confidence, privacy_classification, retention_policy, trusted_origin,
              data_origin, extensions
            )
            values (
              %s, %s, %s, %s, 'infrastructure_adapter', %s,
              'infrastructure.asset.status_changed', 'infrastructure', %s, %s, %s,
              %s, '{}'::jsonb, %s, %s, '{}'::jsonb, %s, %s,
              1, 'operational', 'standard', true, 'real', %s
            )
            on conflict (tenant_id, source, source_event_id) do nothing
            """,
            (
                uuid4(),
                tenant_id,
                asset_id,
                source,
                source_event_id,
                severity,
                observed_at,
                observed_at,
                observed_at,
                Jsonb({"assetName": name}),
                Jsonb({"status": status, "readOnly": True}),
                message,
                fingerprint,
                Jsonb({"adapter": source}),
            ),
        )

    def _mark_integration(
        self,
        conn,
        *,
        tenant_id: UUID,
        adapter_type: str,
        status: str,
        observed_at: datetime,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            """
            update public.integration_instances
            set status = %s, last_tested_at = %s,
                last_success_at = case when %s = 'ready' then %s else last_success_at end,
                last_error = %s,
                metadata = metadata || %s
            where tenant_id = %s and adapter_type = %s
            """,
            (
                status,
                observed_at,
                status,
                observed_at,
                error,
                Jsonb(metadata or {}),
                tenant_id,
                adapter_type,
            ),
        )

    def sync_unifi(self, tenant_id: UUID) -> IntegrationSyncResult:
        observed_at = datetime.now(timezone.utc)
        if not all(
            (
                self.settings.unifi_base_url,
                self.settings.unifi_username,
                self.settings.unifi_password,
            )
        ):
            return IntegrationSyncResult(
                adapterType="unifi",
                status="unavailable",
                dataOrigin="real",
                observedAt=observed_at,
                warnings=["Credencial runtime da UniFi não configurada."],
            )
        try:
            with httpx.Client(
                base_url=self.settings.unifi_base_url,
                verify=self.settings.unifi_verify_tls,
                timeout=20,
                follow_redirects=True,
            ) as client:
                login = client.post(
                    "/api/login",
                    json={
                        "username": self.settings.unifi_username,
                        "password": self.settings.unifi_password,
                    },
                )
                login.raise_for_status()
                response = client.get(f"/api/s/{self.settings.unifi_site}/stat/device")
                response.raise_for_status()
                devices = response.json().get("data", [])
        except Exception as exc:
            warning = f"UniFi indisponível: {type(exc).__name__}"
            with self.repository._connect() as conn:
                self._mark_integration(
                    conn,
                    tenant_id=tenant_id,
                    adapter_type="unifi",
                    status="failed",
                    observed_at=observed_at,
                    error=warning,
                )
                conn.commit()
            return IntegrationSyncResult(
                adapterType="unifi",
                status="unavailable",
                dataOrigin="real",
                observedAt=observed_at,
                warnings=[warning],
            )

        changed = 0
        relationships = 0
        by_name: dict[str, UUID] = {}
        pending_uplinks: list[tuple[UUID, str, int | None]] = []
        with self.repository._connect() as conn:
            default_site = self._default_site(conn, tenant_id)
            for device in devices:
                device_type = "switch" if device.get("type") == "usw" else "access_point"
                name = str(device.get("name") or device.get("mac") or "Equipamento UniFi")
                mac = str(device.get("mac") or "").lower()
                if not mac:
                    continue
                state = int(device.get("state") or 0)
                status = "online" if state == 1 else "offline"
                uplink = device.get("uplink") or {}
                metadata = {
                    "firmware": device.get("version"),
                    "controllerState": state,
                    "clients": int(device.get("num_sta") or 0),
                    "uptimeSeconds": int(device.get("uptime") or 0),
                    "uplinkName": uplink.get("uplink_device_name"),
                    "uplinkPort": uplink.get("uplink_remote_port"),
                    "uplinkSpeedMbps": uplink.get("speed"),
                    "uplinkRxErrors": uplink.get("rx_errors"),
                    "satisfaction": device.get("satisfaction"),
                    "readOnly": True,
                    "observedAt": observed_at.isoformat(),
                }
                asset_id, status_changed = self._upsert_asset(
                    conn,
                    tenant_id=tenant_id,
                    source="unifi",
                    source_key=mac,
                    asset_type=device_type,
                    name=name,
                    hostname=name,
                    address=device.get("ip"),
                    site_id=default_site,
                    manufacturer="Ubiquiti",
                    model=device.get("model"),
                    serial_number=device.get("serial"),
                    mac_address=mac,
                    status=status,
                    observed_at=observed_at,
                    tags=["unifi", "network" if device_type == "switch" else "wifi"],
                    metadata=metadata,
                )
                by_name[name] = asset_id
                if status_changed:
                    changed += 1
                    self._status_event(
                        conn,
                        tenant_id=tenant_id,
                        asset_id=asset_id,
                        source="unifi",
                        source_key=mac,
                        name=name,
                        status=status,
                        observed_at=observed_at,
                    )
                if uplink.get("uplink_device_name"):
                    pending_uplinks.append(
                        (asset_id, str(uplink["uplink_device_name"]), uplink.get("uplink_remote_port"))
                    )
            for asset_id, uplink_name, port in pending_uplinks:
                if uplink_name not in by_name:
                    continue
                self._relationship(
                    conn,
                    tenant_id,
                    asset_id,
                    by_name[uplink_name],
                    "connected_to",
                    "unifi",
                    observed_at,
                    {"uplinkPort": port},
                )
                relationships += 1
            self._mark_integration(
                conn,
                tenant_id=tenant_id,
                adapter_type="unifi",
                status="ready",
                observed_at=observed_at,
                metadata={"devicesSeen": len(devices), "site": self.settings.unifi_site},
            )
            conn.commit()
        return IntegrationSyncResult(
            adapterType="unifi",
            status="ok",
            dataOrigin="real",
            observedAt=observed_at,
            assetsSeen=len(devices),
            assetsUpdated=changed,
            relationshipsUpdated=relationships,
        )

    def sync_proxmox(self, tenant_id: UUID) -> IntegrationSyncResult:
        observed_at = datetime.now(timezone.utc)
        if not all(
            (
                self.settings.proxmox_base_url,
                self.settings.proxmox_username,
                self.settings.proxmox_password,
            )
        ):
            return IntegrationSyncResult(
                adapterType="proxmox",
                status="unavailable",
                dataOrigin="real",
                observedAt=observed_at,
                warnings=["Credencial runtime do Proxmox não configurada."],
            )
        try:
            with httpx.Client(
                base_url=self.settings.proxmox_base_url,
                verify=self.settings.proxmox_verify_tls,
                timeout=20,
            ) as client:
                auth = client.post(
                    "/api2/json/access/ticket",
                    data={
                        "username": self.settings.proxmox_username,
                        "password": self.settings.proxmox_password,
                    },
                )
                auth.raise_for_status()
                ticket = auth.json()["data"]
                headers = {"CSRFPreventionToken": ticket["CSRFPreventionToken"]}
                cookies = {"PVEAuthCookie": ticket["ticket"]}
                nodes_response = client.get("/api2/json/nodes", headers=headers, cookies=cookies)
                resources_response = client.get(
                    "/api2/json/cluster/resources",
                    params={"type": "vm"},
                    headers=headers,
                    cookies=cookies,
                )
                status_response = client.get("/api2/json/cluster/status", headers=headers, cookies=cookies)
                nodes_response.raise_for_status()
                resources_response.raise_for_status()
                status_response.raise_for_status()
                nodes = nodes_response.json()["data"]
                resources = resources_response.json()["data"]
                cluster_status = status_response.json()["data"]
        except Exception as exc:
            warning = f"Proxmox indisponível: {type(exc).__name__}"
            with self.repository._connect() as conn:
                self._mark_integration(
                    conn,
                    tenant_id=tenant_id,
                    adapter_type="proxmox",
                    status="failed",
                    observed_at=observed_at,
                    error=warning,
                )
                conn.commit()
            return IntegrationSyncResult(
                adapterType="proxmox",
                status="unavailable",
                dataOrigin="real",
                observedAt=observed_at,
                warnings=[warning],
            )

        changed = 0
        relationships = 0
        with self.repository._connect() as conn:
            default_site = self._default_site(conn, tenant_id)
            cluster_name = next(
                (
                    str(item.get("name"))
                    for item in cluster_status
                    if item.get("type") == "cluster" and item.get("name")
                ),
                "ERSTRANSPORTES",
            )
            cluster_id, cluster_changed = self._upsert_asset(
                conn,
                tenant_id=tenant_id,
                source="proxmox",
                source_key=f"cluster:{cluster_name}",
                asset_type="proxmox_cluster",
                name=f"Cluster {cluster_name}",
                status="online",
                observed_at=observed_at,
                site_id=default_site,
                manufacturer="Proxmox",
                criticality="critical",
                tags=["proxmox", "virtualization"],
                metadata={"nodes": len(nodes), "readOnly": True, "observedAt": observed_at.isoformat()},
            )
            changed += int(cluster_changed)
            node_assets: dict[str, UUID] = {}
            for node in nodes:
                node_name = str(node["node"])
                node_status = "online" if node.get("status") == "online" else "offline"
                node_id, node_changed = self._upsert_asset(
                    conn,
                    tenant_id=tenant_id,
                    source="proxmox",
                    source_key=f"node:{node_name}",
                    asset_type="virtualization_host",
                    name=node_name,
                    hostname=node_name,
                    address=PROXMOX_NODE_ADDRESSES.get(node_name),
                    status=node_status,
                    observed_at=observed_at,
                    site_id=default_site,
                    manufacturer="Proxmox",
                    criticality="critical",
                    tags=["proxmox", "node"],
                    metadata={
                        "cpuUsage": node.get("cpu"),
                        "cpuCores": node.get("maxcpu"),
                        "memoryBytes": node.get("mem"),
                        "memoryMaxBytes": node.get("maxmem"),
                        "diskBytes": node.get("disk"),
                        "diskMaxBytes": node.get("maxdisk"),
                        "uptimeSeconds": node.get("uptime"),
                        "readOnly": True,
                        "observedAt": observed_at.isoformat(),
                    },
                )
                node_assets[node_name] = node_id
                changed += int(node_changed)
                self._relationship(
                    conn,
                    tenant_id,
                    cluster_id,
                    node_id,
                    "hosts",
                    "proxmox",
                    observed_at,
                )
                relationships += 1
                if node_changed:
                    self._status_event(
                        conn,
                        tenant_id=tenant_id,
                        asset_id=node_id,
                        source="proxmox",
                        source_key=f"node:{node_name}",
                        name=node_name,
                        status=node_status,
                        observed_at=observed_at,
                    )
            for vm in resources:
                vmid = int(vm["vmid"])
                vm_name = str(vm.get("name") or f"VM {vmid}")
                vm_status = "online" if vm.get("status") == "running" else "offline"
                vm_id, vm_changed = self._upsert_asset(
                    conn,
                    tenant_id=tenant_id,
                    source="proxmox",
                    source_key=f"vm:{vmid}",
                    asset_type="virtual_machine",
                    name=vm_name,
                    hostname=vm_name,
                    address="192.168.200.26" if vmid == 103 else None,
                    status=vm_status,
                    observed_at=observed_at,
                    site_id=default_site,
                    manufacturer="Proxmox",
                    criticality="critical" if vmid == 103 else "high",
                    tags=["proxmox", "vm"],
                    metadata={
                        "vmid": vmid,
                        "node": vm.get("node"),
                        "cpuUsage": vm.get("cpu"),
                        "cpuCores": vm.get("maxcpu"),
                        "memoryBytes": vm.get("mem"),
                        "memoryMaxBytes": vm.get("maxmem"),
                        "diskBytes": vm.get("disk"),
                        "diskMaxBytes": vm.get("maxdisk"),
                        "uptimeSeconds": vm.get("uptime"),
                        "template": bool(vm.get("template")),
                        "readOnly": True,
                        "observedAt": observed_at.isoformat(),
                    },
                )
                changed += int(vm_changed)
                host_id = node_assets.get(str(vm.get("node")))
                if host_id:
                    self._relationship(
                        conn,
                        tenant_id,
                        host_id,
                        vm_id,
                        "hosts",
                        "proxmox",
                        observed_at,
                    )
                    relationships += 1
                if vm_changed:
                    self._status_event(
                        conn,
                        tenant_id=tenant_id,
                        asset_id=vm_id,
                        source="proxmox",
                        source_key=f"vm:{vmid}",
                        name=vm_name,
                        status=vm_status,
                        observed_at=observed_at,
                    )
            self._mark_integration(
                conn,
                tenant_id=tenant_id,
                adapter_type="proxmox",
                status="ready",
                observed_at=observed_at,
                metadata={"nodesSeen": len(nodes), "virtualMachinesSeen": len(resources)},
            )
            conn.commit()
        return IntegrationSyncResult(
            adapterType="proxmox",
            status="ok",
            dataOrigin="real",
            observedAt=observed_at,
            assetsSeen=len(nodes) + len(resources) + 1,
            assetsUpdated=changed,
            relationshipsUpdated=relationships,
        )

    def sync(self, tenant_id: UUID, adapter_type: str) -> IntegrationSyncResult:
        if not self.enabled:
            raise ValueError("database is required for infrastructure synchronization")
        if adapter_type == "unifi":
            return self.sync_unifi(tenant_id)
        if adapter_type == "proxmox":
            return self.sync_proxmox(tenant_id)
        raise ValueError("unsupported infrastructure adapter")

    def enabled_tenants(self) -> list[tuple[UUID, str]]:
        if not self.enabled:
            return []
        with self.repository._connect() as conn:
            return [
                (row["tenant_id"], row["adapter_type"])
                for row in conn.execute(
                    """
                    select distinct tenant_id, adapter_type
                    from public.integration_instances
                    where enabled and read_only and adapter_type in ('unifi', 'proxmox')
                    order by tenant_id, adapter_type
                    """
                ).fetchall()
            ]


def run_worker() -> None:
    settings = get_settings()
    service = InfrastructureSyncService(settings)
    while True:
        started = time.monotonic()
        for tenant_id, adapter_type in service.enabled_tenants():
            try:
                result = service.sync(tenant_id, adapter_type)
                print(
                    f"infrastructure_sync adapter={adapter_type} tenant={tenant_id} "
                    f"status={result.status} assets_seen={result.assets_seen}"
                )
            except Exception as exc:
                print(
                    f"infrastructure_sync adapter={adapter_type} tenant={tenant_id} "
                    f"status=failed error={type(exc).__name__}"
                )
        elapsed = time.monotonic() - started
        time.sleep(max(1, settings.infrastructure_sync_interval_seconds - elapsed))


if __name__ == "__main__":
    run_worker()
