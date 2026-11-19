# Host dispatcher checks: syntax, argument quoting and validation before Docker.
$ErrorActionPreference='Stop'
$Root=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$scriptFiles = @((Get-ChildItem -LiteralPath (Join-Path $Root 'scripts') -Recurse -Filter '*.ps1')) + @((Get-ChildItem -LiteralPath (Join-Path $Root 'apps') -Recurse -Filter '*.ps1'))
foreach ($file in $scriptFiles) {
    $tokens=$null; $errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw "PowerShell syntax check failed: $($file.FullName)" }
}
. (Join-Path $Root 'scripts/terminal.ps1')
foreach ($case in @(
    @{Input='';Expected='""'},
    @{Input='a b';Expected='"a b"'},
    @{Input='a"b';Expected='"a\"b"'},
    @{Input='C:\path with space\';Expected='"C:\path with space\\"'}
)) {
    if ((ConvertTo-NativeArgument $case.Input) -cne $case.Expected) { throw 'Argument quoting failed.' }
}
$powerShell=(Get-Process -Id $PID).Path
$launcher=Join-Path $Root 'scripts/cmdc.ps1'
foreach ($parameters in @(
    @('setup'),
    @('setup','--app','unknown'),
    @('setup','--app','oscar','--app','pretix'),
    @('destroy','--app','pretix'),
    @('destroy','--app','nopcommerce'),
    @('destroy','--app','prestashop'),
    @('destroy','--app','woocommerce'),
    @('destroy','--app','prestashop','--yes','--unknown'),
    @('apps','--unknown'),
    @('backup','--app','nopcommerce','unsupported','--accept-resource-risk'),
    @('backup','--app','prestashop','unsupported','--accept-resource-risk'),
    @('backup','--app','woocommerce','unsupported','--accept-resource-risk'),
    @('setup','--app','wowy','--accept-resource-risk')
)) {
    $info=[Diagnostics.ProcessStartInfo]::new()
    $info.FileName=$powerShell
    $all=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$launcher)+$parameters
    $info.Arguments=(($all|ForEach-Object {ConvertTo-NativeArgument $_})-join ' ')
    $info.UseShellExecute=$false
    $info.RedirectStandardOutput=$true
    $info.RedirectStandardError=$true
    $process=[Diagnostics.Process]::new();$process.StartInfo=$info
    [void]$process.Start()
    $out=$process.StandardOutput.ReadToEndAsync();$err=$process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    if ($process.ExitCode -ne 2) { throw 'Invalid selection was accepted.' }
    if (($out.Result+$err.Result)-match 'CategoryInfo|FullyQualifiedErrorId') { throw 'Raw PowerShell error record was printed.' }
    $process.Dispose()
}
Write-Output 'PASS: syntax, quoting and invalid app selection checks.'
Write-Output 'Engine locks, app switching, native progress and spinner need Docker/Windows integration checks.'
