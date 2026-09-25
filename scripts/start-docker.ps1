param([string]$Distribution = 'Ubuntu')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
python scripts/init_env.py
if ($LASTEXITCODE -ne 0) { throw 'Private configuration initialization failed' }
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose up --build -d --wait
} else {
    $logDir = Join-Path $projectRoot '.local'
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    # WSL system services alone do not keep the distribution alive.
    $pidFile = Join-Path $logDir 'wsl-keepalive.pid'
    $keepalive = $null
    if (Test-Path -LiteralPath $pidFile) {
        $processId = [int](Get-Content -LiteralPath $pidFile)
        $candidate = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
        if ($candidate -and $candidate.Name -eq 'wsl.exe' -and $candidate.CommandLine -match 'sleep infinity') { $keepalive = $candidate }
    }
    if (-not $keepalive) {
        $keepalive = Start-Process -FilePath 'wsl.exe' -ArgumentList '-d',$Distribution,'--exec','sleep','infinity' -WindowStyle Hidden -PassThru
        $keepalive.Id | Set-Content -LiteralPath $pidFile
    }
    wsl -d $Distribution -u root --cd $projectRoot -- docker compose up --build -d --wait
}
if ($LASTEXITCODE -ne 0) { throw 'Docker startup failed; inspect docker compose logs' }
Write-Output 'EICC is available at http://127.0.0.1:8080'
