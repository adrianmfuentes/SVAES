import base64
from typing import Any, Dict, List, Optional
import httpx
from application.ports.output.i_connector import IConnector
from infrastructure.secondary.connectors.base_http_connector import assert_safe_outbound_url

TIMEOUT = 30.0


def _dig(data: Any, dotted_key: Optional[str]) -> Any:
    """Navega `data` por un path separado por puntos (p.ej. "data.items")."""
    if not dotted_key:
        return data
    current = data
    for part in dotted_key.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _build_url(base_url: str, path: str) -> str:
    base = (base_url or "").rstrip("/")
    if not path:
        return base
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


class GenericHttpConnector(IConnector):
    """Conector REST configurable por instancia, sin código nuevo por sistema externo.

    Todo su comportamiento (URL base, rutas, tipo de autenticación, clave de
    resultados) viene de `config`, que es el mismo dict de credenciales que ya
    se guarda cifrado por cada conector. Por eso no encaja en las plantillas de
    método de `BaseHttpConnector` (asumen constantes de clase por vendor); se
    implementa `IConnector` directamente, igual que `RedmineConnector`.
    """

    IMPLEMENTATION = "CUSTOM"

    # "Categoría de origen" para el registro en `ConnectorRegistry`: no
    # representa una categoría real de negocio, solo el bucket en el que
    # aparece por defecto en `GET /connectors/types` antes de que
    # `_EXTRA_UI_CATEGORIES["CUSTOM"]` (connectors.py) lo añada también al
    # resto de categorías. El tipo real de cada instancia lo elige quien la
    # crea (ver connector_service.register_connector).
    _HOME_TYPE = "GESTOR_TAREAS"

    @property
    def connector_type(self) -> str:
        return self._HOME_TYPE

    @property
    def connector_implementation(self) -> str:
        return self.IMPLEMENTATION

    def get_connector_type(self) -> str:
        return self._HOME_TYPE

    def get_connector_implementation(self) -> str:
        return self.IMPLEMENTATION

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Custom",
            "version": "1.0",
            "artifact_types": ["custom"],
        }

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        auth_type = (config.get("auth_type") or "none").lower()
        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {config.get('token', '')}"
        elif auth_type == "basic":
            username = config.get("username", "") or ""
            password = config.get("password", "") or ""
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        elif auth_type == "header":
            header_name = config.get("auth_header_name") or ""
            if header_name:
                headers[header_name] = config.get("auth_header_value", "") or ""
        return headers

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        url = _build_url(config.get("base_url", ""), config.get("health_path", "") or "")
        assert_safe_outbound_url(url)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url, headers=self._build_headers(config))
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        template = config.get("fetch_path_template", "") or ""
        path = template.replace("{ref}", ref)
        url = _build_url(config.get("base_url", ""), path)
        assert_safe_outbound_url(url)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url, headers=self._build_headers(config))
            response.raise_for_status()
            data = response.json()
        result = _dig(data, config.get("fetch_result_key"))
        return result if isinstance(result, dict) else (data if isinstance(data, dict) else {})

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        url = _build_url(config.get("base_url", ""), config.get("list_path", "") or "")
        assert_safe_outbound_url(url)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url, headers=self._build_headers(config), params=filter_params)
            response.raise_for_status()
            data = response.json()
        result = _dig(data, config.get("list_result_key"))
        if isinstance(result, list):
            return result
        return data if isinstance(data, list) else []
