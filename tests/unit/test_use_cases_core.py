"""
Branch-coverage tests for 0%-coverage use cases and core modules.
Covers: AuthenticateUser, CreateOrganization, LaunchVerification,
        GetVerificationHistory, UpdateRelease, ToggleConnectorStatus,
        FernetCredentialEncryptor, pseudonymize.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit

VALID_FERNET_KEY = "g7vylajG0IOM0hvMbCNcVWN7G9l1oIF_pHFIj5uO5m8=" # NOSONAR


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_user(*, is_active=True, role=None, email="test@example.com"):
    from domain.entities.user import User
    from domain.enums import UserRole
    return User(
        id=uuid4(),
        email=email,
        hashed_password="hashed",
        display_name="Test User",
        role=role or UserRole.U2,
        is_active=is_active,
    )


def _make_release(status=None, *, artifacts=None, name="v1.0.0", version="1.0.0"):
    from domain.entities.release import Release
    from domain.enums import ReleaseStatus
    return Release(
        id=uuid4(),
        name=name,
        version=version,
        project_id=uuid4(),
        profile_id=uuid4(),
        created_by=uuid4(),
        status=status or ReleaseStatus.BORRADOR,
        artifacts=artifacts if artifacts is not None else [],
    )


def _make_connector(status=None):
    from domain.entities.connector_instance import ConnectorInstance
    from domain.enums import ConnectorStatus
    return ConnectorInstance(
        id=uuid4(),
        name="test-connector",
        connector_type="GESTOR_TAREAS",
        connector_implementation="JIRA",
        organization_id=uuid4(),
        encrypted_credentials=b"encrypted",
        status=status or ConnectorStatus.ACTIVO,
    )


# ── 1. AuthenticateUserUseCase ───────────────────────────────────────────────

class TestAuthenticateUserUseCase:
    @pytest.fixture
    def svc(self):
        from application.use_cases.others.authenticate_user import AuthenticateUserUseCase
        user_repo = AsyncMock()
        token_svc = MagicMock()
        pw_hasher = MagicMock()
        return AuthenticateUserUseCase(user_repo, token_svc, pw_hasher), user_repo, token_svc, pw_hasher

    async def test_user_not_found_raises_value_error(self, svc):
        """Branch: user_repo.get_by_email returns None → ValueError"""
        use_case, user_repo, *_ = svc
        user_repo.get_by_email = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="Credenciales inválidas"):
            await use_case.execute("no@user.com", "password")

    async def test_inactive_user_raises_value_error(self, svc):
        """Branch: user.is_active is False → ValueError"""
        use_case, user_repo, *_ = svc
        user = _make_user(is_active=False)
        user_repo.get_by_email = AsyncMock(return_value=user)
        with pytest.raises(ValueError, match="Usuario inactivo"):
            await use_case.execute(user.email, "password")

    async def test_wrong_password_raises_value_error(self, svc):
        """Branch: password_hasher.verify_password returns False → ValueError"""
        use_case, user_repo, _, pw_hasher = svc
        user = _make_user()
        user_repo.get_by_email = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=False)
        with pytest.raises(ValueError, match="Credenciales inválidas"):
            await use_case.execute(user.email, "wrong-password")

    async def test_success_returns_auth_result(self, svc):
        """Branch: all validations pass → AuthResult with tokens"""
        use_case, user_repo, token_svc, pw_hasher = svc
        from domain.enums import UserRole
        user = _make_user(role=UserRole.U2)
        user_repo.get_by_email = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=True)
        token_svc.create_access_token = MagicMock(side_effect=["access-token", "refresh-token"])

        result = await use_case.execute(user.email, "correct-password")

        assert result.access_token == "access-token"
        assert result.refresh_token == "refresh-token"
        assert result.user_id == user.id
        assert result.role == UserRole.U2
        assert result.token_type == "bearer"

        token_svc.create_access_token.assert_any_call(
            user_id=user.id,
            role=user.role.value,
            email=user.email,
            organization_id=user.organization_id,
            expires_in=3600,
        )
        token_svc.create_access_token.assert_any_call(
            user_id=user.id,
            role=user.role.value,
            email=user.email,
            organization_id=user.organization_id,
            expires_in=86400,
        )


# ── 2. CreateOrganizationUseCase ─────────────────────────────────────────────

class TestCreateOrganizationUseCase:
    @pytest.fixture
    def svc(self):
        from application.use_cases.others.create_organization import CreateOrganizationUseCase
        org_repo = AsyncMock()
        return CreateOrganizationUseCase(org_repo), org_repo

    async def test_duplicate_slug_raises_duplicate_entity_error(self, svc):
        """Branch: get_by_slug returns existing org → DuplicateEntityError"""
        use_case, org_repo = svc
        from domain.entities.organization import Organization
        existing = Organization(name="existing", slug="my-slug")
        org_repo.get_by_slug = AsyncMock(return_value=existing)
        from domain.exceptions import DuplicateEntityError
        with pytest.raises(DuplicateEntityError, match="Ya existe una organización"):
            await use_case.execute("new-name", "my-slug")

    async def test_success_creates_and_returns_organization(self, svc):
        """Branch: slug is unique → org created and returned"""
        use_case, org_repo = svc
        org_repo.get_by_slug = AsyncMock(return_value=None)
        from domain.entities.organization import Organization
        created = Organization(name="new-org", slug="new-slug")
        org_repo.create = AsyncMock(return_value=created)

        result = await use_case.execute("new-org", "new-slug")

        assert result.name == "new-org"
        assert result.slug == "new-slug"
        org_repo.create.assert_awaited_once()


# ── 3. LaunchVerificationUseCase ─────────────────────────────────────────────

class TestLaunchVerificationUseCase:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.launch_verification import LaunchVerificationUseCase
        release_repo = AsyncMock()
        task_queue = AsyncMock()
        return LaunchVerificationUseCase(release_repo, task_queue), release_repo, task_queue

    async def test_release_not_found_raises_validation_error(self, svc):
        """Branch: get_by_id returns None → ValidationError"""
        use_case, release_repo, _ = svc
        release_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Release no encontrada"):
            await use_case.execute(uuid4())

    async def test_invalid_status_raises_validation_error(self, svc):
        """Branch: release.status not in valid_statuses → ValidationError"""
        use_case, release_repo, _ = svc
        from domain.enums import ReleaseStatus
        release = _make_release(status=ReleaseStatus.ARCHIVADA, artifacts=[MagicMock()])
        release_repo.get_by_id = AsyncMock(return_value=release)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="No se puede iniciar verificación"):
            await use_case.execute(release.id)

    async def test_no_artifacts_raises_validation_error(self, svc):
        """Branch: release has empty artifacts → ValidationError"""
        use_case, release_repo, _ = svc
        from domain.enums import ReleaseStatus
        release = _make_release(status=ReleaseStatus.PENDIENTE, artifacts=[])
        release_repo.get_by_id = AsyncMock(return_value=release)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="sin artefactos"):
            await use_case.execute(release.id)

    async def test_pendiente_with_artifacts_succeeds(self, svc):
        """Branch: release in PENDIENTE + has artifacts → success"""
        use_case, release_repo, task_queue = svc
        from domain.enums import ReleaseStatus
        release = _make_release(status=ReleaseStatus.PENDIENTE, artifacts=[MagicMock()])
        release_repo.get_by_id = AsyncMock(return_value=release)
        release_repo.update_status = AsyncMock()
        task_queue.enqueue_verification_task = AsyncMock(return_value="task-123")

        result = await use_case.execute(release.id)

        assert result == "task-123"
        release_repo.update_status.assert_awaited_once_with(release.id, ReleaseStatus.EN_VERIFICACION)
        task_queue.enqueue_verification_task.assert_awaited_once_with(release.id)

    async def test_valida_status_with_artifacts_succeeds(self, svc):
        """Branch: release in VALIDA + has artifacts → success (valid_statuses includes VALIDA)"""
        use_case, release_repo, task_queue = svc
        from domain.enums import ReleaseStatus
        release = _make_release(status=ReleaseStatus.VALIDA, artifacts=[MagicMock()])
        release_repo.get_by_id = AsyncMock(return_value=release)
        release_repo.update_status = AsyncMock()
        task_queue.enqueue_verification_task = AsyncMock(return_value="task-456")

        result = await use_case.execute(release.id)

        assert result == "task-456"
        release_repo.update_status.assert_awaited_once_with(release.id, ReleaseStatus.EN_VERIFICACION)


# ── 4. GetVerificationHistoryUseCase ─────────────────────────────────────────

class TestGetVerificationHistoryUseCase:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.get_verification_history import GetVerificationHistoryUseCase
        verification_repo = AsyncMock()
        return GetVerificationHistoryUseCase(verification_repo), verification_repo

    async def test_empty_release_id_raises_validation_error(self, svc):
        """Branch: release_id is falsy (None/empty) → ValidationError"""
        use_case, _ = svc
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="release_id es requerido"):
            await use_case.execute(None)

    async def test_valid_release_id_returns_history(self, svc):
        """Branch: valid release_id → returns list from repository"""
        use_case, verification_repo = svc
        from domain.entities.verification_result import VerificationResult
        from domain.enums import VerdictType
        vr = VerificationResult(
            id=uuid4(),
            release_id=uuid4(),
            verdict=VerdictType.VALID,
            rule_results=[],
            summary={"text": "all good"},
        )
        verification_repo.find_by_release = AsyncMock(return_value=[vr])

        result = await use_case.execute(uuid4())

        assert len(result) == 1
        assert result[0].verdict == "VALID"
        assert result[0].summary == {"text": "all good"}


# ── 5. UpdateReleaseUseCase ──────────────────────────────────────────────────

class TestUpdateReleaseUseCase:
    @pytest.fixture
    def svc(self):
        from application.use_cases.others.update_release import UpdateReleaseUseCase
        release_repo = AsyncMock()
        return UpdateReleaseUseCase(release_repo), release_repo

    async def test_invalid_semver_raises_validation_error(self, svc):
        """Branch: _is_valid_semver returns False → ValidationError"""
        use_case, _ = svc
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="SemVer"):
            await use_case.execute(uuid4(), "new-name", "not-semver", "desc")

    async def test_release_not_found_raises_validation_error(self, svc):
        """Branch: valid semver but release not found → ValidationError"""
        use_case, release_repo = svc
        release_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="No se encontró el release"):
            await use_case.execute(uuid4(), "new-name", "1.0.0", "desc")

    async def test_success_updates_and_returns_release(self, svc):
        """Branch: valid semver + release found → fields updated + returned"""
        use_case, release_repo = svc
        release = _make_release(name="old", version="0.1.0", artifacts=[])
        release_repo.get_by_id = AsyncMock(return_value=release)
        release_repo.update = AsyncMock(return_value=release)

        result = await use_case.execute(release.id, "new-name", "2.0.0", "new-desc")

        assert release.name == "new-name"
        assert release.version == "2.0.0"
        assert release.description == "new-desc"
        assert result == release
        release_repo.update.assert_awaited_once_with(release)

    # ── _is_valid_semver branch coverage ──────────────────────────────────

    def test_semver_valid_simple(self, svc):
        """Branch: simple valid semver '1.0.0' → True (no -, no +)"""
        use_case, _ = svc
        assert use_case._is_valid_semver("1.0.0") is True

    def test_semver_valid_with_prerelease(self, svc):
        """Branch: valid semver with pre-release '1.0.0-alpha.1' → True"""
        use_case, _ = svc
        assert use_case._is_valid_semver("1.0.0-alpha.1") is True

    def test_semver_valid_with_build(self, svc):
        """Branch: valid semver with build '1.0.0+build.1' → True (no -, + in core)"""
        use_case, _ = svc
        assert use_case._is_valid_semver("1.0.0+build.1") is True

    def test_semver_valid_with_prerelease_and_build(self, svc):
        """Branch: valid semver with pre-release + build '1.0.0-alpha+001' → True"""
        use_case, _ = svc
        assert use_case._is_valid_semver("1.0.0-alpha+001") is True

    def test_semver_invalid_core_non_numeric(self, svc):
        """Branch: core does not match MAJOR.MINOR.PATCH → False"""
        use_case, _ = svc
        assert use_case._is_valid_semver("not-semver") is False

    def test_semver_invalid_core_leading_zero(self, svc):
        """Branch: core has leading zero in minor '1.01.0' → False"""
        use_case, _ = svc
        assert use_case._is_valid_semver("1.01.0") is False

    def test_semver_invalid_core_missing_patch(self, svc):
        """Branch: core only has MAJOR.MINOR '1.0' → False"""
        use_case, _ = svc
        assert use_case._is_valid_semver("1.0") is False

    def test_semver_invalid_prerelease_double_dot(self, svc):
        """Branch: pre-release contains '..' → False"""
        use_case, _ = svc
        assert use_case._is_valid_semver("1.0.0-alpha..beta") is False

    def test_semver_invalid_build_double_dot(self, svc):
        """Branch: build contains '..' → False (no -, + in core)"""
        use_case, _ = svc
        assert use_case._is_valid_semver("1.0.0+build..1") is False

    def test_semver_valid_zero_major(self, svc):
        """Branch: valid semver with 0 major '0.1.0' → True"""
        use_case, _ = svc
        assert use_case._is_valid_semver("0.1.0") is True

    def test_semver_invalid_prerelease_empty_ident(self, svc):
        """Branch: pre-release with empty ident '1.0.0-alpha.' → False"""
        use_case, _ = svc
        assert use_case._is_valid_semver("1.0.0-alpha.") is False

    def test_semver_prerelease_dash_in_ident(self, svc):
        """Branch: pre-release with '-' inside ident (not separator) → True
        After split('-', 1), core='1.0.0', pre='alpha-1'. pre has no '+', 
        so pre stays as 'alpha-1'. Check if pre matches ident pattern.
        'alpha-1' matches r'^[0-9A-Za-z-]+(\\.[0-9A-Za-z-]+)*$' → True.
        """
        use_case, _ = svc
        assert use_case._is_valid_semver("1.0.0-alpha-1") is True

    def test_semver_with_plus_in_prerelease_no_build_metadata(self, svc):
        """Branch: '1.0.0+a.b' → no '-', '+' in core → split core/build.
        core='1.0.0', build='a.b'. Valid → True.
        """
        use_case, _ = svc
        assert use_case._is_valid_semver("1.0.0+a.b") is True


# ── 6. ToggleConnectorStatusUseCase ──────────────────────────────────────────

class TestToggleConnectorStatusUseCase:
    @pytest.fixture
    def svc(self):
        from application.use_cases.others.toggle_connector_status import ToggleConnectorStatusUseCase
        connector_repo = AsyncMock()
        return ToggleConnectorStatusUseCase(connector_repo), connector_repo

    async def test_connector_not_found_raises_entity_not_found_error(self, svc):
        """Branch: get_by_id returns None → EntityNotFoundError"""
        use_case, connector_repo = svc
        connector_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        from domain.enums import ConnectorStatus
        with pytest.raises(EntityNotFoundError, match="Conector no encontrado"):
            await use_case.execute(uuid4(), ConnectorStatus.ACTIVO)

    async def test_toggle_to_active_succeeds(self, svc):
        """Branch: connector found → status updated to ACTIVO"""
        use_case, connector_repo = svc
        from domain.enums import ConnectorStatus
        connector = _make_connector(status=ConnectorStatus.INACTIVO)
        connector_repo.get_by_id = AsyncMock(return_value=connector)
        connector_repo.update = AsyncMock(return_value=connector)

        result = await use_case.execute(connector.id, ConnectorStatus.ACTIVO)

        assert result.status == ConnectorStatus.ACTIVO
        connector_repo.update.assert_awaited_once_with(connector)

    async def test_toggle_to_inactive_succeeds(self, svc):
        """Branch: connector found → status updated to INACTIVO"""
        use_case, connector_repo = svc
        from domain.enums import ConnectorStatus
        connector = _make_connector(status=ConnectorStatus.ACTIVO)
        connector_repo.get_by_id = AsyncMock(return_value=connector)
        connector_repo.update = AsyncMock(return_value=connector)

        result = await use_case.execute(connector.id, ConnectorStatus.INACTIVO)

        assert result.status == ConnectorStatus.INACTIVO
        connector_repo.update.assert_awaited_once_with(connector)


# ── 7. FernetCredentialEncryptor ─────────────────────────────────────────────

class TestFernetCredentialEncryptor:
    @pytest.fixture
    def encryptor(self):
        from core.credential_encryptor import FernetCredentialEncryptor
        return FernetCredentialEncryptor(VALID_FERNET_KEY)

    def test_init_with_string_key_encodes_to_bytes(self):
        """Branch: key is str → encoded to bytes before Fernet init"""
        from core.credential_encryptor import FernetCredentialEncryptor
        enc = FernetCredentialEncryptor(VALID_FERNET_KEY)
        assert enc._fernet is not None

    def test_init_with_bytes_key_uses_directly(self):
        """Branch: key is bytes → used directly without encoding"""
        from core.credential_encryptor import FernetCredentialEncryptor
        key_bytes = VALID_FERNET_KEY.encode()
        enc = FernetCredentialEncryptor(key_bytes)  # type: ignore[arg-type]
        assert enc._fernet is not None

    def test_encrypt_returns_bytes(self, encryptor):
        """Branch: encrypt returns bytes (Fernet token)"""
        result = encryptor.encrypt("hello world", uuid4())
        assert isinstance(result, bytes)
        assert result != b"hello world"

    def test_decrypt_returns_original_string(self, encryptor):
        """Branch: decrypt reverses encrypt"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt("secret data", instance_id)
        decrypted = encryptor.decrypt(encrypted, instance_id)
        assert decrypted == "secret data"

    def test_encrypt_bytes_returns_bytes(self, encryptor):
        """Branch: encrypt_bytes returns Fernet token from bytes input"""
        result = encryptor.encrypt_bytes(b"binary data", uuid4())
        assert isinstance(result, bytes)

    def test_decrypt_bytes_returns_original_bytes(self, encryptor):
        """Branch: decrypt_bytes reverses encrypt_bytes"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt_bytes(b"binary payload", instance_id)
        decrypted = encryptor.decrypt_bytes(encrypted, instance_id)
        assert decrypted == b"binary payload"

    def test_decrypt_with_wrong_instance_id_still_works(self, encryptor):
        """Branch: decrypt ignores instance_id (Fernet does not use it)"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt("data", instance_id)
        decrypted = encryptor.decrypt(encrypted, uuid4())
        assert decrypted == "data"

    def test_decrypt_bytes_with_associated_data_ignored(self, encryptor):
        """Branch: associated_data is accepted but ignored (interface compliance)"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt_bytes(b"payload", instance_id, {"ctx": "test"})
        decrypted = encryptor.decrypt_bytes(encrypted, instance_id, {"ctx": "other"})
        assert decrypted == b"payload"

    def test_encrypt_with_associated_data_provided_ignored(self, encryptor):
        """Branch: encrypt with optional associated_data parameter"""
        result = encryptor.encrypt("test", uuid4(), associated_data={"key": "value"})
        assert isinstance(result, bytes)


# ── 8. pseudonymize ──────────────────────────────────────────────────────────

class TestPseudonymize:
    def test_scalar_passthrough_int(self):
        """Branch: input is int → returned as-is"""
        from core.pseudonymizer import pseudonymize
        assert pseudonymize(42) == 42

    def test_scalar_passthrough_string(self):
        """Branch: input is str → returned as-is"""
        from core.pseudonymizer import pseudonymize
        assert pseudonymize("plain text") == "plain text"

    def test_scalar_passthrough_none(self):
        """Branch: input is None → returned as-is"""
        from core.pseudonymizer import pseudonymize
        assert pseudonymize(None) is None

    def test_empty_dict_returns_empty_dict(self):
        """Branch: input is empty dict → returned empty dict"""
        from core.pseudonymizer import pseudonymize
        assert pseudonymize({}) == {}

    def test_dict_non_pii_keys_passthrough(self):
        """Branch: dict with non-PII keys → values passed through"""
        from core.pseudonymizer import pseudonymize
        data = {"task_id": "T-123", "status": "open", "priority": "high"}
        result = pseudonymize(data)
        assert result == data

    def test_dict_pii_email_is_hashed(self):
        """Branch: dict key 'email' with non-empty str → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"email": "user@example.com"}
        result = pseudonymize(data)
        assert result["email"].startswith("sha256:")
        assert result["email"] != "user@example.com"

    def test_dict_pii_name_is_hashed(self):
        """Branch: dict key 'name' (PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"name": "John Doe"}
        result = pseudonymize(data)
        assert result["name"].startswith("sha256:")

    def test_dict_pii_displayname_is_hashed(self):
        """Branch: dict key 'displayName' (case-insensitive PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"displayName": "Jane"}
        result = pseudonymize(data)
        assert result["displayName"].startswith("sha256:")

    def test_dict_pii_username_is_hashed(self):
        """Branch: dict key 'username' (PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"username": "jdoe"}
        result = pseudonymize(data)
        assert result["username"].startswith("sha256:")

    def test_dict_pii_assignee_is_hashed(self):
        """Branch: dict key 'assignee' (PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"assignee": "worker@corp.com"}
        result = pseudonymize(data)
        assert result["assignee"].startswith("sha256:")

    def test_dict_pii_author_is_hashed(self):
        """Branch: dict key 'author' (PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"author": "writer"}
        result = pseudonymize(data)
        assert result["author"].startswith("sha256:")

    def test_dict_pii_fullname_is_hashed(self):
        """Branch: dict key 'fullName' (case-insensitive PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"fullName": "Full Name Here"}
        result = pseudonymize(data)
        assert result["fullName"].startswith("sha256:")

    def test_dict_pii_empty_string_not_hashed(self):
        """Branch: PII key but value is empty str → not hashed (remains empty)"""
        from core.pseudonymizer import pseudonymize
        data = {"email": ""}
        result = pseudonymize(data)
        assert result["email"] == ""

    def test_dict_pii_non_string_value_not_hashed(self):
        """Branch: PII key but value is not str (e.g. list) → not hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"email": ["a", "b"]}
        result = pseudonymize(data)
        assert result["email"] == ["a", "b"]

    def test_list_of_dicts_each_processed(self):
        """Branch: input is list of dicts → each item pseudonymized"""
        from core.pseudonymizer import pseudonymize
        data = [{"email": "a@b.com"}, {"email": "c@d.com"}]
        result = pseudonymize(data)
        assert result[0]["email"].startswith("sha256:")
        assert result[1]["email"].startswith("sha256:")

    def test_nested_dict_pii_inner_hashed(self):
        """Branch: nested dict → inner PII keys hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"ticket": {"author": "dev1", "title": "fix bug"}}
        result = pseudonymize(data)
        assert result["ticket"]["author"].startswith("sha256:")
        assert result["ticket"]["title"] == "fix bug"

    def test_list_inside_dict_processed(self):
        """Branch: dict value is a list → each item in list pseudonymized"""
        from core.pseudonymizer import pseudonymize
        data = {"comments": [{"author": "u1"}, {"author": "u2"}]}
        result = pseudonymize(data)
        assert result["comments"][0]["author"].startswith("sha256:")
        assert result["comments"][1]["author"].startswith("sha256:")

    def test_mixed_types_passthrough(self):
        """Branch: float and bool values passed through unchanged"""
        from core.pseudonymizer import pseudonymize
        data = {"count": 5, "active": True, "rating": 4.5}
        result = pseudonymize(data)
        assert result == data

    def test_is_pii_key_case_insensitive(self):
        """Branch: _is_pii_key uses key.lower() → case insensitive"""
        from core.pseudonymizer import _is_pii_key
        assert _is_pii_key("EMAIL") is True
        assert _is_pii_key("Email") is True
        assert _is_pii_key("eMaIl") is True
        assert _is_pii_key("task_id") is False

    def test_hash_value_returns_prefixed_sha256(self):
        """Branch: _hash_value returns 'sha256:' + hex digest"""
        from core.pseudonymizer import _hash_value
        import hashlib
        value = "test@example.com"
        expected = "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()
        assert _hash_value(value) == expected
