# Notificacoes Para Agente

O canal Windows/agente prepara comunicacao do backend para o agente instalado na maquina do colaborador. O foco e mensagem operacional, status e acao requerida, sem capturar conteudo pessoal.

## Fluxo Planejado

1. Backend cria uma notificacao para usuario/dispositivo.
2. Agente consulta notificacoes durante heartbeat/sync.
3. Agente exibe a mensagem local quando o sistema operacional permitir.
4. Usuario confirma, ignora ou resolve quando aplicavel.
5. Agente envia ack/dismiss ao backend.
6. Backend atualiza status, tentativas e auditoria.

## Tipos Para Agente

- adocao pendente;
- coleta limitada;
- agente precisa reiniciar;
- politica atualizada;
- fila offline alta;
- falha de sincronizacao;
- mensagem operacional do gestor;
- lembrete de acao.

## Endpoints Atuais E Futuros

Atuais:

- `POST /agent/heartbeat`;
- `POST /agent/sync`;
- `POST /agent/events`;
- `GET /agent/status`;
- `POST /notifications/send` com `channel=windows`.

Futuros:

- `GET /agent/notifications`;
- `POST /agent/notifications/{id}/ack`;
- `POST /agent/notifications/{id}/dismiss`.

## Privacidade

O agente nao deve exibir informacao fora do escopo do usuario da maquina. Mensagens devem ser construtivas e operacionais.

O Vulcan nao coleta:

- senha;
- tecla digitada;
- audio;
- webcam;
- conteudo de mensagem privada;
- print continuo.

Coleta:

- app ativo;
- duracao;
- troca de contexto;
- status do agente;
- qualidade de coleta;
- eventos operacionais.

## Estado No MVP

O backend ja registra notificacoes com canal `windows`, status, tentativas e metadata. A UI mostra o canal como parte da central. A entrega local com ack no agente ainda e pendencia de producao.
