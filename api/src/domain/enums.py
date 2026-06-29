from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"

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


class ConnectorType(str, Enum):
    GESTOR_TAREAS = "GESTOR_TAREAS"
    REPO_CODIGO = "REPO_CODIGO"
    SISTEMA_DOCUMENTAL = "SISTEMA_DOCUMENTAL"
    HERRAMIENTA_PLANIFICACION = "HERRAMIENTA_PLANIFICACION"
    GESTION_CAMBIOS = "GESTION_CAMBIOS"


class ConnectorImplementation(str, Enum):
    JIRA = "JIRA"
    LINEAR = "LINEAR"
    TRELLO = "TRELLO"
    ASANA = "ASANA"
    GITLAB = "GITLAB"
    GITHUB = "GITHUB"
    BITBUCKET = "BITBUCKET"
    GITEA = "GITEA"
    CONFLUENCE = "CONFLUENCE"
    NOTION = "NOTION"
    WIKIJS = "WIKIJS"
    BOOKSTACK = "BOOKSTACK"
    CLICKUP = "CLICKUP"
    TAIGA = "TAIGA"
    PLANE = "PLANE"
    MIRO = "MIRO"
    JIRA_SM = "JIRA_SM"
    GLPI = "GLPI"
    ZAMMAD = "ZAMMAD"
    REDMINE = "REDMINE"

class SeverityType(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RuleSeverityType(str, Enum):
    OBLIGATORIA = "OBLIGATORIA"
    OPCIONAL = "OPCIONAL"
    EXCLUIDA = "EXCLUIDA"


def severity_to_rule_severity(severity: SeverityType) -> RuleSeverityType:
    if severity in (SeverityType.CRITICAL, SeverityType.HIGH):
        return RuleSeverityType.OBLIGATORIA
    return RuleSeverityType.OPCIONAL


def rule_severity_to_string(severity: RuleSeverityType) -> str:
    return severity.value

class UserRole(str, Enum):
    U2 = "OPERATOR"  # Standard User
    U3 = "ADMIN"     # Global Administrator
    U4 = "MANAGER"   # Organization Manager

    def has_permission(self, permission: "Permission") -> bool:
        hierarchy = {
            UserRole.U2: [
                Permission.VIEW_DASHBOARD,
                Permission.VIEW_ORG_PROJECTS,
                Permission.CREATE_RELEASE,
                Permission.UPDATE_OWN_RELEASES,
                Permission.ARCHIVE_RELEASE,
                Permission.EXECUTE_VERIFICATION,
                Permission.VIEW_OWN_HISTORY,
                Permission.MANAGE_OWN_API_KEYS,
            ],
            UserRole.U4: [
                Permission.VIEW_DASHBOARD,
                Permission.VIEW_ORG_PROJECTS,
                Permission.CREATE_RELEASE,
                Permission.UPDATE_OWN_RELEASES,
                Permission.ARCHIVE_RELEASE,
                Permission.EXECUTE_VERIFICATION,
                Permission.VIEW_OWN_HISTORY,
                Permission.MANAGE_OWN_API_KEYS,
                Permission.CREATE_PROJECT,
                Permission.UPDATE_PROJECT,
                Permission.ARCHIVE_PROJECT,
                Permission.DELETE_PROJECT,
                Permission.MANAGE_CONNECTORS,
                Permission.MANAGE_PROFILES,
                Permission.MANAGE_RULES,
                Permission.VIEW_ORG_DASHBOARD,
                Permission.INVITE_USERS,
                Permission.MANAGE_ROLES,
                Permission.TRANSFER_OWNERSHIP,
            ],
            UserRole.U3: list(
                Permission
            ),
        }
        return permission in hierarchy.get(self, [])

class Permission(str, Enum):
    VIEW_DASHBOARD = "VIEW_DASHBOARD"
    VIEW_OWN_PROJECTS = "VIEW_OWN_PROJECTS"
    CREATE_RELEASE = "CREATE_RELEASE"
    UPDATE_OWN_RELEASES = "UPDATE_OWN_RELEASES"
    ARCHIVE_RELEASE = "ARCHIVE_RELEASE"
    EXECUTE_VERIFICATION = "EXECUTE_VERIFICATION"
    VIEW_OWN_HISTORY = "VIEW_OWN_HISTORY"
    MANAGE_OWN_API_KEYS = "MANAGE_OWN_API_KEYS"
    VIEW_ORG_PROJECTS = "VIEW_ORG_PROJECTS"
    CREATE_PROJECT = "CREATE_PROJECT"
    UPDATE_PROJECT = "UPDATE_PROJECT"
    ARCHIVE_PROJECT = "ARCHIVE_PROJECT"
    DELETE_PROJECT = "DELETE_PROJECT"
    MANAGE_CONNECTORS = "MANAGE_CONNECTORS"
    MANAGE_PROFILES = "MANAGE_PROFILES"
    MANAGE_RULES = "MANAGE_RULES"
    VIEW_ORG_DASHBOARD = "VIEW_ORG_DASHBOARD"
    INVITE_USERS = "INVITE_USERS"
    MANAGE_ROLES = "MANAGE_ROLES"
    TRANSFER_OWNERSHIP = "TRANSFER_OWNERSHIP"
    MANAGE_ORGANIZATIONS = "MANAGE_ORGANIZATIONS"
    MANAGE_ALL_USERS = "MANAGE_ALL_USERS"

class AccessRequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ArtifactType(str, Enum):
    TAREA = "TAREA"
    CODIGO = "CODIGO"
    DOCUMENTO = "DOCUMENTO"
    PLAN = "PLAN"
    CAMBIO = "CAMBIO"