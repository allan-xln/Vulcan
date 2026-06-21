# WhatsApp Centralizado

O Vulcan usa um Canal WhatsApp Raiz: um numero oficial da plataforma envia metricas, alertas, insights, relatorios e avisos para os usuarios dos tenants. O cliente nao precisa conectar o proprio WhatsApp para comecar.

O LanChat pode inspirar padroes de sessao/reconexao, mas o Vulcan nao altera arquivos, banco, secrets ou runtime do LanChat.

## Configuracao Central

O numero e os secrets ficam em ambiente/cofre, nunca espalhados no codigo:

```env
ROOT_WHATSAPP_ENABLED=true
ROOT_WHATSAPP_PROVIDER=evolution
ROOT_WHATSAPP_NUMBER=
ROOT_WHATSAPP_NAME=Notificações Vulcan
ROOT_WHATSAPP_MOCK_MODE=false
ROOT_WHATSAPP_BASE_URL=
ROOT_WHATSAPP_API_KEY=

EVOLUTION_ENABLED=true
EVOLUTION_BASE_URL=http://127.0.0.1:8080
EVOLUTION_API_KEY=
EVOLUTION_INSTANCE_NAME=vulcan-root
EVOLUTION_WEBHOOK_URL=http://127.0.0.1:3001/integrations/whatsapp/evolution/webhook
EVOLUTION_WEBHOOK_TOKEN=

WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=
WHATSAPP_GRAPH_API_VERSION=v25.0
WHATSAPP_REQUEST_TIMEOUT_SECONDS=15
```

`ROOT_WHATSAPP_MOCK_MODE=true` registra simulacao explicita. Producao deve usar `false` e credenciais reais.

## Status

- `connected`: provider real pronto.
- `mock`: canal raiz configurado, mas envio real desligado por mock explicito.
- `missing_credentials`: faltam credenciais reais e mock esta desligado.
- `disabled`: canal raiz desativado.
- `unofficial_disconnected`: Evolution/Baileys acessivel, mas instancia desconectada.
- `unofficial_qr_required`: instancia precisa de QR Code.
- `unofficial_connected`: Evolution/Baileys conectada.
- `unofficial_failed`: provider nao oficial indisponivel.
- `unofficial_rate_limited`: provider nao oficial limitou temporariamente.
- `official_ready_future`: caminho oficial Meta Cloud API preparado para migracao.
- `sent` / `delivered`: provider confirmou envio/entrega.
- `mocked`: evento simulado assumido.
- `failed`: provider respondeu erro.
- `pending` / `queued` / `sending` / `retrying`: fila aguardando envio ou retentativa.
- `provider_unavailable` / `qr_required` / `rate_limited`: falhas recuperaveis de provider.

O Vulcan nunca marca envio real sem resposta do provider.

## Modelo De Dados

Migration principal: `20260620000100_root_whatsapp_channel.sql`.

Tabelas:

- `root_whatsapp_templates`: templates globais ou por tenant.
- `notification_schedules`: agendamentos reais por tenant.
- `whatsapp_delivery_queue`: fila duravel por tenant, destinatario e mensagem.
- `whatsapp_delivery_logs`: historico de tentativas, erro, provider e auditoria.
- `notifications`: historico principal exibido no produto.
- `notification_preferences`: preferencias por membership, canal e tipo.

Todas as tabelas de negocio usam `tenant_id` e RLS. A API tambem aplica filtro por hierarquia antes de criar fila.

## Destinatarios E Escopo

Cada tenant configura quem recebe por preferencias e hierarquia:

- Diretor/admin: visao geral do tenant.
- Coordenador/gerente: propria area e subarvore.
- Supervisor/lider: propria equipe.
- Colaborador: metricas basicas pessoais.

O resolver de destinatarios usa `memberships`, `membership_closure`, `notification_preferences` e WhatsApp cadastrado no usuario. Se uma preferencia estiver desabilitada, o usuario nao entra na fila daquele tipo.

## Templates

Tipos iniciais:

- `metrica`
- `alerta`
- `insight`
- `relatorio_diario`
- `relatorio_semanal`
- `critico`

Variaveis comuns:

- `{{escopo}}`
- `{{metrica}}`
- `{{periodo}}`
- `{{valor}}`
- `{{impacto}}`
- `{{resumo}}`
- `{{recomendacao}}`
- `{{economia_estimada}}`
- `{{link_dashboard}}`

Para WhatsApp Business API em producao, templates recorrentes e conversas iniciadas pela empresa devem ser aprovados conforme regra do provider.

## Fluxo

1. Insights, Metricas, Comando ou Notificacoes chamam o canal raiz.
2. A API resolve destinatarios pelo tenant e hierarquia.
3. A API renderiza template por destinatario.
4. A API grava `notifications` e `whatsapp_delivery_queue`.
5. Envio imediato processa a fila na hora; agendamento aguarda worker.
6. Cada tentativa grava `whatsapp_delivery_logs`.
7. Status final volta para `notifications.metadata.deliveryStatus`.
8. Auditoria registra criacao de fila e mudanca de entrega.

## Endpoints

- `GET /integrations/whatsapp/status`
- `POST /integrations/whatsapp/test`
- `GET /integrations/whatsapp/evolution/status`
- `PUT /integrations/whatsapp/evolution/config`
- `POST /integrations/whatsapp/evolution/test`
- `GET /integrations/whatsapp/evolution/qr`
- `POST /integrations/whatsapp/evolution/reconnect`
- `POST /integrations/whatsapp/evolution/send-test`
- `POST /integrations/whatsapp/evolution/webhook`
- `GET /integrations/whatsapp/root/recipients`
- `POST /integrations/whatsapp/root/send`
- `POST /integrations/whatsapp/root/process-queue`
- `GET /integrations/whatsapp/root/queue`
- `GET /integrations/whatsapp/root/logs`
- `POST /integrations/whatsapp/root/queue/{queue_id}/retry`
- `GET /notification-templates`
- `POST /notifications/send`
- `GET /notifications/schedules`
- `POST /notification-schedules`

`POST /notifications/send` usa o canal raiz quando `channel=whatsapp`.

## Provedores

Recomendacao para producao:

1. Meta WhatsApp Cloud API direto: menor dependencia e melhor controle de templates, webhooks, custos e compliance.
2. Twilio: bom para velocidade operacional, suporte e recursos prontos; custo por mensagem tende a ser maior.
3. Zenvia ou outro BSP regional: bom para operacao Brasil, suporte comercial e homologacao assistida.
4. Evolution/Baileys: aceitavel apenas para piloto local/controlado; nao e oficial Meta.
5. Relay HTTP proprio: aceitavel quando houver contrato interno claro, mas precisa webhook, retry, assinatura e observabilidade.

Evite sessao local nao oficial para producao: risco de bloqueio, instabilidade e problema contratual.

## Canal Raiz vs WhatsApp Por Cliente

O canal raiz e melhor para MVP e operacao SaaS porque:

- reduz onboarding;
- simplifica suporte;
- padroniza templates;
- centraliza compliance e logs;
- facilita retry, auditoria e observabilidade;
- evita que cada cliente dependa de configuracao propria.

Riscos:

- volume concentrado no numero oficial;
- limites/rate limits do provider;
- reputacao do numero afeta todos os tenants;
- opt-in e templates precisam ser bem gerenciados;
- queda do canal raiz afeta toda a base.

Mitigacoes:

- filas por tenant;
- rate limit por tenant e tipo;
- dead-letter queue;
- numero raiz por regiao no futuro;
- templates aprovados por categoria;
- webhooks de entrega/leitura;
- fallback por e-mail/sistema.

## Pendencias De Producao

- Configurar provider real e homologar numero.
- Criar templates aprovados para mensagens recorrentes.
- Implementar webhooks de entrega/leitura.
- Rodar worker duravel para agendamentos e retry fora da request HTTP.
- Adicionar rate limit por tenant e prioridade.
- Criar painel de opt-in/opt-out por destinatario.
- Adicionar assinatura de webhooks e mascaramento de PII em logs externos.

Mais detalhes: `docs/WHATSAPP_EVOLUTION.md` e `docs/WHATSAPP_ROOT_CHANNEL.md`.
