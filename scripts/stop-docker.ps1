param([string]$Distribution = 'Ubuntu')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (Get-Command docker -ErrorAction SilentlyContinue) { docker compose down } else { wsl -d $Distribution -u root --cd $projectRoot -- docker compose down }
if ($LASTEXITCODE -ne 0) { throw 'Docker shutdown failed; the WSL helper remains running for inspection' }
$pidFile = Join-Path $projectRoot '.local\wsl-keepalive.pid'
if (Test-Path -LiteralPath $pidFile) {
    $processId = [int](Get-Content -LiteralPath $pidFile)
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if ($process -and $process.Name -eq 'wsl.exe' -and $process.CommandLine -match 'sleep infinity') { Stop-Process -Id $processId }
    Remove-Item -LiteralPath $pidFile
}
Write-Output 'EICC containers stopped. PostgreSQL data volume retained.'
