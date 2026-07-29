# Inventário do Servidor Antigo do Vulcan

## Controle da auditoria

- Data da coleta: `2026-07-29`
- Servidor auditado: `192.168.200.4`
- Hostname: `SRVERS01.erstransportes.local`
- Modo da auditoria: somente leitura
- Estado da remoção: **não aplicável ao listener oficial 8099**
- Destino aprovado: VM isolada `VULCAN-PROD01` (`192.168.200.26`)
- Função atual: ponto oficial de entrada, sem runtime pesado no controlador de domínio.

Credenciais, valores de `.env`, chaves, certificados privados e conteúdo dos dumps não
fazem parte deste documento nem do Git.

## Conclusão principal

O servidor `192.168.200.4` não contém o runtime, os containers nem o banco do Vulcan. Ele
atua como encaminhador TCP para a VM dedicada `192.168.200.26`. Os únicos componentes
exclusivos do Vulcan encontrados no servidor 4
foram:

1. quatro regras de `netsh interface portproxy`;
2. quatro regras de entrada do Windows Firewall;
3. um pacote de instalação do agente em `C:\ProgramData\Vulcan\Deploy`.

O Active Directory, o DNS, o UniFi Controller e os componentes do Windows encontrados
nesse servidor são críticos ou compartilhados e não podem ser tratados como parte do
Vulcan.

## Sistema e funções críticas

| Item | Estado encontrado | Classificação |
| --- | --- | --- |
| Sistema operacional | Windows Server 2025 Standard | compartilhado/crítico |
| Função de domínio | controlador de domínio, `DomainRole=5` | crítico AD |
| AD DS | instalado e em execução | crítico AD |
| DNS Server | instalado e em execução | crítico DNS |
| NTDS | em execução, inicialização automática | crítico AD |
| KDC | em execução, inicialização automática | crítico AD |
| Netlogon | em execução, inicialização automática | crítico AD |
| DFSR/SYSVOL | em execução | crítico AD |
| W32Time | em execução | crítico AD |
| Hardware virtual | QEMU, 4 vCPU, 8 GiB de RAM | compartilhado |
| Disco do sistema | 67,7 GiB; cerca de 12,25 GiB livres na coleta | compartilhado |

Os controladores de domínio retornados pela consulta autorizada no servidor foram
`SRVERS01` (`192.168.200.4`) e `SRVERS08` (`192.168.200.15`).

## Componentes exclusivos do Vulcan

### Encaminhamentos TCP

Os listeners pertencem ao serviço Windows IP Helper (`iphlpsvc`) e encaminham tráfego
para o host atual do produto:

| Listener no servidor 4 | Destino atual | Uso |
| --- | --- | --- |
| `192.168.200.4:80` | `192.168.200.160:3002` | frontend |
| `192.168.200.4:3001` | `192.168.200.160:3001` | API |
| `192.168.200.4:3002` | `192.168.200.160:3002` | frontend direto |
| `192.168.200.4:8099` | `192.168.200.26:8099` | borda oficial atual |

Os listeners 80, 3001 e 3002 continuam como legado apontado ao antigo runtime temporário
`.160`. O destino atual `192.168.200.26:8099` serve a release de produção e foi validado
através do listener `192.168.200.4:8099`. Essa regra é necessária para o acesso oficial e
não deve ser removida enquanto essa arquitetura estiver vigente.

### Regras de firewall

- `Vulcan LAN Frontend 3002`
- `Vulcan LAN Backend 3001`
- `Vulcan LAN Installer 8099`
- `Vulcan LAN HTTP 80`

As quatro regras são de entrada TCP no perfil de domínio e estão classificadas como
exclusivas do Vulcan.

### Arquivo de implantação

- Caminho: `C:\ProgramData\Vulcan\Deploy\VulcanAgent-Windows-x64.zip`
- Tamanho: `9.144.712` bytes
- SHA-256:
  `4179925e62e4565be14757cdbbb9d27f9fb9d6386e750ea85dc1edaec8d1a981`

O arquivo foi copiado para o backup protegido e o hash da cópia foi validado.

## Componentes não encontrados no servidor 4

- Docker, Docker Compose ou containers Vulcan;
- Podman;
- distribuições WSL;
- máquinas virtuais Hyper-V;
- IIS hospedando o Vulcan;
- Nginx ou Apache hospedando o Vulcan;
- PostgreSQL ou Redis do Vulcan;
- serviços Windows com nome Vulcan;
- tarefas agendadas Vulcan;
- entradas Vulcan de inicialização automática;
- certificados identificados como exclusivos do Vulcan;
- diretórios de banco, volumes ou runtime do Vulcan;
- regras Vulcan em SYSVOL/GPO.

## Componentes compartilhados ou de outros sistemas

| Componente | Decisão |
| --- | --- |
| Active Directory Domain Services | não alterar |
| DNS Server, zonas e registros não exclusivos | não alterar |
| SYSVOL, Netlogon, Kerberos e LDAP | não alterar |
| UniFi Controller, Java, MongoDB e porta `8080` | manter; sistema não relacionado |
| Portal de Automações TI/Python | manter; sistema não relacionado |
| Windows Firewall compartilhado | manter; remover futuramente somente as quatro regras Vulcan |
| Serviço IP Helper | manter; remover futuramente somente as entradas `portproxy` Vulcan |

## Origem real dos dados a migrar

Na auditoria inicial, a origem dos dados foi encontrada no runtime temporário Linux
`192.168.200.160`, no repositório `Vulcan`. Esse estado foi migrado para a VM definitiva
sem recriar o banco. O compose contém:

- API;
- frontend;
- PostgreSQL do Vulcan;
- worker de WhatsApp;
- Evolution API;
- PostgreSQL da Evolution;
- Redis exclusivo da Evolution.

Volumes encontrados:

- `vulcan_vulcan_postgres`;
- `vulcan_vulcan_runtime`;
- `vulcan_evolution_instances`;
- `vulcan_evolution_postgres`;
- `vulcan_evolution_redis`.

O tenant real existente é `ERS Transportes`, slug `ers-transportes`.

## Backup protegido e validação

O backup foi armazenado fora do repositório, em diretório local privado com permissão
`0700`. Arquivos e manifests sensíveis usam permissão `0600`.

Conteúdo protegido:

- dump lógico custom do banco Vulcan;
- dump lógico custom do banco Evolution;
- roles/globals necessários ao restore;
- arquivos de configuração e compose resolvido;
- manifests de containers e imagens;
- os cinco volumes persistentes;
- artefato do agente copiado do servidor 4;
- inventários brutos do servidor 4;
- commit de origem;
- `SHA256SUMS`.

Checksums principais:

| Arquivo | SHA-256 |
| --- | --- |
| `vulcan.dump` | `86386aaa086ea5be0c7b2f7e474e4c55d34871687a6466830dbcaa8b327682bb` |
| `evolution.dump` | `bb2d4bb2d1fb864b85ff5e186314a4d4aaaf5767ae39ca82713c1011db3401f4` |

`sha256sum --check` passou para todos os 26 arquivos do conjunto.

### Teste real de restauração

Os dumps foram restaurados em bancos PostgreSQL temporários, isolados do ambiente em
execução. A primeira tentativa revelou a dependência legítima das roles compatíveis com
Supabase; após aplicar o backup de globals, a restauração completa passou.

Validação do banco Vulcan restaurado:

| Entidade | Quantidade |
| --- | ---: |
| Tenants | 1 |
| Usuários de autenticação | 12 |
| Memberships | 11 |
| Dispositivos | 27 |
| Identidades de agente | 21 |
| Eventos unificados | 39.349 |
| Logs de auditoria | 57.992 |

Validação do banco Evolution restaurado:

| Item | Quantidade |
| --- | ---: |
| Tabelas públicas | 37 |
| Instâncias | 1 |

Os bancos e o volume temporários usados no teste foram removidos após a validação. O
ambiente de produção atual não foi alterado.

## Servidor de destino

O runtime aprovado nesta missão é a VM Linux dedicada `VULCAN-PROD01`,
`192.168.200.26`, VMID `103` no nó Proxmox `PVE02`. A release autocontida foi implantada
no projeto `vulcan-production`, com somente a borda 8099 publicada. O antigo runtime
temporário `.160` foi parado após o corte, mantendo volumes e backups. O servidor
`192.168.200.7` deixou de ser requisito desta missão e não recebeu runtime, Docker, WSL
ou aplicação do Vulcan.

## Gate de remoção

O listener e a regra de firewall da porta 8099 permanecem necessários. Os listeners
legados 80, 3001 e 3002 e o pacote ZIP antigo só poderão ser removidos em uma janela
separada, depois de confirmar que nenhum cliente depende deles e com credencial elevada.
Nada foi removido durante este corte.
