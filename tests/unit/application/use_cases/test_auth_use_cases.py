"""
Test suite for ``LoginUseCase``.

``LoginUseCase`` es el servicio de aplicación responsable de autenticar usuarios
mediante credenciales de correo/contraseña y emitir un token JWT firmado. Constituye
la única entrada pública al sistema para sesiones no-OAuth.

Estrategia de prueba:
    Las pruebas son estrictamente unitarias. Los tres puertos externos
    (``IUserRepository``, ``IPasswordHasher``, ``ITokenService``) se sustituyen
    por dobles de prueba (``AsyncMock`` / ``MagicMock``) para aislar la lógica
    del caso de uso de cualquier infraestructura.

Invariantes clave verificadas:
    - Las credenciales incorrectas siempre lanzan ``ValueError``, independientemente
      de si el error proviene del email o de la contraseña (defensa contra
      enumeración de usuarios).
    - El token JWT **nunca** se emite si la autenticación falla.
    - Ante credenciales válidas, el token es el valor devuelto por
      ``ITokenService.create_access_token`` con los argumentos correctos.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from application.use_cases.auth_use_cases import LoginUseCase, LoginCommand
from domain.entities.user import User
from domain.entities.enums import UserRole


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_user():
    """Instancia de ``User`` con rol OPERATOR usada como usuario base en los tests."""
    return User(
        id=uuid.uuid4(),
        email="operador@ejemplo.com",
        hashed_password="$2b$12$hashedpassword",
        role=UserRole.OPERATOR,
        organization_id=uuid.uuid4(),
    )


@pytest.fixture
def user_repo(sample_user):
    """Repositorio stub que devuelve ``sample_user`` para cualquier email consultado."""
    repo = AsyncMock()
    repo.get_by_email.return_value = sample_user
    return repo


@pytest.fixture
def password_hasher():
    """Hasher stub configurado para verificar contraseñas correctamente (retorna ``True``)."""
    hasher = MagicMock()
    hasher.verify.return_value = True
    return hasher


@pytest.fixture
def token_service():
    """Servicio de tokens stub que devuelve un JWT de prueba predecible."""
    svc = MagicMock()
    svc.create_access_token.return_value = "jwt_token_abc"
    return svc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLoginUseCase:
    """
    Pruebas unitarias para ``LoginUseCase``.

    Cubre el flujo de autenticación completo: camino feliz, usuario inexistente,
    contraseña incorrecta y la garantía de no emisión de tokens en caso de fallo.
    Todos los colaboradores externos están aislados mediante dobles de prueba.
    """

    async def test_valid_credentials_return_token(
        self, user_repo, password_hasher, token_service, sample_user
    ):
        """
        Las credenciales válidas producen el JWT generado por ``ITokenService``.

        Given:  Un usuario existente en el repositorio y un hasher que valida la contraseña.
        When:   Se ejecuta ``LoginUseCase`` con el email y contraseña correctos.
        Then:   Se retorna el token JWT y ``create_access_token`` se invoca exactamente una
                vez con el ``user_id`` y ``role`` del usuario autenticado.
        """
        use_case = LoginUseCase(user_repo, password_hasher, token_service)
        token = await use_case.execute(
            LoginCommand(email=sample_user.email, password_plain="pass123") # NOSONAR
        )

        assert token == "jwt_token_abc"
        token_service.create_access_token.assert_called_once_with(
            user_id=sample_user.id,
            role=sample_user.role.value,
        )

    async def test_user_not_found_raises_value_error(self, password_hasher, token_service):
        """
        Un email no registrado provoca ``ValueError`` con mensaje genérico.

        Given:  Un repositorio que devuelve ``None`` para cualquier email.
        When:   Se intenta autenticar con un correo inexistente.
        Then:   Se lanza ``ValueError`` con el texto «inválidas», evitando revelar
                si el email existe en el sistema (mitigación de enumeración de usuarios).
        """
        repo = AsyncMock()
        repo.get_by_email.return_value = None
        use_case = LoginUseCase(repo, password_hasher, token_service)

        with pytest.raises(ValueError, match="Invalid credentials"):
            await use_case.execute(
                LoginCommand(email="noexiste@x.com", password_plain="pw") # NOSONAR
            )

    async def test_wrong_password_raises_value_error(self, user_repo, token_service):
        """
        Una contraseña incorrecta para un usuario existente provoca ``ValueError``.

        Given:  Un repositorio que encuentra al usuario pero un hasher que rechaza la contraseña.
        When:   Se ejecuta ``LoginUseCase`` con contraseña errónea.
        Then:   Se lanza ``ValueError`` con el mismo mensaje genérico que en el caso
                de email inexistente, garantizando respuestas indistinguibles al cliente.
        """
        bad_hasher = MagicMock()
        bad_hasher.verify.return_value = False
        use_case = LoginUseCase(user_repo, bad_hasher, token_service)

        with pytest.raises(ValueError, match="Invalid credentials"):
            await use_case.execute(
                LoginCommand(email="operador@ejemplo.com", password_plain="wrong") # NOSONAR
            )

    async def test_token_not_issued_when_user_not_found(self, password_hasher, token_service):
        """
        El servicio de tokens no se invoca si la autenticación falla por email inexistente.

        Given:  Un repositorio que no encuentra al usuario.
        When:   Se intenta el login y se captura la excepción esperada.
        Then:   ``ITokenService.create_access_token`` no se llama en ningún momento,
                eliminando cualquier posibilidad de emitir tokens no autorizados.
        """
        repo = AsyncMock()
        repo.get_by_email.return_value = None
        use_case = LoginUseCase(repo, password_hasher, token_service)

        with pytest.raises(ValueError):
            await use_case.execute(
                LoginCommand(email="x@x.com", password_plain="pw") # NOSONAR
            )

        token_service.create_access_token.assert_not_called()
