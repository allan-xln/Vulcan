# Vulcan Agent API Contract

Todos os requests usam JSON e `enrollmentToken`. O token de enrollment deve ser diferente por ambiente e, idealmente, por tenant.

O contrato do agente e LGPD-friendly: nao existe keylogger, captura de senha, screenshot, webcam, audio, cookies, tokens ou conteudo privado. Coletas potencialmente sensiveis ficam atras de politica explicita.

## Enroll

`POST /agent/enroll`

Campos principais:

- `tenantId`
- `enrollmentToken`
- `hostname`
- `osUser`
- `osVersion`
- `deviceId`
- `machineFingerprint`
- `agentVersion`
- `linkedUser`
- `membershipId`
- `roleLevel`
- `department`
- `managerMembershipId`

## Heartbeat

`POST /agent/heartbeat`

Usado para manter `devices.last_seen_at`, status, versao do agente, fila offline, ultimo erro, IP local, uptime, saude do agente e qualidade de coleta.

Campos adicionais recomendados:

- `queueDepth`
- `lastError`
- `metadata.localIp`
- `metadata.uptimeSeconds`
- `metadata.collectionQuality`
- `metadata.collectionMethod`
- `metadata.agentMemoryMb`
- `metadata.policy`

## Events

`POST /agent/events`

Recebe lote de eventos operacionais. Eventos aceitos:

- `app_focus_started`
- `app_focus_ended`
- `context_switch`
- `idle_started`
- `idle_ended`
- `session_locked`
- `session_unlocked`
- `user_logged_in`
- `user_logged_out`
- `machine_sleep`
- `machine_resume`
- `heartbeat`
- `sync_status`
- `collection_quality`
- `agent_error`
- `agent_health`

Cada evento pode conter:

- `appName`
- `windowTitle`, somente se permitido por politica
- `startedAt`
- `endedAt`
- `durationSeconds`
- `category`
- `metadata.collectionQuality`
- `metadata.collectionMethod`
- `metadata.browserDomain`, somente se permitido por politica
- `metadata.browserUrl`, somente se permitido por politica e sem querystring por padrao

## Sync

`POST /agent/sync`

Reservado para sincronizacao em lote/fila offline. A implementacao atual usa `/agent/events` para eventos ricos e mantem o contrato de sync para compatibilidade.

## Logs

`POST /agent/logs`

Reservado para logs operacionais relevantes do agente. Nao deve enviar dados privados do usuario.
