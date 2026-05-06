from abc import ABC, abstractmethod
from typing import Any, Dict, List

class IConnector(ABC):
    """
    Puerto IConnector (Sección 5.5.1).
    Contrato único para toda integración con sistemas externos.
    """

    @abstractmethod
    async def test_connection(self, config: Dict[str, Any]) -> bool:
        """Comprueba que las credenciales y URL configuradas permiten establecer comunicación."""
        pass

    @abstractmethod
    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recupera los datos de un artefacto concreto y lo normaliza."""
        pass

    @abstractmethod
    async def list_artifacts(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recupera el conjunto de artefactos que corresponden a los filtros."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Retorna el identificador de tipo, versión y esquema JSON de configuración."""
        pass