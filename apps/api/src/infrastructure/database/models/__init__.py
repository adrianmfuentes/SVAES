# Mapea todos los modelos aquí para que Alembic los encuentre fácilmente

from .base import Base
from .organization import OrganizationModel
from .project import ProjectModel
from .release import ReleaseModel

# Exportamos explícitamente lo que queremos que esté disponible
__all__ = ["Base", "OrganizationModel", "ProjectModel", "ReleaseModel"]