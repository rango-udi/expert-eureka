# Read only the selected app local diagnostics; Docker is not required.
param([Parameter(Mandatory=$true)][string]$Application)
$ErrorActionPreference='Stop'
try {
    if ($Application -notin @('oscar','pretix','shuup','wowy','nopcommerce','prestashop','woocommerce')) { throw 'Select a registered app.' }
    $base=Join-Path (Split-Path -Parent $PSScriptRoot) ('apps/'+$Application)
    $envFile=Join-Path $base '.env'
    $runtime=Join-Path $base '.runtime'
    foreach ($path in @($envFile,$runtime)) {
        if ((Test-Path -LiteralPath $path) -and ((Get-Item -Force -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Diagnostic paths must not be filesystem links.' }
    }
    $secrets=@()
    if (Test-Path -LiteralPath $envFile -PathType Leaf) {
        foreach ($line in Get-Content -LiteralPath $envFile) {
            if ($line -match '^[A-Z_]*(?:PASSWORD|SECRET|TOKEN|KEY)[A-Z_]*=(.*)$' -and $Matches[1].Length -ge 4) { $secret=$Matches[1].Trim().Trim([char[]]@('"',"'")); if ($secret.Length -ge 4) { $secrets+=,$secret } }
        }
    }
    $found=$false
    foreach ($name in @('prestashop-install.log','seed-diagnostic.log','django-migrate.log','django-seed_demo.log','django-collectstatic.log','django-reindex_product_catalog.log','maintenance-errors.log','server-errors.log','data/request-errors.log','data/request-errors.log')) {
        $path=Join-Path $runtime $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
        if ((Get-Item -Force -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Diagnostic files must not be filesystem links.' }
        $found=$true
        Write-Output "`nDiagnostic: apps/$Application/.runtime/$name (last 120 lines)"
        foreach ($line in Get-Content -LiteralPath $path -Tail 120) {
            $safe=$line
            foreach ($value in $secrets) { $safe=$safe.Replace($value,'[hidden]') }
            Write-Output $safe
        }
    }
    if (-not $found) { Write-Output "No backend diagnostic is available under apps/$Application/.runtime. Keep the task log; rerun the failing operation after correcting configuration." }
    Write-Output "`nKnown configured secrets were hidden. Review diagnostics before sharing."
    exit 0
} catch { [Console]::Error.WriteLine('[ERROR] '+$_.Exception.Message); exit 2 }
