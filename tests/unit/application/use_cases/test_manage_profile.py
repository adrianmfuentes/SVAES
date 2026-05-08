"""
Test suite for ``ManageProfileUseCase``.

Verification profiles group sets of rules that determine the acceptance criteria
applied to a release. ``ManageProfileUseCase`` encapsulates the creation of new
profiles under a specific organization.

A profile is an entity with its own identity (auto-generated unique ID), which
allows it to be reused across multiple releases within the same tenant without
duplicating the associated rules.

Testing strategy:
    Unit tests. The ``IProfileRepository`` is replaced by an ``AsyncMock`` to
    isolate entity construction logic and verify the persistence contract without
    infrastructure dependencies.

Key invariants verified:
    - The resulting profile reflects the ``organization_id`` and ``name`` from the command.
    - Each invocation generates a unique ID: two executions of the same command produce
      entities with different IDs.
    - Persistence is delegated to the repository exactly once per creation.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.manage_profile import ManageProfileUseCase, CreateProfileCommand


class TestManageProfileUseCase:
    """
    Unit tests for ``ManageProfileUseCase``.

    Validates correct construction of verification profiles, uniqueness of their
    identifiers, and delegation of persistence to the repository.
    """

    async def test_create_profile_with_correct_org_and_name(self):
        """
        The created profile exactly reflects the ``organization_id`` and ``name`` from the command.

        Given:  A repository that returns the received object without modification and
                a command with explicit ``organization_id`` and ``name``.
        When:   ``ManageProfileUseCase.create_profile`` is invoked.
        Then:   The ``organization_id`` and ``name`` attributes of the resulting profile
                match those provided in the command, guaranteeing correct association
                of the profile with its owning tenant.
        """
        org_id = uuid.uuid4()
        repo = AsyncMock()
        repo.create.side_effect = lambda p: p

        result = await ManageProfileUseCase(repo).create_profile(
            CreateProfileCommand(organization_id=org_id, name="Prod Checklist")
        )

        assert result.organization_id == org_id
        assert result.name == "Prod Checklist"

    async def test_create_profile_generates_unique_id(self):
        """
        Two executions of the same command produce profiles with different IDs.

        Given:  A repository that returns the received object and an identical command
                applied twice consecutively.
        When:   ``create_profile`` is invoked twice with the same command.
        Then:   The IDs of the two resulting profiles are different, confirming that
                the entity generates its own UUID on each instantiation without
                depending on external sequences or the database.
        """
        repo = AsyncMock()
        repo.create.side_effect = lambda p: p
        org_id = uuid.uuid4()
        cmd = CreateProfileCommand(organization_id=org_id, name="Profile A")

        r1 = await ManageProfileUseCase(repo).create_profile(cmd)
        r2 = await ManageProfileUseCase(repo).create_profile(cmd)

        assert r1.id != r2.id

    async def test_delegates_persistence_to_repo(self):
        """
        Profile creation is delegated to the repository exactly once.

        Given:  A repository with an instrumented ``create`` method.
        When:   ``create_profile`` is invoked with a valid command.
        Then:   ``repo.create`` is called exactly once, confirming that the use case
                does not attempt to persist the profile through multiple paths or
                retry the operation after a first success.
        """
        repo = AsyncMock()
        repo.create.side_effect = lambda p: p

        await ManageProfileUseCase(repo).create_profile(
            CreateProfileCommand(organization_id=uuid.uuid4(), name="QA Profile")
        )

        repo.create.assert_called_once()
