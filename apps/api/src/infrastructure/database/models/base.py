from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import DateTime
from datetime import datetime

class Base(DeclarativeBase):
    """
    Clase base para todos los modelos de SQLAlchemy 2.x.
    Mapea el metadato subyacente para Alembic.
    """
    type_annotation_map = {
        datetime: DateTime(timezone=True)
    }