from abc import ABC, abstractmethod
from typing import Any, Dict, List, TypeVar
import ipaddress
import logging
from urllib.parse import urlparse
import httpx
from domain.exceptions import ConnectorConnectionFailedError

_log = logging.getLogger(__name__)

T = TypeVar("T")

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


class BaseHttpConnector(ABC):
    BASE_URL: str = ""
    CONNECTOR_TYPE: str = ""
    CONNECTOR_IMPLEMENTATION: str = ""
    TIMEOUT: float = 30.0
    CONTENT_TYPE: str = "application/json"

    def get_connector_type(self) -> str:
        return self.CONNECTOR_TYPE

    def get_connector_implementation(self) -> str:
        return self.CONNECTOR_IMPLEMENTATION

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.__class__.__name__.replace("Connector", ""),
            "version": "1.0",
            "artifact_types": self.get_artifact_types(),
        }

    @abstractmethod
    def get_artifact_types(self) -> List[str]:
        pass

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        raise NotImplementedError("Subclasses must implement _build_headers")

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        return config.get("base_url", self.BASE_URL)

    async def _get(
        self, url: str, config: Dict[str, Any], params: Dict[str, Any] | None = None
    ) -> httpx.Response:
        assert_safe_outbound_url(url)
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT, verify=True) as client:
                response = await client.get(url, headers=self._build_headers(config), params=params)
                return response
        except httpx.ConnectError as exc:
            _log.exception("SSL/connection error for %s: %s", url, exc)
            raise

    async def _post(
        self, url: str, config: Dict[str, Any], json: Dict[str, Any] | None = None
    ) -> httpx.Response:
        assert_safe_outbound_url(url)
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT, verify=True) as client:
                response = await client.post(url, headers=self._build_headers(config), json=json)
                return response
        except httpx.ConnectError as exc:
            _log.exception("SSL/connection error for %s: %s", url, exc)
            raise

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        url = self._get_health_url(config)
        response = await self._get(url, config)
        return response.status_code == 200

    @abstractmethod
    def _get_health_url(self, config: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        pass

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        url = self._get_fetch_url(ref, config)
        response = await self._get(url, config, self._get_fetch_params(config))
        response.raise_for_status()
        return response.json()

    @abstractmethod
    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        pass

    @abstractmethod
    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        pass

    @abstractmethod
    def _get_results_key(self) -> str:
        pass

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        url = self._get_list_url(filter_params, config)
        json_body = self._get_list_json(filter_params, config)
        if json_body is not None:
            response = await self._post(url, config, json_body)
        else:
            response = await self._get(url, config, self._get_list_params(filter_params, config))
        response.raise_for_status()
        data = response.json()
        key = self._get_results_key()
        if not key:
            return data if isinstance(data, list) else []
        return data.get(key, []) if isinstance(data, dict) else []


class BearerAuthMixin:
    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": BaseHttpConnector.CONTENT_TYPE,
            "Authorization": f"Bearer {config.get('token')}",
        }


class AtlassianAuthMixin:
    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        import base64
        email = config.get("email", "") or ""
        api_token = config.get("api_token", "") or ""
        credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        return {
            "Accept": BaseHttpConnector.CONTENT_TYPE,
            "Authorization": f"Basic {credentials}",
        }


class ApiKeyAuthMixin:
    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": BaseHttpConnector.CONTENT_TYPE,
            "Authorization": f"Bearer {config.get('token')}",
        }