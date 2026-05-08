"""
Test suite for ``CreateReleaseUseCase``.

A release represents a software artefact that is a candidate for verification.
``CreateReleaseUseCase`` creates the entity with the correct initial state
(``BORRADOR``) and persists it linked to a project and a verification profile.

The release lifecycle follows a strict state machine:
    BORRADOR → PENDIENTE → EN_VERIFICACION → COMPLETADA

This use case handles the first transition: instantiating the release in
``BORRADOR`` before the operator submits it for verification.

Testing strategy:
    Unit tests. Both the release repository (``IReleaseRepository``) and the
    organisation repository (``IOrganizationRepository``) are replaced by
    ``AsyncMock`` to isolate domain construction logic from infrastructure.

Key invariants verified:
    - Every release is created in state ``BORRADOR``, without exception.
    - Project, profile, version, and creator identifiers are preserved exactly
      as provided by the command.
    - Persistence is delegated exactly once to the release repository.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.create_release import CreateReleaseUseCase, CreateReleaseCommand
from domain.entities.enums import ReleaseStatus


class TestCreateReleaseUseCase:
    """
    Unit tests for ``CreateReleaseUseCase``.

    Verifies that every release is instantiated in state ``BORRADOR`` with the
    correct fields and that persistence is delegated to the repository.
    """

    def _make_command(self, **kwargs) -> CreateReleaseCommand:
        """
        Builds a ``CreateReleaseCommand`` with default test values.

        Accepts keyword overrides to simplify scenario variation without
        repeating the full initialisation in each test.
        """
        defaults = {
            "project_id": uuid.uuid4(),
            "profile_id": uuid.uuid4(),
            "version": "1.0.0",
            "created_by": uuid.uuid4(),
            "description": "Initial release",
        }
        return CreateReleaseCommand(**{**defaults, **kwargs})

    async def test_release_created_with_borrador_status(self):
        """
        Every newly created release adopts the initial state ``BORRADOR``.

        Given:  A release repository configured to return the received object.
        When:   ``CreateReleaseUseCase`` is executed with a standard command.
        Then:   The resulting release status is ``ReleaseStatus.BORRADOR``,
                matching the first link in the domain state machine.
        """
        release_repo = AsyncMock()
        org_repo = AsyncMock()
        release_repo.create.side_effect = lambda r: r

        result = await CreateReleaseUseCase(release_repo, org_repo).execute(
            self._make_command()
        )

        assert result.status == ReleaseStatus.BORRADOR

    async def test_release_has_correct_project_and_profile(self):
        """
        Project and profile identifiers are transferred without modification.

        Given:  A command with specific ``project_id`` and ``profile_id``.
        When:   The use case is executed.
        Then:   The resulting release references exactly the provided IDs,
                ensuring correct traceability within the entity graph.
        """
        project_id = uuid.uuid4()
        profile_id = uuid.uuid4()
        release_repo = AsyncMock()
        org_repo = AsyncMock()
        release_repo.create.side_effect = lambda r: r

        result = await CreateReleaseUseCase(release_repo, org_repo).execute(
            self._make_command(project_id=project_id, profile_id=profile_id)
        )

        assert result.project_id == project_id
        assert result.profile_id == profile_id

    async def test_release_has_correct_version_and_creator(self):
        """
        Semantic version and creator identifier are preserved in the entity.

        Given:  A command with ``version="2.5.1"`` and a specific ``created_by``.
        When:   The use case is executed.
        Then:   The resulting release exposes the exact values from the command,
                ensuring correct audit of who created which version.
        """
        creator_id = uuid.uuid4()
        release_repo = AsyncMock()
        org_repo = AsyncMock()
        release_repo.create.side_effect = lambda r: r

        result = await CreateReleaseUseCase(release_repo, org_repo).execute(
            self._make_command(version="2.5.1", created_by=creator_id)
        )

        assert result.version == "2.5.1"
        assert result.created_by == creator_id

    async def test_delegates_persistence_to_release_repo(self):
        """
        The entity is persisted via ``IReleaseRepository.create`` exactly once.

        Given:  A release repository with an instrumented ``create`` method.
        When:   The use case is executed with a valid command.
        Then:   ``release_repo.create`` is called once, preventing duplicate
                inserts and confirming that persistence responsibility belongs
                to the repository, not the use case.
        """
        release_repo = AsyncMock()
        org_repo = AsyncMock()
        release_repo.create.side_effect = lambda r: r

        await CreateReleaseUseCase(release_repo, org_repo).execute(self._make_command())

        release_repo.create.assert_called_once()
