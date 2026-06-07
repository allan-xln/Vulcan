$ErrorActionPreference = "Stop"
$AgentPath = "C:\Program Files\Vulcan\Agent\VulcanAgentCtl.exe"
if (-not (Test-Path $AgentPath)) {
  $AgentPath = "C:\Program Files\Vulcan\Agent\VulcanAgent.exe"
}
if (-not (Test-Path $AgentPath)) {
  throw "Vulcan agent control binary not found at C:\Program Files\Vulcan\Agent"
}
& $AgentPath status
