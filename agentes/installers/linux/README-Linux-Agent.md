# Vulcan Linux Agent

Agente Linux do Vulcan para Inteligência Operacional. Ele roda como `systemd --user`, coleta sinais operacionais permitidos e sincroniza com o backend Vulcan.

## Privacidade

O agente não coleta senhas, teclas digitadas, screenshots, áudio, webcam, clipboard irrestrito, tokens, cookies ou conteúdo de mensagens.

Coletas sensíveis ficam desligadas por padrão e dependem de política:

- `collectWindowTitle=false`
- `collectBrowserDomain=false`
- `collectBrowserUrl=false`
- `collectBrowserHistory=false`
- `collectProcessList=false`

O arquivo de política fica em:

```text
~/.config/vulcan/agent/agent-policy.json
```

## O Que Coleta Agora

- aplicativo ativo;
- título da janela ativa, somente quando permitido;
- duração por aplicativo;
- duração por janela, quando título estiver habilitado;
- troca de contexto;
- tempo ativo;
- tempo ocioso;
- bloqueio/desbloqueio de sessão quando o sistema permitir;
- retorno de suspensão por lacuna de tempo;
- hostname;
- usuário Linux;
- versão do sistema;
- uptime;
- IP local;
- versão do agente;
- heartbeat;
- status online/offline/sincronizando;
- qualidade da coleta: `high`, `medium`, `low`, `blocked_by_os`;
- erros de coleta/sync;
- fila offline;
- lote de sincronização limitado por `syncBatchSize` para reduzir timeout;
- `eventId` idempotente no backend para evitar duplicidade quando houver retry;
- categoria do aplicativo;
- saúde do agente.
- qualidade da máquina: carga, memória, swap, disco e processos mais pesados quando permitido;
- histórico recente de navegador, somente quando `collectBrowserHistory=true`, com domínio e URL sanitizada sem querystring/fragmento;
- alerta técnico de domínio adulto quando o domínio bater em padrões conhecidos.

O modo corporativo liga a coleta máxima suportada sem keylogger, screenshot, áudio, webcam, clipboard, cookies ou tokens:

```bash
bash ./instalar-vulcan-teste.sh \
  --backend-url "http://localhost:3001" \
  --install-deps \
  --corporate-monitoring
```

Esse modo habilita:

- `collectWindowTitle=true`
- `collectBrowserDomain=true`
- `collectBrowserUrl=true`
- `collectBrowserHistory=true`
- `collectBrowserPageTitle=true`
- `collectProcessList=true`
- `privacyMode=corporate`

As URLs coletadas removem querystring e fragmento. Exemplo: `https://site.com/pagina?token=...#x` vira `https://site.com/pagina`.

## Camadas De Detecção Linux

O agente tenta, nesta ordem:

1. X11 com `xdotool`;
2. X11 com `xprop` + `wmctrl`;
3. GNOME Shell via DBus;
4. heurística limitada de processo, somente com `collectProcessList=true`;
5. fallback para ambiente desktop.

Em Wayland/GNOME/Zorin, o sistema pode bloquear o app real. Nesse caso o agente envia `collectionQuality=blocked_by_os` e o dashboard mostra `Coleta limitada pelo ambiente gráfico`.

Para melhorar a coleta em X11:

```bash
sudo apt-get update
sudo apt-get install -y xdotool wmctrl x11-utils xprintidle
```

## Instalar No Usuário Teste

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/installers/linux
bash ./instalar-vulcan-teste.sh --backend-url "http://localhost:3001" --install-deps
```

Com título de janela e heurística de processo explicitamente habilitados:

```bash
bash ./instalar-vulcan-teste.sh \
  --backend-url "http://localhost:3001" \
  --install-deps \
  --collect-window-title \
  --collect-browser-history \
  --collect-process-list
```

## Operação

Parar:

```bash
systemctl --user stop vulcan-agent.service
```

Iniciar:

```bash
systemctl --user start vulcan-agent.service
```

Reiniciar:

```bash
systemctl --user restart vulcan-agent.service
```

Status:

```bash
systemctl --user status vulcan-agent.service --no-pager
~/.local/share/vulcan/agent/vulcan_agent.py status
```

Logs:

```bash
journalctl --user -u vulcan-agent.service -f
tail -f ~/.local/state/vulcan-agent/logs/agent.log
```

Sincronizar manualmente:

```bash
~/.local/share/vulcan/agent/vulcan_agent.py heartbeat
~/.local/share/vulcan/agent/vulcan_agent.py sync
```

Desinstalar mantendo dados:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/installers/linux
bash ./uninstall.sh
```

Remover tudo:

```bash
bash ./uninstall.sh --purge
rm -rf ~/.local/share/vulcan/agent ~/.config/vulcan/agent ~/.local/state/vulcan-agent
```
