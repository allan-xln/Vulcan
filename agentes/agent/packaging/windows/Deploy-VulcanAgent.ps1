[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string]$MsiPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$VulcanServer,

    [Parameter(Mandatory = $true)]
    [string]$EnrollmentToken,

    [ValidateSet('workstation', 'server', 'collector')]
    [string]$AgentProfile = 'workstation',

    [string]$Site = '',

    [string]$LogPath = "$env:ProgramData\Vulcan\Agent\install.log"
)

$ErrorActionPreference = 'Stop'
$resolvedMsi = (Resolve-Path -LiteralPath $MsiPath).Path
$logDirectory = Split-Path -Parent $LogPath
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

$arguments = @(
    '/i'
    "`"$resolvedMsi`""
    '/qn'
    '/norestart'
    "VULCAN_SERVER=`"$VulcanServer`""
    "ENROLLMENT_TOKEN=`"$EnrollmentToken`""
    "AGENT_PROFILE=`"$AgentProfile`""
    "SITE=`"$Site`""
    '/l*v'
    "`"$LogPath`""
)

if ($PSCmdlet.ShouldProcess($env:COMPUTERNAME, 'Install Vulcan Agent')) {
    $process = Start-Process -FilePath 'msiexec.exe' -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -notin @(0, 3010)) {
        throw "Vulcan Agent MSI failed with exit code $($process.ExitCode)."
    }

    & "$env:ProgramFiles\Vulcan\Agent\VulcanAgent.exe" status
    sc.exe failure VulcanAgent reset= 86400 actions= restart/5000/restart/15000/restart/60000 | Out-Null
}
