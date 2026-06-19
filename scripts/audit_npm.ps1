<#
.SYNOPSIS
    Audita las dependencias de npm/pnpm en busca de vulnerabilidades de seguridad.
.DESCRIPTION
    Ejecuta pnpm audit en los directorios que usan npm/pnpm (actualmente web/).
    Genera un informe en tests/results/npm_audit_results.txt.
.NOTES
    Requiere: Node.js, pnpm
#>

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\.."
$ResultsDir = "$ProjectRoot\tests\results"

$WebDir = "$ProjectRoot\web"

if (-not (Test-Path -LiteralPath $ResultsDir)) {
    New-Item -ItemType Directory -Path $ResultsDir -Force | Out-Null
}

$AuditOutput = "$ResultsDir\npm_audit_results.txt"

Write-Host "===== Auditoria de seguridad npm/pnpm =====" -ForegroundColor Cyan
Write-Host ""

$HasVulnerabilities = $false
$ExitCode = 0

Push-Location $WebDir
try {
    Write-Host "[1/1] Ejecutando pnpm audit en web/..." -ForegroundColor Yellow

    $result = pnpm audit 2>&1
    $result | ForEach-Object { $_ -replace "\e\[[0-9;]*m", "" } | Set-Content -LiteralPath $AuditOutput

    if ($LASTEXITCODE -ne 0) {
        $HasVulnerabilities = $true
        $ExitCode = $LASTEXITCODE
        Write-Host "  [WARN] Se encontraron vulnerabilidades" -ForegroundColor Red
    } else {
        Write-Host "  [OK] No se encontraron vulnerabilidades" -ForegroundColor Green
    }

    Write-Host "  -> npm_audit_results.txt" -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "===== Auditoria completada =====" -ForegroundColor Cyan

if ($HasVulnerabilities) {
    Write-Host ""
    Write-Host "ADVERTENCIA: Se detectaron vulnerabilidades de seguridad." -ForegroundColor Red
    Write-Host "Revise $AuditOutput para mas detalles." -ForegroundColor Red
    exit $ExitCode
}

exit 0