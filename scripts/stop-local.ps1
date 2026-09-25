$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot '.local\local-processes.json'
if (Test-Path -LiteralPath $pidFile) {
    $processes = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
    foreach ($processId in @($processes.backend, $processes.frontend)) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
        if ($process -and ($process.CommandLine -match 'backend.main:app|node_modules/vite/bin/vite.js')) {
            Stop-Process -Id $processId
        }
    }
    Remove-Item -LiteralPath $pidFile
    Write-Output 'Stopped the recorded EICC local servers.'
}
