from __future__ import annotations

import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb


ROOT_DIR = Path(__file__).resolve().parents[1]
DEMO_TENANT_ID = UUID("00000000-0000-0000-0000-000000000301")
SEED_TAG = "vulcan-demo"


def load_env() -> None:
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


ROLES = {
    "admin": UUID("00000000-0000-0000-0000-000000100001"),
    "hierarchy": UUID("00000000-0000-0000-0000-000000100002"),
    "operator": UUID("00000000-0000-0000-0000-000000100003"),
}

DEPARTMENTS = {
    "operations": UUID("00000000-0000-0000-0000-000000200001"),
    "finance": UUID("00000000-0000-0000-0000-000000200002"),
    "support": UUID("00000000-0000-0000-0000-000000200003"),
    "logistics": UUID("00000000-0000-0000-0000-000000200004"),
    "executive": UUID("00000000-0000-0000-0000-000000200005"),
}

TEAMS = {
    "finance": UUID("00000000-0000-0000-0000-000000700001"),
    "operations": UUID("00000000-0000-0000-0000-000000700002"),
    "administrative": UUID("00000000-0000-0000-0000-000000700003"),
    "support": UUID("00000000-0000-0000-0000-000000700004"),
    "commercial": UUID("00000000-0000-0000-0000-000000700005"),
    "logistics": UUID("00000000-0000-0000-0000-000000700006"),
}

TEAM_BY_DEPARTMENT = {
    "executive": "administrative",
    "operations": "operations",
    "finance": "finance",
    "support": "support",
    "logistics": "logistics",
}

PEOPLE = [
    {
        "login": "teste",
        "password": "teste",
        "membership_id": UUID("00000000-0000-0000-0000-000000300005"),
        "user_id": UUID("00000000-0000-0000-0000-000000400005"),
        "manager_id": None,
        "role": "admin",
        "department": "executive",
        "name": "Root Demo Vulcan",
        "email": "teste@vulcan.local",
        "title": "Root Demo / Diretor",
        "level": 0,
        "phone": "+55 41 98416-6423",
    },
    {
        "login": "diretor",
        "password": "diretor",
        "membership_id": UUID("00000000-0000-0000-0000-000000300001"),
        "user_id": UUID("00000000-0000-0000-0000-000000400001"),
        "manager_id": UUID("00000000-0000-0000-0000-000000300005"),
        "role": "hierarchy",
        "department": "executive",
        "name": "Diretor Operacional",
        "email": "diretor@vulcan.local",
        "title": "Diretor",
        "level": 1,
        "phone": "+55 41 90000-0001",
    },
    {
        "login": "coordenador",
        "password": "coordenador",
        "membership_id": UUID("00000000-0000-0000-0000-000000300002"),
        "user_id": UUID("00000000-0000-0000-0000-000000400002"),
        "manager_id": UUID("00000000-0000-0000-0000-000000300001"),
        "role": "hierarchy",
        "department": "operations",
        "name": "Coordenador de Operações",
        "email": "coordenador@vulcan.local",
        "title": "Coordenador",
        "level": 2,
        "phone": "+55 41 90000-0002",
    },
    {
        "login": "gerente",
        "password": "gerente",
        "membership_id": UUID("00000000-0000-0000-0000-000000300003"),
        "user_id": UUID("00000000-0000-0000-0000-000000400003"),
        "manager_id": UUID("00000000-0000-0000-0000-000000300002"),
        "role": "hierarchy",
        "department": "finance",
        "name": "Gerente Financeiro",
        "email": "gerente@vulcan.local",
        "title": "Gerente",
        "level": 3,
        "phone": "+55 41 90000-0003",
    },
    {
        "login": "supervisor",
        "password": "supervisor",
        "membership_id": UUID("00000000-0000-0000-0000-000000300004"),
        "user_id": UUID("00000000-0000-0000-0000-000000400004"),
        "manager_id": UUID("00000000-0000-0000-0000-000000300003"),
        "role": "hierarchy",
        "department": "finance",
        "name": "Supervisor de Faturamento",
        "email": "supervisor@vulcan.local",
        "title": "Supervisor",
        "level": 4,
        "phone": "+55 41 90000-0004",
    },
    {
        "login": "lider",
        "password": "lider",
        "membership_id": UUID("00000000-0000-0000-0000-000000300008"),
        "user_id": UUID("00000000-0000-0000-0000-000000400008"),
        "manager_id": UUID("00000000-0000-0000-0000-000000300004"),
        "role": "hierarchy",
        "department": "operations",
        "name": "Líder Operacional",
        "email": "lider@vulcan.local",
        "title": "Líder",
        "level": 5,
        "phone": "+55 41 90000-0008",
    },
    {
        "login": "operador1",
        "password": "operador1",
        "membership_id": UUID("00000000-0000-0000-0000-000000300006"),
        "user_id": UUID("00000000-0000-0000-0000-000000400006"),
        "manager_id": UUID("00000000-0000-0000-0000-000000300008"),
        "role": "operator",
        "department": "operations",
        "name": "Operador 1",
        "email": "operador1@vulcan.local",
        "title": "Operador",
        "level": 6,
        "phone": "+55 41 90000-0006",
    },
    {
        "login": "operador2",
        "password": "operador2",
        "membership_id": UUID("00000000-0000-0000-0000-000000300007"),
        "user_id": UUID("00000000-0000-0000-0000-000000400007"),
        "manager_id": UUID("00000000-0000-0000-0000-000000300008"),
        "role": "operator",
        "department": "logistics",
        "name": "Operador 2",
        "email": "operador2@vulcan.local",
        "title": "Operador",
        "level": 6,
        "phone": "+55 41 90000-0007",
    },
    {
        "login": "operador3",
        "password": "operador3",
        "membership_id": UUID("00000000-0000-0000-0000-000000300009"),
        "user_id": UUID("00000000-0000-0000-0000-000000400009"),
        "manager_id": UUID("00000000-0000-0000-0000-000000300008"),
        "role": "operator",
        "department": "support",
        "name": "Operador 3",
        "email": "operador3@vulcan.local",
        "title": "Operador",
        "level": 6,
        "phone": "+55 41 90000-0009",
    },
]

DEVICES = [
    ("WIN-ADM-001", "Windows 11 Pro 23H2", "online", "high", 0, "teste"),
    ("MACBOOK-DIRETORIA-001", "macOS 15 Sequoia", "online", "high", 0, "diretor"),
    ("WIN-FIN-002", "Windows 11 Enterprise", "syncing", "high", 3, "gerente"),
    ("WIN-OPER-003", "Windows 11 Pro", "online", "medium", 0, "operador1"),
    ("LINUX-ALLAN-NB", "Zorin OS 17 / Linux 6.8", "online", "high", 1, "teste"),
    ("LINUX-SUPORTE-001", "Ubuntu 24.04 LTS", "offline", "low", 18, "operador3"),
    ("MACBOOK-GERENCIA-001", "macOS 14 Sonoma", "online", "medium", 0, "coordenador"),
    ("WIN-FAT-004", "Windows 11 Pro", "syncing", "medium", 7, "supervisor"),
    ("WIN-LIDER-005", "Windows 11 Pro", "online", "high", 0, "lider"),
    ("LINUX-LOG-002", "Ubuntu 22.04 LTS", "online", "medium", 2, "operador2"),
]

PENDING_DEVICES = [
    ("WIN-NOVO-001", "Windows 11 Enterprise", "pending", "medium", 0, "joao.silva", "10.30.9.21"),
    ("WIN-NOVO-002", "Windows 11 Pro", "pending", "high", 0, "maria.ops", "10.30.9.22"),
    ("LINUX-NOVO-001", "Ubuntu 24.04 LTS", "pending", "blocked_by_os", 4, "carlos.linux", "10.30.9.23"),
]

APP_PROFILES = {
    "finance": [
        ("ERP Billing", "erp/crm", "Faturamento - conferência de notas", 28),
        ("Excel", "productivity", "Planilha de conciliação financeira", 18),
        ("Outlook", "communication", "E-mail financeiro", 12),
        ("Sistema Financeiro", "business", "Aprovação de pagamentos", 16),
        ("WhatsApp Web", "communication", "Atendimento de exceções", 8),
    ],
    "operations": [
        ("Sistema Interno", "business", "Fila operacional", 22),
        ("ERP", "erp/crm", "Separação de pedidos", 20),
        ("Chrome", "browser", "Portal logístico", 13),
        ("Teams", "communication", "Alinhamento operacional", 8),
        ("Arquivos", "productivity", "Consulta de comprovantes", 6),
    ],
    "logistics": [
        ("Sistema Logístico", "business", "Roteirização", 24),
        ("ERP", "erp/crm", "Baixa de expedição", 18),
        ("WhatsApp Web", "communication", "Contato transportadora", 12),
        ("Chrome", "browser", "Rastreamento", 10),
    ],
    "support": [
        ("Support Desk", "business", "Fila de chamados", 24),
        ("Teams", "communication", "Triagem de suporte", 10),
        ("Chrome", "browser", "Base de conhecimento", 14),
        ("Terminal", "development", "Diagnóstico técnico", 9),
    ],
    "executive": [
        ("Dashboard Vulcan", "business", "Revisão executiva", 20),
        ("Outlook", "communication", "Comunicados executivos", 12),
        ("Excel", "productivity", "Indicadores consolidados", 10),
        ("Teams", "communication", "Reunião de performance", 8),
    ],
}


def ensure_auth_user(conn: psycopg.Connection, user_id: UUID, email: str, name: str, login: str) -> None:
    conn.execute("delete from auth.users where email = %s and id <> %s", (email, user_id))
    conn.execute(
        """
        insert into auth.users (
          id, aud, role, email, email_confirmed_at,
          raw_app_meta_data, raw_user_meta_data, is_sso_user, is_anonymous,
          created_at, updated_at
        )
        values (%s, 'authenticated', 'authenticated', %s, timezone('utc', now()),
                %s, %s, false, false, timezone('utc', now()), timezone('utc', now()))
        on conflict (id) do update
        set email = excluded.email,
            raw_user_meta_data = excluded.raw_user_meta_data,
            updated_at = timezone('utc', now())
        """,
        (user_id, email, Jsonb({}), Jsonb({"name": name, "login": login, "product": "Vulcan", "demo": True})),
    )
    conn.execute(
        """
        insert into public.user_profiles (user_id, primary_email, display_name, locale, timezone, metadata)
        values (%s, %s, %s, 'pt-BR', 'America/Sao_Paulo', %s)
        on conflict (user_id) do update
        set primary_email = excluded.primary_email,
            display_name = excluded.display_name,
            metadata = excluded.metadata,
            updated_at = timezone('utc', now())
        """,
        (user_id, email, name, Jsonb({"seed": SEED_TAG, "login": login})),
    )


def upsert_metric(
    conn: psycopg.Connection,
    membership_id: UUID,
    department_id: UUID,
    key: str,
    label: str,
    value: float,
    start: datetime,
    end: datetime,
    metadata: dict,
) -> None:
    conn.execute(
        """
        insert into public.operational_metrics (
          tenant_id, membership_id, department_id, metric_key, metric_label,
          value_numeric, period_start, period_end, metadata
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (DEMO_TENANT_ID, membership_id, department_id, key, label, value, start, end, Jsonb({"seed": SEED_TAG, **metadata})),
    )


def seed() -> None:
    load_env()
    database_url = require_env("DATABASE_URL")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    people_by_login = {person["login"]: person for person in PEOPLE}

    with psycopg.connect(database_url) as conn:
        conn.execute(
            """
            insert into public.tenants (id, slug, legal_name, display_name, status, country_code, timezone, plan, region, metadata)
            values (%s, 'vulcan-demo', 'Vulcan Demo Ltda', 'Vulcan Demo', 'active', 'BR', 'America/Sao_Paulo', 'commercial-demo', 'latam', %s)
            on conflict (id) do update
            set display_name = excluded.display_name,
                legal_name = excluded.legal_name,
                status = excluded.status,
                plan = excluded.plan,
                region = excluded.region,
                metadata = excluded.metadata,
                updated_at = timezone('utc', now())
            """,
            (DEMO_TENANT_ID, Jsonb({"seed": SEED_TAG, "mode": "commercial-demo", "demoMode": True})),
        )

        conn.execute(
            """
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
            )
            """
        )
        conn.execute(
            """
            create table if not exists public.team_members (
              id uuid primary key default gen_random_uuid(),
              tenant_id uuid not null references public.tenants (id) on delete cascade,
              team_id uuid not null references public.teams (id) on delete cascade,
              membership_id uuid not null references public.memberships (id) on delete cascade,
              role_in_team text not null default 'membro',
              created_at timestamptz not null default timezone('utc', now()),
              updated_at timestamptz not null default timezone('utc', now()),
              unique (tenant_id, team_id, membership_id)
            )
            """
        )

        role_rows = {
            "admin": ("tenant-admin", "Administrador do tenant", "tenant"),
            "hierarchy": ("gestor-hierarquico", "Gestor hierárquico", "hierarchy"),
            "operator": ("operador", "Operador individual", "self"),
        }
        for key, role_id in ROLES.items():
            slug, name, scope = role_rows[key]
            conn.execute(
                """
                insert into public.roles (id, tenant_id, slug, name, description, scope, is_system)
                values (%s, %s, %s, %s, %s, %s, true)
                on conflict (id) do update
                set name = excluded.name,
                    description = excluded.description,
                    slug = excluded.slug,
                    tenant_id = excluded.tenant_id,
                    scope = excluded.scope,
                    is_system = true,
                    updated_at = timezone('utc', now())
                """,
                (role_id, DEMO_TENANT_ID, slug, name, f"Perfil demo Vulcan: {name}", scope),
            )

        departments = {
            "executive": ("Diretoria", None),
            "operations": ("Operações", "executive"),
            "finance": ("Financeiro", "operations"),
            "logistics": ("Logística", "operations"),
            "support": ("Suporte", "operations"),
        }
        for key, (name, parent_key) in departments.items():
            conn.execute(
                """
                insert into public.departments (id, tenant_id, parent_department_id, name, slug, description, metadata)
                values (%s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do update
                set parent_department_id = excluded.parent_department_id,
                    tenant_id = excluded.tenant_id,
                    slug = excluded.slug,
                    name = excluded.name,
                    description = excluded.description,
                    metadata = excluded.metadata,
                    updated_at = timezone('utc', now())
                """,
                (
                    DEPARTMENTS[key],
                    DEMO_TENANT_ID,
                    DEPARTMENTS[parent_key] if parent_key else None,
                    name,
                    key,
                    f"Departamento demo: {name}",
                    Jsonb({"seed": SEED_TAG}),
                ),
            )

        for person in PEOPLE:
            ensure_auth_user(conn, person["user_id"], person["email"], person["name"], person["login"])

        for person in PEOPLE:
            conn.execute(
                """
                insert into public.memberships (
                  id, tenant_id, user_id, role_id, department_id, direct_manager_membership_id,
                  status, full_name, work_email, phone, whatsapp, title, hierarchy_level, joined_at, metadata
                )
                values (%s, %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s, %s, %s, timezone('utc', now()), %s)
                on conflict (id) do update
                set user_id = excluded.user_id,
                    role_id = excluded.role_id,
                    department_id = excluded.department_id,
                    direct_manager_membership_id = excluded.direct_manager_membership_id,
                    status = 'active',
                    full_name = excluded.full_name,
                    work_email = excluded.work_email,
                    phone = excluded.phone,
                    whatsapp = excluded.whatsapp,
                    title = excluded.title,
                    hierarchy_level = excluded.hierarchy_level,
                    metadata = excluded.metadata,
                    updated_at = timezone('utc', now())
                """,
                (
                    person["membership_id"],
                    DEMO_TENANT_ID,
                    person["user_id"],
                    ROLES[person["role"]],
                    DEPARTMENTS[person["department"]],
                    person["manager_id"],
                    person["name"],
                    person["email"],
                    person["phone"],
                    person["phone"],
                    person["title"],
                    person["level"],
                    Jsonb({"seed": SEED_TAG, "login": person["login"], "password": person["password"]}),
                ),
            )

        conn.execute("delete from public.vulcan_root_users where user_id = any(%s::uuid[])", ([person["user_id"] for person in PEOPLE],))
        conn.execute(
            "insert into public.vulcan_root_users (user_id) values (%s) on conflict do nothing",
            (people_by_login["teste"]["user_id"],),
        )
        conn.execute("select public.vulcan_refresh_membership_closure(%s)", (DEMO_TENANT_ID,))

        conn.execute("delete from public.notifications where tenant_id = %s and metadata ->> 'seed' = %s", (DEMO_TENANT_ID, SEED_TAG))
        conn.execute("delete from public.ai_insights where tenant_id = %s and metadata ->> 'seed' = %s", (DEMO_TENANT_ID, SEED_TAG))
        conn.execute("delete from public.operational_metrics where tenant_id = %s and metadata ->> 'seed' = %s", (DEMO_TENANT_ID, SEED_TAG))
        conn.execute("delete from public.activity_events where tenant_id = %s and metadata ->> 'seed' = %s", (DEMO_TENANT_ID, SEED_TAG))
        conn.execute("delete from public.devices where tenant_id = %s and metadata ->> 'seed' = %s", (DEMO_TENANT_ID, SEED_TAG))
        conn.execute(
            "delete from public.team_members where tenant_id = %s and team_id in (select id from public.teams where tenant_id = %s and metadata ->> 'seed' = %s)",
            (DEMO_TENANT_ID, DEMO_TENANT_ID, SEED_TAG),
        )
        conn.execute("delete from public.teams where tenant_id = %s and metadata ->> 'seed' = %s", (DEMO_TENANT_ID, SEED_TAG))

        team_rows = {
            "finance": ("Financeiro", "Contas, faturamento, conciliação e aprovação de pagamentos.", "#fb923c"),
            "operations": ("Operação", "Execução operacional, fila diária e processos repetitivos.", "#34d399"),
            "administrative": ("Administrativo", "Diretoria, backoffice e rotinas de governança.", "#facc15"),
            "support": ("Suporte", "Atendimento, chamados e suporte técnico interno.", "#60a5fa"),
            "commercial": ("Comercial", "Relacionamento, vendas e acompanhamento de oportunidades.", "#f472b6"),
            "logistics": ("Logística", "Expedição, roteirização e rastreio operacional.", "#a78bfa"),
        }
        for key, (name, description, color) in team_rows.items():
            conn.execute(
                """
                insert into public.teams (id, tenant_id, name, description, color, status, metadata)
                values (%s, %s, %s, %s, %s, 'active', %s)
                on conflict (id) do update
                set name = excluded.name,
                    description = excluded.description,
                    color = excluded.color,
                    status = 'active',
                    metadata = excluded.metadata,
                    updated_at = timezone('utc', now())
                """,
                (TEAMS[key], DEMO_TENANT_ID, name, description, color, Jsonb({"seed": SEED_TAG})),
            )

        for person in PEOPLE:
            team_key = TEAM_BY_DEPARTMENT.get(person["department"], "operations")
            conn.execute(
                """
                insert into public.team_members (tenant_id, team_id, membership_id, role_in_team)
                values (%s, %s, %s, %s)
                on conflict (tenant_id, team_id, membership_id) do update
                set role_in_team = excluded.role_in_team,
                    updated_at = timezone('utc', now())
                """,
                (
                    DEMO_TENANT_ID,
                    TEAMS[team_key],
                    person["membership_id"],
                    "gestor" if person["role"] in {"admin", "hierarchy"} else "membro",
                ),
            )

        for index, (hostname, os_name, status, quality, queue_depth, owner_login) in enumerate(DEVICES, start=1):
            owner = people_by_login[owner_login]
            team_id = TEAMS[TEAM_BY_DEPARTMENT.get(owner["department"], "operations")]
            device_id = UUID(f"00000000-0000-0000-0000-00000050{index:04d}")
            conn.execute(
                """
                insert into public.devices (id, tenant_id, owner_membership_id, hostname, os, device_fingerprint, status, last_seen_at, metadata)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do update
                set owner_membership_id = excluded.owner_membership_id,
                    tenant_id = excluded.tenant_id,
                    hostname = excluded.hostname,
                    os = excluded.os,
                    device_fingerprint = excluded.device_fingerprint,
                    status = excluded.status,
                    last_seen_at = excluded.last_seen_at,
                    metadata = excluded.metadata,
                    updated_at = timezone('utc', now())
                """,
                (
                    device_id,
                    DEMO_TENANT_ID,
                    owner["membership_id"],
                    hostname,
                    os_name,
                    f"vulcan-commercial-demo-{hostname.lower()}",
                    status,
                    now - timedelta(minutes=5 + index * 4) if status != "offline" else now - timedelta(hours=4 + index),
                    Jsonb(
                        {
                            "seed": SEED_TAG,
                            "source": "vulcan-demo-agent",
                            "agentVersion": "0.2.0",
                            "collectionQuality": quality,
                            "queueDepth": queue_depth,
                            "localIp": f"10.30.0.{20 + index}",
                            "department": owner["department"],
                            "linkedUser": owner_login,
                            "teamId": str(team_id),
                            "adoptionStatus": "adopted",
                        }
                    ),
                ),
            )

        for index, (hostname, os_name, status, quality, queue_depth, os_user, local_ip) in enumerate(PENDING_DEVICES, start=1):
            device_id = UUID(f"00000000-0000-0000-0000-00000059{index:04d}")
            conn.execute(
                """
                insert into public.devices (id, tenant_id, owner_membership_id, hostname, os, device_fingerprint, status, last_seen_at, metadata)
                values (%s, %s, null, %s, %s, %s, %s, %s, %s)
                on conflict (id) do update
                set owner_membership_id = null,
                    tenant_id = excluded.tenant_id,
                    hostname = excluded.hostname,
                    os = excluded.os,
                    device_fingerprint = excluded.device_fingerprint,
                    status = excluded.status,
                    last_seen_at = excluded.last_seen_at,
                    metadata = excluded.metadata,
                    updated_at = timezone('utc', now())
                """,
                (
                    device_id,
                    DEMO_TENANT_ID,
                    hostname,
                    os_name,
                    f"vulcan-pending-demo-{hostname.lower()}",
                    status,
                    now - timedelta(minutes=2 + index * 5),
                    Jsonb(
                        {
                            "seed": SEED_TAG,
                            "source": "vulcan-agent",
                            "agentVersion": "0.2.0",
                            "collectionQuality": quality,
                            "queueDepth": queue_depth,
                            "localIp": local_ip,
                            "osUser": os_user,
                            "linkedUser": os_user,
                            "adoptionStatus": "pending",
                            "adoptionCode": f"VLC-DEMO-{index}",
                            "privacyNotice": "O Vulcan mede fluxo operacional, não conteúdo pessoal.",
                        }
                    ),
                ),
            )

        devices_by_owner = {
            owner_login: UUID(f"00000000-0000-0000-0000-00000050{index:04d}")
            for index, (_, _, _, _, _, owner_login) in enumerate(DEVICES, start=1)
        }

        event_rows = []
        metric_rows = []
        event_counter = 1
        for day in range(30):
            day_start = datetime.combine((now - timedelta(days=day)).date(), time(8, 0), tzinfo=timezone.utc)
            for person in PEOPLE[1:]:
                profile = APP_PROFILES[person["department"]]
                device_id = devices_by_owner.get(person["login"]) or devices_by_owner.get("teste")
                for slot, (app_name, category, title, weight) in enumerate(profile):
                    start = day_start + timedelta(hours=slot * 1.35, minutes=(person["level"] * 7 + day * 3 + slot * 5) % 38)
                    duration = int((weight * 60) + ((day + slot + person["level"]) % 9) * 95)
                    if day < 3 and person["login"] == "operador2" and slot >= 2:
                        duration = int(duration * 0.62)
                    if person["login"] in {"gerente", "supervisor"} and app_name in {"Excel", "ERP Billing"}:
                        duration = int(duration * 1.28)
                    end = start + timedelta(seconds=duration)
                    event_id = f"demo-{event_counter:06d}"
                    event_rows.append(
                        (
                            DEMO_TENANT_ID,
                            person["membership_id"],
                            device_id,
                            "app_focus_ended",
                            app_name,
                            f"{title} - {person['name']}",
                            category,
                            duration,
                            start,
                            Jsonb({"provider": "llama", "confidence": 0.82 + (slot % 3) * 0.04, "category": category}),
                            Jsonb({"seed": SEED_TAG, "eventId": event_id, "endedAt": end.isoformat(), "demoPeriod": "30d"}),
                        )
                    )
                    metric_rows.append((DEMO_TENANT_ID, person["membership_id"], DEPARTMENTS[person["department"]], "app_usage_seconds", app_name, duration, start, end, Jsonb({"seed": SEED_TAG, "eventId": event_id, "category": category})))
                    metric_rows.append((DEMO_TENANT_ID, person["membership_id"], DEPARTMENTS[person["department"]], "active_seconds", "Tempo ativo", duration, start, end, Jsonb({"seed": SEED_TAG, "eventId": event_id, "category": category})))
                    event_counter += 1

                    if slot in {1, 3}:
                        switch_time = end + timedelta(minutes=2)
                        switch_id = f"demo-switch-{event_counter:06d}"
                        event_rows.append((DEMO_TENANT_ID, person["membership_id"], device_id, "context_switch", "Troca de contexto", None, "sistema", 0, switch_time, Jsonb({}), Jsonb({"seed": SEED_TAG, "eventId": switch_id, "fromApp": app_name})))
                        metric_rows.append((DEMO_TENANT_ID, person["membership_id"], DEPARTMENTS[person["department"]], "context_switch_count", "Trocas de contexto", 1, switch_time, switch_time, Jsonb({"seed": SEED_TAG, "eventId": switch_id})))
                        event_counter += 1

                idle_duration = 900 + ((person["level"] + day) % 5) * 420
                if person["login"] == "operador2" and day < 3:
                    idle_duration += 3600
                idle_start = day_start + timedelta(hours=7, minutes=(day * 11 + person["level"]) % 35)
                idle_end = idle_start + timedelta(seconds=idle_duration)
                idle_id = f"demo-idle-{event_counter:06d}"
                event_rows.append((DEMO_TENANT_ID, person["membership_id"], device_id, "idle_ended", "Sistema", None, "idle", idle_duration, idle_start, Jsonb({}), Jsonb({"seed": SEED_TAG, "eventId": idle_id, "endedAt": idle_end.isoformat()})))
                metric_rows.append((DEMO_TENANT_ID, person["membership_id"], DEPARTMENTS[person["department"]], "idle_seconds", "Tempo ocioso", idle_duration, idle_start, idle_end, Jsonb({"seed": SEED_TAG, "eventId": idle_id})))
                event_counter += 1

        with conn.cursor() as cursor:
            cursor.executemany(
                """
                insert into public.activity_events (
                  tenant_id, membership_id, device_id, event_type, app_name, window_title,
                  category, duration_seconds, occurred_at, llama_classification, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                event_rows,
            )
            cursor.executemany(
                """
                insert into public.operational_metrics (
                  tenant_id, membership_id, department_id, metric_key, metric_label,
                  value_numeric, period_start, period_end, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                metric_rows,
            )

        insights = [
            ("Bom bloco de foco individual no ERP", "low", "O Operador 1 manteve períodos longos sem troca de janela durante execução no ERP.", "Manter blocos de trabalho semelhantes e registrar interrupções recorrentes quando surgirem.", 3, "foco", "operations", "operador1"),
            ("Troca de contexto entre ERP e WhatsApp Web aumentou 32%", "high", "A equipe operacional alternou com frequência entre ERP, WhatsApp Web e sistema interno nos últimos 7 dias.", "Criar fila única de exceções e reduzir retorno manual entre canais.", 18, "bottleneck", "operations", "lider"),
            ("Financeiro concentra 41% do tempo em planilhas", "high", "Gerente e supervisor passam grande parte do tempo entre ERP Billing e Excel, indicando retrabalho de conferência.", "Automatizar validação de notas e conciliação antes do fechamento diário.", 27, "automation", "finance", "gerente"),
            ("Operador 2 com ociosidade elevada após 15h", "medium", "Nos últimos 3 dias, o Operador 2 teve aumento de períodos sem atividade no fim da tarde.", "Rebalancear fila logística e criar alerta preventivo de ociosidade por janela.", 9, "productivity", "logistics", "operador2"),
            ("Operador 3 com coleta limitada", "medium", "O agente do Operador 3 indica qualidade de coleta baixa por limitação do ambiente ou dependência local.", "Verificar serviço do agente e permissões do ambiente antes de comparar métricas individuais.", 4, "coleta_limitada", "support", "operador3"),
            ("ERP Billing concentra sessões longas", "critical", "Sessões longas no ERP Billing indicam gargalo de processo e dependência de validação manual.", "Priorizar automação de campos recorrentes e trilha de aprovação assistida.", 31, "bottleneck", "finance", "supervisor"),
            ("18 horas semanais de atividades repetitivas detectadas", "high", "A IA identificou padrão de baixa variação em rotinas administrativas e operacionais.", "Criar playbook de automação para tarefas repetitivas por setor.", 18, "automation", "operations", "coordenador"),
            ("Agente LINUX-SUPORTE-001 está offline", "medium", "Um dispositivo de suporte não sincroniza há mais de 8 horas.", "Verificar serviço local, rede e fila offline antes do próximo ciclo de atendimento.", 2, "agent", "support", "operador3"),
            ("Equipe de faturamento com risco de fila represada", "high", "Supervisor e líder concentram tempo em aprovações manuais, criando risco de atraso no fechamento.", "Definir responsável por triagem e automatizar validações recorrentes do faturamento.", 16, "risco_operacional", "finance", "supervisor"),
            ("Financeiro tem maior potencial de automação mensal", "high", "O conjunto ERP Billing, Excel e Sistema Financeiro concentra alto volume de repetição operacional.", "Priorizar uma automação piloto no fluxo de conciliação antes de expandir para outros setores.", 46, "economia_estimada", "finance", "diretor"),
            ("Estabilidade dos agentes precisa de atenção executiva", "medium", "Dispositivos offline e coleta limitada reduzem confiança nos indicadores consolidados.", "Criar rotina semanal de saúde dos agentes e alerta automático para filas locais.", 8, "relatorio_executivo", "executive", "teste"),
            ("Suporte apresentou tendência positiva de foco", "low", "A equipe de suporte reduziu alternância entre base de conhecimento e ferramenta de chamados.", "Manter o fluxo atual e transformar o padrão em referência para outros times.", 6, "tendencia_positiva", "support", "coordenador"),
        ]
        for title, impact, summary, recommendation, hours, insight_type, department_key, login in insights:
            severity = "critical" if impact == "critical" else "high" if impact == "high" else "medium" if impact == "medium" else "low"
            role_visibility = ["self"] if login.startswith("operador") else ["hierarchy", "tenant"]
            conn.execute(
                """
                insert into public.ai_insights (
                  tenant_id, membership_id, department_id, source_route, source_model,
                  title, summary, recommendation, impact, automation_savings_hours,
                  confidence, metadata, created_at
                )
                values (%s, %s, %s, 'gpt', %s, %s, %s, %s, %s, %s, 0.89, %s, %s)
                """,
                (
                    DEMO_TENANT_ID,
                    people_by_login[login]["membership_id"],
                    DEPARTMENTS[department_key],
                    os.environ.get("OPENAI_MODEL", "gpt-5.5"),
                    title,
                    summary,
                    recommendation,
                    impact,
                    hours,
                    Jsonb({
                        "seed": SEED_TAG,
                        "type": insight_type,
                        "scope": department_key,
                        "scopeType": "user" if login.startswith("operador") else "subtree" if login in {"lider", "supervisor", "gerente", "coordenador"} else "tenant",
                        "period": "últimos 7 dias",
                        "severity": severity,
                        "status": "open",
                        "diagnosis": summary,
                        "evidence": [
                            "Eventos operacionais consolidados dos últimos 7 dias",
                            f"Departamento: {department_key}",
                            f"Potencial estimado: {hours}h/mês",
                        ],
                        "metricsUsed": ["activity_events", "operational_metrics", "devices"],
                        "affectedUsers": [people_by_login[login]["name"]],
                        "affectedTeams": [TEAM_BY_DEPARTMENT.get(department_key, department_key)],
                        "roleVisibility": role_visibility,
                        "estimatedTimeLoss": hours,
                        "estimatedCostLoss": hours * 95,
                        "estimatedSavings": hours * 95,
                        "suggestedQuestions": [
                            "Por que isso aconteceu?",
                            "O que eu faço primeiro?",
                            "Quanto isso pode custar por mês?",
                            "Dá para automatizar esse processo?",
                        ],
                    }),
                    now - timedelta(hours=len(title) % 9),
                ),
            )

        notification_types = [
            "agente_offline",
            "agente_online",
            "fila_offline_alta",
            "falha_sincronizacao",
            "dispositivo_aguardando_adocao",
            "coleta_limitada",
            "gargalo_operacional",
            "ociosidade_elevada",
            "troca_contexto_excessiva",
            "queda_produtividade",
            "insight_critico",
            "insight_executivo",
            "oportunidade_automacao",
            "relatorio_diario",
            "relatorio_semanal",
            "relatorio_mensal",
            "falha_whatsapp",
            "falha_email",
            "falha_ia",
            "seguranca_lgpd",
            "usuario_sem_equipe",
            "usuario_sem_gestor",
            "metrica_fora_padrao",
            "acao_pendente",
            "acao_vencida",
        ]
        for person in PEOPLE:
            for channel in ["system", "email", "whatsapp", "windows"]:
                for notification_type in notification_types:
                    conn.execute(
                        """
                        insert into public.notification_preferences (tenant_id, membership_id, channel, notification_type, enabled, quiet_hours)
                        values (%s, %s, %s, %s, true, %s)
                        on conflict (tenant_id, membership_id, channel, notification_type) do update
                        set enabled = true, updated_at = timezone('utc', now())
                        """,
                        (
                            DEMO_TENANT_ID,
                            person["membership_id"],
                            channel,
                            notification_type,
                            Jsonb({
                                "start": "22:00",
                                "end": "07:00",
                                "timezone": "America/Sao_Paulo",
                                "frequency": "imediato" if notification_type in {"agente_offline", "insight_critico", "falha_sincronizacao", "falha_whatsapp", "falha_email"} else "resumo_diario",
                                "businessHoursOnly": notification_type not in {"insight_critico", "seguranca_lgpd"},
                            }),
                        ),
                    )

        notifications = [
            {
                "channel": "system",
                "db_status": "sent",
                "delivery": "delivered",
                "title": "Insight crítico gerado",
                "message": "Financeiro concentrou troca de contexto acima do normal entre ERP, Excel e WhatsApp Web.",
                "type": "insight_critico",
                "login": "gerente",
                "priority": "critico",
                "attempts": 1,
                "error": None,
            },
            {
                "channel": "whatsapp",
                "db_status": "missing_credentials",
                "delivery": "missing_credentials",
                "title": "WhatsApp pendente de credencial",
                "message": "Canal raiz Vulcan está configurado no produto, mas ainda precisa de token/provedor para envio real.",
                "type": "falha_whatsapp",
                "login": "teste",
                "priority": "alto",
                "attempts": 1,
                "error": "WHATSAPP_ACCESS_TOKEN não configurado",
            },
            {
                "channel": "email",
                "db_status": "queued",
                "delivery": "queued",
                "title": "Resumo operacional diário",
                "message": "Resumo executivo pronto para envio aos gestores às 08:00.",
                "type": "relatorio_diario",
                "login": "coordenador",
                "priority": "informativo",
                "attempts": 0,
                "error": None,
            },
            {
                "channel": "windows",
                "db_status": "mocked",
                "delivery": "mocked",
                "title": "Agente requer atenção",
                "message": "LINUX-SUPORTE-001 acumulou fila offline e precisa validar conectividade.",
                "type": "fila_offline_alta",
                "login": "operador3",
                "priority": "alto",
                "attempts": 0,
                "error": None,
            },
            {
                "channel": "system",
                "db_status": "sent",
                "delivery": "sent",
                "title": "Dispositivo aguardando adoção",
                "message": "WIN-NOVO-001 apareceu na rede e precisa ser vinculado a usuário/equipe.",
                "type": "dispositivo_aguardando_adocao",
                "login": "teste",
                "priority": "medio",
                "attempts": 1,
                "error": None,
            },
            {
                "channel": "email",
                "db_status": "failed",
                "delivery": "failed",
                "title": "Falha no envio de e-mail",
                "message": "SMTP ainda não possui credenciais válidas para envio de relatório semanal.",
                "type": "falha_email",
                "login": "teste",
                "priority": "alto",
                "attempts": 3,
                "error": "SMTP_HOST/SMTP_PASS ausentes",
            },
            {
                "channel": "system",
                "db_status": "queued",
                "delivery": "retrying",
                "title": "Ação operacional vencendo",
                "message": "Plano de ação do gargalo no faturamento vence hoje e aguarda retorno do supervisor.",
                "type": "acao_pendente",
                "login": "supervisor",
                "priority": "medio",
                "attempts": 2,
                "error": None,
            },
            {
                "channel": "whatsapp",
                "db_status": "mocked",
                "delivery": "mocked",
                "title": "Simulação WhatsApp: automação sugerida",
                "message": "Automação de conferência recorrente pode economizar 34h/mês no Financeiro.",
                "type": "oportunidade_automacao",
                "login": "diretor",
                "priority": "alto",
                "attempts": 1,
                "error": None,
            },
        ]
        for index, item in enumerate(notifications, start=1):
            sent_at = now - timedelta(minutes=index * 9) if item["db_status"] in {"sent", "mocked"} else None
            conn.execute(
                """
                insert into public.notifications (
                  tenant_id, recipient_membership_id, channel, notification_type,
                  status, title, message, provider, sent_at, metadata, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, 'vulcan-demo', %s, %s, %s)
                """,
                (
                    DEMO_TENANT_ID,
                    people_by_login[item["login"]]["membership_id"],
                    item["channel"],
                    item["type"],
                    item["db_status"],
                    item["title"],
                    item["message"],
                    sent_at,
                    Jsonb({"seed": SEED_TAG}),
                    now - timedelta(minutes=index * 12),
                ),
            )

        for index, item in enumerate(notifications, start=1):
            conn.execute(
                """
                update public.notifications
                set metadata = metadata || %s
                where tenant_id = %s
                  and title = %s
                  and metadata ->> 'seed' = %s
                """,
                (
                    Jsonb({
                        "priority": item["priority"],
                        "deliveryStatus": item["delivery"],
                        "attempts": item["attempts"],
                        "maxAttempts": 3,
                        "lastError": item["error"],
                        "requiresAck": item["priority"] in {"alto", "critico"},
                        "scheduledFor": (now + timedelta(hours=2)).isoformat() if item["delivery"] == "queued" else None,
                        "readAt": (now - timedelta(minutes=4)).isoformat() if item["delivery"] in {"sent", "delivered"} else None,
                        "resolvedAt": None,
                        "actionUrl": "http://localhost:3002",
                    }),
                    DEMO_TENANT_ID,
                    item["title"],
                    SEED_TAG,
                ),
            )

        notification_schedules = [
            {
                "name": "Resumo operacional diário",
                "recurrence": "diário",
                "timezone": "America/Sao_Paulo",
                "daysOfWeek": ["seg", "ter", "qua", "qui", "sex"],
                "times": ["08:00"],
                "reportType": "daily",
                "recipients": ["diretor", "coordenador", "gerente"],
                "channels": ["system", "email"],
                "enabled": True,
            },
            {
                "name": "Alertas críticos em tempo real",
                "recurrence": "imediato",
                "timezone": "America/Sao_Paulo",
                "daysOfWeek": [],
                "times": ["tempo real"],
                "reportType": "critical",
                "recipients": ["gestores no escopo"],
                "channels": ["system", "whatsapp"],
                "enabled": True,
            },
            {
                "name": "Relatório executivo semanal",
                "recurrence": "semanal",
                "timezone": "America/Sao_Paulo",
                "daysOfWeek": ["seg"],
                "times": ["07:30"],
                "reportType": "weekly",
                "recipients": ["diretoria"],
                "channels": ["email"],
                "enabled": True,
            },
        ]
        for schedule in notification_schedules:
            conn.execute(
                """
                insert into public.notifications (
                  tenant_id, recipient_membership_id, channel, notification_type,
                  status, title, message, provider, metadata, created_at
                )
                values (%s, %s, 'system', 'schedule_config', %s, %s, %s, 'vulcan-scheduler', %s, %s)
                """,
                (
                    DEMO_TENANT_ID,
                    people_by_login["teste"]["membership_id"],
                    "queued" if schedule["enabled"] else "disabled",
                    schedule["name"],
                    f"Agendamento {schedule['recurrence']} configurado para {', '.join(schedule['channels'])}.",
                    Jsonb({**schedule, "seed": SEED_TAG, "deliveryStatus": "queued", "priority": "informativo"}),
                    now - timedelta(minutes=5),
                ),
            )

        for provider, purpose, model, base_url in [
            ("ollama", "operational", os.environ.get("LLAMA_MODEL", "llama3.1"), os.environ.get("LLAMA_BASE_URL", "http://localhost:11434/v1")),
            ("openai", "executive", os.environ.get("OPENAI_MODEL", "gpt-5.5"), None),
            ("openai", "copilot", os.environ.get("OPENAI_MODEL", "gpt-5.5"), None),
        ]:
            conn.execute(
                """
                insert into public.ai_provider_configs (tenant_id, provider, purpose, model, base_url, secret_ref, enabled, metadata)
                values (%s, %s, %s, %s, %s, %s, true, %s)
                on conflict do nothing
                """,
                (DEMO_TENANT_ID, provider, purpose, model, base_url, f"{provider.upper()}_API_KEY", Jsonb({"seed": SEED_TAG})),
            )

        conn.execute(
            """
            insert into public.audit_logs (
              tenant_id, actor_user_id, action,
              entity_table, change_summary,
              resource_type, metadata
            )
            values (%s, %s, 'seed.demo.completed', 'seed', %s, 'seed', %s)
            """,
            (DEMO_TENANT_ID, people_by_login["teste"]["user_id"], Jsonb({"seed": SEED_TAG, "people": len(PEOPLE), "devices": len(DEVICES) + len(PENDING_DEVICES), "teams": len(TEAMS), "events": event_counter - 1}), Jsonb({"seed": SEED_TAG})),
        )

        conn.commit()

    print("Vulcan commercial demo seed completed")
    print("Local demo users:")
    for person in PEOPLE:
        print(f"- {person['login']} / {person['password']} ({person['email']})")


if __name__ == "__main__":
    seed()
