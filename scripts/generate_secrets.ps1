<#
.SYNOPSIS
    Genera secrets de produccion seguros para SVAES.
.DESCRIPTION
    Genera:
        - JWT_SECRET_KEY: clave para firmar tokens JWT (64 caracteres aleatorios)
        - ENCRYPTION_KEY: clave Fernet para cifrar credenciales de conectores
.NOTES
    Requiere: .NET Framework 4.7+ o .NET Core
#>

$ErrorActionPreference = "Stop"

$JwtSecret = [System.Convert]::ToBase64String(
    [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(48)
).Replace("+", "-").Replace("/", "_").Replace("=", "") | Select-Object -First 64

$AesKey = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
$EncryptionKey = [System.Convert]::ToBase64String($AesKey).Replace("+", "-").Replace("/", "_").TrimEnd("=")

Write-Host "# ============================================================"
Write-Host "# Secrets de produccion para SVAES"
Write-Host "# ============================================================"
Write-Host "# Copia estas variables a tu .env o sistema de gestion de secretos"
Write-Host "# ============================================================"
Write-Host ""
Write-Host "JWT_SECRET_KEY=$JwtSecret"
Write-Host "ENCRYPTION_KEY=$EncryptionKey"
Write-Host ""
Write-Host "# ============================================================"