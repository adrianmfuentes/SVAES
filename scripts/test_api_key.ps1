#!/usr/bin/env pwsh
# test_api_key.ps1 - Verifica que una API Key del sistema SVAES funciona correctamente
# Uso: .\scripts\test_api_key.ps1

$HOST_URL = "https://svaes.amfserver.duckdns.org"

# ─── Colores ────────────────────────────────────────────────────────────────
function Write-Pass($msg)  { Write-Host "  [PASS] $msg" -ForegroundColor Green }
function Write-Fail($msg)  { Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Write-Info($msg)  { Write-Host "  [INFO] $msg" -ForegroundColor Cyan }
function Write-Section($t) { Write-Host "`n── $t ──" -ForegroundColor Yellow }

# ─── Entrada ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║   SVAES — Test de API Key en Producción  ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""
Write-Host "Host: $HOST_URL" -ForegroundColor DarkGray
Write-Host ""

$apiKey = Read-Host "Pega tu API Key"
if (-not $apiKey -or $apiKey.Trim() -eq "") {
    Write-Host "Error: no se proporcionó API Key." -ForegroundColor Red
    exit 1
}
$apiKey = $apiKey.Trim()

$headers = @{ "X-API-Key" = $apiKey }
$pass = 0
$fail = 0

# ─── Helper ──────────────────────────────────────────────────────────────────
function Invoke-Test {
    param(
        [string]$Label,
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers,
        [int[]]$ExpectedCodes,
        [scriptblock]$OnSuccess = $null
    )
    try {
        $resp = Invoke-WebRequest -Method $Method -Uri $Url -Headers $Headers `
                                  -UseBasicParsing -SkipHttpErrorCheck -ErrorAction Stop
        $code = [int]$resp.StatusCode
        if ($ExpectedCodes -contains $code) {
            Write-Pass "$Label → HTTP $code"
            $script:pass++
            if ($OnSuccess) { & $OnSuccess $resp }
        } else {
            Write-Fail "$Label → HTTP $code (esperado: $($ExpectedCodes -join '/'))"
            $script:fail++
        }
        return $resp
    } catch {
        Write-Fail "$Label → Error: $($_.Exception.Message)"
        $script:fail++
        return $null
    }
}

# ─── TEST 1: Clave inválida debe dar 401 ─────────────────────────────────────
Write-Section "TEST 1: Rechazo de clave inválida"
$null = Invoke-Test -Label "Clave basura rechazada con 401" `
            -Method GET `
            -Url "$HOST_URL/api/v1/organizations" `
            -Headers @{ "X-API-Key" = "invalid-key-that-should-fail" } `
            -ExpectedCodes @(401)

# ─── TEST 2: Sin cabecera debe dar 401 ───────────────────────────────────────
Write-Section "TEST 2: Sin X-API-Key"
$null = Invoke-Test -Label "Sin cabecera rechazado con 401" `
            -Method GET `
            -Url "$HOST_URL/api/v1/organizations" `
            -Headers @{} `
            -ExpectedCodes @(401)

# ─── TEST 3: Identidad de la clave via GET /api/v1/me ────────────────────────
Write-Section "TEST 3: Identidad de la clave (GET /api/v1/me)"
$orgId   = $null
$orgName = $null

$r3 = try {
    Invoke-WebRequest -Method GET -Uri "$HOST_URL/api/v1/me" `
                      -Headers $headers -UseBasicParsing -SkipHttpErrorCheck -ErrorAction Stop
} catch { $null }

if ($r3) {
    $code3 = [int]$r3.StatusCode
    if ($code3 -eq 200) {
        $me = $r3.Content | ConvertFrom-Json
        $orgId = $me.organization_id
        Write-Pass "GET /api/v1/me → HTTP 200 — clave válida"
        $script:pass++
        Write-Info "  user_id:         $($me.user_id)"
        Write-Info "  organization_id: $($me.organization_id)"
        Write-Info "  role:            $($me.role)  (U1=OPERATOR, U2=MANAGER, U3=ADMIN global)"
    } elseif ($code3 -eq 401) {
        Write-Fail "GET /api/v1/me → HTTP 401 — la clave no es válida o está revocada"
        $script:fail++
        Write-Host ""
        Write-Host "La clave falló la autenticación. Comprueba que:" -ForegroundColor Red
        Write-Host "  1. Copiaste la clave completa desde Mi Perfil" -ForegroundColor Red
        Write-Host "  2. La clave no está revocada ni expirada" -ForegroundColor Red
        Write-Host ""
        Write-Host "Resultado: $pass PASS  /  $fail FAIL" -ForegroundColor ($fail -eq 0 ? "Green" : "Red")
        exit 1
    } elseif ($code3 -eq 404) {
        # /api/v1/me aún no desplegado — verificar con el endpoint de lista (ADMIN obtiene 200, resto obtiene 403)
        Write-Info "GET /api/v1/me → 404 (endpoint pendiente de despliegue); verificando clave con endpoint alternativo..."
        $r3b = try {
            Invoke-WebRequest -Method GET -Uri "$HOST_URL/api/v1/organizations" `
                              -Headers $headers -UseBasicParsing -SkipHttpErrorCheck -ErrorAction Stop
        } catch { $null }
        if ($r3b) {
            $code3b = [int]$r3b.StatusCode
            if ($code3b -eq 200) {
                Write-Pass "Clave válida — eres ADMIN global (GET /api/v1/organizations → 200)"
                $script:pass++
                $orgs = $r3b.Content | ConvertFrom-Json
                if ($orgs.Count -gt 0) { $orgId = $orgs[0].id }
            } elseif ($code3b -eq 403) {
                Write-Pass "Clave válida — rol MANAGER/OPERATOR (GET /api/v1/organizations → 403 esperado)"
                $script:pass++
                Write-Info "  Tu org ID no es recuperable automáticamente hasta que se despliegue /api/v1/me"
            } elseif ($code3b -eq 401) {
                Write-Fail "Clave inválida o revocada → HTTP 401"
                $script:fail++
                exit 1
            } else {
                Write-Fail "Respuesta inesperada: HTTP $code3b"
                $script:fail++
            }
        }
    } else {
        Write-Fail "GET /api/v1/me → HTTP $code3 inesperado"
        $script:fail++
    }
} else {
    Write-Fail "GET /api/v1/me → sin respuesta (error de red)"
    $script:fail++
}

# ─── TEST 4: GET /api/v1/organizations/{org_id} ──────────────────────────────
Write-Section "TEST 4: GET /api/v1/organizations/{org_id}"
if (-not $orgId) {
    Write-Host ""
    $orgId = Read-Host "  Pega tu Org ID (UUID — visible en GET /api/v1/me → organization_id)"
    $orgId = $orgId.Trim()
}

if ($orgId) {
    $r4 = try {
        Invoke-WebRequest -Method GET -Uri "$HOST_URL/api/v1/organizations/$orgId" `
                          -Headers $headers -UseBasicParsing -SkipHttpErrorCheck -ErrorAction Stop
    } catch { $null }

    if ($r4) {
        $code4 = [int]$r4.StatusCode
        if ($code4 -eq 200) {
            Write-Pass "GET /api/v1/organizations/$orgId → HTTP 200"
            $script:pass++
            $org = $r4.Content | ConvertFrom-Json
            Write-Info "Organización: '$($org.name)'  |  Slug: $($org.slug)"
        } elseif ($code4 -eq 404) {
            Write-Fail "GET /api/v1/organizations/$orgId → HTTP 404 — org ID no encontrado"
            $script:fail++
        } elseif ($code4 -eq 403) {
            Write-Fail "GET /api/v1/organizations/$orgId → HTTP 403 — clave sin acceso a esa org"
            $script:fail++
        } else {
            Write-Fail "GET /api/v1/organizations/$orgId → HTTP $code4"
            $script:fail++
        }
    }
} else {
    Write-Info "Saltando test 4: no se proporcionó Org ID"
}

# ─── TEST 5: Rate limit header presente ──────────────────────────────────────
Write-Section "TEST 5: Cabeceras de rate limiting"
$r5 = try {
    Invoke-WebRequest -Method GET -Uri "$HOST_URL/api/v1/organizations" `
                      -Headers $headers -UseBasicParsing -SkipHttpErrorCheck -ErrorAction Stop
} catch { $null }

if ($r5) {
    $rl = $r5.Headers["X-RateLimit-Limit"] ?? $r5.Headers["RateLimit-Limit"] ?? $r5.Headers["x-ratelimit-limit"]
    if ($rl) {
        Write-Pass "Cabecera rate limit presente (límite: $rl req)"
        $script:pass++
    } else {
        Write-Info "No se detectaron cabeceras de rate limit (puede estar desactivado en prod)"
    }
}

# ─── TEST 6: Clave expirada / mal formato ────────────────────────────────────
Write-Section "TEST 6: Formato de clave"
$prefix = $apiKey.Substring(0, [Math]::Min(8, $apiKey.Length))
$len    = $apiKey.Length
Write-Info "Prefijo detectado: '$prefix...'  |  Longitud: $len caracteres"
if ($len -ge 32) {
    Write-Pass "Longitud de clave parece correcta (≥ 32 chars)"
    $script:pass++
} else {
    Write-Fail "Clave muy corta ($len chars) — puede estar incompleta"
    $script:fail++
}

# ─── Resumen ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor Yellow
$total = $pass + $fail
$color = if ($fail -eq 0) { "Green" } else { "Red" }
Write-Host "  Resultado: $pass/$total PASS   $fail FAIL" -ForegroundColor $color
Write-Host "══════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""
if ($fail -eq 0) {
    Write-Host "API Key operativa en produccion." -ForegroundColor Green
} else {
    Write-Host "Revisa los FAILs anteriores." -ForegroundColor Red
}
Write-Host ""
