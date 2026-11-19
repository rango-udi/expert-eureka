# Require explicit app selection and serialize resource-changing operations.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root
function Stop-Cmdc {
    param([string]$Message, [int]$ExitCode = 2)
    $errorValue = [Exception]::new($Message)
    $errorValue.Data['ExitCode'] = $ExitCode
    throw $errorValue
}
function Read-DockerMetadata {
    param([string[]]$Arguments, [string]$FailureMessage)
    # Use explicit native argument quoting; Windows PowerShell can strip template quotes.
    $result = Invoke-DockerConsole -Arguments $Arguments -QuietLabel 'Inspect Docker metadata' -CaptureResult
    if ($result.ExitCode -ne 0) { Stop-Cmdc $FailureMessage }
    return $result.Stdout.Trim()
}
$lock = $null
$engineToken = $null
$selectedRunning=$false
try {
    . (Join-Path $PSScriptRoot 'terminal.ps1')
    Initialize-Terminal
    $command = if ($args.Count) { [string]$args[0] } else { 'help' }
    $options = [Collections.Generic.List[string]]::new()
    $app = ''
    $appSeen=$false
    $acceptPretixRisk=$false
    $acceptResourceRisk=$false
    for ($i=1; $i -lt $args.Count; $i++) {
        $value = [string]$args[$i]
        if ($value -eq '--accept-resource-risk') {
            if ($acceptResourceRisk) { Stop-Cmdc 'Use --accept-resource-risk once.' }; $acceptResourceRisk=$true
        } elseif ($value -eq '--accept-pretix-risk') {
            if ($acceptPretixRisk) { Stop-Cmdc 'Use --accept-pretix-risk once.' }; $acceptPretixRisk=$true
        } elseif ($value -eq '--app') {
            if ($appSeen -or $i+1 -ge $args.Count) { Stop-Cmdc 'Use exactly one --app oscar, --app pretix, --app shuup, --app wowy, --app nopcommerce, --app prestashop or --app woocommerce.' }
            $appSeen=$true; $i++; $app = [string]$args[$i]
        } elseif ($value.StartsWith('--app=')) {
            if ($appSeen) { Stop-Cmdc 'Choose exactly one app.' }
            $appSeen=$true; $app = $value.Substring(6)
        } else { $options.Add($value) }
    }
    if ($command -in @('help','--help','-h')) {
        Write-Host ([IO.File]::ReadAllText((Join-Path $Root 'config/COMMAND_HELP.txt')))
        exit 0
    }
    if ($command -eq 'apps') {
        if ($app) { Stop-Cmdc 'apps is a global command; omit --app.' }
        if ($options.Count -gt 1) { Stop-Cmdc 'Use apps [--names|--ids|--raw].' }
        $mode=if ($options.Count) { $options[0] } else { 'table' }
        if ($mode -notin @('table','--names','--ids','--raw')) { Stop-Cmdc 'Use apps [--names|--ids|--raw].' }
        if ($mode -eq '--raw') { Get-Content config/apps.list; exit 0 }
        if ($mode -eq 'table') { Write-Output ('{0,-16} {1}' -f 'APP ID','NAME') }
        foreach ($line in Get-Content config/apps.list) {
            if (-not $line -or $line.StartsWith('#')) { continue }
            $fields=$line.Split('|')
            if ($mode -eq '--names') { Write-Output $fields[3] }
            elseif ($mode -eq '--ids') { Write-Output $fields[0] }
            else { Write-Output ('{0,-16} {1}' -f $fields[0],$fields[3]) }
        }
        exit 0
    }
    if ($command -eq 'version') { Get-Content VERSION; exit 0 }
    $powerShell = (Get-Process -Id $PID).Path
    function Invoke-Adapter {
        param([string]$Path, [string[]]$Parameters)
        $info = [Diagnostics.ProcessStartInfo]::new()
        $info.FileName = $powerShell
        $arguments = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$Path) + $Parameters
        $info.Arguments = (($arguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' ')
        $info.UseShellExecute = $false
        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $info
        try { [void]$process.Start(); $process.WaitForExit(); return $process.ExitCode }
        finally { $process.Dispose() }
    }
    if ($command -in @('doctor','wsl-vm-limit-help')) {
        if ($app) { Stop-Cmdc 'This is a global command; omit --app.' }
        exit (Invoke-Adapter (Join-Path $PSScriptRoot 'system.ps1') (@($command)+$options.ToArray()))
    }
    if ($command -notin @('setup','bootstrap','start','up','restart','stop','down','status','urls','resources','logs','diagnostics','init','env','config','robot-init','robot','generate','validate','manage','backup','restore','reset','destroy','source','versions','pull','report')) { Stop-Cmdc 'Unknown command. Run cmdc help.' }
    if ($app -notin @('oscar','pretix','shuup','wowy','nopcommerce','prestashop','woocommerce')) { Stop-Cmdc 'Choose an application: add --app oscar, --app pretix, --app shuup, --app wowy, --app nopcommerce, --app prestashop or --app woocommerce. See documents/APPS.md.' }
    if ($command -eq 'report' -and $app -ne 'shuup') { Stop-Cmdc 'report is supported only for --app shuup.' }
    if ($app -in @('nopcommerce','prestashop','woocommerce') -and $command -notin @('setup','bootstrap','init','start','up','restart','robot-init','robot','env','validate','status','resources','logs','stop','down','urls','config','versions','source','destroy','diagnostics')) { Stop-Cmdc 'Unsupported command for native commerce. See documents/guides/NATIVE_COMMERCE.md. No Docker operation was started.' }
    if ($command -eq 'diagnostics') {
        if ($options.Count) { Stop-Cmdc 'diagnostics takes no options.' }
        exit (Invoke-Adapter (Join-Path $PSScriptRoot 'diagnostics.ps1') @('-Application',$app))
    }
    if ($command -eq 'destroy' -and $app -in @('nopcommerce','prestashop','woocommerce')) {
        foreach ($option in $options) { if ($option -notin @('--yes','--include-files')) { Stop-Cmdc 'Use destroy --app <id> --yes [--include-files].' } }
    }
    if ($acceptPretixRisk -and $app -ne 'pretix') { Stop-Cmdc '--accept-pretix-risk applies only to Pretix.' }
    if ($acceptResourceRisk -and $app -notin @('nopcommerce','prestashop','woocommerce')) { Stop-Cmdc '--accept-resource-risk applies only to native commerce adapters.' }
    if ($app -in @('nopcommerce','prestashop','woocommerce')) {
        . (Join-Path $PSScriptRoot 'commerce/resource_safety.ps1')
        Confirm-CommerceRisk -Command $command -Accepted $acceptResourceRisk -Application $app
    }
    if ($command -in @('destroy','reset','restore') -and $options -notcontains '--yes') { Stop-Cmdc 'Destructive operations require --yes after reviewing their scope.' }
    if ($app -eq 'pretix') {
        . (Join-Path $PSScriptRoot 'pretix_safety.ps1')
        Confirm-PretixRisk -Command $command -Accepted $acceptPretixRisk
    }
    if (-not (Test-Path (Join-Path $Root ('apps/'+$app+'/scripts/adapter.ps1')) -PathType Leaf)) { Stop-Cmdc 'The selected adapter is missing. Extract the complete source package.' }
    if ($command -notin @('stop','down','status','resources','logs')) {
        $shared=Join-Path $Root 'fuzcake-data'
        if (-not (Test-Path (Join-Path $shared 'records/app-profiles.json') -PathType Leaf) -or -not (Test-Path (Join-Path $shared 'fuzcake_data/__init__.py') -PathType Leaf)) { Stop-Cmdc 'Shared fuzcake-data is missing. Extract the complete source package at the repository root before continuing.' }
        if ((Get-Item $shared -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { Stop-Cmdc 'Shared fuzcake-data must be a real source directory, not a filesystem link.' }
    }
    if ($app -eq 'oscar' -and ((Test-Path (Join-Path $Root '.env')) -or (Test-Path (Join-Path $Root '.runtime/data/db.sqlite3')))) { Stop-Cmdc 'Oscar configuration or data remains at the repository root. Follow documents/guides/MIGRATION.md to move it into apps/oscar before continuing.' }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Stop-Cmdc 'Docker CLI is missing. Install and start Docker.' }
    $mutation = $command -notin @('status','resources','logs')
    if ($mutation) {
        if ((Test-Path .runtime) -and ((Get-Item .runtime -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { Stop-Cmdc 'The workspace runtime path must not be a filesystem link.' }
        New-Item -ItemType Directory -Force .runtime | Out-Null
        $candidate = Join-Path $Root '.runtime/app-operation.lock'
        try { New-Item -ItemType Directory -ErrorAction Stop $candidate | Out-Null }
        catch { Stop-Cmdc 'Another application operation is running. Wait for it to finish. After a crash, verify that no launcher or task container is active before removing .runtime/app-operation.lock.' }
        $lock=$candidate
        $earlierLocks=(Read-DockerMetadata -Arguments @('volume','ls','--format','{{.Name}}') -FailureMessage 'Cannot inspect coordinator metadata. Check Docker availability; no application resources were changed.') -split "`r?`n"
        foreach ($name in $earlierLocks) { if ($name -like 'robot-web-*-operation-lock') { Stop-Cmdc 'An earlier coordinator lock is present. Finish or recover that operation with its original version.' } }
        $engineToken=[guid]::NewGuid().ToString('N')
        $claim=Invoke-DockerConsole -Arguments @('volume','create','--label','org.robot-web.operation-lock=true','--label',"org.robot-web.owner=$engineToken",'--label',"org.robot-web.workspace=$Root",'robot-web-operation-lock') -CaptureResult
        if ($claim.ExitCode -ne 0) { Stop-Cmdc 'Cannot acquire the Docker operation lock. No application was started.' }
        $owner=Read-DockerMetadata -Arguments @('volume','inspect','--format','{{index .Labels "org.robot-web.owner"}}','robot-web-operation-lock') -FailureMessage 'Cannot verify Docker operation lock ownership. No application was started. Check the diagnostic log and documents/guides/APP_LIFECYCLE.md before retrying.'
        if (-not $owner) { Stop-Cmdc 'The Docker operation lock has no owner label. Keep it for inspection; see documents/guides/APP_LIFECYCLE.md.' }
        if ($owner -ne $engineToken) { Stop-Cmdc 'Another workspace operation owns the engine lock. Wait for it to finish. For an interrupted operation, see documents/guides/APP_LIFECYCLE.md.' }
    }
    if ($command -notin @('status','resources','logs')) {
        $projects=(Read-DockerMetadata -Arguments @('ps','-a','--format','{{.Label "org.robot-web.app"}}|{{.Label "com.docker.compose.project"}}|{{.Label "com.docker.compose.project.working_dir"}}|{{.Label "com.docker.compose.oneoff"}}|{{.State}}') -FailureMessage 'Cannot inspect Docker container ownership and state. No application was started. Check the diagnostic log and retry.') -split "`r?`n"
        foreach ($record in $projects) {
            $fields=$record -split '\|',5
            if ($fields.Count -lt 5) { if ($record) { Stop-Cmdc 'Docker returned incomplete ownership metadata.' }; continue }
            $managed,$project,$workingDir,$task,$state=$fields
            $active = if ($managed -in @('oscar','pretix','shuup','wowy','nopcommerce','prestashop','woocommerce')) { $managed } elseif ($project -match '^(?:robot-web-.*-oscar|robot-web-oscar|oscar-.*)$') { 'oscar' } elseif ($project -match '^(?:robot-web-.*-pretix|robot-web-pretix|pretix-.*)$') { 'pretix' } elseif ($project -match '^(?:robot-web-.*-shuup|robot-web-shuup|shuup-.*)$') { 'shuup' } elseif ($project -match '^(?:robot-web-.*-wowy|robot-web-wowy|wowy-.*)$') { 'wowy' } elseif ($project -match '^robot-web-(nopcommerce|prestashop|woocommerce)$') { $Matches[1] } else { '' }
            if (-not $active) { continue }
            if ($state -notin @('running','paused','restarting','created','exited','dead','removing')) { Stop-Cmdc 'Docker returned incomplete container state metadata.' }
            $running=$state -in @('running','paused','restarting')
            if ($active -ne $app) {
                if (-not $running) { continue }
                if ($command -in @('stop','down')) { continue }
                Stop-Cmdc "Application $active is still running. Run cmdc down --app $active before selecting $app. No application resources were changed."
            }
            if ($project -ne ('robot-web-'+$app)) { Stop-Cmdc 'An earlier project identifier is present. Stop it with its original launcher before using this version.' }
            if ($running -and $task -eq 'True' -and $command -notin @('stop','down')) { Stop-Cmdc 'An application task is still running. Inspect status and logs; stop it before starting another operation.' }
            $expected = Join-Path $Root ('apps/'+$app)
            if (-not $workingDir -or [IO.Path]::GetFullPath($workingDir) -ne [IO.Path]::GetFullPath($expected)) { Stop-Cmdc 'The selected application belongs to another workspace or its ownership could not be verified. Use its original workspace to stop it.' }
            if ($running) { $selectedRunning=$true }
        }
    }
    if ($command -in @('setup','bootstrap','start','up','restart','robot','robot-init','init','manage','restore','backup','env','pull','source','generate','validate','report')) {
        $code=Invoke-Adapter (Join-Path $PSScriptRoot 'system.ps1') @('doctor')
        if ($code -ne 0) { exit $code }
    }
    $env:CMDC_GUARDED_APP=$app
    $env:CMDC_WORKSPACE=$Root
    $env:CMDC_SELECTED_RUNNING=if ($selectedRunning) { '1' } else { '0' }
    $privateEnv = Join-Path $Root ('apps/'+$app+'/.env')
    if ((Test-Path $privateEnv) -and ((Get-Item $privateEnv -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { Stop-Cmdc 'Application configuration must not be a filesystem link.' }
    $hasData = $app -in @('oscar','shuup','wowy') -and (Test-Path (Join-Path $Root ('apps/'+$app+'/.runtime/data/db.sqlite3')))
    if ($app -eq 'pretix' -and $mutation) {
        $volumes=(Read-DockerMetadata -Arguments @('volume','ls','--format','{{.Name}}') -FailureMessage 'Cannot list existing data volumes. No application data was changed.') -split "`r?`n"
        foreach ($suffix in @('postgres_data','redis_data','pretix_data','pretix_config','mail_data')) {
            $volume='robot-web-pretix_' + $suffix
            if ($volumes -contains $volume) {
                $owner=Read-DockerMetadata -Arguments @('volume','inspect','--format','{{index .Labels "org.robot-web.workspace"}}',$volume) -FailureMessage 'Cannot read data volume ownership. No application data was changed. Check the diagnostic log before retrying.'
                if ($owner -ne $Root) { Stop-Cmdc 'Pretix data volumes belong to another workspace or have no ownership record. Use the original workspace; no data was changed.' }
                $hasData=$true
            }
        }
    }
    if ($app -in @('nopcommerce','prestashop','woocommerce') -and $mutation) {
        $volumes=(Read-DockerMetadata -Arguments @('volume','ls','--format','{{.Name}}') -FailureMessage 'Cannot inspect commerce data ownership.') -split "`r?`n"
        foreach ($suffix in @('database_data','app_data','product_media')) {
            $volume='robot-web-'+$app+'_'+$suffix
            if ($volumes -contains $volume) {
                $owner=Read-DockerMetadata -Arguments @('volume','inspect','--format','{{index .Labels "org.robot-web.workspace"}}',$volume) -FailureMessage 'Cannot verify commerce data ownership.'
                if ($owner -ne $Root) { Stop-Cmdc 'Commerce data belongs to another workspace or has no ownership record. Use the original workspace; no data was changed.' }
                $hasData=$true
            }
        }
    }
    if ($hasData -and -not (Test-Path $privateEnv -PathType Leaf) -and $command -notin @('stop','down','status','resources','logs','reset','destroy')) { Stop-Cmdc 'Application data already exists but its .env is missing. Restore the saved configuration before continuing; new credentials were not generated.' }
    Write-TerminalMessage INFO "Application: $app | Operation: $command"
    $path=Join-Path $Root ('apps/'+$app+'/scripts/adapter.ps1')
    if ($app -eq 'pretix' -and $command -eq 'robot-init') { $command='pull'; $options.Clear(); $options.Add('robot') }
    $code=Invoke-Adapter $path (@($command)+$options.ToArray())
    if ($code -ne 0) { Write-TerminalMessage ERROR "Application $app did not complete $command (exit $code). Inspect status --app $app; use down --app $app before switching applications." }
    exit $code
} catch {
    [Console]::Error.WriteLine('[ERROR] ' + $_.Exception.Message)
    $code=2
    if ($_.Exception.Data.Contains('ExitCode')) { $code=[int]$_.Exception.Data['ExitCode'] }
    exit $code
} finally {
    if ($engineToken) {
        try {
            $probe=Invoke-DockerConsole -Arguments @('volume','inspect','--format','{{index .Labels "org.robot-web.owner"}}','robot-web-operation-lock') -CaptureResult
            if ($probe.ExitCode -ne 0) {
                Write-TerminalMessage WARNING 'Could not verify the operation lock during cleanup. The lock was kept; see documents/guides/APP_LIFECYCLE.md.'
            } elseif ($probe.Stdout.Trim() -eq $engineToken) {
                $release=Invoke-DockerConsole -Arguments @('volume','rm','robot-web-operation-lock') -CaptureResult
                if ($release.ExitCode -ne 0) { Write-TerminalMessage WARNING 'Could not release this operation lock. See documents/guides/APP_LIFECYCLE.md before retrying.' }
            }
        } catch { [Console]::Error.WriteLine('[WARNING] Operation lock cleanup could not finish. The lock was kept; see documents/guides/APP_LIFECYCLE.md.') }
    }
    if ($lock) { Remove-Item -LiteralPath $lock -ErrorAction SilentlyContinue }
}
