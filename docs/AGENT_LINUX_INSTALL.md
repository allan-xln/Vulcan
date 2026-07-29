# Vulcan Agent — instalação Linux

## Compatibilidade

O pacote `.deb` `amd64` atende Ubuntu, Debian, Zorin OS e distribuições compatíveis com
systemd. Há dois modos deliberadamente separados:

- Workstation roda como serviço do usuário para acessar a sessão gráfica sem privilégio;
- Server e Collector rodam como o usuário de sistema sem login `vulcan-agent`.

Não execute coleta de produtividade como root.

## Instalar o pacote

```bash
sudo apt install ./vulcan-agent_0.3.1_amd64.deb
```

O pacote instala o binário e as units, cria usuário/diretórios protegidos, mas não habilita
o serviço antes do enrollment.

## Workstation

No usuário cuja sessão será acompanhada:

```bash
VULCAN_ENROLLMENT_TOKEN='TOKEN_DE_CURTA_DURACAO' \
  vulcan-agent enroll \
  --server 'http://192.168.200.4:8099/api' \
  --profile workstation \
  --allow-insecure-private-network

systemctl --user enable --now vulcan-agent-user
systemctl --user status vulcan-agent-user --no-pager
```

Os dados ficam em `~/.config/vulcan-agent-v2` e
`~/.local/state/vulcan-agent-v2`. Em Wayland, a janela ativa pode não estar disponível; o
agente registra essa limitação e não fabrica atividade.

## Server ou Collector

```bash
sudo -u vulcan-agent env \
  VULCAN_AGENT_CONFIG_DIR=/etc/vulcan-agent \
  VULCAN_AGENT_DATA_DIR=/var/lib/vulcan-agent \
  VULCAN_AGENT_LOG_DIR=/var/log/vulcan-agent \
  VULCAN_ENROLLMENT_TOKEN='TOKEN_DE_CURTA_DURACAO' \
  /usr/bin/vulcan-agent enroll \
  --server 'http://192.168.200.4:8099/api' \
  --profile server \
  --allow-insecure-private-network

sudo systemctl enable --now vulcan-agent
sudo systemctl status vulcan-agent --no-pager
```

Troque `server` por `collector` apenas quando houver política de discovery com allowlist
aprovada. Um allowlist vazio impede descoberta.

## Diretórios e privilégios

- binário: `/usr/bin/vulcan-agent`;
- configuração de sistema: `/etc/vulcan-agent`;
- fila/identidade: `/var/lib/vulcan-agent`;
- logs: `/var/log/vulcan-agent`;
- usuário/grupo: `vulcan-agent`;
- capabilities Linux: nenhuma por padrão;
- filesystem: somente os três diretórios acima são graváveis pela unit endurecida.

ARP de outros namespaces, sensores especiais, logs protegidos e portas privilegiadas podem
exigir um helper futuro. A entrega atual não concede essas capacidades automaticamente.

## Diagnóstico

```bash
sudo -u vulcan-agent env \
  VULCAN_AGENT_CONFIG_DIR=/etc/vulcan-agent \
  VULCAN_AGENT_DATA_DIR=/var/lib/vulcan-agent \
  VULCAN_AGENT_LOG_DIR=/var/log/vulcan-agent \
  vulcan-agent diagnostics

sudo journalctl -u vulcan-agent --since today
```

Para Workstation, execute `vulcan-agent diagnostics` no usuário e consulte
`journalctl --user -u vulcan-agent-user`.

## Remoção

```bash
sudo vulcan-agent unenroll --reason 'remoção autorizada'
sudo apt remove vulcan-agent
```

O pacote preserva dados locais inclusive em `purge`; a exclusão de identidade/fila exige
procedimento explícito de retenção. O agente Python legado permanece suportado apenas como
rollback durante a migração controlada.
