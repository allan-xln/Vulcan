# Configuracoes

A tela Configuracoes e a central de controle do Vulcan. Ela foi desenhada para nao exibir campo inutil: cada campo editavel vem do backend, salva em `tenant_settings.settings`, valida entrada e gera auditoria. Campos sensiveis aparecem apenas como status.

## Arquitetura

Escopos:

- `system`: configuracao global ou derivada de ambiente, geralmente somente leitura no painel.
- `tenant`: configuracao da empresa/cliente.
- `team`: reservado para metas e preferencias por equipe.
- `user`: preferencias do usuario.
- `agent`: politica de agente/dispositivo.

Persistencia:

- tabela: `public.tenant_settings`;
- coluna JSON: `settings`;
- campos diretos usados: `default_locale`, `default_timezone`, `retention_days`;
- auditoria: `public.audit_logs` com acao `settings.updated`.

Secrets:

- nao sao retornados para o frontend;
- nao sao gravados no JSON de settings;
- aparecem como `configurado` ou `requer credencial`;
- devem ser definidos por `.env` ou cofre seguro por tenant.

## Endpoints

- `GET /settings`
- `GET /settings/summary`
- `GET /settings/{section}`
- `PUT /settings/{section}`
- `POST /settings/{section}/test`
- `POST /settings/{section}/reset`
- `GET /audit-logs`

## Secoes

### Empresa

Campos editaveis:

- nome exibido;
- razao social;
- slug;
- timezone;
- idioma;
- moeda;
- responsavel tecnico.

Impacto:

- dashboards;
- notificacoes;
- relatorios;
- timezone de metricas.

### Agentes E Dispositivos

Campos editaveis:

- heartbeat;
- intervalo de sync;
- tamanho de lote;
- timeout;
- limite de fila;
- exigir adocao;
- permitir adocao seca.

Impacto:

- comportamento esperado do agente;
- alertas de fila;
- fluxo de adocao.

### Politicas De Coleta

Campos editaveis:

- app ativo;
- titulo da janela;
- tempo ocioso;
- troca de contexto;
- modo privacidade;
- retencao.

Campos bloqueados por seguranca:

- URL do navegador;
- screenshots.

O backend rejeita ativacao de screenshots continuos e URL por padrao, porque isso exige politica especifica fora do MVP.

### Metricas

Campos editaveis:

- meta de foco;
- limite de ociosidade;
- troca de contexto por hora;
- valor/hora;
- pesos do indice de saude operacional.

Validacao:

- os pesos precisam somar 100%.

### Insights E IA

Campos editaveis:

- modo;
- provider operacional;
- provider executivo;
- timeout;
- limite mensal.

Campos sensiveis:

- OpenAI API key;
- Llama/OpenRouter/Groq key.

Secrets ficam fora do frontend.

### Notificacoes

Campos editaveis:

- notificacoes ativas;
- criticos em tempo real;
- resumo diario;
- resumo semanal;
- janela silenciosa;
- maximo de tentativas.

Integra com `docs/NOTIFICATIONS.md`.

### WhatsApp

Editavel:

- destinatarios padrao;
- modo mock explicito.

Somente leitura:

- canal raiz;
- numero raiz;
- provider;
- token/status.

Env:

```env
ROOT_WHATSAPP_ENABLED=
ROOT_WHATSAPP_PROVIDER=
ROOT_WHATSAPP_NUMBER=5541984166423
ROOT_WHATSAPP_NAME=Vulcan Notifications
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
```

### E-mail

Editavel:

- provider;
- nome do remetente;
- leitura IMAP/POP3 futura.

Somente leitura/secret:

- status SMTP;
- senha SMTP.

SMTP/OAuth sao envio. IMAP/POP3 sao leitura/consulta.

### Seguranca

Somente leitura:

- auth provider;
- fallback local;
- RLS;
- CORS;
- auditoria.

Editavel:

- expiracao de sessao planejada.

### LGPD E Privacidade

Mensagem central:

`O Vulcan mede fluxo operacional, nao conteudo pessoal.`

Editavel:

- exigir consentimento;
- permitir pausa;
- exportacao de dados;
- anonimizar apos X dias.

### Aparencia

Editavel:

- tema;
- intensidade de glow;
- densidade;
- movimento reduzido.

## Permissoes

- admin/diretor root do tenant: edita configuracoes.
- gestor/operador sem escopo de tenant: leitura ou bloqueio de escrita.
- operador demo `operador1`: tentativa de `PUT /settings/company` retorna `400` com `sem permissao para alterar configuracoes`.

## Testes

Com backend rodando:

```bash
TOKEN=dev-vulcan-admin-token
TENANT=00000000-0000-0000-0000-000000000301

curl -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: $TENANT" http://localhost:3001/settings
curl -X POST -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: $TENANT" http://localhost:3001/settings/metrics/test
curl -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -H "X-Tenant-Id: $TENANT" \
  -d '{"values":{"displayName":"Vulcan Demo","slug":"vulcan-demo","timezone":"America/Sao_Paulo","language":"pt-BR"}}' \
  http://localhost:3001/settings/company
```

## Pendencias Para Producao Total

- Cofre por tenant para secrets.
- Tabelas dedicadas para `system_settings`, `team_settings` e `user_settings`.
- UI especifica para logs filtrados por secao.
- Rotacao automatica de tokens.
- MFA e politica de senha avancada.
