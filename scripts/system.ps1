# Global diagnostics and help share no application configuration.
$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $PSScriptRoot
$RepositoryRoot=$Root
function Stop-Cmdc {
    param([string]$Message,[int]$ExitCode=2)
    $errorValue=[Exception]::new($Message)
    $errorValue.Data['ExitCode']=$ExitCode
    throw $errorValue
}
try {
    . (Join-Path $PSScriptRoot 'terminal.ps1')
    . (Join-Path $PSScriptRoot 'memory_policy.ps1')
    Initialize-Terminal
    $command=if ($args.Count) { $args[0] } else { 'doctor' }
    if ($args.Count -gt 1) { Stop-Cmdc 'Global commands do not accept application options.' }
    if ($command -eq 'wsl-vm-limit-help') {
        . (Join-Path $PSScriptRoot 'open_help.ps1')
        Open-WslMemoryHelp -ProjectRoot $Root
        exit 0
    }
    if ($command -ne 'doctor') { Stop-Cmdc 'Use doctor or wsl-vm-limit-help.' }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Stop-Cmdc 'Docker CLI is missing. Install and start Docker.' }
    if ((Read-EngineInfo '{{.OSType}}') -ne 'linux') { Stop-Cmdc 'Select Linux containers.' }
    $code=Invoke-DockerConsole -Arguments @('compose','version')
    if ($code -ne 0) { Stop-Cmdc 'Docker Compose is unavailable.' $code }
    Test-Preflight
    exit 0
} catch {
    [Console]::Error.WriteLine('[ERROR] '+$_.Exception.Message)
    $code=2
    if ($_.Exception.Data.Contains('ExitCode')) {$code=[int]$_.Exception.Data['ExitCode']}
    exit $code
}
