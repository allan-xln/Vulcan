from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


ROOT_DIR = Path(__file__).resolve().parents[1]
TENANT_ID = UUID(os.getenv("ERS_TENANT_ID", "00000000-0000-0000-0000-000000000301"))
ERS_DEPARTMENT_ID = UUID(os.getenv("ERS_DEPARTMENT_ID", "00000000-0000-0000-0000-000000200101"))

SJP_SECTORS = [
    ("TI", "ti"),
    ("RH", "rh"),
    ("Comercial", "comercial"),
    ("Qualidade", "qualidade"),
    ("Compras", "compras"),
    ("Financeiro", "financeiro"),
    ("Operacional", "operacao"),
    ("Rastreamento", "rastreamento"),
    ("Armazém", "armazem"),
    ("Borracharia", "borracharia"),
    ("Almoxarifado", "almoxarifado"),
    ("Frota", "frota"),
    ("Manutenção", "manutencao"),
    ("Abastecimento", "abastecimento"),
    ("Sinistros", "sinistros"),
]

BRANCHES = [
    {
        "name": "SJP - Matriz",
        "slug": "sjp-matriz",
        "description": "Matriz de Sao Jose dos Pinhais. Setores principais da ERS.",
        "metadata": {"type": "branch", "unit": "SJP", "city": "Sao Jose dos Pinhais", "branchScope": True},
    },
    {
        "name": "Paranaguá - Filial",
        "slug": "paranagua-filial",
        "description": "Filial operacional de Paranagua.",
        "metadata": {"type": "branch", "unit": "Paranagua", "city": "Paranagua", "branchScope": True},
    },
    {
        "name": "Paranaguá - Armazém",
        "slug": "paranagua-armazem",
        "description": "Unidade de armazem em Paranagua, separada da filial operacional.",
        "metadata": {"type": "warehouse_branch", "unit": "Paranagua Armazem", "city": "Paranagua", "branchScope": True},
    },
]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def database_url() -> str:
    load_env_file(ROOT_DIR / "docker" / ".env")
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    password = quote(os.getenv("POSTGRES_PASSWORD", "postgres"), safe="")
    host = os.getenv("VULCAN_BIND_HOST", "127.0.0.1")
    if host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"
    port = os.getenv("VULCAN_DB_PORT", "55432")
    return f"postgresql://postgres:{password}@{host}:{port}/vulcan"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return normalized or "departamento"


def upsert_department(conn: psycopg.Connection, *, department_id: UUID | None, parent_id: UUID | None, name: str, slug: str, description: str, metadata: dict) -> dict:
    payload = {
        "source": "seed_ers_structure",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    if department_id:
        row = conn.execute(
            """
            insert into public.departments (id, tenant_id, parent_department_id, name, slug, description, metadata)
            values (%s, %s, %s, %s, %s, %s, %s)
            on conflict (id) do update
            set tenant_id = excluded.tenant_id,
                parent_department_id = excluded.parent_department_id,
                name = excluded.name,
                slug = excluded.slug,
                description = excluded.description,
                metadata = coalesce(public.departments.metadata, '{}'::jsonb) || excluded.metadata,
                updated_at = timezone('utc', now())
            returning id, name, slug, parent_department_id
            """,
            (department_id, TENANT_ID, parent_id, name, slug, description, Jsonb(payload)),
        ).fetchone()
    else:
        row = conn.execute(
            """
            insert into public.departments (tenant_id, parent_department_id, name, slug, description, metadata)
            values (%s, %s, %s, %s, %s, %s)
            on conflict (tenant_id, slug) do update
            set parent_department_id = excluded.parent_department_id,
                name = excluded.name,
                description = excluded.description,
                metadata = coalesce(public.departments.metadata, '{}'::jsonb) || excluded.metadata,
                updated_at = timezone('utc', now())
            returning id, name, slug, parent_department_id
            """,
            (TENANT_ID, parent_id, name, slug, description, Jsonb(payload)),
        ).fetchone()
    return dict(row)


def main() -> None:
    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        conn.execute(
            """
            insert into public.tenants (id, slug, legal_name, display_name, region, plan, status, metadata)
            values (%s, 'ers-transportes', 'ERS Transportes', 'ERS Transportes', 'BR', 'pilot', 'active', %s)
            on conflict (id) do update
            set slug = excluded.slug,
                legal_name = excluded.legal_name,
                display_name = excluded.display_name,
                region = excluded.region,
                plan = excluded.plan,
                status = excluded.status,
                metadata = coalesce(public.tenants.metadata, '{}'::jsonb) || excluded.metadata,
                updated_at = timezone('utc', now())
            """,
            (TENANT_ID, Jsonb({"customer": "ERS", "structure": "branch_department_tree", "updatedBy": "seed_ers_structure"})),
        )

        root = upsert_department(
            conn,
            department_id=ERS_DEPARTMENT_ID,
            parent_id=None,
            name="ERS",
            slug="ers",
            description="Raiz da estrutura ERS. Abaixo dela ficam unidades, filiais e setores.",
            metadata={"type": "company_root", "branchAware": True},
        )

        branch_rows: dict[str, dict] = {}
        for branch in BRANCHES:
            branch_rows[branch["slug"]] = upsert_department(
                conn,
                department_id=None,
                parent_id=root["id"],
                name=branch["name"],
                slug=branch["slug"],
                description=branch["description"],
                metadata=branch["metadata"],
            )

        sjp_id = branch_rows["sjp-matriz"]["id"]
        sector_rows = []
        for name, slug in SJP_SECTORS:
            sector_rows.append(
                upsert_department(
                    conn,
                    department_id=None,
                    parent_id=sjp_id,
                    name=name,
                    slug=slugify(slug),
                    description=f"Setor {name} da matriz SJP.",
                    metadata={"type": "department", "unit": "SJP", "branchSlug": "sjp-matriz"},
                )
            )

        conn.commit()

    print(
        json.dumps(
            {
                "tenantId": str(TENANT_ID),
                "root": root["name"],
                "branches": [item["name"] for item in branch_rows.values()],
                "sjpSectors": [item["name"] for item in sector_rows],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
