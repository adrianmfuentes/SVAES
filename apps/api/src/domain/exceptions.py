class DomainException(Exception):
    """
    Clase base para todas las excepciones del dominio.
    Permite capturar cualquier error de negocio de forma genérica en la capa API.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

# --- Excepciones de Entidad ---
class EntityNotFoundError(DomainException):
    """Lanzada cuando una entidad (Organization, Release, etc.) no existe."""
    pass

# --- Excepciones de Release ---
class ReleaseInvalidStateError(DomainException):
    """
    Lanzada cuando se intenta una operación no permitida para el estado actual de la release.
    Ejemplo: Intentar verificar una release que ya está COMPLETADA.
    """
    def __init__(self, release_id, current_status, expected_status):
        message = f"La release {release_id} está en estado {current_status}, se esperaba {expected_status}."
        super().__init__(message)


# --- Excepciones de Conectores ---
class ConnectorConnectionFailedError(DomainException):
    """
    Lanzada cuando falla la prueba de conexión de un conector con la herramienta externa.
    Cubre errores de autenticación, timeout, etc.
    """
    pass

class InvalidConnectorConfigurationError(DomainException):
    """Lanzada cuando la configuración JSON proporcionada no cumple con el esquema del conector."""
    pass


# --- Excepciones de Seguridad / Multi-tenant ---
class UserNotBelongsToOrganizationError(DomainException):
    """
    Lanzada cuando un usuario intenta acceder o modificar recursos 
    de una organización (Tenant) a la que no pertenece.
    """
    pass

class VerificationProfileNotActiveError(DomainException):
    """Lanzada cuando se intenta usar un perfil de verificación que ha sido desactivado."""
    pass