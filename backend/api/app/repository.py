from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from io import StringIO
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings, get_settings
from app.data import ACTIVITY_EVENTS, DEVICES, HIERARCHY, INSIGHTS, METRICS, NOTIFICATIONS, TENANTS, USERS
from app.schemas import (
    ActivityEventCreate,
    ActivityEventCreateResponse,
    AgentEnrollRequest,
    AgentEnrollResponse,
    AgentEventsRequest,
    AgentEventsResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentLogsRequest,
    DepartmentCreate,
    DeviceAdoptionRequest,
    DeviceMoveRequest,
    DeviceOwnerUpdate,
    MembershipCreate,
    MembershipUpdate,
    NotificationScheduleCreate,
    NotificationSendRequest,
    NotificationSendResponse,
    RootWhatsAppSendRequest,
    RoleCreate,
    SettingsSectionUpdate,
    TeamCreate,
    TeamMemberCreate,
    TeamUpdate,
)
from app.security import AuthContext


DEMO_TEST_MEMBERSHIP_ID = UUID("00000000-0000-0000-0000-000000300005")
DEMO_TENANT_ID = UUID("00000000-0000-0000-0000-000000000301")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug or uuid4().hex[:8]


NOTIFICATION_TYPES: list[dict] = [
    {"id": "agente_offline", "name": "Agente offline", "description": "Dispositivo ficou sem sincronizar acima do limite.", "defaultPriority": "alto", "allowedChannels": ["system", "whatsapp", "email", "windows"], "defaultAudience": "supervisor_ti", "defaultFrequency": "imediato", "template": "{{dispositivo}} ficou offline há {{periodo}}.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "agente_online", "name": "Agente online novamente", "description": "Dispositivo voltou a sincronizar.", "defaultPriority": "baixo", "allowedChannels": ["system", "windows"], "defaultAudience": "responsavel_dispositivo", "defaultFrequency": "imediato", "template": "{{dispositivo}} voltou a sincronizar.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "fila_offline_alta", "name": "Fila offline alta", "description": "Fila local do agente cresceu e pode atrasar métricas.", "defaultPriority": "alto", "allowedChannels": ["system", "whatsapp", "email", "windows"], "defaultAudience": "admin_ti", "defaultFrequency": "imediato", "template": "{{dispositivo}} acumulou {{valor}} eventos pendentes.", "canDisable": True, "requiresPermission": True, "critical": True},
    {"id": "falha_sincronizacao", "name": "Falha de sincronização", "description": "Agente ou backend recusou lote de eventos.", "defaultPriority": "alto", "allowedChannels": ["system", "email", "windows"], "defaultAudience": "admin_ti", "defaultFrequency": "imediato", "template": "Falha de sincronização em {{dispositivo}}: {{erro}}.", "canDisable": True, "requiresPermission": True, "critical": True},
    {"id": "dispositivo_aguardando_adocao", "name": "Dispositivo aguardando adoção", "description": "Novo dispositivo apareceu sem vínculo final.", "defaultPriority": "medio", "allowedChannels": ["system", "email"], "defaultAudience": "admin_operacional", "defaultFrequency": "imediato", "template": "{{dispositivo}} está aguardando adoção no Vulcan.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "coleta_limitada", "name": "Coleta limitada", "description": "Sistema operacional limitou visibilidade do agente.", "defaultPriority": "medio", "allowedChannels": ["system", "windows", "email"], "defaultAudience": "admin_ti", "defaultFrequency": "diario", "template": "{{dispositivo}} está com coleta {{qualidade}}.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "gargalo_operacional", "name": "Gargalo operacional", "description": "Processo ou app concentrou tempo fora do padrão.", "defaultPriority": "alto", "allowedChannels": ["system", "whatsapp", "email"], "defaultAudience": "gestor_subarvore", "defaultFrequency": "imediato", "template": "{{equipe}} tem gargalo em {{metrica}}.", "canDisable": True, "requiresPermission": True, "critical": True},
    {"id": "ociosidade_elevada", "name": "Ociosidade elevada", "description": "Ociosidade acima do limite configurado.", "defaultPriority": "medio", "allowedChannels": ["system", "email"], "defaultAudience": "supervisor", "defaultFrequency": "a_cada_4_horas", "template": "{{equipe}} apresentou ociosidade de {{valor}}.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "troca_contexto_excessiva", "name": "Troca de contexto excessiva", "description": "Alternância entre apps acima do padrão operacional.", "defaultPriority": "medio", "allowedChannels": ["system", "email"], "defaultAudience": "supervisor", "defaultFrequency": "diario", "template": "{{equipe}} alternou sistemas {{valor}} vezes.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "queda_produtividade", "name": "Queda de produtividade", "description": "Queda relevante contra baseline do período.", "defaultPriority": "alto", "allowedChannels": ["system", "whatsapp", "email"], "defaultAudience": "gerente", "defaultFrequency": "diario", "template": "{{equipe}} caiu {{valor}} contra o período anterior.", "canDisable": True, "requiresPermission": True, "critical": True},
    {"id": "insight_critico", "name": "Insight crítico", "description": "Insight de alto impacto criado pela IA/regras.", "defaultPriority": "critico", "allowedChannels": ["system", "whatsapp", "email"], "defaultAudience": "gestor_responsavel", "defaultFrequency": "imediato", "template": "Insight crítico: {{titulo}}.", "canDisable": False, "requiresPermission": True, "critical": True},
    {"id": "insight_executivo", "name": "Insight executivo", "description": "Diagnóstico estratégico para diretoria.", "defaultPriority": "alto", "allowedChannels": ["system", "email", "whatsapp"], "defaultAudience": "diretoria", "defaultFrequency": "diario", "template": "{{empresa}} tem diagnóstico executivo disponível.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "oportunidade_automacao", "name": "Oportunidade de automação", "description": "Processo repetitivo com economia estimada.", "defaultPriority": "alto", "allowedChannels": ["system", "email", "whatsapp"], "defaultAudience": "gestor_area", "defaultFrequency": "diario", "template": "Automação sugerida em {{processo}} com economia de {{economia_estimada}}.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "relatorio_diario", "name": "Relatório diário", "description": "Resumo operacional do dia.", "defaultPriority": "informativo", "allowedChannels": ["system", "email", "whatsapp"], "defaultAudience": "gestores", "defaultFrequency": "diario", "template": "Relatório diário de {{empresa}} pronto.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "relatorio_semanal", "name": "Relatório semanal", "description": "Resumo semanal executivo.", "defaultPriority": "informativo", "allowedChannels": ["system", "email"], "defaultAudience": "diretoria", "defaultFrequency": "semanal", "template": "Relatório semanal de {{empresa}} pronto.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "relatorio_mensal", "name": "Relatório mensal", "description": "Relatório mensal com tendências e ROI.", "defaultPriority": "informativo", "allowedChannels": ["system", "email"], "defaultAudience": "diretoria", "defaultFrequency": "mensal", "template": "Relatório mensal de {{empresa}} pronto.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "falha_whatsapp", "name": "Falha WhatsApp", "description": "Canal WhatsApp está indisponível ou sem credenciais.", "defaultPriority": "alto", "allowedChannels": ["system", "email"], "defaultAudience": "admin", "defaultFrequency": "imediato", "template": "WhatsApp Vulcan requer atenção: {{erro}}.", "canDisable": False, "requiresPermission": True, "critical": True},
    {"id": "falha_email", "name": "Falha e-mail", "description": "Canal de e-mail falhou ou está sem credenciais.", "defaultPriority": "alto", "allowedChannels": ["system"], "defaultAudience": "admin", "defaultFrequency": "imediato", "template": "E-mail Vulcan requer atenção: {{erro}}.", "canDisable": False, "requiresPermission": True, "critical": True},
    {"id": "falha_ia", "name": "Falha IA", "description": "Provider de IA indisponível.", "defaultPriority": "alto", "allowedChannels": ["system", "email"], "defaultAudience": "admin", "defaultFrequency": "imediato", "template": "IA indisponível: {{erro}}.", "canDisable": False, "requiresPermission": True, "critical": True},
    {"id": "seguranca_lgpd", "name": "Segurança/LGPD", "description": "Alerta de privacidade, retenção ou compliance.", "defaultPriority": "critico", "allowedChannels": ["system", "email"], "defaultAudience": "admin_dpo", "defaultFrequency": "imediato", "template": "Alerta LGPD: {{evento}}.", "canDisable": False, "requiresPermission": True, "critical": True},
    {"id": "usuario_sem_equipe", "name": "Usuário sem equipe", "description": "Colaborador não está vinculado a equipe operacional.", "defaultPriority": "baixo", "allowedChannels": ["system"], "defaultAudience": "admin_operacional", "defaultFrequency": "diario", "template": "{{usuario}} está sem equipe.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "usuario_sem_gestor", "name": "Usuário sem gestor", "description": "Nó da hierarquia ficou sem gestor direto.", "defaultPriority": "medio", "allowedChannels": ["system", "email"], "defaultAudience": "admin_operacional", "defaultFrequency": "diario", "template": "{{usuario}} está sem gestor direto.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "metrica_fora_padrao", "name": "Métrica fora do padrão", "description": "Métrica operacional saiu da faixa configurada.", "defaultPriority": "medio", "allowedChannels": ["system", "email"], "defaultAudience": "gestor_subarvore", "defaultFrequency": "a_cada_2_horas", "template": "{{metrica}} está fora do padrão: {{valor}}.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "acao_pendente", "name": "Ação pendente", "description": "Plano de ação ainda não foi iniciado.", "defaultPriority": "medio", "allowedChannels": ["system", "email"], "defaultAudience": "responsavel_acao", "defaultFrequency": "diario", "template": "Ação pendente: {{acao}}.", "canDisable": True, "requiresPermission": True, "critical": False},
    {"id": "acao_vencida", "name": "Ação vencida", "description": "Plano de ação passou do prazo.", "defaultPriority": "alto", "allowedChannels": ["system", "whatsapp", "email"], "defaultAudience": "responsavel_gestor", "defaultFrequency": "imediato", "template": "Ação vencida: {{acao}}.", "canDisable": True, "requiresPermission": True, "critical": True},
]


DEFAULT_NOTIFICATION_TEMPLATES: list[dict] = [
    {"id": "tpl-whatsapp-critical", "channel": "whatsapp", "notificationType": "insight_critico", "title": "Vulcan alerta crítico", "body": "Vulcan: {{equipe}} apresentou {{metrica}} acima do esperado em {{periodo}}. Impacto: {{impacto}}. Acesse {{link_dashboard}}", "variables": ["equipe", "metrica", "periodo", "impacto", "link_dashboard"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "tpl-whatsapp-metric", "channel": "whatsapp", "notificationType": "metrica", "title": "Métrica Vulcan", "body": "{{escopo}} registrou {{metrica}} em {{periodo}}: {{valor}}.", "variables": ["escopo", "metrica", "periodo", "valor"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "tpl-whatsapp-alert", "channel": "whatsapp", "notificationType": "alerta", "title": "Alerta Vulcan", "body": "{{titulo}}. Impacto: {{impacto}}. Recomendação: {{recomendacao}}.", "variables": ["titulo", "impacto", "recomendacao"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "tpl-whatsapp-insight", "channel": "whatsapp", "notificationType": "insight", "title": "Insight Vulcan", "body": "{{resumo}} Próximo passo: {{recomendacao}}.", "variables": ["resumo", "recomendacao"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "tpl-whatsapp-daily", "channel": "whatsapp", "notificationType": "relatorio_diario", "title": "Resumo diário Vulcan", "body": "{{escopo}}: {{tempo_ativo}} ativos, {{tempo_ocioso}} ociosos, {{gargalos}} gargalos.", "variables": ["escopo", "tempo_ativo", "tempo_ocioso", "gargalos"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "tpl-whatsapp-weekly", "channel": "whatsapp", "notificationType": "relatorio_semanal", "title": "Resumo semanal Vulcan", "body": "{{escopo}}: {{insights}} insights, {{automacoes}} oportunidades, {{economia_estimada}} de economia potencial.", "variables": ["escopo", "insights", "automacoes", "economia_estimada"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "tpl-whatsapp-critical-report", "channel": "whatsapp", "notificationType": "relatorio_critico", "title": "Crítico Vulcan", "body": "{{evento}}. Escopo: {{escopo}}. Ação imediata: {{acao}}.", "variables": ["evento", "escopo", "acao"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "tpl-email-daily", "channel": "email", "notificationType": "relatorio_diario", "title": "Vulcan - Relatório operacional diário de {{empresa}}", "body": "Resumo executivo de {{data}}\\n\\nGargalos: {{gargalos}}\\nEconomia estimada: {{economia_estimada}}\\nAções recomendadas: {{acoes}}", "variables": ["empresa", "data", "gargalos", "economia_estimada", "acoes"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "tpl-system-device", "channel": "system", "notificationType": "dispositivo_aguardando_adocao", "title": "Dispositivo aguardando adoção", "body": "{{dispositivo}} apareceu no Vulcan e precisa ser vinculado a usuário/equipe.", "variables": ["dispositivo"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "tpl-windows-policy", "channel": "windows", "notificationType": "coleta_limitada", "title": "Vulcan precisa de atenção", "body": "Sua coleta está limitada por política do sistema. O Vulcan mede fluxo operacional, não conteúdo pessoal.", "variables": ["usuario"], "language": "pt-BR", "version": 1, "active": True},
]


ROOT_WHATSAPP_TEMPLATES: list[dict] = [
    {"id": "root-whatsapp-metrica", "channel": "whatsapp", "notificationType": "metrica", "title": "Métrica operacional Vulcan", "body": "Vulcan: {{escopo}} registrou {{metrica}} em {{periodo}}. Valor: {{valor}}. Acesse {{link_dashboard}}", "variables": ["escopo", "metrica", "periodo", "valor", "link_dashboard"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "root-whatsapp-alerta", "channel": "whatsapp", "notificationType": "alerta", "title": "Alerta operacional Vulcan", "body": "Vulcan Alert: {{titulo}}. Impacto: {{impacto}}. Recomendação: {{recomendacao}}", "variables": ["titulo", "impacto", "recomendacao"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "root-whatsapp-insight", "channel": "whatsapp", "notificationType": "insight", "title": "Insight Vulcan", "body": "Vulcan Insight: {{resumo}}. Oportunidade estimada: {{economia_estimada}}. Próximo passo: {{recomendacao}}", "variables": ["resumo", "economia_estimada", "recomendacao"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "root-whatsapp-relatorio-diario", "channel": "whatsapp", "notificationType": "relatorio_diario", "title": "Resumo diário Vulcan", "body": "Resumo diário: {{escopo}} teve {{tempo_ativo}} ativos, {{tempo_ocioso}} ociosos e {{gargalos}} gargalos. Ver dashboard: {{link_dashboard}}", "variables": ["escopo", "tempo_ativo", "tempo_ocioso", "gargalos", "link_dashboard"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "root-whatsapp-relatorio-semanal", "channel": "whatsapp", "notificationType": "relatorio_semanal", "title": "Resumo semanal Vulcan", "body": "Resumo semanal: {{escopo}} gerou {{insights}} insights, {{automacoes}} oportunidades e {{economia_estimada}} de economia potencial.", "variables": ["escopo", "insights", "automacoes", "economia_estimada"], "language": "pt-BR", "version": 1, "active": True},
    {"id": "root-whatsapp-critico", "channel": "whatsapp", "notificationType": "critico", "title": "Crítico Vulcan", "body": "Alerta crítico: {{evento}}. Escopo: {{escopo}}. Ação imediata: {{acao}}", "variables": ["evento", "escopo", "acao"], "language": "pt-BR", "version": 1, "active": True},
]


SETTINGS_SECTION_DEFINITIONS: list[dict] = [
    {
        "id": "company",
        "title": "Empresa",
        "description": "Dados que aparecem em dashboards, relatórios e notificações.",
        "scope": "tenant",
        "fields": [
            {"key": "displayName", "label": "Nome exibido", "valueType": "text", "description": "Nome comercial da empresa dentro do Vulcan.", "required": True},
            {"key": "legalName", "label": "Razão social", "valueType": "text", "description": "Nome legal para relatórios e auditoria.", "required": False},
            {"key": "slug", "label": "Slug", "valueType": "text", "description": "Identificador único usado em integrações e URLs.", "required": True},
            {"key": "timezone", "label": "Fuso horário", "valueType": "select", "description": "Base de datas para métricas, relatórios e agendamentos.", "required": True, "options": ["America/Sao_Paulo", "America/Manaus", "America/Fortaleza", "UTC"]},
            {"key": "language", "label": "Idioma padrão", "valueType": "select", "description": "Idioma padrão da experiência.", "required": True, "options": ["pt-BR", "en-US"]},
            {"key": "currency", "label": "Moeda", "valueType": "select", "description": "Moeda usada no cálculo de economia estimada.", "required": True, "options": ["BRL", "USD", "EUR"]},
            {"key": "technicalOwnerEmail", "label": "Responsável técnico", "valueType": "text", "description": "E-mail para alertas de infraestrutura.", "required": False},
        ],
    },
    {
        "id": "agents",
        "title": "Agentes e dispositivos",
        "description": "Controla heartbeat, sync, lote, timeout e adoção de dispositivos.",
        "scope": "agent",
        "fields": [
            {"key": "heartbeatIntervalSeconds", "label": "Heartbeat", "valueType": "number", "description": "Intervalo em segundos entre sinais de vida do agente.", "required": True, "unit": "s"},
            {"key": "syncIntervalSeconds", "label": "Sincronização", "valueType": "number", "description": "Intervalo em segundos entre envios de eventos.", "required": True, "unit": "s"},
            {"key": "batchSize", "label": "Tamanho do lote", "valueType": "number", "description": "Quantidade máxima de eventos por sync.", "required": True},
            {"key": "requestTimeoutSeconds", "label": "Timeout", "valueType": "number", "description": "Tempo máximo de chamada do agente para a API.", "required": True, "unit": "s"},
            {"key": "queueLimit", "label": "Limite de fila offline", "valueType": "number", "description": "Dispara alerta quando a fila local ultrapassar esse limite.", "required": True},
            {"key": "requireAdoption", "label": "Exigir adoção", "valueType": "boolean", "description": "Dispositivos novos ficam pendentes até vínculo por admin.", "required": True},
            {"key": "allowDryAdoption", "label": "Permitir adoção seca", "valueType": "boolean", "description": "Admin pode adotar e completar dados depois.", "required": False},
        ],
    },
    {
        "id": "collection",
        "title": "Políticas de coleta",
        "description": "Define exatamente o que o agente pode medir, com padrão LGPD seguro.",
        "scope": "tenant",
        "fields": [
            {"key": "collectActiveApp", "label": "App ativo", "valueType": "boolean", "description": "Coleta o aplicativo ativo para medir fluxo operacional.", "required": True},
            {"key": "collectWindowTitle", "label": "Título da janela", "valueType": "boolean", "description": "Coleta título da janela quando permitido por política.", "required": False},
            {"key": "collectIdleTime", "label": "Tempo ocioso", "valueType": "boolean", "description": "Mede ociosidade operacional sem capturar conteúdo.", "required": True},
            {"key": "collectContextSwitch", "label": "Troca de contexto", "valueType": "boolean", "description": "Mede alternância entre sistemas.", "required": True},
            {"key": "collectBrowserUrl", "label": "URL do navegador", "valueType": "boolean", "description": "Desativado por padrão; exige política específica.", "required": False},
            {"key": "screenshotsEnabled", "label": "Screenshots", "valueType": "boolean", "description": "Fora do MVP e deve permanecer desativado.", "required": False},
            {"key": "privacyMode", "label": "Modo privacidade", "valueType": "boolean", "description": "Reduz granularidade e privilegia métricas agregadas.", "required": False},
            {"key": "retentionDays", "label": "Retenção", "valueType": "number", "description": "Dias de retenção de dados operacionais.", "required": True, "unit": "dias"},
        ],
    },
    {
        "id": "metrics",
        "title": "Métricas",
        "description": "Regras de cálculo para foco, ociosidade, economia e saúde operacional.",
        "scope": "tenant",
        "fields": [
            {"key": "focusTarget", "label": "Meta de foco", "valueType": "number", "description": "Score desejado de foco operacional.", "required": True},
            {"key": "idleLimitPercent", "label": "Limite de ociosidade", "valueType": "number", "description": "Percentual que dispara atenção.", "required": True, "unit": "%"},
            {"key": "contextSwitchLimitPerHour", "label": "Trocas por hora", "valueType": "number", "description": "Limite de alternância por hora.", "required": True},
            {"key": "hourlyCostBRL", "label": "Valor/hora", "valueType": "number", "description": "Base para economia/perda estimada.", "required": True, "unit": "R$"},
            {"key": "weightAgents", "label": "Peso agentes", "valueType": "number", "description": "Peso no índice de saúde operacional.", "required": True, "unit": "%"},
            {"key": "weightFocus", "label": "Peso foco", "valueType": "number", "description": "Peso no índice de saúde operacional.", "required": True, "unit": "%"},
            {"key": "weightIdle", "label": "Peso ociosidade", "valueType": "number", "description": "Peso no índice de saúde operacional.", "required": True, "unit": "%"},
            {"key": "weightContext", "label": "Peso contexto", "valueType": "number", "description": "Peso no índice de saúde operacional.", "required": True, "unit": "%"},
            {"key": "weightBottlenecks", "label": "Peso gargalos", "valueType": "number", "description": "Peso no índice de saúde operacional.", "required": True, "unit": "%"},
        ],
    },
    {
        "id": "ai",
        "title": "Insights e IA",
        "description": "Roteamento GPT/Llama, fallback explícito, timeout e limites de custo.",
        "scope": "tenant",
        "fields": [
            {"key": "mode", "label": "Modo", "valueType": "select", "description": "Define se a IA usa produção ou fallback explícito.", "required": True, "options": ["rules_fallback", "hybrid", "production"]},
            {"key": "operationalProvider", "label": "Provider operacional", "valueType": "select", "description": "Provider para análises recorrentes baratas.", "required": True, "options": ["llama", "ollama", "groq", "openrouter", "rules"]},
            {"key": "executiveProvider", "label": "Provider executivo", "valueType": "select", "description": "Provider para análises premium.", "required": True, "options": ["gpt", "openai", "rules"]},
            {"key": "timeoutSeconds", "label": "Timeout IA", "valueType": "number", "description": "Tempo máximo por chamada de IA.", "required": True, "unit": "s"},
            {"key": "monthlyBudgetBRL", "label": "Limite mensal", "valueType": "number", "description": "Controle simples de custo mensal.", "required": False, "unit": "R$"},
            {"key": "openaiApiKey", "label": "OpenAI API key", "valueType": "secret", "description": "Secret deve ficar no ambiente/cofre. O frontend vê apenas status.", "editable": False, "isSecret": True},
            {"key": "llamaApiKey", "label": "Llama/OpenRouter/Groq key", "valueType": "secret", "description": "Secret deve ficar no ambiente/cofre. O frontend vê apenas status.", "editable": False, "isSecret": True},
        ],
    },
    {
        "id": "notifications",
        "title": "Notificações",
        "description": "Regras globais de prioridade, resumos, janela silenciosa e retry.",
        "scope": "tenant",
        "fields": [
            {"key": "enabled", "label": "Notificações ativas", "valueType": "boolean", "description": "Liga/desliga orquestração de notificações do tenant.", "required": True},
            {"key": "criticalRealtime", "label": "Críticos em tempo real", "valueType": "boolean", "description": "Permite envio imediato de eventos críticos.", "required": True},
            {"key": "dailySummary", "label": "Resumo diário", "valueType": "boolean", "description": "Ativa resumo diário para gestores.", "required": False},
            {"key": "weeklySummary", "label": "Resumo semanal", "valueType": "boolean", "description": "Ativa resumo semanal executivo.", "required": False},
            {"key": "quietStart", "label": "Silêncio início", "valueType": "text", "description": "Início da janela silenciosa.", "required": False},
            {"key": "quietEnd", "label": "Silêncio fim", "valueType": "text", "description": "Fim da janela silenciosa.", "required": False},
            {"key": "maxAttempts", "label": "Tentativas", "valueType": "number", "description": "Máximo de tentativas por notificação.", "required": True},
        ],
    },
    {
        "id": "whatsapp",
        "title": "WhatsApp",
        "description": "Status do canal raiz e provider de envio. Secrets ficam fora do frontend.",
        "scope": "system",
        "fields": [
            {"key": "rootEnabled", "label": "Canal raiz", "valueType": "readonly", "description": "Ligado por ambiente ou configuração local protegida.", "editable": False},
            {"key": "rootNumber", "label": "Número mestre do Vulcan", "valueType": "readonly", "description": "Emissor central em formato E.164.", "editable": False},
            {"key": "provider", "label": "Provider", "valueType": "readonly", "description": "Provider atual de WhatsApp.", "editable": False},
            {"key": "evolutionUrl", "label": "Evolution API", "valueType": "readonly", "description": "URL local do transportador Evolution/Baileys.", "editable": False},
            {"key": "evolutionInstance", "label": "Instância", "valueType": "readonly", "description": "Instância exclusiva do Canal Raiz.", "editable": False},
            {"key": "accessToken", "label": "Evolution API key", "valueType": "secret", "description": "Secret fica no ambiente ou arquivo local com permissão 0600.", "editable": False, "isSecret": True},
            {"key": "unofficialMode", "label": "Modalidade", "valueType": "readonly", "description": "Evolution/Baileys não é uma API oficial da Meta.", "editable": False},
            {"key": "defaultRecipients", "label": "Destinatários padrão", "valueType": "text", "description": "Papéis que recebem alertas críticos por padrão.", "required": False},
            {"key": "mockMode", "label": "Modo mock explícito", "valueType": "readonly", "description": "Simula sem enviar e sem fingir entrega real.", "editable": False},
            {"key": "emailFallback", "label": "Fallback por e-mail", "valueType": "readonly", "description": "Prepara e-mail quando WhatsApp entra em dead-letter.", "editable": False},
            {"key": "inAppFallback", "label": "Fallback interno", "valueType": "readonly", "description": "Cria aviso interno quando WhatsApp falha definitivamente.", "editable": False},
        ],
    },
    {
        "id": "email",
        "title": "E-mail",
        "description": "SMTP/OAuth para envio; IMAP/POP3 somente leitura/consulta.",
        "scope": "tenant",
        "fields": [
            {"key": "provider", "label": "Provider", "valueType": "select", "description": "Canal principal de envio.", "required": True, "options": ["smtp", "gmail", "outlook", "resend", "sendgrid"]},
            {"key": "fromName", "label": "Nome do remetente", "valueType": "text", "description": "Nome exibido nos e-mails.", "required": False},
            {"key": "smtpConfigured", "label": "SMTP", "valueType": "readonly", "description": "Status do SMTP por env/cofre.", "editable": False},
            {"key": "smtpPassword", "label": "Senha SMTP", "valueType": "secret", "description": "Secret fica no ambiente/cofre seguro.", "editable": False, "isSecret": True},
            {"key": "imapReadEnabled", "label": "Leitura IMAP", "valueType": "boolean", "description": "Consulta futura de caixa, não envio.", "required": False},
            {"key": "pop3ReadEnabled", "label": "Leitura POP3", "valueType": "boolean", "description": "Consulta futura de caixa, não envio.", "required": False},
        ],
    },
    {
        "id": "security",
        "title": "Segurança",
        "description": "Auth, RLS, CORS, tokens de agente, auditoria e fallback local.",
        "scope": "system",
        "fields": [
            {"key": "authProvider", "label": "Auth provider", "valueType": "readonly", "description": "Provider ativo de autenticação.", "editable": False},
            {"key": "localFallback", "label": "Login local dev", "valueType": "readonly", "description": "Fallback local deve ficar fora de produção.", "editable": False},
            {"key": "rlsStatus", "label": "RLS", "valueType": "readonly", "description": "Status de políticas Supabase.", "editable": False},
            {"key": "corsMode", "label": "CORS", "valueType": "readonly", "description": "Origens permitidas por env.", "editable": False},
            {"key": "auditEnabled", "label": "Auditoria", "valueType": "readonly", "description": "Alterações críticas geram audit_log.", "editable": False},
            {"key": "sessionMinutes", "label": "Expiração de sessão", "valueType": "number", "description": "Duração de sessão planejada para clientes.", "required": False, "unit": "min"},
        ],
    },
    {
        "id": "privacy",
        "title": "LGPD e privacidade",
        "description": "Retenção, transparência, consentimento e limites de coleta.",
        "scope": "tenant",
        "fields": [
            {"key": "privacyStatement", "label": "Mensagem central", "valueType": "readonly", "description": "O Vulcan mede fluxo operacional, não conteúdo pessoal.", "editable": False},
            {"key": "consentRequired", "label": "Exigir consentimento", "valueType": "boolean", "description": "Exibe política de coleta ao colaborador.", "required": True},
            {"key": "allowUserPause", "label": "Permitir pausa", "valueType": "boolean", "description": "Permite pausa controlada pelo colaborador quando política permitir.", "required": False},
            {"key": "dataExportEnabled", "label": "Exportação de dados", "valueType": "boolean", "description": "Permite exportação LGPD por admin.", "required": True},
            {"key": "anonymizeAfterDays", "label": "Anonimizar após", "valueType": "number", "description": "Dias para anonimização/compactação.", "required": False, "unit": "dias"},
        ],
    },
    {
        "id": "appearance",
        "title": "Aparência",
        "description": "Densidade, movimento e acabamento visual sem quebrar a UI.",
        "scope": "user",
        "fields": [
            {"key": "theme", "label": "Tema", "valueType": "select", "description": "Tema padrão do produto.", "required": True, "options": ["dark"]},
            {"key": "glowIntensity", "label": "Intensidade de glow", "valueType": "select", "description": "Controla brilho sem prejudicar leitura.", "required": True, "options": ["baixo", "medio", "alto"]},
            {"key": "density", "label": "Densidade", "valueType": "select", "description": "Ajusta espaçamento para operação diária.", "required": True, "options": ["confortável", "compacto"]},
            {"key": "reducedMotion", "label": "Movimento reduzido", "valueType": "boolean", "description": "Respeita prefers-reduced-motion e reduz animações.", "required": False},
        ],
    },
]


DEFAULT_SETTINGS_VALUES: dict[str, dict] = {
    "company": {"displayName": "Vulcan Demo", "legalName": "Vulcan Demo", "slug": "vulcan-demo", "timezone": "America/Sao_Paulo", "language": "pt-BR", "currency": "BRL", "technicalOwnerEmail": "teste@vulcan.local"},
    "agents": {"heartbeatIntervalSeconds": 60, "syncIntervalSeconds": 120, "batchSize": 50, "requestTimeoutSeconds": 30, "queueLimit": 500, "requireAdoption": True, "allowDryAdoption": True},
    "collection": {"collectActiveApp": True, "collectWindowTitle": True, "collectIdleTime": True, "collectContextSwitch": True, "collectBrowserUrl": False, "screenshotsEnabled": False, "privacyMode": False, "retentionDays": 90},
    "metrics": {"focusTarget": 72, "idleLimitPercent": 30, "contextSwitchLimitPerHour": 40, "hourlyCostBRL": 95, "weightAgents": 20, "weightFocus": 25, "weightIdle": 20, "weightContext": 15, "weightBottlenecks": 20},
    "ai": {"mode": "rules_fallback", "operationalProvider": "llama", "executiveProvider": "gpt", "timeoutSeconds": 60, "monthlyBudgetBRL": 500},
    "notifications": {"enabled": True, "criticalRealtime": True, "dailySummary": True, "weeklySummary": True, "quietStart": "22:00", "quietEnd": "07:00", "maxAttempts": 3},
    "whatsapp": {"defaultRecipients": "diretor, gerente, supervisor"},
    "email": {"provider": "smtp", "fromName": "Vulcan Notifications", "imapReadEnabled": False, "pop3ReadEnabled": False},
    "security": {"sessionMinutes": 480},
    "privacy": {"consentRequired": True, "allowUserPause": False, "dataExportEnabled": True, "anonymizeAfterDays": 365},
    "appearance": {"theme": "dark", "glowIntensity": "medio", "density": "confortável", "reducedMotion": False},
}


@dataclass(frozen=True)
class AccessScope:
    tenant_id: UUID
    user_id: str
    membership_id: UUID | None
    department_id: UUID | None
    scope: str
    is_root: bool
    local_test: bool = False


class VulcanRepository:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.database_url) and not self.settings.mock_data

    def _connect(self) -> psycopg.Connection:
        if not self.settings.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        return psycopg.connect(self.settings.database_url, row_factory=dict_row, prepare_threshold=None)

    def _access(self, conn: psycopg.Connection, context: AuthContext) -> AccessScope:
        if context.provider == "local":
            membership = conn.execute(
                """
                select m.id, m.department_id, coalesce(r.scope, 'self') as scope
                from public.memberships m
                left join public.roles r on r.id = m.role_id
                where m.tenant_id = %s
                  and m.user_id = %s::uuid
                  and m.status = 'active'
                limit 1
                """,
                (context.tenant_id, context.user_id),
            ).fetchone()
            if membership:
                return AccessScope(
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    membership_id=membership["id"],
                    department_id=membership["department_id"],
                    scope="tenant" if context.role in {"tenant_admin", "owner", "root"} else membership["scope"],
                    is_root=False,
                    local_test=False,
                )
            if context.role == "user":
                return AccessScope(
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    membership_id=None,
                    department_id=None,
                    scope="self",
                    is_root=False,
                    local_test=False,
                )
            return AccessScope(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                membership_id=None,
                department_id=None,
                scope="tenant",
                is_root=False,
            )

        root = conn.execute(
            "select exists(select 1 from public.vulcan_root_users where user_id = %s::uuid)",
            (context.user_id,),
        ).fetchone()
        if root and root["exists"]:
            return AccessScope(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                membership_id=None,
                department_id=None,
                scope="global",
                is_root=True,
            )

        membership = conn.execute(
            """
            select m.id, m.department_id, coalesce(r.scope, 'self') as scope
            from public.memberships m
            left join public.roles r on r.id = m.role_id
            where m.tenant_id = %s
              and m.user_id = %s::uuid
              and m.status = 'active'
            limit 1
            """,
            (context.tenant_id, context.user_id),
        ).fetchone()

        if not membership:
            return AccessScope(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                membership_id=None,
                department_id=None,
                scope="self",
                is_root=False,
            )

        return AccessScope(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            membership_id=membership["id"],
            department_id=membership["department_id"],
            scope=membership["scope"],
            is_root=False,
        )

    def _membership_filter(self, access: AccessScope, alias: str = "m") -> tuple[str, tuple[object, ...]]:
        if access.is_root:
            return "true", ()
        if access.scope in {"tenant", "global"}:
            return f"{alias}.tenant_id = %s", (access.tenant_id,)
        if access.membership_id is None:
            return "false", ()
        department_condition = ""
        params: tuple[object, ...] = (access.tenant_id, access.tenant_id, access.membership_id)
        if access.department_id is not None:
            department_condition = f"""
                and (
                    {alias}.id = %s
                    or {alias}.department_id in (
                        with recursive visible_departments as (
                            select id
                            from public.departments
                            where tenant_id = %s and id = %s
                            union all
                            select child.id
                            from public.departments child
                            join visible_departments parent on parent.id = child.parent_department_id
                            where child.tenant_id = %s
                        )
                        select id from visible_departments
                    )
                )
            """
            params = (*params, access.membership_id, access.tenant_id, access.department_id, access.tenant_id)
        return (
            f"""{alias}.tenant_id = %s and {alias}.id in (
                select descendant_membership_id
                from public.membership_closure
                where tenant_id = %s and ancestor_membership_id = %s
            )
            {department_condition}""",
            params,
        )

    def _owner_filter(self, access: AccessScope, owner_column: str, tenant_column: str = "tenant_id") -> tuple[str, tuple[object, ...]]:
        if access.is_root:
            return "true", ()
        if access.scope in {"tenant", "global"}:
            return f"{tenant_column} = %s", (access.tenant_id,)
        if access.membership_id is None:
            return "false", ()
        department_condition = ""
        params: tuple[object, ...] = (access.tenant_id, access.tenant_id, access.membership_id)
        if access.department_id is not None:
            department_condition = """
                    and (
                        scoped_memberships.id = %s
                        or scoped_memberships.department_id in (
                            with recursive visible_departments as (
                                select id
                                from public.departments
                                where tenant_id = %s and id = %s
                                union all
                                select child.id
                                from public.departments child
                                join visible_departments parent on parent.id = child.parent_department_id
                                where child.tenant_id = %s
                            )
                            select id from visible_departments
                        )
                    )
            """
            params = (*params, access.membership_id, access.tenant_id, access.department_id, access.tenant_id)
        return (
            f"""{tenant_column} = %s and (
                {owner_column} in (
                    select closure.descendant_membership_id
                    from public.membership_closure closure
                    join public.memberships scoped_memberships
                      on scoped_memberships.id = closure.descendant_membership_id
                     and scoped_memberships.tenant_id = closure.tenant_id
                    where closure.tenant_id = %s
                      and closure.ancestor_membership_id = %s
                      {department_condition}
                )
            )""",
            params,
        )

    def _department_visibility_filter(self, access: AccessScope, alias: str = "d") -> tuple[str, tuple[object, ...]]:
        if access.is_root:
            return "true", ()
        if access.scope in {"tenant", "global"}:
            return f"{alias}.tenant_id = %s", (access.tenant_id,)
        if access.department_id is None:
            return "false", ()
        return (
            f"""{alias}.tenant_id = %s and {alias}.id in (
                with recursive visible_departments as (
                    select id
                    from public.departments
                    where tenant_id = %s and id = %s
                    union all
                    select child.id
                    from public.departments child
                    join visible_departments parent on parent.id = child.parent_department_id
                    where child.tenant_id = %s
                )
                select id from visible_departments
            )""",
            (access.tenant_id, access.tenant_id, access.department_id, access.tenant_id),
        )

    def _assert_department_visible(self, conn: psycopg.Connection, access: AccessScope, department_id: UUID | None) -> None:
        if department_id is None or access.is_root or access.scope in {"tenant", "global"}:
            return
        condition, params = self._department_visibility_filter(access, "d")
        row = conn.execute(
            f"select id from public.departments d where d.id = %s and {condition}",
            (department_id, *params),
        ).fetchone()
        if not row:
            raise ValueError("department outside visible scope")

    def _real_agent_data_filter(self, access: AccessScope, alias: str) -> str:
        if not access.local_test:
            return "true"
        return f"coalesce({alias}.metadata ->> 'seed', '') <> 'vulcan-demo'"

    def _resolve_agent_membership(
        self,
        conn: psycopg.Connection,
        tenant_id: UUID,
        requested_membership_id: UUID | None,
        linked_user: str | None = None,
        os_user: str | None = None,
    ) -> UUID | None:
        if requested_membership_id:
            row = conn.execute(
                "select id from public.memberships where tenant_id = %s and id = %s and status = 'active'",
                (tenant_id, requested_membership_id),
            ).fetchone()
            return requested_membership_id if row else None

        candidates = [value.strip() for value in [linked_user, os_user] if value and value.strip()]
        if tenant_id == DEMO_TENANT_ID and any(value.lower() == "teste" for value in candidates):
            row = conn.execute(
                "select id from public.memberships where tenant_id = %s and id = %s and status = 'active'",
                (tenant_id, DEMO_TEST_MEMBERSHIP_ID),
            ).fetchone()
            if row:
                return DEMO_TEST_MEMBERSHIP_ID

        for candidate in candidates:
            row = conn.execute(
                """
                select id
                from public.memberships
                where tenant_id = %s
                  and status = 'active'
                  and (
                    lower(full_name) = lower(%s)
                    or lower(coalesce(work_email::text, '')) = lower(%s)
                    or lower(coalesce(metadata ->> 'linkedUser', '')) = lower(%s)
                  )
                order by updated_at desc nulls last
                limit 1
                """,
                (tenant_id, candidate, candidate, candidate),
            ).fetchone()
            if row:
                return row["id"]
        return None

    def _repair_local_test_agent_scope(self, conn: psycopg.Connection, access: AccessScope) -> None:
        if not access.local_test or access.tenant_id != DEMO_TENANT_ID:
            return

        membership_id = self._resolve_agent_membership(
            conn,
            access.tenant_id,
            access.membership_id,
            linked_user="teste",
        )
        if not membership_id:
            return

        linked_devices = conn.execute(
            """
            update public.devices
            set owner_membership_id = %s,
                metadata = metadata || %s,
                updated_at = timezone('utc', now())
            where tenant_id = %s
              and owner_membership_id is distinct from %s
              and coalesce(metadata ->> 'seed', '') <> 'vulcan-demo'
              and coalesce(metadata ->> 'source', '') = 'vulcan-agent'
              and lower(coalesce(metadata ->> 'linkedUser', '')) = 'teste'
            returning id
            """,
            (
                membership_id,
                Jsonb({"autoLinkedMembershipId": str(membership_id), "autoLinkedReason": "local-test-linked-user"}),
                access.tenant_id,
                membership_id,
            ),
        ).fetchall()

        linked_events = conn.execute(
            """
            update public.activity_events e
            set membership_id = %s,
                metadata = e.metadata || %s
            where e.tenant_id = %s
              and e.membership_id is null
              and coalesce(e.metadata ->> 'seed', '') <> 'vulcan-demo'
              and coalesce(e.metadata ->> 'source', '') = 'vulcan-agent'
              and exists (
                select 1
                from public.devices d
                where d.tenant_id = e.tenant_id
                  and d.id = e.device_id
                  and d.owner_membership_id = %s
              )
            returning id
            """,
            (
                membership_id,
                Jsonb({"autoLinkedMembershipId": str(membership_id), "autoLinkedReason": "local-test-device-owner"}),
                access.tenant_id,
                membership_id,
            ),
        ).fetchall()

        linked_metrics = conn.execute(
            """
            update public.operational_metrics om
            set membership_id = %s,
                metadata = om.metadata || %s
            where om.tenant_id = %s
              and om.membership_id is null
              and coalesce(om.metadata ->> 'seed', '') <> 'vulcan-demo'
              and coalesce(om.metadata ->> 'source', '') = 'vulcan-agent'
              and exists (
                select 1
                from public.activity_events e
                where e.tenant_id = om.tenant_id
                  and e.membership_id = %s
                  and e.metadata ->> 'eventId' = om.metadata ->> 'eventId'
              )
            returning id
            """,
            (
                membership_id,
                Jsonb({"autoLinkedMembershipId": str(membership_id), "autoLinkedReason": "local-test-event-match"}),
                access.tenant_id,
                membership_id,
            ),
        ).fetchall()

        if linked_devices or linked_events or linked_metrics:
            self.write_agent_audit(
                conn,
                access.tenant_id,
                "agent.local_test_scope_repaired",
                "membership",
                membership_id,
                {
                    "devices": len(linked_devices),
                    "events": len(linked_events),
                    "metrics": len(linked_metrics),
                },
            )
            conn.commit()

    def list_tenants(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return TENANTS
        with self._connect() as conn:
            access = self._access(conn, context)
            if access.is_root:
                rows = conn.execute(
                    "select id, display_name as name, slug, plan, region, status from public.tenants order by display_name"
                ).fetchall()
            else:
                rows = conn.execute(
                    "select id, display_name as name, slug, plan, region, status from public.tenants where id = %s",
                    (access.tenant_id,),
                ).fetchall()
            return list(rows)

    def _can_edit_settings(self, access: AccessScope, context: AuthContext) -> bool:
        return access.is_root or access.scope in {"tenant", "global"} or context.role in {"tenant_admin", "owner", "root"}

    def assert_can_manage_integrations(self, context: AuthContext) -> None:
        if not self.enabled:
            if context.role not in {"tenant_admin", "owner", "root"}:
                raise ValueError("integration management requires tenant admin scope")
            return
        with self._connect() as conn:
            access = self._access(conn, context)
            if not self._can_edit_settings(access, context):
                raise ValueError("integration management requires tenant admin scope")

    def assert_can_manage_system_integrations(self, context: AuthContext) -> None:
        if context.role in {"owner", "root"}:
            return
        if not self.enabled:
            raise ValueError("system integration management requires owner scope")
        with self._connect() as conn:
            access = self._access(conn, context)
            if access.is_root:
                return
        raise ValueError("system integration management requires owner scope")

    def _field_definition(self, section_id: str, key: str) -> dict | None:
        section = next((item for item in SETTINGS_SECTION_DEFINITIONS if item["id"] == section_id), None)
        if not section:
            return None
        return next((field for field in section["fields"] if field["key"] == key), None)

    def _env_status_value(self, section_id: str, key: str, tenant_row: dict | None = None) -> tuple[object, str]:
        settings = self.settings
        if section_id == "ai" and key == "openaiApiKey":
            return ("configurado" if settings.openai_configured else "requer credencial", "ok" if settings.openai_configured else "missing")
        if section_id == "ai" and key == "llamaApiKey":
            configured = bool(settings.llama_base_url)
            return ("configurado" if configured else "requer credencial", "ok" if configured else "missing")
        if section_id == "whatsapp" and key == "rootEnabled":
            return ("ativo" if settings.root_whatsapp_enabled else "desativado", "ok" if settings.root_whatsapp_enabled else "missing")
        if section_id == "whatsapp" and key == "rootNumber":
            return (settings.root_whatsapp_number or "requer configuração", "ok" if settings.root_whatsapp_number else "missing")
        if section_id == "whatsapp" and key == "provider":
            return (settings.root_whatsapp_provider or settings.whatsapp_provider or "não definido", "ok" if (settings.root_whatsapp_provider or settings.whatsapp_provider) else "missing")
        if section_id == "whatsapp" and key == "evolutionUrl":
            return (settings.evolution_base_url or "requer configuração", "ok" if settings.evolution_base_url else "missing")
        if section_id == "whatsapp" and key == "evolutionInstance":
            return (settings.evolution_instance_name or "requer configuração", "ok" if settings.evolution_instance_name else "missing")
        if section_id == "whatsapp" and key == "accessToken":
            configured = bool(settings.evolution_api_key) if settings.root_whatsapp_provider == "evolution" else bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id)
            return ("configurado" if configured else "requer credencial", "ok" if configured else "missing")
        if section_id == "whatsapp" and key == "unofficialMode":
            unofficial = settings.root_whatsapp_provider == "evolution"
            return ("não oficial: Evolution/Baileys" if unofficial else "oficial/futuro", "attention" if unofficial else "ok")
        if section_id == "whatsapp" and key == "mockMode":
            return ("ativo" if settings.root_whatsapp_mock_mode else "inativo", "mock" if settings.root_whatsapp_mock_mode else "ok")
        if section_id == "whatsapp" and key == "emailFallback":
            return ("ativo" if settings.whatsapp_email_fallback_enabled else "inativo", "ok" if settings.whatsapp_email_fallback_enabled else "attention")
        if section_id == "whatsapp" and key == "inAppFallback":
            return ("ativo" if settings.whatsapp_in_app_fallback_enabled else "inativo", "ok" if settings.whatsapp_in_app_fallback_enabled else "attention")
        if section_id == "email" and key == "smtpConfigured":
            configured = bool(settings.smtp_host and settings.smtp_user and settings.smtp_pass and settings.email_from)
            return ("configurado" if configured else "requer credencial", "ok" if configured else "missing")
        if section_id == "email" and key == "smtpPassword":
            return ("configurado" if settings.smtp_pass else "requer credencial", "ok" if settings.smtp_pass else "missing")
        if section_id == "security" and key == "authProvider":
            return (settings.auth_provider, "ok" if settings.auth_provider == "supabase" else "attention")
        if section_id == "security" and key == "localFallback":
            enabled = settings.local_test_auth_enabled or settings.mock_auth or settings.auth_provider == "local"
            return ("ativo" if enabled else "inativo", "attention" if enabled and settings.environment == "production" else "ok")
        if section_id == "security" and key == "rlsStatus":
            return ("habilitado", "ok")
        if section_id == "security" and key == "corsMode":
            return ("restrito por env" if settings.environment == "production" else "local flexível", "ok" if settings.environment != "production" or settings.api_allowed_origin_regex is None else "attention")
        if section_id == "security" and key == "auditEnabled":
            return ("ativo", "ok")
        if section_id == "privacy" and key == "privacyStatement":
            return ("O Vulcan mede fluxo operacional, não conteúdo pessoal.", "ok")
        return (None, "ok")

    def _validate_settings_values(self, section_id: str, values: dict) -> dict:
        if section_id not in {item["id"] for item in SETTINGS_SECTION_DEFINITIONS}:
            raise ValueError("seção de configuração desconhecida")
        cleaned: dict = {}
        for key, value in values.items():
            definition = self._field_definition(section_id, key)
            if not definition:
                raise ValueError(f"campo desconhecido: {key}")
            if definition.get("isSecret") or definition.get("editable") is False or definition.get("valueType") == "readonly":
                raise ValueError(f"campo somente leitura ou sensível: {key}")
            value_type = definition.get("valueType")
            if value_type == "number":
                try:
                    number = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{definition['label']} deve ser número") from exc
                if number < 0:
                    raise ValueError(f"{definition['label']} não pode ser negativo")
                cleaned[key] = int(number) if number.is_integer() else number
            elif value_type == "boolean":
                if isinstance(value, bool):
                    cleaned[key] = value
                elif isinstance(value, str) and value.lower() in {"true", "false"}:
                    cleaned[key] = value.lower() == "true"
                else:
                    raise ValueError(f"{definition['label']} deve ser verdadeiro/falso")
            elif value_type == "select":
                options = definition.get("options") or []
                if options and value not in options:
                    raise ValueError(f"{definition['label']} deve ser uma opção válida")
                cleaned[key] = value
            else:
                text = "" if value is None else str(value).strip()
                if definition.get("required") and not text:
                    raise ValueError(f"{definition['label']} é obrigatório")
                cleaned[key] = text

        if section_id == "company":
            slug = cleaned.get("slug")
            if slug and not all(char.isalnum() or char in {"-", "_"} for char in slug):
                raise ValueError("Slug deve conter apenas letras, números, hífen ou underscore")
            email = cleaned.get("technicalOwnerEmail")
            if email and "@" not in email:
                raise ValueError("Responsável técnico deve ser um e-mail válido")
        if section_id == "agents":
            if "heartbeatIntervalSeconds" in cleaned and not 10 <= cleaned["heartbeatIntervalSeconds"] <= 3600:
                raise ValueError("Heartbeat deve ficar entre 10 e 3600 segundos")
            if "syncIntervalSeconds" in cleaned and not 10 <= cleaned["syncIntervalSeconds"] <= 3600:
                raise ValueError("Sync deve ficar entre 10 e 3600 segundos")
            if "batchSize" in cleaned and not 1 <= cleaned["batchSize"] <= 1000:
                raise ValueError("Tamanho do lote deve ficar entre 1 e 1000")
        if section_id == "collection":
            if cleaned.get("screenshotsEnabled"):
                raise ValueError("Screenshots contínuos estão fora do MVP e devem permanecer desativados")
            if cleaned.get("collectBrowserUrl"):
                raise ValueError("Coleta de URL está desativada por padrão e exige política específica fora do MVP")
        if section_id == "metrics":
            weights = ["weightAgents", "weightFocus", "weightIdle", "weightContext", "weightBottlenecks"]
            merged = {**DEFAULT_SETTINGS_VALUES["metrics"], **cleaned}
            total = sum(float(merged.get(item, 0)) for item in weights)
            if round(total, 2) != 100:
                raise ValueError("Pesos da Saúde Operacional precisam somar 100%")
        return cleaned

    def _settings_rows(self, conn: psycopg.Connection, access: AccessScope) -> dict:
        row = conn.execute(
            """
            select t.id as "tenantId", t.display_name as "displayName", t.legal_name as "legalName",
                   t.slug, t.region, t.plan, t.status,
                   coalesce(ts.default_locale, 'pt-BR') as "language",
                   coalesce(ts.default_timezone, 'America/Sao_Paulo') as "timezone",
                   coalesce(ts.retention_days, 90) as "retentionDays",
                   coalesce(ts.analytics_enabled, true) as "analyticsEnabled",
                   coalesce(ts.ai_explanations_enabled, true) as "aiExplanationsEnabled",
                   coalesce(ts.settings, '{}'::jsonb) as settings,
                   ts.updated_at as "lastUpdatedAt"
            from public.tenants t
            left join public.tenant_settings ts on ts.tenant_id = t.id
            where t.id = %s
            """,
            (access.tenant_id,),
        ).fetchone()
        return dict(row) if row else {}

    def _build_settings_response(self, context: AuthContext, tenant_row: dict, can_edit: bool) -> dict:
        persisted = tenant_row.get("settings") or {}
        sections: list[dict] = []
        last_updated = tenant_row.get("lastUpdatedAt")
        system_owner = context.role in {"owner", "root"}
        owner_only_whatsapp_fields = {"evolutionUrl", "evolutionInstance", "accessToken", "unofficialMode"}

        def mask_phone(value: object) -> object:
            digits = "".join(char for char in str(value or "") if char.isdigit())
            if not digits:
                return value
            if len(digits) <= 4:
                return digits
            return f"{digits[:4]}*****{digits[-4:]}"
        company_overrides = {
            "displayName": tenant_row.get("displayName") or DEFAULT_SETTINGS_VALUES["company"]["displayName"],
            "legalName": tenant_row.get("legalName") or DEFAULT_SETTINGS_VALUES["company"]["legalName"],
            "slug": tenant_row.get("slug") or DEFAULT_SETTINGS_VALUES["company"]["slug"],
            "timezone": tenant_row.get("timezone") or DEFAULT_SETTINGS_VALUES["company"]["timezone"],
            "language": tenant_row.get("language") or DEFAULT_SETTINGS_VALUES["company"]["language"],
            "retentionDays": tenant_row.get("retentionDays") or DEFAULT_SETTINGS_VALUES["collection"]["retentionDays"],
        }
        for definition in SETTINGS_SECTION_DEFINITIONS:
            section_id = definition["id"]
            default_values = DEFAULT_SETTINGS_VALUES.get(section_id, {})
            values = {**default_values, **(persisted.get(section_id) or {})}
            if section_id == "company":
                values.update({k: v for k, v in company_overrides.items() if k in {"displayName", "legalName", "slug", "timezone", "language"}})
            if section_id == "collection":
                values["retentionDays"] = company_overrides["retentionDays"]

            section_status = "ok"
            fields: list[dict] = []
            for field_def in definition["fields"]:
                key = field_def["key"]
                if section_id == "whatsapp" and key in owner_only_whatsapp_fields and not system_owner:
                    continue
                value = values.get(key)
                field_status = "ok"
                computed, computed_status = self._env_status_value(section_id, key, tenant_row)
                if computed is not None:
                    value = computed
                    field_status = computed_status
                if section_id == "whatsapp" and key == "rootNumber" and not system_owner:
                    value = mask_phone(value)
                if section_id == "whatsapp" and key == "provider" and not system_owner:
                    value = "gerenciado pela Vulcan"
                    field_status = "ok"
                if field_def.get("required") and (value is None or value == ""):
                    field_status = "missing"
                if field_def.get("isSecret") and field_status == "ok":
                    value = "configurado"
                editable = bool(field_def.get("editable", True)) and can_edit
                fields.append({
                    **field_def,
                    "value": value,
                    "status": field_status,
                    "editable": editable,
                    "required": bool(field_def.get("required", False)),
                    "isSecret": bool(field_def.get("isSecret", False)),
                    "options": field_def.get("options", []),
                })
                if field_status in {"error", "missing"}:
                    section_status = field_status
                elif field_status in {"attention", "mock"} and section_status == "ok":
                    section_status = field_status
            sections.append({
                "id": section_id,
                "title": definition["title"],
                "description": definition["description"],
                "scope": definition.get("scope", "tenant"),
                "status": section_status,
                "canEdit": can_edit and any(field["editable"] for field in fields),
                "lastUpdatedAt": last_updated,
                "fields": fields,
            })
        counters = defaultdict(int)
        for section in sections:
            counters[section["status"]] += 1
        critical_pending = [section["title"] for section in sections if section["status"] in {"missing", "error"}]
        statuses = {section["id"]: section["status"] for section in sections}
        return {
            "summary": {
                "tenantId": tenant_row.get("tenantId", DEMO_TENANT_ID),
                "environment": self.settings.environment,
                "canEdit": can_edit,
                "totalSections": len(sections),
                "ok": counters["ok"],
                "attention": counters["attention"],
                "missing": counters["missing"],
                "error": counters["error"],
                "mock": counters["mock"],
                "lastUpdatedAt": last_updated,
                "criticalPending": critical_pending,
                "statuses": statuses,
            },
            "sections": sections,
        }

    def get_settings_center(self, context: AuthContext) -> dict:
        if not self.enabled:
            can_edit = context.role in {"tenant_admin", "owner", "root"}
            return self._build_settings_response(context, {"tenantId": DEMO_TENANT_ID, "settings": {}, "lastUpdatedAt": None}, can_edit)
        with self._connect() as conn:
            access = self._access(conn, context)
            tenant_row = self._settings_rows(conn, access)
            return self._build_settings_response(context, tenant_row, self._can_edit_settings(access, context))

    def update_settings_section(self, context: AuthContext, section_id: str, request: SettingsSectionUpdate) -> dict:
        cleaned = self._validate_settings_values(section_id, request.values)
        if not self.enabled:
            can_edit = context.role in {"tenant_admin", "owner", "root"}
            if not can_edit:
                raise ValueError("sem permissão para alterar configurações")
            return self._build_settings_response(context, {"tenantId": DEMO_TENANT_ID, "settings": {section_id: cleaned}, "lastUpdatedAt": datetime.now(timezone.utc)}, can_edit)
        with self._connect() as conn:
            access = self._access(conn, context)
            if not self._can_edit_settings(access, context):
                raise ValueError("sem permissão para alterar configurações")
            row = self._settings_rows(conn, access)
            current_settings = row.get("settings") or {}
            merged_section = {**DEFAULT_SETTINGS_VALUES.get(section_id, {}), **(current_settings.get(section_id) or {}), **cleaned}
            current_settings[section_id] = merged_section

            if section_id == "company":
                conn.execute(
                    """
                    update public.tenants
                    set display_name = coalesce(%s, display_name),
                        legal_name = coalesce(%s, legal_name),
                        slug = coalesce(%s, slug),
                        updated_at = timezone('utc', now())
                    where id = %s
                    """,
                    (
                        cleaned.get("displayName"),
                        cleaned.get("legalName"),
                        cleaned.get("slug"),
                        access.tenant_id,
                    ),
                )
            conn.execute(
                """
                insert into public.tenant_settings (
                  tenant_id, default_locale, default_timezone, retention_days,
                  analytics_enabled, ai_explanations_enabled, settings, updated_at
                )
                values (%s, %s, %s, %s, true, true, %s, timezone('utc', now()))
                on conflict (tenant_id) do update
                set default_locale = excluded.default_locale,
                    default_timezone = excluded.default_timezone,
                    retention_days = excluded.retention_days,
                    settings = excluded.settings,
                    updated_at = timezone('utc', now())
                """,
                (
                    access.tenant_id,
                    current_settings.get("company", {}).get("language", row.get("language") or "pt-BR"),
                    current_settings.get("company", {}).get("timezone", row.get("timezone") or "America/Sao_Paulo"),
                    current_settings.get("collection", {}).get("retentionDays", row.get("retentionDays") or 90),
                    Jsonb(current_settings),
                ),
            )
            self.write_audit(conn, context, access.tenant_id, "settings.updated", "tenant_settings", access.tenant_id, {"section": section_id, "changedKeys": sorted(cleaned.keys())})
            conn.commit()
            tenant_row = self._settings_rows(conn, access)
            return self._build_settings_response(context, tenant_row, True)

    def test_settings_section(self, context: AuthContext, section_id: str) -> dict:
        response = self.get_settings_center(context)
        section = next((item for item in response["sections"] if item["id"] == section_id), None)
        if not section:
            raise ValueError("seção de configuração desconhecida")
        if section["status"] in {"missing", "error"}:
            message = f"{section['title']} requer ajuste antes de produção."
            status = section["status"]
        elif section["status"] in {"attention", "mock"}:
            message = f"{section['title']} está utilizável, mas possui atenção/mock explícito."
            status = section["status"]
        else:
            message = f"{section['title']} validado com sucesso."
            status = "ok"
        return {"section": section_id, "status": status, "message": message, "saved": False, "tested": True, "sectionData": section}

    def list_departments(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._department_visibility_filter(access, "d")
            return list(conn.execute(
                f"""
                select id, tenant_id as "tenantId", parent_department_id as "parentDepartmentId",
                       name, slug, description
                from public.departments d
                where {condition}
                order by coalesce(parent_department_id::text, ''), name
                """,
                params,
            ).fetchall())

    def create_department(self, context: AuthContext, request: DepartmentCreate) -> dict:
        if not self.enabled:
            raise ValueError("department writes require Supabase/Postgres")
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_tenant_write(access, request.tenant_id)
            if request.parent_department_id:
                parent = conn.execute(
                    "select id from public.departments where tenant_id = %s and id = %s",
                    (request.tenant_id, request.parent_department_id),
                ).fetchone()
                if not parent:
                    raise ValueError("parent department not found")
            slug = slugify(request.slug or request.name)
            row = conn.execute(
                """
                insert into public.departments (tenant_id, parent_department_id, name, slug, description)
                values (%s, %s, %s, %s, %s)
                on conflict (tenant_id, slug) do update
                set parent_department_id = excluded.parent_department_id,
                    name = excluded.name,
                    description = excluded.description,
                    updated_at = timezone('utc', now())
                returning id, tenant_id as "tenantId", parent_department_id as "parentDepartmentId",
                          name, slug, description
                """,
                (request.tenant_id, request.parent_department_id, request.name.strip(), slug, request.description),
            ).fetchone()
            self.write_audit(conn, context, request.tenant_id, "department.upserted", "department", row["id"], {"slug": slug, "name": request.name})
            conn.commit()
            return dict(row)

    def list_roles(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition = "tenant_id is null" if not access.is_root else "true"
            params: tuple[object, ...] = ()
            if not access.is_root:
                condition = "(tenant_id is null or tenant_id = %s)"
                params = (access.tenant_id,)
            return list(conn.execute(
                f"""
                select id, tenant_id as "tenantId", slug, name, description,
                       coalesce(scope, 'tenant') as scope,
                       coalesce(is_system, false) as "isSystem"
                from public.roles
                where {condition}
                order by is_system desc, name
                """,
                params,
            ).fetchall())

    def create_role(self, context: AuthContext, request: RoleCreate) -> dict:
        if not self.enabled:
            raise ValueError("role writes require Supabase/Postgres")
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_tenant_write(access, request.tenant_id)
            slug = slugify(request.slug)
            row = conn.execute(
                """
                insert into public.roles (tenant_id, slug, name, description, scope, is_system)
                values (%s, %s, %s, %s, %s, false)
                on conflict (tenant_id, slug) do update
                set name = excluded.name,
                    description = excluded.description,
                    scope = excluded.scope,
                    updated_at = timezone('utc', now())
                returning id, tenant_id as "tenantId", slug, name, description,
                          coalesce(scope, 'tenant') as scope,
                          coalesce(is_system, false) as "isSystem"
                """,
                (request.tenant_id, slug, request.name.strip(), request.description, request.scope),
            ).fetchone()
            self.write_audit(conn, context, request.tenant_id, "role.upserted", "role", row["id"], {"slug": slug, "scope": request.scope})
            conn.commit()
            return dict(row)

    def _ensure_team_tables(self, conn: psycopg.Connection) -> None:
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
        conn.execute("create index if not exists idx_teams_tenant_status on public.teams (tenant_id, status)")
        conn.execute("create index if not exists idx_team_members_membership on public.team_members (tenant_id, membership_id)")

    def _ensure_team_write(self, access: AccessScope, tenant_id: UUID) -> None:
        if not access.is_root and access.tenant_id != tenant_id:
            raise ValueError("team tenant outside current context")
        if not access.is_root and access.scope == "self":
            raise ValueError("team writes require manager scope")

    def _team_row(self, conn: psycopg.Connection, access: AccessScope, team_id: UUID) -> dict | None:
        self._ensure_team_tables(conn)
        row = conn.execute(
            """
            select t.id, t.tenant_id as "tenantId", t.name, t.description, t.color,
                   count(distinct tm.membership_id)::int as "membersCount",
                   count(distinct d.id)::int as "devicesCount",
                   coalesce(sum(case when om.metric_key = 'active_seconds' then om.value_numeric else 0 end), 0)::float as "activeSeconds",
                   coalesce(sum(case when om.metric_key = 'idle_seconds' then om.value_numeric else 0 end), 0)::float as "idleSeconds"
            from public.teams t
            left join public.team_members tm on tm.team_id = t.id and tm.tenant_id = t.tenant_id
            left join public.devices d on d.tenant_id = t.tenant_id and d.metadata ->> 'teamId' = t.id::text
            left join public.operational_metrics om on om.tenant_id = t.tenant_id and om.membership_id = tm.membership_id
            where t.tenant_id = %s and t.id = %s and t.status = 'active'
            group by t.id
            """,
            (access.tenant_id, team_id),
        ).fetchone()
        return dict(row) if row else None

    def list_teams(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return [
                {"id": UUID("00000000-0000-0000-0000-000000700001"), "tenantId": DEMO_TENANT_ID, "name": "Financeiro", "description": "Contas, faturamento e conciliação", "color": "#fb923c", "membersCount": 2, "devicesCount": 2, "activeSeconds": 7200, "idleSeconds": 1800},
                {"id": UUID("00000000-0000-0000-0000-000000700002"), "tenantId": DEMO_TENANT_ID, "name": "Operação", "description": "Execução operacional e atendimento", "color": "#34d399", "membersCount": 4, "devicesCount": 4, "activeSeconds": 12800, "idleSeconds": 2600},
            ]
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_team_tables(conn)
            membership_condition, membership_params = self._membership_filter(access, "m")
            if access.scope in {"tenant", "global"} or access.is_root:
                visibility = "true"
                params: tuple[object, ...] = (access.tenant_id,)
            else:
                visibility = f"exists (select 1 from public.team_members vtm join public.memberships m on m.id = vtm.membership_id where vtm.team_id = t.id and {membership_condition})"
                params = (access.tenant_id, *membership_params)
            return list(conn.execute(
                f"""
                select t.id, t.tenant_id as "tenantId", t.name, t.description, t.color,
                       count(distinct tm.membership_id)::int as "membersCount",
                       count(distinct d.id)::int as "devicesCount",
                       coalesce(sum(case when om.metric_key = 'active_seconds' then om.value_numeric else 0 end), 0)::float as "activeSeconds",
                       coalesce(sum(case when om.metric_key = 'idle_seconds' then om.value_numeric else 0 end), 0)::float as "idleSeconds"
                from public.teams t
                left join public.team_members tm on tm.team_id = t.id and tm.tenant_id = t.tenant_id
                left join public.devices d on d.tenant_id = t.tenant_id and d.metadata ->> 'teamId' = t.id::text
                left join public.operational_metrics om on om.tenant_id = t.tenant_id and om.membership_id = tm.membership_id
                where t.tenant_id = %s and t.status = 'active' and {visibility}
                group by t.id
                order by t.name
                """,
                params,
            ).fetchall())

    def create_team(self, context: AuthContext, request: TeamCreate) -> dict:
        if not self.enabled:
            return {**request.model_dump(by_alias=True), "id": uuid4(), "membersCount": 0, "devicesCount": 0, "activeSeconds": 0, "idleSeconds": 0}
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_team_write(access, request.tenant_id)
            self._ensure_team_tables(conn)
            row = conn.execute(
                """
                insert into public.teams (tenant_id, name, description, color)
                values (%s, %s, %s, %s)
                on conflict (tenant_id, name) do update
                set description = excluded.description,
                    color = excluded.color,
                    status = 'active',
                    updated_at = timezone('utc', now())
                returning id
                """,
                (request.tenant_id, request.name.strip(), request.description, request.color),
            ).fetchone()
            self.write_audit(conn, context, request.tenant_id, "team.created", "team", row["id"], {"name": request.name})
            conn.commit()
            return self._team_row(conn, access, row["id"]) or {}

    def update_team(self, context: AuthContext, team_id: UUID, request: TeamUpdate) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_team_write(access, access.tenant_id)
            self._ensure_team_tables(conn)
            existing = conn.execute("select id from public.teams where tenant_id = %s and id = %s", (access.tenant_id, team_id)).fetchone()
            if not existing:
                return None
            row = conn.execute(
                """
                update public.teams
                set name = coalesce(%s, name),
                    description = coalesce(%s, description),
                    color = coalesce(%s, color),
                    status = coalesce(%s, status),
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                returning id
                """,
                (request.name, request.description, request.color, request.status, access.tenant_id, team_id),
            ).fetchone()
            self.write_audit(conn, context, access.tenant_id, "team.updated", "team", team_id, request.model_dump(exclude_none=True))
            conn.commit()
            return self._team_row(conn, access, row["id"]) if row else None

    def delete_team(self, context: AuthContext, team_id: UUID) -> dict | None:
        return self.update_team(context, team_id, TeamUpdate(status="archived"))

    def list_team_members(self, context: AuthContext, team_id: UUID) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_team_tables(conn)
            condition, params = self._membership_filter(access, "m")
            return list(conn.execute(
                f"""
                select tm.id, tm.tenant_id as "tenantId", tm.team_id as "teamId",
                       tm.membership_id as "membershipId", tm.role_in_team as "roleInTeam",
                       m.full_name as "memberName", m.title as "memberTitle"
                from public.team_members tm
                join public.memberships m on m.id = tm.membership_id and m.status = 'active'
                where tm.tenant_id = %s and tm.team_id = %s and {condition}
                order by m.hierarchy_level nulls last, m.full_name
                """,
                (access.tenant_id, team_id, *params),
            ).fetchall())

    def add_team_member(self, context: AuthContext, team_id: UUID, request: TeamMemberCreate) -> dict:
        if not self.enabled:
            return {}
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_team_write(access, request.tenant_id)
            self._ensure_team_tables(conn)
            self._assert_membership_visible(conn, access, request.membership_id)
            team = conn.execute("select id from public.teams where tenant_id = %s and id = %s and status = 'active'", (request.tenant_id, team_id)).fetchone()
            if not team:
                raise ValueError("team not found")
            row = conn.execute(
                """
                insert into public.team_members (tenant_id, team_id, membership_id, role_in_team)
                values (%s, %s, %s, %s)
                on conflict (tenant_id, team_id, membership_id) do update
                set role_in_team = excluded.role_in_team,
                    updated_at = timezone('utc', now())
                returning id
                """,
                (request.tenant_id, team_id, request.membership_id, request.role_in_team),
            ).fetchone()
            self.write_audit(conn, context, request.tenant_id, "team.member.upserted", "team", team_id, {"membership_id": str(request.membership_id)})
            conn.commit()
            members = self.list_team_members(context, team_id)
            return next((member for member in members if member["id"] == row["id"]), members[-1] if members else {})

    def remove_team_member(self, context: AuthContext, team_id: UUID, membership_id: UUID) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_team_write(access, access.tenant_id)
            self._ensure_team_tables(conn)
            result = conn.execute(
                "delete from public.team_members where tenant_id = %s and team_id = %s and membership_id = %s returning team_id",
                (access.tenant_id, team_id, membership_id),
            ).fetchone()
            if not result:
                return None
            self.write_audit(conn, context, access.tenant_id, "team.member.removed", "team", team_id, {"membership_id": str(membership_id)})
            conn.commit()
            return self._team_row(conn, access, team_id)

    def list_memberships(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._membership_filter(access)
            return list(conn.execute(
                f"""
                select m.id, m.tenant_id as "tenantId", m.user_id as "userId",
                       m.role_id as "roleId", m.department_id as "departmentId",
                       m.direct_manager_membership_id as "directManagerMembershipId",
                       m.status, m.full_name as "fullName", m.work_email as "workEmail",
                       m.phone, m.whatsapp,
                       coalesce(m.whatsapp_enabled, true) as "whatsappEnabled",
                       coalesce(m.whatsapp_opt_in, false) as "whatsappOptIn",
                       coalesce(m.whatsapp_notification_types, '[]'::jsonb) as "whatsappNotificationTypes",
                       m.quiet_hours_start::text as "quietHoursStart",
                       m.quiet_hours_end::text as "quietHoursEnd",
                       m.title, m.hierarchy_level as "hierarchyLevel"
                from public.memberships m
                where m.status = 'active' and {condition}
                order by m.hierarchy_level nulls last, m.full_name
                """,
                params,
            ).fetchall())

    def _ensure_tenant_write(self, access: AccessScope, tenant_id: UUID) -> None:
        if access.is_root:
            return
        if access.tenant_id != tenant_id or access.scope not in {"tenant", "global"}:
            raise ValueError("write access requires tenant admin scope")

    def _assert_membership_visible(self, conn: psycopg.Connection, access: AccessScope, membership_id: UUID) -> None:
        condition, params = self._membership_filter(access)
        row = conn.execute(
            f"select id from public.memberships m where m.id = %s and m.status = 'active' and {condition}",
            (membership_id, *params),
        ).fetchone()
        if not row:
            raise ValueError("membership outside visible hierarchy")

    def _fetch_manager_level(self, conn: psycopg.Connection, tenant_id: UUID, manager_id: UUID | None) -> int | None:
        if manager_id is None:
            return None
        row = conn.execute(
            "select hierarchy_level from public.memberships where tenant_id = %s and id = %s and status = 'active'",
            (tenant_id, manager_id),
        ).fetchone()
        if not row:
            raise ValueError("manager membership does not exist in tenant")
        return int(row["hierarchy_level"] or 0)

    def _ensure_hierarchy_write(
        self,
        conn: psycopg.Connection,
        access: AccessScope,
        tenant_id: UUID,
        target_membership_id: UUID | None,
        manager_id: UUID | None,
        hierarchy_level: int | None,
        deleting: bool = False,
    ) -> None:
        if not access.is_root and access.tenant_id != tenant_id:
            raise ValueError("tenant outside current context")
        if not access.is_root and access.scope == "self":
            raise ValueError("hierarchy write requires manager scope")

        if target_membership_id is not None:
            self._assert_membership_visible(conn, access, target_membership_id)

        if manager_id is not None:
            self._assert_membership_visible(conn, access, manager_id)
            manager_level = self._fetch_manager_level(conn, tenant_id, manager_id)
            if hierarchy_level is not None and manager_level is not None and hierarchy_level <= manager_level:
                raise ValueError("new member level must stay below the selected manager")
        elif not access.is_root and access.scope not in {"tenant", "global"}:
            raise ValueError("hierarchy manager is required")

        if deleting and access.membership_id and target_membership_id == access.membership_id:
            raise ValueError("membership cannot delete itself")

    def _role_scope(self, conn: psycopg.Connection, role_id: UUID | None) -> str:
        if role_id is None:
            return "self"
        row = conn.execute("select coalesce(scope, 'self') as scope from public.roles where id = %s", (role_id,)).fetchone()
        return str(row["scope"]) if row else "self"

    def _upsert_auth_user(
        self,
        conn: psycopg.Connection,
        *,
        user_id: UUID | None,
        email: str | None,
        full_name: str,
        username: str | None,
        password: str | None,
    ) -> UUID:
        login = (username or email or full_name).strip().lower()
        primary_email = (email or f"{login}@vulcan.local").strip().lower()
        existing = conn.execute(
            """
            select id
            from auth.users
            where (%s::uuid is not null and id = %s::uuid)
               or lower(email) = lower(%s)
               or lower(coalesce(raw_user_meta_data ->> 'login', '')) = lower(%s)
            order by created_at
            limit 1
            """,
            (user_id, user_id, primary_email, login),
        ).fetchone()
        resolved_user_id = UUID(str(existing["id"])) if existing else (user_id or uuid4())
        password_value = password or uuid4().hex
        encrypted_update = "excluded.encrypted_password" if password else "auth.users.encrypted_password"
        conn.execute(
            f"""
            insert into auth.users (
              id, aud, role, email, encrypted_password, email_confirmed_at,
              raw_app_meta_data, raw_user_meta_data, is_sso_user, is_anonymous,
              created_at, updated_at
            )
            values (%s, 'authenticated', 'authenticated', %s, crypt(%s, gen_salt('bf')), timezone('utc', now()),
                    %s, %s, false, false, timezone('utc', now()), timezone('utc', now()))
            on conflict (id) do update
            set email = excluded.email,
                encrypted_password = {encrypted_update},
                raw_user_meta_data = excluded.raw_user_meta_data,
                updated_at = timezone('utc', now())
            """,
            (
                resolved_user_id,
                primary_email,
                password_value,
                Jsonb({"provider": "vulcan-local"}),
                Jsonb({"name": full_name, "login": login, "product": "Vulcan", "createdBy": "hierarchy-crud"}),
            ),
        )
        conn.execute(
            """
            insert into public.user_profiles (user_id, primary_email, display_name, locale, timezone, metadata)
            values (%s, %s, %s, 'pt-BR', 'America/Sao_Paulo', %s)
            on conflict (user_id) do update
            set primary_email = excluded.primary_email,
                display_name = excluded.display_name,
                metadata = public.user_profiles.metadata || excluded.metadata,
                updated_at = timezone('utc', now())
            """,
            (resolved_user_id, primary_email, full_name, Jsonb({"login": login, "source": "hierarchy-crud"})),
        )
        return resolved_user_id

    def _assert_manager_is_safe(
        self,
        conn: psycopg.Connection,
        tenant_id: UUID,
        membership_id: UUID | None,
        manager_id: UUID | None,
    ) -> None:
        if manager_id is None:
            return
        manager = conn.execute(
            "select id from public.memberships where tenant_id = %s and id = %s",
            (tenant_id, manager_id),
        ).fetchone()
        if not manager:
            raise ValueError("manager membership does not exist in tenant")
        if membership_id is None:
            return
        if manager_id == membership_id:
            raise ValueError("membership cannot manage itself")
        cycle = conn.execute(
            """
            select exists(
              select 1 from public.membership_closure
              where tenant_id = %s
                and ancestor_membership_id = %s
                and descendant_membership_id = %s
                and depth > 0
            )
            """,
            (tenant_id, membership_id, manager_id),
        ).fetchone()
        if cycle and cycle["exists"]:
            raise ValueError("manager assignment would create a hierarchy cycle")

    def _fetch_membership(self, conn: psycopg.Connection, membership_id: UUID) -> dict | None:
        return conn.execute(
            """
            select m.id, m.tenant_id as "tenantId", m.user_id as "userId",
                   m.role_id as "roleId", m.department_id as "departmentId",
                   m.direct_manager_membership_id as "directManagerMembershipId",
                   m.status, m.full_name as "fullName", m.work_email as "workEmail",
                   m.phone, m.whatsapp,
                   coalesce(m.whatsapp_enabled, true) as "whatsappEnabled",
                   coalesce(m.whatsapp_opt_in, false) as "whatsappOptIn",
                   coalesce(m.whatsapp_notification_types, '[]'::jsonb) as "whatsappNotificationTypes",
                   m.quiet_hours_start::text as "quietHoursStart",
                   m.quiet_hours_end::text as "quietHoursEnd",
                   m.title, m.hierarchy_level as "hierarchyLevel"
            from public.memberships m
            where m.id = %s
            """,
            (membership_id,),
        ).fetchone()

    def create_membership(self, context: AuthContext, request: MembershipCreate) -> dict:
        if not self.enabled:
            raise ValueError("membership writes require Supabase/Postgres")
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_hierarchy_write(
                conn,
                access,
                request.tenant_id,
                None,
                request.direct_manager_membership_id,
                request.hierarchy_level,
            )
            self._assert_department_visible(conn, access, request.department_id)
            self._assert_manager_is_safe(conn, request.tenant_id, None, request.direct_manager_membership_id)
            user_id = self._upsert_auth_user(
                conn,
                user_id=request.user_id,
                email=request.work_email,
                full_name=request.full_name,
                username=request.username,
                password=request.password,
            )
            row = conn.execute(
                """
                insert into public.memberships (
                  tenant_id, user_id, role_id, department_id, direct_manager_membership_id,
                  status, full_name, work_email, phone, whatsapp,
                  whatsapp_enabled, whatsapp_opt_in, whatsapp_notification_types,
                  quiet_hours_start, quiet_hours_end,
                  title, hierarchy_level, joined_at, metadata
                )
                values (
                  %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s,
                  %s, %s, %s, %s, %s,
                  %s, %s, timezone('utc', now()), %s
                )
                returning id
                """,
                (
                    request.tenant_id,
                    user_id,
                    request.role_id,
                    request.department_id,
                    request.direct_manager_membership_id,
                    request.full_name,
                    request.work_email,
                    request.phone,
                    request.whatsapp,
                    request.whatsapp_enabled,
                    request.whatsapp_opt_in,
                    Jsonb(request.whatsapp_notification_types),
                    request.quiet_hours_start,
                    request.quiet_hours_end,
                    request.title,
                    request.hierarchy_level,
                    Jsonb({"source": "api", "username": request.username, "notificationEmail": request.work_email, "notificationWhatsapp": request.whatsapp}),
                ),
            ).fetchone()
            conn.execute("select public.vulcan_refresh_membership_closure(%s)", (request.tenant_id,))
            self.write_audit(conn, context, request.tenant_id, "membership.created", "membership", row["id"], {"full_name": request.full_name})
            conn.commit()
            membership = self._fetch_membership(conn, row["id"])
            if not membership:
                raise ValueError("membership was not persisted")
            return dict(membership)

    def update_membership(self, context: AuthContext, membership_id: UUID, request: MembershipUpdate) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            existing = conn.execute(
                "select tenant_id, user_id, direct_manager_membership_id, hierarchy_level, full_name, work_email from public.memberships where id = %s and status = 'active'",
                (membership_id,),
            ).fetchone()
            if not existing:
                return None
            tenant_id = existing["tenant_id"]
            manager_was_sent = "direct_manager_membership_id" in request.model_fields_set
            manager_id = request.direct_manager_membership_id if manager_was_sent else existing["direct_manager_membership_id"]
            hierarchy_level = request.hierarchy_level if request.hierarchy_level is not None else existing["hierarchy_level"]
            self._ensure_hierarchy_write(conn, access, tenant_id, membership_id, manager_id, hierarchy_level)
            self._assert_department_visible(conn, access, request.department_id)
            self._assert_manager_is_safe(conn, tenant_id, membership_id, manager_id)
            if request.username or request.password or request.work_email or request.full_name:
                self._upsert_auth_user(
                    conn,
                    user_id=existing["user_id"],
                    email=request.work_email or existing["work_email"],
                    full_name=request.full_name or existing["full_name"],
                    username=request.username,
                    password=request.password,
                )
            row = conn.execute(
                """
                update public.memberships
                set role_id = coalesce(%s, role_id),
                    department_id = coalesce(%s, department_id),
                    direct_manager_membership_id = case when %s then %s else direct_manager_membership_id end,
                    status = coalesce(%s, status),
                    full_name = coalesce(%s, full_name),
                    work_email = coalesce(%s, work_email),
                    phone = coalesce(%s, phone),
                    whatsapp = coalesce(%s, whatsapp),
                    whatsapp_enabled = coalesce(%s, whatsapp_enabled),
                    whatsapp_opt_in = coalesce(%s, whatsapp_opt_in),
                    whatsapp_notification_types = coalesce(%s, whatsapp_notification_types),
                    quiet_hours_start = coalesce(%s::time, quiet_hours_start),
                    quiet_hours_end = coalesce(%s::time, quiet_hours_end),
                    title = coalesce(%s, title),
                    hierarchy_level = coalesce(%s, hierarchy_level),
                    updated_at = timezone('utc', now())
                where id = %s
                returning id, tenant_id
                """,
                (
                    request.role_id,
                    request.department_id,
                    manager_was_sent,
                    manager_id,
                    request.status,
                    request.full_name,
                    request.work_email,
                    request.phone,
                    request.whatsapp,
                    request.whatsapp_enabled,
                    request.whatsapp_opt_in,
                    Jsonb(request.whatsapp_notification_types) if request.whatsapp_notification_types is not None else None,
                    request.quiet_hours_start,
                    request.quiet_hours_end,
                    request.title,
                    request.hierarchy_level,
                    membership_id,
                ),
            ).fetchone()
            if not row:
                return None
            conn.execute("select public.vulcan_refresh_membership_closure(%s)", (tenant_id,))
            audit_fields = request.model_dump(exclude_none=True, mode="json")
            if "password" in audit_fields:
                audit_fields["password"] = "***"
            self.write_audit(conn, context, tenant_id, "membership.updated", "membership", membership_id, {"fields": audit_fields})
            conn.commit()
            membership = self._fetch_membership(conn, membership_id)
            return dict(membership) if membership else None

    def delete_membership(self, context: AuthContext, membership_id: UUID) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            existing = conn.execute(
                """
                select id, tenant_id, user_id, direct_manager_membership_id, hierarchy_level, full_name
                from public.memberships
                where id = %s and status = 'active'
                """,
                (membership_id,),
            ).fetchone()
            if not existing:
                return None
            tenant_id = existing["tenant_id"]
            self._ensure_hierarchy_write(
                conn,
                access,
                tenant_id,
                membership_id,
                existing["direct_manager_membership_id"],
                existing["hierarchy_level"],
                deleting=True,
            )
            conn.execute(
                """
                update public.memberships
                set direct_manager_membership_id = %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s
                  and direct_manager_membership_id = %s
                  and status = 'active'
                """,
                (existing["direct_manager_membership_id"], tenant_id, membership_id),
            )
            conn.execute(
                """
                update public.devices
                set owner_membership_id = null,
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and owner_membership_id = %s
                """,
                (Jsonb({"ownerRemovedByHierarchyDelete": str(membership_id)}), tenant_id, membership_id),
            )
            row = conn.execute(
                """
                update public.memberships
                set status = 'revoked',
                    direct_manager_membership_id = null,
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where id = %s
                returning id, tenant_id as "tenantId", user_id as "userId",
                          role_id as "roleId", department_id as "departmentId",
                          direct_manager_membership_id as "directManagerMembershipId",
                          status::text, full_name as "fullName", work_email as "workEmail",
                          phone, whatsapp, title, hierarchy_level as "hierarchyLevel"
                """,
                (Jsonb({"deletedAt": datetime.now(timezone.utc).isoformat(), "deletedBy": context.user_id}), membership_id),
            ).fetchone()
            conn.execute("select public.vulcan_refresh_membership_closure(%s)", (tenant_id,))
            self.write_audit(conn, context, tenant_id, "membership.deleted", "membership", membership_id, {"full_name": existing["full_name"]})
            conn.commit()
            return dict(row) if row else None

    def update_membership_manager(self, context: AuthContext, membership_id: UUID, manager_id: UUID | None) -> dict | None:
        return self.update_membership(
            context,
            membership_id,
            MembershipUpdate(directManagerMembershipId=manager_id),
        )

    def list_users(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return USERS
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._membership_filter(access)
            return list(conn.execute(
                f"""
                select m.user_id as id,
                       m.tenant_id as "tenantId",
                       m.full_name as name,
                       coalesce(m.work_email::text, au.email, '') as email,
                       m.phone,
                       m.whatsapp,
                       m.title,
                       m.hierarchy_level as "hierarchyLevel",
                       m.direct_manager_membership_id as "managerId",
                       coalesce(r.slug, r.name, 'member') as role,
                       m.status::text as status
                from public.memberships m
                left join auth.users au on au.id = m.user_id
                left join public.roles r on r.id = m.role_id
                where m.status = 'active' and {condition}
                order by m.hierarchy_level nulls last, m.full_name
                """,
                params,
            ).fetchall())

    def list_hierarchy(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return HIERARCHY
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._membership_filter(access)
            return list(conn.execute(
                f"""
                select m.id,
                       m.tenant_id as "tenantId",
                       m.user_id as "userId",
                       m.role_id as "roleId",
                       m.direct_manager_membership_id as "parentId",
                       m.full_name as name,
                       coalesce(m.title, 'Member') as title,
                       coalesce(d.name, 'Unassigned') as department,
                       coalesce(m.work_email::text, au.email, '') as email,
                       m.phone,
                       m.whatsapp,
                       coalesce(m.whatsapp_enabled, true) as "whatsappEnabled",
                       coalesce(m.whatsapp_opt_in, false) as "whatsappOptIn",
                       coalesce(m.whatsapp_notification_types, '[]'::jsonb) as "whatsappNotificationTypes",
                       m.quiet_hours_start::text as "quietHoursStart",
                       m.quiet_hours_end::text as "quietHoursEnd",
                       coalesce(m.hierarchy_level, 0) as "hierarchyLevel",
                       (
                         select count(*)
                         from public.memberships child
                         where child.tenant_id = m.tenant_id
                           and child.direct_manager_membership_id = m.id
                           and child.status = 'active'
                       )::int as "directReports",
                       case
                         when coalesce(r.scope, 'self') = 'global' then 'global'
                         when coalesce(r.scope, 'self') = 'tenant' then 'tenant'
                         when coalesce(r.scope, 'self') = 'hierarchy' then 'subtree'
                         else 'self'
                       end as "visibleScope"
                from public.memberships m
                left join auth.users au on au.id = m.user_id
                left join public.departments d on d.id = m.department_id
                left join public.roles r on r.id = m.role_id
                where m.status = 'active' and {condition}
                order by coalesce(m.hierarchy_level, 0), m.full_name
                """,
                params,
            ).fetchall())

    def list_devices(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return DEVICES
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_team_tables(conn)
            self._repair_local_test_agent_scope(conn, access)
            condition, params = self._owner_filter(access, "d.owner_membership_id", "d.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "d")
            agent_only_condition = "and coalesce(d.metadata ->> 'source', '') = 'vulcan-agent' and left(d.hostname, 12) <> 'VULCAN-DEMO-'" if access.local_test else ""
            return list(conn.execute(
                f"""
                select d.id, d.tenant_id as "tenantId",
                       d.owner_membership_id as "ownerMembershipId",
                       coalesce(m.full_name, 'Unassigned') as owner,
                       d.hostname, d.os, d.status,
                       coalesce(d.last_seen_at, d.created_at)::text as "lastSeenAt",
                       d.metadata ->> 'collectionQuality' as "collectionQuality",
                       coalesce((d.metadata ->> 'queueDepth')::int, 0) as "queueDepth",
                       nullif(d.metadata ->> 'lastError', '') as "lastError",
                       d.metadata ->> 'localIp' as "localIp",
                       d.metadata ->> 'agentVersion' as "agentVersion",
                       d.metadata ->> 'osUser' as "osUser",
                       coalesce(d.metadata ->> 'adoptionStatus', case when d.owner_membership_id is null then 'pending' else 'adopted' end) as "adoptionStatus",
                       d.metadata ->> 'adoptionCode' as "adoptionCode",
                       nullif(d.metadata ->> 'teamId', '')::uuid as "teamId",
                       t.name as "teamName"
                from public.devices d
                left join public.memberships m on m.id = d.owner_membership_id
                left join public.teams t on t.id = nullif(d.metadata ->> 'teamId', '')::uuid and t.tenant_id = d.tenant_id and t.status = 'active'
                where {condition}
                  and {real_data_condition}
                  {agent_only_condition}
                order by d.last_seen_at desc nulls last, d.hostname
                limit 100
                """,
                params,
            ).fetchall())

    def list_pending_adoption_devices(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return [
                {**device, "ownerMembershipId": None, "owner": "Aguardando adoção", "adoptionStatus": "pending", "adoptionCode": "VLC-DEMO"}
                for device in DEVICES
                if not device.get("ownerMembershipId")
            ]
        with self._connect() as conn:
            access = self._access(conn, context)
            if access.scope not in {"tenant", "global"} and not access.is_root:
                return []
            self._ensure_team_tables(conn)
            condition = "d.tenant_id = %s" if not access.is_root else "true"
            params: tuple[object, ...] = (access.tenant_id,) if not access.is_root else ()
            return list(conn.execute(
                f"""
                select d.id, d.tenant_id as "tenantId",
                       d.owner_membership_id as "ownerMembershipId",
                       'Aguardando adoção' as owner,
                       d.hostname, d.os, d.status,
                       coalesce(d.last_seen_at, d.created_at)::text as "lastSeenAt",
                       d.metadata ->> 'collectionQuality' as "collectionQuality",
                       coalesce((d.metadata ->> 'queueDepth')::int, 0) as "queueDepth",
                       nullif(d.metadata ->> 'lastError', '') as "lastError",
                       d.metadata ->> 'localIp' as "localIp",
                       d.metadata ->> 'agentVersion' as "agentVersion",
                       d.metadata ->> 'osUser' as "osUser",
                       coalesce(d.metadata ->> 'adoptionStatus', 'pending') as "adoptionStatus",
                       d.metadata ->> 'adoptionCode' as "adoptionCode",
                       nullif(d.metadata ->> 'teamId', '')::uuid as "teamId",
                       t.name as "teamName"
                from public.devices d
                left join public.teams t on t.id = nullif(d.metadata ->> 'teamId', '')::uuid and t.tenant_id = d.tenant_id and t.status = 'active'
                where {condition}
                  and d.owner_membership_id is null
                  and coalesce(d.metadata ->> 'source', '') = 'vulcan-agent'
                  and coalesce(d.metadata ->> 'adoptionIgnored', 'false') <> 'true'
                order by d.last_seen_at desc nulls last, d.created_at desc
                limit 50
                """,
                params,
            ).fetchall())

    def update_device_owner(self, context: AuthContext, device_id: UUID, request: DeviceOwnerUpdate) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            if not access.is_root and request.tenant_id != access.tenant_id:
                raise ValueError("device tenant outside current context")

            condition, params = self._owner_filter(access, "d.owner_membership_id", "d.tenant_id")
            device = conn.execute(
                f"""
                select d.id, d.tenant_id, d.owner_membership_id
                from public.devices d
                where d.tenant_id = %s
                  and d.id = %s
                  and {condition}
                limit 1
                """,
                (request.tenant_id, device_id, *params),
            ).fetchone()
            if not device:
                return None

            if request.owner_membership_id:
                target_condition, target_params = self._membership_filter(access)
                target = conn.execute(
                    f"""
                    select m.id
                    from public.memberships m
                    where m.tenant_id = %s
                      and m.id = %s
                      and {target_condition}
                    limit 1
                    """,
                    (request.tenant_id, request.owner_membership_id, *target_params),
                ).fetchone()
                if not target:
                    raise ValueError("target membership outside visible hierarchy")

            conn.execute(
                """
                update public.devices
                set owner_membership_id = %s,
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                """,
                (
                    request.owner_membership_id,
                    Jsonb(
                        {
                            "ownerChangedAt": datetime.now(timezone.utc).isoformat(),
                            "ownerChangedBy": context.user_id,
                            "previousOwnerMembershipId": str(device["owner_membership_id"]) if device["owner_membership_id"] else None,
                        }
                    ),
                    request.tenant_id,
                    device_id,
                ),
            )
            self.write_audit(
                conn,
                context,
                request.tenant_id,
                "device.owner.updated",
                "device",
                device_id,
                {
                    "previous_owner_membership_id": str(device["owner_membership_id"]) if device["owner_membership_id"] else None,
                    "owner_membership_id": str(request.owner_membership_id) if request.owner_membership_id else None,
                },
            )
            conn.commit()

        refreshed = self.list_devices(context)
        for item in refreshed:
            if item["id"] == device_id:
                return item
        return None

    def move_device(self, context: AuthContext, device_id: UUID, request: DeviceMoveRequest) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            if not access.is_root and request.tenant_id != access.tenant_id:
                raise ValueError("device tenant outside current context")
            if request.owner_membership_id:
                self._assert_membership_visible(conn, access, request.owner_membership_id)
            if request.team_id:
                self._ensure_team_tables(conn)
                team = conn.execute(
                    "select id from public.teams where tenant_id = %s and id = %s and status = 'active'",
                    (request.tenant_id, request.team_id),
                ).fetchone()
                if not team:
                    raise ValueError("team not found")
            row = conn.execute(
                """
                update public.devices
                set owner_membership_id = coalesce(%s, owner_membership_id),
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                returning id
                """,
                (
                    request.owner_membership_id,
                    Jsonb(
                        {
                            "teamId": str(request.team_id) if request.team_id else None,
                            "movedAt": datetime.now(timezone.utc).isoformat(),
                            "movedBy": context.user_id,
                        }
                    ),
                    request.tenant_id,
                    device_id,
                ),
            ).fetchone()
            if not row:
                return None
            self.write_audit(conn, context, request.tenant_id, "device.moved", "device", device_id, request.model_dump(mode="json", exclude_none=True))
            conn.commit()
        return next((item for item in self.list_devices(context) if item["id"] == device_id), None)

    def adopt_device(self, context: AuthContext, device_id: UUID, request: DeviceAdoptionRequest) -> dict:
        if not self.enabled:
            device = next((item for item in DEVICES if item["id"] == device_id), None)
            if not device:
                raise ValueError("device not found")
            return {"device": {**device, "adoptionStatus": "adopted"}, "membership": None, "team": None, "adopted": True}
        membership_id: UUID | None = request.membership_id
        membership: dict | None = None
        if request.mode == "new_user":
            if request.user is None:
                raise ValueError("new_user adoption requires user payload")
            membership = self.create_membership(context, request.user)
            membership_id = membership["id"]
        elif request.mode == "existing_user" and membership_id is None:
            raise ValueError("existing_user adoption requires membershipId")
        elif request.mode == "dry":
            membership_id = None

        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_team_write(access, request.tenant_id)
            self._ensure_team_tables(conn)
            device = conn.execute(
                """
                select id, tenant_id, owner_membership_id, metadata
                from public.devices
                where tenant_id = %s and id = %s
                """,
                (request.tenant_id, device_id),
            ).fetchone()
            if not device:
                raise ValueError("device not found")

            if request.mode == "existing_user":
                self._assert_membership_visible(conn, access, membership_id)

            if membership_id and request.team_id:
                team = conn.execute(
                    "select id from public.teams where tenant_id = %s and id = %s and status = 'active'",
                    (request.tenant_id, request.team_id),
                ).fetchone()
                if not team:
                    raise ValueError("team not found")
                conn.execute(
                    """
                    insert into public.team_members (tenant_id, team_id, membership_id, role_in_team)
                    values (%s, %s, %s, 'membro')
                    on conflict (tenant_id, team_id, membership_id) do update
                    set role_in_team = excluded.role_in_team,
                        updated_at = timezone('utc', now())
                    """,
                    (request.tenant_id, request.team_id, membership_id),
                )

            row = conn.execute(
                """
                update public.devices
                set owner_membership_id = %s,
                    status = case when %s::uuid is null then 'pending' else 'online' end,
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                returning id
                """,
                (
                    membership_id,
                    membership_id,
                    Jsonb(
                        {
                            "adoptionStatus": "pending_details" if request.mode == "dry" else "adopted",
                            "adoptedAt": datetime.now(timezone.utc).isoformat(),
                            "adoptedBy": context.user_id,
                            "teamId": str(request.team_id) if request.team_id else None,
                            "collectionPolicy": request.policy,
                        }
                    ),
                    request.tenant_id,
                    device_id,
                ),
            ).fetchone()
            if not row:
                raise ValueError("device not found")
            self.write_audit(
                conn,
                context,
                request.tenant_id,
                "device.adopted",
                "device",
                device_id,
                {
                    "previous_owner_membership_id": str(device["owner_membership_id"]) if device["owner_membership_id"] else None,
                    "owner_membership_id": str(membership_id) if membership_id else None,
                    "team_id": str(request.team_id) if request.team_id else None,
                    "mode": request.mode,
                    "policy": request.policy,
                },
            )
            conn.commit()
            refreshed_device = conn.execute(
                """
                select d.id, d.tenant_id as "tenantId",
                       d.owner_membership_id as "ownerMembershipId",
                       coalesce(m.full_name, 'Aguardando adoção') as owner,
                       d.hostname, d.os, d.status,
                       coalesce(d.last_seen_at, d.created_at)::text as "lastSeenAt",
                       d.metadata ->> 'collectionQuality' as "collectionQuality",
                       coalesce((d.metadata ->> 'queueDepth')::int, 0) as "queueDepth",
                       nullif(d.metadata ->> 'lastError', '') as "lastError",
                       d.metadata ->> 'localIp' as "localIp",
                       d.metadata ->> 'agentVersion' as "agentVersion",
                       d.metadata ->> 'osUser' as "osUser",
                       coalesce(d.metadata ->> 'adoptionStatus', case when d.owner_membership_id is null then 'pending' else 'adopted' end) as "adoptionStatus",
                       d.metadata ->> 'adoptionCode' as "adoptionCode",
                       nullif(d.metadata ->> 'teamId', '')::uuid as "teamId",
                       t.name as "teamName"
                from public.devices d
                left join public.memberships m on m.id = d.owner_membership_id
                left join public.teams t on t.id = nullif(d.metadata ->> 'teamId', '')::uuid and t.tenant_id = d.tenant_id and t.status = 'active'
                where d.tenant_id = %s and d.id = %s
                limit 1
                """,
                (request.tenant_id, device_id),
            ).fetchone()
            team = None
            if request.team_id:
                team_row = conn.execute(
                    """
                    select id, tenant_id as "tenantId", name, description, color
                    from public.teams
                    where tenant_id = %s and id = %s
                    limit 1
                    """,
                    (request.tenant_id, request.team_id),
                ).fetchone()
                team = dict(team_row) if team_row else None
            return {"device": dict(refreshed_device) if refreshed_device else None, "membership": membership, "team": team, "adopted": True}

    def list_activity_events(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return ACTIVITY_EVENTS
        with self._connect() as conn:
            access = self._access(conn, context)
            self._repair_local_test_agent_scope(conn, access)
            condition, params = self._owner_filter(access, "e.membership_id", "e.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "e")
            return list(conn.execute(
                f"""
                select e.id, e.tenant_id as "tenantId",
                       e.event_type as "eventType",
                       coalesce(e.app_name, 'Unknown') as "appName",
                       coalesce(d.name, 'Operations') as department,
                       e.occurred_at::text as "occurredAt",
                       greatest(1, ceil(coalesce(e.duration_seconds, 0)::numeric / 60))::int as "durationMinutes"
                from public.activity_events e
                left join public.memberships m on m.id = e.membership_id
                left join public.departments d on d.id = m.department_id
                where {condition}
                  and {real_data_condition}
                order by e.occurred_at desc
                limit 200
                """,
                params,
            ).fetchall())

    def list_dashboard_metrics(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return METRICS
        with self._connect() as conn:
            access = self._access(conn, context)
            self._repair_local_test_agent_scope(conn, access)
            membership_condition, membership_params = self._membership_filter(access, "m")
            event_condition, event_params = self._owner_filter(access, "membership_id", "tenant_id")
            insight_condition, insight_params = self._owner_filter(access, "membership_id", "tenant_id")
            event_real_filter = self._real_agent_data_filter(access, "activity_events")
            insight_real_filter = self._real_agent_data_filter(access, "ai_insights")
            active_users = conn.execute(
                f"select count(*) as count from public.memberships m where {membership_condition} and m.status = 'active'",
                membership_params,
            ).fetchone()["count"]
            events = conn.execute(
                f"select count(*) as count from public.activity_events where {event_condition} and {event_real_filter}",
                event_params,
            ).fetchone()["count"]
            insight_row = conn.execute(
                f"""
                select
                  count(*) filter (where impact in ('high', 'critical')) as bottlenecks,
                  count(*) as insights,
                  coalesce(sum(automation_savings_hours), 0) as automation
                from public.ai_insights
                where {insight_condition}
                  and {insight_real_filter}
                """,
                insight_params,
            ).fetchone()
            return [
                {"id": "active-users", "label": "Usuários ativos", "value": str(active_users), "trend": "escopo visível", "tone": "positive"},
                {"id": "events", "label": "Eventos processados", "value": f"{events}", "trend": "dados reais do agente", "tone": "neutral"},
                {"id": "bottlenecks", "label": "Gargalos detectados", "value": str(insight_row["bottlenecks"]), "trend": "alto impacto", "tone": "warning"},
                {"id": "insights", "label": "Insights de IA", "value": str(insight_row["insights"]), "trend": "IA híbrida", "tone": "positive"},
                {"id": "automation", "label": "Potencial de automação", "value": f"{float(insight_row['automation']):.0f}h", "trend": "estimativa mensal", "tone": "critical"},
            ]

    def agent_enroll(self, request: AgentEnrollRequest) -> AgentEnrollResponse:
        if not self.enabled:
            return AgentEnrollResponse(
                accepted=True,
                tenantId=request.tenant_id,
                deviceId=request.device_id or UUID("00000000-0000-0000-0000-000000500001"),
                heartbeatIntervalSeconds=60,
                syncIntervalSeconds=30,
            )
        with self._connect() as conn:
            membership_id = self._resolve_agent_membership(
                conn,
                request.tenant_id,
                request.membership_id,
                linked_user=request.linked_user,
                os_user=request.os_user,
            )
            adoption_code = f"VLC-{str(request.machine_fingerprint).upper()[:6]}"
            row = conn.execute(
                """
                insert into public.devices (
                  id, tenant_id, owner_membership_id, hostname, os,
                  device_fingerprint, status, last_seen_at, metadata
                )
                values (
                  coalesce(%s, gen_random_uuid()), %s, %s, %s, %s,
                  %s, %s, timezone('utc', now()), %s
                )
                on conflict (tenant_id, device_fingerprint) do update
                set owner_membership_id = coalesce(excluded.owner_membership_id, public.devices.owner_membership_id),
                    hostname = excluded.hostname,
                    os = excluded.os,
                    status = case when coalesce(excluded.owner_membership_id, public.devices.owner_membership_id) is null then 'pending' else 'online' end,
                    last_seen_at = timezone('utc', now()),
                    metadata = public.devices.metadata || excluded.metadata,
                    updated_at = timezone('utc', now())
                returning id
                """,
                (
                    request.device_id,
                    request.tenant_id,
                    membership_id,
                    request.hostname,
                    request.os_version or "Windows",
                    request.machine_fingerprint,
                    "online" if membership_id else "pending",
                    Jsonb(
                        {
                            "source": "vulcan-agent",
                            "agentVersion": request.agent_version,
                            "linkedUser": request.linked_user,
                            "osUser": request.os_user,
                            "osVersion": request.os_version,
                            "adoptionStatus": "adopted" if membership_id else "pending",
                            "adoptionCode": adoption_code,
                            "roleLevel": request.role_level,
                            "department": request.department,
                            "managerMembershipId": str(request.manager_membership_id) if request.manager_membership_id else None,
                            "note": request.note,
                        }
                    ),
                ),
            ).fetchone()
            self.write_agent_audit(
                conn,
                request.tenant_id,
                "agent.enrolled",
                "device",
                row["id"],
                {"hostname": request.hostname, "machine_fingerprint": request.machine_fingerprint, "membership_id": str(membership_id) if membership_id else None},
            )
            conn.commit()
            return AgentEnrollResponse(
                accepted=True,
                tenantId=request.tenant_id,
                deviceId=row["id"],
                heartbeatIntervalSeconds=60,
                syncIntervalSeconds=30,
            )

    def _ensure_pending_agent_device(
        self,
        conn: psycopg.Connection,
        tenant_id: UUID,
        device_id: UUID | None,
        machine_fingerprint: str,
        hostname: str,
        os_name: str = "Linux",
        metadata: dict | None = None,
    ) -> dict:
        row = conn.execute(
            """
            insert into public.devices (
              id, tenant_id, owner_membership_id, hostname, os,
              device_fingerprint, status, last_seen_at, metadata
            )
            values (
              coalesce(%s, gen_random_uuid()), %s, null, %s, %s,
              %s, 'pending', timezone('utc', now()), %s
            )
            on conflict (tenant_id, device_fingerprint) do update
            set hostname = excluded.hostname,
                os = excluded.os,
                status = case when public.devices.owner_membership_id is null then 'pending' else public.devices.status end,
                last_seen_at = timezone('utc', now()),
                metadata = public.devices.metadata || excluded.metadata,
                updated_at = timezone('utc', now())
            returning id, owner_membership_id, metadata
            """,
            (
                device_id,
                tenant_id,
                hostname,
                os_name,
                machine_fingerprint,
                Jsonb(
                    {
                        "source": "vulcan-agent",
                        "adoptionStatus": "pending",
                        "adoptionCode": f"VLC-{str(machine_fingerprint).upper()[:6]}",
                        **(metadata or {}),
                    }
                ),
            ),
        ).fetchone()
        return row

    def agent_heartbeat(self, request: AgentHeartbeatRequest) -> AgentHeartbeatResponse:
        if self.enabled:
            with self._connect() as conn:
                heartbeat_os = str(request.metadata.get("osVersion") or ("Windows" if request.metadata.get("computerName") else "Linux"))
                row = conn.execute(
                    """
                    update public.devices
                    set status = case when owner_membership_id is null then 'pending' else %s end,
                        hostname = %s,
                        os = %s,
                        last_seen_at = timezone('utc', now()),
                        metadata = metadata || %s,
                        updated_at = timezone('utc', now())
                    where tenant_id = %s
                      and (
                        (%s::uuid is not null and id = %s)
                        or device_fingerprint = %s
                      )
                    returning id, owner_membership_id, metadata
                    """,
                    (
                        request.status if request.status in {"online", "offline", "syncing"} else "online",
                        request.hostname,
                        heartbeat_os,
                        Jsonb(
                            {
                                "agentVersion": request.agent_version,
                                "queueDepth": request.queue_depth,
                                "lastError": request.last_error,
                                **request.metadata,
                            }
                        ),
                        request.tenant_id,
                        request.device_id,
                        request.device_id,
                        request.machine_fingerprint,
                    ),
                ).fetchone()
                if not row:
                    row = self._ensure_pending_agent_device(
                        conn,
                        request.tenant_id,
                        request.device_id,
                        request.machine_fingerprint,
                        request.hostname,
                        os_name=heartbeat_os,
                        metadata={
                            "agentVersion": request.agent_version,
                            "queueDepth": request.queue_depth,
                            "lastError": request.last_error,
                            **request.metadata,
                        },
                    )
                if row and row["owner_membership_id"] is None:
                    metadata = row["metadata"] or {}
                    membership_id = self._resolve_agent_membership(
                        conn,
                        request.tenant_id,
                        None,
                        linked_user=metadata.get("linkedUser"),
                        os_user=metadata.get("osUser"),
                    )
                    if membership_id:
                        conn.execute(
                            """
                            update public.devices
                            set owner_membership_id = %s,
                                metadata = metadata || %s,
                                updated_at = timezone('utc', now())
                            where tenant_id = %s and id = %s
                            """,
                            (
                                membership_id,
                                Jsonb({"autoLinkedMembershipId": str(membership_id), "adoptionStatus": "adopted"}),
                                request.tenant_id,
                                row["id"],
                            ),
                        )
                self.write_agent_audit(
                    conn,
                    request.tenant_id,
                    "agent.heartbeat",
                    "device",
                    request.device_id,
                    {"hostname": request.hostname, "queue_depth": request.queue_depth},
                )
                conn.commit()
        return AgentHeartbeatResponse(accepted=True, serverTime=datetime.now(timezone.utc))

    def agent_events(self, request: AgentEventsRequest) -> AgentEventsResponse:
        if not self.enabled:
            return AgentEventsResponse(accepted=True, received=len(request.events), stored=len(request.events))
        stored = 0
        with self._connect() as conn:
            device = conn.execute(
                """
                select id, owner_membership_id, metadata
                from public.devices
                where tenant_id = %s
                  and (
                    (%s::uuid is not null and id = %s)
                    or device_fingerprint = %s
                  )
                limit 1
                """,
                (request.tenant_id, request.device_id, request.device_id, request.machine_fingerprint),
            ).fetchone()
            if not device:
                device = self._ensure_pending_agent_device(
                    conn,
                    request.tenant_id,
                    request.device_id,
                    request.machine_fingerprint,
                    request.hostname,
                )
            device_id = device["id"] if device else request.device_id
            event_membership_id = request.membership_id or (device["owner_membership_id"] if device else None)
            if event_membership_id is None and device and (device["metadata"] or {}).get("linkedUser") == "teste":
                event_membership_id = self._resolve_agent_membership(conn, request.tenant_id, None, linked_user="teste")
                if event_membership_id and device_id:
                    conn.execute(
                        """
                        update public.devices
                        set owner_membership_id = %s,
                            metadata = metadata || %s,
                            updated_at = timezone('utc', now())
                        where tenant_id = %s and id = %s
                        """,
                        (
                            event_membership_id,
                            Jsonb({"autoLinkedMembershipId": str(event_membership_id)}),
                            request.tenant_id,
                            device_id,
                        ),
                    )
            inserted_events = 0
            duplicate_events = 0
            event_type_counts: dict[str, int] = defaultdict(int)
            for event in request.events:
                event_type = event.event_type or "app_focus_ended"
                row = conn.execute(
                    """
                    insert into public.activity_events (
                      tenant_id, membership_id, device_id, source_event_id, event_type, app_name,
                      window_title, category, duration_seconds, occurred_at, metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (tenant_id, source_event_id) where source_event_id is not null do nothing
                    returning id
                    """,
                    (
                        request.tenant_id,
                        event_membership_id,
                        device_id,
                        event.event_id,
                        event_type,
                        event.app_name,
                        event.window_title,
                        event.category,
                        event.duration_seconds,
                        event.started_at,
                        Jsonb(
                            {
                                **event.metadata,
                                "source": "vulcan-agent",
                                "eventId": event.event_id,
                                "eventType": event_type,
                                "endedAt": event.ended_at.isoformat(),
                                "hostname": request.hostname,
                                "osUser": event.os_user,
                                "machineFingerprint": request.machine_fingerprint,
                            }
                        ),
                    ),
                ).fetchone()
                if not row:
                    duplicate_events += 1
                    continue
                if event_membership_id:
                    for metric_key, metric_label, metric_value in self._metrics_for_agent_event(event_type, event):
                        conn.execute(
                            """
                            insert into public.operational_metrics (
                              tenant_id, membership_id, metric_key, metric_label,
                              value_numeric, period_start, period_end, metadata
                            )
                            values (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                request.tenant_id,
                                event_membership_id,
                                metric_key,
                                metric_label,
                                metric_value,
                                event.started_at,
                                event.ended_at,
                                Jsonb({"source": "vulcan-agent", "eventId": event.event_id, "category": event.category, "eventType": event_type}),
                            ),
                        )
                inserted_events += 1
                event_type_counts[event_type] += 1
                stored += 1
            if device_id:
                conn.execute(
                    """
                    update public.devices
                    set status = 'syncing',
                        last_seen_at = timezone('utc', now()),
                        metadata = metadata || %s,
                        updated_at = timezone('utc', now())
                    where id = %s and tenant_id = %s
                    """,
                    (
                        Jsonb(
                            {
                                "lastSyncAt": datetime.now(timezone.utc).isoformat(),
                                "lastSyncedEvents": stored,
                                "lastDuplicateEvents": duplicate_events,
                            }
                        ),
                        device_id,
                        request.tenant_id,
                    ),
                )
            self.write_agent_audit(
                conn,
                request.tenant_id,
                "agent.events.batch_stored",
                "device",
                device_id,
                {
                    "hostname": request.hostname,
                    "received": len(request.events),
                    "inserted": inserted_events,
                    "duplicates": duplicate_events,
                    "event_type_counts": dict(event_type_counts),
                },
            )
            conn.commit()
        return AgentEventsResponse(accepted=True, received=len(request.events), stored=len(request.events))

    def _metrics_for_agent_event(self, event_type: str, event: AgentEvent) -> list[tuple[str, str, float]]:
        duration = float(event.duration_seconds or 0)
        label = event.app_name or "Vulcan Agent"
        if event_type in {"app_focus_ended", "foreground_application_usage", "foreground_application_change"} and duration > 0:
            return [("app_usage_seconds", label, duration), ("active_seconds", "Tempo ativo", duration)]
        if event_type == "idle_ended" and duration > 0:
            return [("idle_seconds", "Tempo ocioso", duration)]
        if event_type == "context_switch":
            return [("context_switch_count", "Trocas de contexto", 1.0)]
        if event_type == "agent_error":
            return [("agent_error_count", "Erros do agente", 1.0)]
        if event_type == "collection_quality":
            score = {"high": 3.0, "medium": 2.0, "low": 1.0, "blocked_by_os": 0.0}.get(str(event.metadata.get("quality")), 0.0)
            return [("collection_quality_score", str(event.metadata.get("quality") or "desconhecida"), score)]
        if event_type == "agent_health":
            value = float(event.metadata.get("agentMemoryMb") or 0)
            return [("agent_memory_mb", "Memória do agente", value)]
        return []

    def agent_logs(self, request: AgentLogsRequest) -> AgentEventsResponse:
        if self.enabled:
            with self._connect() as conn:
                for entry in request.logs:
                    self.write_agent_audit(
                        conn,
                        request.tenant_id,
                        f"agent.log.{entry.level.lower()}",
                        "agent_log",
                        request.device_id,
                        {
                            "message": entry.message,
                            "createdAt": entry.created_at.isoformat(),
                            "machineFingerprint": request.machine_fingerprint,
                            **entry.metadata,
                        },
                    )
                conn.commit()
        return AgentEventsResponse(accepted=True, received=len(request.logs), stored=len(request.logs))

    def list_operational_metrics(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            self._repair_local_test_agent_scope(conn, access)
            condition, params = self._owner_filter(access, "om.membership_id", "om.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "om")
            return list(conn.execute(
                f"""
                select om.id, om.tenant_id as "tenantId", om.membership_id as "membershipId",
                       om.department_id as "departmentId", om.metric_key as "metricKey",
                       om.metric_label as "metricLabel", om.value_numeric as "valueNumeric",
                       om.value_text as "valueText", om.period_start as "periodStart", om.period_end as "periodEnd"
                from public.operational_metrics om
                where {condition}
                  and {real_data_condition}
                order by om.period_start desc
                limit 200
                """,
                params,
            ).fetchall())

    def _period_interval(self, period: str) -> str:
        return {
            "24h": "24 hours",
            "7d": "7 days",
            "30d": "30 days",
            "90d": "90 days",
        }.get(period, "24 hours")

    def list_detailed_metrics(
        self,
        context: AuthContext,
        *,
        period: str = "24h",
        team_id: UUID | None = None,
        membership_id: UUID | None = None,
        device_id: UUID | None = None,
        supervisor_id: UUID | None = None,
        department: str | None = None,
        title: str | None = None,
        os_name: str | None = None,
        category: str | None = None,
        agent_status: str | None = None,
        metric_type: str | None = None,
        app: str | None = None,
    ) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_team_tables(conn)
            condition, params = self._owner_filter(access, "e.membership_id", "e.tenant_id")
            filters = [condition, "e.occurred_at >= timezone('utc', now()) - (%s::interval)"]
            query_params: list[object] = [*params, self._period_interval(period)]
            if team_id:
                filters.append("tm.team_id = %s")
                query_params.append(team_id)
            if membership_id:
                self._assert_membership_visible(conn, access, membership_id)
                filters.append("e.membership_id = %s")
                query_params.append(membership_id)
            if device_id:
                filters.append("e.device_id = %s")
                query_params.append(device_id)
            if supervisor_id:
                self._assert_membership_visible(conn, access, supervisor_id)
                filters.append("m.direct_manager_membership_id = %s")
                query_params.append(supervisor_id)
            if department:
                filters.append("lower(coalesce(dpt.name, '')) like lower(%s)")
                query_params.append(f"%{department}%")
            if title:
                filters.append("lower(coalesce(m.title, '')) like lower(%s)")
                query_params.append(f"%{title}%")
            if os_name:
                filters.append("lower(coalesce(d.os, '')) like lower(%s)")
                query_params.append(f"%{os_name}%")
            if category:
                filters.append("lower(coalesce(e.category, '')) = lower(%s)")
                query_params.append(category)
            if agent_status:
                filters.append("lower(coalesce(d.status, '')) = lower(%s)")
                query_params.append(agent_status)
            if metric_type:
                normalized_metric_type = metric_type.strip().lower()
                if normalized_metric_type == "idle":
                    filters.append("(e.event_type in ('idle_started', 'idle_ended') or lower(coalesce(e.category, '')) = 'idle')")
                elif normalized_metric_type == "context_switch":
                    filters.append("e.event_type = 'context_switch'")
                elif normalized_metric_type == "agent":
                    filters.append("e.event_type in ('heartbeat', 'sync_status', 'collection_quality', 'agent_error', 'agent_health')")
                elif normalized_metric_type == "productive":
                    filters.append("lower(coalesce(e.category, '')) in ('productivity', 'business', 'development', 'desenvolvimento', 'gestão', 'gestao', 'produtividade')")
                elif normalized_metric_type == "improductive":
                    filters.append("lower(coalesce(e.category, '')) in ('idle', 'distraction', 'communication', 'ocioso', 'distração', 'distracao', 'comunicação', 'comunicacao')")
                else:
                    filters.append("lower(e.event_type) = lower(%s)")
                    query_params.append(metric_type)
            if app:
                filters.append("lower(coalesce(e.app_name, '')) like lower(%s)")
                query_params.append(f"%{app}%")
            real_data_condition = self._real_agent_data_filter(access, "e")
            filters.append(real_data_condition)
            return list(conn.execute(
                f"""
                select e.id::text,
                       e.tenant_id as "tenantId",
                       e.membership_id as "membershipId",
                       coalesce(m.full_name, 'Sem usuário') as "userName",
                       m.title as "userTitle",
                       m.direct_manager_membership_id as "supervisorId",
                       supervisor.full_name as "supervisorName",
                       tm.team_id as "teamId",
                       t.name as "teamName",
                       coalesce(dpt.name, 'Sem departamento') as department,
                       e.device_id as "deviceId",
                       coalesce(d.hostname, 'Sem dispositivo') as device,
                       coalesce(d.os, 'desconhecido') as os,
                       d.status as "agentStatus",
                       coalesce(e.app_name, 'Desconhecido') as app,
                       coalesce(e.category, 'operacional') as category,
                       e.event_type as "eventType",
                       coalesce(e.duration_seconds, 0)::int as "durationSeconds",
                       e.occurred_at::text as "occurredAt",
                       d.metadata ->> 'collectionQuality' as "collectionQuality"
                from public.activity_events e
                left join public.memberships m on m.id = e.membership_id
                left join public.memberships supervisor on supervisor.id = m.direct_manager_membership_id
                left join public.departments dpt on dpt.id = m.department_id
                left join public.devices d on d.id = e.device_id
                left join public.team_members tm on tm.tenant_id = e.tenant_id and tm.membership_id = e.membership_id
                left join public.teams t on t.id = tm.team_id and t.status = 'active'
                where {' and '.join(filters)}
                order by e.occurred_at desc
                limit 1000
                """,
                tuple(query_params),
            ).fetchall())

    def export_metrics_csv(
        self,
        context: AuthContext,
        *,
        period: str = "24h",
        team_id: UUID | None = None,
        membership_id: UUID | None = None,
        device_id: UUID | None = None,
        supervisor_id: UUID | None = None,
        department: str | None = None,
        title: str | None = None,
        os_name: str | None = None,
        category: str | None = None,
        agent_status: str | None = None,
        metric_type: str | None = None,
        app: str | None = None,
    ) -> str:
        rows = self.list_detailed_metrics(
            context,
            period=period,
            team_id=team_id,
            membership_id=membership_id,
            device_id=device_id,
            supervisor_id=supervisor_id,
            department=department,
            title=title,
            os_name=os_name,
            category=category,
            agent_status=agent_status,
            metric_type=metric_type,
            app=app,
        )
        output = StringIO()
        output.write("\ufeff")
        writer = csv.writer(output)
        writer.writerow(["gerado_em", datetime.now(timezone.utc).isoformat()])
        writer.writerow(["periodo", period])
        writer.writerow(["filtro_team_id", str(team_id or "")])
        writer.writerow(["filtro_membership_id", str(membership_id or "")])
        writer.writerow(["filtro_device_id", str(device_id or "")])
        writer.writerow(["filtro_supervisor_id", str(supervisor_id or "")])
        writer.writerow(["filtro_departamento", department or ""])
        writer.writerow(["filtro_cargo", title or ""])
        writer.writerow(["filtro_so", os_name or ""])
        writer.writerow(["filtro_categoria", category or ""])
        writer.writerow(["filtro_status_agente", agent_status or ""])
        writer.writerow(["filtro_tipo_metrica", metric_type or ""])
        writer.writerow(["filtro_app", app or ""])
        writer.writerow([])
        writer.writerow(["data_hora", "usuario", "equipe", "cargo", "supervisor", "departamento", "dispositivo", "so", "status_agente", "app", "categoria", "evento", "duracao_segundos", "qualidade_coleta"])
        for row in rows:
            writer.writerow([
                row["occurredAt"],
                row["userName"],
                row["teamName"] or "",
                row["userTitle"] or "",
                row["supervisorName"] or "",
                row["department"],
                row["device"],
                row["os"],
                row["agentStatus"] or "",
                row["app"],
                row["category"],
                row["eventType"],
                row["durationSeconds"],
                row["collectionQuality"] or "",
            ])
        return output.getvalue()

    def operational_intelligence(self, context: AuthContext) -> dict:
        now = datetime.now(timezone.utc)
        if not self.enabled:
            return self._empty_operational_intelligence(now, "Últimas 24 horas")

        with self._connect() as conn:
            access = self._access(conn, context)
            self._repair_local_test_agent_scope(conn, access)
            condition, params = self._owner_filter(access, "e.membership_id", "e.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "e")
            rows = conn.execute(
                f"""
                select e.id::text,
                       e.event_type,
                       coalesce(e.app_name, 'Desconhecido') as app_name,
                       nullif(e.window_title, '') as window_title,
                       nullif(e.category, '') as category,
                       coalesce(e.duration_seconds, 0)::float as duration_seconds,
                       e.occurred_at,
                       coalesce(e.metadata, '{{}}'::jsonb) as metadata
                from public.activity_events e
                where {condition}
                  and {real_data_condition}
                  and e.occurred_at >= timezone('utc', now()) - interval '24 hours'
                order by e.occurred_at asc
                limit 5000
                """,
                params,
            ).fetchall()

            device_condition, device_params = self._owner_filter(access, "d.owner_membership_id", "d.tenant_id")
            device_real_condition = self._real_agent_data_filter(access, "d")
            devices = conn.execute(
                f"""
                select d.hostname,
                       d.status,
                       coalesce(d.last_seen_at, d.created_at)::text as last_seen_at,
                       d.metadata ->> 'collectionQuality' as collection_quality,
                       coalesce((d.metadata ->> 'queueDepth')::int, 0) as queue_depth,
                       nullif(d.metadata ->> 'lastError', '') as last_error
                from public.devices d
                where {device_condition}
                  and {device_real_condition}
                  and coalesce(d.metadata ->> 'source', '') = 'vulcan-agent'
                order by d.last_seen_at desc nulls last
                limit 50
                """,
                device_params,
            ).fetchall()

        return self._build_operational_intelligence(rows, devices, now)

    def _empty_operational_intelligence(self, now: datetime, period_label: str) -> dict:
        return {
            "generatedAt": now,
            "periodLabel": period_label,
            "totalEvents": 0,
            "totalActiveSeconds": 0.0,
            "totalIdleSeconds": 0.0,
            "unidentifiedSeconds": 0.0,
            "trackedSeconds": 0.0,
            "idleRate": 0.0,
            "focusScore": 0,
            "distractionScore": 0,
            "contextSwitches": 0,
            "contextSwitchesPerHour": 0.0,
            "longestFocusSeconds": 0.0,
            "fragmentedSeconds": 0.0,
            "currentActivity": "Aguardando eventos do agente",
            "aiSummary": "Ainda não há volume suficiente de eventos reais para gerar diagnóstico operacional.",
            "aiRecommendations": [
                "Reinicie ou instale o Vulcan Agent e aguarde alguns minutos de uso real.",
                "Confirme se o dispositivo está vinculado ao usuário correto na Hierarquia.",
            ],
            "topApps": [],
            "topWindows": [],
            "timeline": [],
            "qualitySignals": [],
        }

    def _build_operational_intelligence(self, rows: list[dict], devices: list[dict], now: datetime) -> dict:
        if not rows:
            summary = self._empty_operational_intelligence(now, "Últimas 24 horas")
            summary["qualitySignals"] = self._quality_signals(devices)
            return summary

        app_totals: dict[str, dict] = defaultdict(
            lambda: {
                "activeSeconds": 0.0,
                "idleSeconds": 0.0,
                "events": 0,
                "contextSwitches": 0,
                "category": "desconhecido",
                "lastSeenAt": None,
            }
        )
        window_totals: dict[tuple[str, str], dict] = defaultdict(lambda: {"activeSeconds": 0.0, "events": 0})
        timeline: dict[str, dict] = defaultdict(lambda: {"activeSeconds": 0.0, "idleSeconds": 0.0, "unidentifiedSeconds": 0.0, "contextSwitches": 0, "events": 0})

        total_active = 0.0
        total_idle = 0.0
        unidentified_seconds = 0.0
        context_switches = 0
        longest_focus = 0.0
        fragmented_seconds = 0.0
        potentially_dispersed_seconds = 0.0
        latest_activity = "Aguardando atividade"
        latest_activity_at: datetime | None = None
        saw_window_title = False

        for row in rows:
            event_type = row["event_type"]
            app_name = self._normalize_operational_label(row["app_name"])
            if self._is_technical_process(app_name) and event_type in {"app_focus_ended", "foreground_application_usage", "foreground_application_change", "context_switch"}:
                continue
            category = self._operational_category(app_name, row.get("category"))
            duration = max(0.0, float(row["duration_seconds"] or 0))
            occurred_at = row["occurred_at"]
            label = occurred_at.astimezone(timezone.utc).strftime("%Hh")
            timeline[label]["events"] += 1

            if self._is_limited_graphical_marker(app_name):
                if event_type in {"app_focus_ended", "foreground_application_usage", "foreground_application_change"} and duration > 0:
                    unidentified_seconds += duration
                    timeline[label]["unidentifiedSeconds"] += duration
                continue

            if event_type == "context_switch":
                context_switches += 1
                timeline[label]["contextSwitches"] += 1
                app_totals[app_name]["contextSwitches"] += 1
                app_totals[app_name]["category"] = category
                app_totals[app_name]["lastSeenAt"] = occurred_at
                continue

            if event_type == "idle_ended":
                total_idle += duration
                timeline[label]["idleSeconds"] += duration
                app_totals["Ociosidade"]["idleSeconds"] += duration
                app_totals["Ociosidade"]["events"] += 1
                app_totals["Ociosidade"]["category"] = "ocioso"
                app_totals["Ociosidade"]["lastSeenAt"] = occurred_at
                continue

            if event_type in {"app_focus_ended", "foreground_application_usage", "foreground_application_change"} and duration > 0:
                total_active += duration
                timeline[label]["activeSeconds"] += duration
                app_totals[app_name]["activeSeconds"] += duration
                app_totals[app_name]["events"] += 1
                app_totals[app_name]["category"] = category
                app_totals[app_name]["lastSeenAt"] = occurred_at
                longest_focus = max(longest_focus, duration)
                if duration < 120:
                    fragmented_seconds += duration
                if category in {"comunicação", "navegador", "entretenimento", "desconhecido"}:
                    potentially_dispersed_seconds += duration
                window_title = self._normalize_operational_label(row.get("window_title") or "")
                if window_title:
                    saw_window_title = True
                    window_totals[(app_name, window_title)]["activeSeconds"] += duration
                    window_totals[(app_name, window_title)]["events"] += 1
                if latest_activity_at is None or occurred_at > latest_activity_at:
                    latest_activity_at = occurred_at
                    latest_activity = f"{app_name} · {category}"

        tracked = total_active + total_idle + unidentified_seconds
        active_hours = max(total_active / 3600, 0.01)
        idle_rate = total_idle / tracked if tracked else 0.0
        switch_rate = context_switches / active_hours
        fragmented_rate = fragmented_seconds / total_active if total_active else 0.0
        dispersed_rate = potentially_dispersed_seconds / total_active if total_active else 0.0
        distraction_score = round(min(100.0, idle_rate * 35 + min(switch_rate, 60) * 0.9 + fragmented_rate * 30 + dispersed_rate * 20))
        focus_score = max(0, min(100, 100 - distraction_score))

        top_apps = []
        for app, totals in sorted(app_totals.items(), key=lambda item: item[1]["activeSeconds"] + item[1]["idleSeconds"], reverse=True)[:12]:
            seconds = float(totals["activeSeconds"] or totals["idleSeconds"] or 0)
            if seconds <= 0:
                continue
            denominator = total_idle if app == "Ociosidade" else total_active
            percent = (seconds / denominator * 100) if denominator else 0.0
            top_apps.append(
                {
                    "app": app,
                    "category": totals["category"],
                    "activeSeconds": float(totals["activeSeconds"]),
                    "idleSeconds": float(totals["idleSeconds"]),
                    "events": int(totals["events"]),
                    "contextSwitches": int(totals["contextSwitches"]),
                    "percent": round(percent, 1),
                    "lastSeenAt": totals["lastSeenAt"],
                    "focusLabel": self._focus_label(totals["category"], int(totals["contextSwitches"]), float(totals["activeSeconds"])),
                }
            )

        top_windows = []
        if saw_window_title:
            for (app, title), totals in sorted(window_totals.items(), key=lambda item: item[1]["activeSeconds"], reverse=True)[:10]:
                seconds = float(totals["activeSeconds"])
                top_windows.append(
                    {
                        "title": title,
                        "app": app,
                        "activeSeconds": seconds,
                        "events": int(totals["events"]),
                        "percent": round((seconds / total_active * 100) if total_active else 0.0, 1),
                        "collectionNote": "Título coletado por política habilitada e com redaction ativa.",
                    }
                )
        else:
            top_windows.append(
                {
                    "title": "Títulos de janela não coletados",
                    "app": "Privacidade",
                    "activeSeconds": 0.0,
                    "events": 0,
                    "percent": 0.0,
                    "collectionNote": "A política atual protege títulos de janela. Ative collectWindowTitle apenas com consentimento.",
                }
            )

        ordered_timeline = [
            {
                "label": label,
                "activeSeconds": values["activeSeconds"],
                "idleSeconds": values["idleSeconds"],
                "unidentifiedSeconds": values["unidentifiedSeconds"],
                "contextSwitches": int(values["contextSwitches"]),
                "events": int(values["events"]),
            }
            for label, values in sorted(timeline.items())
        ]

        quality_signals = self._quality_signals(devices, unidentified_seconds)
        recommendations = self._operational_recommendations(
            total_active=total_active,
            idle_rate=idle_rate,
            switch_rate=switch_rate,
            fragmented_rate=fragmented_rate,
            quality_signals=quality_signals,
        )
        ai_summary = self._operational_ai_summary(
            total_active=total_active,
            total_idle=total_idle,
            switch_rate=switch_rate,
            focus_score=focus_score,
            distraction_score=distraction_score,
            top_apps=top_apps,
        )

        return {
            "generatedAt": now,
            "periodLabel": "Últimas 24 horas",
            "totalEvents": len(rows),
            "totalActiveSeconds": round(total_active, 2),
            "totalIdleSeconds": round(total_idle, 2),
            "unidentifiedSeconds": round(unidentified_seconds, 2),
            "trackedSeconds": round(tracked, 2),
            "idleRate": round(idle_rate, 4),
            "focusScore": focus_score,
            "distractionScore": distraction_score,
            "contextSwitches": context_switches,
            "contextSwitchesPerHour": round(switch_rate, 2),
            "longestFocusSeconds": round(longest_focus, 2),
            "fragmentedSeconds": round(fragmented_seconds, 2),
            "currentActivity": latest_activity,
            "aiSummary": ai_summary,
            "aiRecommendations": recommendations,
            "topApps": top_apps,
            "topWindows": top_windows,
            "timeline": ordered_timeline,
            "qualitySignals": quality_signals,
        }

    def _quality_signals(self, devices: list[dict], unidentified_seconds: float = 0.0) -> list[dict]:
        signals = []
        if unidentified_seconds > 0:
            signals.append(
                {
                    "device": "todos",
                    "quality": "limited_graphical_environment",
                    "message": f"{round(unidentified_seconds / 60)} min não foram atribuídos a um app porque o ambiente gráfico bloqueou a janela ativa.",
                    "lastSeenAt": None,
                }
            )
        for device in devices:
            quality = device.get("collection_quality") or "desconhecida"
            queue_depth = int(device.get("queue_depth") or 0)
            last_error = device.get("last_error")
            if quality in {"blocked_by_os", "low", "desconhecida"}:
                message = "Coleta limitada pelo ambiente gráfico." if quality == "blocked_by_os" else "Qualidade de coleta precisa de atenção."
                signals.append({"device": device["hostname"], "quality": quality, "message": message, "lastSeenAt": device.get("last_seen_at")})
            if queue_depth > 0:
                signals.append({"device": device["hostname"], "quality": "fila", "message": f"{queue_depth} evento(s) aguardando sincronização.", "lastSeenAt": device.get("last_seen_at")})
            if last_error:
                signals.append({"device": device["hostname"], "quality": "erro", "message": last_error, "lastSeenAt": device.get("last_seen_at")})
        return signals

    def _normalize_operational_label(self, value: str) -> str:
        label = " ".join((value or "").strip().split())
        if not label:
            return ""
        lowered = label.lower()
        if "desktop" in lowered and any(token in lowered for token in ["gnome", "zorin", "kde", "xfce"]):
            return "Ambiente gráfico limitado"
        return label[:96]

    def _is_limited_graphical_marker(self, app_name: str) -> bool:
        lowered = app_name.strip().lower()
        return lowered in {"ambiente gráfico limitado", "ambiente grafico limitado"} or (
            "desktop" in lowered and any(token in lowered for token in ["gnome", "zorin", "kde", "xfce"])
        )

    def _is_technical_process(self, app_name: str) -> bool:
        lowered = app_name.strip().lower()
        technical = {
            "ps",
            "runc",
            "sleep",
            "sh",
            "bash",
            "zsh",
            "python",
            "python3",
            "node",
            "npm",
            "pnpm",
            "next-server",
            "git",
            "ssh",
            "rg",
            "grep",
            "sed",
            "cat",
            "curl",
            "wget",
            "ls",
            "find",
            "cpuusage.sh",
            "systemctl",
            "journalctl",
            "dbus-daemon",
            "systemd",
            "pipewire",
            "wireplumber",
            "vulcan_agent.py",
        }
        technical_prefixes = ("runc", "containerd", "docker-proxy", "vulcan", "systemd")
        return lowered in technical or any(lowered.startswith(prefix) for prefix in technical_prefixes)

    def _operational_category(self, app_name: str, explicit_category: str | None) -> str:
        if explicit_category:
            normalized = explicit_category.strip().lower()
            if normalized in {"operational", "uncategorized", "unknown", "desconhecido"}:
                explicit_category = None
            else:
                dictionary = {
                    "browser": "navegador",
                    "communication": "comunicação",
                    "development": "desenvolvimento",
                    "documents": "produtividade",
                    "productivity": "produtividade",
                    "system": "sistema",
                    "business": "gestão",
                    "idle": "ocioso",
                    "erp/crm": "gestão",
                }
                return dictionary.get(normalized, normalized)
        app = app_name.lower()
        if any(token in app for token in ["chrome", "chromium", "firefox", "edge", "brave", "safari"]):
            return "navegador"
        if any(token in app for token in ["whatsapp", "slack", "teams", "telegram", "discord", "zoom", "meet"]):
            return "comunicação"
        if any(token in app for token in ["code", "terminal", "bash", "zsh", "powershell", "pycharm", "intellij"]):
            return "desenvolvimento"
        if any(token in app for token in ["libreoffice", "excel", "word", "calc", "writer", "sheets", "docs"]):
            return "produtividade"
        if any(token in app for token in ["erp", "sap", "totvs", "jira", "notion", "crm"]):
            return "gestão"
        if any(token in app for token in ["gnome", "zorin", "desktop", "shell", "nautilus", "system", "ambiente gráfico"]):
            return "sistema"
        return "desconhecido"

    def _focus_label(self, category: str, switches: int, active_seconds: float) -> str:
        if category == "ocioso":
            return "sem atividade"
        if active_seconds and active_seconds < 120:
            return "fragmentado"
        if switches >= 10:
            return "muitas trocas"
        if category in {"desenvolvimento", "produtividade", "gestão"}:
            return "foco operacional"
        if category in {"comunicação", "navegador"}:
            return "atenção distribuída"
        return "neutro"

    def _operational_ai_summary(self, total_active: float, total_idle: float, switch_rate: float, focus_score: int, distraction_score: int, top_apps: list[dict]) -> str:
        productive_apps = [item for item in top_apps if item["category"] != "ocioso"]
        top = productive_apps[0]["app"] if productive_apps else "nenhum aplicativo dominante"
        active_minutes = round(total_active / 60)
        idle_minutes = round(total_idle / 60)
        return (
            f"Nas últimas 24 horas, o Vulcan identificou {active_minutes} min ativos e {idle_minutes} min ociosos. "
            f"O principal foco operacional foi {top}. A taxa de troca ficou em {switch_rate:.1f} por hora, "
            f"com score de foco {focus_score}/100 e dispersão operacional estimada em {distraction_score}/100."
        )

    def _operational_recommendations(self, total_active: float, idle_rate: float, switch_rate: float, fragmented_rate: float, quality_signals: list[dict]) -> list[str]:
        recommendations: list[str] = []
        if total_active == 0:
            recommendations.append("Ainda não há tempo ativo suficiente. Gere alguns minutos de uso real e sincronize o agente.")
        if idle_rate > 0.25:
            recommendations.append("Existe ociosidade relevante. Verifique pausas longas, bloqueio de sessão e períodos sem atividade operacional.")
        if switch_rate > 25:
            recommendations.append("Há muitas trocas de contexto por hora. Agrupe tarefas parecidas e reduza alternância entre sistemas.")
        if fragmented_rate > 0.35:
            recommendations.append("O tempo está fragmentado em sessões curtas. Procure blocos de foco contínuo acima de 15 minutos.")
        if quality_signals:
            recommendations.append("A qualidade de coleta precisa de atenção em pelo menos um dispositivo. Revise política, ambiente gráfico e dependências do agente.")
        if not recommendations:
            recommendations.append("O padrão atual parece estável. Continue coletando para gerar baseline por dia, semana e setor.")
        return recommendations[:5]

    def list_insights(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return INSIGHTS
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "i.membership_id", "i.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "i")
            return list(conn.execute(
                f"""
                select i.id::text,
                       i.tenant_id as "tenantId",
                       i.membership_id as "membershipId",
                       i.department_id as "departmentId",
                       coalesce(i.metadata ->> 'scopeType', case when i.membership_id is null then 'tenant' else 'user' end) as "scopeType",
                       coalesce(i.metadata ->> 'scopeId', coalesce(i.membership_id::text, i.department_id::text, i.tenant_id::text)) as "scopeId",
                       i.membership_id as "targetUserId",
                       nullif(i.metadata ->> 'targetTeamId', '')::uuid as "targetTeamId",
                       i.department_id as "targetDepartmentId",
                       coalesce(i.metadata -> 'roleVisibility', '[]'::jsonb) as "roleVisibility",
                       coalesce(i.metadata ->> 'type', i.metadata ->> 'insightType', 'recomendacao_processo') as "insightType",
                       i.title,
                       case when i.impact = 'critical' then 'high' else i.impact::text end as impact,
                       i.summary,
                       coalesce(i.metadata ->> 'diagnosis', i.summary) as diagnosis,
                       coalesce(i.recommendation, '') as recommendation,
                       coalesce(i.metadata -> 'evidence', '[]'::jsonb) as evidence,
                       coalesce(i.metadata -> 'metricsUsed', '[]'::jsonb) as "metricsUsed",
                       coalesce(i.metadata -> 'affectedUsers', '[]'::jsonb) as "affectedUsers",
                       coalesce(i.metadata -> 'affectedTeams', '[]'::jsonb) as "affectedTeams",
                       coalesce(i.metadata ->> 'severity', case when i.impact in ('critical', 'high') then 'critical' else i.impact::text end) as severity,
                       i.confidence::float as confidence,
                       coalesce((i.metadata ->> 'estimatedTimeLoss')::float, coalesce(i.automation_savings_hours, 0)::float) as "estimatedTimeLoss",
                       coalesce((i.metadata ->> 'estimatedCostLoss')::float, coalesce(i.automation_savings_hours, 0)::float * 95) as "estimatedCostLoss",
                       coalesce((i.metadata ->> 'estimatedSavings')::float, coalesce(i.automation_savings_hours, 0)::float * 95) as "estimatedSavings",
                       coalesce(nullif(i.metadata ->> 'periodStart', '')::timestamptz, i.created_at - interval '7 days') as "periodStart",
                       coalesce(nullif(i.metadata ->> 'periodEnd', '')::timestamptz, i.created_at) as "periodEnd",
                       coalesce(i.metadata ->> 'status', 'open') as status,
                       i.source_route::text as "sourceRoute",
                       coalesce((i.metadata ->> 'sentToWhatsapp')::bool, false) as "sentToWhatsapp",
                       coalesce((i.metadata ->> 'sentToEmail')::bool, false) as "sentToEmail",
                       coalesce(i.metadata ->> 'whatsappStatus', 'not_sent') as "whatsappStatus",
                       coalesce(i.metadata ->> 'emailStatus', 'not_sent') as "emailStatus",
                       nullif(i.metadata ->> 'lastSentAt', '')::timestamptz as "lastSentAt",
                       coalesce(i.metadata -> 'recipients', '[]'::jsonb) as recipients,
                       coalesce(i.metadata -> 'suggestedQuestions', '[]'::jsonb) as "suggestedQuestions",
                       i.metadata ->> 'actionStatus' as "actionStatus",
                       i.created_at as "createdAt",
                       coalesce(nullif(i.metadata ->> 'updatedAt', '')::timestamptz, i.created_at) as "updatedAt",
                       coalesce(i.automation_savings_hours, 0)::int as "automationSavingsHours"
                from public.ai_insights i
                where {condition}
                  and {real_data_condition}
                order by i.created_at desc
                limit 100
                """,
                params,
            ).fetchall())

    def get_insight(self, context: AuthContext, insight_id: UUID) -> dict | None:
        return next((item for item in self.list_insights(context) if str(item["id"]) == str(insight_id)), None)

    def generate_insight(self, context: AuthContext, tenant_id: UUID, period: str = "24h") -> dict:
        if not self.enabled:
            return {
                "id": str(uuid4()),
                "title": "Geração de insight preparada",
                "impact": "medium",
                "summary": "Banco indisponível; geração real depende do PostgreSQL.",
                "recommendation": "Configure DATABASE_URL para persistir insights reais.",
                "automationSavingsHours": 0,
            }
        with self._connect() as conn:
            access = self._access(conn, context)
            if not access.is_root and tenant_id != access.tenant_id:
                raise ValueError("tenant mismatch")
            condition, params = self._owner_filter(access, "e.membership_id", "e.tenant_id")
            row = conn.execute(
                f"""
                select
                  count(*) as events,
                  coalesce(sum(duration_seconds) filter (where event_type in ('idle_started', 'idle_ended') or lower(coalesce(category, '')) = 'idle'), 0) as idle_seconds,
                  count(*) filter (where event_type = 'context_switch') as switches,
                  coalesce(max(app_name), 'operação') as app_name
                from public.activity_events e
                where {condition}
                  and e.occurred_at >= timezone('utc', now()) - case
                    when %s = '30d' then interval '30 days'
                    when %s = '7d' then interval '7 days'
                    else interval '24 hours'
                  end
                """,
                (*params, period, period),
            ).fetchone()
            events = int(row["events"] or 0)
            idle_hours = float(row["idle_seconds"] or 0) / 3600
            switches = int(row["switches"] or 0)
            severity = "critical" if idle_hours >= 4 or switches >= 80 else "high" if idle_hours >= 1.5 or switches >= 35 else "medium"
            insight_type = "troca_contexto" if switches >= max(idle_hours * 10, 20) else "ociosidade"
            title = "Troca de contexto elevada no recorte" if insight_type == "troca_contexto" else "Ociosidade fora do padrão no recorte"
            summary = (
                f"Foram identificadas {switches} trocas de contexto em {events} eventos analisados."
                if insight_type == "troca_contexto"
                else f"Foram identificadas {idle_hours:.1f} horas potenciais de espera, pausa ou bloqueio operacional."
            )
            recommendation = (
                "Agrupe etapas repetitivas em blocos e reduza alternância entre comunicação e sistema operacional."
                if insight_type == "troca_contexto"
                else "Valide se a ociosidade vem de pausa real, gargalo de sistema ou fila aguardando aprovação."
            )
            inserted = conn.execute(
                """
                insert into public.ai_insights (
                  tenant_id, membership_id, source_route, source_model,
                  title, summary, recommendation, impact, automation_savings_hours, confidence, metadata
                )
                values (%s, %s, 'rules', 'deterministic-vulcan-rules', %s, %s, %s, %s, %s, 0.82, %s)
                returning id
                """,
                (
                    tenant_id,
                    access.membership_id if access.scope == "self" else None,
                    title,
                    summary,
                    recommendation,
                    "high" if severity in {"critical", "high"} else "medium",
                    max(1, round(idle_hours + switches * 0.018)),
                    Jsonb(
                        {
                            "type": insight_type,
                            "severity": severity,
                            "status": "open",
                            "scopeType": "user" if access.scope == "self" else "tenant",
                            "diagnosis": summary,
                            "evidence": [f"{events} eventos no período {period}", f"{switches} trocas de contexto", f"{idle_hours:.1f}h de ociosidade estimada"],
                            "metricsUsed": ["activity_events", "duration_seconds", "context_switch"],
                            "estimatedTimeLoss": max(1, round(idle_hours + switches * 0.018, 1)),
                            "estimatedCostLoss": round(max(1, idle_hours + switches * 0.018) * 95, 2),
                            "estimatedSavings": round(max(1, idle_hours + switches * 0.018) * 95, 2),
                            "suggestedQuestions": [
                                "Por que isso aconteceu?",
                                "O que eu faço primeiro?",
                                "Dá para automatizar esse processo?",
                            ],
                        }
                    ),
                ),
            ).fetchone()
            self.write_audit(conn, context, tenant_id, "insight.generated", "ai_insight", inserted["id"], {"period": period, "type": insight_type})
            conn.commit()
            insight = self.get_insight(context, inserted["id"])
            return insight or {"id": str(inserted["id"]), "title": title, "impact": "medium", "summary": summary, "recommendation": recommendation, "automationSavingsHours": 0}

    def ask_insight(self, context: AuthContext, insight_id: UUID, question: str) -> dict:
        insight = self.get_insight(context, insight_id)
        if not insight:
            raise ValueError("insight not found or outside hierarchy")
        forbidden_terms = ("fora da minha hierarquia", "todos os tenants", "outro tenant")
        if any(term in question.lower() for term in forbidden_terms):
            answer = "Você não possui permissão para visualizar dados fora da sua hierarquia."
        else:
            evidence = "; ".join(insight.get("evidence") or []) or insight["summary"]
            answer = (
                f"Diagnóstico: {insight.get('diagnosis') or insight['summary']} "
                f"Evidências: {evidence}. "
                f"Ação recomendada: {insight['recommendation']} "
                f"Impacto estimado: {insight.get('estimatedTimeLoss', 0)}h e {float(insight.get('estimatedCostLoss') or 0):.2f} em custo operacional."
            )
        return {
            "insightId": str(insight_id),
            "question": question,
            "answer": answer,
            "aiMode": "rules_fallback_explicit",
            "suggestedActions": [
                insight["recommendation"],
                "Abrir métricas filtradas para confirmar a evidência.",
                "Criar plano de ação com responsável e prazo.",
            ],
        }

    def update_insight_metadata(self, context: AuthContext, insight_id: UUID, patch: dict, audit_action: str) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "membership_id", "tenant_id")
            row = conn.execute(
                f"""
                update public.ai_insights
                set metadata = metadata || %s
                where id = %s and {condition}
                returning id, tenant_id
                """,
                (Jsonb({**patch, "updatedAt": datetime.now(timezone.utc).isoformat()}), insight_id, *params),
            ).fetchone()
            if not row:
                conn.rollback()
                return None
            self.write_audit(conn, context, row["tenant_id"], audit_action, "ai_insight", row["id"], patch)
            conn.commit()
        return self.get_insight(context, insight_id)

    def create_insight_action(self, context: AuthContext, insight_id: UUID, payload: dict) -> dict | None:
        return self.update_insight_metadata(
            context,
            insight_id,
            {
                "actionStatus": "open",
                "action": {
                    "title": payload.get("title"),
                    "ownerMembershipId": str(payload.get("owner_membership_id") or ""),
                    "priority": payload.get("priority", "alta"),
                    "dueDate": payload.get("due_date").isoformat() if payload.get("due_date") else None,
                    "note": payload.get("note"),
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                },
            },
            "insight.action_created",
        )

    def list_notifications(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return NOTIFICATIONS
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "n.recipient_membership_id", "n.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "n")
            return list(conn.execute(
                f"""
                select n.id::text,
                       n.tenant_id as "tenantId",
                       n.recipient_membership_id as "recipientMembershipId",
                       coalesce(m.full_name, n.metadata ->> 'recipient', 'Não definido') as recipient,
                       n.channel::text,
                       coalesce(n.metadata ->> 'deliveryStatus', n.status::text) as status,
                       n.notification_type as "notificationType",
                       n.title,
                       n.message,
                       coalesce(n.metadata ->> 'priority', 'medio') as priority,
                       coalesce((n.metadata ->> 'attempts')::int, 0) as attempts,
                       coalesce((n.metadata ->> 'maxAttempts')::int, 3) as "maxAttempts",
                       coalesce(n.metadata ->> 'lastError', n.metadata ->> 'error') as error,
                       n.provider,
                       n.provider_message_id as "providerMessageId",
                       nullif(n.metadata ->> 'scheduledFor', '')::timestamptz as "scheduledFor",
                       n.sent_at as "sentAt",
                       nullif(n.metadata ->> 'deliveredAt', '')::timestamptz as "deliveredAt",
                       nullif(n.metadata ->> 'readAt', '')::timestamptz as "readAt",
                       nullif(n.metadata ->> 'resolvedAt', '')::timestamptz as "resolvedAt",
                       n.metadata ->> 'actionUrl' as "actionUrl",
                       coalesce((n.metadata ->> 'requiresAck')::bool, false) as "requiresAck",
                       n.created_at::text as "createdAt"
                from public.notifications n
                left join public.memberships m on m.id = n.recipient_membership_id
                where {condition}
                  and {real_data_condition}
                order by n.created_at desc
                limit 100
                """,
                params,
            ).fetchall())

    def get_notification(self, context: AuthContext, notification_id: UUID) -> dict | None:
        return next((item for item in self.list_notifications(context) if str(item["id"]) == str(notification_id)), None)

    def notification_summary(self, context: AuthContext) -> dict:
        notifications = self.list_notifications(context)
        statuses = defaultdict(int)
        channels = defaultdict(int)
        priorities = defaultdict(int)
        for item in notifications:
            statuses[item["status"]] += 1
            channels[item["channel"]] += 1
            priorities[item["priority"]] += 1
        pending_statuses = {"pending", "queued", "sending", "retrying", "missing_credentials"}
        failed_statuses = {"failed", "missing_credentials"}
        sent_statuses = {"sent", "delivered", "ready", "mocked"}
        return {
            "total": len(notifications),
            "pending": sum(1 for item in notifications if item["status"] in pending_statuses),
            "sent": sum(1 for item in notifications if item["status"] in sent_statuses),
            "failed": sum(1 for item in notifications if item["status"] in failed_statuses),
            "critical": sum(1 for item in notifications if item["priority"] == "critico"),
            "unread": sum(1 for item in notifications if not item.get("readAt")),
            "whatsappReady": any(item["channel"] == "whatsapp" and item["status"] in sent_statuses for item in notifications),
            "emailReady": any(item["channel"] == "email" and item["status"] in sent_statuses for item in notifications),
            "agentReady": any(item["channel"] == "windows" for item in notifications),
            "nextScheduleAt": None,
            "byChannel": dict(channels),
            "byStatus": dict(statuses),
            "byPriority": dict(priorities),
        }

    def list_root_whatsapp_templates(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return ROOT_WHATSAPP_TEMPLATES
        with self._connect() as conn:
            access = self._access(conn, context)
            params: tuple[object, ...] = () if access.is_root else (access.tenant_id,)
            condition = "true" if access.is_root else "(tenant_id is null or tenant_id = %s)"
            rows = conn.execute(
                f"""
                select id,
                       'whatsapp' as channel,
                       template_type as "notificationType",
                       title,
                       body,
                       variables,
                       language,
                       version,
                       active
                from public.root_whatsapp_templates
                where {condition}
                  and active = true
                order by tenant_id nulls first, template_type, version desc
                """,
                params,
            ).fetchall()
            return list(rows) or ROOT_WHATSAPP_TEMPLATES

    def resolve_root_whatsapp_recipients(
        self,
        context: AuthContext,
        notification_type: str = "alerta",
        audience: str = "auto",
        recipient_membership_ids: list[UUID] | None = None,
    ) -> list[dict]:
        if not self.enabled:
            return [
                {"membershipId": DEMO_TEST_MEMBERSHIP_ID, "tenantId": DEMO_TENANT_ID, "name": "teste", "title": "Diretor Demo", "department": "Operações", "whatsapp": "5541999999999", "scope": "tenant", "preferenceEnabled": True},
                {"membershipId": UUID("00000000-0000-0000-0000-000000300002"), "tenantId": DEMO_TENANT_ID, "name": "Coordenador de Operações", "title": "Coordenador", "department": "Operações", "whatsapp": "5541988888888", "scope": "subtree", "preferenceEnabled": True},
            ]
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._membership_filter(access, "m")
            rows = list(conn.execute(
                f"""
                select m.id as "membershipId",
                       m.tenant_id as "tenantId",
                       m.full_name as name,
                       m.title,
                       d.name as department,
                       regexp_replace(coalesce(m.whatsapp, ''), '\\D', '', 'g') as whatsapp,
                       case
                         when coalesce(descendants.total, 0) > 0 then 'subtree'
                         else 'self'
                       end as scope,
                       coalesce(np.enabled, true) as "preferenceEnabled",
                       coalesce(m.whatsapp_enabled, true) as whatsapp_enabled,
                       coalesce(m.whatsapp_opt_in, false) as whatsapp_opt_in,
                       coalesce(m.whatsapp_notification_types, '[]'::jsonb) as whatsapp_notification_types,
                       m.quiet_hours_start,
                       m.quiet_hours_end,
                       coalesce(m.hierarchy_level, 9999) as hierarchy_level
                from public.memberships m
                left join public.departments d on d.id = m.department_id
                left join lateral (
                  select count(*) as total
                  from public.membership_closure mc
                  where mc.tenant_id = m.tenant_id
                    and mc.ancestor_membership_id = m.id
                    and mc.descendant_membership_id <> m.id
                ) descendants on true
                left join public.notification_preferences np
                  on np.tenant_id = m.tenant_id
                 and np.membership_id = m.id
                 and np.channel = 'whatsapp'
                 and np.notification_type = %s
                where {condition}
                  and m.status = 'active'
                  and nullif(regexp_replace(coalesce(m.whatsapp, ''), '\\D', '', 'g'), '') is not null
                  and coalesce(np.enabled, true)
                  and coalesce(m.whatsapp_enabled, true)
                  and (%s = false or coalesce(m.whatsapp_opt_in, false))
                  and (
                    jsonb_array_length(coalesce(m.whatsapp_notification_types, '[]'::jsonb)) = 0
                    or coalesce(m.whatsapp_notification_types, '[]'::jsonb) ? %s
                  )
                order by coalesce(m.hierarchy_level, 9999), m.full_name
                """,
                (notification_type, *params, self.settings.whatsapp_require_opt_in, notification_type),
            ).fetchall())

        critical = notification_type in {"critico", "insight_critico", "relatorio_critico", "falha_integracao"}
        if not critical:
            rows = [row for row in rows if not self._recipient_in_quiet_hours(row)]

        requested = {str(item) for item in (recipient_membership_ids or [])}
        if audience == "custom":
            rows = [row for row in rows if str(row["membershipId"]) in requested]
        elif audience == "self":
            rows = [row for row in rows if str(row["membershipId"]) == str(access.membership_id)]
        elif audience == "managers":
            rows = [row for row in rows if self._is_manager_recipient(row)]
        elif audience == "tenant" and access.scope not in {"tenant", "global"} and not access.is_root:
            rows = [row for row in rows if str(row["membershipId"]) == str(access.membership_id)]
        elif audience == "auto":
            if notification_type in {"relatorio_semanal", "relatorio_mensal", "insight_executivo", "critico", "insight"}:
                managers = [row for row in rows if self._is_manager_recipient(row)]
                rows = managers or rows
            elif notification_type in {"metrica", "relatorio_diario"}:
                managers = [row for row in rows if self._is_manager_recipient(row)]
                rows = managers or rows
        internal_fields = {
            "hierarchy_level",
            "whatsapp_enabled",
            "whatsapp_opt_in",
            "whatsapp_notification_types",
            "quiet_hours_start",
            "quiet_hours_end",
        }
        return [{key: value for key, value in dict(row).items() if key not in internal_fields} for row in rows]

    def _recipient_in_quiet_hours(self, row: dict) -> bool:
        start = row.get("quiet_hours_start")
        end = row.get("quiet_hours_end")
        if not start or not end:
            return False
        now_time = datetime.now(timezone(timedelta(hours=-3))).time().replace(tzinfo=None)
        if start <= end:
            return start <= now_time < end
        return now_time >= start or now_time < end

    def _is_manager_recipient(self, row: dict) -> bool:
        title = str(row.get("title") or "").lower()
        name = str(row.get("name") or "").lower()
        tokens = ("diretor", "coordenador", "gerente", "supervisor", "líder", "lider", "admin")
        return row.get("scope") in {"tenant", "subtree"} or any(token in title or token in name for token in tokens)

    def _root_whatsapp_template_for(self, context: AuthContext, request: RootWhatsAppSendRequest) -> dict:
        templates = self.list_root_whatsapp_templates(context)
        if request.template_id:
            found = next((item for item in templates if item["id"] == request.template_id), None)
            if found:
                return found
        normalized_type = request.notification_type
        aliases = {
            "gargalo_operacional": "alerta",
            "alerta_operacional": "alerta",
            "insight_critico": "critico",
            "oportunidade_automacao": "insight",
            "relatorio_critico": "critico",
        }
        normalized_type = aliases.get(normalized_type, normalized_type)
        return next((item for item in templates if item["notificationType"] == normalized_type), templates[0])

    def _render_root_whatsapp_message(self, context: AuthContext, request: RootWhatsAppSendRequest, template: dict, recipient: dict | None = None) -> tuple[str, str, dict]:
        values = {
            "empresa": "Vulcan",
            "escopo": recipient.get("name") if recipient else "Operação",
            "metrica": "indicador operacional",
            "periodo": "últimas 24 horas",
            "valor": "em análise",
            "impacto": request.priority,
            "titulo": request.title or template["title"],
            "resumo": request.message or "Resumo operacional disponível no Vulcan.",
            "recomendacao": "Abra o painel do Vulcan para revisar a recomendação.",
            "economia_estimada": "a confirmar",
            "tempo_ativo": "tempo ativo consolidado",
            "tempo_ocioso": "tempo ocioso consolidado",
            "gargalos": "gargalos identificados",
            "insights": "insights gerados",
            "automacoes": "oportunidades de automação",
            "evento": request.title or "evento crítico",
            "acao": "verificar agora",
            "link_dashboard": request.action_url or "http://localhost:3002",
            **request.variables,
        }

        def render(text: str) -> str:
            rendered = text
            for key, value in values.items():
                rendered = rendered.replace("{{" + key + "}}", str(value))
            return rendered

        title = request.title or render(template["title"])
        body = request.message or render(template["body"])
        return title, body, values

    def queue_root_whatsapp_messages(self, context: AuthContext, request: RootWhatsAppSendRequest) -> list[dict]:
        recipients = self.resolve_root_whatsapp_recipients(
            context,
            request.notification_type,
            request.audience,
            request.recipient_membership_ids,
        )
        template = self._root_whatsapp_template_for(context, request)
        if request.dry_run or not self.enabled:
            now = datetime.now(timezone.utc)
            return [
                {
                    "id": uuid4(),
                    "tenantId": request.tenant_id,
                    "notificationId": None,
                    "recipientMembershipId": recipient["membershipId"],
                    "recipient": recipient["name"],
                    "destination": recipient["whatsapp"],
                    "notificationType": request.notification_type,
                    "title": self._render_root_whatsapp_message(context, request, template, recipient)[0],
                    "message": self._render_root_whatsapp_message(context, request, template, recipient)[1],
                    "priority": request.priority,
                    "status": "skipped" if request.dry_run else "mocked",
                    "provider": self.settings.root_whatsapp_provider,
                    "providerMessageId": None,
                    "attempts": 0,
                    "maxAttempts": request.max_attempts,
                    "scheduledFor": request.scheduled_for,
                    "sentAt": None,
                    "lastError": None,
                    "createdAt": now,
                }
                for recipient in recipients
            ]
        with self._connect() as conn:
            access = self._access(conn, context)
            if not access.is_root and request.tenant_id != access.tenant_id:
                raise ValueError("tenant mismatch")
            schedule_status = "pending" if request.schedule != "imediato" or request.scheduled_for else "queued"
            created: list[dict] = []
            for recipient in recipients:
                title, message, values = self._render_root_whatsapp_message(context, request, template, recipient)
                idempotency_key = None
                if request.idempotency_key:
                    raw_key = f"{request.idempotency_key}:{recipient['membershipId']}"
                    idempotency_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
                    existing = conn.execute(
                        """
                        select q.id, q.tenant_id as "tenantId", q.notification_id as "notificationId",
                               q.recipient_membership_id as "recipientMembershipId", m.full_name as recipient,
                               q.destination, q.notification_type as "notificationType", q.title, q.message,
                               q.priority, q.status, q.provider, q.provider_message_id as "providerMessageId",
                               q.attempts, q.max_attempts as "maxAttempts", q.scheduled_for as "scheduledFor",
                               q.next_attempt_at as "nextAttemptAt", q.sent_at as "sentAt",
                               q.delivered_at as "deliveredAt", q.dead_letter_at as "deadLetterAt",
                               q.last_error as "lastError", q.created_at as "createdAt"
                        from public.whatsapp_delivery_queue q
                        left join public.memberships m on m.id = q.recipient_membership_id
                        where q.tenant_id = %s
                          and q.recipient_membership_id = %s
                          and q.idempotency_key = %s
                        """,
                        (request.tenant_id, recipient["membershipId"], idempotency_key),
                    ).fetchone()
                    if existing:
                        created.append(dict(existing))
                        continue
                notification = conn.execute(
                    """
                    insert into public.notifications (
                      tenant_id, recipient_membership_id, channel, notification_type,
                      status, title, message, provider, metadata
                    )
                    values (%s, %s, 'whatsapp', %s, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (
                        request.tenant_id,
                        recipient["membershipId"],
                        request.notification_type,
                        schedule_status,
                        title,
                        message,
                        self.settings.root_whatsapp_provider,
                        Jsonb(
                            {
                                "deliveryStatus": schedule_status,
                                "priority": request.priority,
                                "rootChannel": True,
                                "rootChannelName": self.settings.root_whatsapp_name,
                                "scheduledFor": request.scheduled_for.isoformat() if request.scheduled_for else None,
                                "actionUrl": request.action_url,
                                "recipient": recipient["name"],
                                "recipientScope": recipient["scope"],
                                "templateId": template["id"],
                            }
                        ),
                    ),
                ).fetchone()
                queue = conn.execute(
                    """
                    insert into public.whatsapp_delivery_queue (
                      tenant_id, notification_id, recipient_membership_id, template_id,
                      notification_type, root_channel_name, root_channel_number,
                      destination, title, message, priority, status, provider,
                      provider_instance, idempotency_key,
                      scheduled_for, next_attempt_at, max_attempts, payload
                    )
                    values (
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    returning id, tenant_id as "tenantId", notification_id as "notificationId",
                              recipient_membership_id as "recipientMembershipId",
                              destination, notification_type as "notificationType", title, message,
                              priority, status, provider, provider_message_id as "providerMessageId",
                              attempts, max_attempts as "maxAttempts", scheduled_for as "scheduledFor",
                              next_attempt_at as "nextAttemptAt", sent_at as "sentAt",
                              delivered_at as "deliveredAt", dead_letter_at as "deadLetterAt",
                              last_error as "lastError", created_at as "createdAt"
                    """,
                    (
                        request.tenant_id,
                        notification["id"],
                        recipient["membershipId"],
                        template["id"],
                        request.notification_type,
                        self.settings.root_whatsapp_name,
                        self.settings.root_whatsapp_number,
                        recipient["whatsapp"],
                        title,
                        message,
                        request.priority,
                        schedule_status,
                        self.settings.root_whatsapp_provider,
                        self.settings.evolution_instance_name if self.settings.root_whatsapp_provider == "evolution" else None,
                        idempotency_key,
                        request.scheduled_for,
                        request.scheduled_for or datetime.now(timezone.utc),
                        request.max_attempts,
                        Jsonb({"variables": values, "audience": request.audience, "schedule": request.schedule, "recipientScope": recipient["scope"]}),
                    ),
                ).fetchone()
                created.append({**dict(queue), "recipient": recipient["name"]})
            self.write_audit(
                conn,
                context,
                request.tenant_id,
                "root_whatsapp.queue.created",
                "whatsapp_delivery_queue",
                created[0]["id"] if created else None,
                {"count": len(created), "notificationType": request.notification_type, "audience": request.audience},
            )
            conn.commit()
        return created

    def list_root_whatsapp_queue(self, context: AuthContext, limit: int = 100) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "q.recipient_membership_id", "q.tenant_id")
            rows = conn.execute(
                f"""
                select q.id,
                       q.tenant_id as "tenantId",
                       q.notification_id as "notificationId",
                       q.recipient_membership_id as "recipientMembershipId",
                       m.full_name as recipient,
                       q.destination,
                       q.notification_type as "notificationType",
                       q.title,
                       q.message,
                       q.priority,
                       q.status,
                       q.provider,
                       q.provider_message_id as "providerMessageId",
                       q.attempts,
                       q.max_attempts as "maxAttempts",
                       q.scheduled_for as "scheduledFor",
                       q.next_attempt_at as "nextAttemptAt",
                       q.sent_at as "sentAt",
                       q.delivered_at as "deliveredAt",
                       q.dead_letter_at as "deadLetterAt",
                       q.last_error as "lastError",
                       q.created_at as "createdAt"
                from public.whatsapp_delivery_queue q
                left join public.memberships m on m.id = q.recipient_membership_id
                where {condition}
                order by q.created_at desc
                limit %s
                """,
                (*params, limit),
            ).fetchall()
            return list(rows)

    def list_root_whatsapp_logs(self, context: AuthContext, limit: int = 100) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "l.recipient_membership_id", "l.tenant_id")
            rows = conn.execute(
                f"""
                select l.id,
                       l.tenant_id as "tenantId",
                       l.queue_id as "queueId",
                       l.notification_id as "notificationId",
                       l.recipient_membership_id as "recipientMembershipId",
                       l.destination,
                       l.status,
                       l.provider,
                       l.provider_result as "providerResult",
                       l.error,
                       l.created_at as "createdAt"
                from public.whatsapp_delivery_logs l
                where {condition}
                order by l.created_at desc
                limit %s
                """,
                (*params, limit),
            ).fetchall()
            return list(rows)

    def dispatch_root_whatsapp_queue(self, context: AuthContext, queue_ids: list[UUID] | None = None, limit: int = 25) -> list[dict]:
        if not self.enabled:
            return []
        from app.whatsapp import WhatsAppProvider

        provider = WhatsAppProvider(self.settings)
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "q.recipient_membership_id", "q.tenant_id")
            rows = self._claim_root_whatsapp_rows(conn, condition, params, queue_ids, limit)
            conn.commit()
        updated: list[dict] = []
        for row in rows:
            delivery = provider.send(
                str(row["tenant_id"]),
                row["message"],
                row["destination"],
                metadata={"queueId": str(row["id"]), "notificationId": str(row["notification_id"]) if row["notification_id"] else None},
            )
            updated_item = self.record_root_whatsapp_delivery(context, row["id"], delivery)
            if updated_item:
                updated.append(updated_item)
        return updated

    def dispatch_root_whatsapp_queue_system(self, limit: int = 25) -> list[dict]:
        if not self.enabled:
            return []
        from app.whatsapp import WhatsAppProvider

        provider = WhatsAppProvider(self.settings)
        with self._connect() as conn:
            rows = self._claim_root_whatsapp_rows(conn, "true", (), None, limit)
            conn.commit()
        updated: list[dict] = []
        for row in rows:
            delivery = provider.send(
                str(row["tenant_id"]),
                row["message"],
                row["destination"],
                metadata={"queueId": str(row["id"]), "notificationId": str(row["notification_id"]) if row["notification_id"] else None},
            )
            item = self._record_root_whatsapp_delivery_system(row["id"], delivery)
            if item:
                updated.append(item)
        return updated

    def _claim_root_whatsapp_rows(
        self,
        conn: psycopg.Connection,
        condition: str,
        params: tuple[object, ...],
        queue_ids: list[UUID] | None,
        limit: int,
    ) -> list[dict]:
        queue_filter = ""
        queue_params: tuple[object, ...] = ()
        if queue_ids:
            queue_filter = "and q.id = any(%s::uuid[])"
            queue_params = ([str(item) for item in queue_ids],)
        return list(conn.execute(
            f"""
            with candidates as (
              select q.id
              from public.whatsapp_delivery_queue q
              where {condition}
                and q.status in ('pending', 'queued', 'retrying', 'provider_unavailable', 'qr_required', 'rate_limited')
                and coalesce(q.next_attempt_at, q.scheduled_for, timezone('utc', now())) <= timezone('utc', now())
                {queue_filter}
              order by q.priority = 'critico' desc, q.created_at
              for update skip locked
              limit %s
            )
            update public.whatsapp_delivery_queue q
            set status = 'sending',
                attempts = q.attempts + 1,
                updated_at = timezone('utc', now())
            from candidates c
            where q.id = c.id
            returning q.*
            """,
            (*params, *queue_params, limit),
        ).fetchall())

    def record_root_whatsapp_delivery(self, context: AuthContext, queue_id: UUID, delivery) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "recipient_membership_id", "tenant_id")
            row = self._record_root_whatsapp_delivery(conn, queue_id, delivery, condition, params)
            if not row:
                return None
            self.write_audit(
                conn,
                context,
                row["tenant_id"],
                "root_whatsapp.delivery.updated",
                "whatsapp_delivery_queue",
                row["id"],
                {"status": row["status"], "providerResult": delivery.provider_result},
            )
            conn.commit()
        return next((item for item in self.list_root_whatsapp_queue(context, limit=200) if str(item["id"]) == str(queue_id)), None)

    def _record_root_whatsapp_delivery_system(self, queue_id: UUID, delivery) -> dict | None:
        with self._connect() as conn:
            row = self._record_root_whatsapp_delivery(conn, queue_id, delivery, "true", ())
            if not row:
                return None
            self.write_agent_audit(
                conn,
                row["tenant_id"],
                "root_whatsapp.worker.delivery.updated",
                "whatsapp_delivery_queue",
                row["id"],
                {"status": row["status"], "providerResult": delivery.provider_result},
            )
            conn.commit()
            return self._queue_row_to_api(row)

    def _record_root_whatsapp_delivery(
        self,
        conn: psycopg.Connection,
        queue_id: UUID,
        delivery,
        condition: str,
        params: tuple[object, ...],
    ) -> dict | None:
        row = conn.execute(
            f"select * from public.whatsapp_delivery_queue where id = %s and {condition} for update",
            (queue_id, *params),
        ).fetchone()
        if not row:
            return None

        now = datetime.now(timezone.utc)
        attempt_status = str(delivery.status)
        retryable = {"failed", "missing_credentials", "provider_unavailable", "qr_required", "rate_limited"}
        terminal_failure = {"missing_destination", "unknown_provider", "disabled"}
        success = attempt_status in {"sent", "delivered", "mocked"}
        should_retry = attempt_status in retryable and row["attempts"] < row["max_attempts"]
        if success:
            queue_status = attempt_status
        elif should_retry:
            queue_status = "retrying"
        else:
            queue_status = "failed" if attempt_status in retryable | terminal_failure else attempt_status

        next_attempt_at = None
        if should_retry:
            delay_seconds = min(
                self.settings.evolution_retry_backoff_seconds * (2 ** max(0, int(row["attempts"]) - 1)),
                3600,
            )
            next_attempt_at = now + timedelta(seconds=delay_seconds)
        sent_at = now if attempt_status in {"sent", "delivered", "mocked"} else None
        delivered_at = now if attempt_status == "delivered" else None
        dead_letter_at = now if queue_status == "failed" else None
        error_message = None if success else delivery.message

        updated = conn.execute(
            """
            update public.whatsapp_delivery_queue
            set status = %s,
                provider_message_id = coalesce(%s, provider_message_id),
                sent_at = coalesce(%s, sent_at),
                delivered_at = coalesce(%s, delivered_at),
                dead_letter_at = %s,
                last_error = %s,
                next_attempt_at = %s,
                updated_at = timezone('utc', now())
            where id = %s
            returning *
            """,
            (
                queue_status,
                delivery.provider_message_id,
                sent_at,
                delivered_at,
                dead_letter_at,
                error_message,
                next_attempt_at,
                queue_id,
            ),
        ).fetchone()
        if not updated:
            return None

        db_notification_status = (
            "sent" if queue_status in {"sent", "delivered"}
            else "mocked" if queue_status == "mocked"
            else "failed" if queue_status == "failed"
            else "queued"
        )
        if updated["notification_id"]:
            conn.execute(
                """
                update public.notifications
                set status = %s,
                    provider_message_id = coalesce(%s, provider_message_id),
                    sent_at = coalesce(%s, sent_at),
                    delivered_at = coalesce(%s, delivered_at),
                    metadata = metadata || %s
                where id = %s
                """,
                (
                    db_notification_status,
                    delivery.provider_message_id,
                    sent_at,
                    delivered_at,
                    Jsonb({
                        "deliveryStatus": queue_status,
                        "attemptStatus": attempt_status,
                        "lastProviderResult": delivery.provider_result,
                        "lastError": error_message,
                        "attemptedAt": now.isoformat(),
                        "nextAttemptAt": next_attempt_at.isoformat() if next_attempt_at else None,
                    }),
                    updated["notification_id"],
                ),
            )
        conn.execute(
            """
            insert into public.whatsapp_delivery_logs (
              tenant_id, queue_id, notification_id, recipient_membership_id,
              destination, status, provider, provider_result, error, payload
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                updated["tenant_id"],
                updated["id"],
                updated["notification_id"],
                updated["recipient_membership_id"],
                updated["destination"],
                attempt_status,
                updated["provider"],
                delivery.provider_result,
                error_message,
                Jsonb({
                    "message": delivery.message,
                    "providerMessageId": delivery.provider_message_id,
                    "queueStatus": queue_status,
                    "attempt": updated["attempts"],
                }),
            ),
        )
        if queue_status == "failed" and not updated["fallback_triggered_at"]:
            self._create_whatsapp_fallbacks(conn, updated)
            updated["fallback_triggered_at"] = now
        return updated

    def _create_whatsapp_fallbacks(self, conn: psycopg.Connection, row: dict) -> None:
        now = datetime.now(timezone.utc)
        if self.settings.whatsapp_in_app_fallback_enabled:
            conn.execute(
                """
                insert into public.notifications (
                  tenant_id, recipient_membership_id, channel, notification_type,
                  status, title, message, provider, metadata
                )
                values (%s, %s, 'system', 'falha_whatsapp', 'pending', %s, %s, 'vulcan-in-app-fallback', %s)
                """,
                (
                    row["tenant_id"],
                    row["recipient_membership_id"],
                    f"WhatsApp indisponível: {row['title']}",
                    row["message"],
                    Jsonb({"fallbackForQueueId": str(row["id"]), "sourceChannel": "whatsapp"}),
                ),
            )
        if self.settings.whatsapp_email_fallback_enabled:
            recipient = conn.execute(
                "select work_email from public.memberships where tenant_id = %s and id = %s",
                (row["tenant_id"], row["recipient_membership_id"]),
            ).fetchone()
            if recipient and recipient["work_email"]:
                conn.execute(
                    """
                    insert into public.notifications (
                      tenant_id, recipient_membership_id, channel, notification_type,
                      status, title, message, provider, metadata
                    )
                    values (%s, %s, 'email', 'falha_whatsapp', 'pending', %s, %s, 'email-fallback-queue', %s)
                    """,
                    (
                        row["tenant_id"],
                        row["recipient_membership_id"],
                        row["title"],
                        row["message"],
                        Jsonb({"fallbackForQueueId": str(row["id"]), "destination": recipient["work_email"]}),
                    ),
                )
        conn.execute(
            "update public.whatsapp_delivery_queue set fallback_triggered_at = %s where id = %s",
            (now, row["id"]),
        )

    def retry_root_whatsapp_queue_item(self, context: AuthContext, queue_id: UUID) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "recipient_membership_id", "tenant_id")
            row = conn.execute(
                f"""
                update public.whatsapp_delivery_queue
                set status = 'queued', attempts = 0, next_attempt_at = timezone('utc', now()),
                    dead_letter_at = null, fallback_triggered_at = null, last_error = null,
                    updated_at = timezone('utc', now())
                where id = %s and {condition}
                returning *
                """,
                (queue_id, *params),
            ).fetchone()
            if not row:
                return None
            self.write_audit(conn, context, row["tenant_id"], "root_whatsapp.queue.retried", "whatsapp_delivery_queue", row["id"], {})
            conn.commit()
        return next((item for item in self.list_root_whatsapp_queue(context, 200) if item["id"] == queue_id), None)

    def apply_root_whatsapp_webhook(self, provider_message_id: str, delivery_status: str, payload: dict) -> bool:
        if not self.enabled or delivery_status not in {"sent", "delivered", "failed"}:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "select * from public.whatsapp_delivery_queue where provider_message_id = %s for update",
                (provider_message_id,),
            ).fetchone()
            if not row:
                return False
            current = str(row["status"])
            status_value = current if current == "delivered" else delivery_status
            delivered_at = datetime.now(timezone.utc) if status_value == "delivered" else None
            conn.execute(
                """
                update public.whatsapp_delivery_queue
                set status = %s, delivered_at = coalesce(%s, delivered_at),
                    dead_letter_at = case when %s = 'failed' then timezone('utc', now()) else dead_letter_at end,
                    updated_at = timezone('utc', now())
                where id = %s
                """,
                (status_value, delivered_at, status_value, row["id"]),
            )
            if row["notification_id"]:
                conn.execute(
                    """
                    update public.notifications
                    set status = %s, delivered_at = coalesce(%s, delivered_at),
                        metadata = metadata || %s
                    where id = %s
                    """,
                    (
                        status_value,
                        delivered_at,
                        Jsonb({"deliveryStatus": status_value, "webhookReceivedAt": datetime.now(timezone.utc).isoformat()}),
                        row["notification_id"],
                    ),
                )
            conn.execute(
                """
                insert into public.whatsapp_delivery_logs (
                  tenant_id, queue_id, notification_id, recipient_membership_id,
                  destination, status, provider, provider_result, payload
                ) values (%s, %s, %s, %s, %s, %s, %s, 'evolution:webhook', %s)
                """,
                (
                    row["tenant_id"], row["id"], row["notification_id"], row["recipient_membership_id"],
                    row["destination"], status_value, row["provider"], Jsonb(payload),
                ),
            )
            self.write_agent_audit(conn, row["tenant_id"], "root_whatsapp.webhook.received", "whatsapp_delivery_queue", row["id"], {"status": status_value})
            conn.commit()
            return True

    def root_whatsapp_queue_counts_system(self) -> dict[str, int]:
        if not self.enabled:
            return {}
        with self._connect() as conn:
            rows = conn.execute(
                "select status, count(*)::int as total from public.whatsapp_delivery_queue group by status"
            ).fetchall()
        return {str(row["status"]): int(row["total"]) for row in rows}

    def _queue_row_to_api(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "tenantId": row["tenant_id"],
            "notificationId": row["notification_id"],
            "recipientMembershipId": row["recipient_membership_id"],
            "recipient": None,
            "destination": row["destination"],
            "notificationType": row["notification_type"],
            "title": row["title"],
            "message": row["message"],
            "priority": row["priority"],
            "status": row["status"],
            "provider": row["provider"],
            "providerMessageId": row["provider_message_id"],
            "attempts": row["attempts"],
            "maxAttempts": row["max_attempts"],
            "scheduledFor": row["scheduled_for"],
            "nextAttemptAt": row["next_attempt_at"],
            "sentAt": row["sent_at"],
            "deliveredAt": row["delivered_at"],
            "deadLetterAt": row["dead_letter_at"],
            "lastError": row["last_error"],
            "createdAt": row["created_at"],
        }

    def summarize_root_whatsapp_result(self, items: list[dict], recipients: list[dict], mode: str) -> dict:
        statuses = defaultdict(int)
        for item in items:
            statuses[str(item.get("status"))] += 1
        return {
            "status": "ok" if not statuses.get("failed") else "partial",
            "mode": mode,
            "queued": statuses.get("queued", 0) + statuses.get("pending", 0),
            "sent": statuses.get("sent", 0) + statuses.get("delivered", 0),
            "failed": statuses.get("failed", 0) + statuses.get("missing_destination", 0) + statuses.get("unknown_provider", 0) + statuses.get("disabled", 0),
            "mocked": statuses.get("mocked", 0) + statuses.get("skipped", 0),
            "missingCredentials": statuses.get("missing_credentials", 0),
            "recipients": recipients,
            "queueItems": items,
        }

    def list_notification_types(self, context: AuthContext) -> list[dict]:
        preferences = self.list_notification_preferences(context)
        disabled = {item["notificationType"] for item in preferences if not item["enabled"]}
        return [{**item, "enabled": item["id"] not in disabled} for item in NOTIFICATION_TYPES]

    def list_notification_preferences(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "membership_id")
            return list(conn.execute(
                f"""
                select id, tenant_id as "tenantId", membership_id as "membershipId",
                       channel::text, notification_type as "notificationType", enabled,
                       quiet_hours as "quietHours",
                       coalesce(quiet_hours ->> 'frequency', 'imediato') as frequency
                from public.notification_preferences
                where {condition}
                order by notification_type, channel
                """,
                params,
            ).fetchall())

    def list_notification_schedules(self, context: AuthContext) -> list[dict]:
        if self.enabled:
            with self._connect() as conn:
                access = self._access(conn, context)
                condition = "tenant_id = %s"
                params = (access.tenant_id,)
                rows = conn.execute(
                    f"""
                    select id::text,
                           metadata ->> 'name' as name,
                           metadata ->> 'recurrence' as recurrence,
                           coalesce(metadata ->> 'timezone', 'America/Sao_Paulo') as timezone,
                           coalesce(metadata -> 'daysOfWeek', '[]'::jsonb) as "daysOfWeek",
                           coalesce(metadata -> 'times', '[]'::jsonb) as times,
                           coalesce(metadata ->> 'reportType', notification_type) as "reportType",
                           coalesce(metadata -> 'recipients', '[]'::jsonb) as recipients,
                           coalesce(metadata -> 'channels', jsonb_build_array(channel::text)) as channels,
                           coalesce((metadata ->> 'enabled')::bool, status::text <> 'disabled') as enabled
                    from public.notifications
                    where {condition}
                      and notification_type = 'schedule_config'
                    order by created_at desc
                    limit 20
                    """,
                    params,
                ).fetchall()
                if rows:
                    return list(rows)
        return [
            {"id": "daily-ops", "name": "Resumo operacional diário", "recurrence": "diário", "timezone": "America/Sao_Paulo", "daysOfWeek": ["seg", "ter", "qua", "qui", "sex"], "times": ["08:00"], "reportType": "daily", "recipients": ["diretor", "coordenador", "gerente"], "channels": ["system", "email"], "enabled": True},
            {"id": "critical-live", "name": "Alertas críticos em tempo real", "recurrence": "Imediatamente", "timezone": "America/Sao_Paulo", "daysOfWeek": [], "times": ["tempo real"], "reportType": "critical", "recipients": ["gestores no escopo"], "channels": ["system", "whatsapp"], "enabled": True},
            {"id": "weekly-exec", "name": "Relatório executivo semanal", "recurrence": "semanal", "timezone": "America/Sao_Paulo", "daysOfWeek": ["seg"], "times": ["07:30"], "reportType": "weekly", "recipients": ["diretoria"], "channels": ["email"], "enabled": True},
        ]

    def create_notification_schedule(self, context: AuthContext, request: NotificationScheduleCreate) -> dict:
        if not self.enabled:
            return {**request.model_dump(by_alias=True), "id": str(uuid4())}
        with self._connect() as conn:
            access = self._access(conn, context)
            row = conn.execute(
                """
                insert into public.notifications (
                  tenant_id, recipient_membership_id, channel, notification_type,
                  status, title, message, provider, metadata
                )
                values (%s, %s, 'system', 'schedule_config', %s, %s, %s, 'vulcan-scheduler', %s)
                returning id::text
                """,
                (
                    access.tenant_id,
                    access.membership_id,
                    "queued" if request.enabled else "disabled",
                    request.name,
                    f"Agendamento {request.recurrence} para {', '.join(request.channels)}.",
                    Jsonb({**request.model_dump(by_alias=True), "createdBy": context.user_id}),
                ),
            ).fetchone()
            self.write_audit(conn, context, access.tenant_id, "notification_schedule.created", "notification_schedule", row["id"], request.model_dump(by_alias=True))
            conn.commit()
        return next((item for item in self.list_notification_schedules(context) if item["id"] == row["id"]), {**request.model_dump(by_alias=True), "id": row["id"]})

    def update_notification_schedule(self, context: AuthContext, schedule_id: UUID, patch: dict) -> dict | None:
        return self._patch_notification_metadata(context, schedule_id, patch, "notification_schedule.updated")

    def list_notification_templates(self, context: AuthContext) -> list[dict]:
        root_templates = [item for item in self.list_root_whatsapp_templates(context)]
        known_ids = {item["id"] for item in DEFAULT_NOTIFICATION_TEMPLATES}
        return [*DEFAULT_NOTIFICATION_TEMPLATES, *[item for item in root_templates if item["id"] not in known_ids]]

    def preview_notification_template(self, template_id: str, variables: dict) -> dict | None:
        template = next((item for item in [*DEFAULT_NOTIFICATION_TEMPLATES, *ROOT_WHATSAPP_TEMPLATES] if item["id"] == template_id), None)
        if not template:
            return None
        values = {
            "empresa": "Vulcan Demo",
            "usuario": "Colaborador",
            "equipe": "Operação",
            "departamento": "Operações",
            "supervisor": "Supervisor",
            "periodo": "últimas 24 horas",
            "metrica": "ociosidade",
            "valor": "32%",
            "impacto": "alto",
            "economia_estimada": "R$ 2.900",
            "link_dashboard": "http://localhost:3002",
            "link_insight": "http://localhost:3002?view=insights",
            "link_metricas": "http://localhost:3002?view=metrics",
            "data": datetime.now(timezone.utc).date().isoformat(),
            **variables,
        }
        def render(text: str) -> str:
            rendered = text
            for key, value in values.items():
                rendered = rendered.replace("{{" + key + "}}", str(value))
            return rendered
        return {"title": render(template["title"]), "body": render(template["body"]), "variablesUsed": values}

    def _patch_notification_metadata(self, context: AuthContext, notification_id: UUID, patch: dict, action: str, db_status: str | None = None) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "recipient_membership_id", "tenant_id")
            status_sql = "status = coalesce(%s, status),"
            row = conn.execute(
                f"""
                update public.notifications
                set {status_sql}
                    metadata = metadata || %s,
                    sent_at = case when %s = 'sent' then coalesce(sent_at, timezone('utc', now())) else sent_at end
                where id = %s and {condition}
                returning id::text, tenant_id
                """,
                (db_status, Jsonb({**patch, "updatedAt": datetime.now(timezone.utc).isoformat()}), db_status, notification_id, *params),
            ).fetchone()
            if not row:
                conn.rollback()
                return None
            self.write_audit(conn, context, row["tenant_id"], action, "notification", UUID(row["id"]), patch)
            conn.commit()
        return self.get_notification(context, notification_id)

    def retry_notification(self, context: AuthContext, notification_id: UUID) -> dict | None:
        notification = self.get_notification(context, notification_id)
        if not notification:
            return None
        from app.notifications import NotificationPayload, NotificationService
        delivery = NotificationService().send(
            notification["channel"],
            NotificationPayload(
                title=notification["title"],
                message=notification["message"],
                tenant_id=str(notification["tenantId"]),
            ),
        )
        attempts = int(notification.get("attempts") or 0) + 1
        db_status = "sent" if delivery.status in {"ready", "sent", "mocked"} else "failed" if delivery.status in {"failed", "missing_credentials", "missing_destination"} else "queued"
        return self._patch_notification_metadata(
            context,
            notification_id,
            {
                "attempts": attempts,
                "deliveryStatus": delivery.status,
                "lastError": None if db_status in {"sent", "queued"} else delivery.provider_result,
                "lastProviderResult": delivery.provider_result,
            },
            "notification.retry",
            db_status,
        )

    def list_ai_provider_configs(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition = "true" if access.is_root else "(tenant_id is null or tenant_id = %s)"
            params = () if access.is_root else (access.tenant_id,)
            return list(conn.execute(
                f"""
                select id, tenant_id as "tenantId", provider, purpose, model,
                       base_url as "baseUrl", enabled
                from public.ai_provider_configs
                where {condition}
                order by purpose, provider
                """,
                params,
            ).fetchall())

    def list_audit_logs(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition = "true" if access.is_root else "tenant_id = %s"
            params = () if access.is_root else (access.tenant_id,)
            return list(conn.execute(
                f"""
                select id, tenant_id as "tenantId", actor_user_id as "actorUserId",
                       action,
                       coalesce(resource_type, entity_table, 'unknown') as "resourceType",
                       resource_id as "resourceId",
                       created_at as "createdAt"
                from public.audit_logs
                where {condition}
                order by created_at desc
                limit 200
                """,
                params,
            ).fetchall())

    def create_activity_event(self, context: AuthContext, request: ActivityEventCreate) -> ActivityEventCreateResponse:
        if not self.enabled:
            return ActivityEventCreateResponse(id=UUID("20000000-0000-0000-0000-000000000001"), tenantId=request.tenant_id, metricUpdated=True)
        with self._connect() as conn:
            access = self._access(conn, context)
            if not access.is_root and request.tenant_id != access.tenant_id:
                raise ValueError("tenant mismatch")

            membership_id = request.membership_id
            if membership_id is None and request.user_id is not None:
                row = conn.execute(
                    "select id from public.memberships where tenant_id = %s and user_id = %s limit 1",
                    (request.tenant_id, request.user_id),
                ).fetchone()
                membership_id = row["id"] if row else None

            if access.scope not in {"tenant", "global"} and access.membership_id and membership_id != access.membership_id:
                visible = conn.execute(
                    """
                    select exists(
                      select 1 from public.membership_closure
                      where tenant_id = %s and ancestor_membership_id = %s and descendant_membership_id = %s
                    )
                    """,
                    (request.tenant_id, access.membership_id, membership_id),
                ).fetchone()
                if not visible or not visible["exists"]:
                    raise ValueError("membership outside visible hierarchy")

            event = conn.execute(
                """
                insert into public.activity_events (
                  tenant_id, membership_id, device_id, event_type, app_name, window_title,
                  category, duration_seconds, occurred_at, metadata
                )
                values (%s, %s, %s, 'foreground_application_change', %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    request.tenant_id,
                    membership_id,
                    request.device_id,
                    request.app_name,
                    request.window_title,
                    request.category,
                    request.duration_seconds,
                    request.started_at,
                    Jsonb(request.metadata),
                ),
            ).fetchone()

            conn.execute(
                """
                insert into public.operational_metrics (
                  tenant_id, membership_id, metric_key, metric_label,
                  value_numeric, period_start, period_end, metadata
                )
                values (%s, %s, 'app_usage_seconds', %s, %s, %s, %s, %s)
                """,
                (
                    request.tenant_id,
                    membership_id,
                    request.app_name,
                    request.duration_seconds,
                    request.started_at,
                    request.ended_at,
                    Jsonb({"app_name": request.app_name, "category": request.category}),
                ),
            )

            self.write_audit(
                conn,
                context,
                request.tenant_id,
                "activity_event.created",
                "activity_event",
                event["id"],
                {"app_name": request.app_name, "duration_seconds": request.duration_seconds},
            )
            conn.commit()
            return ActivityEventCreateResponse(id=event["id"], tenantId=request.tenant_id, metricUpdated=True)

    def create_notification_record(self, context: AuthContext, request: NotificationSendRequest, status: str, provider_result: str) -> NotificationSendResponse:
        if not self.enabled:
            return NotificationSendResponse(id=None, channel=request.channel, status=status, providerResult=provider_result)
        with self._connect() as conn:
            access = self._access(conn, context)
            if not access.is_root and request.tenant_id != access.tenant_id:
                raise ValueError("tenant mismatch")
            db_status = "sent" if status in {"ready", "sent", "mocked"} else status if status in {"queued", "failed", "missing_credentials", "disabled"} else "failed"
            row = conn.execute(
                """
                insert into public.notifications (
                  tenant_id, recipient_membership_id, channel, notification_type,
                  status, title, message, provider, provider_message_id, sent_at, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, 'vulcan-notification-service', %s, %s, %s)
                returning id
                """,
                (
                    request.tenant_id,
                    request.recipient_membership_id,
                    request.channel,
                    request.notification_type,
                    db_status,
                    request.title,
                    request.message,
                    provider_result,
                    datetime.now(timezone.utc) if db_status == "sent" else None,
                    Jsonb(
                        {
                            "attempts": 1,
                            "deliveryStatus": status,
                            "priority": request.priority,
                            "scheduledFor": request.scheduled_for.isoformat() if request.scheduled_for else None,
                            "actionUrl": request.action_url,
                            "requiresAck": request.priority in {"alto", "critico"},
                            "lastError": provider_result if db_status == "failed" else None,
                            "recipient": str(request.recipient_membership_id) if request.recipient_membership_id else None,
                        }
                    ),
                ),
            ).fetchone()
            self.write_audit(conn, context, request.tenant_id, "notification.created", "notification", row["id"], {"channel": request.channel})
            conn.commit()
            return NotificationSendResponse(id=row["id"], channel=request.channel, status=db_status, providerResult=provider_result)

    def update_notification_preference(self, context: AuthContext, preference_id: UUID, enabled: bool | None, quiet_hours: dict | None = None, frequency: str | None = None) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "membership_id")
            patch = quiet_hours or {}
            if frequency:
                patch["frequency"] = frequency
            row = conn.execute(
                f"""
                update public.notification_preferences
                set enabled = coalesce(%s, enabled),
                    quiet_hours = quiet_hours || %s,
                    updated_at = timezone('utc', now())
                where id = %s and {condition}
                returning id, tenant_id as "tenantId", membership_id as "membershipId",
                          channel::text, notification_type as "notificationType", enabled,
                          quiet_hours as "quietHours",
                          coalesce(quiet_hours ->> 'frequency', 'imediato') as frequency
                """,
                (enabled, Jsonb(patch), preference_id, *params),
            ).fetchone()
            if row:
                self.write_audit(conn, context, row["tenantId"], "notification_preference.updated", "notification_preference", row["id"], {"enabled": enabled, **patch})
            conn.commit()
            return dict(row) if row else None

    def write_audit(
        self,
        conn: psycopg.Connection,
        context: AuthContext,
        tenant_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        metadata: dict,
    ) -> None:
        actor_user_id: str | None = None
        if context.provider != "local":
            try:
                UUID(context.user_id)
                actor_user_id = context.user_id
            except ValueError:
                actor_user_id = None
        conn.execute(
            """
            insert into public.audit_logs (
              tenant_id, actor_user_id, action,
              entity_table, entity_id, change_summary,
              resource_type, resource_id, metadata, created_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tenant_id,
                actor_user_id,
                action,
                resource_type,
                resource_id,
                Jsonb(metadata),
                resource_type,
                resource_id,
                Jsonb(metadata),
                datetime.now(timezone.utc),
            ),
        )

    def write_agent_audit(
        self,
        conn: psycopg.Connection,
        tenant_id: UUID,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        metadata: dict,
    ) -> None:
        conn.execute(
            """
            insert into public.audit_logs (
              tenant_id, actor_user_id, action,
              entity_table, entity_id, change_summary,
              resource_type, resource_id, metadata, created_at
            )
            values (%s, null, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tenant_id,
                action,
                resource_type,
                resource_id,
                Jsonb(metadata),
                resource_type,
                resource_id,
                Jsonb(metadata),
                datetime.now(timezone.utc),
            ),
        )


def get_repository() -> VulcanRepository:
    return VulcanRepository()
