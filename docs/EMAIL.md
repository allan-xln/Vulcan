# E-mail

E-mail no Vulcan serve para teste de canal, alertas importantes, relatorios agendados e resumos executivos.

## Envio

SMTP/OAuth sao canais de envio.

```env
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=
SMTP_SECURE=

RESEND_API_KEY=
SENDGRID_API_KEY=
```

Gmail/Google:

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
```

Outlook/Microsoft 365:

```env
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_TENANT_ID=
MICROSOFT_REDIRECT_URI=
```

## Leitura

IMAP e POP3 sao leitura/consulta futura. Eles nao devem ser tratados como provider principal de envio.

## Status

- `mocked`: modo simulado explicito;
- `missing_credentials`: credenciais ausentes;
- `queued`: aguardando envio;
- `sent`: entregue ao provider;
- `failed`: erro real do provider ou configuracao.

## Templates

Templates de e-mail devem incluir:

- assunto claro;
- resumo executivo;
- principais gargalos;
- impacto financeiro;
- acoes recomendadas;
- link para dashboard/insight/metricas.

## Teste

1. Configure SMTP ou deixe sem credenciais para validar `missing_credentials`.
2. Rode `corepack pnpm dev`.
3. Abra Notificacoes.
4. Clique em `Testar e-mail`.
5. Confira Historico, tentativas e erro legivel.

## Pendencias Para Producao Total

- OAuth completo Google/Microsoft com consent app.
- Bounce handling e delivery receipts.
- Anexos PDF/CSV para relatorios.
- Cofre seguro por tenant para secrets de provider.
