# Vulcan Agent — instalação Windows

## Compatibilidade e estado

O mesmo binário `amd64` atende Workstation, Server e Collector em Windows 10/11 e
Windows Server 2016–2025. A entrega `0.2.0` foi compilada para Windows, teve o CLI executado
via Wine e o MSI foi inspecionado estruturalmente. A instalação e o ciclo do Windows Service
Manager ainda precisam ser homologados em uma VM Windows antes de distribuição ampla.

O pacote ainda não possui assinatura Authenticode. Não distribua como release de produção
até configurar o certificado de code signing e verificar a assinatura no pipeline.

## Instalação interativa

1. No Vulcan, abra **Agentes > Instalação**.
2. Escolha o perfil e gere um token de uma hora e uso único.
3. Baixe `VulcanAgent-Windows-x64.msi`.
4. Execute em um PowerShell elevado:

```powershell
msiexec.exe /i .\VulcanAgent-Windows-x64.msi /qn /norestart `
  VULCAN_SERVER="https://vulcan.exemplo.com" `
  ENROLLMENT_TOKEN="TOKEN_DE_CURTA_DURACAO" `
  AGENT_PROFILE="workstation" `
  /l*v "$env:TEMP\VulcanAgent-install.log"
```

O site, setor e tags vêm do token criado pelo servidor. O token bruto não é salvo no MSI,
no banco ou na configuração final do agente.

## Caminhos e serviço

- binário: `C:\Program Files\Vulcan\Agent\VulcanAgent.exe`;
- identidade, política, fila: `C:\ProgramData\Vulcan\Agent\data`;
- configuração: `C:\ProgramData\Vulcan\Agent\config.json`;
- logs: `C:\ProgramData\Vulcan\Agent\logs\agent.jsonl`;
- serviço: `VulcanAgent`;
- conta: `NT AUTHORITY\LocalService`;
- inicialização: automática;
- recuperação: configurável pelo script `Deploy-VulcanAgent.ps1`.

O instalador restringe a ACL de `ProgramData` a LocalService, SYSTEM e Administradores. A
chave privada nunca sai da máquina.

## Instalação com script

```powershell
.\Deploy-VulcanAgent.ps1 `
  -MsiPath .\VulcanAgent-Windows-x64.msi `
  -VulcanServer "https://vulcan.exemplo.com" `
  -EnrollmentToken "TOKEN_DE_CURTA_DURACAO" `
  -AgentProfile workstation
```

O script usa `msiexec`, aceita códigos `0` e `3010`, executa `status` e configura três
tentativas de recuperação do serviço.

## Diagnóstico

```powershell
& "$env:ProgramFiles\Vulcan\Agent\VulcanAgent.exe" status
& "$env:ProgramFiles\Vulcan\Agent\VulcanAgent.exe" health
& "$env:ProgramFiles\Vulcan\Agent\VulcanAgent.exe" diagnostics
& "$env:ProgramFiles\Vulcan\Agent\VulcanAgent.exe" policy
& "$env:ProgramFiles\Vulcan\Agent\VulcanAgent.exe" logs --lines 200
Get-Service VulcanAgent
```

As saídas omitem token e chave privada.

## Reparo, upgrade e remoção

```powershell
msiexec.exe /fa .\VulcanAgent-Windows-x64.msi /qn
msiexec.exe /i .\VulcanAgent-Windows-x64.msi /qn /norestart
msiexec.exe /x .\VulcanAgent-Windows-x64.msi /qn /norestart
```

Antes de uma remoção definitiva, use `vulcan-agent unenroll --reason "motivo auditável"`
enquanto a identidade ainda pode autenticar. Dados locais não devem ser removidos sem a
política de retenção e o procedimento de evidência aplicáveis.

## Rede, proxy e certificado

O agente inicia apenas conexões HTTPS de saída para o Vulcan, normalmente TCP 443. Não é
necessária porta de entrada para Workstation ou Server. O certificado deve ser válido para
o hostname configurado; HTTP só é permitido em loopback com a flag explícita de
desenvolvimento. Proxy autenticado específico do agente ainda não está implementado.
