$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
& (Join-Path $PSScriptRoot 'stop-local.ps1')
uv sync --frozen
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed' }
uv run python -m backend.seed
if ($LASTEXITCODE -ne 0) { throw 'Demo initialization failed' }
npm --prefix frontend ci
if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed' }
foreach ($port in @(8000, 5173)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is occupied by another process; stop that service before starting EICC"
    }
}
$logDir = Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$backend = Start-Process -FilePath (Join-Path $projectRoot '.venv\Scripts\python.exe') -ArgumentList '-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'backend.log') -RedirectStandardError (Join-Path $logDir 'backend-error.log')
$frontend = Start-Process -FilePath 'node.exe' -ArgumentList 'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173' -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'frontend.log') -RedirectStandardError (Join-Path $logDir 'frontend-error.log')
@{ backend = $backend.Id; frontend = $frontend.Id; root = $projectRoot } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logDir 'local-processes.json')
$deadline = (Get-Date).AddSeconds(30)
$ready = $false
$lastFailure = ''
do {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2 | Out-Null
        Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5173' -TimeoutSec 2 | Out-Null
        $ready = $true
    } catch { $lastFailure = $_.Exception.Message; Start-Sleep -Milliseconds 500 }
} until ($ready -or (Get-Date) -gt $deadline)
if (-not $ready) { throw "Local startup did not become healthy: $lastFailure. Inspect .local logs." }
Write-Output 'EICC: http://127.0.0.1:5173 | API: http://127.0.0.1:8000/docs'
