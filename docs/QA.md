# QA

Este documento registra o QA do MVP comercial demonstrável.

## Comandos Recomendados

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
./scripts/bootstrap.sh
corepack pnpm supabase:validate
corepack pnpm supabase:migrate
corepack pnpm seed:demo
corepack pnpm lint:web
corepack pnpm typecheck:web
corepack pnpm build:web
corepack pnpm dev
```

Testes backend:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
PYTHONPATH=backend/api .venv/bin/python -m pytest backend/api/tests/test_api.py -q
```

Teste visual/e2e:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
corepack pnpm --dir frontend/web test:e2e
```

Comandos raiz esperados para aceite comercial:

```bash
./scripts/start-all.sh
./scripts/status-all.sh
corepack pnpm supabase:validate
corepack pnpm supabase:migrate
corepack pnpm seed:demo
corepack pnpm demo:validate
corepack pnpm verify:phase2
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm build
corepack pnpm test
corepack pnpm test:api
```

WhatsApp Evolution/Baileys:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/infra/evolution
./scripts/start.sh
./scripts/status.sh
./scripts/logs.sh
./scripts/restart.sh
```

Autostart:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
./scripts/install-evolution-autostart.sh
```

Checklist Evolution:

- Docker Compose sobe Evolution, Postgres e Redis;
- `/` da Evolution responde health/version;
- systemd service instala e reinicia em falha;
- Vulcan mostra status `unofficial_*`, `mock`, `missing_credentials` ou `disabled`;
- QR aparece quando a instancia precisa conectar;
- API key fica mascarada no frontend;
- teste mock nao finge envio real;
- envio real so ocorre com Evolution conectada;
- fila cria item com `tenant_id`, destinatario, provider, status e tentativas;
- `process-queue` envia/reagenda/falha com backoff;
- retry reabre item falho;
- webhook protegido atualiza entrega quando ha `provider_message_id`;
- Notificacoes mostra fila do Canal Raiz;
- Configuracoes mostra status, QR, fila, logs e falhas;
- operador nao ve dado fora do proprio escopo;
- supervisor/lider ve apenas subarvore;
- diretor/admin ve consolidado do tenant;
- sem WhatsApp/opt-in nao gera envio para destinatario vazio.

## Validações Executadas Nesta Rodada

### Rodada atual - 2026-06-21 - WhatsApp Evolution/Baileys

- `bash -n scripts/docker-*.sh`: aprovado.
- `docker compose --env-file docker/.env -f docker-compose.yml config --quiet`: aprovado.
- `PYTHONPATH=backend/api .venv/bin/python -m pytest backend/api/tests/test_api.py -q`: aprovado, 17 testes.
- `corepack pnpm lint`: aprovado.
- `corepack pnpm typecheck`: aprovado.
- `corepack pnpm build`: aprovado.
- `corepack pnpm test`: aprovado.
- `corepack pnpm test:api`: aprovado.
- `corepack pnpm supabase:validate`: aprovado.
- `corepack pnpm supabase:migrate`: aprovado, incluindo `20260620000200_evolution_whatsapp_resilience.sql`.
- `corepack pnpm seed:demo`: aprovado.
- `corepack pnpm demo:validate`: aprovado, sem vazamento de hierarquia/dispositivos.
- `corepack pnpm verify:phase1`: aprovado.
- `corepack pnpm verify:phase2`: aprovado.
- `corepack pnpm verify:phase3`: aprovado.
- `corepack pnpm verify:phase4`: aprovado.
- `corepack pnpm verify:phase5`: aprovado.
- `corepack pnpm verify:phase6`: aprovado.
- `corepack pnpm verify:phase7`: aprovado.
- `.venv/bin/python -m pytest backend/ingestion-gateway/tests -q`: aprovado.
- `.venv/bin/python -m pytest backend/jobs/tests -q`: aprovado.
- `.venv/bin/python -m pytest backend/query-api/tests -q`: aprovado.
- `.venv/bin/python -m pytest ai/api/tests -q`: aprovado.
- `FRONTEND_PORT=3002 corepack pnpm --dir frontend/web test:e2e`: aprovado.
- `corepack pnpm agent:linux:package`: aprovado.
- `corepack pnpm agent:windows:build`: aprovado.
- `./scripts/start-vulcan.sh`: aprovado, backend/frontend/worker iniciados.
- `./scripts/status-all.sh`: aprovado parcialmente; Vulcan OK, Evolution bloqueada por permissao do Docker daemon no usuario atual.

Smoke WhatsApp:

- `GET /integrations/whatsapp/evolution/status`: aprovado; API key/webhook mascarados como configurados depois de gerar `infra/evolution/.env`.
- Configuracao temporaria mock via `PUT /integrations/whatsapp/evolution/config`: aprovado.
- `POST /integrations/whatsapp/evolution/send-test`: aprovado em mock explicito, sem envio real.
- `POST /integrations/whatsapp/root/send`: aprovado em mock explicito com fila/log e `idempotencyKey`.
- Seed demo passou a limpar `whatsapp_delivery_queue`/`whatsapp_delivery_logs` do tenant demo para evitar resíduo de teste em demonstrações.

Bloqueio de ambiente:

- `infra/evolution/scripts/start.sh` criou `infra/evolution/.env` com `0600`, mas nao conseguiu subir containers porque o usuario atual nao tem acesso a `/var/run/docker.sock`.
- `./scripts/docker-up.sh` tambem depende do mesmo acesso Docker; a configuracao Docker completa foi validada estaticamente, mas os containers nao puderam ser iniciados nesta sessao.
- `systemctl --user status vulcan-evolution.service` falhou com `Failed to connect to bus: Connection refused`; autostart deve ser instalado em sessao/systemd valida ou via `sudo` no host.

### Rodada atual - 2026-06-15 - Notificacoes

- `PYTHONPATH=backend/api python3 -m py_compile backend/api/app/schemas.py backend/api/app/repository.py backend/api/app/main.py scripts/seed_demo.py`: aprovado.
- `corepack pnpm test:api`: aprovado, 14 testes.
- `corepack pnpm --dir frontend/web typecheck`: aprovado.
- `corepack pnpm --dir frontend/web lint`: aprovado.
- `corepack pnpm --dir frontend/web build`: aprovado.

O que foi validado nesta rodada:

- schemas expandidos de notificacao;
- endpoints de summary, tipos, templates, preview, retry, cancelamento, leitura, resolucao e schedules;
- tela Notificacoes compilando com filtros, historico, canais, templates e acoes;
- seed demo atualizado com tipos, preferencias, historico e agendamentos.

Pendencias de QA desta rodada:

- rodar `corepack pnpm seed:demo` contra banco acessivel para confirmar insercao completa do novo seed;
- smoke manual dos endpoints com backend reiniciado;
- validar envio real WhatsApp/e-mail somente quando credenciais existirem;
- validar canal Windows/agente quando endpoint de ack local for implementado.

### Rodada atual - 2026-06-15 - Configuracoes

- `PYTHONPATH=backend/api python3 -m py_compile backend/api/app/schemas.py backend/api/app/repository.py backend/api/app/main.py scripts/seed_demo.py`: aprovado.
- `corepack pnpm test:api`: aprovado, 15 testes.
- `corepack pnpm lint`: aprovado.
- `corepack pnpm typecheck`: aprovado.
- `corepack pnpm build`: aprovado.
- `corepack pnpm supabase:validate`: aprovado.
- `corepack pnpm seed:demo`: aprovado, com concorrencia do agente real prolongando locks de `activity_events`.
- `corepack pnpm demo:validate`: aprovado.
- `corepack pnpm verify:phase2`: aprovado.

Smoke real:

- `GET /settings`: aprovado, 11 secoes.
- `GET /settings/summary`: aprovado.
- `POST /settings/metrics/test`: aprovado.
- `PUT /settings/company`: aprovado, salva e audita.
- `PUT /settings/metrics` com pesos invalidos: reprovado corretamente com `400`.
- `PUT /settings/company` como `operador1`: bloqueado corretamente com `400 sem permissao para alterar configuracoes`.
- `GET /audit-logs`: aprovado e contem `settings.updated`.

Correcoes feitas:

- Configuracoes passou a usar `tenant_settings.settings`.
- Secrets aparecem apenas como status.
- Campos readonly/secret nao sao aceitos em `PUT`.
- Auditoria legada foi normalizada com `coalesce(resource_type, entity_table, 'unknown')`, evitando 500 em logs antigos.

### Rodada atual - 2026-06-11

- `corepack pnpm lint`: aprovado.
- `corepack pnpm typecheck`: aprovado quando executado de forma sequencial. Em uma tentativa paralela com `next build`, o `tsc` recebeu `TS6053` em `.next/types` porque o build estava recriando os tipos ao mesmo tempo.
- `corepack pnpm build`: aprovado.
- `corepack pnpm test`: aprovado, 1 teste unitário de frontend.
- `corepack pnpm test:api`: aprovado, 12 testes.
- `.venv/bin/python -m pytest backend/ingestion-gateway/tests -q`: aprovado, 3 testes.
- `.venv/bin/python -m pytest backend/jobs/tests -q`: aprovado, 10 testes.
- `.venv/bin/python -m pytest backend/query-api/tests -q`: aprovado, 4 testes.
- `.venv/bin/python -m pytest ai/api/tests -q`: aprovado, 2 testes.
- `corepack pnpm agent:linux:package`: aprovado, gerando `agentes/installers/linux/VulcanAgent-Linux.zip`.
- `corepack pnpm agent:windows:build`: aprovado, gerando `VulcanAgentSetup.exe` e `VulcanAgent-Windows-x64.zip`.
- `FRONTEND_PORT=3102 corepack pnpm --dir frontend/web test:e2e`: aprovado, 1 teste Playwright.
- Playwright manual em `http://127.0.0.1:3102`: aprovado, login `teste/teste`, dashboard renderizado, sem console error e sem requests 4xx/5xx relevantes.
- CORS manual: `http://127.0.0.1:3102`, `http://localhost:3000` e `https://vulcan.lanfuture.dev` aceitos; `https://evil.example` bloqueado.
- `GET /health`: aprovado.
- `POST /auth/login` com `teste/teste`: aprovado.
- `GET /supabase/status`: aprovado com `restReachable=true` e `databaseReachable=false`.
- `GET /ai/status`: aprovado.
- `GET /integrations/whatsapp/status`: aprovado com configuracao pendente controlada.
- `GET /integrations/email/status`: aprovado.
- `corepack pnpm supabase:validate`: falhou por conectividade externa ao Postgres Supabase direto: `Network is unreachable` em `db.gkzgssxcrsxvqiorbhss.supabase.co:5432` via IPv6.
- `corepack pnpm supabase:migrate`: falhou pelo mesmo bloqueio de Postgres direto.
- `corepack pnpm seed:demo`: falhou pelo mesmo bloqueio de Postgres direto.
- `corepack pnpm demo:validate`: falhou porque os endpoints dependentes de banco retornaram `503 database_unavailable`, comportamento esperado enquanto `databaseReachable=false`.
- `corepack pnpm verify:phase2`: falhou pelo mesmo bloqueio de Postgres direto.

Correcoes feitas durante esta rodada:

- API passou a devolver `503 database_unavailable` controlado para falha de Postgres direto, em vez de expor stacktrace/500.
- `/supabase/status` agora separa REST e banco direto com `restReachable` e `databaseReachable`.
- Frontend consulta o status do Supabase antes de bater em endpoints dependentes de banco, evitando console poluido e queda visual quando o Postgres direto esta inacessivel.
- CORS local passou a cobrir a porta `3102`, usada quando `3000` esta ocupada por outro projeto.
- Dev server Next quebrado por cache `.next` foi corrigido limpando apenas o cache gerado e reiniciando o frontend.

- `corepack pnpm supabase:validate`: aprovado.
- `corepack pnpm supabase:migrate`: aprovado, incluindo hardening de RLS e idempotência de eventos do agente.
- `corepack pnpm seed:demo`: aprovado.
- `corepack pnpm verify:phase1`: aprovado.
- `corepack pnpm verify:phase2`: aprovado com smoke test de RLS tentando vazar tenant estrangeiro e linhas sem dono.
- `corepack pnpm verify:phase3`: aprovado.
- `corepack pnpm verify:phase4`: aprovado.
- `corepack pnpm verify:phase5`: aprovado.
- `corepack pnpm verify:phase6`: aprovado.
- `corepack pnpm verify:phase7`: aprovado.
- `PYTHONPATH=backend/api .venv/bin/python -m pytest backend/api/tests/test_api.py -q`: aprovado, 12 testes.
- `.venv/bin/python -m pytest backend/ingestion-gateway/tests -q`: aprovado, 3 testes.
- `corepack pnpm agent:linux:package`: aprovado.
- `corepack pnpm agent:windows:build`: aprovado.
- `FRONTEND_PORT=3012 corepack pnpm --dir frontend/web test:e2e`: aprovado, 1 teste Playwright.
- `corepack pnpm demo:validate`: aprovado, validando login, hierarquia, dispositivos, métricas e notificações para todos os perfis demo.
- Teste manual de CORS: `127.0.0.1:3012` aceito e origem externa bloqueada.
- Teste manual de idempotência do agente: envio duplicado do mesmo `eventId` resultou em 1 linha em `activity_events`.
- Observação do agente real `allan-nb`: backend aceitou sincronização manual e pacote novo foi gerado, mas o agente já instalado no usuário `allan` ainda reporta fila alta e último erro `timed out`. O processo precisa ser reinstalado pelo próprio usuário `allan` para carregar o agente empacotado nesta rodada.

Observação: `go test ./...` não foi executado porque o binário `go` não está instalado no ambiente atual. O build Windows oficial do projeto passou via `corepack pnpm agent:windows:build`.

## Resultado Da Visibilidade Por Perfil

Após seed, a API retornou os seguintes escopos esperados:

```text
teste: hierarquia 9, dispositivos 11, eventos24h 123
diretor: hierarquia 8, dispositivos 8, eventos24h 122
coordenador: hierarquia 7, dispositivos 7, eventos24h 108
gerente: hierarquia 6, dispositivos 6, eventos24h 92
supervisor: hierarquia 5, dispositivos 5, eventos24h 76
lider: hierarquia 4, dispositivos 4, eventos24h 60
operador1: hierarquia 1, dispositivos 1, eventos24h 16
operador2: hierarquia 1, dispositivos 1, eventos24h 14
operador3: hierarquia 1, dispositivos 1, eventos24h 14
```

## Pontos Corrigidos

- Seed comercial ficou idempotente e preserva dados reais do agente.
- Usuários locais por perfil foram habilitados no backend apenas para desenvolvimento.
- Acesso local agora consulta `memberships` reais para calcular escopo hierárquico.
- Dashboard inicial recebeu métricas executivas profundas, heatmap, rankings, saúde da operação e feed vivo.
- `verify:phase2` foi adicionado ao `package.json`.
- CORS da API passou a ser configurável por `API_ALLOWED_ORIGINS` e `API_ALLOWED_ORIGIN_REGEX`.
- O dev server da API passou a observar apenas `backend/api`, evitando reload quando agentes são empacotados.
- RLS foi endurecido para impedir leitura de linhas sem dono em tenants estrangeiros.
- Eventos de agente passaram a ter idempotência por `source_event_id`.
- Ingestão de agente passou a registrar auditoria por lote, reduzindo risco de timeout.
- Agentes Linux/Windows passaram a usar lote menor e timeout maior para sincronização.

## Pendências Reais

- Conectar os botões de simulação comercial a jobs reais do backend.
- Testar pacote Windows em uma máquina Windows real.
- Reinstalar o agente Linux local do usuário `allan` e validar queda real da fila offline até zero.
- Validar OAuth real de Gmail/Outlook quando credenciais existirem.
- Ativar WhatsApp real quando o provedor for definido e credenciais forem preenchidas.
- Rodar Playwright com frontend/backend já ativos no ambiente final de apresentação.
- Trocar local/demo auth por fluxo Supabase Auth completo para produção self-service.
- Trocar o executor de migrations por controle real de versões aplicado uma vez por arquivo.
- Adicionar CI/CD executando a matriz de QA automaticamente.
- Adicionar observabilidade externa: tracing, dashboard de erros, métricas e alertas.
