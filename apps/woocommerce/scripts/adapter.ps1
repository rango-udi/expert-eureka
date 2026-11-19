# Forward a guarded selection without invoking WSL or host language runtimes.
& (Join-Path $PSScriptRoot '../../../scripts/commerce/adapter.ps1') @args
exit $LASTEXITCODE
