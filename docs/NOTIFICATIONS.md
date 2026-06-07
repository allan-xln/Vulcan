# Notificações

O Vulcan possui uma central de notificações para transformar sinais operacionais em ações rápidas. O foco é inteligência operacional: gargalos, agentes offline, oportunidades de automação, resumos executivos e alertas de processo.

## Canais

- Sistema: registros dentro do painel do Vulcan.
- Windows/agente: preparado para envio local pelo agente instalado na máquina.
- WhatsApp: canal raiz oficial do Vulcan e futuras conexões por tenant.
- E-mail: SMTP, Gmail, Outlook/Microsoft 365 e provedores futuros.
- Push/web: preparado para FCM/VAPID em etapa futura.

## Canal WhatsApp Raiz

O canal raiz é o canal oficial da plataforma. Ele permite que o próprio Vulcan envie alertas e relatórios para usuários cadastrados nos tenants.

Variáveis:

```env
ROOT_WHATSAPP_ENABLED=true
ROOT_WHATSAPP_PROVIDER=lanchat
ROOT_WHATSAPP_NUMBER=5541984166423
ROOT_WHATSAPP_NAME=Notificações Vulcan
```

O número oficial inicial é `+55 41 98416-6423`, centralizado em `ROOT_WHATSAPP_NUMBER`. Ele não deve ser espalhado pelo código.

## Inspiração No LanChat

O LanChat foi usado apenas como referência arquitetural. Nenhum arquivo do LanChat foi alterado, nenhum banco foi compartilhado e o Vulcan não importa código vivo do LanChat.

Ideias reaproveitadas conceitualmente:

- sessão em memória com estado de conexão;
- status conectado/desconectado;
- suporte a QR Code quando o provedor exigir sessão local;
- reconexão e teste de envio;
- logs de sessão;
- separação entre conexão, provider, webhook e serviço de notificação.

Reimplementação no Vulcan:

- `backend/api/app/whatsapp.py`
- `WhatsAppConnection`
- `WhatsAppProvider`
- `WhatsAppSession`
- `WhatsAppWebhook`
- `WhatsAppNotificationService`
- `SystemWhatsAppChannel`

## E-mail

O módulo de e-mail fica em `backend/api/app/email_channels.py`.

Providers preparados:

- `SmtpProvider`: prioridade para envio.
- `GmailProvider`: OAuth preparado para envio/leitura futura.
- `OutlookProvider`: OAuth Microsoft 365 preparado para envio/leitura futura.
- `ImapProvider`: leitura/consulta, não envio.
- `Pop3Provider`: leitura/consulta, não envio.
- `EmailNotificationService`: camada de orquestração.

SMTP usa:

```env
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
EMAIL_FROM=
EMAIL_DELIVERY_MODE=mock
```

Use `EMAIL_DELIVERY_MODE=live` apenas quando quiser testar conexão real com SMTP. Em `mock`, o Vulcan valida configuração sem disparar e-mails reais.

Gmail usa:

```env
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REDIRECT_URI=
GMAIL_REFRESH_TOKEN=
```

Outlook/Microsoft 365 usa:

```env
OUTLOOK_TENANT_ID=
OUTLOOK_CLIENT_ID=
OUTLOOK_CLIENT_SECRET=
OUTLOOK_REDIRECT_URI=
OUTLOOK_REFRESH_TOKEN=
```

IMAP/POP3 usam variáveis próprias e são documentados como leitura/consulta, não como envio.

## Tipos De Notificação

- métricas em tempo real;
- alertas operacionais;
- gargalos detectados;
- oportunidades de automação;
- queda de produtividade;
- anomalias operacionais;
- insight executivo;
- resumo diário;
- resumo semanal;
- falha de agente;
- agente offline;
- agente voltou online.

Cada notificação deve possuir tenant, canal, destinatário, horário, usuário relacionado quando houver, mensagem, tentativas e erro em caso de falha.

## Agendamento

O endpoint `GET /notifications/schedules` expõe modelos prontos para:

- imediatamente;
- a cada hora;
- a cada 2, 4 ou 6 horas;
- diário;
- 2 ou 3 vezes por dia;
- semanal;
- 2 vezes por semana;
- mensal;
- 2 vezes por mês;
- trimestral;
- personalizado.

O MVP já entrega a estrutura base para dias da semana, horários, fuso horário, destinatários, canais e tipo de relatório. Persistência visual desses agendamentos no banco é o próximo passo.

## Relatórios Automáticos

O endpoint `GET /reports/templates` expõe:

- Resumo Operacional Diário;
- Resumo Executivo Semanal;
- Relatório Mensal;
- Alertas em Tempo Real.

Fluxo previsto:

```text
activity_events -> operational_metrics -> Llama -> ai_insights -> GPT quando necessário -> notifications -> WhatsApp/e-mail/Windows/sistema
```

## Endpoints

- `GET /notifications`
- `POST /notifications/test`
- `POST /notifications/send`
- `GET /notifications/preferences`
- `PUT /notifications/preferences/{preference_id}`
- `GET /notifications/schedules`
- `GET /reports/templates`
- `GET /integrations/whatsapp/status`
- `POST /integrations/whatsapp/test`
- `GET /integrations/email/status`
- `POST /integrations/email/test`
- `GET /integrations/status`

## Pendências Reais

- Persistir configurações de WhatsApp/e-mail por tenant em cofre seguro.
- Ativar provedor real do WhatsApp Business API ou sessão local equivalente.
- Implementar OAuth completo para Gmail e Outlook.
- Persistir agendamentos customizados no banco.
- Ligar o motor de relatórios aos jobs periódicos.
- Definir templates aprovados do WhatsApp quando usar a API oficial.
