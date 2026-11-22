"""Verificación de firma de webhooks entrantes de conectores REPO_CODIGO.

Cada proveedor de control de versiones firma sus webhooks de forma distinta:
- GitHub / Bitbucket Cloud: `X-Hub-Signature-256: sha256=<hex>`, HMAC-SHA256
  sobre el cuerpo crudo de la petición.
- Gitea: `X-Gitea-Signature: <hex>` (mismo HMAC-SHA256, sin prefijo `sha256=`).
- GitLab: `X-Gitlab-Token: <secreto>` - no es HMAC, es un secreto compartido
  comparado directamente.

En todos los casos la comparación usa `hmac.compare_digest` para evitar
timing attacks, en vez de un `==` directo.
"""
import hashlib
import hmac
from typing import Optional

_SIGNATURE_HEADERS: dict[str, str] = {
    "GITHUB": "X-Hub-Signature-256",
    "GITEA": "X-Gitea-Signature",
    "BITBUCKET": "X-Hub-Signature-256",
    "GITLAB": "X-Gitlab-Token",
}


def signature_header_name(connector_implementation: str) -> Optional[str]:
    """Nombre de la cabecera HTTP donde el proveedor envía la firma/token."""
    return _SIGNATURE_HEADERS.get(connector_implementation.upper())


def _hmac_sha256_hex(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_github_style_signature(secret: str, payload: bytes, header_value: Optional[str]) -> bool:
    """GitHub y Bitbucket Cloud: `sha256=<hex>` sobre el cuerpo crudo."""
    if not header_value or not header_value.startswith("sha256="):
        return False
    expected = _hmac_sha256_hex(secret, payload)
    return hmac.compare_digest(header_value[len("sha256="):], expected)


def verify_gitea_signature(secret: str, payload: bytes, header_value: Optional[str]) -> bool:
    """Gitea: hex HMAC-SHA256 sin prefijo."""
    if not header_value:
        return False
    expected = _hmac_sha256_hex(secret, payload)
    return hmac.compare_digest(header_value, expected)


def verify_gitlab_token(secret: str, header_value: Optional[str]) -> bool:
    """GitLab: token compartido en claro, sin HMAC."""
    if not header_value:
        return False
    return hmac.compare_digest(header_value, secret)


def verify_webhook_signature(
    connector_implementation: str,
    secret: str,
    payload: bytes,
    header_value: Optional[str],
) -> bool:
    """Verifica la firma/token de un webhook entrante según el proveedor.

    Devuelve False (nunca lanza) ante cualquier proveedor no soportado o
    cabecera ausente/mal formada, para que el llamador siempre pueda tratarlo
    de forma uniforme como "firma inválida -> 401".
    """
    impl = connector_implementation.upper()
    if impl in ("GITHUB", "BITBUCKET"):
        return verify_github_style_signature(secret, payload, header_value)
    if impl == "GITEA":
        return verify_gitea_signature(secret, payload, header_value)
    if impl == "GITLAB":
        return verify_gitlab_token(secret, header_value)
    return False
