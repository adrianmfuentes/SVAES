<#
.SYNOPSIS
    Spins up ephemeral PostgreSQL + Redis containers, runs integration tests, tears down.
.DESCRIPTION
    Uses docker-compose.test.yml with unique container names and non-standard ports
    to avoid collisions with a running dev/prod SVAES stack.
#>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\.."

$ComposeFile = "$ProjectRoot\docker-compose.test.yml"

$env:TEST_POSTGRES_USER = "svaes"
$env:TEST_POSTGRES_PASSWORD = "svaes"
$env:TEST_POSTGRES_HOST = "localhost"
$env:TEST_POSTGRES_PORT = "5433"
$env:TEST_POSTGRES_DB = "svaes_test"
$env:TEST_REDIS_URL = "redis://localhost:6380/0"
$env:TEST_ENGINE_URL = "http://localhost:8081"

Write-Host "===== Starting test infrastructure =====" -ForegroundColor Cyan
docker compose -f $ComposeFile down --volumes --remove-orphans 2>$null
docker compose -f $ComposeFile up -d --wait

try {
    Write-Host "===== Running integration tests =====" -ForegroundColor Cyan
    python -m pytest tests/integration/ -v --tb=short
    $testExit = $LASTEXITCODE
    exit $testExit
} finally {
    Write-Host "===== Tearing down test infrastructure =====" -ForegroundColor Cyan
    docker compose -f $ComposeFile down --volumes --remove-orphans
}
