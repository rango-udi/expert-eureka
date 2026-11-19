# Use the same native services and task order as the POSIX coordinator.
$ErrorActionPreference='Stop'
$app=$env:CMDC_GUARDED_APP
if ($app -notin @('nopcommerce','prestashop','woocommerce')) { Write-Host '[ERROR] Use root cmdc with a commerce --app selection.'; exit 2 }
$RepositoryRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$Root=Join-Path $RepositoryRoot ('apps/'+$app)
Set-Location -LiteralPath $Root
. (Join-Path $RepositoryRoot 'scripts/terminal.ps1')
. (Join-Path $RepositoryRoot 'scripts/memory_policy.ps1')
Initialize-Terminal
$env:COMPOSE_PARALLEL_LIMIT='1'
$command=if ($args.Count) { [string]$args[0] } else { 'help' }
$options=@($args | Select-Object -Skip 1)
function Stop-Commerce {
    param([string]$Message,[int]$Code=2)
    Write-TerminalMessage ERROR $Message
    exit $Code
}
function Stop-Cmdc {
    param([string]$Message,[int]$ExitCode=2)
    Stop-Commerce $Message $ExitCode
}
if ($command -in @('setup','bootstrap','init','start','up','restart','robot-init','robot','env','validate')) {
    $probe=Invoke-DockerConsole -Arguments @('compose','version','--short') -QuietLabel 'Check Docker Compose' -CaptureResult
    $version=$null
    $textVersion=($probe.Stdout.Trim() -replace '^v','') -replace '-.*$',''
    if ($probe.ExitCode -ne 0 -or -not [version]::TryParse($textVersion,[ref]$version) -or $version -lt [version]'2.24.0') { Stop-Commerce 'Native commerce requires Docker Compose 2.24.0 or newer. No image was prepared.' }
}
if ($app -eq 'nopcommerce' -and $command -in @('setup','bootstrap','init','start','up','restart','robot-init','robot','env','validate')) {
    $architecture=Read-EngineInfo '{{.Architecture}}'
    if ($architecture -notin @('amd64','x86_64')) { Stop-Commerce 'The locked nopCommerce release requires Linux amd64. No image was prepared; use a supported engine or choose another app.' }
}
function Invoke-Commerce {
    param([string[]]$Arguments,[string]$Label='')
    $all=@('compose','--project-name',('robot-web-'+$app),'--project-directory',$Root,'-f',(Join-Path $Root 'compose.yaml'))+$Arguments
    if ($Label) { Write-TerminalMessage RUN $Label }
    $code=Invoke-DockerConsole -Arguments $all -QuietLabel $Label
    if ($code -ne 0) { Stop-Commerce ("Native commerce step failed (exit $code). Run cmdc.cmd logs --app $app. Keep .env and volumes before retrying.") $code }
    if ($Label) { Write-TerminalMessage OK $Label }
}
function Initialize-Settings {
    foreach ($path in @('.runtime','.env')) {
        $full=Join-Path $Root $path
        if ((Test-Path -LiteralPath $full) -and ((Get-Item -Force -LiteralPath $full).Attributes -band [IO.FileAttributes]::ReparsePoint)) { Stop-Commerce 'Runtime and environment paths must not be filesystem links.' }
    }
    [void][IO.Directory]::CreateDirectory((Join-Path $Root '.runtime'))
    Test-Preflight
    $code=Invoke-DockerConsole -Arguments @('image','inspect','python:3.12-slim-bookworm') -QuietLabel 'Check bootstrap image'
    if ($code -ne 0) {
        $code=Invoke-DockerConsole -Arguments @('pull','python:3.12-slim-bookworm')
        if ($code -ne 0) { Stop-Commerce 'Cannot prepare the configuration bootstrap image.' $code }
    }
    $mount='type=bind,source='+$Root+',target=/workspace'
    $helper='type=bind,source='+(Join-Path $RepositoryRoot 'scripts/commerce')+',target=/opt/commerce,readonly'
    $code=Invoke-DockerConsole -Arguments @('run','--rm','--network','none','--memory','128m','--pids-limit','64','--label',('org.robot-web.app='+$app),'--label',('com.docker.compose.project=robot-web-'+$app),'--label',('com.docker.compose.project.working_dir='+$Root),'--label','com.docker.compose.oneoff=True','--mount',$mount,'--mount',$helper,'python:3.12-slim-bookworm','python','/opt/commerce/commands.py','env',$app) -QuietLabel 'Create private configuration'
    if ($code -ne 0) { Stop-Commerce 'Cannot create .env from .env.template. Keep existing data and restore private configuration if missing.' $code }
}
function Test-Initialized {
    if (-not (Test-Path '.env' -PathType Leaf) -or -not (Test-Path '.runtime/initialized.json' -PathType Leaf)) { Stop-Commerce "Application is not initialized. Run cmdc.cmd setup --app $app." }
}
function Initialize-Commerce {
    Invoke-Commerce @('run','--rm','--no-deps','--pull','never','tools','validate',$app) 'Validate shared data'
    Invoke-Commerce @('up','-d','--no-build','--pull','never','--wait','db') 'Start private database'
    Invoke-Commerce @('up','-d','--no-build','--pull','never','app') 'Start native application'
    if ($app -eq 'nopcommerce') { Invoke-Commerce @('run','--rm','--no-deps','--pull','never','tools','init',$app) 'Install and seed nopCommerce' }
    else {
        Invoke-Commerce @('up','-d','--no-build','--pull','never','--wait','app') 'Wait for native application files'
        Invoke-Commerce @('stop','app') 'Stop writers before initialization'
        Invoke-Commerce @('run','--rm','--no-deps','--pull','never','--entrypoint','php','app','/opt/adapter/initialize.php') 'Install and seed storefront'
    }
    Invoke-Commerce @('up','-d','--no-build','--pull','never','--wait','app') 'Verify storefront readiness'
    Invoke-Commerce @('run','--rm','--no-deps','--pull','never','tools','complete',$app) 'Record successful initialization'
}
switch ($command) {
    { $_ -in @('setup','bootstrap') } {
        foreach ($value in $options) { if ($value -notin @('--with-robot','--run-tests')) { Stop-Commerce "Unknown setup option: $value" } }
        Test-Preflight; Initialize-Settings
        Invoke-Commerce @('pull','db')
        Invoke-Commerce @('build','app','tools')
        Initialize-Commerce
        if ($options -contains '--with-robot' -or $options -contains '--run-tests') { Invoke-Commerce @('build','robot') }
        if ($options -contains '--run-tests') { Invoke-Commerce @('run','--rm','--no-deps','--pull','never','robot') 'Read-only browser smoke checks' }
        Write-TerminalMessage OK "Setup completed. Run cmdc.cmd urls --app $app."
    }
    'init' { if ($options.Count) { Stop-Commerce 'init takes no options.' }; Initialize-Settings; Test-Preflight; Initialize-Commerce }
    { $_ -in @('start','up','restart') } {
        if ($options.Count) { Stop-Commerce 'Startup takes no options.' }
        Test-Initialized; Test-Preflight
        if ($command -eq 'restart') { Invoke-Commerce @('stop','app') 'Stop native application' }
        Invoke-Commerce @('up','-d','--no-build','--pull','never','--wait','db') 'Start private database'
        Invoke-Commerce @('up','-d','--no-build','--pull','never','--wait','app') 'Start native application'
    }
    'robot-init' { Initialize-Settings; Test-Preflight; Invoke-Commerce @('build','robot') }
    'robot' {
        if ($options.Count) { Stop-Commerce 'Native commerce smoke suites take no additional options.' }
        Test-Initialized; Test-Preflight; Invoke-Commerce @('build','robot')
        Invoke-Commerce @('run','--rm','--no-deps','--pull','never','robot') 'Read-only browser smoke checks'
    }
    'env' { if ($options.Count -gt 1 -or ($options.Count -eq 1 -and $options[0] -ne 'init')) { Stop-Commerce 'Use env init. Read private .env locally to view credentials.' }; Initialize-Settings }
    'validate' { Initialize-Settings; Invoke-Commerce @('build','tools'); Invoke-Commerce @('run','--rm','--no-deps','--pull','never','tools','validate',$app) 'Validate shared data' }
    'status' { Invoke-Commerce @('ps') }
    'resources' { Invoke-Commerce @('stats','--no-stream') }
    'logs' { Invoke-Commerce @('logs','--tail','100','app','db') }
    'stop' { Invoke-Commerce @('stop') 'Stop application services' }
    'down' { Invoke-Commerce @('--profile','*','down','--remove-orphans') 'Remove application containers' }
    'destroy' {
        foreach ($option in $options) { if ($option -notin @('--yes','--include-files')) { Stop-Commerce 'Use destroy --yes [--include-files].' } }
        if ($options -notcontains '--yes') { Stop-Commerce 'destroy removes the selected database and media. Add --yes after reviewing the scope.' }
        $paths=@('.runtime','.runtime/initialized.json')
        if ($options -contains '--include-files') { $paths+=@('.env','reports','backups') }
        foreach ($relative in $paths) {
            $path=Join-Path $Root $relative
            if ((Test-Path -LiteralPath $path) -and ((Get-Item -Force -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint)) { Stop-Commerce 'Generated file paths must not be filesystem links.' }
        }
        $probe=Invoke-DockerConsole -Arguments @('volume','ls','--format','{{.Name}}') -QuietLabel 'Inspect selected volumes' -CaptureResult
        if ($probe.ExitCode -ne 0) { Stop-Commerce 'Cannot inspect volumes before destroy.' }
        $volumes=$probe.Stdout.Trim() -split "`r?`n"
        foreach ($suffix in @('database_data','app_data','product_media')) {
            $volume='robot-web-'+$app+'_'+$suffix
            if ($volumes -notcontains $volume) { continue }
            $owner=Invoke-DockerConsole -Arguments @('volume','inspect','--format','{{index .Labels "org.robot-web.workspace"}}',$volume) -QuietLabel 'Verify volume workspace' -CaptureResult
            $identity=Invoke-DockerConsole -Arguments @('volume','inspect','--format','{{index .Labels "org.robot-web.app"}}',$volume) -QuietLabel 'Verify volume application' -CaptureResult
            if ($owner.ExitCode -ne 0 -or $identity.ExitCode -ne 0 -or $owner.Stdout.Trim() -ne $RepositoryRoot -or $identity.Stdout.Trim() -ne $app) { Stop-Commerce 'Volume ownership does not match the selected workspace and app. No resources were deleted.' }
        }
        Invoke-Commerce @('--profile','*','down','--remove-orphans','--volumes') 'Remove selected application and data volumes'
        $marker=Join-Path $Root '.runtime/initialized.json'
        if (Test-Path -LiteralPath $marker) { Remove-Item -LiteralPath $marker -Force }
        if ($options -contains '--include-files') {
            foreach ($relative in @('.env','reports','backups')) {
                $path=Join-Path $Root $relative
                if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force -Recurse }
            }
            [void][IO.Directory]::CreateDirectory((Join-Path $Root 'reports'))
        }
        Write-TerminalMessage OK "Destroyed $app data. Source, shared fuzcake-data, diagnostic logs and image cache were kept."
    }
    'urls' {
        Test-Initialized
        $line=@(Get-Content '.env' | Where-Object { $_ -match '^HTTP_PORT=[0-9]+$' })
        if ($line.Count -ne 1) { Stop-Commerce 'HTTP_PORT must be one numeric port in .env.' }
        $port=$line[0].Substring(10)
        $admin=if ($app -eq 'nopcommerce') { 'Admin' } elseif ($app -eq 'prestashop') { 'control' } else { 'wp-admin' }
        Write-Output "Storefront: http://127.0.0.1:$port/`nAdministration: http://127.0.0.1:$port/$admin/"
    }
    'config' { Invoke-Commerce @('config','--no-interpolate') }
    { $_ -in @('versions','source') } { Get-Content 'config/source-lock.json' }
    default { Stop-Commerce "Command $command is not supported by the native commerce adapter. See documents/guides/NATIVE_COMMERCE.md; no data was changed." }
}
exit 0
