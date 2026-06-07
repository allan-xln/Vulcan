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

        for index, (hostname, os_name, status, quality, queue_depth, owner_login) in enumerate(DEVICES, start=1):
            owner = people_by_login[owner_login]
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
            ("Troca de contexto entre ERP e WhatsApp Web aumentou 32%", "high", "A equipe operacional alternou com frequência entre ERP, WhatsApp Web e sistema interno nos últimos 7 dias.", "Criar fila única de exceções e reduzir retorno manual entre canais.", 18, "bottleneck", "operations", "lider"),
            ("Financeiro concentra 41% do tempo em planilhas", "high", "Gerente e supervisor passam grande parte do tempo entre ERP Billing e Excel, indicando retrabalho de conferência.", "Automatizar validação de notas e conciliação antes do fechamento diário.", 27, "automation", "finance", "gerente"),
            ("Operador 2 com ociosidade elevada após 15h", "medium", "Nos últimos 3 dias, o Operador 2 teve aumento de períodos sem atividade no fim da tarde.", "Rebalancear fila logística e criar alerta preventivo de ociosidade por janela.", 9, "productivity", "logistics", "operador2"),
            ("ERP Billing concentra sessões longas", "critical", "Sessões longas no ERP Billing indicam gargalo de processo e dependência de validação manual.", "Priorizar automação de campos recorrentes e trilha de aprovação assistida.", 31, "bottleneck", "finance", "supervisor"),
            ("18 horas semanais de atividades repetitivas detectadas", "high", "A IA identificou padrão de baixa variação em rotinas administrativas e operacionais.", "Criar playbook de automação para tarefas repetitivas por setor.", 18, "automation", "operations", "coordenador"),
            ("Agente LINUX-SUPORTE-001 está offline", "medium", "Um dispositivo de suporte não sincroniza há mais de 8 horas.", "Verificar serviço local, rede e fila offline antes do próximo ciclo de atendimento.", 2, "agent", "support", "operador3"),
        ]
        for title, impact, summary, recommendation, hours, insight_type, department_key, login in insights:
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
                    Jsonb({"seed": SEED_TAG, "type": insight_type, "scope": department_key, "period": "últimos 7 dias"}),
                    now - timedelta(hours=len(title) % 9),
                ),
            )

        notification_types = [
            "resumo_diario",
            "resumo_semanal",
            "gargalo_detectado",
            "oportunidade_automacao",
            "queda_produtividade",
            "anomalia_operacional",
            "insight_executivo",
            "alerta_critico",
            "agente_offline",
            "agente_online",
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
                        (DEMO_TENANT_ID, person["membership_id"], channel, notification_type, Jsonb({"start": "22:00", "end": "07:00"})),
                    )

        notifications = [
            ("system", "sent", "Gargalo detectado", "ERP Billing concentrou sessões longas no Financeiro.", "gargalo_detectado", "gerente"),
            ("whatsapp", "missing_credentials", "Insight executivo", "18 horas semanais de automação potencial foram detectadas.", "insight_executivo", "diretor"),
            ("email", "queued", "Resumo operacional diário", "Resumo pronto para envio aos gestores.", "resumo_diario", "coordenador"),
            ("windows", "mocked", "Agente offline", "LINUX-SUPORTE-001 está sem sincronização recente.", "agente_offline", "operador3"),
            ("system", "sent", "Queda de produtividade", "Operador 2 apresentou aumento de ociosidade após 15h.", "queda_produtividade", "supervisor"),
        ]
        for index, (channel, status, title, message, notification_type, login) in enumerate(notifications, start=1):
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
                    people_by_login[login]["membership_id"],
                    channel,
                    notification_type,
                    status,
                    title,
                    message,
                    now - timedelta(minutes=index * 9) if status == "sent" else None,
                    Jsonb({"seed": SEED_TAG, "attempts": 1 if status in {"queued", "missing_credentials"} else 0}),
                    now - timedelta(minutes=index * 12),
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
            (DEMO_TENANT_ID, people_by_login["teste"]["user_id"], Jsonb({"seed": SEED_TAG, "people": len(PEOPLE), "devices": len(DEVICES), "events": event_counter - 1}), Jsonb({"seed": SEED_TAG})),
        )

        conn.commit()

    print("Vulcan commercial demo seed completed")
    print("Local demo users:")
    for person in PEOPLE:
        print(f"- {person['login']} / {person['password']} ({person['email']})")


if __name__ == "__main__":
    seed()
