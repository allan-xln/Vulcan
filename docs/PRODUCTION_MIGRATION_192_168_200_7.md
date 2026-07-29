# Migração de Produção para 192.168.200.7

## Estado atual

Data: `2026-07-29`

Estado: **release validada localmente; implantação remota bloqueada por autenticação**.

O servidor `192.168.200.4` permanece controlador de domínio e DNS. Nenhum componente foi
removido, nenhuma regra foi alterada e nenhuma reinicialização foi executada. O runtime
atual continua no host `192.168.200.160`, alcançado pelos encaminhamentos exclusivos do
Vulcan no servidor 4.

O `192.168.200.7` respondeu em rede e apresentou serviços Windows/AD, mas recusou a
credencial fornecida em WinRM e SMB. Nenhum software foi instalado nele. Antes do deploy é
obrigatório confirmar suas funções e localizar uma VM ou host Linux isolado aprovado.

## Arquitetura da release

| Serviço | Profile | Exposição |
| --- | --- | --- |
| `edge` | `core`, `production` | TCP 80 configurável |
| `frontend` | `core`, `production` | somente rede `application` |
| `backend` | `core`, `production` | somente redes internas |
| `whatsapp-worker` | `core`, `production` | sem porta publicada |
| `db` | `core`, `production` | somente rede `data` |
| `evolution` | `core`, `production` | somente redes internas |
| `evolution-db` | `core`, `production` | somente rede `internal` |
| `evolution-redis` | `core`, `production` | somente rede `internal` |
| `discovery` | `network` | sem porta; desabilitado por padrão |

Redes: `edge`, `application`, `telemetry`, `data` e `internal`. As redes `data` e
`internal` têm acesso externo desabilitado. Os volumes persistentes têm nomes fixos para
backup e restore controlados.

O proxy entrega:

- `/` para o frontend;
- `/api/*` para a API;
- `/api/realtime/*` com buffering desabilitado para SSE;
- `/healthz`, `/readyz`, `/livez` e `/version`;
- `/wallboard`;
- `/downloads/agents/*`.

## Variáveis e secrets

O arquivo `.env.production` contém somente configuração operacional: URL, bind, versão,
commit, build, e-mails funcionais e limites. Os valores sensíveis ficam em `secrets/`,
fora do Git e com ACL mínima para os UIDs dos containers.

Secrets obrigatórios:

- senha PostgreSQL do Vulcan;
- chave de assinatura da autenticação;
- token legado de enrollment;
- senhas iniciais root/admin/Wallboard;
- senha do PostgreSQL Evolution;
- API key e webhook token Evolution;
- passphrase separada para backups.

Nunca copie valores desses arquivos para documentação, logs ou linha de comando.

## Build e conteúdo

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
PATH="$HOME/.local/bin:$PATH" ./scripts/build-production-release.sh 0.3.0
sha256sum -c dist/vulcan-0.3.0-linux-amd64.tar.gz.sha256
```

A release contém imagens OCI comprimidas, Compose, Nginx, migrations, scripts operacionais,
agentes publicados, manifest de imagens, SBOM CycloneDX e `SHA256SUMS`. Não contém `.git`,
testes, árvore completa de fontes, caches, secrets ou dumps.

## Primeiro deploy no ambiente aprovado

```bash
tar -xzf vulcan-0.3.0-linux-amd64.tar.gz
cd vulcan-0.3.0-linux-amd64
cp .env.production.example .env.production
chmod 0600 .env.production
vi .env.production
./deploy.sh --restore-dir /backup/validado
./healthcheck.sh
```

O restore inicial recusa destino que já possua tenants. Ele restaura os dois bancos,
reaplica a senha local do PostgreSQL, executa migrations incrementais e provisiona os
acessos sem substituir senhas existentes em reexecuções.

## Validação executada na stack isolada

URL local de teste: `http://127.0.0.1:18080`

- seis endpoints/páginas de health responderam;
- containers de banco, API, frontend, proxy e Evolution ficaram saudáveis;
- login real pelo banco passou para root, tenant admin e Wallboard;
- o Wallboard acessou apenas operações de leitura;
- Chromium validou dados reais e atualização da página;
- logs não apresentaram traceback, panic, fatal ou HTTP 500;
- restore preservou 1 tenant, 12 usuários originais, 11 memberships originais, 27
  dispositivos, 21 identidades e 39.349 eventos;
- o provisionamento adicionou três usuários operacionais e duas memberships;
- Evolution restaurou 37 tabelas e uma instância.

Essa validação não substitui o E2E obrigatório no servidor 7.

## Gate para corte

Somente prosseguir depois de todos os itens abaixo:

1. acesso administrativo válido e inventário somente leitura do servidor 7;
2. confirmação do ambiente Linux isolado e capacidade;
3. release e checksums validados no destino;
4. restore e migrations concluídos;
5. contagens antes/depois comparadas;
6. login root, ERS e Wallboard;
7. Workforce, Infrastructure, Timeline, Agents e Wallboard;
8. agente real online exclusivamente no servidor 7;
9. backup e restore do destino ensaiados;
10. acesso a partir de outra estação e da TV;
11. URL/DNS final e rollback aprovados.

Até esse gate passar, é proibido remover portproxy, firewall ou pacote do servidor 4.

## Comandos operacionais

Health:

```bash
./healthcheck.sh
docker compose --env-file .env.production -f compose.yml --profile core ps
```

Logs:

```bash
./logs.sh
./logs.sh backend edge
```

Reinício seguro da camada de aplicação:

```bash
./restart.sh
```

Backup:

```bash
BACKUP_ENCRYPTION_PASSPHRASE_FILE=/caminho/privado/passphrase ./backup.sh
```

Rollback de imagens, sem rollback destrutivo do banco:

```bash
./rollback.sh /opt/vulcan/releases/release-anterior
```

## Itens pendentes por bloqueio externo

- inventário autorizado e deploy no servidor 7;
- URL principal e Wallboard testados na rede;
- validação de Workstation, Server e Collector no destino;
- corte dos agentes e do proxy;
- remoção exclusiva do Vulcan no servidor 4;
- `dcdiag`, `repadmin` e DNS depois do corte;
- relatório final de remoção.

Os detalhes do servidor antigo e o gate de remoção estão em
`VULCAN_OLD_SERVER_INVENTORY.md` e `VULCAN_SERVER_4_REMOVAL_REPORT.md`.
