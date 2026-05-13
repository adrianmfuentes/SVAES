from enum import Enum

class ReleaseStatus(str, Enum):
    BORRADOR = "BORRADOR"
    PENDIENTE = "PENDIENTE"
    EN_VERIFICACION = "EN_VERIFICACION"
    VALIDA = "VALIDA"
    CON_ADVERTENCIAS = "CON_ADVERTENCIAS"
    NO_VALIDA = "NO_VALIDA"
    ARCHIVADA = "ARCHIVADA"

class VerdictType(str, Enum):
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

class ArtifactType(str, Enum):
    TAREA = "TAREA"         # Historias de usuario, incidencias o tareas (ej. Jira)
    CODIGO = "CODIGO"       # Commits, ramas o etiquetas (ej. GitLab)
    DOCUMENTO = "DOCUMENTO" # Archivos o páginas de documentación (ej. Confluence)