param(
  [switch]$NoElevationPrompt
)

$ErrorActionPreference = "Stop"
$SetupPath = "C:\Program Files\Vulcan\Agent\VulcanAgentCtl.exe"
if (-not (Test-Path $SetupPath)) {
  $SetupPath = "C:\Program Files\Vulcan\Agent\VulcanAgent.exe"
}

if ($NoElevationPrompt) {
  & $SetupPath repair
  exit $LASTEXITCODE
}

$process = Start-Process -FilePath $SetupPath -ArgumentList @("repair") -Verb RunAs -Wait -PassThru
exit $process.ExitCode
