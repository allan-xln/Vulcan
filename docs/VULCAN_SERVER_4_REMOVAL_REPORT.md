# Relatório de preservação do Vulcan no Servidor 4

## Status

**NENHUMA REMOÇÃO EXECUTADA — SERVIDOR 4 É O PONTO OFICIAL DE ENTRADA**

- servidor: `192.168.200.4`;
- hostname: `SRVERS01.erstransportes.local`;
- data: `2026-07-29`;
- reinicialização: não;
- serviços AD/DNS alterados: nenhum;
- runtime pesado instalado no DC: nenhum.

## O que permaneceu

O encaminhamento necessário permanece ativo:

```text
192.168.200.4:8099 -> 192.168.200.26:8099
```

A regra de firewall `Vulcan LAN Installer 8099` também foi preservada. Ela entrega
aplicação, Wallboard, API e downloads através de uma única borda na VM Linux dedicada
`VULCAN-PROD01`.

Os encaminhamentos antigos 80, 3001 e 3002, suas regras de firewall e o artefato
`C:\ProgramData\Vulcan\Deploy\VulcanAgent-Windows-x64.zip` permanecem como legado.
Eles não foram removidos porque a sessão administrativa não possuía elevação suficiente
para mudança e porque a missão atual não autorizou uma janela separada de limpeza.

## O que foi removido

Nada no SRVERS01. A release anterior, os volumes e os backups do runtime temporário
`.160` foram preservados como rollback, mas seus containers de produção foram parados
depois que o acesso oficial passou a responder pela VM `.26`.

## O que não pertence ao Vulcan

AD DS, DNS, SYSVOL, Netlogon, Kerberos, LDAP/LDAPS, SMB, WinRM, Windows Firewall,
IP Helper, UniFi Controller, certificados do domínio e demais serviços compartilhados não
foram alterados nem classificados como removíveis.

## Validação posterior

- NTDS, DNS, KDC, Netlogon, DFSR e W32Time ativos/automáticos;
- Advertising, Services, SysVolCheck, NetLogons e DNS passaram no `dcdiag` focado;
- SYSVOL e NETLOGON presentes;
- DNS SOA, LDAP SRV, Kerberos SRV e A do SRVERS01 válidos;
- `repadmin /replsummary`: zero falhas em cinco objetos para o destino SRVERS01;
- conexão do SRVERS01 ao runtime 8099: aprovada;
- CPU observada: 16%; memória livre: aproximadamente 2 GiB; disco C: 11,4 GiB livres.

O `dcdiag /q` completo registrou bind negado para o SRVERS08 e eventos de confiança
relacionados a SRVERS04/ERS-SJP-021. O `repadmin` registrou erro operacional 110 ao
consultar SRVERS08. Não há evidência de relação com o Vulcan; nenhuma correção automática
foi executada.

## Limpeza futura

Uma janela futura pode remover somente os listeners legados 80/3001/3002, suas regras e o
ZIP antigo, após confirmar ausência de clientes e manter 8099. O procedimento precisa de
backup da configuração `portproxy`, validação antes/depois e credencial elevada.
