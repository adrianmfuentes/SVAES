from uuid import UUID
from application.ports.output.i_connector_repository import IConnectorRepository
from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus
from domain.exceptions import EntityNotFoundError

"""
Este módulo define el caso de uso para alternar el estado de un conector, que es responsable de cambiar el estado de un conector específico a activo o inactivo.
Incluye la lógica de negocio para validar que el conector existe antes de actualizar su estado. Si el conector no se encuentra, se lanza una excepción
indicando que el conector no fue encontrado.
"""
class ToggleConnectorStatusUseCase:
    def __init__(self, connector_repository: IConnectorRepository) -> None:
        self._connector_repo = connector_repository

    async def execute(self, connector_id: UUID, status: ConnectorStatus) -> ConnectorInstance:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")
        connector.status = status
        return await self._connector_repo.update(connector)