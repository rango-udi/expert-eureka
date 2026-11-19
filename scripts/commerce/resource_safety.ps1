# Explicit consent and a host-memory reserve precede heavy Native commerce work.
function Confirm-CommerceRisk {
    param([string]$Command,[bool]$Accepted,[string]$Application)
    if ($Command -notin @('setup','bootstrap','start','up','restart','init','robot-init','robot','pull','source','env','manage','backup','restore','validate','generate')) { return }
    Write-TerminalMessage WARNING 'Native commerce starts several services and may exhaust host RAM or saturate disk during pull, unpack, migration and startup. Container ceilings and WSL cache reclaim do not guarantee host stability.'
    Write-TerminalMessage WARNING 'Review documents/guides/NATIVE_COMMERCE.md. Stop other workloads and check the active VM limit before continuing.'
    $policy=Join-Path $Root 'config/commerce-safety.env'
    if (-not (Test-Path -LiteralPath $policy -PathType Leaf)) { Stop-Cmdc 'Native commerce safety policy is missing. Restore config/commerce-safety.env.' }
    $minimum=$null
    foreach ($line in Get-Content -LiteralPath $policy) {
        if ($line -match '^\s*(#|$)') { continue }
        if ($line -notmatch '^HOST_FREE_MEMORY_MIN_MIB=([1-9][0-9]{0,6})$' -or $null -ne $minimum) { Stop-Cmdc 'Invalid Native commerce safety policy. Set one positive HOST_FREE_MEMORY_MIN_MIB value.' }
        $minimum=[long]$Matches[1]
    }
    if ($null -eq $minimum -or $minimum -lt 1 -or $minimum -gt 1048576) { Stop-Cmdc 'HOST_FREE_MEMORY_MIN_MIB must be within 1..1048576.' }
    try { $system=Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop; $available=[math]::Floor([long]$system.FreePhysicalMemory/1024) }
    catch { Stop-Cmdc 'Windows free physical RAM could not be read. Check CIM access before retrying; no Docker operation was started.' }
    Write-TerminalMessage INFO "Windows available RAM: $available MiB; stop threshold: $minimum MiB. This is not a workload fit guarantee."
    if ($available -lt $minimum) { Stop-Cmdc 'Not enough host RAM reserve for Native commerce. Free memory or choose another app; the risk acknowledgement does not bypass this check.' }
    if (-not $Accepted) {
        if ($env:CI -or [Console]::IsInputRedirected -or [Console]::IsErrorRedirected) { Stop-Cmdc 'Native commerce requires explicit confirmation. Review the resource warning, then add --accept-resource-risk for this operation. No Docker operation was started.' }
        if ((Read-Host "Type $Application to continue this operation, or press Enter to cancel") -cne $Application) { Stop-Cmdc 'Native commerce operation cancelled. No Docker operation was started.' }
    }
}
