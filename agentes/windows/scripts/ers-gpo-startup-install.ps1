$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

param(
  [string]$PackageUrl = "http://192.168.200.160:8099/VulcanAgent-Windows-x64.zip",
  [string]$BackendUrl = "http://192.168.200.160:3001",
  [string]$TenantId = "00000000-0000-0000-0000-000000000301",
  [string]$EnrollmentToken = "vulcan-local-enrollment-token",
  [string]$Department = "AutoAdocao",
  [string]$RoleLevel = "Operador"
)

$DeployRoot = Join-Path $env:ProgramData "Vulcan\Deploy"
$ZipPath = Join-Path $DeployRoot "VulcanAgent-Windows-x64.zip"
$ExtractPath = Join-Path $DeployRoot "package"
$LogPath = Join-Path $DeployRoot "ers-gpo-startup.log"

New-Item -ItemType Directory -Path $DeployRoot -Force | Out-Null

function Write-DeployLog {
  param([string]$Message)
  $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $LogPath -Value "[$stamp] $Message"
}

try {
  Write-DeployLog "startup install begin computer=$env:COMPUTERNAME user=$env:USERDOMAIN\$env:USERNAME"

  try {
    Invoke-WebRequest -Uri "$BackendUrl/health" -UseBasicParsing -TimeoutSec 10 | Out-Null
    Write-DeployLog "backend health ok backend=$BackendUrl"
  } catch {
    Write-DeployLog "backend health failed: $($_.Exception.Message)"
  }

  $service = Get-Service -Name VulcanAgent -ErrorAction SilentlyContinue
  if ($service -and $service.Status -ne "Running") {
    Start-Service -Name VulcanAgent
    Write-DeployLog "existing service started"
  }

  if (Test-Path $ExtractPath) {
    Remove-Item -Recurse -Force $ExtractPath
  }
  New-Item -ItemType Directory -Path $ExtractPath -Force | Out-Null

  Invoke-WebRequest -Uri $PackageUrl -OutFile $ZipPath -UseBasicParsing -TimeoutSec 120
  Expand-Archive -Path $ZipPath -DestinationPath $ExtractPath -Force

  $Installer = Join-Path $ExtractPath "install-gpo.cmd"
  if (-not (Test-Path $Installer)) {
    throw "install-gpo.cmd not found after extraction"
  }

  & $Installer `
    -TenantId $TenantId `
    -BackendUrl $BackendUrl `
    -EnrollmentToken $EnrollmentToken `
    -LinkedUser "$env:USERDOMAIN\$env:COMPUTERNAME`$" `
    -RoleLevel $RoleLevel `
    -Department $Department `
    -CorporateMonitoring

  $service = Get-Service -Name VulcanAgent -ErrorAction Stop
  if ($service.Status -ne "Running") {
    Start-Service -Name VulcanAgent
    $service = Get-Service -Name VulcanAgent -ErrorAction Stop
  }

  Write-DeployLog "startup install ok service=$($service.Status)"
  exit 0
} catch {
  Write-DeployLog "startup install failed: $($_.Exception.Message)"
  exit 1
}
