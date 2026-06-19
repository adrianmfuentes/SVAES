<#
.SYNOPSIS
    Verifica la trazabilidad entre el plan de pruebas y los tests implementados.
.DESCRIPTION
    Analiza archivos de resultado de pytest, cargo test, Jest y JUnit XML para
    verificar que todos los casos del plan de pruebas (77 casos) esten cubiertos.
    Genera informes en tests/results/.
.PARAMETER Files
    Archivos de resultado de tests. Si no se especifican, lee de stdin.
.OUTPUTS
    traceability_report.md y traceability_report.csv en tests/results/
.NOTES
    Codigo de salida: 0=todos cubiertos y pasan, 1=hay fallos o sin implementar
#>

param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]] $Files
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\.."
$OutDir = "$ProjectRoot\tests\results"

if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$PLAN = @(
    @{ Id = "TC-UNI-AGG-01"; Level = "Unitaria";     Section = "7.2.1"; Desc = "Todas OBL=OK, OPC=OK -> VALID";                   Tech = "CE+VL";   Tool = "cargo test" },
    @{ Id = "TC-UNI-AGG-02"; Level = "Unitaria";     Section = "7.2.1"; Desc = ">=1 OBL=ERROR -> INVALID";                      Tech = "CE+VL";   Tool = "cargo test" },
    @{ Id = "TC-UNI-AGG-03"; Level = "Unitaria";     Section = "7.2.1"; Desc = "OBL todas OK, >=1 OPC=WARNING -> VALID_WITH_WARNINGS"; Tech = "CE+VL"; Tool = "cargo test" },
    @{ Id = "TC-UNI-AGG-04"; Level = "Unitaria";     Section = "7.2.1"; Desc = "VL: 0 reglas OBL con ERROR -> veredicto!=INVALID"; Tech = "CE+VL";  Tool = "cargo test" },
    @{ Id = "TC-UNI-AGG-05"; Level = "Unitaria";     Section = "7.2.1"; Desc = "VL: 1 regla OBL con ERROR -> INVALID";           Tech = "CE+VL";   Tool = "cargo test" },
    @{ Id = "TC-UNI-AGG-06"; Level = "Unitaria";     Section = "7.2.1"; Desc = "VL: 1 NOT_EVALUATED -> sufijo _WITH_INCIDENTS";  Tech = "CE+VL";   Tool = "cargo test" },
    @{ Id = "TC-UNI-AGG-07"; Level = "Unitaria";     Section = "7.2.1"; Desc = "VL: 0 NOT_EVALUATED -> sin sufijo";              Tech = "CE+VL";   Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-01"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-01 Conector ACTIVO, artefacto OK";            Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-02"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-01 Conector INACTIVO -> NOT_EVALUATED";      Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-03"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-02 ID cruzado valido";                       Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-04"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-02 ID en commit NOT_FOUND en Jira -> ERROR"; Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-05"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-03 Cobertura documental completa";           Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-06"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-04 Version coherente";                       Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-07"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-05 Tarea bloqueante -> ERROR";               Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-08"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-06 Campo obligatorio vacio -> ERROR";       Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-09"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-07 Back-reference valida";                   Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-10"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-08 Artefacto con antiguedad > umbral -> WARNING"; Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-11"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-09 Dos artefactos mismo external_id -> ERROR"; Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-MOT-12"; Level = "Unitaria";     Section = "7.2.2"; Desc = "RV-10 Documento aprobado existe";               Tech = "Each Choice"; Tool = "cargo test" },
    @{ Id = "TC-UNI-API-00"; Level = "Unitaria";     Section = "7.2.3"; Desc = "Base OPERATOR valido+propia+completo -> 201";   Tech = "Base Choice"; Tool = "pytest" },
    @{ Id = "TC-UNI-API-01"; Level = "Unitaria";     Section = "7.2.3"; Desc = "rol=ADMIN -> 201";                              Tech = "Base Choice"; Tool = "pytest" },
    @{ Id = "TC-UNI-API-02"; Level = "Unitaria";     Section = "7.2.3"; Desc = "rol=VIEWER -> 403";                             Tech = "Base Choice"; Tool = "pytest" },
    @{ Id = "TC-UNI-API-03"; Level = "Unitaria";     Section = "7.2.3"; Desc = "autenticacion=token_caducado -> 401";          Tech = "Base Choice"; Tool = "pytest" },
    @{ Id = "TC-UNI-API-04"; Level = "Unitaria";     Section = "7.2.3"; Desc = "autenticacion=sin_token -> 401";               Tech = "Base Choice"; Tool = "pytest" },
    @{ Id = "TC-UNI-API-05"; Level = "Unitaria";     Section = "7.2.3"; Desc = "org_context=ajena -> 404";                      Tech = "Base Choice"; Tool = "pytest" },
    @{ Id = "TC-UNI-API-06"; Level = "Unitaria";     Section = "7.2.3"; Desc = "body campo faltante -> 422";                    Tech = "Base Choice"; Tool = "pytest" },
    @{ Id = "TC-UNI-API-07"; Level = "Unitaria";     Section = "7.2.3"; Desc = "body tipo incorrecto -> 422";                   Tech = "Base Choice"; Tool = "pytest" },
    @{ Id = "TC-UNI-CON-01"; Level = "Unitaria";     Section = "7.2.4"; Desc = "Credenciales OK, URL alcanzable -> ACTIVO";     Tech = "CE+VL";   Tool = "pytest" },
    @{ Id = "TC-UNI-CON-02"; Level = "Unitaria";     Section = "7.2.4"; Desc = "Token caducado -> AuthError / INACTIVO";        Tech = "CE+VL";   Tool = "pytest" },
    @{ Id = "TC-UNI-CON-03"; Level = "Unitaria";     Section = "7.2.4"; Desc = "URL inexistente -> ConnectionError / INACTIVO"; Tech = "CE+VL";   Tool = "pytest" },
    @{ Id = "TC-UNI-CON-04"; Level = "Unitaria";     Section = "7.2.4"; Desc = "VL latencia = timeout exacto -> TimeoutError";  Tech = "CE+VL";   Tool = "pytest" },
    @{ Id = "TC-UNI-CON-05"; Level = "Unitaria";     Section = "7.2.4"; Desc = "VL latencia = timeout-1ms -> OK";               Tech = "CE+VL";   Tool = "pytest" },
    @{ Id = "TC-UNI-CON-06"; Level = "Unitaria";     Section = "7.2.4"; Desc = "Conector INACTIVO en verificacion -> sin HTTP"; Tech = "CE+VL";   Tool = "pytest" },
    @{ Id = "TC-UNI-FE-GRD-01"; Level = "Unitaria";  Section = "7.2.5.1"; Desc = "Token valido, U2/OPERATOR, ruta permitida -> canActivate=true"; Tech = "CE+BC"; Tool = "Jest" },
    @{ Id = "TC-UNI-FE-GRD-02"; Level = "Unitaria";  Section = "7.2.5.1"; Desc = "Token caducado -> canActivate=false, redirige /login"; Tech = "CE+BC"; Tool = "Jest" },
    @{ Id = "TC-UNI-FE-GRD-03"; Level = "Unitaria";  Section = "7.2.5.1"; Desc = "Token ausente -> canActivate=false, redirige /login"; Tech = "CE+BC"; Tool = "Jest" },
    @{ Id = "TC-UNI-FE-GRD-04"; Level = "Unitaria";  Section = "7.2.5.1"; Desc = "U1/VIEWER en /releases/verify -> canActivate=false, /forbidden"; Tech = "CE+BC"; Tool = "Jest" },
    @{ Id = "TC-UNI-FE-SVC-01"; Level = "Unitaria";  Section = "7.2.5.2"; Desc = "POST /releases 201 -> Observable emite Release, Bearer presente"; Tech = "Base Choice"; Tool = "Jest" },
    @{ Id = "TC-UNI-FE-SVC-02"; Level = "Unitaria";  Section = "7.2.5.2"; Desc = "POST /releases 401 -> Observable emite AuthError"; Tech = "Base Choice"; Tool = "Jest" },
    @{ Id = "TC-UNI-FE-SVC-03"; Level = "Unitaria";  Section = "7.2.5.2"; Desc = "POST /releases 422 -> Observable emite ValidationError"; Tech = "Base Choice"; Tool = "Jest" },
    @{ Id = "TC-UNI-FE-NGR-01"; Level = "Unitaria";  Section = "7.2.5.3"; Desc = "API 202+taskId -> verifyReleaseSuccess con taskId"; Tech = "CE"; Tool = "Jest" },
    @{ Id = "TC-UNI-FE-NGR-02"; Level = "Unitaria";  Section = "7.2.5.3"; Desc = "API 409 -> verifyReleaseFailure con INVALID_STATE"; Tech = "CE"; Tool = "Jest" },
    @{ Id = "TC-INT-EST-01"; Level = "Integracion";  Section = "7.3.1"; Desc = "T1 BORRADOR->EN_VERIFICACION -> HTTP 202";       Tech = "TE";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-EST-02"; Level = "Integracion";  Section = "7.3.1"; Desc = "T2 EN_VERIFICACION->VALIDA";                    Tech = "TE";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-EST-03"; Level = "Integracion";  Section = "7.3.1"; Desc = "T3 EN_VERIFICACION->CON_ADVERTENCIAS";          Tech = "TE";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-EST-04"; Level = "Integracion";  Section = "7.3.1"; Desc = "T4 EN_VERIFICACION->NO_VALIDA";                 Tech = "TE";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-EST-05"; Level = "Integracion";  Section = "7.3.1"; Desc = "T5 VALIDA->ARCHIVADA (inmutable)";              Tech = "TE";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-EST-06"; Level = "Integracion";  Section = "7.3.1"; Desc = "T6 NO_VALIDA->EN_VERIFICACION (rework)";        Tech = "TE";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-EST-07"; Level = "Integracion";  Section = "7.3.1"; Desc = "T-NEG ARCHIVADA->EN_VERIFICACION -> 409";       Tech = "TE";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-EST-08"; Level = "Integracion";  Section = "7.3.1"; Desc = "T-NEG BORRADOR->VALIDA (salto) -> 422";        Tech = "TE";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-FLW-01"; Level = "Integracion";  Section = "7.3.2"; Desc = "CU-01 todas RV-01..10 conectores activos -> VALID"; Tech = "VL";    Tool = "pytest+Docker" },
    @{ Id = "TC-INT-FLW-02"; Level = "Integracion";  Section = "7.3.2"; Desc = "CU-01 conector GitLab INACTIVO -> _WITH_INCIDENTS"; Tech = "VL";  Tool = "pytest+Docker" },
    @{ Id = "TC-INT-FLW-03"; Level = "Integracion";  Section = "7.3.2"; Desc = "Re-verificacion tras NO_VALIDA -> VALIDA";      Tech = "VL";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-LIM-01"; Level = "Integracion";  Section = "7.3.2"; Desc = "VL rate limit peticion 100/60s -> 200";         Tech = "VL";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-LIM-02"; Level = "Integracion";  Section = "7.3.2"; Desc = "VL rate limit peticion 101/60s -> 429+Retry-After"; Tech = "VL"; Tool = "pytest+Docker" },
    @{ Id = "TC-INT-RES-01"; Level = "Integracion";  Section = "7.3.2"; Desc = "docker kill worker durante verificacion -> sin corrupcion"; Tech = "VL"; Tool = "pytest+Docker" },
    @{ Id = "TC-INT-RES-02"; Level = "Integracion";  Section = "7.3.2"; Desc = "Redis caido al lanzar POST /verify -> 503";     Tech = "VL";      Tool = "pytest+Docker" },
    @{ Id = "TC-INT-MIG-01"; Level = "Integracion";  Section = "7.3.2"; Desc = "alembic upgrade head sobre BD vacia -> esquema OK"; Tech = "VL";    Tool = "pytest+Docker" },
    @{ Id = "TC-ACP-CU-00"; Level = "Aceptacion";    Section = "7.4";   Desc = "CU-01 base -> VALIDA en <=5 acciones (RNF-19)";  Tech = "BC";      Tool = "Manual+Cypress" },
    @{ Id = "TC-ACP-CU-01"; Level = "Aceptacion";    Section = "7.4";   Desc = "CU-01 RV-04=WARNING -> semaforo naranja";        Tech = "BC";      Tool = "Manual+Cypress" },
    @{ Id = "TC-ACP-CU-02"; Level = "Aceptacion";    Section = "7.4";   Desc = "CU-01 RV-05=ERROR -> semaforo rojo, msg descriptivo"; Tech = "BC"; Tool = "Manual+Cypress" },
    @{ Id = "TC-ACP-CU-03"; Level = "Aceptacion";    Section = "7.4";   Desc = "Usuario nuevo completa flujo en <=15 min (RNF-24)"; Tech = "BC";    Tool = "Manual" },
    @{ Id = "TC-ACP-UI-01"; Level = "Aceptacion";    Section = "7.4";   Desc = "Snapshot inmutable tras archivar (RNF-36)";      Tech = "BC";      Tool = "Manual+Cypress" },
    @{ Id = "TC-ACP-FRM-01"; Level = "Aceptacion";   Section = "7.4";   Desc = "Campo obligatorio vacio -> mensaje campo+accion"; Tech = "VL";      Tool = "Manual+Cypress" },
    @{ Id = "TC-ACP-FRM-02"; Level = "Aceptacion";   Section = "7.4";   Desc = "Campo numerico con texto -> error de tipo (RNF-20)"; Tech = "VL";   Tool = "Manual+Cypress" },
    @{ Id = "TC-USA-NAV-01"; Level = "Aceptacion";   Section = "7.4";   Desc = "Each choice Chrome/Firefox/Edge/Safari (RNF-29)"; Tech = "EC";      Tool = "Cypress" },
    @{ Id = "TC-USA-RES-01"; Level = "Aceptacion";   Section = "7.4";   Desc = "VL resolucion 1920/768/375 -> sin desbordamiento (RNF-30)"; Tech = "VL"; Tool = "Manual+Cypress" },
    @{ Id = "TC-USA-SEM-01"; Level = "Aceptacion";   Section = "7.4";   Desc = "Semaforo coherente en dashboard/historial/detalle (RNF-21)"; Tech = "EC"; Tool = "Manual+Cypress" },
    @{ Id = "TC-PER-VL-01"; Level = "Rendimiento";   Section = "7.5";   Desc = "Verificacion 10 reglas -> tiempo e2e <=5s p95 (RNF-06)"; Tech = "VL"; Tool = "Locust" },
    @{ Id = "TC-PER-VL-02"; Level = "Rendimiento";   Section = "7.5";   Desc = "Motor Rust bucle -> p95 <500ms (RNF-07)";        Tech = "VL";      Tool = "Locust" },
    @{ Id = "TC-PER-VL-03"; Level = "Rendimiento";   Section = "7.5";   Desc = "50 POST /verify simultaneos -> todas 202 (RNF-06)"; Tech = "VL";    Tool = "Locust" },
    @{ Id = "TC-PER-CE-04"; Level = "Rendimiento";   Section = "7.5";   Desc = "Suite completa -> SonarCloud cobertura >=70% (RNF-27)"; Tech = "CE"; Tool = "SonarCloud" },
    @{ Id = "TC-SEC-AUT-01"; Level = "Seguridad";    Section = "7.6";   Desc = "VL fuerza bruta: 5 intentos -> 403 + bloqueo 15min (RNF-14)"; Tech = "CE"; Tool = "pytest" },
    @{ Id = "TC-SEC-AUT-02"; Level = "Seguridad";    Section = "7.6";   Desc = "JWT manipulado -> 401 (OWASP A2)";               Tech = "CE";      Tool = "pytest" },
    @{ Id = "TC-SEC-INY-01"; Level = "Seguridad";    Section = "7.6";   Desc = "SQLi en nombre release -> neutralizado (OWASP A3)"; Tech = "CE";   Tool = "pytest" },
    @{ Id = "TC-SEC-INY-02"; Level = "Seguridad";    Section = "7.6";   Desc = "XSS en release -> escapado al frontend (OWASP A3)"; Tech = "CE";   Tool = "pytest" },
    @{ Id = "TC-SEC-CIF-01"; Level = "Seguridad";    Section = "7.6";   Desc = "Credenciales cifradas AES-256-GCM en BD (RNF-13)"; Tech = "CE";    Tool = "pytest" }
)

$PLAN_INDEX = @{}
foreach ($entry in $PLAN) { $PLAN_INDEX[$entry.Id] = $entry }

if ($PLAN.Count -ne 77) {
    Write-Warning "El plan debe tener 77 casos, tiene $($PLAN.Count)"
}

function Normalize-TcId {
    param([string]$Raw)
    return $Raw.ToUpper().Replace("_", "-")
}

function Parse-Text {
    param([string]$Content)
    $results = @{}
    $tcPattern = "(?<![A-Za-z])(TC[-_](?:UNI|INT|ACP|USA|PER|SEC)[-_](?:FE[-_])?[A-Z]+[-_]\d+)(?![A-Za-z])"
    $failPattern = "\bFAILED\b|✗|✕|●|\bERROR\b|\bFAIL\b|PANICKED"
    $passPattern = "\bPASSED\b|\bPASS\b|✓|✔|\bok\b|\bOK\b"

    $lines = $Content -split "`n"
    foreach ($line in $lines) {
        $matches = [regex]::Matches($line, $tcPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if ($matches.Count -eq 0) { continue }

        $isFail = [regex]::IsMatch($line, $failPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        $isPass = [regex]::IsMatch($line, $passPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        $status = if ($isFail) { "FAIL" } elseif ($isPass) { "PASS" } else { continue }

        foreach ($m in $matches) {
            $tcId = Normalize-TcId $m.Groups[1].Value
            if ($results[$tcId] -ne "FAIL") {
                $results[$tcId] = $status
            }
        }
    }
    return $results
}

function Parse-JunitXml {
    param([string]$Content)
    $results = @{}
    try {
        [xml]$xml = $Content
        $testCases = $xml.SelectNodes("//testcase")
        foreach ($tc in $testCases) {
            $text = "$($tc.name) $($tc.classname)"
            $failure = $tc.SelectSingleNode("failure")
            $error = $tc.SelectSingleNode("error")
            if ($failure -or $error) {
                $status = "FAIL"
            } else {
                $status = "PASS"
            }

            $tcPattern = "(?<![A-Za-z])(TC[-_](?:UNI|INT|ACP|USA|PER|SEC)[-_](?:FE[-_])?[A-Z]+[-_]\d+)(?![A-Za-z])"
            $matches = [regex]::Matches($text, $tcPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            foreach ($m in $matches) {
                $tcId = Normalize-TcId $m.Groups[1].Value
                if ($results[$tcId] -ne "FAIL") {
                    $results[$tcId] = $status
                }
            }
        }
    } catch { }
    return $results
}

function Parse-File {
    param([string]$Path)
    $content = Get-Content -Path $Path -Raw -Encoding UTF8
    $stripped = $content.TrimStart()
    if ($stripped.StartsWith("<?xml") -or $stripped.StartsWith("<testsuites") -or $stripped.StartsWith("<testsuite")) {
        return Parse-JunitXml $content
    }
    return Parse-Text $content
}

$allResults = @{}
if ($Files -and $Files.Count -gt 0) {
    foreach ($f in $Files) {
        if (Test-Path $f) {
            $parsed = Parse-File $f
            Write-Host "  Leido $(Split-Path $f -Leaf): $($parsed.Count) TC-IDs encontrados" -ForegroundColor DarkGray
            foreach ($tcId in $parsed.Keys) {
                if ($allResults[$tcId] -ne "FAIL") {
                    $allResults[$tcId] = $parsed[$tcId]
                }
            }
        } else {
            Write-Host "  [WARN] Archivo no encontrado: $f" -ForegroundColor Yellow
        }
    }
} else {
    $resultFiles = @(
        "$OutDir\unit_results.txt",
        "$OutDir\security_results.txt",
        "$OutDir\integration_results.txt",
        "$OutDir\rust_results.txt",
        "$OutDir\frontend_results.txt",
        "$OutDir\performance_results.txt",
        "$OutDir\acceptance_results.txt"
    )
    $foundFiles = $resultFiles | Where-Object { Test-Path $_ }
    if ($foundFiles.Count -eq 0) {
        Write-Host "  [WARN] No se encontraron archivos de resultados en $OutDir" -ForegroundColor Yellow
        Write-Host "  Usa: .\trace.ps1 <archivos...>" -ForegroundColor DarkGray
        exit 1
    }
    Write-Host "  Buscando en $OutDir..." -ForegroundColor Cyan
    foreach ($f in $foundFiles) {
        $parsed = Parse-File $f
        Write-Host "  Leido $(Split-Path $f -Leaf): $($parsed.Count) TC-IDs encontrados" -ForegroundColor DarkGray
        foreach ($tcId in $parsed.Keys) {
            if ($allResults[$tcId] -ne "FAIL") {
                $allResults[$tcId] = $parsed[$tcId]
            }
        }
    }
}

$passed = @()
$failed = @()
$missing = @()
$unknown = @()

foreach ($entry in $PLAN) {
    if (-not $allResults.ContainsKey($entry.Id)) {
        $missing += $entry
    } elseif ($allResults[$entry.Id] -eq "FAIL") {
        $failed += $entry
    } else {
        $passed += $entry
    }
}

foreach ($tcId in $allResults.Keys | Sort-Object) {
    if (-not $PLAN_INDEX.ContainsKey($tcId)) {
        $unknown += $tcId
    }
}

$total = $PLAN.Count
$nPass = $passed.Count
$nFail = $failed.Count
$nMiss = $missing.Count
$coveragePct = if ($total -gt 0) { ($nPass / $total) * 100 } else { 0 }

Write-Host ""
Write-Host ("─" * 70) -ForegroundColor White
Write-Host "  SVAES - Informe de Trazabilidad Plan de Pruebas" -ForegroundColor White -NoNewline
Write-Host ""
Write-Host ("─" * 70) -ForegroundColor White
Write-Host "  Plan total    : $total casos"
Write-Host "  [+] Cubiertas y pasan : $($nPass.ToString().PadLeft(3))  ($($coveragePct.ToString("F1"))%)" -ForegroundColor Green
Write-Host "  [-] Fallan             : $($nFail.ToString().PadLeft(3))" -ForegroundColor Red
Write-Host "  [?] Sin implementar    : $($nMiss.ToString().PadLeft(3))" -ForegroundColor Yellow
if ($unknown.Count -gt 0) {
    Write-Host "  [!] TC-IDs no en plan  : $($unknown.Count.ToString().PadLeft(3))" -ForegroundColor DarkGray
}

$barLen = 50
$filled = [int]($barLen * $nPass / $total)
$failF = [int]($barLen * $nFail / $total)
$missF = $barLen - $filled - $failF
$bar = ("█" * $filled)
if ($failF -gt 0) { $bar += "$( [char]27 )[31m" + ("█" * $failF) + "$( [char]27 )[0m" }
if ($missF -gt 0) { $bar += "$( [char]27 )[33m" + ("░" * $missF) + "$( [char]27 )[0m" }
Write-Host ""
Write-Host "  [$bar] $($coveragePct.ToString("F1"))% cubiertas y OK" -ForegroundColor White
Write-Host ""

$levels = @("Unitaria", "Integracion", "Aceptacion", "Rendimiento", "Seguridad")
foreach ($level in $levels) {
    $levelEntries = $PLAN | Where-Object { $_.Level -eq $level }
    $lpass = ($levelEntries | Where-Object { $passed -contains $_ }).Count
    $lfail = ($levelEntries | Where-Object { $failed -contains $_ }).Count
    $lmiss = ($levelEntries | Where-Object { $missing -contains $_ }).Count
    $icon = if ($lmiss -eq 0 -and $lfail -eq 0) { "[+]" } elseif ($lfail -gt 0) { "[-]" } else { "[?]" }
    $iconColor = if ($lmiss -eq 0 -and $lfail -eq 0) { "Green" } elseif ($lfail -gt 0) { "Red" } else { "Yellow" }
    Write-Host "  $icon " -NoNewline; Write-Host ("{0,-14}" -f $level) -NoNewline; Write-Host "  pass=$($lpass.ToString().PadLeft(3)) " -NoNewline -ForegroundColor Green; Write-Host "fail=$($lfail.ToString().PadLeft(3)) " -NoNewline -ForegroundColor Red; Write-Host "miss=$($lmiss.ToString().PadLeft(3))  ($($levelEntries.Count) en plan)" -ForegroundColor Yellow
}

if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "  [-] CASOS QUE FALLAN ($($failed.Count))" -ForegroundColor Red
    foreach ($e in $failed) {
        Write-Host "    " -NoNewline; Write-Host ($e.Id.PadRight(22)) -NoNewline -ForegroundColor Red; Write-Host "  $($e.Section.PadRight(8))  $($e.Desc.Substring(0, [Math]::Min(55, $e.Desc.Length)))" -ForegroundColor Gray
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "  [?] CASOS SIN IMPLEMENTAR ($($missing.Count))" -ForegroundColor Yellow
    $bySection = @{}
    foreach ($e in $missing) {
        if (-not $bySection[$e.Section]) { $bySection[$e.Section] = @() }
        $bySection[$e.Section] += $e
    }
    foreach ($section in ($bySection.Keys | Sort-Object)) {
        Write-Host "    $section" -ForegroundColor DarkGray
        foreach ($e in $bySection[$section]) {
            Write-Host "      " -NoNewline; Write-Host ($e.Id.PadRight(22)) -NoNewline -ForegroundColor Yellow; Write-Host "  " -NoNewline -ForegroundColor DarkGray; Write-Host ($e.Tool.PadRight(18)) -NoNewline -ForegroundColor DarkGray; Write-Host ("  " + $e.Desc.Substring(0, [Math]::Min(45, $e.Desc.Length))) -ForegroundColor Gray
        }
    }
}

if ($unknown.Count -gt 0) {
    Write-Host ""
    Write-Host "  [!] TC-IDs EN TESTS NO PRESENTES EN EL PLAN ($($unknown.Count))" -ForegroundColor DarkGray
    Write-Host "    (puede ser un ID mal escrito o un test fuera del plan)" -ForegroundColor DarkGray
    foreach ($tcId in $unknown) {
        Write-Host "    $tcId" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host ("─" * 70) -ForegroundColor White
Write-Host ""

$mdLines = @(
    "# Informe de trazabilidad - SVAES Plan de Pruebas",
    "",
    "**Total en plan:** $total  |  **Cubiertas OK:** $nPass  |  **Fallan:** $nFail  |  **Sin implementar:** $nMiss",
    "",
    "| TC-ID | Nivel | Seccion | Estado | Herramienta | Descripcion |",
    "|---|---|---|---|---|---|"
)
$statusMap = @{}
foreach ($e in $passed) { $statusMap[$e.Id] = "PASS" }
foreach ($e in $failed) { $statusMap[$e.Id] = "FAIL" }
foreach ($e in $missing) { $statusMap[$e.Id] = "MISSING" }

$iconMap = @{ PASS = "✅"; FAIL = "❌"; MISSING = "⬜" }

foreach ($entry in $PLAN) {
    $st = $statusMap[$entry.Id]
    $icon = $iconMap[$st]
    $mdLines += "| ``$($entry.Id)`` | $($entry.Level) | $($entry.Section) | $icon $st | $($entry.Tool) | $($entry.Desc) |"
}

if ($unknown.Count -gt 0) {
    $mdLines += "", "## TC-IDs en tests no reconocidos en el plan", ""
    foreach ($tcId in $unknown) {
        $mdLines += "- ``$tcId``"
    }
}

$mdPath = Join-Path $OutDir "traceability_report.md"
Set-Content -Path $mdPath -Value ($mdLines -join "`n") -Encoding UTF8
Write-Host "  -> traceability_report.md" -ForegroundColor Green

$csvLines = @("TC-ID,Nivel,Seccion,Estado,Tecnica,Herramienta,Descripcion")
foreach ($entry in $PLAN) {
    $st = $statusMap[$entry.Id]
    $csvLines += "`"$($entry.Id)`",`"$($entry.Level)`",`"$($entry.Section)`",`"$st`",`"$($entry.Tech)`",`"$($entry.Tool)`",`"$($entry.Desc)`""
}
$csvPath = Join-Path $OutDir "traceability_report.csv"
Set-Content -Path $csvPath -Value ($csvLines -join "`n") -Encoding UTF8
Write-Host "  -> traceability_report.csv" -ForegroundColor Green

Write-Host ""

if ($nMiss -eq 0 -and $nFail -eq 0) {
    exit 0
} else {
    exit 1
}