# Verify isolated image-selection decisions; no Docker Engine or image downloads are used.
$ErrorActionPreference='Stop'
$Root=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$tokens=$null;$errors=$null
$source=Join-Path $Root 'apps/pretix/scripts/adapter.ps1'
$tree=[System.Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Pretix adapter syntax check failed.' }
foreach ($name in @('Ensure-BootstrapImage','Pull-ProjectImages')) {
    $definition=$tree.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name},$true)
    if (-not $definition) { throw "Missing image preparation function: $name" }
    . ([scriptblock]::Create($definition.Extent.Text))
}
$script:DockerCalls=[Collections.Generic.List[object]]::new()
$script:ComposeCalls=[Collections.Generic.List[object]]::new()
$script:Cached=$true
$script:FailPull=$false
function Invoke-Docker {
    param($Context,[string[]]$Arguments,[switch]$Capture,[switch]$AllowFailure)
    $script:DockerCalls.Add($Arguments)
    if ($Arguments[0] -eq 'image') {
        $code=if ($script:Cached) { 0 } else { 1 }
        return [pscustomobject]@{ExitCode=$code;Stdout='';Stderr=''}
    }
    if ($script:FailPull) { throw 'Simulated download failure' }
}
function Invoke-Compose {
    param($Context,[string[]]$Arguments)
    $script:ComposeCalls.Add($Arguments)
}
function Write-TerminalMessage { param([string]$Kind,[string]$Message) }
$context=[pscustomobject]@{BootstrapImage='python:test@sha256:exact-digest'}
Ensure-BootstrapImage -Context $context
if ($script:DockerCalls.Count -ne 1 -or $script:DockerCalls[0][-1] -ne $context.BootstrapImage) { throw 'Cached helper should only inspect the exact pinned reference.' }
$script:DockerCalls.Clear();$script:Cached=$false
Ensure-BootstrapImage -Context $context
if ($script:DockerCalls.Count -ne 2 -or $script:DockerCalls[1][0] -ne 'pull') { throw 'Missing helper was not downloaded.' }
$script:FailPull=$true;$failed=$false
try { Ensure-BootstrapImage -Context $context } catch { $failed=$_.Exception.Message -eq 'Simulated download failure' }
if (-not $failed) { throw 'A failed helper download was swallowed.' }
foreach ($selection in @('server','robot','all')) {
    $script:ComposeCalls.Clear()
    Pull-ProjectImages -Context $context -Selection $selection
    if ($script:ComposeCalls.Count -ne 1) { throw 'Expected one Compose image preparation request.' }
    $arguments=$script:ComposeCalls[0]
    if (($arguments[0..4] -join ' ') -ne '--profile tools pull --policy missing') { throw 'Cached service image policy was not preserved.' }
    if ($selection -eq 'server' -and $arguments -contains 'robot') { throw 'Server preparation unexpectedly included the browser.' }
    if ($selection -eq 'robot' -and $arguments.Count -ne 6) { throw 'Browser preparation unexpectedly included other services.' }
    if ($selection -eq 'all' -and ($arguments -notcontains 'robot' -or $arguments -notcontains 'git')) { throw 'Explicit all selection omitted requested tools.' }
}
Write-Output 'PASS: cached and missing helper, pull failure propagation, and service image selection.'
