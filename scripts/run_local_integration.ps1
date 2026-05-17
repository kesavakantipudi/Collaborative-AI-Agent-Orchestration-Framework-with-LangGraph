param()

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

Write-Host 'Starting Docker Compose stack...'
docker compose up --build -d

try {
    Write-Host 'Waiting for task status endpoint and Redis to become ready...'
    Start-Sleep -Seconds 10

    Write-Host 'Running integration test script...'
    python .\run_integration_test.py
}
finally {
    Write-Host 'Tearing down Docker Compose stack...'
    docker compose down --volumes
}
