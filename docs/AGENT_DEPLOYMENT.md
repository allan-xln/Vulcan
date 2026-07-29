# Deploy Corporativo do Agente

O Vulcan suporta instalação corporativa autorizada do agente Windows. Não use técnica de ocultação, bypass de UAC, alteração de antivírus ou instalação fora do inventário aprovado.

## Descoberta controlada

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
ERS_WINRM_USER='administrador-autorizado' \
ERS_WINRM_PASSWORD='senha-runtime' \
.venv/bin/python scripts/discover_ers_windows_targets.py \
  --network 192.168.200.0/24 \
  --out .runtime/ers-windows-discovery.json
```

O script:

- aceita apenas redes privadas;
- recusa ranges acima de 1024 endereços;
- verifica ping e portas `445`, `3389`, `5985`;
- valida WinRM somente quando credenciais são fornecidas;
- não instala nada;
- gera relatório com `deployEligible`.

## Pacote

Depois do corte validado, o pacote de produção deverá ser servido por:

```text
http://192.168.200.7/downloads/agents/VulcanAgent-Windows-x64.msi
```

Essa URL de destino não deve ser usada até o health check e o download no servidor 7
passarem. O endpoint legado no servidor 4 permanece somente durante a janela de migração e
deve ser removido após os agentes validados aparecerem exclusivamente no novo ambiente.

O botão `Preparar disparo` no painel gera comando PowerShell/GPO com:

- `BackendUrl`;
- `TenantId`;
- `EnrollmentToken`;
- política de coleta;
- instalação silenciosa autorizada.

## Piloto

Antes de qualquer massa, selecione um único alvo `deployEligible`, execute o comando como administrador autorizado e valide:

- serviço `VulcanAgent`;
- início automático;
- logs locais;
- heartbeat;
- dispositivo pendente no painel;
- adoção;
- eventos e métricas;
- desinstalação.

Se o piloto falhar, corrija antes de continuar.
