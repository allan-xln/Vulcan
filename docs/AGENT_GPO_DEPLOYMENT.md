# Vulcan Agent — implantação por GPO

O fluxo ERS usa o agente v2 assinado em sessão de usuário. A GPO inicia o agente somente
em Windows cliente; Windows Server é descartado pelo próprio script antes de qualquer
gravação local.

O agente coleta inventário e saúde do equipamento, aplicativo em foco, duração do contexto
e ociosidade. A política padrão mantém desligados título de janela, conteúdo digitado,
URL/histórico do navegador, tela, área de transferência, áudio e câmera.

## Pré-requisitos

- MSI `amd64` assinado e checksum conferido;
- URL do Vulcan acessível pela máquina; prefira HTTPS, ou use o consentimento explícito
  para o IP privado durante a fase temporária da ERS;
- token de enrollment curto, escopo/site/perfil corretos e quantidade de usos compatível;
- piloto concluído em Windows 10/11 e nas versões de Windows Server usadas;
- política do agente criada e revisada no Vulcan;
- janela de mudança e rollback aprovados.

## Disparo ERS

A senha do AD nunca entra na linha de comando. Grave-a em um arquivo local com permissão
`600` e use um token de enrollment temporário, com aprovação automática e limite de usos
compatível com as estações ativas:

```bash
chmod 600 /caminho/credencial-ad /caminho/enrollment.token
ERS_WINRM_USER='ERSTRANSPORTES.LOCAL\\administrador' \
ERS_WINRM_PASSWORD_FILE='/caminho/credencial-ad' \
.venv/bin/python scripts/deploy_ers_agent_gpo.py \
  --token-file /caminho/enrollment.token
```

Sem `--confirm-deploy`, o comando apenas valida AD, módulos e quantidade de estações.
Depois da conferência, repita com `--confirm-deploy`. O disparo:

- publica binário, script e token curto em `SYSVOL`;
- valida o SHA-256 do binário após a cópia;
- cria/vincula `Vulcan Agent - Estacoes ERS` no domínio;
- configura o início no logon de cada usuário;
- agenda a exclusão do token do `SYSVOL` em até 36 horas;
- ignora controladores e demais Windows Server.

## Alternativa: MSI por computador

Mantenha o MSI em um compartilhamento somente leitura para computadores e use um script de
startup equivalente:

```powershell
$arguments = @(
  '/i', '\\servidor\software\VulcanAgent-Windows-x64.msi',
  '/qn', '/norestart',
  'VULCAN_SERVER="https://vulcan.exemplo.com"',
  'ENROLLMENT_TOKEN="TOKEN_DE_CURTA_DURACAO"',
  'AGENT_PROFILE="workstation"',
  '/l*v', 'C:\Windows\Temp\VulcanAgent-install.log'
)
$process = Start-Process msiexec.exe -ArgumentList $arguments -Wait -PassThru
if ($process.ExitCode -notin 0, 3010) { exit $process.ExitCode }
```

Use tokens diferentes por lote ou tokens limitados ao número exato de máquinas. Nunca
grave token permanente em SYSVOL.

## MSI assignment

O MSI suporta atribuição por computador, mas propriedades de enrollment precisam chegar de
forma segura. Evite transform (`.mst`) que contenha token reutilizável. Prefira pré-registro
e token curto entregue no startup script por mecanismo protegido.

## Atualização

O `UpgradeCode` é estável e `MajorUpgrade` impede downgrade. Faça anéis: TI, piloto,
10%, 50%, 100%. O auto-update do agente ainda está desabilitado; upgrades são conduzidos
pelo MSI até a cadeia de assinatura e rollback automático ser homologada.

## Validação

```powershell
Get-Service VulcanAgent
& "$env:ProgramFiles\Vulcan\Agent\VulcanAgent.exe" health
Get-Content "$env:ProgramData\Vulcan\Agent\logs\agent.jsonl" -Tail 50
```

Confirme no Vulcan: tenant, perfil, site, política aplicada, última comunicação, fila e
eventos reais na timeline.

## Remoção e rollback

Revogue a identidade antes da remoção sempre que possível. Para rollback, desinstale o MSI
novo e reinstale o release assinado anterior somente se a política permitir. Não reutilize
o token original.

## Firewall e proxy

Libere apenas a saída para o endpoint Vulcan aprovado. Na ERS temporária, isso significa
TCP 8099 para `192.168.200.4`; não abra NATS, PostgreSQL ou portas de administração para
estações. Proxy autenticado específico ainda é uma limitação conhecida.
