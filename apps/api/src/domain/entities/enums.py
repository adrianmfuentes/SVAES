from enum import Enum

class ReleaseStatus(str, Enum):
    """Lifecycle states of a Release, enforced as a strict state machine."""
    BORRADOR = "BORRADOR"
    PENDIENTE = "PENDIENTE"
    EN_VERIFICACION = "EN_VERIFICACION"
    COMPLETADA = "COMPLETADA"

class VerdictType(str, Enum):
    """Final verdict emitted by the verification engine for a release."""
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    INVALID = "INVALID"

class ConnectorStatus(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    ERROR = "ERROR"

class SeverityType(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class UserRole(str, Enum):
    VIEWER = "VIEWER"
    OPERATOR = "OPERATOR"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"