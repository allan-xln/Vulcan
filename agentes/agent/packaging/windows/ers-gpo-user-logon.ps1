[CmdletBinding()]
param(
    [string]$BackendUrl = "http://192.168.200.26:8099/api",
    [string]$AgentSource = (Join-Path $PSScriptRoot "VulcanAgentUser.exe"),
    [string]$EnrollmentTokenFile = (Join-Path $PSScriptRoot "enrollment.token")
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$operatingSystem = Get-CimInstance Win32_OperatingSystem
if ([int]$operatingSystem.ProductType -ne 1) {
    exit 0
}

$root = Join-Path $env:LOCALAPPDATA "Vulcan\Agent"
$bin = Join-Path $root "bin"
$logs = Join-Path $root "logs"
$agent = Join-Path $bin "VulcanAgentUser.exe"
$runner = Join-Path $bin "Run-VulcanAgent.ps1"
$log = Join-Path $logs "gpo-logon.log"
$scope = "$env:USERDOMAIN\$env:USERNAME"

New-Item -ItemType Directory -Force -Path $bin, $logs | Out-Null

function Write-DeploymentLog {
    param([string]$Message)
    Add-Content -Path $log -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
}

try {
    if (-not (Test-Path -LiteralPath $AgentSource)) {
        throw "Pacote do agente não encontrado."
    }

    $replaceAgent = -not (Test-Path -LiteralPath $agent)
    if (-not $replaceAgent) {
        $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $AgentSource).Hash
        $installedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $agent).Hash
        $replaceAgent = $sourceHash -ne $installedHash
    }
    if ($replaceAgent) {
        Copy-Item -LiteralPath $AgentSource -Destination $agent -Force
        Write-DeploymentLog "Binário atualizado."
    }

    $env:VULCAN_AGENT_ROOT = $root
    $env:VULCAN_AGENT_SCOPE = $scope
    $env:VULCAN_AGENT_DEPLOYMENT = "ers-gpo-user"

    $config = Join-Path $root "config.json"
    if (-not (Test-Path -LiteralPath $config)) {
        if (-not (Test-Path -LiteralPath $EnrollmentTokenFile)) {
            throw "Token temporário de enrollment indisponível."
        }
        & $agent enroll `
            --server $BackendUrl `
            --token-file $EnrollmentTokenFile `
            --profile workstation `
            --allow-insecure-private-network
        if ($LASTEXITCODE -ne 0) {
            throw "Enrollment falhou com código $LASTEXITCODE."
        }
        Write-DeploymentLog "Enrollment concluído para $scope."
    }

    @'
param(
    [Parameter(Mandatory = $true)][string]$AgentPath,
    [Parameter(Mandatory = $true)][string]$AgentRoot,
    [Parameter(Mandatory = $true)][string]$AgentScope
)
$env:VULCAN_AGENT_ROOT = $AgentRoot
$env:VULCAN_AGENT_SCOPE = $AgentScope
$env:VULCAN_AGENT_DEPLOYMENT = "ers-gpo-user"
$sha = [Security.Cryptography.SHA256]::Create()
try {
    $scopeHash = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($AgentScope)))).Replace('-', '')
} finally {
    $sha.Dispose()
}
$mutexName = "Local\VulcanAgentUser-" + $scopeHash.Substring(0, 16)
$mutex = [Threading.Mutex]::new($false, $mutexName)
try {
    if (-not $mutex.WaitOne(0)) { exit 0 }
    & $AgentPath run
} finally {
    try { $mutex.ReleaseMutex() } catch {}
    $mutex.Dispose()
}
'@ | Set-Content -LiteralPath $runner -Encoding UTF8

    $running = Get-CimInstance Win32_Process -Filter "Name = 'VulcanAgentUser.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -eq $agent -and $_.CommandLine -match '\brun\b' }
    if (-not $running) {
        $arguments = @(
            '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
            '-WindowStyle', 'Hidden', '-File', "`"$runner`"",
            '-AgentPath', "`"$agent`"", '-AgentRoot', "`"$root`"", '-AgentScope', "`"$scope`""
        )
        Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WindowStyle Hidden
        Write-DeploymentLog "Agente iniciado para $scope."
    }
    exit 0
} catch {
    Write-DeploymentLog "Falha: $($_.Exception.Message)"
    exit 1
}
