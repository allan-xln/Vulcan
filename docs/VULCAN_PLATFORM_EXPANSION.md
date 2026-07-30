# Expansão da Plataforma Vulcan

## Objetivo

Este documento controla a evolução incremental do Vulcan para uma plataforma unificada de
inteligência operacional, gestão do trabalho e infraestrutura de TI. O módulo **Vulcan
Workforce permanece principal, padrão e fonte do posicionamento do produto**. Infraestrutura
entra como contexto operacional para explicar impacto, causa provável e ações recomendadas;
ela não substitui produtividade, hierarquia, equipes, agentes ou inteligência de trabalho.

Data da auditoria inicial: `2026-07-23`

Repositório auditado: `/home/allan/Documentos/ProjetosLanFuture/Vulcan`

Branch inicial: `main` em `07a8cc9`, alinhado com `origin/main`

## Estado inicial registrado

### Worktree

- Alteração local preexistente e preservada:
  `agentes/windows/agent/cmd/vulcan-agent/main.go`.
- Diretório local preexistente e preservado: `vulcan-logo-downloads/`.
- Nenhuma dessas mudanças pertence à expansão e elas não devem entrar nos commits desta
  iniciativa.
- Caches `.next` e `test-results` haviam sido produzidos por outro usuário local. O baseline
  inicial de lint, build e Playwright falhou por `EACCES`, antes de avaliar o código.
- Os caches foram preservados por renomeação; o Next.js e o Playwright recriaram seus
  diretórios com a propriedade correta.

### Baseline executado antes de alterações de produto

| Verificação | Resultado inicial |
| --- | --- |
| Backend em `GET /health` | `200`, container saudável |
| Frontend em `GET /` | `200`, container saudável |
| `GET /healthz` | `404` (não implementado) |
| TypeScript typecheck | passou |
| Teste unitário web | 1 passou |
| Testes `backend/api` | 17 passaram |
| Testes `backend/ingestion-gateway` | 3 passaram |
| Testes `backend/query-api` | 4 passaram |
| Testes `backend/jobs` | 10 passaram |
| Testes `ai/api` | 2 passaram |
| Lint após isolar cache incompatível | passou, sem avisos |
| Build após isolar cache incompatível | passou |
| Build web inicial | 582 kB de JS na primeira carga da rota `/` |
| Playwright após instalar Chromium local | 1 passou |

Comandos executados:

```bash
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
AUTH_PROVIDER=supabase MOCK_AUTH=true MOCK_DATA=true \
  PYTHONPATH=backend/api .venv/bin/python -m pytest backend/api/tests -q
PYTHONPATH=backend/ingestion-gateway \
  .venv/bin/python -m pytest backend/ingestion-gateway/tests -q
PYTHONPATH=backend/query-api \
  .venv/bin/python -m pytest backend/query-api/tests -q
PYTHONPATH=backend/jobs .venv/bin/python -m pytest backend/jobs/tests -q
PYTHONPATH=ai/api .venv/bin/python -m pytest ai/api/tests -q
FRONTEND_PORT=3002 corepack pnpm --dir frontend/web test:e2e
```

## Arquitetura atual encontrada

### Frontend

- Next.js 15, React 19, TypeScript estrito, Tailwind, SWR, Recharts, Tremor, Framer Motion.
- Aplicação principal em `frontend/web/app/page.tsx`.
- O Workforce atual expõe Comando, Hierarquia, Métricas, Insights, Notificações e
  Configurações.
- Autenticação Supabase é o caminho de produção; autenticação local é fallback de
  desenvolvimento.
- A tela principal já diferencia dados demonstrativos do usuário local de teste real.
- PWA, notificações desktop e atualização periódica de notificações já existem.

### Backend

- `backend/api`: API FastAPI usada pelo produto atual.
- `backend/ingestion-gateway`: ingestão contratual de eventos operacionais, com chave por
  tenant, idempotência e validação de origem.
- `backend/jobs`: normalização determinística, fatos operacionais e métricas diárias.
- `backend/query-api`: consultas tenant-aware sobre fatos e métricas.
- `ai/api`: explicação por IA sobre fatos estruturados; GPT não é fonte da verdade.
- O repositório da API aplica filtros de tenant e de subárvore antes de SQL direto.

### Banco e isolamento

- PostgreSQL/Supabase compartilhado, um banco lógico e schema compartilhado.
- `tenant_id` em dados de negócio.
- RLS ativo nas 44 tabelas públicas de negócio encontradas.
- Hierarquia por `memberships.direct_manager_membership_id` e `membership_closure`.
- Ingestão bruta, eventos normalizados, fatos operacionais e rollups diários já existem.
- `activity_events` é o fluxo usado pela API/agentes atuais.
- `normalized_operational_events` é o fluxo contratual do ingestion gateway.
- Auditoria é append-only para a interface normal e carrega contexto de tenant/ator.

### Agentes

- Linux e Windows funcionais, com fila offline, heartbeat, idempotência e política de
  privacidade.
- Skeleton macOS funcional para heartbeat/fila/sync.
- Não há captura de tela, keylogger, microfone, webcam, clipboard irrestrito ou senha.

### Docker atual

Serviços ativos encontrados no compose principal:

- `db`
- `migrate`
- `backend`
- `frontend`
- `whatsapp-worker`
- `evolution`
- `evolution-db`
- `evolution-redis`

O Redis atual pertence exclusivamente ao runtime da Evolution API. Ele não é cache nem
barramento de eventos do Vulcan.

Portas publicadas:

| Serviço | Porta interna | Publicação esperada |
| --- | --- | --- |
| Frontend | `3002` | `127.0.0.1:3002` |
| Backend | `3001` | `127.0.0.1:3001` |
| PostgreSQL | `5432` | `127.0.0.1:55432` para desenvolvimento |
| Evolution | `8080` | somente rede Docker no stack principal |

Volumes atuais:

- `vulcan_postgres`
- `vulcan_runtime`
- `evolution_instances`
- `evolution_postgres`
- `evolution_redis`

Observação da auditoria: containers já existentes estavam publicados em `0.0.0.0`, apesar
do default seguro do compose ser `127.0.0.1`. A configuração local deve ser revisada antes
de uso fora de uma máquina de desenvolvimento.

## Componentes existentes que serão preservados

- Workforce como módulo padrão.
- Supabase Auth, PostgreSQL e RLS.
- Hierarquia, equipes, usuários, dispositivos e adoção.
- Agentes e contratos operacionais existentes.
- Ingestão bruta, normalização, fatos e métricas diárias.
- Insights determinísticos com explicação por IA.
- Notificações, WhatsApp, e-mail e auditoria.
- Seeds, perfis demonstrativos e compatibilidade com agentes implantados.
- Identidade visual e navegação em camada de comando.

## Problemas encontrados

### Estruturais

- `frontend/web/app/page.tsx` possui mais de 8 mil linhas.
- `backend/api/app/repository.py` possui mais de 4,8 mil linhas.
- A API principal concentra muitas rotas em um único módulo.
- Há dois conjuntos históricos sobrepostos de fundação de schema. Eles funcionam, mas
  aumentam o risco de migrations futuras.
- Migrations históricas contêm declarações redundantes. Não serão reescritas, pois podem já
  ter sido aplicadas em ambientes reais.
- CI instala somente dois serviços Python e executa apenas `verify-phase1`.
- Testes web iniciais cobrem um componente e um fluxo E2E de login.
- Não existe modelo canônico que una eventos de Workforce e infraestrutura.
- Não existem sites, redes, ativos genéricos, relacionamentos/topologia, políticas de
  discovery, incidentes ou retenção por classe.
- Não existem `/healthz`, `/readyz`, `/livez` e `/version`.
- O “tempo real” atual é majoritariamente polling.

### Segurança e operação

- Fallbacks locais usam credenciais conhecidas e devem permanecer impossíveis em produção.
- Enrollment de agente ainda usa token compartilhado; produção precisa de tokens assinados
  por tenant/dispositivo, expiração e revogação.
- `docker compose` emitiu avisos de secrets ausentes da Evolution. O serviço não deve ser
  tratado como pronto enquanto esses itens estiverem ausentes.
- O banco não deve ser publicado fora de loopback.
- Root possui capacidade técnica ampla; acesso a conteúdo sensível de tenants deve exigir
  contexto explícito e auditoria, não acontecer automaticamente.

## Decisões técnicas

### ADR embutida: fonte de verdade e evolução de escala

**Decisão atual:** preservar PostgreSQL/Supabase como fonte de verdade e implementar as
fundações de eventos, timeline, ativos, discovery e incidentes no banco atual.

**Motivo:** o repositório determina explicitamente uma base PostgreSQL única e proíbe
reintroduzir ClickHouse ou Redis sem decisão arquitetural. O volume atual não demonstra
necessidade operacional de outro datastore.

**Gates para componentes futuros:**

- Redis: somente após necessidade medida de presença/fanout/locks que PostgreSQL e processos
  atuais não consigam atender.
- NATS JetStream: somente após múltiplos consumidores independentes, replay operacional e
  throughput sustentado justificarem barramento dedicado.
- ClickHouse: somente após volume/latência/retensão tornarem consultas históricas no
  PostgreSQL inviáveis.
- VictoriaMetrics: somente para métricas temporais de alta cardinalidade comprovada.
- MinIO: somente para evidências/relatórios cujo volume ou política exija objeto dedicado.
- OpenTelemetry Collector: introdução preferencial quando houver mais coletores externos e
  contrato de recepção estabilizado.

Cada gate exige ADR, benchmark, plano de migração, isolamento por tenant, backup, restore e
rollback. Nenhum desses componentes é necessário para a fundação funcional desta fase.

### Evento canônico

- Schema versionado e extensível.
- UUID estável, origem, tenant, tempos de ocorrência/recepção e origem confiável.
- Idempotência por tenant + origem + id do evento na origem.
- Relógio do dispositivo separado do relógio do servidor.
- Sinal explícito de evento offline e drift de relógio.
- Contexto, métricas e dispositivo em JSON versionado, sem segredo.
- Classificação de privacidade e política de retenção.
- Compatibilidade por espelhamento dos `activity_events`; o fluxo antigo não será removido.

### Realtime

- Primeira implementação por SSE autenticado e tenant-scoped, com PostgreSQL como fonte.
- O frontend usará `fetch` streaming com header de autorização, evitando token em query
  string.
- Barramento dedicado permanece um gate de escala, não requisito prematuro.

### Discovery

- Serviço separado, mas com contrato e banco comuns.
- Desabilitado por padrão.
- Somente leitura, limites rígidos, allowlist obrigatória e denylist.
- Redes públicas bloqueadas por padrão.
- Sem alteração remota, configuração, credencial inventada ou automação corretiva.
- Toda execução e aprovação gera auditoria.

### Segredos

- Cadastros armazenam somente `secret_ref`.
- O valor de segredo fica fora das tabelas de inventário.
- API nunca devolve segredo completo.
- Testes de credencial retornam estado e data, não o conteúdo.

## Arquitetura-alvo incremental

```text
Agentes / integrações / discovery somente leitura
                    |
                    v
        contrato de evento canônico versionado
                    |
                    v
     FastAPI + ingestion gateway + workers determinísticos
                    |
          +---------+---------+
          |                   |
          v                   v
 PostgreSQL/Supabase       SSE tenant-scoped
 RLS + auditoria              |
          |                   v
          +----------> Next.js Vulcan
                       Workforce padrão
                       Infraestrutura contextual
                       Timeline unificada
```

Módulos lógicos planejados no mesmo produto:

1. Vulcan Workforce — principal e habilitado por padrão.
2. Vulcan Infrastructure.
3. Vulcan Timeline.
4. Vulcan Assets.
5. Vulcan Print.
6. Vulcan Security.
7. Vulcan Intelligence.
8. Vulcan Automations.
9. Vulcan Compliance.
10. Vulcan Administration.

Módulos são habilitados por tenant/plano. Eles compartilham autenticação, tenant, hierarquia,
permissões, auditoria, backend e identidade visual.

## Modelo de infraestrutura planejado

- `sites`: unidade/local físico e timezone.
- `infrastructure_networks`: rede/sub-rede, gateway, VLAN, DNS, DHCP e permissão de
  discovery.
- `infrastructure_assets`: ativo genérico para estação, servidor, switch, AP, firewall,
  impressora, nobreak, controlador, serviço ou aplicação.
- `asset_interfaces`: porta/interface, VLAN, estado administrativo/operacional e contadores.
- `asset_relationships`: topologia e dependência com origem/confiança.
- `credential_references`: metadado de referência, nunca segredo.
- `integration_instances`: adapters, capacidades e estado de conexão somente leitura.
- `discovery_policies`, `discovery_runs`, `discovery_findings`: execução segura e aprovação.
- `unified_events`: timeline canônica.
- `incidents`, `incident_events`: correlação explicável.
- `retention_policies`: retenção por classe.
- `tenant_modules`: habilitação por tenant/plano.

## Framework de integrações

Contrato comum:

```text
authenticate
testConnection
discover
collectInventory
collectMetrics
collectEvents
getHealth
getTopology
normalize
mapAssets
handleRateLimit
handleRetry
audit
```

Adapters iniciais são apenas estrutura segura; nenhuma credencial será inventada e nenhum
equipamento será alterado. Prioridades futuras: SNMP, UniFi, FortiGate, syslog, traps,
NetFlow/sFlow/IPFIX, WEF, Print Server, Proxmox, VMware, Docker, Linux, Windows Server,
UPS, impressoras, API genérica e webhook.

## Docker por fases

Perfis-alvo:

- `core`: web, API, migrations, PostgreSQL e workers essenciais.
- `observability`: recepção/saúde adicional quando aprovada por ADR.
- `network`: discovery e receivers de rede somente leitura.
- `security`: receivers e análises de segurança.
- `development`: simuladores e ferramentas locais.
- `production`: políticas de runtime sem credenciais locais/fallback.

Redes-alvo:

- `edge`
- `application`
- `telemetry`
- `data`
- `internal`

A expansão de compose será incremental. Serviços atuais não serão quebrados para satisfazer
uma reorganização cosmética.

## Variáveis planejadas

Sem valores secretos:

```env
VULCAN_BUILD_VERSION=
VULCAN_COMMIT_SHA=
VULCAN_REALTIME_POLL_SECONDS=2
DISCOVERY_ENABLED=false
DISCOVERY_WORKER_POLL_SECONDS=10
DISCOVERY_MAX_TARGETS_PER_RUN=256
DISCOVERY_MAX_CONCURRENCY=16
DISCOVERY_ALLOW_PUBLIC_NETWORKS=false
DISCOVERY_MAX_TIMEOUT_MS=2000
DISCOVERY_ALLOWED_TCP_PORTS=22,53,80,443,445,515,631,9100
```

## Migração e compatibilidade

1. Criar migration somente aditiva.
2. Criar tabelas novas com `tenant_id`, FKs, constraints, índices e RLS.
3. Habilitar Workforce para todos os tenants.
4. Habilitar módulos novos por flags explícitas.
5. Espelhar e fazer backfill de `activity_events` em `unified_events`.
6. Manter APIs e agentes atuais sem mudança obrigatória de contrato.
7. Introduzir rotas novas em router isolado.
8. Introduzir views frontend novas sem trocar a tela inicial.
9. Validar RLS com tenant estrangeiro em transação revertida.
10. Aplicar rollback operacional por feature flag; tabelas novas não serão removidas
    automaticamente.

Rollback documentado:

- desabilitar `infrastructure`, `timeline` e `assets` em `tenant_modules`;
- parar o profile `network`;
- manter tabelas e dados para auditoria;
- continuar usando `activity_events`, métricas e telas Workforce anteriores;
- não executar `DROP TABLE` como rollback automático.

## Implementação entregue nesta execução

### Dados e contratos

- Migration aditiva `20260723000100_vulcan_platform_expansion.sql`.
- Contrato JSON `2026-07-vulcan-event.v1` e tipos TypeScript compartilhados.
- Modelo de módulos, sites, redes, referências de credencial, ativos, interfaces,
  relacionamentos, adapters, discovery, eventos unificados, incidentes e retenção.
- FKs compostas de tenant, constraints, índices, RLS, grants e auditoria.
- Inicialização automática e idempotente dos módulos, retenções, papéis e permissões para
  novos tenants.
- Trigger e backfill idempotente de `activity_events` para `unified_events`; `activity_events`
  e agentes existentes permanecem inalterados.
- 27.503 eventos existentes foram normalizados na aplicação local inicial. O total continua
  crescendo com a operação normal dos agentes.

### API e realtime

- Router e repositório separados do monólito para health, módulos, inventário, timeline,
  eventos, discovery, adapters e incidentes.
- `/healthz`, `/readyz`, `/livez` e `/version`.
- CRUD aditivo de sites, redes e ativos.
- Evento canônico idempotente e gerador de desenvolvimento proibido em produção.
- Timeline com filtros, busca, cursor e recorte por tenant/hierarquia.
- SSE autenticado por header, sem token na URL.
- Score de saúde com fórmula e componentes visíveis.
- RBAC diferencia leitura e administração; operador não recebe inventário e auditor não é
  promovido implicitamente a administrador.

### Interface

- Workforce/Comando continua sendo a rota padrão.
- `Vulcan Infrastructure` na mesma camada de navegação, com visão geral, inventário,
  cadastro, discovery, incidentes, adapters e saúde da plataforma.
- `Vulcan Timeline` com filtros, paginação, origem real/simulada, severidade, confiança,
  detalhes técnicos progressivos e atualização SSE.
- Estados vazios, skeleton, erro real e identificação explícita de dados simulados.

### Discovery

- Serviço independente `backend/discovery`, container não root e profile Docker `network`.
- ICMP, DNS reverso e TCP connect limitado por allowlist global.
- CIDR privado obrigatório por padrão, denylist, exclusões, timeout, concorrência e limite
  de alvos.
- Política nasce desativada, exige aprovação auditada e o worker ainda exige
  `DISCOVERY_ENABLED=true`.
- Achados permanecem `discovered/pending_review`; não existe aprovação ou alteração remota
  automática.

### Docker e CI

- Redes `edge`, `application`, `telemetry`, `data` e `internal`; banco fica na rede de
  dados interna e publica somente em loopback por default.
- Backend usa `/readyz` no healthcheck.
- Discovery tem profile, limites de recurso, health file e dependências reais.
- Frontend inicia pelo binário Next já incluído na imagem; o runtime não baixa pnpm nem
  depende da disponibilidade do registry.
- A senha demo preexistente foi removida de todas as variáveis `NEXT_PUBLIC_*`; credencial
  de seed permanece exclusivamente no ambiente do backend.
- Autenticação local é recusada incondicionalmente em `production`, e os defaults do
  compose permanecem desabilitados até ativação explícita no ambiente local.
- CI executa as suítes de API, IA, discovery, ingestion, jobs e query, aplica todas as
  migrations em PostgreSQL 16 limpo e roda o teste RLS da plataforma.

## Validação final

Validação executada em `2026-07-23`:

| Verificação | Resultado |
| --- | --- |
| Lint Next.js | passou, sem avisos |
| Typecheck web e contratos compartilhados | passou |
| Testes unitários web | 3 passaram |
| Testes API | 29 passaram |
| Testes IA | 2 passaram |
| Testes ingestion gateway | 3 passaram |
| Testes query API | 4 passaram |
| Testes jobs | 10 passaram |
| Testes discovery | 5 passaram, sem acessar a rede |
| E2E Chromium em imagem de produção | 1 passou |
| Build Next.js | passou; primeira carga da rota `/`: 594 kB |
| Build de imagens API, frontend e discovery | passou |
| 15 migrations em PostgreSQL temporário limpo | passaram |
| RLS com tenant próprio e estrangeiro | passou com rollback |
| Compose `core` e profile `network` | configuração válida |
| API `/readyz` em container | `200`, PostgreSQL/schema/fila reais |
| Frontend em container | `200`, Next pronto em 395 ms |
| RBAC real de operador | `403` ao consultar inventário |
| Logs dos containers | sem traceback, fatal, panic ou HTTP 500 |

Na base local preservada havia 27.587 eventos unificados no momento da validação. Das 59
tabelas públicas, 58 possuem RLS; a exceção é `vulcan_root_users`, que não contém dados de
tenant e é protegida pelas regras específicas de root já existentes.

Containers isolados usados para validar o código novo, sem substituir a stack que já estava
em uso:

| Serviço | Endpoint/estado validado |
| --- | --- |
| `vulcan-backend:platform-validation` | `127.0.0.1:3103`, `/readyz` real, healthy |
| `vulcan-frontend:platform-validation` | `127.0.0.1:3104`, UI + E2E, healthy |
| `vulcan-discovery:platform-validation` | desativado, somente leitura, healthy |

Comandos finais principais:

```bash
./scripts/verify-phase1.sh
PYTHONPATH=backend/ingestion-gateway .venv/bin/python -m pytest backend/ingestion-gateway/tests -q
PYTHONPATH=backend/query-api .venv/bin/python -m pytest backend/query-api/tests -q
PYTHONPATH=backend/jobs .venv/bin/python -m pytest backend/jobs/tests -q
PYTHONPATH=backend/discovery .venv/bin/python -m pytest backend/discovery/tests -q
VULCAN_PLATFORM_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55432/vulcan \
  ./scripts/verify-platform-expansion.sh
FRONTEND_PORT=3104 corepack pnpm --dir frontend/web test:e2e
docker compose --profile network config --quiet
```

Durante a validação, um servidor Next de desenvolvimento antigo ficou inconsistente porque
um build concorrente substituiu seu `.next`; a instância foi reiniciada e o E2E passou. A
imagem de produção também revelou duas falhas preexistentes de runtime — download de pnpm
no start e diretório de trabalho incorreto — corrigidas e retestadas no container final.

## Fases

### Fase 1 — fundação

- [x] auditoria do projeto
- [x] baseline executável
- [x] documento de expansão inicial
- [x] evento canônico versionado
- [x] timeline unificada
- [x] realtime tenant-scoped
- [x] health/readiness/liveness/version

### Fase 2 — ativos e infraestrutura

- [x] sites
- [x] redes
- [x] ativos
- [x] interfaces e relacionamentos no modelo de dados
- [x] referências de credenciais no modelo seguro
- [x] módulos por tenant
- [x] discovery somente leitura
- [x] framework de adapters

### Fase 3 — rede e incidentes

- [ ] SNMP
- [ ] syslog/traps
- [ ] métricas de infraestrutura
- [ ] topologia
- [ ] alertas
- [x] modelo e leitura de incidentes

### Fase 4 — correlação

- [ ] correlator determinístico
- [ ] impacto na produtividade
- [ ] visão executiva cruzada
- [ ] explicação operacional por IA sobre evidências

### Fase 5 — produção

- [x] suíte ampliada para fundações novas
- [x] hardening do runtime isolado
- [x] backup/restore testado em ambiente temporário e em stack de produção isolada
- [ ] retenção automática
- [x] health básico da plataforma
- [x] runbook e release de produção

## Riscos e controles

| Risco | Controle |
| --- | --- |
| Vazamento entre tenants | RLS, filtros no repositório, testes com tenant estrangeiro |
| Root acessar cliente implicitamente | contexto explícito, permissão e auditoria |
| Discovery invasivo | disabled por padrão, allowlist, limites e read-only |
| Segredo em inventário | somente `secret_ref`, resposta mascarada |
| Duplicidade de evento | chave idempotente por tenant/origem |
| Relógio incorreto | `occurred_at`, `received_at` e drift separados |
| Quebra dos agentes | espelhamento aditivo; contrato atual preservado |
| Banco crescer sem controle | índices, paginação por cursor, retenção configurável |
| UI virar Grafana | mensagens amigáveis, drill-down e detalhe técnico progressivo |
| IA inventar causa | regras/topologia/evidência primeiro; IA só explica |
| Compose excessivo | profiles opcionais e gates por ADR |

## Checklist de Definition of Done

- [x] Vulcan atual executou antes da mudança.
- [x] Login local passou no Playwright.
- [x] Baseline de testes foi registrado.
- [x] Migrations incrementais aplicam sem apagar dados.
- [x] Login e Workforce continuam funcionando.
- [x] Isolamento por tenant é testado para tabelas novas.
- [x] Timeline recebe eventos Workforce e aceita eventos de infraestrutura.
- [x] Atualização realtime funciona.
- [x] Módulo Infrastructure existe sem substituir a home.
- [x] Sites, redes e ativos podem ser cadastrados.
- [x] Discovery funciona apenas em modo seguro.
- [x] Eventos simulados são explicitamente identificados.
- [x] Health checks novos funcionam.
- [x] `.env.example` está atualizado.
- [x] Lint, typecheck, build, unitários, integração e E2E passam.
- [x] Containers atualizados respondem aos health checks.
- [x] Logs são revisados.
- [x] Escopo preparado sem secrets ou alterações locais preexistentes.
- [x] Push do branch correto é confirmado.

## Status de execução

| Marco | Estado |
| --- | --- |
| Descoberta e auditoria | concluído |
| Baseline | concluído |
| Documento inicial | concluído |
| Fundação de dados | concluído |
| API de plataforma | concluído |
| UI integrada | concluído |
| Discovery | concluído em modo seguro/fase 2 |
| Validação final | concluída |
| Commits e push | concluídos em `main` |

## Limitações conhecidas e próximos passos

Itens deliberadamente não apresentados como prontos:

1. Implementar APIs/UI de interfaces, relacionamentos e topologia sem criar grafo ilegível.
2. Implementar adapters SNMP/UniFi/FortiGate e receivers syslog/traps com credenciais por
   secret reference, rate limit e dead-letter queue.
3. Criar regras de alerta e correlator determinístico para produzir incidentes; a tabela e
   a leitura existem, mas não há causa provável inventada.
4. Relacionar impacto de infraestrutura aos indicadores do Workforce e à visão executiva.
5. Implementar serviço de retenção com preview, backup e restore ensaiados.
6. Migrar os agentes legados que ainda usam enrollment token compartilhado para o contrato
   v2 já disponível, com token curto, identidade Ed25519 por instalação e tenant resolvido
   pelo servidor.
7. Medir volume/latência antes de aprovar NATS, Redis de plataforma, ClickHouse,
   VictoriaMetrics, MinIO ou OpenTelemetry Collector.
8. Quebrar gradualmente `page.tsx` e `repository.py`; nenhum refactor grande foi feito nesta
   entrega para preservar compatibilidade.

## Histórico: preparação da migração para `192.168.200.7` — 2026-07-29

Foi criada uma implantação de produção self-hosted incremental, sem substituir a
arquitetura existente:

- autenticação de produção pelo PostgreSQL com token assinado, revalidação de membership e
  bloqueio de mutações para `read_only` e `auditor`;
- provisionamento idempotente do tenant ERS, dos acessos root/admin/Wallboard e dos módulos
  habilitados, sem rotacionar senhas existentes por padrão;
- Wallboard real em `/wallboard`, com SSE, polling de recuperação, reconexão, estado da
  fonte e nenhuma métrica fictícia;
- imagens multi-stage, usuários não-root, root filesystem somente leitura, secrets por
  arquivo, redes separadas, healthchecks, limites, logs estruturados e volumes nomeados;
- backup criptografado, restore inicial protegido, restart, rollback de imagem, checksums e
  SBOM CycloneDX por imagem;
- `discovery` em profile separado, desabilitado por padrão e somente leitura.

O restore do snapshot preservado foi executado em uma stack `vulcan-production` isolada,
publicada apenas em `127.0.0.1:18080`. A validação confirmou:

| Item | Resultado |
| --- | ---: |
| Tenants | 1 |
| Usuários de autenticação | 15 (12 preservados + 3 acessos de produção) |
| Memberships | 13 |
| Dispositivos | 27 |
| Identidades de agente | 21 |
| Eventos unificados | 39.349 |
| Logs de auditoria | 58.046 |
| Evolution | 37 tabelas e 1 instância |

Root, administrador ERS e Wallboard autenticaram pelo banco. O Wallboard acessou métricas,
Infrastructure, Timeline, Agents e Incidents com `200`; uma tentativa de mutação pelo
Wallboard foi recusada com `403`. Chromium validou a página real, e `/healthz`, `/readyz`,
`/livez`, `/version`, `/` e `/wallboard` passaram pelo proxy.

Limites mantidos de forma explícita:

- o servidor `192.168.200.7` ainda não recebeu a release porque a credencial administrativa
  foi rejeitada por WinRM e SMB;
- o servidor `192.168.200.4` não sofreu remoção, alteração ou reinicialização;
- agentes ainda não foram repontados;
- Infrastructure não possui sites, redes ou ativos reais cadastrados neste snapshot;
- nenhum Workstation, Server ou Collector foi validado contra o endpoint definitivo.

O procedimento, os gates e os comandos operacionais estão em
`docs/PRODUCTION_MIGRATION_192_168_200_7.md`.

## Corte de produção ERS por `192.168.200.4:8099` — 2026-07-29

A missão de destino foi corrigida posteriormente. O servidor 7 deixou de ser obrigatório.
O estado preservado do runtime temporário `.160` foi migrado para a VM Linux dedicada
`VULCAN-PROD01` (`192.168.200.26`, VMID `103` no `PVE02`), sem mover containers ou
banco para o controlador de domínio.

Estado validado:

- borda oficial `192.168.200.4:8099 -> 192.168.200.26:8099`;
- release de plataforma `0.3.6` e agente `0.3.1`;
- tenant ERS, Workforce, Infrastructure, Assets, Timeline, Agents, Print, Intelligence e
  Wallboard habilitados;
- login real do backend no frontend, sem autenticação demo;
- Wallboard read-only, SSE e Chromium validados pelo IP oficial;
- MSI, `.deb`, checksums e SBOM publicados;
- Workstation Agent real online, com fila cifrada/replay comprovados;
- backup criptografado e restore em bancos descartáveis validados;
- backup diário local e job de snapshot Proxmox configurados;
- serviços AD/DNS preservados e testes focados do `dcdiag` aprovados.

O runbook e os riscos atuais estão em
`docs/PRODUCTION_ERS_192_168_200_4.md`.

## Expansão Vulcan Agent v2 — 2026-07-23

O agente foi evoluído de forma aditiva em `agentes/agent`, mantendo os agentes Linux/Windows
legados como rollback. O novo núcleo Go compartilha Workstation, Server e Collector sem
separar o produto.

Componentes entregues:

- migration incremental para tokens, identidades, políticas, nonces, comandos e releases;
- enrollment de uso único com hash no banco;
- identidade Ed25519 local e assinatura de cada request;
- política Ed25519 assinada, aplicação atômica e rollback local;
- fila SQLite cifrada, prioridades, retry, deduplicação e replay;
- collectors de saúde, inventário, rede, atividade suportada, checks HTTP/TCP e discovery
  explícito/read-only;
- API v2 integrada a `devices`, `unified_events`, `activity_events` e auditoria;
- migration de guarda para impedir espelho canônico duplicado no caminho v2 sem alterar o
  espelho dos agentes legados;
- migration de re-enrollment que preserva identidades revogadas e mantém somente uma
  identidade ativa por tenant/dispositivo;
- área visual de agentes, políticas, instalação, diagnóstico, eventos e auditoria;
- MSI, `.deb`, systemd user/system, Windows LocalService, SBOM e checksums.

Portas e serviços:

| Componente | Porta/direção | Observação |
| --- | --- | --- |
| agente → Vulcan API | HTTPS TCP 443 | 3001 apenas no desenvolvimento local |
| Workstation/Server | nenhuma entrada | não recebem NATS ou acesso remoto |
| Collector 0.2.0 | nenhuma entrada | receivers syslog/traps/flows ainda não existem |
| `VulcanAgent` Windows | serviço automático | conta LocalService |
| `vulcan-agent` Linux | system unit | usuário sem login `vulcan-agent` |
| `vulcan-agent-user` | user unit | sessão Workstation |

Variáveis:

- `VULCAN_AGENT_POLICY_SIGNING_KEY_FILE`: chave Ed25519 persistente do backend;
- `VULCAN_ENROLLMENT_TOKEN`: token curto apenas no processo de enrollment;
- `VULCAN_AGENT_CONFIG_DIR`, `VULCAN_AGENT_DATA_DIR`, `VULCAN_AGENT_LOG_DIR`: paths
  explícitos usados pelo serviço Linux.

Validação executada:

- migration aplicada em banco temporário e aditivamente no banco local;
- suíte API ampliada de 29 para 34 testes;
- enrollment real, política assinada, heartbeat e ingestão canônica;
- API indisponível, fila local, retorno e replay até profundidade zero;
- repetição do mesmo request assinado rejeitada;
- `go test -race`, `go vet`, cross-build Windows e frontend lint/typecheck/unit;
- `.deb` e MSI gerados e inspecionados; binário Windows executado via Wine;
- 58 testes Python e cinco unitários web passaram;
- E2E Chromium passou sobre os containers reais, incluindo login, Workforce,
  Infrastructure, Timeline, Agentes e os links de download MSI/DEB;
- API, frontend, banco, Evolution e worker foram revisados saudáveis depois do deploy;
- amostra de 73 segundos do agente Go: 12,9–13,2 MiB RSS, CPU ociosa 0,0%, nove threads e
  dez descritores.

Limites não apresentados como prontos:

- Windows SCM e MSI ainda exigem homologação em Windows real;
- pacote `.deb` não substituiu o agente legado ativo nesta máquina;
- assinatura Authenticode/manifesto e auto-update ainda não foram habilitados;
- printing, Windows Event Log detalhado, USB, containers, SNMP, syslog/traps/flows,
  topologia e adapters permanecem nas próximas fases;
- soak de 24 horas e simulação de 1.000 agentes ainda precisam ser executados.
