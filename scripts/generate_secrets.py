#!/usr/bin/env python3
"""
Script para generar secrets de producción seguros para SVAES.

Uso:
    python generate_secrets.py

Genera:
    - JWT_SECRET_KEY: clave para firmar tokens JWT (64 caracteres aleatorios)
    - ENCRYPTION_KEY: clave Fernet para cifrar credenciales de conectores
"""
import secrets
from cryptography.fernet import Fernet


def main():
    jwt_secret = secrets.token_urlsafe(32)
    encryption_key = Fernet.generate_key().decode()

    print("# ============================================================")
    print("# Secrets de producción para SVAES")
    print("# ============================================================")
    print("# Copia estas variables a tu .env o sistema de gestión de secretos")
    print("# ============================================================\n")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print("\n# ============================================================")

if __name__ == "__main__":
    main()