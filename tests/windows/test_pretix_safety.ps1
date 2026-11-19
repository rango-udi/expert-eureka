# Exercise consent and Windows RAM checks with isolated policies and CIM data, without Docker.
$ErrorActionPreference='Stop'
$RepositoryRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Root=Join-Path ([IO.Path]::GetTempPath()) ('robot-web-safety-'+[guid]::NewGuid().ToString('N'))
$savedCi=$env:CI
$script:FreeKiB=4096*1024
$script:CimReads=0
function Stop-Cmdc { param([string]$Message) throw $Message }
function Write-TerminalMessage { param([string]$Kind,[string]$Message) }
function Get-CimInstance {
    param([string]$ClassName,[string]$ErrorAction)
    $script:CimReads++
    return [pscustomobject]@{FreePhysicalMemory=$script:FreeKiB}
}
try {
    [void][IO.Directory]::CreateDirectory((Join-Path $Root 'config'))
    [IO.File]::WriteAllText((Join-Path $Root 'config/pretix-safety.env'),"HOST_FREE_MEMORY_MIN_MIB=1024`n")
    . (Join-Path $RepositoryRoot 'scripts/pretix_safety.ps1')
    $env:CI='1'
    $failure=''
    try { Confirm-PretixRisk -Command setup -Accepted $false } catch { $failure=$_.Exception.Message }
    if ($failure -notmatch 'explicit confirmation') { throw 'CI setup accepted missing consent.' }
    Confirm-PretixRisk -Command setup -Accepted $true
    $script:FreeKiB=512*1024;$failure=''
    try { Confirm-PretixRisk -Command start -Accepted $true } catch { $failure=$_.Exception.Message }
    if ($failure -notmatch 'Not enough host RAM') { throw 'Acknowledgement bypassed the host RAM stop threshold.' }
    $reads=$script:CimReads
    Remove-Item -LiteralPath (Join-Path $Root 'config/pretix-safety.env')
    foreach ($command in @('status','logs','resources','down','stop')) { Confirm-PretixRisk -Command $command -Accepted $false }
    if ($script:CimReads -ne $reads) { throw 'Diagnostic/cleanup commands unexpectedly required a RAM probe.' }
    Write-Output 'PASS: missing consent, accepted consent, low host RAM, and diagnostic/cleanup availability.'
} finally {
    $env:CI=$savedCi
    Remove-Item -LiteralPath $Root -Recurse -Force -ErrorAction SilentlyContinue
}
