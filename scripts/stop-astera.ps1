$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
docker compose -f infrastructure/docker-compose.yml down
Write-Host 'ASTERA containers stopped. Persistent PostgreSQL and Redis volumes were kept.'
