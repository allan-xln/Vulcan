# Vulcan Agents

Esta pasta contem os agentes locais do Vulcan.

## Windows

Status: MVP funcional preparado como EXE x64, servico Windows, coletor de sessao e scripts para instalacao local ou em massa.

Artefatos gerados:

- `agentes/installers/windows/VulcanAgent.exe`
- `agentes/installers/windows/VulcanAgentSetup.exe`
- `agentes/installers/windows/VulcanAgent-Windows-x64.zip`

## Linux

Status: MVP funcional com Python 3, `systemd --user`, fila offline e o mesmo contrato HTTP em `agentes/shared`.

Artefato gerado:

- `agentes/installers/linux/VulcanAgent-Linux.zip`

## macOS

Status: skeleton funcional com Python 3, LaunchAgent por usuario, heartbeat, sync, fila offline e contrato HTTP compartilhado. A coleta de aplicativo ativo usa `osascript`/System Events quando o macOS permitir; sem permissao de Acessibilidade, o agente marca `collectionQuality=blocked_by_os`.

Scripts:

- `agentes/macos/install.sh`
- `agentes/macos/status.sh`
- `agentes/macos/uninstall.sh`
- `agentes/macos/vulcan_macos_agent.py`

Ainda faltam para producao macOS: pacote `.pkg`, assinatura, notarizacao, app de status/tray e fluxo guiado de permissao Accessibility.

## Contrato com backend

Endpoints usados:

- `GET /agent/status`
- `POST /agent/enroll`
- `POST /agent/heartbeat`
- `POST /agent/events`
- `POST /agent/sync`
- `POST /agent/logs`
