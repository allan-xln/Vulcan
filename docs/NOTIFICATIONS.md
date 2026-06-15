# Notificacoes

O modulo de Notificacoes transforma sinais operacionais do Vulcan em acao: alerta interno, WhatsApp, e-mail, Windows/agente e estrutura futura de push/web. A regra do produto e clara: nao fingir envio real. Sem credencial, o status aparece como `missing_credentials` ou `mocked`.

## Canais

- Sistema: central interna do painel, sino, Comando, Insights e historico.
- WhatsApp: canal raiz do Vulcan, configurado por ambiente.
- E-mail: SMTP, Gmail/Google, Outlook/Microsoft 365, Resend/SendGrid preparados.
- Windows/agente: canal para mensagens locais no agente instalado.
- Push/web: reservado para Web Push, FCM, SSE ou Supabase Realtime.

## Tipos E Prioridades

Tipos padrao:

- agente offline;
- agente online novamente;
- fila offline alta;
- falha de sincronizacao;
- dispositivo aguardando adocao;
- coleta limitada;
- gargalo operacional;
- ociosidade elevada;
- troca de contexto excessiva;
- queda de produtividade;
- insight critico;
- insight executivo;
- oportunidade de automacao;
- relatorio diario, semanal e mensal;
- falha WhatsApp, e-mail e IA;
- seguranca/LGPD;
- usuario sem equipe;
- usuario sem gestor;
- metrica fora do padrao;
- acao pendente;
- acao vencida.

Prioridades:

- `informativo`;
- `baixo`;
- `medio`;
- `alto`;
- `critico`.

Prioridade afeta visual, ordenacao, canal recomendado, exigencia de acao e `requiresAck` no metadata.

## Preferencias

Preferencias existem por usuario/membership, canal e tipo:

- habilitado/desabilitado;
- janela silenciosa;
- fuso horario;
- frequencia;
- canais permitidos;
- escopo hierarquico.

Operador recebe apenas alertas pessoais. Lider, supervisor, gerente e coordenador recebem sua subarvore. Diretor/admin recebe a visao consolidada do tenant. Root, quando existir, usa escopo global.

## Agendamentos

Agendamentos sao expostos e podem ser criados/pausados/reativados:

- imediato;
- horario;
- diario;
- 2 ou 3 vezes por dia;
- semanal;
- 2 vezes por semana;
- mensal;
- 2 vezes por mes;
- trimestral;
- personalizado.

Campos principais:

- `name`;
- `recurrence`;
- `timezone`;
- `daysOfWeek`;
- `times`;
- `reportType`;
- `recipients`;
- `channels`;
- `enabled`.

No MVP, agendamentos customizados sao persistidos na tabela `notifications` com `notification_type='schedule_config'` e metadata estruturado. Para producao de alto volume, a evolucao recomendada e uma tabela dedicada `notification_schedules` e worker com fila duravel.

## Templates

Templates padrao ficam centralizados no backend e aparecem na tela Notificacoes:

- WhatsApp critico;
- e-mail diario;
- sistema/dispositivo aguardando adocao;
- Windows/agente para coleta limitada.

Variaveis suportadas:

- `{{empresa}}`;
- `{{usuario}}`;
- `{{equipe}}`;
- `{{departamento}}`;
- `{{supervisor}}`;
- `{{periodo}}`;
- `{{metrica}}`;
- `{{valor}}`;
- `{{impacto}}`;
- `{{economia_estimada}}`;
- `{{link_dashboard}}`;
- `{{link_insight}}`;
- `{{link_metricas}}`;
- `{{data}}`.

## Fila, Retry E Status

Status operacionais aceitos pela API/UI:

- `pending`;
- `queued`;
- `sending`;
- `sent`;
- `delivered`;
- `failed`;
- `cancelled`;
- `skipped`;
- `retrying`;
- `ready`;
- `mocked`;
- `missing_credentials`;
- `missing_destination`;
- `unknown_provider`;
- `disabled`;
- `resolved`.

O enum atual do banco suporta uma base menor (`queued`, `sent`, `failed`, `mocked`, `missing_credentials`, `disabled`). Estados detalhados ficam em `metadata.deliveryStatus`, preservando compatibilidade sem esconder o estado real.

Campos importantes:

- `attempts`;
- `maxAttempts`;
- `lastError`;
- `scheduledFor`;
- `sentAt`;
- `deliveredAt`;
- `readAt`;
- `resolvedAt`;
- `actionUrl`;
- `requiresAck`.

## Endpoints

- `GET /notifications`
- `GET /notifications/summary`
- `GET /notifications/{id}`
- `POST /notifications/send`
- `POST /notifications/test`
- `POST /notifications/{id}/retry`
- `POST /notifications/{id}/cancel`
- `POST /notifications/{id}/mark-read`
- `POST /notifications/{id}/resolve`
- `GET /notification-types`
- `GET /notifications/preferences`
- `PUT /notifications/preferences/{preference_id}`
- `GET /notifications/schedules`
- `POST /notification-schedules`
- `PUT /notification-schedules/{id}`
- `DELETE /notification-schedules/{id}`
- `POST /notification-schedules/{id}/pause`
- `POST /notification-schedules/{id}/resume`
- `GET /notification-templates`
- `POST /notification-templates/{id}/preview`
- `POST /notification-templates/{id}/test`
- `GET /integrations/whatsapp/status`
- `POST /integrations/whatsapp/test`
- `GET /integrations/email/status`
- `POST /integrations/email/test`

## WhatsApp

Variaveis:

```env
ROOT_WHATSAPP_ENABLED=true
ROOT_WHATSAPP_PROVIDER=
ROOT_WHATSAPP_NUMBER=5541984166423
ROOT_WHATSAPP_NAME=Vulcan Notifications

WHATSAPP_PROVIDER=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=
```

O numero inicial do canal raiz e `+55 41 98416-6423`. Ele deve ficar centralizado em ambiente/configuracao, nunca espalhado no codigo.

Sem credencial real, o backend registra explicitamente `missing_credentials` ou `mocked`.

## E-mail

Variaveis:

```env
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=
SMTP_SECURE=

RESEND_API_KEY=
SENDGRID_API_KEY=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=

MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_TENANT_ID=
MICROSOFT_REDIRECT_URI=
```

SMTP/OAuth sao usados para envio. IMAP/POP3 sao leitura/consulta futura e nao devem ser vendidos como canal de envio.

## Agente

O fluxo preparado para agente e:

1. backend cria notificacao para usuario/dispositivo;
2. agente consulta no sync;
3. agente mostra mensagem local quando suportado;
4. agente confirma recebimento;
5. backend atualiza entrega/ack.

Endpoints futuros previstos:

- `GET /agent/notifications`;
- `POST /agent/notifications/{id}/ack`;
- `POST /agent/notifications/{id}/dismiss`.

## Integracoes Com O Produto

- Insights: insight critico gera notificacao e registra status WhatsApp/e-mail.
- Comando: mostra apenas criticos, agente offline, falha de canal e gargalos relevantes.
- Metricas: regras podem gerar alertas por ociosidade, troca de contexto, fila offline e queda de produtividade.
- Hierarquia: destinatarios respeitam tenant, membership e subarvore autorizada.

## Seguranca E LGPD

Notificacoes nao devem vazar dados fora da hierarquia. Mensagens para colaborador usam tom construtivo e nao punitivo. Logs nao devem armazenar secrets. Tokens e credenciais devem ser mascarados.

Mensagem central:

`O Vulcan mede fluxo operacional, nao conteudo pessoal.`

## Seed Demo

`corepack pnpm seed:demo` cria:

- preferencias para todos os perfis demo;
- notificacoes internas;
- WhatsApp mock/credencial pendente;
- e-mail pendente/falho;
- Windows/agente mock;
- historico com tentativas e erros legiveis;
- agendamentos diario, tempo real e semanal;
- templates padrao.

## Pendencias Para Producao Total

- Criar tabelas dedicadas para schedules/templates/regras em vez de usar metadata para tudo.
- Integrar worker duravel de fila/retry/dead-letter.
- Ativar provedor real WhatsApp Business API ou provider equivalente.
- Finalizar OAuth real para Gmail/Outlook.
- Implementar delivery receipts/webhooks de WhatsApp/e-mail.
- Implementar consulta/ack de notificacoes pelo agente.
