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
192.168.200.4:8099 -> 192.168.200.160:8099
```

O runtime fica no host Linux isolado `192.168.200.160`, no projeto Compose
`vulcan-production`. A porta de borda é publicada em `0.0.0.0:8099`; bancos e serviços
internos não possuem porta publicada no host.

## Releases

- plataforma em produção: `0.3.3`;
- agente publicado: `0.3.1`;
- rollback de imagens: releases `0.3.2`, `0.3.1` e base `0.3.0`;
- commit e build exatos: `/version` e `manifests/release.json`;
- os pacotes possuem `SHA256SUMS` e SBOM CycloneDX.

A correção `0.3.1` acrescentou a autorização explícita de HTTP apenas para endereços IP
privados. HTTPS continua sendo o padrão. HTTP público permanece recusado pelo agente.
A correção de plataforma `0.3.3` habilitou a autenticação real do backend no frontend,
sem reativar `admin/admin` ou o modo demo.

## Serviços

| Serviço | Função | Exposição |
| --- | --- | --- |
| `edge` | Nginx de borda | `192.168.200.160:8099` |
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

Backups ficam fora do Git, sob
`/home/allan/.local/share/vulcan-cutover-20260729/`, com modo `0700`; arquivos e
checksums usam `0600`. O backup é AES-256-CBC/PBKDF2 e usa passphrase separada.

O restore foi executado em PostgreSQL descartável, sem porta publicada, incluindo os
roles RLS. Foram validados 1 tenant, 15 usuários, 13 memberships, 27 dispositivos,
22 identidades de agente, eventos/timeline/auditoria e 37 tabelas da Evolution API.

Comandos operacionais:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
dist/vulcan-0.3.3-linux-amd64/healthcheck.sh
dist/vulcan-0.3.3-linux-amd64/logs.sh backend frontend edge
dist/vulcan-0.3.3-linux-amd64/restart.sh
VULCAN_BACKUP_ROOT=/caminho/privado \
  dist/vulcan-0.3.3-linux-amd64/backup.sh
dist/vulcan-0.3.3-linux-amd64/rollback.sh \
  dist/vulcan-0.3.2-linux-amd64
```

O rollback troca apenas imagens e não reverte o banco destrutivamente.

## Saúde do controlador de domínio

Após o corte:

- `NTDS`, `DNS`, `KDC`, `Netlogon`, `DFSR` e `W32Time`: ativos/automáticos;
- `dcdiag` focado em Advertising, Services, SysVolCheck, NetLogons e DNS: sem saída;
- `SYSVOL` e `NETLOGON`: compartilhados;
- SOA, SRV LDAP, SRV Kerberos e A do SRVERS01: resolvidos pelo DNS local;
- `repadmin /replsummary`: `0/5` falhas de objetos para o destino SRVERS01;
- o SRVERS01 alcançou `192.168.200.160:8099`;
- nenhuma reinicialização, correção automática, GPO ou zona DNS foi alterada.

O `dcdiag /q` completo não está limpo por causas externas ao Vulcan: bind negado ao
`SRVERS08` e eventos de confiança referentes a `SRVERS04` e `ERS-SJP-021`.
`repadmin` também registrou erro operacional 110 ao consultar o `SRVERS08`, embora o
resumo de objetos tenha zero falhas. Esses itens precisam de análise separada do time de
AD e não foram reparados por esta entrega.

## Riscos restantes

- o runtime `.160` é um notebook Zorin em Wi-Fi e não é o host ideal de produção;
- o disco raiz estava acima de 97% de uso durante o corte;
- o endpoint oficial ainda usa HTTP interno; planejar certificado confiável e HTTPS;
- encaminhamentos antigos `80`, `3001` e `3002` no DC permanecem como legado inativo;
- o MSI não foi instalado em Windows real nesta janela;
- não há Server Agent piloto nem implantação GPO aprovada;
- o `dcdiag /q` completo contém pendências de AD não causadas pelo Vulcan.

Prioridade operacional: mover o mesmo bundle/volumes para uma VM Linux fixa no Proxmox,
com IP estático, disco monitorado e TLS, mantendo `192.168.200.4:8099` como endereço
oficial durante a transição.
