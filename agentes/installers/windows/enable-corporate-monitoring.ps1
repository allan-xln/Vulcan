param(
  [string]$ConfigPath = "C:\ProgramData\Vulcan\Agent\config\agent.json"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ConfigPath)) {
  throw "Config not found: $ConfigPath"
}

$backup = "$ConfigPath.bak-$(Get-Date -Format yyyyMMddHHmmss)"
Copy-Item -Path $ConfigPath -Destination $backup -Force

$config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
if (-not $config.policy) {
  $config | Add-Member -MemberType NoteProperty -Name policy -Value ([pscustomobject]@{})
}

$policy = $config.policy
$policy | Add-Member -Force -MemberType NoteProperty -Name collectAppName -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name collectWindowTitle -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name collectIdleTime -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name collectSessionEvents -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name collectBrowserDomain -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name collectBrowserUrl -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name collectBrowserHistory -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name collectBrowserPageTitle -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name collectProcessList -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name collectSystemMetrics -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name redactSensitiveTerms -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name browserHistoryIntervalSeconds -Value 300
$policy | Add-Member -Force -MemberType NoteProperty -Name browserHistoryLookbackMinutes -Value 120
$policy | Add-Member -Force -MemberType NoteProperty -Name browserHistoryMaxEvents -Value 100
$policy | Add-Member -Force -MemberType NoteProperty -Name syncIntervalSeconds -Value 30
$policy | Add-Member -Force -MemberType NoteProperty -Name heartbeatIntervalSeconds -Value 60
$policy | Add-Member -Force -MemberType NoteProperty -Name offlineQueueEnabled -Value $true
$policy | Add-Member -Force -MemberType NoteProperty -Name maxOfflineQueueSize -Value 10000
$policy | Add-Member -Force -MemberType NoteProperty -Name allowUserPause -Value $false
$policy | Add-Member -Force -MemberType NoteProperty -Name showTrayStatus -Value $false
$policy | Add-Member -Force -MemberType NoteProperty -Name privacyMode -Value "corporate"
$policy | Add-Member -Force -MemberType NoteProperty -Name idleThresholdSeconds -Value 300

$config | Add-Member -Force -MemberType NoteProperty -Name collectWindowTitle -Value $true
$config | ConvertTo-Json -Depth 20 | Set-Content -Path $ConfigPath -Encoding UTF8

Restart-Service VulcanAgent -ErrorAction SilentlyContinue
schtasks.exe /Run /TN "Vulcan Session Collector" | Out-Null
schtasks.exe /Delete /TN "Vulcan Tray" /F 2>$null | Out-Null

Write-Host "Vulcan Windows Agent corporate background monitoring enabled."
Write-Host "Backup: $backup"
