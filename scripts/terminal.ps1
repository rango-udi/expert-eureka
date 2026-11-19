# Preserve native console handles so Docker can redraw its own progress display.
function Enable-TerminalRendering {
    # Classic Windows consoles need VT processing before Docker emits cursor-control sequences.
    if ($env:OS -ne 'Windows_NT') { return $true }
    try {
        if (-not ('Cmdc.NativeConsole' -as [type])) {
            Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace Cmdc {
    public static class NativeConsole {
        [DllImport("kernel32.dll", SetLastError=true)]
        public static extern IntPtr GetStdHandle(int handle);
        [DllImport("kernel32.dll", SetLastError=true)]
        public static extern bool GetConsoleMode(IntPtr handle, out uint mode);
        [DllImport("kernel32.dll", SetLastError=true)]
        public static extern bool SetConsoleMode(IntPtr handle, uint mode);
    }
}
'@
        }
        foreach ($number in @(-11,-12)) {
            $handle=[Cmdc.NativeConsole]::GetStdHandle($number)
            [uint32]$flags=0
            if (-not [Cmdc.NativeConsole]::GetConsoleMode($handle,[ref]$flags)) { return $false }
            if (-not [Cmdc.NativeConsole]::SetConsoleMode($handle,($flags -bor 4 -bor 1))) { return $false }
        }
        return $true
    } catch { return $false }
}
function Initialize-Terminal {
    $mode = if ($env:CMDC_UI) { $env:CMDC_UI } else { 'rich' }
    if ($mode -notin @('auto','rich','plain')) { Stop-Cmdc 'CMDC_UI must be auto, rich or plain.' }
    $console = -not [Console]::IsOutputRedirected -and -not [Console]::IsErrorRedirected -and $env:TERM -ne 'dumb' -and -not $env:CI
    $script:RichTerminal = $mode -eq 'rich' -and $console
    if ($mode -eq 'auto') {
        $script:RichTerminal = -not [Console]::IsOutputRedirected -and -not [Console]::IsErrorRedirected -and $env:TERM -ne 'dumb' -and -not $env:CI
    }
    if (Test-Path Env:NO_COLOR) { $script:RichTerminal = $false }
    if ($script:RichTerminal -and -not (Enable-TerminalRendering)) { $script:RichTerminal=$false }
    if (-not $env:BUILDKIT_TTY_LOG_LINES) { $env:BUILDKIT_TTY_LOG_LINES = '6' }
    if ($script:RichTerminal) {
        $env:COMPOSE_ANSI = 'always'
        $env:COMPOSE_PROGRESS = 'tty'
        $env:BUILDKIT_PROGRESS = 'tty'
    } else {
        $env:COMPOSE_ANSI = 'never'
        $env:COMPOSE_PROGRESS = 'plain'
        $env:BUILDKIT_PROGRESS = 'plain'
    }
}
function Write-TerminalMessage {
    param([string]$Kind, [string]$Message)
    if ($script:RichTerminal) {
        $color = switch ($Kind) { 'OK' { 'Green' } 'ERROR' { 'Red' } 'WARNING' { 'Yellow' } default { 'Cyan' } }
        Write-Host "[$Kind] " -ForegroundColor $color -NoNewline
        Write-Host $Message
    } else { [Console]::Error.WriteLine("[$Kind] $Message") }
}
function Get-StageLabel {
    param([string[]]$Arguments)
    $line = $Arguments -join ' '
    switch -Wildcard ($line) {
        'build tools' { return 'Build application image' }
        'build robot' { return 'Build browser image' }
        '*tools init' { return 'Initialize database and store data' }
        '*tools validate*' { return 'Validate application' }
        '*tools generate*' { return 'Generate test cases' }
        'run* report*' { return 'Export customer report' }
        'run* robot*' { return 'Run browser tests' }
        '*--wait shuup' { return 'Start Shuup and wait for readiness' }
        '*--wait wowy' { return 'Start Wowy and wait for readiness' }
        '*--wait oscar' { return 'Start Oscar and wait for readiness' }
        'stop*' { return 'Stop application' }
        '*down --remove-orphans*' { return 'Remove project containers and network' }
        'run *' { return 'Run container task' }
        default { return '' }
    }
}
function Write-WaitFrame {
    param([string]$Glyph,[string]$Label,[double]$ElapsedSeconds)
    # Fit one line and right-align the real elapsed duration, including after resize.
    $width=80
    try { if ([Console]::WindowWidth -ge 24) { $width=[Console]::WindowWidth } } catch { }
    $timer=$ElapsedSeconds.ToString('0.0',[Globalization.CultureInfo]::InvariantCulture)+'s'
    $available=[math]::Max(1,$width-$timer.Length-7)
    if ($Label.Length -gt $available) { $Label=$Label.Substring(0,$available) }
    $padding=[math]::Max(1,$width-$Label.Length-$timer.Length-5)
    [Console]::Error.Write(("`r$([char]27)[2K$([char]27)[36m[$Glyph]$([char]27)[0m $Label" + (' '*$padding) + $timer))
}

function ConvertTo-NativeArgument {
    param([AllowEmptyString()][string]$Value)
    # Quote each argument using Windows CRT rules, including quotes and trailing slashes.
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}
function Invoke-DockerConsole {
    param([string[]]$Arguments, [string]$QuietLabel = '', [switch]$CaptureResult)
    $docker = Get-Command docker -ErrorAction Stop
    if ($docker.CommandType -eq 'Application' -and $docker.Source -match '\.exe$') {
        $info = [Diagnostics.ProcessStartInfo]::new()
        $info.FileName = $docker.Source
        $info.Arguments = (($Arguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' ')
        $info.WorkingDirectory = $Root
        $info.UseShellExecute = $false
        $capture = [bool]$QuietLabel -or $CaptureResult.IsPresent
        $info.RedirectStandardOutput = $capture
        $info.RedirectStandardError = $capture
        $info.RedirectStandardInput = $false
        if ($capture) {
            # The launcher owns the waiting row; captured children must not emit terminal redraw frames.
            $info.EnvironmentVariables['COMPOSE_ANSI']='never'
            $info.EnvironmentVariables['COMPOSE_PROGRESS']='plain'
            $info.EnvironmentVariables['BUILDKIT_PROGRESS']='plain'
        }
        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $info
        try {
            [void]$process.Start()
            if ($capture) {
                $outTask = $process.StandardOutput.ReadToEndAsync()
                $errTask = $process.StandardError.ReadToEndAsync()
                $frames = @('|','/','-','\')
                $frame = 0
                $waitTimer=[Diagnostics.Stopwatch]::StartNew()
                try {
                    if ($script:RichTerminal) { [Console]::Error.Write("$([char]27)[?25l") }
                    while (-not $process.WaitForExit(120)) {
                        if ($script:RichTerminal) {
                            Write-WaitFrame -Glyph $frames[$frame % 4] -Label $QuietLabel -ElapsedSeconds $waitTimer.Elapsed.TotalSeconds
                            $frame++
                        }
                    }
                } finally {
                    if ($script:RichTerminal) { [Console]::Error.Write("`r$([char]27)[2K$([char]27)[?25h") }
                }
                $output = $outTask.Result
                $errorOutput = $errTask.Result
                New-Item -ItemType Directory -Force (Join-Path $Root '.runtime') | Out-Null
                $log = Join-Path $Root ('.runtime/task-' + [guid]::NewGuid().ToString('N') + '.log')
                [IO.File]::WriteAllText($log, $output + $errorOutput)
                if ($process.ExitCode -ne 0) { [Console]::Error.WriteLine('Diagnostic output: ' + $log) }
                if ($CaptureResult) { return [pscustomobject]@{ExitCode=$process.ExitCode; Stdout=$output; Stderr=$errorOutput} }
                if ($process.ExitCode -eq 0) {
                    [Console]::Out.Write($output)
                    [Console]::Error.Write($errorOutput)
                } else {
                    foreach ($line in (($output + "`n" + $errorOutput) -split "`r?`n")) {
                        if ($line -match '^(ERROR:|Error:|WARNING:|Review )') { [Console]::Error.WriteLine($line) }
                    }
                }
            } else { $process.WaitForExit() }
            return $process.ExitCode
        } finally { $process.Dispose() }
    }
    # Support shell command wrappers and the function doubles used by launcher tests.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        if ($CaptureResult) {
            $output = & docker @Arguments 2>&1
            return [pscustomobject]@{ExitCode=$LASTEXITCODE; Stdout=($output -join "`n"); Stderr=''}
        }
        & docker @Arguments | Out-Host
        return $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
}

function Invoke-DockerLive {
    param([string[]]$Arguments, [string]$Label)
    # Read both pipes asynchronously and keep the waiting row below live child output.
    $docker=Get-Command docker -ErrorAction Stop
    if ($docker.CommandType -ne 'Application' -or $docker.Source -notmatch '\.exe$') {
        return Invoke-DockerConsole -Arguments $Arguments
    }
    $info=[Diagnostics.ProcessStartInfo]::new()
    $info.FileName=$docker.Source
    $info.Arguments=(($Arguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' ')
    $info.WorkingDirectory=$Root
    $info.UseShellExecute=$false
    $info.RedirectStandardOutput=$true
    $info.RedirectStandardError=$true
    $info.EnvironmentVariables['COMPOSE_ANSI']='never'
    $info.EnvironmentVariables['COMPOSE_PROGRESS']='plain'
    $info.EnvironmentVariables['BUILDKIT_PROGRESS']='plain'
    $process=[Diagnostics.Process]::new()
    $process.StartInfo=$info
    $transcript=[Text.StringBuilder]::new()
    $timer=[Diagnostics.Stopwatch]::StartNew()
    $frames=@('|','/','-','\')
    $frame=0
    try {
        [void]$process.Start()
        $outTask=$process.StandardOutput.ReadLineAsync()
        $errTask=$process.StandardError.ReadLineAsync()
        $outDone=$false
        $errDone=$false
        if ($script:RichTerminal) { [Console]::Error.Write("$([char]27)[?25l") }
        while (-not ($outDone -and $errDone -and $process.HasExited)) {
            while (-not $outDone -and $outTask.IsCompleted) {
                $line=$outTask.Result
                if ($null -eq $line) { $outDone=$true; break }
                if ($script:RichTerminal) { [Console]::Error.Write("`r$([char]27)[2K") }
                [void]$transcript.AppendLine($line)
                [Console]::Out.WriteLine($line)
                $outTask=$process.StandardOutput.ReadLineAsync()
            }
            while (-not $errDone -and $errTask.IsCompleted) {
                $line=$errTask.Result
                if ($null -eq $line) { $errDone=$true; break }
                if ($script:RichTerminal) { [Console]::Error.Write("`r$([char]27)[2K") }
                [void]$transcript.AppendLine($line)
                [Console]::Error.WriteLine($line)
                $errTask=$process.StandardError.ReadLineAsync()
            }
            if (-not $process.HasExited -and $script:RichTerminal) {
                Write-WaitFrame -Glyph $frames[$frame % 4] -Label $Label -ElapsedSeconds $timer.Elapsed.TotalSeconds
                $frame++
            }
            # Bound polling even after the process exits while its final pipe data drains.
            if (-not ($outDone -and $errDone -and $process.HasExited)) {
                [Threading.Thread]::Sleep(120)
            }
        }
        $process.WaitForExit()
        $code=$process.ExitCode
        if ($script:RichTerminal) { [Console]::Error.Write("`r$([char]27)[2K") }
        New-Item -ItemType Directory -Force (Join-Path $Root '.runtime') | Out-Null
        $log=Join-Path $Root ('.runtime/task-' + [guid]::NewGuid().ToString('N') + '.log')
        [IO.File]::WriteAllText($log,$transcript.ToString())
        if ($code -ne 0) { [Console]::Error.WriteLine('Diagnostic output: ' + $log) }
        return $code
    } finally {
        if ($script:RichTerminal) { [Console]::Error.Write("`r$([char]27)[2K$([char]27)[?25h") }
        try { if (-not $process.HasExited) { $process.Kill() } } catch { }
        $timer.Stop()
        $process.Dispose()
    }
}
