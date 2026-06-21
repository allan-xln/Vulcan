# Docker Runtime

Este runtime sobe a pilha local completa do Vulcan em Docker:

- PostgreSQL local do Vulcan;
- Evolution API/Baileys;
- PostgreSQL da Evolution;
- Redis da Evolution;
- backend API;
- worker da fila WhatsApp;
- frontend Next.js.

## Primeiro Uso

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan

./scripts/docker-up.sh
```

O script:

1. cria `docker/.env` com secrets locais em modo `0600`;
2. para a pilha local não Docker gerenciada por `scripts/start-vulcan.sh`;
3. sobe banco e Evolution;
4. aplica migrations;
5. roda o seed demo;
6. sobe backend, worker e frontend;
7. mostra status.

URLs:

- Frontend: `http://localhost:3002`
- Backend: `http://localhost:3001`
- Evolution: `http://localhost:8080`
- Postgres Docker do Vulcan: `localhost:55432`

Login:

```text
teste / teste
```

## Status, Logs E Parada

```bash
./scripts/docker-status.sh
./scripts/docker-logs.sh
./scripts/docker-logs.sh -f
./scripts/docker-down.sh
```

Parar e remover volumes, incluindo banco e sessão WhatsApp:

```bash
./scripts/docker-down.sh -v
```

## Conectar O Celular No WhatsApp Mestre

Use o número do WhatsApp que será o emissor do Vulcan. Informe em E.164, só dígitos:

```bash
./scripts/docker-whatsapp-qr.sh 55DDDNUMERO
```

Exemplo de formato:

```bash
./scripts/docker-whatsapp-qr.sh 5541999999999
```

O script habilita o Canal WhatsApp Raiz com provider Evolution, pede QR para a Evolution e salva o QR em:

```text
.runtime/evolution-qr.png
```

Abra o QR e escaneie no celular:

```bash
xdg-open .runtime/evolution-qr.png
```

Também é possível pela interface:

1. abra `http://localhost:3002`;
2. entre com `teste / teste`;
3. vá em `Configurações -> WhatsApp`;
4. confirme `Número mestre do Vulcan`;
5. clique em `Ver QR`;
6. escaneie pelo WhatsApp do celular.

Depois de escanear:

```bash
./scripts/docker-status.sh
```

O status esperado é `unofficial_connected`.

## Importante

Evolution/Baileys não é API oficial da Meta. Use para piloto local/controlado. Produção oficial deve migrar para Meta WhatsApp Cloud API ou BSP homologado.

Não conecte múltiplas sessões do mesmo número para tentar redundância. A resiliência correta é Docker restart, healthcheck, fila, retry, logs, dead letter e fallback.

## Problemas Com Docker

Se aparecer:

```text
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

rode com um usuário no grupo `docker`, ajuste Docker rootless, ou execute com `sudo`:

```bash
sudo ./scripts/docker-up.sh
```

Se usar `sudo`, o arquivo `docker/.env` será criado como root. Mantenha esse arquivo fora do Git.
