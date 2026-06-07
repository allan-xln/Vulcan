param(
  [switch]$PurgeData,
  [switch]$NoElevationPrompt
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SetupPath = Join-Path $ScriptRoot "..\..\installers\windows\VulcanAgentSetup.exe"
if (-not (Test-Path $SetupPath)) {
  $SetupPath = Join-Path $ScriptRoot "VulcanAgentSetup.exe"
}
if (-not (Test-Path $SetupPath)) {
  $SetupPath = "C:\Program Files\Vulcan\Agent\VulcanAgentCtl.exe"
}
if (-not (Test-Path $SetupPath)) {
  $SetupPath = "C:\Program Files\Vulcan\Agent\VulcanAgent.exe"
}

$agentArgs = @("uninstall")
if ($PurgeData) {
  $agentArgs += "-PurgeData"
}

if ($NoElevationPrompt) {
  & $SetupPath @agentArgs
  exit $LASTEXITCODE
}

$process = Start-Process -FilePath $SetupPath -ArgumentList $agentArgs -Verb RunAs -Wait -PassThru
exit $process.ExitCode
