import ipaddress
from urllib.parse import urlparse

from shared.domain.exceptions import ConnectorConnectionFailedError


_ALLOWED_SCHEMES = {"http", "https"}

_BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_safe_outbound_url(url: str) -> None:
    """Bloquea peticiones salientes hacia hosts/IPs internos o esquemas no HTTP(S).

    Los conectores construyen la URL de destino a partir de un `base_url`
    configurado por el propio usuario/organización (para soportar instancias
    autoalojadas de GitLab, Confluence, etc.). Sin esta validación, cualquier
    miembro de una organización podría convertir el backend en un proxy SSRF
    apuntando a `http://169.254.169.254/...` o a `localhost`.

    Deliberadamente estático (sin resolución DNS): añadir una consulta DNS en
    cada llamada saliente introduciría latencia y un punto de fallo de red en
    el propio chequeo de seguridad. Esto cubre el escenario de explotación
    real (host/IP interno puesto directamente en `base_url`); no protege
    contra DNS rebinding, que exigiría infraestructura adicional.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ConnectorConnectionFailedError(f"Esquema de URL no permitido: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ConnectorConnectionFailedError("URL de conector inválida: falta host")

    host_lower = hostname.lower()
    if host_lower in _BLOCKED_HOSTNAMES or host_lower.endswith(".localhost"):
        raise ConnectorConnectionFailedError(f"Host de conector no permitido: {hostname}")

    if _is_blocked_ip(hostname):
        raise ConnectorConnectionFailedError(f"Host de conector no permitido: {hostname}")
