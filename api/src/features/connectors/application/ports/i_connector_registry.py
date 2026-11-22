from abc import ABC, abstractmethod
from typing import Any, Optional


class IConnectorRegistry(ABC):
    @abstractmethod
    def register(self, connector_type: str, connector: Any) -> None:
        pass

    @abstractmethod
    def get_by_implementation(self, impl_name: str) -> Any:
        pass

    @abstractmethod
    def get_by_type(self, connector_type: str) -> Optional[Any]:
        pass

    @abstractmethod
    def get_by_type_safe(self, connector_type: str) -> Optional[Any]:
        pass

    @abstractmethod
    def list_by_type(self, connector_type: str) -> list[Any]:
        pass

    @abstractmethod
    def list_all_implementations(self) -> list[str]:
        pass