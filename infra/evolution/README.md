# Evolution API do Vulcan

Runtime local/piloto do Canal WhatsApp Raiz. Usa Evolution API 2.3.7 com Baileys e, portanto, **nao e API oficial da Meta**.

## Comandos

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/infra/evolution

./scripts/start.sh
./scripts/status.sh
./scripts/logs.sh --follow
./scripts/restart.sh
./scripts/stop.sh
```

O primeiro `start.sh` cria `.env` com API key, webhook token e senhas aleatorias em modo `0600`. Esse arquivo, sessoes e volumes nao entram no Git. O backend Vulcan le a mesma API key ao iniciar por `scripts/start-vulcan.sh`.

## Autostart

```bash
./scripts/install-service.sh
```

O servico systemd depende do Docker; os tres containers tambem usam `restart: unless-stopped` e health checks. PostgreSQL, Redis e a sessao Baileys ficam em volumes persistentes.

Logs:

```bash
journalctl -u vulcan-evolution.service -f
```

## QR Code

Depois de subir Evolution e Vulcan:

1. Abrir `Configuracoes -> WhatsApp`.
2. Informar numero mestre, URL, API key e instancia.
3. Clicar em `Ver QR`.
4. Escanear com o WhatsApp do numero mestre.

## Documentacao Completa

- `docs/WHATSAPP_EVOLUTION.md`
- `docs/WHATSAPP_ROOT_CHANNEL.md`
- `docs/WHATSAPP.md`
- `docs/NOTIFICATIONS.md`
