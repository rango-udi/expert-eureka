<#
.SYNOPSIS
Run the complete cmdc command set through native Windows Docker CLI.
.DESCRIPTION
Uses Windows PowerShell and Docker Desktop directly. No user Linux distribution,
WSL executable, host Python, or host Git is needed. Linux application tools run
inside Docker containers; the Desktop engine must therefore use Linux containers.
.INPUTS
Command-line arguments for cmdc; private project settings are read by containers.
.OUTPUTS
Streamed command output and the original failing process status, or status 2 for
invalid arguments and project configuration errors. No global Docker prune is used.
#>

function Stop-ProjectCommand {
    <# .SYNOPSIS Throw a readable error carrying the exit code for the outer driver. #>
    param([string] $Message, [int] $ExitCode = 2)
    $errorValue = New-Object System.InvalidOperationException($Message)
    $errorValue.Data['ExitCode'] = $ExitCode
    throw $errorValue
}

function New-ProjectContext {
    <#
    .SYNOPSIS Create isolated paths and constants for one command invocation.
    .PARAMETER ProjectRoot Application directory containing Compose and .env.template.
    .OUTPUTS A context object; no Docker command or filesystem mutation is performed.
    #>
    param([string] $ProjectRoot)
    return [pscustomobject]@{
        Root = [IO.Path]::GetFullPath($ProjectRoot)
        ProjectName = 'robot-web-pretix'
        DockerExecutable = $null
        BootstrapImage = 'python:3.12.8-alpine@sha256:ba13ef990f6e5d13014e9e8d04c02a8fdb0fe53d6dccf6e19147f316e6cc3a84'
        SourceCommit = '46bd2caea20dc1b97ebd02bcb802996f872e0c66'
    }
}

function ConvertTo-NativeArgument {
    <#
    .SYNOPSIS Quote one Windows native-process argument, including empty values.
    .PARAMETER Value Original argument, without shell evaluation or interpolation.
    .OUTPUTS A CRT-compatible quoted argument; backslashes before quotes and at the
    end are doubled. This is used only when ProcessStartInfo.ArgumentList is absent.
    #>
    param([AllowEmptyString()][string] $Value)
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

function Get-DockerExecutable {
    <# .SYNOPSIS Find native Docker CLI or explain how to make it available in PATH. #>
    foreach ($name in @('docker.exe', 'docker')) {
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command) { return $command.Source }
    }
    Stop-ProjectCommand 'Docker CLI was not found in Windows PATH. Start Docker Desktop and reopen this terminal, then retry cmdc doctor.'
}

function Invoke-DockerProcess {
    <#
    .SYNOPSIS Execute Docker with separate arguments and preserve the process status.
    .PARAMETER Context Project paths and native Docker executable.
    .PARAMETER Arguments Docker argument array; never passed through a shell string.
    .PARAMETER Capture Capture stdout/stderr for parsing or files; otherwise inherit
    the console streams so logs and interactive management commands remain usable.
    .OUTPUTS An object with ExitCode, Stdout, and Stderr; no process output is mixed
    into the function's returned object. Capture reads both streams asynchronously.
    #>
    param($Context, [string[]] $Arguments, [switch] $Capture)
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $Context.DockerExecutable
    $startInfo.WorkingDirectory = $Context.Root
    $startInfo.UseShellExecute = $false
    $startInfo.EnvironmentVariables['CMDC_HOST_PLATFORM'] = 'windows'
    if ($startInfo.PSObject.Properties['ArgumentList']) {
        foreach ($argument in $Arguments) { $startInfo.ArgumentList.Add([string] $argument) }
    }
    else {
        $startInfo.Arguments = (($Arguments | ForEach-Object { ConvertTo-NativeArgument -Value $_ }) -join ' ')
    }
    $startInfo.RedirectStandardOutput = $Capture.IsPresent
    $startInfo.RedirectStandardError = $Capture.IsPresent
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    try {
        [void] $process.Start()
        if ($Capture) {
            $stdoutTask = $process.StandardOutput.ReadToEndAsync()
            $stderrTask = $process.StandardError.ReadToEndAsync()
        }
        if ($Capture) {
            $frames = @('|','/','-','\')
            $frame = 0
            $waitTimer=[Diagnostics.Stopwatch]::StartNew()
            try {
                if ($script:RichTerminal) { [Console]::Error.Write("$([char]27)[?25l") }
                while (-not $process.WaitForExit(120)) {
                    if ($script:RichTerminal) { Write-WaitFrame -Glyph $frames[$frame % 4] -Label 'Checking pretix resources' -ElapsedSeconds $waitTimer.Elapsed.TotalSeconds; $frame++ }
                }
            } finally {
                if ($script:RichTerminal) { [Console]::Error.Write("`r$([char]27)[2K$([char]27)[?25h") }
            }
        } else { $process.WaitForExit() }
        $stdout = ''
        $stderr = ''
        if ($Capture) { $stdout = $stdoutTask.Result; $stderr = $stderrTask.Result }
        return [pscustomobject]@{ ExitCode = $process.ExitCode; Stdout = $stdout; Stderr = $stderr }
    }
    finally { $process.Dispose() }
}

function Invoke-Docker {
    <#
    .SYNOPSIS Run native Docker and turn failed steps into actionable driver errors.
    .PARAMETER AllowFailure Return a nonzero result for expected probes or cleanup.
    .OUTPUTS Captured process result when requested; otherwise no success-stream data.
    #>
    param($Context, [string[]] $Arguments, [switch] $Capture, [switch] $AllowFailure)
    $result = Invoke-DockerProcess -Context $Context -Arguments $Arguments -Capture:$Capture
    if ($result.ExitCode -ne 0 -and -not $AllowFailure) {
        if ($Capture) {
            $runtime=Join-Path $Context.Root '.runtime'
            [void][IO.Directory]::CreateDirectory($runtime)
            $log=Join-Path $runtime ('task-' + [guid]::NewGuid().ToString('N') + '.log')
            [IO.File]::WriteAllText($log,$result.Stdout + $result.Stderr)
            [Console]::Error.WriteLine('Diagnostic output: ' + $log)
        }
        $engine=Invoke-DockerProcess -Context $Context -Arguments @('info') -Capture
        if ($engine.ExitCode -ne 0) { Stop-ProjectCommand 'Docker Engine connection was lost. No later startup step was started. Recover Docker Desktop, inspect status/logs and follow documents/helps/PRETIX_RESOURCE_PRESSURE.md. Keep database and media volumes.' $result.ExitCode }
        if ($result.ExitCode -eq 137) {
            Stop-ProjectCommand 'The process was force-killed (exit 137), possibly by a memory limit. Check Docker OOM details and cmdc config --app pretix; inspect OOMKilled and the project/VM memory budget before retrying. Do not disable limits to bypass resource pressure.' 137
        }
        Stop-ProjectCommand "Docker could not complete this step (exit $($result.ExitCode)). Review its message; use cmdc status --app pretix and cmdc logs --app pretix <service> to investigate." $result.ExitCode
    }
    if ($Capture -or $AllowFailure) { return $result }
}

function Invoke-Compose {
    <#
    .SYNOPSIS Run Compose with the fixed project and optional digest override.
    .PARAMETER NoLock Ignore the existing override while resolving fresh digests.
    .OUTPUTS The requested process result or an error preserving Docker's exit code.
    #>
    param($Context, [string[]] $Arguments, [switch] $Capture, [switch] $AllowFailure, [switch] $NoLock)
    $prefix = @('compose', '--parallel', '1', '--project-name', $Context.ProjectName, '--env-file', '.env', '-f', 'compose.yaml')
    if (-not $NoLock -and (Test-Path -LiteralPath (Join-Path $Context.Root 'compose.lock.yaml'))) {
        $prefix += @('-f', 'compose.lock.yaml')
    }
    if (-not $NoLock -and (Test-Path -LiteralPath (Join-Path $Context.Root '.runtime/compose.resources.yaml'))) {
        $prefix += @('-f', '.runtime/compose.resources.yaml')
    }
    Invoke-Docker -Context $Context -Arguments ($prefix + $Arguments) -Capture:$Capture -AllowFailure:$AllowFailure
}

function Get-WindowsMemorySnapshot {
    <#
    .SYNOPSIS Read host free physical memory and aggregate VM working sets on Windows.
    .OUTPUTS A byte-valued snapshot, or null on non-Windows test hosts. A Windows
    query failure stops preparation rather than pretending that RAM is available.
    #>
    if ($env:OS -ne 'Windows_NT') { return $null }
    try {
        $system = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
        $free = [long] $system.FreePhysicalMemory * 1KB
        $vm = 0L
        foreach ($process in @(Get-Process -Name 'VmmemWSL', 'vmmem' -ErrorAction SilentlyContinue)) { $vm += $process.WorkingSet64 }
        return [pscustomobject]@{ FreeBytes = $free; VmWorkingSetBytes = $vm }
    }
    catch { Stop-ProjectCommand 'Windows memory availability could not be read. No later resource step was started. Check Windows CIM access and retry after freeing RAM.' }
}

function Assert-EngineMemoryBudget {
    <# .SYNOPSIS The guarded root dispatcher applies the shared target-plus-tolerance policy. #>
    param($Context)
    if ($env:CMDC_GUARDED_APP -ne 'pretix') { Stop-ProjectCommand 'Use root cmdc --app pretix.' }
}

function Test-ProjectDocker {
    <# .SYNOPSIS Check native Docker, reachable Linux engine, and Compose before setup. #>
    param($Context, [switch] $SkipMemoryCheck)
    $Context.DockerExecutable = Get-DockerExecutable
    $engine = Invoke-Docker -Context $Context -Arguments @('info', '--format', '{{.OSType}}') -Capture -AllowFailure
    if ($engine.ExitCode -ne 0) {
        if ($engine.Stderr) { [Console]::Error.WriteLine($engine.Stderr.TrimEnd()) }
        Stop-ProjectCommand 'Docker Engine is not reachable from Windows. Start Docker Desktop, wait until it is ready, and retry docker info. A user WSL distribution is not required.'
    }
    if ($engine.Stdout.Trim() -ne 'linux') {
        Stop-ProjectCommand 'Docker is using Windows containers. Switch Docker Desktop to Linux containers, then retry cmdc setup --app pretix.'
    }
    if (-not $SkipMemoryCheck) { Assert-EngineMemoryBudget -Context $Context }
    $compose = Invoke-Docker -Context $Context -Arguments @('compose', 'version') -Capture -AllowFailure
    if ($compose.ExitCode -ne 0) { Stop-ProjectCommand 'Docker Compose is unavailable. Check the Compose installation supplied with Docker Desktop.' }
}

function Invoke-Environment {
    <# .SYNOPSIS Run configuration and endpoint maintenance in pinned container Python. #>
    param($Context, [string[]] $Arguments)
    $prefix = @('run', '--pull', 'never', '--rm', '--label', 'org.robot-web.app=pretix', '--label', 'com.docker.compose.project=robot-web-pretix', '--label', 'com.docker.compose.service=python', '--label', 'com.docker.compose.oneoff=True', '--label', ('com.docker.compose.project.working_dir=' + $Context.Root), '--network', 'none', '--env', 'CMDC_HOST_PLATFORM=windows')
    $memoryFile = Join-Path $Context.Root '.runtime/bootstrap-memory.args'
    $limit='128m'; $swapLimit='128m'
    if (Test-Path -LiteralPath $memoryFile) {
        $limit = [IO.File]::ReadAllText($memoryFile).Trim()
        $swapLimit=$limit
        $swapFile=Join-Path $Context.Root '.runtime/bootstrap-memory-swap.args'
        if (Test-Path -LiteralPath $swapFile) { $swapLimit=[IO.File]::ReadAllText($swapFile).Trim() }
    }
    if ($limit) { $prefix += @('--memory',$limit,'--memory-swap',$swapLimit) }
    $prefix += @('--volume', ($Context.Root + ':/workspace'), '--workdir', '/workspace', $Context.BootstrapImage, 'python3', 'scripts/configuration.py')
    $result = Invoke-Docker -Context $Context -Arguments ($prefix + $Arguments) -Capture
    if ($result.Stdout) { [Console]::Out.Write($result.Stdout) }
}

function Initialize-ProjectFiles {
    <# .SYNOPSIS Ensure private settings and Windows-writable output directories exist. #>
    param($Context)
    Invoke-Environment -Context $Context -Arguments @('ensure')
    foreach ($directory in @('reports', 'backups', 'evidence', 'upstream')) {
        [void] [IO.Directory]::CreateDirectory((Join-Path $Context.Root $directory))
    }
}

function Get-ServiceNames {
    <# .SYNOPSIS Map one service selection to fixed allowed Compose names; reject options. #>
    param([string] $Selection = 'all')
    if ($Selection -in @('all', 'pretix')) { return @('postgres', 'redis', 'mailpit', 'gateway', 'pretix', 'worker', 'periodic') }
    if ($Selection -in @('postgres', 'redis', 'mailpit', 'gateway', 'worker', 'periodic')) { return $Selection }
    Stop-ProjectCommand "Unknown service '$Selection'. Choose all, pretix, postgres, redis, mailpit, gateway, worker, or periodic."
}

function Get-PublicPort {
    <# .SYNOPSIS Read one Docker-assigned loopback port, returning empty text if absent. #>
    param($Context, [string] $Service, [string] $Target)
    $result = Invoke-Compose -Context $Context -Arguments @('port', $Service, $Target) -Capture -AllowFailure
    if ($result.ExitCode -eq 0 -and $result.Stdout -match '(?m)^127\.0\.0\.1:(\d+)\s*$') { return $Matches[1] }
    return ''
}

function Sync-ProjectUrls {
    <# .SYNOPSIS Record public gateway and Mailpit ports before configuring web services. #>
    param($Context)
    $web = Get-PublicPort -Context $Context -Service 'gateway' -Target '18445'
    $mail = Get-PublicPort -Context $Context -Service 'mailpit' -Target '8025'
    Invoke-Environment -Context $Context -Arguments @('sync', '--pretix-port', $web, '--mailpit-port', $mail)
}

function Start-OneService {
    <# .SYNOPSIS Check Windows RAM reserve and start one service without dependency fan-out. #>
    param($Context,[string]$Service)
    $snapshot=Get-WindowsMemorySnapshot
    $policy=Join-Path $env:CMDC_WORKSPACE 'config/pretix-safety.env'
    $entries=@(Get-Content -LiteralPath $policy | Where-Object { $_ -notmatch '^\s*(#|$)' })
    if ($entries.Count -ne 1 -or $entries[0] -notmatch '^HOST_FREE_MEMORY_MIN_MIB=([1-9][0-9]{0,6})$') { Stop-ProjectCommand 'Invalid Pretix host reserve policy. Restore config/pretix-safety.env before starting services.' }
    $minimum=[long]$Matches[1]
    if ($minimum -gt 1048576) { Stop-ProjectCommand 'HOST_FREE_MEMORY_MIN_MIB must be within 1..1048576.' }
    if ($snapshot -and $snapshot.FreeBytes -lt ($minimum * 1MB)) { Stop-ProjectCommand 'Windows RAM reserve fell below the Pretix stop threshold. No later service was started. Inspect status and stop this app when Docker is reachable.' }
    Write-TerminalMessage INFO "Start pretix service: $Service"
    Invoke-Compose -Context $Context -Arguments @('up','--no-deps','--pull','never','-d','--wait','--wait-timeout','600',$Service)
}

function Start-ProjectServices {
    <#
    .SYNOPSIS Start a service group, record ports, and clean newly exposed containers on failure.
    .PARAMETER Selection One validated service name or all; existing public containers
    are preserved if a later step fails. Database volumes are never removed here.
    #>
    param($Context, [string] $Selection = 'all')
    $services = @(Get-ServiceNames -Selection $Selection)
    if ($Selection -in @('all','pretix','worker','periodic')) {
        $services=@('postgres','redis','mailpit','gateway','pretix','worker')
        $periodic=Get-Content -LiteralPath (Join-Path $Context.Root '.runtime/periodic-mode')
        if ($Selection -eq 'periodic' -or $periodic -eq 'scheduled') { $services += 'periodic' }
        if ($Selection -in @('all','pretix') -and $periodic -eq 'manual') { Invoke-Compose -Context $Context -Arguments @('stop','periodic') }
    }
    $exposed = @()
    if ($Selection -in @('all', 'pretix', 'worker', 'periodic', 'gateway')) { $exposed = @('gateway', 'mailpit') }
    elseif ($Selection -eq 'mailpit') { $exposed = @('mailpit') }
    $created = @()
    foreach ($service in $exposed) {
        $running = Invoke-Compose -Context $Context -Arguments @('ps', '--status', 'running', '-q', $service) -Capture
        if (-not $running.Stdout.Trim()) { $created += $service }
    }
    try {
        if ($exposed.Count -gt 0) {
            foreach ($service in $exposed) { Start-OneService -Context $Context -Service $service }
            Sync-ProjectUrls -Context $Context
        }
        foreach ($service in $services) { if ($exposed -notcontains $service) { Start-OneService -Context $Context -Service $service } }
        if ($exposed.Count -gt 0) { Invoke-Environment -Context $Context -Arguments @('urls') }
    }
    catch {
        $originalError = $_
        foreach ($service in $created) {
            try { [void] (Invoke-Compose -Context $Context -Arguments @('rm', '-s', '-f', $service) -AllowFailure) }
            catch { Write-Warning "Could not release the new $service container. Retry cmdc down when Docker is available." }
        }
        try { Sync-ProjectUrls -Context $Context }
        catch { Write-Warning 'Could not refresh access links. Retry cmdc urls --app pretix when Docker is available.' }
        throw $originalError
    }
}

function Stop-ProjectServices {
    <# .SYNOPSIS Stop one group and remove its public bindings while keeping data volumes. #>
    param($Context, [string] $Selection = 'all')
    Invoke-Compose -Context $Context -Arguments (@('stop') + @(Get-ServiceNames -Selection $Selection))
    if ($Selection -in @('all', 'pretix')) {
        Invoke-Compose -Context $Context -Arguments @('rm', '-f', 'gateway', 'mailpit')
        Clear-LocalEndpointState -Context $Context
    }
    elseif ($Selection -in @('gateway', 'mailpit')) {
        Invoke-Compose -Context $Context -Arguments @('rm', '-f', $Selection)
        Clear-LocalEndpointState -Context $Context -Scope $Selection
    }
}

function Show-ProjectResources {
    <#
    .SYNOPSIS Show resource use only for this project's running containers.
    .PARAMETER Watch Stream updates; otherwise request one snapshot.
    .OUTPUTS Docker statistics, or a message when no project container runs.
    An empty selection never falls back to host-wide Docker statistics.
    #>
    param($Context, [switch] $Watch)
    $running = Invoke-Compose -Context $Context -Arguments @('--profile', 'tools', 'ps', '--status', 'running', '-q') -Capture
    $ids = @($running.Stdout -split '\r?\n' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($ids.Count -eq 0) {
        Write-Host 'No running project containers were found. Run cmdc start --app pretix to measure resource usage.'
        return
    }
    Write-Host 'Project container usage. Memory limits are ceilings, not reserved allocations. Desktop VM memory may include cache and other projects.'
    $arguments = @('stats')
    if (-not $Watch) { $arguments += '--no-stream' }
    Invoke-Docker -Context $Context -Arguments ($arguments + $ids)
}

function Initialize-Database {
    <# .SYNOPSIS Stop application writers, apply migrations and create missing fixtures. #>
    param($Context)
    Invoke-Compose -Context $Context -Arguments @('stop', 'pretix', 'worker', 'periodic')
    Start-OneService -Context $Context -Service 'postgres'
    Start-OneService -Context $Context -Service 'redis'
    $migration = Invoke-Compose -Context $Context -Arguments @('run', '--pull', 'never', '--rm', '--no-deps', 'worker', 'migrate', '--noinput', '--verbosity', '0') -Capture
    if ($migration.Stdout) { Write-Host $migration.Stdout }
    $seed = Invoke-Compose -Context $Context -Arguments @('run', '--pull', 'never', '--rm', '--no-deps', 'worker', 'shell', '-c', 'exec(open("/workspace/scripts/seed_demo.py").read())') -Capture
    if ($seed.Stdout) { Write-Host $seed.Stdout }
}

function Initialize-Source {
    <# .SYNOPSIS Clone or verify the pinned source without overwriting another checkout. #>
    param($Context)
    Invoke-Compose -Context $Context -Arguments @('pull', '--policy', 'missing', 'git')
    $checkout = Join-Path $Context.Root 'upstream/pretix'
    if (-not (Test-Path -LiteralPath (Join-Path $checkout '.git'))) {
        if (Test-Path -LiteralPath $checkout) { Stop-ProjectCommand 'upstream/pretix already exists without Git metadata. Move it aside; this command will not overwrite it.' }
        Invoke-Compose -Context $Context -Arguments @('run', '--pull', 'never', '--rm', '--no-deps', 'git', 'clone', '--depth', '1', '--branch', 'v2026.9.2', 'https://github.com/pretix/pretix.git', 'pretix')
    }
    $commit = Invoke-Compose -Context $Context -Arguments @('run', '--pull', 'never', '--rm', '--no-deps', 'git', '-C', 'pretix', 'rev-parse', 'HEAD') -Capture
    if ($commit.Stdout.Trim() -ne $Context.SourceCommit) { Stop-ProjectCommand 'The source checkout does not match the pinned commit. Keep your changes separately before replacing it.' }
}

function Write-Utf8File {
    <# .SYNOPSIS Write exact captured output as UTF-8 without a Windows PowerShell BOM. #>
    param([string] $Path, [string] $Text)
    [IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding($false)))
}

function Save-ImageLock {
    <# .SYNOPSIS Resolve image tags using base Compose and replace the digest override. #>
    param($Context)
    Invoke-Compose -Context $Context -Arguments @('--profile', 'tools', 'config', '--lock-image-digests', '-o', 'compose.lock.yaml.tmp') -NoLock
    $temporary = Join-Path $Context.Root 'compose.lock.yaml.tmp'
    $destination = Join-Path $Context.Root 'compose.lock.yaml'
    if (Test-Path -LiteralPath $destination) { [IO.File]::Replace($temporary, $destination, [NullString]::Value) }
    else { [IO.File]::Move($temporary, $destination) }
}

function Clear-LocalEndpointState {
    <#
    .SYNOPSIS Clear recorded ports after shutdown without starting or pulling Python.
    .PARAMETER Context Project directory containing the existing private dotenv file.
    .PARAMETER Scope all, gateway, or mailpit; other settings and secrets are kept.
    .OUTPUTS None. Endpoint reports are removed; dotenv is replaced atomically.
    #>
    param($Context, [string] $Scope = 'all')
    $path = Join-Path $Context.Root '.env'
    if (Test-Path -LiteralPath $path) {
        $text = [IO.File]::ReadAllText($path)
        $keys = @('PRETIX_PUBLIC_PORT', 'MAILPIT_PUBLIC_PORT')
        if ($Scope -eq 'gateway') { $keys = @('PRETIX_PUBLIC_PORT') }
        elseif ($Scope -eq 'mailpit') { $keys = @('MAILPIT_PUBLIC_PORT') }
        foreach ($key in $keys) { $text = [regex]::Replace($text, ('(?m)^' + $key + '=[^\r\n]*'), ($key + '=')) }
        $temporary = $path + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
        try { Write-Utf8File -Path $temporary -Text $text; [IO.File]::Replace($temporary, $path, [NullString]::Value) }
        finally { if (Test-Path -LiteralPath $temporary) { [IO.File]::Delete($temporary) } }
    }
    foreach ($name in @('endpoints.json', 'ENDPOINTS.md')) {
        $endpoint = Join-Path $Context.Root ('.runtime/' + $name)
        if (Test-Path -LiteralPath $endpoint) { [IO.File]::Delete($endpoint) }
    }
}

function Ensure-BootstrapImage {
    <# .SYNOPSIS Reuse the exact pinned helper digest before attempting a download. #>
    param($Context)
    $cached=Invoke-Docker -Context $Context -Arguments @('image','inspect',$Context.BootstrapImage) -Capture -AllowFailure
    if ($cached.ExitCode -eq 0) { Write-TerminalMessage INFO 'Using cached configuration helper image.' }
    else { Invoke-Docker -Context $Context -Arguments @('pull',$Context.BootstrapImage) }
}

function Pull-ProjectImages {
    <# .SYNOPSIS Prepare missing selected service images serially; server excludes Robot browser. #>
    param($Context, [string] $Selection = 'server')
    $services = @('postgres', 'redis', 'mailpit', 'gateway', 'pretix', 'worker', 'periodic', 'python')
    if ($Selection -eq 'robot') { $services = @('robot') }
    elseif ($Selection -eq 'all') { $services += @('git', 'robot') }
    Invoke-Compose -Context $Context -Arguments (@('--profile', 'tools', 'pull', '--policy', 'missing') + $services)
}

function Save-ProjectVersions {
    <# .SYNOPSIS Save image IDs and tool versions as files under evidence without secrets. #>
    param($Context)
    $images = Invoke-Compose -Context $Context -Arguments @('--profile', 'tools', 'config', '--images') -Capture
    Write-Utf8File -Path (Join-Path $Context.Root 'evidence/images.txt') -Text $images.Stdout
    $imageNames = @($images.Stdout -split '\r?\n' | Where-Object { $_ } | Select-Object -Unique)
    if ($imageNames.Count -eq 0) { Stop-ProjectCommand 'Compose returned no image names. Review compose.yaml before recording versions.' }
    $inspections = @(); $missing = @()
    foreach ($name in $imageNames) {
        $inspection = Invoke-Docker -Context $Context -Arguments @('image', 'inspect', $name) -Capture -AllowFailure
        if ($inspection.ExitCode -eq 0) { $inspections += @($inspection.Stdout | ConvertFrom-Json) }
        else { $missing += $name }
    }
    Write-Utf8File -Path (Join-Path $Context.Root 'evidence/image-inspect.json') -Text (ConvertTo-Json -InputObject @($inspections) -Depth 30)
    Write-Utf8File -Path (Join-Path $Context.Root 'evidence/images-not-cached.txt') -Text ($missing -join "`n")
    foreach ($file in @('robot-version.txt', 'browser-version.txt', 'robot-python-version.txt')) {
        Write-Utf8File -Path (Join-Path $Context.Root ('evidence/' + $file)) -Text 'Not probed: version reporting does not pull or launch the browser image. See the image lock and Robot run reports.'
    }
    $commands = @(
        @{ File = 'pretix-python-version.txt'; Args = @('run', '--pull', 'never', '--rm', '--no-deps', '--entrypoint', 'python3', 'worker', '--version') },
        @{ File = 'pretix-version.txt'; Args = @('run', '--pull', 'never', '--rm', '--no-deps', 'worker', '--version') }
    )
    foreach ($command in $commands) {
        $result = Invoke-Compose -Context $Context -Arguments $command.Args -Capture
        Write-Utf8File -Path (Join-Path $Context.Root ('evidence/' + $command.File)) -Text $result.Stdout
    }
}

function Remove-ProjectVolume {
    <# .SYNOPSIS Remove an allowed named volume only after verifying its Compose owner. #>
    param($Context, [string] $Suffix)
    if ($Suffix -notin @('postgres_data', 'redis_data')) { Stop-ProjectCommand 'Unsupported volume deletion target.' }
    $name = $Context.ProjectName + '_' + $Suffix
    $probe = Invoke-Docker -Context $Context -Arguments @('volume', 'inspect', $name) -Capture -AllowFailure
    if ($probe.ExitCode -ne 0) { return }
    $owner = Invoke-Docker -Context $Context -Arguments @('volume', 'inspect', '--format', '{{index .Labels "com.docker.compose.project"}}', $name) -Capture
    if ($owner.Stdout.Trim() -ne $Context.ProjectName) { Stop-ProjectCommand "Refusing to delete volume '$name': it belongs to another project." }
    Invoke-Docker -Context $Context -Arguments @('volume', 'rm', $name)
}

function Reset-ProjectResources {
    <# .SYNOPSIS Clear access state before removing the explicitly selected Docker resources. #>
    param($Context, [string] $Scope)
    Invoke-Environment -Context $Context -Arguments @('clear')
    $arguments = @('--profile', 'tools', 'down', '--remove-orphans')
    if ($Scope -in @('data', 'all')) { $arguments += '--volumes' }
    if ($Scope -eq 'all') { $arguments += @('--rmi', 'all') }
    Invoke-Compose -Context $Context -Arguments $arguments
    if ($Scope -eq 'db') { Remove-ProjectVolume -Context $Context -Suffix 'postgres_data' }
    elseif ($Scope -eq 'cache') { Remove-ProjectVolume -Context $Context -Suffix 'redis_data' }
}

function Remove-GeneratedPath {
    <#
    .SYNOPSIS Delete one generated path recursively without traversing symbolic links.
    .PARAMETER Path A literal path from the driver's fixed generated-path allowlist.
    .OUTPUTS Files or links are removed. Junctions and symbolic links are removed
    themselves, preserving any target outside the project. No wildcard is evaluated.
    #>
    param([string] $Path)
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $attributes = [IO.File]::GetAttributes($Path)
    $directory = ($attributes -band [IO.FileAttributes]::Directory) -ne 0
    $link = ($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
    if ($directory) {
        if (-not $link) {
            foreach ($child in [IO.Directory]::GetFileSystemEntries($Path)) { Remove-GeneratedPath -Path $child }
            [IO.File]::SetAttributes($Path, [IO.FileAttributes]::Normal)
        }
        [IO.Directory]::Delete($Path)
    }
    else {
        if (-not $link) { [IO.File]::SetAttributes($Path, [IO.FileAttributes]::Normal) }
        [IO.File]::Delete($Path)
    }
}

function Remove-GeneratedFiles {
    <# .SYNOPSIS Remove only fixed generated paths after explicit --include-files authorization. #>
    param($Context)
    foreach ($relative in @('reports', 'backups', 'evidence', 'upstream', '.runtime', '.env', 'scripts/__pycache__', 'tests/cli/__pycache__')) {
        Remove-GeneratedPath -Path (Join-Path $Context.Root $relative)
    }
    Write-Host 'Generated files, private configuration, downloaded source and backups were removed. Project code and templates were kept.'
}

function Invoke-ProjectRobot {
    <# .SYNOPSIS Run Robot with unchanged option boundaries and return any failing status. #>
    param($Context, [string[]] $Arguments)
    if ($Arguments -notcontains '--dryrun') { Start-ProjectServices -Context $Context }
    Invoke-Compose -Context $Context -Arguments (@('run', '--pull', 'never', '--rm', '--no-deps', '--name', ($Context.ProjectName + '-robot-run'), 'robot', '--outputdir', '/workspace/reports') + $Arguments + @('/workspace/tests/robot'))
}

function Invoke-ProjectBackup {
    <# .SYNOPSIS Stop writers and save a new database/file pair without overwriting a backup. #>
    param($Context, [string] $Name)
    $path = Join-Path $Context.Root ('backups/' + $Name)
    if (Test-Path -LiteralPath $path) { Stop-ProjectCommand 'That backup name already exists. Choose a new name.' }
    [void] [IO.Directory]::CreateDirectory($path)
    Invoke-Compose -Context $Context -Arguments @('stop', 'pretix', 'worker', 'periodic')
    Invoke-Compose -Context $Context -Arguments @('up', '--pull', 'never', '-d', '--wait', 'postgres')
    Invoke-Compose -Context $Context -Arguments @('exec', '-T', 'postgres', 'pg_dump', '-U', 'pretix', '-d', 'pretix', '-Fc', '-f', "/backups/$Name/database.dump")
    Invoke-Compose -Context $Context -Arguments @('run', '--pull', 'never', '--rm', '--no-deps', '--entrypoint', 'tar', 'worker', '-czf', "/workspace/backups/$Name/data.tar.gz", '-C', '/data', '.')
    Write-Host 'Backup completed. Application writers remain stopped; run cmdc start --app pretix to resume.'
}

function Invoke-ProjectRestore {
    <# .SYNOPSIS Restore an already validated backup and clear stale Redis sessions/tasks. #>
    param($Context, [string] $Name)
    Invoke-Environment -Context $Context -Arguments @('check-backup','--backup',$Name)
    Invoke-Compose -Context $Context -Arguments @('stop', 'pretix', 'worker', 'periodic')
    Start-OneService -Context $Context -Service 'postgres'
    Start-OneService -Context $Context -Service 'redis'
    Invoke-Compose -Context $Context -Arguments @('exec', '-T', 'postgres', 'pg_restore', '-U', 'pretix', '-d', 'pretix', '--clean', '--if-exists', '--exit-on-error', "/backups/$Name/database.dump")
    $restore = 'find /data -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +; tar -xzf "$1" -C /data'
    Invoke-Compose -Context $Context -Arguments @('run', '--pull', 'never', '--rm', '--no-deps', '--entrypoint', '/bin/sh', 'worker', '-c', $restore, 'sh', "/workspace/backups/$Name/data.tar.gz")
    Invoke-Compose -Context $Context -Arguments @('exec', '-T', 'redis', 'redis-cli', 'FLUSHALL')
    Write-Host 'Restore completed. Database and files were replaced; run cmdc start --app pretix to resume.'
}

function Assert-CommandArguments {
    <#
    .SYNOPSIS Validate command options and destructive scopes before invoking Docker.
    .OUTPUTS A normalized plan with command, arguments, and explicit opt-in flags.
    Invalid paths, services, and missing --yes are rejected before any mutation.
    #>
    param([string[]] $CommandArguments, $Context)
    $command = 'help'
    $remaining = @()
    if ($CommandArguments.Count -gt 0) { $command = $CommandArguments[0] }
    if ($CommandArguments.Count -gt 1) { $remaining = @($CommandArguments | Select-Object -Skip 1) }
    $plan = [pscustomobject]@{ Command = $command; Arguments = $remaining; SkipSource = $false; RunTests = $false; IncludeFiles = $false }
    if ($command -in @('setup', 'bootstrap')) {
        $plan.Command = 'setup'
        foreach ($option in $remaining) {
            switch ($option) {
                '--skip-source' { $plan.SkipSource = $true }
                '--run-tests' { $plan.RunTests = $true }
                default { Stop-ProjectCommand 'Usage: cmdc setup --app pretix [--skip-source] [--run-tests]' }
            }
        }
    }
    elseif ($command -eq 'destroy') {
        if ($remaining.Count -lt 1 -or $remaining[0] -ne '--yes' -or $remaining.Count -gt 2 -or ($remaining.Count -eq 2 -and $remaining[1] -ne '--include-files')) {
            Stop-ProjectCommand 'Usage: cmdc destroy --yes [--include-files]. This deletes project runtime data.'
        }
        $plan.Command = 'reset'; $plan.Arguments = @('all', '--yes'); $plan.IncludeFiles = $remaining -contains '--include-files'
    }
    elseif ($command -in @('start', 'up', 'stop', 'restart')) {
        if ($remaining.Count -gt 1) { Stop-ProjectCommand "Usage: cmdc $command [service|all]" }
        $selection = 'all'; if ($remaining.Count -eq 1) { $selection = $remaining[0] }
        [void] (Get-ServiceNames -Selection $selection)
        $plan.Arguments = @($selection)
    }
    elseif ($command -eq 'reset') {
        if ($remaining.Count -ne 2 -or $remaining[0] -notin @('db', 'cache', 'data', 'all') -or $remaining[1] -ne '--yes') {
            Stop-ProjectCommand 'Usage: cmdc reset db|cache|data|all --yes. Review the data-deletion scope first.'
        }
    }
    elseif ($command -in @('backup', 'restore')) {
        $count = 1; if ($command -eq 'restore') { $count = 2 }
        if ($remaining.Count -ne $count -or $remaining[0] -notmatch '^[A-Za-z0-9_-]+$' -or ($command -eq 'restore' -and $remaining[1] -ne '--yes')) {
            Stop-ProjectCommand "Usage: cmdc $command <name>$(if ($command -eq 'restore') { ' --yes' }). Use English letters, numbers, hyphens or underscores in the name."
        }
        if ($command -eq 'restore') {
            foreach ($file in @('database.dump', 'data.tar.gz')) {
                if (-not (Test-Path -LiteralPath (Join-Path $Context.Root ("backups/" + $remaining[0] + '/' + $file)))) { Stop-ProjectCommand 'The backup is incomplete: database.dump and data.tar.gz are both required.' }
            }
        }
    }
    elseif ($command -eq 'env') {
        if ($remaining.Count -gt 1 -or ($remaining.Count -eq 1 -and $remaining[0] -notin @('init', 'show'))) { Stop-ProjectCommand 'Usage: cmdc env [init|show]' }
    }
    elseif ($command -eq 'host-memory') { }
    elseif ($command -eq 'pull') {
        if ($remaining.Count -gt 1 -or ($remaining.Count -eq 1 -and $remaining[0] -notin @('server', 'robot', 'all'))) { Stop-ProjectCommand 'Usage: cmdc pull [server|robot|all]. Default: server; Robot is downloaded only when requested.' }
    }
    elseif ($command -eq 'resources') {
        if ($remaining.Count -gt 1 -or ($remaining.Count -eq 1 -and $remaining[0] -ne '--watch')) { Stop-ProjectCommand 'Usage: cmdc resources --app pretix [--watch]' }
    }
    elseif ($command -eq 'logs') {
        foreach ($service in $remaining) {
            if ($service -notin @('postgres', 'redis', 'mailpit', 'gateway', 'pretix', 'worker', 'periodic', 'robot')) { Stop-ProjectCommand "Unknown log service: $service" }
        }
    }
    elseif ($command -eq 'manage') { if ($remaining.Count -eq 0) { Stop-ProjectCommand 'Usage: cmdc manage <Django command...>' } }
    elseif ($command -eq 'robot') { }
    elseif ($command -in @('help', '-h', '--help', 'version', 'doctor', 'source', 'down', 'init', 'generate', 'validate', 'status', 'versions', 'lock', 'urls', 'config')) {
        if ($remaining.Count -ne 0) { Stop-ProjectCommand "cmdc $command does not accept options." }
    }
    else { Stop-ProjectCommand "Unknown command '$command'. Run cmdc help." }
    return $plan
}

function Invoke-WindowsLauncher {
    <#
    .SYNOPSIS Validate and run a complete cmdc workflow using native Windows Docker.
    .PARAMETER CommandArguments Original cmdc command and option strings.
    .PARAMETER ProjectRoot Windows directory containing the project, including spaces.
    .OUTPUTS Zero on success, a child failure status, or two for readable usage errors.
    No WSL executable, distribution installation, or WSL integration is invoked.
    #>
    param([string[]] $CommandArguments, [string] $ProjectRoot)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Stop'
    try {
        $Root = [IO.Path]::GetFullPath((Join-Path $ProjectRoot '../..'))
        . (Join-Path $Root 'scripts/terminal.ps1')
        Initialize-Terminal
        $context = New-ProjectContext -ProjectRoot $ProjectRoot
        $plan = Assert-CommandArguments -CommandArguments $CommandArguments -Context $context
        $command = $plan.Command
        $options = @($plan.Arguments)
        if ($command -in @('help', '-h', '--help')) {
            Write-Host ([IO.File]::ReadAllText((Join-Path $context.Root 'config/COMMAND_HELP.txt')))
            return 0
        }
        if ($command -eq 'version') { Write-Host ([IO.File]::ReadAllText((Join-Path $context.Root 'VERSION')).Trim()); return 0 }
        if ($command -eq 'host-memory') {
            if ($options.Count -eq 1 -and $options[0] -eq 'verify') { Test-ProjectDocker -Context $context; return 0 }
            . (Join-Path $context.Root 'scripts/host_memory.ps1')
            Invoke-HostMemoryCommand -Arguments $options
            return 0
        }
        $readOrStop = $command -in @('down', 'stop', 'status', 'resources', 'logs')
        Test-ProjectDocker -Context $context -SkipMemoryCheck:$readOrStop
        if ($command -eq 'doctor') { Write-Host 'Docker Desktop is reachable from Windows and ready for Linux containers. No user WSL distribution is needed.'; return 0 }
        if ($readOrStop) {
            if (-not (Test-Path -LiteralPath (Join-Path $context.Root '.env'))) {
                if ($command -in @('stop','down') -and $env:CMDC_SELECTED_RUNNING -eq '1') { Stop-ProjectCommand 'Pretix is running but its .env file is missing. Restore the saved configuration before cleanup; no successful stop is being claimed.' }
                Write-Host 'No project configuration exists. No initialization was attempted.'; return 0
            }
        }
        else {
            if ($command -eq 'setup' -or ($command -eq 'env' -and $options -notcontains 'show')) {
                Ensure-BootstrapImage -Context $context
            }
            Initialize-ProjectFiles -Context $context
        }
        switch ($command) {
            'setup' {
                Pull-ProjectImages -Context $context
                # Source provenance is pinned; checkout is an explicit source command.
                Initialize-Database -Context $context
                Start-ProjectServices -Context $context
                Write-Host "Pinned image digests: compose.lock.yaml"
                Write-Host 'Setup completed. Services are ready; use cmdc urls --app pretix for access links.'
                if ($plan.RunTests) { Pull-ProjectImages -Context $context -Selection 'robot'; Invoke-ProjectRobot -Context $context -Arguments @() }
            }
            { $_ -in @('start', 'up') } { Start-ProjectServices -Context $context -Selection $options[0] }
            'stop' { Stop-ProjectServices -Context $context -Selection $options[0] }
            'restart' { Stop-ProjectServices -Context $context -Selection $options[0]; Start-ProjectServices -Context $context -Selection $options[0] }
            'down' { Invoke-Compose -Context $context -Arguments @('--profile', 'tools', 'down', '--remove-orphans'); Clear-LocalEndpointState -Context $context }
            'pull' { $selection = 'server'; if ($options.Count) { $selection = $options[0] }; Pull-ProjectImages -Context $context -Selection $selection }
            'config' { Invoke-Environment -Context $context -Arguments @('config') }
            'env' { if ($options -contains 'show') { Invoke-Environment -Context $context -Arguments @('show') } }
            'urls' { Sync-ProjectUrls -Context $context; Invoke-Environment -Context $context -Arguments @('urls') }
            'source' { Initialize-Source -Context $context }
            'init' { Initialize-Database -Context $context }
            'robot' { Pull-ProjectImages -Context $context -Selection 'robot'; Invoke-ProjectRobot -Context $context -Arguments $options }
            'generate' { Invoke-Compose -Context $context -Arguments @('run', '--pull', 'never', '--rm', '--no-deps', 'python', 'scripts/generate_cases.py') }
            'validate' {
                Invoke-Compose -Context $context -Arguments @('--profile', 'tools', 'config', '--quiet')
                foreach ($arguments in @(
                    @('-m', 'unittest', 'discover', '-s', 'tests/cli', '-v'),
                    @('-m', 'compileall', '-q', 'scripts', 'tests/cli'),
                    @('-m', 'py_compile', 'scripts/configuration.py'),
                    @('/repository/scripts/check_docs.py'),
                    @('/repository/scripts/check_code.py')
                )) { Invoke-Compose -Context $context -Arguments (@('run', '--pull', 'never', '--rm', '--no-deps', 'python') + $arguments) }
            }
            'status' { Invoke-Compose -Context $context -Arguments @('--profile', 'tools', 'ps', '-a') }
            'resources' { Show-ProjectResources -Context $context -Watch:($options -contains '--watch') }
            'logs' { Invoke-Compose -Context $context -Arguments (@('logs', '--tail', '150') + $options) }
            'versions' { Save-ProjectVersions -Context $context }
            'lock' { Save-ImageLock -Context $context }
            'reset' { Reset-ProjectResources -Context $context -Scope $options[0]; if ($plan.IncludeFiles) { Remove-GeneratedFiles -Context $context }; Write-Host 'Selected project resources were removed. Project code and templates were kept.' }
            'backup' { Invoke-ProjectBackup -Context $context -Name $options[0] }
            'restore' { Invoke-ProjectRestore -Context $context -Name $options[0] }
            'manage' {
                Invoke-Compose -Context $context -Arguments @('up', '--pull', 'never', '-d', '--wait', 'postgres', 'redis')
                Invoke-Compose -Context $context -Arguments (@('run', '--pull', 'never', '--rm', '--no-deps', 'worker') + $options)
            }
        }
        return 0
    }
    catch {
        [Console]::Error.WriteLine('ERROR: ' + $_.Exception.Message)
        if ($_.Exception.Data.Contains('ExitCode')) { return [int] $_.Exception.Data['ExitCode'] }
        if ($command -eq 'host-memory') {
            [Console]::Error.WriteLine('Review host-memory options or Windows profile permissions. No Docker startup or WSL shutdown is performed by this command.')
        }
        else { [Console]::Error.WriteLine('Review the message above and retry cmdc doctor or cmdc status --app pretix. No user WSL distribution is required.') }
        return 2
    }
    finally { $ErrorActionPreference = $previousPreference }
}

# Dot sourcing exposes pure helpers and workflow functions to regression tests.
if ($MyInvocation.InvocationName -ne '.') {
    if ($env:CMDC_GUARDED_APP -ne 'pretix') { [Console]::Error.WriteLine('Use root cmdc --app pretix.'); exit 2 }
    exit (Invoke-WindowsLauncher -CommandArguments @($args) -ProjectRoot (Split-Path -Parent $PSScriptRoot))
}
