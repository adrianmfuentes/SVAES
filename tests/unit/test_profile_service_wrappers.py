"""
Branch-coverage tests for ProfileService wrapper methods that add audit logging
on top of ManageProfileUseCase base methods.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


class TestProfileServiceWrappers:
    """Cover ProfileService methods that are currently uncovered (the ones extending ManageProfileUseCase)."""

    @pytest.fixture
    def svc(self):
        from application.use_cases.main.profile_service import ProfileService
        profile_repo = AsyncMock()
        rule_repo = AsyncMock()
        return ProfileService(profile_repo, rule_repo), profile_repo, rule_repo

    @pytest.fixture(autouse=True)
    def _patch_audit(self):
        with patch("application.use_cases.main.profile_service.get_audit_logger") as mock_audit:
            mock_audit.return_value.log = MagicMock()
            yield

    async def test_create_profile_not_default(self, svc):
        """Branch: ProfileService.create_profile with is_default=False → delegates + audits"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        profile_repo.create = AsyncMock(return_value=p)
        profile_repo.get_default_for_organization = AsyncMock(return_value=None)

        result = await service.create_profile(uuid4(), "name", is_default=False)
        assert result == p

    async def test_create_profile_default_unsets_existing(self, svc):
        """Branch: ProfileService.create_profile is_default=True, existing default → unset"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        existing = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="old", is_default=True)
        new_p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="new", is_default=True)
        profile_repo.get_default_for_organization = AsyncMock(return_value=existing)
        profile_repo.update = AsyncMock(return_value=existing)
        profile_repo.create = AsyncMock(return_value=new_p)

        result = await service.create_profile(uuid4(), "new", is_default=True)
        assert existing.is_default is False
        assert result == new_p

    async def test_update_profile_success(self, svc):
        """Branch: ProfileService.update_profile → delegates + audits"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="updated-name")
        profile_repo.get_by_id = AsyncMock(return_value=p)
        profile_repo.update = AsyncMock(return_value=p)

        result = await service.update_profile(p.id, name="updated-name")
        assert result.name == "updated-name"

    async def test_duplicate_profile_success(self, svc):
        """Branch: ProfileService.duplicate_profile → delegates"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType

        rule = VerificationRule(profile_id=uuid4(), rule_template="RV01", severity=SeverityType.HIGH)
        original = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="orig", rules=[rule])
        copy = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="copy")
        profile_repo.get_by_id = AsyncMock(side_effect=[original, copy])
        profile_repo.create = AsyncMock(return_value=copy)
        rule_repo.create = AsyncMock(return_value=rule)

        result = await service.duplicate_profile(original.id, "copy")
        assert result.name == "copy"

    async def test_delete_profile_success(self, svc):
        """Branch: ProfileService.delete_profile found → deletes + audits"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        profile_repo.get_by_id = AsyncMock(return_value=p)
        profile_repo.delete = AsyncMock()

        await service.delete_profile(p.id, uuid4())
        profile_repo.delete.assert_awaited_once()

    async def test_delete_profile_not_found_raises(self, svc):
        """Branch: ProfileService.delete_profile not found → EntityNotFoundError"""
        service, profile_repo, rule_repo = svc
        profile_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.delete_profile(uuid4(), uuid4())

    async def test_add_rule_success(self, svc):
        """Branch: ProfileService.add_rule found → creates + audits"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType

        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        rule = VerificationRule(profile_id=p.id, rule_template="RV01", severity=SeverityType.HIGH)
        profile_repo.get_by_id = AsyncMock(return_value=p)
        rule_repo.create = AsyncMock(return_value=rule)

        result = await service.add_rule(p.id, "RV01")
        assert result.rule_template == "RV01"

    async def test_update_rule_success(self, svc):
        """Branch: ProfileService.update_rule → delegates + audits"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType

        rule = VerificationRule(profile_id=uuid4(), rule_template="RV01", severity=SeverityType.HIGH)
        rule_repo.get_by_id = AsyncMock(return_value=rule)
        rule_repo.update = AsyncMock(return_value=rule)

        result = await service.update_rule(rule.id, severity=SeverityType.LOW)
        assert result.severity == SeverityType.LOW

    async def test_delete_rule_success(self, svc):
        """Branch: ProfileService.delete_rule → delegates"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType

        rule = VerificationRule(profile_id=uuid4(), rule_template="RV01", severity=SeverityType.HIGH)
        rule_repo.get_by_id = AsyncMock(return_value=rule)
        rule_repo.delete = AsyncMock()

        await service.delete_rule(rule.id, uuid4())
        rule_repo.delete.assert_awaited_once()
