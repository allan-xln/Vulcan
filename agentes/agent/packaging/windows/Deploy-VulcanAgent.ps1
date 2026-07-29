[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string]$MsiPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https?://')]
    [string]$VulcanServer,

    [Parameter(Mandatory = $true)]
    [string]$EnrollmentToken,

    [ValidateSet('workstation', 'server', 'collector')]
    [string]$AgentProfile = 'workstation',

    [string]$Site = '',

    [switch]$AllowInsecurePrivateNetwork,

    [string]$LogPath = "$env:ProgramData\Vulcan\Agent\install.log"
)

$ErrorActionPreference = 'Stop'
$serverUri = [System.Uri]$VulcanServer
if ($serverUri.Scheme -eq 'http') {
    $address = $null
    $isIpAddress = [System.Net.IPAddress]::TryParse($serverUri.Host, [ref]$address)
    $bytes = if ($isIpAddress) { $address.GetAddressBytes() } else { @() }
    $isPrivate = $bytes.Count -eq 4 -and (
        $bytes[0] -eq 10 -or
        ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
        ($bytes[0] -eq 192 -and $bytes[1] -eq 168)
    )
    if (-not $AllowInsecurePrivateNetwork -or -not $isPrivate) {
        throw 'HTTP exige -AllowInsecurePrivateNetwork e um endereço IPv4 privado. Prefira HTTPS.'
    }
}
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
    "ALLOW_INSECURE_PRIVATE_NETWORK=$($AllowInsecurePrivateNetwork.IsPresent.ToString().ToLowerInvariant())"
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
