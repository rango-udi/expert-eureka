# Orchestrate Docker directly from Windows PowerShell; no Python or WSL required.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$RepositoryRoot=[IO.Path]::GetFullPath((Join-Path $Root '../..'))
Set-Location -LiteralPath $Root
$env:COMPOSE_PARALLEL_LIMIT = '1'
$Command = if ($args.Count) { $args[0] } else { 'help' }
$Options = @($args | Select-Object -Skip 1)
function Stop-Cmdc {
    param([string]$Message, [int]$ExitCode = 2)
    $failure = [System.Exception]::new($Message)
    $failure.Data['UserFacing'] = $true
    $failure.Data['ExitCode'] = $ExitCode
    throw $failure
}
function Invoke-Compose {
    $arguments = @('compose','--project-name','robot-web-wowy','--project-directory',$Root,'-f',(Join-Path $Root 'compose.yaml')) + $args
    $label = Get-StageLabel -Arguments $args
    if ($label) { Write-TerminalMessage RUN $label }
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $quiet = if ($label -in @('Initialize database and store data','Start Wowy and wait for readiness','Stop application','Remove project containers and network')) { $label } else { '' }
    if ($label -in @('Validate application','Generate test cases','Run browser tests')) {
        $code = Invoke-DockerLive -Arguments $arguments -Label $label
    } else {
        if ($label -in @('Validate application','Generate test cases','Run browser tests')) {
        $code = Invoke-DockerLive -Arguments $arguments -Label $label
    } else { $code = Invoke-DockerConsole -Arguments $arguments -QuietLabel $quiet }
    }
    $timer.Stop()
    if ($code -ne 0) {
        if ($label) { Write-TerminalMessage ERROR "$label (exit $code)" }
        $recovery = if ($args -contains 'build') { 'Build failed. Review Docker build output or docker buildx history logs.' }
            elseif ($args -contains 'run' -and $args -contains 'tools') { 'Maintenance failed. Read the diagnostic file printed above and apps/wowy/.runtime/django-<step>.log for initialization failures. Correct source/configuration, then rerun setup --app wowy; keep .env and data.' }
            elseif ($args -contains 'run' -and $args -contains 'robot') { 'Browser tests failed. Review the diagnostic output and apps/wowy/reports.' }
            elseif ($args -contains 'up') { 'Startup failed. Run cmdc.cmd status --app wowy and cmdc.cmd logs --app wowy.' }
            else { 'Check Docker availability with cmdc.cmd doctor, then inspect cmdc.cmd status --app wowy.' }
        Stop-Cmdc ("Docker could not complete this step (exit $code).`nNext step: " + $recovery) $code
    }
    if ($label) { Write-TerminalMessage OK ("$label ({0:0.0}s)" -f $timer.Elapsed.TotalSeconds) }
}
function Build-App { Test-Preflight; Invoke-Compose build tools }
function Build-Robot { Test-Preflight; Invoke-Compose build robot }
function Test-AppImage {
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker image inspect robot-web-wowy-app:3.9.2 *> $null
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    if ($code -ne 0) { Stop-Cmdc 'Application image is missing. Run cmdc setup --app wowy. No image was pulled automatically.' }
}
function Invoke-Tool { Test-AppImage; Invoke-Compose run --rm --no-deps --pull never tools @args }
function Start-Wowy {
    Test-AppImage
    if (-not (Test-Path (Join-Path $Root '.env') -PathType Leaf) -or -not (Test-Path (Join-Path $Root '.runtime/data/db.sqlite3') -PathType Leaf)) { Stop-Cmdc 'Wowy is not initialized. Run cmdc setup --app wowy.' }
    foreach ($relative in @('.env','.runtime/data')) {
        if ((Get-Item (Join-Path $Root $relative) -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { Stop-Cmdc 'Wowy environment/data paths must not be filesystem links.' }
    }
    Invoke-Compose up -d --no-build --pull never --wait wowy
    Invoke-Compose port wowy 8000
}
try {
    if ($env:CMDC_GUARDED_APP -ne 'wowy') { Stop-Cmdc 'Use root cmdc with --app wowy.' }
    . (Join-Path $RepositoryRoot 'scripts/terminal.ps1')
    . (Join-Path $RepositoryRoot 'scripts/memory_policy.ps1')
    Initialize-Terminal
    if ($Command -in @('help', '--help', '-h')) {
        Write-Output @'
Wowy Web Tests - Docker only
setup [--with-robot] [--run-tests] | init | start | up | restart | stop | down
robot-init | robot [Robot options...] | validate | generate | manage <command...>
env [init|show] | config | status | urls | resources | logs
backup <name> | restore <name> --yes | reset <scope> --yes
destroy --yes [--include-files] | source | versions
CMDC_UI=auto|rich|plain controls terminal display. NO_COLOR disables colors.
Engine target and upward tolerance: ../../config/host-memory.env; terminal variables override project values.
'@
        exit 0
    }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Stop-Cmdc 'Docker CLI is missing. Install and start Docker with Compose.' }
    Invoke-Compose version
    $osType = Read-EngineInfo '{{.OSType}}'
    if ($osType -ne 'linux') { Stop-Cmdc 'Switch Docker to Linux containers.' }
    switch ($Command) {
        'config' { Invoke-Compose config; exit 0 }
        'status' { Invoke-Compose ps; exit 0 }
        'urls' {
            $probe=Invoke-DockerConsole -Arguments @('compose','--project-name','robot-web-wowy','--project-directory',$Root,'-f',(Join-Path $Root 'compose.yaml'),'port','wowy','8000') -CaptureResult
            if ($probe.ExitCode -ne 0) { Stop-Cmdc 'No Wowy address is available. Run status --app wowy.' }
            $address=$probe.Stdout.Trim()
            Write-Output "Storefront: http://$address/"
            Write-Output "Administration: http://$address/users/admin/"
            exit 0
        }
        'resources' { Invoke-Compose stats --no-stream; exit 0 }
        'logs' { Invoke-Compose logs --tail 100 wowy; exit 0 }
        'stop' { Invoke-Compose stop; exit 0 }
        'down' { Invoke-Compose --profile '*' down --remove-orphans; exit 0 }
    }
    New-Item -ItemType Directory -Force (Join-Path $Root '.runtime') | Out-Null
    $lock = Join-Path $Root '.runtime/launcher.lock'
    try { New-Item -ItemType Directory -ErrorAction Stop $lock | Out-Null }
    catch { Stop-Cmdc 'Another launcher is running. If a previous terminal crashed, verify no cmdc operation is active before removing .runtime/launcher.lock.' }
    try {
        switch ($Command) {
            { $_ -in @('setup', 'bootstrap') } {
                Write-TerminalMessage INFO "Robot Web Tests | wowy | $Command"
                foreach ($option in $Options) { if ($option -notin @('--with-robot', '--run-tests')) { Stop-Cmdc "Unknown setup option: $option" } }
                Build-App
                Invoke-Compose stop wowy
                Invoke-Tool init
                if ($Options -contains '--with-robot' -or $Options -contains '--run-tests') { Build-Robot }
                Start-Wowy
                if ($Options -contains '--run-tests') { Invoke-Compose run --rm --no-deps --pull never robot }
            }
            { $_ -in @('start', 'up') } { Start-Wowy }
            'restart' { Invoke-Compose stop wowy; Start-Wowy }
            'robot-init' { Build-Robot }
            'robot' {
                Build-Robot
                if ($Options -notcontains '--dryrun') { Start-Wowy }
                Invoke-Compose run --rm --no-deps --pull never robot @Options
            }
            { $_ -in @('init', 'backup', 'restore', 'reset', 'manage') } {
                Invoke-Compose stop wowy
                Invoke-Tool $Command @Options
            }
            'destroy' {
                foreach ($option in $Options) { if ($option -notin @('--yes', '--include-files')) { Stop-Cmdc "Unknown destroy option: $option" } }
                if ($Options -notcontains '--yes') { Stop-Cmdc 'Use destroy --yes to remove project data.' }
                Invoke-Compose --profile '*' down --remove-orphans
                Invoke-Tool destroy @Options
                Invoke-Compose --profile '*' down --remove-orphans --rmi all
            }
            'env' { Build-App; Invoke-Tool env @Options }
            { $_ -in @('validate', 'generate', 'source', 'versions') } { Invoke-Tool $Command @Options }
            default { Stop-Cmdc "Unknown command: $Command. Run cmdc help." }
        }
    } finally { Remove-Item -LiteralPath $lock -ErrorAction SilentlyContinue }
} catch {
    $failure = $_.Exception
    $code = 2
    if ($failure.Data['UserFacing']) {
        Write-TerminalMessage ERROR $failure.Message
        $code = [int]$failure.Data['ExitCode']
    } else {
        [Console]::Error.WriteLine('ERROR: The operation could not finish. Check that the project folder is writable and Docker Desktop is running.')
        [Console]::Error.WriteLine('Next step: run cmdc.cmd doctor. For VM memory settings, run cmdc.cmd wsl-vm-limit-help.')
        try {
            New-Item -ItemType Directory -Force (Join-Path $Root '.runtime') | Out-Null
            $failure.ToString() | Out-File -LiteralPath (Join-Path $Root '.runtime/launcher-errors.log') -Append -Encoding utf8
            [Console]::Error.WriteLine('Technical details: .runtime/launcher-errors.log')
        } catch {
            [Console]::Error.WriteLine('A diagnostic file could not be written. Move the project to a writable folder and retry.')
        }
    }
    exit $code
}
