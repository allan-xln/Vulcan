# Vulcan macOS Agent

Estrutura reservada para o agente macOS.

Plano recomendado:

- binario Swift/Go;
- `LaunchDaemon` para heartbeat/sync;
- `LaunchAgent` por usuario para sessao ativa;
- permissao Accessibility para identificar aplicativo/janela ativa;
- fila offline JSONL/SQLite;
- mesmo contrato HTTP de `agentes/shared/agent-api.md`;
- pacote `.pkg` assinado e notarizado.
