# Vulcan Server Agent

## Escopo

Server monitora disponibilidade e recursos sem calcular produtividade de funcionário.
Políticas que habilitem `activity` são rejeitadas para esse perfil.

## Implementado na fundação 0.2.0

- SO, kernel, arquitetura, hostname e uptime;
- CPU, memória, swap e espaço em volumes;
- interfaces e contadores de rede;
- inventário básico de discos e adaptadores;
- probes HTTP/HTTPS configurados;
- probes TCP configurados;
- self-health, versão, política, fila e última comunicação;
- eventos canônicos e replay offline.

Checks são declarativos na política, têm timeout e não contêm shell. Uma conexão a banco
pode ser representada inicialmente por TCP; credenciais e queries não devem ser inseridas
em texto puro.

## Ainda não implementado

- IOPS/latência detalhada por volume;
- logs e Windows Event Log/journald normalizados;
- Docker/containers;
- certificados e expiração;
- scheduled jobs, backups e filas;
- sessões RDP/SSH detalhadas;
- inventário completo de software/hotfix/driver;
- sensores e checks específicos de aplicações;
- helper privilegiado para fontes protegidas.

## Instalação

Linux usa o pacote `.deb`, usuário de sistema `vulcan-agent` e diretórios em `/etc`,
`/var/lib` e `/var/log`. Windows usa MSI e LocalService. Consulte os guias específicos.

## Política

Defina apenas endpoints e portas aprovados, intervalos compatíveis com o serviço e timeout
baixo. Evite consultar todos os processos a cada segundo. Inventário pesado deve ficar em
horas, saúde em dezenas de segundos/minutos e detalhes por exceção.

## Segurança

O perfil não executa PowerShell/Bash, restart de serviço, reparo ou alteração de
configuração. Comandos remotos são tipados e auditados; ações corretivas permanecem
desativadas nesta fase.

## Homologação

Teste em cada família de SO, inclusive reinício, queda do gateway, pouco disco, certificado
ruim e fila cheia. A cross-compilation não substitui validação em Windows Server real.
