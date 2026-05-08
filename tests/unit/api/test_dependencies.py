"""
Tests for FastAPI dependency functions.

Tests ``get_current_user`` by calling it directly with mocked credentials,
repository, and JWT handler — no HTTP layer needed.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from jwt.exceptions import InvalidTokenError
from api.dependencies import get_current_user
from domain.entities.user import User
from domain.entities.enums import UserRole


def _make_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="$2b$12$hashed", # NOSONAR
        role=UserRole.OPERATOR,
        organization_id=uuid.uuid4(),
    )


class TestGetCurrentUser:
    async def test_valid_token_returns_user(self):
        user = _make_user()
        credentials = MagicMock()
        credentials.credentials = "valid.jwt.token"

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user

        jwt_handler = MagicMock()
        jwt_handler.decode_token.return_value = {"sub": str(user.id)}

        result = await get_current_user(credentials, user_repo, jwt_handler)

        assert result is user

    async def test_invalid_token_raises_401(self):
        credentials = MagicMock()
        credentials.credentials = "bad.token.here"

        user_repo = AsyncMock()
        jwt_handler = MagicMock()
        jwt_handler.decode_token.side_effect = InvalidTokenError("expired")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, user_repo, jwt_handler)

        assert exc_info.value.status_code == 401
        assert exc_info.value.headers is not None
        assert exc_info.value.headers.get("WWW-Authenticate") is not None

    async def test_missing_sub_claim_raises_401(self):
        credentials = MagicMock()
        credentials.credentials = "token.without.sub"

        user_repo = AsyncMock()
        jwt_handler = MagicMock()
        jwt_handler.decode_token.return_value = {"role": "OPERATOR"}  # no 'sub'

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, user_repo, jwt_handler)

        assert exc_info.value.status_code == 401

    async def test_invalid_uuid_in_sub_raises_401(self):
        credentials = MagicMock()
        credentials.credentials = "token.with.invalid.uuid"

        user_repo = AsyncMock()
        jwt_handler = MagicMock()
        jwt_handler.decode_token.return_value = {"sub": "not-a-valid-uuid"}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, user_repo, jwt_handler)

        assert exc_info.value.status_code == 401

    async def test_user_not_found_raises_401(self):
        user_id = uuid.uuid4()
        credentials = MagicMock()
        credentials.credentials = "valid.token"

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = None

        jwt_handler = MagicMock()
        jwt_handler.decode_token.return_value = {"sub": str(user_id)}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, user_repo, jwt_handler)

        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Factory function tests
# ---------------------------------------------------------------------------

class TestDependencyFactories:
    def test_get_password_hasher_returns_instance(self):
        from api.dependencies import get_password_hasher
        from infrastructure.security.password_hasher import BcryptPasswordHasher
        result = get_password_hasher()
        assert isinstance(result, BcryptPasswordHasher)

    def test_get_jwt_handler_returns_instance(self):
        from api.dependencies import get_jwt_handler
        from infrastructure.security.jwt_handler import JwtHandler
        result = get_jwt_handler()
        assert isinstance(result, JwtHandler)

    def test_get_credential_encryptor_returns_instance(self):
        from api.dependencies import get_credential_encryptor
        from infrastructure.security.credential_encryptor import FernetCredentialEncryptor
        result = get_credential_encryptor()
        assert isinstance(result, FernetCredentialEncryptor)

    def test_get_connector_registry_returns_instance(self):
        from api.dependencies import get_connector_registry
        from infrastructure.adapters.connector_registry import ConnectorRegistry
        result = get_connector_registry()
        assert isinstance(result, ConnectorRegistry)

    def test_get_release_repository_returns_instance(self):
        from api.dependencies import get_release_repository
        from infrastructure.database.repositories.release_repository import SqlReleaseRepository
        session = MagicMock()
        result = get_release_repository(session=session)
        assert isinstance(result, SqlReleaseRepository)

    def test_get_connector_repository_returns_instance(self):
        from api.dependencies import get_connector_repository
        from infrastructure.database.repositories.connector_repository import SqlConnectorRepository
        session = MagicMock()
        result = get_connector_repository(session=session)
        assert isinstance(result, SqlConnectorRepository)

    def test_get_user_repository_returns_instance(self):
        from api.dependencies import get_user_repository
        from infrastructure.database.repositories.user_repository import SqlUserRepository
        session = MagicMock()
        result = get_user_repository(session=session)
        assert isinstance(result, SqlUserRepository)

    def test_get_organization_repository_returns_instance(self):
        from api.dependencies import get_organization_repository
        from infrastructure.database.repositories.organization_repository import SqlOrganizationRepository
        session = MagicMock()
        result = get_organization_repository(session=session)
        assert isinstance(result, SqlOrganizationRepository)

    def test_get_profile_repository_returns_instance(self):
        from api.dependencies import get_profile_repository
        from infrastructure.database.repositories.profile_repository import SqlProfileRepository
        session = MagicMock()
        result = get_profile_repository(session=session)
        assert isinstance(result, SqlProfileRepository)

    def test_get_project_repository_returns_instance(self):
        from api.dependencies import get_project_repository
        from infrastructure.database.repositories.project_repository import SqlProjectRepository
        session = MagicMock()
        result = get_project_repository(session=session)
        assert isinstance(result, SqlProjectRepository)

    def test_get_login_use_case_returns_instance(self):
        from api.dependencies import get_login_use_case
        from application.use_cases.auth_use_cases import LoginUseCase
        result = get_login_use_case(
            user_repo=MagicMock(),
            password_hasher=MagicMock(),
            token_service=MagicMock(),
        )
        assert isinstance(result, LoginUseCase)

    def test_get_create_organization_use_case_returns_instance(self):
        from api.dependencies import get_create_organization_use_case
        from application.use_cases.organization_use_cases import CreateOrganizationUseCase
        result = get_create_organization_use_case(org_repo=MagicMock())
        assert isinstance(result, CreateOrganizationUseCase)

    def test_get_list_organizations_use_case_returns_instance(self):
        from api.dependencies import get_list_organizations_use_case
        from application.use_cases.organization_use_cases import ListOrganizationsUseCase
        result = get_list_organizations_use_case(org_repo=MagicMock())
        assert isinstance(result, ListOrganizationsUseCase)

    def test_get_manage_profile_use_case_returns_instance(self):
        from api.dependencies import get_manage_profile_use_case
        from application.use_cases.manage_profile import ManageProfileUseCase
        result = get_manage_profile_use_case(profile_repo=MagicMock())
        assert isinstance(result, ManageProfileUseCase)

    def test_get_create_project_use_case_returns_instance(self):
        from api.dependencies import get_create_project_use_case
        from application.use_cases.project_use_cases import CreateProjectUseCase
        result = get_create_project_use_case(project_repo=MagicMock())
        assert isinstance(result, CreateProjectUseCase)

    def test_get_create_release_use_case_returns_instance(self):
        from api.dependencies import get_create_release_use_case
        from application.use_cases.create_release import CreateReleaseUseCase
        result = get_create_release_use_case(
            release_repo=MagicMock(),
            org_repo=MagicMock(),
        )
        assert isinstance(result, CreateReleaseUseCase)

    def test_get_verification_history_use_case_returns_instance(self):
        from api.dependencies import get_verification_history_use_case
        from application.use_cases.get_verification_history import GetVerificationHistoryUseCase
        result = get_verification_history_use_case(release_repo=MagicMock())
        assert isinstance(result, GetVerificationHistoryUseCase)

    def test_get_launch_verification_use_case_returns_instance(self):
        from api.dependencies import get_launch_verification_use_case
        from application.use_cases.launch_verification import LaunchVerificationUseCase
        result = get_launch_verification_use_case(release_repo=MagicMock())
        assert isinstance(result, LaunchVerificationUseCase)

    def test_get_configure_connector_use_case_returns_instance(self):
        from api.dependencies import get_configure_connector_use_case
        from application.use_cases.configure_connector import ConfigureConnectorUseCase
        result = get_configure_connector_use_case(
            repo=MagicMock(),
            registry=MagicMock(),
            encryptor=MagicMock(),
        )
        assert isinstance(result, ConfigureConnectorUseCase)
