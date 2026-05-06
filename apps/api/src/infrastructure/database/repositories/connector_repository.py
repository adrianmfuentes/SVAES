from uuid import UUID
from sqlalchemy.orm import Session
from domain.entities.connector_instance import ConnectorInstance, ConnectorStatus
from domain.ports.i_connector_repository import IConnectorRepository
from infrastructure.database.models.connector_instance import ConnectorInstanceModel

class SqlConnectorRepository(IConnectorRepository):
    def __init__(self, session: Session):
        self.session = session

    async def save(self, connector: ConnectorInstance) -> ConnectorInstance:
        model = self.session.get(ConnectorInstanceModel, connector.id)
        if model is None:
            model = ConnectorInstanceModel(
                id=connector.id,
                organization_id=connector.organization_id,
                connector_type=connector.connector_type,
                name=connector.connector_type,
                config_encrypted=connector.encrypted_credentials,
                status=connector.status.value,
            )
            self.session.add(model)
        else:
            model.config_encrypted = connector.encrypted_credentials
            model.status = connector.status.value
        self.session.flush()
        return connector

    def find_by_id(self, connector_id: UUID) -> ConnectorInstance | None:
        model = self.session.get(ConnectorInstanceModel, connector_id)
        return self._to_entity(model) if model else None

    def find_by_organization(self, organization_id: UUID) -> list[ConnectorInstance]:
        models = (
            self.session.query(ConnectorInstanceModel)
            .filter_by(organization_id=organization_id)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: ConnectorInstanceModel) -> ConnectorInstance:
        return ConnectorInstance(
            id=model.id,
            organization_id=model.organization_id,
            connector_type=model.connector_type,
            encrypted_credentials=model.config_encrypted or b"",
            status=ConnectorStatus(model.status),
            created_at=model.created_at,
            updated_at=model.created_at,
        )