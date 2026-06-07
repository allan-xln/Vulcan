from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

TENANT_ID = UUID("00000000-0000-0000-0000-000000000301")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


TENANTS = [
    {
        "id": TENANT_ID,
        "name": "ACME Operações",
        "slug": "acme-ops",
        "plan": "Growth",
        "region": "US",
        "status": "active",
    }
]

USERS = [
    {
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "tenantId": TENANT_ID,
        "name": "Vulcan Local Admin",
        "email": "admin@vulcan.local",
        "phone": "+1 555 0100",
        "whatsapp": "+1 555 0100",
        "title": "Tenant Admin",
        "hierarchyLevel": 0,
        "managerId": None,
        "role": "owner",
        "status": "active",
    },
    {
        "id": UUID("22222222-2222-2222-2222-222222222222"),
        "tenantId": TENANT_ID,
        "name": "Líder Financeiro",
        "email": "finance@acme.example",
        "phone": "+1 555 0101",
        "whatsapp": "+1 555 0101",
        "title": "Supervisor Financeiro",
        "hierarchyLevel": 2,
        "managerId": UUID("11111111-1111-1111-1111-111111111111"),
        "role": "manager",
        "status": "active",
    },
]

HIERARCHY = [
    {
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "tenantId": TENANT_ID,
        "userId": UUID("11111111-1111-1111-1111-111111111111"),
        "parentId": None,
        "name": "Vulcan Local Admin",
        "title": "Tenant Admin",
        "department": "Operações Executivas",
        "email": "admin@vulcan.local",
        "phone": "+1 555 0100",
        "whatsapp": "+1 555 0100",
        "hierarchyLevel": 0,
        "directReports": 2,
        "visibleScope": "tenant",
    },
    {
        "id": UUID("22222222-2222-2222-2222-222222222222"),
        "tenantId": TENANT_ID,
        "userId": UUID("22222222-2222-2222-2222-222222222222"),
        "parentId": UUID("11111111-1111-1111-1111-111111111111"),
        "name": "Líder Financeiro",
        "title": "Supervisor Financeiro",
        "department": "Financeiro",
        "email": "finance@acme.example",
        "phone": "+1 555 0101",
        "whatsapp": "+1 555 0101",
        "hierarchyLevel": 2,
        "directReports": 1,
        "visibleScope": "subtree",
    },
    {
        "id": UUID("33333333-3333-3333-3333-333333333333"),
        "tenantId": TENANT_ID,
        "userId": UUID("33333333-3333-3333-3333-333333333333"),
        "parentId": UUID("22222222-2222-2222-2222-222222222222"),
        "name": "Billing Operator",
        "title": "Billing Analyst",
        "department": "Financeiro",
        "email": "billing@acme.example",
        "phone": "+1 555 0102",
        "whatsapp": "+1 555 0102",
        "hierarchyLevel": 3,
        "directReports": 0,
        "visibleScope": "self",
    },
]

DEVICES = [
    {
        "id": UUID("00000000-0000-0000-0000-000000000901"),
        "tenantId": TENANT_ID,
        "owner": "Líder Financeiro",
        "hostname": "ACME-FIN-042",
        "os": "Windows 11",
        "status": "online",
        "lastSeenAt": "2026-06-02T21:45:00Z",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000902"),
        "tenantId": TENANT_ID,
        "owner": "Mesa de Operações",
        "hostname": "ACME-OPS-119",
        "os": "Windows 11",
        "status": "syncing",
        "lastSeenAt": "2026-06-02T21:41:00Z",
    },
]

ACTIVITY_EVENTS = [
    {
        "id": UUID("20000000-0000-0000-0000-000000000001"),
        "tenantId": TENANT_ID,
        "eventType": "foreground_application_change",
        "appName": "ERP Billing",
        "department": "Financeiro",
        "occurredAt": "2026-06-02T18:10:00Z",
        "durationMinutes": 84,
    },
    {
        "id": UUID("20000000-0000-0000-0000-000000000002"),
        "tenantId": TENANT_ID,
        "eventType": "context_switch_cluster",
        "appName": "Planilhas + E-mail",
        "department": "Financeiro",
        "occurredAt": "2026-06-02T19:00:00Z",
        "durationMinutes": 47,
    },
    {
        "id": UUID("20000000-0000-0000-0000-000000000003"),
        "tenantId": TENANT_ID,
        "eventType": "workflow_delay",
        "appName": "Portal de Compras",
        "department": "Operações",
        "occurredAt": "2026-06-02T20:05:00Z",
        "durationMinutes": 36,
    },
]

METRICS = [
    {"id": "active-users", "label": "Usuários ativos", "value": "148", "trend": "+12% vs ontem", "tone": "positive"},
    {"id": "events", "label": "Eventos processados", "value": "42,8 mil", "trend": "+8,4% em 24h", "tone": "neutral"},
    {"id": "bottlenecks", "label": "Gargalos detectados", "value": "17", "trend": "5 críticos", "tone": "warning"},
    {"id": "insights", "label": "Insights de IA", "value": "63", "trend": "11 de alto impacto", "tone": "positive"},
    {"id": "automation", "label": "Potencial de automação", "value": "219h", "trend": "estimativa mensal", "tone": "critical"},
]

INSIGHTS = [
    {
        "id": "ins-001",
        "title": "Ciclo de faturamento financeiro está desacelerando",
        "impact": "high",
        "summary": "O tempo médio do fluxo de faturamento aumentou 38% nas últimas 24 horas, concentrado no ERP e em repasses por planilha.",
        "recommendation": "Priorize automação de validação de notas e reduza redigitação entre planilhas e ERP.",
        "automationSavingsHours": 27,
    },
    {
        "id": "ins-002",
        "title": "Troca de contexto está criando retrabalho oculto",
        "impact": "medium",
        "summary": "Usuários financeiros alternaram entre e-mail, planilhas e telas do ERP 420 vezes no último dia útil.",
        "recommendation": "Crie uma fila guiada para exceções e consolide checagens de status no fluxo do ERP.",
        "automationSavingsHours": 14,
    },
    {
        "id": "ins-003",
        "title": "Aprovações de compras formam fila recorrente",
        "impact": "high",
        "summary": "As janelas de espera por aprovação se concentram no fim da tarde e atrasam etapas operacionais posteriores.",
        "recommendation": "Implemente escalonamento automático e uma janela diária de 15 minutos para aprovações.",
        "automationSavingsHours": 19,
    },
]

NOTIFICATIONS = [
    {
        "id": "ntf-001",
        "channel": "windows",
        "status": "mocked",
        "title": "Alerta Vulcan",
        "message": "O setor financeiro apresentou aumento de 38% no tempo médio do processo de faturamento nas últimas 24 horas.",
        "createdAt": now_iso(),
    },
    {
        "id": "ntf-002",
        "channel": "whatsapp",
        "status": "missing_credentials",
        "title": "Insight Vulcan",
        "message": "Foram identificadas aproximadamente 1.200 tarefas repetitivas nesta semana. Potencial estimado: 27 horas mensais.",
        "createdAt": now_iso(),
    },
    {
        "id": "ntf-003",
        "channel": "email",
        "status": "missing_credentials",
        "title": "Resumo executivo semanal",
        "message": "Resumo semanal preparado para gestores com gargalos, oportunidades e recomendações.",
        "createdAt": now_iso(),
    },
]
