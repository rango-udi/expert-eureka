# Run on Windows PowerShell 5.1 or PowerShell 7; no Docker daemon is needed.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../scripts/terminal.ps1')
$saved=[Console]::Error
$writer=[IO.StringWriter]::new()
try {
    [Console]::SetError($writer)
    Write-WaitFrame -Glyph '/' -Label ('Initialize database and store data '*8) -ElapsedSeconds 12.94
    $visible=[regex]::Replace($writer.ToString(),"$([char]27)\[[0-9;?]*[A-Za-z]",'').TrimStart("`r")
    $width=80
    try { if ([Console]::WindowWidth -ge 24) { $width=[Console]::WindowWidth } } catch { }
    if ($visible.Length -ne $width-1 -or -not $visible.EndsWith('12.9s')) { throw 'The waiting frame must fit one row with its timer at the right edge.' }
    $writer.GetStringBuilder().Clear() | Out-Null
    Write-WaitFrame -Glyph '-' -Label 'Waiting' -ElapsedSeconds 14.21
    if (-not $writer.ToString().EndsWith('14.2s')) { throw 'The waiting timer did not advance.' }
} finally {
    [Console]::SetError($saved)
    $writer.Dispose()
}
Write-Output 'PASS: Windows wait-frame duration, truncation and right alignment.'

if ($env:OS -eq 'Windows_NT' -and -not [Console]::IsOutputRedirected -and -not [Console]::IsErrorRedirected) {
    if (Enable-TerminalRendering) {
        foreach ($number in @(-11,-12)) {
            [uint32]$flags=0
            $handle=[Cmdc.NativeConsole]::GetStdHandle($number)
            if (-not [Cmdc.NativeConsole]::GetConsoleMode($handle,[ref]$flags) -or ($flags -band 4) -eq 0) { throw 'VT processing was not enabled for inherited Docker console output.' }
        }
    }
}
