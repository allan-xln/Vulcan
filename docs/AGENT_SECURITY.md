# Vulcan Agent — segurança

## Modelo de confiança

O token serve somente para enrollment. O servidor armazena SHA-256 e prefixo, resolve o
tenant a partir do registro do token e entrega uma identidade vinculada a exatamente um
tenant e dispositivo.

Cada instalação gera uma chave Ed25519 própria. Depois do enrollment, cada request assina
método, path, timestamp, nonce e hash do corpo. O backend:

1. encontra a identidade pelo ID;
2. valida revogação, chave, assinatura e hash;
3. rejeita drift acima da janela de cinco minutos;
4. grava o nonce de uso único;
5. resolve tenant e dispositivo no servidor.

Um replay idêntico retorna `401`.

## Dados locais

- chave privada Ed25519: cifrada com AES-256-GCM;
- fila SQLite: payloads cifrados com AES-256-GCM;
- arquivos Unix: diretórios `0700`, chaves/banco `0600`;
- Windows: ACL para LocalService, SYSTEM e Administradores;
- política: envelope Ed25519 assinado e aplicação atômica com versão anterior.

O token de enrollment não integra a configuração persistida. Diagnóstico e logs redigem
valores que se pareçam com token, segredo ou chave.

## Transporte

TLS válido é obrigatório fora de loopback. O cliente usa timeouts, retry exponencial,
jitter, circuit breaker, lotes, idempotência e confirmação. NATS e bancos internos nunca
são expostos diretamente ao endpoint.

Compressão de lotes e mTLS ainda não estão implementados; são evoluções compatíveis do
gateway HTTPS.

## Privilégios

Workstation Linux roda no usuário da sessão. Server/Collector Linux usam um usuário de
sistema sem capabilities. Windows MSI usa LocalService. O coletor de janela Windows
multi-sessão exigirá um helper de sessão com IPC autenticado; a entrega não tenta contornar
isolamento de sessão nem roda um coletor invasivo como SYSTEM.

## Limites de privacidade

Não existem keylogger, captura de senha, clipboard, screenshot, webcam, microfone ou shell
remoto genérico. Título de janela fica desligado por padrão e filtros ocultam janelas de
senha, autenticação e banco. Perfis Server e Collector rejeitam atividade de funcionário.

Os contratos de módulo visual são apenas reserva arquitetural e permanecem rejeitados pela
validação de política.

## Comandos remotos

O banco/API aceitam somente tipos enumerados, com motivo, solicitante, expiração, alvo e
auditoria. O agente não interpreta PowerShell/Bash arbitrário. Nesta versão, comandos
destrutivos e ações corretivas permanecem desabilitados.

## Release

Cada build produz SHA-256 e SBOM CycloneDX. O update automático não instala artefatos
enquanto manifesto assinado, verificação de assinatura de código, staging e rollback não
forem homologados. O MSI e o binário desta entrega são tecnicamente válidos, mas ainda não
estão assinados.

## Resposta a incidente

Revogue a identidade em `/agent/v2/admin/agents/{id}/revoke`, preserve logs/fila conforme
retenção, emita novo token e faça enrollment limpo. Nunca mova uma identidade silenciosamente
entre tenants.
