"""
Test suite for ``GetVerificationHistoryUseCase``.

This use case provides the verification history of a release: given a release
identifier, it returns a structured summary with the final verdict, verification
duration, and evaluated rules.

It is a query use case within the implicit CQRS pattern of the application layer:
it does not modify state, only aggregates and projects data associated with an
already completed release.

Testing strategy:
    Unit tests. The release repository is replaced by an ``AsyncMock`` that
    controls the state of the returned entity for each scenario.

Key invariants verified:
    - Querying the history of a non-existent release raises ``EntityNotFoundError``.
    - The result is a dictionary that includes the release ID as a string.
    - The dictionary contains the keys ``verdict``, ``duration_ms``, and
      ``rules_evaluated``, defining the API response contract.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.get_verification_history import GetVerificationHistoryUseCase
from domain.entities.release import Release
from domain.entities.enums import ReleaseStatus
from domain.exceptions import EntityNotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_release() -> Release:
    """Builds a test ``Release`` in state ``COMPLETADA``."""
    return Release(
        project_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        version="1.0.0",
        created_by=uuid.uuid4(),
        status=ReleaseStatus.COMPLETADA,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetVerificationHistoryUseCase:
    """
    Unit tests for ``GetVerificationHistoryUseCase``.

    Verifies behavior for non-existent releases and the response dictionary
    structure for found releases.
    """

    async def test_release_not_found_raises_entity_not_found(self):
        """
        Querying the history of a non-existent release raises ``EntityNotFoundError``.

        Given:  A repository that returns ``None`` for any release ID.
        When:   ``GetVerificationHistoryUseCase`` is executed with a random UUID.
        Then:   ``EntityNotFoundError`` is raised, explicitly informing the caller
                that the requested resource does not exist, rather than returning
                an empty result that could be interpreted ambiguously.
        """
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError):
            await GetVerificationHistoryUseCase(repo).execute(uuid.uuid4())

    async def test_returns_dict_with_release_id(self):
        """
        The history includes the release ID serialized as a string.

        Given:  A repository that returns a release in state ``COMPLETADA``.
        When:   The use case is executed with that release's ID.
        Then:   The resulting dictionary contains the key ``"release_id"`` with
                the value ``str(release.id)``, providing the cross-reference
                needed for API consumers to identify the resource.
        """
        release = _make_release()
        repo = AsyncMock()
        repo.get_by_id.return_value = release

        result = await GetVerificationHistoryUseCase(repo).execute(release.id)

        assert result["release_id"] == str(release.id)

    async def test_result_contains_expected_keys(self):
        """
        The history exposes the contract keys defined by the domain.

        Given:  A repository that returns a valid release.
        When:   The use case is executed.
        Then:   The resulting dictionary contains the keys ``"verdict"``,
                ``"duration_ms"``, and ``"rules_evaluated"``, which form the
                minimum response contract consumed by API routers and external clients.
        """
        release = _make_release()
        repo = AsyncMock()
        repo.get_by_id.return_value = release

        result = await GetVerificationHistoryUseCase(repo).execute(release.id)

        assert "verdict" in result
        assert "duration_ms" in result
        assert "rules_evaluated" in result
