param(
  [Parameter(Mandatory = $true)]
  [string]$TenantId,

  [string]$BackendUrl = "http://localhost:3001",

  [Parameter(Mandatory = $true)]
  [string]$EnrollmentToken,

  [string]$LinkedUser = "$env:USERDOMAIN\$env:USERNAME",
  [string]$UserId = "",
  [string]$MembershipId = "",
  [string]$RoleLevel = "Operador",
  [string]$Department = "",
  [string]$ManagerMembershipId = "",
  [string]$Note = "",
  [switch]$CollectWindowTitle,
  [switch]$NoElevationPrompt
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SetupPath = Join-Path $ScriptRoot "..\..\installers\windows\VulcanAgentSetup.exe"
if (-not (Test-Path $SetupPath)) {
  $SetupPath = Join-Path $ScriptRoot "VulcanAgentSetup.exe"
}
if (-not (Test-Path $SetupPath)) {
  throw "VulcanAgentSetup.exe not found. Run ./agentes/windows/build.sh first or use the packaged zip."
}

$agentArgs = @(
  "install",
  "-TenantId", $TenantId,
  "-BackendUrl", $BackendUrl,
  "-EnrollmentToken", $EnrollmentToken,
  "-LinkedUser", $LinkedUser,
  "-UserId", $UserId,
  "-MembershipId", $MembershipId,
  "-RoleLevel", $RoleLevel,
  "-Department", $Department,
  "-ManagerMembershipId", $ManagerMembershipId,
  "-Note", $Note
)

if ($CollectWindowTitle) {
  $agentArgs += "-CollectWindowTitle"
}

if ($NoElevationPrompt) {
  & $SetupPath @agentArgs
  exit $LASTEXITCODE
}

$process = Start-Process -FilePath $SetupPath -ArgumentList $agentArgs -Verb RunAs -Wait -PassThru
exit $process.ExitCode
