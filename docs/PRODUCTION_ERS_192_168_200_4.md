# Produção ERS pelo endereço 192.168.200.4

## Estado autoritativo

Data do corte: `2026-07-29`; última atualização: `2026-07-30`

O endereço oficial do Vulcan na rede ERS é:

- aplicação: `http://192.168.200.4:8099`;
- Wallboard Workforce: `http://192.168.200.4:8099/wallboard/workforce`;
- Wallboard Infrastructure: `http://192.168.200.4:8099/wallboard/infra`;
- Agentes: `http://192.168.200.4:8099/agents`;
- downloads: `http://192.168.200.4:8099/downloads/agents/`.

O `SRVERS01` (`192.168.200.4`) continua dedicado a AD DS e DNS. Ele não executa
PostgreSQL, Redis, containers, frontend, backend, worker, collector ou ferramenta de
build do Vulcan. A única rota oficial é o encaminhamento TCP já existente:

```text
192.168.200.4:8099 -> 192.168.200.26:8099
```

O runtime definitivo fica na VM Linux dedicada `VULCAN-PROD01`, IP estático
`192.168.200.26`, VMID `103` no nó Proxmox `PVE02`. A VM possui 2 vCPU, 8 GiB de RAM e
120 GiB de disco, além de 4 GiB de swap com `vm.swappiness=10`. O projeto Compose é
`vulcan-production`; a porta de borda é publicada em `0.0.0.0:8099`, enquanto bancos e
serviços internos não possuem porta publicada no host.

O antigo runtime temporário `192.168.200.160` era o notebook de desenvolvimento. Seus
containers de produção estão parados, mas os volumes e backups foram preservados como
rollback. O acesso oficial não depende mais desse equipamento.

A regra `Vulcan LAN Installer 8099` aceita a porta TCP 8099 no perfil de domínio e o
acesso foi validado pela VPN. Assim, clientes da rede corporativa roteada e da VPN podem
usar o mesmo endereço oficial; a aplicação não foi publicada diretamente na Internet.

## Releases

- plataforma em produção: `0.4.0`;
- agente publicado: `0.3.1`;
- rollback imediato de imagem: release `0.3.6` preservada em
  `/opt/vulcan/releases/vulcan-0.3.6-linux-amd64`;
- commit e build exatos: `/version` e `manifests/release.json`;
- os pacotes possuem `SHA256SUMS` e SBOM CycloneDX.

Release de produção:

```text
arquivo: dist/vulcan-0.4.0-linux-amd64.tar.gz
SHA-256: da50e45b3feb6e7bb354aaac1207ee7a304ab10d6949f7fa8d3e3e9676ecc19d
commit da release: 334b8b56ad74e9fa8c4aac39ff2eced29b392bd6
build: 20260730T140148Z
```

A correção `0.3.1` acrescentou a autorização explícita de HTTP apenas para endereços IP
privados. HTTPS continua sendo o padrão. HTTP público permanece recusado pelo agente.
A correção de plataforma `0.3.3` habilitou a autenticação real do backend no frontend,
sem reativar `admin/admin` ou o modo demo. A `0.3.4` fixou os entitlements finais do
tenant, com Automations limitado a `read_only`. A `0.3.5` corrige o manifesto de backup
para excluir `SHA256SUMS` do próprio cálculo e permitir validação integral.
A `0.3.6` persiste a sessão local apenas na aba do navegador, revalida o token no
backend e registra módulo e subárea na URL. Assim, F5, voltar/avançar e links diretos
preservam Infrastructure, Agents e suas subseções sem retornar ao login.

A `0.4.0` substitui os parâmetros históricos por rotas reais, preservando sessão,
subárea, F5, voltar e avançar. Também entrega três filiais ERS, inventário relacional,
Wallboards Workforce e Infrastructure persistidos, e reconciliação UniFi/Proxmox
somente leitura. As dez políticas de discovery foram provisionadas desativadas, em modo
seguro e sujeitas a aprovação.

Na homologação de produção, Chromium percorreu `/infrastructure/assets`, F5,
`/infrastructure/branches`, voltar, `/agents/installation`,
`/wallboard/workforce` e `/wallboard/infra`; os três cenários passaram. O banco restaurado
registrou 1 tenant, 15 usuários, 13 memberships, 3 filiais, 10 redes, 78 ativos,
42 relacionamentos, 2 perfis de Wallboard, 8 itens de playlist, 22 identidades de agente,
40.614 eventos unificados e 62.184 registros de auditoria. Os contadores de eventos e
auditoria continuam crescendo com a ingestão real.

Na conferência final ao vivo de `2026-07-30T12:26:02-03:00`, os contadores haviam
avançado para 40.630 eventos e 62.657 auditorias; health, readiness, liveness e version
responderam `200` pelo endereço oficial.

## Serviços

| Serviço | Função | Exposição |
| --- | --- | --- |
| `edge` | Nginx de borda | `192.168.200.26:8099` |
| `frontend` | Vulcan Web | apenas rede Docker |
| `backend` | API, realtime e Agent API v2 | apenas rede Docker |
| `infrastructure-worker` | reconciliação read-only UniFi/Proxmox | sem porta publicada |
| `whatsapp-worker` | worker assíncrono | sem porta publicada |
| `db` | PostgreSQL 16 | apenas rede `data` |
| `evolution` | Evolution API | apenas rede Docker |
| `evolution-db` | PostgreSQL 15 | apenas rede `internal` |
| `evolution-redis` | Redis 7.4 | apenas rede `internal` |

Os nove containers retornaram automaticamente após o reboot controlado da VM. Seis
serviços possuem healthcheck e ficaram saudáveis. O worker reconciliou 23 ativos UniFi e
17 ativos Proxmox sem alterar equipamentos. `discovery` permanece no profile `network`,
desabilitado até aprovação explícita. Não há descoberta agressiva nem automação
corretiva ativa.

## Tenant e identidades

Tenant real: `ERS Transportes`, slug `ers-transportes`, UUID
`00000000-0000-0000-0000-000000000301`.

Contas separadas:

- `root@vulcan.local`: root da plataforma;
- `admin.ers@erstransportes.local`: administrador do tenant;
- `wallboard@erstransportes.local`: somente leitura.

As senhas ficam em arquivos protegidos da release operacional, não no Git. A conta do
Wallboard recebeu `403` ao tentar criar token de enrollment e `200` nas leituras.

## Agente piloto

O Workstation Agent `0.3.1` foi instalado como serviço de usuário no host autorizado
`allan-nb`, com perfil `workstation`, política assinada e endpoint:

```text
http://192.168.200.4:8099/api
```

O piloto enviou heartbeat, inventário, saúde, rede e atividade para a Timeline. A fila
SQLite criptografada foi testada apontando apenas o piloto para uma porta fechada:
quatro eventos ficaram pendentes, nenhum tipo de evento foi encontrado em texto claro e
o replay zerou a fila após a reconexão. No reboot da VM da release `0.4.0`, o agente
registrou a indisponibilidade transitória, preservou quatro eventos e confirmou o lote
após o retorno; a fila terminou novamente em zero.

Não houve piloto Server porque nenhum servidor não crítico foi autorizado nesta janela.
Não instalar primeiro no controlador de domínio. A implantação em massa e a GPO continuam
bloqueadas até o piloto Windows MSI e um Server Agent serem homologados.

Para HTTP privado, o MSI exige a propriedade explícita:

```powershell
msiexec.exe /i .\VulcanAgent-Windows-x64.msi /qn /norestart `
  VULCAN_SERVER="http://192.168.200.4:8099/api" `
  ENROLLMENT_TOKEN="TOKEN_TEMPORARIO" `
  AGENT_PROFILE="workstation" `
  ALLOW_INSECURE_PRIVATE_NETWORK=true
```

O token deve ser gerado em `Comando -> Agentes -> Instalação`, expira e não deve ser
gravado em script permanente.

## Backup, restore e rollback

Backups ficam fora do Git. Na VM, o diretório é `/var/backups/vulcan/daily`, protegido
para `root`; o material de restore fica em `/opt/vulcan/restore`. O backup é
AES-256-CBC/PBKDF2 e usa passphrase separada.

O backup pré-corte é
`vulcan-production-20260729T220432Z.tar.gz.enc`, SHA-256
`bb6a88859690c3d292aaadb8da864bb4287cc017d830cc2efbc1221953a5dbb2`.
O primeiro backup gerado já na VM é
`vulcan-production-20260729T222956Z.tar.gz.enc`, SHA-256
`7f449f66448d7942e1a7cedae41491b1d56b4e6c681c743b6384db48840d0706`.
O manifesto interno, dumps, volumes e catálogos `pg_restore` passaram na validação.

Antes da atualização `0.3.6`, foi criado o backup
`vulcan-production-20260730T115536Z.tar.gz.enc`, SHA-256
`3208fc38ec9e7e7416132cba9d2b729771cbd3395a6b710057d0e275a95295fb`.
O arquivo cifrado, o manifesto interno e os catálogos `pg_restore` dos bancos Vulcan e
Evolution foram validados. O restore integral mais recente continua sendo o ensaio
descartável descrito abaixo; nenhum restore destrutivo foi executado sobre produção.

Antes da atualização `0.4.0`, foi criado:

```text
/var/backups/vulcan/pre-deploy/vulcan-production-20260730T140805Z.tar.gz.enc
SHA-256: 8b6e8ad24e62fe99f15794e47ec58c0881fb03a3345e530df2ee3d4b9fc041a5
```

Depois do deploy foi criado e restaurado integralmente em dois PostgreSQL descartáveis:

```text
/var/backups/vulcan/post-deploy/vulcan-production-20260730T151307Z.tar.gz.enc
SHA-256: f43a025f1a1c5d734fed0639871ffce34ded8614af8c23d192de0d6ec56f24cc
```

O ensaio pós-deploy validou os dois catálogos, todos os checksums internos, 1 tenant,
15 usuários, 13 memberships, 3 filiais, 10 redes, 78 ativos, 2 perfis de Wallboard,
22 identidades, 40.614 eventos, 62.184 auditorias e as 37 tabelas públicas da Evolution.
Nenhum restore destrutivo foi executado no banco de produção.

O timer `vulcan-backup.timer` executa diariamente, com retenção local de 14 dias. No
Proxmox, o job `vulcan-prod01-daily` protege a VMID `103` no storage `BACKUPSERS` às
`03:15`, em modo snapshot, com retenção de 7 diários, 4 semanais e 6 mensais.

O snapshot inicial `BACKUPSERS:backup/vm/103/2026-07-29T22:31:40Z` terminou com
`TASK OK`. O backup leu 120 GiB, reutilizou 93% dos blocos e foi listado novamente no
storage depois da conclusão.

O restore final foi executado em PostgreSQL descartável, sem porta publicada, incluindo
os roles RLS. Foram validados 1 tenant, 15 usuários, 27 dispositivos, 22 identidades de
agente e 11 módulos habilitados. Após o corte e o replay do piloto, a produção registrava
39.909 eventos, 39.717 atividades e 58.946 registros de auditoria. A Evolution API possui
37 tabelas. Os containers descartáveis usados no teste de restore foram removidos.

Um novo reboot controlado somente da VM foi executado no fechamento da `0.4.0`; o boot
registrado foi `2026-07-30T12:16:22-03:00`. Docker, os nove containers, o backup timer e
o QEMU Guest Agent voltaram automaticamente. O endereço oficial recuperou health às
`12:17:32-03:00`, o worker sincronizou novamente as integrações e o Workstation Agent
reenviou o lote acumulado. O SRVERS01 não foi reiniciado.

Comandos operacionais:

```bash
ssh vulcanops@192.168.200.26
cd /opt/vulcan/current
sudo ./healthcheck.sh
sudo ./logs.sh backend frontend edge infrastructure-worker
sudo ./restart.sh
VULCAN_BACKUP_ROOT=/caminho/privado \
  sudo ./backup.sh
sudo ./rollback.sh /opt/vulcan/releases/<release-anterior>
```

Uma release anterior só deve ser informada ao `rollback.sh` depois de transferida e
validada. Para retorno com dados, use o backup pré-corte e o procedimento de restore; o
rollback de imagem não reverte o banco destrutivamente.

## Saúde do controlador de domínio

Após o corte:

- `NTDS`, `DNS`, `KDC`, `Netlogon`, `DFSR` e `W32Time`: ativos/automáticos;
- `dcdiag` focado em Advertising, Services, SysVolCheck, NetLogons e DNS: sem saída;
- `SYSVOL` e `NETLOGON`: compartilhados;
- SOA, SRV LDAP, SRV Kerberos e A do SRVERS01: resolvidos pelo DNS local;
- `repadmin /replsummary`: `0/5` falhas de objetos para o destino SRVERS01;
- o SRVERS01 alcançou `192.168.200.26:8099`;
- nenhuma reinicialização, correção automática, GPO ou zona DNS foi alterada.

Na validação posterior ao reboot da VM, `DFSR`, `DNS`, `Kdc`, `Netlogon`, `NTDS` e
`W32Time` permaneceram `Running/Automatic`; `SYSVOL` e `NETLOGON` permaneceram
compartilhados. Os testes focados de `dcdiag` (Advertising, Services, SysVolCheck,
NetLogons e DNS) terminaram com código zero. Não houve evento crítico de Directory
Service ou DNS Server nas duas horas verificadas.

O `dcdiag /q` completo não está limpo por causas externas ao Vulcan: bind negado ao
`SRVERS08` e eventos de confiança referentes a `SRVERS04` e `ERS-SJP-021`.
`repadmin` também registrou erro operacional 110 ao consultar o `SRVERS08`, embora o
resumo de objetos tenha zero falhas. Esses itens precisam de análise separada do time de
AD e não foram reparados por esta entrega.

## Riscos restantes

- o endpoint oficial ainda usa HTTP interno; planejar certificado confiável e HTTPS;
- encaminhamentos antigos `80`, `3001` e `3002` no DC permanecem como legado; não foram
  removidos porque a auditoria de dependências compartilhadas ainda não foi concluída;
- o MSI não foi instalado em Windows real nesta janela;
- não há Server Agent piloto nem implantação GPO aprovada;
- ainda não há piloto Collector, receivers syslog/traps/flows ou SNMP homologado;
- incidentes permanecem vazios porque o correlator determinístico ainda não foi ativado;
- o `dcdiag /q` completo contém pendências de AD não causadas pelo Vulcan.

Prioridade operacional: homologar MSI e Server Agent em hosts Windows não críticos e
configurar TLS interno confiável, mantendo `192.168.200.4:8099` como endereço oficial.
