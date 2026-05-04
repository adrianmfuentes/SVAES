from abc import ABC, abstractmethod
from typing import Optional, List
import uuid

from domain.entities.organization import Organization

class IOrganizationRepository(ABC):
    """
    Puerto de salida (Outbound Port): IOrganizationRepository
    Define el contrato para la persistencia de la entidad Organization.
    La capa de dominio y aplicación interactúa con esta interfaz sin conocer
    si los datos van a PostgreSQL, a memoria, o a otro lugar.
    """

    @abstractmethod
    async def create(self, organization: Organization) -> Organization:
        """Persiste una nueva organización en el almacén de datos."""
        pass

    @abstractmethod
    async def get_by_id(self, organization_id: uuid.UUID) -> Optional[Organization]:
        """
        Recupera una organización por su identificador único.
        Retorna None si no se encuentra.
        """
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        """
        Recupera una organización por su slug (que es UNIQUE según el esquema).
        Retorna None si no se encuentra.
        """
        pass

    @abstractmethod
    async def list_all(self, active_only: bool = True) -> List[Organization]:
        """
        Devuelve un listado de organizaciones.
        Permite filtrar para devolver solo las activas.
        """
        pass

    @abstractmethod
    async def update(self, organization: Organization) -> Organization:
        """Actualiza el estado de una organización existente."""
        pass