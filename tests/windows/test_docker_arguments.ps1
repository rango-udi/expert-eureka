# Run in Windows PowerShell 5.1: exercise the real native-process argument boundary.
$ErrorActionPreference='Stop'
if ($env:OS -ne 'Windows_NT' -or $PSVersionTable.PSEdition -eq 'Core') {
    throw 'Run this regression with Windows PowerShell 5.1 (powershell.exe).'
}
$RepositoryRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('robot-web-arguments-'+[guid]::NewGuid().ToString('N'))
$workspace=Join-Path $temporary 'workspace with spaces'
$bin=Join-Path $temporary 'bin'
$state=Join-Path $temporary 'owner.txt'
$marker=Join-Path $temporary 'adapter-ran.txt'
$savedPath=$env:PATH
$variableNames=@('ROBOT_TEST_OWNER','ROBOT_TEST_WORKSPACE','ROBOT_TEST_MODE','ROBOT_TEST_MARKER','ROBOT_TEST_CALLS','CMDC_UI','NO_COLOR')
$savedVariables=@{}
foreach ($name in $variableNames) { $savedVariables[$name]=[Environment]::GetEnvironmentVariable($name,'Process') }
try {
    [void][IO.Directory]::CreateDirectory($bin)
    [void][IO.Directory]::CreateDirectory((Join-Path $workspace 'scripts'))
    [void][IO.Directory]::CreateDirectory((Join-Path $workspace 'apps/pretix/scripts'))
    [void][IO.Directory]::CreateDirectory((Join-Path $workspace 'fuzcake-data/records'))
    [void][IO.Directory]::CreateDirectory((Join-Path $workspace 'fuzcake-data/fuzcake_data'))
    [IO.File]::WriteAllText((Join-Path $workspace 'fuzcake-data/records/app-profiles.json'),'{}')
    [IO.File]::WriteAllText((Join-Path $workspace 'fuzcake-data/fuzcake_data/__init__.py'),'')
    foreach ($file in @('cmdc.ps1','terminal.ps1','pretix_safety.ps1')) {
        Copy-Item -LiteralPath (Join-Path $RepositoryRoot ('scripts/'+$file)) -Destination (Join-Path $workspace ('scripts/'+$file))
    }
    # Isolate the dispatcher: app work and doctor are markers, never real Docker work.
    [IO.File]::WriteAllText((Join-Path $workspace 'scripts/system.ps1'),'exit 0')
    [IO.File]::WriteAllText((Join-Path $workspace 'apps/pretix/scripts/adapter.ps1'),'[IO.File]::WriteAllText($env:ROBOT_TEST_MARKER,($args -join "|")); exit 0')
    [IO.File]::WriteAllText((Join-Path $workspace 'apps/pretix/.env'),'POSTGRES_PASSWORD=test-only')
    $source=@'
using System;
using System.IO;
public static class DockerArgumentDouble {
    static string Env(string key) { return Environment.GetEnvironmentVariable(key) ?? ""; }
    public static int Main(string[] a) {
        string mode=Env("ROBOT_TEST_MODE"), owner=Env("ROBOT_TEST_OWNER");
        File.AppendAllText(Env("ROBOT_TEST_CALLS"),String.Join("\t",a)+Environment.NewLine);
        if(a.Length>=2 && a[0]=="volume" && a[1]=="ls") {
            if(mode=="data") Console.WriteLine("robot-web-pretix_postgres_data");
            return 0;
        }
        if(a.Length>=2 && a[0]=="volume" && a[1]=="create") {
            foreach(string value in a) {
                if(value.StartsWith("org.robot-web.owner=") && !File.Exists(owner))
                    File.WriteAllText(owner,value.Substring("org.robot-web.owner=".Length));
                if(value.StartsWith("org.robot-web.workspace=") && value.Substring("org.robot-web.workspace=".Length)!=Env("ROBOT_TEST_WORKSPACE")) return 66;
            }
            Console.WriteLine("robot-web-operation-lock"); return 0;
        }
        if(a.Length>=5 && a[0]=="volume" && a[1]=="inspect") {
            bool data=a[a.Length-1]!="robot-web-operation-lock";
            string expected=data ? "{{index .Labels \"org.robot-web.workspace\"}}" : "{{index .Labels \"org.robot-web.owner\"}}";
            if(a[3]!=expected || mode=="inspect-fail") {
                Console.Error.WriteLine("template parsing error: template: :1: function org not defined"); return 64;
            }
            Console.WriteLine(data ? Env("ROBOT_TEST_WORKSPACE") : File.ReadAllText(owner)); return 0;
        }
        if(a.Length>=4 && a[0]=="ps") {
            string expected="{{.Label \"org.robot-web.app\"}}|{{.Label \"com.docker.compose.project\"}}|{{.Label \"com.docker.compose.project.working_dir\"}}|{{.Label \"com.docker.compose.oneoff\"}}|{{.State}}";
            if(a[3]!=expected || mode=="ps-fail") { Console.Error.WriteLine("Container metadata failed"); return 65; }
            return 0;
        }
        if(a.Length>=3 && a[0]=="volume" && a[1]=="rm") { File.Delete(owner); return 0; }
        Console.Error.WriteLine("Unexpected fake Docker command"); return 67;
    }
}
'@
    # This executable sees actual argv after Windows native quoting, unlike a PS function mock.
    Add-Type -TypeDefinition $source -Language CSharp -OutputAssembly (Join-Path $bin 'docker.exe') -OutputType ConsoleApplication
    $env:PATH=$bin+';'+$savedPath
    $env:ROBOT_TEST_OWNER=$state
    $env:ROBOT_TEST_WORKSPACE=$workspace
    $env:ROBOT_TEST_MARKER=$marker
    $env:ROBOT_TEST_CALLS=Join-Path $temporary 'calls.txt'
    $env:CMDC_UI='plain';$env:NO_COLOR='1'
    . (Join-Path $RepositoryRoot 'scripts/terminal.ps1')
    foreach ($mode in @('success','data','foreign','inspect-fail','ps-fail')) {
        Remove-Item -LiteralPath $state,$marker,$env:ROBOT_TEST_CALLS -Force -ErrorAction SilentlyContinue
        $env:ROBOT_TEST_MODE=$mode
        if ($mode -eq 'foreign') { [IO.File]::WriteAllText($state,'another-owner') }
        $info=[Diagnostics.ProcessStartInfo]::new()
        $info.FileName=Join-Path $PSHOME 'powershell.exe'
        $arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $workspace 'scripts/cmdc.ps1'),'down','--app','pretix')
        $info.Arguments=(($arguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' ')
        $info.UseShellExecute=$false
        $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
        $process=[Diagnostics.Process]::new();$process.StartInfo=$info
        try {
            [void]$process.Start()
            $out=$process.StandardOutput.ReadToEndAsync();$err=$process.StandardError.ReadToEndAsync()
            $process.WaitForExit();$text=$out.Result+$err.Result;$exitCode=$process.ExitCode
        } finally { $process.Dispose() }
        if ($mode -in @('success','data')) {
            if ($exitCode -ne 0 -or -not (Test-Path $marker) -or (Test-Path $state)) { throw "Native quote/cleanup regression: $mode; $text" }
        } else {
            if ($exitCode -ne 2 -or (Test-Path $marker)) { throw "Metadata failure reached adapter: $mode; $text" }
            if ($mode -eq 'foreign') {
                if ((Get-Content -Raw $state) -ne 'another-owner' -or $text -notmatch 'Another workspace operation owns') { throw 'Foreign engine lock was not preserved.' }
            } elseif ($text -match 'Another workspace operation owns') { throw 'A probe failure was misreported as lock contention.' }
            if ($mode -eq 'inspect-fail' -and ($text -notmatch 'Cannot verify Docker operation lock ownership' -or -not (Test-Path $state))) { throw 'Unreadable lock metadata was not preserved for recovery.' }
            if ($mode -eq 'ps-fail' -and ($text -notmatch 'Cannot inspect Docker container ownership' -or (Test-Path $state))) { throw 'Container metadata failure did not release the verified owned lock.' }
        }
        if ($text -match 'CategoryInfo|FullyQualifiedErrorId|template parsing error') { throw 'Raw diagnostic output leaked to the terminal.' }
        if (Test-Path (Join-Path $workspace '.runtime/app-operation.lock')) { throw 'Workspace lock was not released.' }
        Write-Output "PASS: native Docker argument boundary and lock handling: $mode"
    }
} finally {
    $env:PATH=$savedPath
    foreach ($name in $variableNames) { [Environment]::SetEnvironmentVariable($name,$savedVariables[$name],'Process') }
    Remove-Item -LiteralPath $temporary -Recurse -Force -ErrorAction SilentlyContinue
}
