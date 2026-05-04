from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Organization:
    """
    Entidad de Dominio: Organization
    Representa la entidad raíz del modelo multi-tenant del SVAES.
    Sin dependencias de frameworks externos (SQLAlchemy, Pydantic, etc.).
    """
    name: str
    slug: str
    plan: str
    is_active: bool = True
    
    # El ID se genera automáticamente como UUID4 si no se proporciona
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    
    # Fechas de auditoría
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_plan(self, new_plan: str) -> None:
        """Ejemplo de lógica de negocio pura encapsulada en la entidad."""
        self.plan = new_plan
        self.updated_at = datetime.now(timezone.utc)
        
    def deactivate(self) -> None:
        """Regla de negocio para desactivar un tenant."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)