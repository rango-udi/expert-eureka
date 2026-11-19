# Shared engine policy and probes.
function Read-EngineInfo {
    param([string]$Format)
    $probe = Invoke-DockerConsole -Arguments @('info','--format',$Format) -QuietLabel 'Check Docker Engine' -CaptureResult
    if ($probe.ExitCode -ne 0) { Stop-Cmdc 'Docker Engine information is unavailable. Start Docker Desktop and retry cmdc.cmd doctor.' }
    return $probe.Stdout.Trim()
}
function Test-Preflight {
    $total = Read-EngineInfo '{{.MemTotal}}'
    [long]$totalBytes = 0
    if (-not [long]::TryParse([string]$total, [ref]$totalBytes) -or $totalBytes -le 0) {
        Stop-Cmdc 'Docker returned an unreadable RAM size. No image preparation was started. Retry cmdc.cmd doctor after restarting Docker.'
    }
    $policyPath = Join-Path $RepositoryRoot 'config/host-memory.env'
    if (-not (Test-Path -LiteralPath $policyPath -PathType Leaf)) { Stop-Cmdc 'Memory policy is missing. Restore config/host-memory.env.' }
    $policy = @{}
    foreach ($line in Get-Content -LiteralPath $policyPath) {
        if ($line -match '^\s*(#|$)') { continue }
        if ($line -notmatch '^(HOST_MEMORY_TARGET_MIB|HOST_MEMORY_TOLERANCE_MIB)=([0-9]+)$') {
            Stop-Cmdc 'Invalid memory policy. Keep one whole-number value per key in config/host-memory.env.'
        }
        $key = $Matches[1]
        $value = $Matches[2]
        if ($policy.ContainsKey($key)) { Stop-Cmdc 'Duplicate memory policy key. Keep one value per key in config/host-memory.env.' }
        $policy[$key] = $value
    }
    if (-not $policy.ContainsKey('HOST_MEMORY_TARGET_MIB') -or -not $policy.ContainsKey('HOST_MEMORY_TOLERANCE_MIB')) {
        Stop-Cmdc 'Memory policy needs HOST_MEMORY_TARGET_MIB and HOST_MEMORY_TOLERANCE_MIB.'
    }
    $target = if ($env:HOST_MEMORY_TARGET_MIB) { $env:HOST_MEMORY_TARGET_MIB } elseif ($env:HOST_MEMORY_MAX_MIB) { $env:HOST_MEMORY_MAX_MIB } else { $policy['HOST_MEMORY_TARGET_MIB'] }
    $tolerance = if ($env:HOST_MEMORY_TOLERANCE_MIB) { $env:HOST_MEMORY_TOLERANCE_MIB } else { $policy['HOST_MEMORY_TOLERANCE_MIB'] }
    foreach ($value in @($target, $tolerance)) {
        if ($value -notmatch '^(0|[1-9][0-9]{0,6})$' -or [long]$value -gt 1048576) {
            Stop-Cmdc 'Memory target and tolerance must be whole numbers within 0..1048576 MiB, without leading zeros.'
        }
    }
    if ([long]$target -le 0) { Stop-Cmdc 'HOST_MEMORY_TARGET_MIB must be positive.' }
    $ceiling = [long]$target + [long]$tolerance
    $reported = [math]::Ceiling($totalBytes / 1048576)
    Write-Output "Engine reports $reported MiB. Memory policy: target $target MiB; upward tolerance $tolerance MiB; accepted maximum $ceiling MiB."
    if ($totalBytes -gt ($ceiling * 1048576)) {
        Stop-Cmdc "Image preparation blocked: Docker Engine reports $reported MiB; the accepted maximum is $ceiling MiB (target $target MiB + tolerance $tolerance MiB).`nNo image preparation was started.`nNext step: run cmdc.cmd wsl-vm-limit-help. Adjust the VM limit or the project memory policy, restart Docker if its VM settings changed, then retry."
    }
    if ($totalBytes -lt ([long]$target * 1048576)) {
        Write-TerminalMessage WARNING "Engine RAM is below the nominal target ($reported MiB available; target $target MiB). Preparation may continue; check workload memory if it fails."
    }
}
