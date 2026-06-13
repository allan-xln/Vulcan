# macOS Agent

## Status Atual

macOS ainda nao esta production-ready, mas deixou de ser apenas placeholder.

Existe um skeleton funcional em:

```text
agentes/macos/
```

Ele entrega:

- `vulcan_macos_agent.py`;
- `install.sh`;
- `status.sh`;
- `uninstall.sh`;
- LaunchAgent por usuario;
- configuracao local;
- enroll;
- heartbeat;
- fila offline JSONL;
- sync;
- tentativa de leitura do app ativo via `osascript`;
- qualidade de coleta `medium` ou `blocked_by_os`;
- mensagem de privacidade.

## Instalar

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/macos
bash ./install.sh \
  --backend-url "http://localhost:3001" \
  --tenant-id "00000000-0000-0000-0000-000000000301" \
  --enrollment-token "vulcan-local-enrollment-token"
```

Com usuario vinculado:

```bash
bash ./install.sh \
  --backend-url "http://localhost:3001" \
  --tenant-id "00000000-0000-0000-0000-000000000301" \
  --enrollment-token "vulcan-local-enrollment-token" \
  --membership-id "00000000-0000-0000-0000-000000300005"
```

Sem `membership-id`, o dispositivo entra como pendente para adoção no painel.

## Status E Logs

```bash
./status.sh
launchctl list | grep com.lanfuture.vulcan.agent
tail -f "$HOME/Library/Logs/VulcanAgent/agent.log"
```

## Permissao Accessibility

Para ler app ativo de forma confiavel, o macOS pode exigir permissao em:

```text
Ajustes do Sistema > Privacidade e Seguranca > Acessibilidade
```

Permita Terminal/iTerm ou o app que executa o agente.

Se a leitura for bloqueada, o agente envia `collectionQuality=blocked_by_os`, e o Vulcan mostra coleta limitada.

## Privacidade

O macOS agent segue a mesma regra dos demais agentes:

Nao coleta:

- senhas;
- teclas digitadas;
- audio;
- webcam;
- conteudo de mensagens;
- screenshots continuos;
- clipboard;
- cookies/tokens.

Coleta:

- app ativo quando permitido;
- duracao operacional aproximada;
- heartbeat;
- fila offline;
- hostname;
- usuario do sistema;
- versao macOS;
- IP local;
- qualidade de coleta.

## Roadmap Para Producao

1. Migrar skeleton para binario Swift ou Go.
2. Criar app de status/tray.
3. Criar pacote `.pkg`.
4. Assinar e notarizar.
5. Preparar distribuicao Jamf/MDM/Intune.
6. Criar fluxo visual para permissao Accessibility.
7. Validar em hardware macOS real.
