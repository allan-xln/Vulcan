# Vulcan Collector Agent

## Escopo

Collector compartilha identidade, política, fila, transporte e inventário do agente Go,
mas nunca carrega produtividade de funcionário.

## Implementado na fundação 0.2.0

- inventário do host coletor;
- self-health, CPU, memória, disco e rede;
- discovery read-only em CIDRs explicitamente permitidos;
- resolução DNS direta;
- probes TCP apenas para portas permitidas na política;
- limites de alvos, concorrência e timeout;
- eventos canônicos, fila cifrada, deduplicação e forwarding HTTPS.

Discovery vem habilitado no perfil, porém `allowedNetworks=[]` significa **nenhuma
descoberta**. Redes públicas/proibidas e alvos fora do allowlist são rejeitados.

## Não implementado nesta versão

- SNMP v2c/v3 e templates/OIDs;
- ping sweep, reverse DNS, ARP e identificação OUI;
- receiver de traps;
- syslog UDP/TCP/TLS;
- NetFlow, sFlow e IPFIX;
- adapters UniFi/FortiGate;
- tabela MAC e LLDP/CDP;
- cache de credenciais por secret reference;
- topologia derivada.

Esses itens não aparecem como dados reais na UI.

## Instalação

Use o pacote Linux no perfil `collector`, usuário `vulcan-agent` e unit de sistema. O
coletor inicia somente conexões HTTPS de saída. Nenhum receiver abre porta nesta versão.

## Política segura

Uma política de produção precisa definir:

- redes permitidas e exclusões;
- janela e frequência;
- máximo de alvos;
- concorrência e timeout;
- portas TCP aprovadas;
- site do coletor;
- retenção e volume de fila.

Comece com poucos alvos. Não use `0.0.0.0/0`, não habilite scan agressivo e não execute
alterações remotas. Toda descoberta deve ser atribuída ao tenant/site pelo servidor.

## Próxima fase

Introduzir adapters sob contrato comum, secret references no backend e receivers isolados
com rate limit/dead-letter queue. SNMP/syslog/flows devem virar eventos canônicos e ativos
pendentes de aprovação, nunca mudanças automáticas na rede.
