#!/usr/bin/env python3
"""Idempotently seed the audited ERS infrastructure inventory.

The file intentionally contains no credentials and performs no network requests.
Dynamic collectors reconcile the imported observations after provisioning.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


TENANT_SLUG = "ers-transportes"
OBSERVED_AT = datetime(2026, 7, 30, 13, 30, tzinfo=timezone.utc)


@dataclass(frozen=True)
class NetworkSeed:
    site: str
    key: str
    name: str
    cidr: str
    gateway: str | None
    vlan: int | None = None
    metadata: dict[str, Any] | None = None


SITES = (
    {
        "code": "SJP",
        "slug": "matriz-sjp",
        "name": "Matriz SJP",
        "city": "São José dos Pinhais",
        "state": "PR",
        "description": "Matriz operacional da ERS Transportes.",
        "order": 10,
        "color": "#f97316",
    },
    {
        "code": "PNG",
        "slug": "paranagua",
        "name": "Paranaguá",
        "city": "Paranaguá",
        "state": "PR",
        "description": "Filial operacional de Paranaguá.",
        "order": 20,
        "color": "#f59e0b",
    },
    {
        "code": "AZ",
        "slug": "armazem",
        "name": "Armazém",
        "city": None,
        "state": "PR",
        "description": "Operação de armazém; cidade ainda não confirmada.",
        "order": 30,
        "color": "#d97706",
    },
)

NETWORKS = (
    NetworkSeed("SJP", "sjp-lan", "LAN principal", "192.168.200.0/24", "192.168.200.1"),
    NetworkSeed("SJP", "sjp-mobile", "Mobile", "192.168.210.0/24", "192.168.210.254", 10),
    NetworkSeed("SJP", "sjp-visitors", "Visitantes", "192.168.220.0/24", "192.168.220.254", 20),
    NetworkSeed("SJP", "sjp-employees", "Colaboradores", "192.168.230.0/24", "192.168.230.254", 30),
    NetworkSeed("SJP", "sjp-cctv", "CFTV", "192.168.240.0/24", "192.168.240.254"),
    NetworkSeed("PNG", "png-admin", "Administrativo", "10.1.1.0/24", "10.1.1.1"),
    NetworkSeed("PNG", "png-warehouse", "Armazém", "10.1.2.0/24", "10.1.2.1"),
    NetworkSeed(
        "PNG",
        "png-cctv-admin",
        "CFTV Administrativo",
        "10.1.40.0/24",
        "10.1.40.1",
        metadata={"alternateGateway": "10.1.40.254", "requiresReconciliation": True},
    ),
    NetworkSeed("PNG", "png-cctv-warehouse", "CFTV Armazém", "10.1.42.0/24", "10.1.42.254"),
    NetworkSeed(
        "SJP",
        "ers-advpn",
        "ADVPN entre filiais",
        "10.252.252.0/24",
        "10.252.252.1",
        metadata={"scope": "inter_site", "endpoints": ["10.252.252.1", "10.252.252.3"]},
    ),
)

PRINTERS = (
    ("SJP", "Almoxarifado", "Almoxarifado", "Xerox", "WorkCentre 3345", "192.168.200.205", "Locada", "Qualiinfo", "D203U", 10),
    ("SJP", "Borracharia", "Borracharia", "Xerox", None, "192.168.200.203", "Locada", "Qualiinfo", "D203U", 10),
    ("SJP", "Compras", "Compras", "Canon", "iR1643i II", "192.168.200.249", "Locada", "Qualiinfo", "258x", 6),
    ("SJP", "Financeiro", "Financeiro", "Canon", "iR1643i II", "192.168.200.48", "Locada", "Qualiinfo", "258x", 6),
    ("SJP", "Frota", "Frota", "Samsung", "M4080FX", "192.168.200.196", "Locada", "Qualiinfo", "BQ-MLT201L", 4),
    ("SJP", "Oficina", "Oficina", "Xerox", "WorkCentre 3345", "192.168.200.230", "Locada", "Qualiinfo", "D203U", 10),
    ("SJP", "Operacional", "Operacional", "Samsung", "M4080FX", "192.168.200.25", "Própria", None, None, None),
    ("SJP", "Qualidade", "Qualidade", "Epson", "WF-C5710", "192.168.200.132", "Locada", "Qualiinfo", None, None),
    ("SJP", "RH", "RH", "Xerox", None, "192.168.200.95", "Locada", "Qualiinfo", "D203U", 10),
    ("SJP", "Torre", "Torre", "Xerox", None, "192.168.200.107", "Locada", "Qualiinfo", "D203U", 10),
    ("PNG", "Armazém", "Armazém", "HP", None, "10.1.2.116", "Locada", "Qualiinfo", "258x", 6),
    ("PNG", "Armazém Barracão", "Armazém Barracão", "Samsung", "M408x", "10.1.2.120", "Própria", None, None, None),
    ("PNG", "Etiquetas Armazém", "Galpão", "Honeywell", None, "10.1.2.166", "Locada", "Qualiinfo", None, None),
    ("PNG", "Operacional Paranaguá", "Operacional", "Brother", "MFC-L6902DW", "10.1.1.125", "Locada", "Qualiinfo", "BQ-TN3470/3492", 1),
)

UNIFI_DEVICES = (
    ("access_point", "U6-LR-ADM-01", "192.168.200.30", "ac:8b:a9:53:d9:b5", "AC8BA953D9B5", "UALR6v2", "6.7.54.15663", 1, 33, "USW-TI-3-POE", 11, 1000, 271665),
    ("access_point", "U6-LR-PORTARIA-1", "192.168.200.118", "ac:8b:a9:53:d9:21", "AC8BA953D921", "UALR6v2", "6.7.54.15663", 1, 5, "USW-PORTARIA", 2, 1000, 117),
    ("access_point", "U6-Mesh-RH", "192.168.200.50", "ac:8b:a9:db:3a:d0", "AC8BA9DB3AD0", "U6M", "6.8.2.15592", 1, 17, "USW-TI-2-PRO", 3, 1000, 0),
    ("access_point", "U7 LR Operacional - Matriz", "10.1.1.96", "a8:9c:6c:dc:d2:3f", "A89C6CDCD23F", "UAPA6B3", "8.0.74.16817", 1, 7, "USW Pro Max 16 PoE", 5, 1000, 2930),
    ("access_point", "U7 Long-Range", "192.168.200.74", "a8:9c:6c:dc:83:9a", "A89C6CDC839A", "UAPA6B3", "8.0.74.16817", 1, 7, "USW-TI-1-PRO", 9, 1000, 335),
    ("access_point", "U7 Outdoor Frente - Matriz", "10.1.1.91", "0c:ea:14:b9:78:81", "0CEA14B97881", "UKPW", "8.6.11.18870", 1, 1, "USW Pro Max 16 PoE", 2, 1000, 0),
    ("access_point", "U7 Outdoor Fundos - Matriz", "10.1.40.2", "0c:ea:14:b9:0b:c9", "0CEA14B90BC9", "UKPW", "8.6.11.18870", 1, 3, None, None, 1000, 0),
    ("access_point", "U7 Outdoor Portaria - Matriz", "10.1.1.131", "58:d6:1f:a6:11:79", "58D61FA61179", "UKPW", "8.6.11.18870", 1, 1, None, None, 100, 0),
    ("access_point", "U7 Outdoor Traz - Matriz", "10.1.1.92", "0c:ea:14:b9:75:42", "0CEA14B97542", "UKPW", "8.6.11.18870", 1, 2, "USW Pro Max 16 PoE", 3, 1000, 0),
    ("access_point", "U7-LR-ADM-02", "192.168.200.59", "a8:9c:6c:dc:78:66", "A89C6CDC7866", "UAPA6B3", "8.0.74.16817", 1, 26, "USW-TI-3-POE", 7, 100, 48503),
    ("access_point", "U7-OUT-ARMAZEM", "10.1.2.101", "0c:ea:14:b9:76:86", "0CEA14B97686", "UKPW", "8.6.11.18870", 1, 2, None, None, 1000, 0),
    ("access_point", "U7-OUT-BORRACHARIA", "192.168.200.75", "0c:ea:14:b9:77:64", "0CEA14B97764", "UKPW", "8.6.11.18870", 1, 7, "USW-TI-1-PRO", 9, 1000, 0),
    ("access_point", "U7-OUT-PATIO-01", "192.168.200.78", "0c:ea:14:b9:75:96", "0CEA14B97596", "UKPW", "8.6.11.18870", 1, 6, "USW-OFICINA", 9, 1000, 0),
    ("access_point", "U7-OUT-PORTARIA-2", "192.168.200.85", "0c:ea:14:b3:ab:92", "0CEA14B3AB92", "UKPW", "8.6.11.18870", 1, 11, "USW-PORTARIA", 1, 1000, 0),
    ("access_point", "U7_LR_OFICINA", "192.168.200.77", "a8:9c:6c:dc:de:96", "A89C6CDCDE96", "UAPA6B3", "8.0.74.16817", 1, 30, "USW-OFICINA", 23, 1000, 584),
    ("access_point", "U7_MATRIZ", "10.1.1.95", "a8:9c:6c:dc:d0:fb", "A89C6CDCD0FB", "UAPA6B3", "8.0.74.16817", 1, 18, "USW Pro Max 16 PoE", 4, 1000, 26038),
    ("access_point", "U7_PISO2_MATRIZ", "192.168.240.1", "0c:ea:14:b9:76:e9", "0CEA14B976E9", "UKPW", "8.6.11.18870", 0, 0, None, 24, None, None),
    ("switch", "USW Pro Max 16 PoE", "10.1.1.94", "58:d6:1f:45:84:4f", "58D61F45844F", "USPM16P", "7.4.1.16850", 1, 0, None, None, 1000, 0),
    ("switch", "USW-OFICINA", "192.168.200.40", "1c:6a:1b:3c:4c:c9", "1C6A1B3C4CC9", "USL24PB", "7.4.1.16850", 1, 10, "USW-TI-1-PRO", 14, 1000, 0),
    ("switch", "USW-PORTARIA", "192.168.200.44", "1c:6a:1b:38:1d:e3", "1C6A1B381DE3", "USL16PB", "7.4.1.16850", 1, 8, "USW-TI-1-PRO", 24, 1000, 0),
    ("switch", "USW-TI-1-PRO", "192.168.200.41", "d8:b3:70:8d:19:a7", "D8B3708D19A7", "US24PRO2", "7.4.1.16850", 1, 22, None, None, 1000, 0),
    ("switch", "USW-TI-2-PRO", "192.168.200.42", "d8:b3:70:8d:18:21", "D8B3708D1821", "US24PRO2", "7.4.1.16850", 1, 41, None, None, 1000, 0),
    ("switch", "USW-TI-3-POE", "192.168.200.43", "28:70:4e:db:64:64", "28704EDB6464", "USL24PB", "7.4.1.16850", 1, 15, None, None, 1000, 0),
)

WINDOWS_SERVERS = (
    ("SRVERS01", "192.168.200.4", "Windows Server 2025 Standard", ["Active Directory", "DNS", "controlador de domínio", "entrada oficial Vulcan"], []),
    ("SRVERS02", "192.168.200.9", "Windows Server 2025 Standard", ["servidor de impressão", "compartilhamentos"], []),
    ("SRVERS04", "192.168.200.7", "Windows Server 2019 Standard", [], ["SRVBKP"]),
    ("SRVERS05", "192.168.200.59", "Windows Server 2025 Standard", [], []),
    ("SRVERS06", "192.168.200.10", "Windows Server 2025 Standard", ["KMM", "aplicação corporativa"], ["SRVHV01"]),
    ("SRVERS07", "192.168.200.11", "Windows Server 2025 Standard", [], ["SRVBKP01"]),
    ("SRVERS08", "192.168.200.15", "Windows Server 2025 Standard", ["Active Directory", "DNS", "controlador de domínio"], []),
    ("SRVBACKUP-PNG", "192.168.200.150", "Windows Server 2019 Standard", [], []),
    ("SRVHV02", "192.168.200.216", "Windows Server 2012 R2 Standard", [], []),
    ("SVR-ICONS", "192.168.200.18", "Windows Server 2012 R2 Standard", [], []),
)

PROXMOX_NODES = (
    ("PVE01", "192.168.200.20"),
    ("PVE02", "192.168.200.23"),
    ("PVE03", "192.168.200.22"),
    ("PVE04", "192.168.200.24"),
)

PROXMOX_VMS = (
    (100, "PBS01", "PVE01", "running"),
    (101, "PDM01", "PVE01", "running"),
    (102, "SRVERS02", "PVE04", "running"),
    (103, "VULCAN-PROD01", "PVE02", "running"),
    (124, "SRVERS04", "PVE01", "running"),
    (125, "SRVERS05", "PVE04", "stopped"),
    (127, "SRVERS07", "PVE02", "stopped"),
    (129, "SRVERS01", "PVE04", "running"),
    (131, "SRVERS08", "PVE01", "running"),
    (132, "SRVERS06", "PVE04", "stopped"),
    (133, "SRVERS03", "PVE01", "stopped"),
    (134, "SRVERS06", "PVE01", "running"),
)


def network_for_ip(networks: dict[str, dict[str, Any]], value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    parsed = ip_address(value)
    matches = [row for row in networks.values() if parsed in ip_network(row["cidr"])]
    return max(matches, key=lambda row: ip_network(row["cidr"]).prefixlen) if matches else None


def upsert_asset(
    conn: psycopg.Connection,
    *,
    tenant_id: UUID,
    sites: dict[str, UUID],
    networks: dict[str, dict[str, Any]],
    source: str,
    source_key: str,
    asset_type: str,
    name: str,
    site_code: str | None = None,
    ip: str | None = None,
    hostname: str | None = None,
    manufacturer: str | None = None,
    model: str | None = None,
    serial: str | None = None,
    mac: str | None = None,
    operating_system: str | None = None,
    status: str = "unknown",
    criticality: str = "medium",
    last_seen_at: datetime | None = None,
    physical_location: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> UUID:
    matched_network = network_for_ip(networks, ip)
    if matched_network:
        site_code = str(matched_network["site"])
    site_id = sites.get(site_code or "")
    network_id = matched_network["id"] if matched_network else None
    row = conn.execute(
        """
        select id
        from public.infrastructure_assets
        where tenant_id = %s and source = %s and source_key = %s
        """,
        (tenant_id, source, source_key),
    ).fetchone()
    values = (
        site_id,
        network_id,
        asset_type,
        name,
        hostname,
        manufacturer,
        model,
        serial,
        ip,
        mac,
        operating_system,
        status,
        criticality,
        last_seen_at,
        physical_location,
        tags or [],
        Jsonb(metadata or {}),
    )
    if row:
        conn.execute(
            """
            update public.infrastructure_assets
            set site_id = %s, network_id = %s, asset_type = %s, name = %s, hostname = %s,
                manufacturer = %s, model = %s, serial_number = %s, ip_address = %s::inet,
                mac_address = %s, operating_system = %s, status = %s, criticality = %s,
                lifecycle_state = 'managed', last_seen_at = %s, physical_location = %s,
                tags = %s, metadata = metadata || %s
            where id = %s
            """,
            (*values, row["id"]),
        )
        return row["id"]
    return conn.execute(
        """
        insert into public.infrastructure_assets (
          tenant_id, site_id, network_id, asset_type, name, hostname, manufacturer, model,
          serial_number, ip_address, mac_address, operating_system, status, criticality,
          lifecycle_state, last_seen_at, physical_location, tags, source, source_key, metadata,
          confidence, discovered_at
        )
        values (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::inet, %s, %s, %s, %s,
          'managed', %s, %s, %s, %s, %s, %s, 1, %s
        )
        returning id
        """,
        (tenant_id, *values[:16], source, source_key, values[16], last_seen_at),
    ).fetchone()["id"]


def relate(
    conn: psycopg.Connection,
    tenant_id: UUID,
    source_asset_id: UUID,
    target_asset_id: UUID,
    relationship_type: str,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        insert into public.asset_relationships (
          tenant_id, source_asset_id, target_asset_id, relationship_type, source,
          confidence, status, observed_at, metadata
        )
        values (%s, %s, %s, %s, %s, 1, 'active', %s, %s)
        on conflict (tenant_id, source_asset_id, target_asset_id, relationship_type)
        do update set source = excluded.source, status = 'active',
                      observed_at = excluded.observed_at,
                      metadata = public.asset_relationships.metadata || excluded.metadata
        """,
        (tenant_id, source_asset_id, target_asset_id, relationship_type, source, OBSERVED_AT, Jsonb(metadata or {})),
    )


def seed() -> dict[str, int]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        tenant = conn.execute(
            "select id from public.tenants where slug = %s",
            (TENANT_SLUG,),
        ).fetchone()
        if not tenant:
            raise RuntimeError(f"tenant {TENANT_SLUG!r} not found")
        tenant_id = tenant["id"]

        sites: dict[str, UUID] = {}
        for item in SITES:
            row = conn.execute(
                """
                insert into public.sites (
                  tenant_id, code, slug, name, description, city, state, timezone, status,
                  display_order, semantic_color, rotation_enabled, rotation_seconds, visible,
                  tags, source, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, 'America/Sao_Paulo', 'active',
                        %s, %s, true, 30, true, %s, 'ers_inventory', %s)
                on conflict (tenant_id, code)
                do update set slug = excluded.slug, name = excluded.name,
                              description = excluded.description, city = excluded.city,
                              state = excluded.state, display_order = excluded.display_order,
                              semantic_color = excluded.semantic_color,
                              tags = excluded.tags, source = excluded.source,
                              metadata = public.sites.metadata || excluded.metadata
                returning id
                """,
                (
                    tenant_id,
                    item["code"],
                    item["slug"],
                    item["name"],
                    item["description"],
                    item["city"],
                    item["state"],
                    item["order"],
                    item["color"],
                    ["ers", "filial"],
                    Jsonb({"inventorySource": "authorized_ers_closeout", "cityConfirmed": item["city"] is not None}),
                ),
            ).fetchone()
            sites[item["code"]] = row["id"]

        networks: dict[str, dict[str, Any]] = {}
        for item in NETWORKS:
            row = conn.execute(
                """
                insert into public.infrastructure_networks (
                  tenant_id, site_id, name, network_cidr, gateway, vlan_id,
                  discovery_allowed, status, tags, source, source_key, metadata
                )
                values (%s, %s, %s, %s::cidr, %s::inet, %s, false, 'active',
                        %s, 'ers_inventory', %s, %s)
                on conflict (tenant_id, site_id, network_cidr)
                do update set name = excluded.name, gateway = excluded.gateway,
                              vlan_id = excluded.vlan_id, tags = excluded.tags,
                              source = excluded.source, source_key = excluded.source_key,
                              metadata = public.infrastructure_networks.metadata || excluded.metadata
                returning id
                """,
                (
                    tenant_id,
                    sites[item.site],
                    item.name,
                    item.cidr,
                    item.gateway,
                    item.vlan,
                    ["ers", item.site.lower()],
                    item.key,
                    Jsonb(item.metadata or {}),
                ),
            ).fetchone()
            networks[item.key] = {"id": row["id"], "cidr": item.cidr, "site": item.site}

        for item in NETWORKS:
            conn.execute(
                """
                insert into public.discovery_policies (
                  tenant_id, site_id, name, enabled, read_only, safe_mode,
                  allowed_networks, denied_networks, excluded_addresses,
                  allowed_protocols, allowed_tcp_ports, frequency_minutes,
                  concurrency, timeout_ms, max_targets, execution_window, metadata
                )
                values (
                  %s, %s, %s, false, true, true,
                  array[%s::cidr], '{}'::cidr[], '{}'::inet[],
                  array['icmp', 'dns', 'reverse_dns']::text[], '{}'::integer[],
                  360, 4, 750, 256, '{}'::jsonb, %s
                )
                on conflict (tenant_id, site_id, name)
                do update set enabled = false, read_only = true, safe_mode = true,
                              allowed_networks = excluded.allowed_networks,
                              allowed_protocols = excluded.allowed_protocols,
                              allowed_tcp_ports = excluded.allowed_tcp_ports,
                              frequency_minutes = excluded.frequency_minutes,
                              concurrency = excluded.concurrency,
                              timeout_ms = excluded.timeout_ms,
                              max_targets = excluded.max_targets,
                              metadata = public.discovery_policies.metadata || excluded.metadata
                """,
                (
                    tenant_id,
                    sites[item.site],
                    f"Descoberta segura — {item.name}",
                    item.cidr,
                    Jsonb(
                        {
                            "approvalRequired": True,
                            "createdBy": "ers_inventory",
                            "networkKey": item.key,
                            "readOnly": True,
                        }
                    ),
                ),
            )

        assets: dict[str, UUID] = {}
        ping_observation = {"method": "icmp", "observedAt": OBSERVED_AT.isoformat(), "readOnly": True}
        firewall_seeds = (
            ("SJP", "FGT-ERSSJP", "192.168.200.1", ["187.95.123.200", "189.112.145.205"], "online"),
            ("PNG", "FGT-ERSPNG", "10.1.1.1", ["177.220.148.149", "200.142.150.226"], "online"),
            ("AZ", "FGT-ERSAZ", None, ["187.95.122.114", "200.142.150.222"], "unknown"),
        )
        for site_code, name, ip, wan_addresses, status in firewall_seeds:
            firewall_id = upsert_asset(
                conn,
                tenant_id=tenant_id,
                sites=sites,
                networks=networks,
                source="ers_inventory",
                source_key=f"firewall:{name}",
                asset_type="firewall",
                name=name,
                hostname=name,
                manufacturer="Fortinet",
                site_code=site_code,
                ip=ip,
                status=status,
                criticality="critical",
                last_seen_at=OBSERVED_AT if status == "online" else None,
                tags=["firewall", "gateway", "fortigate"],
                metadata={"wanAddresses": wan_addresses, "observation": ping_observation if ip else None},
            )
            assets[name] = firewall_id
            for index, wan_ip in enumerate(wan_addresses, start=1):
                wan_id = upsert_asset(
                    conn,
                    tenant_id=tenant_id,
                    sites=sites,
                    networks=networks,
                    source="ers_inventory",
                    source_key=f"wan:{name}:{index}",
                    asset_type="wan_link",
                    name=f"{name} WAN {index}",
                    site_code=site_code,
                    ip=wan_ip,
                    status="unknown",
                    criticality="critical",
                    tags=["wan", "internet"],
                    metadata={"publicAddress": wan_ip, "monitoring": "pending"},
                )
                relate(conn, tenant_id, firewall_id, wan_id, "connected_to", "ers_inventory")

        advpn_id = upsert_asset(
            conn,
            tenant_id=tenant_id,
            sites=sites,
            networks=networks,
            source="ers_inventory",
            source_key="vpn:advpn",
            asset_type="vpn_tunnel",
            name="ADVPN entre filiais",
            site_code="SJP",
            status="online",
            criticality="critical",
            last_seen_at=OBSERVED_AT,
            tags=["advpn", "inter_site"],
            metadata={"network": "10.252.252.0/24", "endpoints": ["10.252.252.1", "10.252.252.3"], "observation": ping_observation},
        )
        for firewall_name in ("FGT-ERSSJP", "FGT-ERSPNG", "FGT-ERSAZ"):
            relate(conn, tenant_id, assets[firewall_name], advpn_id, "connected_to", "ers_inventory")

        nat_id = upsert_asset(
            conn,
            tenant_id=tenant_id,
            sites=sites,
            networks=networks,
            source="ers_inventory",
            source_key="nat:veeder-root",
            asset_type="nat_service",
            name="Veeder-Root publicado",
            site_code="PNG",
            status="unknown",
            criticality="high",
            tags=["nat", "veeder-root", "published_service"],
            metadata={"externalEndpoint": "200.142.150.226:7443", "probableInternalTarget": "10.1.1.250:7443", "targetRequiresConfirmation": True},
        )
        relate(conn, tenant_id, assets["FGT-ERSPNG"], nat_id, "runs", "ers_inventory")

        for hostname, ip, os_name, roles, aliases in WINDOWS_SERVERS:
            assets[f"server:{hostname}"] = upsert_asset(
                conn,
                tenant_id=tenant_id,
                sites=sites,
                networks=networks,
                source="active_directory",
                source_key=hostname.lower(),
                asset_type="server",
                name=hostname,
                hostname=hostname,
                ip=ip,
                operating_system=os_name,
                status="unknown",
                criticality="critical" if "controlador de domínio" in roles else "high",
                tags=["windows", "active_directory"],
                metadata={"roles": roles, "aliases": aliases, "source": "AD/DNS audit", "observedAt": OBSERVED_AT.isoformat()},
            )

        cluster_id = upsert_asset(
            conn,
            tenant_id=tenant_id,
            sites=sites,
            networks=networks,
            source="proxmox",
            source_key="cluster:ERSTRANSPORTES",
            asset_type="proxmox_cluster",
            name="Cluster ERSTRANSPORTES",
            site_code="SJP",
            manufacturer="Proxmox",
            status="online",
            criticality="critical",
            last_seen_at=OBSERVED_AT,
            tags=["proxmox", "virtualization"],
            metadata={"nodes": 4, "readOnly": True},
        )
        for node_name, node_ip in PROXMOX_NODES:
            node_id = upsert_asset(
                conn,
                tenant_id=tenant_id,
                sites=sites,
                networks=networks,
                source="proxmox",
                source_key=f"node:{node_name}",
                asset_type="virtualization_host",
                name=node_name,
                hostname=node_name,
                site_code="SJP",
                ip=node_ip,
                manufacturer="Proxmox",
                status="online",
                criticality="critical",
                last_seen_at=OBSERVED_AT,
                tags=["proxmox", "node"],
                metadata={"readOnly": True},
            )
            assets[f"node:{node_name}"] = node_id
            relate(conn, tenant_id, cluster_id, node_id, "hosts", "proxmox")

        for vmid, vm_name, node_name, vm_status in PROXMOX_VMS:
            vm_id = upsert_asset(
                conn,
                tenant_id=tenant_id,
                sites=sites,
                networks=networks,
                source="proxmox",
                source_key=f"vm:{vmid}",
                asset_type="virtual_machine",
                name=vm_name,
                hostname=vm_name,
                site_code="SJP",
                ip="192.168.200.26" if vmid == 103 else None,
                manufacturer="Proxmox",
                status="online" if vm_status == "running" else "offline",
                criticality="critical" if vmid == 103 else "high",
                last_seen_at=OBSERVED_AT,
                tags=["proxmox", "vm"],
                metadata={"vmid": vmid, "node": node_name, "proxmoxStatus": vm_status, "readOnly": True},
            )
            assets[f"vm:{vmid}"] = vm_id
            relate(conn, tenant_id, assets[f"node:{node_name}"], vm_id, "hosts", "proxmox")

        backup_id = upsert_asset(
            conn,
            tenant_id=tenant_id,
            sites=sites,
            networks=networks,
            source="proxmox",
            source_key="backup-job:vulcan-prod01-daily",
            asset_type="backup_job",
            name="Backup diário VULCAN-PROD01",
            site_code="SJP",
            status="online",
            criticality="critical",
            last_seen_at=OBSERVED_AT,
            tags=["backup", "pbs", "vm103"],
            metadata={"jobId": "vulcan-prod01-daily", "schedule": "03:15", "storage": "BACKUPSERS", "vmid": 103, "retention": {"daily": 7, "weekly": 4, "monthly": 6}, "lastTask": "TASK OK"},
        )
        relate(conn, tenant_id, backup_id, assets["vm:103"], "depends_on", "proxmox")

        for site_code, name, location, manufacturer, model, ip, ownership, supplier, toner, stock in PRINTERS:
            upsert_asset(
                conn,
                tenant_id=tenant_id,
                sites=sites,
                networks=networks,
                source="ers_inventory",
                source_key=f"printer:{ip}",
                asset_type="printer",
                name=f"Impressora {name}",
                site_code=site_code,
                ip=ip,
                manufacturer=manufacturer,
                model=model,
                status="online",
                criticality="medium",
                last_seen_at=OBSERVED_AT,
                physical_location=location,
                tags=["printer", site_code.lower()],
                metadata={"ownership": ownership, "supplier": supplier, "toner": toner, "stock": stock, "observation": ping_observation},
            )

        for device in UNIFI_DEVICES:
            asset_type, name, ip, mac, serial, model, firmware, state, clients, uplink, port, speed, rx_errors = device
            status = "online" if state == 1 else "offline"
            device_id = upsert_asset(
                conn,
                tenant_id=tenant_id,
                sites=sites,
                networks=networks,
                source="unifi",
                source_key=mac,
                asset_type=asset_type,
                name=name,
                hostname=name,
                ip=ip,
                manufacturer="Ubiquiti",
                model=model,
                serial=serial,
                mac=mac,
                status=status,
                criticality="high",
                last_seen_at=OBSERVED_AT,
                tags=["unifi", "wifi" if asset_type == "access_point" else "network"],
                metadata={
                    "controllerVersion": "10.1.85",
                    "firmware": firmware,
                    "controllerState": state,
                    "clients": clients,
                    "uplinkName": uplink,
                    "uplinkPort": port,
                    "uplinkSpeedMbps": speed,
                    "uplinkRxErrors": rx_errors,
                    "observedAt": OBSERVED_AT.isoformat(),
                    "readOnly": True,
                },
            )
            assets[f"unifi:{name}"] = device_id

        for device in UNIFI_DEVICES:
            _, name, _, _, _, _, _, _, _, uplink, port, _, _ = device
            if uplink and f"unifi:{uplink}" in assets:
                relate(
                    conn,
                    tenant_id,
                    assets[f"unifi:{name}"],
                    assets[f"unifi:{uplink}"],
                    "connected_to",
                    "unifi",
                    {"uplinkPort": port},
                )

        upsert_asset(
            conn,
            tenant_id=tenant_id,
            sites=sites,
            networks=networks,
            source="ers_inventory",
            source_key="switch:192.168.200.223",
            asset_type="switch",
            name="SW-BORRACHARIA",
            site_code="SJP",
            ip="192.168.200.223",
            manufacturer="TP-Link",
            status="online",
            criticality="high",
            last_seen_at=OBSERVED_AT,
            tags=["switch", "read_only"],
            metadata={"observation": ping_observation, "inventoryStatus": "model_pending"},
        )
        upsert_asset(
            conn,
            tenant_id=tenant_id,
            sites=sites,
            networks=networks,
            source="ers_inventory",
            source_key="switch:10.1.1.221",
            asset_type="switch",
            name="SW-CISCO-PNG",
            site_code="PNG",
            ip="10.1.1.221",
            manufacturer="Cisco",
            status="online",
            criticality="high",
            last_seen_at=OBSERVED_AT,
            tags=["switch", "read_only"],
            metadata={"observation": ping_observation, "inventoryStatus": "model_pending"},
        )

        for provider, name, external_ref, adapter_type, endpoint in (
            ("docker_secret", "UniFi ERS", "unifi_controller", "unifi", "https://192.168.200.4:8443"),
            ("docker_secret", "Proxmox ERS", "proxmox_cluster", "proxmox", "https://192.168.200.20:8006"),
        ):
            credential_id = conn.execute(
                """
                insert into public.credential_references (
                  tenant_id, name, provider, external_ref, status, metadata
                )
                values (%s, %s, %s, %s, 'untested', %s)
                on conflict (tenant_id, provider, external_ref)
                do update set name = excluded.name,
                              metadata = public.credential_references.metadata || excluded.metadata
                returning id
                """,
                (tenant_id, name, provider, external_ref, Jsonb({"secretValuesStored": False, "runtimeSecretOnly": True})),
            ).fetchone()["id"]
            conn.execute(
                """
                insert into public.integration_instances (
                  tenant_id, credential_reference_id, adapter_type, name, enabled, read_only,
                  status, capabilities, sanitized_config, metadata
                )
                values (%s, %s, %s, %s, true, true, 'unconfigured', %s, %s, %s)
                on conflict (tenant_id, adapter_type, name)
                do update set credential_reference_id = excluded.credential_reference_id,
                              enabled = true, read_only = true,
                              capabilities = excluded.capabilities,
                              sanitized_config = excluded.sanitized_config,
                              metadata = public.integration_instances.metadata || excluded.metadata
                """,
                (
                    tenant_id,
                    credential_id,
                    adapter_type,
                    name,
                    ["inventory", "metrics", "health", "topology"],
                    Jsonb({"baseUrl": endpoint, "site": "default"} if adapter_type == "unifi" else {"baseUrl": endpoint}),
                    Jsonb({"mode": "read_only"}),
                ),
            )

        for wallboard_type, slug, name in (
            ("workforce", "ers-workforce", "Workforce ERS"),
            ("infrastructure", "ers-infrastructure", "Infraestrutura ERS"),
        ):
            profile_id = conn.execute(
                """
                insert into public.wallboard_profiles (
                  tenant_id, slug, name, wallboard_type, view_mode, enabled,
                  refresh_seconds, fullscreen, night_mode, burn_in_prevention,
                  show_clock, show_last_update, show_connection_status, config
                )
                values (%s, %s, %s, %s, 'overview', true, 30, true, true, true,
                        true, true, true, %s)
                on conflict (tenant_id, slug)
                do update set name = excluded.name, wallboard_type = excluded.wallboard_type,
                              enabled = true
                returning id
                """,
                (tenant_id, slug, name, wallboard_type, Jsonb({"privacyMode": "aggregate"})),
            ).fetchone()["id"]
            playlist_id = conn.execute(
                """
                insert into public.wallboard_playlists (
                  tenant_id, profile_id, slug, name, enabled, rotation_enabled,
                  default_duration_seconds, transition, alert_priority_enabled,
                  auto_return_seconds
                )
                values (%s, %s, %s, %s, true, true, 30, 'none', true, 120)
                on conflict (tenant_id, slug)
                do update set profile_id = excluded.profile_id, name = excluded.name,
                              enabled = true, rotation_enabled = true
                returning id
                """,
                (tenant_id, profile_id, f"{slug}-default", f"Rotação {name}"),
            ).fetchone()["id"]
            panels = (
                ("overview", "Visão geral", None),
                ("sjp", "Matriz SJP", sites["SJP"]),
                ("png", "Paranaguá", sites["PNG"]),
                ("az", "Armazém", sites["AZ"]),
            )
            for position, (panel_key, title, site_id) in enumerate(panels):
                conn.execute(
                    """
                    insert into public.wallboard_playlist_items (
                      tenant_id, playlist_id, site_id, panel_key, title, position,
                      duration_seconds, enabled
                    )
                    values (%s, %s, %s, %s, %s, %s, 30, true)
                    on conflict (tenant_id, playlist_id, position)
                    do update set site_id = excluded.site_id, panel_key = excluded.panel_key,
                                  title = excluded.title, enabled = true
                    """,
                    (tenant_id, playlist_id, site_id, panel_key, title, position),
                )

        conn.commit()
        counts = {}
        for table in (
            "sites",
            "infrastructure_networks",
            "infrastructure_assets",
            "asset_relationships",
            "wallboard_profiles",
            "wallboard_playlists",
            "wallboard_playlist_items",
            "integration_instances",
            "discovery_policies",
        ):
            counts[table] = conn.execute(
                f"select count(*) as count from public.{table} where tenant_id = %s",
                (tenant_id,),
            ).fetchone()["count"]
        return counts


if __name__ == "__main__":
    result = seed()
    print("ERS infrastructure seed completed:", ", ".join(f"{key}={value}" for key, value in result.items()))
