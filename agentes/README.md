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

Status: estrutura reservada. O agente macOS deve usar LaunchDaemon/LaunchAgent, Accessibility permission para app ativo, fila offline e o mesmo contrato HTTP em `agentes/shared`.

## Contrato com backend

Endpoints usados:

- `GET /agent/status`
- `POST /agent/enroll`
- `POST /agent/heartbeat`
- `POST /agent/events`
- `POST /agent/sync`
- `POST /agent/logs`
