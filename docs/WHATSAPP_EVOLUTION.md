# WhatsApp Evolution/Baileys

Este documento descreve a infra local/piloto do WhatsApp do Vulcan usando Evolution API com Baileys.

Evolution/Baileys nao e API oficial da Meta. O Vulcan deve exibir isso no produto e nunca vender este modo como estabilidade equivalente a WhatsApp Cloud API.

## Arquitetura

```text
Vulcan
-> Notification Orchestrator
-> WhatsApp Provider Interface
-> MockWhatsAppProvider
-> EvolutionWhatsAppProvider
-> MetaCloudWhatsAppProvider futuro
-> Email/In-app fallback
```

A Evolution e apenas transporte. O Vulcan continua responsavel por tenant, hierarquia, permissoes, templates, destinatarios, preferencias, fila, retry, logs, auditoria e agendamentos.

## Infra

Arquivos principais:

- `infra/evolution/docker-compose.yml`
- `infra/evolution/.env.example`
- `infra/evolution/scripts/start.sh`
- `infra/evolution/scripts/stop.sh`
- `infra/evolution/scripts/status.sh`
- `infra/evolution/scripts/logs.sh`
- `infra/evolution/scripts/restart.sh`
- `infra/evolution/scripts/install-service.sh`
- `infra/evolution/systemd/vulcan-evolution.service`

O compose sobe:

- Evolution API `evoapicloud/evolution-api:v2.3.7`;
- PostgreSQL persistente da Evolution;
- Redis persistente;
- volumes para banco/cache/sessao;
- health checks;
- `restart: unless-stopped`;
- no runtime Docker completo, Evolution fica interna na rede do Compose e nao publica porta para usuario final;
- no runtime standalone/owner, a porta local pode ser exposta em `127.0.0.1:${EVOLUTION_PORT}` para manutencao controlada.

## Subir Local

Runtime Docker completo recomendado:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan

./scripts/docker-up.sh
./scripts/docker-whatsapp-qr.sh 55DDDNUMERO
```

O comando sobe Vulcan, backend, frontend, worker, banco, Redis e Evolution. Detalhes: `docs/DOCKER.md`.

Runtime Evolution isolado:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/infra/evolution

./scripts/start.sh
./scripts/status.sh
./scripts/logs.sh
```

O primeiro start cria `infra/evolution/.env` com secrets aleatorios em `0600`. Esse arquivo nao entra no Git.

## Autostart

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
./scripts/install-evolution-autostart.sh
```

O service instalado:

- depende de Docker;
- sobe o docker compose;
- reinicia em falha;
- deixa logs no journal:

```bash
journalctl -u vulcan-evolution.service -f
```

## Configuracao Do Vulcan

Variaveis relevantes:

```env
ROOT_WHATSAPP_ENABLED=true
ROOT_WHATSAPP_PROVIDER=evolution
ROOT_WHATSAPP_NUMBER=
ROOT_WHATSAPP_NAME=Vulcan Notifications
ROOT_WHATSAPP_MOCK_MODE=false

EVOLUTION_ENABLED=true
EVOLUTION_BASE_URL=http://evolution:8080
EVOLUTION_API_KEY=
EVOLUTION_INSTANCE_NAME=vulcan-root
EVOLUTION_WEBHOOK_URL=http://backend:3001/integrations/whatsapp/evolution/webhook
EVOLUTION_WEBHOOK_TOKEN=
EVOLUTION_REQUEST_ORIGIN=http://evolution:8080
EVOLUTION_REQUEST_TIMEOUT_SECONDS=30
EVOLUTION_MAX_RETRIES=3
EVOLUTION_RETRY_BACKOFF_SECONDS=5

WHATSAPP_PROVIDER=evolution
WHATSAPP_DEFAULT_COUNTRY=BR
WHATSAPP_REQUIRE_OPT_IN=true
WHATSAPP_ENABLE_UNOFFICIAL_PROVIDER=true
WHATSAPP_EMAIL_FALLBACK_ENABLED=true
WHATSAPP_IN_APP_FALLBACK_ENABLED=true
```

Tambem e possivel salvar a configuracao pela tela `Configuracoes -> WhatsApp`, mas somente com usuario owner. Secrets ficam mascarados e sao gravados no runtime store local `.runtime/integration-secrets.json`, que nao entra no Git. Usuarios de tenant nao veem URL, API key, QR, fila tecnica ou logs tecnicos.

## Status

Status do provider:

- `disabled`: canal desligado.
- `mock`: mock explicito, sem envio real.
- `missing_credentials`: falta URL, API key, numero mestre ou token.
- `unofficial_disconnected`: Evolution acessivel, instancia desconectada.
- `unofficial_qr_required`: instancia precisa de QR.
- `unofficial_connected`: instancia Baileys conectada.
- `unofficial_failed`: Evolution indisponivel ou falhou.
- `unofficial_rate_limited`: provider limitou temporariamente.
- `official_ready_future`: adapter oficial futuro preparado.

Status de fila:

- `pending`
- `queued`
- `sending`
- `sent`
- `delivered`
- `failed`
- `retrying`
- `skipped`
- `cancelled`
- `provider_unavailable`
- `qr_required`
- `rate_limited`

## QR Code

1. Suba o runtime Docker completo com `./scripts/docker-up.sh`.
2. Gere QR pelo owner: `./scripts/docker-whatsapp-qr.sh 55DDDNUMERO`.
3. Abra `.runtime/evolution-qr.png`.
4. Escaneie com o WhatsApp do numero mestre.
5. Confirme status `unofficial_connected` em `./scripts/docker-status.sh`.

Alternativa UI owner: entrar como `admin/admin`, abrir `Configuracoes -> WhatsApp`, clicar em `Ver QR` e escanear. Login de tenant nao mostra QR.

## Redundancia Realista

Nao conecte quatro sessoes do mesmo numero. Isso aumenta risco de instabilidade e bloqueio.

Camadas usadas:

- Docker `restart: unless-stopped`;
- systemd `Restart=on-failure`;
- health check no container;
- health check do provider no Vulcan;
- fila duravel no Vulcan;
- retry com backoff;
- dead letter por `dead_letter_at`;
- logs por tentativa;
- webhook protegido por token;
- fallback preparado por e-mail e in-app;
- provider oficial Meta Cloud API preparado para migracao futura.

## Endpoints

- `GET /integrations/whatsapp/evolution/status`
- `PUT /integrations/whatsapp/evolution/config`
- `POST /integrations/whatsapp/evolution/test`
- `GET /integrations/whatsapp/evolution/qr`
- `POST /integrations/whatsapp/evolution/reconnect`
- `POST /integrations/whatsapp/evolution/send-test`
- `POST /integrations/whatsapp/evolution/webhook`
- `GET /integrations/whatsapp/root/queue`
- `GET /integrations/whatsapp/root/logs`
- `POST /integrations/whatsapp/root/process-queue`
- `POST /integrations/whatsapp/root/queue/{queue_id}/retry`

O webhook exige `X-Vulcan-Webhook-Token`.

Os endpoints Evolution e as operacoes manuais de fila/log/retry exigem escopo owner/root. O cliente usa apenas status comercial, destinatarios, preferencias, notificacoes e historico normal do tenant.

## Producao Oficial

Para producao enterprise, a recomendacao continua sendo Meta WhatsApp Cloud API direto ou BSP homologado. Evolution/Baileys serve para piloto local/controlado quando o risco operacional e aceito.

Antes de producao oficial:

- homologar numero e templates na Meta;
- trocar provider para Cloud API;
- ativar webhooks de entrega/leitura;
- aplicar rate limit por tenant;
- criar opt-out visivel;
- ligar observabilidade externa;
- executar worker duravel fora da request HTTP.
