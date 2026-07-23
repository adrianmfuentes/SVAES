"""
Este archivo define las excepciones personalizadas para el dominio de la aplicación.
Estas excepciones se utilizan para manejar errores específicos relacionados con la lógica de negocio y las entidades del dominio.
Cada excepción hereda de la clase base `DomainException`
"""

class DomainException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class EntityNotFoundError(DomainException):
    pass

class ReleaseInvalidStateError(DomainException):
    def __init__(self, release_id, current_status, expected_status):
        message = f"The  release {release_id} is in state {current_status}, expected {expected_status}."
        super().__init__(message)

class ConnectorConnectionFailedError(DomainException):
    pass

class InvalidConnectorConfigurationError(DomainException):
    pass

class DuplicateEntityError(DomainException):
    pass

class UserNotBelongsToOrganizationError(DomainException):
    pass

class VerificationProfileNotActiveError(DomainException):
    pass

class ValidationError(DomainException):
    pass

class AuthenticationError(DomainException):
    pass

class InvalidWebhookSignatureError(DomainException):
    pass