# Reveal a bundled guide in Explorer and request foreground focus on its window.
function Open-WslMemoryHelp {
    param([string]$ProjectRoot)
    $path = Join-Path $ProjectRoot 'documents\helps\WSL_VM_MEMORY_LIMIT.md'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw 'The bundled WSL VM memory guide is missing. Extract the complete project ZIP again.'
    }
    $path = (Resolve-Path -LiteralPath $path).Path
    Write-Output ('Help file: ' + $path)
    Write-Output ('Help link: ' + ([System.Uri]$path).AbsoluteUri)
    try {
        Start-Process -FilePath explorer.exe -ArgumentList ('/select,"{0}"' -f $path) | Out-Null
        $shell = New-Object -ComObject Shell.Application
        if (-not ('Cmdc.HelpWindow' -as [type])) {
            Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace Cmdc {
    public static class HelpWindow {
        [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr window, int command);
        [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr window);
        [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    }
}
'@
        }
        $folder = Split-Path -Parent $path
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            foreach ($window in @($shell.Windows())) {
                try {
                    if ($window.Document.Folder.Self.Path -ne $folder) { continue }
                    $item = $window.Document.Folder.ParseName((Split-Path -Leaf $path))
                    if ($null -eq $item) { continue }
                    $window.Document.SelectItem($item, 29)
                    $handle = [IntPtr]$window.HWND
                    [void][Cmdc.HelpWindow]::ShowWindowAsync($handle, 9)
                    [void][Cmdc.HelpWindow]::SetForegroundWindow($handle)
                    if ([Cmdc.HelpWindow]::GetForegroundWindow() -eq $handle) {
                        Write-Output 'Memory guide selected in File Explorer.'
                        return
                    }
                } catch {
                    # Explorer windows can disappear while enumerating; retry briefly.
                }
            }
            Start-Sleep -Milliseconds 100
        }
        [Console]::Error.WriteLine('Help file: use the path or link above to read the guide.')
    } catch {
        [Console]::Error.WriteLine('File Explorer is unavailable. Open the help file using the path or link above.')
    }
}
