# Linux Agent

## Build

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
corepack pnpm agent:linux:package
```

## Install Local Demo

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/installers/linux
bash ./instalar-vulcan-teste.sh --backend-url "http://localhost:3001" --install-deps
```

## Service Commands

```bash
./status.sh
systemctl --user status vulcan-agent.service
systemctl --user restart vulcan-agent.service
journalctl --user -u vulcan-agent.service -f
./uninstall.sh
./uninstall.sh --purge
```

## Collection Quality

Linux desktops can restrict active-window collection depending on GNOME, Wayland, X11 and security policy. Vulcan must report collection quality instead of pretending the data is complete.

Supported signals:

- heartbeat;
- active app/window when allowed;
- idle/session signals where available;
- queue depth;
- sync status;
- device metadata.

## Queue And Retry

The Linux agent should use:

- configurable batch size;
- configurable timeout;
- retry with backoff;
- offline queue;
- readable logs;
- dashboard alert when queue grows.
