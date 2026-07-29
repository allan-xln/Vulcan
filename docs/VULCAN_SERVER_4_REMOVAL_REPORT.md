# Relatório de Remoção do Vulcan no Servidor 4

## Status

**REMOÇÃO NÃO EXECUTADA — CORTE BLOQUEADO COM SEGURANÇA**

- Servidor: `192.168.200.4`
- Hostname: `SRVERS01.erstransportes.local`
- Data do relatório inicial: `2026-07-29`
- Impacto causado pela auditoria: nenhum
- Reinicialização executada: não
- Serviços AD/DNS alterados: nenhum

## Motivo

O backup do ambiente atual foi gerado, teve checksums validados e passou por um restore
temporário. Entretanto, a implantação no `192.168.200.7` ainda não ocorreu porque o
acesso administrativo ao servidor foi rejeitado por WinRM e SMB.

Remover agora os encaminhamentos do servidor 4 interromperia o acesso à instalação que
continua executando em `192.168.200.160`. Isso violaria o gate obrigatório de migração e
foi deliberadamente evitado.

## Itens exclusivos identificados para a futura remoção

- encaminhamentos `portproxy` das portas `80`, `3001`, `3002` e `8099`;
- quatro regras Windows Firewall nomeadas para o Vulcan;
- `C:\ProgramData\Vulcan\Deploy\VulcanAgent-Windows-x64.zip`;
- diretório `C:\ProgramData\Vulcan` caso permaneça vazio e seja confirmado como exclusivo
  após a remoção do artefato.

## Itens removidos

Nenhum.

## Itens que permaneceram e por quê

- todos os componentes AD DS, DNS, SYSVOL, Netlogon, Kerberos, LDAP e Windows: críticos;
- UniFi Controller/Java/MongoDB: sistema compartilhado e não relacionado ao Vulcan;
- Portal de Automações TI/Python: sistema não relacionado;
- serviço Windows IP Helper: compartilhado; somente entradas específicas poderão ser
  removidas;
- Windows Firewall: compartilhado; somente regras específicas poderão ser removidas;
- encaminhamentos e artefato Vulcan: mantidos até o novo ambiente passar pelo gate de
  validação.

## Backup e rollback

Existe um backup privado, fora do Git, contendo dumps lógicos, volumes, configurações,
manifests e checksums. O restore temporário validou as principais quantidades do Vulcan
e da Evolution API. O rollback técnico dos dados está disponível, mas o rollback
operacional do corte só será documentado depois que o destino e a URL final forem
definidos.

## Validações pendentes antes da remoção

- implantação e E2E no servidor 7;
- migração final com janela de corte;
- agente real online no novo endpoint;
- Wallboard real no novo endpoint;
- prova de backup/restore no destino;
- validação de DNS e rota final;
- captura de baseline e pós-corte de `dcdiag`;
- validação de replicação com `repadmin`;
- validação final do DNS;
- observação de portas e conexões;
- autorização do corte.

Este documento deve ser atualizado com data, responsável, comandos, evidências,
resultado de AD/DNS e risco residual imediatamente após o corte real.
