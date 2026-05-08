"""
Test suite for ``CreateProjectUseCase``.

Projects are the second level of the SVAES hierarchy: they group releases under
an organization and define the logical context of each verification cycle.
``CreateProjectUseCase`` encapsulates the construction and persistence logic for
new projects.

Testing strategy:
    Unit tests. The ``IProjectRepository`` is replaced by an ``AsyncMock`` to
    verify entity composition and the persistence contract in isolation.

Key invariants verified:
    - The resulting ``Project`` entity exactly reflects the command fields
      (``organization_id``, ``name``, ``description``).
    - Persistence is delegated to the repository and the final result is the
      object returned by ``repo.create``.
    - The ``description`` field defaults to an empty string, allowing minimal
      projects to be created without optional fields.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.project_use_cases import CreateProjectUseCase, CreateProjectCommand
from domain.entities.project import Project


class TestCreateProjectUseCase:
    """
    Unit tests for ``CreateProjectUseCase``.

    Validates correct construction of the ``Project`` entity and delegation of
    persistence to the repository, including default-value behavior of the command.
    """

    async def test_creates_project_with_correct_fields(self):
        """
        Command fields are faithfully transferred to the created ``Project`` entity.

        Given:  A repository that returns the received object without modification and
                a command with explicit ``organization_id``, ``name``, and ``description``.
        When:   ``CreateProjectUseCase`` is executed with that command.
        Then:   The resulting entity has exactly the values provided in the command,
                confirming that the use case does not alter the input data.
        """
        org_id = uuid.uuid4()
        repo = AsyncMock()
        repo.create.side_effect = lambda p: p

        cmd = CreateProjectCommand(organization_id=org_id, name="Backend", description="Core API")
        result = await CreateProjectUseCase(repo).execute(cmd)

        assert result.organization_id == org_id
        assert result.name == "Backend"
        assert result.description == "Core API"

    async def test_delegates_persistence_to_repo(self):
        """
        The use case persists the entity through the repository and returns its result.

        Given:  A repository that returns a predefined ``Project`` instance.
        When:   The use case is executed with a command matching that instance.
        Then:   The returned object is exactly the repository instance and
                ``repo.create`` is called exactly once, ensuring no retry logic
                or duplicate creation exists.
        """
        repo = AsyncMock()
        saved = Project(organization_id=uuid.uuid4(), name="X", description="")
        repo.create.return_value = saved

        result = await CreateProjectUseCase(repo).execute(
            CreateProjectCommand(organization_id=saved.organization_id, name="X")
        )

        assert result is saved
        repo.create.assert_called_once()

    def test_default_description_is_empty(self):
        """
        Omitting ``description`` in the command produces an empty description, not an error.

        Given:  A ``CreateProjectCommand`` constructed without the ``description`` field.
        When:   The ``description`` attribute of the command is accessed.
        Then:   The value is the empty string ``""``, allowing projects to be registered
                with minimal information without violating any domain constraint.
        """
        cmd = CreateProjectCommand(organization_id=uuid.uuid4(), name="Minimal")
        assert cmd.description == ""
