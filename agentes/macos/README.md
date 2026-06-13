# Vulcan macOS Agent

Skeleton funcional do agente macOS do Vulcan.

Ele ainda nao substitui um pacote `.pkg` assinado/notarizado, mas ja executa o fluxo minimo real:

- configuracao local;
- enroll no backend;
- heartbeat;
- fila offline JSONL;
- sync;
- LaunchAgent por usuario;
- status local;
- tentativa de identificar aplicativo ativo via `osascript`;
- qualidade de coleta `medium` ou `blocked_by_os`;
- mensagem explicita de privacidade.

## Privacidade

O agente mede fluxo operacional, nao conteudo pessoal.

Nao coleta:

- senha;
- tecla digitada;
- audio;
- webcam;
- screenshot continuo;
- conteudo de mensagens;
- clipboard;
- tokens/cookies.

Coleta:

- app ativo quando o macOS permitir;
- duracao operacional aproximada;
- hostname;
- usuario do sistema;
- versao do macOS;
- IP local;
- status do agente;
- fila offline;
- qualidade da coleta.

## Instalar

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/macos
bash ./install.sh \
  --backend-url "http://localhost:3001" \
  --tenant-id "00000000-0000-0000-0000-000000000301" \
  --enrollment-token "vulcan-local-enrollment-token"
```

Com vinculo direto a um usuario:

```bash
bash ./install.sh \
  --backend-url "http://localhost:3001" \
  --tenant-id "00000000-0000-0000-0000-000000000301" \
  --enrollment-token "vulcan-local-enrollment-token" \
  --membership-id "00000000-0000-0000-0000-000000300005"
```

Sem `membership-id`, o dispositivo aparece no Vulcan como `Dispositivo aguardando adocao`.

## Permissao Accessibility

Para coletar app ativo de forma mais confiavel:

1. Abra `Ajustes do Sistema`.
2. Va em `Privacidade e Seguranca`.
3. Entre em `Acessibilidade`.
4. Permita Terminal/iTerm ou o app que estiver executando o agente.

Se o macOS bloquear a leitura, o agente envia `collectionQuality=blocked_by_os`, e o dashboard deve mostrar coleta limitada.

## Operacao

```bash
./status.sh
launchctl list | grep com.lanfuture.vulcan.agent
tail -f "$HOME/Library/Logs/VulcanAgent/agent.log"
```

Sync manual:

```bash
"$HOME/Library/Application Support/Vulcan/Agent/vulcan_macos_agent.py" heartbeat
"$HOME/Library/Application Support/Vulcan/Agent/vulcan_macos_agent.py" sync
```

Desinstalar:

```bash
./uninstall.sh
```

Remover dados locais:

```bash
./uninstall.sh --purge
```

## Proximos Passos Para Producao

- migrar para binario Swift/Go;
- app de status/tray;
- `.pkg` assinado;
- notarizacao Apple;
- MDM/Intune/Jamf;
- fluxo visual para permissao Accessibility;
- update automatico;
- politica remota.
