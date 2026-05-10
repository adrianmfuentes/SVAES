"""
Test suite for ``CreateOrganizationUseCase`` and ``ListOrganizationsUseCase``.

Organizations are the root of the tenant hierarchy in SVAES: every project,
release, and connector belongs to an organization. These use cases encapsulate
the logic for creating and listing tenants, delegating persistence to
``IOrganizationRepository``.

Testing strategy:
    Pure unit tests. The repository is replaced by an ``AsyncMock`` to verify
    only entity construction logic and call contracts, without database dependencies.

Key invariants verified:
    - The ``Organization`` entity is built with the ``name`` and ``slug`` fields
      exactly as provided by the command.
    - The default plan for a new organization is ``"free"``.
    - The organization listing always filters by ``active_only=True``,
      preventing exposure of deactivated tenants.
    - When no active organizations exist, the use case returns an empty list
      without raising an exception.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.organization_use_cases import (
    CreateOrganizationUseCase,
    CreateOrganizationCommand,
    ListOrganizationsUseCase,
)
from domain.entities.organization import Organization


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_org(name: str = "Acme", slug: str = "acme") -> Organization:
    """Builds a test ``Organization`` with a random ID."""
    return Organization(id=uuid.uuid4(), name=name, slug=slug)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateOrganizationUseCase:
    """
    Unit tests for ``CreateOrganizationUseCase``.

    Verifies that the use case correctly constructs the ``Organization`` entity
    from the received command, delegates persistence to the repository, and
    respects domain defaults (plan «free»).
    """

    async def test_creates_and_returns_organization(self):
        """
        The use case returns the organization as returned by the repository.

        Given:  A repository whose ``create`` method returns an ``Organization`` instance.
        When:   ``CreateOrganizationUseCase`` is executed with valid name and slug.
        Then:   The result is the same instance returned by the repository and
                ``create`` is called exactly once.
        """
        org = _make_org()
        repo = AsyncMock()
        repo.create.return_value = org

        result = await CreateOrganizationUseCase(repo).execute(
            CreateOrganizationCommand(name="Acme", slug="acme")
        )

        assert result is org
        repo.create.assert_called_once()

    async def test_passes_correct_slug_to_repo(self):
        """
        The slug and name from the command are faithfully transferred to the persisted entity.

        Given:  A repository that returns the received argument without modification.
        When:   The use case is executed with ``name="Beta Corp"`` and ``slug="beta-corp"``.
        Then:   The resulting entity reflects exactly the command values,
                guaranteeing that the repository stores the expected canonical slug.
        """
        repo = AsyncMock()
        repo.create.side_effect = lambda o: o

        result = await CreateOrganizationUseCase(repo).execute(
            CreateOrganizationCommand(name="Beta Corp", slug="beta-corp")
        )

        assert result.slug == "beta-corp"
        assert result.name == "Beta Corp"

    def test_default_plan_is_free(self):
        """
        The default plan of ``CreateOrganizationCommand`` is ``"free"``.

        Given:  A command created without specifying the ``plan`` field.
        When:   The ``plan`` attribute of the command is accessed.
        Then:   The value is ``"free"``, in accordance with the business model
                that assigns the free tier to every newly created organization.
        """
        cmd = CreateOrganizationCommand(name="X", slug="x")
        assert cmd.plan == "free"


class TestListOrganizationsUseCase:
    """
    Unit tests for ``ListOrganizationsUseCase``.

    Verifies that the listing always queries only active organizations and that
    the use case propagates the repository result without transformations.
    """

    async def test_returns_active_organizations(self):
        """
        The use case returns exactly the list returned by the repository.

        Given:  A repository that returns two active organizations.
        When:   ``ListOrganizationsUseCase`` is executed.
        Then:   The resulting list matches the repository's list and ``list_all``
                is invoked with ``active_only=True``, guaranteeing that deactivated
                tenants are not exposed to API consumers.
        """
        orgs = [_make_org("A", "a"), _make_org("B", "b")]
        repo = AsyncMock()
        repo.list_all.return_value = orgs

        result = await ListOrganizationsUseCase(repo).execute()

        assert result == orgs
        repo.list_all.assert_called_once_with(active_only=True, skip=0, limit=100)

    async def test_returns_empty_list_when_no_orgs(self):
        """
        When no active organizations exist, the use case returns an empty list without error.

        Given:  A repository that returns an empty list.
        When:   ``ListOrganizationsUseCase`` is executed.
        Then:   The result is an empty list (``[]``), preventing the absence of
                data from being treated as an error condition in the application layer.
        """
        repo = AsyncMock()
        repo.list_all.return_value = []

        result = await ListOrganizationsUseCase(repo).execute()

        assert result == []
