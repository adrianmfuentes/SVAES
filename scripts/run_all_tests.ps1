<#
.SYNOPSIS
    Ejecuta todos los tests del proyecto SVAES y genera informes en tests/results/.
.DESCRIPTION
    Crea la carpeta tests/results/, ejecuta cada suite de tests redirigiendo la
    salida a un .txt, y después lanza trace.ps1 con todos ellos.
.NOTES
    Requiere: Python 3.11+, Rust (cargo), Docker, Node.js (pnpm)
#>

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\.."
$ResultsDir = "$ProjectRoot\tests\results"

if (-not (Test-Path -LiteralPath $ResultsDir)) {
    New-Item -ItemType Directory -Path $ResultsDir -Force | Out-Null
}
Write-Host "===== Resultados en: $ResultsDir =====" -ForegroundColor Cyan

# ------------------------------------------------------------------
# 1. Tests unitarios Python
# ------------------------------------------------------------------
Write-Host "`n[1/7] Tests unitarios Python..." -ForegroundColor Yellow
pytest "$ProjectRoot\tests\unit\" -v --tb=short 2>&1 |
    ForEach-Object { $_ -replace "\e\[[0-9;]*m", "" } |
    Set-Content -LiteralPath "$ResultsDir\unit_results.txt"
Write-Host "  -> unit_results.txt" -ForegroundColor Green

# ------------------------------------------------------------------
# 2. Tests de seguridad Python
# ------------------------------------------------------------------
Write-Host "`n[2/7] Tests de seguridad Python..." -ForegroundColor Yellow
pytest "$ProjectRoot\tests\security\" -v --tb=short 2>&1 |
    ForEach-Object { $_ -replace "\e\[[0-9;]*m", "" } |
    Set-Content -LiteralPath "$ResultsDir\security_results.txt"
Write-Host "  -> security_results.txt" -ForegroundColor Green

# ------------------------------------------------------------------
# 3. Tests de integración (requiere Docker)
# ------------------------------------------------------------------
Write-Host "`n[3/7] Tests de integración (Docker)..." -ForegroundColor Yellow
$ComposeFile = "$ProjectRoot\docker-compose.test.yml"

$env:TEST_POSTGRES_USER = "svaes"
$env:TEST_POSTGRES_PASSWORD = "svaes"
$env:TEST_POSTGRES_HOST = "localhost"
$env:TEST_POSTGRES_PORT = "5433"
$env:TEST_POSTGRES_DB = "svaes_test"
$env:TEST_REDIS_URL = "redis://localhost:6380/0"
$env:TEST_ENGINE_URL = "http://localhost:8081"

Write-Host "    Levantando infraestructura de test..." -ForegroundColor Gray
docker compose -f $ComposeFile down --volumes --remove-orphans 2>$null
docker compose -f $ComposeFile up -d --wait 2>&1 | Out-Null

try {
    python -m pytest "$ProjectRoot\tests\integration\" -v --tb=short 2>&1 |
        ForEach-Object { $_ -replace "\e\[[0-9;]*m", "" } |
        Set-Content -LiteralPath "$ResultsDir\integration_results.txt"
    Write-Host "  -> integration_results.txt" -ForegroundColor Green
} finally {
    Write-Host "    Tirando infraestructura..." -ForegroundColor Gray
    docker compose -f $ComposeFile down --volumes --remove-orphans 2>$null
}

# ------------------------------------------------------------------
# 4. Tests Rust (engine)
# ------------------------------------------------------------------
Write-Host "`n[4/7] Tests Rust (cargo test)..." -ForegroundColor Yellow
Push-Location "$ProjectRoot\engine"
try {
    cargo test 2>&1 |
        ForEach-Object { $_ -replace "\e\[[0-9;]*m", "" } |
        Set-Content -LiteralPath "$ResultsDir\rust_results.txt"
    Write-Host "  -> rust_results.txt" -ForegroundColor Green
} finally {
    Pop-Location
}

# ------------------------------------------------------------------
# 5. Tests frontend Angular (Vitest)
# ------------------------------------------------------------------
Write-Host "`n[5/7] Tests frontend Angular (Vitest)..." -ForegroundColor Yellow
Push-Location "$ProjectRoot\web"
try {
    npx ng test --watch=false 2>&1 |
        ForEach-Object { $_ -replace "\e\[[0-9;]*m", "" } |
        Set-Content -LiteralPath "$ResultsDir\frontend_results.txt"
    Write-Host "  -> frontend_results.txt" -ForegroundColor Green
} finally {
    Pop-Location
}

# ------------------------------------------------------------------
# 6. Tests de rendimiento (verificación de estructura + coverage)
# ------------------------------------------------------------------
Write-Host "`n[6/7] Tests de rendimiento..." -ForegroundColor Yellow
pytest "$ProjectRoot\tests\performance\test_coverage_threshold.py" -v --tb=short 2>&1 |
    ForEach-Object { $_ -replace "\e\[[0-9;]*m", "" } |
    Set-Content -LiteralPath "$ResultsDir\performance_results.txt"
Write-Host "  -> performance_results.txt" -ForegroundColor Green

# ------------------------------------------------------------------
# 7. Tests de aceptación (verificación de estructura Cypress)
# ------------------------------------------------------------------
Write-Host "`n[7/7] Tests de aceptación (estructura Cypress)..." -ForegroundColor Yellow
pytest "$ProjectRoot\tests\acceptance\test_acceptance_structure.py" -v --tb=short 2>&1 |
    ForEach-Object { $_ -replace "\e\[[0-9;]*m", "" } |
    Set-Content -LiteralPath "$ResultsDir\acceptance_results.txt"
Write-Host "  -> acceptance_results.txt" -ForegroundColor Green

# ------------------------------------------------------------------
# Trazabilidad
# ------------------------------------------------------------------
Write-Host "`n===== Generando informe de trazabilidad =====" -ForegroundColor Cyan
& "$ProjectRoot\scripts\trace.ps1" `
    "$ResultsDir\unit_results.txt" `
    "$ResultsDir\security_results.txt" `
    "$ResultsDir\integration_results.txt" `
    "$ResultsDir\rust_results.txt" `
    "$ResultsDir\frontend_results.txt" `
    "$ResultsDir\performance_results.txt" `
    "$ResultsDir\acceptance_results.txt"

Write-Host "`n===== Script completado =====" -ForegroundColor Cyan
Write-Host "Nota: Los tests Cypress E2E reales requieren la app corriendo:" -ForegroundColor Gray
Write-Host "  npx cypress run --config-file tests/acceptance/cypress.config.js" -ForegroundColor Gray
