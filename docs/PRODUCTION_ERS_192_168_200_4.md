# Produção ERS pelo endereço 192.168.200.4

## Estado autoritativo

Data do corte: `2026-07-29`

O endereço oficial do Vulcan na rede ERS é:

- aplicação: `http://192.168.200.4:8099`;
- Wallboard: `http://192.168.200.4:8099/wallboard`;
- Agentes: `http://192.168.200.4:8099/?view=agents`;
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

- plataforma em produção: `0.3.5`;
- agente publicado: `0.3.1`;
- rollback imediato: restore do backup pré-corte na VM; o runtime temporário anterior foi
  preservado desligado como contingência adicional;
- commit e build exatos: `/version` e `manifests/release.json`;
- os pacotes possuem `SHA256SUMS` e SBOM CycloneDX.

Release de produção:

```text
arquivo: dist/vulcan-0.3.5-linux-amd64.tar.gz
SHA-256: fad45b7f7929dbe49be9dede3e5df34865231462eaf66f5abde35ae0748d860f
commit: 466e9bab376211bf74d5194af31c269b757b7425
build: 20260729T184432Z
```

A correção `0.3.1` acrescentou a autorização explícita de HTTP apenas para endereços IP
privados. HTTPS continua sendo o padrão. HTTP público permanece recusado pelo agente.
A correção de plataforma `0.3.3` habilitou a autenticação real do backend no frontend,
sem reativar `admin/admin` ou o modo demo. A `0.3.4` fixou os entitlements finais do
tenant, com Automations limitado a `read_only`. A `0.3.5` corrige o manifesto de backup
para excluir `SHA256SUMS` do próprio cálculo e permitir validação integral.

## Serviços

| Serviço | Função | Exposição |
| --- | --- | --- |
| `edge` | Nginx de borda | `192.168.200.26:8099` |
| `frontend` | Vulcan Web | apenas rede Docker |
| `backend` | API, realtime e Agent API v2 | apenas rede Docker |
| `whatsapp-worker` | worker assíncrono | sem porta publicada |
| `db` | PostgreSQL 16 | apenas rede `data` |
| `evolution` | Evolution API | apenas rede Docker |
| `evolution-db` | PostgreSQL 15 | apenas rede `internal` |
| `evolution-redis` | Redis 7.4 | apenas rede `internal` |

`discovery` permanece no profile `network`, desabilitado até existirem redes permitidas e
aprovação explícita. Não há descoberta agressiva nem automação corretiva ativa.

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
o replay zerou a fila após a reconexão.

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

Um reboot controlado somente da VM foi executado às `20:13:47 -03`. Docker, os oito
containers, o backup timer e o QEMU Guest Agent voltaram automaticamente. O endereço
oficial respondeu novamente, os endpoints de health/readiness passaram, o Workstation
Agent reenviou os três eventos acumulados e zerou a fila. Chromium validou Agentes e
Wallboard no IP oficial com `2/2` testes aprovados.

Comandos operacionais:

```bash
ssh vulcanops@192.168.200.26
cd /opt/vulcan/current
sudo ./healthcheck.sh
sudo ./logs.sh backend frontend edge
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

O `dcdiag /q` completo não está limpo por causas externas ao Vulcan: bind negado ao
`SRVERS08` e eventos de confiança referentes a `SRVERS04` e `ERS-SJP-021`.
`repadmin` também registrou erro operacional 110 ao consultar o `SRVERS08`, embora o
resumo de objetos tenha zero falhas. Esses itens precisam de análise separada do time de
AD e não foram reparados por esta entrega.

## Riscos restantes

- o endpoint oficial ainda usa HTTP interno; planejar certificado confiável e HTTPS;
- encaminhamentos antigos `80`, `3001` e `3002` no DC permanecem como legado inativo;
- o MSI não foi instalado em Windows real nesta janela;
- não há Server Agent piloto nem implantação GPO aprovada;
- o `dcdiag /q` completo contém pendências de AD não causadas pelo Vulcan.

Prioridade operacional: homologar MSI e Server Agent em hosts Windows não críticos e
configurar TLS interno confiável, mantendo `192.168.200.4:8099` como endereço oficial.
