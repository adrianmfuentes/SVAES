"""This module defines custom exceptions for the domain layer of the application. 
These exceptions are used to represent specific error conditions that can occur 
during business logic execution, such as invalid states, missing entities, or configuration issues. 

By using custom exceptions, we can provide more meaningful error messages and handle different error 
scenarios in a structured way within the API layer."""

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
class UserNotBelongsToOrganizationError(DomainException):
    pass
class VerificationProfileNotActiveError(DomainException):
    pass